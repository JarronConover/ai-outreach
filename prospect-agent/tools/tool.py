import os
import gspread
from google.oauth2.service_account import Credentials
from schemas.output import LeadsOutput
from agent.exceptions import SheetsWriteError

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
_HEADER_ROW = ["id", "name", "company", "email", "title", "stage", "last_message", "next_action"]


def _get_worksheet():
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    creds = Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    try:
        worksheet = sheet.worksheet("Leads")
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title="Leads", rows=1000, cols=20)
        worksheet.append_row(_HEADER_ROW)
    return worksheet


def write_leads_to_sheet(leads_output: LeadsOutput) -> str:
    """Write validated leads to the Google Sheet. Returns a status string."""
    try:
        worksheet = _get_worksheet()
        for lead in leads_output.leads:
            row = [
                lead.id, lead.name, lead.company, lead.email,
                lead.title, lead.stage, lead.last_message, lead.next_action,
            ]
            worksheet.append_row(row)
        return f"Success: wrote {len(leads_output.leads)} leads to Google Sheets."
    except Exception as e:
        raise SheetsWriteError(f"Failed to write to Sheets: {e}") from e
