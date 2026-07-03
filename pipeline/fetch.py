"""Stage 1 — fetch. albums.csv → Last.fm tags/info + MusicBrainz years → cache.db.

Writes raw responses verbatim (via http_client) and one `albums` row per input.
Never silently drops an album: a failed fetch still gets status='failed' so
coverage is auditable (music-project.md). Re-runnable — served entirely from cache on
a second run. Run: python -m pipeline.fetch
"""
from __future__ import annotations

import csv
import json

import config
from pipeline import db, lastfm, musicbrainz
from pipeline.identity import album_id
from pipeline.logsetup import get_logger

log = get_logger("fetch")


def read_albums_csv() -> list[tuple[str, str]]:
    with open(config.ALBUMS_CSV, encoding="utf-8", newline="") as f:
        return [(r["artist"].strip(), r["album"].strip())
                for r in csv.DictReader(f) if r.get("artist") and r.get("album")]


def resolve_year(conn, artist: str, album: str, lastfm_year: int | None) -> tuple[int | None, str]:
    """ADR-006 order: Last.fm year if present → MusicBrainz → unresolved."""
    if lastfm_year is not None:
        return lastfm_year, "resolved"
    mb_year = musicbrainz.resolve_year(conn, artist, album)
    if mb_year is not None:
        return mb_year, "resolved"
    return None, "unresolved"


def fetch_one(conn, artist: str, album: str) -> None:
    node_id = album_id(artist, album)
    info = lastfm.get_album_info(conn, artist, album)
    tags = lastfm.get_top_tags(conn, artist, album)

    if info is None and not tags:
        log.warning("FAILED %s — %s (no info, no tags)", artist, album)
        conn.execute(
            """INSERT OR REPLACE INTO albums
               (id, artist, album, mbid, year, year_status, status, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, 'failed', ?)""",
            (node_id, artist, album, None, None, "unresolved", db.utcnow()),
        )
        conn.commit()
        return

    mbid = info.mbid if info else None
    lastfm_year = info.year if info else None
    year, year_status = resolve_year(conn, artist, album, lastfm_year)

    conn.execute(
        """INSERT OR REPLACE INTO albums
           (id, artist, album, mbid, year, year_status, status, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, 'ok', ?)""",
        (node_id, artist, album, mbid, year, year_status, db.utcnow()),
    )
    # Stash the raw (pre-blacklist) tags on the raw cache already; clean reads them.
    conn.commit()
    log.info("ok %s — %s | year=%s (%s) | %d tags",
             artist, album, year, year_status, len(tags or []))


def main() -> None:
    conn = db.connect()
    db.init_db(conn)
    if not config.LASTFM_API_KEY:
        log.error("LASTFM_API_KEY is empty — set it in .env (see .env.example). Aborting.")
        raise SystemExit(2)

    albums = read_albums_csv()
    log.info("fetching %d albums", len(albums))
    for artist, album in albums:
        try:
            fetch_one(conn, artist, album)
        except Exception:  # one album must never abort the batch
            log.exception("unexpected error on %s — %s", artist, album)

    ok = conn.execute("SELECT COUNT(*) c FROM albums WHERE status='ok'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) c FROM albums WHERE status='failed'").fetchone()["c"]
    unresolved = conn.execute(
        "SELECT COUNT(*) c FROM albums WHERE year_status='unresolved'").fetchone()["c"]
    log.info("fetch done: ok=%d failed=%d year_unresolved=%d", ok, failed, unresolved)
    conn.close()


if __name__ == "__main__":
    main()
