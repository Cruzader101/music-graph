"""Logging setup (music-project.md: use logging, not print; DEBUG→file, INFO→console)
plus the structured fetch-error sink at logs/fetch_errors.jsonl.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

import config

# The system uses non-ASCII (the ␟ node separator, unicode album titles). Force
# UTF-8 on the Windows console so logs/prints don't hit cp1252 encode errors.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root.addHandler(console)

        fileh = logging.FileHandler(config.LOG_DIR / "pipeline.log", encoding="utf-8")
        fileh.setLevel(logging.DEBUG)
        fileh.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(fileh)
        _configured = True
    return logging.getLogger(name)


def log_fetch_error(endpoint: str, params: dict, status: int | None, body: str) -> None:
    """Append one structured failure row (music-project.md error-handling contract)."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "params": {k: v for k, v in params.items() if k != "api_key"},
        "status": status,
        "body": (body or "")[:500],
    }
    with open(config.FETCH_ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
