"""OPERATION XXIII S4 -- the activity-based solid dissolution law (solid_equilibrium.py): hostile + reference tests.

PREDECLARED: PASS = (1) every operative parameter is bound by the descriptor, so a post-construction mutation is a
StaleCertificateError in a CoupledWorld; (2) both laws run as AUDITED_BUILTIN via the CLOSED pin table; (3) the law
REFUSES (OutOfDomainError) above its declared ionic-strength domain -- the nahcolite holdout, where Davies mispredicts
the solubility by ~1.7x, is stopped by the guard instead of integrating silently; (4) calcite reproduces the frozen
harness result and PHREEQC (model-vs-model) to the stated tolerance; (5) conservation is re-derived here, not read from
the receipt; (6) the existing BicarbonateDissolutionRate is byte-untouched.
"""
from __future__ import annotations

import hashlib
import math

import pytest

from experiments.sandbox_foundation import general_kernel as gk
from experiments.sandbox_foundation.aqueous_equilibrium import DAVIES_A_25C, SourcedConstant, _davies_gamma
from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as H
from experiments.sandbox_foundation.claim_tiers import OUT_OF_DOMAIN
from experiments.sandbox_foundation.general_kernel import (
    AUDITED_BUILTIN,
    UNVERIFIABLE_AUTHORITY,
    KernelError,
    Phase,
    Reaction,
    Species,
    StaleCertificateError,
    audit_status,
    is_certified_rate_law_type,
    rate_law_authority,
)
from experiments.sandbox_foundation.solid_equilibrium import (
    ActivityReversibleRate,
    ActivitySolubilityRate,
    OutOfDomainError,
)
from experiments.sandbox_foundation.unified_chemical_world import BicarbonateDissolutionRate

MOD = "experiments.sandbox_foundation.solid_equilibrium"
# Frozen from the committed harness (result_solid_equilibrium_xxiii.json): kernel steady-state dissolved Ca, 25 C.
FROZEN_CA_TOTAL_M = 1.2300896033886228e-4
PHREEQC_CA_MOLAL = 1.2300690436987488e-4       # phreeqc.dat, EQUILIBRIUM_PHASES Calcite SI=0 (model-vs-model)


# ------------------------------------------------------------------------------------------------ small fixtures
def _salt(zm=1, zx=-1):
    M = Species.of("M", {"M": 1}, zm, Phase.AQUEOUS)
    X = Species.of("X", {"X": 1}, zx, Phase.AQUEOUS)
    S = Species.of("MX(s)", {"M": 1, "X": 1}, 0, Phase.SOLID)
    return M, X, S


def _ksp(v=1.0e-4):
    return SourcedConstant("Ksp_test", v, v * 0.01, "dimensionless", 298.15, "unit test", "SOURCED")


def _law(**kw):
    M, X, S = _salt()
    st = ((S, -1), (M, 1), (X, 1))
    args = dict(k=1.0e-3, ksp=_ksp(), stoich=st)
    args.update(kw)
    return ActivitySolubilityRate(**args), Reaction("diss", st, None), (M, X, S)


@pytest.fixture(scope="module")
def calcite_n60():
    return H.run_calcite(60)


# --------------------------------------------------------------------- (1) descriptor binds EVERY operative parameter
def _fresh_calcite_world():
    world, sp, init, _ = H.build_calcite_world()
    return world, sp, init


def _mutations_solubility(law, sp):
    other_ksp = SourcedConstant("Ksp_other", 9.9e-9, 1e-10, "dimensionless", 298.15, "mutant", "SOURCED")
    swapped = ((law.stoich[0][0], -1), (sp["CO3"], 1), (sp["Ca"], 1))                # reordered ions
    return {"k": 2.0 * law.k, "ksp": other_ksp, "allow_precipitation": True, "davies_A": 0.5,
            "ionic_strength_max": 0.2, "tier": "UNVERIFIED", "source": "mutated provenance", "stoich": swapped}


