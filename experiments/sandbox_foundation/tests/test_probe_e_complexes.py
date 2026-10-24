"""PROBE E -- reaction COMPLEXES vs net stoichiometry.

A mechanism's authority is the (reactant complex, product complex) pair; the net matrix N = product - reactant
is a LOSSY projection.  Reading mass-action orders off N (the historical bug) drops any species whose net
contribution is zero or cancelled -- catalysts and autocatalysts.  These tests pin the correct behaviour and
are the red-first reproductions of the fix.  Everything here is SYNTHETIC / idealized (abstract species)."""
import numpy as np
import pytest

from experiments.sandbox_foundation.fixtures import single_cell_system
from experiments.sandbox_foundation.twocell import (
    InvalidParameterError, Mechanism, ReactionRate, State, reaction_step)


def _autocatalytic():
    """A + B -> 2B (elementary).  reactant = {A:1, B:1}, product = {B:2}; net = {A:-1, B:+1}.
    A, B are 'isomers' of element X (both carry 1 X); charge 0.  True rate r = k[A][B]."""
    return Mechanism(("A", "B"), [[1.0], [1.0]], [[0.0], [2.0]], ("X", "charge"),
                     [[1, 1], [0, 0]], (ReactionRate(k_f=1.0, reversible=False),),
                     label="SYNTHETIC-autocatalysis A+B->2B")


def _catalytic():
    """A + C -> B + C (elementary).  C is a catalyst: on both sides, NET zero, but IN the rate law.
    reactant = {A:1, C:1}, product = {B:1, C:1}.  X carries A/B, Y carries C.  True rate r = k[A][C]."""
    return Mechanism(("A", "B", "C"), [[1.0], [0.0], [1.0]], [[0.0], [1.0], [1.0]],
                     ("X", "Y", "charge"), [[1, 1, 0], [0, 0, 1], [0, 0, 0]],
                     (ReactionRate(k_f=1.0, reversible=False),), label="SYNTHETIC-catalysis A+C->B+C")


# ---- T1: autocatalysis needs a seed; the rate depends on the (shared) product --------------------------------
def test_T1_autocatalytic_rate_needs_a_seed_and_depends_on_the_product():
    m = _autocatalytic()
    assert np.array_equal(m.N, [[-1.0], [1.0]])                       # net is identical to a unimolecular A->B...
    assert m.rate_vector([5.0, 0.0])[0] == 0.0                        # ...yet with B=0 the TRUE rate is 0, not k[A]
    assert m.rate_vector([5.0, 2.0])[0] == pytest.approx(10.0)        # r = k[A][B] = 1*5*2
    assert np.array_equal(m.source_density([5.0, 0.0]), [0.0, 0.0])   # no net source without a seed


def test_T1_contrast_true_unimolecular_with_the_same_net_DOES_proceed():
    # A -> B shares the net column [-1, +1] but is a DIFFERENT reaction (no shared species): it runs from pure A.
    uni = Mechanism.from_net(("A", "B"), [[-1.0], [1.0]], ("X", "charge"), [[1, 1], [0, 0]],
                             (ReactionRate(k_f=1.0, reversible=False),), label="SYNTHETIC A->B")
    assert np.array_equal(uni.N, _autocatalytic().N)                 # identical NET...
    assert uni.rate_vector([5.0, 0.0])[0] == 5.0                     # ...opposite behaviour at B=0 (complexes differ)


# ---- T2: a catalyst has zero net but keeps its kinetic dependence --------------------------------------------
def test_T2_catalyst_has_zero_net_but_keeps_its_kinetic_dependence():
    m = _catalytic()
    assert np.array_equal(m.N[:, 0], [-1.0, 1.0, 0.0])               # C's NET stoichiometry is exactly zero
    assert m.rate_vector([5.0, 0.0, 0.0])[0] == 0.0                  # no catalyst -> no reaction (not k[A])
    assert m.rate_vector([5.0, 0.0, 3.0])[0] == pytest.approx(15.0)  # r = k[A][C] = 1*5*3
    # a cell with C=0 stays inert for all time: c_C never changes (net 0), so the rate is identically 0
    sysm = single_cell_system(m)
    inert = State(np.array([[5.0, 0.0, 0.0]] * 2), np.ones(2))
    s1, _ = reaction_step(sysm, inert, 10.0)
    assert np.max(np.abs(s1.n - inert.n)) < 1e-12


# ---- a NET column cannot masquerade as a complex -------------------------------------------------------------
def test_negative_complex_entry_is_refused():
    with pytest.raises(InvalidParameterError):                        # a negative 'reactant' entry is a net column
        Mechanism(("A", "B"), [[-1.0], [1.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, reversible=False),))


# ---- empirical (non-elementary) orders: explicit, never inferred, never from the net -------------------------
def test_empirical_orders_decouple_kinetics_from_stoichiometry():
    # A -> B stoichiometrically, but an empirically measured half-order forward law r = k[A]^0.5 (NOT elementary).
    m = Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=2.0, reversible=False),),
                  kinetics="empirical", forward_orders=[[0.5], [0.0]],
                  rate_law_note="measured half-order in A; 298 K, dilute (SYNTHETIC)")
    assert m.rate_vector([4.0, 0.0])[0] == pytest.approx(2.0 * 2.0)   # k[A]^0.5 = 2*sqrt(4) = 4
    assert np.array_equal(m.N, [[-1.0], [1.0]])                       # stoichiometry (hence conservation) unchanged


