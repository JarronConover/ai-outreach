import pytest
from unittest.mock import patch, MagicMock
from schemas.input import ICPInput
from schemas.output import Person, PeopleOutput
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
def mock_people_output():
    return PeopleOutput(
        people=[
            Person(
                id="1",
                name="Alice",
                company_id="techcorp",
                email="alice@techcorp.com",
                title="CTO",
                linkedin="https://linkedin.com/in/alice",
            ),
        ]
    )


def test_run_returns_people_output(sample_icp, mock_people_output):
    agent = ProspectingAgent()
    with patch.object(agent, "_discover_and_structure_leads", return_value=mock_people_output):
        result = agent.run(sample_icp)
    assert isinstance(result, PeopleOutput)
    assert len(result.people) >= 1


def test_run_calls_discover(sample_icp, mock_people_output):
    agent = ProspectingAgent()
    with patch.object(agent, "_discover_and_structure_leads", return_value=mock_people_output) as mock_discover:
        agent.run(sample_icp)
    mock_discover.assert_called_once_with(sample_icp)
