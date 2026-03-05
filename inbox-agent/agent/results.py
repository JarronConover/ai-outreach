"""Result models for the inbox-agent run."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InboxEmailResult(BaseModel):
    """Outcome for a single email processed during an inbox scan."""
    message_id: str
    from_email: str
    from_name: Optional[str] = None
    subject: str = ""
    people_id: Optional[str] = None   # set if sender matched a Person record
    category: str = "other"
    action_id: Optional[str] = None   # set if a pending Action was created
    skipped: bool = False             # True if message_id was already in the Emails sheet
    error: Optional[str] = None


class InboxRunResult(BaseModel):
    """Aggregated outcome of a complete inbox scan."""
    run_at: datetime
    dry_run: bool = False
    emails_processed: list[InboxEmailResult] = []
    actions_created: int = 0
    errors: list[str] = []

    @property
    def total(self) -> int:
        return len(self.emails_processed)

    @property
    def skipped(self) -> int:
        return sum(1 for e in self.emails_processed if e.skipped)

    @property
    def manual_count(self) -> int:
        return sum(1 for e in self.emails_processed if e.category == "manual")
