"""0.9.5 barrier A14 -- front-door Wave D fixes (hostile non-author review, findings F1 / F3 / F4 / F6 / F9 / InChI P3).

Each test's docstring states what the pre-fix code (``1fc9068``) did; every witness FAILS there and passes here.

Accepted-set movement (narrowing only; every spelling whose outcome MOVES is pinned in this file):

=============================  ==========================================  ==========================================
spelling                       pre-fix (1fc9068)                            post-fix
=============================  ==========================================  ==========================================
``[CH3]1[CH3]1``               SMILES, keyed as ethane                      SmilesError (ring closure onto a bonded
``[CH2]12[CH2][CH2]12``        SMILES, keyed as cyclopropane                pair); AUTO falls to the formula grammar
``[OH]1[OH]1``                 SMILES, keyed as H2O2                        (FORMULA layer, no structure) or refuses
``C1C1`` ``C12CC12``           SMILES, a C2H4 / C3H4 phantom
``C1=C1`` ``c1c1`` ``C=1C1``   bare ValueError (plan exit 70)               SmilesError / IdentityParseError (exit 2)
``C:C`` ``CC:CC``              SMILES ethene / 2-butene                     SmilesError (':' needs two aromatic ends)
``C:1CCCCC:1``                 SMILES cyclohexene                           SmilesError
``C1:C:C:C:C:C1``              SMILES benzene                               SmilesError (uppercase ends)
``c1ccccc1:c1ccccc1``          SMILES biphenyl                              SmilesError (':' on a bond in no ring)
``c1cc1:c1cc1``                SMILES triafulvalene (bridge read DOUBLE)    SmilesError (':' on a bond in no ring)
``plan --target-file`` ``CO``  STRUCTURAL_PLANNING (methanol, exit 0)       INPUT_KIND_AMBIGUOUS (exit 2, no search)
``synthesize --have <bound>``  human exit 70 (CanonicalBoundExceeded)       exit 2 (IdentityOutOfBounds)
``InChI=1/CH4/f/q+1``          CH4 charge +1 (sublayer /q read as main)     IdentityParseError (/f, /r refused)
=============================  ==========================================  ==========================================

Unchanged by design (controls below): ``C1CC1``, ``c1ccccc1``, ``C=1CCC1``, ``C1CCCC=1``, ``c1:c:c:c:c:c1`` (benzene's
key), ``c1ccccc1-c1ccccc1`` and the implicit-bond ``c1ccccc1c1ccccc1`` (biphenyl), ring-label reuse, a fused and a
bridged bicycle, and standard InChI with /q and /p.
"""
from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

import smartchem.category as cat
from smartchem.category import Molecule
from smartchem.identity_parse import (
    IdentityParseError,
    InputKind,
    detect_auto_ambiguity,
    detect_target_file_ambiguity,
    resolve_identity,
    resolve_target,
)
from smartchem.smiles import SmilesError, _Atom, _build_molecule, parse_smiles, resonance_identity

NEO2 = "C(C(C)(C)C)(C(C)(C)C)(C(C)(C)C)C(C)(C)C"   # over-bound once the S16 node ceiling is lowered to 5


def _cli(argv):
    from smartchem import cli

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue() + err.getvalue()


class _NoSearch:
    """A ``run_compilation`` stand-in that records every call -- a refusal must come BEFORE any search runs."""

    def __init__(self):
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        return None


# =====================================================================================================================
# F1 (P0): a ring closure onto an already-bonded pair is refused, typed, naming the duplicate
# =====================================================================================================================

F1_WITNESSES = [
    # (spelling, ring label, the pair it re-bonds, what the pre-fix parse silently keyed it as)
    ("[CH3]1[CH3]1", "1", (0, 1), "CC"),
    ("[CH2]12[CH2][CH2]12", "2", (0, 2), "C1CC1"),
    ("[OH]1[OH]1", "1", (0, 1), "OO"),
    ("C1C1", "1", (0, 1), None),            # a C2H4 that is neither ethene nor ethane
    ("C12CC12", "2", (0, 2), None),
    ("OC1C1O", "1", (1, 2), None),
    ("N1N1", "1", (0, 1), None),
    ("C12C1C2", "1", (0, 1), None),
    ("C1C2C12", "2", (1, 2), None),
]


