"""0.9.5 A13 -- the canonicalisation amplifier bound (release-blocking).

Two front-door shapes made the compiler's WORK grow with something the string's LENGTH did not show:

* a bracket hydrogen count -- ``[CH1234567]`` (17 characters) held the parser past 60 s and ``[CH123456789]`` raised
  MemoryError under 1.5 GB, because every H became an atom before any canonicaliser ceiling ran;
* a long chain -- ``resolve_identity("C" * 1000)`` took 22-27 s and ``"C" * 4000`` over 90 s: Weisfeiler-Leman
  refinement (~O(n**2) on a hydrogenated chain) ran ahead of every ceiling and charge, the search charged a node its
  atom count however many rounds its refinement took, and a block-path candidate cost 1 unit whatever its size.

The operation, and what each test here pins:

1. a bracket H count is ONE digit (OpenSMILES), refused typed before anything is materialised;
2. an ATOM ceiling -- the parser counts the graph before building it, ``canonical()`` refuses before any work; both
   raise the canonicaliser's own ``CanonicalBoundExceeded`` (-> ``IdentityOutOfBounds``, INVALID_INPUT, exit 2), on the
   SMILES path, a built graph and a decoded payload;
3. canonicalisation is metered in PASSES over the graph (``atoms + 2 x bonds`` per refinement round and per block-path
   candidate), each charged BEFORE it runs, the call bounded at ``_MAX_CANONICAL_CALL_WORK`` -- refused with the work
   undone.

Every test names the broken behaviour it fails on.  Wall-time rates and the worst cases the bounds imply are measured
by the committed harness ``experiments/v0_9_5_amplifier_bound.py``; the maxima the ceilings are sized from by
``experiments/v0_9_5_canonical_differential.py``.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import signal
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

import smartchem.category as cat
import smartchem.smiles as sm
from smartchem.category import Bond, CanonicalBoundExceeded, Molecule
from smartchem.identity_parse import IdentityOutOfBounds, IdentityParseError, InputKind, resolve_identity
from smartchem.smiles import SmilesError, parse_smiles
from smartchem.verification import VerificationBudget, _recording_canonical_work

NEO2 = "C(C(C)(C)C)(C(C)(C)C)(C(C)(C)C)C(C)(C)C"


@contextmanager
def _within(seconds: int, what: str):
    """The A13 broken behaviour is a GRIND: fail it at a generous explicit bound instead of waiting it out."""
    def _boom(*_a):
        raise AssertionError(f"{what} still running after {seconds}s: the A13 amplifier is back")
    old = signal.signal(signal.SIGALRM, _boom)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _star(hydrogens: int) -> Molecule:
    return Molecule(("C",) + ("H",) * hydrogens, frozenset(Bond(0, i, 1) for i in range(1, hydrogens + 1)))


def _chain(k: int) -> Molecule:
    """C_k H_(2k+2) built directly (the parse-free twin of ``"C" * k``)."""
    atoms, bonds = ["C"] * k, [Bond(i, i + 1, 1) for i in range(k - 1)]
    for c in range(k):
        for _ in range(3 if c in (0, k - 1) else 2):
            atoms.append("H")
            bonds.append(Bond(c, len(atoms) - 1, 1))
    return Molecule(tuple(atoms), frozenset(bonds))


def _cold(m: Molecule) -> tuple:
    """``(canonical form, work charged)`` of the live body, uncached, the work read off the charge channel."""
    with _recording_canonical_work() as frame:
        form = Molecule.canonical.__wrapped__(m)
    return form, frame.total


def _passes(m: Molecule) -> int:
    return len(m.atoms) + 2 * len(m.bonds)


@contextmanager
def _counting_sorted():
    """Counts every ``sorted`` call made by smartchem.category (a module global shadowing the builtin): each refinement
    ROUND sorts every atom's neighbour list, so this is how a test sees whether a round actually RAN."""
    calls = [0]
    real = sorted

    def counting(*a, **k):
        calls[0] += 1
        return real(*a, **k)
    cat.sorted = counting
    try:
        yield calls
    finally:
        del cat.sorted


# ---------------------------------------------------------------------------------------------------------------------
# 1. a bracket hydrogen count is one digit
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["[CH10]", "[NH44+]", "[CH00]", "[CH1234567]", "[CH123456789]", "C[CH12]C"])
def test_a_bracket_hydrogen_count_is_one_digit(text):
    """Broken: every H of a bracket count became an atom before any ceiling -- ``[CH10]`` read as CH10, ``[CH1234567]``
    held the parser past 60 s, ``[CH123456789]`` MemoryError.  Now a typed refusal, before any fill."""
    with _within(10, f"parse {text}"):
        with pytest.raises(SmilesError, match="hydrogen count"):
            parse_smiles(text)
        with pytest.raises(IdentityParseError):
            resolve_identity("smiles:" + text)


