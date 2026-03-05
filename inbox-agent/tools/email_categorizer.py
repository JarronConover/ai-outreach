"""
Email categorizer and reply generator for the inbox-agent.

Uses Gemini 2.5 Flash (consistent with the prospect-agent) to:
  1. Classify an inbound email into one of five categories.
  2. Generate a note (key-points summary) for storage in the Emails sheet.
  3. Generate a personalised HTML reply body using the base templates.
  4. Refine a draft reply at confirm time using the stored note.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# ---------------------------------------------------------------------------
# Category constants (mirror schemas.crm.EmailCategory)
# ---------------------------------------------------------------------------
INTERESTED     = "interested"
NOT_INTERESTED = "not_interested"
DEMO_REQUEST   = "demo_request"
MANUAL         = "manual"
OTHER          = "other"

_VALID_CATEGORIES = {INTERESTED, NOT_INTERESTED, DEMO_REQUEST, MANUAL, OTHER}

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "business" / "templates"

_TEMPLATE_MAP = {
    INTERESTED:     _TEMPLATES_DIR / "interested_reply.txt",
    NOT_INTERESTED: _TEMPLATES_DIR / "not_interested_reply.txt",
    DEMO_REQUEST:   _TEMPLATES_DIR / "demo_request_reply.txt",
}

_CATEGORIZE_PROMPT = """\
You are an AI assistant helping an SDR team categorize inbound sales email replies.

Classify the email below into exactly one of these categories:
- interested      : The sender shows genuine interest, asks questions, or wants to learn more
- not_interested  : The sender clearly opts out, rejects further contact, or unsubscribes
- demo_request    : The sender explicitly asks to schedule a meeting, demo, or call
- manual          : Ambiguous, complex, price negotiation, objection, or needs human judgment
- other           : Auto-reply, out-of-office, newsletter, spam, or unrelated system message

Email subject : {subject}
From          : {from_name} <{from_email}>

Email body:
{body}

Reply with exactly one word — the category name. Nothing else."""

_NOTE_PROMPT = """\
You are helping an SDR team track key points from inbound sales emails.

Read the email below and write a concise 1-2 sentence note capturing:
- What the sender is asking for or responding to
- Any specific details, objections, or requests worth remembering

Be factual and brief. Do not write a greeting or sign-off — just the note text.

Email subject : {subject}
From          : {from_name}
Email body:
{body}"""

_REPLY_PROMPT = """\
You are drafting a short, professional reply email on behalf of {sender_name} at {our_company}.

Use the template below as a starting point. Personalise it naturally using the context provided.
Keep the tone warm and conversational. Return only the email body as plain HTML — no subject line,
no "From:" header, just the <p> tags that make up the body.

--- TEMPLATE ---
{template}
--- END TEMPLATE ---

Context:
- Recipient name  : {recipient_name}
- Our company     : {our_company}
- Sender name     : {sender_name}
- Original subject: {original_subject}
- Email excerpt   : {body_snippet}"""

_REFINE_PROMPT = """\
You are refining a draft reply email on behalf of {sender_name} at {our_company}.

The draft was generated from a template. Use the note below (a summary of what the recipient said)
to make the reply more specific and personal where appropriate. Keep it concise and warm.
Return only the email body as plain HTML — no subject line, no "From:" header, just <p> tags.

--- DRAFT ---
{draft}
--- END DRAFT ---

Note about what the recipient said:
{note}

Recipient name: {recipient_name}"""


class EmailCategorizer:
    """
    Wraps Gemini 2.5 Flash (via langchain-google-genai) to categorise emails,
    generate key-point notes, and draft personalised replies.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0,
        )

    def _invoke(self, prompt: str) -> str:
        response = self._llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    def categorize(
        self,
        subject: str,
        from_email: str,
        from_name: str,
        body_snippet: str,
    ) -> str:
        """Return one of: interested | not_interested | demo_request | manual | other."""
        prompt = _CATEGORIZE_PROMPT.format(
            subject=subject or "(no subject)",
            from_name=from_name or from_email,
            from_email=from_email,
            body=body_snippet[:1500],
        )
        try:
            raw = self._invoke(prompt).lower()
            first_word = raw.split()[0].rstrip(".,;:") if raw else OTHER
            return first_word if first_word in _VALID_CATEGORIES else MANUAL
        except Exception as exc:
            print(f"[categorizer] Gemini error during categorization: {exc}")
            return MANUAL  # fail safe to manual review

    def generate_note(
        self,
        subject: str,
        from_name: str,
        from_email: str,
        body_snippet: str,
    ) -> Optional[str]:
        """
        Generate a concise 1-2 sentence note summarising the email's key points.
        Stored in the Emails sheet and used at confirm time to refine the reply.
        Returns None on failure (non-critical).
        """
        prompt = _NOTE_PROMPT.format(
            subject=subject or "(no subject)",
            from_name=from_name or from_email,
            body=body_snippet[:1500],
        )
        try:
            return self._invoke(prompt)
        except Exception as exc:
            print(f"[categorizer] Gemini error during note generation: {exc}")
            return None

    def generate_reply(
        self,
        category: str,
        recipient_name: str,
        from_email: str,
        original_subject: str,
        body_snippet: str,
        sender_name: str,
        our_company: str,
    ) -> Optional[str]:
        """
        Generate an HTML reply body for the given category.

        Returns None if the category has no template (e.g. manual / other).
        """
        template_path = _TEMPLATE_MAP.get(category)
        if template_path is None or not template_path.exists():
            return None

        template = template_path.read_text(encoding="utf-8")

        prompt = _REPLY_PROMPT.format(
            sender_name=sender_name,
            our_company=our_company,
            template=template,
            recipient_name=recipient_name or from_email,
            original_subject=original_subject or "(no subject)",
            body_snippet=body_snippet[:800],
        )
        try:
            return self._invoke(prompt)
        except Exception as exc:
            print(f"[categorizer] Gemini error during reply generation: {exc}")
            # Fall back to the raw template with simple substitution
            return (
                template
                .replace("{recipient_name}", recipient_name or from_email)
                .replace("{our_company}", our_company)
                .replace("{sender_name}", sender_name)
                .replace("{original_subject}", original_subject or "(no subject)")
                .replace("\n", "<br>")
            )


# ---------------------------------------------------------------------------
# Standalone refine function — called by orchestrator-agent at confirm time
# ---------------------------------------------------------------------------

def refine_reply(
    draft_body: str,
    note: str,
    recipient_name: str,
    sender_name: str,
    our_company: str,
) -> str:
    """
    Refine a draft reply body using the stored note about what the recipient said.
    Returns the refined HTML body, or the original draft on failure.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or not note or not draft_body:
        return draft_body

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0,
    )
    prompt = _REFINE_PROMPT.format(
        draft=draft_body,
        note=note,
        recipient_name=recipient_name or "",
        sender_name=sender_name,
        our_company=our_company,
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as exc:
        print(f"[categorizer] Gemini error during reply refinement: {exc}")
        return draft_body
