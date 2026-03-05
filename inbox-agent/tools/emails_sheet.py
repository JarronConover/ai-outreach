"""CRUD helpers for the Emails sheet in Google Sheets.

The Emails sheet stores one row per inbound email processed by the inbox-agent.

Column layout matches schemas/sheet_config.EmailColumns (0-based):
    A  id
    B  message_id        (Gmail message ID — dedup key)
    C  from_email
    D  from_name
    E  people_id         (matched Person.id, or "")
    F  subject
    G  body_snippet      (first 500 chars)
    H  received_at       (ISO datetime)
    I  category          (interested | not_interested | manual | demo_request | other)
    J  status            (new | pending_response | responded | ignored)
    K  response_action_id
    L  note              (LLM-generated summary of email intent/key points)
"""

import os
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_HEADER = [
    "id", "message_id", "from_email", "from_name",
    "people_id", "subject", "body_snippet", "received_at",
    "category", "status", "response_action_id", "note",
]

_gspread_client = None
_spreadsheet = None
_emails_ws = None


def _get_sheet():
    """Return the Emails worksheet, creating it (with header) if absent."""
    global _gspread_client, _spreadsheet, _emails_ws
    if _emails_ws is not None:
        return _emails_ws
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    if _gspread_client is None:
        creds = Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
        _gspread_client = gspread.authorize(creds)
    if _spreadsheet is None:
        _spreadsheet = _gspread_client.open_by_key(sheet_id)
    try:
        _emails_ws = _spreadsheet.worksheet("Emails")
    except gspread.WorksheetNotFound:
        _emails_ws = _spreadsheet.add_worksheet(title="Emails", rows=1000, cols=len(_HEADER))
        _emails_ws.append_row(_HEADER, value_input_option="RAW")
    return _emails_ws


# ---------------------------------------------------------------------------
# Row ↔ dict conversion
# ---------------------------------------------------------------------------

def _row_to_dict(row: list) -> dict:
    def _c(col: int) -> str:
        return row[col].strip() if col < len(row) else ""

    return {
        "id": _c(0),
        "message_id": _c(1),
        "from_email": _c(2),
        "from_name": _c(3) or None,
        "people_id": _c(4) or None,
        "subject": _c(5),
        "body_snippet": _c(6),
        "received_at": _c(7) or None,
        "category": _c(8),
        "status": _c(9),
        "response_action_id": _c(10) or None,
        "note": _c(11) or None,
    }


def _dict_to_row(email: dict) -> list:
    return [
        email.get("id", ""),
        email.get("message_id", ""),
        email.get("from_email", ""),
        email.get("from_name", "") or "",
        email.get("people_id", "") or "",
        email.get("subject", ""),
        email.get("body_snippet", ""),
        email.get("received_at", "") or "",
        email.get("category", "other"),
        email.get("status", "new"),
        email.get("response_action_id", "") or "",
        email.get("note", "") or "",
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_existing_message_ids() -> set:
    """Return the set of Gmail message_ids already recorded in the Emails sheet."""
    sheet = _get_sheet()
    rows = sheet.get_all_values()
    ids = set()
    for row in rows[1:]:  # skip header
        if len(row) > 1 and row[1].strip():
            ids.add(row[1].strip())
    return ids


def get_emails(status_filter: Optional[str] = None) -> list:
    """Return all email dicts, optionally filtered by status."""
    sheet = _get_sheet()
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        return []
    result = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        email = _row_to_dict(row)
        if status_filter is None or email["status"] == status_filter:
            result.append(email)
    return result


def get_emails_needing_response() -> list:
    """Return emails with category=manual that still need a human response."""
    sheet = _get_sheet()
    rows = sheet.get_all_values()
    if not rows or len(rows) < 2:
        return []
    result = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        email = _row_to_dict(row)
        if email["category"] == "manual" and email["status"] in ("new", "pending_response"):
            result.append(email)
    return result


def get_email_by_id(email_id: str) -> Optional[dict]:
    """Return a single email dict by its id field, or None."""
    for email in get_emails():
        if email["id"] == email_id:
            return email
    return None


def append_email(email: dict) -> None:
    """Append a single email row to the sheet."""
    sheet = _get_sheet()
    sheet.append_row(_dict_to_row(email), value_input_option="RAW")


def update_email_status(
    email_id: str,
    status: str,
    response_action_id: Optional[str] = None,
) -> None:
    """Find the row by email_id and update its status (and optionally response_action_id)."""
    sheet = _get_sheet()
    rows = sheet.get_all_values()
    for i, row in enumerate(rows):
        if i == 0 or not row:
            continue
        if row[0].strip() == email_id:
            row_num = i + 1  # 1-based
            cells = [gspread.Cell(row_num, 10, status)]  # col J = status (1-based col 10)
            if response_action_id is not None:
                cells.append(gspread.Cell(row_num, 11, response_action_id))  # col K
            sheet.update_cells(cells)
            return