@pytest.mark.parametrize("text, formula", [("[CH4]", {"C": 1, "H": 4}), ("[NH4+]", {"N": 1, "H": 4}),
                                           ("[NH3+]C", {"N": 1, "C": 1, "H": 6}), ("[CH0]", {"C": 1}),
                                           ("[OH2]", {"O": 1, "H": 2}),
                                           ("[13CH3]C", {"C": 2, "H": 6}), ("[C@@H](F)(Cl)Br", {"C": 1, "H": 1, "F": 1,
                                                                                                "Cl": 1, "Br": 1})])
def test_one_digit_bracket_hydrogen_counts_are_unchanged(text, formula):
    """Broken: an over-eager cap that also refuses (or re-reads) the one-digit counts real chemistry spells."""
    assert parse_smiles(text).formula == formula


def test_the_hydrogen_cap_refuses_before_any_atom_is_materialised(monkeypatch):
    """Broken: a cap checked AFTER the fill -- the 10**8-atom list is built, then refused."""
    def _no_fill(*_a, **_k):
        raise AssertionError("_fill_hydrogens reached: the H count was materialised before the refusal")
    monkeypatch.setattr(sm, "_fill_hydrogens", _no_fill)
    with pytest.raises(SmilesError, match="9-digit hydrogen count"):
        parse_smiles("[CH123456789]")


def test_a_carried_amplifier_target_is_refused_on_load_not_ground():
    """Broken: the verifier re-derives a carried target through the same parser -- a payload naming
    ``smiles:[CH1234567]`` was a 60 s grind on load.  Now a typed refusal."""
    from smartchem.service import build_recompile_request, request_from_payload, request_to_payload

    payload = request_to_payload(build_recompile_request("smiles:CCO"))
    payload["target_input"] = "smiles:[CH1234567]"
    with _within(20, "the carried amplifier target"):
        with pytest.raises(ValueError):
            request_from_payload(payload)


# ---------------------------------------------------------------------------------------------------------------------
# 2. the atom ceiling: parser, built graph, decoded payload, CLI
# ---------------------------------------------------------------------------------------------------------------------

def test_the_parser_counts_the_graph_before_it_builds_it(monkeypatch):
    """Broken: no parser ceiling -- ``"C" * 100000`` materialises 300,002 atoms (and their Bonds) before the
    canonicaliser refuses them.  Now ``_fill_hydrogens`` refuses on the COUNT: not one Bond is constructed."""
    atoms, bonds = sm._parse_skeleton("C" * 400)                # 400 heavy atoms + 802 implicit H = 1,202 > 1,024
    built = [0]
    real_bond = sm.Bond

    def counting_bond(*a):
        built[0] += 1
        return real_bond(*a)
    monkeypatch.setattr(sm, "Bond", counting_bond)
    with pytest.raises(CanonicalBoundExceeded, match=r"1,202 atoms with its hydrogens, over the 1,024-atom ceiling"):
        sm._fill_hydrogens(atoms, bonds)
    assert built[0] == 0
    assert len(sm._fill_hydrogens(*sm._parse_skeleton("C" * 340))[0]) == 1_022   # under the ceiling: unchanged


def test_the_parser_ceiling_is_the_canonicaliser_ceiling(monkeypatch):
    """Broken: two constants that drift -- a parser admitting what canonical() refuses (or the reverse)."""
    monkeypatch.setattr(cat, "_MAX_CANONICAL_ATOMS", 10)
    with pytest.raises(CanonicalBoundExceeded, match="14 atoms with its hydrogens, over the 10-atom ceiling"):
        parse_smiles("CCCC")
    assert parse_smiles("CC").formula == {"C": 2, "H": 6}                    # 8 atoms: admitted


@pytest.mark.parametrize("text", ["C" * 400, "smiles:" + "C" * 400, "C" * 4000, "OC" + "C" * 600 + "O"])
def test_an_oversized_smiles_is_out_of_bounds_never_a_formula(text):
    """Broken: a parser ceiling raised as ``SmilesError`` lets AUTO fall through to the formula grammar, which reads
    ``"C" * 400`` as the composition C400 -- an identity for a string that IS SMILES, just too large.  The ceiling
    raises the canonicaliser's own refusal, which every front door files as IdentityOutOfBounds."""
    with pytest.raises(IdentityOutOfBounds, match="atom ceiling"):
        resolve_identity(text)


