"""smartchem/material_spec.py -- Round V: typed, SOURCE-AUTHORED material specifications + the ONE comparison law.

*Listen.* Round IV deleted the target whitelist and the runtime ``"glacial" in prose`` scan, then quietly rebuilt the
same sin one level up: a global adjective table (``_FORMULATION_SPECS``) that "knew" ``conc.`` meant >=95%, that
``saturated`` meant >=20%, that ``anhydrous`` meant a >=97% assay and that ``neat`` meant ``Phase.LIQUID``. Every one
of those is chemically false in general (conc. HCl is ~37%; saturated limewater is ~0.17%; MgSO4.7H2O can assay
98% "magnesium sulfate"; 10% bromine in DCM is a LIQUID). Round V moves material semantics to the EVIDENCE ORIGIN:

* the SOURCE author types what the cited procedure actually says, per use, as a :class:`MaterialSpecification`;
* the raw formulation words (``ProcedureMaterialUse.formulation``) are provenance/display ONLY -- nothing reads them;
* the generic capability compiler PROJECTS the typed spec and never learns what any adjective means;
* a load-bearing formulation word the author could NOT type (``unresolved_terms``) makes the formulation question
  UNKNOWN (F69) -- never "no constraint";
* a percentage of unknown basis stays unknown-basis (F68) and can never certify FIT;
* an ASSUMED number on either side can never discharge a requirement to FIT (F71: consistency is not evidence).

This module is frozen Round-V interface (barrier decisions 3-6). It is deliberately small: it represents only the
distinctions the current corpus forces (composition + basis, neat/solution, hydration, saturation) and refuses to be a
universal formulation ontology. It imports nothing from the capability package -- the verdict is a local tri-state
(:class:`SpecVerdict`) the capability fold maps onto its own statuses.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .contracts import Digestible

__all__ = [
    "EvidenceKind",
    "CERTIFYING_REQUIREMENT_EVIDENCE",
    "CERTIFYING_STOCK_EVIDENCE",
    "ConcentrationBasis",
    "Tolerance",
    "DilutionState",
    "HydrationState",
    "SaturationState",
    "CompositionConstraint",
    "StateClaim",
    "PhaseClaim",
    "MaterialSpecification",
    "SpecVerdict",
    "StockSpecView",
    "compare_phase",
    "compare_specification",
    "exact_fraction",
]


def exact_fraction(value: str, what: str = "value") -> Fraction:
    """Parse an EXACT decimal/integer string to a :class:`~fractions.Fraction` (no float ever touches it). Rejects
    non-ASCII digits (Wave-C K6), ``"1/3"``, ``"1_000"``, surrounding whitespace, NaN/inf, exponents beyond two digits -- one strict grammar."""
    import re

    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?", value):
        raise ValueError(f"{what} must be an exact non-negative decimal string, got {value!r}")
    return Fraction(value)


class EvidenceKind(str, Enum):
    """How strongly a numeric interval or a material-state claim is established. NOT a total order used for
    arithmetic -- the only law is which kinds may CERTIFY a FIT (below)."""

    SOURCE_QUOTED = "SOURCE_QUOTED"      # the cited source states it verbatim
    DERIVED = "DERIVED"                  # computed from typed sourced inputs by a registered kernel
    CLAMPED = "CLAMPED"                  # a sourced range clipped to a physical bound by a registered kernel
    USER_DECLARED = "USER_DECLARED"      # the bench operator declares/measured it about THEIR OWN stock
    AUTHOR_INFERRED = "AUTHOR_INFERRED"  # the evidence author's reading, not stated by the source
    ASSUMED = "ASSUMED"                  # a convenience assumption (tolerance, basis, convention)
    UNKNOWN = "UNKNOWN"


#: What a REQUIREMENT claim needs to be allowed to certify FIT: the source must actually say it (or it must be
#: derived from what the source says). A user cannot declare what a third-party source demands.
CERTIFYING_REQUIREMENT_EVIDENCE = frozenset({EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED})
#: What a STOCK claim needs: sourced/derived, or the operator's own declaration about their own bottle.
CERTIFYING_STOCK_EVIDENCE = frozenset({
    EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED, EvidenceKind.USER_DECLARED,
})


class ConcentrationBasis(str, Enum):
    """What a composition number MEANS. ``UNKNOWN`` is a first-class value: "5%" with no stated basis."""

    MASS_FRACTION = "MASS_FRACTION"        # g solute / g material, in [0, 1]
    MASS_PER_VOLUME = "MASS_PER_VOLUME"    # g solute / mL material (w/v), NOT a fraction
    VOLUME_FRACTION = "VOLUME_FRACTION"    # mL solute / mL material, in [0, 1]
    MOLAR = "MOLAR"                        # mol solute / L material, NOT a fraction
    UNKNOWN = "UNKNOWN"


class Tolerance(str, Enum):
    """How the requirement's composition interval was stated."""

    STATED_INTERVAL = "STATED_INTERVAL"            # the source gives an explicit range (or a range is DERIVED)
    FLOOR = "FLOOR"                                # the source gives a minimum only ("at least 99%"); hi is 1
    NOMINAL_UNSTATED_TOLERANCE = "NOMINAL_UNSTATED_TOLERANCE"  # "5%": a nominal point, tolerance unknown


