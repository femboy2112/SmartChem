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
from smartchem.experiment.composability import (
    TransitionStatus,
    resolve_stability,
    verify_composability,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles
from smartchem.structure import resolve_structure


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


class TestStabilityKeyIsStructureNotFormula:
    """Tension-A (Move 4, ``a-reaction-key-by-formula-borrows-a-rate``): a KNOWN isomer never borrows a same-formula
    sibling's sourced record. This guards the LIVE default data -- 4-aminophenyl acetate (the O-acetyl ester) and
    paracetamol are both registered C8H9NO2 isomers, but only paracetamol carries a default stability record, so the
    ester USED to inherit paracetamol's 523 K onset + isolability + provenance as if sourced for it (a fabricated
    derivational chain, live on the default table). The fix keys ``resolve_stability`` on canonical structure: a
    resolved isomer gets its NAMED record or a loud ``None``, never the formula fallback."""

    ESTER = parse_smiles("CC(=O)Oc1ccc(N)cc1")  # 4-aminophenyl acetate, a distinct C8H9NO2 isomer of paracetamol

    def test_a_registered_isomer_does_not_borrow_a_sibling_record_on_default_data(self):
        # both are the same formula AND both are registered, structurally-distinct isomers ...
        assert self.ESTER.formula == PARA.formula
        assert resolve_structure(self.ESTER).name == "4-aminophenyl acetate"
        assert resolve_structure(PARA).name == "paracetamol"
        # ... only paracetamol has a default stability record; the ester must NOT borrow it (a loud None) ...
        assert resolve_stability(self.ESTER) is None
        # ... while paracetamol still resolves to its OWN sourced record (the named path is intact, no regression).
        para_rec = resolve_stability(PARA)
        assert para_rec is not None and para_rec.name == "paracetamol"

    def test_an_unregistered_isomer_of_a_seeded_formula_fails_closed_not_borrowed(self):
        # evil-morty MEDIUM fold -- the GENERAL borrow, closed. An unregistered isomer of a SEEDED formula must not
        # inherit a registered sibling's record (it is a different compound): ethynol (C2H2O) is an unregistered
        # isomer of ketene, 2-aminophenol (C6H7NO) of 4-aminophenol. Pre-fix, ethynol borrowed ketene's
        # isolable=False (a fabricated DEGENERATE) and 2-aminophenol borrowed 4-aminophenol's 557 K onset.
        ethynol = parse_smiles("C#CO")            # C2H2O, unregistered isomer of ketene
        aminophenol_2 = parse_smiles("Nc1ccccc1O")  # C6H7NO, unregistered isomer of 4-aminophenol
        assert resolve_structure(ethynol) is None and resolve_structure(aminophenol_2) is None
        # NON-VACUITY: the borrow-able seeded records really ARE present, so a None is the gate firing (an
        # unregistered isomer of a KNOWN formula), never an empty table.
        assert DEFAULT_STABILITY.for_formula("C2H2O") is not None   # ketene
        assert DEFAULT_STABILITY.for_formula("C6H7NO") is not None  # 4-aminophenol
        assert resolve_stability(ethynol) is None
        assert resolve_stability(aminophenol_2) is None

    def test_an_unregistered_compound_of_a_novel_formula_still_resolves_by_formula_the_injection_lever(self):
        # the universality lever survives: a structure of a formula the registry knows NOTHING of (ethyl acetate,
        # C4H8O2 -- known_compounds empty) falls through to the formula key, so a caller can still bring any such
        # chemical by injecting a formula-keyed record. (An unregistered isomer of a KNOWN formula is fail-closed
        # above; only a genuinely novel formula reaches this path, where there is no sibling to be confused with.)
        assert resolve_structure(EA) is None
        table = DEFAULT_STABILITY.with_records(StabilityRef(
            "C4H8O2", "ethyl acetate", Interval(190, 190, "K"), Interval(350, 350, "K"), None, True,
            "CRC: ethyl acetate isolable, no bench-range decomposition",
        ))
        rec = resolve_stability(EA, table)
        assert rec is not None and rec.name == "ethyl acetate"


H2O2 = parse_smiles("OO")
O2 = parse_smiles("O=O")


class TestPressurePhaseClausiusClapeyron:
    """E1 depth: a real pressure DROP that boils a condensed intermediate off across the transition is
    DEGENERATE, grounded in the Clausius-Clapeyron estimate over sourced bp + dHvap -- the operator's
    'pressure can't be reconciled' case.  Fires only when fully sourced and unambiguous.
    """

    def _pstep(self, target, reactants, products, t, p, prov):
        env = ConditionEnvelope(
            temperature=Interval(t, t, "K"), pressure=Interval(p, p, "atm"),
            status=EvidenceStatus.EXPERIMENTAL, provenance=prov,
        )
        return ExperimentStep.assembling(target, reactants, products, envelope=env)

    def test_a_pressure_drop_that_boils_the_intermediate_off_is_degenerate(self):
        # water intermediate: liquid at 5 atm / 340 K, but a gas at 0.1 atm / 340 K (CC estimate)
        s1 = self._pstep(WATER, (H2O2, H2O2), (WATER, WATER, O2), 340, 5.0, "high-P step")
        s2 = self._pstep(ACOH, (WATER, ANH), (ACOH, ACOH), 340, 0.1, "low-P step")
        comp = verify_composability(ExperimentRoute.of(s1, s2))
        assert comp.is_degenerate
        assert "Clausius-Clapeyron" in comp.degenerate_reasons[0]

    def test_the_same_pressure_is_not_a_pressure_degeneracy(self):
        s1 = self._pstep(WATER, (H2O2, H2O2), (WATER, WATER, O2), 340, 5.0, "step")
        s2 = self._pstep(ACOH, (WATER, ANH), (ACOH, ACOH), 340, 5.0, "same-P step")
        assert verify_composability(ExperimentRoute.of(s1, s2)).verdict == "COMPOSABLE"

    def test_without_sourced_dhvap_the_pressure_dimension_does_not_fabricate_a_verdict(self):
        # 4-aminophenol has no sourced dHvap in the seed -> no CC pressure verdict, not a fabricated one
        amp_acetate = parse_smiles("CC(=O)Oc1ccc(N)cc1")
        s1 = self._pstep(AMP, (amp_acetate, WATER), (AMP, ACOH), 340, 5.0, "hydrolysis")
        s2 = self._pstep(PARA, (AMP, ANH), (PARA, ACOH), 340, 0.1, "low-P")
        # not degenerate on pressure (no dHvap); the temperature check clears it -> COMPOSABLE
        assert verify_composability(ExperimentRoute.of(s1, s2)).verdict == "COMPOSABLE"


class TestNonVacuity:
    def test_single_step_route_is_never_a_vacuous_composable(self):
        route = ExperimentRoute.of(
            ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER), envelope=_env(340, 350, "esterify"))
        )
        comp = verify_composability(route)
        assert comp.verdict == "SINGLE_STEP"
        assert not comp.transitions_cleared  # nothing was composed; it is not a pass

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
