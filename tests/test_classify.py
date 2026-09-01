"""L2 -- the unified epistemic classifier: ONE graded verdict over any formal combination.

The mission made literal: parse ANY formal combination and grade it KNOWN / DERIVED / PREDICTED /
HYPOTHESIZED / REFUTED / UNKNOWN, composing every rung (conservation, composability, feasibility,
equilibrium, selectivity) with no new engine and no new physics.  These tests pin each of the six grades to
a checkable condition, both sources of a REFUTED (conservation and a sourced impossibility), the
worst-step-dominated aggregation over routes and DAGs, and that the verdict carries its bucketed evidence.
"""
import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment import (
    Bucket,
    ExperimentRoute,
    ExperimentStep,
    Grade,
    SynthesisDAG,
    UnifiedVerdict,
    classify,
    classify_dag,
    classify_reaction,
    classify_route,
    classify_step,
)
from smartchem.experiment.feasibility import FeasibilityDirection, FeasibilityGrade
from smartchem.smiles import parse_smiles

H2 = parse_smiles("[H][H]")
O2 = parse_smiles("O=O")
H2O = parse_smiles("O")
N2 = parse_smiles("N#N")
NH3 = parse_smiles("N")
# the paracetamol acetylation family (a sourced-attested reaction)
APAP = parse_smiles("CC(=O)Nc1ccc(O)cc1")       # paracetamol
AMINOPHENOL = parse_smiles("Nc1ccc(O)cc1")       # 4-aminophenol
ANHYDRIDE = parse_smiles("CC(=O)OC(=O)C")        # acetic anhydride
ACOH = parse_smiles("CC(=O)O")                    # acetic acid
# unseeded species (no sourced thermo) -- a formally valid but ungrounded candidate
CYCLOPROPANE = parse_smiles("C1CC1")
PROPENE = parse_smiles("C=CC")
ACETAMIDE = parse_smiles("CC(=O)N")
# ketene: a sourced NOT-isolable intermediate
KETENE = parse_smiles("C=C=O")


def water_synthesis() -> ExperimentStep:            # 2 H2 + O2 -> 2 H2O  (seeded => DERIVED)
    return ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O))


def haber() -> ExperimentStep:                      # N2 + 3 H2 -> 2 NH3  (seeded => DERIVED at 298)
    return ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))


def acetylation() -> ExperimentStep:                # 4-aminophenol + Ac2O -> paracetamol + AcOH (attested)
    return ExperimentStep.assembling(APAP, (AMINOPHENOL, ANHYDRIDE), (APAP, ACOH))


# Off-coverage species for the derivation engine -> reliably HYPOTHESIZED steps.  (cyclopropane/propene/
# acetic-acid/acetamide, and now the THIOLS/SULFIDES and halogens, all DERIVE via the ring-strain +
# amine/acid + sulfur/halogen rungs -- so those are no longer the floor.)  What is STILL off-coverage:
# H2S (a bare S-(H)2 has no sourced group -- H2S is a library species, not a Benson group), NITRILES (the
# nitrile N needs second-nearest-neighbour keying the flat scheme can't express) and PHOSPHORUS (a deferred
# family: a real source exists but no independent NIST calibration anchor does).  These are the honest floor.
CH3SH = parse_smiles("CS")       # methanethiol -- NOW COVERED (thiol rung); kept for the mixed-grade tests
MEAMINE = parse_smiles("CN")     # methylamine -- COVERED (primary-amine rung)
H2S = parse_smiles("S")          # hydrogen sulfide -- OFF-COVERAGE (bare S-(H)2, no sourced group)
ACETONITRILE = parse_smiles("CC#N")        # off-coverage (nitrile N unrepresentable in the flat scheme)
ISOCYANIDE = parse_smiles("[C-]#[N+]C")    # methyl isocyanide, same formula C2H3N -- also off-coverage


def isomerization() -> ExperimentStep:   # acetonitrile -> methyl isocyanide (C2H3N; both off-coverage => HYPOTHESIZED)
    return ExperimentStep.assembling(ISOCYANIDE, (ACETONITRILE,), (ISOCYANIDE,))