def test_canonical_refuses_over_the_atom_ceiling_before_any_work(monkeypatch):
    """Broken: canonical() with no atom ceiling -- the symbol sort, the factorial of the block sizes and a full
    Weisfeiler-Leman refinement run on a 100,001-atom graph before any other ceiling or charge."""
    def _no_work(*_a, **_k):
        raise AssertionError("canonicalisation work started on a graph over the atom ceiling")
    monkeypatch.setattr(cat, "_canonical_blocks", _no_work)
    monkeypatch.setattr(cat, "_refine_from", _no_work)
    for m in (_star(1_100), _star(100_000), _chain(400)):
        with _within(10, "the atom-ceiling refusal"):
            with _recording_canonical_work() as frame:
                with pytest.raises(CanonicalBoundExceeded, match=r"atoms is over the 1,024-atom ceiling") as info:
                    Molecule.canonical.__wrapped__(m)
        assert isinstance(info.value, NotImplementedError) and frame.total == 0
    with pytest.raises(CanonicalBoundExceeded, match="over the 1,024-atom ceiling"):
        cat._canonical_by_individualisation(_star(1_100).atoms, _star(1_100).bonds)   # the search's own door too


def test_a_graph_at_the_atom_ceiling_still_canonicalises():
    """Broken: a ceiling at or below what it claims to admit.  1,024 atoms -- the C-H1023 star, 1,022 nested
    individualisations, deeper than the interpreter's recursion limit (Wave C6's RecursionError) -- answers."""
    with _within(120, "the 1,024-atom star"):
        form, work = _cold(_star(1_023))
    assert form.formula == {"C": 1, "H": 1_023} and 0 < work <= cat._MAX_CANONICAL_CALL_WORK


def test_a_decoded_payload_molecule_over_the_ceiling_is_a_typed_refusal():
    """Broken: a decoded payload molecule of ~100k atoms fits the payload-node budget and reached a full refinement on
    load.  Re-forged by the keyless forger (every derived key and the whole-body digest recomputed), the load is
    refused -- typed (a ValueError naming the atom ceiling), never an untyped NotImplementedError."""
    from smartchem.service import build_recompile_request, load_response, response_to_payload, run_compilation

    spec = importlib.util.spec_from_file_location("_a13_loader_laws",
                                                  Path(__file__).with_name("test_v0_9_5_loader_laws.py"))
    laws = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_a13_loader_laws", laws)
    spec.loader.exec_module(laws)
    thick = response_to_payload(run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2,
                                                                        capability_profile="poor-man")))
    for hydrogens in (1_100, 20_000):
        forged = copy.deepcopy(thick)
        forged["ranked_route_dossiers"][0]["replay_payload"][0]["reactants"][0] = {
            "atoms": ["C"] + ["H"] * hydrogens, "bonds": [[0, i, 1] for i in range(1, hydrogens + 1)],
            "charge": 0, "state": ""}
        forged = laws._reforge(forged)
        with _within(60, "the decoded over-ceiling molecule"):
            with pytest.raises(ValueError, match="atom ceiling") as info:
                load_response(forged)
        assert not isinstance(info.value, NotImplementedError)


@pytest.mark.parametrize("argv", [["recompile", "C" * 400], ["recompile", "C" * 400, "--json"],
                                  ["recompile", "smiles:" + "C" * 4000], ["plan", "C" * 400],
                                  ["plan", "C" * 400, "--json"]])
def test_an_oversized_smiles_exits_2_on_the_cli(argv):
    """Broken: exit 70 (an internal error) or a 20+ s grind for what is a bound."""
    from smartchem import cli

    out, err = io.StringIO(), io.StringIO()
    with _within(60, "the CLI"):
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
    assert code == 2, (argv, code, err.getvalue()[-400:])
    assert "ERROR_INTERNAL" not in err.getvalue()
    assert "atom ceiling" in out.getvalue() + err.getvalue()


# ---------------------------------------------------------------------------------------------------------------------
# 3. the chain is bounded
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("length, seconds", [(1_000, 20), (4_000, 20), (100_000, 60)])
def test_a_long_chain_refuses_fast(length, seconds):
    """Broken: ``"C" * 1000`` took 22-27 s and ``"C" * 4000`` > 90 s in refinement before any ceiling; the generous
    bounds here are ~100x the measured refusal (0.01 s / 0.01 s / 0.5 s)."""
    with _within(seconds, f'resolve_identity("C" * {length})'):
        with pytest.raises(IdentityOutOfBounds, match="atom ceiling"):
            resolve_identity("C" * length)


