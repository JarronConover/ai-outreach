"""
Tool 1 – Email Current Clients

Sends a personalised check-in email to every Person in the People sheet
whose stage is "client" and who has not been contacted within the configured
client_checkin_days window.

After a successful send the tool writes back to the People sheet:
    last_contact      ← "email"
    last_contact_date ← today (YYYY-MM-DD)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.exceptions import GmailAPIError, SheetUpdateError
from agent.results import EmailResult
from schemas.crm import CRMContext, PersonWithCompany, Stage
from schemas.sheet_config import PeopleColumns, SheetNames
from tools.tool import BaseTool

_TEMPLATE = Path(__file__).parent.parent.parent / "business" / "templates" / "client_outreach.html"


def _build_email(
    pwc: PersonWithCompany,
    sender_name: str,
    company_name: str,
) -> tuple[str, str]:
    subject = f"Checking in – {company_name}"
    html_body = _TEMPLATE.read_text(encoding="utf-8").format(
        name=pwc.name,
        sender_name=sender_name,
        our_company=company_name,
        company_name=pwc.company_name,
    )
    return subject, html_body


class EmailClientsTool(BaseTool):
    """
    Emails existing clients who haven't been contacted recently.

    Filtering criteria (People sheet):
        stage = "client"
        AND (last_contact_date is null  OR  last_contact_date < today − client_checkin_days)

    Sheet updates on success (People tab):
        last_contact      ← "email"
        last_contact_date ← today
    """

    tool_name = "email_clients"

    def execute(self, crm: CRMContext) -> list[EmailResult]:
        results: list[EmailResult] = []

        cutoff = datetime.now() - timedelta(days=self.config.client_checkin_days)
        to_contact = [
            pwc for pwc in crm.people_with_company
            if pwc.stage.lower() == Stage.CLIENT
            and pwc.email
            and (
                pwc.person.last_contact_date is None
                or pwc.person.last_contact_date < cutoff
            )
        ]

        self.tracer.log_tool_start(
            self.tool_name,
            {"clients_to_email": len(to_contact)},
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
                    email_type="client_outreach",
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
                    email_type="client_outreach",
                )
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    message_id=resp.get("id"),
                    email_type="client_outreach",
                    sent_at=datetime.now(timezone.utc),
                    success=True,
                ))

            except (GmailAPIError, SheetUpdateError) as exc:
                self.tracer.log_error(exc, {"contact": pwc.email})
                results.append(EmailResult(
                    recipient_email=pwc.email,
                    recipient_name=pwc.name,
                    subject=subject,
                    email_type="client_outreach",
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
