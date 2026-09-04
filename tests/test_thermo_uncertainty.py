"""THERMO-UNC-01 (item 3b): the sourced measurement uncertainty is now a first-class field on the PRIMARY thermo
type (`data.thermo.ThermoRef`, the phase/grade record the manifest row first named), populated from the same dated
CODATA seed, guarded non-vacuously, and -- crucially -- IDENTITY-NEUTRAL (a ± is metadata, so no digest/golden moves)
and reachable by a consumer through `resolve_thermo`.
"""

import pytest

from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef
from smartchem.experiment.feasibility import resolve_thermo
from smartchem.smiles import parse_smiles


def _ref(formula, name):
    return next(r for r in DEFAULT_THERMO.records if r.formula == formula and r.name == name)


class TestSeedCarriesSourcedUncertainties:
    def test_codata_sourced_values_carry_their_cited_pm(self):
        # the CODATA-sourced ΔfH° values carry the CODATA ± (cross-checked against experiments.thermo_codata_seed).
        assert _ref("H2O", "water").uncertainty_dhf_kj == 0.040
        assert _ref("CO", "carbon monoxide").uncertainty_dhf_kj == 0.17
        assert _ref("CO2", "carbon dioxide").uncertainty_dhf_kj == 0.13
        assert _ref("H2O", "water").uncertainty_s_j_per_mol_k == 0.03

    def test_reference_states_carry_the_convention_zero_dfh_uncertainty(self):
        # ΔfH° = 0 EXACTLY by convention -> a 0.0 uncertainty is legitimate (a definition, not a hollow value).
        for f, n in (("H2", "hydrogen"), ("O2", "oxygen"), ("N2", "nitrogen")):
            r = _ref(f, n)
            assert r.dhf_kj_per_mol == 0.0 and r.uncertainty_dhf_kj == 0.0

    def test_a_nist_value_without_a_sourced_pm_is_honest_none(self):
        # ammonia and methane are NIST-sourced here with no stated ± -> None (honest absence), NOT a borrowed CODATA
        # ± (no provenance mixing) and NOT a fabricated 0.0.
        assert _ref("H3N", "ammonia").uncertainty_dhf_kj is None
        assert _ref("CH4", "methane").uncertainty_dhf_kj is None
        assert _ref("N2", "nitrogen").uncertainty_s_j_per_mol_k is None  # N2 S° is NIST-cited, no ± stated


class TestNonVacuousGuard:
    def test_a_hollow_zero_dfh_uncertainty_on_a_nonreference_value_is_refused(self):
        # a 0.0 ΔfH° ± with a NON-zero ΔfH° is a hollow precision claim (not a reference-state convention-zero).
        with pytest.raises(ValueError, match="reference state|hollow|> 0"):
            ThermoRef("X2", "x", -10.0, 100.0, "gas", "src", uncertainty_dhf_kj=0.0)

    def test_a_negative_dfh_uncertainty_is_refused(self):
        with pytest.raises(ValueError, match="reference state|hollow|> 0"):
            ThermoRef("X2", "x", -10.0, 100.0, "gas", "src", uncertainty_dhf_kj=-0.5)

    def test_a_zero_entropy_uncertainty_is_refused(self):
        # S° never has a convention-zero: a 0/negative S° ± is hollow, refused.
        with pytest.raises(ValueError, match="entropy|> 0|hollow"):
            ThermoRef("X2", "x", -10.0, 100.0, "gas", "src", uncertainty_s_j_per_mol_k=0.0)

    def test_a_reference_state_zero_dfh_uncertainty_is_allowed(self):
        r = ThermoRef("O2", "oxygen", 0.0, 205.15, "gas", "ref", uncertainty_dhf_kj=0.0)
        assert r.uncertainty_dhf_kj == 0.0

    def test_none_is_allowed_the_default(self):
        r = ThermoRef("X2", "x", -10.0, 100.0, "gas", "src")
        assert r.uncertainty_dhf_kj is None and r.uncertainty_s_j_per_mol_k is None


class TestIdentityNeutral:
    def test_uncertainty_is_metadata_not_identity_so_no_digest_moves(self):
        # compare=False: two records identical but for their ± are EQUAL and share a digest -- adding a sourced ±
        # to the seed cannot move a semantic fingerprint or a golden (the whole reason it is safe to add now).
        bare = ThermoRef("CO2", "carbon dioxide", -393.51, 213.79, "gas", "src")
        with_unc = ThermoRef("CO2", "carbon dioxide", -393.51, 213.79, "gas", "src",
                             uncertainty_dhf_kj=0.13, uncertainty_s_j_per_mol_k=0.010)
        assert bare == with_unc
        assert bare.digest == with_unc.digest


class TestConsumerReachesIt:
    def test_resolve_thermo_surfaces_the_uncertainty_to_a_consumer(self):
        # the wiring: a consumer resolving a SOURCED species through resolve_thermo (the feasibility path) receives
        # the ± on the returned record -- it is not merely present on the dataclass, it flows to the consumer.
        water = parse_smiles("O")
        ref = resolve_thermo(water)
        assert ref is not None
        assert ref.uncertainty_dhf_kj == 0.040
