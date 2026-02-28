from agent.tracer import log_trace
from tools.people_sheet import append_people, filter_duplicates
from agent.orchestrator import ProspectingAgent
from schemas.input import ICPInput
from dotenv import load_dotenv
import sys
import os

# Add prospect-agent directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))


load_dotenv()

# --- Configure your ICP here ---
ICP = ICPInput(
    industry="Personal Injury Law Firms",
    company_size="10-250 employees",
    roles_to_target=["Managing Partner", "Partner", "Founding Partner",
                     "Operations Manager", "Firm Administrator", "Intake Manager", "Intake Director"],
    pain_points=[
        "Missed inbound calls from potential clients",
        "Slow follow-up after initial inquiry",
        "Leads contacting multiple law firms before response",
        "Manual data entry into case management systems",
        "Inconsistent intake questioning between staff members",
        "Unqualified cases reaching attorneys",
        "Qualified cases slipping through the cracks",
        "No after-hours or weekend intake coverage",
        "Delayed conflict checks",
        "Slow retainer agreement generation",
        "Clients dropping off before signing",
        "Poor communication between intake and legal teams",
        "Lack of standardized intake workflow",
        "Difficulty tracking lead-to-signed-case conversion",
        "High intake staff turnover requiring constant retraining",
        "No automated reminders for follow-ups",
        "Fragmented tools (CRM, phone, email not connected)",
        "Limited visibility into intake performance metrics",
        "Marketing spend wasted on unconverted leads",
        "Attorneys spending time on administrative onboarding tasks"
    ],
    location="Utah",
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
        print(
            f"  - {person.name} ({person.title}) at {person.company_id} — {person.email}{linkedin_str}")

    log_trace("writing_to_sheets", {"people_count": len(people_output.people)})
    people_dicts = [p.model_dump() for p in people_output.people]

    # Filter out duplicates
    filtered_people, duplicates = filter_duplicates(people_dicts)

    if duplicates:
        print(f"\n⚠️  Skipped {len(duplicates)} duplicates (already in sheet):")
        for email in duplicates:
            print(f"   - {email}")

    if filtered_people:
        result = append_people(filtered_people)
        print(f"\n✅ {result}")
    else:
        print("\n✅ No new people to add.")
