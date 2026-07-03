# ADR-003 — Tag filtering by blacklist + IDF, reversing the whitelist decision

**Status:** Accepted (2026-07-02) — **supersedes** the original whitelist decision in
`music-project.md`.

## Context
The original plan filtered genre tags with a **whitelist** (`data/genre_whitelist.txt`):
a tag counts only if it's on the list. That decision predates the decision to apply **IDF**
(inverse document frequency, ADR-005) to the tag vectors.

A whitelist was doing two jobs at once:
1. Remove **junk** tags (`seen live`, `albums i own`, bare decades).
2. Suppress **over-common, low-signal** tags (`rock`, `indie`, `alternative`).

IDF now does job (2) automatically and continuously, using Last.fm global tag frequencies —
no list to maintain. That leaves the whitelist doing only job (1), which is a **blacklist's**
job (deny known junk, allow everything else).

Worse, on a *taste-curated* corpus a strict allow-list actively harms quality: niche-but-real
subgenres (`slowcore`, `third stream`, `shoegaze revival`) that the curator forgets to list are
silently dropped — manufacturing the exact "albums with <2 genre tags" problem the
data-audit-agent exists to catch. On a curated set the long tail of niche tags is often the
*most discriminating* signal, not noise.

## Decision
- Replace the whitelist with a **blacklist**: `data/genre_blacklist.txt` (git-tracked, plain
  text, one per line). A tag counts **unless** it's on the blacklist.
- Blacklist targets **rare, idiosyncratic junk** (personal-collection tags, bare years/decades)
  — the case IDF does *not* handle, because a rare junk tag gets *high* IDF and would be
  amplified rather than suppressed.
- **IDF handles common-generic tags**; the two mechanisms cover different halves of the problem.

## Consequences
- Niche subgenres survive as signal → better clustering on a curated corpus.
- Coverage improves; fewer manufactured sparse nodes.
- Ongoing curation shifts from "enumerate every valid genre" (unbounded) to "add junk as spotted"
  (small, bounded).
- **Doc debt paid:** `music-project.md` updated to reference the blacklist.
- data-audit-agent's "junk tag leakage" metric becomes the feedback loop that grows the blacklist.

## Amendment (2026-07-03) — filtering refinements from scaling 40 → 250

Scaling surfaced that a plain-text blacklist alone is the wrong tool for *unbounded junk
families*. The filtering in `pipeline/clean.py` was extended (still blacklist-first in spirit —
deny known junk, allow everything else):

- **Tag normalization before filtering:** hyphen/underscore/slash → space, so `hip-hop` ≡
  `hip hop` and `post-rock` ≡ `post rock`. Last.fm ships both variants; left split they fragment
  a cluster's cosine dimensions *and* its community color. (Affects `sim_genre`, so noted here
  rather than in ADR-007, which governs the album *key*, not tag strings.)
- **Pattern-killed junk families** (regex, not enumeration): `^best…` (best of YEAR / best albums
  ever / best new reissues), `…albums you must hear…`, trailing `… records` (labels), `vinyl`,
  and any tag > 45 chars (personal-narrative tags). Bare years/decades already handled.
- **The blacklist file now targets only fixed-string junk** (specific labels, `where is my bong`,
  rating words); the *families* live as patterns. `tools/audit.py` (the built coverage audit,
  roadmap #2) is the feedback loop: its junk-leakage report is where new patterns/entries come
  from. At 250 albums this drove leakage to a single legitimate borderline tag (`field
  recordings`).

Sibling class (identity, not filtering): several albums returned **junk-only or empty** top-tags
because the source *title/artist string missed Last.fm's canonical page* (Kendrick, Sly, Eno, GZA,
Art Blakey, Smashing Pumpkins). Fix is a curated title in `data/albums.csv`; see ADR-007.
