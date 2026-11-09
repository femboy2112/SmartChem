"""Issue #130 -- the SEARCH/STOCK identity layer collapses configuration and isotope (DEFECT PIN).

OPERATION XXVI, WAVE 2. Research-only; NO production behaviour changes. Extends the XXV design doc
``docs/research/IDENTITY_CARRIER_DESIGN_XXV.md`` (which characterised the *perception* layer and pinned its
controls in the sandbox suite) with the unpinned, synthesis-relevant half: route-search terminals and stock
supply are keyed on CONSTITUTION-ONLY identity, so the configuration and isotopic distinctions the perception
layer already carries are DISCARDED the moment they reach the search/stock key.

This is the exact hazard OPERATION XXVI phase I-D names:

    "A system that knows chemical constitution but not configuration cannot silently treat two enantiomeric
     stocks as interchangeable."

GROUND TRUTH (what is actually true in the world, independent of SmartChem):
  * (R)- and (S)-alanine are DIFFERENT substances (non-superimposable mirror images).
  * (E)- and (Z)-2-butene are DIFFERENT substances (geometric isomers, not interconvertible without breaking pi).
  * CD4 and CH4, and 13C-ethane and ethane, are DIFFERENT substances (isotopologues).
  * ethanol and dimethyl ether are DIFFERENT substances (different constitution) -- the CONTROL.

These tests are GREEN on main because the search/stock key COLLAPSES the first four pairs to one identity while
correctly separating the control. That collapse is the DEFECT. A successor that keys route terminals / stock on a
configuration-aware identity (the versioned migration sketched in STEREO_SEARCH_IDENTITY_130_XXVI.md) flips the
``==`` assertions in :func:`test_search_key_collapses_configuration_and_isotope` and
:func:`test_structure_key_is_configuration_blind` to ``!=``; GROUND TRUTH distinctness never changes.

The anti-vacuity guard is :func:`test_constitution_control_stays_distinct`: if the search key were simply broken
(collapsing *everything*), the control would collapse too. It does not -- the key is constitution-SOUND and
configuration-BLIND, which is precisely the #130 shape.

:func:`test_perception_layer_carries_the_discarded_information` proves the information is not lost at the parser --
it is perceived (or fail-closed to ``None``) one layer up and then thrown away at the search key.
"""

from __future__ import annotations

import pytest

from smartchem.smiles import parse_smiles, parse_smiles_features, resonance_identity
from smartchem.experiment.stock import structure_key
from smartchem.identity import LayeredIdentity, MatchLayer, same_identity_at


# (label, SMILES a, SMILES b) -- pairs that are DISTINCT substances but share one constitution.
COLLAPSING_PAIRS = [
    ("(R)- vs (S)-alanine (enantiomers)", "N[C@@H](C)C(=O)O", "N[C@H](C)C(=O)O"),
    ("(E)- vs (Z)-2-butene (geometric)", "C/C=C/C", r"C/C=C\C"),
    ("CD4 vs CH4 (isotopologue)", "[2H]C([2H])([2H])[2H]", "C"),
    ("13C-ethane vs ethane (isotopologue)", "[13CH3]C", "CC"),
]

# The CONTROL: genuinely different CONSTITUTION. The search key MUST separate this, or it is merely broken.
CONSTITUTION_CONTROL = ("ethanol vs dimethyl ether", "CCO", "COC")


def _rid(smiles: str) -> str:
    return resonance_identity(parse_smiles(smiles))


def _skey(smiles: str) -> str:
    return structure_key(parse_smiles(smiles))


@pytest.mark.parametrize("label,a,b", COLLAPSING_PAIRS, ids=[p[0] for p in COLLAPSING_PAIRS])
def test_search_key_collapses_configuration_and_isotope(label: str, a: str, b: str) -> None:
    """DEFECT PIN: the constitution-only route-search terminal key (resonance_identity) treats distinct
    substances as the same terminal. A configuration-aware successor flips this ``==`` to ``!=``."""
    assert _rid(a) == _rid(b), (
        f"{label}: resonance_identity now SEPARATES these -- the #130 search-key collapse has been fixed. "
        f"Flip this assertion to != and update STEREO_SEARCH_IDENTITY_130_XXVI.md."
    )


@pytest.mark.parametrize("label,a,b", COLLAPSING_PAIRS, ids=[p[0] for p in COLLAPSING_PAIRS])
def test_structure_key_is_configuration_blind(label: str, a: str, b: str) -> None:
    """DEFECT PIN: stock supply is keyed by structure_key, which is equally configuration-blind, so an
    enantiomeric/isotopic stock would satisfy a demand for its distinct partner."""
    assert _skey(a) == _skey(b), (
        f"{label}: structure_key now SEPARATES these -- stock supply is no longer configuration-blind. "
        f"Flip this assertion to != and update the design doc."
    )


def test_constitution_control_stays_distinct() -> None:
    """ANTI-VACUITY: the collapse is specific to configuration/isotope, not a broken key that collapses
    everything. A genuine constitution difference is kept distinct by BOTH keys."""
    _, a, b = CONSTITUTION_CONTROL
    assert _rid(a) != _rid(b), "resonance_identity wrongly collapses ethanol and dimethyl ether"
    assert _skey(a) != _skey(b), "structure_key wrongly collapses ethanol and dimethyl ether"


def test_enantiomeric_stock_satisfies_opposite_demand() -> None:
    """The synthesis hazard made concrete (phase I-D): a stock set keyed by structure_key that holds ONLY
    (R)-alanine reports an (S)-alanine target as 'in stock'. Pinned as a DEFECT: the two are different
    substances, but the supply layer cannot tell them apart."""
    r_alanine = "N[C@@H](C)C(=O)O"
    s_alanine = "N[C@H](C)C(=O)O"
    # Emulate stock membership exactly as search does: a set of structure_keys.
    stock_keyset = {_skey(r_alanine)}
    assert _skey(s_alanine) in stock_keyset, (
        "structure_key now distinguishes the enantiomers -- the configuration-blind supply defect is fixed."
    )


def test_perception_layer_carries_the_discarded_information() -> None:
    """The information is NOT lost at the parser: the feature-aware perception layer either SEPARATES the
    distinct substances (CONFIGURATION/ISOTOPIC) or fail-closes to ``None`` when it cannot perceive a marked
    element. It is the constitution-only SEARCH key, not the parser, that discards it."""
    def layered(smiles: str) -> LayeredIdentity:
        molecule, features = parse_smiles_features(smiles)
        return LayeredIdentity.of_molecule(molecule, features)

    # (R)/(S)-alanine: same constitution, SEPARATED at configuration.
    r = layered("N[C@@H](C)C(=O)O")
    s = layered("N[C@H](C)C(=O)O")
    assert same_identity_at(r, s, MatchLayer.CONSTITUTION) is True
    assert same_identity_at(r, s, MatchLayer.CONFIGURATION) is False

    # CD4/CH4: same constitution AND same configuration, SEPARATED at isotopic.
    cd4 = layered("[2H]C([2H])([2H])[2H]")
    ch4 = layered("C")
    assert same_identity_at(cd4, ch4, MatchLayer.CONSTITUTION) is True
    assert same_identity_at(cd4, ch4, MatchLayer.CONFIGURATION) is True
    assert same_identity_at(cd4, ch4, MatchLayer.ISOTOPIC) is False

    # (E)/(Z)-2-butene: perception FAIL-CLOSES (None) rather than guessing a marked geometry it cannot resolve.
    e = layered("C/C=C/C")
    z = layered(r"C/C=C\C")
    assert same_identity_at(e, z, MatchLayer.CONFIGURATION) is None
