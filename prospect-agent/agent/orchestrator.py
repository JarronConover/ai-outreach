import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from schemas.input import ICPInput
from schemas.output import LeadsOutput
from agent.tracer import log_trace
from agent.exceptions import StructuredOutputError

load_dotenv()

_SYSTEM_PROMPT = """You are a B2B sales prospecting expert. Your job is to find real companies and people who match a given Ideal Customer Profile (ICP).

You have access to a web search tool. Use it to:
1. First, search for real companies that match the ICP's industry, size, and location.
2. Then, for each company you find, search for specific people with the target roles (e.g. "VP Engineering at [Company]").
3. Try to find their business email if possible (look for company email format or LinkedIn/company page hints).

After your research, return a JSON object with this exact structure:
{
  "leads": [
    {
      "id": "unique-string",
      "name": "Full Name",
      "company": "Company Name",
      "email": "email@company.com",
      "title": "Their Job Title",
      "stage": "PROSPECTING",
      "last_message": "",
      "next_action": "Send outreach email"
    }
  ]
}

Be specific and realistic. Use real company names and real people you find through search. If you cannot find a specific person's email, make a reasonable guess using the company's email format."""


class ProspectingAgent:
    def __init__(self):
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.environ.get("GOOGLE_API_KEY", ""),
            temperature=0.3,
        )
        self._search_tool = TavilySearch(
            max_results=5,
            tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
        )
        self._agent = create_agent(
            model=self._llm,
            tools=[self._search_tool],
            system_prompt=_SYSTEM_PROMPT,
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

    def _discover_and_structure_leads(self, icp: ICPInput) -> LeadsOutput:
        log_trace("start", {"icp": icp.model_dump()})
        prompt = self._build_search_prompt(icp)
        log_trace("search_prompt", {"prompt": prompt})

        result = self._agent.invoke({"messages": [HumanMessage(content=prompt)]})
        # Extract the final AI message content
        messages = result.get("messages", [])
        raw_output = messages[-1].content if messages else ""
        log_trace("raw_output", {"output": raw_output})

        try:
            json_match = re.search(r'\{[\s\S]*"leads"[\s\S]*\}', raw_output)
            if not json_match:
                raise StructuredOutputError("No JSON leads block found in agent output.")
            data = json.loads(json_match.group())
            leads_output = LeadsOutput(**data)
            log_trace("structured_output", {"leads_count": len(leads_output.leads)})
            return leads_output
        except Exception as e:
            raise StructuredOutputError(f"Failed to parse structured output: {e}\nRaw: {raw_output}") from e

    def run(self, icp: ICPInput) -> LeadsOutput:
        return self._discover_and_structure_leads(icp)
