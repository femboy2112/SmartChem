"""OPERATION XXVI, Packet F -- the pluggable coproduct-producer registry, salvaged onto main.

What this pins (and what it deliberately does NOT): the deferred branch generalised the single hard-wired
lactonization type-3 producer into a CLOSED, caller-order-independent registry.  That mechanism is what we
lifted; the dehydration producer that rode in with it was left on the table (invalid chemistry).  So these
tests exercise the registry's guarantees with lactonization as the only resident built-in, plus a sterile
no-op look-alike stood up ONLY inside a test's local known set -- never a second shipped producer.

The incisions under the knife:
* identity-CLOSED admission -- a producer not in :data:`KNOWN_COPRODUCT_PRODUCERS` is refused by identity;
* tuple + no-repeat validation -- a list is rejected; a repeated provider_id is rejected;
* ORDER-INDEPENDENCE of the grammar digest -- canonicalised before the search, so caller order cannot move it;
* BYTE-IDENTITY of the default path -- the default call's grammar digest reproduces the literal 1.6.0 tuple,
  so nobody downstream (receipts, replay, cli_json goldens) sees a bit move when the registry is unused.
"""
from __future__ import annotations

import pytest

from smartchem.contracts import canonical_digest
from smartchem.experiment import event_search
from smartchem.experiment.event_search import (
    DEFAULT_COPRODUCT_PRODUCERS,
    KNOWN_COPRODUCT_PRODUCERS,
    LACTONIZATION_PRODUCER,
    CoproductProducer,
    UnknownCoproductProducerError,
    search_event_routes,
)
from smartchem.lateral_rewrite import LATERAL_FAMILIES
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY, search_algebra_digest

TARGET = parse_smiles("CCO")                 # a small neutral target; the search terminates cheaply at max_depth=1
WATER = parse_smiles("O")
SEARCH_KW = dict(reagents=(WATER,), max_depth=1)


class _NoopEnum:
    """The record shape a producer's ``enumerate`` must return: no edges, scan exhaustive (nothing truncated)."""

    edges = ()
    exhaustive = True


def _noop_enumerate(target, *, budget):
    """A sterile look-alike enumeration -- contributes no type-3 edges, so it cannot change which routes survive;
    it exists only to prove the registry MECHANISM is order- and arity-agnostic, not to add chemistry."""
    return _NoopEnum()


# provider_id sorts BEFORE "lactonization-v1", so canonical-sort must reorder a caller who lists it second --
# that reordering is exactly what the order-independence pin needs to see cancel out.
FAKE_PRODUCER = CoproductProducer("aaa-fake-v1", _noop_enumerate)


# -- (a) identity-closed admission -------------------------------------------------------------------------------

def test_unregistered_producer_is_refused_by_identity():
    """A freshly built CoproductProducer -- even one reusing a built-in's provider_id -- is NOT in the closed set,
    so it is refused by object identity (the digest names code that actually shipped, never a caller's look-alike)."""
    impostor = CoproductProducer("lactonization-v1", LACTONIZATION_PRODUCER.enumerate)
    assert not any(impostor is k for k in KNOWN_COPRODUCT_PRODUCERS)   # same id, different object
    with pytest.raises(UnknownCoproductProducerError):
        search_event_routes(TARGET, coproduct_producers=(impostor,), **SEARCH_KW)
    with pytest.raises(UnknownCoproductProducerError):
        search_event_routes(TARGET, coproduct_producers=(FAKE_PRODUCER,), **SEARCH_KW)


# -- (b) tuple + no-repeat validation ----------------------------------------------------------------------------

def test_non_tuple_producers_rejected():
    """The parameter is a tuple of built-ins, not a list -- a mutable sequence is refused before the search runs."""
    with pytest.raises(TypeError):
        search_event_routes(TARGET, coproduct_producers=[LACTONIZATION_PRODUCER], **SEARCH_KW)


