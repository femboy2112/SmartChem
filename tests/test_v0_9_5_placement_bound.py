"""0.9.5 A13 (parent) -- the resonance placement search's AGGREGATE work bound.

Each complete placement is canonicalised, and each canonical() call is bounded per call (A13's call ceiling), so a large
symmetric pi-system spelled in explicit Kekule form was bounded only by matchings x per-call ceiling on the front door,
where no load budget applies. ``smiles._MAX_PLACEMENT_SEARCH_WORK`` bounds the search's COLD work (DFS nodes plus every
placement's canonicalisation), read through ``verification.canonical_work_frame`` -- a frame that is transparent to the
load accounting and identical cold or warm. Honest maximum and margin: ``experiments/v0_9_5_amplifier_bound.py
--placement``.
"""
from __future__ import annotations

import pytest

import smartchem.smiles as sm
from smartchem import verification as ver
from smartchem.category import Molecule
from smartchem.smiles import SmilesError, parse_smiles

NAPHTHALENE_KEKULE = "C1=CC=C2C=CC=CC2=C1"   # three placements


def _search_total(text: str) -> int:
    """The placement search's own frame total for one parse (its last search)."""
    seen: list = []
    live = sm.canonical_work_frame

    from contextlib import contextmanager

    @contextmanager
    def spy():
        with live() as frame:
            seen.append(frame)
            yield frame
    sm.canonical_work_frame = spy
    try:
        parse_smiles(text)
    finally:
        sm.canonical_work_frame = live
    return seen[-1].total


def test_the_aggregate_ceiling_refuses_typed(monkeypatch):
    monkeypatch.setattr(sm, "_MAX_PLACEMENT_SEARCH_WORK", 10)
    with pytest.raises(SmilesError, match="placement search exceeded 10 units of canonicalisation work"):
        parse_smiles(NAPHTHALENE_KEKULE)


def test_honest_inputs_are_far_under_the_ceiling():
    total = _search_total(NAPHTHALENE_KEKULE)
    assert 0 < total < sm._MAX_PLACEMENT_SEARCH_WORK // 1000


def test_the_search_total_is_cache_independent():
    """Cold and warm read the same total: a canonical() hit hands its closure's cold work up to the frame."""
    Molecule.canonical.cache_clear()
    cold = _search_total(NAPHTHALENE_KEKULE)
    warm = _search_total(NAPHTHALENE_KEKULE)        # every placement's canonical() is now a process-cache hit
    assert cold == warm > 0


def test_the_frame_is_transparent_to_an_enclosing_frame():
    """Broken: the frame keeps its work -- an enclosing cached computation records less than it cost (cold != warm)."""
    Molecule.canonical.cache_clear()
    inner = _search_total(NAPHTHALENE_KEKULE)
    Molecule.canonical.cache_clear()
    with ver._recording_canonical_work() as outer:
        parse_smiles(NAPHTHALENE_KEKULE)
    assert outer.total >= inner > 0
