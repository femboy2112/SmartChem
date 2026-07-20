"""
Machine-checked structural laws.

These are the tests that make the categorical framing load-bearing. Each one enforces a
property the original design *described* but never checked, and several of them make a
defect from the review unconstructible rather than merely absent.

The headline is ``TestConservationTheorem``: conservation is enforced once, on generators,
in the ``Reaction`` constructor. Everything else -- every composite, every tensor, every
chain hypothesis can build -- inherits it for free. That is the payoff for having a
category at all, and it is checked here against randomly generated chains rather than a
handful of examples.
"""
from __future__ import annotations

import itertools
import math
import random

import pytest
from hypothesis import given, settings, strategies as st

from smartchem.category import (
    UNIT,
    Bond,
    CompositionError,
    Config,
    ConservationError,
    Molecule,
    Reaction,
    braid,
    catalytic_cycle,
    conserves,
    identity,
    is_catalytic,
    tensor_obj,
)
# private, but the budget gate and the candidate enumeration are exactly what
# TestCanonicalShortcutIsExact exists to hold down.
from smartchem.category import (
    _MAX_CANONICAL_CANDIDATES,
    _canonical_cost,
    _sorting_permutations,
)

ELEMENTS = ["H", "C", "N", "O", "F", "Na", "Cl"]


# ==================================================================================
# strategies
# ==================================================================================
@st.composite
def molecules(draw, max_atoms: int = 3):
    n = draw(st.integers(min_value=1, max_value=max_atoms))
    atoms = tuple(draw(st.sampled_from(ELEMENTS)) for _ in range(n))
    # a random spanning-ish set of bonds, kept simple and always valid
    bonds = set()
    for i in range(1, n):
        if draw(st.booleans()):
            bonds.add(Bond(i - 1, i, draw(st.integers(min_value=1, max_value=3))))
    charge = draw(st.integers(min_value=-1, max_value=1))
    return Molecule(atoms, frozenset(bonds), charge)


@st.composite
def configs(draw, max_species: int = 3):
    k = draw(st.integers(min_value=0, max_value=max_species))
    return Config(tuple(draw(molecules()) for _ in range(k)))


@st.composite
def reactions(draw):
    """
    A random *valid* reaction.

    Built by rearranging bonds while holding the atom multiset fixed, which is the only
    way to produce a morphism at all -- the constructor rejects anything else.
    """
    src = draw(configs(max_species=2))
    atoms = [s for m in src.species for s in m.atoms]
    charge = src.charge
    if not atoms:
        return identity(src)
    # regroup the same atoms into a different partition of species
    split = draw(st.integers(min_value=1, max_value=len(atoms)))
    left, right = atoms[:split], atoms[split:]
    species = []
    if left:
        species.append(Molecule(tuple(left), frozenset(), charge))
    if right:
        species.append(Molecule(tuple(right), frozenset(), 0))
    return Reaction(src, Config(tuple(species)), "generated")


