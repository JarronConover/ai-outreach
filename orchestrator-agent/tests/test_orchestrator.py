import sys, os
# Insert orchestrator-agent first so its schemas/ takes precedence over prospect-agent's schemas/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "prospect-agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from schemas.input import PipelineInput
from schemas.output import PipelineResult, StageResult
from agent.orchestrator import OrchestratorAgent


@pytest.fixture
def sample_input():
    return PipelineInput(
        industry="SaaS",
        roles_to_target=["CTO"],
        pain_points=["slow deploys"],
        num_companies=2,
        num_people_per_company=1,
        stages=["prospect"],
    )


def test_run_returns_pipeline_result(sample_input):
    agent = OrchestratorAgent()
    mock_stage = StageResult(stage="prospect", status="completed", people_written=1)
    with patch.object(agent, "_run_prospect_stage", return_value=mock_stage):
        result = agent.run(sample_input)
    assert isinstance(result, PipelineResult)
    assert len(result.stages) == 1


def test_run_prospect_stage_only(sample_input):
    agent = OrchestratorAgent()
    mock_stage = StageResult(stage="prospect", status="completed", people_written=2)
    with patch.object(agent, "_run_prospect_stage", return_value=mock_stage) as mock:
        result = agent.run(sample_input)
    mock.assert_called_once()
    assert result.stages[0].stage == "prospect"


def test_outreach_stage_skipped_when_not_in_stages(sample_input):
    """Outreach should be skipped if not in stages list."""
    agent = OrchestratorAgent()
    mock_stage = StageResult(stage="prospect", status="completed", people_written=1, new_person_ids=["id-1"])
    with patch.object(agent, "_run_prospect_stage", return_value=mock_stage):
        result = agent.run(sample_input)
    stage_names = [s.stage for s in result.stages]
    assert "outreach" not in stage_names


def test_outreach_stage_included_when_requested():
    """Outreach stage should appear (as skipped) when requested but not implemented."""
    pipeline_input = PipelineInput(
        industry="SaaS",
        roles_to_target=["CTO"],
        pain_points=["slow deploys"],
        stages=["prospect", "outreach"],
    )
    agent = OrchestratorAgent()
    mock_prospect = StageResult(stage="prospect", status="completed", people_written=1, new_person_ids=["id-1"])
    with patch.object(agent, "_run_prospect_stage", return_value=mock_prospect):
        result = agent.run(pipeline_input)
    stage_names = [s.stage for s in result.stages]
    assert "outreach" in stage_names
    outreach = next(s for s in result.stages if s.stage == "outreach")
    assert outreach.status == "skipped"
