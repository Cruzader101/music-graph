"""Acceptance Check 1 (docs/acceptance-thin-slice.md): print top-5 nearest
neighbors by sim_genre_raw_cosine for seed albums. Reads the exported edges so
it tests exactly what shipped. Run: python -m tools.neighbors [N]
"""
from __future__ import annotations

import sys
from collections import defaultdict

from pipeline import db
import config

# Hand-picked seeds spanning the intended clusters (one per genre + the bridges).
SEEDS = [
    "my bloody valentine␟loveless",      # shoegaze
    "deafheaven␟sunbather",              # blackgaze bridge → shoegaze/black metal
    "mayhem␟de mysteriis dom sathanas",  # black metal
    "nick drake␟pink moon",              # folk
    "kendrick lamar␟good kid m a a d city",  # hip-hop
    "miles davis␟kind of blue",          # jazz
    "aphex twin␟selected ambient works 85 92",  # electronic/ambient
    "godspeed you black emperor␟lift your skinny fists like antennas to heaven",  # post-rock
]


def main() -> None:
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    conn = db.connect()
    names = {r["id"]: f'{r["artist"]} — {r["album"]}'
             for r in conn.execute("SELECT id, artist, album FROM albums")}

    sims: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for e in conn.execute(
        "SELECT source, target, sim_genre_raw_cosine s FROM edges WHERE pipeline_version=?",
        (config.PIPELINE_VERSION,),
    ):
        if e["s"] is None:
            continue
        sims[e["source"]].append((e["s"], e["target"]))
        sims[e["target"]].append((e["s"], e["source"]))

    for seed in SEEDS:
        label = names.get(seed, f"<missing: {seed}>")
        print(f"\n{label}")
        for s, other in sorted(sims.get(seed, []), reverse=True)[:top_n]:
            print(f"   {s:.3f}  {names.get(other, other)}")
    conn.close()


if __name__ == "__main__":
    main()
