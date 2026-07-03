"""Stage 5 — export. albums + edges + album_tags → frontend/graph.json.

Emits EXACTLY the schema in docs/export-schema.md (ADR-008) — the one contract
the frontend consumes. Node color comes from dominant_tag (highest-weight
post-blacklist tag). Reads only cache.db; writes only the JSON.
Run: python -m pipeline.export
"""
from __future__ import annotations

import json

import config
from pipeline import db
from pipeline.logsetup import get_logger

log = get_logger("export")


def dominant_tags(conn) -> dict[str, str]:
    """Highest-weight surviving tag per album → node color key."""
    rows = conn.execute(
        """SELECT album_id, tag FROM album_tags t
           WHERE pipeline_version = ?
             AND weight = (SELECT MAX(weight) FROM album_tags t2
                           WHERE t2.album_id = t.album_id AND t2.pipeline_version = t.pipeline_version)
           GROUP BY album_id""",
        (config.PIPELINE_VERSION,),
    ).fetchall()
    return {r["album_id"]: r["tag"] for r in rows}


def build_meta(conn) -> dict:
    album_count = conn.execute("SELECT COUNT(*) c FROM albums WHERE status='ok'").fetchone()["c"]
    return {
        "pipeline_version": config.PIPELINE_VERSION,
        "generated": db.utcnow(),
        "album_count": album_count,
        "defaults": config.DEFAULTS,
        "export_floor": config.EXPORT_FLOOR,
        "top_k_guarantee": config.TOP_K_GUARANTEE,
        "genre_metric_default": config.GENRE_METRIC_DEFAULT,
        "genre_weighting_default": config.GENRE_WEIGHTING_DEFAULT,
        "draw_mode_default": config.DRAW_MODE_DEFAULT,
    }


def build_nodes(conn, dom: dict[str, str]) -> list[dict]:
    rows = conn.execute(
        "SELECT id, artist, album, year, year_status FROM albums WHERE status='ok' ORDER BY id"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "artist": r["artist"],
            "album": r["album"],
            "dominant_tag": dom.get(r["id"], "unknown"),
            "year": r["year"],
            "year_status": r["year_status"],
        }
        for r in rows
    ]


def build_edges(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT source, target, sim_genre_raw_cosine, sim_genre_raw_jaccard,
                  sim_genre_idf_cosine, sim_genre_idf_jaccard, sim_year
           FROM edges WHERE pipeline_version = ?""",
        (config.PIPELINE_VERSION,),
    ).fetchall()
    return [
        {
            "source": r["source"],
            "target": r["target"],
            "sim_genre_raw_cosine": r["sim_genre_raw_cosine"],
            "sim_genre_raw_jaccard": r["sim_genre_raw_jaccard"],
            "sim_genre_idf_cosine": r["sim_genre_idf_cosine"],
            "sim_genre_idf_jaccard": r["sim_genre_idf_jaccard"],
            "sim_year": r["sim_year"],
        }
        for r in rows
    ]


def main() -> None:
    conn = db.connect()
    dom = dominant_tags(conn)
    graph = {"meta": build_meta(conn), "nodes": build_nodes(conn, dom), "edges": build_edges(conn)}

    node_ids = {nd["id"] for nd in graph["nodes"]}
    dangling = [e for e in graph["edges"] if e["source"] not in node_ids or e["target"] not in node_ids]
    if dangling:
        raise SystemExit(f"invariant violated: {len(dangling)} edges reference missing nodes")

    config.GRAPH_JSON.write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("export done: %d nodes, %d edges → %s",
             len(graph["nodes"]), len(graph["edges"]), config.GRAPH_JSON)
    conn.close()


if __name__ == "__main__":
    main()
