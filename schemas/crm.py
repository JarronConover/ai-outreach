"""
Pydantic models for the Fellowship CRM Google Sheets database.

Sheets
------
  People    – individual contacts in the sales pipeline
  Companies – organisations that contacts belong to
  Demos     – pipeline tracking for each demo engagement
  Emails    – email log (columns TBD)
  Threads   – thread/conversation log (columns TBD)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums (plain string subclasses so sheet values compare directly)
# ---------------------------------------------------------------------------


class Stage(str):
    """Known values for People.stage.  The field accepts any string."""
    PROSPECT       = "prospect"
    CONTACTED      = "contacted"
    DEMO_SCHEDULED = "demo_scheduled"
    DEMO_COMPLETED = "demo_completed"
    PRICING        = "pricing"
    ONBOARDING     = "onboarding"
    CLIENT         = "client"
    NOT_INTERESTED = "not_interested"
    CHURNED        = "churned"


class DemoStatus(str):
    """Known values for Demo.status."""
    SCHEDULED  = "scheduled"
    COMPLETED  = "completed"
    CANCELED   = "canceled"
    MISSED     = "missed"


# ---------------------------------------------------------------------------
# Helper used by all from_sheet_row() methods
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",   # Google Sheets datetime with seconds
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",   # ISO 8601 with seconds
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S",   # US date with time and seconds
    "%m/%d/%Y %H:%M",      # US date with time
    "%m/%d/%Y",
    "%m/%d/%y %H:%M:%S",
    "%m/%d/%y %H:%M",
    "%m/%d/%y",
)


def _parse_dt(raw: str) -> Optional[datetime]:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _cell(row: list, col: int) -> str:
    return row[col].strip() if col < len(row) else ""


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class Person(BaseModel):
    """
    One row from the People sheet.
    row_index is 1-based (the row number used when writing back to the sheet).
    """
    row_index: int

    id: str
    name: str
    company_id: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    title: Optional[str] = None
    stage: str = Stage.PROSPECT
    last_demo_id: Optional[str] = None
    next_demo_id: Optional[str] = None
    last_response: Optional[str] = None
    last_contact: Optional[str] = None
    last_response_date: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None

    @classmethod
    def from_sheet_row(cls, row: list, row_index: int) -> "Person":
        from schemas.sheet_config import PeopleColumns as PC
        return cls(
            row_index=row_index,
            id=_cell(row, PC.ID),
            name=_cell(row, PC.NAME),
            company_id=_cell(row, PC.COMPANY_ID),
            email=_cell(row, PC.EMAIL),
            phone=_cell(row, PC.PHONE) or None,
            linkedin=_cell(row, PC.LINKEDIN) or None,
            title=_cell(row, PC.TITLE) or None,
            stage=_cell(row, PC.STAGE) or Stage.PROSPECT,
            last_demo_id=_cell(row, PC.LAST_DEMO_ID) or None,
            next_demo_id=_cell(row, PC.NEXT_DEMO_ID) or None,
            last_response=_cell(row, PC.LAST_RESPONSE) or None,
            last_contact=_cell(row, PC.LAST_CONTACT) or None,
            last_response_date=_parse_dt(_cell(row, PC.LAST_RESPONSE_DATE)),
            last_contact_date=_parse_dt(_cell(row, PC.LAST_CONTACT_DATE)),
        )

    # Convenience predicates
    @property
    def is_prospect(self) -> bool:
        return self.stage.lower() == Stage.PROSPECT

    @property
    def is_client(self) -> bool:
        return self.stage.lower() == Stage.CLIENT

    @property
    def is_active(self) -> bool:
        return self.stage.lower() not in (Stage.NOT_INTERESTED, Stage.CHURNED)

    @property
    def needs_initial_outreach(self) -> bool:
        """A prospect with no recorded contact yet."""
        return self.is_prospect and self.last_contact_date is None


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


class Company(BaseModel):
    """One row from the Companies sheet."""
    row_index: int

    id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None

    @classmethod
    def from_sheet_row(cls, row: list, row_index: int) -> "Company":
        from schemas.sheet_config import CompanyColumns as CC

        def _int(col: int) -> Optional[int]:
            raw = _cell(row, col).replace(",", "")
            try:
                return int(raw) if raw else None
            except ValueError:
                return None

        return cls(
            row_index=row_index,
            id=_cell(row, CC.ID),
            name=_cell(row, CC.NAME),
            address=_cell(row, CC.ADDRESS) or None,
            city=_cell(row, CC.CITY) or None,
            state=_cell(row, CC.STATE) or None,
            zip=_cell(row, CC.ZIP) or None,
            phone=_cell(row, CC.PHONE) or None,
            website=_cell(row, CC.WEBSITE) or None,
            industry=_cell(row, CC.INDUSTRY) or None,
            employee_count=_int(CC.EMPLOYEE_COUNT),
        )


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------


class Demo(BaseModel):
    """
    One row from the Demos sheet.

    Columns: id, people_id, company_id, type, date, status, count, event_id

    event_id is written back by the outreach agent after it creates
    a Google Calendar event, making the tool idempotent on subsequent runs.
    """
    row_index: int

    id: str
    people_id: str
    company_id: str

    type: str = "discovery"              # e.g. "discovery", "tech", "pricing", "onboarding"
    date: Optional[datetime] = None      # the scheduled meeting date/time

    status: str = DemoStatus.SCHEDULED   # "scheduled" | "completed" | "canceled" | "missed"
    count: Optional[int] = None
    event_id: Optional[str] = None  # agent-managed (Demos col H, index 7)

    @classmethod
    def from_sheet_row(cls, row: list, row_index: int) -> "Demo":
        from schemas.sheet_config import DemoColumns as DC

        def _int(col: int) -> Optional[int]:
            raw = _cell(row, col)
            try:
                return int(raw) if raw else None
            except ValueError:
                return None

        return cls(
            row_index=row_index,
            id=_cell(row, DC.ID),
            people_id=_cell(row, DC.PEOPLE_ID),
            company_id=_cell(row, DC.COMPANY_ID),
            type=_cell(row, DC.TYPE) or "discovery",
            date=_parse_dt(_cell(row, DC.DATE)),
            status=_cell(row, DC.STATUS) or DemoStatus.SCHEDULED,
            count=_int(DC.COUNT),
            event_id=_cell(row, DC.EVENT_ID) or None,
        )

    @property
    def current_stage_label(self) -> str:
        """Human-readable label derived from the demo type."""
        return self.type.replace("_", " ").title() if self.type else "Discovery"


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


class Action(BaseModel):
    """
    One row from the Actions sheet.

    Represents a planned outreach action (email or calendar event) that has
    been generated by the outreach agent and is awaiting user approval.
    """
    row_index: int

    id: str
    kind: str                           # "email" | "calendar"
    status: str                         # "pending" | "confirming" | "confirmed" | "canceled"
    created_at: str
    confirmed_at: Optional[str] = None

    # Email-only fields
    email_type: Optional[str] = None    # prospect_outreach | client_outreach | followup_email | demo_invite
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    person_id: Optional[str] = None

    # Calendar-only fields
    event_type: Optional[str] = None    # demo_discovery | demo_tech | demo_pricing | …
    event_title: Optional[str] = None
    attendees: list = []                # list[str]
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    demo_id: Optional[str] = None

    @classmethod
    def from_sheet_row(cls, row: list, row_index: int) -> "Action":
        from schemas.sheet_config import ActionColumns as AC

        def _c(col: int) -> str:
            return row[col].strip() if col < len(row) else ""

        attendees_raw = _c(AC.ATTENDEES)
        attendees = [a.strip() for a in attendees_raw.split(",") if a.strip()] if attendees_raw else []

        return cls(
            row_index=row_index,
            id=_c(AC.ID),
            kind=_c(AC.KIND),
            status=_c(AC.STATUS),
            created_at=_c(AC.CREATED_AT),
            confirmed_at=_c(AC.CONFIRMED_AT) or None,
            email_type=_c(AC.EMAIL_TYPE) or None,
            recipient_email=_c(AC.RECIPIENT_EMAIL) or None,
            recipient_name=_c(AC.RECIPIENT_NAME) or None,
            subject=_c(AC.SUBJECT) or None,
            person_id=_c(AC.PERSON_ID) or None,
            event_type=_c(AC.EVENT_TYPE) or None,
            event_title=_c(AC.EVENT_TITLE) or None,
            attendees=attendees,
            start_time=_c(AC.START_TIME) or None,
            end_time=_c(AC.END_TIME) or None,
            demo_id=_c(AC.DEMO_ID) or None,
        )

    def to_sheet_row(self) -> list:
        """Convert to a flat list matching ActionColumns order."""
        return [
            self.id,
            self.kind,
            self.status,
            self.created_at,
            self.confirmed_at or "",
            self.email_type or "",
            self.recipient_email or "",
            self.recipient_name or "",
            self.subject or "",
            self.person_id or "",
            self.event_type or "",
            self.event_title or "",
            ", ".join(self.attendees) if self.attendees else "",
            self.start_time or "",
            self.end_time or "",
            self.demo_id or "",
        ]

    def to_dict(self) -> dict:
        """Convert to the dict format served by the API."""
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "created_at": self.created_at,
            "confirmed_at": self.confirmed_at,
            "email_type": self.email_type,
            "recipient_email": self.recipient_email,
            "recipient_name": self.recipient_name,
            "subject": self.subject,
            "person_id": self.person_id,
            "event_type": self.event_type,
            "event_title": self.event_title,
            "attendees": self.attendees,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "demo_id": self.demo_id,
        }


# ---------------------------------------------------------------------------
# Emails (placeholder)
# ---------------------------------------------------------------------------


class Email(BaseModel):
    """Placeholder model for the Emails sheet.  Columns TBD."""
    row_index: int
    raw_data: dict = {}

    @classmethod
    def from_sheet_row(cls, row: list, row_index: int) -> "Email":
        return cls(row_index=row_index, raw_data={str(i): v for i, v in enumerate(row)})


# ---------------------------------------------------------------------------
# Threads (placeholder)
# ---------------------------------------------------------------------------


class Thread(BaseModel):
    """Placeholder model for the Threads sheet.  Columns TBD."""
    row_index: int
    raw_data: dict = {}

    @classmethod
    def from_sheet_row(cls, row: list, row_index: int) -> "Thread":
        return cls(row_index=row_index, raw_data={str(i): v for i, v in enumerate(row)})


# ---------------------------------------------------------------------------
# Joined view helpers
# ---------------------------------------------------------------------------


@dataclass
class PersonWithCompany:
    """
    A Person record joined with its Company record.
    Passed to email tools so templates can reference both contact and
    company fields without doing the lookup themselves.
    """
    person: Person
    company: Optional[Company] = None

    # Convenience pass-throughs so tools can read pwc.name, pwc.email etc.
    @property
    def name(self) -> str:
        return self.person.name

    @property
    def email(self) -> str:
        return self.person.email

    @property
    def company_name(self) -> str:
        return self.company.name if self.company else "your company"

    @property
    def industry(self) -> Optional[str]:
        return self.company.industry if self.company else None

    @property
    def title(self) -> Optional[str]:
        return self.person.title

    @property
    def stage(self) -> str:
        return self.person.stage

    @property
    def row_index(self) -> int:
        return self.person.row_index


@dataclass
class CRMContext:
    """
    Full snapshot of the CRM data loaded from Google Sheets at the start of
    each outreach run.  Passed to every tool so they can cross-reference
    People ↔ Companies ↔ Demos without additional sheet reads.
    """
    people: list[Person]
    companies: dict[str, Company]       # keyed by Company.id
    demos: list[Demo]

    # Built automatically in __post_init__
    people_by_id: dict[str, Person]             = field(default_factory=dict)
    demos_by_id: dict[str, Demo]                = field(default_factory=dict)
    demos_by_people_id: dict[str, list[Demo]]   = field(default_factory=dict)
    people_with_company: list[PersonWithCompany] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.people_by_id = {p.id: p for p in self.people}

        for demo in self.demos:
            self.demos_by_id[demo.id] = demo
            self.demos_by_people_id.setdefault(demo.people_id, []).append(demo)

        self.people_with_company = [
            PersonWithCompany(
                person=p,
                company=self.companies.get(p.company_id),
            )
            for p in self.people
        ]
