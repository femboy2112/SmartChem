"""smartchem/capability/waste.py -- the waste-stream projection (Round V, barrier D9).

**Listen, Morty, a waste category is a CLAIM ABOUT A STREAM, not a vibe about a molecule.** Round IV derived
``AQUEOUS_NEUTRAL`` from "this byproduct's GHS record is empty" -- and an empty GHS record says nothing about the
STREAM it ends up in: its phase (the isopentyl water byproduct is ``Fate.UNKNOWN`` and was still called
"condensed"), its pH, or what else is dissolved in it (excess acetic acid, the H2SO4 catalyst, bicarbonate).
That was F76. F77: the catalyst, the excess reagent and the unreacted substrate never entered the waste question
at all, and spent streams existed only when an OPTIONAL typed use named them -- so a schema-legal source that
kept its auxiliaries in ``materials=`` strings reached overall ``CAPABILITY_FIT`` (Lane E's latent P0).

:func:`derive_waste` is the pure replacement for ``requirements._waste_requirement``:

* **byproducts** (``verify_handling``): unassessed -> unresolved; off-gas -> ``OFFGAS_CAPTURE`` (+``HAZARDOUS``
  on real GHS); real GHS at any fate -> ``HAZARDOUS`` (+unresolved when the fate is ``UNKNOWN``); EMPTY GHS at any
  fate -> unresolved ("benign species, untyped waste stream"). ``AQUEOUS_NEUTRAL`` would need a typed aqueous
  stream with a sourced neutral endpoint and every component assessed benign -- no such evidence type exists in
  the corpus, so it is never derived here (honest, not a gap in the code).
* **residuals**: every CATALYST use / envelope catalyst is a certain residual (``HAZARDOUS`` if its resolved hazard
  carries real GHS, else unresolved); every SUBSTRATE/REACTANT use and every step reactant/reagent no SUBSTRATE/REACTANT use
  covers is an unresolved residual (no stoichiometry guessing -- "consumed completely" is never assumed).
* **spent streams** come from OPERATIONS (role WASH/RECRYSTALLIZATION or kind SEPARATE/FILTER/DRY/DISTILL): one
  unresolved obligation per op, named from its typed uses, else its ``materials`` strings, else its ordinal/kind.
  Typed uses refine the name; their absence never deletes the stream. Spent-stream-role uses
  (WASH/RINSE/DRY/SOLVENT/NEUTRALIZE) anywhere still add their own stream too.

Round V X-high amendments (barrier D17):

* **Nothing introduced may vanish (F-6).** Every ``op.materials`` string that no typed use OF THAT OP covers
  (whitespace-folded, case-preserving EQUALITY since S18 -- the same exact rule the requirement projection uses) is an unresolved
  obligation of its own, on EVERY op kind (ADD/QUENCH/MIX/HEAT/HOLD/COOL as much as the spent-stream ops): an
  untyped material's fate -- consumed, recovered, routed -- is untyped, so its disposal routing is UNKNOWN. The
  typed-use path is TOTAL over :class:`~smartchem.procedure_evidence.ProcedureMaterialRole` (an import-time guard
  refuses a role that would silently map to no obligation).
* **A CATALYST label must agree with the chemistry (F-7).** A known-identity CATALYST use that its own step's
  balanced reaction NET-CONSUMES is a role contradiction: it earns NO resolved catalyst category (a relabelled
  reactant must never launder its unresolved residual into a resolved ``HAZARDOUS``), only an unresolved residual
  naming the contradiction -- and a same-named envelope catalyst cannot smuggle the category back in.
* **``envelope.medium`` is provenance ONLY (Part IV).** Every corpus medium is a condition DESCRIPTION ("neat;
  acid-catalyzed (conc. H2SO4); reflux then fractional distillation"), never one species; reading the sentence as
  a spent stream minted a fake waste obligation for the wrong reason. Materials are typed uses; the medium reader
  is deleted.

0.9.5 S10 (freeze §6) -- the CONSUMPTION of :mod:`smartchem.stream_disposition`:

* **Law L1 (exact key, one for one, monotone).** An obligation that has a structural subject (BYPRODUCT, RESIDUAL,
  OP_STREAM, USE_STREAM) looks its disposition up by EXACT :class:`~smartchem.stream_disposition.StreamSubject`
  equality inside its own step's procedure. A matching disposition moves exactly ONE obligation from ``unresolved``
  to ``reasons`` (a disposition that already discharged one discharges no second); ``ROUTED`` ADDS its category. A
  disposition never deletes a derived category -- derived and routed categories are kept apart and UNIONED.
* **It discharges only when** the procedure source is ACCEPTED (``is_sourced`` -- the vocabulary deliberately does
  not refuse an unaccepted source at construction, so this gate is real), the evidence is SOURCE_QUOTED, the value is
  one THIS obligation admits (a byproduct / op stream: ROUTED only; a use stream / catalyst residual: ROUTED or
  RECOVERED; a SUBSTRATE/REACTANT residual: CONSUMED_COMPLETELY too, iff the step net-consumes that identity),
  RECOVERED names a DISTILL/FILTER/SEPARATE ``via_op`` of the same procedure, a species-level ROUTED has a known
  hazard record (L3), and ROUTED does not contradict a derived fate (OFFGAS vs CONDENSED). A present disposition that
  fails any of these discharges nothing and says why in ``unresolved`` -- the obligation stays UNKNOWN, never BLOCKED.
  The construction-time refusals in the vocabulary are the loud layer; these derive-time checks are the second,
  independent one (a hand-forged record that skipped construction still discharges nothing it should not).
* **The latent defects discharge would otherwise make unsound are fixed here.** D-C1: a spent-stream-role use is ONE
  obligation PER USE (same-named uses no longer collapse into one discharge target). D-C2: residual and catalyst
  de-duplication is PER STEP (a step-1 residual no longer hides step 2's own obligation for the same species -- a
  strict superset of obligations on such routes, the safe direction). D-C4: an envelope catalyst that a same-step
  typed CATALYST use exact-fold-covers is attributed to THAT use's RESIDUAL subject (with no covering use it has no
  subject at all, like untyped op material and untyped step input -- excluded kinds that no disposition can reach).
  With no dispositions, the output is byte-identical to the pre-S10 projection on every route that repeats no species
  across steps.

0.9.5 S18 (Wave C1 evidence soundness -- a reachable false CAPABILITY_FIT, closed here):

* **C1-1: evidence is never discarded by a name.** An envelope catalyst a typed CATALYST use covers resolves its
  hazard from THAT use's identity (structure first), never from the envelope string; catalyst de-duplication keys on
  (species, exact name), never on a name fold -- a capitalised envelope string can no longer shadow the structure-
  resolved GHS record of the use it names. The hazard name lookup itself folds through the ONE material-name fold.
* **C1-2: ROUTED discharges, and still carries its species.** A ROUTED disposition on a subject whose species has a
  hazard record adds the categories that record implies (:func:`_hazard_categories`, the SAME mapping the byproduct
  and catalyst legs use) on top of its own category -- ``AQUEOUS_NEUTRAL`` alone cannot launder a GHS-hazardous
  residual. An OP_STREAM has no species identity: its SOURCE_QUOTED category is the only evidence (the boundary).
* **C1-3: case-folding never covers.** A typed use covers a raw string (F-6, D-C4) only under the case-PRESERVING
  fold (``stock.collapse_material_name``): ``"CO"`` never covers ``"Co"``.
* **C1-4: RECOVERED needs structural corroboration.** Its ``via_op`` must come AFTER every op that introduces the
  subject, the subject's phase must be CERTIFIED (every typed use behind it carries a phase claim on requirement-
  certifying evidence, and they agree), and that phase must be one the op kind can recover (``_RECOVERABLE_PHASES``).
* **C5-F4: only a consumed-role use covers an input.** A step reactant/reagent whose typed uses are all non-
  stoichiometric (a rinse, a catalyst) keeps its own residual obligation -- a disposition on the rinse stream never
  closes the leftover reactant.
* **C5-F6: a present identity is looked up by structure only.** No record for the structure is UNKNOWN (L3 fails
  closed); the name fallback is for identity-less (name-keyed) uses alone.
* **Monotone.** Adding a piece of evidence (a disposition, an envelope string, a typed use) never removes a derived
  category and never turns BLOCKED into FIT -- with one declared exception inherited from F-7: a typed CATALYST use
  its own step net-consumes opens an undischargeable role-contradiction line for every mention sharing its folded name,
  in place of their resolved category (UNKNOWN, never FIT).

0.9.5 A15 (Wave D):

* **F8: a covered string keeps its name's FORCING categories.** C1-1 reads a covered envelope string through its
  cover's identity; its own name record may still add the categories it forces (never clear, never discharge), so a
  typed use whose identity lacks the name's GHS can no longer delete what the string alone derived (monotone again).
* **L3 binds a USE_STREAM.** A ROUTED on the spent stream of a use whose species has no hazard record discharges
  nothing (it used to discharge with ``AQUEOUS_NEUTRAL`` alone); the species-less OP_STREAM stays the boundary.

Every reason quotes the real ``Fate``. Nothing here decides FIT/BLOCKED/UNKNOWN (that fold is assess's).
"""
from __future__ import annotations

