"""Data-coverage audit (roadmap #2; run after any ingestion change per music-project.md).

Reports: fetch success, tag coverage %, albums with <2 tags, year resolution,
and junk-tag leakage candidates (rare tags + non-genre-looking tags that IDF
would amplify — feeds the blacklist growth loop, ADR-003). Read-only.
Run: python -m tools.audit
"""
from __future__ import annotations

import re
from collections import Counter

import config
from pipeline import db

# Heuristics for junk that shouldn't be a genre (labels, listening-habit tags).
_JUNK_HINTS = re.compile(
    r"\b(records?|recordings?|label|entertainment|favou?rite|owned?|vinyl|"
    r"listened|heard|spotify|best|essential|masterpiece|perfect|amazing|"
    r"my |seen live|wishlist|to listen)\b", re.IGNORECASE)


def main() -> None:
    conn = db.connect()
    pv = config.PIPELINE_VERSION

    total = conn.execute("SELECT COUNT(*) c FROM albums").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) c FROM albums WHERE status='failed'").fetchone()["c"]
    ok = total - failed

    # Tag coverage per ok album.
    counts = {r["id"]: r["n"] for r in conn.execute(
        """SELECT a.id, COUNT(t.tag) n FROM albums a
           LEFT JOIN album_tags t ON t.album_id=a.id AND t.pipeline_version=?
           WHERE a.status='ok' GROUP BY a.id""", (pv,)).fetchall()}
    names = {r["id"]: f'{r["artist"]} — {r["album"]}'
             for r in conn.execute("SELECT id, artist, album FROM albums")}

    ge1 = sum(1 for n in counts.values() if n >= 1)
    ge2 = sum(1 for n in counts.values() if n >= 2)
    sparse = sorted([(n, names[i]) for i, n in counts.items() if n < 2])

    # Year resolution.
    yr_ok = conn.execute("SELECT COUNT(*) c FROM albums WHERE year_status='resolved'").fetchone()["c"]
    yr_bad = [names[r["id"]] for r in conn.execute(
        "SELECT id FROM albums WHERE year_status='unresolved' AND status='ok'").fetchall()]

    # Tag distribution + junk candidates.
    tag_rows = conn.execute(
        "SELECT tag, COUNT(*) df FROM album_tags WHERE pipeline_version=? GROUP BY tag", (pv,)).fetchall()
    df = Counter({r["tag"]: r["df"] for r in tag_rows})
    singletons = [t for t, c in df.items() if c == 1]
    junk = sorted([t for t in df if _JUNK_HINTS.search(t)])

    def pct(x): return f"{100*x/ok:.0f}%" if ok else "n/a"

    print(f"\n=== COVERAGE AUDIT (pipeline v{pv}) ===")
    print(f"albums: {total} total | {ok} ok | {failed} failed")
    if failed:
        for r in conn.execute("SELECT id FROM albums WHERE status='failed'"):
            print(f"   FAILED: {names[r['id']]}")
    print(f"\ntag coverage: >=1 tag {ge1}/{ok} ({pct(ge1)}) | >=2 tags {ge2}/{ok} ({pct(ge2)})")
    print(f"distinct tags: {len(df)} | singletons (df=1): {len(singletons)}")
    if sparse:
        print(f"\nsparse (<2 tags), {len(sparse)}:")
        for n, name in sparse:
            print(f"   [{n}] {name}")
    print(f"\nyears: {yr_ok}/{ok} resolved ({pct(yr_ok)}) | {len(yr_bad)} unresolved")
    for name in yr_bad:
        print(f"   unresolved: {name}")
    if junk:
        print(f"\njunk-tag leakage candidates ({len(junk)}) — review for blacklist (ADR-003):")
        for t in junk:
            print(f"   {t!r} (df={df[t]})")
    print(f"\ntop 15 tags by df (IDF handles these): "
          f"{', '.join(f'{t}·{c}' for t, c in df.most_common(15))}")
    conn.close()


if __name__ == "__main__":
    main()
