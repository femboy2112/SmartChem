"""smartchem/stream_disposition.py -- the StreamDisposition vocabulary (0.9.5 barrier S10, freeze §6).

Round V left every spent stream, residual and byproduct an UNKNOWN waste obligation for a reason: nothing in the model
could SAY what happens to one. The whole-``WasteRequirement`` replacement the old zero-FIT witness used discharged
everything at once and was bound to nothing. This module is the one permitted vocabulary closure: a source-quoted
statement about ONE structurally-named stream of ONE reaction, and nothing broader.

* **Subject algebra (CLOSED, four kinds).** ``BYPRODUCT`` (core = the species' structure key), ``RESIDUAL`` (core =
  the species key of a typed SUBSTRATE/REACTANT/CATALYST use; one per (step, species)), ``OP_STREAM`` (op ordinal +
  :func:`op_core`), ``USE_STREAM`` ((op ordinal, use index) + :func:`use_core`). Every subject carries
  ``step_signature`` = :func:`reaction_signature` of its step. Keys are injective and deliberately NOT reorder-invariant:
  a prose edit never unbinds, a reorder makes the subject VANISH and binding refuses -- never a silent rebind.
  Untyped op material and untyped step input are EXCLUDED: no subject kind can name them (their material terms stay
  unresolved on their own, so a disposition there could only ever decorate the waste axis).
* **Values.** ``CONSUMED_COMPLETELY`` (RESIDUAL only; the step must net-consume the species -- checked at binding),
  ``RECOVERED`` (RESIDUAL or USE_STREAM; names ``via_op``, a DISTILL/FILTER/SEPARATE op of the same procedure -- checked
  by :class:`~smartchem.procedure_evidence.ProcedureEvidence`), ``ROUTED`` (any kind; carries a
  :class:`~smartchem.capability.enums.WasteCapability`). Absence is UNKNOWN; there is no NONE/UNKNOWN member.
* **Evidence.** ``SOURCE_QUOTED`` only, plus a non-empty locator. The accepted-source gate is derive-time
  (``procedure.is_sourced`` in ``derive_waste``), like every other sourcing gate in the model.

Where the laws live: STRUCTURE here and in ``ProcedureEvidence``/``ExperimentStep`` construction (loud, and a wire
forgery is refused at decode); SOUNDNESS in ``derive_waste``'s exact-subject lookup (an unbound disposition can never
match anything). This module decides no verdict.

LEAF: it imports no part of the capability package and not ``smartchem.service`` (``experiment/step.py`` must be able
to load it). ``WasteCapability`` is NOT moved here -- an enum is digested by its qualified class name, so moving it
would shift every ``CapabilityProfile`` digest. The ``category`` type check therefore reads the class out of
``sys.modules`` instead of importing it: a genuine ``WasteCapability`` member cannot exist unless its module is already
loaded, so the check is exact without an import edge. (A clean incision needs no drain.)
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .contracts import Digestible, canonical_digest
from .material_spec import EvidenceKind
from .procedure_evidence import OperationKind, OperationRole, ProcedureMaterialRole

if TYPE_CHECKING:
    from .capability.enums import WasteCapability
    from .category import Molecule
    from .procedure_evidence import ProcedureMaterialUse, ProcedureOperation

__all__ = [
    "SubjectKind",
    "DispositionValue",
    "StreamSubject",
    "StreamDisposition",
    "LEGAL_SUBJECT_KINDS",
    "CERTIFYING_DISPOSITION_EVIDENCE",
    "SPENT_STREAM_ROLES",
    "SPENT_STREAM_OP_ROLES",
    "SPENT_STREAM_OP_KINDS",
    "CONSUMED_ROLES",
    "CATALYST_ROLES",
    "RESIDUAL_ROLES",
    "RECOVERY_OP_KINDS",
    "reaction_signature",
    "species_key",
    "use_core",
    "op_core",
    "stream_subjects",
    "binding_refusal",
]


class SubjectKind(str, Enum):
    """The CLOSED set of things a disposition can be about (freeze §6). A fifth kind is a barrier change."""

    BYPRODUCT = "BYPRODUCT"
    RESIDUAL = "RESIDUAL"
    OP_STREAM = "OP_STREAM"
    USE_STREAM = "USE_STREAM"


class DispositionValue(str, Enum):
    """What the source says happens to the subject. ABSENCE is UNKNOWN; no speculative states."""

    CONSUMED_COMPLETELY = "CONSUMED_COMPLETELY"
    RECOVERED = "RECOVERED"
    ROUTED = "ROUTED"


#: LAW L2 -- the whole kind x value table. The two values that REDUCE an obligation are narrow; ROUTED only ever adds a
#: requirement, so it may name any subject. RECOVERED on a BYPRODUCT is refused on purpose: recovering a byproduct is a
#: second-PRODUCT claim (identity/purity/yield of an unmodelled product), parked at requirements.py's stream note.
LEGAL_SUBJECT_KINDS: "dict[DispositionValue, frozenset[SubjectKind]]" = {
    DispositionValue.CONSUMED_COMPLETELY: frozenset({SubjectKind.RESIDUAL}),
    DispositionValue.RECOVERED: frozenset({SubjectKind.RESIDUAL, SubjectKind.USE_STREAM}),
    DispositionValue.ROUTED: frozenset(SubjectKind),
}

#: Stricter than ``CERTIFYING_REQUIREMENT_EVIDENCE``: DERIVED/CLAMPED are kernel-backed numeric labels and no kernel
#: derives a disposition, so a bare DERIVED here would be an unbacked label wearing a lab coat.
CERTIFYING_DISPOSITION_EVIDENCE: "frozenset[EvidenceKind]" = frozenset({EvidenceKind.SOURCE_QUOTED})

#: The stream/residual role tables ``capability/waste.py`` keys its obligations on (identical members; the waste
#: consumer imports these back when it lands -- until then a test pins the two copies equal).
SPENT_STREAM_ROLES: "frozenset[ProcedureMaterialRole]" = frozenset({
    ProcedureMaterialRole.WASH, ProcedureMaterialRole.RINSE, ProcedureMaterialRole.DRY,
    ProcedureMaterialRole.SOLVENT, ProcedureMaterialRole.NEUTRALIZE,
})
SPENT_STREAM_OP_ROLES: "frozenset[OperationRole]" = frozenset({OperationRole.WASH, OperationRole.RECRYSTALLIZATION})
SPENT_STREAM_OP_KINDS: "frozenset[OperationKind]" = frozenset({
    OperationKind.SEPARATE, OperationKind.FILTER, OperationKind.DRY, OperationKind.DISTILL,
})
CONSUMED_ROLES: "frozenset[ProcedureMaterialRole]" = frozenset({
    ProcedureMaterialRole.SUBSTRATE, ProcedureMaterialRole.REACTANT,
})
CATALYST_ROLES: "frozenset[ProcedureMaterialRole]" = frozenset({ProcedureMaterialRole.CATALYST})
#: the roles whose leftover is a species-level RESIDUAL subject.
RESIDUAL_ROLES: "frozenset[ProcedureMaterialRole]" = CONSUMED_ROLES | CATALYST_ROLES
#: the op kinds that can REALIZE a recovery (``via_op``). That op's own spent stream stays a separate obligation.
RECOVERY_OP_KINDS: "frozenset[OperationKind]" = frozenset({
    OperationKind.DISTILL, OperationKind.FILTER, OperationKind.SEPARATE,
})

_STRUCT_PREFIX = "struct:"
_STRUCT_ASGIVEN = "struct-asgiven:"
_NAME_PREFIX = "name:"
_ASGIVEN = "asgiven:"
_HEX64 = re.compile(r"[0-9a-f]{64}")


# -- structural keys (pure functions of ONE step) ----------------------------------------------------------------------

def _fold_name(text: str) -> str:
    """strip + casefold + collapse internal whitespace (the one name normaliser S8 hands to ``stock``)."""
    return " ".join(text.strip().casefold().split())


def _structure_key(molecule: "Molecule") -> str:
    """``"struct:" + resonance_identity(m)``; an ``asgiven:`` fallback maps to ``"struct-asgiven:" + ...``. Byte-for-byte
    the key S7's ``stock.structure_key`` produces (freeze §7) -- retarget to that one authority once it lands."""
    from .smiles import resonance_identity  # lazy, as step.py's _ident: keeps this module a cheap leaf

    ident = resonance_identity(molecule)
    if ident.startswith(_ASGIVEN):
        return _STRUCT_ASGIVEN + ident[len(_ASGIVEN):]
    return _STRUCT_PREFIX + ident


