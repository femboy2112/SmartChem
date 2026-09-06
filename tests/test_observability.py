"""OBSERVABILITY-01 (queue item 1, DOW): the three-axis Observability Score.

The battery pins the load-bearing honesty (the three axes NEVER collapse), the non-vacuous DOW ranking
(Br2 dominates I2 on redundant cheap process signals), fail-closed UNKNOWN + anti-fabrication (a signature
needs a citation; the table is keyed on canonical structure, not a formula string), and the negation-aware
bridge to ROUND-17's ProcessObservationIR.
"""
from __future__ import annotations

import pytest

from experiments.observability_probe import FROZEN_HASH, content_hash
from experiments.observability_probe import validate as validate_probe
from smartchem.category import Molecule
from smartchem.decompiler_conditions import ReactionDirection
from smartchem.observation.observability import (
    OBSERVABILITY_SCHEMA,
    ObservabilityAxis,
    ObservabilityProfile,
    ObservableModality,
    ObservableSignature,
    SignalCost,
    observability_dominates,
    observability_frontier,
    observability_profile,
    observation_corroborates,
    signatures_for,
)
from smartchem.observation.process_observation import (
    ClaimStatus,
    ObservationClaim,
    ObservationPhase,
    ProcessObservationIR,
    SourceFragment,
    SourceRole,
)

_BR2 = Molecule.diatomic("Br", "Br")
_I2 = Molecule.diatomic("I", "I")


# --- the non-vacuous DOW ranking --------------------------------------------------------------------

def test_br2_has_redundant_cheap_process_signatures_non_vacuously():
    profile = observability_profile((_BR2,))
    assert profile.sourced is True
    # NON-VACUOUS: the exact three-axis strengths (2 free process, 1 free identity, 0 purity).
    assert profile.cheap_strengths == (2, 1, 0)
    # both process signals are FREE and chemistry-supplied.
    assert all(s.is_cheap for s in profile.process)
    assert {s.modality for s in profile.process} == {ObservableModality.COLOUR, ObservableModality.PHASE_SEPARATION}


def test_br2_pareto_dominates_i2_on_cheap_observability():
    br2 = observability_profile((_BR2,))
    i2 = observability_profile((_I2,))
    assert i2.cheap_strengths == (1, 1, 0)
    assert observability_dominates(br2, i2)      # more redundant process signals
    assert not observability_dominates(i2, br2)


def test_the_frontier_keeps_the_non_dominated_route():
    class Item:
        def __init__(self, mol):
            self.observability_profile = observability_profile((mol,))
    br2, i2 = Item(_BR2), Item(_I2)
    frontier = observability_frontier([br2, i2])
    assert br2 in frontier and i2 not in frontier


# --- the load-bearing honesty: the three axes NEVER collapse ----------------------------------------

def test_a_process_strong_profile_does_not_dominate_an_identity_strong_one():
    # THE anti-collapse invariant: (2,0,0) and (0,1,0) are INCOMPARABLE -- a process signal never buys
    # an identity claim (invariants 5 & 7).  Built from the REAL sourced Br2 signatures.
    br2_sigs = signatures_for(_BR2)
    proc = tuple(s for s in br2_sigs if s.axis is ObservabilityAxis.PROCESS)
    ident = tuple(s for s in br2_sigs if s.axis is ObservabilityAxis.IDENTITY)
    a = ObservabilityProfile(OBSERVABILITY_SCHEMA, process=proc)      # (2,0,0)
    b = ObservabilityProfile(OBSERVABILITY_SCHEMA, identity=ident)    # (0,1,0)
    assert a.cheap_strengths == (2, 0, 0)
    assert b.cheap_strengths == (0, 1, 0)
    assert not observability_dominates(a, b)
    assert not observability_dominates(b, a)


def test_the_profile_has_no_collapsed_total_score():
    # structural refusal (invariant 7): there is no single-number score to read.
    profile = observability_profile((_BR2,))
    assert not hasattr(profile, "overall_score")
    assert not hasattr(profile, "total")
    assert not hasattr(profile, "score")


def test_a_signature_is_bucketed_by_its_own_declared_axis_no_leakage():
    # a PROCESS signature cannot be placed in the identity bucket.
    proc_sig = signatures_for(_BR2)[0]
    assert proc_sig.axis is ObservabilityAxis.PROCESS
    with pytest.raises(ValueError, match="must declare axis IDENTITY"):
        ObservabilityProfile(OBSERVABILITY_SCHEMA, identity=(proc_sig,))


# --- fail-closed UNKNOWN + anti-fabrication ---------------------------------------------------------

def test_an_unsourced_product_is_unknown_and_incomparable():
    h2 = Molecule.diatomic("H", "H")  # absent from the sourced table
    unsourced = observability_profile((h2,))
    assert unsourced.sourced is False
    assert unsourced.cheap_strengths == (0, 0, 0)
    br2 = observability_profile((_BR2,))
    # absence of a sourced signal is NOT evidence of silent failure -> incomparable both ways.
    assert not observability_dominates(br2, unsourced)
    assert not observability_dominates(unsourced, br2)


def test_signatures_for_is_keyed_on_structure_not_formula():
    a, b = Molecule.diatomic("Br", "Br"), Molecule.diatomic("Br", "Br")
    assert signatures_for(a) == signatures_for(b) and signatures_for(a)  # same structure -> same, non-empty


