"""
InboxOrchestrator — core logic for the inbox-agent.

Run flow:
1. Load People from Supabase -> build email-address -> Person lookup dict.
2. Load already-processed Gmail message IDs from Supabase emails table (dedup).
3. Fetch unread Gmail messages.
4. For each new message:
   a. Match sender to a Person record.
   b. Unknown senders -> category = "manual" (no LLM call, no action).
   c. Known senders -> categorise with Gemini.
   d. Insert a row into the Supabase emails table.
   e. For actionable categories (interested / not_interested / demo_request):
      - Generate a personalised reply body with Gemini + template.
      - Write a pending Action to Supabase.
      - Update emails row: status = pending_response, response_action_id = <action.id>.
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
# `agent.*` and `tools.*` imports resolve here.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_INBOX_AGENT_DIR = os.path.dirname(_THIS_DIR)
_PROJECT_ROOT = os.path.dirname(_INBOX_AGENT_DIR)

# inbox-agent must be at the front so its tools/ is found first
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

# Use Supabase-backed write_actions (via api.supabase_crud)
from api.supabase_crud import write_actions  # noqa: E402

# ---------------------------------------------------------------------------
# People lookup from Supabase
# ---------------------------------------------------------------------------


def _load_people_lookup() -> dict:
    """Return a dict keyed by lowercase email address -> {id, name, email}."""
    from api.db import get_db
    db = get_db()
    res = db.table("people").select("id, name, email").execute()
    return {
        row["email"].lower(): {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"].lower(),
        }
        for row in res.data
        if row.get("email")
    }


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

        # 1. Build People email lookup from Supabase
        try:
            people_lookup = _load_people_lookup()
        except Exception as exc:
            result.errors.append(f"Failed to load People from Supabase: {exc}")
            return result

        # 2. Load already-processed message IDs from Supabase
        try:
            seen_message_ids = get_existing_message_ids()
        except Exception as exc:
            result.errors.append(f"Failed to load existing message IDs: {exc}")
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

        # Match sender to People table
        person = people_lookup.get(from_email.lower() if from_email else "")
        people_id = person["id"] if person else None
        display_name = (from_name or (person["name"] if person else from_email))

        # Categorise (unknown senders always -> manual, no LLM call)
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

        # Build email record
        email_record_id = str(uuid.uuid4())
        email_dict = {
            "id": email_record_id,
            "message_id": message_id,
            "from_email": from_email,
            "from_name": display_name,
            "people_id": people_id,
            "subject": subject,
            "body_snippet": body_snippet,
            "received_at": received_at.isoformat() if received_at else None,
            "category": category,
            "status": "new",
            "response_action_id": None,
            "note": note,
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

        # Write to Supabase
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
                    error=f"Supabase write failed: {exc}",
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
            "people_id": people_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "source_email_id": email_record_id,
            "body": body_html,
        }

        if not self.config.dry_run:
            try:
                write_actions([action])
            except Exception as exc:
                print(f"[inbox] failed to write action: {exc}")
                return None

        return action_id
