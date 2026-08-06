"""Registry-completeness guard for the executor-id dispatch chains.

Two hand-written ``if executor_id == …`` chains shadow the closed runtime
registry: :func:`smartchem.program._observable_payload_error` and
:func:`smartchem.structure_ir.structure_attachment_for_subject`.  Nothing forced
them to stay in sync with ``runtime_registry._DESCRIPTORS``, which is exactly the
"a check derived by hand-copying its subject" pattern this project's own doctrine
distrusts (``THE_COMPILER.md:317``).

This guard applies that doctrine reflexively.  It does **not** re-list the
executor ids by hand; it *derives* the expected set from the registry
(``executor_ids()``) and reads the actual dispatch branches straight out of each
shadow chain's source with the AST, so the guard cannot itself drift out of sync
with the code it checks.

Failure modes closed:

* ``_observable_payload_error`` fails **closed** past its last branch
  (``program.py`` returns a non-``None`` error, and the caller marks the run
  ``invalid``): a tenth executor without a payload validator is a *refused* run,
  never a wrong number.  This guard turns "benign because fail-closed" into
  "impossible by construction" — add such an executor and collection goes red.
* ``structure_attachment_for_subject`` fails **degraded** (a benign
  ``NOT_APPLICABLE``) for any executor whose subject is not an S0 open-diagram.
  Full coverage there is neither required nor correct, so the guard pins the
  reviewed S0 allowlist instead and forbids a branch for an unregistered id.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Callable, Mapping

import smartchem.program as program
import smartchem.runtime_registry as registry
import smartchem.structure_ir as structure_ir


# The executors whose subject carries an S0 electrical open-diagram, and therefore
# a real StructureAttachment rather than a benign NOT_APPLICABLE.  Whether a subject
# *should* carry S0 structure is a semantic judgment not derivable from the
# descriptor alone (both S0 subjects happen to expose a ``.diagram`` that adapts via
# ``adapt_open_diagram``; other ``subject``-attribute executors do not), so this set
# is a **reviewed** decision.  A new S0-diagram-bearing executor must be added here
# consciously — which is precisely the review this guard forces.
_S0_STRUCTURE_EXECUTORS = {
    "smartchem.resistive_dc/exact-relation-sparse-mna-v1",
    "smartchem.rlc_ac/positive-frequency-passive-rlc-v1",
}


def _is_executor_id_operand(node: ast.expr) -> bool:
    """True for ``plan.executor_id`` (attribute) or a bare ``executor_id`` name."""
    if isinstance(node, ast.Attribute):
        return node.attr == "executor_id"
    if isinstance(node, ast.Name):
        return node.id == "executor_id"
    return False


def _resolve_str(node: ast.expr, module_globals: Mapping[str, object]) -> str | None:
    """Resolve an AST comparator to its string value, or ``None`` if not a string.

    Handles a string literal directly and a module-level constant referenced by
    name (the ``_*_EXECUTOR`` constants the dispatch chains actually compare
    against).  Anything else is ignored.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        value = module_globals.get(node.id)
        return value if isinstance(value, str) else None
    return None


def _dispatched_executor_ids(func: Callable[..., object], module: object) -> set[str]:
    """Extract the exact set of executor-id strings a function dispatches on.

    Walks the function's AST for ``==`` comparisons whose left operand is the
    executor id under test (``plan.executor_id`` or a bare ``executor_id``) and
    resolves each right operand — a module-level constant or a string literal — to
    its value in the function's defining module.  Non-equality comparisons and
    comparisons on any other operand (``plan.model``, ``diagnostic``, …) are
    ignored, so only the true dispatch branches are collected.
    """
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    module_globals = vars(module)
    dispatched: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
            continue
        if not _is_executor_id_operand(node.left):
            continue
        value = _resolve_str(node.comparators[0], module_globals)
        if value is not None:
            dispatched.add(value)
    return dispatched


def test_ast_dispatch_extractor_finds_the_known_two_branch_chain():
    """Sanity-anchor the extractor itself on the smaller, hand-checkable chain.

    ``structure_attachment_for_subject`` has exactly two visible branches; if the
    AST walker ever silently stops finding them, the coverage assertions below
    would pass vacuously.  This pins the extractor's own behaviour first.
    """
    dispatched = _dispatched_executor_ids(
        structure_ir.structure_attachment_for_subject, structure_ir
    )
    assert dispatched == _S0_STRUCTURE_EXECUTORS


def test_observable_payload_validator_covers_every_registered_executor_exactly():
    """Every registered executor has a payload branch; no branch is unregistered."""
    dispatched = _dispatched_executor_ids(program._observable_payload_error, program)
    registered = set(registry.executor_ids())
    missing = registered - dispatched
    stale = dispatched - registered
    assert not missing, (
        "registered executors with no _observable_payload_error branch (they would "
        f"fail closed at completion instead of validating): {sorted(missing)}"
    )
    assert not stale, (
        f"_observable_payload_error branches for unregistered executor ids: {sorted(stale)}"
    )
    assert dispatched == registered


def test_structure_attachment_branches_are_a_reviewed_registry_subset():
    """S0 structure branches equal the reviewed allowlist and are all registered."""
    dispatched = _dispatched_executor_ids(
        structure_ir.structure_attachment_for_subject, structure_ir
    )
    registered = set(registry.executor_ids())
    stale = dispatched - registered
    assert not stale, (
        f"structure_attachment_for_subject branches for unregistered ids: {sorted(stale)}"
    )
    assert _S0_STRUCTURE_EXECUTORS <= registered, (
        "reviewed S0 allowlist names an executor id absent from the registry: "
        f"{sorted(_S0_STRUCTURE_EXECUTORS - registered)}"
    )
    assert dispatched == _S0_STRUCTURE_EXECUTORS, (
        "structure_attachment_for_subject S0 branches drifted from the reviewed "
        "allowlist; add a new S0-diagram-bearing executor to _S0_STRUCTURE_EXECUTORS "
        "with a real branch, or remove an obsolete branch"
    )


def test_program_executor_dispatch_constants_are_registered_ids():
    """Every module-level ``_*_EXECUTOR`` string constant is a real registry id.

    Catches a dead or mistyped dispatch constant even before it is wired into a
    branch, so the constant layer cannot silently drift from the registry either.
    """
    registered = set(registry.executor_ids())
    constants = {
        name: value
        for name, value in vars(program).items()
        if name.endswith("_EXECUTOR") and isinstance(value, str)
    }
    assert constants, "expected _*_EXECUTOR dispatch constants in smartchem.program"
    drifted = {
        name: value for name, value in constants.items() if value not in registered
    }
    assert not drifted, f"program dispatch constants absent from the registry: {drifted}"