from ..experiment.handling import Fate, verify_handling
from ..experiment.step import ExperimentRoute
from ..experiment.stock import Phase, structure_key
from ..experiment.stock import collapse_material_name as _exact_text
from ..experiment.stock import normalize_material_name as _norm_text
from ..material_spec import CERTIFYING_REQUIREMENT_EVIDENCE
from ..procedure_evidence import OperationKind, ProcedureMaterialRole
from ..stream_disposition import CATALYST_ROLES as _CATALYST_ROLES
from ..stream_disposition import CERTIFYING_DISPOSITION_EVIDENCE, RECOVERY_OP_KINDS, RESIDUAL_ROLES
from ..stream_disposition import CONSUMED_ROLES as _CONSUMED_ROLES
from ..stream_disposition import SPENT_STREAM_OP_KINDS as _SPENT_STREAM_OP_KINDS
from ..stream_disposition import SPENT_STREAM_OP_ROLES as _SPENT_STREAM_OP_ROLES
from ..stream_disposition import SPENT_STREAM_ROLES as _SPENT_STREAM_ROLES
from ..stream_disposition import (
    DispositionValue,
    StreamSubject,
    SubjectKind,
    op_core,
    reaction_signature,
    species_key,
    use_core,
)
from .enums import WasteCapability

