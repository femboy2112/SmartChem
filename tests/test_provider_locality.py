"""Provider locality -- the architectural regression guard for manifest section 2A.3 invariant G3.

(This is manifest section 2A.3 **G3**, "provider locality". It is NOT standard section 16 G3, which is
"terminal policy" -- see the canonical G-numbering table, manifest section 2A.8. The filename carries no bare
"G3" token on purpose, for the same reason ``test_g5_coverage.py`` was renamed.)

The genericity thesis (``TRANSFORM-PROVIDER-01``) is that a NEW transform family is added by registering a
:class:`~smartchem.transform_provider.TransformProvider` -- never by rewriting the core route/DAG/decompile
search recursion.  This file regression-guards the architectural half of that invariant.

WHAT THIS GUARD ENFORCES (and what it cannot):

* The core search recursion (``experiment/routes.py`` ``search_routes``/``search_dags`` and ``compilation_ir.py``
  ``decompile_structure_to_ir``) reaches transforms ONLY through ``registry.enumerate(...)``.  Concretely it may
  not, in those files: reference a family ENUMERATOR (``capped_scissions`` / ``heterolytic_scissions`` /
  ``redox_couples`` / ``bond_order_edits`` and any future one) or a concrete ``*Provider`` class; dynamically
  dispatch to a family via a ``getattr`` / ``importlib.import_module`` / ``__import__`` STRING that names a family
  enumerator or a family module (the string-literal escape a bare identifier scan misses); or delegate to the
  SECOND structural recursion (``structure_decompose`` / ``ionic_decompose``), which reaches families directly and
  lives in a module this guard otherwise whitelists.
* Repo-wide, a family enumerator is referenced in CODE only by the provider layer -- its defining module plus the
  provider module(s) that call it -- so a family call inlined into ANY module (``experiment/dag.py``, a future
  search path, ...) is caught, not just the two core files.

The policed inventory is **DERIVED from the live provider layer**, not hardcoded: the provider classes are every
``class *(TransformProvider)`` in the package, and the family enumerators are the package-level functions each
provider's ``enumerate_transforms`` calls.  So when family #5 lands as a provider, its enumerator and class are
auto-policed (closing the silent-drift and provider-relocation gaps) rather than needing a manual set edit.

THE HONEST BOUNDARY (a static guard cannot close this; do not let the docstring over-claim it does): a WHOLLY
INLINE, hand-rolled transform family written directly into the core recursion with NO shared symbol -- no
enumerator, no provider, no dynamic-dispatch string -- is not statically detectable as "a transform family".  That
residual is covered by the BEHAVIORAL half of G3 (a real new family is found only with an extended ``registry=``,
never the default -- see ``tests/test_bond_order_edit.py``) and by code review, not by this file.  The AST is used
(not grep) so a family name in a docstring -- ``routes.py`` cites ``capped_scissions`` in prose -- is invisible,
while a real import/call/getattr-string is not; :func:`test_detector_is_precise_and_non_vacuous` proves both the
fire and the precision, and :func:`test_the_guard_reddens_on_a_planted_fork` proves it reddens on a real fork.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SMARTCHEM = _REPO / "smartchem"

# The core search recursion: the three ``registry.enumerate`` seams live in exactly these two modules.
_CORE_FILES = (
    _SMARTCHEM / "experiment" / "routes.py",
    _SMARTCHEM / "compilation_ir.py",
)

# The SECOND structural recursion inside structure_descent.py: it reaches families directly (not via the registry).
# It is not on the compiler's route/DAG/decompile path today, but the core delegating to it would violate G3 inside
# a whitelisted module -- so the core is forbidden from naming these entry points.
_SECOND_RECURSION_ENTRYPOINTS = frozenset({"structure_decompose", "ionic_decompose"})

# Modules where a transform family is DEFINED (used only to catch a dynamic-dispatch string naming a family module).
_FAMILY_MODULE_BASENAMES = frozenset({"structure_descent", "bond_order_edit"})

# Non-vacuity FLOOR (not a ceiling): the derivation MUST rediscover at least these; more is fine (a new family
# auto-enters). If the derivation ever returns fewer, it silently broke -- and this floor reddens.
_KNOWN_ENUMERATORS = frozenset(
    {"capped_scissions", "heterolytic_scissions", "redox_couples", "bond_order_edits"}
)
_KNOWN_PROVIDERS = frozenset(
    {"CappedScissionProvider", "HeterolyticScissionProvider", "RedoxHalfReactionProvider", "BondOrderEditProvider"}
)


def _all_smartchem_sources() -> list[Path]:
    return sorted(p for p in _SMARTCHEM.rglob("*.py") if "__pycache__" not in p.parts)


def _referenced_identifiers(source: str) -> set[str]:
    """Every identifier NAMED in code -- ``Name`` ids, ``Attribute`` attrs, imported names.  Docstrings and
    comments are constant/comment nodes, never ``Name``/``Attribute``, so a family name in prose is invisible
    (the whole reason this guard parses the AST instead of grepping)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[-1])
    return names


