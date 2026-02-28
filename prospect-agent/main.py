import sys
import os

# Add prospect-agent directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from schemas.input import ICPInput
from agent.orchestrator import ProspectingAgent
from tools.tool import write_leads_to_sheet
from agent.tracer import log_trace

load_dotenv()

# --- Configure your ICP here ---
ICP = ICPInput(
    industry="SaaS",
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
    leads_output = agent.run(ICP)

    print(f"\nFound {len(leads_output.leads)} leads:")
    for lead in leads_output.leads:
        print(f"  - {lead.name} ({lead.title}) at {lead.company} — {lead.email}")

    log_trace("writing_to_sheets", {"leads_count": len(leads_output.leads)})
    result = write_leads_to_sheet(leads_output)
    print(f"\n{result}")