class TestTheSixGrades:
    def test_water_synthesis_is_derived_and_favorable(self):
        v = classify_step(water_synthesis())
        assert v.grade is Grade.DERIVED
        assert v.feasibility.direction is FeasibilityDirection.FAVORABLE
        assert v.feasibility.grade is FeasibilityGrade.DERIVED
        assert abs(v.feasibility.delta_g_kj - (-474.3)) < 1.0   # the instrument reads the textbook value

    def test_haber_is_derived_at_298(self):
        v = classify_step(haber())
        assert v.grade is Grade.DERIVED
        assert v.feasibility.direction is FeasibilityDirection.FAVORABLE

    def test_haber_is_predicted_when_extrapolated_to_700(self):
        v = classify_step(haber(), temperature_k=700.0)
        assert v.grade is Grade.PREDICTED                        # the model extrapolated -> flagged
        assert v.feasibility.direction is FeasibilityDirection.UNFAVORABLE   # the real T-flip

    def test_paracetamol_acetylation_is_known_with_unknown_thermodynamics(self):
        # a documented reaction (sourced regiochemistry) whose ΔG has no sourced formation data:
        # the grade reflects the sourced attestation; the thermo gap is a separate, noted dimension.
        v = classify_step(acetylation())
        assert v.grade is Grade.KNOWN
        assert v.feasibility.grade is FeasibilityGrade.UNKNOWN      # thermo genuinely unknown, not faked
        assert "UNKNOWN" in v.headline

    def test_a_balanced_unseeded_reaction_is_hypothesized(self):
        v = classify_step(isomerization())
        assert v.grade is Grade.HYPOTHESIZED
        assert v.conserves is True                                 # balanced => a formally valid candidate

    def test_an_unbalanced_combination_is_refuted_citing_conservation(self):
        v = classify_reaction((H2O,), (H2,))                       # loses an oxygen
        assert v.grade is Grade.REFUTED
        assert v.conserves is False
        assert v.law == "conservation of mass and charge"

    def test_a_conserving_step_never_falls_below_hypothesized(self):
        # the floor invariant: any balanced reaction is at least a hypothesis; only an unbalanced one refutes.
        for step in (water_synthesis(), haber(), acetylation(), isomerization()):
            assert classify_step(step).grade is not Grade.UNKNOWN


class TestRefutedByANamedLaw:
    def test_conservation_violation_names_the_law_and_the_imbalance(self):
        v = classify_reaction((H2O,), (H2,))
        assert v.law == "conservation of mass and charge"
        assert any(q.bucket is Bucket.CONSERVATION and q.value == "violated" for q in v.findings)

    def test_a_not_isolable_intermediate_refutes_the_route(self):
        # acetic acid -> ketene + water ; ketene + acetic acid -> anhydride : ketene cannot be carried.
        make_ketene = ExperimentStep.assembling(KETENE, (ACOH,), (KETENE, H2O))
        use_ketene = ExperimentStep.assembling(ANHYDRIDE, (KETENE, ACOH), (ANHYDRIDE,))
        v = classify(ExperimentRoute.of(make_ketene, use_ketene))
        assert v.grade is Grade.REFUTED
        assert "not isolable" in v.law                             # cites the sourced fact, not a vibe

    def test_a_refuted_verdict_must_name_a_law(self):
        with pytest.raises(ValueError, match="must NAME the law"):
            UnifiedVerdict(Grade.REFUTED, "x", None, False, (), (), None, None, None, None)

    def test_a_non_refuted_verdict_carries_no_law(self):
        with pytest.raises(ValueError, match="only a REFUTED verdict"):
            UnifiedVerdict(Grade.DERIVED, "x", "some law", True, (), (), None, None, None, None)


