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


# -- grammar identity: now CONTENT-BOUND (0.7 Round II closed the honor-system gap; plan §4) -------------------
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


def test_provider_identity_is_now_content_bound_and_prose_independent():
    # 0.7 Round III CALIBRATED MOVEMENT: a provider's identity WAS
    # (id, version, capability_manifest, semantic_descriptor.digest) in Round II -- the raw manifest (carrying human
    # "mechanism" prose) sat in slot 2, so a prose edit moved registry.digest.  It is now the PROSE-INDEPENDENT
    # 3-tuple (id, version, semantic_descriptor.digest): the descriptor binds every LOAD-BEARING manifest value
    # (typed knobs, family/projection/authority) plus the declarative rule/guard digests and the reagentless flag,
    # so chemistry moves the digest and prose does not.  Pinned at the new shape so a future change surfaces HERE.
    ident = DielsAlderProvider().identity
    assert len(ident) == 3
    assert ident[0] == "diels-alder-retro" and ident[1] == "v1"
    assert ident[2] == DielsAlderProvider().semantic_descriptor.digest  # the content-bound descriptor digest
    desc = DielsAlderProvider().semantic_descriptor
    # the DA descriptor still carries REAL declarative content digests (not None): the rewrite rule + the guard spec.
    assert desc.structural_rule_digest is not None and desc.guard_spec_digest is not None
    # identity is still deterministic for identically-constructed providers.
    assert CappedScissionProvider().identity == CappedScissionProvider().identity


def test_mechanism_prose_edit_does_not_move_identity_but_a_load_bearing_edit_does():
    # SS1B PROSE-INDEPENDENCE (0.7 Round III): editing ONLY the non-semantic 'mechanism' wording must leave the
    # provider's registry identity STABLE, while every load-bearing edit still moves it.  Round II FAILED the first
    # half: the raw manifest was in identity, so a prose edit moved registry.digest.  This pins the discriminator.
    from smartchem.transform_provider import TransformProviderRegistry

    real = CappedScissionProvider()
    real_reg = TransformProviderRegistry((real,)).digest

    class ProseOnlyEdit(CappedScissionProvider):
        @property
        def capability_manifest(self):
            return tuple(("mechanism", "COMPLETELY REWORDED PROSE") if k == "mechanism" else (k, v)
                         for k, v in super().capability_manifest)

    # (stable) a pure mechanism-prose edit moves NOTHING in the digested identity.
    assert ProseOnlyEdit().semantic_descriptor.digest == real.semantic_descriptor.digest
    assert TransformProviderRegistry((ProseOnlyEdit(),)).digest == real_reg

    # (moves) a typed behavior knob -> identity moves.
    class KnobEdit(CappedScissionProvider):
        @property
        def capability_manifest(self):
            return tuple(("max_reactant_cuts", 2) if k == "max_reactant_cuts" else (k, v)
                         for k, v in super().capability_manifest)
    assert KnobEdit().semantic_descriptor.digest != real.semantic_descriptor.digest

    # (moves) the supported-use set -> identity moves.
    from smartchem.transform_provider import ProviderUse
    class UseEdit(CappedScissionProvider):
        supported_uses = frozenset({ProviderUse.LINEAR_ROUTE})
    assert UseEdit().semantic_descriptor.digest != real.semantic_descriptor.digest

    # (moves) a provider-version bump -> identity moves (it is slot 1 of the identity tuple). CappedScissionProvider
    # is a frozen dataclass, so bump the field directly rather than annotating a subclass (which the dataclass
    # machinery would ignore).
    assert CappedScissionProvider(provider_version="v2").identity != real.identity


def test_reagentless_capability_is_bound_into_semantic_identity():
    # SS1A REAGENT-POLICY BINDING (0.7 Round III): reagentless_capable gates whether an empty-pool search RUNS, so it
    # is semantic -- flipping it MUST move the descriptor digest (Round II left it out, breaking the one-way law).
    real = CappedScissionProvider()  # reagentless_capable = False (needs a cutting reagent)
    assert real.reagentless_capable is False
    assert real.semantic_descriptor.reagentless_capable is False

    class CapReagentless(CappedScissionProvider):
        reagentless_capable = True

    flipped = CapReagentless()
    assert flipped.semantic_descriptor.reagentless_capable is True
    # the flip moves the descriptor digest, hence identity, hence registry.digest.
    assert flipped.semantic_descriptor.digest != real.semantic_descriptor.digest
    assert flipped.identity != real.identity
    from smartchem.transform_provider import TransformProviderRegistry
    assert TransformProviderRegistry((flipped,)).digest != TransformProviderRegistry((real,)).digest


def test_semantic_identity_moves_when_the_rule_or_a_load_bearing_guard_changes():
    # The semantic-identity DISCRIMINATOR (plan §4 / §8): a change to the declarative rewrite rule OR a load-bearing
    # guard policy MUST move the provider identity.  Pre-0.7 this test would have FAILED (identity was hand-declared
    # metadata that ignored the rule/guard entirely).  Prose-only edits must NOT move it.
    from dataclasses import replace as _replace

    from smartchem.diels_alder import _ALKENE_SPEC, _ALKYNE_SPEC, _da_semantic_descriptor

    real = DielsAlderProvider()
    real_digest = real.semantic_descriptor.digest

    # (a) mutate a load-bearing GUARD (loosen the exocyclic-order ceiling) -> identity MUST move.
    guard_mutant = _replace(_ALKENE_SPEC, exocyclic_max_order=2)
    assert _da_semantic_descriptor(real, guard_mutant).digest != real_digest
    # (b) mutate the guard-2c neutral-valence table (loosen sulfur) -> identity MUST move.
    nv_mutant = _replace(_ALKENE_SPEC, neutral_valence=tuple(sorted({"C": 4, "N": 3, "O": 2, "S": 4}.items())))
    assert _da_semantic_descriptor(real, nv_mutant).digest != real_digest
    # (c) swap in a genuinely different (valid, degree-preserving) rewrite RULE -- the alkyne family's own retro --
    #     so the structural_rule_digest changes -> identity MUST move.  (A degree-BREAKING mutant can't even be
    #     constructed: BondRule.__post_init__ refuses it, which is the rule layer's own guard, not this test's job.)
    rule_mutant = _replace(_ALKENE_SPEC, retro_rule=_ALKYNE_SPEC.retro_rule)
    assert _da_semantic_descriptor(real, rule_mutant).digest != real_digest
    # (d) an identical reconstruction of the real spec keeps a STABLE digest (no spurious movement).
    same = _replace(_ALKENE_SPEC)
    assert _da_semantic_descriptor(real, same).digest == real_digest
