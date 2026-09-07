"""Move-1 keystone Rung D: closing an open diagram IS compiling an underdetermined spec.

``compile_open(target, ...)`` closes the open spec "synthesise this target from stock" by running the
shipped bounded route SEARCH, projecting each candidate onto a closed ``OpenChemDiagram`` (Rung C), and
scoring it by the M2-FP functorial objective (ΔG drive x survival, Pareto).  This is the load-bearing
call site for Rungs B/C + M2-FP.  Gates: closures are real saturated conserving diagrams; the ΔG axis
is the additive functor; the Pareto frontier admits only complete (both-axis) objectives; fail-closed on
an uncompilable spec.
"""
from smartchem.experiment.meta_compile import (
    ClosedCompilation,
    MetaCompilation,
    compile_open,
    pareto_frontier,
)
from smartchem.open_chem_diagram import ConservationStatus, OpenChemDiagram
from smartchem.smiles import parse_smiles as M

ETOAC = M("CCOC(C)=O")
ACOH = M("CC(=O)O")
ETOH = M("CCO")
WATER = M("O")


def _cc(dg, surv):
    return ClosedCompilation(route=None, net_delta_g_kj=dg, surviving_fraction=surv)


# ======================================================================================
# The Pareto frontier over the M2-FP objective -- no scalar collapse, complete-only
# ======================================================================================
class TestParetoFrontier:
    def test_dominated_closures_are_off_the_frontier(self):
        best = _cc(-50.0, 0.9)
        dominated = _cc(-10.0, 0.5)
        assert best in pareto_frontier((best, dominated))
        assert dominated not in pareto_frontier((best, dominated))

    def test_incomparable_closures_are_both_on_the_frontier(self):
        favorable_fragile = _cc(-80.0, 0.2)
        marginal_durable = _cc(-5.0, 0.99)
        front = pareto_frontier((favorable_fragile, marginal_durable))
        assert favorable_fragile in front and marginal_durable in front

    def test_an_incomplete_objective_is_never_on_the_frontier(self):
        known = _cc(-50.0, 0.9)
        unknown_survival = _cc(-99.0, None)
        assert unknown_survival not in pareto_frontier((known, unknown_survival))


# ======================================================================================
# The single-axis free-energy ranking (useful when survival is unsourced)
# ======================================================================================
class TestFreeEnergyRanking:
    def test_by_free_energy_sorts_most_favorable_first(self):
        mc = MetaCompilation(M("C"), (_cc(-10.0, None), _cc(-90.0, None), _cc(-50.0, None)))
        order = [c.net_delta_g_kj for c in mc.by_free_energy]
        assert order == [-90.0, -50.0, -10.0]

    def test_by_free_energy_omits_unknown_delta_g(self):
        mc = MetaCompilation(M("C"), (_cc(-10.0, None), _cc(None, 0.9)))
        assert [c.net_delta_g_kj for c in mc.by_free_energy] == [-10.0]


# ======================================================================================
# compile_open end-to-end: closing the spec produces real closed diagrams (the call site)
# ======================================================================================
class TestCompileOpen:
    def test_a_reachable_target_compiles_to_saturated_conserving_closures(self):
        mc = compile_open(ETOAC, reagents=(WATER,), available=(ACOH, ETOH, WATER), max_depth=2, max_routes=20)
        assert mc.is_compilable
        for closure in mc.closures:
            diagram = closure.diagram
            assert type(diagram) is OpenChemDiagram          # the Rung C call site is exercised
            assert diagram.is_saturated
            assert diagram.conservation_status() is ConservationStatus.CONSERVING
            net = closure.net_reaction()
            assert net.dom.formula == net.cod.formula        # the closure's net conserves

    def test_the_free_energy_axis_is_populated_for_a_sourced_closure(self):
        mc = compile_open(ETOAC, reagents=(WATER,), available=(ACOH, ETOH, WATER), max_depth=2, max_routes=20)
        # acetic acid + ethanol are in the extended thermo table, so at least one closure has a known drive
        assert any(c.net_delta_g_kj is not None for c in mc.closures)

    def test_an_uncompilable_spec_fails_closed(self):
        mc = compile_open(M("[Xe]"), reagents=(), available=(), max_depth=1, max_routes=5)
        assert not mc.is_compilable
        assert mc.closures == ()
        assert mc.frontier == ()