@pytest.mark.parametrize("field", ["k", "ksp", "allow_precipitation", "davies_A", "ionic_strength_max", "tier",
                                   "source", "stoich"])
def test_solubility_descriptor_binds_every_parameter(field):
    world, sp, init = _fresh_calcite_world()
    law = world.compartments[0].system.reactions[0].rate_law
    assert type(law) is ActivitySolubilityRate
    d0 = law.descriptor()
    object.__setattr__(law, field, _mutations_solubility(law, sp)[field])
    assert law.descriptor() != d0, f"descriptor does not bind {field!r}"
    with pytest.raises(StaleCertificateError):
        world.integrate(init, duration=10.0, n_steps=2, require_certified_execution=True)


@pytest.mark.parametrize("field", ["kf", "K", "unit_activity", "davies_A", "ionic_strength_max", "tier", "source",
                                   "stoich"])
def test_reversible_descriptor_binds_every_parameter(field):
    world, sp, init = _fresh_calcite_world()
    rx = [r for r in world.compartments[0].system.reactions if r.name == "water"][0]
    law = rx.rate_law
    assert type(law) is ActivityReversibleRate
    d0 = law.descriptor()
    mut = {"kf": 3.0 * law.kf, "K": SourcedConstant("K_other", 2.0, 0.1, "x", 298.15, "mutant", "SOURCED"),
           "unit_activity": (), "davies_A": 0.5, "ionic_strength_max": 0.3, "tier": "UNVERIFIED",
           "source": "mutated", "stoich": ((sp["OH"], -1), (sp["H"], -1), (sp["H2O"], 1))}[field]
    object.__setattr__(law, field, mut)
    assert law.descriptor() != d0, f"descriptor does not bind {field!r}"
    with pytest.raises(StaleCertificateError):
        world.integrate(init, duration=10.0, n_steps=2, require_certified_execution=True)


def test_ksp_provenance_is_inside_the_descriptor():
    law, _, _ = _law()
    d = law.descriptor()
    flat = repr(d)
    assert "Ksp_test" in flat and "unit test" in flat and "SOURCED" in flat
    # a Ksp that differs ONLY in its stated uncertainty is a different law
    law2, _, _ = _law(ksp=SourcedConstant("Ksp_test", 1.0e-4, 2.0e-6, "dimensionless", 298.15, "unit test", "SOURCED"))
    assert law.descriptor() != law2.descriptor()


# --------------------------------------------------------------------------- (2) audited-builtin authority + pins
@pytest.mark.parametrize("cls", [ActivitySolubilityRate, ActivityReversibleRate])
def test_audited_builtin_authority_and_pin_regression(cls):
    key = (MOD, cls.__qualname__)
    assert key in gk._AUDITED_BUILTIN_PINS
    live = hashlib.sha256(gk._class_source(cls)[0].encode("utf-8")).hexdigest()
    assert live == gk._AUDITED_BUILTIN_PINS[key], "class edited without re-auditing: update the pin"
    assert audit_status()[key] == "SEALED"
    assert is_certified_rate_law_type(cls)


def test_instances_run_as_audited_builtin_and_receipt_says_so(calcite_n60):
    world, sp, init, traj, _ = calcite_n60
    for r in world.compartments[0].system.reactions:
        assert rate_law_authority(r.rate_law) == AUDITED_BUILTIN
    rc = traj.receipt
    assert rc.execution_identity_certified is True and rc.execution_identity_basis == "AUDITED_BUILTIN"


def test_subclass_and_instance_override_are_demoted():
    class Sub(ActivitySolubilityRate):
        pass

    M, X, S = _salt()
    st = ((S, -1), (M, 1), (X, 1))
    assert rate_law_authority(Sub(1e-3, _ksp(), st)) == UNVERIFIABLE_AUTHORITY
    law, _, _ = _law()
    object.__setattr__(law, "evaluate", lambda reaction, c: 0.0)
    assert rate_law_authority(law) == UNVERIFIABLE_AUTHORITY


