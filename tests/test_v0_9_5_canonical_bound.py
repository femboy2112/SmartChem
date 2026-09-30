"""0.9.5 S16 -- the canonical bound (barrier amendment, release-blocking).

``parse_smiles`` of 17-carbon tetra-tert-butylmethane did not finish in 40 s: the individualisation search pruned only
false twins, so symmetric SUBTREES were enumerated factorially while the leaf cap never fired.  It was a front-door hang
AND a verifier hole (every canonicalisation of a load ran uncharged).  The operation, and what each test here pins:

1. automorphism pruning, identity-PRESERVING  -- neo2 finishes in ~600 nodes; NEW == the verbatim OLD search;
2. node / atom-node ceilings, explicit stack  -- past them: ``CanonicalBoundExceeded`` (a ``NotImplementedError``);
                                                 deep graphs no longer die of RecursionError (Wave C6);
3. canonicalisation is budgeted work          -- ``canonical_work``: each distinct cached computation charged its
                                                 cold work ONCE per load (replayed through every work-transparent
                                                 cache, never recomputed in a load), refused STICKILY (never inside);
4. the enumeration-work floor                 -- no reagents no longer means W = 0 (Wave C3 C3-F1);
5. the typed front-door refusal               -- ``IdentityOutOfBounds`` (exit 2), never exit 70;
6. the Kekule placement DFS bound             -- dead ends count, bounded and charged (Wave C6 C6-F4);
7. the enumeration cache                      -- a size (not count) bound, and no store after a clear (C3-F3/F4).

Every test names the broken behaviour it fails on.  The whole-corpus byte-identity proof is the committed harness
``experiments/v0_9_5_canonical_differential.py``; the in-suite checks below are its seeded miniature.
"""
from __future__ import annotations

import copy
import io
import random
import signal
from contextlib import contextmanager, redirect_stderr, redirect_stdout

import pytest

import smartchem.category as cat
import smartchem.smiles as sm
from experiments.v0_9_5_canonical_differential import (
    _old_min_constitution_placement,
    acene,
    new_canonical_with_work,
    old_canonical,
    random_family,
    relabel,
    rings_corpus,
    two_orbit_cell,
)
from smartchem.category import Bond, CanonicalBoundExceeded, Molecule
from smartchem.contracts import canonical_digest
from smartchem.smiles import SmilesError, parse_smiles, resonance_canonical, resonance_identity
from smartchem.verification import (
    EnumerationCache,
    VerificationBudget,
    VerificationBudgetExceeded,
    VerificationContext,
    VerificationPolicy,
    WorkMeter,
    cached_enumerate,
    predicted_enumeration_work,
    retained_size,
    work_transparent_cache,
)

NEO2 = "C(C(C)(C)C)(C(C)(C)C)(C(C)(C)C)C(C)(C)C"          # tetra-tert-butylmethane, 17 C (53 atoms with H)


@contextmanager
def _hang_guard(seconds: int):
    """A hang is the broken behaviour here -- fail it instead of waiting forever (never a timing assertion)."""
    def _boom(*_a):
        raise AssertionError(f"still running after {seconds}s: the S16 hang is back")
    old = signal.signal(signal.SIGALRM, _boom)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _cold_canonical(m: Molecule):
    """``(form, work)`` computed cold (uncached), the work measured by the charge channel itself."""
    form, work, _individualised = new_canonical_with_work(m)
    return form, work


def _nodes(m: Molecule) -> int:
    count = [0]

    def tick():
        count[0] += 1
    cat._canonical_by_individualisation(m.atoms, m.bonds, on_node=tick)
    return count[0]


# ---------------------------------------------------------------------------------------------------------------------
# 1. automorphism pruning: bounded, and byte-identical to the unpruned search
# ---------------------------------------------------------------------------------------------------------------------

