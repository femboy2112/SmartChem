"""Item 6 -- the Woodward-Hoffmann selection-rule layer (:mod:`smartchem.pericyclic_selection`), a THEOREM-CONSTANT
annotation (no geometry oracle).

Pins: (1) the WH rule computes correctly from electron count -- thermal 4n+2 -> Hueckel (suprafacial/disrotatory),
thermal 4n -> Moebius (antarafacial/conrotatory), photochemical inverts; (2) every recognized pericyclic family maps
to a selection and every non-pericyclic input maps to None; (3) the electron counts are the textbook constants
(cycloaddition 6, [3,3] 6, 4pi 4, 6pi 6).  Endo/exo PREDICTION is a documented verified-defer (needs a TS oracle that
does not exist in-tree), so it is NOT asserted here.
"""
from __future__ import annotations

import pytest

import smartchem.diels_alder as da
import smartchem.lateral_rewrite as lr
from smartchem.pericyclic_selection import (
    CYCLOADDITION, ELECTROCYCLIZATION, SIGMATROPIC, _PERICYCLIC,
    selection_for_class, selection_for_family, woodward_hoffmann,
)

_DA_FAMILIES = [da.AZA_DA, da.OXA_DA, da.THIA_DA, da.AZA_DIENE_DA, da.OXA_DIENE_DA, da.THIA_DIENE_DA]
_LATERAL_FAMILIES = [lr.COPE, lr.CLAISEN, lr.AZA_CLAISEN, lr.THIA_CLAISEN, lr.ELECTRO_4PI, lr.ELECTRO_6PI]


def test_all_fourteen_pericyclic_classes_registered():
    assert len(_PERICYCLIC) == 14


def test_woodward_hoffmann_theorem_constants():
    # electrocyclization: 4pi (4n) thermal conrotatory, photochemical disrotatory; 6pi (4n+2) thermal disrotatory.
    e4 = woodward_hoffmann(ELECTROCYCLIZATION, 4)
    assert e4.aromatic_transition_state is False
    assert e4.thermal_mode == "conrotatory" and e4.photochemical_mode == "disrotatory"
    e6 = woodward_hoffmann(ELECTROCYCLIZATION, 6)
    assert e6.aromatic_transition_state is True and e6.thermal_mode == "disrotatory"
    # cycloaddition / sigmatropic: 6 electrons (4n+2) thermal all-suprafacial.
    for arch in (CYCLOADDITION, SIGMATROPIC):
        s = woodward_hoffmann(arch, 6)
        assert s.aromatic_transition_state is True and "suprafacial-suprafacial" in s.thermal_mode


def test_photochemical_inverts_thermal():
    for arch in (CYCLOADDITION, SIGMATROPIC, ELECTROCYCLIZATION):
        for e in (4, 6, 8):
            s = woodward_hoffmann(arch, e)
            assert s.thermal_mode != s.photochemical_mode


@pytest.mark.parametrize("family", _DA_FAMILIES, ids=lambda f: f.class_label)
def test_da_families_are_6e_cycloadditions(family):
    s = selection_for_family(family)
    assert s is not None and s.archetype == CYCLOADDITION and s.electron_count == 6
    assert "suprafacial" in s.thermal_mode


@pytest.mark.parametrize("family,arch,ecount", [
    (lr.COPE, SIGMATROPIC, 6), (lr.CLAISEN, SIGMATROPIC, 6), (lr.AZA_CLAISEN, SIGMATROPIC, 6),
    (lr.THIA_CLAISEN, SIGMATROPIC, 6), (lr.ELECTRO_4PI, ELECTROCYCLIZATION, 4), (lr.ELECTRO_6PI, ELECTROCYCLIZATION, 6),
], ids=lambda x: getattr(x, "class_label", x))
def test_lateral_families_selection(family, arch, ecount):
    s = selection_for_family(family)
    assert s is not None and s.archetype == arch and s.electron_count == ecount


def test_all_carbon_da_via_class_string():
    for cl in (da.DA_CLASS, da.ALKYNE_DA_CLASS):
        s = selection_for_class(cl)
        assert s is not None and s.archetype == CYCLOADDITION and s.electron_count == 6


def test_non_pericyclic_and_none_map_to_none():
    assert selection_for_class("acyl condensation (esterification/amidation)") is None
    assert selection_for_class(None) is None
    assert selection_for_family(object()) is None      # a non-family object has no class_label


def test_bad_electron_count_refused():
    for bad in (0, -2, 3, 5):
        with pytest.raises(ValueError):
            woodward_hoffmann(CYCLOADDITION, bad)


def test_unknown_archetype_refused():
    with pytest.raises(ValueError):
        woodward_hoffmann("retro-cheletropic", 6)
