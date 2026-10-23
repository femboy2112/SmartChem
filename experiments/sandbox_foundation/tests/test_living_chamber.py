"""Wave C (Round VII) tests -- the first living chemical chamber.

The five flagship scenarios (C4), each with positive / negative / mutation coverage, plus the mandatory falsifiers:
  #8  analytical component inventory survives local speciation (A E(b) = b);
  #9  internal neutral-HAc flux is exactly equal-and-opposite across each face;
  #10 sodium is immobile when the membrane admits only HAc;
  #11 local charge balance closes after every accepted state update;
  #12 zero permeability (shut valve or g=0) produces no transport;
  #13 the mol/L <-> mol/m^3 conversion is exact;
  #14 a step that would export more neutral acid than the donor holds is refused or substepped;
  #15 pH trajectories survive changes to rendering frequency;
  #16 the passive-interface dissipation claim uses no unjustified global free-energy formula.
Plus a C5 numerical-reference check (dt-halving self-consistency; NOT validation) and input-validation refusals.
"""
import math

import numpy as np
import pytest

from experiments.sandbox_foundation.living_chamber import (
    Chamber, ChamberError, ChamberWorld, FREE_ENERGY_OBSTRUCTION, LITRES_PER_M3, Membrane,
    conservation_report, make_chamber, run, step, transport_dissipation_margin, two_chamber_world)
from experiments.sandbox_foundation.twocell import InvalidParameterError

CONS_ATOL = 1e-12          # mol: global-total drift a transport step may show
CHARGE_ATOL = 1e-10        # mol/L: per-cell charge-balance closure (the solver achieves ~1e-18)


def _acid(**kw):   return make_chamber(acetate_M=0.1, sodium_M=0.0, **kw)
def _water(**kw):  return make_chamber(acetate_M=0.0, sodium_M=0.0, **kw)
def _buffer(**kw): return make_chamber(acetate_M=0.1, sodium_M=0.05, **kw)


# =============================================================================== Scenario 1 -- impermeable membrane
class TestScenario1_Impermeable:
    def test_shut_valve_freezes_every_pH_and_inventory(self):
        world = two_chamber_world(left=_acid(), right=_buffer(), valve=0.0)           # wall
        traj = run(world, dt=10.0, n_steps=12)
        pH0 = traj[0].pH
        for s in traj:
            assert np.allclose(s.pH, pH0, atol=0.0, rtol=0.0)                         # bit-identical: nothing moved
            assert all(e.amount_mol == 0.0 for e in s.ledger)                         # no transfer recorded
        rep = conservation_report(traj[0].world, traj[-1].world)
        assert rep["conserves"] and rep["global_acetate_drift_mol"] == 0.0

    def test_g_zero_wall_is_also_impermeable(self):
        world = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=0.0)
        traj = run(world, dt=10.0, n_steps=5)
        assert np.array_equal(traj[0].pH, traj[-1].pH)

    def test_negative_control_opening_the_wall_DOES_move_pH(self):
        # the fixity above must be the WALL, not a dead simulation: open it and the receiver's pH must change.
        world = two_chamber_world(left=_acid(), right=_water(), valve=1.0)
        traj = run(world, dt=5.0, n_steps=8, policy="substep")
        assert traj[-1].pH[1] < traj[0].pH[1] - 1.0                                   # pure water acidifies markedly


# =============================================================================== Scenario 2 -- pure acid vs water
class TestScenario2_AcidVsWater:
    def test_acetate_redistributes_and_pH_evolves_conservatively(self):
        world = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=1e-9)
        traj = run(world, dt=1.0, n_steps=20, policy="substep")
        left_ac = [s.world.chambers[0].n_acetate_mol for s in traj]
        right_ac = [s.world.chambers[1].n_acetate_mol for s in traj]
        assert left_ac[-1] < left_ac[0] and right_ac[-1] > right_ac[0]               # acid -> water
        assert all(b <= a + 1e-18 for a, b in zip(left_ac, left_ac[1:]))             # donor monotonically decreases
        assert traj[-1].pH[1] < 5.0 and traj[-1].pH[1] > 3.0                          # water became a dilute acid
        rep = conservation_report(traj[0].world, traj[-1].world)
        assert rep["conserves"]

    def test_mutation_a_sodium_moving_step_would_be_caught(self):
        # a MUTATION control: if a buggy step moved sodium, the sodium-immobility invariant would fire.  We prove
        # the invariant HOLDS on the real step, and that a hand-forged sodium change is detectable.
        world = two_chamber_world(left=_buffer(), right=_water(), g_HAc_m3_per_s=1e-9)
        traj = run(world, dt=1.0, n_steps=10, policy="substep")
        assert traj[0].world.chambers[0].n_sodium_mol == traj[-1].world.chambers[0].n_sodium_mol
        forged = traj[-1].world.chambers[0].with_components(n_sodium_mol=traj[-1].world.chambers[0].n_sodium_mol * 1.1)
        assert forged.n_sodium_mol != traj[-1].world.chambers[0].n_sodium_mol        # the forgery is a real change...
        assert conservation_report(traj[0].world,
                                   ChamberWorld((forged, traj[-1].world.chambers[1]),
                                                traj[-1].world.membranes))["max_per_cell_sodium_change_mol"] > 0


