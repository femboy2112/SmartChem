"""0.9.5 A13 (parent) -- a wire molecule past the canonicaliser's atom ceiling is refused BEFORE its graph is built.

No identity can be established past ``category._MAX_CANONICAL_ATOMS``, and building the graph first cost a linear digest
fallback over every atom (~85 us/atom; bounded only by the payload-node budget) before the step refused it. Both wire
decoders -- the service's molecule codec and the IR's witness graph codec -- refuse up front, in the refusal class.
"""
from __future__ import annotations

import time

import pytest

from smartchem import compilation_ir as cir
from smartchem import service as svc
from smartchem.category import _MAX_CANONICAL_ATOMS


def _star(n: int) -> dict:
    return {"atoms": ["C"] + ["H"] * (n - 1), "bonds": [[0, i, 1] for i in range(1, n)], "charge": 0, "state": "gas"}


def test_service_decoder_refuses_past_the_ceiling_before_construction():
    t = time.perf_counter()
    with pytest.raises(ValueError, match=r"over the canonicaliser's 1,024-atom ceiling; refused before construction"):
        svc._molecule_from_payload(_star(200_001))
    assert time.perf_counter() - t < 2.0


def test_ir_decoder_refuses_past_the_ceiling_before_construction():
    p = _star(_MAX_CANONICAL_ATOMS + 1)
    with pytest.raises(ValueError, match=r"IR graph payload carries 1,025 atoms"):
        cir._graph_from_payload((p["atoms"], [tuple(b) for b in p["bonds"]], 0, "gas"))


def test_at_the_ceiling_still_decodes():
    m = svc._molecule_from_payload(_star(_MAX_CANONICAL_ATOMS))
    assert len(m.atoms) == _MAX_CANONICAL_ATOMS