# ---------------------------------------------------------------- activity arithmetic, independent of the law's code
def test_davies_activity_arithmetic_matches_independent_calculation():
    law, rx, (M, X, S) = _law()
    c = {M: 0.005, X: 0.005, S: 1.0}                                   # undersaturated (Omega ~ 0.2)
    ionic = 0.005
    g = _davies_gamma(ionic, DAVIES_A_25C.value)
    omega = (g * 0.005) ** 2 / 1.0e-4
    assert 0.0 < omega < 1.0
    assert law.evaluate(rx, c) == pytest.approx(1.0e-3 * (1.0 - omega), rel=1e-12)
    # divalent ions: log gamma scales with z^2
    M2, X2, S2 = _salt(2, -2)
    st = ((S2, -1), (M2, 1), (X2, 1))
    law2 = ActivitySolubilityRate(1e-3, _ksp(1e-8), st)
    c2 = {M2: 1e-4, X2: 1e-4, S2: 1.0}
    I2 = 0.5 * (1e-4 * 4 + 1e-4 * 4)
    g2 = _davies_gamma(I2, DAVIES_A_25C.value) ** 4
    assert law2.evaluate(Reaction("d", st, None), c2) == pytest.approx(1e-3 * (1.0 - (g2 * 1e-4) ** 2 / 1e-8), rel=1e-12)


def test_reversible_law_matches_independent_calculation_and_vanishes_at_equilibrium():
    M, X, _ = _salt()
    P = Species.of("MX(aq)", {"M": 1, "X": 1}, 0, Phase.AQUEOUS)
    st = ((M, -1), (X, -1), (P, 1))
    K = SourcedConstant("K_pair", 50.0, 1.0, "x", 298.15, "unit test", "SOURCED")
    law = ActivityReversibleRate(1e5, K, st)
    rx = Reaction("pair", st, None)
    cM = cX = 1e-3
    g = _davies_gamma(1e-3, DAVIES_A_25C.value)
    expect = 1e5 * ((g * cM) * (g * cX) - 0.0)
    assert law.evaluate(rx, {M: cM, X: cX, P: 0.0}) == pytest.approx(expect, rel=1e-12)
    cP = 50.0 * (g * cM) * (g * cX)                                    # a_P = K a_M a_X, gamma_P = 1
    # (I changes slightly because P is neutral: it does not, so gammas are unchanged)
    assert abs(law.evaluate(rx, {M: cM, X: cX, P: cP})) < 1e-12 * expect


def test_precipitation_switch_and_solid_presence():
    law, rx, (M, X, S) = _law()
    sup = {M: 0.05, X: 0.05, S: 1.0}                                   # IAP >> Ksp
    assert law.evaluate(rx, sup) == 0.0                                # default: dissolution only
    lawp, _, _ = _law(allow_precipitation=True)
    assert lawp.evaluate(rx, sup) < 0.0                                # solid present -> grows
    assert lawp.evaluate(rx, {M: 0.05, X: 0.05, S: 0.0}) == 0.0        # no solid, no nucleation
    assert lawp.evaluate(rx, {M: 1e-4, X: 1e-4, S: 0.0}) == 0.0        # undersaturated, nothing to dissolve
    assert lawp.evaluate(rx, {M: 1e-4, X: 1e-4, S: 1.0}) > 0.0


