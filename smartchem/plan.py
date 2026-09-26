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

from .identity_parse import InputKind

__all__ = ["PlanResult", "plan", "plan_result_to_payload", "render_plan_human"]

PLAN_SCHEMA = "smartchem.plan/plan-result-v0.6"


@dataclass(frozen=True)
class PlanResult:
    """The total answer for one human chemical input: what was understood, and what honestly follows.

    ``resolved`` is the front-door identity (normalized syntax, composition, layer, losses, receipt,
    registry candidates) or ``None`` when resolution itself failed (``invalid_reason`` is then set).
    ``structural_planning_eligible`` is true iff a single constitution was perceived (so a structural
    ``recompile`` may honestly run).  ``operation``/``response`` are the delegated primitive actually
    run and its typed result -- ``None`` for an invalid input.
    """

    target_input: str
    input_kind: InputKind
    resolved: "object | None"
    invalid_reason: "str | None"
    structural_planning_eligible: bool
    operation: "object | None"
    response: "object | None"

    @property
    def identity_layer(self) -> str:
        """The strongest identity layer perceived (``CONSTITUTION`` / ``FORMULA``), or ``NONE`` if invalid."""
        return self.resolved.receipt.identity_layer if self.resolved is not None else "NONE"

    @property
    def registry_candidates(self) -> tuple:
        """Registry-known structures sharing this composition -- NOT an exhaustive isomer set (may be empty)."""
        return tuple(self.resolved.registry_candidates) if self.resolved is not None else ()

    @property
    def exit_code(self) -> int:
        """The section-14.4 exit code.

        The delegated response's code when an operation ran; SUCCESS when the identity resolved but no
        operation applies (e.g. a charged species has no neutral formula descent -- the front door still
        answered the identity question successfully); INVALID_INPUT only when resolution itself failed.
        """
        from .service import EXIT_INVALID_INPUT, EXIT_SUCCESS

        if self.response is not None:
            return self.response.exit_code
        if self.resolved is not None:
            return EXIT_SUCCESS
        return EXIT_INVALID_INPUT


def plan(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO) -> PlanResult:
    """Resolve ``target_input`` and deliver the total answer, routing to the eligible existing primitive.

    Never guesses a structure from a bare formula: a FORMULA-layer identity is routed to ``decompile``
    (composition-level), a perceived constitution to ``recompile`` (structural).  An unresolvable input
    returns a typed invalid :class:`PlanResult`, not a raised traceback.
    """
    from .compilation_ir import CompilationOperation
    from .identity_parse import IdentityParseError, resolve_identity
    from .service import build_decompile_request, build_recompile_request, run_compilation

    kind = input_kind if isinstance(input_kind, InputKind) else InputKind(input_kind)

    try:
        resolved = resolve_identity(target_input, kind)
    except IdentityParseError as exc:
        return PlanResult(target_input, kind, None, str(exc), False, None, None)

    # pass the user's kind through to the builder unchanged (AUTO -> None so its origin reads DEFAULT); the
    # builder re-resolves the SAME (target, kind) deterministically, so plan and the delegate never diverge.
    builder_kind = None if kind is InputKind.AUTO else kind

    if resolved.structure_perceived:
        # a single constitution IS established -> structural planning is eligible.
        request = build_recompile_request(target_input, input_kind=builder_kind)
        response = run_compilation(request)
        return PlanResult(
            target_input, kind, resolved, None, True, CompilationOperation.RECOMPILE, response
        )

    # composition known, constitution NOT established -> a structure search is NOT eligible and is
    # deliberately not run (guessing a constitution would be a defect).  Formula decomposition IS justified
    # -- but we hand the descent the RESOLVED composition, not the raw human spelling: plan already resolved
    # the identity through the tolerant grammar, and the formula-descent primitive parses a strict formula.
    # A charged species has no neutral scission descent, so decomposition is skipped and only the identity /
    # ambiguity is reported (never a misleading "invalid" from feeding an ion to a neutral descent).
    formula = resolved.formula
    if getattr(formula, "charge", 0) != 0:
        return PlanResult(target_input, kind, resolved, None, False, None, None)
    request = build_decompile_request(repr(formula), input_kind=InputKind.FORMULA)
    response = run_compilation(request)
    return PlanResult(
        target_input, kind, resolved, None, False, CompilationOperation.DECOMPILE, response
    )


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
    return {
        "schema": PLAN_SCHEMA,
        "target_input": result.target_input,
        "input_kind": result.input_kind.value,
        "invalid_reason": result.invalid_reason,
        "identity": identity,
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
    elif getattr(resolved.formula, "charge", 0) != 0:
        lines.append(
            "  ran           : nothing further -- a charged species has no neutral formula descent; "
            "identity reported only"
        )
    return "\n".join(lines)
