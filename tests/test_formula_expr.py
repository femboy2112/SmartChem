"""FORMULA-EXPR-01 -- the lossless human-formula syntax layer (v0.6 Human Chemical Front Door).

Proves the finite tolerant grammar that sits BEFORE :class:`~smartchem.decompiler.Formula`:

* the declared positive corpus parses, each to its EXACT composition/charge/component structure;
* the boundary corpus is refused with the RIGHT typed reason (malformed vs parametric) -- never coerced
  into a concrete formula, never silently stripped;
* the normalization laws hold (idempotence, Unicode/ASCII composition-equality, conservation, component
  retention, render/reparse, fail-closed malformed input);
* the input-size and nesting-depth guards fire (a pasted identity is a short string, not a program).

Every spelling claimed as supported has a committed assertion here; nothing is documented that is not tested.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from smartchem.decompiler import Formula
from smartchem.formula_expr import (
    FormulaExpr,
    FormulaSyntaxError,
    ParametricFormulaError,
    normalize_formula_text,
    parse_formula_expr,
)


def _comp(expr: FormulaExpr) -> dict[str, int]:
    return dict(expr.to_formula().counts)


# -- positive corpus: (input, expected composition, expected charge, expected component count) ---------------
_POSITIVE = [
    ("H2O", {"H": 2, "O": 1}, 0, 1),
    ("C8H10N4O2", {"C": 8, "H": 10, "N": 4, "O": 2}, 0, 1),
    ("C₈H₁₀N₄O₂", {"C": 8, "H": 10, "N": 4, "O": 2}, 0, 1),   # Unicode subscripts
    ("(NH4)2SO4", {"H": 8, "N": 2, "O": 4, "S": 1}, 0, 1),
    ("(NH₄)₂SO₄", {"H": 8, "N": 2, "O": 4, "S": 1}, 0, 1),
    ("CuSO4·5H2O", {"Cu": 1, "H": 10, "O": 9, "S": 1}, 0, 2),                     # middle-dot hydrate
    ("CuSO₄·5H₂O", {"Cu": 1, "H": 10, "O": 9, "S": 1}, 0, 2),
    ("CuSO4 . 5 H2O", {"Cu": 1, "H": 10, "O": 9, "S": 1}, 0, 2),                       # spaced ASCII-dot hydrate
    ("CaCl2·2H2O", {"Ca": 1, "Cl": 2, "H": 4, "O": 2}, 0, 2),
    ("Al2(SO4)3", {"Al": 2, "O": 12, "S": 3}, 0, 1),
    ("K4[Fe(CN)6]", {"C": 6, "Fe": 1, "K": 4, "N": 6}, 0, 1),                          # square grouping
    ("SO4^2-", {"O": 4, "S": 1}, -2, 1),                                              # caret charge
    ("SO₄²⁻", {"O": 4, "S": 1}, -2, 1),                                 # Unicode superscript charge
    ("NH4+", {"H": 4, "N": 1}, 1, 1),                                                  # bare-sign charge
    ("[NH4]+", {"H": 4, "N": 1}, 1, 1),                                                # bracket ion
    ("[Fe(CN)6]4-", {"C": 6, "Fe": 1, "N": 6}, -4, 1),                                 # bracket-ion magnitude
]


@pytest.mark.parametrize("text,comp,charge,ncomp", _POSITIVE)
def test_positive_corpus_parses_to_exact_composition(text, comp, charge, ncomp):
    expr = parse_formula_expr(text)
    assert _comp(expr) == comp, f"{text!r} composition"
    assert expr.charge == charge, f"{text!r} charge"
    assert len(expr.components) == ncomp, f"{text!r} component count"
    # the projection is a real Formula (validates elements/counts at construction)
    assert isinstance(expr.to_formula(), Formula)


# -- boundary corpus: each refused with the RIGHT typed error class -------------------------------------------
_MALFORMED = ["2", "()", "CuSO4·", "·H2O", "A..B", "(NH4", "NH4)", "Fe0", "Xx2",
              "garbage prose here", "H2O extra", "", "   ", "K4[Fe(CN)6)"]
_PARAMETRIC = ["(C2H4)n", "C6H(12±2)O6", "[Fe(CN)6]n", "(SiO2)x"]


@pytest.mark.parametrize("text", _MALFORMED)
def test_malformed_refused_as_syntax_error(text):
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr(text)
    # and NOT as the parametric subclass (a malformed string is not a parametric family)
    try:
        parse_formula_expr(text)
    except ParametricFormulaError:  # pragma: no cover - would fail the assertion below
        pytest.fail(f"{text!r} was misclassified as parametric")
    except FormulaSyntaxError:
        pass


@pytest.mark.parametrize("text", _PARAMETRIC)
def test_parametric_refused_with_its_own_type_never_coerced(text):
    # a well-formed-but-parametric form is refused as ParametricFormulaError, never coerced to a concrete count.
    with pytest.raises(ParametricFormulaError):
        parse_formula_expr(text)


def test_MxOy_is_refused_not_coerced():
    # MxOy: 'Mx' is read as a 2-letter symbol and refused as an unknown element -- a typed refusal, never a
    # silent concrete formula.  (The exact class is FormulaSyntaxError; the point is it does not parse.)
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr("MxOy")


# -- normalization laws --------------------------------------------------------------------------------------
_NORMALIZE_CASES = [
    "H2O", "C8H10N4O2", "C₈H₁₀N₄O₂", "(NH₄)₂SO₄",
    "CuSO4·5H2O", "CuSO₄·5H₂O", "CuSO4 . 5 H2O", "SO₄²⁻", "[Fe(CN)6]4-",
]


@pytest.mark.parametrize("text", _NORMALIZE_CASES)
def test_normalize_is_idempotent(text):
    once = normalize_formula_text(text)
    assert normalize_formula_text(once) == once


@pytest.mark.parametrize("ascii_text,unicode_text", [
    ("CuSO4·5H2O", "CuSO₄·5H₂O"),
    ("(NH4)2SO4", "(NH₄)₂SO₄"),
    ("C8H10N4O2", "C₈H₁₀N₄O₂"),
    ("SO4^2-", "SO₄²⁻"),
])
def test_unicode_and_ascii_spellings_are_the_same_expression(ascii_text, unicode_text):
    a, u = parse_formula_expr(ascii_text), parse_formula_expr(unicode_text)
    assert a.to_formula() == u.to_formula(), "same composition"
    assert a.charge == u.charge, "same charge"
    assert a == u, "same FormulaExpr identity (provenance excluded from equality)"
    assert a.digest == u.digest, "same digest"


def test_conservation_projection_sums_every_component():
    # CuSO4.5H2O: the 5x on the water component must reach the H (10) and O (9=4+5) counts.
    comp = _comp(parse_formula_expr("CuSO4·5H2O"))
    assert comp == {"Cu": 1, "H": 10, "O": 9, "S": 1}


def test_component_boundary_survives_in_the_expression():
    # the hydrate boundary is retained in FormulaExpr even though to_formula() forgets it.
    expr = parse_formula_expr("CuSO4·5H2O")
    assert expr.is_multi_component
    assert len(expr.components) == 2
    mults = sorted(c.multiplier for c in expr.components)
    assert mults == [1, 5]
    assert any("component" in n.lower() or "hydrate" in n.lower() for n in expr.notes)


@pytest.mark.parametrize("text", [c[0] for c in _POSITIVE])
def test_render_reparses_to_an_equal_expression(text):
    expr = parse_formula_expr(text)
    reparsed = parse_formula_expr(expr.render())
    assert reparsed == expr, f"{text!r} render {expr.render()!r} did not round-trip"


def test_malformed_never_normalizes_into_a_valid_unrelated_formula():
    # fail-closed: a dangling separator must be REFUSED, not silently become the valid neighbour 'CuSO4'.
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr("CuSO4·")
    # a stray superscript-minus with no atoms must not become a valid formula either.
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr("^2-")


# -- guards --------------------------------------------------------------------------------------------------
def test_oversize_input_is_refused():
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr("H2O" * 500)  # ~1500 chars, over the 512 bound


def test_deep_nesting_is_refused_not_stack_overflowed():
    bomb = "(" * 200 + "H" + ")" * 200
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr(bomb)


# -- property-based -----------------------------------------------------------------------------------------
_ELEMENTS = ["H", "C", "N", "O", "S", "Na", "Cl", "Ca", "Fe", "Cu"]


@st.composite
def _ascii_formula(draw):
    n = draw(st.integers(min_value=1, max_value=5))
    parts = []
    for _ in range(n):
        el = draw(st.sampled_from(_ELEMENTS))
        k = draw(st.integers(min_value=1, max_value=99))
        parts.append(f"{el}{k if k > 1 else ''}")
    return "".join(parts)


@given(_ascii_formula())
@settings(max_examples=200)
def test_property_parse_then_render_round_trips(text):
    expr = parse_formula_expr(text)
    assert parse_formula_expr(expr.render()) == expr


@given(_ascii_formula())
@settings(max_examples=200)
def test_property_normalize_idempotent(text):
    once = normalize_formula_text(text)
    assert normalize_formula_text(once) == once


@given(_ascii_formula())
@settings(max_examples=200)
def test_property_projection_conserves_total_atoms(text):
    expr = parse_formula_expr(text)
    total = sum(k for _, k in expr.to_formula().counts)
    # the atom total equals the sum over components of multiplier * that component's atoms.
    by_component = sum(m * k for c in expr.components for _, k in c.formula.counts for m in (c.multiplier,))
    assert total == by_component