# ==================================================================================
# The theorem
# ==================================================================================
class TestConservationTheorem:
    """
    Conservation checked once on generators, inherited by every composite.

    This is the whole argument for the categorical layer. If these pass, a
    mass-violating reaction cannot be expressed in this system at all.
    """

    def test_violating_reaction_is_unconstructible(self):
        """Finding F1: Fe + O + Cl -> FeO silently dropped the chlorine."""
        reactants = Config.atoms("Fe", "O", "Cl")
        product = Config.of(Molecule.diatomic("Fe", "O"))
        with pytest.raises(ConservationError, match="mass not conserved"):
            Reaction(reactants, product)

    def test_charge_violation_is_unconstructible(self):
        with pytest.raises(ConservationError, match="charge not conserved"):
            Reaction(
                Config.of(Molecule.atom("Na")),
                Config.of(Molecule.atom("Na", charge=1)),
            )

    def test_nitrogen_fixation_case(self):
        """Finding F1, second case: Mo + N2 + H2 -> MoH2 lost the nitrogen."""
        src = Config.of(
            Molecule.atom("Mo"),
            Molecule.diatomic("N", "N", order=3),
            Molecule.diatomic("H", "H"),
        )
        bad = Config.of(Molecule(("Mo", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)})))
        with pytest.raises(ConservationError):
            Reaction(src, bad)

    @settings(max_examples=200, deadline=None)
    @given(reactions())
    def test_generator_conserves(self, f: Reaction):
        assert conserves(f)

    @settings(max_examples=200, deadline=None)
    @given(reactions(), reactions())
    def test_composition_inherits_conservation(self, f: Reaction, g: Reaction):
        """If f and g compose at all, the composite conserves without re-checking."""
        try:
            h = f.then(g)
        except CompositionError:
            return  # not composable; nothing to prove
        assert conserves(h)
        assert h.dom == f.dom and h.cod == g.cod

    @settings(max_examples=200, deadline=None)
    @given(reactions(), reactions())
    def test_tensor_inherits_conservation(self, f: Reaction, g: Reaction):
        """Tensor is always defined, and always conserves."""
        assert conserves(f.tensor(g))

    @settings(max_examples=100, deadline=None)
    @given(st.lists(reactions(), min_size=2, max_size=5))
    def test_long_chains_inherit_conservation(self, chain: list[Reaction]):
        composite = chain[0]
        for nxt in chain[1:]:
            try:
                composite = composite.then(nxt)
            except CompositionError:
                break
        assert conserves(composite)


# ==================================================================================
# Category laws
# ==================================================================================
class TestCategoryLaws:
    @settings(max_examples=200, deadline=None)
    @given(reactions())
    def test_left_identity(self, f: Reaction):
        assert identity(f.dom).then(f) == f

    @settings(max_examples=200, deadline=None)
    @given(reactions())
    def test_right_identity(self, f: Reaction):
        assert f.then(identity(f.cod)) == f

    @settings(max_examples=200, deadline=None)
    @given(reactions(), reactions(), reactions())
    def test_associativity(self, f: Reaction, g: Reaction, h: Reaction):
        try:
            left = f.then(g).then(h)
            right = f.then(g.then(h))
        except CompositionError:
            return
        assert left == right

    def test_composition_rejects_mismatch(self):
        f = Reaction(Config.atoms("H", "H"), Config.of(Molecule.diatomic("H", "H")))
        g = Reaction(Config.atoms("O", "O"), Config.of(Molecule.diatomic("O", "O")))
        with pytest.raises(CompositionError, match="codomain"):
            f.then(g)


# ==================================================================================
# Symmetric monoidal structure
# ==================================================================================
class TestMonoidalLaws:
    @settings(max_examples=200, deadline=None)
    @given(configs())
    def test_unit_laws(self, a: Config):
        assert tensor_obj(UNIT, a) == a
        assert tensor_obj(a, UNIT) == a

    @settings(max_examples=200, deadline=None)
    @given(configs(), configs(), configs())
    def test_tensor_associative(self, a: Config, b: Config, c: Config):
        assert tensor_obj(tensor_obj(a, b), c) == tensor_obj(a, tensor_obj(b, c))

    @settings(max_examples=200, deadline=None)
    @given(configs(), configs())
    def test_symmetry(self, a: Config, b: Config):
        """A (x) B == B (x) A. Symmetric on the nose, because Config canonicalises."""
        assert tensor_obj(a, b) == tensor_obj(b, a)

    @settings(max_examples=100, deadline=None)
    @given(configs(), configs())
    def test_braid_is_well_typed(self, a: Config, b: Config):
        s = braid(a, b)
        assert s.dom == tensor_obj(a, b)
        assert s.cod == tensor_obj(b, a)

    @settings(max_examples=100, deadline=None)
    @given(reactions())
    def test_tensor_with_identity_preserves_shape(self, f: Reaction):
        idu = identity(UNIT)
        assert f.tensor(idu).dom == f.dom
        assert f.tensor(idu).cod == f.cod