def _dynamic_dispatch_family_strings(source: str, enumerators: frozenset[str]) -> set[str]:
    """String literals passed to ``getattr`` / ``importlib.import_module`` / ``__import__`` that name a family
    enumerator or a family-defining module -- the dynamic-dispatch fork a bare identifier scan misses.  Scoped to
    those call ARGS so ordinary reflection (``getattr(self, name)`` with a variable, ubiquitous in the dataclass
    validators) and any docstring mention are NOT flagged."""
    hits: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        is_dyn = (isinstance(f, ast.Name) and f.id in ("getattr", "__import__")) or (
            isinstance(f, ast.Attribute) and f.attr == "import_module"
        )
        if not is_dyn:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                s = arg.value
                if s in enumerators or any(m in s for m in _FAMILY_MODULE_BASENAMES):
                    hits.add(f"getattr/import string {s!r}")
    return hits


def _has_registry_enumerate_call(source: str) -> bool:
    """True iff the source calls ``.enumerate(...)`` on a receiver named ``registry`` /
    ``DEFAULT_TRANSFORM_REGISTRY`` -- the actual seam, not any stray ``.enumerate`` (which would let the positive
    control pass vacuously over a gutted search)."""
    receivers = {"registry", "DEFAULT_TRANSFORM_REGISTRY"}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "enumerate"):
            continue
        recv = node.func.value
        if isinstance(recv, ast.Name) and recv.id in receivers:
            return True
        if isinstance(recv, ast.Attribute) and recv.attr in receivers:
            return True
    return False


def _discover_provider_layer() -> tuple[set[str], set[str], dict[str, set[Path]]]:
    """Derive the policed inventory STATICALLY from the live provider layer, so a new family's provider + enumerator
    are auto-policed (no manual set edit; closes the silent-drift and provider-relocation gaps).

    Returns ``(provider_classes, enumerators, enumerator_homes)`` where a provider class is every
    ``class *(TransformProvider)`` in the package, an enumerator is a package-level function called inside some
    provider's ``enumerate_transforms``, and an enumerator's homes are its defining module plus the module(s) of the
    providers that call it (so relocating a provider to its own module keeps that module a legitimate home)."""
    func_defs: dict[str, Path] = {}
    for path in _all_smartchem_sources():
        for node in ast.parse(path.read_text()).body:  # top-level defs only
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_defs.setdefault(node.name, path)

    provider_classes: set[str] = set()
    enumerator_homes: dict[str, set[Path]] = {}
    for path in _all_smartchem_sources():
        for node in ast.walk(ast.parse(path.read_text())):
            if not (
                isinstance(node, ast.ClassDef)
                and any(isinstance(b, ast.Name) and b.id == "TransformProvider" for b in node.bases)
            ):
                continue
            provider_classes.add(node.name)
            for item in node.body:
                if not (isinstance(item, ast.FunctionDef) and item.name == "enumerate_transforms"):
                    continue
                for call in ast.walk(item):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                        fn = call.func.id
                        if fn in func_defs:  # a package-level function the provider delegates to = the enumerator
                            enumerator_homes.setdefault(fn, set())
                            enumerator_homes[fn].add(path)              # the calling provider's module is a home
                            enumerator_homes[fn].add(func_defs[fn])     # the defining module is a home
    return provider_classes, set(enumerator_homes), enumerator_homes


# Derive once at import; every test reads from the live provider layer, not a hardcoded list.
_PROVIDER_CLASSES, _FAMILY_ENUMERATORS, _ENUMERATOR_HOMES = _discover_provider_layer()


def test_the_derivation_is_non_vacuous():
    """The policed inventory is DERIVED, so first prove the derivation actually found the known provider layer --
    otherwise every locality test below would pass by policing an empty set.  A FLOOR, not a ceiling: a new family
    may push the sets larger (and is then auto-policed); the derivation silently returning fewer reddens here."""
    missing_p = _KNOWN_PROVIDERS - _PROVIDER_CLASSES
    missing_e = _KNOWN_ENUMERATORS - _FAMILY_ENUMERATORS
    assert not missing_p, f"provider-class derivation lost known providers: {sorted(missing_p)}"
    assert not missing_e, f"enumerator derivation lost known families: {sorted(missing_e)}"
    for e in _KNOWN_ENUMERATORS:
        assert _ENUMERATOR_HOMES.get(e), f"{e} derived with no home module -- derivation is broken"