# =============================================================================== Scenario 3 -- acid vs buffer
class TestScenario3_AcidVsBuffer:
    def test_neutral_acid_moves_and_sodium_stays_home(self):
        world = two_chamber_world(left=_acid(), right=_buffer(), g_HAc_m3_per_s=1e-9)
        na_right0 = world.chambers[1].n_sodium_mol
        traj = run(world, dt=1.0, n_steps=25, policy="substep")
        # c_HAc(acid) ~ 0.0998 M >> c_HAc(buffer, half-neutralised) ~ 0.05 M, so HAc flows acid -> buffer:
        assert traj[-1].world.chambers[1].n_acetate_mol > traj[0].world.chambers[1].n_acetate_mol
        assert traj[-1].pH[1] < traj[0].pH[1]                                         # the buffer acidifies (a little)
        # #10: every sodium ion stays in the buffer chamber -- the membrane admits none.
        assert traj[-1].world.chambers[1].n_sodium_mol == na_right0
        assert all(s.world.chambers[1].n_sodium_mol == na_right0 for s in traj)
        assert all(s.world.chambers[0].n_sodium_mol == 0.0 for s in traj)

    def test_buffer_blunts_the_pH_swing_vs_plain_water(self):
        # the receiving chamber's pH response depends on its local buffer speciation: the buffer moves LESS than
        # pure water would for a comparable acetate gain.
        wb = two_chamber_world(left=_acid(), right=_buffer(), g_HAc_m3_per_s=1e-9)
        ww = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=1e-9)
        tb = run(wb, dt=1.0, n_steps=20, policy="substep")
        tw = run(ww, dt=1.0, n_steps=20, policy="substep")
        assert abs(tb[-1].pH[1] - tb[0].pH[1]) < abs(tw[-1].pH[1] - tw[0].pH[1])


# =============================================================================== Scenario 4 -- ion-pair comparison
class TestScenario4_IonPairComparison:
    def test_pair_on_vs_off_both_admitted_and_difference_is_bounded_and_disclosed(self):
        def worlds(pair):
            return two_chamber_world(left=_acid(include_ion_pair=pair), right=_buffer(include_ion_pair=pair),
                                     g_HAc_m3_per_s=1e-9)
        t_off = run(worlds(False), dt=1.0, n_steps=20, policy="substep")
        t_on = run(worlds(True), dt=1.0, n_steps=20, policy="substep")
        # both admitted and conservative:
        assert conservation_report(t_off[0].world, t_off[-1].world)["conserves"]
        assert conservation_report(t_on[0].world, t_on[-1].world)["conserves"]
        # the pair's influence on THIS scenario is small (weak pair, K<1; ~1-4% of acetate paired at these I):
        maxdiff = max(abs(a.pH[j] - b.pH[j]) for a, b in zip(t_on, t_off) for j in (0, 1))
        assert 0.0 <= maxdiff < 0.1                                                   # bounded, and disclosed as small
        # the pair IS active where there is sodium (buffer side carries NaAc), so it is not a trivial no-op there:
        assert t_on[-1].specs[1].naac_M > 0.0 and t_off[-1].specs[1].naac_M == 0.0


# =============================================================================== Scenario 5 -- renderer disabled
class _RecordingPresenter:
    def __init__(self): self.seen = []
    def __call__(self, state): self.seen.append((state.tick, tuple(state.pH)))


