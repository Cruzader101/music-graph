"""Stage 3 — features. album_tags + tag_global + albums.year → feature matrices.

Builds the raw and IDF-weighted tag-vector matrices and the year array, and
writes them to data/derived/features.npz (git-ignored). IDF is corpus-aware
from Last.fm global reach (ADR-005): idf(tag) = log(N / df), N = max reach,
df = tag's global reach — so ubiquitous tags (rock) are damped, niche tags kept.
Reads only cache.db; writes only files. Run: python -m pipeline.features
"""
from __future__ import annotations

import json

import numpy as np

import config
from pipeline import db
from pipeline.logsetup import get_logger

log = get_logger("features")

FEATURES_NPZ = config.DERIVED_DIR / "features.npz"
IDS_JSON = config.DERIVED_DIR / "album_ids.json"


def build_idf(conn, vocab: list[str]) -> np.ndarray:
    rows = conn.execute("SELECT tag, reach FROM tag_global").fetchall()
    reach = {r["tag"]: (r["reach"] or 0) for r in rows}
    max_reach = max([v for v in reach.values() if v > 0], default=1)
    idf = np.ones(len(vocab), dtype=np.float64)
    for i, tag in enumerate(vocab):
        df = reach.get(tag, 0)
        # reach<=0 (unknown/failed global fetch) → neutral weight, don't amplify.
        idf[i] = np.log(max_reach / df) if df > 0 else 1.0
    # Floor at 0 so a tag as common as the reference doesn't zero out.
    return np.clip(idf, 0.0, None)


def main() -> None:
    conn = db.connect()
    pv = config.PIPELINE_VERSION

    albums = conn.execute(
        "SELECT id, year FROM albums WHERE status = 'ok' ORDER BY id"
    ).fetchall()
    ids = [a["id"] for a in albums]
    years = np.array([a["year"] if a["year"] is not None else np.nan for a in albums], dtype=np.float64)
    idx = {aid: i for i, aid in enumerate(ids)}

    tag_rows = conn.execute(
        "SELECT album_id, tag, weight FROM album_tags WHERE pipeline_version = ?", (pv,)
    ).fetchall()
    vocab = sorted({r["tag"] for r in tag_rows})
    vpos = {t: j for j, t in enumerate(vocab)}

    m_raw = np.zeros((len(ids), len(vocab)), dtype=np.float64)
    for r in tag_rows:
        if r["album_id"] in idx:                      # skip tags for non-ok albums
            m_raw[idx[r["album_id"]], vpos[r["tag"]]] = r["weight"]

    idf = build_idf(conn, vocab)
    m_idf = m_raw * idf[np.newaxis, :]

    np.savez(
        FEATURES_NPZ,
        ids=np.array(ids, dtype=object),
        vocab=np.array(vocab, dtype=object),
        years=years,
        m_raw=m_raw,
        m_idf=m_idf,
        idf=idf,
    )
    IDS_JSON.write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")

    n_year = int(np.sum(~np.isnan(years)))
    log.info("features: %d albums × %d tags; %d/%d have year → %s",
             len(ids), len(vocab), n_year, len(ids), FEATURES_NPZ.name)
    conn.close()


if __name__ == "__main__":
    main()