class DilutionState(str, Enum):
    NEAT = "NEAT"          # undiluted material (NOT a phase: a LIQUID can be a dilute solution)
    SOLUTION = "SOLUTION"  # dissolved in a solvent


class HydrationState(str, Enum):
    ANHYDROUS = "ANHYDROUS"  # a hydration-state assertion, NOT a bulk-assay theorem
    HYDRATE = "HYDRATE"      # a hydrate (count in the claim's note when known)


class SaturationState(str, Enum):
    SATURATED = "SATURATED"      # species- AND temperature-dependent; never a generic numeric threshold
    UNSATURATED = "UNSATURATED"  # positively known to be below saturation


_STATE_ENUMS = (DilutionState, HydrationState, SaturationState)


def _check_evidence(value: object, what: str) -> None:
    if type(value) is not EvidenceKind:
        raise TypeError(f"{what} must be an EvidenceKind")


@dataclass(frozen=True)
class CompositionConstraint(Digestible):
    """The concentration of THE USE'S OWN SPECIES in the material, as exact decimal strings on a stated basis."""

    low: str
    high: str
    basis: ConcentrationBasis
    tolerance: Tolerance
    evidence: EvidenceKind
    note: str = ""

    def __post_init__(self) -> None:
        lo = exact_fraction(self.low, "low")
        hi = exact_fraction(self.high, "high")
        if lo > hi:
            raise ValueError("low cannot exceed high")
        if type(self.basis) is not ConcentrationBasis:
            raise TypeError("basis must be a ConcentrationBasis")
        if type(self.tolerance) is not Tolerance:
            raise TypeError("tolerance must be a Tolerance")
        _check_evidence(self.evidence, "evidence")
        if self.basis in (ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.VOLUME_FRACTION) and hi > 1:
            raise ValueError("a fraction basis must lie in [0, 1]")
        if self.tolerance is Tolerance.NOMINAL_UNSTATED_TOLERANCE and lo != hi:
            raise ValueError("a NOMINAL_UNSTATED_TOLERANCE constraint is a single nominal point (low == high)")
        if not isinstance(self.note, str):
            raise TypeError("note must be a string")

    @property
    def interval(self) -> "tuple[Fraction, Fraction]":
        return exact_fraction(self.low), exact_fraction(self.high)


@dataclass(frozen=True)
class StateClaim(Digestible):
    """One positively-claimed material state (NEAT / ANHYDROUS / SATURATED / ...) with its evidence strength."""

    state: "DilutionState | HydrationState | SaturationState"
    evidence: EvidenceKind
    note: str = ""

    def __post_init__(self) -> None:
        if type(self.state) not in _STATE_ENUMS:
            raise TypeError("state must be a DilutionState, HydrationState or SaturationState")
        _check_evidence(self.evidence, "evidence")
        if not isinstance(self.note, str):
            raise TypeError("note must be a string")


