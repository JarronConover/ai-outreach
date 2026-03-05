"""
Gmail reader and base API client for the inbox-agent.

Uses OAuth with gmail.modify scope (read + modify labels) plus spreadsheets.
Token is stored in inbox-token.pickle — separate from the outreach-agent token.
"""

from __future__ import annotations

import base64
import os
import pickle
import re
from datetime import datetime, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for inbox reading + sheet writes.
# gmail.modify allows reading messages and removing the UNREAD label.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]


class InboxAPIClient:
    """
    Authenticated Google API client for the inbox-agent.

    Provides Gmail read/modify helpers and a Sheets helper for writing
    email records back to the Emails sheet.
    """

    def __init__(self, credentials_file: str, token_file: str) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self._creds: Optional[Credentials] = None
        self._gmail = None
        self._sheets = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> Credentials:
        creds: Optional[Credentials] = None

        if os.path.exists(self._token_file):
            with open(self._token_file, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self._credentials_file):
                    raise FileNotFoundError(
                        f"credentials file not found: {self._credentials_file}. "
                        "Download from Google Cloud Console → APIs & Services → Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self._token_file, "wb") as f:
                pickle.dump(creds, f)

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

    # ------------------------------------------------------------------
    # Gmail helpers
    # ------------------------------------------------------------------

    def list_unread(self, max_results: int = 50) -> list[dict]:
        """Return up to max_results unread message stubs from the inbox."""
        try:
            resp = (
                self.gmail.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=["INBOX", "UNREAD"],
                    maxResults=max_results,
                )
                .execute()
            )
            return resp.get("messages", [])
        except HttpError as exc:
            raise RuntimeError(f"Failed to list unread messages: {exc}") from exc

    def get_message(self, message_id: str) -> dict:
        """
        Fetch a full message and return a normalized dict:
            id, from_email, from_name, subject, body_snippet, received_at
        """
        try:
            msg = (
                self.gmail.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(f"Failed to fetch message {message_id}: {exc}") from exc

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

        from_raw = headers.get("from", "")
        from_name, from_email = _parse_from(from_raw)
        subject = headers.get("subject", "")
        date_raw = headers.get("date", "")
        received_at = _parse_email_date(date_raw) or datetime.now(timezone.utc)

        body_snippet = _extract_body(msg.get("payload", {}))[:500]

        return {
            "id": message_id,
            "from_email": from_email.lower().strip(),
            "from_name": from_name,
            "subject": subject,
            "body_snippet": body_snippet,
            "received_at": received_at,
        }

    def mark_as_read(self, message_id: str) -> None:
        """Remove the UNREAD label from a message."""
        try:
            self.gmail.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
        except HttpError as exc:
            raise RuntimeError(f"Failed to mark message {message_id} as read: {exc}") from exc


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------


def _parse_from(from_header: str) -> tuple[str, str]:
    """Parse 'Name <email>' or just 'email' into (name, email)."""
    m = re.match(r'^"?([^"<]*?)"?\s*<([^>]+)>', from_header)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", from_header.strip()


def _parse_email_date(date_str: str) -> Optional[datetime]:
    """Parse an RFC 2822 email date header into a naive UTC datetime."""
    if not date_str:
        return None
    try:
        import email.utils
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", html)
        return ""

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text.strip():
            return text

    return ""
