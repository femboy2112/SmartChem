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
  carries real GHS, else unresolved); every SUBSTRATE/REACTANT use and every step reactant/reagent no typed use
  covers is an unresolved residual (no stoichiometry guessing -- "consumed completely" is never assumed).
* **spent streams** come from OPERATIONS (role WASH/RECRYSTALLIZATION or kind SEPARATE/FILTER/DRY/DISTILL): one
  unresolved obligation per op, named from its typed uses, else its ``materials`` strings, else its ordinal/kind.
  Typed uses refine the name; their absence never deletes the stream. Spent-stream-role uses
  (WASH/RINSE/DRY/SOLVENT/NEUTRALIZE) anywhere still add their own stream too.

Round V X-high amendments (barrier D17):

* **Nothing introduced may vanish (F-6).** Every ``op.materials`` string that no typed use OF THAT OP covers
  (case/whitespace-folded EQUALITY -- the same exact rule the requirement projection uses) is an unresolved
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

Every reason quotes the real ``Fate``. Nothing here decides FIT/BLOCKED/UNKNOWN (that fold is assess's).
"""
from __future__ import annotations

from ..experiment.handling import Fate, verify_handling
from ..experiment.step import ExperimentRoute
from ..experiment.stock import normalize_material_name as _norm_text
from ..experiment.stock import structure_key
from ..procedure_evidence import OperationKind, OperationRole, ProcedureMaterialRole
from .enums import WasteCapability

__all__ = ["derive_waste"]


#: workup material roles whose use is itself a spent process stream (kept from Round IV F49).
_SPENT_STREAM_ROLES = frozenset({
    ProcedureMaterialRole.WASH, ProcedureMaterialRole.RINSE, ProcedureMaterialRole.DRY,
    ProcedureMaterialRole.SOLVENT, ProcedureMaterialRole.NEUTRALIZE,
})
#: operations that GENERATE a spent stream whatever their typed uses say (D9).
_SPENT_STREAM_OP_ROLES = frozenset({OperationRole.WASH, OperationRole.RECRYSTALLIZATION})
_SPENT_STREAM_OP_KINDS = frozenset({
    OperationKind.SEPARATE, OperationKind.FILTER, OperationKind.DRY, OperationKind.DISTILL,
})
#: roles that are consumed into the product -- their leftover is an unresolved residual.
_CONSUMED_ROLES = frozenset({ProcedureMaterialRole.SUBSTRATE, ProcedureMaterialRole.REACTANT})
#: the role whose use is a certain (unconsumed) residual -- resolved HAZARDOUS on real GHS, else unresolved.
_CATALYST_ROLES = frozenset({ProcedureMaterialRole.CATALYST})


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
    never imported across modules): a typed use covers a raw ``op.materials`` string only on case/whitespace-folded
    EQUALITY -- never a substring, so a second species hidden in a longer phrase stays uncovered."""
    name, text = _norm_text(use_name), _norm_text(raw)
    return bool(name) and name == text


def _resolve_hazard(identity, name: "str | None"):
    """Same lookup order as ``requirements._procedure_hazard_scan``: structure first, then the SOURCED name.
    Lazy imports (import cycle), resolved at call time so a monkeypatched resolver is honoured."""
    from ..data.hazards import hazards_for_named
    from ..decompiler_review import molecule_hazards

    hazard = molecule_hazards(identity) if identity is not None else None
    if hazard is None and name is not None:
        hazard = hazards_for_named(name)
    return hazard


def derive_waste(
    route: ExperimentRoute,
) -> "tuple[frozenset[WasteCapability], tuple[str, ...], tuple[str, ...]]":
    """``(categories, reasons, unresolved)`` for ``route`` under barrier D9 -- pure, route-only.

    ``reasons`` name the facts that EARNED a category; ``unresolved`` names every stream whose routing could not
    be positively determined (assess caps the waste axis at UNKNOWN on any). Both are sorted, de-duplicated.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be a smartchem.experiment.step.ExperimentRoute")
    categories: "set[WasteCapability]" = set()
    reasons: "set[str]" = set()
    unresolved: "set[str]" = set()

    # -- byproducts ---------------------------------------------------------------------------------------------
    handling = verify_handling(route)
    ghs_by_name: "dict[str, tuple[str, ...]]" = {}
    for step_handling in handling.steps:
        for flag in step_handling.hazards:
            ghs_by_name.setdefault(flag.name, tuple(flag.ghs_codes))
    for b in handling.all_byproducts:
        fate = b.fate.value if isinstance(b.fate, Fate) else str(b.fate)
        label = f"byproduct {b.molecule!r} (fate={fate})"
        if b.hazard_name is None:
            unresolved.add(f"waste: {label} has NO hazard assessment -- its disposal routing is UNKNOWN, never "
                           "benign by negation (F48)")
            continue
        if b.hazard_name not in ghs_by_name:
            unresolved.add(f"waste: {label} names hazard record {b.hazard_name!r} but no GHS flag for it is "
                           "present in the handling ledger -- routing UNKNOWN")
            continue
        codes = ghs_by_name[b.hazard_name]
        if b.fate is Fate.OFFGAS:
            categories.add(WasteCapability.OFFGAS_CAPTURE)
            reasons.add(f"waste: {label} evolves as an off-gas ({b.reason}) -- needs OFFGAS_CAPTURE")
        if codes:
            categories.add(WasteCapability.HAZARDOUS)
            reasons.add(f"waste: {label} carries sourced GHS {', '.join(codes)} ({b.hazard_name}) -- HAZARDOUS")
            if b.fate is Fate.UNKNOWN:
                unresolved.add(f"waste: {label} is hazardous ({b.hazard_name}) but its phase is UNASSESSED -- "
                               "which stream carries it is UNKNOWN")
        else:
            # F76: an empty GHS profile clears the SPECIES, never the STREAM (phase/pH/co-residents unknown).
            unresolved.add(f"waste: {label} ({b.hazard_name}, empty GHS) -- benign species, untyped waste stream "
                           "(phase/pH/co-residents unestablished); never AQUEOUS_NEUTRAL (F76)")

    # -- residuals (F77), role consistency (F-7), untyped introductions (F-6), spent streams (D9) ------------------
    catalyst_seen: "set[str]" = set()
    residual_seen: "set[str]" = set()
    stream_names_seen: "set[str]" = set()

    # F-7 pre-pass: every name a known-identity CATALYST use carries while its own step NET-CONSUMES that structure.
    # Computed before any catalyst is read, so neither the use nor a same-named envelope catalyst (read first, and
    # deduplicated by name) can ever earn the resolved catalyst category for a consumed reactant.
    contradicted: "set[str]" = set()
    for step in route.steps:
        procedure = step.envelope.procedure
        if procedure is None:
            continue
        for op in procedure.operations:
            for use in op.material_uses:
                if (use.role in _CATALYST_ROLES and use.identity is not None
                        and step.net_consumes(use.identity)):
                    contradicted.add(use.name.strip().casefold())

    def _catalyst(identity, name: str, where: str) -> None:
        key = name.strip().casefold()
        if key in contradicted:
            unresolved.add(
                f"waste: catalyst {name!r} ({where}) is NET-CONSUMED by its step's balanced reaction -- a role "
                "contradiction, never a catalyst residual; its unreacted/excess residual's disposal routing is "
                "UNKNOWN (F-7)")
            return
        if key in catalyst_seen:
            return
        catalyst_seen.add(key)
        hazard = _resolve_hazard(identity, name)
        if hazard is not None and hazard.ghs_codes:
            categories.add(WasteCapability.HAZARDOUS)
            reasons.add(f"waste: catalyst residual {name!r} ({where}) is not consumed and carries sourced GHS "
                        f"{', '.join(hazard.ghs_codes)} ({hazard.name}) -- HAZARDOUS")
        else:
            why = "no hazard record" if hazard is None else f"{hazard.name}, empty GHS -- benign species, untyped stream"
            unresolved.add(f"waste: catalyst residual {name!r} ({where}) is not consumed ({why}) -- its disposal "
                           "routing is UNKNOWN")

    for s_index, step in enumerate(route.steps, start=1):
        for cat in step.envelope.catalysts:
            _catalyst(None, cat, f"step {s_index} envelope catalyst")
        # Part IV: ``envelope.medium`` is condition PROSE / provenance only -- it is never read as a stream.
        procedure = step.envelope.procedure
        covered: "set[str]" = set()
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
                for use in op.material_uses:
                    if use.identity is not None:
                        covered.add(structure_key(use.identity))
                    if use.role in _CATALYST_ROLES:
                        _catalyst(use.identity, use.name, f"step {s_index} op #{op.ordinal} CATALYST use")
                        if use.identity is not None and step.net_consumes(use.identity):
                            residual_seen.add(structure_key(use.identity))
                    elif use.role in _CONSUMED_ROLES:
                        key = (structure_key(use.identity) if use.identity is not None
                               else f"name:{use.name.strip().casefold()}")
                        if key not in residual_seen:
                            residual_seen.add(key)
                            unresolved.add(
                                f"waste: unreacted/excess {use.name!r} ({use.role.value}) residual -- full "
                                "consumption or recovery is not typed, so its disposal routing is UNKNOWN (F77)")
                    if use.role in _SPENT_STREAM_ROLES:
                        nkey = use.name.strip().casefold()
                        if nkey not in stream_names_seen:
                            stream_names_seen.add(nkey)
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
                    unresolved.add(
                        f"waste: step {s_index} op #{op.ordinal} {op.kind.value}/{op.role.value} leaves a spent "
                        f"stream ({what}) -- no disposal routing is sourced, so it is UNKNOWN (D9)")
        # every reactant/reagent no typed use covers is an unresolved residual (no procedure => all of them).
        for molecule in tuple(step.reactants) + tuple(step.reagents):
            key = structure_key(molecule)
            if key in covered or key in residual_seen:
                continue
            residual_seen.add(key)
            unresolved.add(
                f"waste: step {s_index} input {molecule!r} has no typed procedure use -- any unreacted/excess "
                "residual's disposal routing is UNKNOWN (F77; no stoichiometry guessed)")

    return frozenset(categories), tuple(sorted(reasons)), tuple(sorted(unresolved))
