"""
Tool 4 – Send Follow-Up Emails

Sends a follow-up email to People who are mid-pipeline (stage is "contacted",
"demo_completed", or "pricing") and whose last_contact_date is older than the
configured followup_days threshold.

After a successful send the tool writes back to Supabase:
    last_contact      <- "email"
    last_contact_date <- today (ISO datetime)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.exceptions import GmailAPIError
from agent.results import EmailResult
from schemas.crm import CRMContext, PersonWithCompany, Stage
from tools.tool import BaseTool

# Stages that warrant a follow-up nudge
_FOLLOWUP_STAGES = {
    Stage.CONTACTED,
    Stage.DEMO_COMPLETED,
    Stage.PRICING,
    "contacted",
    "demo_completed",
    "pricing",
}

_TEMPLATE = Path(__file__).parent.parent.parent / "business" / "templates" / "followup_email.html"


def _build_followup_email(
    pwc: PersonWithCompany,
    sender_name: str,
    company_name: str,
) -> tuple[str, str]:
    subject = f"Following up – {company_name}"
    html_body = _TEMPLATE.read_text(encoding="utf-8").format(
        name=pwc.name,
        sender_name=sender_name,
        our_company=company_name,
        company_name=pwc.company_name,
    )
    return subject, html_body


class ScheduleFollowUpTool(BaseTool):
    """
    Sends follow-up emails to mid-pipeline contacts who have gone quiet.

    Filtering criteria:
        stage in ("contacted", "demo_completed", "pricing")
        AND (last_contact_date is null  OR  last_contact_date < today - followup_days)

    Supabase updates on success:
        last_contact      <- "email"
        last_contact_date <- today
    """

    tool_name = "schedule_followup"

    def execute(self, crm: CRMContext) -> list[EmailResult]:
        results: list[EmailResult] = []

        cutoff = datetime.now() - timedelta(days=self.config.followup_days)
        to_followup = [
            pwc for pwc in crm.people_with_company
            if pwc.stage in _FOLLOWUP_STAGES
            and pwc.email
            and (
                pwc.person.last_contact_date is None
                or pwc.person.last_contact_date < cutoff
            )
        ]

        self.tracer.log_tool_start(
            self.tool_name,
            {"contacts_to_follow_up": len(to_followup)},
        )

        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        for pwc in to_followup:
            subject, html_body = _build_followup_email(
                pwc, self.config.sender_name, self.config.company_name
            )

            if self.config.dry_run:
                self.tracer.log_email_skipped(pwc.email, "dry_run=True")
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    body=html_body,
                    email_type="followup_email",
                    sent_at=datetime.now(timezone.utc),
                    success=True,
                    error="dry_run – not sent",
                    person_id=pwc.person.id,
                ))
                continue

            try:
                resp = self.api.send_email(
                    sender=self._sender_address(),
                    to=pwc.email,
                    subject=subject,
                    html_body=html_body,
                )
                # Write back to Supabase
                self.api.update_person(pwc.person.id, {
                    "last_contact": "email",
                    "last_contact_date": today_str,
                })

                self.tracer.log_email_sent(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    message_id=resp.get("id", ""),
                    email_type="followup_email",
                )
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    message_id=resp.get("id"),
                    email_type="followup_email",
                    sent_at=datetime.now(timezone.utc),
                    success=True,
                ))

            except Exception as exc:
                self.tracer.log_error(exc, {"contact": pwc.email})
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    email_type="followup_email",
                    sent_at=datetime.now(timezone.utc),
                    success=False,
                    error=str(exc),
                ))

        self.tracer.log_tool_end(
            self.tool_name,
            success=True,
            result_summary=f"{sum(1 for r in results if r.success)}/{len(to_followup)} sent",
        )
        return results
