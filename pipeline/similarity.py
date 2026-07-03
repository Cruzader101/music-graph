"""Stage 4 — similarity (the core). features.npz → per-axis edge similarities.

Computes, per album pair:
  sim_genre_{raw,idf}_{cosine,jaccard}   (ADR-005: dual metric × dual weighting)
  sim_year = exp(-Δyear² / 2σ²)          (null if either year missing → ADR-002)

Then applies the export contract (ADR-004): an edge is kept iff its peak axis
value ≥ EXPORT_FLOOR, OR it is within either endpoint's TOP_K_GUARANTEE
neighbors by peak axis — so client-side kNN/mutual-kNN are never starved.
Vectorized with numpy/scipy (music-project.md perf rules). Writes the `edges` table.
Run: python -m pipeline.similarity
"""
from __future__ import annotations

import numpy as np

import config
from pipeline import db
from pipeline.features import FEATURES_NPZ
from pipeline.logsetup import get_logger

log = get_logger("similarity")


def cosine_matrix(m: np.ndarray) -> np.ndarray:
    """Row-wise cosine similarity via one normalized matmul (ADR-005)."""
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0  # zero-vector rows → zero similarity, no divide-by-0
    unit = m / norms
    sim = unit @ unit.T
    return np.clip(sim, 0.0, 1.0)


def weighted_jaccard_matrix(m: np.ndarray) -> np.ndarray:
    """Weighted Jaccard Σmin/Σmax per pair (ADR-005). O(n²·V) — the costly axis;
    profile this first if O(n²) bites at scale (ADR-005 consequence)."""
    n = m.shape[0]
    sim = np.zeros((n, n), dtype=np.float64)
    row_sums = m.sum(axis=1)
    for i in range(n):
        mins = np.minimum(m[i], m).sum(axis=1)           # Σ min over all j at once
        maxs = (row_sums[i] + row_sums - mins)           # Σmax = Σa + Σb - Σmin
        with np.errstate(divide="ignore", invalid="ignore"):
            sim[i] = np.where(maxs > 0, mins / maxs, 0.0)
    return np.clip(sim, 0.0, 1.0)


def year_matrix(years: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian year kernel; NaN where either album's year is missing (→ null)."""
    diff = years[:, None] - years[None, :]
    sim = np.exp(-(diff ** 2) / (2.0 * sigma ** 2))
    missing = np.isnan(years)
    sim[missing, :] = np.nan
    sim[:, missing] = np.nan
    return sim


def main() -> None:
    data = np.load(FEATURES_NPZ, allow_pickle=True)
    ids = list(data["ids"])
    n = len(ids)
    log.info("computing similarities for %d albums", n)

    raw_cos = cosine_matrix(data["m_raw"])
    idf_cos = cosine_matrix(data["m_idf"])
    raw_jac = weighted_jaccard_matrix(data["m_raw"])
    idf_jac = weighted_jaccard_matrix(data["m_idf"])
    year = year_matrix(data["years"], config.SIGMA_YEAR)

    genre_axes = np.stack([raw_cos, raw_jac, idf_cos, idf_jac])   # (4, n, n)
    peak = genre_axes.max(axis=0)                                 # best genre axis per pair
    year_peak = np.nan_to_num(year, nan=0.0)
    peak = np.maximum(peak, year_peak)
    np.fill_diagonal(peak, 0.0)

    # Export contract (ADR-004): floor OR either endpoint's top-K by peak.
    keep = peak >= config.EXPORT_FLOOR
    k = min(config.TOP_K_GUARANTEE, n - 1)
    for i in range(n):
        top = np.argpartition(peak[i], -k)[-k:]
        keep[i, top] = True
        keep[top, i] = True
    np.fill_diagonal(keep, False)

    conn = db.connect()
    db.init_db(conn)
    conn.execute("DELETE FROM edges WHERE pipeline_version = ?", (config.PIPELINE_VERSION,))

    def r(x):  # round / null helper
        return None if np.isnan(x) else round(float(x), 4)

    n_edges = 0
    for i in range(n):
        for j in range(i + 1, n):
            if not (keep[i, j] or keep[j, i]):
                continue
            conn.execute(
                """INSERT OR REPLACE INTO edges
                   (source, target, sim_genre_raw_cosine, sim_genre_raw_jaccard,
                    sim_genre_idf_cosine, sim_genre_idf_jaccard, sim_year, pipeline_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (ids[i], ids[j], r(raw_cos[i, j]), r(raw_jac[i, j]),
                 r(idf_cos[i, j]), r(idf_jac[i, j]), r(year[i, j]), config.PIPELINE_VERSION),
            )
            n_edges += 1
    conn.commit()

    density = n_edges / (n * (n - 1) / 2) if n > 1 else 0
    log.info("similarity done: %d edges (%.1f%% of complete graph)", n_edges, 100 * density)
    conn.close()


if __name__ == "__main__":
    main()
