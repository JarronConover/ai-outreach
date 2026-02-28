"""Outreach agent configuration schema."""

from __future__ import annotations

from pydantic import BaseModel


class OutreachAgentConfig(BaseModel):
    """Top-level configuration passed to the orchestrator at startup."""

    spreadsheet_id: str

    # Google OAuth credentials paths
    credentials_file: str = "credentials.json"
    token_file: str = "token.pickle"

    # Sender identity
    sender_email: str
    sender_name: str
    company_name: str

    # Calendar settings
    calendar_timezone: str = "America/New_York"
    demo_duration_minutes: int = 60
    followup_duration_minutes: int = 30
    google_meet: bool = True  # attach a Google Meet link to calendar events

    # Outreach cadence (days)
    followup_days: int = 7        # days since last contact before sending a follow-up
    client_checkin_days: int = 30  # days since last contact before checking in with a client

    # Safety
    dry_run: bool = False  # if True, log actions but do not send / create anything
