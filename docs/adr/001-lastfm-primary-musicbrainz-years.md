# ADR-001 — Last.fm primary source; MusicBrainz for release years only

**Status:** Accepted (formalized 2026-07-02; implicit since project start)

## Context
The graph needs two data inputs per album: genre/vibe tags (for `sim_genre`) and a
release year (for `sim_year`). Candidate sources were Last.fm, MusicBrainz, Spotify,
and Wikipedia.

- Spotify's audio-features endpoint has been dead for new apps since late 2024.
- Last.fm has rich, weighted, user-generated tags but deprecated/spotty release dates.
- MusicBrainz has structured, reliable `first-release-date` on release-groups but weaker
  tag data.
- Wikipedia year data means parsing infoboxes — fragile vs. MusicBrainz's structured field.

## Decision
- **Last.fm is the primary source**: one client, one cache path, one auth. It supplies
  tags (`album.getTopTags`), album metadata (`album.getInfo`), and global tag frequencies
  (`tag.getInfo`, see ADR for IDF).
- **MusicBrainz is used for release years only** — never for anything else without a new ADR.
- Year resolution order: Last.fm year if present → MusicBrainz release-group search → else
  flagged unresolved (see ADR-006 for the conservative matching policy).

## Consequences
- Single dominant integration surface keeps rate-limiting, caching, and error handling simple.
- Year coverage depends on MusicBrainz match quality; unresolved years degrade gracefully
  (term dropped, weights renormalized) rather than blocking a node.
- Adding any new signal from MusicBrainz (or a new source entirely) requires a fresh ADR.
