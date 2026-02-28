import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "prospect-agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from schemas.input import PipelineInput
from schemas.output import StageResult, PipelineResult


def test_pipeline_input_defaults():
    p = PipelineInput(
        industry="SaaS",
        roles_to_target=["CTO"],
        pain_points=["slow deploys"],
    )
    assert p.stages == ["prospect"]
    assert p.num_companies == 5


def test_pipeline_input_custom_stages():
    p = PipelineInput(
        industry="SaaS",
        roles_to_target=["CTO"],
        pain_points=["slow deploys"],
        stages=["prospect", "outreach"],
    )
    assert "outreach" in p.stages


def test_stage_result_fields():
    r = StageResult(stage="prospect", status="completed", people_written=3)
    assert r.people_written == 3
    assert r.error is None


def test_pipeline_result_collects_stages():
    result = PipelineResult(
        pipeline_job_id="abc-123",
        stages=[
            StageResult(stage="prospect", status="completed", people_written=2),
            StageResult(stage="outreach", status="skipped"),
        ],
    )
    assert len(result.stages) == 2
