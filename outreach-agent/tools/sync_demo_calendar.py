"""
Tool 5 – Sync Demo Dates to Google Calendar

Scans every Demo record in the Demos sheet for rows where a discovery_date
is set but calendar_event_id is still empty.  This catches demos whose dates
were manually entered into the sheet (by a human or another agent) but for
which no Google Calendar event was ever created.

For each such demo the tool:
  1. Looks up the Person and Company from the CRM context.
  2. Creates a Google Calendar event – Google sends the attendee an invite.
  3. Writes the new event ID back to Demos.calendar_event_id (column P).

This tool is idempotent: once an event ID is written to the sheet the demo
is excluded from future runs.

Difference from ScheduleDemoTool:
  ScheduleDemoTool  → finds demos with status="scheduled", creates event + sends email
  SyncDemoCalendarTool → finds ANY demo with a date set but no event, calendar-only sync
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.exceptions import GoogleCalendarAPIError
from agent.results import CalendarEventResult
from schemas.crm import CRMContext, Demo
from schemas.sheet_config import DemoColumns, SheetNames
from tools.tool import BaseTool


class SyncDemoCalendarTool(BaseTool):
    """
    Idempotent sync: creates Google Calendar events for any demo with a
    discovery_date set but no calendar_event_id yet.

    Filtering criteria (Demos sheet):
        discovery_date    is set
        calendar_event_id is empty

    Sheet updates on success (Demos tab):
        calendar_event_id ← Google Calendar event ID
    """

    tool_name = "sync_demo_calendar"

    def execute(self, crm: CRMContext) -> list[CalendarEventResult]:
        results: list[CalendarEventResult] = []

        to_sync = [
            demo for demo in crm.demos
            if demo.discovery_date is not None
            and not demo.calendar_event_id
        ]

        self.tracer.log_tool_start(
            self.tool_name,
            {"demos_to_sync": len(to_sync)},
        )

        for demo in to_sync:
            person = crm.people_by_id.get(demo.people_id)
            if not person or not person.email:
                self.tracer.log_calendar_event_skipped(
                    demo.people_id, "person not found or missing email"
                )
                continue

            company = crm.companies.get(demo.company_id)
            company_name = company.name if company else "their company"

            demo_start: datetime = demo.discovery_date  # type: ignore[assignment]
            demo_end = demo_start + timedelta(minutes=self.config.demo_duration_minutes)
            attendees = [person.email, self.config.sender_email]

            if self.config.dry_run:
                self.tracer.log_calendar_event_skipped(person.email, "dry_run=True")
                results.append(CalendarEventResult(
                    event_title=f"Discovery: {company_name}",
                    attendees=attendees,
                    start_time=demo_start,
                    end_time=demo_end,
                    event_type="demo_sync",
                    created_at=datetime.now(timezone.utc),
                    success=True,
                    error="dry_run – not created",
                ))
                continue

            try:
                event_resp = self.api.create_event(
                    summary=f"Discovery: {company_name} × {self.config.company_name}",
                    description=(
                        f"Discovery call synced from Fellowship CRM.\n"
                        f"Contact : {person.name} ({person.email})\n"
                        f"Company : {company_name}\n"
                        f"Demo ID : {demo.id}\n"
                        f"Notes   : {demo.discovery or 'N/A'}"
                    ),
                    start=demo_start,
                    end=demo_end,
                    attendees=attendees,
                    timezone=self.config.calendar_timezone,
                    add_meet=self.config.google_meet,
                )
                event_id = event_resp.get("id", "")
                event_link = event_resp.get("htmlLink", "")

                # Write event ID to Demos sheet (column P)
                self.api.update_cell(
                    self.config.spreadsheet_id,
                    SheetNames.DEMOS,
                    demo.row_index,
                    DemoColumns.CALENDAR_EVENT_ID,
                    event_id,
                )

                self.tracer.log_calendar_event_created(
                    event_id=event_id,
                    event_title=f"Discovery: {company_name}",
                    attendees=attendees,
                    start_time=demo_start.isoformat(),
                    end_time=demo_end.isoformat(),
                    event_type="demo_sync",
                )
                results.append(CalendarEventResult(
                    event_id=event_id,
                    event_title=f"Discovery: {company_name}",
                    event_link=event_link,
                    attendees=attendees,
                    start_time=demo_start,
                    end_time=demo_end,
                    event_type="demo_sync",
                    created_at=datetime.now(timezone.utc),
                    success=True,
                ))

            except Exception as exc:
                err = GoogleCalendarAPIError(
                    f"Failed to sync calendar for demo {demo.id} ({person.email}): {exc}"
                )
                self.tracer.log_error(err, {"demo_id": demo.id})
                results.append(CalendarEventResult(
                    event_title=f"Discovery: {company_name}",
                    attendees=attendees,
                    start_time=demo_start,
                    end_time=demo_end,
                    event_type="demo_sync",
                    created_at=datetime.now(timezone.utc),
                    success=False,
                    error=str(err),
                ))

        self.tracer.log_tool_end(
            self.tool_name,
            success=True,
            result_summary=f"Synced {sum(1 for r in results if r.success)}/{len(to_sync)} events",
        )
        return results
