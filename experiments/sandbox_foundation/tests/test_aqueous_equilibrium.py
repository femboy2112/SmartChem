"""Wave F / Wave A -- the source-backed acetic acid / acetate / water 0-D equilibrium.

SYNTHETIC/experimental.  The equilibrium CONSTANTS are sourced (CRC 84th ed. / standard Kw).  The pH predictions
are checked against (a) the agreement of two INDEPENDENT solver algorithms on the same sourced data and (b) textbook
pH anchors -- and those anchors are labelled honestly as equation/implementation VERIFICATION (same Ka + ideal
approximation), NOT independent experimental validation.  The Reaktoro cross-tool is unavailable here, so its
benchmark carries the permanent EXTERNAL_VALIDATION_UNAVAILABLE verdict, never a fabricated number.

Wave A added, red-first, four pieces of intellectual honesty -- each test below that pins NEW behaviour notes the
fact it enforces and the pre-fix lie it replaces:
  A1  pH is activity-based in a nonideal model; p[H] and pH_activity are distinguished; c_ref is declared.
  A2  the 25 C source-temperature domain is enforced in EVERY activity model, not just davies.
  A3  an admission gate fails CLOSED: disagreeing routes / non-convergence / out-of-domain I never present a result.
  A4  the uncertainty discipline is split into single-cause controls; a zero error bar on a MEASURED constant is banned.
  A5  the result carries an explicit verdict from a named vocabulary.
"""
import math

import pytest

from experiments.sandbox_foundation import aqueous_equilibrium as aqmod
from experiments.sandbox_foundation.aqueous_equilibrium import (
    AGREEMENT_RTOL, BENCHMARK_AGREEMENT_I_MAX, BEYOND_BENCHMARK_CAVEAT, C_REF, DAVIES_A_25C, DAVIES_I_MAX,
    EXTERNAL_VALIDATION_UNAVAILABLE, KA_ACETIC_25C, KW_25C, NUMERICALLY_UNVERIFIED, OUT_OF_SOURCE_DOMAIN,
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL, SOLVED_WITHIN_IDEAL_MODEL, SOURCE_T_K, SOURCE_T_TOL_K, VERDICTS,
    AcetateWaterSystem, NumericalVerificationError, OutOfSourceDomainError, SourcedConstant, _is_molar_standard_state,
    _verify_admission, reaktoro_benchmark_obligation, solve)
from experiments.sandbox_foundation.twocell import InvalidParameterError


# ---- provenance discipline: a sourced constant carries real provenance -----------------------------------------
def test_sourced_constants_carry_provenance():
    for c in (KA_ACETIC_25C, KW_25C, DAVIES_A_25C):
        assert c.status == "SOURCED" and c.source.strip() and c.uncertainty > 0 and c.value > 0
    assert abs(-math.log10(KA_ACETIC_25C.value) - 4.756) < 0.01      # pKa 4.756
    assert abs(-math.log10(KW_25C.value) - 14.0) < 0.01             # pKw ~ 14


# ---- A4: the uncertainty discipline, split into INDEPENDENT single-cause controls ------------------------------
# The old test conflated "zero uncertainty" AND "missing source"; it could not say which refused the constant.
# These isolate each cause, and decide explicitly that a zero error bar on a MEASURED constant is itself banned.
def test_a4a_zero_uncertainty_on_a_measured_constant_is_banned_even_with_a_source():
    # RED on old code: it only required uncertainty >= 0, so this constructed.  A measurement with exactly zero
    # spread is a fiction -- a fabricated/decorative error bar, ranked worse than an honest UNKNOWN.
    with pytest.raises(InvalidParameterError):
        SourcedConstant("Ka_fake", 1.75e-5, 0.0, "dimensionless (molar)", 298.15, "a perfectly real-looking source")