def test_neo2_parses_within_a_small_node_count():
    """Broken: false-twin-only pruning recursed 24+ levels (> 40 s) on neo2 -- the hang guard fires."""
    with _hang_guard(60):
        m = parse_smiles(NEO2)
        a = relabel(m, random.Random(1))
        form, work = _cold_canonical(a)
        nodes = _nodes(a)
    assert form == m.canonical()
    assert m.formula == {"C": 17, "H": 36}
    assert 0 < nodes <= 2_048                                 # measured ~600; the ceiling is far above
    assert work == nodes * len(a.atoms)                        # each node is charged the atoms it re-refines


def test_pruned_search_is_byte_identical_to_the_unpruned_one():
    """Broken: an orbit computed from automorphisms that do NOT fix the individualised prefix (or an unverified one),
    or a sibling pruned for being WL-equivalent rather than automorphic, prunes a live branch -> a different minimum
    -> a different canonical form (spot mutants: prefix test dropped moves 128 forms; first-child-only moves 8)."""
    rng = random.Random(95)
    corpus = [random_family(rng, kind) for kind in ("star", "ring", "dimer", "dendrimer") for _ in range(40)]
    corpus += [parse_smiles(s) for s in ("c1ccccc1", "C12C3C4C1C5C2C3C45", "C1C2CC3CC1CC(C2)C3", "C1CCCCC1",
                                         "CC(C)(C)C", "c1ccc2cc3ccccc3cc2c1", "Cc1c(C)c(C)c(C)c(C)c1C")]
    corpus += [m for label, m in rings_corpus() if int(label.rsplit("C", 1)[1]) <= 24]
    corpus += [two_orbit_cell()] * 20      # one WL cell, two orbits: the graph that catches over-pruning
    reached = 0
    for m in corpus:
        a = relabel(m, rng)
        if len(a.atoms) > 1 and cat._cost_of(cat._canonical_blocks(a.atoms, a.bonds)) > cat._MAX_CANONICAL_CANDIDATES:
            reached += 1
        new, _work = _cold_canonical(a)
        old = old_canonical(a)
        assert new == old and canonical_digest(new) == canonical_digest(old), f"canonical form moved for {m!r}"
    assert reached >= 100                                     # the corpus really exercises the individualisation path


def test_canonical_is_relabel_invariant_on_symmetric_families():
    """Broken: pruning that depends on the input labelling's orbit choice leaks into the answer."""
    rng = random.Random(7)
    for kind in ("star", "ring", "dendrimer"):
        for _ in range(15):
            m = random_family(rng, kind)
            forms = {_cold_canonical(relabel(m, rng))[0] for _ in range(4)}
            assert len(forms) == 1


def test_bond_orders_are_part_of_the_verified_automorphism():
    """Broken: an automorphism check that ignores bond ORDER would equate Kekule-distinct labellings and prune a
    live branch; the alternating ring's canonical form must still match the unpruned search exactly."""
    n = 10                                                    # 10! candidates: over budget -> individualisation
    bonds = frozenset(Bond(min(i, (i + 1) % n), max(i, (i + 1) % n), 2 if i % 2 == 0 else 1) for i in range(n))
    ring = Molecule(("C",) * n, bonds)
    assert cat._cost_of(cat._canonical_blocks(ring.atoms, ring.bonds)) > cat._MAX_CANONICAL_CANDIDATES
    rng = random.Random(4)
    for _ in range(5):
        a = relabel(ring, rng)
        assert _cold_canonical(a)[0] == old_canonical(a)


# ---------------------------------------------------------------------------------------------------------------------
# 2. the ceilings, and the explicit stack
# ---------------------------------------------------------------------------------------------------------------------

def test_node_ceiling_refuses_as_the_same_not_implemented_family(monkeypatch):
    """Broken: no node ceiling (only leaves were capped) -> the internal-node grind is unbounded."""
    monkeypatch.setattr(cat, "_MAX_INDIVIDUALISATION_NODES", 5)
    m = relabel(parse_smiles("C1C2CC3CC1CC(C2)C3"), random.Random(3))   # adamantane: ~56 nodes, over a cap of 5
    with pytest.raises(CanonicalBoundExceeded, match="5 search nodes") as info:
        Molecule.canonical.__wrapped__(m)
    assert isinstance(info.value, NotImplementedError)       # every existing `except NotImplementedError` still holds
    resonance_canonical.cache_clear()
    Molecule.canonical.cache_clear()
    try:
        assert resonance_identity(m).startswith("asgiven:")  # the literal-key fallback keeps working
    finally:
        resonance_canonical.cache_clear()
        Molecule.canonical.cache_clear()


