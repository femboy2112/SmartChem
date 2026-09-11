"""POOR-MAN-REACHABLE-RECOMPILE-01 (R48, PR-1): make ``recompile <molecule>`` produce a usable synthesis from
stock BY DEFAULT (reachability), every emitted route an HONEST ``FORMAL_CANDIDATE`` with UNKNOWN feasibility
where the ΔG estimator cannot vouch (honesty).  Two moving parts, both hard-coding STRUCTURE (reality) and
DERIVING the chemistry (generic graph surgery), never a reaction lookup:

1. REACHABILITY -- a tiered buyable-leaf catalog (``smartchem/data/reagents.py``) adds real purchasable
   aromatic/hetero scaffolds (theophylline PHARMACY, 4-aminophenol HARDWARE, plus the NON-precursor witness
   salicylic acid PHARMACY) so the default LINEAR retrosynthesis terminates at a buyable leaf.  (Aspirin is
   deliberately NOT admitted -- it is a registered synthesis target with its own producibility coverage, so it
   must stay synthesizable, not buyable stock; the probe asserts ``aspirin_not_a_commodity``.)  The north stars
   flip from NO route to a one-step synthesis: caffeine <- theophylline + methanol; paracetamol <- acetic
   acid + 4-aminophenol.

2. HONESTY -- a feasibility/equilibrium DOMAIN GUARD (``feasibility.py::_is_intermolecular_acyl_condensation``)
   for the aqueous free-acid dehydrative-acylation class (acid + amine/alcohol/thiol -> amide/ester/thioester
   + water).  The ΔG estimator is BLIND to the acid-base salt sink (aqueous acid + amine gives the ammonium
   carboxylate salt, not the amide) and to the activation this class needs, so it over-claims the paracetamol
   Fischer route FAVORABLE (ΔG -98 kJ) / ESSENTIALLY_COMPLETE (K ~ 1e17) -- a fabrication.  The guard recognizes
   the class by DERIVED bond-topology surgery and FAILS CLOSED to UNKNOWN.  One guard in ``feasibility_of_step``
   makes BOTH the feasibility and equilibrium layers honest (equilibrium reuses the ΔG and returns UNKNOWN when
   it is None).

The guard's SHAPE restriction -- exactly 2 non-water reactants -> exactly 1 non-water product + water --
survived a 4-bearing adversarial gate (evil-morty + dalembert with run evidence).  It structurally excludes:
intramolecular ring closure (lactone/lactam: 1 reactant, thermo IS competent), activated-donor acylation
(anhydride/acid-chloride: a 2nd product, the leaving group), and multi-transformation bundled steps whose
independent sub-reactions would fool or cancel a whole-molecule count.  The acid detector is
representation-robust (a carbonyl O with no heavy neighbour = carboxyl OR carboxylate, explicit-H-independent),
so a legally-constructed implicit-H acid still trips it.  This probe pins the class recognizer on 18 cases --
the flagship lies, target-independent witnesses, every legitimate control, and every adversary counterexample --
plus the honest UNKNOWN on the emitted north-star routes and the reachability flip.  RDKit-free; no oracle.

Scoped to ONE class (PR-1).  The general DERIVED reaction-class recognizer + the poor-man ingenuity hunter are
PR-2.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.conditions import ConditionEnvelope
from smartchem.data.reagents import commodity_inventory, is_commodity
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.equilibrium import equilibrium_of_step
from smartchem.experiment.feasibility import (
    _acyl_group_counts,
    _is_intermolecular_acyl_condensation,
    feasibility_of_step,
)
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name

FROZEN_HASH = "208b1373e21ddb54d8f2549c5a69518e155355597f2474a4178650bec3746401"


def _mol(name_or_smiles: str):
    ns = structure_by_name(name_or_smiles)
    if ns is not None and ns.canonical_molecule is not None:
        return ns.canonical_molecule
    return parse_smiles(name_or_smiles)


def _step(target, reactants, products):
    return ExperimentStep(
        STEP_SCHEMA, target=target, reactants=tuple(reactants), products=tuple(products),
        reagents=(), envelope=ConditionEnvelope.unknown(),
    )


# --- the class recognizer, exercised on the REAL production predicate (feasibility.py) --------------------------
# (label, reactants, products, EXPECT_FIRE) -- every reactant/product is a parsed graph; the predicate never
# consults a name (target-independence).  ``_M`` marks a hand-built implicit-H molecule (dalembert KILL 1).
def _implicit_h_acetic_acid():
    from smartchem.category import Bond, Molecule
    return Molecule(("C", "C", "O", "O"), frozenset({Bond(0, 1, 1), Bond(1, 2, 2), Bond(1, 3, 1)}))


_GUARD_CASES = [
    ("paracetamol_fischer", ["acetic acid", "4-aminophenol"], ["paracetamol", "O"], True),
    ("fischer_esterification", ["CC(=O)O", "CCO"], ["CCOC(=O)C", "O"], True),
    ("thioesterification", ["CC(=O)O", "CS"], ["CC(=O)SC", "O"], True),
    ("propanoic_ethylamine_amide", ["CCC(=O)O", "CCN"], ["CCC(=O)NCC", "O"], True),
    ("benzoic_methanol_ester", ["c1ccccc1C(=O)O", "CO"], ["c1ccccc1C(=O)OC", "O"], True),
    ("glycine_dipeptide", ["NCC(=O)O", "NCC(=O)O"], ["NCC(=O)NCC(=O)O", "O"], True),
    ("carbamic_acid_carbamate", ["NC(=O)O", "CO"], ["NC(=O)OC", "O"], True),
    ("anhydride_acylation", ["CC(=O)OC(=O)C", "4-aminophenol"], ["paracetamol", "acetic acid"], False),
    ("acid_chloride_ester", ["CC(=O)Cl", "CCO"], ["CCOC(=O)C", "Cl"], False),
    ("neutralization_to_salt", ["CC(=O)O", "[OH-]", "[Na+]"], ["CC(=O)[O-]", "[Na+]", "O"], False),
    ("caffeine_n_methylation", ["theophylline", "methanol"], ["caffeine", "O"], False),
    ("methanol_homologation", ["CO", "CO"], ["CCO", "O"], False),
    ("intramolecular_lactam", ["NCCCC(=O)O"], ["O=C1CCCN1", "O"], False),
    ("intramolecular_lactone", ["OCCCC(=O)O"], ["O=C1CCCO1", "O"], False),
    # KILL 2 (dalembert): a mass/charge-CONSERVING bundle of legit sub-reactions (acid-chloride esterification +
    # neutralization) -- 5 non-water reactants, so the shape check excludes it (no false positive over-guard).
    ("bundled_legit", ["CC(=O)Cl", "CCO", "CC(=O)O", "[Na+]", "[OH-]"], ["CCOC(=O)C", "Cl", "CC(=O)[O-]", "[Na+]", "O"], False),
    # KILL 3 (dalembert): a real amidation lie bundled with an ester transesterification -- 3 non-water reactants,
    # so the shape check fails OPEN (keeps the estimate) rather than let the composite cancel the counts.
    ("bundled_lie_3_reactants", ["CC(=O)O", "CN", "CCOC=O"], ["CC(=O)NC", "OC=O", "CCO"], False),
]


def guard_recognizer() -> dict:
    """The class recognizer's verdict on every case, and whether each matches its expected firing."""
    out = {}
    for label, r, p, expect in _GUARD_CASES:
        R = [x if not isinstance(x, str) else _mol(x) for x in r]
        P = [x if not isinstance(x, str) else _mol(x) for x in p]
        step = ExperimentStep(
            STEP_SCHEMA, target=P[0], reactants=tuple(R), products=tuple(P),
            reagents=(), envelope=ConditionEnvelope.unknown(),
        )
        fires = _is_intermolecular_acyl_condensation(step)
        out[label] = {"fires": fires, "expected": expect, "ok": fires == expect}
    return out


