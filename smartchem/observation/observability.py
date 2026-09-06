"""OBSERVABILITY-01 (queue item 1, DOW): the Observability Score -- rank routes by cheap, visible,
redundant success/failure signatures.  The poor-man ethos made into a RANKING objective.

Affordable chemistry is not only cheap reagents + cheap apparatus; it is cheap EPISTEMOLOGY -- *can I
tell, with low-cost observations, whether the process is behaving correctly?*  A route that needs
chromatography / NMR / MS after every step is structurally hostile to the ethos even when its reagents
are cheap.  So this makes observability a first-class ranking objective: prefer a route with a
MULTIMODAL, cheap, chemistry-supplied success signature -- an expected colour change AND a precipitate
AND a phase separation -- over one that fails silently.  A 70 %-yield route with three obvious naked-eye
checkpoints can beat a 90 % route that needs a $20k instrument to notice a silent failure.

Builds on ROUND-17's :class:`~smartchem.observation.process_observation.ProcessObservationIR`
VERIFICATION bucket (PROCESS-OBS-01): that bucket asks whether an evidence-backed observable/acceptance
plan EXISTS; this module RANKS how cheap, redundant, and chemistry-supplied those observables are.

THE LOAD-BEARING HONESTY (why this is not a one-number score).  A visible checkpoint is NOT chemical
proof.  A colour appearing is good evidence a STATE CHANGED; it does not establish that the final
material IS the target, or is PURE.  So the score keeps three axes SEPARATE and never collapses them to
one number (ProcessObservationIR invariants 5 & 7):

    * PROCESS  -- "something happened as expected" (a colour appears, gas evolves, a layer separates).
    * IDENTITY -- "this behaves like target X" (a characteristic colour/precipitate/spot test that
                  DISCRIMINATES the target from its neighbours).
    * PURITY   -- "little enough else is present".

A strong PROCESS signal NEVER silently upgrades to an IDENTITY or PURITY claim -- each signature
declares which axis it serves, and the profile reports the three independently.  There is deliberately
NO ``overall_score`` / ``total`` property: like ProcessObservationIR carries no readiness field, this
carries no collapsed number (a caller that wants one has to write the trade-off itself, in the open).

Section 10.4 (anti-fabrication): an observable signature is a sourced CLAIM ("Br2 is orange-red") --
you cannot invent "turns orange".  So the signatures live in a SOURCED table (:data:`OBSERVABLE_SIGNATURES`),
tiny by design and UNKNOWN elsewhere -- the same curation wall as ``SEED_CONDITIONS`` -- keyed on the
product's CANONICAL STRUCTURE (never a formula string, the fail-open lesson).  An unsourced product
yields an UNKNOWN profile that is INCOMPARABLE in the ranking (absence of a sourced signature is not
evidence the route fails silently -- it is just unmeasured).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..category import Molecule
from ..contracts import Digestible
from .process_observation import ProcessObservationIR

__all__ = [
    "OBSERVABILITY_SCHEMA",
    "ObservableModality",
    "ObservabilityAxis",
    "SignalCost",
    "ObservableSignature",
    "ObservabilityProfile",
    "OBSERVABLE_SIGNATURES",
    "signatures_for",
    "observability_profile",
    "observability_dominates",
    "observability_frontier",
    "observation_corroborates",
]

OBSERVABILITY_SCHEMA = "smartchem.observation/observability-v1"


class ObservableModality(str, Enum):
    """The free/cheap sensor the chemistry itself supplies (naked-eye or a kitchen tool)."""

    COLOUR = "COLOUR"
    PRECIPITATE = "PRECIPITATE"
    GAS_EVOLUTION = "GAS_EVOLUTION"
    PHASE_SEPARATION = "PHASE_SEPARATION"
    CRYSTALLIZATION = "CRYSTALLIZATION"
    PH_THRESHOLD = "PH_THRESHOLD"
    CONDUCTIVITY = "CONDUCTIVITY"
    TEMPERATURE_EXCURSION = "TEMPERATURE_EXCURSION"
    MELTING_FREEZING = "MELTING_FREEZING"
    MASS_CHANGE = "MASS_CHANGE"


class ObservabilityAxis(str, Enum):
    """The three SEPARATE epistemic levels a signal can serve.  Never collapsed (invariants 5 & 7)."""

    PROCESS = "PROCESS"   # something happened as expected
    IDENTITY = "IDENTITY"  # this behaves like target X (discriminates the target)
    PURITY = "PURITY"     # little enough else present


class SignalCost(str, Enum):
    """How cheap the observation is -- the poor-man ethos ranks FREE/CHEAP up, INSTRUMENT down."""

    FREE = "FREE"          # naked-eye, chemistry-supplied (colour, effervescence, a layer)
    CHEAP = "CHEAP"        # a few-dollar tool or kitchen reagent (pH paper, thermometer, starch, balance)
    INSTRUMENT = "INSTRUMENT"  # chromatography / NMR / MS / spectrophotometer -- hostile to the ethos


#: the cheap costs the ethos actually credits (an INSTRUMENT-only axis is NOT cheap observability).
_CHEAP_COSTS = frozenset({SignalCost.FREE, SignalCost.CHEAP})


@dataclass(frozen=True)
class ObservableSignature(Digestible):
    """One SOURCED observable signature of a species/reaction.

    ``expected`` is what a person would actually observe; ``discriminates`` states what it distinguishes
    the target from AND what it does not establish (invariant 5: observables have scope -- a process
    signal cannot masquerade as identity/purity).  ``citation`` is REQUIRED and must be a real reference
    (section 10.4: a signature is a sourced claim, never invented) -- an unsourced signature is refused
    at construction, so the table cannot silently carry a fabricated "turns orange".
    """

    schema_version: str
    modality: ObservableModality
    axis: ObservabilityAxis
    cost: SignalCost
    expected: str
    discriminates: str
    citation: str

    def __post_init__(self) -> None:
        if self.schema_version != OBSERVABILITY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {OBSERVABILITY_SCHEMA!r}")
        if not isinstance(self.modality, ObservableModality):
            raise TypeError("modality must be an ObservableModality")
        if not isinstance(self.axis, ObservabilityAxis):
            raise TypeError("axis must be an ObservabilityAxis")
        if not isinstance(self.cost, SignalCost):
            raise TypeError("cost must be a SignalCost")
        for name in ("expected", "discriminates", "citation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"an observable signature needs a non-empty {name} "
                                 "(section 10.4: sourced + scoped, never invented)")
            object.__setattr__(self, name, value.strip())

    @property
    def is_cheap(self) -> bool:
        return self.cost in _CHEAP_COSTS

    @classmethod
    def of(cls, modality: ObservableModality, axis: ObservabilityAxis, cost: SignalCost,
           expected: str, discriminates: str, citation: str) -> "ObservableSignature":
        return cls(OBSERVABILITY_SCHEMA, modality, axis, cost, expected, discriminates, citation)


@dataclass(frozen=True)
class ObservabilityProfile(Digestible):
    """A route/product's observability as THREE SEPARATE axes -- never one number.

    :attr:`sourced` (a COMPUTED property, never a stored field) is True iff the profile carries at least
    one signature AND every signature is provenanced to the curated :data:`OBSERVABLE_SIGNATURES` table;
    an unsourced (or fabricated) profile is UNKNOWN and incomparable in the ranking (absence of a sourced
    signature is not evidence of silent failure).  Storing ``sourced`` as a flag was an evil-morty fold:
    a hand-built profile could set ``sourced=True`` over fabricated signatures and dominate a real route,
    exactly the forgeable-flag defect the sibling module's ``provenance_digest`` computed-property
    discipline exists to prevent ([[declarative-auditor-trusts-the-field-it-polices]]).  Each axis holds
    its signatures; the CHEAP STRENGTH of an axis (:meth:`axis_strength`) is the count of its FREE/CHEAP
    signatures (higher = more, and more redundant, cheap checkpoints).  There is deliberately NO collapsed
    total (invariant 7).
    """

    schema_version: str
    process: tuple[ObservableSignature, ...] = ()
    identity: tuple[ObservableSignature, ...] = ()
    purity: tuple[ObservableSignature, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != OBSERVABILITY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {OBSERVABILITY_SCHEMA!r}")
        for name, expected_axis in (("process", ObservabilityAxis.PROCESS),
                                    ("identity", ObservabilityAxis.IDENTITY),
                                    ("purity", ObservabilityAxis.PURITY)):
            seq = getattr(self, name)
            if type(seq) is not tuple or any(type(s) is not ObservableSignature for s in seq):
                raise TypeError(f"{name} must be a tuple of ObservableSignature")
            if any(s.axis is not expected_axis for s in seq):
                raise ValueError(f"a signature in the {name} bucket must declare axis {expected_axis.value} "
                                 "(a signal is bucketed by its OWN declared axis -- no cross-axis leakage)")
            object.__setattr__(self, name, tuple(sorted(seq, key=lambda s: s.digest)))

    def _bucket(self, axis: ObservabilityAxis) -> tuple[ObservableSignature, ...]:
        return {ObservabilityAxis.PROCESS: self.process,
                ObservabilityAxis.IDENTITY: self.identity,
                ObservabilityAxis.PURITY: self.purity}[axis]

    def axis_strength(self, axis: ObservabilityAxis) -> int:
        """The number of CHEAP (FREE/CHEAP) signatures on ``axis`` -- higher is better and more redundant.
        INSTRUMENT-only signals do NOT count toward cheap epistemology (they are the expensive fallback)."""
        return sum(1 for s in self._bucket(axis) if s.is_cheap)

    def is_instrument_only(self, axis: ObservabilityAxis) -> bool:
        """True iff the axis HAS signatures but NONE are cheap -- observable only via an instrument, which
        is hostile to the poor-man ethos (a distinct, surfaced condition, not folded into the strength)."""
        bucket = self._bucket(axis)
        return bool(bucket) and all(not s.is_cheap for s in bucket)

    @property
    def cheap_strengths(self) -> tuple[int, int, int]:
        """The three cheap-axis strengths as a vector ``(process, identity, purity)`` -- reported together
        but NEVER summed.  This is the tuple the Pareto ranking compares."""
        return (self.axis_strength(ObservabilityAxis.PROCESS),
                self.axis_strength(ObservabilityAxis.IDENTITY),
                self.axis_strength(ObservabilityAxis.PURITY))

    @property
    def sourced(self) -> bool:
        """COMPUTED (never stored, evil-morty fold): True iff the profile carries at least one signature
        AND every signature is provenanced to the curated :data:`OBSERVABLE_SIGNATURES` table.  A profile
        built over fabricated signatures is NOT sourced, so it stays incomparable and cannot dominate a
        real route -- the forgeable-flag ranking flip is closed."""
        signals = self.process + self.identity + self.purity
        return bool(signals) and all(s in _ALL_SOURCED for s in signals)


def _key(product: Molecule) -> Molecule:
    """The canonical-structure key a signature attaches to (never a formula string, the fail-open lesson)."""
    if type(product) is not Molecule:
        raise TypeError("an observable signature is keyed on a Molecule product")
    return product.canonical()


def _sig(*args) -> ObservableSignature:
    return ObservableSignature.of(*args)


# Sourced observable-signature table (KNOWN chemistry; DOW-focused, tiny by design, UNKNOWN elsewhere).
# Citations are real references; keyed on canonical structure.  Note the honest asymmetry the three-axis
# separation exposes: cheap PROCESS and IDENTITY signals are common, cheap PURITY signals are rare
# (purity usually needs an instrument), so the PURITY axis is a genuine known-0 for these species.
_GE = "Greenwood & Earnshaw, Chemistry of the Elements 2nd ed., Ch. 17 (the halogens)"
_CRC = "CRC Handbook of Chemistry and Physics, 97th ed. (2016-2017)"
_VOGEL = "Vogel, Qualitative Inorganic Analysis 5th ed."

OBSERVABLE_SIGNATURES: dict[Molecule, tuple[ObservableSignature, ...]] = {
    # Br2 -- the DOW flagship: redundant, free, naked-eye process signals (Herbert Dow watched the red
    # vapour blow out), plus a weak colour-based identity discriminator.  No cheap purity signal.
    _key(Molecule.diatomic("Br", "Br")): (
        _sig(ObservableModality.COLOUR, ObservabilityAxis.PROCESS, SignalCost.FREE,
             "an orange-red colour develops in the aqueous/organic phase as elemental bromine is liberated",
             "signals that bromine was liberated (a state change); does NOT alone establish purity or "
             "exclude a coloured co-product such as I2 (violet)",
             f"{_GE}; {_CRC} (Br2 is a red-brown liquid, orange-red vapour)"),
        _sig(ObservableModality.PHASE_SEPARATION, ObservabilityAxis.PROCESS, SignalCost.FREE,
             "elemental Br2 (density ~3.10 g/mL, only slightly water-soluble) separates as a dense layer "
             "and can be air/steam-stripped as an orange vapour -- Dow's actual process",
             "signals bromine formed and left the aqueous phase; a redundant SECOND free process check "
             "alongside colour; does NOT establish identity or purity",
             f"{_CRC} (density 3.1028 g/mL); {_GE}"),
        _sig(ObservableModality.COLOUR, ObservabilityAxis.IDENTITY, SignalCost.FREE,
             "the specific orange-red colour distinguishes Br2 from Cl2 (pale yellow-green), I2 (violet) "
             "and colourless bromide",
             "discriminates the halogen by colour; a WEAK identity signal only -- does NOT quantify "
             "purity or exclude a colourless impurity",
             _GE),
    ),
    # I2 -- the contrast: one free process colour signal, plus the classic CHEAP starch-iodine identity
    # test (starch is a kitchen reagent).  Fewer redundant process signals than Br2 -> ranks below it.
    _key(Molecule.diatomic("I", "I")): (
        _sig(ObservableModality.COLOUR, ObservabilityAxis.PROCESS, SignalCost.FREE,
             "a violet vapour (I2 sublimes) or a brown solution appears as iodine is liberated",
             "signals iodine was liberated (a state change); does NOT establish purity",
             f"{_GE}; {_CRC}"),
        _sig(ObservableModality.COLOUR, ObservabilityAxis.IDENTITY, SignalCost.CHEAP,
             "a deep blue-black colour with starch (the starch-iodine test) -- starch is a kitchen reagent",
             "discriminates iodine specifically; a sensitive spot test that does NOT quantify purity",
             _VOGEL),
    ),
}

assert all(type(k) is Molecule for k in OBSERVABLE_SIGNATURES), "table keys must be canonical Molecules"

#: every curated signature, flattened -- the provenance set the COMPUTED ``ObservabilityProfile.sourced``
#: checks membership against (a fabricated signature is not in here, so it cannot forge a sourced profile).
_ALL_SOURCED: frozenset[ObservableSignature] = frozenset(
    s for sigs in OBSERVABLE_SIGNATURES.values() for s in sigs
)


def signatures_for(product: Molecule) -> tuple[ObservableSignature, ...]:
    """The sourced observable signatures for ``product``, or ``()`` (UNKNOWN) if not tabulated.

    Fail-closed and keyed on canonical structure: a species absent from the sourced table returns no
    signatures (never a fabricated one), and a same-formula species cannot borrow another's signatures.
    """
    return OBSERVABLE_SIGNATURES.get(_key(product), ())


def observability_profile(products: tuple[Molecule, ...]) -> ObservabilityProfile:
    """Build the three-axis :class:`ObservabilityProfile` for a route from its product species.

    Each product's sourced signatures are bucketed by their OWN declared axis (no cross-axis leakage).
    The resulting profile's :attr:`~ObservabilityProfile.sourced` is COMPUTED: it is True iff a product's
    signatures were found in the curated table (a wholly-unsourced route yields an UNKNOWN, incomparable
    profile).
    """
    if type(products) is not tuple or any(type(p) is not Molecule for p in products):
        raise TypeError("observability_profile takes a tuple of Molecule products")
    process: list[ObservableSignature] = []
    identity: list[ObservableSignature] = []
    purity: list[ObservableSignature] = []
    for product in products:
        for s in signatures_for(product):
            if s.axis is ObservabilityAxis.PROCESS:
                process.append(s)
            elif s.axis is ObservabilityAxis.IDENTITY:
                identity.append(s)
            else:
                purity.append(s)
    return ObservabilityProfile(OBSERVABILITY_SCHEMA, tuple(process), tuple(identity), tuple(purity))


def observability_dominates(a: ObservabilityProfile, b: ObservabilityProfile) -> bool:
    """Does ``a`` Pareto-dominate ``b`` on cheap observability?  True iff ``a`` is no-worse on ALL THREE
    axes and strictly better on at least one (higher cheap-strength is better) -- the same Pareto shape
    as :func:`smartchem.experiment.affordability.dominates`, refusing to collapse the three axes.

    UNKNOWN is INCOMPARABLE: an unsourced profile neither dominates nor is dominated (absence of a sourced
    signature is not evidence of silent failure).  So a route strong on PROCESS but weak on IDENTITY does
    NOT dominate one weak on PROCESS but strong on IDENTITY -- they are incomparable, exactly as the
    three-axis honesty requires (a process signal never buys an identity claim).
    """
    if type(a) is not ObservabilityProfile or type(b) is not ObservabilityProfile:
        raise TypeError("observability_dominates compares two ObservabilityProfile values")
    if not a.sourced or not b.sourced:
        return False  # UNKNOWN is incomparable
    a_axes, b_axes = a.cheap_strengths, b.cheap_strengths
    if any(av < bv for av, bv in zip(a_axes, b_axes)):
        return False  # worse on some axis -> not dominating
    return any(av > bv for av, bv in zip(a_axes, b_axes))  # strictly better somewhere


def observability_frontier(items: list) -> list:
    """The non-dominated subset of ``items`` (order preserved).  Each item must expose an
    ``.observability_profile`` of type :class:`ObservabilityProfile` (mirrors
    :func:`smartchem.experiment.affordability.pareto_frontier`)."""
    profiles = []
    for it in items:
        p = getattr(it, "observability_profile", None)
        if type(p) is not ObservabilityProfile:
            raise TypeError("every item must expose an .observability_profile of type ObservabilityProfile")
        profiles.append(p)
    frontier = []
    for i, it in enumerate(items):
        if not any(j != i and observability_dominates(profiles[j], profiles[i]) for j in range(len(items))):
            frontier.append(it)
    return frontier


# --------------------------------------------------------------------------------------------------
# Bridge to ROUND-17's ProcessObservationIR (honest, does NOT mint signatures).
# --------------------------------------------------------------------------------------------------

#: single-WORD negation/absence cues, matched on WORD BOUNDARIES.  Extended past the ROUND-17 hand-list to
#: cover MORPHOLOGICAL absence and appeared-then-vanished / persistence-of-null narration -- the evil-morty
#: fold where "the solution remained colourless" slipped a bare substring matcher ("colour" is inside
#: "colourless") with no cue firing.  Fail-closed: any of these vetoes a corroboration.
_NEGATION_WORDS = frozenset({
    "no", "not", "without", "lack", "lacks", "lacked", "absent", "none", "missing", "failed", "fail",
    "fails", "never", "unchanged", "negative", "nil", "neither", "nor", "unreacted",
    "colourless", "colorless",                                # morphological absence of the colour signal
    "disappeared", "disappears", "faded", "fades", "fade",    # appeared then vanished
    "ceased", "ceases", "stopped", "redissolved", "remixed", "recombined",
    "remained", "stayed",                                     # persistence of the null / starting state
})
#: multi-word / contraction negation cues, matched as SUBSTRINGS (they span word boundaries).
_NEGATION_PHRASES = ("did not", "didn't", "n't", "no change", "not observed", "failed to",
                     "never appeared", "did nothing", "stayed the same", "remained the same")
#: per-axis EVIDENCE cues: an IDENTITY / PURITY signature needs axis-appropriate language, not just the
#: modality keyword -- a bare process sighting ("a colour appeared") must NOT corroborate an IDENTITY or
#: PURITY signature (the process->identity upgrade the module forbids; evil-morty fold F2).
_IDENTITY_CUES = frozenset({"distinguish", "distinguishes", "distinguished", "characteristic", "identity",
                            "identify", "identified", "confirms", "confirmed", "specific", "matches",
                            "matched", "authentic", "diagnostic", "discriminates"})
_PURITY_CUES = frozenset({"pure", "purity", "impurity", "impurities", "single", "clean", "only",
                          "uncontaminated", "homogeneous"})


def observation_corroborates(signature: ObservableSignature, obs: ProcessObservationIR) -> bool:
    """Does ``obs`` POSITIVELY document that the expected ``signature`` was actually seen?

    A bridge to ROUND-17's evidence-ingress layer: the sourced table says a signature is EXPECTED; an
    observation can CORROBORATE that it was observed, but it can never MINT a new signature (section 10.4
    -- only the sourced table is the authority).  Three fail-closed disciplines:

    * WORD-BOUNDARY modality match (evil-morty fold F1): every token of the modality must appear as a
      WHOLE word, so "colour" does not match inside "colourless" / "discolouration".
    * NEGATION veto over the WHOLE text (the ROUND-17 fold, extended to morphological absence): a claim
      narrating the signal's ABSENCE -- "remained colourless", "the colour disappeared", "no change",
      "unchanged" -- does NOT corroborate it.
    * AXIS-AWARE evidence (evil-morty fold F2): a PROCESS signature is corroborated by the modality
      sighting; an IDENTITY / PURITY signature additionally needs axis-appropriate language (a
      discrimination / purity claim), so a bare process sighting never buys an identity/purity claim.
    """
    if type(signature) is not ObservableSignature:
        raise TypeError("signature must be an ObservableSignature")
    if type(obs) is not ProcessObservationIR:
        raise TypeError("obs must be a ProcessObservationIR")
    modality_tokens = signature.modality.value.replace("_", " ").casefold().split()
    for claim in obs.claims:
        if not claim.is_positive:
            continue
        text = f"{claim.subject}\n{claim.what_it_supports}".casefold()
        words = set(re.findall(r"[a-z]+", text))
        if not all(tok in words for tok in modality_tokens):
            continue  # the modality is not mentioned as a whole word (F1: "colourless" != "colour")
        if words & _NEGATION_WORDS or any(p in text for p in _NEGATION_PHRASES):
            continue  # the claim narrates the signal's ABSENCE -> not corroboration (fail-closed)
        if signature.axis is ObservabilityAxis.PROCESS:
            return True
        cues = _IDENTITY_CUES if signature.axis is ObservabilityAxis.IDENTITY else _PURITY_CUES
        if words & cues:
            return True  # F2: identity/purity needs its own evidence, not just the modality keyword
    return False
