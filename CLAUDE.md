# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI-Outreach** is an Autonomous Sales Development Representative (SDR) system built as a hackathon MVP. It uses autonomous AI agents to generate leads, draft outreach emails, and draft replies to incoming emails—all while keeping the user in control of execution.

**Key Philosophy**: Agents autonomously reason and draft content, but never send emails without user approval. Google Sheets is the single source of truth for all data and drafts.

## Architecture

### Core Agents

The system has 4 agents, each in its own directory with consistent structure:

1. **Orchestrator Agent** (`orchestrator-agent/`)
   - Listens for events in Google Sheets (LEAD_GENERATED, EMAIL_RECEIVED)
   - Dispatches the appropriate agent based on event type
   - Acts as the event router/coordinator

2. **Prospecting Agent** (`prospect-agent/`)
   - Generates leads based on ICP (Ideal Customer Profile)
   - Writes leads to Google Sheets
   - Triggered by user action (e.g., "Generate Leads" button)

3. **Outreach Agent** (`outreach-agent/`)
   - Drafts personalized outreach emails for each lead
   - Triggered by LEAD_GENERATED event
   - Writes draft subject + body to Sheets

4. **Inbox Agent** (`inbox-agent/`)
   - Drafts replies to incoming emails
   - Classifies incoming emails (INTERESTED, NOT_INTERESTED, QUESTION, OTHER)
   - Triggered by EMAIL_RECEIVED event

### Event-Driven Flow

```
User triggers "Generate Leads"
        ↓
   Prospecting Agent → writes leads to Sheets
        ↓ LEAD_GENERATED event
   Orchestrator → Outreach Agent
        ↓
   Outreach Agent → writes drafts to Sheets
        ↓
   User reviews & clicks SEND (manual)
        ↓
   EMAIL_RECEIVED event (simulated or real)
        ↓
   Orchestrator → Inbox Agent
        ↓
   Inbox Agent → writes reply drafts to Sheets
        ↓
   User reviews & clicks SEND
```

### Agent Directory Structure

Each agent directory follows this pattern:

```
{agent-name}/
├── main.py                  # Entry point (currently empty, needs implementation)
├── agent/
│   ├── orchestrator.py      # Agent logic/reasoning (core implementation)
│   ├── exceptions.py        # Custom exceptions
│   └── tracer.py            # Optional: reasoning trace/logging
├── schemas/
│   ├── input.py             # Input data models (Pydantic)
│   └── output.py            # Output data models (Pydantic)
├── tools/
│   └── tool.py              # External API integrations (Sheets, Gmail, enrichment)
└── docs/
    └── text.txt             # Agent-specific documentation
```

This "folded" structure reduces boilerplate while keeping concerns separated.

## Key Technologies & Dependencies

- **Framework**: LangChain (agent orchestration & LLM calls)
- **LLM**: Claude (via Anthropic API)
- **Data Storage**: Google Sheets API (source of truth)
- **Email**: Gmail API (draft only, user controls sending)
- **Data Validation**: Pydantic (schemas for structured outputs)
- **Optional**: Fake enrichment API for demo leads (no real LinkedIn scraping)

## Data Models

### Lead Schema
```json
{
  "id": "uuid",
  "name": "string",
  "company": "string",
  "email": "string",
  "stage": "string",
  "last_message": "string",
  "next_action": "string"
}
```

### Email Draft Schema
```json
{
  "lead_id": "uuid",
  "subject": "string",
  "body": "string",
  "status": "draft|sent",
  "timestamp": "ISO string"
}
```

## Development Setup

### Prerequisites
- Python 3.9+
- Google Sheets API credentials (project needs setup)
- Gmail API credentials (project needs setup)
- Anthropic API key (Claude access)

### Commands (to be implemented)

Once dependencies are installed:

```bash
# Install dependencies
pip install -r requirements.txt

# Run a specific agent
python {agent-name}/main.py

# Run tests (when implemented)
pytest

# Run type checking
mypy .

# Format code
black .

# Lint code
ruff check .
```

### Environment Variables

You'll need to set up:
- `ANTHROPIC_API_KEY` - Claude API key
- `GOOGLE_SHEETS_API_KEY` or credentials file
- `GMAIL_API_KEY` or credentials file
- `GOOGLE_SHEET_ID` - The Sheet ID containing leads, drafts, and events

## Implementation Status

This is an **early-stage hackathon project**. The directory structure and PRD are complete, but **code implementation is just beginning**.

All agent files (`orchestrator.py`, `tool.py`, `input.py`, `output.py`, etc.) are currently empty.

### What Needs to Be Built

1. **Schemas**: Define Pydantic models in each agent's `input.py` and `output.py`
2. **Tools**: Implement Google Sheets and Gmail API interactions in `tools/tool.py`
3. **Agent Logic**: Implement reasoning in `agent/orchestrator.py` using LangChain
4. **Tracing**: Optional debug logging in `agent/tracer.py`
5. **Main Entry Points**: Implement `main.py` for each agent
6. **UI/Buttons**: Simple trigger mechanism for user actions (can be CLI or web interface)
7. **Integration**: Orchestrator event loop that polls Sheets and dispatches agents

## Key Design Notes

- **No Production Error Handling Yet**: The PR notes that this is MVP-level code. Add production-grade retries, timeouts, and error handling as needed.
- **Google Sheets = Single Source of Truth**: All data flows through Sheets for visibility and debugging. This is intentional for hackathon demo purposes.
- **Draft-Only Philosophy**: Agents never send emails directly. All outputs are drafts that users must approve.
- **Structured Outputs**: Use JSON schemas (via Pydantic) to ensure predictable, parseable LLM outputs.
- **Trace Logs**: Include reasoning logs for each agent run (helpful for demos and debugging).

## Tools Integration

### Google Sheets API
- **Read**: Event detection (LEAD_GENERATED, EMAIL_RECEIVED rows)
- **Write**: Store leads, email drafts, trace logs
- **Access**: Service account or OAuth credentials

### Gmail API
- **Read**: Incoming emails (simulated in MVP, can be real later)
- **Write**: Draft emails (user sends manually, not automated)

### Anthropic API (Claude)
- **Tool Use**: Agents use Claude with tool-calling for structured outputs
- **Reasoning**: Include chain-of-thought for agent decisions

## Git Workflow

- **Main branch**: Stable code (only for complete, tested features)
- **Feature branches**: One per agent or feature (e.g., `prospect-agent-impl`, `orchestrator-event-loop`)
- **Commit messages**: Clear, descriptive (e.g., "Implement prospect agent with lead generation")

## Testing Strategy (to implement)

- **Unit tests**: Each agent's logic in isolation
- **Integration tests**: Agent + Sheets API interactions
- **E2E tests**: Full flow from trigger to draft in Sheets
- **Mock data**: Fake leads and emails for testing without real APIs

## Questions for Next Steps

1. **UI**: Will this be CLI-based, web UI, or a Sheets add-on?
2. **Email Service**: Real Gmail or simulated email events?
3. **Enrichment**: Will you use fake data or a real enrichment API?
4. **Async vs Sync**: Should agents run in parallel or sequentially?
5. **Logging Level**: How much trace detail for the demo?

See `prd.md` for the complete specification.
