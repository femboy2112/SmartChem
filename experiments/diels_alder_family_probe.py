"""DIELS-ALDER-FAMILY-01 -- committed frozen evidence for the first NEW reaction family on the rule_calculus kernel.

Reproducible harness for the round's MEASURED claims (experiments-are-committed): the parent Diels-Alder
disconnection, the evil-morty ketene KILL now closed by guard 2b, dalembert's norbornene coverage, the three
existing oracle classes NOT poached, opt-in (absent from the default registry), and the search_routes seam
integration with its control. ``content_hash()`` over ``_payload()`` is frozen so a silent behaviour change trips
the paired test (:mod:`tests.test_diels_alder_family_probe`). Design: docs/research/RULE_CALCULUS_DIELS_ALDER_FAMILY_v0.1.md.

Run: ``.venv/bin/python -m experiments.diels_alder_family_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.diels_alder import DA_CLASS, DielsAlderProvider
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY, CappedScissionProvider, TransformProviderRegistry,
)

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "a0e61e51cb39196187e8d61aa5999d275a663900ad35818a8c11f3d1fb067faa"


def _emit(smiles: str) -> list[str]:
    """The sorted DA disconnection equations the opt-in provider emits for ``smiles`` (``[]`` = none, fail-closed)."""
    transforms = DielsAlderProvider().enumerate_transforms(parse_smiles(smiles), (), budget=100000)[0]
    return sorted(t.equation() for t in transforms)


def parent_da() -> list[str]:
    """The consumer served: cyclohexene disconnects to butadiene + ethylene (the parent [4+2])."""
    return _emit("C1CC=CCC1")


def ketene_kill_closed() -> dict[str, list[str]]:
    """evil-morty CRITICAL kill, closed: enones/tetralones must NOT vouch (a ring carbonyl -> ketene is fiction)."""
    return {s: _emit(s) for s in ("O=C1CCCC=C1", "O=C1CCC=CC1", "O=C1CCCc2ccccc21")}


def norbornene_genuine() -> list[str]:
    """dalembert coverage: a single-atom-bridged bicyclic IS a genuine retro-DA (-> cyclopentadiene + ethylene)."""
    return _emit("C1CC2CC1C=C2")


def three_classes_not_poached() -> dict[str, list[str]]:
    """Soundness vs the existing whitelist: acyl/ether/N-alkylation substrates + aromatic near-miss yield no DA."""
    return {s: _emit(s) for s in ("CC(=O)OC", "CCOCC", "CCN", "c1ccccc1")}


def opt_in() -> bool:
    """The provider is absent from the default registry (production search/ranking byte-unchanged)."""
    return "diels-alder-retro" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids


def seam_integration() -> dict[str, int]:
    """Plugged through the UNCHANGED seam: search_routes finds the DA route WITH the provider, none without it."""
    chx, buta, eth = parse_smiles("C1CC=CCC1"), parse_smiles("C=CC=C"), parse_smiles("C=C")
    reg = TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))
    with_da = len(search_routes(chx, reagents=(), available=(buta, eth), registry=reg, max_depth=2).routes)
    without = len(search_routes(chx, reagents=(), available=(buta, eth), max_depth=2).routes)
    return {"with_da_provider": with_da, "default_registry": without}


def _payload() -> dict:
    return {
        "class": DA_CLASS,
        "parent_da": parent_da(),
        "ketene_kill_closed": ketene_kill_closed(),
        "norbornene_genuine": norbornene_genuine(),
        "three_classes_not_poached": three_classes_not_poached(),
        "opt_in": opt_in(),
        "seam_integration": seam_integration(),
    }


def content_hash() -> str:
    return sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """The frozen claims, checked structurally (independent of the hash) so the pins are readable."""
    p = _payload()
    return bool(
        p["class"] == "diels-alder-[4+2]-carbocyclic"
        and p["parent_da"] == ["C6H10 -> C2H4 + C4H6"]
        and all(v == [] for v in p["ketene_kill_closed"].values())      # ketene fiction stays killed
        and p["norbornene_genuine"] == ["C7H10 -> C2H4 + C5H6"]
        and all(v == [] for v in p["three_classes_not_poached"].values())
        and p["opt_in"] is True
        and p["seam_integration"] == {"with_da_provider": 1, "default_registry": 0}
    )


if __name__ == "__main__":
    print(json.dumps(_payload(), indent=2, sort_keys=True))
    print("content_hash:", content_hash())
    print("validate:", validate())