def test_stoichiometry_mismatch_and_bad_construction_fail_closed():
    law, _, (M, X, S) = _law()
    other = Reaction("wrong", ((S, -1), (M, 2), (X, 1)), None)
    with pytest.raises(KernelError):
        law.evaluate(other, {M: 0.0, X: 0.0, S: 1.0})
    for bad in (dict(k=-1.0), dict(k=float("nan")), dict(allow_precipitation=1), dict(ionic_strength_max=0.0),
                dict(davies_A=-0.5), dict(ksp=SourcedConstant("u", float("nan"), float("nan"), "", 0.0, "", "UNKNOWN"))):
        with pytest.raises(KernelError):
            _law(**bad)
    with pytest.raises(KernelError):                                   # no solid reactant
        ActivitySolubilityRate(1e-3, _ksp(), ((M, 1), (X, -1)))
    with pytest.raises(KernelError):                                   # charge not conserved
        ActivitySolubilityRate(1e-3, _ksp(), ((S, -1), (M, 1)))


# ------------------------------------------------------------------------- (3) the domain guard (RED -> GREEN)
def test_guard_refuses_above_declared_domain_and_allows_at_or_below():
    law, rx, (M, X, S) = _law(ionic_strength_max=0.1)
    ok = law.evaluate(rx, {M: 0.1, X: 0.1, S: 1.0})                    # I = 0.1 exactly: in domain (strict >)
    assert math.isfinite(ok)
    with pytest.raises(OutOfDomainError) as ei:
        law.evaluate(rx, {M: 0.1001, X: 0.1001, S: 1.0})
    assert ei.value.verdict == OUT_OF_DOMAIN and isinstance(ei.value, KernelError)
    assert ei.value.ionic_strength > ei.value.ionic_strength_max == 0.1
    # a bystander charged species raises I too: it is the compartment's I, computed from every charged species handed in
    Y = Species.of("Y", {"Y": 1}, 1, Phase.AQUEOUS)
    with pytest.raises(OutOfDomainError):
        law.evaluate(rx, {M: 0.01, X: 0.01, S: 1.0, Y: 0.2})
    assert math.isfinite(ActivitySolubilityRate(1e-3, _ksp(), law.stoich, ionic_strength_max=1.0)
                         .evaluate(rx, {M: 0.5, X: 0.5, S: 1.0, Y: 0.0}))     # a DECLARED wider domain is allowed


def test_reversible_law_is_domain_guarded_too():
    M, X, _ = _salt()
    P = Species.of("MX(aq)", {"M": 1, "X": 1}, 0, Phase.AQUEOUS)
    st = ((M, -1), (X, -1), (P, 1))
    law = ActivityReversibleRate(1e5, SourcedConstant("K", 5.0, 0.1, "x", 298.15, "t", "SOURCED"), st)
    with pytest.raises(OutOfDomainError):
        law.evaluate(Reaction("pair", st, None), {M: 0.3, X: 0.3, P: 0.0})


def test_nahcolite_holdout_world_fails_closed_not_silently():
    # the hostile case: Davies-activity saturation of NaHCO3 sits at I ~ 0.71 (far outside I_max = 0.1) ...
    world, init, _ = H._nahcolite_world(0.1)
    with pytest.raises(OutOfDomainError) as ei:
        world.integrate(init, duration=20000.0, n_steps=20, require_certified_execution=True)
    assert 0.1 < ei.value.ionic_strength < 0.2                        # refused on APPROACH, not after overshooting wildly
    # ... RED witness: with the domain hand-raised the SAME world integrates silently to a WRONG answer (>1.5x off the
    # sourced bulk solubility).  This counterfactual is exactly what the guard exists to block; it is not a result.
    wide, init2, _ = H._nahcolite_world(5.0)
    tr = wide.integrate(init2, duration=200000.0, n_steps=20, rtol=1e-10, atol=1e-14)
    na = [s for s in tr.amounts["cell"][-1] if s.name == "Na+"][0]
    assert tr.amounts["cell"][-1][na] == pytest.approx(0.70865, rel=1e-3)
    from experiments.sandbox_foundation.solid_bicarbonate import NAHCO3_SOLUBILITY_25C as S
    assert S.value / tr.amounts["cell"][-1][na] > 1.5


