"""0.9.5 barrier amendment A8 = S17 -- front-door identity hardening (Wave C6 + C8-F3), each law pinned here.

Every item is a *silent identity hallucination* (a string read into a constitution it does not denote) or an untyped
crash of the one parser (``resolve_identity``).  Evidence: the Wave C6 report (findings F1, F2, F3, F5, F7, F8, F9,
F11; minimized repros ``f*_*.py``) and the Wave C8 report section C8-F3.  Each test's docstring states what the
pre-fix code (``fd12895``) did; every one of those FAILS there and passes here.

Accepted-set movement -- narrowing only; every spelling whose outcome MOVES is in this file:

=========================  ======================================  ============================================
spelling                   pre-fix (fd12895)                        post-fix
=========================  ======================================  ============================================
``Co`` ``Cs`` ``Sc``        SMILES methanol / methanethiol           SmilesError (aromatic atom not in a ring);
``Cc`` ``c`` ``o`` ``Cn``   ethane / methane / water / methylamine   AUTO falls to the formula grammar (``Co`` =
``OCc`` ``c1CCCCC1``        ethanol / cyclohexane                    cobalt, FORMULA layer) or refuses
``C1C[H]1`` ``C[H][H]``     C2H5 / CH5 keyed as ethane / methane     SmilesError (hydrogen is terminal, single)
``[O]#[H]`` ``C[H]C``       hydroxyl / ValueError (exit 70)          SmilesError
``C٦.5H12`` ``C６.５H12``   C6H60 (a hydrate reading)                FormulaSyntaxError (the decimal refusal)
``H٢.٥O`` ``CuSO٤.5H2O``    H2O5 / a hydrate                          FormulaSyntaxError (the decimal refusal)
``SO⁴2-`` ``C⁶0-``          SO charge -42 / C charge -60             AmbiguousChargeError
``C=#C`` ``CC=`` ``=C``     ethyne / ethane / methane                SmilesError (contradictory / dangling bond)
``C(=)C`` ``C=(C)C``        ethene / propene                         SmilesError
``C=1CCCC-1``              cyclopentane (the closing end won)       SmilesError (ring bond ends disagree)
``[O-+]`` ``[Fe+2+]``       neutral O / Fe charge +3                 SmilesError (one charge run)
``[ı]`` ``[ſ]`` ``[ſi]``    iodine / sulfur / silicon                SmilesError (non-ASCII element letter)
``c1cc[ſ]c1``              thiophene (a long-s ring sulfur)          SmilesError (non-ASCII element letter)
``H④O`` ``InChI=1S/C④H4``   bare ValueError (exit 70)                IdentityParseError (exit 2)
4,400-digit bracket runs   bare ValueError (int-string limit)       IdentityParseError
``/q+1/q+1`` ``/p+1/p+1``   charge +2 (summed)                       IdentityParseError (repeated layer)
``/q+1_0``                 charge +10 (PEP 515 grouping)            IdentityParseError
``InChI=garbage/CH4``      accepted (version unread)                IdentityParseError
``InChI=1S/CuO4S·H2O``     one species CuH2O5S                      IdentityParseError (not one Hill formula)
``WAtEr`` ``AsPIrIn``       registry water / aspirin (a case fold)   the formula grammar they spell (S17 law 9)
``acetic  acid`` (2 sp.)   unknown name                             acetic acid (the ONE fold)
=========================  ======================================  ============================================

Unchanged by design (each pinned below as a control): benzene / pyridine / furan / indole / naphthalene / phenol /
biphenyl keys, ``[H][H]`` / ``[HH]`` / ``[H+]`` / ``[2H]C``, ``C=1CCCC=1``, ``[Fe++]``, ``H٤O`` (= H4O), ``Fe³+``,
``InChI=1/CH4`` (non-standard), ``Water`` / ``ACETIC ACID``.

Law 8 (AUTO parity, C6-F7) is a DECLARED BOUNDARY, not a refusal: stock / helper-reagent strings keep the expert AUTO
precedence (``CO`` = methanol there).  Refusing would move the pinned route fixtures of
``tests/test_synthesize_provider.py`` (``--reagents O ...``, exit 0) and ``tests/test_v0_7_transport_algebra.py``
(``stock_materials=("CO", ...)``) and refuse ``O`` -- water's everyday SMILES -- as a reagent.  The boundary is
written into COMPATIBILITY §5 and ARCHITECTURE stage 1, pinned below.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from smartchem.category import Bond, Molecule
from smartchem.contracts import canonical_digest
from smartchem.formula_expr import AmbiguousChargeError, FormulaSyntaxError, parse_formula_expr
from smartchem.identity_parse import (
    IdentityParseError,
    InputKind,
    detect_auto_ambiguity,
    resolve_identity,
    resolve_target,
)
from smartchem.smiles import SmilesError, parse_smiles, resonance_canonical, resonance_identity

_ROOT = Path(__file__).resolve().parent.parent


def _counts(ident) -> dict:
    return dict(ident.formula.counts)


def _key(smiles: str) -> str:
    return resonance_identity(parse_smiles(smiles))


# =====================================================================================================================
# Law 1 (C8-F3): an aromatic (lowercase) atom must be a member of an aromatic ring
# =====================================================================================================================

_NOT_IN_AROMATIC_RING = [
    ("Co", "O"), ("Cs", "S"), ("Sc", "C"), ("Cc", "C"), ("c", "C"), ("o", "O"), ("OCc", "C"), ("Cn", "N"),
    ("Nc", "C"), ("c1CCCCC1", "C"), ("c-1c-c-c-c-c-1", "C"), ("C[nH]C", "N"),
]


@pytest.mark.parametrize("text, upper", _NOT_IN_AROMATIC_RING)
def test_aromatic_atom_outside_an_aromatic_ring_is_refused_naming_the_uppercase_form(text, upper):
    """Pre-fix: ACCEPTED as the aliphatic atom -- ``Co`` methanol, ``Cs``/``Sc`` methanethiol, ``Cc`` ethane, ``c``
    methane, ``o`` water, ``c1CCCCC1`` cyclohexane (the lowercase silently ignored)."""
    with pytest.raises(SmilesError, match=f"not a member of an aromatic ring.*write '{upper}'"):
        parse_smiles(text)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.SMILES)
    with pytest.raises(IdentityParseError):
        resolve_identity("smiles:" + text, InputKind.AUTO)


def test_auto_co_is_cobalt_and_stock_co_no_longer_puts_methanol_on_the_shelf():
    """Pre-fix: ``resolve_target('Co')`` (the AUTO read every stock / helper string takes) returned METHANOL, so a
    declared cobalt bottle grounded a methanol-consuming route (C8-F3b).  Now ``Co`` is the formula it spells (cobalt,
    composition only), a structure search refuses it, and ``plan`` sees one reading, not an ambiguity."""
    ident = resolve_identity("Co", InputKind.AUTO)
    assert ident.molecule is None and _counts(ident) == {"Co": 1}
    with pytest.raises(IdentityParseError, match="no perceived structure"):
        resolve_target("Co", InputKind.AUTO)
    assert detect_auto_ambiguity("Co") is None


def test_stock_co_is_refused_end_to_end():
    """Pre-fix: ``stock_materials=("Co", "acetic acid")`` turned NO_ROUTE_COMPLETE into ROUTES_FOUND via
    ``CH4O + C2H4O2 -> C3H6O2 + H2O`` (C8-F3b, verified).  Now the cobalt string is typed invalid input."""
    from smartchem.service import build_recompile_request, run_compilation

    resp = run_compilation(build_recompile_request("CC(=O)OC", commodities_enabled=False, helper_reagents=("water",),
                                                   stock_materials=("Co", "acetic acid")))
    assert resp.exit_code == 2 and not resp.ranked_route_dossiers


@pytest.mark.parametrize("aromatic, kekule", [
    ("c1ccccc1", "C1=CC=CC=C1"), ("n1ccccc1", "N1=CC=CC=C1"), ("o1cccc1", "O1C=CC=C1"),
    ("c1ccc2[nH]ccc2c1", "C1=CC=C2NC=CC2=C1"), ("c1ccc2ccccc2c1", "C1=CC=C2C=CC=CC2=C1"),
    ("c1ccccc1O", "OC1=CC=CC=C1"), ("c1ccccc1c1ccccc1", "C1=CC=C(C=C1)C1=CC=CC=C1"),
    ("c1ccccc1-c1ccccc1", "C1=CC=C(C=C1)C1=CC=CC=C1"),
])
def test_real_aromatic_spellings_keep_their_keys(aromatic, kekule):
    """The rule narrows only the lowercase-that-meant-nothing: each aromatic spelling still parses, to the SAME key as
    its uppercase Kekulé spelling (which never meets the new check)."""
    assert _key(aromatic) == _key(kekule)


# =====================================================================================================================
# Law 2 (C6-F2): hydrogen is a terminal, single-bonded atom
# =====================================================================================================================

@pytest.mark.parametrize("text", ["C1C[H]1", "O1C[H]1", "N1N[H]1", "C[H][H]", "[O]#[H]", "[H]=C", "C[H]C", "F[H]F",
                                  "[Na][H][Na]", "[HH2]", "C[H]([H])"])
def test_non_terminal_or_multiply_bonded_hydrogen_is_refused_at_the_parser(text):
    """Pre-fix: ``C1C[H]1`` (C2H5) shared ethane's key, ``C[H][H]`` (CH5) methane's, ``[O]#[H]`` read as hydroxyl, and
    ``C[H]C`` / ``F[H]F`` / ``[Na][H][Na]`` crashed ``structure_key`` with a bare ValueError."""
    with pytest.raises(SmilesError, match="hydrogen"):
        parse_smiles(text)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.SMILES)


@pytest.mark.parametrize("text, formula, charge", [
    ("[H][H]", {"H": 2}, 0), ("[HH]", {"H": 2}, 0), ("[H+]", {"H": 1}, 1), ("[H-]", {"H": 1}, -1),
    ("[2H]C", {"C": 1, "H": 4}, 0), ("[H]C([H])([H])[H]", {"C": 1, "H": 4}, 0), ("[H]O[H]", {"H": 2, "O": 1}, 0),
])
def test_terminal_hydrogen_spellings_still_parse(text, formula, charge):
    m = parse_smiles(text)
    assert m.formula == formula and m.charge == charge


def _raw(atoms, bonds):
    return Molecule(tuple(atoms), frozenset(Bond(i, j, o) for i, j, o in bonds))


# raw graphs no parser emits (a wire replay payload or fragment surgery can): C1C[H]1 = C2H5, C-H-H = CH5, O#H
_BRIDGED_C2H5 = _raw(["C", "C", "H", "H", "H", "H", "H"], [(0, 1, 1), (0, 2, 1), (1, 2, 1), (0, 3, 1), (0, 4, 1),
                                                          (1, 5, 1), (1, 6, 1)])
_CHAINED_CH5 = _raw(["C", "H", "H", "H", "H", "H"], [(0, 1, 1), (1, 2, 1), (0, 3, 1), (0, 4, 1), (0, 5, 1)])
_TRIPLE_OH = _raw(["O", "H"], [(0, 1, 3)])
_BRIDGE_ONLY = _raw(["C", "H", "C"] + ["H"] * 6, [(0, 1, 1), (1, 2, 1), (0, 3, 1), (0, 4, 1), (0, 5, 1), (2, 6, 1),
                                                  (2, 7, 1), (2, 8, 1)])


@pytest.mark.parametrize("graph, honest", [(_BRIDGED_C2H5, "CC"), (_CHAINED_CH5, "C"), (_TRIPLE_OH, "[OH]")])
def test_resonance_key_never_rewrites_hydrogens_so_distinct_formulas_keep_distinct_keys(graph, honest):
    """Pre-fix: ``resonance_canonical`` re-derived every H as terminal -- the bridged C2H5 keyed as ethane, the chained
    CH5 as methane, O#H as hydroxyl (same key, different formula / bond order).  Now such a graph keeps its literal
    identity: the formula survives the key, and it differs from the honest species'."""
    from smartchem.experiment.stock import structure_key

    assert resonance_canonical(graph).formula == graph.formula
    assert resonance_identity(graph) == canonical_digest(graph.canonical())
    assert structure_key(graph) != structure_key(parse_smiles(honest))