@dataclass(frozen=True)
class PhaseClaim(Digestible):
    """Round V X-high (D18): a material PHASE with the evidence that establishes it -- the phase analogue of
    :class:`StateClaim`. Round V graded composition and every material state, then left phase an ungraded scalar
    that certified FIT on a match and BLOCKED on a mismatch whoever asserted it (an author's inference included):
    the exact F71 sin -- agreement of an unsupported assertion is not evidence. There is still ONE phase vocabulary
    (:class:`smartchem.experiment.stock.Phase`); this only attaches the evidence strength to it.

    ``Phase.UNKNOWN`` is refused as a claim: an unknown phase is the ABSENCE of a claim (``None``), never a claim."""

    phase: object
    evidence: EvidenceKind
    note: str = ""

    def __post_init__(self) -> None:
        from .experiment.stock import Phase  # lazy: experiment.stock imports this module at import time

        if type(self.phase) is not Phase:
            raise TypeError("phase must be a smartchem.experiment.stock.Phase")
        if self.phase is Phase.UNKNOWN:
            raise ValueError("Phase.UNKNOWN is not a claim -- an unknown phase is the absence of a PhaseClaim (None)")
        _check_evidence(self.evidence, "evidence")
        if not isinstance(self.note, str):
            raise TypeError("note must be a string")


def compare_phase(required: "PhaseClaim | None", stock: "PhaseClaim | None") -> "tuple[SpecVerdict, str]":
    """THE phase law (D18) -- ``_compare_state``'s law exactly, applied to phase:

    * no required phase -> SATISFIES (the source demanded no phase; nothing to compare);
    * no stock claim -> UNDETERMINED (an undeclared bottle phase is UNKNOWN, never assumed);
    * a match certifies SATISFIES, and a mismatch certifies VIOLATES, ONLY when the requirement's evidence is in
      :data:`CERTIFYING_REQUIREMENT_EVIDENCE` AND the stock's is in :data:`CERTIFYING_STOCK_EVIDENCE`; otherwise
      UNDETERMINED either way (an author's inference can neither discharge nor refute a phase demand -- F71).
    """
    if required is None:
        return SpecVerdict.SATISFIES, "no phase demanded"
    if type(required) is not PhaseClaim:
        raise TypeError("required must be a PhaseClaim or None")
    label = f"phase {required.phase.value} ({required.evidence.value})"
    if stock is None:
        return SpecVerdict.UNDETERMINED, f"{label}: the stock declares no phase -- UNKNOWN, never assumed"
    if type(stock) is not PhaseClaim:
        raise TypeError("stock must be a PhaseClaim or None")
    certified = (required.evidence in CERTIFYING_REQUIREMENT_EVIDENCE
                 and stock.evidence in CERTIFYING_STOCK_EVIDENCE)
    relation = _phase_relation(required.phase, stock.phase)
    if relation == "within":
        if certified:
            return SpecVerdict.SATISFIES, (
                f"{label}: satisfied by the stock's {stock.evidence.value} phase {stock.phase.value}")
        return SpecVerdict.UNDETERMINED, (
            f"{label}: matched only on {required.evidence.value}/{stock.evidence.value} evidence -- agreement of an "
            "unsupported phase assertion is not evidence (F71)")
    if relation == "overlap":
        return SpecVerdict.UNDETERMINED, (
            f"{label}: the stock's phase {stock.phase.value} overlaps the demand without settling it (D24.7: an "
            "AQUEOUS_SOLUTION is a LIQUID, a LIQUID need not be aqueous) -- UNKNOWN, neither a match nor a refutation")
    if certified:
        return SpecVerdict.VIOLATES, f"{label}: the stock's {stock.evidence.value} phase is {stock.phase.value}"
    return SpecVerdict.UNDETERMINED, (
        f"{label}: stock phase {stock.phase.value} on {required.evidence.value}/{stock.evidence.value} evidence -- an "
        "unsupported assertion cannot refute a phase demand either")


def _phase_relation(required: object, held: object) -> str:
    """How the stock's phase ``held`` relates to the demanded phase ``required`` (D24.7, Wave-C' C5): ``"within"``
    when every material in ``held`` has the demanded phase (equal, or AQUEOUS_SOLUTION held against a LIQUID demand --
    an aqueous solution IS a liquid); ``"overlap"`` when ``held`` only MAY be the demanded phase (a LIQUID bottle
    against an AQUEOUS_SOLUTION demand); ``"disjoint"`` otherwise. Only a disjoint pair can prove VIOLATES."""
    from .experiment.stock import Phase  # lazy: experiment.stock imports this module at import time

    if held is required:
        return "within"
    if required is Phase.LIQUID and held is Phase.AQUEOUS_SOLUTION:
        return "within"
    if required is Phase.AQUEOUS_SOLUTION and held is Phase.LIQUID:
        return "overlap"
    return "disjoint"


