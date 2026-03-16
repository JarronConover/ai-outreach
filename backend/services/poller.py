"""
Background threads: Supabase poller (watches for new uncontacted people)
and outreach ticker (scheduled follow-up cadence).
"""
from __future__ import annotations

import os
import threading

from backend.services.agent_loader import get_existing_people
from backend.services.jobs import start_outreach_job

_seen_person_ids: set[str] = set()
_stop_poller = threading.Event()

_POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
_OUTREACH_INTERVAL = int(os.getenv("OUTREACH_INTERVAL_HOURS", "24")) * 3600


def seed_seen_ids() -> None:
    """Pre-populate seen IDs from Supabase so we don't re-trigger on startup."""
    try:
        people = get_existing_people()
        for record in people.values():
            pid = record.get("id", "")
            last_contact = record.get("last_contact") or ""
            if pid and str(last_contact).strip():
                _seen_person_ids.add(pid)
        print(f"[poller] seeded {len(_seen_person_ids)} already-contacted person IDs")
    except Exception as e:
        print(f"[poller] failed to seed existing people: {e}")


def _supabase_poller() -> None:
    """Poll Supabase and trigger outreach for new uncontacted people."""
    print(f"[poller] started, interval={_POLL_INTERVAL}s")
    while not _stop_poller.wait(timeout=_POLL_INTERVAL):
        try:
            people = get_existing_people()
            new_ids = []
            for record in people.values():
                person_id = record.get("id", "")
                last_contact = record.get("last_contact") or ""
                if person_id and not str(last_contact).strip() and person_id not in _seen_person_ids:
                    _seen_person_ids.add(person_id)
                    new_ids.append(person_id)

            if new_ids:
                print(f"[poller] detected {len(new_ids)} new uncontacted person(s) — triggering outreach")
                job_id = start_outreach_job()
                print(f"[poller] outreach job queued: {job_id}")
        except Exception as e:
            print(f"[poller] error during poll: {e}")


def _outreach_ticker() -> None:
    """Fire outreach on a fixed cadence for follow-ups and check-ins."""
    print(f"[ticker] started, interval={_OUTREACH_INTERVAL // 3600}h")
    while not _stop_poller.wait(timeout=_OUTREACH_INTERVAL):
        print("[ticker] scheduled outreach run — triggering follow-ups/check-ins")
        job_id = start_outreach_job()
        print(f"[ticker] outreach job queued: {job_id}")


def start_background_threads() -> tuple[threading.Thread, threading.Thread]:
    """Start poller and ticker threads. Returns (poller_thread, ticker_thread)."""
    poller_thread = threading.Thread(target=_supabase_poller, daemon=True)
    ticker_thread = threading.Thread(target=_outreach_ticker, daemon=True)
    poller_thread.start()
    ticker_thread.start()
    return poller_thread, ticker_thread


def stop_background_threads() -> None:
    """Signal both background threads to stop."""
    _stop_poller.set()