def test_repeated_producer_id_rejected():
    """Both entries ARE the built-in (identity passes), but a repeated provider_id is still refused: a producer may
    appear at most once, so the per-route coproduct budget is never double-charged against one grammar."""
    with pytest.raises(ValueError):
        search_event_routes(
            TARGET, coproduct_producers=(LACTONIZATION_PRODUCER, LACTONIZATION_PRODUCER), **SEARCH_KW
        )


# -- (c) order-independence of the grammar digest ----------------------------------------------------------------

def test_grammar_digest_is_order_independent(monkeypatch):
    """Caller order must not move the grammar digest.  With the fake temporarily admitted to a LOCAL known set,
    passing {lactonization, fake} in either order yields the SAME transform_grammar_digest -- the canonical sort
    (by provider_id) runs before the digest, so the ordering cancels."""
    monkeypatch.setattr(
        event_search, "KNOWN_COPRODUCT_PRODUCERS", (LACTONIZATION_PRODUCER, FAKE_PRODUCER)
    )
    forward = search_event_routes(
        TARGET, coproduct_producers=(LACTONIZATION_PRODUCER, FAKE_PRODUCER), **SEARCH_KW
    )
    reverse = search_event_routes(
        TARGET, coproduct_producers=(FAKE_PRODUCER, LACTONIZATION_PRODUCER), **SEARCH_KW
    )
    assert forward.receipt.transform_grammar_digest == reverse.receipt.transform_grammar_digest
    # and the multi-producer digest is NOT the default one -- the order-independence above is non-trivial.
    default = search_event_routes(TARGET, **SEARCH_KW)
    assert forward.receipt.transform_grammar_digest != default.receipt.transform_grammar_digest


def test_canonical_sort_key_is_provider_id():
    """The sort key itself, pinned directly: canonicalising by provider_id is what makes order irrelevant."""
    unsorted = (FAKE_PRODUCER, LACTONIZATION_PRODUCER)
    canonical = tuple(sorted(unsorted, key=lambda p: p.provider_id))
    assert [p.provider_id for p in canonical] == ["aaa-fake-v1", "lactonization-v1"]


# -- (d) byte-identity of the default path -----------------------------------------------------------------------

def test_default_coproduct_component_is_the_literal_1_6_0_tuple():
    """The coproduct grammar COMPONENT, by itself, hashes to the literal 1.6.0 value -- a direct byte anchor on the
    one thing the registry must not perturb when unused."""
    assert canonical_digest(("coproduct", "lactonization-v1", 1)) == (
        "24d5dc40e94c2774a13cfdd104dc245745082d365ac660192988c85944ef4873"
    )


def test_default_call_grammar_digest_is_byte_identical_to_1_6_0():
    """The DEFAULT call reproduces the pre-registry grammar digest EXACTLY.  The expected value is rebuilt here from
    the same structural pieces 1.6.0 used, with the LITERAL coproduct component spliced in -- so if the default path
    ever switched to the sorted-provider-ids form (or any other shape), this fails byte-for-byte.  This is the pin
    that protects the cli_json goldens and the replay surface from the lift."""
    assert DEFAULT_COPRODUCT_PRODUCERS == (LACTONIZATION_PRODUCER,)
    expected = canonical_digest((
        "event-route",
        search_algebra_digest("linear-route", DEFAULT_TRANSFORM_REGISTRY),
        tuple(sorted(f.provider_id for f in LATERAL_FAMILIES)),
        1,                                           # lateral_hops default
        ("coproduct", "lactonization-v1", 1),        # the LITERAL 1.6.0 coproduct component, max_coproduct_events=1
    ))
    result = search_event_routes(TARGET, **SEARCH_KW)   # defaults: lateral_hops=1, max_coproduct_events=1
    assert result.receipt.transform_grammar_digest == expected
    # and passing the default set EXPLICITLY must not differ from omitting it.
    explicit = search_event_routes(TARGET, coproduct_producers=(LACTONIZATION_PRODUCER,), **SEARCH_KW)
    assert explicit.receipt.transform_grammar_digest == expected