def test_a4b_empty_source_is_refused_for_the_SOURCE_reason_only():
    # valid positive uncertainty, only the source missing -> isolates the source cause (characterisation).
    with pytest.raises(InvalidParameterError):
        SourcedConstant("Ka_fake", 1.75e-5, 1.0e-6, "dimensionless (molar)", 298.15, "   ")


def test_a4c_unknown_status_allows_an_unavailable_value():
    # an honest blank: UNKNOWN may have no value and no error bar, and that is NOT a fabrication.
    c = SourcedConstant("not_measured_here", float("nan"), float("nan"), "", 298.15, "", status="UNKNOWN")
    assert c.status == "UNKNOWN"


def test_a4d_sourced_constant_at_the_wrong_temperature_is_refused():
    # RED on old code: the system never checked a constant's own T, so an off-temperature record was borrowed.
    off_T_Ka = SourcedConstant("Ka", 1.75e-5, 1.0e-6, "dimensionless (molar)", 350.0, "a 350 K table")
    with pytest.raises(OutOfSourceDomainError):
        AcetateWaterSystem(0.1, Ka=off_T_Ka)


def test_a4e_mismatched_standard_state_units_are_refused():
    # RED on old code: no units check, so a MOLAL constant could be mixed with a MOLAR ionic strength unlabelled.
    molal_Ka = SourcedConstant("Ka", 1.75e-5, 1.0e-6, "mol/kg (molal reference)", 298.15, "a molal table")
    with pytest.raises(InvalidParameterError):
        AcetateWaterSystem(0.1, Ka=molal_Ka)


def test_a4f_exact_by_definition_is_distinguished_from_a_measured_constant():
    # RED on old code: there was no EXACT status at all.  Exact-by-definition is the ONLY thing allowed zero spread;
    # a nonzero bar on it, OR a zero bar on a measured constant, is refused.  The two cannot be confused.
    assert C_REF.status == "EXACT" and C_REF.value == 1.0 and C_REF.uncertainty == 0.0
    with pytest.raises(InvalidParameterError):      # a nonzero error bar on a DEFINED quantity is fabricated
        SourcedConstant("c_ref_bad", 1.0, 0.01, "mol/L", 298.15, "def", status="EXACT")
    with pytest.raises(InvalidParameterError):      # a zero error bar on a MEASURED quantity is fabricated
        SourcedConstant("Ka_bad", 1.75e-5, 0.0, "dimensionless (molar)", 298.15, "src", status="SOURCED")


# ---- the two independent solver routes must agree (a SOLVER cross-check) --------------------------------------
@pytest.mark.parametrize("C_T,Na", [(0.1, 0.0), (1.0, 0.0), (0.01, 0.0), (0.1, 0.05), (0.2, 0.1)])
def test_two_routes_agree_and_charge_balances(C_T, Na):
    r = solve(AcetateWaterSystem(C_T, sodium_M=Na))
    assert r.solver_agreement_residual <= 1e-12 * max(1.0, r.h_plus_M)   # numpy.roots vs brentq agree
    assert r.charge_balance_residual <= 1e-12                            # the solution satisfies charge balance
    # mass balance: HAc + Ac- == C_T
    assert abs((r.hac_M + r.ac_minus_M) - C_T) <= 1e-12 * max(1.0, C_T)


# ---- A3: the admission gate fails CLOSED -- a solver failure is never presented as a prediction ----------------
def test_a3_disagreeing_routes_are_not_admitted():
    # RED on old code: the gate did not exist; solve() averaged two roots and reported success regardless.
    # Feed the gate two routes that disagree grossly; everything else consistent with route1.
    with pytest.raises(NumericalVerificationError) as ei:
        _verify_admission(
            h1=1.0e-3, h2=2.0e-3, h=1.0e-3, oh=1e-11, ac=0.0, hac=0.0, C_T=0.0, Na=0.0,
            Ka_c=KA_ACETIC_25C.value, Kw_c=KW_25C.value, activity_model="ideal",
            ionic_strength=1e-3, davies_converged=True, davies_iterations=0)
    assert ei.value.verdict == NUMERICALLY_UNVERIFIED


