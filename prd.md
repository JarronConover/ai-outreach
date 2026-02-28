PRD: Hackathon MVP — Autonomous AI SDR (Draft-Only, Event-Driven)
1. Objective

Build a working AI SDR demo with autonomous-feeling agents that:

Generate leads

Draft outreach emails

Draft replies to incoming emails

Store all data and drafts in Google Sheets as the source of truth

Respond to events (LEAD_GENERATED, EMAIL_RECEIVED)

Keep user in control for execution (sending emails or applying)

Goal: showcase agentic reasoning and automation in a hackathon-ready MVP.

2. Scope
Included Features
Feature	Description
Prospecting Agent	Finds leads based on ICP, writes them to Sheet
Outreach Agent	Drafts personalized outreach emails for each generated lead
Reply Agent	Drafts responses to incoming emails
Orchestrator Agent	Listens for events and dispatches correct agent
Tools	Google Sheets API, Gmail API (draft only), optional fake enrichment API
Autonomy	Agents reason and draft content independently, but do not execute actions automatically
Excluded / Out-of-Scope

Real LinkedIn scraping / enrichment

Multi-channel outreach (LinkedIn, SMS)

Fully automated email sending without user approval

Persistent memory beyond Sheet + minimal in-memory context

Production-level logging, retries, error handling

3. Architecture

High-Level Flow

User triggers action (button)
        │
        ▼
Prospecting Agent
    - finds leads
    - writes to Google Sheet
        │
        ▼  (LEAD_GENERATED event)
Orchestrator Agent
    - detects event
    - calls Outreach Agent
        │
        ▼
Outreach Agent
    - drafts email for each lead
    - writes draft to Sheet
        │
User reviews → clicks SEND
        │
        ▼  (EMAIL_RECEIVED event)
Orchestrator Agent
    - detects event
    - calls Reply Agent
        │
        ▼
Reply Agent
    - drafts reply
    - writes draft to Sheet
User reviews → clicks SEND

Key Notes:

Google Sheet = source of truth for leads, drafts, stages

User controls execution (sends emails or takes next actions)

Agents remain autonomous in drafting

4. Agent Design & Responsibilities
4.1 Orchestrator Agent

Role: Listens for events in the Sheet and dispatches the correct agent

Event Types:

LEAD_GENERATED → call Outreach Agent

EMAIL_RECEIVED → call Reply Agent

Files:

main.py (handles event detection + dispatch)

tools/ (event reading utilities)

schemas/ (event schemas)

tracer.py (optional reasoning logs)

4.2 Prospecting Agent

Trigger: User clicks “Generate Leads”

Responsibility: Generate leads, write to Google Sheet

Files:

main.py (folded orchestrator, planner, exception handling, tracing)

tools/ (Sheets API, optional enrichment API)

schemas/ (lead JSON schema)

Flow:

Read ICP input

Generate leads (via LLM)

Write leads to Sheet

Log trace of reasoning

4.3 Outreach Agent

Trigger: LEAD_GENERATED event

Responsibility: Draft outreach email per lead, write draft to Sheet

Files: Same structure as Prospecting Agent

Flow:

Read lead data from event/Sheet

Generate email draft via LLM

Write draft (subject + body) to Sheet

Log trace

4.4 Reply Agent

Trigger: EMAIL_RECEIVED event

Responsibility: Draft reply email, write to Sheet

Flow:

Read incoming email from event/Sheet

Classify email type (INTERESTED, NOT_INTERESTED, QUESTION, OTHER)

Generate reply draft

Write draft to Sheet

6. Tools
Tool	Purpose
Google Sheets API	Store leads, drafts, and stages (source of truth)
Gmail API	Send emails manually (after user approval)
Optional enrichment API	Fake data for leads if no real API
7. Data Models / JSON Schemas
Lead Schema
{
  "id": "uuid",
  "name": "string",
  "company": "string",
  "email": "string",
  "stage": "string",
  "last_message": "string",
  "next_action": "string"
}
Email Draft Schema
{
  "lead_id": "uuid",
  "subject": "string",
  "body": "string",
  "status": "draft|sent",
  "timestamp": "ISO string"
}
8. Event Definitions
Event	Description	Trigger
LEAD_GENERATED	Lead added to Sheet	Prospecting Agent completes
EMAIL_RECEIVED	Incoming email detected	Gmail / simulated button
DRAFT_READY	Optional, for logging	Agents write draft to Sheet
9. Workflow Summary

Generate Leads → Prospecting Agent adds leads to Sheet

Outreach Draft → Orchestrator detects LEAD_GENERATED → Outreach Agent drafts emails → updates Sheet

User Review & Send → user clicks send

Reply Draft → Orchestrator detects EMAIL_RECEIVED → Reply Agent drafts reply → updates Sheet

User Review & Send → user clicks send

Google Sheet is the single source of truth, visible for demo and debugging.

10. Hackathon Timeline (~16 Hours)
Phase	Hours	Tasks
0	0–1	Repo setup, LangChain, API keys, Google Sheet skeleton
1	1–3	Prospecting Agent → generate leads, update Sheet
2	3–6	Outreach Agent → draft emails for each lead
3	6–9	Reply Agent → draft replies (simulate email reception)
4	9–11	Orchestrator Agent → detect events, dispatch agents
5	11–13	UI buttons / triggers, Sheet view for user approval
6	13–15	Trace logs, debug, ensure draft-only autonomy
7	15–16	Demo polish & testing
11. Hackathon Considerations

Draft-only model → prevents accidental emails

JSON structured outputs → ensures predictable LLM outputs

Sheet as source of truth → simplifies memory / state handling

Trace logs → optional but helpful for showing agent reasoning during demo

✅ Summary

3 main agents (Prospecting, Outreach, Reply) + Orchestrator

Agents are autonomous in reasoning and drafting, but execution is user-controlled

Google Sheet is the single source of truth

Folded agent structure reduces boilerplate and speeds up hackathon implementation

Event-driven design ensures each agent acts only when triggered
