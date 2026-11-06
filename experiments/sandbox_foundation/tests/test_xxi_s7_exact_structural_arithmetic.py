"""OPERATION XXI section 7 -- the bridge's STRUCTURAL verdicts are EXACT integers over FULL species identity.

Ooh yeah, no more float-then-round!  Task A: ``_matrix_column_sums`` (E N column sums) and ``_exact_net_production``
(N 1) are summed in unbounded Python ints straight off the integer stoichiometry.  The ``_legacy_*`` helpers below are
the OLD float-numpy bodies, kept ONLY so each test can show the old path giving a WRONG integer where the exact one is
right.  Task B: ``kernel_signature`` keys reaction participants by the FULL species identity, not the display name.
"""
from __future__ import annotations

import numpy as np

from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Reaction, Species
from experiments.sandbox_foundation.open_diagram_bridge import (
    _exact_net_production,
    _matrix_column_sums,
    build_demo_diagram,
    bridge_to_kernel,
    column_summed_EN,
    kernel_signature,
)

BIG = 2 ** 60


def _legacy_column_sums(system: ChemicalSystem) -> dict:
    """The pre-XXI-7 body of ``_matrix_column_sums`` (float E @ float N, then rint) -- the thing being replaced."""
    totals = np.rint(system.E @ system.N @ np.ones(len(system.reactions))).astype(int)
    return {label: int(v) for label, v in zip(system.component_labels, totals) if v != 0}


def _legacy_net_production(system: ChemicalSystem) -> tuple:
    """The pre-XXI-7 N 1 row sums (float N @ ones, then rint)."""
    return tuple(int(v) for v in np.rint(system.N @ np.ones(len(system.reactions))).astype(int))


# ======================================================================================
# Task A -- exact integer arithmetic
# ======================================================================================
class TestAExactColumnSums:
    @staticmethod
    def _beyond_float_system():
        # A has 1 X, B has 3 X.  Reaction: -3k A + k B  (X: -3k + 3k = 0, EXACTLY balanced), k = 2**60 + 200.
        # k and 3k are NOT float64-representable (spacing 256 / 512 up there), so the float cast shifts them by
        # different amounts: the float E@N column is -256 + ... != 0 even though the reaction is exactly balanced.
        k = BIG + 200
        a = Species.of("A", {"X": 1})
        b = Species.of("B", {"X": 3})
        return ChemicalSystem([a, b], [Reaction("r", ((a, -3 * k), (b, k)))])

    def test_balanced_beyond_2_53_is_verified_exactly(self):
        system = self._beyond_float_system()
        assert max(abs(c) for _, c in system.reactions[0].stoich) > 2 ** 53
        assert _matrix_column_sums(system) == {}                       # exact: E N = 0
        assert column_summed_EN(system.reactions) == {}                # the other (composition-first) exact route agrees

    def test_the_old_float_rint_path_gives_a_WRONG_integer_here(self):
        system = self._beyond_float_system()
        legacy = _legacy_column_sums(system)
        # Measured on this box: float+rint reports X: 512 for a reaction that is exactly balanced (a FALSE imbalance
        # that bridge_to_kernel would have raised as BridgeCrossCheckError against the exact pre-kernel sums).
        assert legacy != {}
        assert legacy != _matrix_column_sums(system)
        assert set(legacy) == {"X"}

    def test_exact_cancellation_where_float_loses_the_small_term(self):
        # four species with 1 X each; coefficients -2**60, +1, +2**60, -1 sum to EXACTLY 0.  In float64 the +1 is
        # absorbed (-2**60 + 1 == -2**60) and the trailing -1 is left over.  Whether numpy's dot reorders its
        # accumulation is a BLAS detail (on this box it happens to reorder and get 0), so the float loss is pinned with a
        # plain left-to-right float sum -- the order-DEPENDENCE is the whole point: an exact int sum has none.
        species = [Species.of(name, {"X": 1}) for name in "ABCD"]
        a, b, c, d = species
        system = ChemicalSystem(species, [Reaction("r", ((a, -BIG), (b, 1), (c, BIG), (d, -1)))])
        assert _matrix_column_sums(system) == {}
        assert column_summed_EN(system.reactions) == {}
        coefficients = [-BIG, 1, BIG, -1]
        left_to_right = 0.0
        for coeff in coefficients:
            left_to_right += float(coeff)
        assert left_to_right == -1.0 and sum(coefficients) == 0        # float: wrong, non-zero; exact int: 0

    def test_charge_row_is_exact_too(self):
        # charge carried at magnitude: k M0 + k N0 -> k M+ + k N-  with k = 2**60 + 1 (not float-representable).
        # The charge row is k*(+1) + k*(-1) = 0 exactly.
        cation = Species.of("M+", {"M": 1}, charge=1)
        neutral = Species.of("M0", {"M": 1}, charge=0)
        anion = Species.of("N-", {"N": 1}, charge=-1)
        k = BIG + 1
        n0 = Species.of("N0", {"N": 1})
        system = ChemicalSystem(
            [cation, neutral, anion, n0],
            [Reaction("r", ((cation, k), (anion, k), (n0, -k), (neutral, -k)))])
        assert _matrix_column_sums(system) == {}                       # M: k-k, N: k-k, charge: k(+1)+k(-1)

    def test_dict_shape_is_preserved_on_the_real_demo(self):
        # same return shape as before: {label: python int}, zeros dropped (empty for an accepted system).
        system = bridge_to_kernel(build_demo_diagram()).system
        assert _matrix_column_sums(system) == {} == column_summed_EN(system.reactions)
        assert all(type(v) is int for v in _matrix_column_sums(system).values())

    def test_no_reactions_is_the_empty_dict(self):
        a = Species.of("A", {"X": 1})
        assert _matrix_column_sums(ChemicalSystem([a], [])) == {}


