"""Single source of config: paths, weights, thresholds, secrets (via env).

No magic numbers live in pipeline code (music-project.md) — they live here. Every stage
imports from this module; nothing here imports from a pipeline stage.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DERIVED_DIR = DATA_DIR / "derived"       # git-ignored feature matrices
LOG_DIR = ROOT / "logs"
DB_PATH = ROOT / "cache.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
BLACKLIST_PATH = DATA_DIR / "genre_blacklist.txt"
ALBUMS_CSV = DATA_DIR / "albums.csv"
FETCH_ERROR_LOG = LOG_DIR / "fetch_errors.jsonl"
GRAPH_JSON = ROOT / "frontend" / "graph.json"

for _d in (DERIVED_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Pipeline versioning ---------------------------------------------------
# Bump when a derived-feature computation changes so stale rows are visible.
PIPELINE_VERSION = "1"

# --- Secrets (env / .env) --------------------------------------------------
def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader — avoids a dependency for a 10-line parse."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "")

# --- API endpoints & etiquette ---------------------------------------------
LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/release-group/"
# MusicBrainz requires a descriptive UA with contact info.
USER_AGENT = "MusicGraph/0.1 (personal project; cruzmaldonado2473@gmail.com)"

LASTFM_RATE_LIMIT_RPS = 5.0      # Last.fm ~5 req/s
MUSICBRAINZ_RATE_LIMIT_RPS = 1.0  # MusicBrainz hard 1 req/s
REQUEST_TIMEOUT_S = 20
MAX_RETRIES = 4
RETRY_BACKOFF_BASE_S = 1.0        # exponential: base * 2**attempt

# --- Similarity model ------------------------------------------------------
SIGMA_YEAR = 5.0                 # gaussian year-kernel width, exp(-Δ²/2σ²)
TOP_TAGS_PER_ALBUM = 30          # cap on tags pulled per album

# Export/edge contract (ADR-004) — coupled to the frontend, change together.
EXPORT_FLOOR = 0.15              # ship edge if max axis >= floor ...
TOP_K_GUARANTEE = 15            # ... OR in either endpoint's top-15 (no kNN starvation)

# Frontend slider/toggle defaults (mirrored into graph.json meta.defaults).
DEFAULTS = {
    "w_genre": 0.5,
    "w_year": 0.5,
    "sigma_year": SIGMA_YEAR,
    "threshold": 0.35,
    "k": 8,
}
GENRE_METRIC_DEFAULT = "cosine"    # cosine | jaccard
GENRE_WEIGHTING_DEFAULT = "raw"    # raw | idf
DRAW_MODE_DEFAULT = "threshold"    # threshold | knn | mutual_knn

# --- MusicBrainz conservative year matching (ADR-006) ----------------------
MB_ARTIST_FUZZ_FLOOR = 85        # rapidfuzz token_sort_ratio 0..100
MB_SCORE_FLOOR = 80              # MB search score 0..100
