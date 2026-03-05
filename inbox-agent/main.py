"""Entry point for the inbox-agent.

Usage:
    python inbox-agent/main.py [--dry-run]
"""

import argparse
import os
import sys

# inbox-agent/ must be first so agent.* and tools.* resolve here
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

from agent.config import InboxAgentConfig
from agent.orchestrator import InboxOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="AI SDR Inbox Agent")
    parser.add_argument("--dry-run", action="store_true", help="Preview only — no writes or sends")
    args = parser.parse_args()

    config = InboxAgentConfig.from_env()
    if args.dry_run:
        config = config.model_copy(update={"dry_run": True})

    print(f"[inbox] starting run (dry_run={config.dry_run}, max_emails={config.max_emails})")
    result = InboxOrchestrator(config).run()

    print(f"\n[inbox] summary:")
    print(f"  total messages seen : {result.total}")
    print(f"  skipped (dedup)     : {result.skipped}")
    print(f"  actions created     : {result.actions_created}")
    print(f"  needs manual review : {result.manual_count}")
    if result.errors:
        print(f"  errors              : {len(result.errors)}")
        for err in result.errors:
            print(f"    - {err}")


if __name__ == "__main__":
    main()