class TestAExactNetProduction:
    @staticmethod
    def _cancelling_system():
        # a, b each 1 X.  r1 moves 2**60 a->b, r2 moves 1 a->b, r3 moves 2**60 b->a.  Net a->b is exactly 1.
        a, b = Species.of("A", {"X": 1}), Species.of("B", {"X": 1})
        rxns = [Reaction("r1", ((a, -BIG), (b, BIG))), Reaction("r2", ((a, -1), (b, 1))),
                Reaction("r3", ((a, BIG), (b, -BIG)))]
        return ChemicalSystem([a, b], rxns)

    def test_large_positive_negative_cancellation_is_exact(self):
        system = self._cancelling_system()
        assert _exact_net_production(system) == (-1, 1)
        assert all(type(v) is int for v in _exact_net_production(system))

    def test_the_old_float_rint_path_loses_the_unit(self):
        system = self._cancelling_system()
        # float: (-2**60 - 1) rounds back to -2**60, then + 2**60 -> 0, so the true net of -1 / +1 vanishes entirely.
        assert _legacy_net_production(system) == (0, 0)
        assert _legacy_net_production(system) != _exact_net_production(system)

    def test_sum_beyond_2_53_keeps_the_low_bit(self):
        a, b = Species.of("A", {"X": 1}), Species.of("B", {"X": 1})
        rxns = [Reaction("r1", ((a, -BIG), (b, BIG))), Reaction("r2", ((a, -1), (b, 1)))]
        system = ChemicalSystem([a, b], rxns)
        assert _exact_net_production(system) == (-(BIG + 1), BIG + 1)
        assert _legacy_net_production(system)[1] == BIG            # float forgot the +1

    def test_matches_the_float_path_on_the_real_demo(self):
        # control: in the ordinary regime the exact helper and the old float path agree, so nothing else moved.
        system = bridge_to_kernel(build_demo_diagram()).system
        assert _exact_net_production(system) == _legacy_net_production(system)
        assert _matrix_column_sums(system) == _legacy_column_sums(system) == {}