# ==================================================================================
# Object structure -- why Na + Cl and NaCl are different objects
# ==================================================================================
class TestObjectStructure:
    def test_bonded_and_unbonded_are_distinct_objects(self):
        """
        The distinction that makes reactions non-trivial.

        Same atoms, same charge, same formula -- different objects, because one has a
        bond and the other does not. Without this every conserving reaction would be an
        endomorphism (finding F11).
        """
        separate = Config.atoms("Na", "Cl")
        bonded = Config.of(Molecule.diatomic("Na", "Cl"))
        assert separate.formula == bonded.formula
        assert separate.charge == bonded.charge
        assert separate != bonded

        rxn = Reaction(separate, bonded, "Na + Cl -> NaCl")
        assert conserves(rxn)
        assert rxn.dom != rxn.cod, "a real reaction, not an identity"

    def test_canonical_form_is_order_independent(self):
        """
        Deterministic equality. The legacy Species used a frozenset, whose iteration
        order varies with PYTHONHASHSEED.
        """
        a = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
        b = Molecule(("H", "O", "H"), frozenset({Bond(1, 0), Bond(1, 2)}))
        assert a.canonical() == b.canonical()
        assert Config.of(a) == Config.of(b)

    def test_config_ordering_is_deterministic(self):
        h, o = Molecule.atom("H"), Molecule.atom("O")
        assert Config.of(h, o) == Config.of(o, h)

    def test_degree_reports_used_valence(self):
        co2 = Molecule(("C", "O", "O"), frozenset({Bond(0, 1, 2), Bond(0, 2, 2)}))
        assert co2.degree(0) == 4
        assert co2.degree(1) == 2

    def test_connectivity(self):
        assert Molecule.diatomic("H", "H").is_connected()
        assert not Molecule(("H", "H"), frozenset()).is_connected()

    def test_large_molecule_refuses_rather_than_lies(self):
        # H12 costs 12! = 479_001_600 candidates -- every permutation sorts the symbols
        # when there is only one symbol, so the shortcut buys exactly nothing here. This
        # is the case the budget exists for.
        big = Molecule(tuple("H" * 12), frozenset())
        with pytest.raises(NotImplementedError, match="out of scope"):
            big.canonical()

    def test_reach_is_set_by_composition_not_by_atom_count(self):
        """
        The old cap refused at 9 atoms. It priced canonicalisation as n!, which it is
        not -- so it refused ethanol while accepting an octane fragment that costs 28x
        more. Reach follows the symbol multiplicities, not the atom count.
        """
        ethanol = ("C", "C", "O", "H", "H", "H", "H", "H", "H")   # 9 atoms
        octyl = tuple("C" * 8)                                     # 8 atoms
        assert _canonical_cost(ethanol) == 1_440
        assert _canonical_cost(octyl) == 40_320
        assert _canonical_cost(ethanol) < _canonical_cost(octyl)
        # and the bigger species is the one that is now affordable
        assert _canonical_cost(ethanol) <= _MAX_CANONICAL_CANDIDATES