def _check_claims(claims: object, what: str) -> None:
    if type(claims) is not tuple or any(type(c) is not StateClaim for c in claims):
        raise TypeError(f"{what} must be a tuple of StateClaim")
    kinds = [type(c.state) for c in claims]
    if len(kinds) != len(set(kinds)):
        raise ValueError(f"{what} may carry at most ONE claim per state family (dilution/hydration/saturation)")


@dataclass(frozen=True)
class MaterialSpecification(Digestible):
    """What the SOURCE says the material must BE, typed by the evidence author (never inferred by the compiler).

    ``composition`` -- the use's own species' concentration (``None`` = the source states no number).
    ``states``      -- positively-required material states, one per family.
    ``unresolved_terms`` -- load-bearing source words the author could NOT honestly type (e.g. ``"conc."`` with no
    species-scoped cited range). Non-empty => the formulation question is UNKNOWN, never silently dropped (F69).
    Phase is NOT here: it stays on ``ProcedureMaterialUse.phase`` -- one representation, one meaning.
    """

    composition: "CompositionConstraint | None" = None
    states: "tuple[StateClaim, ...]" = ()
    unresolved_terms: "tuple[str, ...]" = ()

    def __post_init__(self) -> None:
        if self.composition is not None and type(self.composition) is not CompositionConstraint:
            raise TypeError("composition must be a CompositionConstraint or None")
        _check_claims(self.states, "states")
        if type(self.unresolved_terms) is not tuple or any(
            not isinstance(t, str) or not t.strip() for t in self.unresolved_terms
        ):
            raise TypeError("unresolved_terms must be a tuple of non-empty strings")


class SpecVerdict(str, Enum):
    SATISFIES = "SATISFIES"        # provably meets every typed requirement with certifying evidence
    VIOLATES = "VIOLATES"          # provably fails at least one requirement (certifying evidence on BOTH sides)
    UNDETERMINED = "UNDETERMINED"  # anything else -- UNKNOWN, never a pass


@dataclass(frozen=True)
class StockSpecView:
    """The stock-side facts the comparison needs for ONE species in ONE bottle (built by the stock layer):
    the matched component interval (fraction, exact), its basis and evidence, and the bottle's state claims."""

    interval: "tuple[Fraction, Fraction]"
    basis: ConcentrationBasis
    interval_evidence: EvidenceKind
    states: "tuple[StateClaim, ...]"


def _compare_composition(req: CompositionConstraint, stock: StockSpecView) -> "tuple[SpecVerdict, str]":
    rlo, rhi = req.interval
    slo, shi = stock.interval
    label = f"composition [{req.low}, {req.high}] {req.basis.value}"
    if req.basis is ConcentrationBasis.UNKNOWN or stock.basis is ConcentrationBasis.UNKNOWN:
        return SpecVerdict.UNDETERMINED, (
            f"{label}: requirement basis {req.basis.value} vs stock basis {stock.basis.value} -- a percentage of "
            "unknown basis stays unknown-basis (F68), never compared as w/w")
    if req.basis is not stock.basis:
        return SpecVerdict.UNDETERMINED, (
            f"{label}: stock declared on {stock.basis.value} -- different bases are incomparable without a "
            "declared conversion (no conversion engine)")
    req_ok = req.evidence in CERTIFYING_REQUIREMENT_EVIDENCE
    stock_ok = stock.interval_evidence in CERTIFYING_STOCK_EVIDENCE
    if stock.interval_evidence is EvidenceKind.CLAMPED and slo == shi and slo in (0, 1):
        # D24.7 (Wave-C' C4): a clamp that collapsed the WHOLE quoted range onto a bound proves the quoted quantity
        # was not this fraction (an assay reading >= 100 %, say) -- it certifies no composition, exactly as it
        # certifies no purity (D18).
        return SpecVerdict.UNDETERMINED, (
            f"{label}: stock [{slo}, {shi}] is a CLAMPED range collapsed onto a bound -- the quoted quantity was not "
            "this fraction, so it certifies nothing (D24.7)")
    if req.tolerance is Tolerance.NOMINAL_UNSTATED_TOLERANCE:
        return SpecVerdict.UNDETERMINED, (
            f"{label}: a nominal value with UNSTATED tolerance can neither be certified nor refuted by an interval")
    inside = slo >= rlo and shi <= rhi
    disjoint = shi < rlo or slo > rhi
    if inside:
        if req_ok and stock_ok:
            return SpecVerdict.SATISFIES, f"{label}: stock [{float(slo):.4g}, {float(shi):.4g}] provably inside"
        return SpecVerdict.UNDETERMINED, (
            f"{label}: numerically inside, but requirement evidence {req.evidence.value} / stock evidence "
            f"{stock.interval_evidence.value} -- agreement of an unsupported assumption is not evidence (F71)")
    if disjoint:
        if req_ok and stock_ok:
            return SpecVerdict.VIOLATES, f"{label}: stock [{float(slo):.4g}, {float(shi):.4g}] provably outside"
        return SpecVerdict.UNDETERMINED, (
            f"{label}: numerically outside, but on {req.evidence.value}/{stock.interval_evidence.value} evidence "
            "-- an assumption cannot refute either")
    return SpecVerdict.UNDETERMINED, f"{label}: stock [{float(slo):.4g}, {float(shi):.4g}] straddles (measure)"