# ======================================================================================
# Task B -- full species identity in the signature
# ======================================================================================
class TestBFullIdentitySignature:
    @staticmethod
    def _two_step(composition_of_S: int):
        s = Species.of("S", {"X": composition_of_S})
        t = Species.of("T", {"X": composition_of_S})
        return ChemicalSystem([s, t], [Reaction("r", ((s, -1), (t, 1)))])

    def test_same_name_different_composition_do_not_collapse(self):
        one, two = self._two_step(1), self._two_step(2)
        assert [sp.name for sp in one.species] == [sp.name for sp in two.species] == ["S", "T"]
        sig_one, sig_two = kernel_signature(one), kernel_signature(two)
        assert sig_one != sig_two
        assert sig_one[0] != sig_two[0]                               # species part differs (already the case)
        assert sig_one[1] != sig_two[1]                               # reaction participants differ (the XXI-7 fix)

    def test_same_name_different_charge_do_not_collapse(self):
        def make(charge):
            s = Species.of("S", {"X": 1}, charge=charge)
            t = Species.of("T", {"X": 1}, charge=charge)
            return ChemicalSystem([s, t], [Reaction("r", ((s, -1), (t, 1)))])
        a, b = make(0), make(1)
        assert kernel_signature(a)[1] != kernel_signature(b)[1]
        assert kernel_signature(a) != kernel_signature(b)

    def test_same_name_different_phase_and_substance_do_not_collapse(self):
        def make(phase, substance):
            s = Species.of("S", {"X": 1}, phase=phase, substance=substance)
            t = Species.of("T", {"X": 1})
            return ChemicalSystem([s, t], [Reaction("r", ((s, -1), (t, 1)))])
        base = make(Phase.AQUEOUS, None)
        assert kernel_signature(base)[1] != kernel_signature(make(Phase.GAS, None))[1]
        assert kernel_signature(base)[1] != kernel_signature(make(Phase.AQUEOUS, "other-compound"))[1]

    def test_two_distinct_species_sharing_a_name_stay_two_participants_in_one_reaction(self):
        # S(neutral) and S(+) share the display name "S" AND the coefficient -1: a name-keyed frozenset would merge
        # them into ONE participant.  Full identity keeps all three participants.
        s0 = Species.of("S", {"X": 1}, charge=0)
        s1 = Species.of("S", {"X": 1}, charge=1)
        p = Species.of("P", {"X": 2}, charge=1)
        system = ChemicalSystem([s0, s1, p], [Reaction("merge", ((s0, -1), (s1, -1), (p, 1)))])
        participants = next(iter(kernel_signature(system)[1]))[1]
        assert len(participants) == 3
        assert len({name for (name, *_), _ in participants}) == 2    # only TWO distinct names -> the old key had 2 entries

    def test_still_presentation_independent_and_a_frozenset(self):
        s0 = Species.of("S", {"X": 1})
        t = Species.of("T", {"X": 1})
        forward = ChemicalSystem([s0, t], [Reaction("r", ((s0, -1), (t, 1)))])
        backward = ChemicalSystem([t, s0], [Reaction("r", ((t, 1), (s0, -1)))])      # species + stoich order swapped
        sig = kernel_signature(forward)
        assert sig == kernel_signature(backward)
        assert isinstance(sig[0], frozenset) and isinstance(sig[1], frozenset)
        assert all(isinstance(participants, frozenset) for _, participants in sig[1])

    def test_demo_signature_is_stable_in_shape(self):
        sig = bridge_to_kernel(build_demo_diagram()).signature()
        assert len(sig[0]) == 6 and len(sig[1]) == 2
        for _, participants in sig[1]:
            for identity, coeff in participants:
                assert len(identity) == 5 and type(coeff) is int