def test_bridging_hydrogen_graph_no_longer_crashes_the_key():
    """Pre-fix: a bridging H that was the only link between two heavy fragments made the rebuild raise a bare
    ``ValueError`` ('a Molecule must be one connected species') out of ``resonance_identity`` / ``structure_key``."""
    from smartchem.experiment.stock import structure_key

    assert resonance_identity(_BRIDGE_ONLY) == canonical_digest(_BRIDGE_ONLY.canonical())
    assert structure_key(_BRIDGE_ONLY).startswith("struct:")


def _o_xylene(doubles):
    """Hand-built o-xylene (ring C0..C5, methyls C6 on C0 and C7 on C1) with the given ring double bonds, every H an
    explicit terminal atom -- the fragment-surgery shape, which never meets the parser."""
    ring = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)]
    bonds = [(a, b, 2 if (a, b) in doubles else 1) for a, b in ring] + [(0, 6, 1), (1, 7, 1)]
    atoms = ["C"] * 8
    for heavy, n_h in ((2, 1), (3, 1), (4, 1), (5, 1), (6, 3), (7, 3)):
        for _ in range(n_h):
            atoms.append("H")
            bonds.append((heavy, len(atoms) - 1, 1))
    return _raw(atoms, bonds)


def test_terminal_hydrogen_graphs_still_take_the_resonance_path():
    """Control, discriminating: the two NON-isomorphic Kekulé forms of o-xylene have different literal digests, and the
    resonance key still unifies them with each other and with the parsed spelling -- the guard above fires only on a
    non-terminal / multiply bonded H, never on an ordinary explicit-H fragment."""
    form_a, form_b = _o_xylene({(0, 1), (2, 3), (4, 5)}), _o_xylene({(1, 2), (3, 4), (0, 5)})
    assert canonical_digest(form_a.canonical()) != canonical_digest(form_b.canonical())
    assert resonance_identity(form_a) == resonance_identity(form_b) == _key("Cc1ccccc1C")


