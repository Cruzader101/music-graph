"""Unit tests for identity.normalize / album_id (ADR-007 mandates testing the
suffix stripping — this is the primary key of the whole system).

Run: python -m pytest tests/  (or: python tests/test_identity.py)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.identity import album_id, normalize, strip_editions


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_reissues_collapse():
    base = album_id("My Bloody Valentine", "Loveless")
    for variant in [
        "Loveless (Remastered 2021)",
        "Loveless (Deluxe Edition)",
        "Loveless (Remastered)",
        "Loveless [2018 Remaster]",
        "Loveless - Deluxe Edition",
        "Loveless (Expanded Edition)",
    ]:
        check(album_id("My Bloody Valentine", variant) == base,
              f"{variant!r} should collapse to Loveless, got {album_id('MBV', variant)!r}")


def test_diacritics_and_case():
    check(normalize("Sigur Rós") == normalize("sigur ros"), "diacritics not stripped")
    check(normalize("The BEATLES") == "the beatles", "case not normalized")


def test_punctuation_and_whitespace():
    check(normalize("good kid, m.A.A.d city") == "good kid m a a d city", "punct")
    check(normalize("  Spirit   of  Eden ") == "spirit of eden", "whitespace collapse")


def test_strip_editions_repeated():
    check(strip_editions("Loveless (Deluxe) (Remastered 2021)") == "Loveless",
          "repeated suffix strip failed")


def test_non_edition_parens_preserved():
    # A parenthetical that is NOT an edition marker must survive (e.g. Sigur Rós '()').
    check("(" in strip_editions("Album (Live at Wembley)") or
          strip_editions("Album (Live at Wembley)") == "Album (Live at Wembley)",
          "non-edition paren wrongly stripped")


def test_id_shape():
    nid = album_id("Slowdive", "Souvlaki")
    check("␟" in nid, "separator missing")
    check(nid == "slowdive␟souvlaki", f"unexpected id {nid!r}")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} passed")
