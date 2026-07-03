"""Stage 2 — clean. Raw cached tags → blacklist-filtered tag vectors (album_tags),
plus global tag frequencies (tag_global) for the distinct surviving tags.

Filtering (ADR-003): a tag counts UNLESS it is on data/genre_blacklist.txt or is a
bare year/decade (1998, 90s, 1990s). IDF (ADR-005) handles common-generic tags
separately, so this only kills rare idiosyncratic junk. Reads the `albums` table
+ the Last.fm cache; writes derived rows tagged with pipeline_version.
Run: python -m pipeline.clean
"""
from __future__ import annotations

import re

import config
from pipeline import db, lastfm
from pipeline.logsetup import get_logger

log = get_logger("clean")

_DECADE_RE = re.compile(r"^\s*(?:19|20)?\d{2}s?\s*$")  # 90s, 1990s, 1998, 98


def load_blacklist() -> set[str]:
    tags: set[str] = set()
    for line in config.BLACKLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            tags.add(line.lower())
    return tags


def clean_tag(name: str) -> str:
    # Normalize hyphen/underscore/slash to space so "hip-hop" ≡ "hip hop" and
    # "post-rock" ≡ "post rock" — Last.fm returns both variants as distinct
    # tags, which otherwise split a cluster's color AND its cosine dimensions.
    name = re.sub(r"[-_/]+", " ", name.strip().lower())
    return re.sub(r"\s+", " ", name).strip()


def is_junk(tag: str, blacklist: set[str]) -> bool:
    return tag in blacklist or bool(_DECADE_RE.match(tag))


def clean_album(conn, album_id: str, artist: str, album: str, blacklist: set[str]) -> int:
    tags = lastfm.get_top_tags(conn, artist, album)  # cache hit after fetch stage
    if not tags:
        return 0
    conn.execute(
        "DELETE FROM album_tags WHERE album_id = ? AND pipeline_version = ?",
        (album_id, config.PIPELINE_VERSION),
    )
    kept = 0
    for raw_name, weight in tags:
        tag = clean_tag(raw_name)
        if not tag or is_junk(tag, blacklist) or weight <= 0:
            continue
        conn.execute(
            """INSERT OR REPLACE INTO album_tags
               (album_id, tag, weight, pipeline_version) VALUES (?, ?, ?, ?)""",
            (album_id, tag, float(weight), config.PIPELINE_VERSION),
        )
        kept += 1
    conn.commit()
    return kept


def fetch_global_freqs(conn) -> None:
    """One cached tag.getInfo per distinct surviving tag → tag_global (IDF df)."""
    rows = conn.execute(
        "SELECT DISTINCT tag FROM album_tags WHERE pipeline_version = ?",
        (config.PIPELINE_VERSION,),
    ).fetchall()
    for row in rows:
        tag = row["tag"]
        if conn.execute("SELECT 1 FROM tag_global WHERE tag = ?", (tag,)).fetchone():
            continue
        stats = lastfm.get_tag_global(conn, tag)
        reach, taggings = stats if stats else (0, 0)
        conn.execute(
            "INSERT OR REPLACE INTO tag_global (tag, reach, taggings, fetched_at) VALUES (?, ?, ?, ?)",
            (tag, reach, taggings, db.utcnow()),
        )
    conn.commit()


def main() -> None:
    conn = db.connect()
    db.init_db(conn)
    blacklist = load_blacklist()
    albums = conn.execute(
        "SELECT id, artist, album FROM albums WHERE status = 'ok'"
    ).fetchall()

    sparse: list[str] = []
    for a in albums:
        kept = clean_album(conn, a["id"], a["artist"], a["album"], blacklist)
        if kept < 2:  # data-audit signal: <2 genre tags
            sparse.append(f"{a['artist']} — {a['album']} ({kept})")

    log.info("cleaned %d albums; %d have <2 tags", len(albums), len(sparse))
    for s in sparse:
        log.warning("sparse tags: %s", s)

    fetch_global_freqs(conn)
    n_global = conn.execute("SELECT COUNT(*) c FROM tag_global").fetchone()["c"]
    log.info("clean done: %d distinct tags with global freqs", n_global)
    conn.close()


if __name__ == "__main__":
    main()