def test_a3_davies_nonconvergence_is_not_admitted():
    # RED on old code: the davies loop could fall through its 100-iter cap and still return the last gamma silently.
    with pytest.raises(NumericalVerificationError) as ei:
        _verify_admission(
            h1=1.0e-7, h2=1.0e-7, h=1.0e-7, oh=1.0e-7, ac=0.0, hac=0.0, C_T=0.0, Na=0.0,
            Ka_c=KA_ACETIC_25C.value, Kw_c=KW_25C.value, activity_model="davies",
            ionic_strength=0.01, davies_converged=False, davies_iterations=100)
    assert ei.value.verdict == NUMERICALLY_UNVERIFIED


def test_a3_negative_concentration_is_not_admitted():
    with pytest.raises(NumericalVerificationError):
        _verify_admission(
            h1=1.0e-7, h2=1.0e-7, h=1.0e-7, oh=1.0e-7, ac=-1.0, hac=1.0, C_T=0.0, Na=0.0,
            Ka_c=KA_ACETIC_25C.value, Kw_c=KW_25C.value, activity_model="ideal",
            ionic_strength=1e-7, davies_converged=True, davies_iterations=0)


def test_a3_davies_beyond_ionic_strength_domain_is_not_admitted_end_to_end():
    # RED on old code: a davies solve at I ~ 1.0 (1 M NaOH) returned a result with no domain check at all.
    with pytest.raises(NumericalVerificationError) as ei:
        solve(AcetateWaterSystem(0.0, sodium_M=1.0, activity_model="davies"))
    assert ei.value.verdict == NUMERICALLY_UNVERIFIED


def test_a3_in_domain_davies_stays_admitted():
    # guard the gate's negative polarity: a legitimate low-I davies case must still pass, with I in domain.
    r = solve(AcetateWaterSystem(0.1, sodium_M=0.1, activity_model="davies"))
    assert r.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
    assert r.ionic_strength_M <= DAVIES_I_MAX
    assert 0 < r.davies_iterations <= 100       # the fixed point demonstrably ran and did not fall through the cap


def test_a3_adversarial_regimes_are_each_admitted_with_closed_balances():
    # pure water / concentrated acid / basic / half-neutralised buffer / near-degenerate / extreme-but-finite.
    for C_T, Na in [(0.0, 0.0), (5.0, 0.0), (0.0, 0.1), (0.1, 0.05), (1e-10, 0.0), (1e-7, 0.0)]:
        r = solve(AcetateWaterSystem(C_T, sodium_M=Na))
        assert r.verdict == SOLVED_WITHIN_IDEAL_MODEL, (C_T, Na)
        assert r.solver_agreement_residual <= AGREEMENT_RTOL * max(r.h_plus_M, r.solver_agreement_residual)
        assert abs((r.hac_M + r.ac_minus_M) - C_T) <= 1e-9 * max(1.0, C_T)
        assert min(r.h_plus_M, r.oh_minus_M, r.hac_M, r.ac_minus_M) >= -1e-12


# ---- A1: pH is ACTIVITY-based in a nonideal model; p[H] and pH_activity are distinguished ----------------------
def test_a1_davies_primary_pH_is_activity_based_not_concentration():
    # RED on old code: the davies solve reported pH = -log10([H+]) = 4.58662 and called it pH.  IUPAC pH is on
    # H+ ACTIVITY.  For the reference case gamma = 0.82149, so the honest activity pH is 4.67201.
    r = solve(AcetateWaterSystem(total_acetic_M=0.1, sodium_M=0.05, temperature_K=298.15, activity_model="davies"))
    assert r.gamma_monovalent == pytest.approx(0.82149, abs=1e-5)
    assert r.pH_concentration == pytest.approx(4.58662, abs=1e-5)       # the old number, honestly renamed p[H]
    assert r.pH_activity == pytest.approx(4.67201, abs=1e-5)            # the activity-based value (permanent pin)
    assert r.pH == r.pH_activity                                        # the PRIMARY pH is the activity value
    assert r.pH != pytest.approx(r.pH_concentration, abs=1e-3)          # they genuinely differ in a nonideal model


