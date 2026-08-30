"""M-4b C0: the Env comonad and the ConditionEnvelope tiering.

The three comonad laws are swept over representative (envelope, value) pairs with
context-*reading* functions (so `extend` is non-trivial), and every honesty gate on the
envelope is isolated: the unknown default is the only unsourced envelope, a declared
condition demands a provenance, and the status can never reach the certified lane.
"""

import math

import pytest

from smartchem.conditions import (
    ConditionEnvelope,
    Conditioned,
    Interval,
    condition,
    duplicate,
    extend,
    extract,
    unconditioned,
)
from smartchem.contracts import EvidenceStatus, canonical_digest
from smartchem.decompiler import DecompositionEdge, Formula

UNKNOWN = ConditionEnvelope.unknown()
AQUEOUS = ConditionEnvelope(medium="aqueous", status=EvidenceStatus.EXPERIMENTAL, provenance="lit:acetylation")
HOT_CAT = ConditionEnvelope(
    temperature=Interval(300, 400, "K"),
    catalysts=("H2SO4",),
    status=EvidenceStatus.EXPERIMENTAL,
    provenance="lit:hydrolysis",
)
ENVELOPES = [UNKNOWN, AQUEOUS, HOT_CAT]
VALUES = [0, 7, -3, 42]


# two functions that actually READ the context, so extend is not the identity in disguise
def _f(w):
    return w.extract() * 2 + len(w.envelope.catalysts)


def _g(w):
    return w.extract() + (100 if w.envelope.is_declared else 0)


class TestComonadLaws:
    @pytest.mark.parametrize("env", ENVELOPES)
    @pytest.mark.parametrize("v", VALUES)
    def test_left_identity_extend_extract_is_id(self, env, v):
        w = condition(v, env)
        assert w.extend(extract) == w

    @pytest.mark.parametrize("env", ENVELOPES)
    @pytest.mark.parametrize("v", VALUES)
    def test_right_identity_extract_after_extend(self, env, v):
        w = condition(v, env)
        assert extract(extend(_f, w)) == _f(w)  # point-free extract . extend f = f

    @pytest.mark.parametrize("env", ENVELOPES)
    @pytest.mark.parametrize("v", VALUES)
    def test_associativity_extend_f_after_extend_g(self, env, v):
        w = condition(v, env)
        assert w.extend(_g).extend(_f) == w.extend(lambda x: _f(x.extend(_g)))

    @pytest.mark.parametrize("env", ENVELOPES)
    @pytest.mark.parametrize("v", VALUES)
    def test_extract_after_duplicate_is_id(self, env, v):
        w = condition(v, env)
        assert extract(duplicate(w)) == w

    @pytest.mark.parametrize("env", ENVELOPES)
    @pytest.mark.parametrize("v", VALUES)
    def test_map_extract_after_duplicate_is_id(self, env, v):
        w = condition(v, env)
        assert duplicate(w).map(lambda inner: inner.extract()) == w

    @pytest.mark.parametrize("env", ENVELOPES)
    @pytest.mark.parametrize("v", VALUES)
    def test_coassociativity_of_duplicate(self, env, v):
        w = condition(v, env)
        assert duplicate(duplicate(w)) == duplicate(w).map(lambda inner: inner.duplicate())


class TestInterval:
    def test_bounds_must_be_ordered(self):
        with pytest.raises(ValueError):
            Interval(5, 1, "K")

    def test_bounds_must_be_finite(self):
        with pytest.raises(ValueError):
            Interval(0, math.inf, "K")

    def test_unit_required(self):
        with pytest.raises(ValueError):
            Interval(0, 1, "")

    def test_int_and_float_bounds_share_a_digest(self):
        assert Interval(0, 100, "K").digest == Interval(0.0, 100.0, "K").digest


class TestConditionEnvelopeTiering:
    def test_unknown_is_the_only_unsourced_envelope(self):
        u = ConditionEnvelope.unknown()
        assert u.status is EvidenceStatus.UNSUPPORTED and not u.is_declared

    def test_content_without_a_raised_status_is_refused(self):
        # you cannot state a condition while claiming UNSUPPORTED -- that is a fabricated envelope
        with pytest.raises(ValueError, match="UNSUPPORTED"):
            ConditionEnvelope(medium="aqueous")

    def test_declared_condition_without_provenance_is_refused(self):
        with pytest.raises(ValueError, match="fabricated"):
            ConditionEnvelope(medium="aqueous", status=EvidenceStatus.EXPERIMENTAL, provenance="")

    def test_status_is_capped_below_the_certified_lane(self):
        with pytest.raises(ValueError, match="certified-lane"):
            ConditionEnvelope(
                medium="aqueous",
                status=EvidenceStatus.VALIDATED_WITHIN_REGIME,
                provenance="lit",
            )

    def test_a_sourced_declared_envelope_is_accepted(self):
        e = ConditionEnvelope(
            temperature=Interval(370, 380, "K"),
            medium="aqueous",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance="lit:paracetamol-hydrolysis",
        )
        assert e.is_declared

    def test_catalyst_order_and_duplicates_do_not_move_the_digest(self):
        a = ConditionEnvelope(catalysts=("B", "A", "A"), status=EvidenceStatus.EXPERIMENTAL, provenance="p")
        b = ConditionEnvelope(catalysts=("A", "B"), status=EvidenceStatus.EXPERIMENTAL, provenance="p")
        assert a.digest == b.digest


class TestConditionedOverDecompositionEdges:
    def test_wraps_an_edge_and_is_a_first_class_digestible(self):
        edge = DecompositionEdge(
            Formula.parse("H2O"), 1, ((Formula.bucket("H"), 2), (Formula.bucket("O"), 1))
        )
        w = unconditioned(edge)
        assert w.extract() is edge
        assert not w.envelope.is_declared  # the honest default: no conditions claimed yet
        assert w.digest == canonical_digest(w)
        assert type(w) is Conditioned