def reaction_signature(step_like: object) -> str:
    """THE step signature: the digest of the sorted ``resonance_identity`` multisets of ``step_like.reactants`` and
    ``step_like.products``. Resonance-invariant (two Kekulé spellings of one species agree), constitution-exact (an
    isomer is a different reaction), blind to envelope/prose. One function; every consumer imports it."""
    from .smiles import resonance_identity

    return canonical_digest((
        tuple(sorted(resonance_identity(m) for m in step_like.reactants)),
        tuple(sorted(resonance_identity(m) for m in step_like.products)),
    ))


def species_key(identity: "Molecule | None", name: str) -> str:
    """The species a residual is about: its structure key when the use carries an identity, else ``"name:"`` + the
    folded name (an ionic salt has no single connected Molecule; its name is the only honest key)."""
    if identity is not None:
        return _structure_key(identity)
    return _NAME_PREFIX + _fold_name(name)


def use_core(use: "ProcedureMaterialUse") -> str:
    """The semantic core of one typed use: (role, species). Name/formulation/quantity text/locator are not in it, so
    rewording a structure-bearing use never unbinds; retyping its role or species does."""
    return canonical_digest((use.role.value, species_key(use.identity, use.name)))


def op_core(op: "ProcedureOperation") -> str:
    """The semantic core of one operation: kind, role, its uses' cores in order, and its folded ``materials`` set.
    Locator, apparatus and every EvidenceField are presentation here and stay out."""
    return canonical_digest((
        op.kind.value,
        op.role.value,
        tuple(use_core(u) for u in op.material_uses),
        tuple(sorted(_fold_name(m) for m in op.materials)),
    ))


