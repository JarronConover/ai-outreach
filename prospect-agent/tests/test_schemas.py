import pytest
from schemas.input import ICPInput
from schemas.output import Person, PeopleOutput


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


def test_person_valid():
    person = Person(
        id="abc-123",
        name="Jane Smith",
        company_id="acme-corp",
        email="jane@acme.com",
        title="VP of Engineering",
    )
    assert person.stage == "PROSPECTING"
    assert person.linkedin is None


def test_person_with_linkedin():
    person = Person(
        id="1",
        name="Jane",
        company_id="acme",
        email="jane@acme.com",
        title="CTO",
        linkedin="https://linkedin.com/in/jane",
    )
    assert person.linkedin == "https://linkedin.com/in/jane"


def test_people_output_valid():
    output = PeopleOutput(
        people=[
            Person(
                id="1",
                name="Jane",
                company_id="acme",
                email="jane@acme.com",
                title="CTO",
            )
        ]
    )
    assert len(output.people) == 1
