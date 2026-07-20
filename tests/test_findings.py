"""
The discharge ledger for the 2026-07-20 adversarial review.

This file used to hold 28 ``xfail(strict=True)`` tests, one per defect, each importing the
legacy engine that carried it. Those modules were retired on 2026-07-20 and consolidated
into ``smartchem/legacy.py``, so this file has been rewritten -- and the rewrite is the
point, because *deleting the module that fails a test is not the same as fixing it*.

Conflating the two is how a cleanup silently removes a capability. So every finding gets an
explicit verdict, and both kinds are pinned here:

  DISCHARGED  the new stack genuinely does the thing. The test now asserts that against
              ``category`` / ``store`` / ``pathway`` / ``thermo``, unmarked, and PASSES.
              If the capability regresses, this file goes red.

  DROPPED     the capability is gone, deliberately, and the claim was withdrawn from the
              docs. Recorded in ``RETIRED`` below and asserted to be genuinely absent, so
              it cannot creep back in unmeasured.

The old ratchet is preserved in spirit: a defect still cannot be quietly fixed (the test
would xpass) and still cannot be quietly left broken (the test would fail). What changed is
that the ratchet now tracks a live system rather than a dead one.

Original findings F1-F12 map as:

    F1  mass not conserved              DISCHARGED  unconstructible in Reaction
    F2  environment comonad inert       DISCHARGED  Store.extend + is_responsive
    F3  catalysis printed not computed  DISCHARGED  catalytic_cycles returns evidence
    F4  certificate lost by bind        DISCHARGED  Tally monoid
    F5  bond energies wrong / refused   DISCHARGED  PySCF oracle, measured
    F11 product is the reactants        DISCHARGED  Bond/Molecule topology
    F6  valency hardcoded               DROPPED     no valency model at all now
    F7  Na refusal via cap not energy   DROPPED     gate retired with engine.py
    F8  lattice gate dead and wrong     DROPPED     Poset.is_favorable retired
    F9  allotropes indistinguishable    DROPPED     polyatomic out of scope
    F10 band gap dimensionally invalid  DROPPED     solid state out of scope
    F12 crash surface and hygiene       DROPPED     the crash surface was the demo scripts
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from smartchem.category import (
    Bond,
    Config,
    ConservationError,
    Molecule,
    Reaction,
    identity,
    is_catalytic,
)
from smartchem.store import Store, is_responsive, survey
from smartchem.pathway import Pathway, Step, Tally, catalytic_cycles
from smartchem.data import bonds, CHEMICAL_ACCURACY_EV

REPO = Path(__file__).resolve().parent.parent


#: Capabilities the legacy engine claimed, which the current system does NOT have.
#: Listed so a reader can see what retirement cost, not only what it bought.
RETIRED = {
    "F6":  "environment-responsive valency. The legacy Atom.valence_cap was a hardcoded "
           "group/period rule taking no environment. The current stack models no valency "
           "at all; THE_DIFFERENCE.md withdrew the 'no hardcoded valency' claim.",
    "F7":  "multi-electron ionization search. Na(2+) was refused by a cap of 1, not by "
           "its 47 eV second ionization energy. No such search exists now.",
    "F8":  "the frontier-orbital lattice gate. Poset.is_favorable was dead code and "
           "structurally wrong (charge transfer is identically 0 for A-A pairs). "
           "THE_ORBITAL.md section VIII withdrew the lattice-as-orbitals claim.",
    "F9":  "photolysis and allotrope discrimination. Needs polyatomic support the oracle "
           "interface does not have.",
    "F10": "solid-state band gaps. The formula was dimensionally invalid; nothing "
           "replaced it.",
    "F12": "the demo scripts that carried the crash surface (degenerate dielectric, zero "
           "wavelength, zero temperature, empty species) were retired with the engine.",
}


# ======================================================================================
# F1 -- mass and charge conservation.  DISCHARGED: unconstructible, not merely absent.
# ======================================================================================
class TestF1MassIsConserved:
    """
    Legacy: ``Fe + O + Cl -> FeO`` silently dropped the chlorine (engine.py:140 built the
    product from two elements). Now the constructor refuses it.
    """

    def test_three_element_violation_is_unconstructible(self):
        with pytest.raises(ConservationError):
            Reaction(Config.atoms("Fe", "O", "Cl"),
                     Config.of(Molecule.diatomic("Fe", "O")))

    def test_nitrogen_fixation_violation_is_unconstructible(self):
        # Mo + N2 + H2 -> MoH2 was the legacy catalysis demo; it lost both nitrogens.
        mo_n2_h2 = Config.of(Molecule.atom("Mo"),
                             Molecule.diatomic("N", "N", order=3),
                             Molecule.diatomic("H", "H"))
        moh2 = Molecule(("Mo", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
        with pytest.raises(ConservationError):
            Reaction(mo_n2_h2, Config.of(moh2))

    def test_element_identity_is_conserved_not_just_count(self):
        # Same atom count, different elements: must still be refused.
        with pytest.raises(ConservationError):
            Reaction(Config.atoms("Na", "Cl"), Config.atoms("K", "Cl"))

    def test_charge_violation_is_unconstructible(self):
        with pytest.raises(ConservationError):
            Reaction(Config.atoms("Na"), Config.of(Molecule.atom("Na", charge=1)))

    def test_conservation_survives_composition(self):
        """The theorem, not the spot check: composites inherit it for free."""
        a = Config.atoms("H", "H")
        b = Config.of(Molecule.diatomic("H", "H"))
        f = Reaction(a, b, "associate")
        g = Reaction(b, a, "dissociate")
        composed = f.then(g)
        assert composed.dom.formula == composed.cod.formula
        assert composed.dom.charge == composed.cod.charge


# ======================================================================================
# F2 -- the environment.  DISCHARGED: Store.extend yields a whole surface, and a flat
#       surface is now detectable rather than invisible.
# ======================================================================================
class TestF2EnvironmentIsResponsive:
    """
    Legacy: NaCl returned byte-identical energies across dielectric 1.0 -> 109.0, because
    ``min(ionic, covalent)`` picked the covalent branch, which had no solvation term.
    """

    def test_a_solvation_surface_actually_varies(self):
        # Born solvation: stabilisation grows as (1 - 1/eps). Any real solvent model must
        # move when the dielectric moves.
        born = Store(lambda eps: -7.2 * (1.0 - 1.0 / eps), 1.0)
        eps_values = [1.0, 10.0, 40.0, 80.1, 109.0]
        assert is_responsive(born, eps_values)

    def test_a_flat_surface_is_detected_as_unresponsive(self):
        """The detector must actually detect. This is the F2 defect, reproduced."""
        ignores_env = Store(lambda eps: -4.23, 1.0)
        assert not is_responsive(ignores_env, [1.0, 10.0, 40.0, 80.1, 109.0])

    def test_the_surface_is_computed_through_extend(self):
        # survey() is implemented via extend; if extend were removed this would fail.
        born = Store(lambda eps: -7.2 * (1.0 - 1.0 / eps), 1.0)
        surface = survey(born, [1.0, 80.1])
        assert surface[1.0] == pytest.approx(0.0)
        assert surface[80.1] < -7.0
        assert len(set(surface.values())) == 2


# ======================================================================================
# F3 -- stoichiometric regeneration. DISCHARGED structurally; this is not proof of catalysis.
# ======================================================================================
class TestF3CatalysisIsDecidedNotPrinted:
    """
    Legacy: network.py:77 printed "Catalytic Loop Closed mathematically" unconditionally,
    on a supporting edge that had silently lost its nitrogen. Nothing was computed and
    nothing was returned.
    """

    def _mo_cycle(self):
        mo = Molecule.atom("Mo")
        n2 = Molecule.diatomic("N", "N", order=3)
        bound = Molecule(("Mo", "N", "N"), frozenset({Bond(0, 1), Bond(1, 2)}))
        free, complexed = Config.of(mo, n2), Config.of(bound)
        return mo, [
            Step(Reaction(free, complexed, "coordinate"), -1.2, 0.05, "ccsd(t)"),
            Step(Reaction(complexed, free, "release"), +1.0, 0.05, "ccsd(t)"),
        ], free

    def test_a_cycle_returns_evidence_not_a_bare_bool(self):
        mo, steps, free = self._mo_cycle()
        cycles = catalytic_cycles(free, steps, mo, max_depth=3)
        assert cycles, "coordinate -> release should regenerate the Mo"
        cycle = cycles[0]
        assert not isinstance(cycle, bool)
        # The claim must survive independent re-checking by the caller.
        assert is_catalytic(cycle.route, mo)

    def test_a_consumed_catalyst_yields_no_cycle(self):
        mo = Molecule.atom("Mo")
        free = Config.of(mo, Molecule.atom("N"))
        consumed = Config.of(Molecule.diatomic("Mo", "N"))
        steps = [Step(Reaction(free, consumed, "bind"), -3.0, 0.1, "ccsd(t)")]
        assert catalytic_cycles(free, steps, mo, max_depth=3) == []

    def test_a_zero_step_route_does_not_count_as_catalysis(self):
        """Doing nothing regenerates everything. That must not read as a cycle."""
        mo, steps, free = self._mo_cycle()
        for cycle in catalytic_cycles(free, steps, mo, max_depth=3):
            assert cycle.tally.steps


# ======================================================================================
# F4 -- the certificate.  DISCHARGED: Tally is a monoid, so bind cannot drop it.
# ======================================================================================
class TestF4CertificateSurvivesComposition:
    """Legacy: ``Reaction.bind`` rebuilt its result without carrying ``metadata``."""

    def test_provenance_survives_bind(self):
        start = Pathway(((1, Tally(-1.0, 0.1, ("bind Mo",), frozenset({"ccsd(t)"}))),))
        out = start.bind(lambda n: Pathway(
            ((n, Tally(-2.0, 0.1, ("insert H2",), frozenset({"ccsd(t)"}))),)))
        _, tally = out.branches[0]
        assert tally.steps == ("bind Mo", "insert H2")
        assert tally.energy_ev == pytest.approx(-3.0)

    def test_provenance_survives_a_long_chain(self):
        p = Pathway.pure(0)
        for i in range(6):
            p = p.bind(lambda n, i=i: Pathway(
                ((n + 1, Tally(-0.5, 0.1, (f"s{i}",), frozenset({"m"}))),)))
        _, tally = p.branches[0]
        assert len(tally.steps) == 6
        assert "s0" in tally.certificate and "s5" in tally.certificate

    def test_uncertainty_accumulates_rather_than_resetting(self):
        total = Tally(0.0, 0.3) + Tally(0.0, 0.4)
        assert total.uncertainty_ev == pytest.approx(0.5)   # quadrature


# ======================================================================================
# F5 -- energies.  DISCHARGED: measured, with the baseline preserved for comparison.
# ======================================================================================
class TestF5EnergiesAreMeasured:
    """
    Legacy: MAE 3.28 eV against a claimed 1 kcal/mol, with CO, NO and HCl refused outright
    -- CO being the strongest known diatomic bond.

    The accurate tiers need PySCF and real wall-clock, so they are marked and skipped by
    default. What runs unconditionally is the part that must never silently change: the
    baseline's own numbers.
    """

    def test_the_legacy_baseline_is_still_measurable(self):
        from smartchem.oracle import HeuristicOracle
        from smartchem.bench import evaluate
        result = evaluate(HeuristicOracle(), verbose=False)
        assert result.scored, "the baseline must remain runnable to stay comparable"
        assert result.mae_ev > 1.0, "if this improved, the baseline is no longer the baseline"

    def test_the_baseline_still_refuses_the_bonds_it_always_refused(self):
        from smartchem.oracle import HeuristicOracle
        oracle = HeuristicOracle()
        for formula, atoms in [("CO", ("C", "O")), ("NO", ("N", "O")), ("HCl", ("H", "Cl"))]:
            assert oracle.bond_energy(atoms) is None, (
                f"{formula} newly bonds in the legacy engine; it was preserved verbatim, "
                f"so a change here means the frozen baseline was edited"
            )

    @pytest.mark.slow
    @pytest.mark.optional_backend
    def test_ccsdt_cbs_reaches_chemical_accuracy_on_co(self):
        pyscf = pytest.importorskip("pyscf")            # noqa: F841
        from smartchem.oracle.pyscf_oracle import PySCFOracle
        ref = next(b for b in bonds() if b.formula == "CO")
        # ``estimate(symbols)`` was the old atom-pair primitive and was removed when the
        # oracle interface became species-based. This test kept calling it and went on
        # passing collection while failing on execution, because it is marked slow and
        # the slow suite was not being run -- exactly the decay tests/conftest.py warns
        # about. ``bond_energy`` is the surviving compat path, returning D_0 in eV.
        got = PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", tight_d=False).bond_energy(("C", "O"))
        assert got is not None, "CO must not be refused"
        assert abs(got - ref.d0_ev) < CHEMICAL_ACCURACY_EV


# ======================================================================================
# F11 -- objects.  DISCHARGED: bond topology makes products distinct from reactants.
# ======================================================================================
class TestF11ProductsCarryTopology:
    """
    Legacy: ``propose_bond`` returned an endomorphism on the composition bag. Every
    computed "product" was literally its own reactants, so there were no arrows at all.
    """

    def test_bonded_and_unbonded_are_different_objects(self):
        free = Config.atoms("Na", "Cl")
        bound = Config.of(Molecule.diatomic("Na", "Cl"))
        assert free != bound, "Na + Cl must not be the same object as NaCl"

    def test_a_real_reaction_is_not_an_endomorphism(self):
        free = Config.atoms("Na", "Cl")
        bound = Config.of(Molecule.diatomic("Na", "Cl"))
        rxn = Reaction(free, bound, "associate")
        assert rxn.dom != rxn.cod
        assert rxn != identity(free)

    def test_products_expose_their_bonds(self):
        nacl = Molecule.diatomic("Na", "Cl")
        assert nacl.bonds, "a diatomic must record the bond that makes it one"
        assert next(iter(nacl.bonds)) == Bond(0, 1)


# ======================================================================================
# The frozen baseline.  Retirement must not have moved the number it produces.
# ======================================================================================
class TestBaselineIsPreserved:
    """
    ``smartchem/legacy.py`` consolidated seven modules into one. That is only safe if
    ``propose_bond`` still produces exactly what it produced before, since the published
    accuracy table compares against it.

    These values were captured from commit ef4f533 (pre-consolidation) and must not drift.
    Recompute with ``python -m smartchem.bench --oracle heuristic``.

    Every digit below is a ``repr()`` of a measured float, pasted verbatim. That is not
    pedantry: the first draft of this test carried hand-extended digits for the two split
    values -- correct to the 4 decimals that had actually been printed, invented after
    that -- and the test failed on its own fabricated precision. Do not type these by hand.
    """

    #: MAE in eV over the full reference set, and over each declared split.
    EXPECTED_MAE = {None: 3.423075614354034,
                    "train": 3.379941139673477,
                    "test": 3.4949664054882965}

    @pytest.mark.parametrize("split", [None, "train", "test"])
    def test_mae_is_unchanged(self, split):
        from smartchem.oracle import HeuristicOracle
        from smartchem.bench import evaluate
        result = evaluate(HeuristicOracle(), split, verbose=False)
        assert result.mae_ev == pytest.approx(self.EXPECTED_MAE[split], abs=1e-9), (
            f"the frozen baseline moved on split={split}: consolidation was supposed to "
            f"preserve propose_bond byte-for-byte"
        )

    def test_selected_species_are_unchanged(self):
        """Spot values across the mechanism branches, to localise any drift."""
        from smartchem.oracle import HeuristicOracle
        oracle = HeuristicOracle()
        expected = {
            ("H", "H"): 4.6084272,               # homonuclear covalent branch
            ("Na", "Cl"): 12.14162534017432,     # ionic branch, ~3x too strong
            ("Na", "F"): 19.776636865431097,     # the worst case in the set
            ("O", "O"): 6.913940538440608,
        }
        for symbols, want in expected.items():
            got = oracle.bond_energy(symbols)
            assert got is not None
            assert got == pytest.approx(want, abs=1e-9), f"{symbols} drifted"


# ======================================================================================
# What retirement cost.  Asserted absent, so it cannot creep back unmeasured.
# ======================================================================================
class TestRetiredCapabilitiesAreGone:
    """
    A dropped capability must be genuinely dropped. If one of these imports starts working
    again, someone has revived a defective module and this file should say so loudly.
    """

    @pytest.mark.parametrize("module", ["engine", "comonad", "lattice", "monad",
                                        "network", "molecule", "electrochem"])
    def test_legacy_module_is_retired(self, module):
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"smartchem.{module}")

    def test_the_frozen_baseline_is_still_importable(self):
        """Retirement consolidated the engine; it did not delete the measurement."""
        from smartchem.legacy import propose_bond, Env, Situated
        assert callable(propose_bond)
        assert Env.standard().solvent_dielectric == 1.0
        assert Situated(1, Env.standard()).extract() == 1

    def test_the_defective_operations_are_not_in_the_frozen_baseline(self):
        """The retirement removed the defects, not merely relocated them."""
        import smartchem.legacy as legacy
        assert not hasattr(legacy.Poset, "is_favorable"), "F8 gate must stay retired"
        assert not hasattr(legacy.Poset, "leq"), "F8 dead code must stay retired"
        assert not hasattr(legacy.Reaction, "bind"), "F4 lossy bind must stay retired"
        assert not hasattr(legacy.Situated, "extend"), "F2 inert extend must stay retired"
        assert not hasattr(legacy.ThermoEffect, "equilibrium_constant"), "F12 div-by-zero"

    def test_demo_scripts_carrying_the_crash_surface_are_gone(self):
        leftovers = sorted(p.name for p in REPO.glob("*.py"))
        assert leftovers == [], f"legacy demo scripts still present: {leftovers}"

    def test_every_dropped_capability_is_documented(self):
        """The ledger must stay complete: no silent removals."""
        for finding in ("F6", "F7", "F8", "F9", "F10", "F12"):
            assert finding in RETIRED
            assert len(RETIRED[finding]) > 40, f"{finding} needs a real explanation"


# ======================================================================================
# Hygiene that survived the retirement
# ======================================================================================
def test_no_duplicate_periodic_table_keys():
    """He was defined twice in atoms.py; the second won and silently had mass 0.0."""
    import re
    src = (REPO / "smartchem" / "atoms.py").read_text()
    keys = re.findall(r'^\s*"([A-Za-z]{1,3})":\s*Atom\(', src, re.M)
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"duplicate periodic table entries: {dupes}"


def test_no_debug_prints_in_the_frozen_baseline():
    src = (REPO / "smartchem" / "legacy.py").read_text()
    offenders = [line.strip() for line in src.splitlines()
                 if "DEBUG" in line and "print" in line]
    assert not offenders, f"debug prints left in the baseline: {offenders}"


def test_uncertainty_is_never_negative_or_nan():
    """Even an uncalibrated reported scale must be numerically well formed."""
    t = Tally(-3.0, 0.2) + Tally(-1.0, 0.4)
    assert t.uncertainty_ev >= 0.0
    assert not math.isnan(t.uncertainty_ev)
