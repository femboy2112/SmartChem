"""Move-1 keystone Rung D: closing an open diagram IS compiling an underdetermined spec.

``compile_open(target, ...)`` closes the open spec "synthesise this target from stock" by running the
shipped bounded route SEARCH, projecting each candidate onto a closed ``OpenChemDiagram`` (Rung C), and
scoring it by the M2-FP functorial objective.  This is the load-bearing call site for Rungs B/C + M2-FP.

Honest scope (adversarial fold): the LIVE objective on today's data is the additive free-energy functor
(``by_free_energy``) -- genuinely new over ``compile_synthesis``, which never computes a net ΔG.  The
SURVIVAL axis (and thus the two-axis Pareto ``frontier``) is wired and correct but DATA-GATED: it fires
only where a sourced kinetic record reaches a multi-step intermediate (rare today), so ``frontier`` is
usually empty -- the same fail-closed, data-add-away discipline as the DOW-Br₂ thermo verdict.  The
Pareto math itself is unit-tested on synthetic objectives in ``test_functorial_physics.py``.
"""
from smartchem.experiment.functorial_physics import route_net_delta_g
from smartchem.experiment.meta_compile import ClosedCompilation, MetaCompilation, compile_open
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.open_chem_diagram import ConservationStatus, OpenChemDiagram
from smartchem.smiles import parse_smiles as M

ETOAC = M("CCOC(C)=O")
ACOH = M("CC(=O)O")
ETOH = M("CCO")
WATER = M("O")


def _step(reactants, products, target):
    return ExperimentStep.assembling(target, tuple(reactants), tuple(products))


def _one_step_route(reactants, products, target) -> ExperimentRoute:
    return ExperimentRoute.of(_step(reactants, products, target))


def _closure(route: ExperimentRoute, survival=None) -> ClosedCompilation:
    return ClosedCompilation(route, route_net_delta_g(route), survival)


# sourced single-step routes (known ΔG) for the free-energy ranking
_AMMONIA = _one_step_route([M("N#N"), M("[H][H]"), M("[H][H]"), M("[H][H]")], [M("N"), M("N")], M("N"))
_REFORM = _one_step_route([M("C"), WATER], [M("[C-]#[O+]"), M("[H][H]"), M("[H][H]"), M("[H][H]")], M("[C-]#[O+]"))
_SHIFT = _one_step_route([M("[C-]#[O+]"), WATER], [M("O=C=O"), M("[H][H]")], M("O=C=O"))
# an underivable species (HBr has no Benson group and is unsourced) -> unknown ΔG
_HBR_ROUTE = _one_step_route([M("C=C"), M("Br")], [M("CCBr")], M("CCBr"))


# ======================================================================================
# The single-axis free-energy ranking (the LIVE objective surface today)
# ======================================================================================
class TestFreeEnergyRanking:
    def test_by_free_energy_sorts_most_favorable_first(self):
        mc = MetaCompilation(M("C"), (_closure(_AMMONIA), _closure(_REFORM), _closure(_SHIFT)))
        order = [c.net_delta_g_kj for c in mc.by_free_energy]
        assert all(x is not None for x in order)
        assert order == sorted(order)  # ascending: most thermodynamically favorable (most negative) first

    def test_by_free_energy_omits_unknown_delta_g(self):
        assert route_net_delta_g(_HBR_ROUTE) is None       # HBr is unsourced AND underivable (no fabrication)
        mc = MetaCompilation(M("C"), (_closure(_SHIFT), _closure(_HBR_ROUTE)))
        ranked = mc.by_free_energy
        assert len(ranked) == 1 and ranked[0].route is _SHIFT


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

    def test_frontier_is_a_subset_of_closures(self):
        # the two-axis Pareto frontier is data-gated (survival usually None) -> a subset, often empty
        mc = compile_open(ETOAC, reagents=(WATER,), available=(ACOH, ETOH, WATER), max_depth=2, max_routes=20)
        assert set(mc.frontier).issubset(set(mc.closures))

    def test_an_uncompilable_spec_fails_closed(self):
        mc = compile_open(M("[Xe]"), reagents=(), available=(), max_depth=1, max_routes=5)
        assert not mc.is_compilable
        assert mc.closures == ()
        assert mc.frontier == ()


# ======================================================================================
# ClosedCompilation validation (adversarial fold: no route-less half-built objects)
# ======================================================================================
class TestClosedCompilationValidation:
    def test_a_route_less_compilation_is_refused(self):
        import pytest

        with pytest.raises(TypeError):
            ClosedCompilation(route=None, net_delta_g_kj=-10.0, surviving_fraction=0.9)
