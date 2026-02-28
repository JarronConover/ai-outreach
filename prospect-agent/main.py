import sys
import os

# Add prospect-agent directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from schemas.input import ICPInput
from agent.orchestrator import ProspectingAgent
from tools.people_sheet import append_people
from agent.tracer import log_trace

load_dotenv()

# --- Configure your ICP here ---
ICP = ICPInput(
    industry="Personal Injury Law Firms",
    company_size="50-200 employees",
    roles_to_target=["VP of Engineering", "CTO", "Head of Engineering"],
    pain_points=["slow CI/CD pipelines", "developer productivity", "scaling engineering teams"],
    location="United States",
    num_companies=3,
    num_people_per_company=2,
)

if __name__ == "__main__":
    print("Starting Prospecting Agent...")
    agent = ProspectingAgent()
    people_output = agent.run(ICP)

    print(f"\nFound {len(people_output.people)} people:")
    for person in people_output.people:
        linkedin_str = f" | {person.linkedin}" if person.linkedin else ""
        print(f"  - {person.name} ({person.title}) at {person.company_id} — {person.email}{linkedin_str}")

    log_trace("writing_to_sheets", {"people_count": len(people_output.people)})
    people_dicts = [p.model_dump() for p in people_output.people]
    result = append_people(people_dicts)
    print(f"\n{result}")