def test_atom_node_ceiling_refuses_a_large_repetitive_graph(monkeypatch):
    """Broken: a node ceiling alone -- [CH5000] is 5,000 nodes (under it) and 610 s, since every node re-refines the
    whole graph; nodes x atoms is what bounds the time."""
    monkeypatch.setattr(cat, "_MAX_INDIVIDUALISATION_ATOM_NODES", 10_000)
    star = Molecule(("C",) + ("H",) * 400, frozenset(Bond(0, i, 1) for i in range(1, 401)))
    with pytest.raises(CanonicalBoundExceeded, match="atom-refinements"):
        Molecule.canonical.__wrapped__(star)


def test_a_deep_individualisation_no_longer_hits_the_recursion_limit():
    """Broken: the recursive walk -- one Python frame per individualisation -- died with RecursionError near depth
    1,000 ([CH1000], an 8-character input; C*1000), an exit-70 crash instead of an answer or a typed refusal."""
    with _hang_guard(120):
        m = parse_smiles("[CH1100]")                          # 1,100 nodes deep, 1.2M atom-refinements: in bounds
    assert m.formula == {"C": 1, "H": 1100}


def test_ceilings_are_far_above_every_measured_molecule():
    """Broken: a ceiling tighter than chemistry (a false refusal) -- neo2, coronene, C80 rings stay well under."""
    worst_nodes = worst_atom_nodes = 0
    molecules = [parse_smiles(s) for s in (NEO2, "c1cc2ccc3ccc4ccc5ccc6ccc1c7c2c3c4c5c67",
                                           "CC(C)(C)c1cc(C(C)(C)C)cc(C(C)(C)C)c1")]
    molecules += [m for label, m in rings_corpus() if label.endswith(("C80", "C79"))]
    for m in molecules:
        a = relabel(m, random.Random(5))
        nodes = _nodes(a)
        worst_nodes = max(worst_nodes, nodes)
        worst_atom_nodes = max(worst_atom_nodes, nodes * len(a.atoms))
    assert worst_nodes * 8 <= cat._MAX_INDIVIDUALISATION_NODES
    assert worst_atom_nodes * 8 <= cat._MAX_INDIVIDUALISATION_ATOM_NODES


# ---------------------------------------------------------------------------------------------------------------------
# 3. canonicalisation is budgeted verification work -- deterministic, hit or miss, sticky, never swallowed
# ---------------------------------------------------------------------------------------------------------------------

def _charged(fn, *args) -> int:
    context = VerificationContext(VerificationPolicy(budget=VerificationBudget.unlimited()))
    with context.activate():
        fn(*args)
    return context.meter.consumed("canonical_work")


def test_canonical_charges_the_same_work_on_a_hit_and_on_a_miss():
    """Broken: a bare lru_cache charges the miss and not the hit -> the budget depends on what is warm."""
    m = relabel(parse_smiles("C1C2CC3CC1CC(C2)C3"), random.Random(11))
    Molecule.canonical.cache_clear()
    miss = _charged(Molecule.canonical, m)
    hit = _charged(Molecule.canonical, m)
    Molecule.canonical.cache_clear()
    again = _charged(Molecule.canonical, m)
    assert miss == hit == again == _cold_canonical(m)[1] > 0
    info = Molecule.canonical.cache_info()                    # the lru_cache surface callers read is preserved
    assert (info.maxsize, info.currsize) == (8192, 1) and info.hits == 0 and info.misses == 1


