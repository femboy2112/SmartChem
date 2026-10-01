"""PLAN-01: the one human total-answer front door (v0.6 Human Chemical Front Door).

:func:`plan` resolves a human chemical identity ONCE through the single identity authority
(:func:`~smartchem.identity_parse.resolve_identity`), reports the strongest identity layer it
actually perceives, and routes to the EXISTING compiler primitive the identity layer makes eligible:

* a perceived CONSTITUTION (a registered NAME or a SMILES) -> structural ``recompile``;
* a FORMULA-layer identity (composition known, constitution NOT established) -> formula-level
  ``decompile``, plus the registry-known -- explicitly NOT exhaustive -- ambiguity set;
* an unresolvable/invalid input -> a typed invalid result naming the defect.

It is ORCHESTRATION ONLY.  It forks no search, duplicates no parser, and builds no second ranking
engine: every heavy step is :func:`~smartchem.service.build_recompile_request` /
:func:`~smartchem.service.build_decompile_request` + :func:`~smartchem.service.run_compilation`,
exactly as the expert ``recompile``/``decompile`` commands do.  It NEVER guesses a structure from a
bare formula -- the v0.6 identity law, ``formula -> structure`` is a relation, not a function.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .identity_parse import InputKind

__all__ = ["PlanStatus", "PlanResult", "plan", "plan_result_to_payload", "render_plan_human"]

PLAN_SCHEMA = "smartchem.plan/plan-result-v0.6"


class PlanStatus(str, Enum):
    """Why planning did or did not continue -- an explicit outcome, so the plan schema never OVERLOADS the
    ``(operation, response, exit_code)`` triple to imply its own reason (P1).

    Each member says exactly what the front door concluded, and no more than it knows:

    * ``STRUCTURAL_PLANNING`` -- a single constitution was perceived (NAME/SMILES); a structural ``recompile`` ran.
    * ``FORMULA_DECOMPOSITION`` -- a neutral bare formula; a composition-level ``decompile`` ran.  NO structure
      was selected (the v0.6 identity law: composition is not constitution).
    * ``IDENTITY_ONLY`` -- the identity resolved but no primitive applies (e.g. a charged species has no neutral
      scission descent); the identity question was answered, nothing further was run.
    * ``INPUT_KIND_AMBIGUOUS`` -- more than one input-kind reading resolves to a materially-distinct identity
      (``CO`` = SMILES methanol OR formula carbon monoxide); the front door REFUSES to pick and asks for an
      explicit kind rather than silently launching structural planning (P0-A).
    * ``INVALID_INPUT`` -- the input could not be resolved to any identity, or a helper-reagent string the
      structural plan would read is input-kind ambiguous (0.9.5 A12: the front door guesses for no string it reads).
    """

    STRUCTURAL_PLANNING = "STRUCTURAL_PLANNING"
    FORMULA_DECOMPOSITION = "FORMULA_DECOMPOSITION"
    IDENTITY_ONLY = "IDENTITY_ONLY"
    INPUT_KIND_AMBIGUOUS = "INPUT_KIND_AMBIGUOUS"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class PlanResult:
    """The total answer for one human chemical input: what was understood, and what honestly follows.

    ``status`` is the explicit :class:`PlanStatus` outcome.  ``resolved`` is the front-door identity
    (normalized syntax, composition, layer, losses, receipt, registry candidates), or ``None`` when resolution
    failed (``invalid_reason`` set) OR when the input was input-kind ambiguous (``ambiguity`` set instead --
    the front door deliberately did not select one identity).  ``structural_planning_eligible`` is true iff a
    single constitution was perceived (so a structural ``recompile`` may honestly run).  ``operation``/
    ``response`` are the delegated primitive actually run and its typed result -- ``None`` when none ran.
    """

    target_input: str
    input_kind: InputKind
    status: PlanStatus
    resolved: "object | None"
    invalid_reason: "str | None"
    structural_planning_eligible: bool
    operation: "object | None"
    response: "object | None"
    ambiguity: "object | None" = None

    @property
    def identity_layer(self) -> str:
        """The strongest identity layer perceived (``CONSTITUTION`` / ``FORMULA``), or ``NONE`` if unresolved."""
        return self.resolved.receipt.identity_layer if self.resolved is not None else "NONE"

    @property
    def registry_candidates(self) -> tuple:
        """Registry-known structures sharing this composition -- NOT an exhaustive isomer set (may be empty)."""
        return tuple(self.resolved.registry_candidates) if self.resolved is not None else ()

    @property
    def exit_code(self) -> int:
        """The section-14.4 exit code, derived from :attr:`status`.

        A delegated response's code when an operation ran; SUCCESS when the identity resolved but no operation
        applies (IDENTITY_ONLY -- the front door still answered the identity question); INVALID_INPUT when
        resolution failed OR the input was input-kind ambiguous (the caller must supply an explicit kind).
        """
        from .service import EXIT_INVALID_INPUT, EXIT_SUCCESS

        if self.status in (PlanStatus.INVALID_INPUT, PlanStatus.INPUT_KIND_AMBIGUOUS):
            return EXIT_INVALID_INPUT
        if self.response is not None:
            return self.response.exit_code
        return EXIT_SUCCESS


def plan(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO,
         algebra_profile: "str | None" = None,
         helper_reagents: "tuple[str, ...] | None" = None,
         capability_profile: "str | None" = None) -> PlanResult:
    """Resolve ``target_input`` and deliver the total answer, routing to the eligible existing primitive.

    Never guesses a structure from a bare formula: a FORMULA-layer identity is routed to ``decompile``
    (composition-level), a perceived constitution to ``recompile`` (structural).  An unresolvable input
    returns a typed invalid :class:`PlanResult`, not a raised traceback.

    ``helper_reagents`` (0.7 Round III) threads the human reagent pool into the STRUCTURAL recompile so the canonical
    front door can express it: ``None`` -> the builder's water DEFAULT; a tuple -> an explicit pool; ``()`` -> an
    explicit EMPTY pool (no invented water), runnable only under an algebra with a reagentless-capable provider.
    Formula decomposition has no reagent pool, so it ignores this argument.  0.9.5 (A12, Wave C6 F7): a pool string
    is read like the target -- a bare AUTO string with materially-distinct readings (``CO``: SMILES methanol OR
    formula carbon monoxide) is refused as ``INVALID_INPUT`` naming it, before any search; ``smiles:CO`` or a
    registered name is a decision and proceeds.

    ``capability_profile`` (0.9 Round III, D12a) declares a bench preset name (``"research-lab"``/``"poor-man"``) the
    STRUCTURAL plan projects every ranked route through -- ``None`` asks NO capability question and assumes NO bench.
    Formula decomposition has no route to project, so it ignores this argument.
    """
    from .compilation_ir import CompilationOperation
    from .identity_parse import (
        IdentityParseError,
        detect_auto_ambiguity,
        detect_target_file_ambiguity,
        resolve_identity,
    )
    from .service import build_decompile_request, build_recompile_request, run_compilation

    kind = input_kind if isinstance(input_kind, InputKind) else InputKind(input_kind)

    # P0-A: on the human AUTO surface (a bare paste, no explicit kind), refuse to silently pick between
    # materially-distinct input-kind readings -- 'CO' is methanol (SMILES) AND carbon monoxide (formula).
    # An explicit kind (a flag, or an inline 'smiles:'/'formula:' prefix) is a DECISION, so detect_auto_ambiguity
    # returns None for it and planning proceeds; only a genuinely ambiguous bare AUTO input is refused here.
    # 0.9.5 A14 (Wave D F4): a TARGET_FILE's contents are resolved on that same AUTO path, so an unprefixed string
    # inside the file gets the same refusal -- 'plan CO' refused while a file holding 'CO' planned methanol.  The
    # ambiguity names the file's inner string; a 'smiles:'/'formula:' prefix in the file is the decision, as ever.
    ambiguity = None
    if kind is InputKind.AUTO:
        ambiguity = detect_auto_ambiguity(target_input)
    elif kind is InputKind.TARGET_FILE:
        ambiguity = detect_target_file_ambiguity(target_input)
    if ambiguity is not None:
        return PlanResult(
            target_input, kind, PlanStatus.INPUT_KIND_AMBIGUOUS, None, None, False, None, None,
            ambiguity=ambiguity,
        )

    try:
        resolved = resolve_identity(target_input, kind)
    except IdentityParseError as exc:
        return PlanResult(target_input, kind, PlanStatus.INVALID_INPUT, None, str(exc), False, None, None)

    # pass the user's kind through to the builder unchanged (AUTO -> None so its origin reads DEFAULT); the
    # builder re-resolves the SAME (target, kind) deterministically, so plan and the delegate never diverge.
    builder_kind = None if kind is InputKind.AUTO else kind

    if resolved.structure_perceived:
        # a single constitution IS established -> structural planning is eligible.  The selected transform-algebra
        # profile (0.7 Round II) flows into the structural recompile so `plan --algebra certified-route-v07` widens
        # the algebra end-to-end; formula decomposition (below) has no route algebra, so it ignores the profile.
        # 0.9 Round III (D12a): the capability profile flows into the STRUCTURAL recompile exactly as the algebra
        # profile does -- `plan TARGET --capability-profile poor-man` projects every planned route through that bench.
        # Formula decomposition (below) has no route to project, so it ignores the profile.
        # 0.9.5 (A12, Wave C6 F7): the human front door never guesses between readings for ANY string it reads --
        # a helper reagent is refused exactly like the target ('plan CO' refused while '--reagents CO' ran methanol).
        for reagent in helper_reagents or ():
            reagent_ambiguity = detect_auto_ambiguity(reagent)
            if reagent_ambiguity is not None:
                return PlanResult(target_input, kind, PlanStatus.INVALID_INPUT, None,
                                  _reagent_ambiguity_reason(reagent, reagent_ambiguity), False, None, None)
        request = build_recompile_request(target_input, input_kind=builder_kind, algebra_profile=algebra_profile,
                                           helper_reagents=helper_reagents, capability_profile=capability_profile)
        response = run_compilation(request)
        return PlanResult(
            target_input, kind, PlanStatus.STRUCTURAL_PLANNING, resolved, None, True,
            CompilationOperation.RECOMPILE, response,
        )

    # composition known, constitution NOT established -> a structure search is NOT eligible and is
    # deliberately not run (guessing a constitution would be a defect).  Formula decomposition IS justified
    # -- but we hand the descent the RESOLVED composition, not the raw human spelling: plan already resolved
    # the identity through the tolerant grammar, and the formula-descent primitive parses a strict formula.
    # A charged species has no neutral scission descent, so decomposition is skipped and only the identity /
    # ambiguity is reported (never a misleading "invalid" from feeding an ion to a neutral descent).
    formula = resolved.formula
    if getattr(formula, "charge", 0) != 0:
        return PlanResult(target_input, kind, PlanStatus.IDENTITY_ONLY, resolved, None, False, None, None)
    request = build_decompile_request(repr(formula), input_kind=InputKind.FORMULA)
    response = run_compilation(request)
    return PlanResult(
        target_input, kind, PlanStatus.FORMULA_DECOMPOSITION, resolved, None, False,
        CompilationOperation.DECOMPILE, response,
    )


def _reagent_ambiguity_reason(reagent: str, ambiguity: "object") -> str:
    """The refusal text for an input-kind ambiguous helper reagent: every reading, and the explicit forms to use."""
    readings = " | ".join(f"{kind.value} -> {ident.receipt.normalized}" for kind, ident in ambiguity.interpretations)
    return (f"helper reagent {reagent!r} is input-kind ambiguous ({readings}); the plan front door will not choose -- "
            f"write smiles:{reagent} or formula:{reagent}, or a registered name")


def _candidate_names(resolved: "object") -> tuple[str, ...]:
    """The display names of the registry-known candidate structures (best-effort)."""
    names: list[str] = []
    for cand in getattr(resolved, "registry_candidates", ()):  # NamedStructure or similar
        name = getattr(cand, "name", None) or getattr(cand, "common_name", None)
        names.append(name if isinstance(name, str) else repr(cand))
    return tuple(names)


def plan_result_to_payload(result: PlanResult) -> dict:
    """A stable, machine-readable payload for a :class:`PlanResult` (the ``smartchem plan --json`` view).

    It nests the FULL delegated :func:`~smartchem.service.response_to_payload` under ``compilation`` so no
    downstream information is lost, and adds the front-door identity summary the plan verb exists to expose:
    normalized syntax, composition, the identity layer, whether structural planning is eligible, and the
    labelled -- non-exhaustive -- registry candidate set.
    """
    from .service import response_to_payload

    identity: "dict | None" = None
    if result.resolved is not None:
        receipt = result.resolved.receipt
        expr = result.resolved.formula_expr
        identity = {
            "requested_kind": receipt.requested_kind.value,
            "resolved_kind": receipt.resolved_kind.value,
            "identity_layer": receipt.identity_layer,
            "normalized": receipt.normalized,
            "structure_perceived": result.resolved.structure_perceived,
            "constitution_established": result.resolved.constitution_established,
            "receipt_summary": receipt.summary(),
            "formula_syntax": (
                {
                    "original": expr.original,
                    "normalized": expr.normalized,
                    "components": [
                        {"multiplier": c.multiplier, "formula": expr_render_component(c)}
                        for c in expr.components
                    ],
                    "charge": expr.charge,
                    "notes": list(expr.notes),
                }
                if expr is not None
                else None
            ),
            "registry_candidates": list(_candidate_names(result.resolved)),
            "registry_candidates_note": (
                "registry-known structures sharing this composition; NOT an exhaustive isomer set, and "
                "an empty set is NOT proof the composition has no other real constitution"
            ),
        }
    ambiguity_payload: "dict | None" = None
    if result.ambiguity is not None:
        ambiguity_payload = {
            "interpretations": [
                {
                    "input_kind": k.value,
                    "identity_layer": ident.receipt.identity_layer,
                    "normalized": ident.receipt.normalized,
                    "resolved_kind": ident.receipt.resolved_kind.value,
                }
                for k, ident in result.ambiguity.interpretations
            ],
            "note": (
                "more than one input-kind reading resolves to a materially-distinct identity; supply an "
                "explicit kind (e.g. smiles:… or formula:…) -- the front door will not choose for you"
            ),
        }
    return {
        "schema": PLAN_SCHEMA,
        "target_input": result.target_input,
        "input_kind": result.input_kind.value,
        "status": result.status.value,
        "invalid_reason": result.invalid_reason,
        "identity": identity,
        "input_kind_ambiguity": ambiguity_payload,
        "structural_planning_eligible": result.structural_planning_eligible,
        "operation": result.operation.value if result.operation is not None else None,
        "exit_code": result.exit_code,
        "compilation": response_to_payload(result.response) if result.response is not None else None,
    }


def expr_render_component(component: "object") -> str:
    """The element string of one FormulaComponent's atoms (delegates to the syntax layer's renderer)."""
    from .formula_expr import _render_formula_body

    return _render_formula_body(component.formula)


def render_plan_human(result: PlanResult) -> str:
    """A concise human report: what was understood, the identity layer, ambiguity, and what honestly follows."""
    lines: list[str] = [f"plan {result.target_input!r}"]
    if result.status is PlanStatus.INPUT_KIND_AMBIGUOUS and result.ambiguity is not None:
        lines.append("  INPUT-KIND AMBIGUOUS: more than one reading resolves to a distinct identity --")
        for kind, ident in result.ambiguity.interpretations:
            lines.append(
                f"    - as {kind.value:8} -> {ident.receipt.normalized} ({ident.receipt.identity_layer} layer)"
            )
        # the ambiguous string itself: the paste for AUTO, the file's contents for TARGET_FILE (A14 F4)
        inner = result.ambiguity.target_input
        if result.input_kind is InputKind.TARGET_FILE:
            lines.append("  the front door will NOT choose; prefix the file's contents with an explicit kind (e.g. "
                         f"smiles:{inner} or formula:{inner})")
        else:
            lines.append("  the front door will NOT choose; re-run with an explicit kind (e.g. "
                         f"smiles:{inner} or formula:{inner})")
        return "\n".join(lines)
    if result.resolved is None:
        lines.append(f"  INVALID INPUT: {result.invalid_reason}")
        return "\n".join(lines)

    resolved = result.resolved
    receipt = resolved.receipt
    lines.append(f"  understood as : {receipt.resolved_kind.value} ({receipt.identity_layer} layer)")
    lines.append(f"  composition   : {receipt.normalized}")
    if resolved.formula_expr is not None and resolved.formula_expr.is_multi_component:
        boundary = " + ".join(
            f"{c.multiplier}x {expr_render_component(c)}" if c.multiplier != 1 else expr_render_component(c)
            for c in resolved.formula_expr.components
        )
        lines.append(f"  components    : {boundary}  (hydrate/adduct boundary retained)")
    # receipt.notes is the superset (it already carries the FormulaExpr syntax notes), so render it alone.
    for note in resolved.receipt.notes:
        lines.append(f"  parse note    : {note}")

    if resolved.constitution_established:
        lines.append("  identity      : a single constitution is established -> structural planning eligible")
    else:
        names = _candidate_names(resolved)
        if names:
            lines.append(
                f"  ambiguity     : composition known; constitution NOT established. "
                f"registry-known structures with this formula (NOT exhaustive): {', '.join(names)}"
            )
        else:
            lines.append(
                "  ambiguity     : composition known; constitution NOT established. No registry-known "
                "structure has this formula (this is registry coverage, NOT proof none exists)."
            )
        lines.append("  identity      : structural planning NOT eligible -- a structure is not selected")

    if result.response is not None:
        resp = result.response
        lines.append(
            f"  ran           : {result.operation.value.lower()} -> outcome {resp.outcome.value}"
            + (f"; status {resp.standard_status}" if getattr(resp, "standard_status", None) else "")
        )
        # 0.9 Round III (D12a): the front door gains a per-route READINESS + CAPABILITY block for the first time --
        # the 0.6 front door showed only the outcome banner.  The mission's own example is `plan TARGET
        # --capability-profile ...`, and human == JSON parity demands the same capability semantics the --json plan
        # payload nests.  Uses the ONE shared capability renderer, so plan and recompile cannot drift.
        dossiers = getattr(resp, "ranked_route_dossiers", ())
        if dossiers:
            from .service import readiness_tier_line, render_capability_lines
            lines.append("  ranked routes (best first; readiness + capability):")
            for i, r in enumerate(dossiers[:20], 1):
                lines.append(f"    {i}. [{r.fit_status}/{r.readiness_tier}] {r.equation}  #{r.route_digest[:12]}")
                lines.append(f"        READINESS: {readiness_tier_line(r.readiness_tier)}")
                lines.extend(render_capability_lines(
                    r.capability_assessment, resp.request.capability_profile_origin, indent="        ",
                ))
            if len(dossiers) > 20:
                lines.append(f"    ... and {len(dossiers) - 20} more ranked route(s)")
    elif getattr(resolved.formula, "charge", 0) != 0:
        lines.append(
            "  ran           : nothing further -- a charged species has no neutral formula descent; "
            "identity reported only"
        )
    return "\n".join(lines)