# -- the records -------------------------------------------------------------------------------------------------------

def _positive_int(value: object) -> bool:
    return not isinstance(value, bool) and type(value) is int and value >= 1


@dataclass(frozen=True)
class StreamSubject(Digestible):
    """One structurally-named stream of one reaction. Build it from :func:`stream_subjects`; a hand-made subject that
    names nothing real is refused when its step is constructed."""

    kind: SubjectKind
    step_signature: str
    ordinal: "int | None"
    index: "int | None"
    core: str

    def __post_init__(self) -> None:
        if type(self.kind) is not SubjectKind:
            raise TypeError("kind must be a SubjectKind")
        if not isinstance(self.step_signature, str) or not _HEX64.fullmatch(self.step_signature):
            raise ValueError("step_signature must be a reaction_signature() digest (64 lowercase hex)")
        if not isinstance(self.core, str) or not self.core:
            raise ValueError("core must be a non-empty structural key")
        if self.kind in (SubjectKind.BYPRODUCT, SubjectKind.RESIDUAL):
            if self.ordinal is not None or self.index is not None:
                raise ValueError(f"a {self.kind.value} subject is species-level: ordinal and index must be None")
            prefixes = (_STRUCT_PREFIX, _STRUCT_ASGIVEN) + ((_NAME_PREFIX,) if self.kind is SubjectKind.RESIDUAL else ())
            if not self.core.startswith(prefixes):
                raise ValueError(f"a {self.kind.value} core must be a species key with prefix in {prefixes}")
        else:
            if not _positive_int(self.ordinal):
                raise ValueError(f"a {self.kind.value} subject needs a positive int op ordinal")
            if self.kind is SubjectKind.OP_STREAM and self.index is not None:
                raise ValueError("an OP_STREAM subject has no use index")
            if self.kind is SubjectKind.USE_STREAM and (
                    isinstance(self.index, bool) or type(self.index) is not int or self.index < 0):
                raise ValueError("a USE_STREAM subject needs a non-negative int use index")
            if not _HEX64.fullmatch(self.core):
                raise ValueError(f"a {self.kind.value} core must be a use_core()/op_core() digest")

    @property
    def sort_key(self) -> tuple:
        """A total order for canonical sorting (kinds partition the space; None only where a kind never has one)."""
        return (self.kind.value, -1 if self.ordinal is None else self.ordinal,
                -1 if self.index is None else self.index, self.core, self.step_signature)

    @property
    def label(self) -> str:
        where = "" if self.ordinal is None else f" op #{self.ordinal}" + (
            "" if self.index is None else f" use[{self.index}]")
        return f"{self.kind.value}{where} core={self.core}"


def _waste_capability_class() -> "type | None":
    # Read, never import (see the module docstring): a real member implies its module is loaded.
    enums = sys.modules.get("smartchem.capability.enums")
    return None if enums is None else getattr(enums, "WasteCapability", None)