def test_a_node_is_charged_once_per_load_and_never_recomputed_in_it():
    """Broken (every-call charging): each of the thousands of hits an honest load makes costs the full cold price --
    the honest re-execution maximum reached 1.77e9 units.  Broken (no per-load memo): a process-LRU eviction mid-load
    buys a recomputation.  Law: a distinct node costs its cold work once per load, and is computed at most once."""
    m = relabel(parse_smiles("C1C2CC3CC1CC(C2)C3"), random.Random(12))
    Molecule.canonical.cache_clear()
    context = VerificationContext(VerificationPolicy(budget=VerificationBudget.unlimited()))
    with context.activate():
        first = m.canonical()
        once = context.meter.consumed("canonical_work")
        assert m.canonical() == first
        Molecule.canonical.cache_clear()                     # the process LRU forgets it mid-load ...
        assert m.canonical() == first
        assert context.meter.consumed("canonical_work") == once == _cold_canonical(m)[1]
        assert Molecule.canonical.cache_info().misses == 0   # ... and the load still never recomputes it


def test_resonance_canonical_replays_the_work_of_its_placement_search():
    """Broken: resonance_canonical as a bare lru_cache -> a hit skips every canonical() beneath it uncharged."""
    m = relabel(parse_smiles("c1ccc2ccccc2c1"), random.Random(2))
    resonance_canonical.cache_clear()
    Molecule.canonical.cache_clear()
    miss = _charged(resonance_canonical, m)
    hit = _charged(resonance_canonical, m)
    assert miss == hit > 0


def test_enumeration_cache_replays_the_canonical_work_of_its_enumeration():
    """Broken: an enumeration-cache hit skips the fragment canonicalisations the miss paid for."""
    from smartchem.algebra_profiles import resolve_algebra_profile

    registry = resolve_algebra_profile("legacy-capped-v1")
    target = parse_smiles("CC(=O)OC")
    reagents = (parse_smiles("O"),)
    Molecule.canonical.cache_clear()
    resonance_canonical.cache_clear()
    miss = _charged(lambda: cached_enumerate(registry, target, reagents, budget=4))
    hit = _charged(lambda: cached_enumerate(registry, target, reagents, budget=4))
    assert miss == hit > 0


def test_canonical_overflow_is_recorded_never_raised_inside_and_refused_stickily():
    """Broken: raising from inside canonical() -- where `requirements._resolved_name_key` swallows ValueErrors (and
    memoises the swallow) and the reaction-type oracle demotes on any exception -- turns exhaustion into an answer."""
    meter = WorkMeter(VerificationBudget(canonical_work=5))
    meter.charge_canonical(10)                                # over the limit: recorded, not raised
    assert meter.exhausted and meter.consumed("canonical_work") == 10
    with pytest.raises(VerificationBudgetExceeded, match="canonical_work consumed 10 > limit 5"):
        meter.charge("dossiers")                              # the next CHECKED charge refuses
    with pytest.raises(VerificationBudgetExceeded):
        meter.check_item("steps_per_dossier", 1)             # ... and every one after it
    with pytest.raises(ValueError, match="deferred counter"):
        meter.charge("canonical_work", 1)                     # one semantics per counter

    context = VerificationContext(VerificationPolicy(budget=VerificationBudget(canonical_work=1)))
    with pytest.raises(VerificationBudgetExceeded) as info:
        with context.activate():
            try:
                relabel(parse_smiles("C1C2CC3CC1CC(C2)C3"), random.Random(9)).canonical()
                raise ValueError("a handler inside the load that swallows / replaces errors")
            except ValueError:
                pass
    assert info.value.counter == "canonical_work"            # refused at the end of the load all the same