def _compare_state(required: StateClaim, stock_states: "tuple[StateClaim, ...]") -> "tuple[SpecVerdict, str]":
    family = type(required.state)
    label = f"state {required.state.value}"
    held = next((c for c in stock_states if type(c.state) is family), None)
    req_ok = required.evidence in CERTIFYING_REQUIREMENT_EVIDENCE
    if held is None:
        return SpecVerdict.UNDETERMINED, f"{label}: the stock declares no {family.__name__} -- UNKNOWN, never assumed"
    stock_ok = held.evidence in CERTIFYING_STOCK_EVIDENCE
    if held.state is required.state:
        if req_ok and stock_ok:
            return SpecVerdict.SATISFIES, f"{label}: positively declared by the stock ({held.evidence.value})"
        return SpecVerdict.UNDETERMINED, (
            f"{label}: matched only on {required.evidence.value}/{held.evidence.value} evidence -- not certifying")
    if req_ok and stock_ok:
        return SpecVerdict.VIOLATES, f"{label}: stock positively declares {held.state.value}"
    return SpecVerdict.UNDETERMINED, f"{label}: stock declares {held.state.value} on non-certifying evidence"


def compare_specification(
    spec: MaterialSpecification, stock: "StockSpecView | None",
) -> "tuple[SpecVerdict, tuple[str, ...]]":
    """THE comparison law (barrier decisions 3-6), folded VIOLATES > UNDETERMINED > SATISFIES:

    * ``unresolved_terms`` -> UNDETERMINED (F69: an untyped load-bearing formulation term is an open question);
    * composition: either basis UNKNOWN -> UNDETERMINED (F68); mismatched bases -> UNDETERMINED; nominal with unstated
      tolerance -> UNDETERMINED; inside/outside decide ONLY when both sides carry certifying evidence (F71);
    * each required state (NEAT / ANHYDROUS / SATURATED / ...) must be POSITIVELY declared by the stock -- phase,
      purity or a numeric floor never discharge it (M67/M68/M69); a contrary certified declaration VIOLATES.

    ``stock is None`` means the species' component could not be matched (the caller decides absence separately).
    An EMPTY spec (no composition, no states, no unresolved terms) SATISFIES trivially -- the source demanded
    nothing beyond identity/phase/quantity, which the capability layer checks on its own axes.
    """
    if type(spec) is not MaterialSpecification:
        raise TypeError("spec must be a MaterialSpecification")
    results: "list[tuple[SpecVerdict, str]]" = []
    for term in spec.unresolved_terms:
        results.append((SpecVerdict.UNDETERMINED,
                        f"formulation term {term!r} carries load-bearing meaning the evidence author could not type "
                        "-- UNKNOWN, never silently dropped (F69)"))
    if spec.composition is not None or spec.states:
        if stock is None:
            results.append((SpecVerdict.UNDETERMINED, "no stock composition/state view for this species"))
        else:
            if spec.composition is not None:
                results.append(_compare_composition(spec.composition, stock))
            for claim in spec.states:
                results.append(_compare_state(claim, stock.states))
    verdicts = [v for v, _ in results]
    if SpecVerdict.VIOLATES in verdicts:
        verdict = SpecVerdict.VIOLATES
    elif SpecVerdict.UNDETERMINED in verdicts:
        verdict = SpecVerdict.UNDETERMINED
    else:
        verdict = SpecVerdict.SATISFIES
    return verdict, tuple(note for _, note in results)
