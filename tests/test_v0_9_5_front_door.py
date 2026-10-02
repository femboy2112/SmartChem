"""0.9.5 barrier amendment A1 = S15 -- the three front-door misparse fixes (0.6 layer), each pinned here.

Evidence: ``experiments/RESULTS_v0_9_5_boundary_fuzz.md`` and the seed-950 repros
``experiments/fuzz_repros/frontdoor_0{1,2,3}_*.json``.  This file is the ledger the barrier asks for: every
spelling whose front-door outcome MOVES is listed below, with the pre-fix behaviour next to it.

* **F-2 (release-blocking)** -- interior whitespace was deleted wholesale, so ``CuSO4 5H2O`` came back as
  ``CuH2O46S`` with exit 0.  The law now: whitespace is removed only where removal cannot change tokenization;
  a count attached across it, or two letters fused into a different symbol, is a typed ``FormulaSyntaxError``
  naming the explicit separator (a trailing ``<digits><sign>`` after whitespace is the ion ambiguity, so it is an
  ``AmbiguousChargeError``).
* **F-1** -- a superscript digit inside a SMILES bracket atom (``[³]``, ``C[²H]``, ``[¹²C]``) escaped as a bare
  ``ValueError`` and the CLI answered exit 70 INTERNAL; it is now a ``SmilesError``, i.e. typed invalid input.
* **F-3** was adjudicated NOT a defect: a multi-element body with one digit before a bare sign is the declared
  polyatomic-ion convention (count reading, charge +-1: ``NH4+``, ``NO3-``, ``H3O+``, ``VO2+``), so ``HZn3+`` is
  H1 Zn3 charge +1 BY CONVENTION; a single-element body (``Fe3+``) stays refused.  No rule change -- the row
  below pins the convention so that changing it is a visible decision (the fuzzer's R2 signature is this
  declared boundary).
* **F-4** (same defect class as F-1) -- the SMILES ring-closure lexer took ``str.isdigit()`` labels, so a
  superscript became a ring bond and AUTO silently read ``S²N²`` as an S=N ring molecule (seed-952
  ``P-auto-silent-misread``).  Ring labels and ``%nn`` are ASCII decimal only; anything else is a SmilesError.
  ``S²N²`` then reaches the formula grammar, whose contract reads a superscript run as a CHARGE (``S^2N^2``,
  a caret charge with no sign), so it is typed invalid input on every surface and the CLI exits 2.

Accepted-set movement (narrowing only; every other spelling keeps its pre-fix outcome):

====================  =====================================  =====================================
spelling              pre-fix                                post-fix
====================  =====================================  =====================================
``CuSO4 5H2O``        accepted  Cu S O46 H2                  FormulaSyntaxError (separator hint)
``O4 2``              accepted  O42                          FormulaSyntaxError
``Na2SO4 10H2O``      accepted  Na2 S O410 H2                FormulaSyntaxError
``H2 2O``             accepted  H22 O                        FormulaSyntaxError
``H 2O``              accepted  H2 O                         FormulaSyntaxError (count attached)
``Ca(OH) 2``          accepted  Ca O2 H2                     FormulaSyntaxError (count attached)
``K4[Fe(CN)6] 2``     accepted  (group x2)                   FormulaSyntaxError (count attached)
``N a`` / ``C l``     accepted  Na / Cl                      FormulaSyntaxError (symbol fusion)
``[Fe(CN)6] 4-``      accepted  charge -4                    AmbiguousChargeError
``[³]`` ``C[²H]`` …   ValueError -> CLI exit 70              IdentityParseError -> CLI exit 2
``S²N²`` (AUTO)       accepted  SMILES ring H S N            IdentityParseError -> CLI exit 2
``C¹CC¹``             accepted  cyclopropane                 SmilesError
``C%¹⁰CC%¹⁰``         accepted  cyclopropane                 SmilesError
``C%1aCC%1a``         accepted  cyclopropane (unchecked)     SmilesError
====================  =====================================  =====================================

Fullwidth decimal ring labels (``C１CC１``) deliberately do NOT move: ring labels are ``isdecimal()``, not
ASCII-only, because an ASCII-only lexer would drop that SMILES reading and plan would silently decompile the
formula C3 instead of flagging the input-kind ambiguity it flags today.

``SO4 2-`` / ``Fe 3+`` / ``NH4 2+`` were already refused (via the merged ``SO42-`` etc.) and stay
``AmbiguousChargeError`` -- oracle member FD-09 keeps its ``AMBIGUOUS_ASCII_ION`` reason.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartchem.formula_expr import (
    AmbiguousChargeError,
    FormulaSyntaxError,
    normalize_formula_text,
    parse_formula_expr,
)
from smartchem.identity_parse import IdentityParseError, InputKind, resolve_identity
from smartchem.smiles import SmilesError, parse_smiles

_REPRO_DIR = Path(__file__).resolve().parent.parent / "experiments" / "fuzz_repros"
_PENTAHYDRATE = {"Cu": 1, "S": 1, "O": 9, "H": 10}


def _repro(stem: str) -> dict:
    (path,) = sorted(_REPRO_DIR.glob(f"{stem}_*.json"))
    return json.loads(path.read_text(encoding="utf-8"))["repro"]


def _counts(ident) -> dict:
    return dict(ident.formula.counts)


# == the committed repros: minimal text AND its shrunk_from are both refused, typed =============================
# Pre-fix: frontdoor_01 texts were ACCEPTED (O42 / CuH2O46S) -> both parametrizations FAIL on the old code.
@pytest.mark.parametrize("field", ["text", "shrunk_from"])
@pytest.mark.parametrize("kind", [InputKind.FORMULA, InputKind.AUTO])
def test_repro_frontdoor_01_whitespace_merge_is_refused(field, kind):
    text = _repro("frontdoor_01")[field]
    assert text in ("O4 2", "CuSO4 5H2O")
    with pytest.raises(IdentityParseError):
        resolve_identity(text, kind)


# Pre-fix: resolve_identity('[³]') raised a bare ValueError (not IdentityParseError) -> FAILS on the old code.
@pytest.mark.parametrize("field", ["text", "shrunk_from"])
def test_repro_frontdoor_02_bracket_crash_is_typed(field):
    text = _repro("frontdoor_02")[field]
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.AUTO)


# == F-2: the hydrate-by-space spelling and its explicit-separator siblings =====================================
# Pre-fix: 'CuSO4 5H2O' was accepted as CuH2O46S -> FAILS on the old code.
def test_space_hydrate_is_refused_naming_the_explicit_separator():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula_expr("CuSO4 5H2O")
    assert not isinstance(exc.value, AmbiguousChargeError)
    msg = str(exc.value)
    assert "CuSO4·5H2O" in msg and "CuSO4 . 5 H2O" in msg
    # the hint only names spellings that actually parse: the compact ASCII 'CuSO4.5H2O' is the P0-C decimal
    # refusal (oracle FD-08), so recommending it would send the user from one refusal straight into another.
    assert "CuSO4.5H2O" not in msg
    for suggested in ("CuSO4·5H2O", "CuSO4 . 5 H2O"):
        assert dict(parse_formula_expr(suggested).to_formula().counts) == _PENTAHYDRATE


# Pre-fix: these already passed -- they pin that the fix did not take the explicit separators down with it.
@pytest.mark.parametrize("text", ["CuSO4·5H2O", "CuSO4 · 5 H2O", "CuSO4 . 5 H2O", "CuSO₄·5H₂O", "CuSO4\t·\t5H2O"])
@pytest.mark.parametrize("kind", [InputKind.FORMULA, InputKind.AUTO])
def test_explicit_separator_hydrates_are_accepted(text, kind):
    ident = resolve_identity(text, kind)
    assert _counts(ident) == _PENTAHYDRATE
    assert ident.formula.charge == 0
    assert [c.multiplier for c in ident.formula_expr.components] == [1, 5]


# P0-C is untouched: the compact ASCII dot stays a decimal refusal (pre-fix: passed; still passes).
def test_compact_ascii_dot_hydrate_stays_the_decimal_refusal():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula_expr("CuSO4.5H2O")
    assert "decimal" in str(exc.value).lower()


# -- the whitespace law, as a table ---------------------------------------------------------------------------
# REMOVABLE: the right neighbour is a capital / '(' / '[' (a token always starts there, whatever precedes it),
# either neighbour is the separator, or the right neighbour is a charge glyph.  Pre-fix: all passed.
_WS_ACCEPTED = [
    ("H2 O", {"H": 2, "O": 1}, 0),                           # digit -> capital
    ("Na Cl", {"Na": 1, "Cl": 1}, 0),                        # lowercase -> capital: 'l' cannot absorb 'C'
    ("C O", {"C": 1, "O": 1}, 0),                            # capital -> capital
    ("Ca (OH)2", {"Ca": 1, "O": 2, "H": 2}, 0),              # letter -> '('
    ("K4 [Fe(CN)6]", {"K": 4, "Fe": 1, "C": 6, "N": 6}, 0),  # digit -> '['
    ("(NH4)2 SO4", {"N": 2, "H": 8, "S": 1, "O": 4}, 0),     # digit -> capital after a group count
    ("H2 O", {"H": 2, "O": 1}, 0),                      # NBSP is whitespace too
    ("NH4 +", {"N": 1, "H": 4}, 1),                          # -> bare sign
    ("SO4 ^2-", {"S": 1, "O": 4}, -2),                       # -> caret
    ("SO4^ 2-", {"S": 1, "O": 4}, -2),                       # caret -> magnitude digit (not a count)
    ("SO₄ ²⁻", {"S": 1, "O": 4}, -2),                        # -> superscript charge
]


@pytest.mark.parametrize("text,comp,charge", _WS_ACCEPTED)
def test_whitespace_removed_only_where_tokenization_cannot_change(text, comp, charge):
    expr = parse_formula_expr(text)
    assert dict(expr.to_formula().counts) == comp
    assert expr.charge == charge


# REFUSED: removal would attach a count (digit/letter/')'/']' -> digit) or fuse letters into another symbol.
# Pre-fix: EVERY row here was accepted (a silent composition) -> each FAILS on the old code.
_WS_REFUSED = [
    "CuSO4 5H2O",       # digit -> digit: the hydrate coefficient glued onto O4 (was CuH2O46S)
    "O4 2",             # the shrunk repro (was O42)
    "Na2SO4 10H2O",     # (was Na2 S O410 H2)
    "H2 2O",            # (was H22 O)
    "H 2O",             # letter -> digit: the '2' would become H's count
    "Ca(OH) 2",         # ')' -> digit: the '2' would become the group multiplier
    "K4[Fe(CN)6] 2",    # ']' -> digit: likewise
    "C l",              # capital -> lowercase: fuses into chlorine
    "N a",              # fuses into sodium
    "CuSO4\t5H2O",      # tab
    "CuSO4 5H2O",  # NBSP
]


@pytest.mark.parametrize("text", _WS_REFUSED)
def test_whitespace_that_would_change_tokenization_is_a_typed_refusal(text):
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula_expr(text)
    assert not isinstance(exc.value, AmbiguousChargeError)
    assert "separator" in str(exc.value)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.AUTO)


# A lowercase LEFT neighbour can never fuse (the tokenizer takes one lowercase, only after a capital), so these
# keep their pre-fix refusal and its reason -- the RC funnel's LOWERCASE_ELEMENT_NOT_A_KNOWN_NAME class does not
# get relabelled as a whitespace fault.  Pre-fix: passed; still passes.
@pytest.mark.parametrize("text", ["Na l", "sodium chloride"])
def test_lowercase_left_neighbour_keeps_its_old_refusal(text):
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula_expr(text)
    assert "unexpected lowercase" in str(exc.value)


# A whitespace-separated trailing '<digits><sign>' is the ion ambiguity itself (magnitude vs merged count).
# Pre-fix: '[Fe(CN)6] 4-' was accepted at -4 -> FAILS on the old code; the other three were already
# AmbiguousChargeError (via the merged 'SO42-' / 'Fe3+' / 'NH42+') and pass either way.
@pytest.mark.parametrize("text", ["SO4 2-", "Fe 3+", "NH4 2+", "[Fe(CN)6] 4-"])
def test_spaced_charge_magnitude_is_an_ambiguous_ion(text):
    with pytest.raises(AmbiguousChargeError) as exc:
        parse_formula_expr(text)
    assert "ambiguous ASCII ion" in str(exc.value)   # the RC funnel's AMBIGUOUS_ASCII_ION reason (FD-09)


# -- normaliser idempotence over the accepted corpus, and it never hands back whitespace ------------------------
# Pre-fix: idempotence already held (the old normaliser deleted all whitespace) -- this pins that the new,
# selective normaliser keeps it; the refusal half FAILS on the old code (it returned the merged spelling).
_IDEMPOTENCE_CORPUS = [t for t, _, _ in _WS_ACCEPTED] + [
    "H2O", "C8H10N4O2", "C₈H₁₀N₄O₂", "(NH₄)₂SO₄", "CuSO4·5H2O", "CuSO₄·5H₂O", "CuSO4 . 5 H2O",
    "CuSO4 · 5 H2O", "SO₄²⁻", "[Fe(CN)6]4-", "NH4+", "  H2O  ", "(C2H4)n", "Fe³⁺",
]


@pytest.mark.parametrize("text", _IDEMPOTENCE_CORPUS)
def test_normalizer_is_idempotent_and_whitespace_free(text):
    once = normalize_formula_text(text)
    assert normalize_formula_text(once) == once
    assert not any(ch.isspace() for ch in once)


@pytest.mark.parametrize("text", _WS_REFUSED + ["SO4 2-", "[Fe(CN)6] 4-"])
def test_normalizer_refuses_rather_than_merging(text):
    with pytest.raises(FormulaSyntaxError):
        normalize_formula_text(text)


# == F-1: a malformed SMILES bracket atom is typed invalid input, never a bare ValueError ======================
_BAD_BRACKETS = ["[³]", "C[²H]", "[¹²C]", "[CH²]", "[Fe+²]"]


# Pre-fix: parse_smiles raised a bare ValueError (int('³')), not SmilesError -> FAILS on the old code.
@pytest.mark.parametrize("text", _BAD_BRACKETS)
def test_superscript_digit_in_bracket_atom_is_a_smiles_error(text):
    with pytest.raises(SmilesError):
        parse_smiles(text)


# Pre-fix: the ValueError escaped resolve_identity on every surface below -> FAILS on the old code.
@pytest.mark.parametrize("text", _BAD_BRACKETS)
@pytest.mark.parametrize("kind", [InputKind.AUTO, InputKind.SMILES])
def test_bad_bracket_is_invalid_input_through_the_resolver(text, kind):
    with pytest.raises(IdentityParseError):
        resolve_identity(text, kind)


def test_bad_bracket_inline_smiles_prefix_is_invalid_input():
    with pytest.raises(IdentityParseError):
        resolve_identity("smiles:[³]", InputKind.AUTO)


# Pre-fix: exit 70 (ERROR_INTERNAL) -> FAILS on the old code.
@pytest.mark.parametrize("text", ["[³]", "C[²H]", "[¹²C]"])
def test_cli_plan_bad_bracket_exits_2_not_70(text, capsys):
    from smartchem.cli import main

    assert main(["plan", text]) == 2
    assert "ERROR_INTERNAL" not in capsys.readouterr().err


# The fix narrows NOTHING else: a decimal (Unicode Nd) isotope that int() genuinely reads keeps parsing
# exactly as before (pre-fix: passed; still passes).
def test_decimal_unicode_isotope_still_parses():
    assert dict(parse_smiles("[１３CH4]").formula) == {"C": 1, "H": 4}


# == F-3 (adjudicated): the declared polyatomic-ion convention, pinned so a change is a visible decision =======
# Pre-fix: passes (no rule change -- this is a pin, not a fix).  Single-element bodies stay refused
# (test_formula_expr.py::test_P0B_single_element_bare_sign_ion_is_ambiguous).
@pytest.mark.parametrize("text,comp,charge", [
    ("HZn3+", {"H": 1, "Zn": 3}, 1),     # the fuzzer's R2 spelling: count reading BY CONVENTION, not a +3 ion
    ("NH4+", {"N": 1, "H": 4}, 1),
    ("NO3-", {"N": 1, "O": 3}, -1),
    ("VO2+", {"V": 1, "O": 2}, 1),
])
def test_multi_element_one_digit_bare_sign_is_the_declared_count_convention(text, comp, charge):
    expr = parse_formula_expr(text)
    assert dict(expr.to_formula().counts) == comp
    assert expr.charge == charge
    assert any("bare charge sign read as" in note for note in expr.notes)   # the reading is disclosed, not silent


def test_single_element_bare_sign_stays_ambiguous_under_the_convention():
    with pytest.raises(AmbiguousChargeError):
        parse_formula_expr("Zn3+")


# == F-4: a non-decimal digit is never a SMILES ring label ====================================================
# Pre-fix (ebee000): every row parsed as a ring molecule -> FAILS on the old code.
@pytest.mark.parametrize("text", ["S²N²", "C¹CC¹", "C%¹⁰CC%¹⁰", "C%1aCC%1a"])
def test_non_decimal_ring_label_is_a_smiles_error(text):
    with pytest.raises(SmilesError):
        parse_smiles(text)


# 'S²N²' is refused on every surface: SMILES now declines it, and the formula contract reads a superscript run as
# a CHARGE ('S^2N^2' -- a caret charge with no sign), so there is no reading left.  Pre-fix: AUTO silently
# returned the SMILES ring {H1 N1 S1} -> FAILS on the old code.
@pytest.mark.parametrize("kind", [InputKind.AUTO, InputKind.SMILES, InputKind.FORMULA])
def test_superscript_pair_s2n2_is_typed_invalid_input(kind):
    with pytest.raises(IdentityParseError):
        resolve_identity("S²N²", kind)


def test_superscript_pair_s2n2_is_not_an_auto_ambiguity_either():
    from smartchem.identity_parse import detect_auto_ambiguity

    assert detect_auto_ambiguity("S²N²") is None   # no reading survives, so there is nothing to choose between


# Pre-fix: plan resolved the silent ring and exited 0 -> FAILS on the old code.
def test_cli_plan_s2n2_exits_2(capsys):
    from smartchem.cli import main

    assert main(["plan", "S²N²"]) == 2
    assert "ERROR_INTERNAL" not in capsys.readouterr().err


# The decimal ring labels are untouched (pre-fix: passed; still passes) -- including fullwidth, whose SMILES
# reading keeps plan's input-kind ambiguity flag alive rather than handing the formula reading C3 a silent win.
@pytest.mark.parametrize("text", ["C1CC1", "C%10CC%10", "C１CC１"])
def test_decimal_ring_labels_still_parse(text):
    assert dict(parse_smiles(text).formula) == {"C": 3, "H": 6}


def test_fullwidth_ring_smiles_stays_input_kind_ambiguous():
    from smartchem.identity_parse import detect_auto_ambiguity

    assert detect_auto_ambiguity("C１CC１") is not None


# ...and a genuine internal error is still not laundered into "invalid input" (no broad except was added).
def test_resolver_does_not_swallow_a_genuine_internal_error(monkeypatch):
    import smartchem.smiles as smiles_mod

    def _boom(_text):
        raise RuntimeError("synthetic internal bug")

    monkeypatch.setattr(smiles_mod, "parse_smiles_features", _boom)
    with pytest.raises(RuntimeError, match="synthetic internal bug"):
        resolve_identity("CCO", InputKind.SMILES)