@dataclass(frozen=True)
class StreamDisposition(Digestible):
    """What the cited source says happens to ONE subject. Construction refuses every structurally-illegal claim (L2,
    evidence, category/via_op shape); binding to a real step is ``ExperimentStep``'s job, discharge is ``derive_waste``'s.
    No free-text note: a presentation host would widen the D13 boundary for nothing."""

    subject: StreamSubject
    value: DispositionValue
    evidence: EvidenceKind
    locator: str
    category: "WasteCapability | None" = None
    via_op: "int | None" = None

    def __post_init__(self) -> None:
        if type(self.subject) is not StreamSubject:
            raise TypeError("subject must be a StreamSubject")
        if type(self.value) is not DispositionValue:
            raise TypeError("value must be a DispositionValue")
        if type(self.evidence) is not EvidenceKind:
            raise TypeError("evidence must be an EvidenceKind")
        if self.evidence not in CERTIFYING_DISPOSITION_EVIDENCE:
            raise ValueError(
                f"a stream disposition must be SOURCE_QUOTED; {self.evidence.value} cannot certify one (no kernel "
                f"derives a disposition, and an author's/user's word is not the source's)")
        if not isinstance(self.locator, str) or not self.locator.strip():
            raise ValueError("a stream disposition must carry a non-empty source locator")
        object.__setattr__(self, "locator", self.locator.strip())
        if self.subject.kind not in LEGAL_SUBJECT_KINDS[self.value]:
            raise ValueError(f"{self.value.value} may not name a {self.subject.kind.value} subject (L2)")
        if self.value is DispositionValue.ROUTED:
            waste_capability = _waste_capability_class()
            if self.category is None or waste_capability is None or type(self.category) is not waste_capability:
                raise TypeError("ROUTED needs category = a smartchem.capability.enums.WasteCapability member")
        elif self.category is not None:
            raise ValueError(f"only ROUTED carries a category; {self.value.value} does not")
        if self.value is DispositionValue.RECOVERED:
            if not _positive_int(self.via_op):
                raise ValueError("RECOVERED must name via_op, the positive ordinal of the op that realizes the recovery")
        elif self.via_op is not None:
            raise ValueError(f"only RECOVERED names a via_op; {self.value.value} does not")


# -- the subject universe and the step binding -------------------------------------------------------------------------

def _subject_universe(step: object) -> "dict[StreamSubject, tuple]":
    """Every subject ``step`` has, mapped to the typed uses behind it (RESIDUAL) or ``()``. Pure function of the step."""
    sig = reaction_signature(step)
    out: "dict[StreamSubject, tuple]" = {}
    for molecule in step.byproducts:
        out.setdefault(StreamSubject(SubjectKind.BYPRODUCT, sig, None, None, _structure_key(molecule)), ())
    procedure = step.envelope.procedure
    if procedure is None:
        return out
    for op in procedure.operations:
        if op.role in SPENT_STREAM_OP_ROLES or op.kind in SPENT_STREAM_OP_KINDS:
            out[StreamSubject(SubjectKind.OP_STREAM, sig, op.ordinal, None, op_core(op))] = ()
        for index, use in enumerate(op.material_uses):
            if use.role in SPENT_STREAM_ROLES:
                out[StreamSubject(SubjectKind.USE_STREAM, sig, op.ordinal, index, use_core(use))] = ()
            if use.role in RESIDUAL_ROLES:
                subject = StreamSubject(SubjectKind.RESIDUAL, sig, None, None, species_key(use.identity, use.name))
                out[subject] = out.get(subject, ()) + (use,)
    return out


def stream_subjects(step: object) -> "tuple[StreamSubject, ...]":
    """Every subject a disposition on ``step`` may name, canonically sorted. Excluded kinds have no entry by design."""
    return tuple(sorted(_subject_universe(step), key=lambda s: s.sort_key))


def binding_refusal(step: object, dispositions: "tuple[StreamDisposition, ...]") -> "str | None":
    """Why ``dispositions`` cannot ride on ``step`` (the first reason), or ``None`` when every one binds. Refuses a
    foreign ``step_signature``, a subject that does not exist in this step (reordered op, retyped role, other species),
    and CONSUMED_COMPLETELY on a species the step does not net-consume. Never rebinds anything."""
    if not dispositions:
        return None
    sig = reaction_signature(step)
    universe = _subject_universe(step)
    for disposition in dispositions:
        subject = disposition.subject
        if subject.step_signature != sig:
            return (f"stream disposition on {subject.label} is bound to reaction signature {subject.step_signature}, "
                    f"but this step's reaction signature is {sig} -- a disposition is never transplanted onto another "
                    f"reaction")
        if subject not in universe:
            return (f"stream disposition names {subject.label}, which does not exist in this step (an op reorder, a "
                    f"role change or a different species makes a subject vanish) -- refused, never silently rebound")
        if disposition.value is DispositionValue.CONSUMED_COMPLETELY:
            for use in universe[subject]:
                if use.role not in CONSUMED_ROLES or use.identity is None or not step.net_consumes(use.identity):
                    return (f"CONSUMED_COMPLETELY on {subject.label} needs every typed use of that species to be an "
                            f"identity-bearing SUBSTRATE/REACTANT the step's balanced reaction NET-consumes; "
                            f"{use.name!r} ({use.role.value}) is not")
    return None
