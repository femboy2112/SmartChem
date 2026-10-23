"""PERICYCLIC-LAYER-A-FUZZ-132 -- is Layer A a SOUND SOLE GATE + SEPARATOR for the 14 pericyclic recognizers?

The authority question behind issue #132.  Each pericyclic recognizer (8 Diels-Alder + 4 [3,3] sigmatropic + 2
electrocyclic) is three-layer: Layer A re-derives the transformation FROM THE MOLECULES (a guarded retro whose
fragments must be EXACTLY the declared reactants, with an independent reconstruction verifier); Layer B checks the
declared ``reaction_center == family.center`` by exact equality; Layer C fail-closed blocks a step with no centre.
Layers B/C read the step's ``reaction_center`` -- a caller-settable, forgeable field (the same one issue #126
retired for the condensation families).  They are the LAST forgeable-field dependency in the oracle.

The safety argument for dropping B/C (making the pericyclics content-deterministic like the condensations).  Layer B
is an ADDED ``and`` condition after Layer A, so removing it can only turn an ABSTAIN into a MATCH -- and only for a
step that ALREADY passes Layer A.  Therefore dropping B/C introduces NO new false-vouch IFF **every step that passes
Layer A is a genuine member of that family** (Layer A is sound alone) AND **no step passes two families' Layer A**
(Layer A separates, so the first-match recognizer scan assigns the right class).  This harness is the evidence for
both, as a committed, seeded, replayable differential fuzz.  (It also records the #132 WIN: a centre-less genuine
pericyclic step the oracle demotes TODAY, which Layer-A-alone recognition vouches.)

What it establishes:
  1. IDENTITY MATRIX (positive + separation).  For the 14 genuine centre-less members x 14 families, Layer A fires
     EXACTLY on the diagonal: each member passes its own family and NO other (no cross-poach, including the three
     diene-position families that SHARE a centre with their dienophile siblings and so are separable by Layer A
     alone -- precisely the case Layer B cannot distinguish).
  2. FICTION BATTERY (soundness, the cardinal).  A curated set of mass-CONSERVING non-members -- isomeric-fragment
     decoys, non-ring products, aromatic adducts, wrong ring sizes, exocyclic-alkene isomers, wrong dienophile --
     fires NO family's Layer A.
  3. SEEDED RANDOM DIFFERENTIAL (soundness net).  Over many seeded random (family, product, reactants) triples drawn
     from a molecule pool, EVERY Layer-A firing is a mass+charge-CONSERVING step (Layer A never vouches a
     non-conserving pairing), and firings are rare (the gate discriminates, it does not fire on everything).
  4. CONTENT-DETERMINISM / the #132 win (end-to-end).  Each genuine member built as a CENTRE-LESS ``ExperimentStep``
     is recognized as its family by :func:`recognize_reaction_type` -- the residual the §3 corpus records as
     PERICYCLIC_CENTRELESS_RESIDUAL is closed once Layers B/C are dropped.  (Run BEFORE the drop, check #4 FAILS and
     1-3 PASS -- Layer A is sound but the centre gate still demotes the genuine centre-less step; AFTER the drop, all
     pass.)

Run: ``.venv/bin/python -m experiments.pericyclic_layer_a_fuzz_132``
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from smartchem.smiles import parse_smiles as P
from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.diels_alder import (
    _reactant_da_disconnects_to, _reactant_alkyne_da_disconnects_to, _reactant_hetero_da_disconnects_to,
    AZA_DA, OXA_DA, THIA_DA, AZA_DIENE_DA, OXA_DIENE_DA, THIA_DIENE_DA,
)
from smartchem.lateral_rewrite import (
    _reactant_rewrites_to, lateral_rewrites, COPE, CLAISEN, AZA_CLAISEN, THIA_CLAISEN, ELECTRO_4PI, ELECTRO_6PI,
)


def _layer_a_da(product, reactants):
    return _reactant_da_disconnects_to(product, tuple(reactants))


def _layer_a_alkyne(product, reactants):
    return _reactant_alkyne_da_disconnects_to(product, tuple(reactants))


def _layer_a_hetero(family):
    def f(product, reactants):
        return _reactant_hetero_da_disconnects_to(family, product, tuple(reactants))
    return f


def _layer_a_lateral(family):
    def f(product, reactants):
        return _reactant_rewrites_to(family, product, tuple(reactants))
    return f


@dataclass
class Family:
    name: str
    layer_a: object            # (product_mol, reactants_tuple) -> bool
    reactants: tuple           # the genuine member's reactants (SMILES)
    product: str               # the genuine member's product (SMILES); or "" if derived at build time
    product_mol: object = None # resolved genuine product Molecule


def _cope_product():
    """Cope's genuine (non-degenerate) partner, derived by one lateral rewrite of a substituted 1,5-diene (the
    symmetric isomer has an awkward SMILES; the rewrite gives the real partner Molecule directly)."""
    return lateral_rewrites(COPE, P("C=CC(C)CC=C"))[0]


def families() -> "list[Family]":
    fams = [
        Family("alkene-DA (cyclohexene)", _layer_a_da, ("C=CC=C", "C=C"), "C1CCC=CC1"),
        Family("alkyne-DA (1,4-cyclohexadiene)", _layer_a_alkyne, ("C=CC=C", "C#C"), "C1C=CCC=C1"),
        Family("aza-DA (tetrahydropyridine)", _layer_a_hetero(AZA_DA), ("C=CC=C", "C=N"), "C1CC=CCN1"),
        Family("oxa-DA (dihydropyran)", _layer_a_hetero(OXA_DA), ("C=CC=C", "C=O"), "C1CC=CCO1"),
        Family("thia-DA (dihydrothiopyran)", _layer_a_hetero(THIA_DA), ("C=CC=C", "C=S"), "C1CC=CCS1"),
        Family("aza-diene-DA", _layer_a_hetero(AZA_DIENE_DA), ("C=CC=N", "C=C"), "C1=CCCCN1"),
        Family("oxa-diene-DA", _layer_a_hetero(OXA_DIENE_DA), ("C=CC=O", "C=C"), "C1=CCCCO1"),
        Family("thia-diene-DA", _layer_a_hetero(THIA_DIENE_DA), ("C=CC=S", "C=C"), "C1=CCCCS1"),
        Family("Cope [3,3]", _layer_a_lateral(COPE), ("C=CC(C)CC=C",), ""),       # product derived
        Family("Claisen [3,3]", _layer_a_lateral(CLAISEN), ("C=COCC=C",), "O=CCCC=C"),
        Family("aza-Claisen [3,3]", _layer_a_lateral(AZA_CLAISEN), ("C=CNCC=C",), "N=CCCC=C"),
        Family("thia-Claisen [3,3]", _layer_a_lateral(THIA_CLAISEN), ("C=CSCC=C",), "S=CCCC=C"),
        Family("electrocyclization 4pi", _layer_a_lateral(ELECTRO_4PI), ("C=CC=C",), "C1CC=C1"),
        Family("electrocyclization 6pi", _layer_a_lateral(ELECTRO_6PI), ("C=CC=CC=C",), "C1C=CC=CC1"),
    ]
    for f in fams:
        f.product_mol = _cope_product() if f.name.startswith("Cope") else P(f.product)
    return f and fams


def _reactant_mols(f: Family) -> tuple:
    return tuple(P(s) for s in f.reactants)


#: A curated set of mass-CONSERVING fictions (product, reactants-SMILES): each is a plausible near-miss that is NOT a
#: genuine member of ANY family, so Layer A must fire for NONE of the 14.  (Conservation is checked by the harness.)
_FICTIONS: "tuple[tuple[str, tuple[str, ...]], ...]" = (
    ("C1CCC=CC1", ("C=C=CC", "C=C")),         # cyclohexene from ALLENE + ethylene -- allene is not the true diene
    ("C1CCC=CC1", ("C=CC=C", "C#C")),         # cyclohexene from butadiene + ACETYLENE -- that gives 1,4-chd, not this
    ("C1CCC=CC1", ("C=CC=C", "C=CC=C")),      # cyclohexene from two butadienes -- wrong fragments
    ("C=CCCC=C", ("C=CC=C", "C=C")),          # ACYCLIC hexadiene "adduct" from butadiene + ethylene -- non-ring
    ("C=C1CCCC1", ("C=CC=C", "C=C")),         # methylenecyclopentane (EXOCYCLIC alkene isomer) -- not the [4+2] adduct
    ("c1ccccc1", ("C=CC=C", "C#C")),          # benzene "adduct" -- aromatic, guard 3 excludes
    ("C1CCC=C1", ("C=CC=C", "C=C")),          # cyclopentene -- wrong ring size / mass-mismatched (checked)
    ("C1CC=CCN1", ("C=CC=C", "C=C")),         # the aza-DA adduct with all-carbon fragments -- heteroatom mismatch
    ("C1CC=CCO1", ("C=CC=C", "C=C")),         # the oxa-DA adduct with all-carbon fragments -- heteroatom mismatch
    ("O=CCCC=C", ("C=CCC=C", "C")),           # pentenal from a bad 2-fragment split -- not a [3,3] of one molecule
    ("C1CC=C1", ("C=CC=C", "C=C")),           # cyclobutene as a 2->1 DA "adduct" -- wrong archetype/shape
    ("CC(=O)OC", ("CC(=O)O", "CO")),          # an esterification -- a CONDENSATION, never a pericyclic
    ("C1CCCCC1", ("C=CC=C", "C=C")),          # cyclohexane (no C=C) from butadiene+ethylene -- mass-mismatched
    ("C1CCC=CC1", ("C1CCC=CC1", "C1CCC=CC1")),  # self-pairing nonsense
)

#: The molecule pool for the seeded random differential (members' molecules + decoys).
_POOL_SMILES = (
    "C=CC=C", "C=C", "C#C", "C=N", "C=O", "C=S", "C=CC=N", "C=CC=O", "C=CC=S",
    "C1CCC=CC1", "C1C=CCC=C1", "C1CC=CCN1", "C1CC=CCO1", "C1CC=CCS1", "C1=CCCCN1", "C1=CCCCO1", "C1=CCCCS1",
    "C=COCC=C", "O=CCCC=C", "C=CNCC=C", "N=CCCC=C", "C=CSCC=C", "S=CCCC=C", "C=CC=CC=C", "C1C=CC=CC1", "C1CC=C1",
    "c1ccccc1", "C1CCCCC1", "C1CCC=C1", "C1CCCCC=C1", "C=C=CC", "C=CCCC=C", "C=C1CCCC1", "CC(=O)OC", "C=CC(C)CC=C",
)


def _formula_multiset(mols) -> dict:
    total: dict = {}
    for m in mols:
        for el, n in dict(m.formula).items():
            total[el] = total.get(el, 0) + n
    return {k: v for k, v in total.items() if v}


def _conserves(product, reactants) -> bool:
    try:
        lhs = _formula_multiset(reactants)
        rhs = _formula_multiset((product,))
        lc = sum(getattr(r, "charge", 0) for r in reactants)
        rc = getattr(product, "charge", 0)
        return lhs == rhs and lc == rc
    except Exception:
        return False


def measure_layer_a(seed: int = 1320, random_trials: int = 1500) -> dict:
    fams = families()
    n = len(fams)
    # 1. IDENTITY MATRIX: M[i][j] = does member i pass family j's Layer A?  Must be the identity.
    matrix = [[bool(fams[j].layer_a(fams[i].product_mol, _reactant_mols(fams[i]))) for j in range(n)]
              for i in range(n)]
    diagonal_ok = all(matrix[i][i] for i in range(n))
    offdiagonal_fires = [(fams[i].name, fams[j].name) for i in range(n) for j in range(n)
                         if i != j and matrix[i][j]]
    # 2. FICTION BATTERY: no family's Layer A may fire on any curated fiction (all are checked to conserve).
    fiction_fires, nonconserving_fictions = [], []
    for prod_s, react_s in _FICTIONS:
        prod = P(prod_s)
        reacts = tuple(P(s) for s in react_s)
        if not _conserves(prod, reacts):
            nonconserving_fictions.append((prod_s, react_s))  # a mass-mismatched decoy (still must not fire)
        for f in fams:
            if f.layer_a(prod, reacts):
                fiction_fires.append((f.name, prod_s, react_s))
    # 3. SEEDED RANDOM DIFFERENTIAL: every firing must conserve mass+charge; report firing count.
    rng = random.Random(seed)
    pool = [P(s) for s in _POOL_SMILES]
    nonconserving_fires = []
    firings = 0
    for _ in range(random_trials):
        f = rng.choice(fams)
        prod = rng.choice(pool)
        k = rng.choice((1, 2))
        reacts = tuple(rng.choice(pool) for _ in range(k))
        try:
            fired = bool(f.layer_a(prod, reacts))
        except Exception:
            fired = False  # a Layer-A fault is an abstain, never a fire (fail-closed) -- recorded as non-firing
        if fired:
            firings += 1
            if not _conserves(prod, reacts):
                nonconserving_fires.append((f.name, prod.formula, reacts))
    return {
        "matrix": matrix, "names": [f.name for f in fams],
        "diagonal_ok": diagonal_ok, "offdiagonal_fires": offdiagonal_fires,
        "fiction_fires": fiction_fires, "nonconserving_fictions": nonconserving_fictions,
        "random_trials": random_trials, "random_firings": firings, "nonconserving_fires": nonconserving_fires,
    }


def measure_recognition() -> dict:
    """The #132 win, end-to-end: each genuine member built as a CENTRE-LESS ExperimentStep, through the oracle.
    BEFORE dropping Layers B/C every row is None (Layer C demotes a centre-less step); AFTER, every row MATCHes."""
    rows = []
    for f in families():
        reacts = _reactant_mols(f)
        prod = f.product_mol
        try:
            step = ExperimentStep.assembling(prod, reacts, (prod,), reagents=(),
                                             envelope=ConditionEnvelope.unknown(), reaction_center=None)
            klass = recognize_reaction_type(step)
        except Exception as exc:
            klass = f"ERROR: {type(exc).__name__}: {exc}"
        rows.append((f.name, klass))
    return {"rows": rows, "all_recognized": all(k is not None and not str(k).startswith("ERROR") for _n, k in rows)}


#: evil-morty's #132-hardening kills: net-NEUTRAL but NOT closed-shell "adducts" -- a charge-separated zwitterion
#: ([CH-]/[CH+] ring carbons at degree 3) or an odd-electron radical -- that USED to pass Layer A as a genuine
#: pericyclic (a false-vouch of the type).  The closed-shell-neutral guard (is_closed_shell_neutral) now rejects each.
_CHARGE_RADICAL_KILLS = (
    ("alkene-DA zwitterion", "C1=C[CH-][CH+]CC1"),
    ("aza-DA zwitterion", "[CH-]1[CH+]C=CCN1"),
    ("oxa-DA zwitterion", "[CH-]1[CH+]C=CCO1"),
    ("thia-DA zwitterion", "[CH-]1[CH+]C=CCS1"),
    ("Cope radical", "[CH-]=[CH+]CCC=C"),
)


def measure_hardening() -> dict:
    """The #132 hardening (evil-morty's adversarial kills): a net-neutral charge-separated / radical species is NOT a
    closed-shell pericyclic partner.  Each kill's 'adduct' is rejected by :func:`is_closed_shell_neutral`, so no
    recognizer can vouch a step carrying one -- and the end-to-end alkene kill (the zwitterion built with its own
    retro fragments, exactly as the adversary constructed it) now ABSTAINS through the public recognizer."""
    from smartchem.diels_alder import is_closed_shell_neutral, retro_da_disconnections
    from smartchem.rule_calculus_bridge import _config, _joined
    rows = [(name, P(smi).charge, bool(is_closed_shell_neutral(P(smi)))) for name, smi in _CHARGE_RADICAL_KILLS]
    # end-to-end: rebuild the alkene zwitterion kill faithfully (product + its radical retro fragments) and recognize.
    ring = P("C1=C[CH-][CH+]CC1")
    audits, _ = retro_da_disconnections(_joined((ring,)))
    end_to_end = None
    if audits:
        frags = tuple(_config(audits[0].witness.target).species)
        step = ExperimentStep.assembling(ring, frags, (ring,), reagents=(),
                                         envelope=ConditionEnvelope.unknown(), reaction_center=None)
        end_to_end = recognize_reaction_type(step)
    return {
        "rows": rows,
        "all_rejected": all(not csn for _n, _c, csn in rows),
        "end_to_end_recognized": end_to_end,   # must be None (demoted) post-fix
    }


def validate() -> bool:
    """Post-change invariant: Layer A is a sound sole gate + separator (1-3) AND centre-less genuine pericyclics are
    recognized (4).  Run before the Layer-B/C drop and #4 is expected to FAIL (the residual) while 1-3 hold."""
    m = measure_layer_a()
    r = measure_recognition()
    h = measure_hardening()
    return (m["diagonal_ok"] and not m["offdiagonal_fires"] and not m["fiction_fires"]
            and not m["nonconserving_fires"] and r["all_recognized"]
            and h["all_rejected"] and h["end_to_end_recognized"] is None)


