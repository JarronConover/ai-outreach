import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

from schemas.input import ICPInput
from schemas.output import PeopleOutput
from agent.tracer import log_trace
from agent.exceptions import StructuredOutputError

load_dotenv()

_ENRICH_SYSTEM_PROMPT = """You are a data enrichment expert. Given partial information about a person or company, use web search to find the missing details.

For a PERSON, try to find: email, phone, LinkedIn URL, job title, and their company's website.
For a COMPANY, try to find: website, industry, address, city, state, zip, phone number, and employee count.

Always return a JSON object with ALL fields filled in as best you can. Use null for fields you cannot find.

For a person, return:
{
  "name": "...",
  "email": "...",
  "company_name": "...",
  "title": "...",
  "phone": "...",
  "linkedin": "...",
  "stage": "prospect"
}

For a company, return:
{
  "name": "...",
  "website": "...",
  "industry": "...",
  "address": "...",
  "city": "...",
  "state": "...",
  "zip": "...",
  "phone": "...",
  "employee_count": null
}

Be specific and accurate. Only include real information you find through search."""

_SYSTEM_PROMPT = """You are a B2B sales prospecting expert. Your job is to find real companies and people who match a given Ideal Customer Profile (ICP).

You have access to a web search tool. Use it to:
1. First, search for real companies that match the ICP's industry, size, and location.
2. For each company, search for: website, industry, street address, city, state, zip, phone number, and employee count.
3. Then, for each company, search for specific people with the target roles (e.g. "VP Engineering at [Company]").
4. Try to find their business email if possible (look for company email format or LinkedIn/company page hints).
5. Search for their LinkedIn profile URL when possible (e.g. "linkedin.com/in/...").

After your research, return a JSON object with this exact structure:
{
  "companies": [
    {
      "name": "Full Company Name",
      "website": "https://company.com",
      "industry": "Industry Name",
      "address": "123 Main St",
      "city": "City",
      "state": "UT",
      "zip": "84101",
      "phone": "801-555-0100",
      "employee_count": "50-200"
    }
  ],
  "people": [
    {
      "id": "unique-string",
      "name": "Full Name",
      "company_id": "company-name-slugified",
      "company_name": "Full Company Name",
      "email": "email@company.com",
      "title": "Their Job Title",
      "linkedin": "https://linkedin.com/in/username",
      "stage": "prospect",
      "last_response": null,
      "last_contact": null,
      "created_at": "2026-02-28T00:00:00",
      "updated_at": "2026-02-28T00:00:00"
    }
  ]
}

Be specific and realistic. Use real company names and real people you find through search.
- Search for the company's official website, office address, phone number, and employee count.
- If you cannot find a specific person's email, make a reasonable guess using the company's email format.
- For company_id, use a slugified version of the company name (e.g., "mind-studios" from "Mind Studios").
- For company_name, use the full human-readable company name (e.g., "Mind Studios").
- For linkedin, only include if you found it; otherwise set to null.
- For employee_count, use a range string like "10-50" or "200-500" if exact count is unknown."""