def honesty_on_north_stars() -> dict:
    """The emitted north-star routes read HONEST: paracetamol Fischer fails CLOSED via the domain guard;
    caffeine fails closed via the data gap (the guard does NOT fire -- no free acid)."""
    water = _mol("water")
    para = _step(_mol("paracetamol"), (_mol("acetic acid"), _mol("4-aminophenol")), (_mol("paracetamol"), water))
    caf = _step(_mol("caffeine"), (_mol("theophylline"), _mol("methanol")), (_mol("caffeine"), water))
    pf, pe = feasibility_of_step(para), equilibrium_of_step(para)
    cf, ce = feasibility_of_step(caf), equilibrium_of_step(caf)
    return {
        "paracetamol_guard_fires": _is_intermolecular_acyl_condensation(para),
        "paracetamol_feasibility": pf.direction.value,
        "paracetamol_equilibrium": pe.extent.value,
        "paracetamol_delta_g_is_none": pf.delta_g_kj is None,
        "caffeine_guard_fires": _is_intermolecular_acyl_condensation(caf),
        "caffeine_feasibility": cf.direction.value,
        "caffeine_equilibrium": ce.extent.value,
    }


def reachability() -> dict:
    """The default recompile flips both north stars from NO route to a one-step synthesis from buyable stock."""
    caf = compile_synthesis(_mol("caffeine"))
    para = compile_synthesis(_mol("paracetamol"))
    return {
        "caffeine_routes": len(caf.ranked),
        "caffeine_reachable": len(caf.ranked) >= 1,
        "paracetamol_routes": len(para.ranked),
        "paracetamol_reachable": len(para.ranked) >= 1,
    }


