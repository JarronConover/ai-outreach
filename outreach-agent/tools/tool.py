"""
Base tool class and shared Google API helpers.

All outreach tools inherit from BaseTool and share a single authenticated
GoogleAPIClient instance. The client loads CRM data from Supabase (replacing
the previous Google Sheets reads) and provides update helpers that write back
to Supabase after emails are sent or calendar events are created.
"""

from __future__ import annotations

import base64
import os
import pickle
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agent.config import OutreachAgentConfig
from agent.exceptions import (
    AuthenticationError,
    GmailAPIError,
    GoogleCalendarAPIError,
)
from schemas.crm import CRMContext, Company, Demo, Person

# Ensure project root is in sys.path so `api.*` resolves correctly.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.db import get_db  # noqa: E402

# Google OAuth scopes required by this agent (gmail + calendar only)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]


# ---------------------------------------------------------------------------
# Helpers: build CRM model objects from Supabase row dicts
# ---------------------------------------------------------------------------


def _parse_dt_from_db(val) -> Optional[datetime]:
    """Parse a datetime value returned by Supabase (may be str or datetime)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        # Import the shared parser from schemas
        from schemas.crm import _parse_dt
        return _parse_dt(val)
    return None


def _person_from_dict(row: dict) -> Person:
    return Person(
        row_index=0,
        id=row["id"],
        name=row.get("name", ""),
        company_id=row.get("company_id") or "",
        email=row.get("email", ""),
        phone=row.get("phone") or None,
        linkedin=row.get("linkedin") or None,
        title=row.get("title") or None,
        stage=row.get("stage", "prospect"),
        last_demo_id=None,
        next_demo_id=None,
        last_response=row.get("last_response") or None,
        last_contact=row.get("last_contact") or None,
        last_response_date=_parse_dt_from_db(row.get("last_response_date")),
        last_contact_date=_parse_dt_from_db(row.get("last_contact_date")),
    )


def _company_from_dict(row: dict) -> Company:
    return Company(
        row_index=0,
        id=row["id"],
        name=row.get("name", ""),
        address=row.get("address") or None,
        city=row.get("city") or None,
        state=row.get("state") or None,
        zip=row.get("zip") or None,
        phone=row.get("phone") or None,
        website=row.get("website") or None,
        industry=row.get("industry") or None,
        employee_count=row.get("employee_count") or None,
    )


def _demo_from_dict(row: dict) -> Demo:
    return Demo(
        row_index=0,
        id=row["id"],
        people_id=row["people_id"],
        company_id=row.get("company_id") or "",
        type=row.get("type", "discovery"),
        date=_parse_dt_from_db(row.get("date")),
        status=row.get("status", "scheduled"),
        count=row.get("count"),
        event_id=row.get("event_id") or None,
    )


# ---------------------------------------------------------------------------
# Google API client (shared across all tools)
# ---------------------------------------------------------------------------


class GoogleAPIClient:
    """
    Handles Google OAuth authentication and exposes lazy-loaded service
    clients for Gmail and Calendar. CRM data is loaded from Supabase.
    """

    def __init__(self, credentials_file: str, token_file: str) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self._creds: Optional[Credentials] = None
        self._gmail = None
        self._calendar = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> Credentials:
        creds: Optional[Credentials] = None

        if os.path.exists(self._token_file):
            with open(self._token_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:
                    raise AuthenticationError(
                        f"Failed to refresh Google token: {exc}"
                    ) from exc
            else:
                if not os.path.exists(self._credentials_file):
                    raise AuthenticationError(
                        f"credentials file not found: {self._credentials_file}. "
                        "Download from Google Cloud Console → APIs & Services → Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self._token_file, "wb") as token:
                pickle.dump(creds, token)

        return creds  # type: ignore[return-value]

    @property
    def creds(self) -> Credentials:
        if self._creds is None:
            self._creds = self._authenticate()
        return self._creds

    # ------------------------------------------------------------------
    # Service accessors (lazy)
    # ------------------------------------------------------------------

    @property
    def gmail(self):
        if self._gmail is None:
            self._gmail = build("gmail", "v1", credentials=self.creds)
        return self._gmail

    @property
    def calendar(self):
        if self._calendar is None:
            self._calendar = build("calendar", "v3", credentials=self.creds)
        return self._calendar

    # ------------------------------------------------------------------
    # Gmail helpers
    # ------------------------------------------------------------------

    def send_email(
        self,
        sender: str,
        to: str,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
    ) -> dict:
        """Send an email via Gmail API. Returns the raw API response."""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to

        if plain_body:
            message.attach(MIMEText(plain_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        try:
            return (
                self.gmail.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
        except HttpError as exc:
            raise GmailAPIError(f"Failed to send email to {to}: {exc}") from exc

    # ------------------------------------------------------------------
    # Google Calendar helpers
    # ------------------------------------------------------------------

    def create_event(
        self,
        summary: str,
        description: str,
        start: datetime,
        end: datetime,
        attendees: list,
        timezone: str = "America/New_York",
        add_meet: bool = True,
    ) -> dict:
        """Create a Google Calendar event and return the API response."""
        event_body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone},
            "attendees": [{"email": email} for email in attendees],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        if add_meet:
            event_body["conferenceData"] = {
                "createRequest": {
                    "requestId": f"outreach-{start.isoformat()}-{attendees[0]}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        try:
            return (
                self.calendar.events()
                .insert(
                    calendarId="primary",
                    body=event_body,
                    conferenceDataVersion=1 if add_meet else 0,
                    sendUpdates="all",
                )
                .execute()
            )
        except HttpError as exc:
            raise GoogleCalendarAPIError(
                f"Failed to create calendar event '{summary}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # CRM data loading (from Supabase)
    # ------------------------------------------------------------------

    def load_crm_context(self) -> CRMContext:
        """Read People, Companies, and Demos from Supabase and return a CRMContext."""
        db = get_db()

        people_rows = db.table("people").select("*").execute().data
        company_rows = db.table("companies").select("*").execute().data
        demo_rows = db.table("demos").select("*").execute().data

        people = [_person_from_dict(r) for r in people_rows]
        companies = {r["id"]: _company_from_dict(r) for r in company_rows}
        demos = [_demo_from_dict(r) for r in demo_rows]

        return CRMContext(people=people, companies=companies, demos=demos)

    # ------------------------------------------------------------------
    # Supabase write-back helpers (called by tools after successful sends)
    # ------------------------------------------------------------------

    def update_person(self, person_id: str, payload: dict) -> None:
        """Update a Person record in Supabase."""
        try:
            get_db().table("people").update(payload).eq("id", person_id).execute()
        except Exception as exc:
            print(f"[outreach] warning: failed to update person {person_id}: {exc}")

    def update_demo(self, demo_id: str, payload: dict) -> None:
        """Update a Demo record in Supabase."""
        try:
            get_db().table("demos").update(payload).eq("id", demo_id).execute()
        except Exception as exc:
            print(f"[outreach] warning: failed to update demo {demo_id}: {exc}")


# ---------------------------------------------------------------------------
# Base tool
# ---------------------------------------------------------------------------


class BaseTool(ABC):
    """
    Abstract base for all outreach tools.
    Subclasses must define tool_name and implement execute().
    """

    tool_name: str = "base_tool"

    def __init__(
        self,
        api_client: GoogleAPIClient,
        config: OutreachAgentConfig,
        tracer,  # OutreachTracer – avoid circular import by using duck typing
    ) -> None:
        self.api = api_client
        self.config = config
        self.tracer = tracer

    @abstractmethod
    def execute(self, crm: CRMContext) -> list:
        """Run this tool against the full CRM context and return result objects."""
        ...

    def _sender_address(self) -> str:
        return f"{self.config.sender_name} <{self.config.sender_email}>"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _s(row: list, col: int) -> str:
    return row[col].strip() if col < len(row) else ""


def _col_index_to_letter(index: int) -> str:
    """Convert a 0-based column index to a spreadsheet column letter (A, B, …, AA, …)."""
    letters = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
