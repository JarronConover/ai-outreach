"""
Outreach Agent Orchestrator

Reads People, Companies, and Demos from the "Fellowship CRM" Google Sheet,
builds a CRMContext, then runs all four outreach tools in sequence:

  1. EmailClientsTool     – check-in emails to existing clients
  2. EmailProspectsTool   – intro emails to uncontacted new prospects
  3. ScheduleDemoTool     – calendar events + confirmation emails for scheduled demos;
                            also writes demo.id to People.next_demo_id
  4. ScheduleFollowUpTool – follow-up emails for mid-pipeline contacts gone quiet
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent.config import OutreachAgentConfig
from agent.exceptions import GoogleSheetsAPIError, OutreachAgentError
from agent.results import OutreachRunResult
from agent.tracer import OutreachTracer
from tools.email_clients import EmailClientsTool
from tools.email_prospects import EmailProspectsTool
from tools.schedule_demo import ScheduleDemoTool
from tools.schedule_followup import ScheduleFollowUpTool
from tools.tool import GoogleAPIClient


class OutreachOrchestrator:
    """
    Main orchestrator for the outreach agent.

    Usage
    -----
    config = OutreachAgentConfig(...)
    orchestrator = OutreachOrchestrator(config)
    result = orchestrator.run()
    print(result.to_summary_dict())
    """

    def __init__(self, config: OutreachAgentConfig) -> None:
        self.config = config
        self.tracer = OutreachTracer()
        self.api = GoogleAPIClient(
            credentials_file=config.credentials_file,
            token_file=config.token_file,
        )
        self._init_tools()

    # ------------------------------------------------------------------
    # Tool initialisation
    # ------------------------------------------------------------------

    def _init_tools(self) -> None:
        args = (self.api, self.config, self.tracer)
        self.email_clients_tool     = EmailClientsTool(*args)
        self.email_prospects_tool   = EmailProspectsTool(*args)
        self.schedule_demo_tool     = ScheduleDemoTool(*args)
        self.schedule_followup_tool = ScheduleFollowUpTool(*args)

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self) -> OutreachRunResult:
        result = OutreachRunResult(
            run_at=datetime.now(timezone.utc),
            dry_run=self.config.dry_run,
        )

        self.tracer.log_run_start({
            "spreadsheet_id": self.config.spreadsheet_id,
            "dry_run": self.config.dry_run,
            "sender_email": self.config.sender_email,
        })

        # ------------------------------------------------------------------
        # Load CRM data (People + Companies + Demos) in one pass
        # ------------------------------------------------------------------
        try:
            crm = self.api.load_crm_context(self.config.spreadsheet_id)
        except GoogleSheetsAPIError as exc:
            self.tracer.log_error(exc)
            result.errors.append(str(exc))
            self.tracer.log_run_end(result.to_summary_dict())
            return result

        self.tracer.log_sheet_read(
            spreadsheet_id=self.config.spreadsheet_id,
            sheet_name="People + Companies + Demos",
            row_count=len(crm.people),
        )

        if not crm.people:
            self.tracer.log_run_end({"warning": "No people found in People sheet."})
            return result

        # ------------------------------------------------------------------
        # Tool 1: Check-in emails to existing clients
        # ------------------------------------------------------------------
        try:
            client_emails = self.email_clients_tool.execute(crm)
            result.emails_sent.extend(client_emails)
            result.clients_contacted = sum(1 for e in client_emails if e.success)
        except OutreachAgentError as exc:
            self.tracer.log_error(exc, {"tool": "email_clients"})
            result.errors.append(f"[email_clients] {exc}")

        # ------------------------------------------------------------------
        # Tool 2: Intro emails to new prospects
        # ------------------------------------------------------------------
        try:
            prospect_emails = self.email_prospects_tool.execute(crm)
            result.emails_sent.extend(prospect_emails)
            result.prospects_contacted = sum(1 for e in prospect_emails if e.success)
        except OutreachAgentError as exc:
            self.tracer.log_error(exc, {"tool": "email_prospects"})
            result.errors.append(f"[email_prospects] {exc}")

        # ------------------------------------------------------------------
        # Tool 3: Calendar events + emails for scheduled demos
        # ------------------------------------------------------------------
        try:
            demo_results = self.schedule_demo_tool.execute(crm)
            for cal_res, email_res in demo_results:
                result.calendar_events_created.append(cal_res)
                result.emails_sent.append(email_res)
            result.demos_scheduled = sum(1 for c, _ in demo_results if c.success)
        except OutreachAgentError as exc:
            self.tracer.log_error(exc, {"tool": "schedule_demo"})
            result.errors.append(f"[schedule_demo] {exc}")

        # ------------------------------------------------------------------
        # Tool 4: Follow-up emails for mid-pipeline contacts
        # ------------------------------------------------------------------
        try:
            followup_results = self.schedule_followup_tool.execute(crm)
            result.emails_sent.extend(followup_results)
            result.followups_sent = sum(1 for e in followup_results if e.success)
        except OutreachAgentError as exc:
            self.tracer.log_error(exc, {"tool": "schedule_followup"})
            result.errors.append(f"[schedule_followup] {exc}")

        # ------------------------------------------------------------------
        # Wrap up
        # ------------------------------------------------------------------
        self.tracer.log_run_end(result.to_summary_dict())
        return result

    # ------------------------------------------------------------------
    # Plan (dry-run preview)
    # ------------------------------------------------------------------

    def plan(self) -> OutreachRunResult:
        """
        Run all tools in dry-run mode and return the planned actions.
        The orchestrator's real dry_run setting is restored afterwards.
        """
        original = self.config.dry_run
        self.config = self.config.model_copy(update={"dry_run": True})
        try:
            return self.run()
        finally:
            self.config = self.config.model_copy(update={"dry_run": original})

    def print_plan(self, result: OutreachRunResult) -> None:
        """Print a human-readable preview of every email and calendar event that would be sent."""
        planned_emails = [e for e in result.emails_sent if e.success]
        planned_events = [c for c in result.calendar_events_created if c.success]

        print("\n" + "=" * 60)
        print("  REVIEW – PLANNED ACTIONS")
        print("=" * 60)

        if not planned_emails and not planned_events:
            print("\n  Nothing to send or create based on current CRM data.\n")
            print("=" * 60 + "\n")
            return

        if planned_emails:
            print(f"\n  EMAILS ({len(planned_emails)}):")
            print("  " + "─" * 56)
            for i, e in enumerate(planned_emails, 1):
                label = e.email_type.replace("_", " ").upper()
                print(f"  {i}. [{label}]")
                print(f"     To:      {e.recipient_name} <{e.recipient_email}>")
                print(f"     Subject: {e.subject}")

        if planned_events:
            print(f"\n  CALENDAR EVENTS ({len(planned_events)}):")
            print("  " + "─" * 56)
            for i, c in enumerate(planned_events, 1):
                label = c.event_type.replace("_", " ").upper()
                try:
                    time_str = c.start_time.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
                except Exception:
                    time_str = str(c.start_time)
                print(f"  {i}. [{label}] {c.event_title}")
                print(f"     When:      {time_str}")
                print(f"     Attendees: {', '.join(c.attendees)}")

        parts = []
        if planned_emails:
            parts.append(f"{len(planned_emails)} email{'s' if len(planned_emails) != 1 else ''}")
        if planned_events:
            n = len(planned_events)
            parts.append(f"{n} calendar event{'s' if n != 1 else ''}")
        print("\n  " + "─" * 56)
        print(f"  Total: {' · '.join(parts)}")
        print("=" * 60 + "\n")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def print_summary(self, result: OutreachRunResult) -> None:
        summary = result.to_summary_dict()
        print("\n" + "=" * 60)
        print("  OUTREACH AGENT RUN SUMMARY")
        print("=" * 60)
        for key, value in summary.items():
            if key == "error_details":
                continue
            print(f"  {key:<30} {value}")
        if summary["error_details"]:
            print("\n  ERRORS:")
            for err in summary["error_details"]:
                print(f"    • {err}")
        print("=" * 60 + "\n")

    def export_trace(self, filepath: str) -> None:
        """Write the full execution trace to a JSON file."""
        with open(filepath, "w") as f:
            f.write(self.tracer.dump_history())
