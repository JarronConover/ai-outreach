"""
Tool 2 – Email New Prospects

Sends an introductory email to every Person in Supabase whose stage is
"prospect" and who has never been contacted (last_contact_date is null).

After a successful send the tool writes back to Supabase:
    stage             <- "contacted"
    last_contact      <- "email"
    last_contact_date <- today (ISO datetime)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent.exceptions import GmailAPIError
from agent.results import EmailResult
from schemas.crm import CRMContext, PersonWithCompany, Stage
from tools.tool import BaseTool

_TEMPLATE = Path(__file__).parent.parent.parent / "business" / "templates" / "prospect_outreach.html"


def _build_email(
    pwc: PersonWithCompany,
    sender_name: str,
    company_name: str,
) -> tuple[str, str]:
    industry_line = f" in the {pwc.industry} space" if pwc.industry else ""
    subject = f"Quick intro from {company_name}"
    html_body = _TEMPLATE.read_text(encoding="utf-8").format(
        name=pwc.name,
        sender_name=sender_name,
        our_company=company_name,
        company_name=pwc.company_name,
        industry_line=industry_line,
    )
    return subject, html_body


class EmailProspectsTool(BaseTool):
    """
    Emails new prospects who have never been contacted.

    Filtering criteria:
        stage = "prospect"
        AND last_contact_date is null

    Supabase updates on success:
        stage             <- "contacted"
        last_contact      <- "email"
        last_contact_date <- today
    """

    tool_name = "email_prospects"

    def execute(self, crm: CRMContext) -> list[EmailResult]:
        results: list[EmailResult] = []

        to_contact = [
            pwc for pwc in crm.people_with_company
            if pwc.stage.lower() in (Stage.PROSPECT, "prospecting")
            and pwc.person.last_contact_date is None
            and pwc.email
        ]

        self.tracer.log_tool_start(
            self.tool_name,
            {"prospects_to_email": len(to_contact)},
        )

        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

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
                    body=html_body,
                    email_type="prospect_outreach",
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
                # Advance stage and record contact in Supabase
                self.api.update_person(pwc.person.id, {
                    "stage": Stage.CONTACTED,
                    "last_contact": "email",
                    "last_contact_date": today_str,
                })

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

            except Exception as exc:
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