class TestScenario5_RendererDisabled:
    def test_trajectory_is_identical_for_zero_one_or_many_renders(self):
        def pH_series(calls):
            pres = _RecordingPresenter()
            world = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=1e-9)
            traj = run(world, dt=1.0, n_steps=12, policy="substep", presenter=pres, calls_per_tick=calls)
            return np.array([s.pH for s in traj]), pres

        p0, pres0 = pH_series(0)
        p1, pres1 = pH_series(1)
        p5, pres5 = pH_series(5)
        assert np.array_equal(p0, p1) and np.array_equal(p0, p5)                      # #15: rendering is a pure read
        assert len(pres0.seen) == 0 and len(pres1.seen) == 13 and len(pres5.seen) == 65  # but it really ran


# =============================================================================== mandatory falsifiers #8-#16
class TestFalsifiers:
    def test_8_component_identity_A_E_b_equals_b(self):
        for ch in (_acid(), _buffer(), _water(), _buffer(include_ion_pair=True)):
            assert ch.component_identity_residual() <= 1e-12

    def test_9_internal_flux_is_equal_and_opposite_each_face(self):
        world = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=1e-9)
        new_world, ledger = step(world, 1.0, policy="substep")
        # the global inventory is unchanged: what leaves tail arrives at head, exactly.
        assert np.max(np.abs(new_world.totals() - world.totals())) <= CONS_ATOL
        # and the carrier is acetate only (sodium global unchanged to the bit):
        assert new_world.totals()[1] == world.totals()[1]

    def test_10_sodium_is_immobile(self):
        world = two_chamber_world(left=_buffer(), right=_buffer(), g_HAc_m3_per_s=1e-9)
        traj = run(world, dt=1.0, n_steps=15, policy="substep")
        for s in traj:
            assert s.world.chambers[0].n_sodium_mol == world.chambers[0].n_sodium_mol
            assert s.world.chambers[1].n_sodium_mol == world.chambers[1].n_sodium_mol

    def test_11_local_charge_balance_closes_every_step(self):
        world = two_chamber_world(left=_acid(), right=_buffer(), g_HAc_m3_per_s=1e-9)
        traj = run(world, dt=1.0, n_steps=20, policy="substep")
        for s in traj:
            assert float(np.max(s.charge_residuals())) < CHARGE_ATOL

    def test_12_zero_permeability_no_transport(self):
        for world in (two_chamber_world(left=_acid(), right=_water(), valve=0.0),
                      two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=0.0)):
            after, ledger = step(world, 1e6, policy="raise")                          # even a huge dt moves nothing
            assert np.array_equal(after.totals(), world.totals())
            assert all(e.amount_mol == 0.0 for e in ledger)

    def test_13_mol_per_L_to_mol_per_m3_conversion_is_exact(self):
        assert LITRES_PER_M3 == 1000.0
        ch = make_chamber(acetate_M=0.1, sodium_M=0.0, volume_m3=1e-6)
        assert ch.n_acetate_mol == 0.1 * 1e-6 * 1000.0                                # 1e-4 mol, exactly
        sp = ch.speciate()
        assert ch.c_hac_mol_per_m3(sp) == sp.hac_M * 1000.0                           # the transport-side unit
        # a wrong factor would be a 1000x error: c_HAc(mol/m^3) must be 1000x the mol/L value, never equal to it.
        assert abs(ch.c_hac_mol_per_m3(sp) - sp.hac_M) > 1.0

    def test_14_overexport_is_refused_under_raise_and_substepped_otherwise(self):
        world = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=1e-9)
        dt_max = world.transport_dt_max()
        assert math.isfinite(dt_max) and dt_max > 0
        big = dt_max * 50.0                                                           # one step would over-export
        with pytest.raises(ChamberError):
            step(world, big, policy="raise")
        after, ledger = step(world, big, policy="substep")                           # substep handles it...
        assert conservation_report(world, after)["conserves"]                        # ...and still conserves
        assert after.chambers[0].n_acetate_mol >= 0.0 and after.chambers[1].n_acetate_mol > world.chambers[1].n_acetate_mol

    def test_16_dissipation_margin_nonnegative_and_no_global_free_energy_claim(self):
        # both sides carry HAc -> a FINITE down-gradient margin (not the inf of the ln(0) corner).
        world = two_chamber_world(left=_acid(), right=make_chamber(acetate_M=0.02, sodium_M=0.0), g_HAc_m3_per_s=1e-9)
        m = transport_dissipation_margin(world)
        assert m >= 0.0 and math.isfinite(m)                                         # HAc moves DOWN its gradient
        assert "No global free-energy Lyapunov is claimed" in FREE_ENERGY_OBSTRUCTION


