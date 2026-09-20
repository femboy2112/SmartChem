"""VALENCE-PRECONDITION-01 -- committed frozen evidence for the charge-agnostic valence ceiling.

Reproducible harness for the round's MEASURED claims (experiments-are-committed): valences impossible in
EVERY charge state are refused at both seams (pentavalent carbon, hexavalent oxygen); real chemistry is NOT
false-rejected -- including the two adversary kills, net-neutral charge-separated species (carbon monoxide,
ozone; dalembert) and hypervalent halogen/iodine reagents (IF5, PhI(OAc)2, chloric acid, BrF3; evil-morty);
the parent Diels-Alder is unaffected; and the charge-blindness BOUNDARY is stated honestly (a hand-built
neutral ammonium, impossible only as a neutral, is admitted because the graph carries no per-atom formal
charge).  ``content_hash()`` over ``_payload()`` is frozen so a silent behaviour change trips the paired
test.  Design: docs/research/RULE_CALCULUS_VALENCE_PRECONDITION_v0.1.md.

Run: ``.venv/bin/python -m experiments.valence_precondition_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.category import Bond, Molecule
from smartchem.diels_alder import DielsAlderProvider, retro_da_disconnections
from smartchem.rule_calculus import BondGraph, Edge, RuleError
from smartchem.rule_calculus_bridge import _joined, valence_sane
from smartchem.smiles import parse_smiles

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "abaae41604b04d0b81e37a912c7ae797048c2c597e7381ccf3b57868c4e1c39f"


def _g(labels, edges):
    return BondGraph(tuple(labels), frozenset(Edge(*e) for e in edges))


def _pentavalent_carbon() -> Molecule:
    return Molecule(("C", "F", "F", "F", "F", "F"), frozenset({Bond(0, k, 1) for k in range(1, 6)}))


def _joined_accepts(smiles: str) -> bool:
    """True iff the parsed (net-neutral) species passes the valence gate through the Molecule->graph adapter."""
    try:
        _joined((parse_smiles(smiles),))
        return True
    except RuleError:
        return False


def impossible_rejected() -> dict[str, bool]:
    """Valences impossible in EVERY charge state are refused at both seams (True = correctly refused)."""
    try:
        _joined((_pentavalent_carbon(),))
        joined_refused = False
    except RuleError:
        joined_refused = True
    transforms, complete = DielsAlderProvider().enumerate_transforms(_pentavalent_carbon(), (), budget=100000)
    core_audits, core_complete = retro_da_disconnections(_g("CF", [(0, 1, 5)]))
    return {
        "pentavalent_carbon_joined_refused": joined_refused,
        "pentavalent_carbon_provider_drops": transforms == () and complete is True,
        "order5_cc_core_refused": core_audits == () and core_complete is True,
        "oxygen_degree_4_rejected": valence_sane(_g("OCC", [(0, 1, 2), (0, 2, 2)])) is False,
    }


def real_chemistry_accepted() -> dict[str, bool]:
    """No real neutral molecule is false-rejected -- the two adversary kills pinned (True = accepted)."""
    return {
        "carbon_monoxide": _joined_accepts("[C-]#[O+]"),   # dalembert KILL 2 (net-neutral charge-separated)
        "ozone": _joined_accepts("[O-][O+]=O"),
        "IF5": _joined_accepts("F[I](F)(F)(F)F"),           # evil-morty KILL 1 (hypervalent halogen/iodine)
        "PhI_diacetate": _joined_accepts("C[I](OC(C)=O)OC(C)=O"),
        "chloric_acid": _joined_accepts("O=[Cl](=O)O[H]"),
        "BrF3": _joined_accepts("F[Br](F)F"),
    }


def hand_built_hypervalent_accepted() -> dict[str, bool]:
    """Correctly-valenced expanded-octet chemistry passes valence_sane (True = accepted)."""
    return {
        "sulfate_S6": valence_sane(_g("SOOOO", [(0, 1, 2), (0, 2, 2), (0, 3, 1), (0, 4, 1)])),
        "PCl5_P5": valence_sane(_g("PClClClClCl", [(0, k, 1) for k in range(1, 6)])),
        "N2_N3": valence_sane(_g("NN", [(0, 1, 3)])),
    }


def charge_blindness_boundary() -> bool:
    """HONEST boundary: a hand-built NEUTRAL ammonium (N degree 4, impossible only as a neutral) is ADMITTED,
    because the graph carries no per-atom formal charge to tell it from a valid ion (True = admitted)."""
    neutral_ammonium = Molecule(("N", "H", "H", "H", "H"), frozenset({Bond(0, k, 1) for k in range(1, 5)}))
    return valence_sane(_joined((neutral_ammonium,))) is True


def parent_da_unaffected() -> list[str]:
    """The gate is a no-op on valid chemistry: cyclohexene still disconnects."""
    edges = DielsAlderProvider().enumerate_transforms(parse_smiles("C1CC=CCC1"), (), budget=100000)[0]
    return sorted(e.equation() for e in edges)


def _payload() -> dict:
    return {
        "impossible_rejected": impossible_rejected(),
        "real_chemistry_accepted": real_chemistry_accepted(),
        "hand_built_hypervalent_accepted": hand_built_hypervalent_accepted(),
        "charge_blindness_boundary_admits_neutral_ammonium": charge_blindness_boundary(),
        "parent_da_unaffected": parent_da_unaffected(),
    }


def content_hash() -> str:
    return sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """The frozen claims, checked structurally (independent of the hash) so the pins are readable."""
    p = _payload()
    return bool(
        all(p["impossible_rejected"].values())               # every impossible-in-any-state input refused
        and all(p["real_chemistry_accepted"].values())       # both adversary kills stay closed
        and all(p["hand_built_hypervalent_accepted"].values())
        and p["charge_blindness_boundary_admits_neutral_ammonium"] is True   # the disclosed boundary
        and p["parent_da_unaffected"] == ["C6H10 -> C2H4 + C4H6"]
    )


if __name__ == "__main__":
    print(json.dumps(_payload(), indent=2, sort_keys=True))
    print("content_hash:", content_hash())
    print("validate:", validate())