__all__ = ["derive_waste"]


# The role tables this module keys its obligations on live in :mod:`smartchem.stream_disposition` -- ONE copy, bound
# here under their historical private names (the mutation gate patches ``waste._SPENT_STREAM_ROLES`` by name, and a
# patch of this module's binding still reaches derive_waste). Ownership sits with the leaf because the dependency only
# runs one way: ``experiment/step.py`` loads the leaf, and the leaf may never load the capability package.
#   _SPENT_STREAM_ROLES      workup material roles whose use is itself a spent process stream (Round IV F49)
#   _SPENT_STREAM_OP_ROLES   operation roles that GENERATE a spent stream whatever their typed uses say (D9)
#   _SPENT_STREAM_OP_KINDS   operation kinds that do the same (D9)
#   _CONSUMED_ROLES          consumed into the product -- the leftover is an unresolved residual
#   _CATALYST_ROLES          a certain (unconsumed) residual -- resolved HAZARDOUS on real GHS, else unresolved

#: S10 -- which disposition values may discharge which obligation (the derive-time half of freeze §6's L2; the
#: vocabulary's construction table is the loud half, this is the independent one).
_ROUTED_ONLY: "frozenset[DispositionValue]" = frozenset({DispositionValue.ROUTED})
_ROUTED_OR_RECOVERED: "frozenset[DispositionValue]" = frozenset({DispositionValue.ROUTED, DispositionValue.RECOVERED})
_ANY_VALUE: "frozenset[DispositionValue]" = frozenset(DispositionValue)
#: L3's reach: the subject kinds that name a species, so a ROUTED on them is checked against that species' hazard
#: record. 0.9.5 A15: USE_STREAM joined -- a ROUTED(AQUEOUS_NEUTRAL) on the spent stream of an unassessed species used
#: to discharge it with no record behind it.
_SPECIES_SUBJECT_KINDS: "frozenset[SubjectKind]" = frozenset(
    {SubjectKind.BYPRODUCT, SubjectKind.RESIDUAL, SubjectKind.USE_STREAM})


def _check_role_totality() -> None:
    """D17 (F-6) import-time guard: EVERY ProcedureMaterialRole maps to a waste obligation (catalyst residual,
    consumed-role residual, or spent stream). A future role added to the closed vocabulary without a waste reading
    would otherwise make its typed uses silently produce NOTHING -- the exact vanishing this module exists to
    refuse. Raises ``RuntimeError`` naming the orphan (or phantom) roles."""
    covered = _CATALYST_ROLES | _CONSUMED_ROLES | _SPENT_STREAM_ROLES
    universe = frozenset(ProcedureMaterialRole)
    if covered != universe:
        orphan = sorted(r.value for r in universe - covered)
        phantom = sorted(getattr(r, "value", repr(r)) for r in covered - universe)
        raise RuntimeError(
            f"waste role map is not total over ProcedureMaterialRole: roles with NO waste obligation {orphan}; "
            f"unknown roles {phantom} -- every typed use must reach the waste question (D17/F-6)")


_check_role_totality()


# Barrier S7/S8: the name fold (bound to the historical local name ``_norm_text``) and the structure key are imported
# from :mod:`smartchem.experiment.stock`, their one owner. This module used to keep private copies of both; a copy
# is a second opinion, and identity is not a matter of opinion.


def _name_covers(use_name: str, raw: str) -> bool:
    """The requirement projection's exact coverage rule (Wave-C K4), duplicated here on purpose (a private helper is
    never imported across modules): a typed use covers a raw string only on whitespace-folded, CASE-PRESERVING
    EQUALITY -- never a substring (a second species hidden in a longer phrase stays uncovered) and never a case-fold
    (S18 C1-3: ``"CO"`` covering ``"Co"`` made cobalt vanish from the waste question)."""
    name, text = _exact_text(use_name), _exact_text(raw)
    return bool(name) and name == text


def _resolve_hazard(identity, name: "str | None"):
    """The hazard record of one species: by STRUCTURE when the use carries an identity, by the SOURCED name (folded by
    ``hazards_for_named`` itself, S18) only when it carries none. 0.9.5 S18 / C5-F6: a present identity with no record
    is UNKNOWN -- it never falls back to the name, or a tert-butylbenzene use labelled "water" would borrow water's
    empty record and pass L3. Lazy imports (import cycle), resolved at call time so a monkeypatched resolver is
    honoured."""
    from ..data.hazards import hazards_for_named
    from ..decompiler_review import molecule_hazards

    if identity is not None:
        return molecule_hazards(identity)
    return hazards_for_named(name) if name is not None else None


