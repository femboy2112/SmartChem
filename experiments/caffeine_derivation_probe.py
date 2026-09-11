"""CAFFEINE-DERIVE-01: caffeine works by NAME, and its synthesis is DERIVED, not hard-coded.

The user's litmus: "it works when I try 'caffeine'" -- with the explicit demand that we NOT solve it by hard-coding
chemical reactions ("that's what the entire category-theoretical-math-framing is supposed to be for").  This probe is
the evidence that both hold:

* The ONLY thing registered is the ``name -> structure`` dictionary -- 4 real purines (caffeine + the xanthine
  methylation ladder: theophylline, theobromine, xanthine).  A name is a human convention and is underivable, so a
  name->structure table is unavoidable; it hard-codes STRUCTURES (reality), never reactions.
* Every reaction connecting them is DERIVED by the generic capped-scission engine from conservation + the transform
  algebra -- ``decompiler_conditions.py`` only DECORATES derived edges with sourced conditions (loud ``unknown()``
  otherwise), it is not a reaction generator.

THE LOAD-BEARING PROOF that a route is DERIVED, not retrieved, is STRUCTURAL, not the bench-sensitivity control (an
adversarial review -- evil-morty/dalembert -- correctly showed a reactant-AVAILABILITY-gated lookup table would ALSO
return 0 under a wrong stock, so "wrong stock -> 0 routes" cannot by itself discriminate derivation from a gated
lookup).  The real discriminator: caffeine's methylation is ABSENT from ``SEED_CONDITIONS`` (the only table in the
system -- 6 esterification/acylation edges, zero purine), yet the engine derives a caffeine route.  An UNTABULATED
reaction cannot be a table hit.  See ``route_is_derived_and_untabulated``.

HONESTY about what the engine does NOT guarantee (adversarial review -- dalembert): the capped-scission grammar is
valence-preserving but NOT chemically selective -- it OVER-GENERATES.  Alongside the sound N-methylation it also emits
valence-valid but chemically dubious candidates (e.g. a C-C homologation ``ethanol + theophylline -> caffeine +
methanol``).  Every route is stamped ``FORMAL_CANDIDATE`` (conservation certified, mechanism NOT).  The demonstrations
below are EXISTENCE checks -- they prove the sound disconnection is AMONG the derived set, never that the set is
chemically clean.  ``over_generation_is_present`` pins that honestly so the freeze cannot drift into an overclaim.

Re-checkable demonstrations, all on the REAL registry + ``compile_synthesis`` route engine:

1. NAMES RESOLVE -- the 4 purines (+ caffeine's synonyms) resolve offline to the correct composition + a
   presentation-invariant structural identity, cross-anchored to the RDKit InChIKey in the gated cross-check.
2. THE ROUTE IS DERIVED AND UNTABULATED -- the engine derives ``methanol + theophylline -> caffeine + water`` (a
   FORMAL, conservation-valid methylation), and caffeine's composition appears in NO ``SEED_CONDITIONS`` entry, so the
   derivation cannot be a table hit.  The derived step is pinned by the STRUCTURAL identity of its reactant (so the
   N7 disconnection from theophylline is distinguishable from the N1 disconnection from theobromine -- a formula-level
   readout alone collapses those isomers).
3. THE CONTROL (corroborating, NOT the proof) -- a structurally-unrelated stock (ethanol) yields ZERO caffeine
   routes: the search is bench-sensitive.  This is necessary, not sufficient (a gated lookup would also return 0);
   the untabulated fact in #2 is the discriminator.
4. THE LADDER DERIVES -- xanthine -> (theophylline | theobromine) -> caffeine: the sound rung is derived on each
   branch, and each C6H6N4O2 intermediate is the SPECIFIC expected monomethylxanthine (verified by structural
   identity / gated InChIKey), not merely a formula that balances.
5. OVER-GENERATION IS PRESENT -- the derived set for caffeine<-theophylline contains BOTH the sound methylation AND a
   valence-valid non-methylation (a C-C homologation).  Pinned so "the ladder derives" is never read as "only sound
   chemistry derives" (the FORMAL_CANDIDATE boundary, made concrete).
6. KEKULE-SPELLING INVARIANT -- caffeine drawn two different Kekulé ways resolves to ONE structural identity.
7. AROMATIC-PURINE GAP (documented boundary) -- the lowercase-aromatic purine spelling does NOT yet kekulize; the
   registry uses the explicit-Kekulé form.  Pinned so the boundary is a recorded, fail-closed fact.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.contracts import canonical_digest
from smartchem.decompiler_conditions import SEED_CONDITIONS
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox
from smartchem.smiles import SmilesError
from smartchem.smiles import parse_smiles as M
from smartchem.structure import structure_by_name

# --- the 4 ladder structures (explicit-Kekulé; InChIKey-verified against RDKit in the dev venv) --------------
_SMILES = {
    "caffeine": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",       # C8H10N4O2  RYYVLZVUVIJVGH
    "theophylline": "N1C=NC2=C1C(=O)N(C)C(=O)N2C",     # C7H8N4O2   ZFXYFBGIUFBOJW  (1,3-diMe)
    "theobromine": "CN1C=NC2=C1C(=O)NC(=O)N2C",        # C7H8N4O2   YAPQBXQYLJRXSA  (3,7-diMe)
    "xanthine": "N1C=NC2=C1C(=O)NC(=O)N2",             # C5H4N4O2   LRFVTYWOQMYALW  (parent)
}
_INCHIKEYS = {   # PubChem-anchored; the gated _rdkit_cross_check re-derives + compares (dalembert confirmed the
    "caffeine": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",         # anchors DISCRIMINATE isomers -- a paraxanthine decoy matches
    "theophylline": "ZFXYFBGIUFBOJW-UHFFFAOYSA-N",     # none, so they are real keys, not values fitted to the SMILES).
    "theobromine": "YAPQBXQYLJRXSA-UHFFFAOYSA-N",
    "xanthine": "LRFVTYWOQMYALW-UHFFFAOYSA-N",
}
# composition of caffeine, in the shape SEED_CONDITIONS signatures use, for the untabulated-reaction discriminator.
_CAFFEINE_COMP = (("C", 8), ("H", 10), ("N", 4), ("O", 2))


def _formula_str(mol) -> str:
    return "".join(f"{el}{n if n > 1 else ''}" for el, n in sorted(mol.formula.items()))


def _digest(mol) -> str:
    try:
        canon = mol.canonical()
    except NotImplementedError:
        canon = None
    return canonical_digest(canon) if canon is not None else "asgiven:" + canonical_digest(mol)


def _derived_steps(target_smiles: str, stock_smiles: tuple[str, ...],
                   reagent_smiles: tuple[str, ...] = ("CO", "O")) -> tuple[dict, ...]:
    """Every DERIVED single-or-multi step the engine finds for ``target`` from the declared stock/reagents.

    Each step is recorded BOTH at the composition level (``eq``, a formula string) AND at the STRUCTURAL level
    (``react_ids``/``prod_ids``, canonical-identity digests), so N7 (from theophylline) and N1 (from theobromine)
    disconnections -- which share the formula string -- are distinguishable in the frozen payload.  Deterministic.
    """
    target = M(target_smiles)
    available = tuple(M(s) for s in stock_smiles)
    reagents = tuple(M(s) for s in reagent_smiles)
    compiled = compile_synthesis(
        target, reagents=reagents, available=available,
        max_depth=2, max_routes=8, cut_budget=20000, commodities=(),
        box=ConstraintBox(),
    )
    steps: dict[str, dict] = {}
    for route in compiled.ranked:
        for step in route.route.steps:
            lhs = sorted(_formula_str(r) for r in step.reactants)
            rhs = sorted(_formula_str(p) for p in step.products)
            eq = " + ".join(lhs) + " -> " + " + ".join(rhs)
            steps.setdefault(eq, {
                "eq": eq,
                "react_ids": tuple(sorted(_digest(r)[:16] for r in step.reactants)),
                "prod_ids": tuple(sorted(_digest(p)[:16] for p in step.products)),
            })
    return tuple(steps[k] for k in sorted(steps))


def _eqs(steps: tuple[dict, ...]) -> tuple[str, ...]:
    return tuple(s["eq"] for s in steps)


# --- demonstrations ------------------------------------------------------------------------------------------
def names_resolve() -> dict:
    out = {}
    for name in _SMILES:
        s = structure_by_name(name)
        out[name] = {
            "resolved": s is not None,
            "formula": str(s.formula) if s else None,
            "identity": s.structure_identity[:16] if s else None,
        }
    out["synonym:1,3,7-trimethylxanthine"] = getattr(structure_by_name("1,3,7-trimethylxanthine"), "name", None)
    out["synonym:theine"] = getattr(structure_by_name("theine"), "name", None)
    return out


def _caffeine_is_untabulated() -> bool:
    """Caffeine's composition appears in NO SEED_CONDITIONS signature -> its reaction cannot be a table hit."""
    for sig in SEED_CONDITIONS:
        for term in sig:                          # each term is (side, (composition, charge), coefficient)
            if term[1][0] == _CAFFEINE_COMP:
                return False
    return True