def test_a1_ideal_mode_concentration_and_activity_pH_coincide():
    r = solve(AcetateWaterSystem(0.1))
    assert r.gamma_monovalent == 1.0
    assert r.pH == r.pH_concentration == r.pH_activity


def test_a1_c_ref_is_declared_exact_and_unit_molar():
    assert r"mol/L" in C_REF.units and "molar" in C_REF.units.lower()
    assert C_REF.status == "EXACT" and C_REF.value == 1.0 and C_REF.uncertainty == 0.0
    r = solve(AcetateWaterSystem(0.1))
    assert r.c_ref_M == 1.0


# ---- SOURCED textbook pH anchors (ideal model) -- equation VERIFICATION, not independent validation ------------
def test_pure_water_is_pH_7():
    r = solve(AcetateWaterSystem(0.0, 0.0))
    assert abs(r.pH - 7.0) < 1e-6


def test_tenth_molar_acetic_acid_is_about_pH_2_87():
    # standard general-chemistry result: 0.1 M acetic acid -> pH ~ 2.87-2.88
    r = solve(AcetateWaterSystem(0.1))
    assert 2.86 <= r.pH <= 2.89, r.pH
    assert r.hac_M > r.ac_minus_M > r.oh_minus_M                     # weakly dissociated, acidic


def test_one_molar_acetic_acid_is_about_pH_2_38():
    r = solve(AcetateWaterSystem(1.0))
    assert 2.36 <= r.pH <= 2.40, r.pH


def test_equimolar_acetate_buffer_sits_at_the_pKa():
    # 0.05 M acetic acid + 0.05 M acetate (as NaAc) -> [HAc]=[Ac-] -> pH = pKa = 4.756 (Henderson-Hasselbalch)
    r = solve(AcetateWaterSystem(total_acetic_M=0.1, sodium_M=0.05))
    assert abs(r.pH - 4.756) < 0.02, r.pH
    assert abs(r.hac_M - r.ac_minus_M) < 1e-3                        # genuinely at the half-neutralisation point


# ---- A5: the result carries an explicit verdict from a named vocabulary ----------------------------------------
def test_a5_solve_carries_a_model_appropriate_verdict():
    assert solve(AcetateWaterSystem(0.1)).verdict == SOLVED_WITHIN_IDEAL_MODEL
    assert solve(AcetateWaterSystem(0.1, sodium_M=0.05, activity_model="davies")).verdict == \
        SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL


def test_a5_verdict_vocabulary_is_the_declared_set():
    assert VERDICTS == {
        SOLVED_WITHIN_IDEAL_MODEL, SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
        NUMERICALLY_UNVERIFIED, OUT_OF_SOURCE_DOMAIN, EXTERNAL_VALIDATION_UNAVAILABLE}


# ---- the Davies nonideal correction shifts pH (documented, not claimed exact) ---------------------------------
def test_davies_correction_shifts_pH_and_lowers_gamma():
    ideal = solve(AcetateWaterSystem(0.1, sodium_M=0.1, activity_model="ideal"))
    davies = solve(AcetateWaterSystem(0.1, sodium_M=0.1, activity_model="davies"))
    assert davies.gamma_monovalent < 1.0                            # activity coefficient below 1 at finite I
    assert ideal.gamma_monovalent == 1.0
    assert abs(davies.pH - ideal.pH) > 1e-3                         # a real, documented shift
    assert davies.pH == davies.pH_activity                          # the davies primary pH is the activity value
    assert davies.activity_model == "davies"


