-- cache.db schema. Raw API responses are cached verbatim BEFORE any transform
-- (music-project.md: refetching is a failure mode). Derived rows carry pipeline_version.

-- Verbatim API response cache. Key = "<source>:<endpoint>:<canonical-params>".
CREATE TABLE IF NOT EXISTS raw_responses (
    cache_key   TEXT PRIMARY KEY,
    source      TEXT NOT NULL,          -- lastfm | musicbrainz
    endpoint    TEXT NOT NULL,
    params      TEXT NOT NULL,          -- JSON of request params
    status_code INTEGER,
    body        TEXT,                   -- raw response text, unmodified
    fetched_at  TEXT NOT NULL           -- ISO8601 UTC
);

-- One row per album in the corpus. id = normalize(artist)␟normalize(album) (ADR-007).
-- Nothing is silently dropped: a failed fetch still gets a row with status='failed'.
CREATE TABLE IF NOT EXISTS albums (
    id            TEXT PRIMARY KEY,
    artist        TEXT NOT NULL,        -- display casing
    album         TEXT NOT NULL,
    mbid          TEXT,                 -- Last.fm mbid, merge aid only (ADR-007)
    year          INTEGER,              -- resolved release year, or NULL
    year_status   TEXT,                 -- resolved | unresolved
    status        TEXT NOT NULL,        -- ok | failed
    fetched_at    TEXT
);

-- Cleaned, blacklist-filtered tag vector per album (derived — ADR-003).
-- weight is the Last.fm per-album count (top tag = 100).
CREATE TABLE IF NOT EXISTS album_tags (
    album_id         TEXT NOT NULL,
    tag              TEXT NOT NULL,     -- normalized (lowercased, trimmed)
    weight           REAL NOT NULL,
    pipeline_version TEXT NOT NULL,
    PRIMARY KEY (album_id, tag, pipeline_version),
    FOREIGN KEY (album_id) REFERENCES albums(id)
);

-- Global tag frequency from Last.fm tag.getInfo — the df source for IDF (ADR-005).
-- Corpus-independent on purpose: local df would punish deliberately-overloaded genres.
CREATE TABLE IF NOT EXISTS tag_global (
    tag        TEXT PRIMARY KEY,        -- normalized
    reach      INTEGER,                 -- distinct users (df proxy)
    taggings   INTEGER,                 -- total taggings
    fetched_at TEXT
);

-- Precomputed per-axis edge similarities (similarity stage → export stage).
-- Only edges clearing the export contract (ADR-004) are stored. sim_year NULL =>
-- pair drops the year term client-side and renormalizes (ADR-002).
CREATE TABLE IF NOT EXISTS edges (
    source                TEXT NOT NULL,
    target                TEXT NOT NULL,
    sim_genre_raw_cosine  REAL,
    sim_genre_raw_jaccard REAL,
    sim_genre_idf_cosine  REAL,
    sim_genre_idf_jaccard REAL,
    sim_year              REAL,          -- nullable
    pipeline_version      TEXT NOT NULL,
    PRIMARY KEY (source, target, pipeline_version)
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
