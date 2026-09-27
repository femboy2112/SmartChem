"""Pins :mod:`experiments.v0_7_forcing_corpus` -- the certified route algebra widens generation across ALL EIGHT
admitted Diels-Alder families (Round I's forcing vertical only exercised the alkene family; this closes the gap).
"""
from __future__ import annotations

from experiments.v0_7_forcing_corpus import FAMILIES, HOLDOUTS, HOSTILE, run
from smartchem.algebra_profiles import resolve_algebra_profile
from smartchem.contracts import canonical_digest
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY

# The certified profile under test -- same resolve call the experiment module makes, never mutates the default.
_CERTIFIED = resolve_algebra_profile("certified-route-v07")

# Fresh, post-freeze substituted targets, one per admitted DA family (8/8) -- NOT in FAMILIES/HOLDOUTS above, and
# confirmed live (never re-typed from memory) to still fire exactly their own family and nothing else.
_FRESH_HOLDOUTS: tuple[tuple[str, str, str], ...] = (
    ("alkene", "CC1=CCCCC1", "DIELS_ALDER"),
    ("alkyne", "C1=CC(C)C=CC1", "DIELS_ALDER_ALKYNE"),
    ("aza-dienophile", "CC1C=CCCN1", "DIELS_ALDER_AZA"),
    ("oxa-dienophile", "CC1C=CCCO1", "DIELS_ALDER_OXA"),
    ("thia-dienophile", "CC1C=CCCS1", "DIELS_ALDER_THIA"),
    ("aza-diene", "N1C=CCC(C)C1", "DIELS_ALDER_AZA_DIENE"),
    ("oxa-diene", "O1C=CCC(C)C1", "DIELS_ALDER_OXA_DIENE"),
    ("thia-diene", "S1C=CCC(C)C1", "DIELS_ALDER_THIA_DIENE"),
)

# The committed fixture SMILES this fresh set must NOT re-mint under a different spelling (ring symmetry lets the
# same molecule wear more than one SMILES string, so a plain string-diff would miss a re-mint -- compare digests).
_COMMITTED_EXCLUSION_SET: tuple[str, ...] = (
    "C1CC=CCC1", "C1=CCC=CC1", "C1C=CCCN1", "C1C=CCCO1", "C1C=CCCS1",
    "N1C=CCCC1", "O1C=CCCC1", "C1CCC=CS1", "CCC1CCC=CC1", "CC1=CCC=CC1", "CC1CCC=CC1",
)


def _da_kinds(registry, reactant) -> tuple[dict, bool]:
    """Same idiom as ``experiments/v0_7_forcing_corpus.py``'s ``_da_kinds``: every DIELS_ALDER* witness kind
    ``registry`` emits for ``reactant`` (reagentless), plus the aggregate completeness flag."""
    ets, complete = registry.enumerate(reactant, (), budget=100_000)
    by_kind: dict = {}
    for e in ets:
        if e.witness_kind.startswith("DIELS_ALDER"):
            by_kind.setdefault(e.witness_kind, []).append(e)
    return by_kind, complete


def test_fresh_post_freeze_holdout_per_da_family():
    # Ugh, fine -- eight fresh substituted targets, one per admitted DA family, none of them borrowed from any
    # committed fixture. Each must fire EXACTLY its own family's kind (no sibling cross-poach), stay invisible to
    # the untouched default registry, and come out the other end oracle-vouched, not just witness-emitted.
    for name, smiles, kind in _FRESH_HOLDOUTS:
        target = parse_smiles(smiles)
        by_kind, complete = _da_kinds(_CERTIFIED, target)
        assert complete, f"{name}: certified enumeration over {smiles!r} was not COMPLETE"
        assert set(by_kind) == {kind}, (
            f"{name}: expected exactly {{{kind!r}}}, got {sorted(by_kind)} for {smiles!r} (cross-poach)"
        )

        d_by_kind, _ = _da_kinds(DEFAULT_TRANSFORM_REGISTRY, target)
        assert d_by_kind == {}, f"{name}: default registry must stay silent, got {sorted(d_by_kind)}"

        edge = by_kind[kind][0].transform
        fragments = edge.products
        with_da = search_routes(target, reagents=(), available=fragments, registry=_CERTIFIED, max_depth=2)
        assert with_da.routes, f"{name}: no route reconstructed under the certified registry"
        step0 = with_da.routes[0].steps[0]
        assert recognize_reaction_type(step0) is not None, f"{name}: oracle did not vouch the generated step"


def test_fresh_holdouts_are_canonically_distinct_from_committed_fixtures():
    # String-diff is not enough here -- ring symmetry lets the same ring wear two different SMILES spellings, so
    # this checks the actual canonical digest, catching a re-mint of an old fixture under a fresh-looking string.
    excluded_digests = {
        canonical_digest(parse_smiles(s).canonical()) for s in _COMMITTED_EXCLUSION_SET
    }
    for name, smiles, _kind in _FRESH_HOLDOUTS:
        digest = canonical_digest(parse_smiles(smiles).canonical())
        assert digest not in excluded_digests, (
            f"{name}: fresh holdout {smiles!r} canonically COLLIDES with a committed exclusion-set fixture"
        )


def test_all_properties_hold():
    results = run()
    failed = [(name, detail) for name, ok, detail in results if not ok]
    assert failed == [], f"forcing-corpus properties FAILED: {failed}"


def test_eight_families_declared():
    assert len(FAMILIES) == 8
    assert len({kind for _, kind, _, _, _ in FAMILIES}) == 8   # 8 distinct witness_kinds, no duplicate family


def test_each_family_enumerates_and_is_class_vouched_with_no_cross_poach():
    results = run()
    by_name = {name: ok for name, ok, _ in results}
    for name, _kind, _smiles, _marker, _source in FAMILIES:
        assert by_name[f"{name}: enumerated"] is True
        assert by_name[f"{name}: re-derived + reachable"] is True
        assert by_name[f"{name}: class-vouched"] is True
        assert by_name[f"{name}: no cross-poach"] is True
        assert by_name[f"{name}: default registry stays silent"] is True


def test_hostile_near_misses_emit_zero_da_witnesses_under_both_registries():
    results = run()
    by_name = {name: ok for name, ok, _ in results}
    for name, _smiles in HOSTILE:
        assert by_name[f"hostile near-miss ({name}): certified registry emits zero DA witnesses"] is True
        assert by_name[f"hostile near-miss ({name}): default registry emits zero DA witnesses"] is True


def test_fresh_holdouts_fire_their_family_and_stay_silent_under_default():
    results = run()
    by_name = {name: ok for name, ok, _ in results}
    for name, _smiles, _kind in HOLDOUTS:
        assert by_name[f"fresh holdout ({name}): certified registry enumerates its family"] is True
        assert by_name[f"fresh holdout ({name}): default registry stays silent"] is True
