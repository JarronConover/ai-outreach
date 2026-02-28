import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from schemas.input import ICPInput
from schemas.output import PeopleOutput
from agent.tracer import log_trace
from agent.exceptions import StructuredOutputError

load_dotenv()

_SYSTEM_PROMPT = """You are a B2B sales prospecting expert. Your job is to find real companies and people who match a given Ideal Customer Profile (ICP).

You have access to a web search tool. Use it to:
1. First, search for real companies that match the ICP's industry, size, and location.
2. Then, for each company you find, search for specific people with the target roles (e.g. "VP Engineering at [Company]").
3. Try to find their business email if possible (look for company email format or LinkedIn/company page hints).
4. Search for their LinkedIn profile URL when possible (e.g. "linkedin.com/in/...").

After your research, return a JSON object with this exact structure:
{
  "people": [
    {
      "id": "unique-string",
      "name": "Full Name",
      "company_id": "company-name-slugified",
      "email": "email@company.com",
      "title": "Their Job Title",
      "linkedin": "https://linkedin.com/in/username",
      "stage": "PROSPECTING",
      "last_response": null,
      "last_contact": null,
      "created_at": "2026-02-28T00:00:00",
      "updated_at": "2026-02-28T00:00:00"
    }
  ]
}

Be specific and realistic. Use real company names and real people you find through search.
- If you cannot find a specific person's email, make a reasonable guess using the company's email format.
- For company_id, use a slugified version of the company name (e.g., "mind-studios" from "Mind Studios").
- For linkedin, only include if you found it; otherwise set to null."""


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

    def _build_agent_with_exclusions(self, existing_emails: list = None) -> AgentExecutor:
        """Build an AgentExecutor with existing emails injected into the system prompt."""
        system_prompt = _SYSTEM_PROMPT
        if existing_emails:
            excluded_list = "\n".join([f"- {email}" for email in existing_emails])
            system_prompt += f"\n\nIMPORTANT: Do NOT include these people (already in the system):\n{excluded_list}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(self._llm, [self._search_tool], prompt)
        return AgentExecutor(agent=agent, tools=[self._search_tool], verbose=False)

    def _discover_and_structure_leads(self, icp: ICPInput, existing_emails: list = None) -> PeopleOutput:
        log_trace("start", {"icp": icp.model_dump(), "existing_emails_count": len(existing_emails or [])})

        executor = self._build_agent_with_exclusions(existing_emails)

        search_prompt = self._build_search_prompt(icp)
        log_trace("search_prompt", {"prompt": search_prompt})

        result = executor.invoke({"input": search_prompt})
        raw_output = result.get("output", "")
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
            log_trace("structured_output", {"people_count": len(people_output.people)})
            return people_output
        except Exception as e:
            raise StructuredOutputError(f"Failed to parse structured output: {e}\nRaw: {raw_output}") from e

    def run(self, icp: ICPInput, existing_emails: list = None) -> PeopleOutput:
        """Run the prospecting agent.

        Args:
            icp: Ideal Customer Profile
            existing_emails: List of emails to exclude from search (optional)

        Returns:
            PeopleOutput with discovered people
        """
        return self._discover_and_structure_leads(icp, existing_emails)
