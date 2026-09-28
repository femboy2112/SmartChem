"""smartchem/data/derived_evidence.py -- Round V (barrier D7): stable, digestible interval evidence.

**Chart note.** Round IV's ``DerivedIntervalEvidence`` carried a Python CALLABLE and a free ``DerivationMethod``
label. Round V's Lane C broke it three ways: (F70) the callable made the record un-digestible, so swapping the source,
method, domain or kernel moved no material/profile digest at all; (F63/F71) the method was a free LABEL -- a
``BROADENED`` band with an arbitrary width, or a ``SOURCE_QUOTED`` label over a unit-conversion kernel, both built
fine; (F72) solubility inputs reported per-VOLUME (g/100 mL, mg/L) were fed to a per-100-g-SOLVENT kernel.

The replacement, :class:`IntervalEvidence`, is a plain frozen record of exact decimal STRINGS and closed enums -- no
``Fraction``, no callable -- so ``canonical_digest`` accepts it and every field moves every digest above it. The
derivation is named by a closed :class:`DerivationKernel`; the kernel's arity, input units, admissible input evidence
and the ONE :class:`~smartchem.material_spec.EvidenceKind` it may emit live in a CLOSED registry (:data:`KERNELS`),
and ``__post_init__`` RE-COMPUTES the interval exactly (``Fraction`` internally) and refuses any mismatch of value,
units or kind. A label can no longer claim more than its arithmetic: an arbitrary symmetric width is only expressible
as ``ASSUMED_BAND_V1`` -> ``ASSUMED``; a source-quoted interval is only ``IDENTITY_SOURCE_QUOTED_V1`` over
source-quoted inputs; a g/100 mL figure has no kernel that accepts it as g/100 g.

Rounding law (one, sound): a kernel's exact result is rounded OUTWARD (low down, high up) to :data:`PRECISION_DP`
decimal places, so a non-terminating exact value (36/136 = 0.2647058823...) is represented by the smallest enclosing
6-dp decimal interval. Outward rounding only ever WIDENS the interval -- it can cost a FIT, never mint one. The
record's ``low``/``high`` must be the CANONICAL decimal spelling of that rounded value (``"1"``, not ``"1.0"``), so
equal intervals digest equally.

**Kernel semantic identity -- the 1.0 compatibility contract (Round V X-high, barrier D19).** A stored record names its
kernel by ID only (``SOLUBILITY_..._V1``); the arithmetic lives here, in code, and is NOT digested into the record.
So the ID must MEAN one function forever:

    A DerivationKernel member names ONE immutable function. Its arithmetic on every admissible input, its rounding
    precision, its admissible input names/units/evidence kinds/bases, its parent requirement and the EvidenceKind it
    emits are frozen at release. Any change -- including a bug fix -- mints a new member (``X_V2``) with its own
    known-answer vectors; ``X_V1`` keeps its implementation forever, so a stored record naming ``X_V1`` re-verifies to
    exactly its minted value. Retiring a member (refusing NEW records) is allowed; changing one is not.

Enforcement is structural, not a promise: :data:`KERNEL_KNOWN_ANSWERS` freezes known-answer vectors per member
(boundary AND refusal cases, well outside the regions any shipped record exercises) and
:func:`verify_kernel_known_answers` replays them at import -- a drifted kernel fails to import. The test
``tests/test_v0_9_kernel_semantic_lock.py`` additionally pins, as hex literals, each member's semantic-descriptor digest
(:func:`kernel_semantic_descriptor`) and the version-portable AST digest of every kernel function and arithmetic helper
(:func:`kernel_ast_digest`); editing any of them is a compatibility break by definition. (Content-addressing the
descriptor digest INSIDE each ``IntervalEvidence`` is a 0.9.5 item -- the lock above already makes a silent V1 edit
fail loudly.)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Callable

from ..contracts import Digestible
from ..material_spec import ConcentrationBasis, EvidenceKind, exact_fraction

__all__ = [
    "PRECISION_DP",
    "InputUnit",
    "DerivationKernel",
    "TypedInput",
    "IntervalEvidence",
    "KernelSpec",
    "KERNELS",
    "KernelVector",
    "KERNEL_KNOWN_ANSWERS",
    "canonical_decimal",
    "kernel_ast_digest",
    "kernel_semantic_descriptor",
    "verify_kernel_known_answers",
]

#: Outward-rounding precision for every kernel result (decimal places).
PRECISION_DP = 6

_FRACTION_BASES = frozenset({ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.VOLUME_FRACTION})
_SOURCED_KINDS = frozenset({EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED})


class InputUnit(str, Enum):
    """The physical TYPE of one raw input number. Kernels accept only the units they declare -- the type system that
    makes a per-volume solubility non-interchangeable with a per-mass one (F72)."""

    FRACTION = "FRACTION"                          # already in the record's basis, scale 1 (e.g. 0.995 w/w)
    PERCENT = "PERCENT"                            # the record's basis x 100 (e.g. 99.5 "% w/w" on MASS_FRACTION)
    PERCENT_UNSTATED_BASIS = "PERCENT_UNSTATED_BASIS"  # "5%" with no w/w / w/v / v/v stated -- never certifying
    G_PER_100G_SOLVENT = "G_PER_100G_SOLVENT"      # solubility: g solute per 100 g of SOLVENT
    G_PER_100ML_SOLVENT = "G_PER_100ML_SOLVENT"    # solubility per volume of solvent -- NOT convertible here
    G_PER_100ML_SOLUTION = "G_PER_100ML_SOLUTION"  # w/v of solution -- NOT convertible here
    MG_PER_L = "MG_PER_L"                          # mg per litre -- NOT convertible here
    MG_PER_ML = "MG_PER_ML"                        # mg per mL -- NOT convertible here


class DerivationKernel(str, Enum):
    """The CLOSED set of registered derivations (see :data:`KERNELS`)."""

    IDENTITY_SOURCE_QUOTED_V1 = "IDENTITY_SOURCE_QUOTED_V1"
    SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1 = "SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1"
    COMPLEMENT_V1 = "COMPLEMENT_V1"
    CLAMP_TO_UNIT_INTERVAL_V1 = "CLAMP_TO_UNIT_INTERVAL_V1"
    ASSUMED_BAND_V1 = "ASSUMED_BAND_V1"
    USER_DECLARED_V1 = "USER_DECLARED_V1"
    UNKNOWN_V1 = "UNKNOWN_V1"


def canonical_decimal(value: Fraction) -> str:
    """The canonical exact decimal spelling of a TERMINATING non-negative fraction: ``Fraction(1)`` -> ``"1"``,
    ``Fraction(199, 200)`` -> ``"0.995"``. Raises on a non-terminating or negative value."""
    if value < 0:
        raise ValueError("negative values have no canonical non-negative decimal spelling")
    den = value.denominator
    twos = fives = 0
    while den % 2 == 0:
        den //= 2
        twos += 1
    while den % 5 == 0:
        den //= 5
        fives += 1
    if den != 1:
        raise ValueError(f"{value} is not a terminating decimal")
    places = max(twos, fives)
    scaled = value * (10 ** places)
    digits = str(scaled.numerator).rjust(places + 1, "0")
    if places == 0:
        return digits
    whole, frac = digits[:-places], digits[-places:].rstrip("0")
    return whole if not frac else f"{whole}.{frac}"


def _round_outward(lo: Fraction, hi: Fraction) -> "tuple[Fraction, Fraction]":
    scale = 10 ** PRECISION_DP
    return Fraction(math.floor(lo * scale), scale), Fraction(math.ceil(hi * scale), scale)


_SOURCED_INPUT_KINDS = frozenset({EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED})


@dataclass(frozen=True)
class TypedInput(Digestible):
    """One raw kernel input: an exact decimal string, its physical unit, its own evidence strength and locator."""

    name: str
    value: str
    unit: InputUnit
    kind: EvidenceKind
    source_locator: str = ""
    temperature_k: "str | None" = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        exact_fraction(self.value, f"input {self.name!r} value")
        if type(self.unit) is not InputUnit:
            raise TypeError("unit must be an InputUnit")
        if type(self.kind) is not EvidenceKind:
            raise TypeError("kind must be an EvidenceKind")
        if not isinstance(self.source_locator, str):
            raise TypeError("source_locator must be a string ('' when none)")
        # Wave-C2 A1: EVERY sourced kind needs a locator -- a raw input self-labelled DERIVED/CLAMPED with nothing
        # behind it was a label-only bypass of the D7 kind gate.
        if self.kind in _SOURCED_INPUT_KINDS and not self.source_locator.strip():
            raise ValueError(f"input {self.name!r}: a {self.kind.value} input must carry a non-empty source_locator")
        if self.temperature_k is not None:
            exact_fraction(self.temperature_k, "temperature_k")

    @property
    def exact(self) -> Fraction:
        return exact_fraction(self.value)


@dataclass(frozen=True)
class KernelSpec:
    """A registry entry: admissible input-name patterns, admissible units and input kinds, the pure exact function,
    and the rule for the ONE output kind. Not a record (never digested) -- the registry is code, keyed by enum."""

    name_patterns: "tuple[tuple[str, ...], ...]"
    units: "frozenset[InputUnit]"
    input_kinds: "frozenset[EvidenceKind] | None"   # None = any kind
    output_kind: "EvidenceKind | None"               # None = the parent's kind (COMPLEMENT only)
    bases: "frozenset[ConcentrationBasis] | None"    # None = any basis
    needs_parent: bool
    fn: "Callable[[dict[str, TypedInput], IntervalEvidence | None], tuple[Fraction, Fraction]]"


def _scaled(inp: TypedInput) -> Fraction:
    v = inp.exact
    return v / 100 if inp.unit in (InputUnit.PERCENT, InputUnit.PERCENT_UNSTATED_BASIS) else v


def _k_identity(inputs: "dict[str, TypedInput]", _parent: "IntervalEvidence | None") -> "tuple[Fraction, Fraction]":
    return _scaled(inputs["low"]), _scaled(inputs["high"])


def _k_solubility(inputs: "dict[str, TypedInput]", _parent: "IntervalEvidence | None") -> "tuple[Fraction, Fraction]":
    # x = s / (s + 100): g solute per 100 g SOLVENT -> g solute per g SOLUTION. Monotone increasing in s.
    s_lo, s_hi = inputs["low"].exact, inputs["high"].exact
    return s_lo / (s_lo + 100), s_hi / (s_hi + 100)


def _k_complement(_inputs: "dict[str, TypedInput]", parent: "IntervalEvidence | None") -> "tuple[Fraction, Fraction]":
    p_lo, p_hi = parent.interval  # type: ignore[union-attr]
    return 1 - p_hi, 1 - p_lo


def _k_clamp(inputs: "dict[str, TypedInput]", _parent: "IntervalEvidence | None") -> "tuple[Fraction, Fraction]":
    if "floor" in inputs:
        lo = _scaled(inputs["floor"])
        if lo > 1:
            raise ValueError("CLAMP_TO_UNIT_INTERVAL_V1: a floor above 1 cannot be clamped into [0, 1]")
        # the source states only a floor ("at least 97%"); the open upper end is clipped to the physical bound 1
        return max(Fraction(0), lo), Fraction(1)
    lo, hi = _scaled(inputs["low"]), _scaled(inputs["high"])
    if not (lo < 0 or hi > 1):
        raise ValueError("CLAMP_TO_UNIT_INTERVAL_V1 must actually clip: the quoted range already lies in [0, 1] "
                         "(use IDENTITY_SOURCE_QUOTED_V1)")
    if lo > 1 or hi < 0:
        raise ValueError("CLAMP_TO_UNIT_INTERVAL_V1: the quoted range lies entirely outside [0, 1]")
    return max(Fraction(0), lo), min(Fraction(1), hi)


def _k_band(inputs: "dict[str, TypedInput]", _parent: "IntervalEvidence | None") -> "tuple[Fraction, Fraction]":
    if "nominal" in inputs:
        n, w = _scaled(inputs["nominal"]), _scaled(inputs["half_width"])
        return n - w, n + w
    return _scaled(inputs["low"]), _scaled(inputs["high"])


def _k_unknown(_inputs: "dict[str, TypedInput]", _parent: "IntervalEvidence | None") -> "tuple[Fraction, Fraction]":
    return Fraction(0), Fraction(1)


_SCALE_UNITS = frozenset({InputUnit.FRACTION, InputUnit.PERCENT})

#: THE closed kernel registry (barrier D7). Adding a kernel is a code change reviewed as such -- never data.
KERNELS: "dict[DerivationKernel, KernelSpec]" = {
    DerivationKernel.IDENTITY_SOURCE_QUOTED_V1: KernelSpec(
        name_patterns=(("low", "high"),), units=_SCALE_UNITS,
        input_kinds=frozenset({EvidenceKind.SOURCE_QUOTED}), output_kind=EvidenceKind.SOURCE_QUOTED,
        bases=None, needs_parent=False, fn=_k_identity),
    DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1: KernelSpec(
        name_patterns=(("low", "high"),), units=frozenset({InputUnit.G_PER_100G_SOLVENT}),
        input_kinds=frozenset({EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED}), output_kind=EvidenceKind.DERIVED,
        bases=frozenset({ConcentrationBasis.MASS_FRACTION}), needs_parent=False, fn=_k_solubility),
    # Wave-C1/C2: 1 - x is the solvent ONLY under an unsourced BINARY-mixture premise -> the complement is ASSUMED,
    # never an inherited SOURCE_QUOTED/DERIVED strength (the H2SO4 complement is not a sourced water assay).
    DerivationKernel.COMPLEMENT_V1: KernelSpec(
        name_patterns=((),), units=frozenset(), input_kinds=None, output_kind=EvidenceKind.ASSUMED,
        bases=_FRACTION_BASES, needs_parent=True, fn=_k_complement),
    DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1: KernelSpec(
        name_patterns=(("low", "high"), ("floor",)), units=_SCALE_UNITS,
        input_kinds=frozenset({EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED}), output_kind=EvidenceKind.CLAMPED,
        bases=_FRACTION_BASES, needs_parent=False, fn=_k_clamp),
    DerivationKernel.ASSUMED_BAND_V1: KernelSpec(
        name_patterns=(("low", "high"), ("nominal", "half_width")),
        units=_SCALE_UNITS | {InputUnit.PERCENT_UNSTATED_BASIS},
        input_kinds=None, output_kind=EvidenceKind.ASSUMED, bases=None, needs_parent=False, fn=_k_band),
    DerivationKernel.USER_DECLARED_V1: KernelSpec(
        name_patterns=(("low", "high"),), units=_SCALE_UNITS,
        input_kinds=frozenset({EvidenceKind.USER_DECLARED}), output_kind=EvidenceKind.USER_DECLARED,
        bases=None, needs_parent=False, fn=_k_identity),
    DerivationKernel.UNKNOWN_V1: KernelSpec(
        name_patterns=((),), units=frozenset(), input_kinds=None, output_kind=EvidenceKind.UNKNOWN,
        bases=None, needs_parent=False, fn=_k_unknown),
}


@dataclass(frozen=True)
class IntervalEvidence(Digestible):
    """One component-fraction interval WITH the typed, re-computable derivation that produced it (barrier D7).

    Invariant (enforced at construction): ``(low, high)`` is exactly the registered ``kernel`` applied to ``inputs``
    (and ``parent`` for COMPLEMENT), outward-rounded to :data:`PRECISION_DP`, canonically spelled; ``kind`` is the
    one kind that kernel may emit; every input carries a unit and kind the kernel admits; sourced kinds
    (SOURCE_QUOTED / DERIVED / CLAMPED) cite at least one locator and cover every input's own locator.
    """

    kind: EvidenceKind
    low: str
    high: str
    basis: ConcentrationBasis
    source_locators: "tuple[str, ...]"
    kernel: DerivationKernel
    inputs: "tuple[TypedInput, ...]"
    domain_of_validity: str
    parent: "IntervalEvidence | None" = None

    def __post_init__(self) -> None:
        if type(self.kind) is not EvidenceKind:
            raise TypeError("kind must be an EvidenceKind")
        if type(self.basis) is not ConcentrationBasis:
            raise TypeError("basis must be a ConcentrationBasis")
        # Wave-C2 A2: a FRACTION/PERCENT number on a MOLAR basis is a unit/basis lie (6 % is not 6 mol/L). No MOLAR
        # input unit exists yet, so a MOLAR interval can only be UNKNOWN_V1 -- honest until one is added.
        if self.basis is ConcentrationBasis.MOLAR and any(
                isinstance(i, TypedInput) and i.unit in _SCALE_UNITS for i in (self.inputs or ())):
            raise ValueError("a FRACTION/PERCENT input cannot carry a MOLAR basis (no unit conversion)")
        if type(self.kernel) is not DerivationKernel:
            raise TypeError("kernel must be a DerivationKernel (the closed registry)")
        if type(self.source_locators) is not tuple or any(
            not isinstance(s, str) or not s.strip() for s in self.source_locators
        ):
            raise TypeError("source_locators must be a tuple of non-empty strings")
        if type(self.inputs) is not tuple or any(type(i) is not TypedInput for i in self.inputs):
            raise TypeError("inputs must be a tuple of TypedInput")
        if not isinstance(self.domain_of_validity, str) or not self.domain_of_validity.strip():
            raise ValueError("domain_of_validity must be a non-empty string")
        lo, hi = exact_fraction(self.low, "low"), exact_fraction(self.high, "high")
        if lo > hi:
            raise ValueError("low cannot exceed high")
        if self.basis in _FRACTION_BASES and hi > 1:
            raise ValueError("a fraction basis must lie in [0, 1]")

        spec = KERNELS[self.kernel]
        # -- parent ------------------------------------------------------------------------------------------
        if spec.needs_parent:
            if type(self.parent) is not IntervalEvidence:
                raise TypeError(f"{self.kernel.value} requires an IntervalEvidence parent")
            if self.parent.basis is not self.basis:
                raise ValueError(f"{self.kernel.value}: basis must equal the parent's basis")
            if self.source_locators != self.parent.source_locators:
                raise ValueError(f"{self.kernel.value}: source_locators must be the parent's (no new citation)")
        elif self.parent is not None:
            raise ValueError(f"{self.kernel.value} takes no parent")
        if spec.bases is not None and self.basis not in spec.bases:
            raise ValueError(f"{self.kernel.value} is not valid on basis {self.basis.value}")
        # -- inputs: names, units, kinds ---------------------------------------------------------------------
        names = tuple(i.name for i in self.inputs)
        if names not in spec.name_patterns:
            raise ValueError(f"{self.kernel.value} takes inputs named one of {spec.name_patterns}, got {names}")
        for inp in self.inputs:
            if inp.unit not in spec.units:
                raise ValueError(
                    f"{self.kernel.value} refuses input {inp.name!r} in unit {inp.unit.value} "
                    f"(admits {sorted(u.value for u in spec.units)}) -- never relabel one unit as another (F72)")
            if spec.input_kinds is not None and inp.kind not in spec.input_kinds:
                raise ValueError(
                    f"{self.kernel.value} refuses input {inp.name!r} of evidence {inp.kind.value} "
                    f"(admits {sorted(k.value for k in spec.input_kinds)})")
        # -- output kind (F63/F71: the label is the kernel's, never free) ------------------------------------
        expected_kind = self.parent.kind if spec.output_kind is None else spec.output_kind  # type: ignore[union-attr]
        if self.kind is not expected_kind:
            raise ValueError(
                f"{self.kernel.value} may only emit {expected_kind.value}, not {self.kind.value} -- a label cannot "
                "claim more than its arithmetic")
        if self.kind in _SOURCED_KINDS:
            if not self.source_locators:
                raise ValueError(f"{self.kind.value} evidence must cite at least one source locator")
            missing = {i.source_locator for i in self.inputs if i.source_locator} - set(self.source_locators)
            if missing:
                raise ValueError(f"input locators {sorted(missing)} are not among the record's source_locators")
        # -- the load-bearing check: exact recomputation --------------------------------------------------------
        r_lo, r_hi = self.recompute()
        if (self.low, self.high) != (canonical_decimal(r_lo), canonical_decimal(r_hi)):
            raise ValueError(
                f"{self.kernel.value} recomputes [{canonical_decimal(r_lo)}, {canonical_decimal(r_hi)}] "
                f"(outward-rounded to {PRECISION_DP} dp, canonical spelling), not the stated [{self.low}, {self.high}]")

    # -- construction helper -------------------------------------------------------------------------------------

    @classmethod
    def build(
        cls, *, kernel: DerivationKernel, basis: ConcentrationBasis, inputs: "tuple[TypedInput, ...]" = (),
        source_locators: "tuple[str, ...]" = (), domain_of_validity: str, parent: "IntervalEvidence | None" = None,
    ) -> "IntervalEvidence":
        """Construct by running the kernel: endpoints and kind are COMPUTED, then re-verified by ``__post_init__``.
        The stored record is still fully explicit (and a hand-written record must match it exactly)."""
        spec = KERNELS[kernel]
        by_name = {i.name: i for i in inputs}
        probe_kind = parent.kind if (spec.output_kind is None and parent is not None) else spec.output_kind
        if spec.needs_parent and parent is None:
            raise TypeError(f"{kernel.value} requires an IntervalEvidence parent")
        lo, hi = _round_outward(*spec.fn(by_name, parent if spec.needs_parent else None))  # type: ignore[arg-type]
        if spec.needs_parent and not source_locators:
            source_locators = parent.source_locators  # type: ignore[union-attr]
        return cls(probe_kind, canonical_decimal(lo), canonical_decimal(hi), basis,  # type: ignore[arg-type]
                   tuple(source_locators), kernel, tuple(inputs), domain_of_validity, parent)

    # -- reading ---------------------------------------------------------------------------------------------------

    @property
    def interval(self) -> "tuple[Fraction, Fraction]":
        return exact_fraction(self.low), exact_fraction(self.high)

    def recompute(self) -> "tuple[Fraction, Fraction]":
        """Re-run the registered kernel on the typed inputs (exact), outward-rounded to :data:`PRECISION_DP`."""
        spec = KERNELS[self.kernel]
        return _round_outward(*spec.fn({i.name: i for i in self.inputs}, self.parent))

    def verify(self) -> bool:
        """True iff the stated interval equals the recomputation (always True for a constructed record)."""
        r_lo, r_hi = self.recompute()
        return (self.low, self.high) == (canonical_decimal(r_lo), canonical_decimal(r_hi))

    def as_floats(self) -> "tuple[float, float]":
        """``(float, float)`` for the ``MaterialComponent`` slots. Exact round-trip: every endpoint has at most
        :data:`PRECISION_DP` decimals, so ``Fraction(repr(float(x))) == Fraction(x)``."""
        return float(exact_fraction(self.low)), float(exact_fraction(self.high))


# == D19: kernel semantic identity -- frozen known-answer vectors, replayed at import ==============================

@dataclass(frozen=True)
class KernelVector:
    """One frozen known-answer vector for a registered kernel: a labelled input set (``(name, value, unit, kind)``
    rows; a sourced kind gets the fixed vector locator), an optional PARENT (the label of an earlier vector, for
    COMPLEMENT), and EITHER the exact expected ``(low, high, kind)`` OR ``refuses`` -- a substring of the
    ``ValueError`` the kernel must raise. Plain strings and enums only, so the vector itself is part of the frozen
    semantic descriptor."""

    label: str
    kernel: DerivationKernel
    basis: ConcentrationBasis
    inputs: "tuple[tuple[str, str, InputUnit, EvidenceKind], ...]" = ()
    parent: "str | None" = None
    low: "str | None" = None
    high: "str | None" = None
    kind: "EvidenceKind | None" = None
    refuses: "str | None" = None


_VECTOR_LOCATOR = "kernel-known-answer-vector (D19)"
_MF, _UB = ConcentrationBasis.MASS_FRACTION, ConcentrationBasis.UNKNOWN
_SQ, _AS, _UD = EvidenceKind.SOURCE_QUOTED, EvidenceKind.ASSUMED, EvidenceKind.USER_DECLARED
_PCT, _FR, _S100 = InputUnit.PERCENT, InputUnit.FRACTION, InputUnit.G_PER_100G_SOLVENT

#: THE frozen known-answer vectors (D19). Every DerivationKernel member has at least one; the values are the exact
#: outward-rounded canonical spellings the V1 implementations produce. NEVER edit a row to follow a code change --
#: a failing row means the change must mint a new ``_V2`` member instead.
KERNEL_KNOWN_ANSWERS: "tuple[KernelVector, ...]" = (
    KernelVector("identity-percent", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, _MF,
                 (("low", "95.0", _PCT, _SQ), ("high", "98.0", _PCT, _SQ)), low="0.95", high="0.98", kind=_SQ),
    KernelVector("identity-fraction", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, _MF,
                 (("low", "0.25", _FR, _SQ), ("high", "0.5", _FR, _SQ)), low="0.25", high="0.5", kind=_SQ),
    KernelVector("identity-refuses-assumed-input", DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, _MF,
                 (("low", "95.0", _PCT, _AS), ("high", "98.0", _PCT, _AS)), refuses="refuses input"),
    KernelVector("solubility-nacl-36", DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, _MF,
                 (("low", "36.0", _S100, _SQ), ("high", "36.0", _S100, _SQ)),
                 low="0.264705", high="0.264706", kind=EvidenceKind.DERIVED),
    KernelVector("solubility-60", DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, _MF,
                 (("low", "60", _S100, _SQ), ("high", "60", _S100, _SQ)),
                 low="0.375", high="0.375", kind=EvidenceKind.DERIVED),
    KernelVector("solubility-band-0-300", DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, _MF,
                 (("low", "0", _S100, _SQ), ("high", "300", _S100, _SQ)),
                 low="0", high="0.75", kind=EvidenceKind.DERIVED),
    KernelVector("solubility-refuses-per-volume", DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
                 _MF, (("low", "36.0", InputUnit.G_PER_100ML_SOLVENT, _SQ),
                       ("high", "36.0", InputUnit.G_PER_100ML_SOLVENT, _SQ)), refuses="refuses input"),
    KernelVector("complement-of-nacl", DerivationKernel.COMPLEMENT_V1, _MF, parent="solubility-nacl-36",
                 low="0.735294", high="0.735295", kind=_AS),
    KernelVector("clamp-titration-99.5-100.5", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, _MF,
                 (("low", "99.5", _PCT, _SQ), ("high", "100.5", _PCT, _SQ)), low="0.995", high="1",
                 kind=EvidenceKind.CLAMPED),
    KernelVector("clamp-floor-97", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, _MF,
                 (("floor", "97", _PCT, _SQ),), low="0.97", high="1", kind=EvidenceKind.CLAMPED),
    KernelVector("clamp-refuses-no-clip", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, _MF,
                 (("low", "95.0", _PCT, _SQ), ("high", "98.0", _PCT, _SQ)), refuses="must actually clip"),
    KernelVector("clamp-refuses-floor-above-1", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, _MF,
                 (("floor", "101", _PCT, _SQ),), refuses="a floor above 1"),
    KernelVector("clamp-refuses-wholly-outside", DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, _MF,
                 (("low", "101", _PCT, _SQ), ("high", "102", _PCT, _SQ)), refuses="entirely outside"),
    KernelVector("band-nominal-5-half-0.5", DerivationKernel.ASSUMED_BAND_V1, _UB,
                 (("nominal", "5", InputUnit.PERCENT_UNSTATED_BASIS, _SQ),
                  ("half_width", "0.5", InputUnit.PERCENT_UNSTATED_BASIS, _AS)), low="0.045", high="0.055", kind=_AS),
    KernelVector("band-low-high", DerivationKernel.ASSUMED_BAND_V1, _UB,
                 (("low", "0.04", _FR, _AS), ("high", "0.08", _FR, _AS)), low="0.04", high="0.08", kind=_AS),
    KernelVector("user-declared-pure", DerivationKernel.USER_DECLARED_V1, _MF,
                 (("low", "1", _FR, _UD), ("high", "1", _FR, _UD)), low="1", high="1", kind=_UD),
    KernelVector("user-declared-refuses-sourced-kind", DerivationKernel.USER_DECLARED_V1, _MF,
                 (("low", "1", _FR, _SQ), ("high", "1", _FR, _SQ)), refuses="refuses input"),
    KernelVector("unknown-full-interval", DerivationKernel.UNKNOWN_V1, _UB, low="0", high="1",
                 kind=EvidenceKind.UNKNOWN),
)


def _vector_inputs(vector: KernelVector) -> "tuple[TypedInput, ...]":
    return tuple(
        TypedInput(name, value, unit, kind, _VECTOR_LOCATOR if kind in _SOURCED_INPUT_KINDS else "")
        for name, value, unit, kind in vector.inputs)


def verify_kernel_known_answers() -> None:
    """Replay every :data:`KERNEL_KNOWN_ANSWERS` vector through :meth:`IntervalEvidence.build` (the kernel fn, the
    outward rounding, the canonical spelling and the output-kind rule, together) and raise ``RuntimeError`` on ANY
    deviation -- a value, a kind, a refusal that no longer refuses, or a DerivationKernel member with no vector.
    Called at import: a silently-edited V1 kernel makes this module fail to import (D19)."""
    by_label: "dict[str, IntervalEvidence]" = {}
    covered: "set[DerivationKernel]" = set()
    for v in KERNEL_KNOWN_ANSWERS:
        covered.add(v.kernel)
        parent = by_label.get(v.parent) if v.parent is not None else None
        if v.parent is not None and parent is None:
            raise RuntimeError(f"kernel vector {v.label!r}: parent vector {v.parent!r} is not an earlier accepted vector")
        locators = (_VECTOR_LOCATOR,) if any(k in _SOURCED_INPUT_KINDS for *_n, k in v.inputs) else ()
        try:
            record = IntervalEvidence.build(kernel=v.kernel, basis=v.basis, inputs=_vector_inputs(v),
                                            source_locators=locators, domain_of_validity="D19 known-answer vector",
                                            parent=parent)
        except ValueError as exc:
            if v.refuses is not None and v.refuses in str(exc):
                continue
            raise RuntimeError(f"kernel vector {v.label!r} ({v.kernel.value}) raised unexpectedly: {exc}") from exc
        if v.refuses is not None:
            raise RuntimeError(f"kernel vector {v.label!r} ({v.kernel.value}) must refuse ({v.refuses!r}) but built "
                               f"[{record.low}, {record.high}] -- the V1 semantics changed; mint a _V2")
        if (record.low, record.high, record.kind) != (v.low, v.high, v.kind):
            raise RuntimeError(
                f"kernel vector {v.label!r} ({v.kernel.value}) now yields [{record.low}, {record.high}] "
                f"{record.kind.value}, frozen answer [{v.low}, {v.high}] {v.kind.value if v.kind else None} -- a V1 "
                "kernel's arithmetic or kind changed; mint a _V2 member instead (D19)")
        by_label[v.label] = record
    missing = set(DerivationKernel) - covered
    if missing:
        raise RuntimeError(f"DerivationKernel member(s) with no known-answer vector: {sorted(m.value for m in missing)}")


def kernel_semantic_descriptor(kernel: DerivationKernel) -> "tuple":
    """The canonical, hashable DECLARED semantics of one registered kernel: its name, admissible input-name patterns,
    units, input kinds, output kind, bases, parent requirement, :data:`PRECISION_DP`, and its frozen vectors. The lock
    test pins ``canonical_digest`` of this per member."""
    spec = KERNELS[kernel]

    def _sorted_values(xs: "frozenset | None") -> "tuple[str, ...] | None":
        return None if xs is None else tuple(sorted(x.value for x in xs))

    vectors = tuple(
        (v.label, v.basis.value, tuple((n, val, u.value, k.value) for n, val, u, k in v.inputs), v.parent, v.low,
         v.high, v.kind.value if v.kind else None, v.refuses)
        for v in KERNEL_KNOWN_ANSWERS if v.kernel is kernel)
    return (kernel.value, spec.name_patterns, _sorted_values(spec.units), _sorted_values(spec.input_kinds),
            spec.output_kind.value if spec.output_kind else None, _sorted_values(spec.bases), spec.needs_parent,
            PRECISION_DP, vectors)


def _canonical_ast(node: object) -> object:
    """A Python-version-portable canonical form of an AST: node type + its ``_fields`` (never line/column
    attributes), with ``None`` and empty-list fields DROPPED -- so a field a newer Python adds empty (3.12's
    ``type_params=[]``) does not move the digest, while every real code edit does."""
    import ast
    if isinstance(node, ast.AST):
        return (type(node).__name__, tuple(
            (name, _canonical_ast(value)) for name in node._fields
            if (value := getattr(node, name, None)) is not None and value != []))
    if isinstance(node, list):
        return tuple(_canonical_ast(x) for x in node)
    return node


def kernel_ast_digest(fn: "Callable[..., object]") -> str:
    """The digest of ``fn``'s canonical AST -- insensitive to comments, formatting and docstrings, sensitive to every
    code edit. The lock test pins it for every kernel function and arithmetic helper, so any edit to a V1 kernel's
    arithmetic is caught by name."""
    import ast
    import hashlib
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    for node in ast.walk(tree):  # a docstring is prose, not arithmetic: rewording one is never a semantic change
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body
                and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return hashlib.sha256(repr(_canonical_ast(tree)).encode("utf-8")).hexdigest()


verify_kernel_known_answers()
