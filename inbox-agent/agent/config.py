"""Configuration model for the inbox-agent."""

from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel


class InboxAgentConfig(BaseModel):
    """All runtime settings for an inbox-agent run."""

    # Google Sheets
    spreadsheet_id: str

    # OAuth (inbox-agent uses its own token file with gmail.modify scope)
    credentials_file: str
    token_file: str

    # Email identity
    sender_email: str
    sender_name: str
    company_name: str = "Fellowship"

    # Behaviour
    dry_run: bool = False      # If True, don't send emails or write to Sheets
    max_emails: int = 50       # Max unread messages to fetch per run

    @classmethod
    def from_env(cls) -> "InboxAgentConfig":
        """Build config from environment variables."""
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        _INBOX_DIR = os.path.dirname(_THIS_DIR)
        return cls(
            spreadsheet_id=os.environ["GOOGLE_SHEET_ID"],
            credentials_file=os.getenv(
                "INBOX_CREDENTIALS_FILE",
                # Fall back to outreach-agent's OAuth credentials (installed app type)
                os.path.join(_INBOX_DIR, "..", "outreach-agent", "credentials.json"),
            ),
            token_file=os.getenv(
                "INBOX_TOKEN_FILE",
                os.path.join(_INBOX_DIR, "inbox-token.pickle"),
            ),
            sender_email=os.environ["SENDER_EMAIL"],
            sender_name=os.environ["SENDER_NAME"],
            company_name=os.getenv("COMPANY_NAME", "Fellowship"),
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
            max_emails=int(os.getenv("INBOX_MAX_EMAILS", "50")),
        )