# ---- A2: the 25 C source-temperature domain is enforced in EVERY activity model --------------------------------
def test_a2_davies_off_25C_is_refused_not_extrapolated():
    with pytest.raises(InvalidParameterError):
        AcetateWaterSystem(0.1, temperature_K=310.0, activity_model="davies")


def test_a2_ideal_mode_cannot_bypass_the_source_temperature():
    # RED on old code: the 25 C guard only fired for davies, so ideal mode silently reused 25 C Ka/Kw at 350 K.
    with pytest.raises(OutOfSourceDomainError) as ei:
        AcetateWaterSystem(0.1, temperature_K=350.0, activity_model="ideal")
    assert ei.value.verdict == OUT_OF_SOURCE_DOMAIN


def test_a2_source_temperature_band_is_explicit_and_enforced_in_both_modes():
    assert SOURCE_T_K == 298.15 and SOURCE_T_TOL_K == 0.01           # the band is DECLARED, not implicit
    for model in ("ideal", "davies"):
        AcetateWaterSystem(0.1, temperature_K=298.15, activity_model=model)          # dead-centre: ok
        AcetateWaterSystem(0.1, temperature_K=298.159, activity_model=model)         # inside the band (0.009): ok
        with pytest.raises(OutOfSourceDomainError):
            AcetateWaterSystem(0.1, temperature_K=298.161, activity_model=model)     # just outside (0.011): refused
        with pytest.raises(OutOfSourceDomainError):
            AcetateWaterSystem(0.1, temperature_K=350.0, activity_model=model)       # far outside: refused


# ---- A5: the independent benchmark is EXTERNAL_VALIDATION_UNAVAILABLE, never a fabricated number ---------------
def test_reaktoro_benchmark_is_external_validation_unavailable_not_fabricated():
    ob = reaktoro_benchmark_obligation()
    assert ob.tool == "Reaktoro" and ob.verdict == EXTERNAL_VALIDATION_UNAVAILABLE
    assert ob.comparison is None                                    # no fabricated comparison
    assert "activity_model" in ob.recipe and "independence_caveat" in ob.recipe


# ---- the species set is CURATED (fixed), not arbitrary chemistry by formula similarity ------------------------
def test_negative_inputs_are_refused():
    for kw in (dict(total_acetic_M=-0.1), dict(total_acetic_M=0.1, sodium_M=-0.01)):
        with pytest.raises(InvalidParameterError):
            AcetateWaterSystem(**kw)


# ================================================================================================================
# Wave A follow-up (evil-morty + PHREEQC honesty defects) -- three claim-honesty repairs, each red-first.
# ================================================================================================================

# ---- follow-up #1: the header must DISCLOSE the molal-A / molar-I approximation, not deny it -------------------
def test_followup1_header_discloses_the_molal_A_molar_I_approximation_honestly():
    # RED on Wave A: its header falsely claimed it "does not silently mix a molal Davies coefficient with a molar
    # ionic strength".  It does mix them (DAVIES_A_25C.units is molal, applied to a molar ionic strength); the fix
    # is to state the rho~1 approximation honestly, not to pretend it was removed.
    doc = aqmod.__doc__.lower()
    assert "does not silently mix" not in aqmod.__doc__      # the over-claim is gone
    assert "molal" in doc and "rho" in doc                   # the approximation is named ...
    assert "ion pair" in doc                                 # ... and the ion-pairing scope limit documented (#3a)
    # and the coefficient itself really is molal, so the disclosure is not theatre:
    assert "kg" in DAVIES_A_25C.units and "/l" not in DAVIES_A_25C.units.lower()


