"""Read Demos from Google Sheets using a service account (same auth as people_sheet.py).

Returns demo rows enriched with person name/email and company name, ready for
the /demos API endpoint.  Does not require OAuth / outreach-agent credentials.
"""

import os
import gspread
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Column indices (0-based) matching sheet_config.DemoColumns
_COL_ID        = 0
_COL_PEOPLE_ID = 1
_COL_COMPANY_ID = 2
_COL_TYPE      = 3
_COL_DATE      = 4
_COL_STATUS    = 5
_COL_EVENT_ID  = 7

# Column indices (0-based) matching sheet_config.PeopleColumns
_PCOL_ID    = 0
_PCOL_NAME  = 1
_PCOL_EMAIL = 3

# Column indices (0-based) matching sheet_config.CompanyColumns
_CCOL_ID   = 0
_CCOL_NAME = 1


_gspread_client = None
_spreadsheet = None


def _get_spreadsheet():
    """Return the cached gspread Spreadsheet, creating the client once."""
    global _gspread_client, _spreadsheet
    if _spreadsheet is not None:
        return _spreadsheet
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    if _gspread_client is None:
        creds = Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
        _gspread_client = gspread.authorize(creds)
    _spreadsheet = _gspread_client.open_by_key(sheet_id)
    return _spreadsheet


def get_demos() -> list[dict]:
    """Return all demo rows enriched with person and company info."""
    spreadsheet = _get_spreadsheet()

    # Read all three relevant sheets in one pass
    try:
        people_rows = spreadsheet.worksheet("People").get_all_values()
    except gspread.WorksheetNotFound:
        people_rows = []

    try:
        companies_rows = spreadsheet.worksheet("Companies").get_all_values()
    except gspread.WorksheetNotFound:
        companies_rows = []

    try:
        demos_rows = spreadsheet.worksheet("Demos").get_all_values()
    except gspread.WorksheetNotFound:
        return []

    if not demos_rows or len(demos_rows) < 2:
        return []

    # Build lookup dicts (skip header row)
    def _cell(row, col):
        return row[col].strip() if col < len(row) else ""

    people_by_id = {}
    for row in people_rows[1:]:
        pid = _cell(row, _PCOL_ID)
        if pid:
            people_by_id[pid] = row

    companies_by_id = {}
    for row in companies_rows[1:]:
        cid = _cell(row, _CCOL_ID)
        if cid:
            companies_by_id[cid] = row

    demos = []
    for row in demos_rows[1:]:
        people_id = _cell(row, _COL_PEOPLE_ID)
        if not people_id:
            continue

        person_row = people_by_id.get(people_id, [])
        company_id = _cell(row, _COL_COMPANY_ID)
        company_row = companies_by_id.get(company_id, [])

        event_id_val = _cell(row, _COL_EVENT_ID) or None
        date_val = _cell(row, _COL_DATE) or None

        demos.append({
            "id": _cell(row, _COL_ID),
            "type": _cell(row, _COL_TYPE),
            "date": date_val,
            "status": _cell(row, _COL_STATUS),
            "event_id": event_id_val,
            "person_name": _cell(person_row, _PCOL_NAME) if person_row else "Unknown",
            "person_email": _cell(person_row, _PCOL_EMAIL) if person_row else None,
            "company_name": _cell(company_row, _CCOL_NAME) if company_row else "Unknown",
        })

    return demos