def test_a_signature_requires_a_citation_no_fabrication():
    with pytest.raises(ValueError, match="citation"):
        ObservableSignature.of(ObservableModality.COLOUR, ObservabilityAxis.PROCESS, SignalCost.FREE,
                               "turns orange", "signals a state change", "   ")


def test_every_sourced_signature_carries_a_real_citation():
    for sigs in (signatures_for(_BR2), signatures_for(_I2)):
        assert sigs
        for s in sigs:
            assert s.citation and s.expected and s.discriminates


# --- instrument-only axis is not cheap observability ------------------------------------------------

def test_an_instrument_only_signal_does_not_count_as_cheap_strength():
    instr = ObservableSignature.of(ObservableModality.COLOUR, ObservabilityAxis.PURITY, SignalCost.INSTRUMENT,
                                   "an HPLC trace shows a single peak", "purity via chromatography", "a lab manual")
    profile = ObservabilityProfile(OBSERVABILITY_SCHEMA, purity=(instr,))
    assert profile.axis_strength(ObservabilityAxis.PURITY) == 0        # instrument does not count
    assert profile.is_instrument_only(ObservabilityAxis.PURITY) is True  # but the condition is surfaced


# --- the negation-aware bridge to ROUND-17 ----------------------------------------------------------

def _obs(support: str) -> ProcessObservationIR:
    return ProcessObservationIR(
        "o1", "rid", ReactionDirection.ASSEMBLY, "ctx", ObservationPhase.ANALYSIS,
        SourceFragment("vid@0:30", SourceRole.CREATOR),
        claims=(ObservationClaim(ClaimStatus.OBSERVED, "colour", support, "does not establish purity"),),
    )


def test_observation_corroborates_a_seen_signature_but_not_a_negated_one():
    colour = signatures_for(_BR2)[0]
    assert colour.modality is ObservableModality.COLOUR
    assert colour.axis is ObservabilityAxis.PROCESS
    assert observation_corroborates(colour, _obs("an orange colour appeared as expected"))
    # negation-aware (the ROUND-17 fold): a claim narrating the signal's ABSENCE does not corroborate.
    assert not observation_corroborates(colour, _obs("the colour showed no change at all"))
    assert not observation_corroborates(colour, _obs("colour was not observed"))


def test_corroboration_is_not_fooled_by_morphological_absence_the_colourless_fold():
    # evil-morty fold F1: "colourless" contains "colour" -- a substring matcher read the FAILURE signal
    # ("the solution remained colourless") as POSITIVE corroboration.  Word-boundary + morphological cues fix it.
    colour = signatures_for(_BR2)[0]
    assert not observation_corroborates(colour, _obs("the solution remained colourless throughout the run"))
    assert not observation_corroborates(colour, _obs("the flask remained colourless after addition"))
    assert not observation_corroborates(colour, _obs("the colour disappeared and the mixture went pale"))
    assert not observation_corroborates(colour, _obs("the orange colour faded to nothing"))


def test_a_bare_process_sighting_does_not_corroborate_an_identity_signature_the_leak_fold():
    # evil-morty fold F2: corroboration used only the modality, never the axis, so a process-grade
    # "a colour appeared" corroborated an IDENTITY signature -- the process->identity upgrade the module forbids.
    sigs = signatures_for(_BR2)
    ident = next(s for s in sigs if s.axis is ObservabilityAxis.IDENTITY)
    assert ident.modality is ObservableModality.COLOUR
    # a bare process colour sighting must NOT corroborate the identity (discriminating) signature.
    assert not observation_corroborates(ident, _obs("an orange colour appeared in the flask"))
    # but an observation documenting a DISCRIMINATING check does corroborate it.
    assert observation_corroborates(ident, _obs("the orange colour distinguishes it from pale green chlorine"))


def test_a_forged_profile_is_not_sourced_and_cannot_dominate_the_flag_fold():
    # evil-morty fold F4: `sourced` was a stored, forgeable flag -- a hand-built profile over FABRICATED
    # signatures could claim sourced=True and evict the real route from the frontier.  It is now COMPUTED
    # from table provenance, so a fabricated profile is not sourced and stays incomparable.
    fake = tuple(
        ObservableSignature.of(ObservableModality.COLOUR, ObservabilityAxis.PROCESS, SignalCost.FREE,
                               f"a fake signal {i}", "fabricated", "trust me")
        for i in range(3)
    )
    forged = ObservabilityProfile(OBSERVABILITY_SCHEMA, process=fake)  # cheap_strengths (3,0,0)
    assert forged.cheap_strengths == (3, 0, 0)
    assert forged.sourced is False  # NOT table-provenanced -> UNKNOWN
    real = observability_profile((_BR2,))
    assert not observability_dominates(forged, real)  # a forgery cannot dominate a real route
    # and the frontier keeps the real route, does not evict it for the forgery.
    class Item:
        def __init__(self, p):
            self.observability_profile = p
    real_item, forged_item = Item(real), Item(forged)
    assert real_item in observability_frontier([real_item, forged_item])


# --- the committed harness --------------------------------------------------------------------------

def test_the_committed_harness_validates_and_its_hash_is_frozen():
    validate_probe()
    assert content_hash() == FROZEN_HASH
