import sys
import os
import uuid
import threading
import time
import importlib.util
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Load orchestrator-agent modules via importlib to avoid namespace collisions
# with prospect-agent's schemas.input / agent.orchestrator.
# ---------------------------------------------------------------------------
def _import_from(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_orch_mod = _import_from(
    os.path.join(os.path.dirname(__file__), "..", "orchestrator-agent", "agent", "orchestrator.py"),
    "orchestrator_agent.agent.orchestrator",
)
OrchestratorAgent = _orch_mod.OrchestratorAgent

_pipeline_input_mod = _import_from(
    os.path.join(os.path.dirname(__file__), "..", "orchestrator-agent", "schemas", "input.py"),
    "orchestrator_agent.schemas.input",
)
PipelineInput = _pipeline_input_mod.PipelineInput

_PROSPECT_AGENT_DIR = os.path.join(os.path.dirname(__file__), "..", "prospect-agent")

# Load prospect-agent leaf modules (no bare import side-effects)
_pa_input = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "schemas", "input.py"), "_api.pa.schemas.input")
_pa_output = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "schemas", "output.py"), "_api.pa.schemas.output")
_pa_tracer = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "agent", "tracer.py"), "_api.pa.agent.tracer")
_pa_exceptions = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "agent", "exceptions.py"), "_api.pa.agent.exceptions")
_pa_tools = _import_from(os.path.join(_PROSPECT_AGENT_DIR, "tools", "people_sheet.py"), "_api.pa.tools.people_sheet")

ICPInput = _pa_input.ICPInput
log_trace = _pa_tracer.log_trace
append_people = _pa_tools.append_people
filter_duplicates = _pa_tools.filter_duplicates
get_existing_people = _pa_tools.get_existing_people
get_company_names = _pa_tools.get_company_names
get_people_dicts = _pa_tools.get_people_dicts
get_demos_dicts = _pa_tools.get_demos_dicts

# prospect-agent/agent/orchestrator.py uses bare imports (`from schemas.input import ICPInput`).
# Swap sys.modules so those bare imports resolve to prospect-agent's modules, not orchestrator-agent's.
_swap_keys = ["schemas.input", "schemas.output", "agent.tracer", "agent.exceptions"]
_saved_mods = {k: sys.modules.get(k) for k in _swap_keys}
try:
    sys.modules["schemas.input"] = _pa_input
    sys.modules["schemas.output"] = _pa_output
    sys.modules["agent.tracer"] = _pa_tracer
    sys.modules["agent.exceptions"] = _pa_exceptions
    _pa_orch = _import_from(
        os.path.join(_PROSPECT_AGENT_DIR, "agent", "orchestrator.py"),
        "_api.pa.agent.orchestrator",
    )
    ProspectingAgent = _pa_orch.ProspectingAgent
finally:
    for _k, _v in _saved_mods.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

load_dotenv()

# ---------------------------------------------------------------------------
# Sheet poller — watches for new PROSPECTING people and fires outreach jobs
# ---------------------------------------------------------------------------
_seen_person_ids: set[str] = set()
_stop_poller = threading.Event()
_POLL_INTERVAL = int(os.getenv("SHEET_POLL_INTERVAL", "15"))  # seconds
_OUTREACH_INTERVAL = int(os.getenv("OUTREACH_INTERVAL_HOURS", "24")) * 3600  # seconds

# Index positions in the People sheet header row
_IDX_ID = 0
_IDX_LAST_CONTACT = 11