@pytest.mark.parametrize("smiles, label, pair, _collides_with", F1_WITNESSES)
def test_a_ring_closure_onto_a_bonded_pair_is_refused_naming_it(smiles, label, pair, _collides_with):
    """Pre-fix: each parsed -- the chain bond and the ring bond both reached the hydrogen fill (H counted from the doubled
    degree) and only then did the Molecule frozenset fold the two equal records into one bond."""
    with pytest.raises(SmilesError) as info:
        parse_smiles(smiles)
    message = str(info.value)
    assert f"ring-closure bond {label!r}" in message and "already bonded" in message
    assert f"atoms #{pair[0]} and #{pair[1]}" in message


@pytest.mark.parametrize("smiles, _label, _pair, collides_with", F1_WITNESSES)
def test_no_duplicate_bond_spelling_perceives_a_structure_on_any_kind(smiles, _label, _pair, collides_with):
    """Pre-fix: ``[CH3]1[CH3]1`` resolved (AUTO and SMILES) to a molecule whose key equalled ethane's, and likewise
    cyclopropane / H2O2.  Now SMILES refuses typed, and AUTO never perceives a structure: it either refuses or falls to
    the formula grammar (the declared AUTO order -- a FORMULA-layer composition, constitution NOT established)."""
    with pytest.raises(IdentityParseError, match="already bonded"):
        resolve_identity(smiles, InputKind.SMILES)
    try:
        auto = resolve_identity(smiles, InputKind.AUTO)
    except IdentityParseError:
        auto = None
    assert auto is None or (auto.molecule is None and auto.receipt.identity_layer == "FORMULA")
    with pytest.raises(IdentityParseError):
        resolve_target(smiles, InputKind.AUTO)           # the expert / helper-string door: no molecule, typed
    if collides_with is not None:
        honest_key = resonance_identity(parse_smiles(collides_with))
        assert auto is None or auto.molecule is None or resonance_identity(auto.molecule) != honest_key


# =====================================================================================================================
# F3 (P1): unequal duplicate orders were a bare ValueError -- now typed at every front-door entry
# =====================================================================================================================

F3_WITNESSES = ["C1=C1", "c1c1", "C=1C1"]


@pytest.mark.parametrize("smiles", F3_WITNESSES)
def test_unequal_duplicate_bonds_are_a_typed_smiles_error(smiles):
    """Pre-fix: ``Molecule.__post_init__``'s "multiple bond records for atom pair" ValueError escaped parse_smiles."""
    with pytest.raises(SmilesError, match="already bonded"):
        parse_smiles(smiles)


@pytest.mark.parametrize("smiles", F3_WITNESSES)
def test_unequal_duplicate_bonds_are_typed_on_every_front_door(smiles):
    """Pre-fix: resolve_identity (AUTO and SMILES) and detect_auto_ambiguity raised a bare ValueError, so ``plan`` --
    target or A12 helper-reagent loop -- escaped to exit 70 ERROR_INTERNAL."""
    from smartchem.plan import PlanStatus, plan

    for kind in (InputKind.AUTO, InputKind.SMILES):
        with pytest.raises(IdentityParseError):
            resolve_identity(smiles, kind)
    assert detect_auto_ambiguity(smiles) is None
    target = plan(smiles)
    assert target.status is PlanStatus.INVALID_INPUT and target.exit_code == 2
    assert "already bonded" in target.invalid_reason
    reagent = plan("smiles:CCOC(C)=O", helper_reagents=(smiles,))   # the refusal lands before any search
    assert reagent.exit_code == 2


