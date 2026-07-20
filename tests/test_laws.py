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
        big = Molecule(tuple("H" * 9), frozenset())
        with pytest.raises(NotImplementedError, match="out of scope"):
            big.canonical()


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
