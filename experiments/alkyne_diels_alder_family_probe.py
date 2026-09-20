"""ALKYNE-DIELS-ALDER-FAMILY-01 -- committed frozen evidence for the alkyne-dienophile [4+2] sibling family.

Mirrors :mod:`experiments.diels_alder_family_probe` for the alkyne-dienophile family
(:mod:`smartchem.diels_alder`'s :class:`AlkyneDielsAlderProvider`): the parent disconnection (1,4-cyclohexadiene ->
butadiene + acetylene, the verified 1,4 chemistry, NOT 1,3), opt-in (absent from the default registry), the
search_routes seam integration with its control, and the FOUR pre-existing oracle classes (the three dehydrative
classes plus the alkene-dienophile DA family) staying not-poached. ``content_hash()`` over ``_payload()`` is frozen
so a silent behaviour change trips the paired test (:mod:`tests.test_alkyne_diels_alder_family_probe`).

Run: ``.venv/bin/python -m experiments.alkyne_diels_alder_family_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.diels_alder import ALKYNE_DA_CLASS, AlkyneDielsAlderProvider, DielsAlderProvider
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY, CappedScissionProvider, TransformProviderRegistry,
)

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "cbf1962582257d0902dc07886bd8a469fb5e3ca596c32d63e5f608c95aeb8b8f"


def _emit(smiles: str) -> list[str]:
    """The sorted alkyne-DA disconnection equations the opt-in provider emits for ``smiles`` (``[]`` = none)."""
    transforms = AlkyneDielsAlderProvider().enumerate_transforms(parse_smiles(smiles), (), budget=100000)[0]
    return sorted(t.equation() for t in transforms)


def parent_alkyne_da() -> list[str]:
    """The consumer served: 1,4-cyclohexadiene disconnects to butadiene + acetylene (the verified 1,4 [4+2]).

    1,4-cyclohexadiene's own 2-fold ring symmetry means the guarded enumerator legitimately finds TWO distinct
    vertex-role matches that both yield this SAME product pair (isomorphism dedup is deliberately not performed
    by the kernel) -- so the sorted, de-duplicated equation SET is the stable, freezable evidence, not a raw count.
    """
    return sorted(set(_emit("C1=CCC=CC1")))


def alkene_pattern_is_not_matched() -> list[str]:
    """1,3-cyclohexadiene (the alkENE family's own adjacent-double-bond pattern) is NOT a match for this family."""
    return _emit("C1=CC=CCC1")


def four_classes_not_poached() -> dict[str, list[str]]:
    """Soundness vs the pre-existing whitelist: acyl/ether/N-alkylation substrates, the alkene-DA family's own
    product (cyclohexene), and an aromatic near-miss all yield no alkyne-DA transform."""
    return {s: _emit(s) for s in ("CC(=O)OC", "CCOCC", "CCN", "C1CC=CCC1", "c1ccccc1")}


def opt_in() -> bool:
    """The provider is absent from the default registry (production search/ranking byte-unchanged)."""
    return "diels-alder-alkyne-retro" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids


def seam_integration() -> dict[str, int]:
    """Plugged through the UNCHANGED seam: search_routes finds the alkyne-DA route WITH the provider, none without."""
    chd, buta, ac = parse_smiles("C1=CCC=CC1"), parse_smiles("C=CC=C"), parse_smiles("C#C")
    reg = TransformProviderRegistry((CappedScissionProvider(), AlkyneDielsAlderProvider()))
    with_da = len(search_routes(chd, reagents=(), available=(buta, ac), registry=reg, max_depth=2).routes)
    without = len(search_routes(chd, reagents=(), available=(buta, ac), max_depth=2).routes)
    return {"with_alkyne_da_provider": with_da, "default_registry": without}


def sibling_families_do_not_cross_poach() -> dict[str, list[str]]:
    """The alkene-DA family's own registry does not vouch this family's molecule, and vice versa (mixed registry
    tagging stays separated by ``provider_id``/``witness_kind``, checked directly at the oracle layer elsewhere)."""
    alkene = DielsAlderProvider().enumerate_transforms(parse_smiles("C1=CCC=CC1"), (), budget=100000)[0]
    alkyne = AlkyneDielsAlderProvider().enumerate_transforms(parse_smiles("C1CC=CCC1"), (), budget=100000)[0]
    return {
        "alkene_provider_on_1_4_chd": sorted(t.equation() for t in alkene),
        "alkyne_provider_on_cyclohexene": sorted(t.equation() for t in alkyne),
    }


def _payload() -> dict:
    return {
        "class": ALKYNE_DA_CLASS,
        "parent_alkyne_da": parent_alkyne_da(),
        "alkene_pattern_is_not_matched": alkene_pattern_is_not_matched(),
        "four_classes_not_poached": four_classes_not_poached(),
        "opt_in": opt_in(),
        "seam_integration": seam_integration(),
        "sibling_families_do_not_cross_poach": sibling_families_do_not_cross_poach(),
    }


def content_hash() -> str:
    return sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """The frozen claims, checked structurally (independent of the hash) so the pins are readable."""
    p = _payload()
    return bool(
        p["class"] == "diels-alder-[4+2]-alkyne-cyclohexadiene"
        and p["parent_alkyne_da"] == ["C6H8 -> C2H2 + C4H6"]
        and p["alkene_pattern_is_not_matched"] == []
        and all(v == [] for v in p["four_classes_not_poached"].values())
        and p["opt_in"] is True
        and p["seam_integration"] == {"with_alkyne_da_provider": 1, "default_registry": 0}
        and p["sibling_families_do_not_cross_poach"] == {
            "alkene_provider_on_1_4_chd": [],
            "alkyne_provider_on_cyclohexene": [],
        }
    )


if __name__ == "__main__":
    print(json.dumps(_payload(), indent=2, sort_keys=True))
    print("content_hash:", content_hash())
    print("validate:", validate())