# ---- follow-up #2: the standard-state units guard is an allowlist/blocklist, correct in BOTH directions --------
def test_followup2_real_molar_spellings_are_accepted():
    # RED on Wave A: only the literal word "molar" passed, so these correctly-labelled molar spellings were REFUSED.
    for units in ("mol/L", "mol dm^-3", "mol/dm^3", "M", "molar (ideal reference)", "mol L^-1"):
        assert _is_molar_standard_state(units), units
        good_Ka = SourcedConstant("Ka", 1.75e-5, 1.0e-6, units, 298.15, "a correctly-labelled molar table")
        AcetateWaterSystem(0.1, Ka=good_Ka)                  # constructs: a valid molar spelling is accepted


def test_followup2_molal_string_containing_the_substring_molar_is_still_refused():
    # RED on Wave A: substring test accepted this because it contains "molar"; the blocklist must veto on "mol/kg".
    for units in ("molar-labelled but mol/kg molal", "mol/kg (molal)", "mol kg^-1", "molality m (mol per kg)"):
        assert not _is_molar_standard_state(units), units
        molal_Ka = SourcedConstant("Ka", 1.75e-5, 1.0e-6, units, 298.15, "a molal table wearing a molar label")
        with pytest.raises(InvalidParameterError):
            AcetateWaterSystem(0.1, Ka=molal_Ka)


# ---- follow-up #3: the demonstrated benchmark-agreement domain is distinct from the Davies validity domain -----
def test_followup3_benchmark_domain_is_strictly_inside_the_davies_domain():
    assert BENCHMARK_AGREEMENT_I_MAX == 0.1                  # the demonstrated PHREEQC-agreement domain is DECLARED
    assert BENCHMARK_AGREEMENT_I_MAX < DAVIES_I_MAX          # ... and strictly inside the Davies validity domain


def test_followup3_result_beyond_benchmark_domain_carries_the_caveat_but_still_solves():
    # RED on Wave A: no `caveats` field existed; a davies result at I ~ 0.45 (past the ~0.1 M PHREEQC-agreement
    # domain, where the omitted NaAc ion pair drives |dpH| ~ 0.052) was presented as a bare, unqualified SOLVED.
    r = solve(AcetateWaterSystem(0.7, sodium_M=0.45, activity_model="davies"))
    assert r.ionic_strength_M > BENCHMARK_AGREEMENT_I_MAX
    assert r.ionic_strength_M <= DAVIES_I_MAX                # still inside Davies validity, so it legitimately solves
    assert r.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
    assert BEYOND_BENCHMARK_CAVEAT in r.caveats              # ... but it is NOT presented as independently benchmarked
    assert "ion pair" in BEYOND_BENCHMARK_CAVEAT.lower() and "benchmark" in BEYOND_BENCHMARK_CAVEAT.lower()


def test_followup3_result_inside_benchmark_domain_has_no_caveat():
    # a davies result at I ~ 0.05 is inside the demonstrated agreement domain -> no qualifier, clean SOLVED.
    r = solve(AcetateWaterSystem(0.1, sodium_M=0.05, activity_model="davies"))
    assert r.ionic_strength_M <= BENCHMARK_AGREEMENT_I_MAX
    assert r.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
    assert r.caveats == ()


# ================================================================================================================
# Round VI "The Salt Bridge" -- the NaAc(aq) ion pair, OPT-IN (default off), closing the documented C5 divergence.
# Red-first: the include_ion_pair path, the na_plus_M / naac_M result fields, and K_NAAC_ION_PAIR_25C do not yet
# exist, so every assertion below fails on the current module.  The new names are referenced module-qualified
# (aqmod.*) and via the new kwarg so that ONLY these tests go red, not the whole file's import.
# ================================================================================================================

# committed PHREEQC-with-pair reference pH at C5 (C_T=0.45, Na=0.45), molar-matched, from comparison_stdout.txt:
_PHREEQC_C5_MINTEQ = 9.0177   # minteq.v4 (NaAc log_k -0.18, NIST46.4); the independent tool INCLUDES the ion pair