def main() -> None:
    m = measure_layer_a()
    print("PERICYCLIC-LAYER-A-FUZZ-132 -- is Layer A a sound sole gate + separator?\n")
    print("  1. IDENTITY MATRIX (diagonal True, off-diagonal False):")
    print(f"       diagonal (every member passes its own family): {'OK' if m['diagonal_ok'] else 'FAIL'}")
    print(f"       off-diagonal cross-poach firings: {len(m['offdiagonal_fires'])}  {m['offdiagonal_fires'][:6]}")
    print(f"  2. FICTION BATTERY ({len(_FICTIONS)} curated near-misses, "
          f"{len(m['nonconserving_fictions'])} mass-mismatched):")
    print(f"       fictions that wrongly fired Layer A: {len(m['fiction_fires'])}  {m['fiction_fires'][:6]}")
    print(f"  3. SEEDED RANDOM DIFFERENTIAL ({m['random_trials']} trials):")
    print(f"       Layer-A firings: {m['random_firings']}  "
          f"non-conserving firings (must be 0): {len(m['nonconserving_fires'])}")
    r = measure_recognition()
    print("  4. CONTENT-DETERMINISM (centre-less genuine member -> oracle class; the #132 win):")
    for name, klass in r["rows"]:
        print(f"       {'OK ' if klass and not str(klass).startswith('ERROR') else '** '}{name:34s} -> {klass}")
    h = measure_hardening()
    print("  5. HARDENING (evil-morty charge-separated / radical kills -- each must be rejected):")
    for name, charge, csn in h["rows"]:
        print(f"       {'OK ' if not csn else '** '}{name:26s} net-charge={charge} closed-shell-neutral={csn}")
    print(f"       end-to-end alkene zwitterion kill -> {h['end_to_end_recognized']} (must be None)")
    print(f"\n  VERDICT: {'PASS' if validate() else 'FAIL (expected before the Layer-B/C drop: #4 abstains)'}")


if __name__ == "__main__":
    main()
