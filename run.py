"""Pipeline orchestrator. Runs the stages in order; each is also runnable alone
(python -m pipeline.<stage>) since every stage reads/writes cache.db + files.

Usage:
    python run.py                # full pipeline: fetch → clean → features → similarity → export
    python run.py --from clean   # resume from a stage (uses cached upstream data)
"""
from __future__ import annotations

import argparse

from pipeline import clean, export, features, fetch, similarity
from pipeline.logsetup import get_logger

log = get_logger("run")

STAGES = [
    ("fetch", fetch.main),
    ("clean", clean.main),
    ("features", features.main),
    ("similarity", similarity.main),
    ("export", export.main),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="fetch",
                    choices=[name for name, _ in STAGES],
                    help="resume from this stage (cached upstream reused)")
    args = ap.parse_args()

    names = [n for n, _ in STAGES]
    start = names.index(args.start)
    for name, fn in STAGES[start:]:
        log.info("=== stage: %s ===", name)
        fn()
    log.info("pipeline complete → open frontend/index.html")


if __name__ == "__main__":
    main()