def test_the_largest_admitted_chain_answers_within_the_call_ceiling():
    """Broken: an atom ceiling looser than the call ceiling can pay for -- ``"C" * 340`` (1,022 atoms) must answer."""
    with _within(120, '"C" * 340'):
        resolved = resolve_identity("C" * 340, InputKind.SMILES)
    assert resolved.molecule.formula == {"C": 340, "H": 682}


# ---------------------------------------------------------------------------------------------------------------------
# 4. the work unit, the per-call ceiling, and charge-before-work
# ---------------------------------------------------------------------------------------------------------------------

def test_every_charge_is_a_pass_over_the_graph():
    """Broken: a node priced at its atom count (S16), or a block-path candidate at 1 unit, whatever the graph -- the
    unit then runs ~1,000x slower per unit on a big molecule than a small one.  Now: a block-path call charges
    candidates x (atoms + 2 bonds), and every refinement charge is whole passes."""
    ethanol = parse_smiles("CCO")
    assert cat._cost_of(cat._canonical_blocks(ethanol.atoms, ethanol.bonds)) == 1_440       # the block path
    assert _cold(ethanol)[1] == 1_440 * _passes(ethanol)
    for m in (parse_smiles("C1C2CC3CC1CC(C2)C3"), parse_smiles(NEO2), _chain(60), _star(50)):
        form, work = _cold(m)
        assert work > 0 and work % _passes(m) == 0, m
        assert form == Molecule.canonical(m)


def test_metering_never_changes_a_colouring():
    """Broken: a meter that alters what refinement computes (the A13 claim is metering ONLY)."""
    for m in (_chain(30), _star(20), parse_smiles("c1ccc2ccccc2c1"), parse_smiles(NEO2)):
        seed = cat._partition_colours(cat._blocks(m.atoms), len(m.atoms))
        assert cat._refine_from(m.atoms, m.bonds, seed) == cat._refine_from(
            m.atoms, m.bonds, seed, cat._CanonicalMeter(charge=False))


def test_the_per_call_ceiling_refuses_on_both_branches(monkeypatch):
    """Broken: no per-call work ceiling -- one call's refinement (search included) or block loop is bounded only by the
    node / leaf ceilings, which say nothing about how long each node takes."""
    monkeypatch.setattr(cat, "_MAX_CANONICAL_CALL_WORK", 10_000)
    with pytest.raises(CanonicalBoundExceeded, match="10,000 units of work in one call"):
        Molecule.canonical.__wrapped__(_star(400))                       # the search
    with pytest.raises(CanonicalBoundExceeded, match="10,000 units of work in one call"):
        Molecule.canonical.__wrapped__(_chain(100))                      # refinement before any search node
    with pytest.raises(CanonicalBoundExceeded, match="10,000 units of work in one call"):
        Molecule.canonical.__wrapped__(parse_smiles("CCO"))             # the block path: 36,000 up front


def test_the_per_call_ceiling_is_a_typed_refusal_on_the_front_door(monkeypatch):
    """Broken: the call ceiling escaping as a bare NotImplementedError (exit 70)."""
    from smartchem import cli

    monkeypatch.setattr(cat, "_MAX_CANONICAL_CALL_WORK", 50_000)
    Molecule.canonical.cache_clear()
    try:
        with pytest.raises(IdentityOutOfBounds, match="units of work in one call"):
            resolve_identity(NEO2)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert cli.main(["recompile", NEO2]) == 2
    finally:
        Molecule.canonical.cache_clear()


def test_a_tiny_call_ceiling_refuses_before_the_work_runs(monkeypatch):
    """Broken (charge AFTER the work): the round runs, THEN the meter refuses -- the work a ceiling exists to prevent is
    done anyway.  With the ceiling at exactly one pass (the refinement setup), the first round is refused before a
    single neighbour list is sorted: the only sorts are the symbol sort, the symbol ranks and the seed."""
    m = _chain(340)                                                       # 1,022 atoms; one round sorts 1,022 lists
    monkeypatch.setattr(cat, "_MAX_CANONICAL_CALL_WORK", _passes(m))
    with _counting_sorted() as calls, _recording_canonical_work() as frame:
        with pytest.raises(CanonicalBoundExceeded, match="more asked"):
            Molecule.canonical.__wrapped__(m)
    assert calls[0] <= 3, calls[0]
    assert frame.total == _passes(m)                                     # the setup it did, charged; nothing more
    monkeypatch.setattr(cat, "_MAX_CANONICAL_CALL_WORK", 0)
    with _counting_sorted() as calls, _recording_canonical_work() as frame:
        with pytest.raises(CanonicalBoundExceeded):
            Molecule.canonical.__wrapped__(m)
    assert calls[0] <= 2 and frame.total == 0                             # not even the setup