# =====================================================================================================================
# Law 3 (C6-F3): every Unicode decimal digit is folded BEFORE the decimal-point / ion-ambiguity guards
# =====================================================================================================================

@pytest.mark.parametrize("text", ["C٦.5H12", "C６.５H12", "H٢.٥O", "CuSO٤.5H2O", "CuSO4.٥H2O", "C₁.٥H₂"])
@pytest.mark.parametrize("kind", [InputKind.FORMULA, InputKind.AUTO])
def test_unicode_digit_twin_of_a_decimal_is_the_decimal_refusal(text, kind):
    """Pre-fix: ACCEPTED -- ``C٦.5H12`` / ``C６.５H12`` as C6H60 and ``H٢.٥O`` as H2O5 (a hydrate reading), because the
    decimal guard looked at ASCII digits only while ``int()`` read every Nd digit."""
    with pytest.raises(FormulaSyntaxError, match="decimal point"):
        parse_formula_expr(text)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, kind)


@pytest.mark.parametrize("text", ["SO٤2-", "PO４3-"])
def test_unicode_digit_twin_of_an_ambiguous_ion_is_the_ambiguity_refusal(text):
    """Control (passes on fd12895 too -- the old ``isdigit()`` run in ``_extract_charge`` already admitted Nd digits):
    after the fold the guard sees ``SO42-`` itself, so the refusal must survive it."""
    with pytest.raises(AmbiguousChargeError):
        parse_formula_expr(text)