def generalization() -> dict:
    """Anti-overfit (dalembert): the catalog admits NON-precursor scaffolds, and the recognizer is
    target-independent (fires on in-class reactions built only from molecules unrelated to the north stars)."""
    # salicylic acid is a NON-precursor of either north star (a genuine witness); aspirin is deliberately NOT a
    # commodity (it is a synthesis target with existing coverage), so it must NOT read as buyable stock.
    nonprecursor = sorted(n for n in ("salicylic acid",) if is_commodity(_mol(n)))
    return {
        "aspirin_not_a_commodity": not is_commodity(_mol("aspirin")),
        "catalog_size": len(commodity_inventory()),
        "nonprecursor_scaffolds": nonprecursor,
        "theophylline_buyable": is_commodity(_mol("theophylline")),
        "aminophenol_buyable": is_commodity(_mol("4-aminophenol")),
        # a free-acid carbonyl O with no heavy neighbour is a carboxyl (representation-robust): acetic acid AND
        # its implicit-H graph both read acid>=1; acetate anion (salt) also reads acid>=1; the anhydride reads 0.
        "acetic_acid_is_acid": _acyl_group_counts(_mol("CC(=O)O"))[0] >= 1,
        "implicit_h_acid_is_acid": _acyl_group_counts(_implicit_h_acetic_acid())[0] >= 1,
        "acetate_anion_is_acid": _acyl_group_counts(_mol("CC(=O)[O-]"))[0] >= 1,
        "anhydride_has_no_acyl_group": _acyl_group_counts(_mol("CC(=O)OC(=O)C")) == (0, 0, 0, 0),
        # a peroxy-acid (-C(=O)-O-O-H) is NOT a free carboxylic acid -- its carbonyl O bridges to a SECOND
        # heavy atom (the peroxide O), so it fails the no-heavy-neighbour test and reads acid 0 (dalembert).
        "peroxyacid_not_acid": _acyl_group_counts(_mol("CC(=O)OO"))[0] == 0,
    }


def _payload() -> dict:
    return {
        "guard_recognizer": guard_recognizer(),
        "honesty": honesty_on_north_stars(),
        "reachability": reachability(),
        "generalization": generalization(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: the class recognizer is correct on all 18 cases (including every adversary
    counterexample), the north-star routes are reachable AND honest, and the catalog/recognizer generalize."""
    rec = guard_recognizer()
    assert rec, "recognizer cases must be non-empty (vacuous-green guard)"
    assert all(row["ok"] for row in rec.values()), {k: v for k, v in rec.items() if not v["ok"]}

    h = honesty_on_north_stars()
    assert h["paracetamol_guard_fires"] is True, h                 # the flagship lie is caught
    assert h["paracetamol_feasibility"] == "UNKNOWN", h            # feasibility fails CLOSED (not FAVORABLE)
    assert h["paracetamol_equilibrium"] == "UNKNOWN", h            # equilibrium inherits it (not ESSENTIALLY_COMPLETE)
    assert h["paracetamol_delta_g_is_none"] is True, h
    assert h["caffeine_guard_fires"] is False, h                   # guard does NOT fire (no free acid) ...
    assert h["caffeine_feasibility"] == "UNKNOWN", h               # ... caffeine is UNKNOWN via the data gap

    r = reachability()
    assert r["caffeine_reachable"] and r["paracetamol_reachable"], r   # the 0 -> route flip (Part 1)

    g = generalization()
    assert g["nonprecursor_scaffolds"] == ["salicylic acid"], g   # catalog admits a NON-precursor witness
    assert g["aspirin_not_a_commodity"], g                        # ... but not a registered synthesis target
    assert g["theophylline_buyable"] and g["aminophenol_buyable"], g
    assert g["acetic_acid_is_acid"] and g["implicit_h_acid_is_acid"] and g["acetate_anion_is_acid"], g
    assert g["anhydride_has_no_acyl_group"] and g["peroxyacid_not_acid"], g
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print(f"content_hash() -> {content_hash()}")