@pytest.mark.parametrize("argv_tail", [[], ["--json"]])
@pytest.mark.parametrize("smiles", F3_WITNESSES)
def test_cli_plan_exits_2_on_a_duplicate_bond_target_and_reagent(smiles, argv_tail):
    """Pre-fix: ``plan C1=C1`` and ``plan X --reagents C1=C1`` exited 70 ERROR_INTERNAL."""
    for argv in (["plan", smiles, *argv_tail], ["plan", "smiles:CCOC(C)=O", "--reagents", smiles, *argv_tail]):
        code, text = _cli(argv)
        assert code == 2, (argv, code, text)
        assert "ERROR_INTERNAL" not in text


def test_build_molecule_types_a_molecule_construction_value_error():
    """The second suture, independent of the walk: a bond list carrying two records for one pair (a shape the walk now
    refuses, built by hand here) reaches ``_build_molecule``.  Pre-fix the Molecule's ValueError escaped untyped."""
    atoms = [_Atom("C", False, 0, None), _Atom("C", False, 0, None)]
    with pytest.raises(SmilesError, match="does not form a valid molecule graph"):
        _build_molecule(atoms, [[0, 1, 1], [0, 1, 2]], 0)


# =====================================================================================================================
# F9 (P2): an explicit ':' bond is legal only as a ring bond between two aromatic atoms
# =====================================================================================================================

@pytest.mark.parametrize("smiles, what", [
    ("C:C", "joins a non-aromatic"),
    ("CC:CC", "joins a non-aromatic"),
    ("C:1CCCCC:1", "joins a non-aromatic"),
    ("C1:C:C:C:C:C1", "joins a non-aromatic"),
    ("c1ccccc1:c1ccccc1", "is not in an aromatic ring"),
    ("c1cc1:c1cc1", "is not in an aromatic ring"),
])
def test_an_explicit_colon_bond_outside_an_aromatic_ring_is_refused(smiles, what):
    """Pre-fix: the Kekule pass chose an order -- ``C:C`` keyed as ethene, ``CC:CC`` as 2-butene, ``C:1CCCCC:1`` as
    cyclohexene, ``C1:C:C:C:C:C1`` as benzene; on a bridge ``c1cc1:c1cc1`` became a DOUBLE bond (triafulvalene)."""
    with pytest.raises(SmilesError, match="explicit aromatic bond ':'") as info:
        parse_smiles(smiles)
    assert what in str(info.value)
    with pytest.raises(IdentityParseError):
        resolve_identity(smiles, InputKind.SMILES)
    with pytest.raises(IdentityParseError):
        resolve_target(smiles, InputKind.AUTO)


def test_colon_inside_an_aromatic_ring_is_unchanged():
    """Control: every real ':' (both ends lowercase, on a ring edge) keys exactly as the implicit spelling."""
    benzene = resonance_identity(parse_smiles("c1ccccc1"))
    for spelling in ("c1:c:c:c:c:c1", "c:1ccccc:1", "c1ccc:cc1"):
        assert resonance_identity(parse_smiles(spelling)) == benzene
    assert resonance_identity(parse_smiles("c1:c:c:n:c:c1")) == resonance_identity(parse_smiles("c1ccncc1"))


def test_biphenyl_spellings_without_a_colon_bridge_are_unchanged():
    """Control: the explicit single bridge and the implicit one still read biphenyl (the implicit sibling of the ':'
    bridge is out of A14's scope and untouched)."""
    biphenyl = resonance_identity(parse_smiles("c1ccccc1-c1ccccc1"))
    assert resonance_identity(parse_smiles("c1ccccc1c1ccccc1")) == biphenyl
    assert parse_smiles("c1ccccc1-c1ccccc1").formula == {"C": 12, "H": 10}


# =====================================================================================================================
# honest ring-closure controls
# =====================================================================================================================

