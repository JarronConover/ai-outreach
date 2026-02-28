"""
Tool 2 – Email New Prospects

Sends an introductory email to every Person in the People sheet whose stage
is "prospect" and who has never been contacted (last_contact_date is null).
These prospects were added to the sheet by the prospect-agent.

After a successful send the tool writes back to the People sheet:
    stage             ← "contacted"
    last_contact      ← "email"
    last_contact_date ← today (YYYY-MM-DD)
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent.exceptions import GmailAPIError, SheetUpdateError
from agent.results import EmailResult
from schemas.crm import CRMContext, PersonWithCompany, Stage
from schemas.sheet_config import PeopleColumns, SheetNames
from tools.tool import BaseTool


def _build_email(
    pwc: PersonWithCompany,
    sender_name: str,
    company_name: str,
) -> tuple[str, str]:
    industry_line = (
        f" in the {pwc.industry} space" if pwc.industry else ""
    )
    subject = f"Quick intro from {company_name}"
    html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <p>Hi {pwc.name},</p>

    <p>
      My name is <strong>{sender_name}</strong> from
      <strong>{company_name}</strong>. I came across
      <strong>{pwc.company_name}</strong>{industry_line} and thought there
      might be a great opportunity for us to connect.
    </p>

    <p>
      We help teams like yours streamline their workflows using AI – and I'd
      love to learn more about what you're working on and see if there's a fit.
    </p>

    <p>
      Would you be open to a quick 15-minute introductory call this week?
      Just reply to this email and we can find a time that works for you.
    </p>

    <p>No pressure at all – I appreciate your time either way!</p>

    <p>
      Best,<br/>
      <strong>{sender_name}</strong><br/>
      {company_name}
    </p>
  </body>
</html>
"""
    return subject, html_body


class EmailProspectsTool(BaseTool):
    """
    Emails new prospects who have never been contacted.

    Filtering criteria (People sheet):
        stage = "prospect"
        AND last_contact_date is null

    Sheet updates on success (People tab):
        stage             ← "contacted"
        last_contact      ← "email"
        last_contact_date ← today
    """

    tool_name = "email_prospects"

    def execute(self, crm: CRMContext) -> list[EmailResult]:
        results: list[EmailResult] = []

        to_contact = [
            pwc for pwc in crm.people_with_company
            if pwc.stage.lower() == Stage.PROSPECT
            and pwc.person.last_contact_date is None
            and pwc.email
        ]

        self.tracer.log_tool_start(
            self.tool_name,
            {"prospects_to_email": len(to_contact)},
        )

        today_str = datetime.now().strftime("%Y-%m-%d")

        for pwc in to_contact:
            subject, html_body = _build_email(
                pwc, self.config.sender_name, self.config.company_name
            )

            if self.config.dry_run:
                self.tracer.log_email_skipped(pwc.email, "dry_run=True")
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    email_type="prospect_outreach",
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
                # Advance stage and record contact in the People sheet
                for col, val in [
                    (PeopleColumns.STAGE, Stage.CONTACTED),
                    (PeopleColumns.LAST_CONTACT, "email"),
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
                    email_type="prospect_outreach",
                )
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    message_id=resp.get("id"),
                    email_type="prospect_outreach",
                    sent_at=datetime.now(timezone.utc),
                    success=True,
                ))

            except (GmailAPIError, SheetUpdateError) as exc:
                self.tracer.log_error(exc, {"contact": pwc.email})
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    email_type="prospect_outreach",
                    sent_at=datetime.now(timezone.utc),
                    success=False,
                    error=str(exc),
                ))

        self.tracer.log_tool_end(
            self.tool_name,
            success=True,
            result_summary=f"{sum(1 for r in results if r.success)}/{len(to_contact)} sent",
        )
        return results