def route_is_derived_and_untabulated() -> dict:
    steps = _derived_steps(_SMILES["caffeine"], (_SMILES["theophylline"],))
    theo_id = _digest(M(_SMILES["theophylline"]))[:16]
    caf_id = _digest(M(_SMILES["caffeine"]))[:16]
    # the SOUND methylation: theophylline + methanol -> caffeine + water, pinned by STRUCTURE not just formula.
    methylation = [
        s for s in steps
        if theo_id in s["react_ids"] and caf_id in s["prod_ids"] and s["eq"] == "C7H8N4O2 + CH4O -> C8H10N4O2 + H2O"
    ]
    return {
        "n_derived": len(steps),
        "sound_methylation_present": len(methylation) == 1,
        "caffeine_absent_from_seed_conditions": _caffeine_is_untabulated(),   # THE discriminator
        "n_seed_conditions": len(SEED_CONDITIONS),
    }


def control_bench_sensitive() -> dict:
    # CORROBORATING (not the proof): ethanol-only stock -> 0 caffeine routes.  A gated lookup would also return 0,
    # so this shows bench-sensitivity, NOT derivation-vs-lookup (route_is_derived_and_untabulated is the proof).
    return {"n_derived_from_wrong_stock": len(_derived_steps(_SMILES["caffeine"], ("CCO",))), "bench_sensitive": True}