class TestWorstStepDominatedAggregation:
    def test_a_route_is_graded_by_its_weakest_step(self):
        # step 1 (DERIVED): make NH3 ; step 2 (HYPOTHESIZED): NH3 + AcOH -> acetamide + water (unseeded)
        make_nh3 = haber()
        # step 2: NH3 + CH3SH -> CH3NH2 + H2S -- consumes the NH3 and is HYPOTHESIZED (H2S off-coverage; the
        # thiol/amine now derive, but the bare S-(H)2 of H2S has no sourced group, so the step stays UNKNOWN)
        use_nh3 = ExperimentStep.assembling(MEAMINE, (NH3, CH3SH), (MEAMINE, H2S))
        assert classify_step(make_nh3).grade is Grade.DERIVED
        assert classify_step(use_nh3).grade is Grade.HYPOTHESIZED
        v = classify(ExperimentRoute.of(make_nh3, use_nh3))
        assert v.grade is Grade.HYPOTHESIZED                       # min(DERIVED, HYPOTHESIZED)

    def test_a_convergent_dag_is_graded_by_its_weakest_step(self):
        # a convergent thio-ester synthesis: the two branches join at a thioester; the thiol branch and the
        # join are HYPOTHESIZED (H2S / thioester are off-coverage for the derivation engine).
        ALD, ETHENE, THIOL, THIOESTER = (parse_smiles(s) for s in ("CC=O", "C=C", "CCS", "CCSC(=O)C"))
        branch_acid = ExperimentStep.assembling(ACOH, (ALD, ALD, O2), (ACOH, ACOH))          # 2 MeCHO + O2 -> 2 AcOH
        branch_thiol = ExperimentStep.assembling(THIOL, (ETHENE, H2S), (THIOL,))             # ethene + H2S -> EtSH
        thioesterify = ExperimentStep.assembling(THIOESTER, (ACOH, THIOL), (THIOESTER, H2O))  # AcOH + EtSH -> thioester + H2O
        dag = SynthesisDAG.of(branch_acid, branch_thiol, thioesterify)
        assert dag.is_convergent
        v = classify(dag)
        assert v.grade is Grade.HYPOTHESIZED                       # weakest branch (thiol/thioester) is off-coverage

    def test_a_degenerate_dag_edge_refutes_the_whole_dag(self):
        make_ketene = ExperimentStep.assembling(KETENE, (ACOH,), (KETENE, H2O))
        use_ketene = ExperimentStep.assembling(ANHYDRIDE, (KETENE, ACOH), (ANHYDRIDE,))
        v = classify_dag(SynthesisDAG.of(make_ketene, use_ketene))
        assert v.grade is Grade.REFUTED
        assert "not isolable" in v.law


class TestDispatcherAndEvidence:
    def test_classify_dispatches_by_type(self):
        step = water_synthesis()
        assert classify(step).grade is classify_step(step).grade
        route = ExperimentRoute.of(step)
        assert classify(route).grade is classify_route(route).grade

    def test_classify_rejects_an_unknown_subject(self):
        with pytest.raises(TypeError, match="classify_reaction"):
            classify(42)

    def test_a_derived_verdict_carries_conservation_and_known_sourced_evidence(self):
        # bucket.py's documented promise, made concrete: a DERIVED verdict is carried by a KNOWN_SOURCED ΔG
        # over a CONSERVATION balance.
        v = classify_step(water_synthesis())
        buckets = {q.bucket for q in v.findings}
        assert Bucket.CONSERVATION in buckets
        assert Bucket.KNOWN_SOURCED in buckets

    def test_a_declared_envelope_is_context_not_reaction_attestation(self):
        # Arbitrary provenance-bearing context must not promote a formal candidate to KNOWN.  A typed,
        # direction-specific reaction attestation is a separate object; ConditionEnvelope is not one.
        declared = ConditionEnvelope(
            temperature=Interval(295.0, 300.0, "K"), provenance="because I said so",
            status=EvidenceStatus.EXPERIMENTAL,
        )
        step = ExperimentStep.assembling(ISOCYANIDE, (ACETONITRILE,), (ISOCYANIDE,), envelope=declared)
        assert step.is_declared
        assert classify_step(step).grade is Grade.HYPOTHESIZED

    def test_explain_names_the_grade(self):
        text = classify_step(haber()).explain()
        assert text.startswith("DERIVED")
