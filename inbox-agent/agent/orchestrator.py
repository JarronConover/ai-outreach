"""
InboxOrchestrator — core logic for the inbox-agent.

Run flow:
1. Load People sheet → build email-address → Person lookup dict.
2. Load already-processed Gmail message IDs from the Emails sheet (dedup).
3. Fetch unread Gmail messages.
4. For each new message:
   a. Match sender to a Person record.
   b. Unknown senders → category = "manual" (no LLM call, no action).
   c. Known senders → categorise with Gemini.
   d. Append a row to the Emails sheet.
   e. For actionable categories (interested / not_interested / demo_request):
      - Generate a personalised reply body with Gemini + template.
      - Write a pending Action to the Actions sheet.
      - Update Emails row: status = pending_response, response_action_id = <action.id>.
   f. Mark the Gmail message as read.
5. Return InboxRunResult.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Locate project root. Add inbox-agent dir to sys.path so that
# `agent.*` and `tools.*` imports resolve here, not in prospect-agent.
# We load prospect-agent's actions_sheet via importlib by absolute path
# to avoid shadowing inbox-agent/tools/.
# ---------------------------------------------------------------------------
import importlib.util as _ilu

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_INBOX_AGENT_DIR = os.path.dirname(_THIS_DIR)
_PROJECT_ROOT = os.path.dirname(_INBOX_AGENT_DIR)
_PROSPECT_AGENT_DIR = os.path.join(_PROJECT_ROOT, "prospect-agent")

# inbox-agent must be at the front so its tools/ is found before prospect-agent's
if _INBOX_AGENT_DIR not in sys.path:
    sys.path.insert(0, _INBOX_AGENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from agent.config import InboxAgentConfig
from agent.results import InboxEmailResult, InboxRunResult
from tools.tool import InboxAPIClient
from tools.email_categorizer import EmailCategorizer, INTERESTED, NOT_INTERESTED, DEMO_REQUEST, MANUAL
from tools.emails_sheet import (
    get_existing_message_ids,
    append_email,
    update_email_status,
)

# Load write_actions from prospect-agent by absolute path (avoids tools/ namespace conflict)
_pa_actions_spec = _ilu.spec_from_file_location(
    "_inbox_pa_actions",
    os.path.join(_PROSPECT_AGENT_DIR, "tools", "actions_sheet.py"),
)
_pa_actions_mod = _ilu.module_from_spec(_pa_actions_spec)
_pa_actions_spec.loader.exec_module(_pa_actions_mod)
write_actions = _pa_actions_mod.write_actions

# ---------------------------------------------------------------------------
# People sheet helper — minimal gspread read for email→id lookup
# ---------------------------------------------------------------------------


def _load_people_lookup() -> dict[str, dict]:
    """Return a dict keyed by email address → {id, name, people_id}."""
    import gspread
    from google.oauth2.service_account import Credentials

    _SCOPES = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    creds = Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet("People")
    rows = ws.get_all_values()

    # PeopleColumns: ID=0, NAME=1, EMAIL=3
    lookup: dict[str, dict] = {}
    for row in rows[1:]:  # skip header
        if len(row) < 4:
            continue
        pid = row[0].strip()
        name = row[1].strip()
        email = row[3].strip().lower()
        if email:
            lookup[email] = {"id": pid, "name": name, "email": email}
    return lookup


# ---------------------------------------------------------------------------
# Email type mapping
# ---------------------------------------------------------------------------
_CATEGORY_TO_EMAIL_TYPE = {
    INTERESTED:     "inbox_reply_interested",
    NOT_INTERESTED: "inbox_reply_not_interested",
    DEMO_REQUEST:   "inbox_reply_demo_request",
}


class InboxOrchestrator:
    """Coordinates the full inbox scan for one run."""

    def __init__(self, config: InboxAgentConfig) -> None:
        self.config = config
        self.api = InboxAPIClient(
            credentials_file=config.credentials_file,
            token_file=config.token_file,
        )
        self.categorizer = EmailCategorizer()

    def run(self) -> InboxRunResult:
        result = InboxRunResult(run_at=datetime.utcnow(), dry_run=self.config.dry_run)

        # 1. Build People email lookup
        try:
            people_lookup = _load_people_lookup()
        except Exception as exc:
            result.errors.append(f"Failed to load People sheet: {exc}")
            return result

        # 2. Load already-processed message IDs
        try:
            seen_message_ids = get_existing_message_ids()
        except Exception as exc:
            result.errors.append(f"Failed to load Emails sheet: {exc}")
            return result

        # 3. Fetch unread messages
        try:
            stubs = self.api.list_unread(max_results=self.config.max_emails)
        except Exception as exc:
            result.errors.append(f"Failed to list unread Gmail messages: {exc}")
            return result

        # 4. Process each message
        for stub in stubs:
            message_id = stub.get("id", "")
            email_result = self._process_message(
                message_id=message_id,
                seen_message_ids=seen_message_ids,
                people_lookup=people_lookup,
            )
            result.emails_processed.append(email_result)
            if email_result.action_id:
                result.actions_created += 1
            if email_result.error:
                result.errors.append(
                    f"[{message_id}] {email_result.error}"
                )

        print(
            f"[inbox] run complete — {result.total} messages, "
            f"{result.actions_created} actions created, "
            f"{result.manual_count} manual, "
            f"{result.skipped} skipped",
            flush=True,
        )
        return result

    def _process_message(
        self,
        message_id: str,
        seen_message_ids: set,
        people_lookup: dict,
    ) -> InboxEmailResult:
        # Deduplication
        if message_id in seen_message_ids:
            return InboxEmailResult(
                message_id=message_id,
                from_email="",
                skipped=True,
            )

        # Fetch full message
        try:
            msg = self.api.get_message(message_id)
        except Exception as exc:
            return InboxEmailResult(
                message_id=message_id,
                from_email="",
                error=str(exc),
            )

        from_email = msg["from_email"]
        from_name = msg["from_name"]
        subject = msg["subject"]
        body_snippet = msg["body_snippet"]
        received_at = msg["received_at"]

        # Match sender to People sheet
        person = people_lookup.get(from_email)
        people_id = person["id"] if person else None
        display_name = (from_name or (person["name"] if person else from_email))

        # Categorise (unknown senders always → manual, no LLM call)
        note: Optional[str] = None
        if person is None:
            category = MANUAL
        else:
            try:
                category = self.categorizer.categorize(
                    subject=subject,
                    from_email=from_email,
                    from_name=display_name,
                    body_snippet=body_snippet,
                )
            except Exception as exc:
                category = MANUAL
                print(f"[inbox] categorization failed for {message_id}: {exc}")

            # Generate note for known senders (non-blocking)
            try:
                note = self.categorizer.generate_note(
                    subject=subject,
                    from_name=display_name,
                    from_email=from_email,
                    body_snippet=body_snippet,
                )
            except Exception as exc:
                print(f"[inbox] note generation failed for {message_id}: {exc}")

        # Build Emails sheet record
        email_record_id = str(uuid.uuid4())
        email_dict = {
            "id": email_record_id,
            "message_id": message_id,
            "from_email": from_email,
            "from_name": display_name,
            "people_id": people_id or "",
            "subject": subject,
            "body_snippet": body_snippet,
            "received_at": received_at.isoformat() if received_at else "",
            "category": category,
            "status": "new",
            "response_action_id": "",
            "note": note or "",
        }

        action_id: Optional[str] = None

        # Generate action for actionable categories (known sender only)
        if category in _CATEGORY_TO_EMAIL_TYPE and person is not None:
            action_id = self._create_reply_action(
                email_record_id=email_record_id,
                category=category,
                recipient_email=from_email,
                recipient_name=display_name,
                people_id=people_id,
                subject=subject,
                body_snippet=body_snippet,
            )
            if action_id:
                email_dict["status"] = "pending_response"
                email_dict["response_action_id"] = action_id

        # Write to Emails sheet
        if not self.config.dry_run:
            try:
                append_email(email_dict)
                if action_id:
                    update_email_status(email_record_id, "pending_response", action_id)
            except Exception as exc:
                return InboxEmailResult(
                    message_id=message_id,
                    from_email=from_email,
                    from_name=display_name,
                    subject=subject,
                    people_id=people_id,
                    category=category,
                    error=f"Emails sheet write failed: {exc}",
                )

            # Mark Gmail message as read
            try:
                self.api.mark_as_read(message_id)
            except Exception as exc:
                print(f"[inbox] could not mark {message_id} as read: {exc}")
        else:
            print(
                f"[inbox][dry-run] would process: {from_email!r} | category={category} | action={action_id or 'none'}",
                flush=True,
            )

        return InboxEmailResult(
            message_id=message_id,
            from_email=from_email,
            from_name=display_name,
            subject=subject,
            people_id=people_id,
            category=category,
            action_id=action_id,
        )

    def _create_reply_action(
        self,
        email_record_id: str,
        category: str,
        recipient_email: str,
        recipient_name: str,
        people_id: Optional[str],
        subject: str,
        body_snippet: str,
    ) -> Optional[str]:
        """Generate a personalised reply body and write a pending Action. Returns action_id."""
        email_type = _CATEGORY_TO_EMAIL_TYPE[category]

        try:
            body_html = self.categorizer.generate_reply(
                category=category,
                recipient_name=recipient_name,
                from_email=recipient_email,
                original_subject=subject,
                body_snippet=body_snippet,
                sender_name=self.config.sender_name,
                our_company=self.config.company_name,
            )
        except Exception as exc:
            print(f"[inbox] reply generation failed: {exc}")
            body_html = None

        action_id = str(uuid.uuid4())
        action = {
            "id": action_id,
            "kind": "email",
            "email_type": email_type,
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "subject": f"Re: {subject}",
            "people_id": people_id or "",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "source_email_id": email_record_id,
            "body": body_html or "",
        }

        if not self.config.dry_run:
            try:
                write_actions([action])
            except Exception as exc:
                print(f"[inbox] failed to write action: {exc}")
                return None

        return action_id