def test_nahcolite_davies_vs_measured_disagreement_numbers():
    h = H.nahcolite_holdout()
    assert h["wateq4f_log_k"] == -0.548
    assert h["davies_saturation_molality_pure_water"] == pytest.approx(0.70865, rel=1e-4)
    assert 1.65 < h["disagreement_factor_measured_over_davies"] < 1.75
    assert h["guarded_run"]["refused"] is True and h["guarded_run"]["verdict"] == OUT_OF_DOMAIN


# ---------------------------------------------------- (4) calcite steady state vs frozen harness result and PHREEQC
def test_calcite_steady_state_matches_frozen_harness_result(calcite_n60):
    world, sp, init, traj, _ = calcite_n60
    fin = traj.amounts["cell"][-1]
    ca = H._total_ca(fin, sp)
    assert ca == pytest.approx(FROZEN_CA_TOTAL_M, rel=1e-6)
    # steady: the last step moved dissolved Ca by < 1e-5 relative
    prev = H._total_ca(traj.amounts["cell"][-2], sp)
    assert abs(ca - prev) / ca < 1e-5


def test_calcite_vs_phreeqc_model_vs_model_within_half_percent(calcite_n60):
    world, sp, init, traj, _ = calcite_n60
    ca = H._total_ca(traj.amounts["cell"][-1], sp)
    rho = 0.9970574594094036                                           # PHREEQC solution density, kg/L
    assert abs(ca / rho / PHREEQC_CA_MOLAL - 1.0) < 5e-3               # measured +0.30% (molar-vs-molal convention slack)
    assert abs(ca / PHREEQC_CA_MOLAL - 1.0) < 1e-3                    # raw numbers: +0.002%


def test_calcite_steady_state_is_saturation_in_activities(calcite_n60):
    """Independent re-derivation: at steady state Omega = 1 with Davies gammas at the final I (my own arithmetic)."""
    world, sp, init, traj, _ = calcite_n60
    fin = traj.amounts["cell"][-1]
    ionic = 0.5 * sum(fin[s] * s.charge ** 2 for s in sp.values())
    g1 = _davies_gamma(ionic, DAVIES_A_25C.value)
    iap = (g1 ** 4 * fin[sp["Ca"]]) * (g1 ** 4 * fin[sp["CO3"]])        # gamma(|z|=2) = g1**4 for each divalent ion
    assert iap / 10.0 ** -8.48 == pytest.approx(1.0, abs=2e-4)
    assert ionic < 0.1


# ----------------------------------------------------------------------------------- (5) conservation, independent
def test_conservation_rederived_from_the_trajectory_not_the_receipt(calcite_n60):
    world, sp, init, traj, _ = calcite_n60
    species = list(sp.values())
    n0 = traj.amounts["cell"][0]
    for el, tol in (("Ca", 1e-12), ("C", 1e-12), ("H", 1e-9), ("O", 1e-9)):
        t0 = sum(n0[s] * s.count(el) for s in species)
        for st in traj.amounts["cell"]:
            assert abs(sum(st[s] * s.count(el) for s in species) - t0) < tol, el
    for st in traj.amounts["cell"]:                                    # (e) charge: net zero in the compartment
        assert abs(sum(st[s] * s.charge for s in species)) < 1e-14
    assert all(s.charge == 0 for s in species if s.phase is Phase.SOLID)
    assert sp["calcite"].phase is Phase.SOLID and sp["Ca"].phase is Phase.AQUEOUS


def test_receipt_agrees_with_the_independent_check(calcite_n60):
    rc = calcite_n60[3].receipt
    assert rc.positivity_held and rc.conserved_components_held and rc.structural_tier == "STRUCTURALLY_CONSERVING"