def test_exhaustion_inside_a_swallowing_cache_does_not_poison_it():
    """Broken: a budget refusal thrown from inside canonical() under `requirements._resolved_name_key` (``except
    (ValueError, NotImplementedError): return None``, lru-cached) would leave the whole process believing the name no
    longer resolves -- a verdict change for every later compile, from one refused load."""
    import smartchem.capability.requirements as req_mod

    req_mod._resolved_name_key.cache_clear()
    Molecule.canonical.cache_clear()
    resonance_canonical.cache_clear()
    context = VerificationContext(VerificationPolicy(budget=VerificationBudget(canonical_work=1)))
    inside = "unset"
    try:
        with pytest.raises(VerificationBudgetExceeded):
            with context.activate():
                inside = req_mod._resolved_name_key("acetic acid")    # its canonicalisations blow a budget of 1
        assert inside is not None                                    # ... but it answered, and cached, the truth
        req_mod._resolved_name_key.cache_clear()
        assert inside == req_mod._resolved_name_key("acetic acid")
    finally:
        req_mod._resolved_name_key.cache_clear()


@pytest.fixture(scope="module")
def methyl_acetate():
    from smartchem.service import build_recompile_request, response_to_payload, run_compilation

    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"))
    return resp, response_to_payload(resp)


def test_tiny_canonical_budget_refuses_the_methyl_acetate_load(methyl_acetate):
    """Broken: canonicalisation uncharged -> the load is accepted whatever canonical_work allows."""
    from smartchem.service import load_response

    _resp, thick = methyl_acetate
    with pytest.raises(VerificationBudgetExceeded) as info:
        load_response(copy.deepcopy(thick), VerificationPolicy(budget=VerificationBudget(canonical_work=64)))
    assert info.value.counter == "canonical_work" and info.value.limit == 64


def _clear_every_cache_above_canonical() -> None:
    import smartchem.capability.requirements as req_mod
    import smartchem.experiment.kinetics as kin_mod
    import smartchem.experiment.stock as stock_mod
    from smartchem.verification import ENUMERATION_CACHE

    for fn in (Molecule.canonical, resonance_canonical, stock_mod._structure_key, req_mod._resolved_name_key,
               kin_mod._side_key_from_smiles):
        fn.cache_clear()
    ENUMERATION_CACHE.clear()


def test_profile_load_receipt_is_the_same_cold_warm_and_after_a_clear(methyl_acetate):
    """Broken: any cache above canonical() left a bare lru_cache (stock._structure_key, requirements._resolved_name_key,
    kinetics._side_key_from_smiles -- measured: +26,652 / +44,376 units cold vs warm on profile loads), or a charge
    that depends on process state -> the receipt, and a near-limit verdict, depend on what an earlier load left."""
    from smartchem.service import load_response
    from smartchem.verification import ENUMERATION_CACHE

    _resp, thick = methyl_acetate
    _clear_every_cache_above_canonical()
    cold = load_response(copy.deepcopy(thick)).receipt.work
    warm = load_response(copy.deepcopy(thick)).receipt.work
    ENUMERATION_CACHE.clear()
    after_clear = load_response(copy.deepcopy(thick)).receipt.work
    assert cold == warm == after_clear and cold.canonical_work > 0


def test_load_canonical_work_is_charged_and_far_under_the_default(methyl_acetate):
    """Broken: canonical work not on the receipt, or a default a routine load comes near (a false refusal)."""
    from smartchem.service import load_response

    _resp, thick = methyl_acetate
    first = load_response(copy.deepcopy(thick)).receipt.work
    second = load_response(copy.deepcopy(thick)).receipt.work
    assert first == second and first.canonical_work > 0
    assert first.canonical_work * 64 <= VerificationBudget().canonical_work


# ---------------------------------------------------------------------------------------------------------------------
# 4. the enumeration-work floor (Wave C4 conjecture 3, confirmed end to end by Wave C3 C3-F1)
# ---------------------------------------------------------------------------------------------------------------------

