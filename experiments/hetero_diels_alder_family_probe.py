"""HETERO-DIELS-ALDER-FAMILY-01 -- committed frozen evidence for the heteroatom-dienophile [4+2] families.

Mirrors :mod:`experiments.alkyne_diels_alder_family_probe` for the FIRST non-all-carbon Diels-Alder families
(:mod:`smartchem.diels_alder`'s :class:`AzaDielsAlderProvider` / :class:`OxaDielsAlderProvider`): the parent
disconnections (a tetrahydropyridine -> butadiene + imine; a dihydropyran -> butadiene + formaldehyde -- the
verified chemistry, product isomer confirmed on the kernel), opt-in (absent from the default registry), the
search_routes seam integration with its control, and NO cross-poach among the FOUR DA families (aza / oxa / alkene /
alkyne, locked apart by their heteroatom-bearing reaction centres) nor the three dehydrative oracle classes.
``content_hash()`` over ``_payload()`` is frozen so a silent behaviour change trips the paired test
(:mod:`tests.test_hetero_diels_alder_family_probe`).

Run: ``.venv/bin/python -m experiments.hetero_diels_alder_family_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.diels_alder import (
    AZA_DA, OXA_DA, AlkyneDielsAlderProvider, AzaDielsAlderProvider, DielsAlderProvider, OxaDielsAlderProvider,
)
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY, CappedScissionProvider, TransformProviderRegistry,
)

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "de854e453af8166131960d6402f6eaaac2f92a89f2b30467b96197ee4143c38b"


def _emit(provider, smiles: str) -> list[str]:
    """The sorted disconnection equations ``provider`` emits for ``smiles`` (``[]`` = none)."""
    transforms = provider.enumerate_transforms(parse_smiles(smiles), (), budget=100000)[0]
    return sorted(t.equation() for t in transforms)


def parent_aza_da() -> list[str]:
    """The consumer served: a tetrahydropyridine (C1C=CCCN1) disconnects to butadiene + methanimine."""
    return sorted(set(_emit(AzaDielsAlderProvider(), "C1C=CCCN1")))


def parent_oxa_da() -> list[str]:
    """The consumer served: a dihydropyran (C1C=CCCO1) disconnects to butadiene + formaldehyde."""
    return sorted(set(_emit(OxaDielsAlderProvider(), "C1C=CCCO1")))


def negatives_not_matched() -> dict[str, list[str]]:
    """Fail-closed near-misses: a saturated (no ring C=C) azinane/oxane, an aromatic pyridine/pyran, and the
    all-carbon cyclohexene all yield no hetero-DA transform for the family whose heteroatom they carry."""
    return {
        "aza_on_piperidine_saturated": _emit(AzaDielsAlderProvider(), "C1CCCCN1"),
        "aza_on_pyridine_aromatic": _emit(AzaDielsAlderProvider(), "c1ccncc1"),
        "oxa_on_oxane_saturated": _emit(OxaDielsAlderProvider(), "C1CCCCO1"),
        "oxa_on_furan_aromatic": _emit(OxaDielsAlderProvider(), "c1ccoc1"),
        "aza_on_cyclohexene_allcarbon": _emit(AzaDielsAlderProvider(), "C1CC=CCC1"),
    }


def classes_not_poached() -> dict[str, list[str]]:
    """Soundness vs the pre-existing whitelist: acyl/ether/N-alkylation substrates yield no hetero-DA transform."""
    return {f"{tag}:{s}": _emit(prov, s)
            for tag, prov in (("aza", AzaDielsAlderProvider()), ("oxa", OxaDielsAlderProvider()))
            for s in ("CC(=O)OC", "CCOCC", "CCN")}


def opt_in() -> dict[str, bool]:
    """Both providers are absent from the default registry (production search/ranking byte-unchanged)."""
    ids = DEFAULT_TRANSFORM_REGISTRY.provider_ids
    return {"diels-alder-aza-retro": "diels-alder-aza-retro" not in ids,
            "diels-alder-oxa-retro": "diels-alder-oxa-retro" not in ids}


def seam_integration() -> dict[str, dict[str, int]]:
    """Plugged through the UNCHANGED seam: search_routes finds the hetero-DA route WITH the provider, none without."""
    out = {}
    for tag, prov, adduct, dienophile in (("aza", AzaDielsAlderProvider(), "C1C=CCCN1", "C=N"),
                                          ("oxa", OxaDielsAlderProvider(), "C1C=CCCO1", "C=O")):
        target, buta, dp = parse_smiles(adduct), parse_smiles("C=CC=C"), parse_smiles(dienophile)
        reg = TransformProviderRegistry((CappedScissionProvider(), prov))
        with_da = len(search_routes(target, reagents=(), available=(buta, dp), registry=reg, max_depth=2).routes)
        without = len(search_routes(target, reagents=(), available=(buta, dp), max_depth=2).routes)
        out[tag] = {"with_provider": with_da, "default_registry": without}
    return out


def families_do_not_cross_poach() -> dict[str, list[str]]:
    """No DA family vouches another family's adduct: aza<->oxa, and the all-carbon alkene/alkyne families vouch
    neither hetero adduct (their rules cannot embed a heteroatom vertex; the hetero rules cannot embed all-carbon)."""
    return {
        "aza_provider_on_oxa_adduct": _emit(AzaDielsAlderProvider(), "C1C=CCCO1"),
        "oxa_provider_on_aza_adduct": _emit(OxaDielsAlderProvider(), "C1C=CCCN1"),
        "alkene_provider_on_aza_adduct": _emit(DielsAlderProvider(), "C1C=CCCN1"),
        "alkene_provider_on_oxa_adduct": _emit(DielsAlderProvider(), "C1C=CCCO1"),
        "alkyne_provider_on_aza_adduct": _emit(AlkyneDielsAlderProvider(), "C1C=CCCN1"),
        "alkyne_provider_on_oxa_adduct": _emit(AlkyneDielsAlderProvider(), "C1C=CCCO1"),
    }


def _payload() -> dict:
    return {
        "classes": [AZA_DA.class_label, OXA_DA.class_label],
        "parent_aza_da": parent_aza_da(),
        "parent_oxa_da": parent_oxa_da(),
        "negatives_not_matched": negatives_not_matched(),
        "classes_not_poached": classes_not_poached(),
        "opt_in": opt_in(),
        "seam_integration": seam_integration(),
        "families_do_not_cross_poach": families_do_not_cross_poach(),
    }


def content_hash() -> str:
    return sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """The frozen claims, checked structurally (independent of the hash) so the pins are readable."""
    p = _payload()
    return bool(
        p["classes"] == ["diels-alder-[4+2]-aza-tetrahydropyridine", "diels-alder-[4+2]-oxa-dihydropyran"]
        and p["parent_aza_da"] == ["C5H9N -> CH3N + C4H6"]
        and p["parent_oxa_da"] == ["C5H8O -> CH2O + C4H6"]
        and all(v == [] for v in p["negatives_not_matched"].values())
        and all(v == [] for v in p["classes_not_poached"].values())
        and all(p["opt_in"].values())
        and p["seam_integration"] == {"aza": {"with_provider": 1, "default_registry": 0},
                                      "oxa": {"with_provider": 1, "default_registry": 0}}
        and all(v == [] for v in p["families_do_not_cross_poach"].values())
    )


if __name__ == "__main__":
    print(json.dumps(_payload(), indent=2, sort_keys=True))
    print("content_hash:", content_hash())
    print("validate:", validate())
