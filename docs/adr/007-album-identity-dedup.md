# ADR-007 — Album identity and dedup key

**Status:** Accepted (2026-07-02)

## Context
Album identity is the primary key of the whole system: the graph node ID, the `cache.db` key,
and the join between Last.fm and MusicBrainz. Raw source strings collide and duplicate:
`Loveless`, `Loveless (Remastered 2021)`, `Loveless (Deluxe Edition)` are one album as three
strings; `The Beatles` vs `Beatles`; capitalization; unicode. If these don't collapse, a
100-album set renders as 118 phantom-duplicate nodes clustered on top of each other — poisoning
the "does it feel right" test the slice exists for.

MBID-required identity was rejected: albums MusicBrainz can't confidently match would be dropped,
violating "never silently drop an album," and it puts MB resolution on the critical path for every
node rather than just for years.

## Decision
- **Canonical key = `normalize(artist) ␟ normalize(album)`** where `normalize` = lowercase, strip
  diacritics, drop reissue/edition suffixes (`remaster(ed)`, `deluxe`, `mono`, `expanded`,
  `anniversary`, `... edition`, trailing parenthetical years), collapse whitespace.
- **Store Last.fm's `mbid` when present** as a secondary field — a merge hint and validation aid,
  not the primary key.
- Reissues/remasters collapse to one node; nothing is dropped.

## Consequences
- On a curated ~100 where the operator controls input strings, normalization is sufficient.
- The normalization rule is a small, testable pure function — unit-test the suffix stripping.
- The normalized artist string is also what's fed to MusicBrainz year search (ADR-006), so
  normalization quality affects match quality — one function, two consumers.
- If the corpus later grows to an uncontrolled library, revisit (fuzzy merge / MBID reconciliation)
  under a new ADR.

## Notes from scaling 40 → 250 (2026-07-03)

The "operator controls input strings" assumption held, but with a recurring wrinkle: the CSV
string must match **Last.fm's canonical page**, or `album.getTopTags` returns junk-only or empty
tags (a sparse/isolated node), independent of the identity key. Observed on Kendrick (`good kid,
m.A.A.d city` needs the comma), Sly (`Sly & The Family Stone`, ampersand not "and"), Eno
(`Ambient 1: Music for Airports`, colon), GZA (`GZA/Genius`), Art Blakey (drop "& the Jazz
Messengers"), Smashing Pumpkins (leading "The"). `tools/audit.py`'s sparse-album report is how
these are caught; the fix is a curated title, not a code change.

Consequence for identity: a title fix can **change the normalized node id** (e.g. `Sly and…` →
`Sly &…`). So `data/albums.csv` is the **source of truth** and `pipeline/fetch.py` now **prunes**
albums (and their tags) no longer present in the CSV — this is deliberate sync with the input
list, distinct from the "never silently drop a *failed fetch*" rule.