# ------------------------------------------------------------------------------------------------ (b) refinement
def test_refinement_converges_monotonically_N_2N_4N():
    ca = {}
    for n in (30, 60, 120):
        _, sp, _, tr, _ = H.run_calcite(n)
        ca[n] = H._total_ca(tr.amounts["cell"][-1], sp)
    d1, d2 = abs(ca[60] - ca[30]), abs(ca[120] - ca[60])
    assert d2 <= d1 or d1 < 1e-13 * ca[30]                             # monotone (or already at the solver floor)
    assert d1 / ca[30] < 1e-9 and d2 / ca[30] < 1e-9                  # honest: only restart points differ, so ~solver floor


def test_loose_tolerance_steady_state_is_stable_across_step_counts():
    ca = {}
    for n in (30, 60, 120):
        _, sp, _, tr, _ = H.run_calcite(n, rtol=1e-5, atol=1e-12)
        ca[n] = H._total_ca(tr.amounts["cell"][-1], sp)
    d1, d2 = abs(ca[60] - ca[30]), abs(ca[120] - ca[60])
    # NOT an order claim: at rtol 1e-5 the N-to-2N differences are solver noise (~1e-8 relative), not a convergence rate
    assert d1 / ca[30] < 1e-6 and d2 / ca[30] < 1e-6


def test_steady_state_is_independent_of_the_assumed_kinetic_scales():
    _, sp, _, tr, _ = H.run_calcite(60, k_diss=1.0e-5)
    assert H._total_ca(tr.amounts["cell"][-1], sp) == pytest.approx(FROZEN_CA_TOTAL_M, rel=1e-4)


# --------------------------------------------------------------- (6) the existing proxy law is untouched + contrast
def test_existing_bicarbonate_dissolution_rate_is_untouched():
    key = ("experiments.sandbox_foundation.unified_chemical_world", "BicarbonateDissolutionRate")
    assert gk._AUDITED_BUILTIN_PINS[key] == "69826a64cab8de88b974e6a9e7895932721a74b24290c0a86f502b17e8ec854c"
    assert hashlib.sha256(gk._class_source(BicarbonateDissolutionRate)[0].encode()).hexdigest() == gk._AUDITED_BUILTIN_PINS[key]
    assert audit_status()[key] == "SEALED"


def test_existing_proxy_has_no_domain_guard_which_is_why_the_new_law_exists():
    # contrast only: the empirical Qsp = S^2 proxy happily evaluates at I ~ 1.2 mol/L (no guard); the new law refuses.
    import inspect
    assert "OutOfDomainError" not in inspect.getsource(BicarbonateDissolutionRate)


# --------------------------------------------------- (7) hermetic constants: vendored, SHA-pinned, fail-closed on drift
def test_constants_come_only_from_vendored_sha_pinned_databases():
    # REGRESSION (hosted CI on PR #161): the harness used to read phreeqc.dat / wateq4f_PWN.dat from the INSTALLED
    # phreeqpython under sys.prefix -- absent on CI (27 FileNotFoundErrors), and unpinned wherever it did exist.
    repo_sandbox = H.SANDBOX.resolve()
    assert set(H.DB_SHA256) == {H.MINTEQ, H.PHREEQC_DAT, H.WATEQ_DAT}
    for path, pinned in H.DB_SHA256.items():
        assert path.resolve().is_relative_to(repo_sandbox), f"{path} lives outside the repo"
        assert "site-packages" not in path.parts
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pinned, path.name
    assert H.PHREEQC_DAT.parent == H.WATEQ_DAT.parent == H.DB_DIR


def test_drifted_or_unpinned_database_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setitem(H.DB_SHA256, H.PHREEQC_DAT, "0" * 64)
    with pytest.raises(ValueError, match="refusing drifted constants"):
        H.load_constants()
    stray = tmp_path / "phreeqc.dat"
    stray.write_bytes(H.PHREEQC_DAT.read_bytes())      # byte-identical copy, but not a pinned path
    with pytest.raises(ValueError, match="not a pinned database"):
        H._read_block(stray, "Calcite")