def _ghs(hazard) -> "tuple[str, tuple[str, ...]] | None":
    """``(record name, GHS codes)`` of a resolved hazard record, or ``None`` when there is no record at all."""
    return None if hazard is None else (hazard.name, tuple(hazard.ghs_codes))


def _hazard_categories(codes: "tuple[str, ...]") -> "frozenset[WasteCapability]":
    """THE species-hazard -> waste-category mapping (S18 C1-2): real GHS codes make the stream ``HAZARDOUS``; an empty
    record implies no category (it clears the species, never the stream -- F76). ONE function: the byproduct leg, the
    catalyst leg and a ROUTED disposition's species all read it, so a routing can never disagree with the chemistry
    about what a species demands."""
    return frozenset({WasteCapability.HAZARDOUS}) if codes else frozenset()


#: S18 C1-4 -- the certified subject phases each recovery op kind can physically recover. A filter holds back a
#: SOLID; a still and a separatory funnel take off a LIQUID phase (an aqueous solution is a liquid, D24.7). A GAS is
#: recovered by none of them. Keyed on the closed ``RECOVERY_OP_KINDS``; an import-time guard keeps the two in step.
_RECOVERABLE_PHASES: "dict[OperationKind, frozenset[Phase]]" = {
    OperationKind.FILTER: frozenset({Phase.SOLID}),
    OperationKind.DISTILL: frozenset({Phase.LIQUID, Phase.AQUEOUS_SOLUTION}),
    OperationKind.SEPARATE: frozenset({Phase.LIQUID, Phase.AQUEOUS_SOLUTION}),
}
if frozenset(_RECOVERABLE_PHASES) != RECOVERY_OP_KINDS:
    raise RuntimeError("waste._RECOVERABLE_PHASES must cover exactly stream_disposition.RECOVERY_OP_KINDS (S18)")


def _recovery_refusal(procedure, subject: StreamSubject, via_op: int, via_kind: OperationKind) -> "str | None":
    """S18 C1-4: why a RECOVERED ``via_op`` does NOT corroborate recovering ``subject``, or ``None``.

    The typed uses behind the subject (a USE_STREAM: its one use; a RESIDUAL: every RESIDUAL-role use of that species
    in this procedure) fix two facts. ORDER: ``via_op`` must come after the LAST op that introduces the subject -- a
    recovery before (or at) the addition recovers nothing that was added. PHASE: every one of those uses must carry a
    CERTIFIED phase (a ``PhaseClaim`` on ``CERTIFYING_REQUIREMENT_EVIDENCE`` -- the requirement half of the D18
    certifying rule ``compare_phase`` applies) and they must agree; an uncertified or contradictory phase can be
    recovered by nothing. That phase must be one ``via_kind`` can recover (``_RECOVERABLE_PHASES``): a gravity filter
    does not recover a liquid. Structural corroboration only -- a source claim that passes is still a claim.

    A ``via_op`` naming no recovery op at all is not this helper's call: the kind law in ``_refusal`` owns that refusal
    (one law, one place -- so each can be tested, and mutated, on its own)."""
    if via_kind not in _RECOVERABLE_PHASES:
        return None
    if subject.kind is SubjectKind.USE_STREAM:
        op = next((o for o in procedure.operations if o.ordinal == subject.ordinal), None)
        uses = () if op is None or not 0 <= subject.index < len(op.material_uses) else (
            (op.ordinal, op.material_uses[subject.index]),)
    else:
        uses = tuple((op.ordinal, u) for op in procedure.operations for u in op.material_uses
                     if u.role in RESIDUAL_ROLES and species_key(u.identity, u.name) == subject.core)
    if not uses:
        return "no typed use of this procedure introduces the subject, so nothing corroborates a recovery (S18)"
    last = max(ordinal for ordinal, _use in uses)
    if via_op <= last:
        return (f"RECOVERED via op #{via_op} does not come after op #{last}, which introduces the subject -- a "
                "recovery cannot precede what it recovers (S18)")
    phases = {u.phase.phase for _ordinal, u in uses
              if u.phase is not None and u.phase.evidence in CERTIFYING_REQUIREMENT_EVIDENCE}
    if len(phases) != 1 or any(u.phase is None or u.phase.evidence not in CERTIFYING_REQUIREMENT_EVIDENCE
                               for _ordinal, u in uses):
        return ("the subject's phase is not CERTIFIED (every typed use behind it needs a phase claim on certifying "
                "evidence, and they must agree), so no operation can be shown to recover it (S18)")
    phase = next(iter(phases))
    if phase not in _RECOVERABLE_PHASES[via_kind]:
        return (f"a {via_kind.value} operation cannot recover a {phase.value} subject (it recovers "
                f"{', '.join(sorted(p.value for p in _RECOVERABLE_PHASES[via_kind]))}) (S18)")
    return None