def test_ion_pair_sourced_constant_carries_nist_provenance():
    k = aqmod.K_NAAC_ION_PAIR_25C
    assert k.status == "SOURCED" and k.value > 0 and k.uncertainty > 0 and k.source.strip()
    assert abs(math.log10(k.value) - (-0.18)) < 0.01        # logK = -0.18 (K ~ 0.661 L/mol)
    assert "nist" in k.source.lower() or "46" in k.source    # the NIST-selected (NIST46.4) lineage is cited


def test_ion_pair_default_off_is_identical_to_the_base_model():
    # the opt-in must not perturb the default: include_ion_pair defaults False, and an explicit False == omitting it.
    base = solve(AcetateWaterSystem(0.1, sodium_M=0.05, activity_model="davies"))
    off = solve(aqmod.AcetateWaterSystem(0.1, sodium_M=0.05, activity_model="davies", include_ion_pair=False))
    assert base.pH == off.pH == pytest.approx(4.67201, abs=1e-5)   # the Wave A activity-pH pin is untouched


def test_ion_pair_closes_the_pair_attributable_half_of_the_c5_divergence():
    # The documented ~0.052 pH divergence vs PHREEQC-with-pair at C5 splits into the omitted-NaAc-pair effect (~half)
    # and the Davies-vs-WATEQ-DH activity-model + molal/molar difference (~half), which the pair does NOT touch.
    # Adding the pair must close the pair half: lower the pH toward PHREEQC and cut the gap by a clear margin.  We do
    # NOT claim it reaches AGREE (0.02) -- that would require also matching PHREEQC's activity model (a different,
    # unmade change).  Honest target: a clear majority of the pair-attributable part, pH lowered, a real pair formed.
    no_pair = solve(AcetateWaterSystem(0.45, sodium_M=0.45, activity_model="davies"))
    with_pair = solve(aqmod.AcetateWaterSystem(0.45, sodium_M=0.45, activity_model="davies", include_ion_pair=True))
    gap_no = abs(no_pair.pH - _PHREEQC_C5_MINTEQ)
    gap_with = abs(with_pair.pH - _PHREEQC_C5_MINTEQ)
    assert gap_no > 0.045                                   # the documented omission (~0.052)
    assert with_pair.pH < no_pair.pH                        # the pair lowers pH (locks free Ac- -> less hydrolysis)
    assert gap_with < 0.65 * gap_no                         # a clear majority of the pair-attributable gap is closed
    assert with_pair.naac_M > 0.0                           # a neutral NaAc population genuinely forms
    assert with_pair.na_plus_M < 0.45                       # ... so free Na+ is below the total added sodium


def test_ion_pair_sodium_and_acetate_mass_balances_both_close():
    r = solve(aqmod.AcetateWaterSystem(0.45, sodium_M=0.45, activity_model="davies", include_ion_pair=True))
    assert abs((r.na_plus_M + r.naac_M) - 0.45) <= 1e-9              # NEW: total sodium = free Na+ + paired NaAc
    assert abs((r.hac_M + r.ac_minus_M + r.naac_M) - 0.45) <= 1e-9   # total acetate now includes the pair
    # charge balance EXCLUDES the neutral pair: Na+ + H+ == OH- + Ac-
    assert abs((r.na_plus_M + r.h_plus_M) - (r.oh_minus_M + r.ac_minus_M)) <= 1e-9


def test_ion_pair_two_independent_routes_agree():
    r = solve(aqmod.AcetateWaterSystem(0.45, sodium_M=0.45, activity_model="davies", include_ion_pair=True))
    assert r.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
    assert r.solver_agreement_residual <= AGREEMENT_RTOL * max(1.0, r.h_plus_M)   # two routes still cross-check


