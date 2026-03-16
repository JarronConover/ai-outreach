import threading
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.agent_loader import get_default_icp, PipelineInput
from backend.services.jobs import (
    _jobs,
    _make_job,
    _orchestrator_job_id,
    _orchestrator_lock,
    run_pipeline_job,
)

router = APIRouter(tags=["orchestrator"])


class ProspectRequest(BaseModel):
    industry: Optional[str] = None
    company_size: Optional[str] = None
    roles_to_target: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    location: Optional[str] = None
    num_companies: Optional[int] = None
    num_people_per_company: Optional[int] = None
    enable_post_deduplication: bool = True


class RunRequest(BaseModel):
    industry: Optional[str] = None
    company_size: Optional[str] = None
    roles_to_target: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    location: Optional[str] = None
    num_companies: Optional[int] = None
    num_people_per_company: Optional[int] = None
    stages: List[str] = ["prospect"]
    enable_post_deduplication: bool = True


def _build_pipeline_input(req: RunRequest) -> PipelineInput:
    # Reload ICP from disk each time so References page edits are picked up immediately
    icp_data = get_default_icp().model_dump()
    overrides = req.model_dump(
        exclude={"stages", "enable_post_deduplication"},
        exclude_none=True,
    )
    icp_data.update(overrides)
    return PipelineInput(
        **icp_data,
        stages=req.stages,
        enable_post_deduplication=req.enable_post_deduplication,
    )


# ---------------------------------------------------------------------------
# Pipeline / prospect
# ---------------------------------------------------------------------------

@router.post("/run", status_code=202)
def start_run(req: RunRequest = RunRequest()):
    """Start a full pipeline run through the orchestrator."""
    pipeline_input = _build_pipeline_input(req)
    job_id, _ = _make_job("pipeline")
    threading.Thread(target=run_pipeline_job, args=(job_id, pipeline_input), daemon=True).start()
    return {"job_id": job_id, "status": "pending", "stages": req.stages}


@router.post("/prospect", status_code=202)
def start_prospect(req: ProspectRequest = ProspectRequest()):
    """Send a prospect request to the orchestrator, which activates the prospect agent."""
    run_req = RunRequest(
        industry=req.industry,
        company_size=req.company_size,
        roles_to_target=req.roles_to_target,
        pain_points=req.pain_points,
        location=req.location,
        num_companies=req.num_companies,
        num_people_per_company=req.num_people_per_company,
        stages=["prospect"],
        enable_post_deduplication=req.enable_post_deduplication,
    )
    pipeline_input = _build_pipeline_input(run_req)
    job_id, _ = _make_job("prospect")
    threading.Thread(target=run_pipeline_job, args=(job_id, pipeline_input), daemon=True).start()
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Check the status of a job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs")
def list_jobs():
    """List all jobs."""
    return list(_jobs.values())


# ---------------------------------------------------------------------------
# Orchestrator process control
# ---------------------------------------------------------------------------

@router.post("/orchestrator/start", status_code=202)
def start_orchestrator(req: RunRequest = RunRequest()):
    """Start the orchestrator pipeline. Returns existing job_id if already running."""
    import backend.services.jobs as _jobs_module
    with _orchestrator_lock:
        if _jobs_module._orchestrator_job_id:
            existing = _jobs.get(_jobs_module._orchestrator_job_id, {})
            if existing.get("status") in ("pending", "running"):
                return {"status": "already_running", "job_id": _jobs_module._orchestrator_job_id}

        pipeline_input = _build_pipeline_input(req)
        job_id, _ = _make_job("orchestrator_pipeline")
        _jobs_module._orchestrator_job_id = job_id

        threading.Thread(target=run_pipeline_job, args=(job_id, pipeline_input), daemon=True).start()
        return {"job_id": job_id, "status": "pending"}


@router.post("/orchestrator/stop")
def stop_orchestrator():
    """Signal the running orchestrator job to stop."""
    import backend.services.jobs as _jobs_module
    with _orchestrator_lock:
        oid = _jobs_module._orchestrator_job_id
        if not oid:
            return {"status": "not_running"}
        job = _jobs.get(oid)
        if not job or job.get("status") not in ("pending", "running"):
            _jobs_module._orchestrator_job_id = None
            return {"status": "not_running"}
        _jobs[oid]["status"] = "canceled"
        _jobs[oid]["completed_at"] = datetime.utcnow().isoformat()
        _jobs_module._orchestrator_job_id = None
        return {"status": "stopped", "job_id": oid}


@router.get("/orchestrator/status")
def orchestrator_status():
    """Return the current orchestrator run state."""
    import backend.services.jobs as _jobs_module
    with _orchestrator_lock:
        oid = _jobs_module._orchestrator_job_id
        if not oid:
            return {"status": "idle", "job_id": None}
        job = _jobs.get(oid)
        if not job:
            _jobs_module._orchestrator_job_id = None
            return {"status": "idle", "job_id": None}
        s = job.get("status", "idle")
        if s in ("completed", "failed", "canceled"):
            _jobs_module._orchestrator_job_id = None
            return {"status": "idle", "job_id": None}
        return {"status": s, "job_id": oid}