@pytest.mark.parametrize("text", ["SO⁴2-", "PO⁴3-", "Cr2O⁷2-", "C⁶0-"])
def test_superscript_charge_run_against_ascii_digits_is_ambiguous(text):
    """Pre-fix: ACCEPTED -- the runs merged into one magnitude: ``SO⁴2-`` as SO charge -42, ``C⁶0-`` as C charge -60."""
    with pytest.raises(AmbiguousChargeError, match="superscript"):
        parse_formula_expr(text)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.FORMULA)


@pytest.mark.parametrize("text, comp, charge", [
    ("H٤O", {"H": 4, "O": 1}, 0), ("C６H６", {"C": 6, "H": 6}, 0), ("Fe³+", {"Fe": 1}, 3), ("SO4²-", {"S": 1, "O": 4}, -2),
    ("SO₄²⁻", {"S": 1, "O": 4}, -2), ("CuSO4·5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0),
    ("CuSO٤·٥H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0),
])
def test_digit_twins_keep_their_ascii_reading(text, comp, charge):
    """Control: a digit twin reads exactly as its ASCII twin (accepted when that is accepted)."""
    expr = parse_formula_expr(text)
    assert dict(expr.to_formula().counts) == comp and expr.charge == charge


# =====================================================================================================================
# Law 4 (C6-F5): contradictory / dangling SMILES bond markers are refused
# =====================================================================================================================

@pytest.mark.parametrize("text", ["C=#C", "C#=C", "C=-C", "CC=", "C=", "=C", "C(=)C", "C=(C)C", "CC(C=)C",
                                  "C=1CCCC-1", "C#1CCCC=1", "C:1CCCC=1"])
def test_contradictory_or_dangling_bond_symbol_is_refused(text):
    """Pre-fix: ACCEPTED one way -- ``C=#C`` ethyne (last symbol won), ``CC=`` ethane (dangling dropped: a truncated
    ``CC=O``), ``C(=)C`` ethene, ``C=1CCCC-1`` cyclopentane (the closing end won over the opening)."""
    with pytest.raises(SmilesError, match="bond"):
        parse_smiles(text)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.SMILES)


@pytest.mark.parametrize("text, formula", [
    ("C=1CCCC=1", {"C": 5, "H": 8}), ("C=1CCCC1", {"C": 5, "H": 8}), ("C1CCCC=1", {"C": 5, "H": 8}),
    ("CC(=O)O", {"C": 2, "H": 4, "O": 2}), ("C/C=C/C", {"C": 4, "H": 8}), ("C(C)C", {"C": 3, "H": 8}),
])
def test_well_formed_bond_symbols_still_parse(text, formula):
    assert parse_smiles(text).formula == formula


# =====================================================================================================================
# Law 5 (C6-F8): opposite-sign / repeated charge runs and malformed InChI layers are refused
# =====================================================================================================================

@pytest.mark.parametrize("text", ["[O-+]", "[O+-]", "[Fe+2+]", "[O-2+]", "[OH-+]", "[O-2-]", "[Fe++-]"])
def test_second_charge_run_in_a_bracket_is_refused(text):
    """Pre-fix: the runs were SUMMED -- ``[O-+]`` a neutral O, ``[Fe+2+]`` +3, ``[O-2+]`` -1."""
    with pytest.raises(SmilesError, match="more than one charge"):
        parse_smiles(text)


@pytest.mark.parametrize("text, charge", [("[Fe++]", 2), ("[Fe+2]", 2), ("[O--]", -2), ("[O-2]", -2), ("[NH4+]", 1)])
def test_one_charge_run_still_parses(text, charge):
    assert parse_smiles(text).charge == charge


@pytest.mark.parametrize("text", [
    "InChI=1S/CH4/q+1/q+1", "InChI=1S/CH4/p+1/p+1", "InChI=1S/CH4/q+1_0", "InChI=1S/CH4/q+١",
    "InChI=garbage/CH4", "InChI=2S/CH4", "InChI=1S/CuO4S·H2O", "InChI=1S/C2H6 O", "InChI=1S/C2H6\tO",
    "InChI=1S/C２H6",
])
def test_malformed_inchi_layers_are_refused(text):
    """Pre-fix: ACCEPTED -- repeated ``/q`` / ``/p`` summed (+2), ``+1_0`` read as +10, the version token never read,
    and a middle dot / space / tab let a two-component InChI pass as one species (the refusal was ASCII-dot-only)."""
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.INCHI)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.AUTO)


