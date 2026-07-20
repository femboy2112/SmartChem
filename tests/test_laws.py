"""
Machine-checked structural laws.

These are the tests that make the categorical framing load-bearing. Each one enforces a
property the original design *described* but never checked, and several of them make a
defect from the review unconstructible rather than merely absent.

The headline is ``TestConservationTheorem``: conservation is enforced once, on generators,
in the ``Reaction`` constructor. Everything else -- every composite and every scheduled
product that the hypotheses build -- inherits it for free. That is the payoff for having a
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
    _blocks,
    _canonical_blocks,
    _canonical_cost,
    _cost_of,
    _refined_blocks,
    _sorting_permutations,
    _symbol_cost,
    _wl_colours,
)

ELEMENTS = ["H", "C", "N", "O", "F", "Na", "Cl"]


def _perms_within(blocks, n):
    """Every permutation that shuffles atoms only within the given classes."""
    targets, position = [], 0
    for block in blocks:
        targets.append(tuple(range(position, position + len(block))))
        position += len(block)
    for choice in itertools.product(*(itertools.permutations(b) for b in blocks)):
        perm = [0] * n
        for olds, news in zip(choice, targets):
            for old, new in zip(olds, news):
                perm[old] = new
        yield tuple(perm)


# ==================================================================================
# strategies
# ==================================================================================
@st.composite
def molecules(draw, max_atoms: int = 3):
    n = draw(st.integers(min_value=1, max_value=max_atoms))
    atoms = tuple(draw(st.sampled_from(ELEMENTS)) for _ in range(n))
    # one connected random path; a Molecule is one species, never a mixture
    bonds = set()
    for i in range(1, n):
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
        species.append(Molecule(
            tuple(left),
            frozenset(Bond(i - 1, i) for i in range(1, len(left))),
            charge,
        ))
    if right:
        species.append(Molecule(
            tuple(right),
            frozenset(Bond(i - 1, i) for i in range(1, len(right))),
            0,
        ))
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
    def test_scheduled_product_inherits_conservation(self, f: Reaction, g: Reaction):
        """The compatibility schedule is always defined and always conserves."""
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

    def test_an_elementary_endomorphism_is_not_silently_an_identity(self):
        a = Config.atoms("H")
        event = Reaction(a, a, "one period")
        assert event.steps == 1
        assert event != identity(a)

    def test_a_forged_path_is_rejected(self):
        h_free = Config.atoms("H", "H")
        h_bound = Config.of(Molecule.diatomic("H", "H"))
        n_free = Config.atoms("N", "N")
        n_bound = Config.of(Molecule.diatomic("N", "N", order=3))
        with pytest.raises(CompositionError, match="starts at"):
            Reaction(h_free, h_bound, path=((n_free, n_bound),))

    def test_a_discontinuous_path_is_rejected(self):
        free = Config.atoms("H", "H")
        bound = Config.of(Molecule.diatomic("H", "H"))
        with pytest.raises(CompositionError, match="starts at"):
            Reaction(free, free, path=((free, bound), (free, bound)))

    def test_generator_id_cannot_contradict_the_typed_word(self):
        free = Config.atoms("H", "H")
        bound = Config.of(Molecule.diatomic("H", "H"))
        with pytest.raises(ValueError, match="must match"):
            Reaction(
                free,
                bound,
                generator_id="channel-a",
                generator_word=((free, bound, "channel-b"),),
            )


# ==================================================================================
# Object commutative monoid and the compatibility scheduling operation
# ==================================================================================
class TestObjectProductAndScheduledProduct:
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

    def test_tensor_with_unit_preserves_a_composite_certificate(self):
        free = Config.atoms("H", "H")
        bound = Config.of(Molecule.diatomic("H", "H"))
        loop = Reaction(free, bound, "associate").then(
            Reaction(bound, free, "dissociate")
        )
        alongside_unit = loop.tensor(identity(UNIT))
        assert alongside_unit == loop
        assert alongside_unit.steps == 2

    def test_tensor_does_not_collapse_parallel_loops_to_identity(self):
        h_free = Config.atoms("H", "H")
        h_bound = Config.of(Molecule.diatomic("H", "H"))
        n_free = Config.atoms("N", "N")
        n_bound = Config.of(Molecule.diatomic("N", "N", order=3))
        h_loop = Reaction(h_free, h_bound).then(Reaction(h_bound, h_free))
        n_loop = Reaction(n_free, n_bound).then(Reaction(n_bound, n_free))
        combined = h_loop.tensor(n_loop)
        assert combined.steps == 4
        assert combined != identity(combined.dom)

    def test_generator_identity_is_structural_not_a_display_label(self):
        free = Config.atoms("H", "H")
        bound = Config.of(Molecule.diatomic("H", "H"))
        channel_a = Reaction(free, bound, "same display", generator_id="channel-a")
        channel_b = Reaction(free, bound, "same display", generator_id="channel-b")
        renamed_a = Reaction(free, bound, "renamed", generator_id="channel-a")
        assert channel_a != channel_b
        assert channel_a == renamed_a

    def test_scheduled_product_is_associative_and_unital(self):
        h0, h1 = Config.atoms("H", "H"), Config.of(Molecule.diatomic("H", "H"))
        n0 = Config.atoms("N", "N")
        n1 = Config.of(Molecule.diatomic("N", "N", order=3))
        o0, o1 = Config.atoms("O", "O"), Config.of(Molecule.diatomic("O", "O", order=2))
        f, g, h = Reaction(h0, h1), Reaction(n0, n1), Reaction(o0, o1)
        assert f.scheduled_product(identity(UNIT)) == f
        assert identity(UNIT).scheduled_product(f) == f
        assert (f.scheduled_product(g).scheduled_product(h)
                == f.scheduled_product(g.scheduled_product(h)))

    @pytest.mark.xfail(
        strict=True,
        reason="linear histories cannot quotient independent events by interchange",
    )
    def test_true_parallel_interchange_is_architecture_debt(self):
        h0, h1 = Config.atoms("H", "H"), Config.of(Molecule.diatomic("H", "H"))
        n0 = Config.atoms("N", "N")
        n1 = Config.of(Molecule.diatomic("N", "N", order=3))
        f, g = Reaction(h0, h1, generator_id="h+"), Reaction(h1, h0, generator_id="h-")
        k, ell = (Reaction(n0, n1, generator_id="n+"),
                  Reaction(n1, n0, generator_id="n-"))
        lhs = f.then(g).scheduled_product(k.then(ell))
        rhs = f.scheduled_product(k).then(g.scheduled_product(ell))
        assert lhs == rhs

    def test_duplicate_edge_records_are_rejected(self):
        with pytest.raises(ValueError, match="multiple bond records"):
            Molecule(("C", "C"), frozenset({Bond(0, 1, 1), Bond(0, 1, 2)}))


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
        with pytest.raises(ValueError, match="connected species"):
            Molecule(("H", "H"), frozenset())

    def test_large_molecule_refuses_rather_than_lies(self):
        # H12 costs 12! = 479_001_600 candidates -- every permutation sorts the symbols
        # when there is only one symbol, so the shortcut buys exactly nothing here. This
        # is the case the budget exists for.
        big = Molecule(
            tuple("H" * 12),
            frozenset(Bond(i, (i + 1) % 12) for i in range(12)),
        )
        with pytest.raises(NotImplementedError, match="out of scope"):
            big.canonical()

    def test_reach_is_set_by_composition_not_by_atom_count(self):
        """
        The original cap refused at 9 atoms, pricing canonicalisation as n!, which it is
        not -- so it refused ethanol while accepting an octane fragment costing 28x more.
        Reach follows the symbol multiplicities, not the atom count.
        """
        ethanol_atoms = ("C", "C", "O", "H", "H", "H", "H", "H", "H")   # 9 atoms
        ethanol_bonds = frozenset({
            Bond(0, 1), Bond(1, 2),                                     # C-C, C-O
            Bond(0, 3), Bond(0, 4), Bond(0, 5),                         # methyl
            Bond(1, 6), Bond(1, 7),                                     # methylene
            Bond(2, 8),                                                 # hydroxyl
        })
        octyl_atoms, octyl_bonds = tuple("C" * 8), frozenset()          # 8 atoms
        assert _canonical_cost(ethanol_atoms, ethanol_bonds) == 1_440
        assert _canonical_cost(octyl_atoms, octyl_bonds) == 40_320
        # the *bigger* species is the affordable one
        assert _canonical_cost(ethanol_atoms, ethanol_bonds) <= _MAX_CANONICAL_CANDIDATES

    def test_refinement_is_spent_only_where_it_buys_reach(self):
        """
        Refinement is reach, not speed. Spending it unconditionally was measured to make
        H2O, CO2 and CH2O ~3x slower while splitting nothing -- so it is gated on the
        plain restriction failing first.

        Ethanol is the witness on the cheap side: refinement WOULD cut it 1,440 -> 12,
        and deliberately is not asked to, because 1,440 is already affordable and the
        molecule already worked. Propane is the witness on the other: 241,920 is not
        affordable, so refinement runs and brings it to 2,880.
        """
        ethanol_atoms = ("C", "C", "O", "H", "H", "H", "H", "H", "H")
        ethanol_bonds = frozenset({
            Bond(0, 1), Bond(1, 2), Bond(0, 3), Bond(0, 4),
            Bond(0, 5), Bond(1, 6), Bond(1, 7), Bond(2, 8),
        })
        assert _symbol_cost(ethanol_atoms) == 1_440 <= _MAX_CANONICAL_CANDIDATES
        assert _canonical_cost(ethanol_atoms, ethanol_bonds) == 1_440   # unrefined
        assert _cost_of(_refined_blocks(ethanol_atoms, ethanol_bonds)) == 12   # if asked

    def test_no_previously_canonicalisable_molecule_changed_its_form(self):
        """
        The additivity claim, checked rather than argued: refinement can only ever be
        reached by a molecule whose symbol cost exceeds the budget, and such a molecule
        used to raise. So every canonical form that existed before #23 is untouched.
        """
        rng = random.Random(20260722)
        for _ in range(300):
            n = rng.randrange(2, 8)
            atoms = tuple(rng.choice("HCON") for _ in range(n))
            bonds = frozenset(
                Bond(rng.randrange(i), i, rng.choice([1, 1, 2])) for i in range(1, n)
            )
            if _symbol_cost(atoms) > _MAX_CANONICAL_CANDIDATES:
                continue                                    # would have raised before
            assert _canonical_blocks(atoms, bonds) == _blocks(atoms), (
                f"{atoms} was refined although the plain restriction could afford it"
            )

    def test_propane_is_now_in_reach_and_benzene_is_still_not(self):
        """
        The point of the refinement, and its boundary, in one test. Propane is what #17
        needs (a carbonyl-free isodesmic reaction needs C3); benzene is what refinement
        provably cannot help, because its carbons are genuinely interchangeable.
        """
        propane_atoms = tuple("CCC" + "H" * 8)
        propane_bonds = frozenset(
            {Bond(0, 1), Bond(1, 2)}
            | {Bond(0, 3), Bond(0, 4), Bond(0, 5)}
            | {Bond(1, 6), Bond(1, 7)}
            | {Bond(2, 8), Bond(2, 9), Bond(2, 10)}
        )
        assert _canonical_cost(propane_atoms, propane_bonds) == 2_880
        assert _canonical_cost(propane_atoms, propane_bonds) < _MAX_CANONICAL_CANDIDATES
        Molecule(propane_atoms, propane_bonds).canonical()      # does not raise

        benzene_atoms = tuple("C" * 6 + "H" * 6)
        benzene_bonds = frozenset(
            {Bond(i, (i + 1) % 6, 2 if i % 2 == 0 else 1) for i in range(6)}
            | {Bond(i, 6 + i) for i in range(6)}
        )
        assert _canonical_cost(benzene_atoms, benzene_bonds) == 518_400
        with pytest.raises(NotImplementedError, match="out of scope"):
            Molecule(benzene_atoms, benzene_bonds).canonical()

    def test_colours_refine_symbols_rather_than_reordering_them(self):
        """
        Load-bearing for stage 2 of the restriction: sorting by colour must also sort by
        element, or the two stages of the argument would fight and the argmin could sit
        outside the candidate set.
        """
        atoms = ("O", "H", "C", "H", "C", "H", "H", "H", "H")
        bonds = frozenset({
            Bond(2, 4), Bond(4, 0), Bond(2, 1), Bond(2, 3),
            Bond(2, 5), Bond(4, 6), Bond(4, 7), Bond(0, 8),
        })
        colours = _wl_colours(atoms, bonds)
        by_colour = sorted(range(len(atoms)), key=lambda i: colours[i])
        assert tuple(atoms[i] for i in by_colour) == tuple(sorted(atoms))
        # and it is a strict refinement here, not a no-op: 3 elements, 6 colours
        assert len(set(atoms)) == 3 and len(set(colours)) == 6

    def test_colours_are_equivariant_under_relabelling(self):
        """The property that lets colours sit in the sort key at all."""
        rng = random.Random(20260721)
        for _ in range(200):
            n = rng.randrange(2, 8)
            atoms = tuple(rng.choice("HCON") for _ in range(n))
            bonds = frozenset(
                Bond(rng.randrange(i), i, rng.choice([1, 1, 2])) for i in range(1, n)
            )
            sigma = list(range(n))
            rng.shuffle(sigma)                                  # sigma[old] = new
            moved_atoms = tuple(atoms[sigma.index(k)] for k in range(n))
            moved_bonds = frozenset(Bond(sigma[b.i], sigma[b.j], b.order) for b in bonds)
            before, after = _wl_colours(atoms, bonds), _wl_colours(moved_atoms, moved_bonds)
            assert all(before[i] == after[sigma[i]] for i in range(n)), (
                f"colours failed to move with the atoms: {atoms} under {sigma}"
            )


class TestCanonicalShortcutIsExact:
    """
    The shortcut restricts the search from n! permutations to prod(m_i!) over classes.
    That is only admissible if it never changes the answer, so this compares it against
    an unrestricted loop over all n! permutations -- on every labelling of small chains,
    and on seeded random graphs.

    A restriction of a search is exactly the kind of change that looks free and is not:
    if the argument about the lexicographic key were subtly wrong, every downstream
    equality in the category would silently drift. So the brute force is kept here, in
    the test, as the oracle.

    Both branches are checked. The refined key is only *reached* in production by
    molecules too big to brute-force, so the tests exercise it directly on small ones
    rather than leave the new path unverified -- which is the whole reason it is
    `_refined_blocks` under test here and not `canonical()`.
    """

    @staticmethod
    def _brute_force(atoms, bonds, colours=None):
        """
        Unrestricted minimisation over all n! permutations. Pass `colours` to score the
        refined key, omit it for the plain one.
        """
        best = None
        for perm in itertools.permutations(range(len(atoms))):
            symbols = tuple(x for _, x in sorted(zip(perm, atoms)))
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in bonds
            ))
            if colours is None:
                key = (symbols, edges)
            else:
                key = (symbols, tuple(c for _, c in sorted(zip(perm, colours))), edges)
            if best is None or key < best:
                best = key
        symbols, edges = (best[0], best[-1])
        return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in edges))

    @staticmethod
    def _restricted(atoms, bonds, blocks):
        """`canonical()`'s loop, run over a block set chosen by the caller."""
        best = None
        for perm in _perms_within(blocks, len(atoms)):
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in bonds
            ))
            if best is None or edges < best:
                best = edges
        symbols = tuple(atoms[i] for block in blocks for i in block)
        return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in best))

    def test_the_refined_restriction_is_exact_too(self):
        """
        The branch production only takes on molecules too large to brute-force. Checked
        here on small ones, where the n! oracle is affordable: restricting to colour
        classes must find the same argmin as searching every permutation under the same
        key.
        """
        rng = random.Random(20260723)
        exercised = 0
        for _ in range(400):
            n = rng.randrange(2, 8)
            atoms = tuple(rng.choice("HCON") for _ in range(n))
            # Keep one edge record per unordered pair.  Bond multiplicity belongs in
            # Bond.order; two records for the same pair are not a molecular graph.
            edge_orders = {
                (rng.randrange(i), i): rng.choice([1, 1, 1, 2, 3])
                for i in range(1, n)
            }
            for _ in range(rng.randrange(0, 3)):
                i, j = rng.sample(range(n), 2)
                edge_orders[tuple(sorted((i, j)))] = rng.choice([1, 2])
            bonds = frozenset(Bond(i, j, order)
                              for (i, j), order in edge_orders.items())
            colours = _wl_colours(atoms, bonds)
            refined = _refined_blocks(atoms, bonds)
            if _cost_of(refined) < _symbol_cost(atoms):
                exercised += 1                       # refinement actually split something
            assert (self._restricted(atoms, bonds, refined)
                    == self._brute_force(atoms, bonds, colours)), (
                f"refined restriction disagrees with brute force on {atoms} {sorted(bonds)}"
            )
        assert exercised > 100, (
            f"only {exercised}/400 cases refined anything -- the sample is not testing "
            f"the branch it claims to"
        )

    def test_isomorphic_molecules_still_canonicalise_together(self):
        """
        The property everything downstream actually rides on, checked on both branches:
        relabelling a molecule must not change what it canonicalises to, and molecules
        that differ must not collide.

        Checked through `_restricted` on each block set rather than through `canonical()`,
        so the refined branch is covered on molecules small enough to also verify by
        brute force.
        """
        rng = random.Random(20260721)
        seen: dict[tuple, tuple] = {}
        for _ in range(300):
            n = rng.randrange(2, 7)
            atoms = tuple(rng.choice("HCO") for _ in range(n))
            bonds = frozenset(
                Bond(rng.randrange(i), i, rng.choice([1, 1, 2])) for i in range(1, n)
            )
            sigma = list(range(n))
            rng.shuffle(sigma)                                      # sigma[old] = new
            moved_atoms = tuple(atoms[sigma.index(k)] for k in range(n))
            moved_bonds = frozenset(Bond(sigma[b.i], sigma[b.j], b.order) for b in bonds)
            for blocks_of in (lambda a, _: _blocks(a), _refined_blocks):
                here = self._restricted(atoms, bonds, blocks_of(atoms, bonds))
                there = self._restricted(moved_atoms, moved_bonds,
                                         blocks_of(moved_atoms, moved_bonds))
                assert here == there, f"{atoms} moved under {sigma} and changed form"
                # and the form must discriminate: same canonical form => same brute force
                truth = self._brute_force(atoms, bonds)
                if here in seen:
                    assert seen[here] == truth, f"{atoms} collided with a different molecule"
                seen[here] = truth

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
            edge_orders = {}
            for i in range(1, n):                      # spanning path: always connected
                edge_orders[(rng.randrange(i), i)] = rng.choice([1, 1, 1, 2, 3])
            for _ in range(rng.randrange(0, 3)):       # a few chords
                i, j = rng.sample(range(n), 2)
                edge_orders[tuple(sorted((i, j)))] = rng.choice([1, 2])
            bonds = frozenset(Bond(i, j, order)
                              for (i, j), order in edge_orders.items())
            assert Molecule(atoms, bonds).canonical() == self._brute_force(atoms, bonds), (
                f"shortcut disagrees with brute force on {atoms} {sorted(bonds)}"
            )

    def test_the_candidate_count_is_what_is_actually_enumerated(self):
        """`_canonical_cost` is the budget gate, so it must not be an estimate."""
        cases = [
            (("H", "H"), frozenset({Bond(0, 1)})),
            (("C", "H", "H", "O"), frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3)})),
            (("C", "C", "H", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2), Bond(1, 3),
                                                   Bond(1, 4)})),
        ]
        for atoms, bonds in cases:
            enumerated = len(list(_sorting_permutations(atoms, bonds)))
            assert enumerated == _canonical_cost(atoms, bonds), atoms

    def test_every_candidate_realises_the_same_prefix(self):
        """
        `canonical()` compares only `edges`, having hoisted the rest of the key out of
        the loop as constant across the candidate set. If that were false it would be
        silently minimising a different key than the one its argument is about.

        The invariant is branch-dependent, and that is the point: permuting within symbol
        classes fixes `symbols` but NOT `colours` -- which is exactly why colours are not
        in the key on that branch. Only the refined branch fixes both.
        """
        atoms = ("O", "H", "C", "H", "C", "H", "H", "H", "H")       # scrambled ethanol
        bonds = frozenset({
            Bond(2, 4), Bond(4, 0), Bond(2, 1), Bond(2, 3),
            Bond(2, 5), Bond(4, 6), Bond(4, 7), Bond(0, 8),
        })
        colours = _wl_colours(atoms, bonds)

        def prefixes(blocks):
            out = set()
            for perm in _perms_within(blocks, len(atoms)):
                out.add((tuple(x for _, x in sorted(zip(perm, atoms))),
                         tuple(c for _, c in sorted(zip(perm, colours)))))
            return out

        by_symbol = prefixes(_blocks(atoms))
        assert {s for s, _ in by_symbol} == {tuple(sorted(atoms))}
        assert len({c for _, c in by_symbol}) > 1, (
            "colours are not constant here, so they must not be in this branch's key"
        )

        by_colour = prefixes(_refined_blocks(atoms, bonds))
        assert by_colour == {(tuple(sorted(atoms)), tuple(sorted(colours)))}

    def test_homonuclear_saves_nothing_and_says_so(self):
        """
        The boundary, and it is now a topological one rather than a compositional one.
        Seven carbons in a ring: one element, and every atom has the same surroundings as
        every other, so refinement splits nothing and prod(m_i!) is still n!.
        """
        atoms = tuple("C" * 7)
        ring = frozenset(Bond(i, (i + 1) % 7) for i in range(7))
        assert _canonical_cost(atoms, ring) == math.factorial(7)
        assert _canonical_cost(atoms, frozenset()) == math.factorial(7)


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
