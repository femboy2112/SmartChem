"""CAFFEINE-DERIVE-01: caffeine works by NAME, and its synthesis is DERIVED (not hard-coded).

Pins the user's litmus ("it works when I try 'caffeine'") under the user's constraint ("we aren't just hard coding
chemical reactions").  The ONLY thing registered is the 4 purine name->structure entries (caffeine + the xanthine
methylation ladder); every reaction connecting them is derived by the generic capped-scission engine.

The LOAD-BEARING proof of derivation-not-lookup is STRUCTURAL: caffeine's reaction is absent from SEED_CONDITIONS (the
only table) yet derived -- an untabulated reaction cannot be a table hit.  (An adversarial review showed the
bench-sensitivity control is corroborating, not sufficient: a reactant-gated lookup would also return 0 on a wrong
stock.)  The engine over-generates valence-valid-but-dubious candidates -- pinned honestly, since every route is only
FORMAL_CANDIDATE (conservation certified, mechanism NOT).
"""
from __future__ import annotations

import pytest

from experiments import caffeine_derivation_probe as probe
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.service import RankedRouteSummary
from smartchem.smiles import SmilesError
from smartchem.smiles import parse_smiles as M
from smartchem.structure import structure_by_name

_LADDER = {
    "caffeine": ("C8H10N4O2", "RYYVLZVUVIJVGH-UHFFFAOYSA-N"),
    "theophylline": ("C7H8N4O2", "ZFXYFBGIUFBOJW-UHFFFAOYSA-N"),
    "theobromine": ("C7H8N4O2", "YAPQBXQYLJRXSA-UHFFFAOYSA-N"),
    "xanthine": ("C5H4N4O2", "LRFVTYWOQMYALW-UHFFFAOYSA-N"),
}


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_four_purines_resolve_by_name_with_the_right_formula():
    for name, (formula, _ik) in _LADDER.items():
        s = structure_by_name(name)
        assert s is not None, f"{name} did not resolve offline"
        assert str(s.formula) == formula, (name, str(s.formula), formula)


def test_caffeine_synonyms_resolve():
    for syn in ("1,3,7-trimethylxanthine", "theine", "guaranine", "methyltheobromine"):
        assert getattr(structure_by_name(syn), "name", None) == "caffeine", syn


def test_caffeine_resolves_through_the_public_identity_parser_not_invalid_input():
    # the exact front-door path `recompile caffeine` takes: AUTO -> offline name.  Before registration this raised
    # IdentityParseError (INVALID_INPUT / exit 2); now it resolves to the caffeine structure.
    target = resolve_target("caffeine", InputKind.AUTO)
    mol = getattr(target, "molecule", target)
    formula = "".join(f"{el}{n if n > 1 else ''}" for el, n in sorted(mol.formula.items()))
    assert formula == "C8H10N4O2"


def test_caffeine_route_is_DERIVED_and_the_reaction_is_UNTABULATED():
    # THE load-bearing proof: the engine derives the sound methylation, AND caffeine appears in NO SEED_CONDITIONS
    # entry -- an untabulated reaction cannot be a table lookup.  (Structural, not the bench-sensitivity control.)
    d = probe.route_is_derived_and_untabulated()
    assert d["sound_methylation_present"] is True, d
    assert d["caffeine_absent_from_seed_conditions"] is True, d
    assert d["n_seed_conditions"] == 6, d


def test_control_is_only_bench_sensitive_not_the_derivation_proof():
    # corroborating (necessary, not sufficient): a structurally-unrelated stock -> 0 caffeine routes.  A
    # reactant-gated lookup would ALSO return 0, so this alone does not prove genericity (the untabulated fact does).
    c = probe.control_bench_sensitive()
    assert c["n_derived_from_wrong_stock"] == 0, c


def test_the_full_methylation_ladder_derives_via_real_intermediates():
    # 4 hard-coded structures -> the ladder, each rung derived; the C6H6N4O2 intermediate is the SPECIFIC expected
    # monomethylxanthine (structural identity), not merely a formula that balances.
    assert all(probe.ladder_derives().values()), probe.ladder_derives()


def test_engine_over_generates_valence_valid_but_dubious_candidates():
    # HONEST boundary: alongside the sound methylation the engine emits a valence-valid C-C homologation.  The
    # demonstrations are EXISTENCE checks; this pins that "the ladder derives" is NOT "only sound chemistry derives".
    o = probe.over_generation_is_present()
    assert o["sound_methylation_present"] and o["dubious_homologation_also_present"], o


def test_every_derived_caffeine_route_is_only_FORMAL_CANDIDATE():
    # birdperson fold: pin the epistemic floor to the caffeine route itself.  The engine certifies conservation, NOT
    # mechanism -- so no caffeine route may claim a readiness tier above FORMAL_CANDIDATE.  If a future refactor
    # promotes a formal candidate to a sourced/verified tier without real evidence, THIS fires.
    caf = M(probe._SMILES["caffeine"])
    theo = M(probe._SMILES["theophylline"])
    compiled = compile_synthesis(caf, reagents=(M("CO"), M("O")), available=(theo,), max_depth=2,
                                 max_routes=8, cut_budget=20000, commodities=(), box=ConstraintBox())
    assert compiled.ranked, "expected at least one derived caffeine route"
    for fit in compiled.ranked:
        assert RankedRouteSummary.of_fit(fit).readiness_tier == "FORMAL_CANDIDATE"


def test_caffeine_identity_is_kekule_spelling_invariant():
    a = M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C")
    b = M("O=C1N(C)C(=O)N(C)C2=C1N(C)C=N2")
    from smartchem.contracts import canonical_digest
    assert canonical_digest(a.canonical()) == canonical_digest(b.canonical())


def test_aromatic_purine_spelling_is_a_documented_kekulizer_gap():
    # the lowercase-aromatic purine spelling does NOT yet kekulize (a generic fused-ring aromaticity gap, the
    # R39 conjugated-carbonyl class); the registry uses the explicit-Kekulé form.  Pinned as a KNOWN, fail-closed
    # boundary so a future kekulizer fix is a deliberate, reviewed flip -- not a silent behaviour change.
    with pytest.raises(SmilesError):
        M("Cn1cnc2c1c(=O)n(C)c(=O)n2C")   # aromatic caffeine


@pytest.mark.parametrize("name", list(_LADDER))
def test_registered_structure_matches_rdkit_inchikey(name):
    # DEV-VENV oracle: bind NAME->structure to the external PubChem reality anchor.  Skipped on the committed baseline.
    Chem = pytest.importorskip("rdkit.Chem")
    from rdkit.Chem.inchi import MolToInchiKey
    smiles = probe._SMILES[name]
    _formula, anchor = _LADDER[name]
    ik = MolToInchiKey(Chem.MolFromSmiles(smiles))
    assert ik == anchor, (name, ik, anchor)
