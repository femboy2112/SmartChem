"""v0.8 Round II -- typed procedure evidence (Blocker B's foundation).

Round I stopped the compiler cosplaying as a bench chemist by refusing to award ``PROCESS_SPECIFIED``:
``readiness.process_representation_is_complete`` was a hard ``return False`` because the fields a complete
bench procedure needs -- scale, ordered operations, addition rate, a reaction endpoint, quench, workup,
separation, wash, drying, purification, analytical acceptance -- *did not exist as structured data*. The old
``ProcessRequirements`` (``process_constraints.py``) is a whole-step resource/logistics schema (times,
attention, equipment, T/P extrema), and it is deliberately NOT extended here: those are the exact fields the
0.9 capability gate compares against an operator's ``ProcessBounds``, and co-mingling "what the source procedure
SAID" with "what MY bench can DO" is one refactor away from a capability fact laundering into a procedure claim
(Wave A Lane E, seam B).

So this module is a SEPARATE type describing only *what the literature-supported procedure specified*. It hangs
off :class:`~smartchem.conditions.ConditionEnvelope` as a new ``procedure`` field, INSIDE the digest-covered,
replay-reconstructed envelope (Wave A Lane F design condition: a ``compare=False`` field, or one not
reconstructed into the replayed step, would float free of both the digest bind and the load-time
re-derivation). Nothing here decides whether a particular lab can execute the procedure -- there is no field for
equipment *ownership*, vessel ratings, ventilation, waste routing, affordability, or measurement precision. Those
are 0.9. ``apparatus`` names the equipment the *paper's* bench used; it is never compared against an inventory.

The 0.8/0.9 line, stated once: **0.8 answers "what did the source procedure specify?"; 0.9 answers "can this
capability profile execute it?".** This module lives entirely on the 0.8 side.

Well-formedness (structural coherence) is enforced in ``__post_init__`` here. COMPLETENESS (is the represented
procedure sufficient to earn ``PROCESS_SPECIFIED``) is a separate predicate,
``readiness.procedure_representation_is_complete``, and SOURCING (is it backed by an accepted citation) is a
third, separate gate in the readiness evaluator. Three axes, never collapsed (plan
``docs/research/V0_8_ROUND_II_PROCEDURE_EVIDENCE_PLAN_v0.1.md`` D2/D3/D4).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .contracts import Digestible
from .provenance import SourceCitation

if TYPE_CHECKING:
    from .category import Molecule
    from .conditions import Interval
    from .experiment.stock import StockQuantity
    from .material_spec import MaterialSpecification, PhaseClaim
    from .stream_disposition import StreamDisposition

__all__ = [
    "EvidenceFieldStatus",
    "EvidenceField",
    "OperationKind",
    "OperationRole",
    "ProcedureMaterialRole",
    "ProcedureMaterialUse",
    "ProcedureOperation",
    "ProcedureEvidence",
    "WHOLE_PROCEDURE_FIELDS",
]

#: The whole-procedure evidence fields the completeness predicate inspects (readiness.py reads the same tuple).
WHOLE_PROCEDURE_FIELDS: tuple[str, ...] = (
    "scale", "quench", "workup_isolation", "separation", "wash", "drying",
    "purification", "analytical_verification",
)


class EvidenceFieldStatus(str, Enum):
    """Whether ONE structured claim about the sourced procedure is represented -- a raw-evidence-presence
    axis, distinct from :class:`~smartchem.experiment.readiness.ObligationStatus` (obligation discharge) and
    :class:`~smartchem.contracts.EvidenceStatus` (strength). Its own enum on purpose."""

    #: A structured value IS represented, tied to a source locator.
    PRESENT = "PRESENT"
    #: The source AFFIRMATIVELY closes this out (a complete procedure in which this operation genuinely does not
    #: occur) -- carries a locator AND a non-empty justification, and NO value (D24.2: a field that states a value
    #: is PRESENT). NEVER derived from chemistry/phase, NEVER a synonym for silence.
    EXPLICIT_NOT_APPLICABLE = "EXPLICIT_NOT_APPLICABLE"
    #: The source is silent; no claim either way. Blocks completeness (mere silence is not N/A).
    UNKNOWN_MISSING = "UNKNOWN_MISSING"


@dataclass(frozen=True)
class EvidenceField(Digestible):
    """One tri-state structured claim: its status, an optional normalized value, the source locator it traces
    to, and (for EXPLICIT_NOT_APPLICABLE only) the justification that closes it out.

    ``value`` is a normalized ``str`` (an amount, a ratio, a quoted phrase) or an
    :class:`~smartchem.conditions.Interval` (T in 'K', duration in 'min') or ``None``. Only PRESENT carries a
    value; UNKNOWN_MISSING and EXPLICIT_NOT_APPLICABLE never do (D24.2).
    """

    status: EvidenceFieldStatus
    value: "str | Interval | None" = None
    locator: "str | None" = None
    justification: str = ""

    def __post_init__(self) -> None:
        from .conditions import Interval  # lazy: conditions imports THIS module at import time

        if not isinstance(self.status, EvidenceFieldStatus):
            raise TypeError("status must be an EvidenceFieldStatus")
        if self.value is not None and not isinstance(self.value, (str, Interval)):
            raise TypeError("value must be a str, an Interval, or None")
        if isinstance(self.value, str) and not self.value.strip():
            raise ValueError("a represented value must be a non-empty string")
        if self.locator is not None and (not isinstance(self.locator, str) or not self.locator.strip()):
            raise TypeError("locator must be a non-empty string or None")
        if not isinstance(self.justification, str):
            raise TypeError("justification must be a string")
        object.__setattr__(self, "justification", self.justification.strip())
        if self.locator is not None:
            object.__setattr__(self, "locator", self.locator.strip())

        if self.status is EvidenceFieldStatus.UNKNOWN_MISSING:
            # Silence carries nothing: no value, no locator, no justification.
            if self.value is not None or self.locator is not None or self.justification:
                raise ValueError("UNKNOWN_MISSING carries no value, locator, or justification")
        else:
            # PRESENT / EXPLICIT_NOT_APPLICABLE are CLAIMS: each must trace to a source locator.
            if self.locator is None:
                raise ValueError(f"{self.status.value} must carry a source locator")
        if self.status is EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE and not self.justification:
            raise ValueError(
                "EXPLICIT_NOT_APPLICABLE must carry a non-empty justification (the source text that closes it "
                "out) -- silence is UNKNOWN_MISSING, never N/A"
            )
        if self.status is EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE and self.value is not None:
            # Round V X-high D24.2 (Wave-C' A4): a closing-out claim cannot also STATE a value. Every capability
            # reader gates on ``is_present``, so an N/A field carrying ``Interval(650, 650, "K")`` was a demand that
            # reached no axis while readiness counted it resolved. The value belongs in a PRESENT field.
            raise ValueError(
                "EXPLICIT_NOT_APPLICABLE carries no value -- a field that states a value is PRESENT, not N/A (D24.2)"
            )
        if self.status is EvidenceFieldStatus.PRESENT and self.value is None:
            raise ValueError("PRESENT must carry a value")

    @property
    def is_present(self) -> bool:
        return self.status is EvidenceFieldStatus.PRESENT

    @property
    def is_unknown(self) -> bool:
        return self.status is EvidenceFieldStatus.UNKNOWN_MISSING

    @classmethod
    def present(cls, value: "str | Interval", locator: str) -> "EvidenceField":
        return cls(EvidenceFieldStatus.PRESENT, value, locator)

    @classmethod
    def not_applicable(cls, locator: str, justification: str) -> "EvidenceField":
        return cls(EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE, None, locator, justification)

    @classmethod
    def unknown(cls) -> "EvidenceField":
        return cls(EvidenceFieldStatus.UNKNOWN_MISSING)


class OperationKind(str, Enum):
    """The minimum set of physically-irreducible bench actions forced by the sourced corpus (Wave A Lane A).
    Composite/named techniques are NOT primitives: a quench is ``ADD`` with ``role=QUENCH``, a wash is ``ADD``
    with ``role=WASH``, a recrystallization is ``HEAT``/``COOL``/``FILTER`` tagged ``role=RECRYSTALLIZATION``."""

    ADD = "ADD"          # charge a material (reagent/catalyst/quench/wash liquid -- see role)
    MIX = "MIX"          # an agitation instruction not co-located with a stated ADD/HEAT/HOLD
    HEAT = "HEAT"
    COOL = "COOL"
    HOLD = "HOLD"        # maintain conditions for a stated duration (reflux, "heat ... for at least 10 min")
    SEPARATE = "SEPARATE"  # liquid-liquid partition
    FILTER = "FILTER"      # solid-liquid separation
    DRY = "DRY"            # desiccant or air-dry
    DISTILL = "DISTILL"    # collect a fraction by volatility/boiling range
    VERIFY = "VERIFY"      # analytical/product confirmation (weigh, m.p., yield, spectroscopy)


class OperationRole(str, Enum):
    """A CLOSED discriminator distinguishing same-kind operations by purpose, so the completeness/coherence
    logic never parses prose to tell a reaction charge from a wash charge."""

    REACTION = "REACTION"
    QUENCH = "QUENCH"
    WASH = "WASH"
    RECRYSTALLIZATION = "RECRYSTALLIZATION"
    OTHER = "OTHER"


class ProcedureMaterialRole(str, Enum):
    """The purpose a procedure-only auxiliary serves -- a MATERIAL-level role, deliberately DISTINCT from
    :class:`OperationRole` (which classifies an *operation*, not a species). The dissection that forced it: op1 of
    both isopentyl and aspirin glues a catalyst (H2SO4) into a ``role=REACTION`` charge alongside the true reactants,
    and nothing typed told the H2SO4 from the substrate. This enum is where that distinction finally has a home.

    Closed vocabulary; extend only when the sourced corpus produces an auxiliary none of these fit -- never
    speculatively. A material's role is what the source SAYS it does, not what a runtime parser guesses.

    Round IV F45: REACTANT/SUBSTRATE were added so the SOURCE can carry the reaction inputs themselves as
    typed uses (not just the workup auxiliaries), letting the generic capability compiler read a route's
    reactant material specification off ``material_uses`` instead of hard-coding leaf identities + a runtime
    'glacial' prose scan. SUBSTRATE is the principal species being transformed; REACTANT is a co-reactant
    charged stoichiometrically into the product (the two are distinguished only where the source does)."""

    SUBSTRATE = "SUBSTRATE"      # the principal input being transformed (the alcohol in a Fischer esterification)
    REACTANT = "REACTANT"        # a co-reactant charged stoichiometrically into the product (the acid)
    CATALYST = "CATALYST"        # accelerates without being consumed stoichiometrically (H2SO4 in a Fischer esterification)
    WASH = "WASH"                # a medium (usually a liquid) contacted with the product to carry impurities away
                                 # (5% NaHCO3, brine, a decolorizing adsorbent) -- the closest home the corpus's
                                 # charcoal has in this frozen vocab; a dedicated adsorbent role is a later extension
    DRY = "DRY"                  # a desiccant that pulls residual water (anhydrous MgSO4)
    SOLVENT = "SOLVENT"          # a recrystallization/reaction medium (hot ethyl acetate)
    RINSE = "RINSE"              # a low-volume flush of a collected solid/vessel (cold water, petroleum ether)
    NEUTRALIZE = "NEUTRALIZE"    # an acid/base charged to move pH, not to react into the product (HCl to dissolve p-aminophenol)


@dataclass(frozen=True)
class ProcedureMaterialUse(Digestible):
    """One procedure-only auxiliary the source names -- a catalyst, wash, drier, solvent, rinse, or pH agent that
    the balanced reaction equation never sees but the bench chemist must still possess. AUTHORED source evidence,
    never runtime-parsed prose: each field is transcribed by hand from the cited procedure.

    ``identity`` is HONESTLY OPTIONAL and it is load-bearing. NaHCO3 / NaCl / MgSO4 are ionic lattices; the SMILES
    parser refuses a disconnected species, so ~half this corpus cannot resolve to a single connected
    :class:`~smartchem.category.Molecule`. Inventing a covalent spelling for an ionic salt to force a resolution is
    banned -- ``identity=None`` is the truthful carrier, mirroring the ``required_assay: float | None`` honesty
    pattern the stock layer already uses. ``quantity`` is populated only where the source gives a cleanly-separable
    per-material amount (``None`` where the page glues quantities together -- a fabricated split would be worse than
    the honest gap).

    Round V (barrier D3) semantics of the three material-description fields -- one representation, one meaning each:

    * ``formulation`` -- RAW provenance/display text: the adjective words the cited source puts around the species
      name ("glacial", "conc.", "saturated aqueous", ...). NOTHING downstream interprets it; no compiler, stock layer
      or axis may learn what an adjective means from this string.
    * ``specification`` -- the LOAD-BEARING, source-authored :class:`~smartchem.material_spec.MaterialSpecification`:
      what the source says the material must BE (composition on a stated basis, positively-required states,
      and ``unresolved_terms`` for load-bearing words the author could not honestly type). A use whose
      ``formulation`` is non-empty but whose ``specification`` is ``None`` is projected as UNRESOLVED (F69 ->
      UNKNOWN), never as "no constraint". A use with neither is a plain identity/phase/quantity demand.
    * ``phase`` -- stays HERE, on the use, and ONLY here; it is never duplicated into the specification (a NEAT
      claim is a dilution state, not a phase: a LIQUID can be a dilute solution).

    Round V X-high (barrier D18): ``phase`` is an evidence-graded :class:`~smartchem.material_spec.PhaseClaim`, not
    a bare ``Phase`` scalar. Same ONE phase vocabulary, now carrying WHO says so: a phase the cited page states is
    ``SOURCE_QUOTED``; a phase the evidence author reads off a volume, a drop count or a species' usual state is
    ``AUTHOR_INFERRED`` -- and by F71 an author's inference can neither discharge nor refute a stock's phase. A bare
    ``Phase`` is REFUSED (a stale caller fails loudly instead of silently shipping an ungraded claim)."""

    name: str
    role: ProcedureMaterialRole
    identity: "Molecule | None" = None
    formulation: "str | None" = None
    phase: "PhaseClaim | None" = None
    quantity: "StockQuantity | None" = None
    evidence_source: str = ""
    #: Round V (barrier D3): the SOURCE-AUTHORED typed material specification. ``formulation`` above is now raw
    #: provenance/display text ONLY -- nothing downstream interprets it. ``None`` with a non-empty ``formulation``
    #: means the author could not type the load-bearing words, which the capability compiler projects as an
    #: UNRESOLVED formulation term (UNKNOWN, F69) -- never as "no constraint".
    specification: "MaterialSpecification | None" = None

    def __post_init__(self) -> None:
        # Lazy imports mirror EvidenceField's Interval dance: keep the structural type checks honest without
        # welding a module-load-order dependency onto category/experiment.stock.
        from .category import Molecule
        from .experiment.stock import StockQuantity
        from .material_spec import MaterialSpecification, PhaseClaim

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string (the exact sourced material name)")
        object.__setattr__(self, "name", self.name.strip())
        if not isinstance(self.role, ProcedureMaterialRole):
            raise TypeError("role must be a ProcedureMaterialRole")
        if self.identity is not None and type(self.identity) is not Molecule:
            raise TypeError("identity must be a Molecule or None (None for ionic/mixture/unresolvable species)")
        if self.formulation is not None and (not isinstance(self.formulation, str) or not self.formulation.strip()):
            raise ValueError("formulation must be a non-empty string or None")
        if self.formulation is not None:
            object.__setattr__(self, "formulation", self.formulation.strip())
        if self.phase is not None and type(self.phase) is not PhaseClaim:
            raise TypeError(
                "phase must be a smartchem.material_spec.PhaseClaim or None (D18: a phase carries its evidence "
                "strength -- a bare Phase is an ungraded claim and is refused)")
        if self.quantity is not None and type(self.quantity) is not StockQuantity:
            raise TypeError("quantity must be a StockQuantity or None")
        if not isinstance(self.evidence_source, str) or not self.evidence_source.strip():
            raise ValueError("evidence_source must be a non-empty source locator")
        object.__setattr__(self, "evidence_source", self.evidence_source.strip())
        if self.specification is not None and type(self.specification) is not MaterialSpecification:
            raise TypeError("specification must be a smartchem.material_spec.MaterialSpecification or None")


_AGITATION_KINDS = frozenset({OperationKind.ADD, OperationKind.MIX, OperationKind.HEAT,
                              OperationKind.HOLD, OperationKind.COOL})
_THERMAL_KINDS = frozenset({OperationKind.HEAT, OperationKind.COOL, OperationKind.HOLD})


@dataclass(frozen=True)
class ProcedureOperation(Digestible):
    """One ordered operation the source procedure specifies."""

    ordinal: int
    kind: OperationKind
    role: OperationRole = OperationRole.REACTION
    materials: tuple[str, ...] = ()
    quantity: "EvidenceField | None" = None
    rate: "EvidenceField | None" = None
    agitation: "EvidenceField | None" = None
    temperature: "EvidenceField | None" = None
    pressure: "EvidenceField | None" = None
    duration: "EvidenceField | None" = None
    endpoint: "EvidenceField | None" = None
    apparatus: tuple[str, ...] = ()
    material_uses: "tuple[ProcedureMaterialUse, ...]" = ()
    locator: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or type(self.ordinal) is not int or self.ordinal < 1:
            raise ValueError("ordinal must be a positive int (1-based)")
        if not isinstance(self.kind, OperationKind):
            raise TypeError("kind must be an OperationKind")
        if not isinstance(self.role, OperationRole):
            raise TypeError("role must be an OperationRole")
        for name in ("materials", "apparatus"):
            value = getattr(self, name)
            if type(value) is not tuple or any(not isinstance(m, str) or not m.strip() for m in value):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
            object.__setattr__(self, name, tuple(m.strip() for m in value))
        for name in ("quantity", "rate", "agitation", "temperature", "pressure", "duration", "endpoint"):
            value = getattr(self, name)
            if value is not None and type(value) is not EvidenceField:
                raise TypeError(f"{name} must be an EvidenceField or None")
        # The procedure-only auxiliaries this op charges (catalyst/wash/drier/...); empty by default so every
        # pre-Round-III construction still builds untouched. It is SOURCE evidence, never a capability claim.
        if type(self.material_uses) is not tuple or any(
            type(u) is not ProcedureMaterialUse for u in self.material_uses
        ):
            raise TypeError("material_uses must be a tuple of ProcedureMaterialUse")
        if not isinstance(self.locator, str) or not self.locator.strip():
            raise ValueError("a procedure operation must carry a non-empty source locator")
        object.__setattr__(self, "locator", self.locator.strip())


def _field_matches(evidence: "ProcedureEvidence", name: str, op: ProcedureOperation) -> bool:
    """Whether ``op`` is an operation that would realize whole-procedure field ``name``. Used only for the
    coherence guard (a PRESENT field needs a realizing op; an EXPLICIT_NOT_APPLICABLE field must have none),
    never for capability -- this is pure structural bookkeeping over kinds/roles."""
    if name == "quench":
        return op.role is OperationRole.QUENCH
    if name == "separation":
        return op.kind is OperationKind.SEPARATE
    if name == "wash":
        return op.role is OperationRole.WASH
    if name == "drying":
        return op.kind is OperationKind.DRY
    if name == "purification":
        return op.role is OperationRole.RECRYSTALLIZATION or op.kind is OperationKind.DISTILL
    if name == "analytical_verification":
        return op.kind is OperationKind.VERIFY
    if name == "workup_isolation":
        return op.kind in (OperationKind.SEPARATE, OperationKind.FILTER, OperationKind.DRY) \
            or op.role is OperationRole.WASH
    return False  # "scale" is a batch-level fact with no per-operation correspondent


@dataclass(frozen=True)
class ProcedureEvidence(Digestible):
    """The structured, source-scoped record of what a literature procedure specified for one reaction.

    Well-formedness is enforced here. Completeness is ``readiness.procedure_representation_is_complete``;
    sourcing is ``is_sourced`` (checked as a separate mandatory conjunct in the readiness evaluator).
    """

    reaction_scope: str
    source: "SourceCitation | None"
    scale: EvidenceField
    operations: "tuple[ProcedureOperation, ...]"
    quench: EvidenceField
    workup_isolation: EvidenceField
    separation: EvidenceField
    wash: EvidenceField
    drying: EvidenceField
    purification: EvidenceField
    analytical_verification: EvidenceField
    evidence_scope: str = ""
    unresolved_omissions: tuple[str, ...] = ()
    #: 0.9.5 S10: what the source says happens to individual streams (:mod:`smartchem.stream_disposition`). APPENDED
    #: LAST so positional callers keep working; digest-covered (compare=True) so a disposition moves every identity
    #: above it; canonically sorted by subject. Empty is the honest default -- absence is UNKNOWN, never "handled".
    stream_dispositions: "tuple[StreamDisposition, ...]" = ()

    def __post_init__(self) -> None:
        if not isinstance(self.reaction_scope, str) or not self.reaction_scope.strip():
            raise ValueError("reaction_scope must be a non-empty string")
        object.__setattr__(self, "reaction_scope", self.reaction_scope.strip())
        if self.source is not None and type(self.source) is not SourceCitation:
            raise TypeError("source must be a SourceCitation or None")
        for name in WHOLE_PROCEDURE_FIELDS:
            if type(getattr(self, name)) is not EvidenceField:
                raise TypeError(f"{name} must be an EvidenceField")
        if not isinstance(self.evidence_scope, str):
            raise TypeError("evidence_scope must be a string")
        object.__setattr__(self, "evidence_scope", self.evidence_scope.strip())

        if type(self.operations) is not tuple or not self.operations or any(
            type(op) is not ProcedureOperation for op in self.operations
        ):
            raise TypeError("operations must be a non-empty tuple of ProcedureOperation")
        ordinals = [op.ordinal for op in self.operations]
        if ordinals != list(range(1, len(ordinals) + 1)):
            raise ValueError("operation ordinals must be contiguous 1..N in order (no gaps, no repeats)")
        if not any(op.kind is OperationKind.ADD and op.role is OperationRole.REACTION
                   for op in self.operations):
            raise ValueError("a procedure must have at least one ADD operation with role=REACTION")

        # Coherence: a PRESENT whole-procedure field needs at least one realizing operation; an
        # EXPLICIT_NOT_APPLICABLE field must have zero (you cannot claim "no wash" while a WASH op exists, nor
        # claim "washed" as PRESENT with no WASH op). This is what makes marking a field N/A to skip a real,
        # present operation impossible (plan M15). "scale" has no operation correspondent and is exempt.
        for name in WHOLE_PROCEDURE_FIELDS:
            if name == "scale":
                continue
            fld: EvidenceField = getattr(self, name)
            matches = sum(1 for op in self.operations if _field_matches(self, name, op))
            if fld.status is EvidenceFieldStatus.PRESENT and matches == 0:
                raise ValueError(f"{name} is PRESENT but no operation realizes it")
            if fld.status is EvidenceFieldStatus.EXPLICIT_NOT_APPLICABLE and matches != 0:
                raise ValueError(f"{name} is EXPLICIT_NOT_APPLICABLE but {matches} operation(s) realize it")

        if type(self.unresolved_omissions) is not tuple or any(
            not isinstance(o, str) or not o.strip() for o in self.unresolved_omissions
        ):
            raise TypeError("unresolved_omissions must be a tuple of non-empty strings")
        object.__setattr__(self, "unresolved_omissions",
                           tuple(sorted({o.strip() for o in self.unresolved_omissions})))

        # 0.9.5 S10: the dispositions' procedure-internal structure. Their binding to a REAL step (signature, subject
        # existence, net consumption) is ExperimentStep's; the accepted-source gate is derive_waste's. A procedure
        # without dispositions never loads the module -- the healthy majority of patients skip this ward entirely.
        if type(self.stream_dispositions) is not tuple:
            raise TypeError("stream_dispositions must be a tuple of StreamDisposition")
        if self.stream_dispositions:
            from .stream_disposition import RECOVERY_OP_KINDS, StreamDisposition  # lazy: it imports THIS module

            if any(type(d) is not StreamDisposition for d in self.stream_dispositions):
                raise TypeError("stream_dispositions must be a tuple of smartchem.stream_disposition.StreamDisposition")
            subjects = [d.subject for d in self.stream_dispositions]
            if len(set(subjects)) != len(subjects):
                raise ValueError("two stream dispositions name the same subject -- one statement per stream, never a "
                                 "first-or-last-wins merge")
            kind_of = {op.ordinal: op.kind for op in self.operations}
            for d in self.stream_dispositions:
                if d.via_op is not None and kind_of.get(d.via_op) not in RECOVERY_OP_KINDS:
                    raise ValueError(
                        f"RECOVERED via_op={d.via_op} must name a DISTILL/FILTER/SEPARATE operation of THIS procedure "
                        f"(found {getattr(kind_of.get(d.via_op), 'value', 'no such op')})")
            object.__setattr__(self, "stream_dispositions",
                               tuple(sorted(self.stream_dispositions, key=lambda d: d.subject.sort_key)))

    @property
    def is_sourced(self) -> bool:
        """True only when an accepted :class:`SourceCitation` backs this evidence. Necessary (not sufficient)
        for a ``PROCESS_SPECIFIED`` readiness claim -- mirrors ``ConditionEnvelope.is_sourced`` /
        ``ProcessRequirements.is_sourced``. Completeness is a separate predicate."""
        return self.source is not None and self.source.accepted

    @property
    def source_locator(self) -> "str | None":
        """The accepted source's locator, or None when unsourced -- the provenance a SATISFIED process/workup
        readiness axis reports (NEVER the enclosing envelope's conditions citation; plan D4 / Lane F KILL 1)."""
        return self.source.locator if self.is_sourced else None
