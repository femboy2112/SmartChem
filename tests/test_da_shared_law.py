"""Item F: the ONE shared product-config law behind every Diels-Alder family's edge + provider.

The alkene, alkyne and three hetero families historically each carried a byte-identical ``forget()`` and provider
enumeration body.  Item F factored the single law into :func:`~smartchem.diels_alder._da_forget` (the composition
image) and :func:`~smartchem.diels_alder._enumerate_da_transforms` (the config-canonical enumeration), WITHOUT
merging the edge classes (their qualnames are baked into the content digest, so merging would move a frozen probe).
These pins assert the law is genuinely shared and the product presentation is config-canonical across ALL families,
so a future re-duplication that drifts is caught.
"""
from __future__ import annotations

import pytest

from smartchem.diels_alder import (
    AlkyneDielsAlderProvider, AzaDielsAlderProvider, AzaDieneDielsAlderProvider, DielsAlderProvider,
    OxaDielsAlderProvider, OxaDieneDielsAlderProvider, ThiaDielsAlderProvider, _da_forget,
)
from smartchem.smiles import parse_smiles

# (provider, an adduct that family disconnects)
_FAMILIES = [
    (DielsAlderProvider(), "C1CC=CCC1"),           # alkene -> cyclohexene
    (AlkyneDielsAlderProvider(), "C1=CCC=CC1"),    # alkyne -> 1,4-cyclohexadiene
    (AzaDielsAlderProvider(), "C1C=CCCN1"),        # aza dienophile
    (OxaDielsAlderProvider(), "C1C=CCCO1"),        # oxa dienophile
    (ThiaDielsAlderProvider(), "C1C=CCCS1"),       # thia dienophile
    (AzaDieneDielsAlderProvider(), "N1C=CCCC1"),   # 1-azadiene
    (OxaDieneDielsAlderProvider(), "O1C=CCCC1"),   # 1-oxadiene
]
_IDS = ["alkene", "alkyne", "aza", "oxa", "thia", "aza-diene", "oxa-diene"]


@pytest.mark.parametrize("provider,adduct", _FAMILIES, ids=_IDS)
def test_every_family_edge_forget_uses_the_one_shared_law(provider, adduct):
    edge = provider.enumerate_transforms(parse_smiles(adduct), (), budget=100000)[0][0]
    # the edge's composition image is EXACTLY what the shared _da_forget law produces from its own fields.
    assert edge.forget() == _da_forget(edge.reactant, edge.products)


@pytest.mark.parametrize("provider,adduct", _FAMILIES, ids=_IDS)
def test_every_family_presents_products_deterministically(provider, adduct):
    # the shared enumeration law reads products back through the ONE _config canonicalisation, so re-enumerating the
    # same adduct yields byte-identical product presentations every time (config-canonical, family-independent).
    mol = parse_smiles(adduct)
    once = provider.enumerate_transforms(mol, (), budget=100000)[0]
    twice = provider.enumerate_transforms(mol, (), budget=100000)[0]
    assert [e.equation() for e in once] == [e.equation() for e in twice]
    assert once and all(len(e.products) == 2 for e in once)
