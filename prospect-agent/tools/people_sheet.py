import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Optional

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_PEOPLE_HEADER_ROW = [
    "id",
    "name",
    "company_id",
    "email",
    "linkedin",
    "phone",
    "title",
    "stage",
    "last_response",
    "last_contact",
    "created_at",
    "updated_at",
]


def _get_people_worksheet():
    """Get or create the People worksheet in Google Sheets."""
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    creds = Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    try:
        worksheet = sheet.worksheet("People")
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title="People", rows=1000, cols=20)
        worksheet.append_row(_PEOPLE_HEADER_ROW)
    return worksheet


def append_person(person_dict: dict) -> str:
    """Append a single person record to the People sheet."""
    try:
        worksheet = _get_people_worksheet()
        row = [
            person_dict.get("id", ""),
            person_dict.get("name", ""),
            person_dict.get("company_id", ""),
            person_dict.get("email", ""),
            person_dict.get("linkedin", ""),
            person_dict.get("phone", ""),
            person_dict.get("title", ""),
            person_dict.get("stage", "PROSPECTING"),
            person_dict.get("last_response", ""),
            person_dict.get("last_contact", ""),
            person_dict.get("created_at", datetime.utcnow().isoformat()),
            person_dict.get("updated_at", datetime.utcnow().isoformat()),
        ]
        worksheet.append_row(row)
        return f"Success: added person {person_dict.get('name', 'Unknown')}"
    except Exception as e:
        raise Exception(f"Failed to append person to Sheets: {e}") from e


def append_people(people_list: List[dict]) -> str:
    """Append multiple person records to the People sheet."""
    try:
        worksheet = _get_people_worksheet()
        for person in people_list:
            row = [
                person.get("id", ""),
                person.get("name", ""),
                person.get("company_id", ""),
                person.get("email", ""),
                person.get("linkedin", ""),
                person.get("phone", ""),
                person.get("title", ""),
                person.get("stage", "PROSPECTING"),
                person.get("last_response", ""),
                person.get("last_contact", ""),
                person.get("created_at", datetime.utcnow().isoformat()),
                person.get("updated_at", datetime.utcnow().isoformat()),
            ]
            worksheet.append_row(row)
        return f"Success: added {len(people_list)} people to Google Sheets."
    except Exception as e:
        raise Exception(f"Failed to append people to Sheets: {e}") from e