@pytest.mark.parametrize("text, formula, charge", [
    ("InChI=1S/CH4/h1H4", {"C": 1, "H": 4}, 0), ("InChI=1S/H3N/h1H3/p+1", {"H": 4, "N": 1}, 1),
    ("InChI=1/CH4/h1H4", {"C": 1, "H": 4}, 0), ("InChI=1S/C2H4O2/c1-2(3)4/h1H3,(H,3,4)/p-1", {"C": 2, "H": 3, "O": 2}, -1),
])
def test_well_formed_inchi_still_resolves(text, formula, charge):
    ident = resolve_identity(text, InputKind.INCHI)
    assert _counts(ident) == formula and ident.formula.charge == charge


# =====================================================================================================================
# Law 6 (C6-F9): non-ASCII element letters are refused
# =====================================================================================================================

@pytest.mark.parametrize("text", ["[ı]", "[ſ]", "[ſi]", "[Cſ]", "[ıH]", "c1cc[ſ]c1", "[ſ]1cccc1"])
def test_non_ascii_element_letter_is_refused(text):
    """Pre-fix: ``[ı]`` (U+0131) parsed as iodine, ``[ſ]`` (U+017F) as sulfur, ``[ſi]`` as silicon, ``[ıH]`` as HI --
    ``str.upper()`` and ``capitalize()`` map those confusables onto real symbols -- and ``c1cc[ſ]c1`` parsed as
    THIOPHENE, a case law 1 cannot see (the long-s sulfur really is an aromatic ring member), so this check is not
    redundant with it.  (``[Cſ]`` was already refused -- the stray letter was left over -- and stays a guard on the
    second-letter check.)"""
    with pytest.raises(SmilesError):
        parse_smiles(text)
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.SMILES)


