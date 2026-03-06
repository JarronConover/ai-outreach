"""
Tool 3 – Schedule Demo Meetings

Scans the Demos sheet for every row where:
  • status            = "scheduled"
  • date              is set
  • event_id is empty  (not yet on the calendar)

For each matching demo the tool:
  1. Creates a Google Calendar event with all three attendees:
       • the contact's email
       • SENDER_EMAIL  (from .env)
       • BCC_EMAIL     (from .env, if set)
     Google automatically sends calendar invites to all attendees.
  2. Writes the new event ID back to Demos.event_id (column H).
  3. Writes the demo's ID to People.next_demo_id (column J) for the
     matching person, so the People sheet always reflects the upcoming demo.
  4. Sends a personalised confirmation email to the contact.

This tool is idempotent: once event_id is written the demo is
excluded from future runs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.exceptions import DemoSchedulingError, GmailAPIError
from agent.results import CalendarEventResult, EmailResult
from schemas.crm import CRMContext, DemoStatus
from schemas.sheet_config import DemoColumns, PeopleColumns, SheetNames
from tools.tool import BaseTool

_TEMPLATE = Path(__file__).parent.parent.parent / "business" / "templates" / "demo_invite.html"


def _build_invite_email(
    person_name: str,
    person_email: str,
    company_name: str,
    sender_name: str,
    our_company: str,
    demo_start: datetime,
    meet_link: str | None,
    stage_label: str,
) -> tuple[str, str]:
    date_str = demo_start.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
    meet_section = (
        f'<p>Join via Google Meet: <a href="{meet_link}">{meet_link}</a></p>'
        if meet_link else ""
    )
    subject = f"{stage_label} Confirmed – {our_company} × {company_name}"
    html_body = _TEMPLATE.read_text(encoding="utf-8").format(
        name=person_name,
        email=person_email,
        company_name=company_name,
        sender_name=sender_name,
        our_company=our_company,
        date_str=date_str,
        meet_section=meet_section,
        stage_label=stage_label,
    )
    return subject, html_body


class ScheduleDemoTool(BaseTool):
    """
    Creates calendar events and sends confirmation emails for scheduled demos.

    Filtering criteria (Demos sheet):
        status            = "scheduled"
        date              is set
        event_id is empty

    Calendar attendees: contact email + sender_email + bcc_email (if set)

    Sheet updates on success:
        Demos.event_id ← Google Calendar event ID
        People.next_demo_id     ← demo.id  (for the matching person)
    """

    tool_name = "schedule_demo"

    def _attendees(self, person_email: str) -> list[str]:
        return [
            e for e in [person_email, self.config.sender_email, self.config.bcc_email]
            if e
        ]

    def execute(self, crm: CRMContext) -> list[tuple[CalendarEventResult, EmailResult]]:
        results: list[tuple[CalendarEventResult, EmailResult]] = []

        to_schedule = [
            demo for demo in crm.demos
            if demo.status.lower() == DemoStatus.SCHEDULED
            and demo.date is not None
            and not demo.event_id
        ]

        # Warn about any scheduled demos that will be skipped due to a missing date
        for demo in crm.demos:
            if demo.status.lower() == DemoStatus.SCHEDULED and not demo.event_id and demo.date is None:
                self.tracer.log_calendar_event_skipped(
                    demo.id, f"demo {demo.id} is scheduled but has no parseable date – add a date to the Demos sheet"
                )

        self.tracer.log_tool_start(
            self.tool_name,
            {"demos_to_schedule": len(to_schedule)},
        )

        for demo in to_schedule:
            person = crm.people_by_id.get(demo.people_id)
            if not person or not person.email:
                self.tracer.log_calendar_event_skipped(
                    demo.people_id, "person not found or missing email"
                )
                continue

            company = crm.companies.get(demo.company_id)
            company_name = company.name if company else "their company"

            demo_start: datetime = demo.date  # type: ignore[assignment]
            demo_end = demo_start + timedelta(minutes=self.config.demo_duration_minutes)
            attendees = self._attendees(person.email)
            stage_label = demo.current_stage_label
            event_title = f"{stage_label}: {company_name}"

            if self.config.dry_run:
                self.tracer.log_calendar_event_skipped(person.email, "dry_run=True")
                self.tracer.log_email_skipped(person.email, "dry_run=True")
                _dry_subject, _dry_body = _build_invite_email(
                    person_name=person.name,
                    person_email=person.email,
                    company_name=company_name,
                    sender_name=self.config.sender_name,
                    our_company=self.config.company_name,
                    demo_start=demo_start,
                    meet_link=None,
                    stage_label=stage_label,
                )
                results.append((
                    CalendarEventResult(
                        event_title=event_title,
                        attendees=attendees,
                        start_time=demo_start,
                        end_time=demo_end,
                        event_type=f"demo_{demo.type}",
                        created_at=datetime.now(timezone.utc),
                        success=True,
                        error="dry_run – not created",
                        demo_id=demo.id,
                    ),
                    EmailResult(
                        recipient_email=person.email,
                        recipient_name=person.name,
                        subject=_dry_subject,
                        body=_dry_body,
                        email_type="demo_invite",
                        sent_at=datetime.now(timezone.utc),
                        success=True,
                        error="dry_run – not sent",
                        person_id=person.id,
                    ),
                ))
                continue

            # --- 1. Create Google Calendar event ---
            try:
                event_resp = self.api.create_event(
                    summary=f"{event_title} × {self.config.company_name}",
                    description=(
                        f"{stage_label} with {person.name} from {company_name}.\n\n"
                        f"Demo ID: {demo.id}"
                    ),
                    start=demo_start,
                    end=demo_end,
                    attendees=attendees,
                    timezone=self.config.calendar_timezone,
                    add_meet=self.config.google_meet,
                )
                event_id = event_resp.get("id", "")
                event_link = event_resp.get("htmlLink", "")
                meet_link = (
                    event_resp.get("conferenceData", {})
                    .get("entryPoints", [{}])[0]
                    .get("uri")
                )

                # Write event ID back to Demos sheet (idempotency guard)
                self.api.update_cell(
                    self.config.spreadsheet_id,
                    SheetNames.DEMOS,
                    demo.row_index,
                    DemoColumns.EVENT_ID,
                    event_id,
                )

                # Write demo ID to People.next_demo_id so the People sheet
                # always reflects the contact's upcoming scheduled demo
                self.api.update_cell(
                    self.config.spreadsheet_id,
                    SheetNames.PEOPLE,
                    person.row_index,
                    PeopleColumns.NEXT_DEMO_ID,
                    demo.id,
                )

                self.tracer.log_calendar_event_created(
                    event_id=event_id,
                    event_title=event_title,
                    attendees=attendees,
                    start_time=demo_start.isoformat(),
                    end_time=demo_end.isoformat(),
                    event_type=f"demo_{demo.type}",
                )
                cal_result = CalendarEventResult(
                    event_id=event_id,
                    event_title=event_title,
                    event_link=event_link,
                    attendees=attendees,
                    start_time=demo_start,
                    end_time=demo_end,
                    event_type=f"demo_{demo.type}",
                    created_at=datetime.now(timezone.utc),
                    success=True,
                )

            except Exception as exc:
                err = DemoSchedulingError(
                    f"Calendar creation failed for demo {demo.id} ({person.email}): {exc}"
                )
                self.tracer.log_error(err, {"demo_id": demo.id})
                results.append((
                    CalendarEventResult(
                        event_title=event_title,
                        attendees=attendees,
                        start_time=demo_start,
                        end_time=demo_end,
                        event_type=f"demo_{demo.type}",
                        created_at=datetime.now(timezone.utc),
                        success=False,
                        error=str(err),
                    ),
                    EmailResult(
                        recipient_email=person.email,
                        recipient_name=person.name,
                        subject="",
                        email_type="demo_invite",
                        sent_at=datetime.now(timezone.utc),
                        success=False,
                        error="Calendar event failed; email skipped.",
                    ),
                ))
                continue

            # --- 2. Send confirmation email ---
            subject, html_body = _build_invite_email(
                person_name=person.name,
                person_email=person.email,
                company_name=company_name,
                sender_name=self.config.sender_name,
                our_company=self.config.company_name,
                demo_start=demo_start,
                meet_link=meet_link,
                stage_label=stage_label,
            )
            try:
                email_resp = self.api.send_email(
                    sender=self._sender_address(),
                    to=person.email,
                    subject=subject,
                    html_body=html_body,
                )
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                for col, val in [
                    (PeopleColumns.LAST_CONTACT, now_str),
                    (PeopleColumns.LAST_CONTACT_DATE, now_str),
                ]:
                    self.api.update_cell(
                        self.config.spreadsheet_id,
                        SheetNames.PEOPLE,
                        person.row_index,
                        col,
                        val,
                    )
                self.tracer.log_email_sent(
                    recipient_email=person.email,
                    recipient_name=person.name,
                    subject=subject,
                    message_id=email_resp.get("id", ""),
                    email_type="demo_invite",
                )
                email_result = EmailResult(
                    recipient_email=person.email,
                    recipient_name=person.name,
                    subject=subject,
                    message_id=email_resp.get("id"),
                    email_type="demo_invite",
                    sent_at=datetime.now(timezone.utc),
                    success=True,
                )
            except GmailAPIError as exc:
                self.tracer.log_error(exc, {"demo_id": demo.id})
                email_result = EmailResult(
                    recipient_email=person.email,
                    recipient_name=person.name,
                    subject=subject,
                    email_type="demo_invite",
                    sent_at=datetime.now(timezone.utc),
                    success=False,
                    error=str(exc),
                )

            results.append((cal_result, email_result))

        self.tracer.log_tool_end(
            self.tool_name,
            success=True,
            result_summary=(
                f"{sum(1 for c, _ in results if c.success)}/{len(to_schedule)} "
                "calendar events created"
            ),
        )
        return results