def test_enumeration_work_is_never_zero_without_reagents():
    """Broken: E = |bonds| x sum(reagent bonds) = 0 with no reagents, yet a reagentless provider (Diels-Alder)
    enumerates matches over the target alone -> uncharged work (C3-F1: a 16-ring chain loaded in 9.2 s for W = 0)."""
    ma, water = parse_smiles("CC(=O)OC"), parse_smiles("O")
    assert predicted_enumeration_work(ma, ()) == (10, 100)
    assert predicted_enumeration_work(ma, (water,)) == (20, 200)            # honest values with reagents unchanged
    assert predicted_enumeration_work(ma, (Molecule.atom("Na"),)) == (10, 100)   # a bondless pool is no pool
    assert predicted_enumeration_work(Molecule.atom("Na"), ()) == (0, 0)    # nothing to cut or match
    rings = "".join(f"C{(k % 9) + 1}CC=CCC{(k % 9) + 1}" for k in range(16))
    assert predicted_enumeration_work(parse_smiles("C" + rings + "C"), ())[1] > VerificationBudget().work_per_target


# ---------------------------------------------------------------------------------------------------------------------
# 5. the typed front-door refusal
# ---------------------------------------------------------------------------------------------------------------------

def test_over_bound_input_is_a_typed_refusal_on_every_front_door(monkeypatch):
    """Broken: the canonicaliser's NotImplementedError escaped resolve_identity -> exit 70 ERROR_INTERNAL on
    recompile and plan (an internal error for what is a bound, not a bug)."""
    from smartchem import cli
    from smartchem.identity_parse import IdentityOutOfBounds, IdentityParseError, resolve_identity
    from smartchem.service import ResponseOutcome, build_recompile_request, run_compilation

    monkeypatch.setattr(cat, "_MAX_INDIVIDUALISATION_NODES", 5)
    Molecule.canonical.cache_clear()
    try:
        with pytest.raises(IdentityOutOfBounds, match="too symmetric to canonicalise") as info:
            resolve_identity(NEO2)
        assert isinstance(info.value, IdentityParseError)
        assert run_compilation(build_recompile_request(NEO2)).outcome is ResponseOutcome.INVALID_INPUT
        for argv in (["recompile", NEO2], ["recompile", NEO2, "--json"], ["plan", NEO2], ["plan", NEO2, "--json"],
                     ["recompile", "smiles:" + NEO2]):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv)
            assert code == 2, (argv, code, err.getvalue())
            assert "ERROR_INTERNAL" not in err.getvalue()
            assert "too symmetric to canonicalise" in out.getvalue() + err.getvalue()
    finally:
        Molecule.canonical.cache_clear()


def test_the_same_input_resolves_under_the_real_ceiling():
    """Broken: a refusal that fires for chemistry the pruned search handles (neo2 is ~600 nodes)."""
    from smartchem.identity_parse import resolve_identity

    with _hang_guard(60):
        resolved = resolve_identity(NEO2)
    assert resolved.molecule is not None and resolved.molecule.formula == {"C": 17, "H": 36}


# ---------------------------------------------------------------------------------------------------------------------
# 6. the Kekule placement DFS (Wave C6 C6-F4)
# ---------------------------------------------------------------------------------------------------------------------

def test_polyacene_l50_is_refused_in_bounded_time_on_the_placement_caps_road():
    """Broken: the placement DFS counted only COMPLETE placements -- L=50 (51 placements, under every cap) walked
    dead ends for 1,425 s.  Now its node bound refuses with the placement cap's own SmilesError."""
    with _hang_guard(120):
        with pytest.raises(SmilesError, match="placement search exceeded"):
            parse_smiles(acene(50))


def test_placement_bound_leaves_every_under_bound_acene_byte_identical(monkeypatch):
    """Broken: a bound (or a reordered walk) that changes the placement a parse picks for a molecule it still admits."""
    for length in range(2, 13):
        for seed in (1, 2):
            smiles = acene(length, seed)
            new = canonical_digest(parse_smiles(smiles))
            with monkeypatch.context() as patch:
                patch.setattr(sm, "_min_constitution_placement", _old_min_constitution_placement)
                old = canonical_digest(parse_smiles(smiles))
            assert new == old, (length, seed)