@pytest.mark.parametrize("text, formula", [("[I-]", {"I": 1}), ("[S]", {"S": 1}), ("[Si]", {"Si": 1}),
                                           ("[Cl-]", {"Cl": 1}), ("[Zn+2]", {"Zn": 1})])
def test_ascii_bracket_elements_still_parse(text, formula):
    assert parse_smiles(text).formula == formula


# =====================================================================================================================
# Law 7 (C6-F1, C8-F4): every front-door parse failure is typed -- IdentityParseError, CLI exit 2, never 70
# =====================================================================================================================

@pytest.mark.parametrize("text, kind", [
    ("H④O", InputKind.FORMULA), ("formula:H④O", InputKind.AUTO), ("H④O", InputKind.AUTO),
    ("Ca(OH)②", InputKind.FORMULA), ("CuSO4·⑤H2O", InputKind.FORMULA), ("C④C", InputKind.AUTO),
    ("InChI=1S/C④H4", InputKind.AUTO), ("InChI=1S/C²H4", InputKind.INCHI),
])
def test_non_decimal_digit_is_typed_invalid_input(text, kind):
    """Pre-fix: a bare ``ValueError: invalid literal for int()`` -- ``isdigit()`` admitted the glyph, ``int()`` did not."""
    with pytest.raises(IdentityParseError):
        resolve_identity(text, kind)


def test_non_decimal_digit_is_not_an_untyped_crash_in_the_ambiguity_detector():
    """Pre-fix: ``detect_auto_ambiguity('H④O')`` raised the same bare ValueError (it calls the formula grammar)."""
    assert detect_auto_ambiguity("H④O") is None


_HUGE = "1" * 4400


@pytest.mark.parametrize("text, kind", [
    ("[" + _HUGE + "C]", InputKind.SMILES), ("[C+" + _HUGE + "]", InputKind.SMILES),
    ("[CH" + _HUGE + "]", InputKind.SMILES), ("[C+" + _HUGE + "]", InputKind.AUTO),
    ("InChI=1S/C" + "9" * 4400 + "H4", InputKind.INCHI), ("InChI=1S/CH4/q+" + _HUGE, InputKind.INCHI),
])
def test_digit_run_past_the_int_limit_is_typed(text, kind):
    """Pre-fix: ``ValueError: Exceeds the limit (4300 digits) for integer string conversion`` escaped untyped from the
    bracket isotope / charge / H-count runs and the InChI formula layer.  (The ``/q`` row was already typed -- its
    ``int()`` sat inside a ``try`` -- and stays as the guard for the new regex in front of it.)"""
    with pytest.raises(IdentityParseError):
        resolve_identity(text, kind)


def test_recursion_error_from_a_front_door_walk_is_typed(monkeypatch):
    """Pre-fix: a ``RecursionError`` escaping a parser walk (the deep-branch canonicaliser path Wave C8 hit; S16 made
    that walk iterative) left ``resolve_identity`` untyped -> exit 70.  The resolver now folds it into a typed
    refusal, whatever walk overflowed."""
    import smartchem.smiles as smiles_mod

    def _deep(_text):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(smiles_mod, "parse_smiles_features", _deep)
    with pytest.raises(IdentityParseError, match="nests too deeply"):
        resolve_identity("CCO", InputKind.SMILES)


def test_a_genuine_internal_error_is_still_not_laundered(monkeypatch):
    """Control: only RecursionError joined the typed family -- an internal bug still propagates (P0-F discipline)."""
    import smartchem.smiles as smiles_mod

    def _boom(_text):
        raise RuntimeError("synthetic internal bug")

    monkeypatch.setattr(smiles_mod, "parse_smiles_features", _boom)
    with pytest.raises(RuntimeError, match="synthetic internal bug"):
        resolve_identity("CCO", InputKind.SMILES)