def test_ion_pair_is_negligible_at_low_ionic_strength():
    # at C3 (I ~ 0.05) only a few percent of Na is paired, so the pH barely moves off the base result.
    base = solve(AcetateWaterSystem(0.1, sodium_M=0.05, activity_model="davies"))
    with_pair = solve(aqmod.AcetateWaterSystem(0.1, sodium_M=0.05, activity_model="davies", include_ion_pair=True))
    assert with_pair.pH <= base.pH + 1e-9                   # pair lowers pH (weakly) ...
    assert (base.pH - with_pair.pH) < 0.02                  # ... but only slightly: still AGREE-scale at low I


def test_ion_pair_admission_still_fails_closed_beyond_davies_domain():
    # the opt-in path must inherit the same fail-closed admission: I > DAVIES_I_MAX is refused, not extrapolated.
    with pytest.raises(NumericalVerificationError) as ei:
        solve(aqmod.AcetateWaterSystem(0.6, sodium_M=0.6, activity_model="davies", include_ion_pair=True))
    assert ei.value.verdict == NUMERICALLY_UNVERIFIED


def test_ion_pair_admits_basic_excess_base_regime_no_route2_cancellation():
    # RED (evil-morty Finding 1): Route 2's h_of_a used 0.5*(-b + sqrt(b^2 + 4*Kw_c)) with b = na_plus - a.  When the
    # solution is basic (free Na+ > free Ac-, b > 0, b^2 >> 4*Kw_c) that subtracts two near-equal large numbers --
    # catastrophic cancellation -- so route 2's [H+] carried a large relative error, the two routes disagreed past
    # AGREEMENT_RTOL, and the pair path REFUSED every basic Na > C_T case the base model solves cleanly (exactly the
    # excess-base regime where hydrolysis-suppressing pairing matters).  The cancellation-free conjugate branch
    # 2*Kw_c/(b + sqrt(...)) for b > 0 fixes it: these must now ADMIT, with the two independent routes agreeing.
    for CT, Na in [(0.1, 0.12), (0.1, 0.2), (0.1, 0.4), (0.2, 0.21), (0.45, 0.46)]:
        base = solve(AcetateWaterSystem(CT, sodium_M=Na, activity_model="davies"))
        assert base.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL, (CT, Na)   # base always solved these
        pair = solve(aqmod.AcetateWaterSystem(CT, sodium_M=Na, activity_model="davies", include_ion_pair=True))
        assert pair.verdict == SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL, (CT, Na)   # pair must no longer refuse
        assert pair.solver_agreement_residual <= AGREEMENT_RTOL * max(1.0, pair.h_plus_M)   # routes agree now
        assert abs((pair.na_plus_M + pair.naac_M) - Na) <= 1e-8 * max(1.0, Na)   # sodium conserved
        assert pair.naac_M > 0.0 and pair.na_plus_M < Na                         # a real pair formed
        assert abs(pair.pH - base.pH) < 0.3                                      # same solution, modestly shifted


def test_ion_pair_with_no_sodium_or_no_acetate_reduces_to_base():
    # no Na+ -> nothing to pair; no acetate -> nothing to pair.  Either way the pair path must equal the base result
    # byte-for-byte (it takes the same base solver branch).  Regimes chosen to be well-conditioned: (0.1,0.0) is
    # acidic davies; (0.0,0.1) pure NaOH is the deep-basic (pH~13) oh=Kw/h conditioning corner, so it is checked
    # under the IDEAL model (proven admissible by test_a3_adversarial_regimes) rather than davies -- the corner's
    # charge-closure limit is a pre-existing base-path numerical issue, orthogonal to the ion pair, not papered over.
    for CT, Na, model in [(0.1, 0.0, "davies"), (0.0, 0.1, "ideal")]:
        base = solve(AcetateWaterSystem(CT, sodium_M=Na, activity_model=model))
        pair = solve(aqmod.AcetateWaterSystem(CT, sodium_M=Na, activity_model=model, include_ion_pair=True))
        assert pair.pH == pytest.approx(base.pH, abs=1e-12), (CT, Na, model)
        assert pair.naac_M == pytest.approx(0.0, abs=1e-15)
