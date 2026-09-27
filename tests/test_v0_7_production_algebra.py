"""v0.7 Production Chemical Algebra -- Round I gate tests.

Pins two committed artifacts:

* the provider/family INVENTORY invariants (the measured gap 0.7 exists to close: the default registry
  GENERATES with one provider while the oracle RECOGNISES 17 classes);
* the FORCING VERTICAL: the alkene Diels-Alder family widening the algebra through the UNCHANGED route
  search, all eight plan properties, WITHOUT flipping the global default.

The semantic grammar-identity content digest (plan §4) is the next sub-round; this file pins the CURRENT
identity shape so that change is a visible, tested movement rather than a silent one.
"""
from __future__ import annotations

from experiments.v0_7_algebra_funnel import run_funnel
from experiments.v0_7_forcing_vertical import CANDIDATE, run
from experiments.v0_7_provider_inventory import _oracle_class_count, build_rows
from smartchem.diels_alder import DielsAlderProvider
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    CappedScissionProvider,
    search_algebra_digest,
)


# -- inventory invariants: the measured "recognised != generated" gap -----------------------------------------
def test_default_registry_generates_with_exactly_one_provider():
    assert DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",)


def test_oracle_recognises_seventeen_classes_but_none_are_wired_into_the_default():
    assert _oracle_class_count() == 17
    # every non-capped family is opt-in: none but capped-scission is in the default.
    rows = build_rows()
    in_default = [r["provider_id"] for r in rows if r["in_default"]]
    assert in_default == ["capped-scission-mediated"]
    # the DA family exists as a live provider but is opt-in (the forcing-vertical candidate).
    da = [r for r in rows if r["provider_id"] == "diels-alder-retro"]
    assert da and da[0]["in_default"] is False


# -- forcing vertical: all eight properties hold (drive the committed experiment) ------------------------------
def test_forcing_vertical_all_properties_hold():
    results = run()
    failed = [name for name, ok, _ in results if not ok]
    assert not failed, f"forcing-vertical properties failed: {failed}"
    assert len(results) == 8


# direct (not-just-via-run) assertions of the two load-bearing properties, so a bug in run() cannot hide them.
def test_da_target_is_reachable_only_with_the_provider():
    chx, buta, eth = parse_smiles("C1CC=CCC1"), parse_smiles("C=CC=C"), parse_smiles("C=C")
    with_da = search_routes(chx, reagents=(), available=(buta, eth), registry=CANDIDATE, max_depth=2)
    without = search_routes(chx, reagents=(), available=(buta, eth), max_depth=2)
    assert len(with_da.routes) == 1
    assert len(without.routes) == 0
    assert [repr(m) for m in with_da.routes[0].steps[0].products] == ["C6H10"]


def test_widening_the_algebra_moves_the_receipt_digest_and_leaves_the_default_untouched():
    d = search_algebra_digest("linear-route", DEFAULT_TRANSFORM_REGISTRY)
    c = search_algebra_digest("linear-route", CANDIDATE)
    assert d != c, "a wider algebra must stamp a different transform-algebra digest"
    # the default is not mutated by constructing the candidate.
    assert DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",)


# -- current grammar-identity shape (the honor-system gap the next sub-round closes; plan §4) -------------------
# -- generative funnel: the before/after denominator delta the wider algebra buys -----------------------------
def test_generative_funnel_before_after_delta_is_stable():
    rows = run_funnel()
    # the DEFAULT is not empty everywhere -- the ester routes and is vouched via capped-scission.
    assert rows["default"]["aggregate"] == {
        "total": 6, "structure": 6, "family_enumerated": 1, "type_vouched": 1, "terminal": 1,
    }
    # the CANDIDATE widens generative reach without touching the default.
    assert rows["candidate"]["aggregate"] == {
        "total": 6, "structure": 6, "family_enumerated": 4, "type_vouched": 2, "terminal": 2,
    }


def test_current_provider_identity_shape_is_declared_metadata_only():
    # TODAY a provider's identity is (id, version, capability_manifest) -- hand-declared metadata, NOT a content
    # digest of the rewrite rule. Pinned so that when 0.7 adds a rule_content_digest, the identity shape CHANGES
    # visibly here (a calibrated movement), rather than a rule edit silently keeping the same digest.
    ident = DielsAlderProvider().identity
    assert len(ident) == 3
    assert ident[0] == "diels-alder-retro" and ident[1] == "v1"
    assert isinstance(ident[2], tuple)  # the capability_manifest (declared prose), not a structural digest
    # two capped-scission providers with identical declared fields share an identity (the gap: identity does not
    # yet reflect the actual enumerate_transforms body).
    assert CappedScissionProvider().identity == CappedScissionProvider().identity