def ladder_derives() -> dict:
    caf_id = _digest(M(_SMILES["caffeine"]))[:16]
    # the SPECIFIC expected monomethylxanthine intermediates (dalembert-verified structures), pinned by identity.
    mono_ids = {_digest(M(s))[:16] for s in ("CN1C=NC2=C1C(=O)NC(=O)N2", "N1C=NC2=C1C(=O)N(C)C(=O)N2",
                                             "N1C=NC2=C1C(=O)NC(=O)N2C")}   # 1-/3-/7-methylxanthine (some spellings)
    theo_steps = _derived_steps(_SMILES["caffeine"], (_SMILES["theophylline"],))
    thbr_steps = _derived_steps(_SMILES["caffeine"], (_SMILES["theobromine"],))
    xan_to_theo = _derived_steps(_SMILES["theophylline"], (_SMILES["xanthine"],))
    return {
        # the sound methylation reaches caffeine (structural: caffeine is a product) on each precursor branch
        "caffeine<-theophylline": any(caf_id in s["prod_ids"] for s in theo_steps),
        "caffeine<-theobromine": any(caf_id in s["prod_ids"] for s in thbr_steps),
        # xanthine climbs via a REAL monomethylxanthine intermediate (structure, not just C6H6N4O2)
        "theophylline<-xanthine_via_real_intermediate": any(
            any(i in mono_ids for i in s["prod_ids"]) for s in xan_to_theo
        ),
    }


def over_generation_is_present() -> dict:
    # HONEST: the derived set contains a valence-valid non-methylation (C-C homologation) alongside the sound
    # methylation.  Existence checks are blind to this; FORMAL_CANDIDATE is why it is emitted, not a defect.
    eqs = _eqs(_derived_steps(_SMILES["caffeine"], (_SMILES["theophylline"],)))
    homologation = "C2H6O + C7H8N4O2 -> C8H10N4O2 + CH4O"   # ethanol + theophylline -> caffeine + methanol
    methylation = "C7H8N4O2 + CH4O -> C8H10N4O2 + H2O"      # LHS is sorted: C7... sorts before CH4O
    return {
        "sound_methylation_present": methylation in eqs,
        "dubious_homologation_also_present": homologation in eqs,
        "engine_over_generates": (methylation in eqs) and (homologation in eqs),
    }