class TestCanonicalShortcutIsExact:
    """
    The shortcut restricts the search from n! permutations to prod(m_i!). That is only
    admissible if it never changes the answer, so this compares it against the brute
    force it replaced -- on every labelling of small chains, and on seeded random graphs.

    A restriction of a search is exactly the kind of change that looks free and is not:
    if the argument about the lexicographic key were subtly wrong, every downstream
    equality in the category would silently drift. So the old loop is kept here, in the
    test, as the oracle.
    """

    @staticmethod
    def _brute_force(atoms, bonds):
        """The pre-shortcut loop, preserved verbatim so it cannot drift with the code."""
        best = None
        for perm in itertools.permutations(range(len(atoms))):
            symbols = tuple(x for _, x in sorted(zip(perm, atoms)))
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in bonds
            ))
            key = (symbols, edges)
            if best is None or key < best:
                best = key
        symbols, edges = best
        return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in edges))

    @pytest.mark.parametrize("n", [2, 3, 4, 5])
    def test_agrees_on_every_labelling_of_a_chain(self, n):
        bonds = frozenset(Bond(i, i + 1) for i in range(n - 1))
        for atoms in itertools.product("HCO", repeat=n):
            assert Molecule(atoms, bonds).canonical() == self._brute_force(atoms, bonds)

    def test_agrees_on_random_graphs(self):
        """Seeded, so any disagreement replays exactly rather than haunting CI."""
        rng = random.Random(20260720)
        for _ in range(400):
            n = rng.randrange(2, 8)
            atoms = tuple(rng.choice("HCON") for _ in range(n))
            bonds = set()
            for i in range(1, n):                      # spanning path: always connected
                bonds.add(Bond(rng.randrange(i), i, rng.choice([1, 1, 1, 2, 3])))
            for _ in range(rng.randrange(0, 3)):       # a few chords
                i, j = rng.sample(range(n), 2)
                bonds.add(Bond(i, j, rng.choice([1, 2])))
            bonds = frozenset(bonds)
            assert Molecule(atoms, bonds).canonical() == self._brute_force(atoms, bonds), (
                f"shortcut disagrees with brute force on {atoms} {sorted(bonds)}"
            )

    def test_the_candidate_count_is_what_is_actually_enumerated(self):
        """`_canonical_cost` is the budget gate, so it must not be an estimate."""
        for atoms in [("H", "H"), ("C", "H", "H", "O"), ("C", "C", "H", "H", "H")]:
            assert len(list(_sorting_permutations(atoms))) == _canonical_cost(atoms)

    def test_every_candidate_really_sorts_the_symbols(self):
        """The premise of the restriction: candidates all realise the minimal `symbols`."""
        atoms = ("O", "H", "C", "H", "C")
        target = tuple(sorted(atoms))
        for perm in _sorting_permutations(atoms):
            assert tuple(x for _, x in sorted(zip(perm, atoms))) == target

    def test_homonuclear_saves_nothing_and_says_so(self):
        """The boundary. One symbol means every permutation sorts it: no reduction."""
        assert _canonical_cost(tuple("C" * 7)) == math.factorial(7)


# ==================================================================================
# Catalysis as a decided property
# ==================================================================================
class TestCatalysis:
    """Finding F3: the legacy version printed the closing step and computed nothing."""

    def test_catalyst_regenerated_is_catalytic(self):
        mo = Molecule.atom("Mo")
        src = Config.of(mo, Molecule.diatomic("N", "N", order=3))
        cod = Config.of(mo, Molecule.atom("N"), Molecule.atom("N"))
        assert is_catalytic(Reaction(src, cod), mo)

    def test_catalyst_consumed_is_not_catalytic(self):
        mo = Molecule.atom("Mo")
        src = Config.of(mo, Molecule.atom("N"))
        cod = Config.of(Molecule.diatomic("Mo", "N"))
        assert not is_catalytic(Reaction(src, cod), mo)

    def test_cycle_returns_evidence_not_a_bool(self):
        """A cycle claim must hand back the composite morphism, so it can be re-checked."""
        mo = Molecule.atom("Mo")
        n2 = Molecule.diatomic("N", "N", order=3)
        bound = Molecule(("Mo", "N", "N"), frozenset({Bond(0, 1), Bond(1, 2)}))

        bind = Reaction(Config.of(mo, n2), Config.of(bound), "bind")
        release = Reaction(Config.of(bound), Config.of(mo, n2), "release")

        cycle = catalytic_cycle([bind, release], mo)
        assert cycle is not None
        assert isinstance(cycle, Reaction)
        assert is_catalytic(cycle, mo)
        assert conserves(cycle)

    def test_broken_chain_returns_none(self):
        """Steps that do not compose are a real gap, reported as None rather than True."""
        mo = Molecule.atom("Mo")
        bind = Reaction(
            Config.of(mo, Molecule.diatomic("N", "N", order=3)),
            Config.of(Molecule(("Mo", "N", "N"), frozenset({Bond(0, 1), Bond(1, 2)}))),
        )
        unrelated = Reaction(Config.atoms("H", "H"), Config.of(Molecule.diatomic("H", "H")))
        assert catalytic_cycle([bind, unrelated], mo) is None
