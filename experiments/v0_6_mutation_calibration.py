"""v0.6 mutation calibration -- prove the front-door mutation-control tests are NOT vacuous.

For each of the eight mutants the v0.6 plan requires to die, this harness INJECTS the mutation (a targeted
monkeypatch that faithfully reproduces the defect), then evaluates the discriminating check the matching
``tests/test_plan_front_door.py::test_mutant_N_*`` pins.  A mutant is KILLED iff the check now yields the wrong
answer (i.e. the test would fail); a mutant that SURVIVES means the test is vacuous and the harness exits 1.

This is the calibration behind the "checks derived from their own subject" / "vacuous mutant survival" lesson:
a soundness gate is only worth its green if a plausible break turns it red.  Run:

    .venv/bin/python experiments/v0_6_mutation_calibration.py
"""
from __future__ import annotations

import sys
from contextlib import contextmanager

import smartchem.formula_expr as fe
import smartchem.identity_parse as ip
from smartchem.compilation_ir import CompilationOperation
from smartchem.identity_parse import IdentityParseError, InputKind, resolve_identity
from smartchem.plan import plan, plan_result_to_payload


@contextmanager
def _patched(obj, attr, value):
    """Temporarily set ``obj.attr = value``, restoring the original on exit."""
    sentinel = object()
    original = getattr(obj, attr, sentinel)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        if original is sentinel:
            delattr(obj, attr)
        else:
            setattr(obj, attr, original)


def _kill(name: str, detected: bool, detail: str) -> bool:
    tag = "KILLED " if detected else "SURVIVED"
    print(f"  [{tag}] mutant {name}: {detail}")
    return detected


# -- MUTANT 1: drop Unicode subscripts instead of translating them -------------------------------------------
def mutant_1() -> bool:
    delete_table = {ord(c): None for c in "₀₁₂₃₄₅₆₇₈₉"}
    with _patched(fe, "_SUBSCRIPTS", delete_table):
        comp = dict(resolve_identity("C₈H₁₀N₄O₂").formula.counts)
    detected = comp != {"C": 8, "H": 10, "N": 4, "O": 2}
    return _kill("1 (subscripts dropped)", detected, f"C8H10N4O2 -> {comp}")


# -- MUTANT 2: ignore the hydrate leading multiplier ---------------------------------------------------------
def mutant_2() -> bool:
    def to_formula_no_mult(self):  # multiplier forced to 1 on every component
        totals: dict[str, int] = {}
        for c in self.components:
            for sym, k in c.formula.counts:
                totals[sym] = totals.get(sym, 0) + k
        return fe.Formula.of(totals, self.charge)

    with _patched(fe.FormulaExpr, "to_formula", to_formula_no_mult):
        comp = dict(resolve_identity("CuSO4·5H2O").formula.counts)
    detected = comp != {"Cu": 1, "H": 10, "O": 9, "S": 1}
    return _kill("2 (hydrate multiplier dropped)", detected, f"CuSO4.5H2O -> {comp}")


# -- MUTANT 3: flatten component boundaries before the receipt -----------------------------------------------
def mutant_3() -> bool:
    orig = fe.parse_formula_expr

    def collapse(text):
        expr = orig(text)
        merged = fe.FormulaComponent(1, expr.to_formula() if expr.charge == 0 else _neutralize(expr), source=text)
        return fe.FormulaExpr((merged,), expr.charge, original=expr.original,
                              normalized=expr.normalized, notes=())  # boundary + notes erased

    def _neutralize(expr):
        totals: dict[str, int] = {}
        for c in expr.components:
            for sym, k in c.formula.counts:
                totals[sym] = totals.get(sym, 0) + k * c.multiplier
        return fe.Formula.of(totals)

    with _patched(fe, "parse_formula_expr", collapse):
        r = resolve_identity("CuSO4·5H2O")
        ncomp = len(r.formula_expr.components)
        boundary_note = any("component" in n.lower() or "hydrate" in n.lower() for n in r.receipt.notes)
    detected = (ncomp != 2) or (not boundary_note)
    return _kill("3 (component boundary flattened)", detected, f"ncomponents={ncomp} boundary_note={boundary_note}")