def _start_outreach_job() -> str:
    """Enqueue a pipeline job for the outreach stage only."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "type": "poller_outreach",
        "created_at": datetime.utcnow().isoformat(),
    }
    pipeline_input = PipelineInput(
        **_DEFAULT_ICP.model_dump(),
        stages=["outreach"],
    )
    thread = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id, pipeline_input),
        daemon=True,
    )
    thread.start()
    return job_id


def _outreach_ticker():
    """Background thread: fires outreach on a fixed cadence for follow-ups and check-ins."""
    print(f"[ticker] started, interval={_OUTREACH_INTERVAL // 3600}h")
    while not _stop_poller.wait(timeout=_OUTREACH_INTERVAL):
        print("[ticker] scheduled outreach run — triggering follow-ups/check-ins")
        job_id = _start_outreach_job()
        print(f"[ticker] outreach job queued: {job_id}")


def _sheet_poller():
    """Background thread: polls Google Sheets and triggers outreach for new PROSPECTING people."""
    print(f"[poller] started, interval={_POLL_INTERVAL}s")
    while not _stop_poller.wait(timeout=_POLL_INTERVAL):
        try:
            people = get_existing_people()  # dict keyed by email, values are raw rows
            new_ids = []
            for row in people.values():
                person_id = row[_IDX_ID] if len(row) > _IDX_ID else ""
                last_contact = row[_IDX_LAST_CONTACT] if len(row) > _IDX_LAST_CONTACT else ""
                if person_id and not last_contact.strip() and person_id not in _seen_person_ids:
                    _seen_person_ids.add(person_id)
                    new_ids.append(person_id)

            if new_ids:
                print(f"[poller] detected {len(new_ids)} new PROSPECTING person(s) — triggering outreach")
                job_id = _start_outreach_job()
                print(f"[poller] outreach job queued: {job_id}")
        except Exception as e:
            print(f"[poller] error during poll: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed seen IDs from the current sheet state so we don't re-trigger on startup
    try:
        people = get_existing_people()
        for row in people.values():
            pid = row[_IDX_ID] if len(row) > _IDX_ID else ""
            last_contact = row[_IDX_LAST_CONTACT] if len(row) > _IDX_LAST_CONTACT else ""
            if pid and last_contact.strip():
                _seen_person_ids.add(pid)
        print(f"[poller] seeded {len(_seen_person_ids)} already-contacted person IDs")
    except Exception as e:
        print(f"[poller] failed to seed existing people: {e}")

    poller_thread = threading.Thread(target=_sheet_poller, daemon=True)
    poller_thread.start()
    ticker_thread = threading.Thread(target=_outreach_ticker, daemon=True)
    ticker_thread.start()
    yield
    _stop_poller.set()


app = FastAPI(title="AI Outreach API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store
_jobs: dict[str, dict] = {}

# Default ICP — override via request body
_DEFAULT_ICP = ICPInput(
    industry="Personal Injury Law Firms",
    company_size="10-250 employees",
    roles_to_target=[
        "Managing Partner", "Partner", "Founding Partner",
        "Operations Manager", "Firm Administrator", "Intake Manager", "Intake Director",
    ],
    pain_points=[
        "Missed inbound calls from potential clients",
        "Slow follow-up after initial inquiry",
        "Leads contacting multiple law firms before response",
        "Manual data entry into case management systems",
        "No after-hours or weekend intake coverage",
        "High intake staff turnover requiring constant retraining",
    ],
    location="Utah",
    num_companies=1,
    num_people_per_company=5,
)


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


def _run_prospect_job(job_id: str, icp: ICPInput, enable_post_dedup: bool, industry: str = ""):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        existing_people = get_existing_people()
        existing_emails = list(existing_people.keys())

        agent = ProspectingAgent()
        people_output = agent.run(icp, existing_emails=existing_emails)

        log_trace("writing_to_sheets", {"people_count": len(people_output.people)})
        people_dicts = [p.model_dump() for p in people_output.people]

        duplicates_skipped = 0
        if enable_post_dedup:
            people_dicts, duplicates = filter_duplicates(people_dicts)
            duplicates_skipped = len(duplicates)

        if people_dicts:
            append_people(people_dicts, industry=industry)

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = {
            "people_found": len(people_output.people),
            "people_written": len(people_dicts),
            "duplicates_skipped": duplicates_skipped,
            "people": [
                {
                    "name": p.name,
                    "title": p.title,
                    "company": p.company_id,
                    "email": p.email,
                    "linkedin": p.linkedin,
                }
                for p in people_output.people
            ],
        }
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def _run_pipeline_job(job_id: str, pipeline_input: PipelineInput):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        agent = OrchestratorAgent()
        result = agent.run(pipeline_input)

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = result.model_dump()
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


@app.post("/run", status_code=202)
def start_run(req: RunRequest = RunRequest()):
    """Start a full pipeline run through the orchestrator. Returns a job_id to poll."""
    icp_data = _DEFAULT_ICP.model_dump()
    overrides = req.model_dump(
        exclude={"stages", "enable_post_deduplication"},
        exclude_none=True,
    )
    icp_data.update(overrides)

    pipeline_input = PipelineInput(
        **icp_data,
        stages=req.stages,
        enable_post_deduplication=req.enable_post_deduplication,
    )

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "type": "pipeline",
        "created_at": datetime.utcnow().isoformat(),
    }

    thread = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id, pipeline_input),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "pending", "stages": req.stages}


@app.post("/prospect", status_code=202)
def start_prospect(req: ProspectRequest = ProspectRequest()):
    """Start a prospecting run. Returns a job_id to poll for status."""
    # Merge request fields over defaults
    icp_data = _DEFAULT_ICP.model_dump()
    overrides = req.model_dump(exclude={"enable_post_deduplication"}, exclude_none=True)
    icp_data.update(overrides)
    icp = ICPInput(**icp_data)

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    thread = threading.Thread(
        target=_run_prospect_job,
        args=(job_id, icp, req.enable_post_deduplication, icp.industry),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Check the status of a job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
def list_jobs():
    """List all jobs."""
    return list(_jobs.values())


@app.get("/people")
def list_people():
    """List all prospects from Google Sheets, with company_name resolved from Companies sheet."""
    people = get_people_dicts()
    companies = get_company_names()
    for person in people:
        person["company_name"] = companies.get(person.get("company_id", ""), person.get("company_id", ""))
    return people


@app.get("/stats")
def get_stats():
    """Return KPI counts derived from the People and Demos sheets."""
    people = get_people_dicts()
    demos = get_demos_dicts()

    stages = [p.get("stage", "").strip().upper() for p in people]
    demo_statuses = [d.get("status", "").strip().lower() for d in demos]

    return {
        "total_prospects": len(people),
        "interested": sum(1 for s in stages if s == "INTERESTED"),
        "clients": sum(1 for s in stages if s == "CLIENT"),
        "demos_scheduled": sum(1 for s in demo_statuses if s == "scheduled"),
        "demos_completed": sum(1 for s in demo_statuses if s == "completed"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
