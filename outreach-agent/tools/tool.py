"""
Base tool class and shared Google API helpers.

All outreach tools inherit from BaseTool and share a single authenticated
GoogleAPIClient instance.  The GoogleAPIClient also loads all three active
CRM sheets (People, Companies, Demos) and assembles a CRMContext so every
tool sees the full relational picture without additional sheet reads.
"""

from __future__ import annotations

import base64
import os
import pickle
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
    GoogleSheetsAPIError,
)
from schemas.crm import CRMContext, Company, Demo, Person
from schemas.sheet_config import (
    CompanyColumns,
    DemoColumns,
    PeopleColumns,
    SheetNames,
)

# Google OAuth scopes required by this agent
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]


# ---------------------------------------------------------------------------
# Google API client (shared across all tools)
# ---------------------------------------------------------------------------


class GoogleAPIClient:
    """
    Handles Google OAuth authentication and exposes lazy-loaded service
    clients for Gmail, Sheets, and Calendar.
    """

    def __init__(self, credentials_file: str, token_file: str) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self._creds: Optional[Credentials] = None
        self._gmail = None
        self._sheets = None
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
    def sheets(self):
        if self._sheets is None:
            self._sheets = build("sheets", "v4", credentials=self.creds)
        return self._sheets

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
        """Send an email via Gmail API.  Returns the raw API response."""
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
    # Google Sheets helpers
    # ------------------------------------------------------------------

    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> list[list]:
        """Return all rows (including header row) from a sheet tab."""
        try:
            result = (
                self.sheets.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=sheet_name)
                .execute()
            )
            return result.get("values", [])
        except HttpError as exc:
            raise GoogleSheetsAPIError(
                f"Failed to read sheet '{sheet_name}': {exc}"
            ) from exc

    def update_cell(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_index: int,
        col_index: int,
        value: str,
    ) -> None:
        """Update a single cell.  row_index is 1-based (matching the sheet row number)."""
        col_letter = _col_index_to_letter(col_index)
        range_notation = f"{sheet_name}!{col_letter}{row_index}"
        try:
            self.sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueInputOption="USER_ENTERED",
                body={"values": [[value]]},
            ).execute()
        except HttpError as exc:
            raise GoogleSheetsAPIError(
                f"Failed to update cell {range_notation}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Google Calendar helpers
    # ------------------------------------------------------------------

    def create_event(
        self,
        summary: str,
        description: str,
        start: datetime,
        end: datetime,
        attendees: list[str],
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
                    sendUpdates="all",  # emails invites to attendees automatically
                )
                .execute()
            )
        except HttpError as exc:
            raise GoogleCalendarAPIError(
                f"Failed to create calendar event '{summary}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # CRM data loading
    # ------------------------------------------------------------------

    def load_crm_context(self, spreadsheet_id: str) -> CRMContext:
        """
        Read People, Companies, and Demos sheets and return a CRMContext.
        The header row (row 0) of each sheet is skipped.
        """
        people_rows = self.read_sheet(spreadsheet_id, SheetNames.PEOPLE)
        company_rows = self.read_sheet(spreadsheet_id, SheetNames.COMPANIES)
        demo_rows = self.read_sheet(spreadsheet_id, SheetNames.DEMOS)

        people = _parse_people(people_rows)
        companies = {c.id: c for c in _parse_companies(company_rows)}
        demos = _parse_demos(demo_rows)

        return CRMContext(people=people, companies=companies, demos=demos)


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
# Sheet parsing helpers
# ---------------------------------------------------------------------------


def _parse_people(rows: list[list]) -> list[Person]:
    people = []
    for i, row in enumerate(rows[1:], start=2):  # skip header; 1-based index starts at 2
        if len(row) <= PeopleColumns.EMAIL or not _s(row, PeopleColumns.EMAIL):
            continue
        try:
            people.append(Person.from_sheet_row(row, row_index=i))
        except Exception:
            pass
    return people


def _parse_companies(rows: list[list]) -> list[Company]:
    companies = []
    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= CompanyColumns.NAME or not _s(row, CompanyColumns.NAME):
            continue
        try:
            companies.append(Company.from_sheet_row(row, row_index=i))
        except Exception:
            pass
    return companies


def _parse_demos(rows: list[list]) -> list[Demo]:
    demos = []
    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= DemoColumns.PEOPLE_ID or not _s(row, DemoColumns.PEOPLE_ID):
            continue
        try:
            demos.append(Demo.from_sheet_row(row, row_index=i))
        except Exception:
            pass
    return demos


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
