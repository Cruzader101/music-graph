"""MusicBrainz year resolution (ADR-001, ADR-006) — years ONLY, nothing else.

Conservative matching: accept a release-group only if fuzzy(artist) AND search
score both clear floors; among qualifiers take the EARLIEST first-release-date
(defeats reissues). Missing over wrong — return None rather than guess.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

import config
from pipeline import http_client
from pipeline.logsetup import get_logger

log = get_logger("musicbrainz")
SOURCE = "musicbrainz"

_YEAR_RE = re.compile(r"^(?P<y>(?:19|20)\d{2})")


def resolve_year(conn, artist: str, album: str) -> int | None:
    """Return the earliest confidently-matched release year, or None."""
    data = http_client.get_json(
        conn, SOURCE, "release-group", config.MUSICBRAINZ_URL,
        {"query": f'artist:"{artist}" AND releasegroup:"{album}"', "fmt": "json", "limit": 10},
        config.MUSICBRAINZ_RATE_LIMIT_RPS,
    )
    if data is None:
        return None

    candidate_years: list[int] = []
    for rg in data.get("release-groups", []):
        score = int(rg.get("score") or 0)
        if score < config.MB_SCORE_FLOOR:
            continue
        rg_artist = _artist_credit(rg)
        if fuzz.token_sort_ratio(rg_artist.lower(), artist.lower()) < config.MB_ARTIST_FUZZ_FLOOR:
            continue
        year = _year_of(rg.get("first-release-date", ""))
        if year is not None:
            candidate_years.append(year)

    if not candidate_years:
        log.info("year unresolved: %s — %s", artist, album)
        return None
    return min(candidate_years)  # earliest defeats reissues


def _artist_credit(rg: dict) -> str:
    credits = rg.get("artist-credit") or []
    return "".join(
        (c.get("name") or (c.get("artist") or {}).get("name") or "") + (c.get("joinphrase") or "")
        for c in credits
    ).strip()


def _year_of(date_str: str) -> int | None:
    m = _YEAR_RE.match(date_str or "")
    return int(m.group("y")) if m else None