def test_each_round_is_charged_before_it_runs():
    """Broken: charges booked after (or batched behind) the rounds they pay for.  Each charge reaches the load's meter
    while the sorts of the round it pays for have not happened yet."""
    m = _chain(40)
    events: list = []
    sorts = [0]
    real = sorted

    def counting(*a, **k):
        sorts[0] += 1
        return real(*a, **k)
    cat.sorted = counting
    real_charge = cat._charge_work
    try:
        cat._charge_work = lambda units: events.append((sorts[0], units))
        Molecule.canonical.__wrapped__(m)
    finally:
        cat._charge_work = real_charge
        del cat.sorted
    n = len(m.atoms)
    assert events and all(units == _passes(m) for _s, units in events)
    # a round sorts n neighbour lists + 1: consecutive round charges are never closer than that, and the FIRST charge
    # comes before any round's sorts (only the symbol sort and symbol ranks precede it)
    assert events[0][0] <= 2
    gaps = [b[0] - a[0] for a, b in zip(events, events[1:])]
    assert max(gaps) >= n                                                 # some round did run between two charges


ISOTOPIC, CHIRAL = "[13CH3]CCCCCCCC", "C[C@H](O)CCCCCCCC"


def test_the_isotope_search_and_configuration_wl_charge_their_refinement(monkeypatch):
    """Broken: the parser's own refinements -- the isotope-refined key's search (isotope-coloured atoms) and the
    configuration perception's Weisfeiler-Leman -- run on an uncharged meter (or none): bounded, but the load pays
    nothing for them."""
    seen: list = []
    live_search, live_wl = cat._canonical_by_individualisation, sm._wl_colours

    def search(atoms, bonds, on_node=None, meter=None):
        if any(":" in a for a in atoms):                                  # only the isotope key colours atoms
            seen.append(("isotope search", meter is not None and meter.charge))
        return live_search(atoms, bonds, on_node=on_node, meter=meter)

    def wl(atoms, bonds, meter=None):                                     # smiles' binding: perception only
        seen.append(("configuration wl", meter is not None and meter.charge))
        return live_wl(atoms, bonds, meter)
    monkeypatch.setattr(cat, "_canonical_by_individualisation", search)
    monkeypatch.setattr(sm, "_wl_colours", wl)
    sm.isotope_refined_key(ISOTOPIC)
    sm.configuration_key(CHIRAL)
    assert ("isotope search", True) in seen and ("configuration wl", True) in seen
    assert all(charged for _what, charged in seen), seen


def test_the_isotope_search_and_configuration_wl_are_bounded_per_call(monkeypatch):
    """Broken: those refinements bounded by nothing but the atom ceiling.  With every canonical() they need already
    cached, a tiny call ceiling reaches THEM -- and refuses."""
    sm.isotope_refined_key(ISOTOPIC)                                      # warm every canonical() underneath
    sm.configuration_key(CHIRAL)
    monkeypatch.setattr(cat, "_MAX_CANONICAL_CALL_WORK", 100)
    with pytest.raises(CanonicalBoundExceeded, match="units of work in one call"):
        sm.isotope_refined_key(ISOTOPIC)
    with pytest.raises(CanonicalBoundExceeded, match="units of work in one call"):
        sm.configuration_key(CHIRAL)


def test_the_default_load_budget_admits_the_honest_frozen_loads():
    """Broken: a default sized in the old unit -- every honest load's receipt grew ~30-50x in passes, so the S16
    default (2**25) would refuse honest payloads.  The v0.8 producer fixtures all load under the default."""
    import json

    from smartchem.service import load_response

    fixtures = Path(__file__).with_name("fixtures") / "v08"
    loaded = 0
    for name in ("response_isopentyl_acetate.json", "response_isopentyl_acetate_dag.json",
                 "response_stereo_isopentyl_acetate_smiles.json", "response_ethyl_acetate_smiles.json"):
        receipt = load_response(json.loads((fixtures / name).read_text())).receipt
        assert 0 < receipt.work.canonical_work * 4 <= VerificationBudget().canonical_work, name
        loaded += 1
    assert loaded == 4
