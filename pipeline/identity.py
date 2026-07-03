"""Album identity & normalization (ADR-007).

The canonical node key is  normalize(artist) ␟ normalize(album)  where normalize
lowercases, strips diacritics, drops reissue/edition suffixes, and collapses
whitespace. This is the primary key of the whole system (graph node, cache key,
Last.fm↔MusicBrainz join), so it is a small pure function with unit tests.

The normalized *artist* string is also what MusicBrainz year search consumes
(ADR-006) — one function, two consumers.
"""
from __future__ import annotations

import re
import unicodedata

# U+241F SYMBOL FOR UNIT SEPARATOR — visible, stable, absent from real titles.
SEP = "␟"

# Reissue / edition suffixes to strip. Matched case-insensitively against a
# trailing parenthetical/bracket group OR a trailing " - <edition>" tail.
_EDITION_WORDS = (
    r"remaster(?:ed)?",
    r"deluxe(?:\s+edition)?",
    r"expanded(?:\s+edition)?",
    r"anniversary(?:\s+edition)?",
    r"special\s+edition",
    r"collector'?s\s+edition",
    r"legacy\s+edition",
    r"super\s+deluxe",
    r"mono",
    r"stereo",
    r"reissue",
    r"bonus\s+track[s]?(?:\s+version)?",
    r"\d{4}\s+remaster(?:ed)?",
    r"remaster(?:ed)?\s+\d{4}",
    r"\d{4}\s+version",
    r".*\bedition\b",          # any "... edition"
    r"(?:19|20)\d{2}",         # trailing bare year, e.g. "(2011)"
)
_EDITION_RE = re.compile(
    r"\s*[\(\[]\s*(?:" + "|".join(_EDITION_WORDS) + r")\s*[\)\]]\s*$",
    flags=re.IGNORECASE,
)
_EDITION_TAIL_RE = re.compile(
    r"\s*[-–—:]\s*(?:" + "|".join(_EDITION_WORDS) + r")\s*$",
    flags=re.IGNORECASE,
)
_WS_RE = re.compile(r"\s+")


def strip_diacritics(text: str) -> str:
    """é → e, ü → u. NFKD decompose, drop combining marks."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def strip_editions(title: str) -> str:
    """Remove trailing reissue/edition suffixes, repeatedly (Loveless
    (Deluxe) (Remastered 2021) → Loveless). Applied before lowercasing so the
    parenthetical patterns read naturally; case-insensitive regardless."""
    prev = None
    out = title.strip()
    while out != prev:
        prev = out
        out = _EDITION_RE.sub("", out)
        out = _EDITION_TAIL_RE.sub("", out)
        out = out.strip()
    return out


def normalize(text: str) -> str:
    """Normalize an artist or album string to its canonical form."""
    text = strip_editions(text)
    text = strip_diacritics(text)
    text = text.lower()
    # Drop punctuation to spaces, then collapse. Keep alphanumerics + spaces.
    text = re.sub(r"[^\w\s]", " ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def album_id(artist: str, album: str) -> str:
    """Canonical node id: normalize(artist) ␟ normalize(album)."""
    return f"{normalize(artist)}{SEP}{normalize(album)}"


def split_id(node_id: str) -> tuple[str, str]:
    """Inverse of album_id for debugging: (norm_artist, norm_album)."""
    artist, _, album = node_id.partition(SEP)
    return artist, album
