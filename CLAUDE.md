# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI-Outreach** is an Autonomous Sales Development Representative (SDR) system. AI agents generate leads, draft outreach emails, and handle reply logic—but never send emails without user approval. Google Sheets is the single source of truth for all CRM data.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run prospect agent (generates leads from ICP)
python prospect-agent/main.py

# Run outreach agent
python outreach-agent/main.py [--dry-run] [--export-trace]

# Run tests (prospect-agent has tests; others do not yet)
pytest prospect-agent/tests/

# Run a single test file
pytest prospect-agent/tests/test_orchestrator.py

# Type checking / linting
mypy .
ruff check .
black .
```

## Architecture

### Implementation Status

| Agent | Status |
|-------|--------|
| `prospect-agent/` | Complete — generates leads via Tavily web search + Gemini |
| `outreach-agent/` | Complete — sends 5 email types, creates calendar events |
| `orchestrator-agent/` | Empty — was meant to route events from Sheets to agents |
| `inbox-agent/` | Empty — was meant to draft replies to incoming emails |

### Global Schemas (`schemas/`)

Shared CRM data models used by all agents:
- `schemas/crm.py` — `Person`, `Company`, `Demo`, `Email`, `Thread`, `Stage` (enum), `DemoStatus` (enum), `CRMContext`
- `schemas/sheet_config.py` — Column index constants (`PeopleColumns`, `CompanyColumns`, `DemoColumns`) and `SheetNames` for all 3 Google Sheets tabs

These are the canonical models. Agent-local schemas re-export from here.

### Prospect Agent (`prospect-agent/`)

- **LLM**: Gemini 2.5 Flash (via `langchain-google-genai`) — not Claude
- **Search**: Tavily web search (via `langchain-tavily`) to find leads matching an ICP
- **Entry**: `main.py` configures an `ICPInput` and calls `ProspectingAgent`
- **Output**: Writes `Person` records to Google Sheets via `tools/people_sheet.py` (gspread), with deduplication by email
- **Note**: `tools/tool.py` exists but is broken (references a non-existent `LeadsOutput`); use `tools/people_sheet.py` instead

### Outreach Agent (`outreach-agent/`)

The most complete agent. Has 5 distinct tools in `tools/`, each implementing a `BaseTool` interface from `tools/tool.py`:

| Tool | Trigger Condition | Action |
|------|-------------------|--------|
| `EmailClientsTool` | `stage=client` | Sends check-in email |
| `EmailProspectsTool` | `stage=prospect`, no prior contact | Sends intro email |
| `ScheduleDemoTool` | Demo status = scheduled | Creates calendar event + sends confirmation |
| `ScheduleFollowUpTool` | Mid-pipeline (7-day cadence) | Sends follow-up email |
| `SyncDemoCalendarTool` | Manually-entered demo dates | Syncs to Google Calendar |

- `agent/orchestrator.py` — `OutreachOrchestrator` runs all 5 tools sequentially
- `agent/config.py` — `OutreachAgentConfig` (Pydantic) controls which tools run and dry-run mode
- `agent/results.py` — `EmailResult`, `CalendarEventResult`, `OutreachRunResult`
- `agent/tracer.py` — `OutreachTracer` with structured JSON logging
- Uses `google-api-python-client` directly (not LangChain) for Gmail and Google Calendar

## Environment Variables

Copy `.env.example` (root) and `outreach-agent/.env.example`. Key variables:

```
GOOGLE_API_KEY         # Gemini API key (prospect-agent)
TAVILY_API_KEY         # Web search (prospect-agent)
GOOGLE_SHEET_ID        # Sheet ID for all CRM data
```

Outreach agent also needs OAuth credentials for Gmail and Google Calendar (see `outreach-agent/.env.example`).

## Key Design Decisions

- **Gemini, not Claude**: The prospect-agent uses Gemini 2.5 Flash. The outreach-agent uses direct Google API calls for email/calendar, not an LLM.
- **Draft-only philosophy**: No agent sends emails autonomously. All actions require user approval via Sheets.
- **`conftest.py`** at the root adds `prospect-agent/` to `sys.path` for test discovery.
- Each agent has its own `requirements.txt`; root `requirements.txt` covers shared/test deps.
