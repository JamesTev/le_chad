"""
Structured JSON logging for pipeline runs. Each run appends one entry to the log file.
The dashboard reads these logs to show pipeline history.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path("pipeline_runs.jsonl")


def log_run(
    log_path: Path | None = None,
    *,
    story_id: int | None = None,
    story_title: str = "",
    hn_url: str = "",
    plan_title: str = "",
    plan_summary: str = "",
    changes: list[dict] | None = None,
    apply_results: list[dict] | None = None,
    test_result: dict | None = None,
    pr_result: dict | None = None,
    outcome: str = "unknown",
    error: str | None = None,
    duration_s: float = 0,
) -> dict:
    """Append a structured log entry. Returns the entry dict."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "story_id": story_id,
        "story_title": story_title,
        "hn_url": hn_url,
        "plan_title": plan_title,
        "plan_summary": plan_summary,
        "changes": changes or [],
        "apply_results": apply_results or [],
        "test_result": test_result or {},
        "pr_result": pr_result or {},
        "outcome": outcome,
        "error": error,
        "duration_s": round(duration_s, 2),
    }

    path = log_path or DEFAULT_LOG_PATH
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def read_logs(log_path: Path | None = None) -> list[dict]:
    """Read all log entries from the JSONL file."""
    path = log_path or DEFAULT_LOG_PATH
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