@pytest.mark.parametrize("smiles, formula", [
    ("C1CC1", {"C": 3, "H": 6}),
    ("c1ccccc1", {"C": 6, "H": 6}),
    ("C=1CCC1", {"C": 4, "H": 6}),
    ("C1CCCC=1", {"C": 5, "H": 8}),
    ("c1:c:c:c:c:c1", {"C": 6, "H": 6}),
    ("C1CC1C1CC1", {"C": 6, "H": 10}),               # a ring label reused after it closed
    ("C1CCC2CCCCC2C1", {"C": 10, "H": 18}),          # fused (decalin)
    ("C1CC2CCC1C2", {"C": 7, "H": 12}),              # bridged (norbornane)
    ("C1=CC1", {"C": 3, "H": 4}),
    ("C%10CC%10", {"C": 3, "H": 6}),
])
def test_honest_ring_closures_still_parse(smiles, formula):
    assert parse_smiles(smiles).formula == formula
    assert resolve_identity(smiles, InputKind.SMILES).molecule is not None


def test_a_self_ring_closure_keeps_its_own_refusal():
    """Control: ``CC11`` (a ring bond from an atom to itself) is still the self-bond refusal, not the duplicate one."""
    with pytest.raises(SmilesError, match="connects an atom to itself"):
        parse_smiles("CC11")


# =====================================================================================================================
# F4 (P1): plan --target-file gets the same AUTO-ambiguity refusal as a direct target
# =====================================================================================================================

@pytest.fixture
def no_search(monkeypatch):
    import smartchem.service as svc

    spy = _NoSearch()
    monkeypatch.setattr(svc, "run_compilation", spy)
    return spy


def test_plan_target_file_holding_an_ambiguous_string_is_refused_before_search(tmp_path, no_search):
    """Pre-fix: ``plan(<file 'CO'>, TARGET_FILE)`` -> STRUCTURAL_PLANNING with methanol (exit 0) while ``plan('CO')``
    -> INPUT_KIND_AMBIGUOUS."""
    from smartchem.plan import PlanStatus, plan

    target = tmp_path / "target.txt"
    target.write_text("CO\n", encoding="utf-8")
    result = plan(str(target), InputKind.TARGET_FILE)
    assert result.status is PlanStatus.INPUT_KIND_AMBIGUOUS and result.exit_code == 2
    assert result.ambiguity.target_input == "CO"
    assert set(result.ambiguity.kinds) == {InputKind.SMILES, InputKind.FORMULA}
    assert detect_target_file_ambiguity(str(target)) is not None
    assert no_search.calls == []


@pytest.mark.parametrize("flags", [["--target-file", "{f}"], ["{f}", "--input-kind", "target-file"]])
def test_cli_plan_target_file_ambiguity_exits_2_before_any_search(tmp_path, no_search, flags):
    """Pre-fix: ``plan --target-file <file 'CO'>`` exit 0 after a methanol structural search."""
    target = tmp_path / "target_CO.txt"
    target.write_text("CO", encoding="utf-8")
    code, text = _cli(["plan", *[a.format(f=target) for a in flags]])
    assert code == 2 and no_search.calls == []
    assert "INPUT-KIND AMBIGUOUS" in text and "smiles:CO" in text and "formula:CO" in text


def test_plan_target_file_with_an_explicit_kind_inside_still_plans(tmp_path, no_search):
    """Control: a prefixed file (``smiles:CO``) or a registered name is a decision -- planning proceeds."""
    from smartchem.plan import PlanStatus, plan

    for contents in ("smiles:CO", "water"):
        no_search.calls.clear()
        target = tmp_path / "t.txt"
        target.write_text(contents, encoding="utf-8")
        assert detect_target_file_ambiguity(str(target)) is None
        result = plan(str(target), InputKind.TARGET_FILE)
        assert result.status is PlanStatus.STRUCTURAL_PLANNING and len(no_search.calls) == 1


def test_plan_target_file_unreadable_stays_a_typed_invalid_input(tmp_path, no_search):
    """Control: a missing file is not an ambiguity -- resolution's own typed refusal answers (exit 2)."""
    from smartchem.plan import PlanStatus, plan

    missing = str(tmp_path / "absent.txt")
    assert detect_target_file_ambiguity(missing) is None
    result = plan(missing, InputKind.TARGET_FILE)
    assert result.status is PlanStatus.INVALID_INPUT and result.exit_code == 2 and no_search.calls == []


