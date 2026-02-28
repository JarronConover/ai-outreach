import json
from datetime import datetime
from typing import Any


def log_trace(step: str, data: Any) -> None:
    """Print a timestamped reasoning trace entry to stdout."""
    timestamp = datetime.utcnow().isoformat()
    entry = {"timestamp": timestamp, "step": step, "data": data}
    print(f"[TRACE] {json.dumps(entry, default=str, indent=2)}")