# -- MUTANT 4: select a registered structure because its formula matches -------------------------------------
def mutant_4() -> bool:
    orig = ip._resolve_formula_layer

    def pick_a_structure(requested, payload, prefix_note, *, auto):
        res = orig(requested, payload, prefix_note, auto=auto)
        if res.registry_candidates:
            mol = getattr(res.registry_candidates[0], "molecule", None)
            if mol is not None:
                return ip.ResolvedIdentity(mol, res.formula, None, res.losses, res.receipt,
                                           formula_expr=res.formula_expr, registry_candidates=res.registry_candidates)
        return res

    with _patched(ip, "_resolve_formula_layer", pick_a_structure):
        r = resolve_identity("C2H6O")
        picked = r.molecule is not None or r.constitution_established
    detected = picked  # the test asserts molecule is None / not constitution_established
    return _kill("4 (structure inferred from formula)", detected, f"molecule_selected={picked}")


# -- MUTANT 5: try formula FIRST on AUTO, so it steals a name/SMILES -----------------------------------------
def mutant_5() -> bool:
    orig_resolve = ip.resolve_identity

    def formula_first(target_input, input_kind=InputKind.AUTO):
        kind = input_kind if isinstance(input_kind, InputKind) else InputKind(input_kind)
        if kind is InputKind.AUTO:
            try:
                return ip._resolve_formula_layer(InputKind.AUTO, target_input, None, auto=True)
            except fe.FormulaSyntaxError:
                pass
        return orig_resolve(target_input, input_kind)

    with _patched(ip, "resolve_identity", formula_first):
        stolen = ip.resolve_identity("CO").receipt.resolved_kind is InputKind.FORMULA
    detected = stolen  # the test asserts CO -> SMILES
    return _kill("5 (AUTO formula steals SMILES)", detected, f"CO_stolen_as_formula={stolen}")


# -- MUTANT 6: a formula-only identity is routed into structural recompile ------------------------------------
def mutant_6() -> bool:
    with _patched(ip.ResolvedIdentity, "structure_perceived", property(lambda self: True)):
        op = plan("C8H10N4O2").operation
    detected = op is CompilationOperation.RECOMPILE  # the test asserts operation is NOT RECOMPILE
    return _kill("6 (formula routed to recompile)", detected, f"operation={op}")


# -- MUTANT 7: normalization/identity provenance is dropped before serialization -----------------------------
def mutant_7() -> bool:
    orig = fe.parse_formula_expr

    def strip_provenance(text):
        expr = orig(text)
        return fe.FormulaExpr(expr.components, expr.charge, original="", normalized="", notes=())

    with _patched(fe, "parse_formula_expr", strip_provenance):
        payload = plan_result_to_payload(plan("CuSO4·5H2O"))
        syntax = payload["identity"]["formula_syntax"]
        lost = (syntax["original"] != "CuSO4·5H2O") or (not syntax["notes"])
    detected = lost  # the test asserts original is retained and notes survive
    return _kill("7 (provenance dropped)", detected, f"original={syntax['original']!r} notes={syntax['notes']}")


# -- MUTANT 8: a parametric form is coerced into a concrete molecule ------------------------------------------
def mutant_8() -> bool:
    orig_body = fe._parse_body

    def coerce_body(text, source):
        return orig_body(text.rstrip("nmxyz"), source)  # strip a trailing variable, coerce to concrete

    with _patched(fe, "_looks_parametric", lambda text: None), _patched(fe, "_parse_body", coerce_body):
        try:
            resolve_identity("(C2H4)n")
            coerced = True   # it parsed -> the parametric family was coerced to a concrete molecule
        except IdentityParseError:
            coerced = False
    detected = coerced  # the test asserts (C2H4)n RAISES
    return _kill("8 (parametric coerced to concrete)", detected, f"(C2H4)n_coerced={coerced}")


def main() -> int:
    print("v0.6 mutation calibration -- each mutant must be KILLED (the matching test must go red):")
    results = [m() for m in (mutant_1, mutant_2, mutant_3, mutant_4, mutant_5, mutant_6, mutant_7, mutant_8)]
    killed = sum(results)
    print(f"\n{killed}/8 mutants killed.")
    if killed != 8:
        print("CALIBRATION FAILED: a mutant survived -- the corresponding test is VACUOUS.", file=sys.stderr)
        return 1
    print("All eight mutation-control tests are discriminating (non-vacuous).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