@pytest.mark.parametrize("path", _CORE_FILES, ids=lambda p: p.name)
def test_core_recursion_reaches_transforms_only_via_the_registry(path: Path):
    """G3, half one: the core search recursion names no family enumerator, no concrete provider class, and no
    second-recursion entry point -- and does not dynamic-dispatch to a family by string.  Adding a family by
    forking the search (any of those) is exactly the rewrite G3 forbids, and fails here."""
    src = path.read_text()
    forbidden_names = _FAMILY_ENUMERATORS | _PROVIDER_CLASSES | _SECOND_RECURSION_ENTRYPOINTS
    named = _referenced_identifiers(src) & forbidden_names
    dynamic = _dynamic_dispatch_family_strings(src, _FAMILY_ENUMERATORS)
    violations = sorted(named) + sorted(dynamic)
    assert not violations, (
        f"{path.name} reaches a transform family directly {violations} -- G3 (provider locality) requires the core "
        f"search to reach transforms ONLY via registry.enumerate(...)"
    )


@pytest.mark.parametrize("path", _CORE_FILES, ids=lambda p: p.name)
def test_core_recursion_keeps_the_registry_enumerate_seam(path: Path):
    """G3, positive control: the ``registry.enumerate`` seam (on a registry receiver) is PRESENT, so the "names no
    family" half cannot pass over a search that was gutted or rerouted around the algebra parameter."""
    assert _has_registry_enumerate_call(path.read_text()), (
        f"{path.name} no longer reaches transforms via registry.enumerate(...) -- the G3 provider seam is gone"
    )


def test_family_enumerators_are_referenced_only_by_the_provider_layer():
    """G3, half two (repo-wide): a family enumerator is referenced in CODE only by its defining module and the
    provider module(s) that call it.  Catches a family call inlined into ANY module -- the core files,
    ``experiment/dag.py``, or a not-yet-written search path -- not just the two core files."""
    offenders: list[str] = []
    for path in _all_smartchem_sources():
        refs = _referenced_identifiers(path.read_text())
        for enumerator in _FAMILY_ENUMERATORS & refs:
            if path not in _ENUMERATOR_HOMES[enumerator]:
                allowed = sorted(p.name for p in _ENUMERATOR_HOMES[enumerator])
                offenders.append(
                    f"{path.relative_to(_REPO)} references {enumerator!r} (allowed only in {allowed})"
                )
    assert not offenders, (
        "family enumerators are called outside the provider layer -- G3 provider-locality broken:\n  "
        + "\n  ".join(offenders)
    )


def test_detector_is_precise_and_non_vacuous():
    """The AST detectors MUST fire on a genuine reference/fork and MUST NOT fire on a docstring mention or ordinary
    reflection -- the two things that would make the guard useless (miss a fork) or wrong (false-red a legit file)."""
    # a real import+call is flagged
    assert "capped_scissions" in _referenced_identifiers(
        "from smartchem.structure_descent import capped_scissions\n"
        "def fork(m, r):\n    return capped_scissions(m, r)\n"
    )
    # a docstring/comment mention is NOT (the exact routes.py situation)
    assert "capped_scissions" not in _referenced_identifiers(
        'def refuse(m):\n    """used to be a side effect of capped_scissions raising."""\n'
        "    return None  # capped_scissions only in prose\n"
    )
    # the getattr-string dynamic-dispatch fork IS flagged
    assert _dynamic_dispatch_family_strings(
        'x = getattr(sd, "capped_scissions")(m, r)\n', _FAMILY_ENUMERATORS
    )
    assert _dynamic_dispatch_family_strings(
        'mod = importlib.import_module("smartchem.structure_descent")\n', _FAMILY_ENUMERATORS
    )
    # ordinary reflection with a VARIABLE arg is NOT flagged (ubiquitous in the dataclass validators)
    assert not _dynamic_dispatch_family_strings(
        "for name in fields:\n    v = getattr(self, name)\n", _FAMILY_ENUMERATORS
    )


@pytest.mark.parametrize(
    "planted",
    [
        "from .structure_descent import capped_scissions\ncleavages = capped_scissions(t, r)\n",
        "import smartchem.structure_descent as sd\nx = sd.redox_couples(t)\n",
        'x = getattr(sd, "heterolytic_scissions")(t)\n',
        "y = structure_decompose(t)\n",
    ],
    ids=["import+call", "module.attr", "getattr-string", "second-recursion"],
)
def test_the_guard_reddens_on_a_planted_fork(planted: str):
    """Prove the core-locality check reddens on each real fork vector, applied to a genuine core file's source (so
    the check is exercised end to end, not just its helpers).  The clean tree passing + these reddening is the
    non-vacuity of the guard as a whole."""
    mutant = _CORE_FILES[0].read_text() + "\n" + planted
    forbidden_names = _FAMILY_ENUMERATORS | _PROVIDER_CLASSES | _SECOND_RECURSION_ENTRYPOINTS
    named = _referenced_identifiers(mutant) & forbidden_names
    dynamic = _dynamic_dispatch_family_strings(mutant, _FAMILY_ENUMERATORS)
    assert named or dynamic, f"a planted fork slipped past the guard: {planted!r}"
