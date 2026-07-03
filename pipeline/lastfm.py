"""Last.fm client (ADR-001): tags, album metadata, global tag frequencies.

Thin typed wrappers over the shared http_client. One client, one cache path,
one auth. Returns parsed domain objects; leaves persistence to the stages.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import config
from pipeline import http_client
from pipeline.identity import normalize

SOURCE = "lastfm"


@dataclass
class AlbumInfo:
    artist: str
    album: str
    mbid: str | None
    year: int | None                      # Last.fm listing year if present (often absent)
    tags: list[tuple[str, float]] = field(default_factory=list)  # (tag, weight 0..100)


def get_top_tags(conn, artist: str, album: str) -> list[tuple[str, float]] | None:
    """album.getTopTags → [(tag, weight)], normalized weights (Last.fm gives 0..100)."""
    data = http_client.get_json(
        conn, SOURCE, "album.getTopTags", config.LASTFM_API_URL,
        {"method": "album.getTopTags", "artist": artist, "album": album, "autocorrect": 1},
        config.LASTFM_RATE_LIMIT_RPS,
    )
    if data is None or "error" in data:
        return None
    raw = (data.get("toptags") or {}).get("tag") or []
    if isinstance(raw, dict):
        raw = [raw]
    out: list[tuple[str, float]] = []
    for t in raw[: config.TOP_TAGS_PER_ALBUM]:
        name = (t.get("name") or "").strip()
        try:
            count = float(t.get("count") or 0)
        except (TypeError, ValueError):
            count = 0.0
        if name:
            out.append((name, count))
    return out


def get_album_info(conn, artist: str, album: str) -> AlbumInfo | None:
    """album.getInfo → metadata (mbid, any listed year). Tags fetched separately."""
    data = http_client.get_json(
        conn, SOURCE, "album.getInfo", config.LASTFM_API_URL,
        {"method": "album.getInfo", "artist": artist, "album": album, "autocorrect": 1},
        config.LASTFM_RATE_LIMIT_RPS,
    )
    if data is None or "error" in data or "album" not in data:
        return None
    a = data["album"]
    mbid = a.get("mbid") or None
    # Last.fm getInfo has NO reliable release-year field: the deprecated
    # `releasedate` is empty, and `wiki.published` is the wiki EDIT date (it
    # returns e.g. 2026 for a 1993 album). Never guess a year here — defer
    # entirely to MusicBrainz (ADR-001/006). year stays None.
    return AlbumInfo(artist=a.get("artist", artist), album=a.get("name", album), mbid=mbid, year=None)


def get_tag_global(conn, tag: str) -> tuple[int, int] | None:
    """tag.getInfo → (reach, taggings) — the df source for IDF (ADR-005).

    Corpus-independent on purpose. Cached per distinct tag.
    """
    data = http_client.get_json(
        conn, SOURCE, "tag.getInfo", config.LASTFM_API_URL,
        {"method": "tag.getInfo", "tag": tag},
        config.LASTFM_RATE_LIMIT_RPS,
    )
    if data is None or "error" in data or "tag" not in data:
        return None
    stats = (data["tag"] or {}).get("stats") or {}
    try:
        reach = int(stats.get("reach") or 0)
        taggings = int(stats.get("taggings") or 0)
    except (TypeError, ValueError):
        return None
    return reach, taggings