def test_elementary_kinetics_rejects_explicit_orders():
    with pytest.raises(InvalidParameterError):                        # orders without declaring empirical
        Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, reversible=False),), forward_orders=[[0.5], [0.0]])


def test_empirical_reversible_requires_reverse_orders():
    with pytest.raises(InvalidParameterError):                        # reversible empirical law with no reverse orders
        Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, k_r=1.0, reversible=True),),
                  kinetics="empirical", forward_orders=[[1.0], [0.0]])


# ---- B1: the THREE permanent distinguishing examples, pinned together ----------------------------------------
def test_the_three_permanent_distinguishing_examples_share_a_net_yet_differ_in_kinetics():
    """A -> B, A + B -> 2B, A + C -> B + C: the net column CANNOT be the kinetic authority.
    A->B and A+B->2B share the EXACT net column on (A,B) but diverge at a seedless state; the catalyst
    A+C->B+C has net C = 0 yet a live [C] dependence.  This is the permanent guard for the lossy-projection
    theorem [[net-stoichiometry-is-not-a-mechanism]]."""
    uni = Mechanism.from_net(("A", "B"), [[-1.0], [1.0]], ("X", "charge"), [[1, 1], [0, 0]],
                             (ReactionRate(k_f=1.0, reversible=False),), label="A->B")
    auto = _autocatalytic()      # A + B -> 2B
    cat = _catalytic()           # A + C -> B + C
    # A->B and A+B->2B: identical net column, opposite behaviour where the shared product is absent.
    assert np.array_equal(uni.N, auto.N)
    assert uni.rate_vector([5.0, 0.0])[0] == 5.0 and auto.rate_vector([5.0, 0.0])[0] == 0.0
    # the catalyst's net is zero on C, but reducing to net would wrongly erase its rate dependence.
    assert cat.N[2, 0] == 0.0 and cat.rate_vector([5.0, 0.0, 0.0])[0] == 0.0
    assert cat.rate_vector([5.0, 0.0, 3.0])[0] == pytest.approx(15.0)


# ---- B1: strengthened structural validation (finite / integer / unique / bounded) ----------------------------
def test_duplicate_species_identity_is_refused():
    with pytest.raises(InvalidParameterError):
        Mechanism(("A", "A"), [[1.0], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, reversible=False),))


def test_fractional_complex_multiplicity_is_refused_but_fractional_orders_are_not():
    with pytest.raises(InvalidParameterError):   # a half MOLECULE as a structural reactant is nonsense...
        Mechanism(("A", "B"), [[0.5], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, reversible=False),))
    # ...but a half-ORDER empirical rate law is legitimate (integer complex, fractional order) -- must NOT raise.
    m = Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, reversible=False),),
                  kinetics="empirical", forward_orders=[[0.5], [0.0]], rate_law_note="half-order (SYNTHETIC)")
    assert m.rate_vector([4.0, 0.0])[0] == pytest.approx(2.0)


def test_non_finite_complex_is_refused():
    with pytest.raises(InvalidParameterError):
        Mechanism(("A", "B"), [[np.inf], [0.0]], [[0.0], [1.0]], ("X",), [[1, 1]],
                  (ReactionRate(k_f=1.0, reversible=False),))


def test_oversized_reaction_count_is_a_bounded_refusal():
    from experiments.sandbox_foundation.twocell import MAX_REACTIONS
    big = MAX_REACTIONS + 1
    with pytest.raises(InvalidParameterError):   # refused at the bound BEFORE any (big) allocation downstream
        Mechanism(("A", "B"), np.zeros((2, big)), np.zeros((2, big)), ("X", "charge"),
                  [[1, 1], [0, 0]], ())


def test_oversized_coefficient_is_a_bounded_refusal():
    from experiments.sandbox_foundation.twocell import MAX_COEFF
    with pytest.raises(InvalidParameterError):
        Mechanism(("A", "B"), [[MAX_COEFF + 1.0], [0.0]], [[0.0], [1.0]], ("X", "charge"),
                  [[1, 1], [0, 0]], (ReactionRate(k_f=1.0, reversible=False),))


# ---- B1: explicit behaviour for the degenerate cases ---------------------------------------------------------
def test_zero_net_transformation_is_well_defined():
    # reactant == product (A -> A): net column is exactly zero, so the net source is identically 0.
    m = Mechanism(("A", "B"), [[1.0], [0.0]], [[1.0], [0.0]], ("X", "charge"), [[1, 1], [0, 0]],
                  (ReactionRate(k_f=3.0, reversible=False),), label="A->A (zero-net)")
    assert np.array_equal(m.N, [[0.0], [0.0]])
    assert np.array_equal(m.source_density([5.0, 0.0]), [0.0, 0.0])   # no net change for any state


def test_zero_reaction_network_is_well_defined():
    # an empty reaction set (R = 0) is a valid, inert mechanism: no reactions, no source, no crash.
    m = Mechanism(("A",), np.zeros((1, 0)), np.zeros((1, 0)), ("X",), [[1.0]], ())
    assert m.n_reactions == 0
    assert m.rate_vector([2.0]).shape == (0,)
    assert np.array_equal(m.source_density([2.0]), [0.0])
