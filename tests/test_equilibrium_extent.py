"""Item 4 -- the declared-reference general-Δn equilibrium extent solver (:func:`smartchem.experiment.equilibrium.
equilibrium_extent`), the sound extension that closes the Δn != 0 case _ideal_conversion correctly refuses.

Pins: (1) it solves the Haber Δn=-2 case _ideal_conversion returns UNKNOWN for, with the extent respecting exact mass
balance; (2) the root is physically admissible and the solver is monotone/unique (a known-K calibration + a
Le Chatelier shift when product is added); (3) fail-closed: no K -> None, absent reactant -> None; (4) the honest
boundary is carried in the note and it is NEVER a practical yield or capability verdict (label-only, checked in the
note string).
"""
from __future__ import annotations

from smartchem.experiment.equilibrium import equilibrium_extent, equilibrium_of_step
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

H2 = parse_smiles("[H][H]")
O2 = parse_smiles("O=O")
N2 = parse_smiles("N#N")
H2O = parse_smiles("O")
NH3 = parse_smiles("N")
ETHANOL = parse_smiles("CCO")


def _haber():
    return ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))   # N2 + 3H2 -> 2NH3, Δn = -2


def test_ideal_conversion_still_refuses_delta_n_nonzero():
    # the existing closed form correctly returns UNKNOWN conversion for Haber (Δn != 0); the new solver is the opt-in.
    se = equilibrium_of_step(_haber())
    assert se.log10_k is not None and se.conversion_fraction is None


def test_haber_extent_solved_with_declared_reference():
    sol = equilibrium_extent(_haber(), initial_concentrations={N2: 1.0, H2: 3.0, NH3: 0.0})
    assert sol is not None
    assert 0.9 < sol.conversion <= 1.0                    # K ~ 5e5 at 298 K -> high conversion
    # exact mass balance on nitrogen at equilibrium: 2*[N2] + [NH3] == 2*(initial N2) == 2.0
    assert abs(2 * sol.equilibrium_concentrations[N2] + sol.equilibrium_concentrations[NH3] - 2.0) < 1e-9
    # every equilibrium concentration is non-negative (physically admissible root)
    assert all(c >= -1e-12 for c in sol.equilibrium_concentrations.values())


def test_le_chatelier_added_product_lowers_conversion():
    base = equilibrium_extent(_haber(), initial_concentrations={N2: 1.0, H2: 3.0, NH3: 0.0})
    pushed = equilibrium_extent(_haber(), initial_concentrations={N2: 1.0, H2: 3.0, NH3: 2.0})
    assert pushed.conversion < base.conversion            # Le Chatelier: added product suppresses forward extent


def test_water_synthesis_is_essentially_complete():
    water = ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O))    # 2H2 + O2 -> 2H2O, astronomically large K
    sol = equilibrium_extent(water, initial_concentrations={H2: 2.0, O2: 1.0, H2O: 0.0})
    assert sol is not None and sol.conversion == 1.0      # exact forward boundary


def test_reverse_favored_reaction_barely_proceeds():
    split = ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2))     # 2H2O -> 2H2 + O2, tiny K
    sol = equilibrium_extent(split, initial_concentrations={H2O: 2.0, H2: 0.0, O2: 0.0})
    assert sol is not None and sol.conversion < 1e-6      # essentially no forward extent


def test_fail_closed_absent_reactant_and_no_thermo():
    # an absent reactant -> None (no forward reaction to solve)
    assert equilibrium_extent(_haber(), initial_concentrations={N2: 0.0, H2: 3.0, NH3: 0.0}) is None
    # no sourced OR derivable thermo (derive=False forces the seed table only; ethanol is off-seed) -> None
    combustion = ExperimentStep.assembling(
        H2O, (ETHANOL, O2, O2, O2), (parse_smiles("O=C=O"), parse_smiles("O=C=O"), H2O, H2O, H2O))
    assert equilibrium_extent(combustion, initial_concentrations={ETHANOL: 1.0, O2: 3.0}, derive=False) is None


def test_note_labels_the_boundary_ranking_only():
    sol = equilibrium_extent(_haber(), initial_concentrations={N2: 1.0, H2: 3.0, NH3: 0.0})
    assert "ranking/evidence only" in sol.note
    assert "NOT a practical yield" in sol.note or "capability" in sol.note


def test_reference_c_must_be_positive():
    import pytest
    with pytest.raises(ValueError):
        equilibrium_extent(_haber(), initial_concentrations={N2: 1.0, H2: 3.0}, reference_c=0.0)


def test_net_empty_step_fails_closed_to_none_not_a_crash():
    # dalembert's kill: a net-empty (fully-cancelling) step -- a self-map -- has an empty coefficient vector, so the
    # forward-limit bracket would be min() over nothing.  The documented fail-closed contract must return None, not
    # raise ValueError.  (Production CappedScission never emits a self-map; this hardens the public opt-in surface.)
    self_map = ExperimentStep.assembling(NH3, (NH3,), (NH3,))     # N -> N, conserving, constructible
    assert equilibrium_extent(self_map, initial_concentrations={NH3: 1.0}) is None


def test_net_reverse_reaction_gives_none_conversion_never_out_of_0_1():
    # evil-morty KILL #1: with an initial product present and Q > K, the reaction runs net-BACKWARD (xi < 0).  The
    # forward `conversion` field must NOT emit a negative value (its [0,1] contract) -- it is None (undefined for a
    # reverse reaction), and the signed direction lives in `xi`.
    split = ExperimentStep.assembling(H2, (H2O, H2O), (H2, H2, O2))     # 2H2O -> 2H2 + O2
    sol = equilibrium_extent(split, initial_concentrations={H2O: 1.0, H2: 1.0, O2: 0.5}, log10_k=-1.0)
    assert sol is not None
    assert sol.xi < 0.0                 # ran net-backward (consumed product)
    assert sol.conversion is None       # forward conversion undefined -> None, never a negative that escapes [0,1]
    # and a genuine forward reaction still reports a conversion in [0, 1]
    fwd = equilibrium_extent(split, initial_concentrations={H2O: 2.0, H2: 0.0, O2: 0.0}, log10_k=-1.0)
    assert fwd.conversion is not None and 0.0 <= fwd.conversion <= 1.0
