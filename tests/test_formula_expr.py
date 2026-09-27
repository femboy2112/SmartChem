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
    AmbiguousChargeError,
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


# == v0.6 hostile merge-readiness fixes (P0-B / P0-C / P0-D) ==================================================

# -- P0-B: an ambiguous single-element ASCII ion is a typed refusal, never a silent mis-charge ---------------
# The digit before a BARE sign could be an atom count (Fe3, charge +-1) or the charge magnitude (Fe, charge
# +-3); the two readings materially differ, so a single-element body is refused with AmbiguousChargeError.
@pytest.mark.parametrize("text", ["Fe3+", "Ca2+", "Mg2+", "Al3+", "O2-", "Fe2+", "Cu2+", "N3-", "C60-"])
def test_P0B_single_element_bare_sign_ion_is_ambiguous(text):
    with pytest.raises(AmbiguousChargeError):
        parse_formula_expr(text)


# a MULTI-element body with a >=2-digit trailing run before a bare sign is ALSO ambiguous (SO4+2- vs SO42+1-):
# accepting it fails open to an absurd 42-oxygen composition, so it too is refused (the adversarial-review gap).
@pytest.mark.parametrize("text", ["SO42-", "PO43-", "CO32-", "CrO42-", "Cr2O72-", "B12H122-"])
def test_P0B_multi_element_two_digit_run_is_ambiguous(text):
    with pytest.raises(AmbiguousChargeError):
        parse_formula_expr(text)


# a MULTI-element body is unambiguous (the trailing digit is the last element's count) -> accepted at +-1.
@pytest.mark.parametrize("text,comp,charge", [
    ("NH4+", {"N": 1, "H": 4}, 1),
    ("NO3-", {"N": 1, "O": 3}, -1),
    ("OH-", {"O": 1, "H": 1}, -1),
    ("H3O+", {"H": 3, "O": 1}, 1),      # digit is not adjacent to the sign -> plainly a count
    ("CH3COO-", {"C": 2, "H": 3, "O": 2}, -1),
])
def test_P0B_multi_element_bare_sign_ion_is_accepted(text, comp, charge):
    expr = parse_formula_expr(text)
    assert _comp(expr) == comp
    assert expr.charge == charge


# the unambiguous spellings the refusal points to all resolve, at the intended magnitude.
@pytest.mark.parametrize("text,charge", [
    ("Fe^3+", 3), ("Fe³⁺", 3), ("[Fe]3+", 3), ("Ca^2+", 2), ("Ca²⁺", 2), ("O^2-", -2), ("[O]2-", -2),
])
def test_P0B_explicit_magnitude_spellings_resolve(text, charge):
    assert parse_formula_expr(text).charge == charge


# -- P0-C: a compact ASCII decimal is refused (never coerced into an adduct); '°' is not a separator ---------
@pytest.mark.parametrize("text", [
    "C1.5H2", "CuSO4.5H2O", "2.5H2O", "C0.5O",
    "C₁.5H₂", "Fe₂.₅O", "C₂.5H₆",          # subscript integer before the dot must NOT bypass the guard
])
def test_P0C_compact_ascii_decimal_is_refused_not_an_adduct(text):
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula_expr(text)
    assert "decimal" in str(exc.value).lower()


@pytest.mark.parametrize("text", ["CuSO4°5H2O", "NaCl°2H2O"])
def test_P0C_degree_sign_is_not_a_hydrate_separator(text):
    # the degree sign was silently accepted as an adduct dot; it is now an unknown character.
    with pytest.raises(FormulaSyntaxError):
        parse_formula_expr(text)


# the LEGITIMATE hydrate spellings (Unicode middle-dot, spaced ASCII dot) still parse to the exact composition.
@pytest.mark.parametrize("text,comp", [
    ("CuSO4·5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
    ("CuSO4 . 5 H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
    ("CaCl2·2H2O", {"Ca": 1, "Cl": 2, "H": 4, "O": 2}),
])
def test_P0C_legitimate_hydrate_spellings_still_parse(text, comp):
    assert _comp(parse_formula_expr(text)) == comp


def test_P0C_render_uses_middle_dot_and_round_trips_through_the_decimal_guard():
    # a hydrate renders with '·' (never a compact ASCII '4.5' that the decimal guard would then reject).
    expr = parse_formula_expr("CuSO4·5H2O")
    rendered = expr.render()
    assert "·" in rendered and "." not in rendered
    assert parse_formula_expr(rendered) == expr


# -- P0-D: a leading whole-expression coefficient is a quantity, refused at the identity front door ----------
@pytest.mark.parametrize("text", ["5H2O", "2NaCl", "3CO2", "10H2O"])
def test_P0D_leading_coefficient_is_refused(text):
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula_expr(text)
    assert "coefficient" in str(exc.value).lower()


def test_P0D_a_hydrate_multiplier_after_a_separator_is_still_valid():
    # the '5' AFTER a component separator is a hydrate multiplier, not a leading coefficient -- still accepted.
    expr = parse_formula_expr("CuSO4·5H2O")
    assert sorted(c.multiplier for c in expr.components) == [1, 5]


# -- P1: the "lossless" claim, pinned HONESTLY -- intra-component grouping is a COMPOSITION quotient ---------
def test_P1_intra_component_grouping_is_a_documented_composition_quotient():
    # (NH4)2SO4 and its flat spelling name ONE composition; v0.6 does NOT establish a constitution, so promoting
    # the parenthesization to an identity distinction would smuggle in a bond-graph claim.  This is the DELIBERATE
    # quotient the module docstring now states -- pinned so it is a decision, not a silent overclaim.
    assert parse_formula_expr("(NH4)2SO4") == parse_formula_expr("N2H8SO4")
    assert parse_formula_expr("(NH4)2SO4").digest == parse_formula_expr("N2H8SO4").digest
    assert parse_formula_expr("K4[Fe(CN)6]") == parse_formula_expr("C6FeK4N6")


def test_P1_the_component_boundary_is_NOT_quotiented_away():
    # what IS preserved in identity: the hydrate/adduct boundary -- a flatten is a DIFFERENT expression.
    hydrate = parse_formula_expr("CuSO4·5H2O")            # two components: Cu1 S1 O9 H10
    flat = parse_formula_expr("CuH10O9S")                 # same atoms, ONE component -- must NOT be equal
    assert hydrate.to_formula() == flat.to_formula()      # identical composition
    assert hydrate != flat                                # but a DIFFERENT expression (boundary preserved)
    assert hydrate.is_multi_component and not flat.is_multi_component