class ProspectingAgent:
    def __init__(self):
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.environ.get("GOOGLE_API_KEY", ""),
            temperature=0.3,
        )
        self._search_tool = TavilySearch(
            max_results=5,
            tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
        )

    def _build_search_prompt(self, icp: ICPInput) -> str:
        roles = ", ".join(icp.roles_to_target)
        pain_points = ", ".join(icp.pain_points)
        location = f" in {icp.location}" if icp.location else ""
        return (
            f"Find {icp.num_companies} real companies{location} in the {icp.industry} industry "
            f"with {icp.company_size} employees. "
            f"For each company, find {icp.num_people_per_company} people with roles: {roles}. "
            f"These people should care about: {pain_points}. "
            f"Return the results as the JSON structure described."
        )

    def _build_agent_with_exclusions(self, existing_emails: list = None, existing_companies: list = None):
        """Build an agent with existing emails and companies injected into the system prompt."""
        system_prompt = _SYSTEM_PROMPT
        if existing_emails:
            excluded_list = "\n".join([f"- {email}" for email in existing_emails])
            system_prompt += f"\n\nIMPORTANT: Do NOT include these people (already in the system):\n{excluded_list}"
        if existing_companies:
            excluded_companies = "\n".join([f"- {name}" for name in existing_companies])
            system_prompt += f"\n\nIMPORTANT: Do NOT prospect at these companies (already in the system):\n{excluded_companies}\nFind entirely different companies that are NOT on this list."
        return create_react_agent(self._llm, [self._search_tool], prompt=system_prompt)

    def _discover_and_structure_leads(self, icp: ICPInput, existing_emails: list = None, existing_companies: list = None) -> PeopleOutput:
        log_trace("start", {"icp": icp.model_dump(), "existing_emails_count": len(existing_emails or []), "existing_companies_count": len(existing_companies or [])})

        agent = self._build_agent_with_exclusions(existing_emails, existing_companies)

        search_prompt = self._build_search_prompt(icp)
        log_trace("search_prompt", {"prompt": search_prompt})

        result = agent.invoke({"messages": [{"role": "user", "content": search_prompt}]})
        raw_output = result["messages"][-1].content
        # langchain 1.x may return a list of content blocks instead of a plain string
        if isinstance(raw_output, list):
            raw_output = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_output
            )
        log_trace("raw_output", {"output": raw_output})

        try:
            json_match = re.search(r'\{[\s\S]*"people"[\s\S]*\}', raw_output)
            if not json_match:
                raise StructuredOutputError("No JSON people block found in agent output.")
            data = json.loads(json_match.group())
            # Strip LLM-generated ids so Pydantic default_factory generates valid UUID4s
            for person in data.get("people", []):
                if isinstance(person, dict):
                    person.pop("id", None)
            people_output = PeopleOutput(**data)
            log_trace("structured_output", {
                "people_count": len(people_output.people),
                "companies_count": len(people_output.companies),
            })
            return people_output
        except Exception as e:
            raise StructuredOutputError(f"Failed to parse structured output: {e}\nRaw: {raw_output}") from e

    def enrich_entity(self, entity_type: str, partial_data: dict) -> dict:
        """Enrich a partial entity record using web search.

        Args:
            entity_type: "person" or "company"
            partial_data: Dict with whatever fields the user provided

        Returns:
            Enriched dict with as many fields filled as possible
        """
        if entity_type == "person":
            return self._enrich_person(partial_data)
        elif entity_type == "company":
            return self._enrich_company(partial_data)
        return partial_data

    def _enrich_person(self, partial_data: dict) -> dict:
        name = partial_data.get("name", "")
        company = partial_data.get("company_name", "")
        known = {k: v for k, v in partial_data.items() if v}
        known_str = ", ".join(f"{k}: {v}" for k, v in known.items())

        prompt = (
            f"I have partial information about a person. Here is what I know: {known_str}. "
            f"Please search for '{name}' at '{company}' and find: "
            f"their email address, phone number, LinkedIn URL, job title, and any other relevant info. "
            f"Return the result as the JSON structure described in the system prompt."
        )

        agent = create_react_agent(self._llm, [self._search_tool], prompt=_ENRICH_SYSTEM_PROMPT)
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        raw = result["messages"][-1].content
        if isinstance(raw, list):
            raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)

        log_trace("enrich_person_raw", {"output": raw})

        try:
            json_match = re.search(r'\{[\s\S]*"name"[\s\S]*\}', raw)
            if json_match:
                enriched = json.loads(json_match.group())
                # Merge: keep user-provided values, fill in missing ones from enrichment
                merged = {**enriched, **{k: v for k, v in partial_data.items() if v}}
                return merged
        except Exception as e:
            log_trace("enrich_person_parse_error", {"error": str(e)})

        return partial_data

    def _enrich_company(self, partial_data: dict) -> dict:
        name = partial_data.get("name", "")
        known = {k: v for k, v in partial_data.items() if v}
        known_str = ", ".join(f"{k}: {v}" for k, v in known.items())

        prompt = (
            f"I have partial information about a company. Here is what I know: {known_str}. "
            f"Please search for '{name}' and find: their website, industry, address, city, state, zip, "
            f"phone number, and approximate employee count. "
            f"Return the result as the JSON structure described in the system prompt."
        )

        agent = create_react_agent(self._llm, [self._search_tool], prompt=_ENRICH_SYSTEM_PROMPT)
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        raw = result["messages"][-1].content
        if isinstance(raw, list):
            raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)

        log_trace("enrich_company_raw", {"output": raw})

        try:
            json_match = re.search(r'\{[\s\S]*"name"[\s\S]*\}', raw)
            if json_match:
                enriched = json.loads(json_match.group())
                # Merge: keep user-provided values, fill in missing ones from enrichment
                merged = {**enriched, **{k: v for k, v in partial_data.items() if v}}
                return merged
        except Exception as e:
            log_trace("enrich_company_parse_error", {"error": str(e)})

        return partial_data

    def run(self, icp: ICPInput, existing_emails: list = None, existing_companies: list = None) -> PeopleOutput:
        """Run the prospecting agent.

        Args:
            icp: Ideal Customer Profile
            existing_emails: List of emails to exclude from search (optional)
            existing_companies: List of company names to exclude from search (optional)

        Returns:
            PeopleOutput with discovered people
        """
        return self._discover_and_structure_leads(icp, existing_emails, existing_companies)