def kekule_spelling_invariant() -> dict:
    a = _digest(M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C"))
    b = _digest(M("O=C1N(C)C(=O)N(C)C2=C1N(C)C=N2"))    # a different Kekulé drawing of caffeine (verified same identity)
    return {"spelling_a": a[:16], "spelling_b": b[:16], "same_identity": a == b}


def aromatic_purine_gap() -> dict:
    raised = False
    try:
        M("Cn1cnc2c1c(=O)n(C)c(=O)n2C")   # aromatic caffeine
    except SmilesError:
        raised = True
    return {"aromatic_caffeine_kekulizes": not raised, "gap_present": raised}


def _payload() -> dict:
    return {
        "1_names_resolve": names_resolve(),
        "2_route_is_derived_and_untabulated": route_is_derived_and_untabulated(),
        "3_control_bench_sensitive": control_bench_sensitive(),
        "4_ladder_derives": ladder_derives(),
        "5_over_generation_is_present": over_generation_is_present(),
        "6_kekule_spelling_invariant": kekule_spelling_invariant(),
        "7_aromatic_purine_gap": aromatic_purine_gap(),
    }


FROZEN_HASH = "4ca338d56707b212339012c9a0b26b3df42ee216565189973d1a3991f4803b02"


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: names resolve to the right composition; the caffeine route is DERIVED and UNTABULATED
    (the structural discriminator); the control is bench-sensitive (corroborating); the ladder derives via REAL
    intermediates; the engine over-generates (honest FORMAL_CANDIDATE boundary); identity is Kekulé-spelling-invariant;
    and the aromatic-purine kekulization gap is present (a documented, fail-closed boundary)."""
    p = _payload()
    r = p["1_names_resolve"]
    assert all(r[n]["resolved"] for n in _SMILES), r
    assert r["caffeine"]["formula"] == "C8H10N4O2", r
    assert r["synonym:theine"] == "caffeine" and r["synonym:1,3,7-trimethylxanthine"] == "caffeine", r
    d = p["2_route_is_derived_and_untabulated"]
    assert d["sound_methylation_present"] is True, d
    assert d["caffeine_absent_from_seed_conditions"] is True, d          # the load-bearing discriminator
    assert d["n_seed_conditions"] == 6, d
    assert p["3_control_bench_sensitive"]["n_derived_from_wrong_stock"] == 0, p["3_control_bench_sensitive"]
    assert all(p["4_ladder_derives"].values()), p["4_ladder_derives"]
    assert p["5_over_generation_is_present"]["engine_over_generates"] is True, p["5_over_generation_is_present"]
    assert p["6_kekule_spelling_invariant"]["same_identity"] is True, p["6_kekule_spelling_invariant"]
    assert p["7_aromatic_purine_gap"]["gap_present"] is True, p["7_aromatic_purine_gap"]
    return True


def _rdkit_cross_check() -> dict:
    """DEV-VENV ONLY (rdkit): re-derive each registered structure's InChIKey and compare to the PubChem anchor.

    Skipped when rdkit is absent (the committed baseline) -- the structural identity in ``names_resolve`` is the
    rdkit-free invariant; this binds NAME->structure to an external reality anchor when the oracle is present.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem.inchi import MolToInchiKey
    except ImportError:
        return {"skipped": "rdkit absent"}
    out = {}
    for name, smiles in _SMILES.items():
        m = Chem.MolFromSmiles(smiles)
        ik = MolToInchiKey(m) if m is not None else None
        out[name] = {"inchikey": ik, "matches_anchor": ik == _INCHIKEYS[name]}
    return out


if __name__ == "__main__":
    print("content_hash:", content_hash())
    print("validate:", validate())
    print("rdkit cross-check:", json.dumps(_rdkit_cross_check(), indent=2))