def derive_waste(
    route: ExperimentRoute,
) -> "tuple[frozenset[WasteCapability], tuple[str, ...], tuple[str, ...]]":
    """``(categories, reasons, unresolved)`` for ``route`` under barrier D9 + S10 -- pure, route-only.

    ``reasons`` name the facts that EARNED a category (and every obligation a stream disposition discharged);
    ``unresolved`` names every stream whose routing could not be positively determined (assess caps the waste axis at
    UNKNOWN on any). Both are sorted, de-duplicated.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be a smartchem.experiment.step.ExperimentRoute")
    categories: "set[WasteCapability]" = set()     # DERIVED from the chemistry; no disposition ever removes one (L1)
    routed: "set[WasteCapability]" = set()         # ADDED by ROUTED dispositions; unioned in, never swapped in
    reasons: "set[str]" = set()
    unresolved: "set[str]" = set()

    # -- S10: the exact-subject disposition table, built ONLY for steps whose procedure carries dispositions (the
    # disposition-free majority never computes a signature, a subject or a core -- and never changes a byte) ----------
    signatures: "dict[int, str]" = {}
    by_subject: "dict[int, dict]" = {}
    for s_index, step in enumerate(route.steps, start=1):
        procedure = step.envelope.procedure
        if procedure is not None and procedure.stream_dispositions:
            signatures[s_index] = reaction_signature(step)
            by_subject[s_index] = {d.subject: d for d in procedure.stream_dispositions}
    spent: "set[tuple[int, StreamSubject]]" = set()    # L1: one disposition, one obligation

    def _subject(s_index: int, kind: SubjectKind, core_of, *args, ordinal=None, index=None) -> "StreamSubject | None":
        sig = signatures.get(s_index)
        return None if sig is None else StreamSubject(kind, sig, ordinal, index, core_of(*args))

    def _residual(s_index: int, use) -> "StreamSubject | None":
        return _subject(s_index, SubjectKind.RESIDUAL, species_key, use.identity, use.name)

    def _refusal(s_index, subject, disposition, allowed, fate, hazard_known) -> "str | None":
        """Why ``disposition`` may NOT discharge this obligation, or ``None``. Every check is fail-closed: a refusal
        keeps the obligation unresolved (UNKNOWN), it never converts a source claim into a BLOCKED."""
        if (s_index, subject) in spent:
            return "it has already discharged one obligation (L1: one disposition, one obligation)"
        procedure = route.steps[s_index - 1].envelope.procedure
        if not procedure.is_sourced:
            return "the procedure source is not an ACCEPTED citation, so nothing it states discharges an obligation"
        if disposition.evidence not in CERTIFYING_DISPOSITION_EVIDENCE:
            return f"{disposition.evidence.value} evidence cannot certify a disposition (SOURCE_QUOTED only)"
        if disposition.value not in allowed:
            return f"{disposition.value.value} cannot discharge this obligation (freeze §6 kind x value law)"
        if disposition.value is DispositionValue.RECOVERED:
            kinds = {op.ordinal: op.kind for op in procedure.operations}
            if kinds.get(disposition.via_op) not in RECOVERY_OP_KINDS:
                return (f"RECOVERED via_op={disposition.via_op!r} names no DISTILL/FILTER/SEPARATE operation of this "
                        "procedure")
            why = _recovery_refusal(procedure, subject, disposition.via_op, kinds.get(disposition.via_op))
            if why is not None:
                return why
        if disposition.value is DispositionValue.ROUTED:
            if type(disposition.category) is not WasteCapability:
                return "ROUTED carries no WasteCapability category"
            # A15: a USE_STREAM names a species too (its use's), so L3 binds it exactly as it binds a byproduct or a
            # residual; only the species-less OP_STREAM is exempt (S18 boundary).
            if subject.kind in _SPECIES_SUBJECT_KINDS and not hazard_known():
                return "the species has no hazard record, so a species-level routing cannot be checked (L3)"
            if fate is Fate.OFFGAS and disposition.category is not WasteCapability.OFFGAS_CAPTURE:
                return f"ROUTED({disposition.category.value}) contradicts the derived OFFGAS fate"
            if fate is Fate.CONDENSED and disposition.category is WasteCapability.OFFGAS_CAPTURE:
                return "ROUTED(OFFGAS_CAPTURE) contradicts the derived CONDENSED fate"
        return None

    def _credit(s_index, subject, disposition, label: str, effect: str, species_ghs=lambda: None) -> None:
        """The ONE place a disposition takes effect: mark it spent, ADD a routed category, name it in ``reasons``.
        S18 C1-2: a ROUTED stream still CARRIES its species -- ``species_ghs()`` (``(record, codes)`` or ``None``) adds
        the categories that species' hazard record implies, through the one mapping, on top of the routed one."""
        spent.add((s_index, subject))
        if disposition.value is DispositionValue.ROUTED:
            routed.add(disposition.category)
            found = species_ghs()
            implied = _hazard_categories(found[1]) if found is not None else frozenset()
            if implied:
                categories.update(implied)
                reasons.add(f"waste: {label} -- the routed stream carries {found[0]} (sourced GHS "
                            f"{', '.join(found[1])}), so ROUTED({disposition.category.value}) also requires "
                            f"{', '.join(sorted(c.value for c in implied))} -- a routing never launders a hazardous "
                            "species (S18)")
        what = disposition.value.value + (f"({disposition.category.value})" if disposition.category is not None
                                          else "") + (f" via op #{disposition.via_op}" if disposition.via_op else "")
        reasons.add(f"waste: {label} -- the sourced procedure states {what} [{disposition.evidence.value} @ "
                    f"{disposition.locator}]; {effect} (S10)")

    def _settle(s_index, subject, allowed, label: str, *, fate=None, hazard_known=lambda: True,
                species_ghs=lambda: None) -> bool:
        """True iff a disposition DISCHARGES this one obligation (the caller then skips its unresolved line). A
        present-but-refused disposition leaves the obligation open and records why."""
        if subject is None:
            return False
        disposition = by_subject[s_index].get(subject)
        if disposition is None:
            return False
        why = _refusal(s_index, subject, disposition, allowed, fate, hazard_known)
        if why is not None:
            unresolved.add(f"waste: {label} -- a stream disposition ({disposition.value.value}) is present but "
                           f"discharges nothing: {why}")
            return False
        _credit(s_index, subject, disposition, label, "this obligation is discharged", species_ghs)
        return True

    # -- byproducts ---------------------------------------------------------------------------------------------
    handling = verify_handling(route)
    ghs_by_name: "dict[str, tuple[str, ...]]" = {}
    for step_handling in handling.steps:
        for flag in step_handling.hazards:
            ghs_by_name.setdefault(flag.name, tuple(flag.ghs_codes))
    for s_index, step_handling in enumerate(handling.steps, start=1):
        for b in step_handling.byproducts:
            fate = b.fate.value if isinstance(b.fate, Fate) else str(b.fate)
            label = f"byproduct {b.molecule!r} (fate={fate})"
            subject = _subject(s_index, SubjectKind.BYPRODUCT, structure_key, b.molecule)
            if b.hazard_name is None:
                # L3 always refuses here (no hazard record); the call only records a present disposition's refusal.
                if not _settle(s_index, subject, _ROUTED_ONLY, label, fate=b.fate, hazard_known=lambda: False):
                    unresolved.add(f"waste: {label} has NO hazard assessment -- its disposal routing is UNKNOWN, never "
                                   "benign by negation (F48)")
                continue
            if b.hazard_name not in ghs_by_name:
                unresolved.add(f"waste: {label} names hazard record {b.hazard_name!r} but no GHS flag for it is "
                               "present in the handling ledger -- routing UNKNOWN")
                continue
            codes = ghs_by_name[b.hazard_name]
            def species(b=b, codes=codes):  # S18: a routed stream still carries this species' record
                return b.hazard_name, codes

            if b.fate is Fate.OFFGAS:
                categories.add(WasteCapability.OFFGAS_CAPTURE)
                reasons.add(f"waste: {label} evolves as an off-gas ({b.reason}) -- needs OFFGAS_CAPTURE")
            if codes:
                categories.update(_hazard_categories(codes))
                reasons.add(f"waste: {label} carries sourced GHS {', '.join(codes)} ({b.hazard_name}) -- HAZARDOUS")
                if b.fate is Fate.UNKNOWN:
                    if not _settle(s_index, subject, _ROUTED_ONLY, label, fate=b.fate, species_ghs=species):
                        unresolved.add(f"waste: {label} is hazardous ({b.hazard_name}) but its phase is UNASSESSED -- "
                                       "which stream carries it is UNKNOWN")
            else:
                # F76: an empty GHS profile clears the SPECIES, never the STREAM (phase/pH/co-residents unknown).
                if not _settle(s_index, subject, _ROUTED_ONLY, label, fate=b.fate, species_ghs=species):
                    unresolved.add(f"waste: {label} ({b.hazard_name}, empty GHS) -- benign species, untyped waste stream "
                                   "(phase/pH/co-residents unestablished); never AQUEOUS_NEUTRAL (F76)")

    # -- residuals (F77), role consistency (F-7), untyped introductions (F-6), spent streams (D9) ------------------
    # F-7 pre-pass: every name a known-identity CATALYST use carries while its own step NET-CONSUMES that structure.
    # Computed before any catalyst is read, so neither the use nor a same-named envelope catalyst (read first) can
    # ever earn the resolved catalyst category for a consumed reactant. (This one fold stays a fold on purpose: it
    # only ever opens an undischargeable UNKNOWN, so a lossy match here errs toward refusal, never toward FIT.)
    contradicted: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                if (use.role in _CATALYST_ROLES and use.identity is not None
                        and step.net_consumes(use.identity)):
                    contradicted.add(_norm_text(use.name))  # S8: the ONE name fold

    # ``catalyst_seen`` / ``residual_seen`` are (re)bound PER STEP in the loop below (D-C2); this closure reads the
    # current step's set at call time.
    def _catalyst(s_index: int, identity, name: str, where: str, subject: "StreamSubject | None",
                  covered: bool = False) -> None:
        key = _norm_text(name)  # S8: the ONE name fold
        if key in contradicted:
            unresolved.add(
                f"waste: catalyst {name!r} ({where}) is NET-CONSUMED by its step's balanced reaction -- a role "
                "contradiction, never a catalyst residual; its unreacted/excess residual's disposal routing is "
                "UNKNOWN (F-7)")
            return
        # S18 C1-1: de-duplicate by (species, EXACT name) -- never by a name fold. Two mentions merge only when they
        # carry the same structure-or-name key AND the same case-preserving spelling, i.e. exactly the same evidence
        # (same structure -> same structure-resolved record; same spelling -> same name fallback), so a skipped
        # mention can never take a GHS record with it. A fold-key merge let an identity-less envelope string shadow
        # the typed use whose structure carried H290/H314.
        seen = (species_key(identity, name), _exact_text(name))
        if seen in catalyst_seen:
            return
        catalyst_seen.add(seen)
        hazard = _resolve_hazard(identity, name)
        label = f"catalyst residual {name!r} ({where})"
        if covered and (hazard is None or not hazard.ghs_codes):
            # A15 (Wave D F8): a covered envelope string is read through its cover's identity (C1-1), but its OWN name
            # record may still FORCE -- one-sided, never a clearance and never a discharge. Without this, adding a
            # typed use ("sulfuric acid" whose identity is water) under an envelope "sulfuric acid" deleted the
            # HAZARDOUS the string alone derived: the monotonicity law broken by the cover-identity rule.
            named = _resolve_hazard(None, name)
            if named is not None and named.ghs_codes:
                categories.update(_hazard_categories(tuple(named.ghs_codes)))
                reasons.add(f"waste: {label} -- its own name carries sourced GHS {', '.join(named.ghs_codes)} "
                            f"({named.name}); a name may force a category its cover's identity lacks, never clear one "
                            "(A15)")
        if hazard is not None and hazard.ghs_codes:
            categories.update(_hazard_categories(tuple(hazard.ghs_codes)))
            reasons.add(f"waste: catalyst residual {name!r} ({where}) is not consumed and carries sourced GHS "
                        f"{', '.join(hazard.ghs_codes)} ({hazard.name}) -- HAZARDOUS")
            # No open obligation to discharge: a disposition here is ADDITIVE only (a ROUTED category joins the
            # derived HAZARDOUS, a RECOVERED is noted) -- the derived category stays whatever the source says (L1).
            disposition = None if subject is None else by_subject[s_index].get(subject)
            if disposition is not None and _refusal(s_index, subject, disposition, _ROUTED_OR_RECOVERED, None,
                                                    lambda: True) is None:
                _credit(s_index, subject, disposition, label, "additive only -- the derived HAZARDOUS stays (L1)",
                        lambda: _ghs(hazard))
        else:
            why = "no hazard record" if hazard is None else f"{hazard.name}, empty GHS -- benign species, untyped stream"
            if not _settle(s_index, subject, _ROUTED_OR_RECOVERED, label, hazard_known=lambda: hazard is not None,
                           species_ghs=lambda: _ghs(hazard)):
                unresolved.add(f"waste: catalyst residual {name!r} ({where}) is not consumed ({why}) -- its disposal "
                               "routing is UNKNOWN")

    for s_index, step in enumerate(route.steps, start=1):
        catalyst_seen, residual_seen = set(), set()  # D-C2: PER STEP -- step 1 never answers for step 2's species
        procedure = step.envelope.procedure
        typed_catalysts = () if procedure is None else tuple(
            u for op in procedure.operations for u in op.material_uses if u.role in _CATALYST_ROLES)
        for cat in step.envelope.catalysts:
            # D-C4: the envelope string names no stream of its own; its residual IS the covering typed CATALYST use's
            # (same exact rule as F-6 -- case-PRESERVING since S18). No covering use -> no subject (an excluded kind:
            # untyped, never reachable). S18 C1-1: a covered string is read through the cover's IDENTITY, so its
            # hazard resolves from structure exactly as the typed use's does -- the string adds a name, never removes
            # a record. (An uncovered string resolves by its own folded name; no record stays UNKNOWN.)
            cover = next((u for u in typed_catalysts if _name_covers(u.name, cat)), None)
            _catalyst(s_index, None if cover is None else cover.identity, cat, f"step {s_index} envelope catalyst",
                      None if cover is None else _residual(s_index, cover), covered=cover is not None)
        # Part IV: ``envelope.medium`` is condition PROSE / provenance only -- it is never read as a stream.
        covered: "set[str]" = set()   # species a consumed-role (SUBSTRATE/REACTANT) typed use answers for
        typed: "set[str]" = set()     # species ANY typed use names (for the reason text only)
        if procedure is not None:
            for op in procedure.operations:
                # F-6: an untyped material this op introduces has an untyped fate -- its own obligation, on every
                # op kind (a spent-stream op's line below names only its typed uses when it has any).
                for raw in op.materials:
                    if not any(_name_covers(u.name, raw) for u in op.material_uses):
                        unresolved.add(
                            f"waste: step {s_index} op #{op.ordinal} {op.kind.value}/{op.role.value} introduces "
                            f"untyped material {raw.strip()!r} -- its fate is untyped, so its disposal routing is "
                            "UNKNOWN (F-6)")
                for index, use in enumerate(op.material_uses):
                    if use.identity is not None:
                        # S18 / C5-F4: only a SUBSTRATE/REACTANT use answers for a step input's residual (it mints
                        # that residual's own obligation below). A rinse or catalyst use of the same species is a
                        # different stream, and a disposition on it must not close the leftover reactant too.
                        typed.add(structure_key(use.identity))
                        if use.role in _CONSUMED_ROLES:
                            covered.add(structure_key(use.identity))
                    if use.role in _CATALYST_ROLES:
                        _catalyst(s_index, use.identity, use.name, f"step {s_index} op #{op.ordinal} CATALYST use",
                                  _residual(s_index, use))
                        if use.identity is not None and step.net_consumes(use.identity):
                            residual_seen.add(structure_key(use.identity))
                    elif use.role in _CONSUMED_ROLES:
                        key = (structure_key(use.identity) if use.identity is not None
                               else f"name:{_exact_text(use.name)}")  # S18: exact spelling -- a fold never merges
                        if key not in residual_seen:
                            residual_seen.add(key)
                            subject = _residual(s_index, use)
                            # CONSUMED_COMPLETELY is admissible only for an identity the balanced step net-consumes.
                            allowed = (_ANY_VALUE if subject is not None and use.identity is not None
                                       and step.net_consumes(use.identity) else _ROUTED_OR_RECOVERED)
                            if not _settle(s_index, subject, allowed, f"step {s_index} residual {use.name!r}",
                                           hazard_known=lambda use=use: _resolve_hazard(use.identity, use.name)
                                           is not None,
                                           species_ghs=lambda use=use: _ghs(_resolve_hazard(use.identity, use.name))):
                                unresolved.add(
                                    f"waste: unreacted/excess {use.name!r} ({use.role.value}) residual -- full "
                                    "consumption or recovery is not typed, so its disposal routing is UNKNOWN (F77)")
                    if use.role in _SPENT_STREAM_ROLES:
                        # D-C1: ONE obligation PER USE (never de-duplicated by name): two same-named washes are two
                        # physical streams, and a disposition on one must leave the other open.
                        subject = _subject(s_index, SubjectKind.USE_STREAM, use_core, use, ordinal=op.ordinal,
                                           index=index)
                        if not _settle(s_index, subject, _ROUTED_OR_RECOVERED,
                                       f"step {s_index} op #{op.ordinal} use[{index}] spent workup stream "
                                       f"{use.name!r}",
                                       hazard_known=lambda use=use: _resolve_hazard(use.identity, use.name)
                                       is not None,
                                       species_ghs=lambda use=use: _ghs(_resolve_hazard(use.identity, use.name))):
                            unresolved.add(
                                f"waste: spent workup stream {use.name!r} ({use.role.value}) -- the sourced "
                                "procedure declares no disposal routing, so its waste handling is UNKNOWN (F49)")
                if op.role in _SPENT_STREAM_OP_ROLES or op.kind in _SPENT_STREAM_OP_KINDS:
                    if op.material_uses:
                        what = ", ".join(sorted({u.name for u in op.material_uses}))
                    elif op.materials:
                        what = ", ".join(sorted(set(op.materials)))
                    else:
                        what = "no named materials"
                    # S18 boundary: an OP_STREAM names no species, so its SOURCE_QUOTED routed category is the only
                    # evidence about it (its untyped materials stay F-6 obligations of their own).
                    subject = _subject(s_index, SubjectKind.OP_STREAM, op_core, op, ordinal=op.ordinal)
                    if not _settle(s_index, subject, _ROUTED_ONLY,
                                   f"step {s_index} op #{op.ordinal} {op.kind.value}/{op.role.value} spent stream"):
                        unresolved.add(
                            f"waste: step {s_index} op #{op.ordinal} {op.kind.value}/{op.role.value} leaves a spent "
                            f"stream ({what}) -- no disposal routing is sourced, so it is UNKNOWN (D9)")
        # every reactant/reagent no SUBSTRATE/REACTANT use covers is an unresolved residual (no procedure => all of them).
        for molecule in tuple(step.reactants) + tuple(step.reagents):
            key = structure_key(molecule)
            if key in covered or key in residual_seen:
                continue
            residual_seen.add(key)
            if key in typed:
                unresolved.add(
                    f"waste: step {s_index} input {molecule!r} is typed only in a non-stoichiometric role (its stream "
                    "is not this input's residual) -- any unreacted/excess residual's disposal routing is UNKNOWN "
                    "(F77; S18)")
                continue
            unresolved.add(
                f"waste: step {s_index} input {molecule!r} has no typed procedure use -- any unreacted/excess "
                "residual's disposal routing is UNKNOWN (F77; no stoichiometry guessed)")

    return frozenset(categories | routed), tuple(sorted(reasons)), tuple(sorted(unresolved))
