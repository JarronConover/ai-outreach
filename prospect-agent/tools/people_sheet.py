import os
import uuid
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Optional

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Matches schemas/sheet_config.py PeopleColumns exactly (0-based)
# A  id
# B  name
# C  company_id
# D  email
# E  phone
# F  linkedin
# G  title
# H  stage
# I  last_demo_id
# J  next_demo_id
# K  last_response
# L  last_contact
# M  last_response_date
# N  last_contact_date
_PEOPLE_HEADER_ROW = [
    "id", "name", "company_id", "email",
    "phone", "linkedin", "title", "stage",
    "last_demo_id", "next_demo_id",
    "last_response", "last_contact",
    "last_response_date", "last_contact_date",
]

# Matches schemas/sheet_config.py CompanyColumns exactly (0-based)
_COMPANIES_HEADER_ROW = [
    "id", "name", "address", "city", "state", "zip",
    "phone", "website", "industry", "employee_count",
]


def _get_client():
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    creds = Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    return sheet


def _get_worksheet(sheet, title: str, rows: int = 1000, header: list = None):
    try:
        return sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=rows, cols=len(header or []) + 5)
        if header:
            ws.append_row(header)
        return ws


def get_company_names() -> dict:
    """Fetch all companies from the Companies sheet.

    Returns a dict keyed by company id mapping to company name.
    """
    try:
        sheet = _get_client()
        ws = _get_worksheet(sheet, "Companies", header=_COMPANIES_HEADER_ROW)
        all_rows = ws.get_all_values()
        if not all_rows or len(all_rows) < 2:
            return {}
        return {
            row[0].strip(): row[1].strip()
            for row in all_rows[1:]
            if len(row) > 1 and row[0].strip()
        }
    except Exception as e:
        raise Exception(f"Failed to fetch companies: {e}") from e


def get_people_dicts() -> list[dict]:
    """Fetch all people from the People sheet as a list of dicts.

    Reads the actual header row from the sheet so column order doesn't matter.
    """
    try:
        sheet = _get_client()
        ws = _get_worksheet(sheet, "People", header=_PEOPLE_HEADER_ROW)
        all_rows = ws.get_all_values()
        if not all_rows or len(all_rows) < 2:
            return []
        header = [h.strip() for h in all_rows[0]]
        result = []
        for row in all_rows[1:]:
            if len(row) > 3 and row[3].strip():
                result.append({header[i]: (row[i] if i < len(row) else "") for i in range(len(header))})
        return result
    except Exception as e:
        raise Exception(f"Failed to fetch people: {e}") from e


def get_existing_people() -> dict:
    """Fetch all existing people from the People sheet.

    Returns a dict keyed by email (lowercase) for fast duplicate checking.
    Values are the raw row lists.
    """
    try:
        sheet = _get_client()
        ws = _get_worksheet(sheet, "People", header=_PEOPLE_HEADER_ROW)
        all_rows = ws.get_all_values()

        if not all_rows or len(all_rows) < 2:
            return {}

        existing = {}
        for row in all_rows[1:]:
            email = row[3].strip().lower() if len(row) > 3 and row[3] else ""
            if email:
                existing[email] = row
        return existing
    except Exception as e:
        raise Exception(f"Failed to fetch existing people: {e}") from e


def filter_duplicates(new_people: List[dict]) -> tuple[List[dict], List[str]]:
    """Filter out people whose email already exists in the sheet."""
    existing = get_existing_people()
    filtered, duplicates = [], []
    for person in new_people:
        email = person.get("email", "").strip().lower()
        if email and email in existing:
            duplicates.append(email)
        else:
            filtered.append(person)
    return filtered, duplicates


def _person_row(person: dict) -> list:
    """Build a 14-column People row from a person dict."""
    def _dt(val) -> str:
        if val is None:
            return ""
        return val.isoformat() if hasattr(val, "isoformat") else str(val)

    return [
        person.get("id", ""),
        person.get("name", ""),
        person.get("company_id", ""),
        person.get("email", ""),
        person.get("phone", ""),              # E — phone (prospect agent won't have this)
        person.get("linkedin", ""),           # F — linkedin
        person.get("title", ""),
        person.get("stage", "prospect"),
        person.get("last_demo_id", ""),
        person.get("next_demo_id", ""),
        person.get("last_response", ""),      # K — last_response type string
        person.get("last_contact", ""),       # L — last_contact type string
        _dt(person.get("last_response_date")),  # M
        _dt(person.get("last_contact_date")),   # N
    ]


def append_person(person_dict: dict) -> str:
    """Append a single person record to the People sheet."""
    try:
        sheet = _get_client()
        ws = _get_worksheet(sheet, "People", header=_PEOPLE_HEADER_ROW)
        ws.append_row(_person_row(person_dict))
        return f"Success: added person {person_dict.get('name', 'Unknown')}"
    except Exception as e:
        raise Exception(f"Failed to append person to Sheets: {e}") from e


def append_people(people_list: List[dict], industry: Optional[str] = None) -> str:
    """Append multiple person records to the People sheet.

    Also upserts a Company row for each unique company_id so the outreach
    agent can look up company details by id.
    """
    try:
        sheet = _get_client()
        people_ws = _get_worksheet(sheet, "People", header=_PEOPLE_HEADER_ROW)
        companies_ws = _get_worksheet(sheet, "Companies", header=_COMPANIES_HEADER_ROW)

        # Load existing company IDs to avoid duplicates
        existing_company_rows = companies_ws.get_all_values()
        existing_company_ids = {
            row[0].strip()
            for row in existing_company_rows[1:]
            if row and row[0].strip()
        }

        seen_companies = set()
        for person in people_list:
            people_ws.append_row(_person_row(person))

            company_id = person.get("company_id", "").strip()
            if company_id and company_id not in existing_company_ids and company_id not in seen_companies:
                seen_companies.add(company_id)
                companies_ws.append_row([
                    company_id,   # id  (same as the name for prospect-generated companies)
                    company_id,   # name
                    "", "", "", "", "", "",  # address, city, state, zip, phone, website
                    industry or "",         # industry (passed through from ICP)
                    "",                     # employee_count
                ])

        return f"Success: added {len(people_list)} people to Google Sheets."
    except Exception as e:
        raise Exception(f"Failed to append people to Sheets: {e}") from e