def test_placement_bound_falls_back_to_the_literal_key_on_the_identity_path(monkeypatch):
    """Broken: an over-bound placement search on the identity path crashes instead of taking the literal-key road
    the placement cap already takes (resonance_identity's SmilesError fallback)."""
    m = relabel(parse_smiles("C1=CC=C2C=CC=CC2=C1"), random.Random(6))
    monkeypatch.setattr(sm, "_MAX_PLACEMENT_DFS_NODES", 2)
    resonance_canonical.cache_clear()
    try:
        assert resonance_identity(m) == canonical_digest(m.canonical())
        with pytest.raises(SmilesError, match="exceeded 2 search nodes"):
            parse_smiles("C1=CC=C2C=CC=CC2=C1")
    finally:
        resonance_canonical.cache_clear()


def test_placement_dfs_nodes_are_charged_to_canonical_work(monkeypatch):
    """Broken: the placement DFS left out of canonical_work -- a load pays nothing for walking dead ends."""
    smiles = acene(10)
    Molecule.canonical.cache_clear()
    charged = _charged(parse_smiles, smiles)
    Molecule.canonical.cache_clear()
    monkeypatch.setattr(sm, "charge_canonical_work", lambda amount: None)   # smiles' own binding: the DFS only
    without_dfs = _charged(parse_smiles, smiles)
    assert charged > without_dfs > 0


# ---------------------------------------------------------------------------------------------------------------------
# 7. the caches: a size bound (C3-F3) and no store after a clear (C3-F4)
# ---------------------------------------------------------------------------------------------------------------------

def _molecule_transforms(k: int, atoms: int) -> tuple:
    chain = Molecule(("C",) * atoms, frozenset(Bond(i, i + 1, 1) for i in range(atoms - 1)))
    return tuple((f"t{i}", (chain,)) for i in range(k)), True


def test_enumeration_cache_bounds_retained_size_not_transform_count():
    """Broken: weight = transform count -- Diels-Alder transforms carry products by value (59 KB each at 24 rings),
    so 512 entries far under the count bound held ~0.37 GB."""
    value = _molecule_transforms(2, 50)
    assert retained_size(value[0]) == 50 + 49                 # one shared Molecule object, counted once
    cache = EnumerationCache(max_transforms=1_000, max_entries=100, max_entry_transforms=100,
                             max_retained_size=250, max_entry_size=120)
    cache.get_or_compute("a", lambda: value)
    cache.get_or_compute("b", lambda: _molecule_transforms(1, 60))            # 119 units
    assert cache.stats().retained_size == 99 + 119 and cache.stats().entries == 2
    cache.get_or_compute("c", lambda: _molecule_transforms(1, 55))            # 109: 327 > 250 -> evict "a"
    assert cache.stats().entries == 2 and cache.stats().retained_size == 119 + 109
    cache.get_or_compute("big", lambda: _molecule_transforms(1, 70))          # 139 > 120: returned, never retained
    assert cache.stats().entries == 2


def test_a_clear_during_an_inflight_enumeration_is_not_undone():
    """Broken: compute outside the lock, store after it with no generation check -> a value computed before a clear()
    (e.g. under a provider patch the clear was meant to flush) is stored after it and served next time."""
    cache = EnumerationCache()
    calls: list = []

    def compute():
        calls.append(1)
        cache.clear()                                         # a concurrent clear() lands mid-computation
        return (("stale",), True)
    cache.get_or_compute("k", compute)
    assert cache.stats().entries == 0
    cache.get_or_compute("k", lambda: (calls.append(2), (("fresh",), True))[1])
    assert calls == [1, 2]                                    # recomputed, not served stale


def test_a_clear_during_an_inflight_work_transparent_miss_is_not_undone():
    """Broken: the same race on the canonical / resonance caches -- a stale value stored after cache_clear()."""
    seen: list = []

    @work_transparent_cache(maxsize=8)
    def slow(x):
        seen.append(x)
        slow.cache_clear()
        return x * 2
    assert slow(3) == 6 and slow.cache_info().currsize == 0
    assert slow(3) == 6 and seen == [3, 3]
