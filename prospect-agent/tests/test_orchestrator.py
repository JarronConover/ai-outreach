import pytest
from unittest.mock import patch, MagicMock
from schemas.input import ICPInput
from schemas.output import Lead, LeadsOutput
from agent.orchestrator import ProspectingAgent


@pytest.fixture
def sample_icp():
    return ICPInput(
        industry="SaaS",
        roles_to_target=["CTO", "VP Engineering"],
        pain_points=["slow CI/CD", "scaling issues"],
        num_companies=2,
        num_people_per_company=1,
    )


@pytest.fixture
def mock_leads_output():
    return LeadsOutput(
        leads=[
            Lead(id="1", name="Alice", company="TechCorp", email="alice@techcorp.com", title="CTO"),
        ]
    )


def test_run_returns_leads_output(sample_icp, mock_leads_output):
    agent = ProspectingAgent()
    with patch.object(agent, "_discover_and_structure_leads", return_value=mock_leads_output):
        result = agent.run(sample_icp)
    assert isinstance(result, LeadsOutput)
    assert len(result.leads) >= 1


def test_run_calls_discover(sample_icp, mock_leads_output):
    agent = ProspectingAgent()
    with patch.object(agent, "_discover_and_structure_leads", return_value=mock_leads_output) as mock_discover:
        agent.run(sample_icp)
    mock_discover.assert_called_once_with(sample_icp)
