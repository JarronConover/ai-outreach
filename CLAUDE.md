# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI-Outreach** is an Autonomous Sales Development Representative (SDR) system. AI agents generate leads, draft outreach emails, and handle reply logic—but never send emails without user approval. **Supabase is the single source of truth for all CRM data** (people, companies, demos, actions, emails).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run prospect agent (generates leads from ICP)
python prospect-agent/main.py

# Run outreach agent
python outreach-agent/main.py [--dry-run] [--export-trace]

# Run inbox agent
python inbox-agent/main.py [--dry-run]

# Run API server
uvicorn api.main:app --reload

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
| `prospect-agent/` | Complete — generates leads via Tavily web search + Gemini, writes to Supabase |
| `outreach-agent/` | Complete — sends 5 email types, creates calendar events, reads/writes Supabase |
| `orchestrator-agent/` | Complete — coordinates prospect + outreach agents, executes confirmed actions |
| `inbox-agent/` | Complete — reads Gmail, categorizes replies, writes to Supabase |

### Global Schemas (`schemas/`)

Shared CRM data models used by all agents:
- `schemas/crm.py` — `Person`, `Company`, `Demo`, `Action`, `InboxEmail`, `Stage` (enum), `DemoStatus` (enum), `CRMContext`
- `schemas/sheet_config.py` — Legacy column constants (kept for reference; not used for DB access)

These are the canonical models. Agent-local schemas re-export from here.

### Database (`api/`)

- `api/db.py` — Supabase client singleton (`get_db()`)
- `api/supabase_crud.py` — Shared CRUD for people, companies, demos, actions, emails
- `api/csv_import.py` — Parses uploaded CSV files → inserts into Supabase (the only path that doesn't go through agents)

### Prospect Agent (`prospect-agent/`)

- **LLM**: Gemini 2.5 Flash (via `langchain-google-genai`) — not Claude
- **Search**: Tavily web search (via `langchain-tavily`) to find leads matching an ICP
- **Entry**: `main.py` configures an `ICPInput` and calls `ProspectingAgent`
- **Output**: Writes `Person` + `Company` records to Supabase via `tools/people_sheet.py`, with deduplication by email

### Outreach Agent (`outreach-agent/`)

Has 4 distinct tools in `tools/`, each implementing a `BaseTool` interface from `tools/tool.py`:

| Tool | Trigger Condition | Action |
|------|-------------------|--------|
| `EmailClientsTool` | `stage=client` | Sends check-in email |
| `EmailProspectsTool` | `stage=prospect`, no prior contact | Sends intro email |
| `ScheduleDemoTool` | Demo status = scheduled | Creates calendar event + sends confirmation |
| `ScheduleFollowUpTool` | Mid-pipeline (7-day cadence) | Sends follow-up email |

- `agent/orchestrator.py` — `OutreachOrchestrator` runs all 4 tools sequentially
- `agent/config.py` — `OutreachAgentConfig` (Pydantic) controls dry-run mode and sender identity
- `agent/results.py` — `EmailResult`, `CalendarEventResult`, `OutreachRunResult`
- `agent/tracer.py` — `OutreachTracer` with structured JSON logging
- Uses `google-api-python-client` directly (not LangChain) for Gmail and Google Calendar

### Inbox Agent (`inbox-agent/`)

- Reads unread Gmail messages, categorizes them with Gemini
- Known senders → auto-reply drafted (pending Action); unknown senders → manual review queue
- All state persisted to Supabase `emails` table
- `tools/email_categorizer.py` — Gemini categorization + reply generation

### Orchestrator Agent (`orchestrator-agent/`)

- Coordinates prospect → outreach pipeline
- `execute_confirmed_actions()` — sends emails/creates calendar events when user approves pending actions
- Uses `importlib` isolation to load outreach-agent without namespace collisions

## Environment Variables

Copy `.env.example` (root). Key variables:

```
SUPABASE_URL           # Supabase project URL
SUPABASE_KEY           # Supabase service-role key
GOOGLE_API_KEY         # Gemini API key (prospect-agent + inbox-agent)
TAVILY_API_KEY         # Web search (prospect-agent)
SENDER_EMAIL           # Gmail address used to send outreach
SENDER_NAME            # Display name for outreach emails
COMPANY_NAME           # Your company name
```

Outreach and inbox agents also need OAuth credentials for Gmail and Google Calendar (see `outreach-agent/.env.example`).

## Key Design Decisions

- **Gemini, not Claude**: The prospect-agent and inbox-agent use Gemini 2.5 Flash. The outreach-agent uses direct Google API calls for email/calendar.
- **Draft-only philosophy**: No agent sends emails autonomously. All actions require user approval via the React dashboard.
- **Supabase as source of truth**: All CRM state lives in Supabase (5 tables: people, companies, demos, actions, emails). CSV import is the only non-agent write path.
- **`importlib` isolation**: `orchestrator-agent` and `api/main.py` load agent modules via `importlib` to prevent `schemas.*` namespace collisions between agents.
- **`conftest.py`** at the root adds `prospect-agent/` to `sys.path` for test discovery.
- Each agent has its own `requirements.txt`; root `requirements.txt` covers shared/test deps.
