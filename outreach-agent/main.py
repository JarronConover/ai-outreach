"""
Outreach Agent – Entry Point

Adds the project root to sys.path so that the global `schemas` package
(ai-outreach/schemas/) is importable from here.

Run:
    python main.py
    python main.py --dry-run         # preview actions, nothing is sent
    python main.py --export-trace    # write trace.json after the run

Required environment variables (see .env.example):
    SENDER_EMAIL, SENDER_NAME, COMPANY_NAME
    SUPABASE_URL, SUPABASE_KEY
    GOOGLE_CREDENTIALS_FILE  (default: credentials.json)
    GOOGLE_TOKEN_FILE        (default: token.pickle)
"""

from __future__ import annotations

import argparse
import os
import sys

# ── Path fix ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
# ─────────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv  # noqa: E402

from agent.config import OutreachAgentConfig  # noqa: E402
from agent.orchestrator import OutreachOrchestrator  # noqa: E402


def _load_config(dry_run: bool) -> OutreachAgentConfig:
    load_dotenv()

    missing = [
        var for var in ("SENDER_EMAIL", "SENDER_NAME", "COMPANY_NAME")
        if not os.getenv(var)
    ]
    if missing:
        print(
            f"[ERROR] Missing required environment variables: {', '.join(missing)}\n"
            "        Copy .env.example to .env and fill in the values.",
            file=sys.stderr,
        )
        sys.exit(1)

    return OutreachAgentConfig(
        credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        token_file=os.getenv("GOOGLE_TOKEN_FILE", "token.pickle"),
        sender_email=os.environ["SENDER_EMAIL"],
        sender_name=os.environ["SENDER_NAME"],
        company_name=os.environ["COMPANY_NAME"],
        bcc_email=os.getenv("BCC_EMAIL") or None,
        calendar_timezone=os.getenv("CALENDAR_TIMEZONE", "America/Denver"),
        demo_duration_minutes=int(os.getenv("DEMO_DURATION_MINUTES", "60")),
        followup_duration_minutes=int(os.getenv("FOLLOWUP_DURATION_MINUTES", "30")),
        google_meet=os.getenv("GOOGLE_MEET", "true").lower() == "true",
        followup_days=int(os.getenv("FOLLOWUP_DAYS", "7")),
        client_checkin_days=int(os.getenv("CLIENT_CHECKIN_DAYS", "30")),
        dry_run=dry_run,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the outreach agent against the Fellowship CRM (Supabase)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log all planned actions without sending emails or creating calendar events.",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt and send immediately.",
    )
    parser.add_argument(
        "--export-trace",
        metavar="FILE",
        nargs="?",
        const="trace.json",
        help="Export the full execution trace to a JSON file (default: trace.json).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    config = _load_config(dry_run=args.dry_run)
    orchestrator = OutreachOrchestrator(config)

    # ── Step 1: Plan (always runs as dry-run internally) ──────────────
    plan = orchestrator.plan()
    orchestrator.print_plan(plan)

    # ── Step 2: Dry-run mode – show plan only, no prompt ─────────────
    if args.dry_run:
        print("[DRY RUN] No emails sent and no calendar events created.\n")
        if args.export_trace:
            orchestrator.export_trace(args.export_trace)
            print(f"[INFO] Trace exported to {args.export_trace}")
        return

    # ── Step 3: Nothing to do ─────────────────────────────────────────
    planned_emails = [e for e in plan.emails_sent if e.success]
    planned_events = [c for c in plan.calendar_events_created if c.success]
    if not planned_emails and not planned_events:
        print("Nothing to do.")
        return

    # ── Step 4: Confirm ───────────────────────────────────────────────
    if not args.yes:
        try:
            answer = input("Proceed? [y/N] ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted.")
            return
        if answer != "y":
            print("Aborted.")
            return
        print()

    # ── Step 5: Execute live ──────────────────────────────────────────
    result = orchestrator.run()
    orchestrator.print_summary(result)

    if args.export_trace:
        orchestrator.export_trace(args.export_trace)
        print(f"[INFO] Trace exported to {args.export_trace}")

    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
