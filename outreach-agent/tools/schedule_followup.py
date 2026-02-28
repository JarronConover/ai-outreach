"""
Tool 4 – Send Follow-Up Emails

Sends a follow-up email to People who are mid-pipeline (stage is "contacted",
"demo_completed", or "pricing") and whose last_contact_date is older than the
configured followup_days threshold.

This tool sends email-only follow-ups (no calendar event) to re-engage contacts
who have gone quiet.  If a formal meeting needs scheduling, add a row to the
Demos sheet with status="scheduled" and a date — ScheduleDemoTool will handle
the calendar event.

After a successful send the tool writes back to the People sheet:
    last_contact      ← "email"
    last_contact_date ← today (YYYY-MM-DD)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.exceptions import GmailAPIError, SheetUpdateError
from agent.results import EmailResult
from schemas.crm import CRMContext, PersonWithCompany, Stage
from schemas.sheet_config import PeopleColumns, SheetNames
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


def _build_followup_email(
    pwc: PersonWithCompany,
    sender_name: str,
    company_name: str,
) -> tuple[str, str]:
    subject = f"Following up – {company_name}"
    html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <p>Hi {pwc.name},</p>

    <p>
      I wanted to follow up on my last message and see if you'd had a chance
      to think things over. I know you're busy at <strong>{pwc.company_name}</strong>,
      so I'll keep this short.
    </p>

    <p>
      Is now still a good time to explore how we can help? If you have any
      questions or want to set up a quick call, just reply and we'll make it
      happen.
    </p>

    <p>
      If the timing isn't right, no worries at all – just let me know and
      I'll circle back later.
    </p>

    <p>
      Thanks,<br/>
      <strong>{sender_name}</strong><br/>
      {company_name}
    </p>
  </body>
</html>
"""
    return subject, html_body


class ScheduleFollowUpTool(BaseTool):
    """
    Sends follow-up emails to mid-pipeline contacts who have gone quiet.

    Filtering criteria (People sheet):
        stage in ("contacted", "demo_completed", "pricing")
        AND (last_contact_date is null  OR  last_contact_date < today − followup_days)

    Sheet updates on success (People tab):
        last_contact      ← "email"
        last_contact_date ← today
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
                    email_type="followup_email",
                    sent_at=datetime.now(timezone.utc),
                    success=True,
                    error="dry_run – not sent",
                ))
                continue

            try:
                resp = self.api.send_email(
                    sender=self._sender_address(),
                    to=pwc.email,
                    subject=subject,
                    html_body=html_body,
                )
                # Update People sheet
                for col, val in [
                    (PeopleColumns.LAST_CONTACT, today_str),
                    (PeopleColumns.LAST_CONTACT_DATE, today_str),
                ]:
                    self.api.update_cell(
                        self.config.spreadsheet_id,
                        SheetNames.PEOPLE,
                        pwc.row_index,
                        col,
                        val,
                    )

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

            except (GmailAPIError, SheetUpdateError) as exc:
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
