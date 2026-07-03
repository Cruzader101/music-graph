"""Offline smoke test for stages 3-5 (features → similarity → export).

Seeds a TEMP cache.db with synthetic albums whose tag vectors form 3 obvious
clusters + one A/B bridge + one year-less album, runs the real feature/
similarity/export code, then asserts the export-schema invariants AND that
intra-cluster cosine > inter-cluster. Proves the downstream pipeline + writes a
renderable placeholder frontend/graph.json (overwritten by the real run).

Run: python -m tools.smoke
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import config

# Redirect the DB to a temp file BEFORE any stage connects, so we never pollute
# the real cache.db (which the live fetch will build).
_tmp = Path(os.environ.get("SMOKE_JOB_DIR", tempfile.gettempdir())) / "smoke_cache.db"
_tmp.parent.mkdir(parents=True, exist_ok=True)
if _tmp.exists():
    _tmp.unlink()
config.DB_PATH = _tmp

from pipeline import db, features, similarity, export  # noqa: E402  (after DB override)

PV = config.PIPELINE_VERSION

# cluster label -> (base tag vector, member albums, year)
CLUSTERS = {
    "shoegaze":    ({"shoegaze": 100, "dream pop": 70, "noise pop": 40}, 4, 1991),
    "black metal": ({"black metal": 100, "atmospheric black metal": 60}, 4, 1994),
    "jazz":        ({"jazz": 100, "hard bop": 55, "modal jazz": 45}, 4, 1959),
}
GLOBAL_REACH = {  # synthetic Last.fm reach (df for IDF); common vs niche
    "shoegaze": 90000, "dream pop": 120000, "noise pop": 20000,
    "black metal": 150000, "atmospheric black metal": 8000,
    "jazz": 400000, "hard bop": 15000, "modal jazz": 9000,
}


def seed(conn):
    conn.execute("DELETE FROM albums"); conn.execute("DELETE FROM album_tags")
    conn.execute("DELETE FROM tag_global"); conn.execute("DELETE FROM edges")
    idx = 0
    for label, (vec, count, year) in CLUSTERS.items():
        for i in range(count):
            aid = f"{label}␟ album {i}"
            # last album of each cluster has no year (exercise null year path)
            y = None if i == count - 1 else year + i
            conn.execute(
                "INSERT INTO albums (id, artist, album, mbid, year, year_status, status, fetched_at)"
                " VALUES (?, ?, ?, NULL, ?, ?, 'ok', '2026-07-02T00:00:00Z')",
                (aid, f"{label.title()} Artist {i}", f"{label.title()} Album {i}",
                 y, "resolved" if y else "unresolved"),
            )
            for tag, w in vec.items():
                jitter = 1 + (i - 1) * 3  # small per-album variation
                conn.execute(
                    "INSERT INTO album_tags (album_id, tag, weight, pipeline_version) VALUES (?,?,?,?)",
                    (aid, tag, max(w + jitter, 1), PV),
                )
            idx += 1
    # bridge album: half shoegaze, half black metal (blackgaze)
    bid = "blackgaze␟ bridge"
    conn.execute(
        "INSERT INTO albums (id, artist, album, mbid, year, year_status, status, fetched_at)"
        " VALUES (?, 'Bridge Artist', 'Bridge Album', NULL, 2013, 'resolved', 'ok', '2026-07-02T00:00:00Z')",
        (bid,))
    for tag, w in {"shoegaze": 60, "black metal": 60, "atmospheric black metal": 30}.items():
        conn.execute("INSERT INTO album_tags (album_id, tag, weight, pipeline_version) VALUES (?,?,?,?)",
                     (bid, tag, w, PV))
    for tag, reach in GLOBAL_REACH.items():
        conn.execute("INSERT INTO tag_global (tag, reach, taggings, fetched_at) VALUES (?,?,?,?)",
                     (tag, reach, reach * 3, "2026-07-02T00:00:00Z"))
    conn.commit()


def validate(graph) -> list[str]:
    errs = []
    meta = graph["meta"]
    for key in ("pipeline_version", "generated", "album_count", "defaults",
                "export_floor", "top_k_guarantee", "genre_metric_default",
                "genre_weighting_default", "draw_mode_default"):
        if key not in meta:
            errs.append(f"meta missing {key}")
    ids = {n["id"] for n in graph["nodes"]}
    for n in graph["nodes"]:
        for key in ("id", "artist", "album", "dominant_tag", "year", "year_status"):
            if key not in n:
                errs.append(f"node {n.get('id')} missing {key}")
    for e in graph["edges"]:
        if e["source"] not in ids or e["target"] not in ids:
            errs.append(f"edge endpoint missing: {e['source']}→{e['target']}")
        for f in ("sim_genre_raw_cosine", "sim_genre_raw_jaccard",
                  "sim_genre_idf_cosine", "sim_genre_idf_jaccard"):
            v = e[f]
            if v is not None and not (0 <= v <= 1):
                errs.append(f"{f}={v} out of [0,1]")
        if e["sim_year"] is not None and not (0 <= e["sim_year"] <= 1):
            errs.append(f"sim_year={e['sim_year']} out of [0,1]")
    return errs


def cluster_separation(graph) -> tuple[float, float]:
    """Mean intra-cluster vs inter-cluster raw cosine (bridge excluded)."""
    def clab(nid): return nid.split("␟")[0]
    intra, inter = [], []
    for e in graph["edges"]:
        c = e["sim_genre_raw_cosine"]
        if c is None or "blackgaze" in (e["source"] + e["target"]):
            continue
        (intra if clab(e["source"]) == clab(e["target"]) else inter).append(c)
    mi = sum(intra) / len(intra) if intra else 0
    mo = sum(inter) / len(inter) if inter else 0
    return mi, mo


def main():
    conn = db.connect(); db.init_db(conn); seed(conn); conn.close()
    features.main(); similarity.main(); export.main()

    graph = json.loads(config.GRAPH_JSON.read_text(encoding="utf-8"))
    errs = validate(graph)
    mi, mo = cluster_separation(graph)

    print(f"\nnodes={len(graph['nodes'])} edges={len(graph['edges'])}")
    print(f"mean intra-cluster cosine={mi:.3f}  inter-cluster={mo:.3f}")
    bridge = [e for e in graph["edges"] if "blackgaze" in e["source"] or "blackgaze" in e["target"]]
    print(f"bridge album edges={len(bridge)} (should connect shoegaze <-> black metal)")
    yearless = [n for n in graph["nodes"] if n["year"] is None]
    print(f"year-less nodes={len(yearless)} (null sim_year path exercised)")

    if errs:
        print("\nSCHEMA ERRORS:"); [print("  -", e) for e in errs]; sys.exit(1)
    if not (mi > mo):
        print("\nFAIL: clusters not separated (intra <= inter)"); sys.exit(1)
    print("\nSMOKE PASS — schema valid, clusters separated. "
          "frontend/graph.json is synthetic placeholder; real `python run.py` overwrites it.")


if __name__ == "__main__":
    main()