# =============================================================================== C5 -- numerical self-consistency
class TestC5_NumericalReference:
    def test_dt_halving_self_consistency_not_validation(self):
        # refining dt must not change the trajectory beyond the explicit-Euler truncation error -- a NUMERICAL
        # self-consistency check (NOT experimental validation, and NOT a convergence-order claim).
        def end_pH(n_steps, dt):
            world = two_chamber_world(left=_acid(), right=_water(), g_HAc_m3_per_s=1e-9)
            return run(world, dt=dt, n_steps=n_steps, policy="substep")[-1].pH

        coarse = end_pH(10, 1.0)
        fine = end_pH(20, 0.5)                                                        # same total time, half dt
        assert np.max(np.abs(coarse - fine)) < 0.05                                   # close; halving barely moves it

    def test_closed_world_conserves_over_a_long_run_frozen_control(self):
        world = two_chamber_world(left=_buffer(), right=_water(), g_HAc_m3_per_s=1e-9)
        traj = run(world, dt=2.0, n_steps=50, policy="substep")
        rep = conservation_report(traj[0].world, traj[-1].world)
        assert rep["global_acetate_drift_mol"] < 1e-12 and rep["global_sodium_drift_mol"] == 0.0


# =============================================================================== input validation (fail closed)
class TestValidation:
    def test_bad_chamber_inputs_refused(self):
        with pytest.raises(InvalidParameterError):
            Chamber(n_acetate_mol=-1.0, n_sodium_mol=0.0, volume_m3=1e-6)
        with pytest.raises(InvalidParameterError):
            Chamber(n_acetate_mol=1e-4, n_sodium_mol=0.0, volume_m3=0.0)
        with pytest.raises(InvalidParameterError):
            Chamber(n_acetate_mol=1e-4, n_sodium_mol=0.0, volume_m3=1e-6, activity_model="wishful")

    def test_bad_membrane_and_world_refused(self):
        with pytest.raises(InvalidParameterError):
            Membrane(0, 0, 1e-9)                                                      # self-loop
        with pytest.raises(InvalidParameterError):
            Membrane(0, 1, 1e-9, valve=1.5)                                           # valve out of [0,1]
        with pytest.raises(InvalidParameterError):
            ChamberWorld(chambers=(_acid(), _acid()), membranes=(Membrane(0, 5, 1e-9),))   # index out of range
        with pytest.raises(InvalidParameterError):
            ChamberWorld(chambers=(Chamber(1e-4, 0.0, 1e-6, temperature_K=298.15),
                                   Chamber(1e-4, 0.0, 1e-6, temperature_K=300.0)))         # mixed temperature


class TestWaveF_AdaptiveSubstep:
    """Wave F Finding 1 (fixed red-first): substep must COMPLETE on a heterogeneous multi-cell world -- an empty
    middle cell that FILLS must not over-export under a fixed step size -- and must fail CLOSED on a genuinely stiff
    one.  Before the adaptive fix, both the moderate and the stiff case raised ChamberError."""

    def _three(self, g_bc):
        return ChamberWorld((make_chamber(acetate_M=0.5, sodium_M=0.0),
                             make_chamber(acetate_M=0.0, sodium_M=0.0),
                             make_chamber(acetate_M=0.0, sodium_M=0.0)),
                            (Membrane(0, 1, 1e-9), Membrane(1, 2, g_bc)))

    def test_heterogeneous_multicell_substep_completes_and_conserves(self):
        w = self._three(2e-9)                                                          # heterogeneous, non-stiff
        before = w.totals()
        after, _ledger = step(w, dt=5 * w.transport_dt_max(), policy="substep")        # pre-fix: this RAISED
        assert float(np.max(np.abs(after.totals() - before))) <= CONS_ATOL             # conserved
        assert after.totals()[1] == before[1]                                          # sodium untouched
        assert after.chambers[2].n_acetate_mol > 0.0                                   # HAc reached the far cell

    def test_a_too_stiff_world_fails_closed(self):
        w = self._three(1e-4)                                                          # g_BC huge -> stiff
        with pytest.raises(ChamberError):
            step(w, dt=5 * w.transport_dt_max(), policy="substep")