def test_target_file_ambiguity_uses_the_direct_target_detector():
    """One implementation: the file detector is the AUTO detector applied to the file's contents."""
    import inspect

    import smartchem.identity_parse as ip

    assert "detect_auto_ambiguity(contents)" in inspect.getsource(ip.detect_target_file_ambiguity)


# =====================================================================================================================
# F6 (P2): the synthesize human helper parser routes through the one front-door authority (exit 2, not 70)
# =====================================================================================================================

@pytest.mark.parametrize("flag", ["--reagents", "--have"])
def test_synthesize_human_over_bound_helper_string_exits_2(monkeypatch, flag):
    """Pre-fix: human ``synthesize CC(=O)OC --have <over-bound>`` exited 70 (CanonicalBoundExceeded passed the input
    stage's except) while ``--json`` exited 2."""
    from smartchem.experiment.cli import main as syn_main

    monkeypatch.setattr(cat, "_MAX_INDIVIDUALISATION_NODES", 5)
    Molecule.canonical.cache_clear()
    try:
        for argv in (["CC(=O)OC", flag, NEO2], ["CC(=O)OC", flag, NEO2, "--json"]):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = syn_main(argv)
            assert code == 2, (argv, code, err.getvalue())
            assert "ERROR_INTERNAL" not in err.getvalue()
    finally:
        Molecule.canonical.cache_clear()


def test_synthesize_helper_parser_is_the_front_door_resolution():
    """``_parse`` IS ``resolve_target`` on AUTO: the same molecule for a name, a SMILES and both prefixes; and the same
    typed refusal for an unknown name and a formula-only string."""
    from smartchem.experiment.cli import _parse

    for text in ("water", "O", "smiles:CO", "name:water", "CC(=O)OC(=O)C"):
        assert _parse(text) == resolve_target(text, InputKind.AUTO)
    for text in ("name:no-such-chemical", "formula:CO", "C1=C1", "C:C"):
        with pytest.raises(IdentityParseError):
            _parse(text)


# =====================================================================================================================
# InChI P3: the /f (fixed-H) and /r (reconnected) sublayers are refused
# =====================================================================================================================

@pytest.mark.parametrize("inchi, layer", [
    ("InChI=1/CH4/f/q+1", "/f"),
    ("InChI=1S/CH4/r/q+1", "/r"),
    ("InChI=1/C2H4O2/c1-2(3)4/h1H3,(H,3,4)/f/h3H", "/f"),
    ("InChI=1/CH5N/c1-2/h2H2,1H3/p+1/fCH6N/h2H3/q+1", "/f"),
])
def test_inchi_fixed_h_and_reconnected_sublayers_are_refused(inchi, layer):
    """Pre-fix: the flat layer list read a /q written after /f or /r as the MAIN charge (``InChI=1/CH4/f/q+1`` -> CH4
    charge +1)."""
    for text, kind in ((inchi, InputKind.INCHI), (inchi, InputKind.AUTO), ("inchi:" + inchi, InputKind.AUTO)):
        with pytest.raises(IdentityParseError, match="sublayer") as info:
            resolve_identity(text, kind)
        assert layer in str(info.value)


@pytest.mark.parametrize("inchi, counts, charge", [
    ("InChI=1S/CH4/h1H4", {"C": 1, "H": 4}, 0),
    ("InChI=1S/H3N/h1H3/p+1", {"H": 4, "N": 1}, 1),
    ("InChI=1S/C2H3O2/c1-2(3)4/h1H3/q-1", {"C": 2, "H": 3, "O": 2}, -1),
    ("InChI=1/CH4", {"C": 1, "H": 4}, 0),
])
def test_standard_inchi_charge_layers_are_unchanged(inchi, counts, charge):
    """Control: the main-layer /q and /p are consumed exactly as before."""
    formula = resolve_identity(inchi, InputKind.INCHI).formula
    assert dict(formula.counts) == counts and formula.charge == charge
