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

    def test_the_widen_wires_the_codata_uncertainties_previously_missing(self):
        # THERMO-UNC-01-widen: N2's S° ± and ammonia's ΔfH°+S° ± are now wired in from the frozen CODATA seed (they
        # ARE CODATA key values -- the earlier NIST citation understated them).  This is the gap the frozen seed's
        # docstring named as the "next brick", now closed.
        assert _ref("N2", "nitrogen").uncertainty_s_j_per_mol_k == 0.004
        assert _ref("H3N", "ammonia").uncertainty_dhf_kj == 0.35
        assert _ref("H3N", "ammonia").uncertainty_s_j_per_mol_k == 0.05

    def test_the_widen_carries_the_past_codata_gurvich_uncertainty_for_methane(self):
        # THERMO-UNC-01-widen past the CODATA key set: CH4 is NOT a CODATA key species; its ΔfH° ± is the Gurvich/JANAF
        # value (via the NIST WebBook, cross-checked against JANAF Chase 1998), never fabricated (§10.4).
        assert _ref("CH4", "methane").uncertainty_dhf_kj == 0.3

    def test_methane_entropy_uncertainty_stays_an_honest_none(self):
        # the ONE remaining honest absence: CH4's S° has no single stated ± (the statistical 186.25 vs calorimetric
        # 188.66 J/mol/K sources disagree), so it is None -- NOT a fabricated ± -- keeping σ(ΔG) UNKNOWN for any
        # reaction that uses methane (the honesty property, now carried by CH4 rather than by N2/NH3).
        assert _ref("CH4", "methane").uncertainty_s_j_per_mol_k is None


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


class TestLiveSeedMirrorsFrozenCodata:
    """The live seed's wired ± must AGREE, value-for-value, with the frozen, dated, cross-checked CODATA source
    (experiments.thermo_codata_seed). This ties the live σ to the frozen reference so a future edit that drifts a live
    ± away from the source it cites reddens here -- the σ can never silently diverge from its provenance."""

    # (live formula, phase) -> frozen (formula, phase); only the CODATA key species (CH4 is the past-CODATA Gurvich
    # widen, deliberately excluded -- it is not in the frozen CODATA set).  Ammonia's live formula "H3N" maps to the
    # frozen "NH3"; the reference-state elements map identically.
    _LIVE_TO_FROZEN = {
        ("H2O", "liquid"): ("H2O", "liquid"),
        ("CO", "gas"): ("CO", "gas"),
        ("CO2", "gas"): ("CO2", "gas"),
        ("H3N", "gas"): ("NH3", "gas"),
        ("ClH", "gas"): ("HCl", "gas"),   # live Hill formula "ClH" <-> frozen human "HCl" (ROUND-7 widen)
        ("O2", "gas"): ("O2", "gas"),
        ("H2", "gas"): ("H2", "gas"),
        ("N2", "gas"): ("N2", "gas"),
        ("Cl2", "gas"): ("Cl2", "gas"),   # ROUND-7 widen: a CODATA element reference state
    }

    def test_every_wired_codata_sigma_matches_the_frozen_source(self):
        from experiments.thermo_codata_seed import CODATA_KEY_VALUES
        frozen = {(r.formula, r.phase): r for r in CODATA_KEY_VALUES}
        checked = 0
        for (live_f, live_ph), frozen_key in self._LIVE_TO_FROZEN.items():
            live = _ref(live_f, next(r.name for r in DEFAULT_THERMO.records
                                     if r.formula == live_f and r.phase == live_ph))
            fr = frozen[frozen_key]
            assert live.uncertainty_dhf_kj == fr.dfh_unc_kj, f"{live_f}: ΔfH° ± drifted from frozen CODATA"
            assert live.uncertainty_s_j_per_mol_k == fr.s_unc_j_per_k, f"{live_f}: S° ± drifted from frozen CODATA"
            # also pin the VALUES to the frozen source (to stored precision) -- a ± is only honest if it sits on the
            # value it was measured for.  This catches a future value drift that leaves the ± intact (the provenance
            # mismatch the standing lesson warns of); the tolerance covers the live seed's 1-2 dp rounding of CODATA.
            assert abs(live.dhf_kj_per_mol - fr.dfh_kj) < 0.05, f"{live_f}: ΔfH° value drifted from frozen CODATA"
            assert abs(live.s_j_per_mol_k - fr.s_j_per_k) < 0.05, f"{live_f}: S° value drifted from frozen CODATA"
            checked += 1
        assert checked == 9  # non-vacuous: all nine wired CODATA species were actually compared


class TestTheWidenFixesBrokenInorganicThermo:
    """ROUND-7 widen: HCl and Cl2 are CODATA key values whose group-additivity estimates were broken (HCl -> a
    degenerate ΔfH°=0/S°=0; Cl2 -> a NEGATIVE S° that CRASHED resolve_thermo).  The sourced seed rows are found by
    for_formula FIRST, so the sourced values pre-empt the broken estimates."""

    def test_hcl_resolves_to_the_sourced_codata_record_not_a_degenerate_estimate(self):
        ref = resolve_thermo(parse_smiles("Cl"))  # SMILES "Cl" == hydrogen chloride (implicit H)
        assert ref is not None and ref.grade == "SOURCED"
        assert ref.dhf_kj_per_mol == -92.31 and ref.s_j_per_mol_k == 186.902  # not the old 0/0 garbage
        assert ref.uncertainty_dhf_kj == 0.10 and ref.uncertainty_s_j_per_mol_k == 0.005

    def test_cl2_resolves_without_crashing_on_a_negative_group_additivity_entropy(self):
        ref = resolve_thermo(parse_smiles("ClCl"))  # previously CRASHED (negative Benson S°) before the sourced row
        assert ref is not None and ref.grade == "SOURCED"
        assert ref.dhf_kj_per_mol == 0.0 and ref.s_j_per_mol_k == 223.081  # element reference state, sourced S°
