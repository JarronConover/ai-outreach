"""Tracer for logging and tracking outreach agent actions."""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Optional


def _configure_root_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class OutreachTracer:
    """
    Structured tracer that records every meaningful action the outreach agent
    takes.  Each event is emitted via Python's logging module *and* appended
    to an in-memory history list so the orchestrator can inspect the full run
    at the end and build a summary.
    """

    def __init__(self, agent_name: str = "outreach-agent") -> None:
        _configure_root_logger()
        self.logger = logging.getLogger(agent_name)
        self.history: list[dict] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record(self, event_type: str, data: dict) -> None:
        entry = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.history.append(entry)
        self.logger.info("%s | %s", event_type, json.dumps(data, default=str))

    # ------------------------------------------------------------------
    # Public tracing methods
    # ------------------------------------------------------------------

    def log_run_start(self, config: dict) -> None:
        self._record("RUN_START", {"config": config})

    def log_run_end(self, summary: dict) -> None:
        self._record("RUN_END", {"summary": summary})

    def log_db_read(self, source: str, table_name: str, row_count: int) -> None:
        self._record(
            "DB_READ",
            {
                "source": source,
                "table_name": table_name,
                "row_count": row_count,
            },
        )

    def log_email_sent(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        message_id: str,
        email_type: str,
    ) -> None:
        self._record(
            "EMAIL_SENT",
            {
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "subject": subject,
                "message_id": message_id,
                "email_type": email_type,
            },
        )

    def log_email_skipped(self, recipient_email: str, reason: str) -> None:
        self._record(
            "EMAIL_SKIPPED",
            {"recipient_email": recipient_email, "reason": reason},
        )

    def log_calendar_event_created(
        self,
        event_id: str,
        event_title: str,
        attendees: list[str],
        start_time: str,
        end_time: str,
        event_type: str,
    ) -> None:
        self._record(
            "CALENDAR_EVENT_CREATED",
            {
                "event_id": event_id,
                "event_title": event_title,
                "attendees": attendees,
                "start_time": start_time,
                "end_time": end_time,
                "event_type": event_type,
            },
        )

    def log_calendar_event_skipped(self, contact_email: str, reason: str) -> None:
        self._record(
            "CALENDAR_EVENT_SKIPPED",
            {"contact_email": contact_email, "reason": reason},
        )

    def log_tool_start(self, tool_name: str, inputs: dict) -> None:
        self._record("TOOL_START", {"tool": tool_name, "inputs": inputs})

    def log_tool_end(self, tool_name: str, success: bool, result_summary: Optional[str] = None) -> None:
        self._record(
            "TOOL_END",
            {"tool": tool_name, "success": success, "result_summary": result_summary},
        )

    def log_error(self, error: Exception, context: Optional[dict] = None) -> None:
        self._record(
            "ERROR",
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            },
        )
        self.logger.exception("Error in outreach agent: %s", error)

    def log_content_generated(self, recipient_email: str, content_type: str) -> None:
        self._record(
            "CONTENT_GENERATED",
            {"recipient_email": recipient_email, "content_type": content_type},
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> dict:
        """Return a high-level count summary of the current run."""
        counts: dict[str, int] = {}
        for entry in self.history:
            event_type = entry["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1

        return {
            "total_events": len(self.history),
            "counts_by_type": counts,
            "emails_sent": counts.get("EMAIL_SENT", 0),
            "emails_skipped": counts.get("EMAIL_SKIPPED", 0),
            "calendar_events_created": counts.get("CALENDAR_EVENT_CREATED", 0),
            "errors": counts.get("ERROR", 0),
        }

    def dump_history(self) -> str:
        """Return the full trace history as a JSON string."""
        return json.dumps(self.history, indent=2, default=str)
