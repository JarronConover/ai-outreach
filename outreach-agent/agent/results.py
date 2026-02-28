"""Output result models for the outreach agent run."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel


class EmailResult(BaseModel):
    recipient_email: str
    recipient_name: str
    subject: str
    message_id: Optional[str] = None
    # "client_outreach" | "prospect_outreach" | "demo_invite" | "followup_email"
    email_type: str
    sent_at: datetime
    success: bool
    error: Optional[str] = None


class CalendarEventResult(BaseModel):
    event_id: Optional[str] = None
    event_title: str
    event_link: Optional[str] = None
    attendees: list[str]
    start_time: datetime
    end_time: datetime
    # "demo_discovery" | "demo_sync" | "followup"
    event_type: str
    created_at: datetime
    success: bool
    error: Optional[str] = None


class OutreachRunResult(BaseModel):
    """Aggregated result returned after a full orchestrator run."""

    run_at: datetime = datetime.now(timezone.utc)
    dry_run: bool = False

    emails_sent: list[EmailResult] = []
    calendar_events_created: list[CalendarEventResult] = []

    # High-level counters
    clients_contacted: int = 0
    prospects_contacted: int = 0
    demos_scheduled: int = 0
    followups_sent: int = 0

    errors: list[str] = []

    @property
    def total_emails_sent(self) -> int:
        return sum(1 for e in self.emails_sent if e.success)

    @property
    def total_calendar_events(self) -> int:
        return sum(1 for e in self.calendar_events_created if e.success)

    def to_summary_dict(self) -> dict:
        return {
            "run_at": self.run_at.isoformat(),
            "dry_run": self.dry_run,
            "emails_sent": self.total_emails_sent,
            "calendar_events_created": self.total_calendar_events,
            "clients_contacted": self.clients_contacted,
            "prospects_contacted": self.prospects_contacted,
            "demos_scheduled": self.demos_scheduled,
            "followups_sent": self.followups_sent,
            "errors": len(self.errors),
            "error_details": self.errors,
        }