@pytest.mark.parametrize("argv", [["plan", "H④O"], ["plan", "--formula", "H④O"], ["plan", "C④C"],
                                  ["plan", "--inchi", "InChI=1S/C²H4"], ["plan", "smiles:C[H]C"],
                                  ["plan", "SO⁴2-"], ["plan", "smiles:Co"]])
def test_cli_plan_exits_2_not_70(argv, capsys):
    """Pre-fix: ``plan 'H④O'`` / ``--inchi 'InChI=1S/C²H4'`` / ``smiles:C[H]C`` exited 70 ERROR_INTERNAL; ``SO⁴2-`` and
    ``smiles:Co`` exited 0 with a hallucinated composition."""
    from smartchem.cli import main

    assert main(argv) == 2
    assert "ERROR_INTERNAL" not in capsys.readouterr().err


# =====================================================================================================================
# Law 8 (C6-F7): AUTO parity for stock / helper strings -- DECLARED boundary (see the module docstring for why)
# =====================================================================================================================

def test_expert_auto_precedence_is_a_declared_boundary_in_both_documents():
    """Pre-fix: the documents claimed 'AUTO never guesses' without saying that only the ``plan`` target asks.  Both now
    declare the expert-path precedence with the ``CO`` = methanol example."""
    compat = (_ROOT / "COMPATIBILITY.md").read_text(encoding="utf-8")
    arch = (_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "AUTO precedence on expert paths (declared)" in compat and "`CO` is methanol" in compat
    assert "stock_materials" in compat and "helper_reagents" in compat
    assert "Declared boundary:" in arch and "`CO` there is methanol" in arch


def test_the_declared_precedence_is_what_the_code_does():
    """The boundary is a description, not a wish: AUTO reads ``CO`` as the SMILES (methanol) while the detector -- which
    only ``plan`` consults -- knows it is ambiguous."""
    assert resolve_target("CO", InputKind.AUTO).formula == {"C": 1, "H": 4, "O": 1}
    assert detect_auto_ambiguity("CO") is not None


# =====================================================================================================================
# Law 9 (C6-F11): ONE name fold -- structure_by_name uses stock's folds; stream_disposition uses stock's prefixes
# =====================================================================================================================

@pytest.mark.parametrize("name", ["acetic  acid", "acetic\xa0acid", "acetic\tacid", "  acetic   acid "])
def test_structure_by_name_folds_whitespace_like_the_stock_layer(name):
    """Pre-fix: None -- the resolver kept its own fold (strip + casefold, no interior collapse) while
    ``stock.normalize_material_name`` called every one of these 'acetic acid'."""
    from smartchem.structure import structure_by_name

    assert structure_by_name(name).name == "acetic acid"


@pytest.mark.parametrize("name, expected", [("Water", "water"), ("ACETIC ACID", "acetic acid"), ("Aspirin", "aspirin"),
                                            ("water", "water")])
def test_case_only_agreement_still_resolves_a_non_formula_string(name, expected):
    from smartchem.structure import structure_by_name

    assert structure_by_name(name).name == expected


_FORMULA_CASE_VARIANTS = [("WAtEr", {"W": 1, "At": 1, "Er": 1}), ("AsPIrIn", {"As": 1, "P": 1, "Ir": 1, "In": 1}),
                          ("CaFFeINe", {"Ca": 1, "F": 1, "Fe": 1, "I": 1, "Ne": 1})]


@pytest.mark.parametrize("text, formula", _FORMULA_CASE_VARIANTS)
def test_a_formula_spelling_is_not_hijacked_by_a_case_folded_registry_name(text, formula):
    """Pre-fix: AUTO resolved ``WAtEr`` (W At Er) to registry WATER (H2O) and ``AsPIrIn`` to aspirin -- the resolver is
    asked FIRST and its casefold made a case-sensitive formula token a name.  Now a case-only match resolves only a
    string that does not itself read as a formula."""
    from smartchem.structure import structure_by_name

    assert structure_by_name(text) is None
    ident = resolve_identity(text, InputKind.AUTO)
    assert ident.molecule is None and _counts(ident) == formula


def _formula_case_variants(label: str) -> "set[str]":
    """Every case variant of ``label`` whose letter runs split into element symbols -- exactly the variants that can
    parse as a formula (any other case pattern has a token starting lowercase or an unknown symbol)."""
    from smartchem.decompiler import _FORMULA_SYMBOLS

    symbols = {s.casefold(): s for s in _FORMULA_SYMBOLS}
    variants = [""]
    i = 0
    while i < len(label):
        if not label[i].isalpha():
            variants = [v + label[i] for v in variants]
            i += 1
            continue
        j = i
        while j < len(label) and label[j].isalpha():
            j += 1
        run, spellings = label[i:j].casefold(), []

        def split(k, acc, run=run, spellings=spellings):
            if k == len(run):
                spellings.append(acc)
                return
            for width in (1, 2):
                if k + width <= len(run) and run[k:k + width] in symbols:
                    split(k + width, acc + symbols[run[k:k + width]])
        split(0, "")
        variants = [v + s for v in variants for s in spellings]
        i = j
    return set(variants)


def _reads_as_formula(text: str) -> bool:
    try:
        parse_formula_expr(text)
    except (FormulaSyntaxError, ValueError):
        return False
    return True


def test_no_registered_label_resolves_a_formula_spelling_through_the_case_fold():
    """The invariant the S18 case-fold law asks of every casefolded table: here it was FALSE (eight labels -- water,
    aspirin, caffeine, theine, propanone, carbolic / prussic / salicylic acid -- have formula-reading case variants,
    four of them two or more), so the lookup was fixed rather than the table pinned: no case variant of any label that
    reads as a formula resolves to a registered structure, unless it IS the label verbatim."""
    from smartchem.structure import registered_structures, structure_by_name

    offenders, readable = [], set()
    for structure in registered_structures():
        for label in structure.all_names:
            for variant in _formula_case_variants(label):
                if variant != label and _reads_as_formula(variant):
                    readable.add(label)
                    if structure_by_name(variant) is not None:
                        offenders.append((label, variant))
    assert not offenders, offenders[:10]
    assert {"water", "aspirin"} <= readable                          # the instrument sees the collisions it guards


def test_the_case_variant_instrument_discriminates():
    """Control for the instrument above: it finds both readings of ``co``, the three of ``tin``, one of ``hcl``."""
    def readings(text):
        return {tuple(sorted(parse_formula_expr(v).to_formula().counts))
                for v in _formula_case_variants(text) if _reads_as_formula(v)}

    assert len(readings("co")) == 2 and len(readings("tin")) == 3 and len(readings("hcl")) == 1


def test_stream_disposition_reads_the_structure_prefixes_from_stock(monkeypatch):
    """Pre-fix: ``stream_disposition`` kept private literal copies of stock's ``struct:`` / ``struct-asgiven:`` prefixes
    (equal only by coincidence), so moving the owner's constant would not move the subject check.  Discriminating:
    patch the OWNER and the subject check follows it."""
    import smartchem.experiment.stock as stock_mod
    from smartchem.stream_disposition import StreamSubject, SubjectKind

    sig = "0" * 64
    monkeypatch.setattr(stock_mod, "_STRUCT_PREFIX", "owner-moved:")
    StreamSubject(SubjectKind.BYPRODUCT, sig, None, None, "owner-moved:abc")      # accepted: the owner's prefix
    with pytest.raises(ValueError, match="species key"):
        StreamSubject(SubjectKind.BYPRODUCT, sig, None, None, "struct:abc")      # the stale literal is not the owner's


# =====================================================================================================================
# Law 10 (C6-F6): hypervalent vs charge-separated spellings are different keys -- a declared split
# =====================================================================================================================

@pytest.mark.parametrize("hypervalent, separated", [("CN(=O)=O", "C[N+](=O)[O-]"), ("CS(C)=O", "C[S+](C)[O-]")])
def test_hypervalent_and_charge_separated_spellings_are_split_as_declared(hypervalent, separated):
    """The behaviour the boundary describes (unchanged by S17): one species, two keys -- the false-BLOCKED direction."""
    assert _key(hypervalent) != _key(separated)
    assert parse_smiles(hypervalent).formula == parse_smiles(separated).formula


def test_the_split_is_declared_in_compatibility_section_5():
    """Pre-fix: COMPATIBILITY §5 named only merge-side limits; the nitro / sulfoxide SPLIT was undeclared (C6-F6)."""
    compat = (_ROOT / "COMPATIBILITY.md").read_text(encoding="utf-8")
    section5 = compat.split("## 5.", 1)[1].split("## 6.", 1)[0]
    assert "`CN(=O)=O` vs `C[N+](=O)[O-]`" in section5 and "two different species are never merged" in section5
