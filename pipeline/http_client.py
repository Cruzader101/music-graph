"""The one HTTP wrapper every API call goes through (music-project.md).

Responsibilities: per-source rate limiting, verbatim cache read/write, retries
with exponential backoff, and a structured failure row in fetch_errors.jsonl.
Callers (lastfm, musicbrainz) never touch requests directly.
"""
from __future__ import annotations

import time

import requests

import config
from pipeline import db
from pipeline.logsetup import get_logger, log_fetch_error

log = get_logger("http")

# Simple per-source spacing to respect rate limits (last-request timestamps).
_last_request: dict[str, float] = {}


def _throttle(source: str, rps: float) -> None:
    min_gap = 1.0 / rps
    now = time.monotonic()
    last = _last_request.get(source, 0.0)
    wait = min_gap - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[source] = time.monotonic()


def get_json(
    conn,
    source: str,
    endpoint: str,
    url: str,
    params: dict,
    rps: float,
    headers: dict | None = None,
) -> dict | None:
    """Return parsed JSON for a request, using cache when present.

    `params` is the cache identity (must exclude the API key). `url` is the
    actual endpoint hit. Returns None on unrecoverable failure (already logged
    and, for corpus items, recorded as a failed row by the caller).
    """
    key = db.cache_key(source, endpoint, params)
    cached = db.cache_get(conn, key)
    if cached is not None and cached["status_code"] == 200 and cached["body"]:
        log.debug("cache hit %s", key)
        return _parse(cached["body"])

    req_params = dict(params)
    if source == "lastfm":
        req_params["api_key"] = config.LASTFM_API_KEY
        req_params["format"] = "json"

    body = None
    status = None
    for attempt in range(config.MAX_RETRIES):
        _throttle(source, rps)
        try:
            resp = requests.get(
                url,
                params=req_params,
                headers={"User-Agent": config.USER_AGENT, **(headers or {})},
                timeout=config.REQUEST_TIMEOUT_S,
            )
            status, body = resp.status_code, resp.text
        except requests.RequestException as exc:
            status, body = None, f"{type(exc).__name__}: {exc}"
            log.warning("%s %s network error (attempt %d): %s", source, endpoint, attempt, exc)
            time.sleep(config.RETRY_BACKOFF_BASE_S * (2 ** attempt))
            continue

        if status == 200:
            db.cache_put(conn, key, source, endpoint, params, status, body)
            return _parse(body)

        # 429 / 5xx are retryable; 4xx (except 429) are not.
        if status == 429 or 500 <= status < 600:
            log.warning("%s %s HTTP %d (attempt %d), backing off", source, endpoint, status, attempt)
            time.sleep(config.RETRY_BACKOFF_BASE_S * (2 ** attempt))
            continue
        break  # non-retryable

    log.error("%s %s failed: status=%s", source, endpoint, status)
    log_fetch_error(endpoint, params, status, body or "")
    # Cache the failure too, so a re-run doesn't hammer a known-bad request.
    db.cache_put(conn, key, source, endpoint, params, status, body)
    return None


def _parse(body: str) -> dict | None:
    import json
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None
