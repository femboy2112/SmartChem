"""E1 -- the composability verifier, proven on the operator's own degeneracy examples.

The teeth are SOURCED facts (a non-isolable species, a decomposition onset), compared against the route's
DECLARED envelopes.  The tests pin: the two kinds of ``DEGENERATE`` fire; ``UNKNOWN`` is loud (no sourced
data, never "fine") and closes when a caller injects sourced data (the universality lever); and the whole
route verdict is guarded against a vacuous green (a single-step route is never ``COMPOSABLE``).
"""
import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.stability import DEFAULT_STABILITY, StabilityRef
from smartchem.experiment.composability import TransitionStatus, verify_composability
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles


def _env(tlo, thi, prov, medium=""):
    return ConditionEnvelope(
        temperature=Interval(tlo, thi, "K"), medium=medium,
        status=EvidenceStatus.EXPERIMENTAL, provenance=prov,
    )


ACOH = parse_smiles("CC(=O)O")
WATER = parse_smiles("O")
KETENE = parse_smiles("C=C=O")
AMP = parse_smiles("Nc1ccc(O)cc1")
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(=O)C")
ETOH = parse_smiles("CCO")
EA = parse_smiles("CCOC(=O)C")


class TestDegenerateOnNonIsolable:
    def test_ketene_route_is_degenerate(self):
        # the operator's own example: a route through ketene, which is generated/consumed in situ
        s1 = ExperimentStep.assembling(KETENE, (ACOH,), (KETENE, WATER),
                                       envelope=_env(973, 1023, "acetic acid pyrolysis to ketene"))
        s2 = ExperimentStep.assembling(PARA, (KETENE, AMP), (PARA,),
                                       envelope=_env(273, 298, "ketene acetylation near RT"))
        comp = verify_composability(ExperimentRoute.of(s1, s2))
        assert comp.is_degenerate
        assert comp.verdict == "DEGENERATE"
        assert "not isolable" in comp.degenerate_reasons[0]


class TestDegenerateOnDecompositionOnset:
    def test_intermediate_heated_past_its_sourced_onset_is_degenerate(self):
        # 4-aminophenol decomposes >= 557 K (sourced). A transition holding it at 600 K must be DEGENERATE.
        # step 1 makes 4-aminophenol; step 2 (declared hot) consumes it.
        amp_acetate = parse_smiles("CC(=O)Oc1ccc(N)cc1")  # 4-aminophenyl acetate, C8H9NO2
        # step 1: hydrolyse the acetate to 4-aminophenol + acetic acid (target = 4-aminophenol)
        s1 = ExperimentStep.assembling(AMP, (amp_acetate, WATER), (AMP, ACOH),
                                       envelope=_env(330, 360, "acetate hydrolysis"))
        # step 2: a hot step that consumes 4-aminophenol, above its decomposition onset
        s2 = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH),
                                       envelope=_env(590, 610, "deliberately above 4-aminophenol onset"))
        comp = verify_composability(ExperimentRoute.of(s1, s2))
        assert comp.is_degenerate
        assert "decomposes" in comp.degenerate_reasons[0]

    def test_same_intermediate_below_its_onset_is_composable(self):
        amp_acetate = parse_smiles("CC(=O)Oc1ccc(N)cc1")
        s1 = ExperimentStep.assembling(AMP, (amp_acetate, WATER), (AMP, ACOH),
                                       envelope=_env(330, 360, "acetate hydrolysis"))
        s2 = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH),
                                       envelope=_env(295, 320, "well below onset"))
        comp = verify_composability(ExperimentRoute.of(s1, s2))
        assert comp.verdict == "COMPOSABLE"
        assert all(t.status is TransitionStatus.COMPOSABLE for t in comp.transitions)


class TestUnknownIsLoudAndCloses:
    def _route_with_ethyl_acetate_intermediate(self):
        s1 = ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER), envelope=_env(340, 350, "esterify"))
        s2 = ExperimentStep.assembling(PARA, (EA, AMP), (PARA, ETOH),
                                       envelope=_env(300, 320, "toy consume of ethyl acetate"))
        return ExperimentRoute.of(s1, s2)

    def test_no_sourced_data_is_unknown_not_fine(self):
        comp = verify_composability(self._route_with_ethyl_acetate_intermediate())
        assert comp.verdict == "UNKNOWN"
        assert comp.gaps and "no sourced stability data" in comp.gaps[0]

    def test_injecting_sourced_data_closes_the_gap(self):
        table = DEFAULT_STABILITY.with_records(StabilityRef(
            "C4H8O2", "ethyl acetate", Interval(190, 190, "K"), Interval(350, 350, "K"), None, True,
            "CRC: ethyl acetate bp 77 C, isolable, no bench-range decomposition",
        ))
        comp = verify_composability(self._route_with_ethyl_acetate_intermediate(), stability=table)
        assert comp.verdict == "COMPOSABLE"


class TestNonVacuity:
    def test_single_step_route_is_never_a_vacuous_composable(self):
        route = ExperimentRoute.of(
            ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER), envelope=_env(340, 350, "esterify"))
        )
        comp = verify_composability(route)
        assert comp.verdict == "SINGLE_STEP"
        assert not comp.is_runnable  # nothing was composed; it is not a pass

    def test_a_transition_count_mismatch_is_refused(self):
        from smartchem.experiment.composability import Composability
        route = ExperimentRoute.of(
            ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER), envelope=_env(340, 350, "esterify"))
        )
        with pytest.raises(ValueError, match="expected 0 transitions"):
            Composability(route, verify_composability(
                ExperimentRoute.of(
                    ExperimentStep.assembling(ACOH, (ANH, WATER), (ACOH, ACOH), envelope=_env(298, 330, "h")),
                    ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER), envelope=_env(340, 350, "e")),
                )
            ).transitions)
