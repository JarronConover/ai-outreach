import pytest
from schemas.input import ICPInput
from schemas.output import Lead, LeadsOutput


def test_icp_input_valid():
    icp = ICPInput(
        industry="SaaS",
        company_size="50-200 employees",
        roles_to_target=["VP of Engineering", "CTO"],
        pain_points=["slow deployments", "technical debt"],
        location="United States",
        num_companies=3,
        num_people_per_company=2,
    )
    assert icp.num_companies == 3


def test_icp_input_defaults():
    icp = ICPInput(
        industry="Fintech",
        roles_to_target=["Head of Engineering"],
        pain_points=["compliance burden"],
    )
    assert icp.num_companies == 5
    assert icp.num_people_per_company == 2


def test_lead_valid():
    lead = Lead(
        id="abc-123",
        name="Jane Smith",
        company="Acme Corp",
        email="jane@acme.com",
        title="VP of Engineering",
    )
    assert lead.stage == "PROSPECTING"
    assert lead.next_action == "Send outreach email"


def test_leads_output_valid():
    output = LeadsOutput(
        leads=[
            Lead(id="1", name="Jane", company="Acme", email="jane@acme.com", title="CTO")
        ]
    )
    assert len(output.leads) == 1
