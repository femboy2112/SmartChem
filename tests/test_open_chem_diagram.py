"""The Move-1 keystone Rung-B acceptance gate (contract v0.2 section 6) + preservation.

Four falsifiable gates on :mod:`smartchem.open_chem_diagram`, each mirroring the shape of the
electrical open-diagram laws (``tests/test_open_diagram.py:350-412``) -- equality is taken under the
structural ``canonicalize`` quotient, never raw ``==``:

1. interchange / braid / hexagon under the quotient, plus a fail-closed budget refusal;
2. a real non-test consumer -- ``ExperimentStep.open().close()`` reproduces the step's ``Reaction``
   certificate byte-for-byte, and a mass-violating closed diagram is unconstructible as closed;
3. P4 -- the causal DAG round-trips to/from ``Reaction.path``/``generator_word`` for the linear case,
   and two interchange-equivalent assemblies yield EQUAL provenance;
4. any OPEN port ⇒ conservation UNDECIDED (never conserved, never violated).
"""
from __future__ import annotations

import pytest

from smartchem.category import (
    Config,
    ConservationError,
    Molecule,
    Reaction,
    tensor_obj,
)
from smartchem.contracts import canonical_digest
from smartchem.experiment.step import ExperimentStep
from smartchem.open_chem_diagram import (
    ConservationStatus,
    OpenChemDiagram,
    OpenDiagramError,
    braid,
    canonicalize,
    identity_diagram,
)
from smartchem.open_core import CanonicalizationBudgetExceeded


# -- shared species & single-step reaction diagrams -------------------------------------
H = Molecule.atom("H")
N = Molecule.atom("N")
H2 = Molecule.diatomic("H", "H")
N2 = Molecule.diatomic("N", "N", order=3)

HH = Config.of(H, H)
NN = Config.of(N, N)
H2C = Config.of(H2)
N2C = Config.of(N2)


def _f() -> OpenChemDiagram:  # H + H -> H2
    return OpenChemDiagram.single_step(HH, H2C, generator_id="h+")


def _g() -> OpenChemDiagram:  # H2 -> H + H
    return OpenChemDiagram.single_step(H2C, HH, generator_id="h-")


def _h() -> OpenChemDiagram:  # N + N -> N2
    return OpenChemDiagram.single_step(NN, N2C, generator_id="n+")


def _k() -> OpenChemDiagram:  # N2 -> N + N
    return OpenChemDiagram.single_step(N2C, NN, generator_id="n-")


# ======================================================================================
# GATE 1 -- interchange / braid / hexagon under the quotient + fail-closed refusal
# ======================================================================================
class TestGate1LawsUnderTheQuotient:
    @staticmethod
    def _same(left: OpenChemDiagram, right: OpenChemDiagram) -> None:
        assert canonicalize(left) == canonicalize(right)

    def test_raw_equality_is_not_the_quotient(self):
        # A control mirroring the electrical review: the law holds under canonicalize, and the
        # two assemblies are genuinely different *presentations* (so the quotient is doing work).
        f, g, h, k = _f(), _g(), _h(), _k()
        lhs = f.then(g).tensor(h.then(k))
        rhs = f.tensor(h).then(g.tensor(k))
        assert lhs.core != rhs.core  # different raw presentations
        assert canonicalize(lhs) == canonicalize(rhs)  # equal under the quotient

    def test_tensor_interchange(self):
        f, g, h, k = _f(), _g(), _h(), _k()
        self._same(
            f.then(g).tensor(h.then(k)),
            f.tensor(h).then(g.tensor(k)),
        )

    def test_braid_involution_and_naturality(self):
        self._same(braid(HH, NN).then(braid(NN, HH)), identity_diagram(tensor_obj(HH, NN)))
        f, g = _f(), _h()
        self._same(
            f.tensor(g).then(braid(f.external_output(), g.external_output())),
            braid(f.external_input(), g.external_input()).then(g.tensor(f)),
        )

    def test_hexagon(self):
        # tensor_obj canonically re-sorts a Config's species, so pick species whose canonical order
        # (F < H < O) already matches the positional intent b (x) c -- otherwise the object-level sort
        # and the position-level interface tensor would disagree on port order.
        a = Config.atoms("H")
        b = Config.atoms("F")
        c = Config.atoms("O")
        self._same(
            braid(a, tensor_obj(b, c)),
            braid(a, b).tensor(identity_diagram(c)).then(
                identity_diagram(b).tensor(braid(a, c))
            ),
        )

    def test_identity_and_associativity(self):
        f = _f()
        self._same(identity_diagram(f.external_input()).then(f), f)
        self._same(f.then(identity_diagram(f.external_output())), f)
        # A genuinely composable chain a;b;c : (H+H -> H2) ; (H2 -> H+H) ; (H+H -> H2).
        a, b, c = _f(), _g(), _f()
        self._same(a.then(b).then(c), a.then(b.then(c)))

    def test_quotient_budget_refuses_fail_closed_never_a_silent_pass(self):
        # A pathologically symmetric apex: one reactant, four indistinguishable OPEN products of the
        # same species.  WL cannot split them, so the exact search is 4! candidates.
        symmetric = OpenChemDiagram.single_step(
            Config.atoms("H"),
            Config.of(H, H, H, H),
            open_products=frozenset({0, 1, 2, 3}),
        )
        with pytest.raises(CanonicalizationBudgetExceeded):
            canonicalize(symmetric, budget=10)
        # The refusal is budget-driven, not a broken diagram: a large enough budget succeeds.
        assert canonicalize(symmetric) == canonicalize(symmetric)


# ======================================================================================
# GATE 2 -- a real non-test consumer: ExperimentStep.open().close() is byte-identical (P3)
# ======================================================================================
class TestGate2RealConsumerByteIdentity:
    def _step(self) -> ExperimentStep:
        # H + H -> H2, a genuinely conserving bench step.
        return ExperimentStep.assembling(H2, (H, H), (H2,))

    def test_open_close_reproduces_the_certificate_byte_for_byte(self):
        step = self._step()
        # The reference is the SAME conservation certificate __post_init__ builds and re-checks.
        reference = Reaction(
            Config.of(*step.reactants), Config.of(*step.products), name="experiment-step"
        )
        closed = step.open().close()
        assert closed == reference
        assert canonical_digest(closed) == canonical_digest(reference)

    def test_open_close_round_trips_a_multi_species_step(self):
        step = ExperimentStep.assembling(
            Molecule.diatomic("H", "Cl"),
            (H, Molecule.atom("Cl")),
            (Molecule.diatomic("H", "Cl"),),
        )
        reference = Reaction(
            Config.of(*step.reactants), Config.of(*step.products), name="experiment-step"
        )
        assert canonical_digest(step.open().close()) == canonical_digest(reference)

    def test_mass_violating_closed_diagram_is_unconstructible_as_closed(self):
        # The open diagram exists (a morphism regardless of balance); closing it is refused exactly
        # as Reaction.__post_init__ refuses today -- a mass-violating CLOSED value cannot be built.
        bad = OpenChemDiagram.single_step(Config.atoms("H"), Config.atoms("O"))
        assert bad.is_saturated  # no OPEN ports -- it is closeable, and closing must reject it
        with pytest.raises(ConservationError, match="mass not conserved"):
            bad.close()

    def test_open_diagram_never_touches_the_step_digest(self):
        # P2 spot check: opening a step does not mutate the step nor its digest.
        step = self._step()
        before = step.digest
        step.open()
        assert step.digest == before


# ======================================================================================
# GATE 3 -- P4: provenance round-trips (linear) and survives the interchange quotient
# ======================================================================================
class TestGate3Provenance:
    def test_linear_dag_round_trips_to_path_and_generator_word(self):
        a = Config.atoms("H", "H")
        b = Config.of(H2)
        c = Config.atoms("H", "H")
        reaction = Reaction(a, b, generator_id="assoc").then(
            Reaction(b, c, generator_id="dissoc")
        )
        diagram = OpenChemDiagram.from_reaction(reaction)
        path, word = diagram.to_reaction_path()
        assert path == reaction.path
        assert word == reaction.generator_word

    def test_interchange_equivalent_assemblies_have_equal_provenance(self):
        f, g, h, k = _f(), _g(), _h(), _k()
        lhs = f.then(g).tensor(h.then(k))
        rhs = f.tensor(h).then(g.tensor(k))
        # The spurious linearization is erased, the causal trail is not: identical DAGs.
        assert lhs.apex.provenance == rhs.apex.provenance
        # And the dependency edges are exactly the two intended causal chains, no cross-links.
        deps = lhs.apex.provenance.deps
        assert len(deps) == 2
        assert len(lhs.apex.provenance.nodes) == 4

    def test_tensor_is_independent_then_adds_dependencies(self):
        f, g = _f(), _g()
        # f;g is a causal chain (one dependency); f (x) g is independent (no dependency).
        assert len(f.then(g).apex.provenance.deps) == 1
        assert len(f.tensor(g).apex.provenance.deps) == 0


# ======================================================================================
# GATE 4 -- any OPEN port ⇒ conservation UNDECIDED (never conserved, never violated)
# ======================================================================================
class TestGate4OpenIsUndecided:
    def _open_diagram(self) -> OpenChemDiagram:
        # H2 -> H + H, but one product H is left as an unfilled (OPEN) slot.
        return OpenChemDiagram.single_step(H2C, HH, open_products=frozenset({1}))

    def test_open_port_is_undecided(self):
        diagram = self._open_diagram()
        assert not diagram.is_saturated
        assert diagram.open_nodes()  # at least one OPEN slot
        assert diagram.conservation_status() is ConservationStatus.UNDECIDED
        assert diagram.conservation_status() is not ConservationStatus.VIOLATED
        assert diagram.conservation_status() is not ConservationStatus.CONSERVING
        assert not diagram.is_closed_and_conserving

    def test_open_diagram_cannot_be_closed(self):
        with pytest.raises(OpenDiagramError, match="OPEN"):
            self._open_diagram().close()

    def test_saturated_conserving_diagram_is_conserving(self):
        # The contrast case: with every port filled and mass balanced, the verdict is CONSERVING.
        diagram = OpenChemDiagram.single_step(H2C, HH)
        assert diagram.is_saturated
        assert diagram.conservation_status() is ConservationStatus.CONSERVING
        assert diagram.is_closed_and_conserving

    def test_saturated_but_unbalanced_diagram_is_violated(self):
        diagram = OpenChemDiagram.single_step(Config.atoms("H"), Config.atoms("O"))
        assert diagram.is_saturated
        assert diagram.conservation_status() is ConservationStatus.VIOLATED


# ======================================================================================
# Supporting: the conservation decoration is an additive, interchange-invariant slot
# ======================================================================================
class TestConservationDecorationSlot:
    def test_conserving_steps_carry_the_zero_vector(self):
        assert _f().apex.conservation.is_balanced
        assert _f().then(_g()).apex.conservation.is_balanced

    def test_non_conserving_step_carries_the_real_net_vector(self):
        # H -> O produces one O and consumes one H: net {H:-1, O:+1}.
        net = OpenChemDiagram.single_step(Config.atoms("H"), Config.atoms("O")).apex.conservation.net
        assert net == (("H", -1), ("O", 1))

    def test_decoration_is_additive_and_interchange_invariant(self):
        f, g, h, k = _f(), _g(), _h(), _k()
        lhs = f.then(g).tensor(h.then(k)).apex.conservation
        rhs = f.tensor(h).then(g.tensor(k)).apex.conservation
        assert lhs == rhs


# ======================================================================================
# CONGRUENCE -- the SMC obligation the first draft missed (adversarial-review regression)
# ======================================================================================
class TestQuotientIsACongruence:
    """canonicalize-equality must be preserved by then/tensor, or it is not a category quotient.

    The pre-merge review proved the first draft was NOT a congruence: an identity wire laundered a
    provenance frontier so ``f`` and ``f;id`` compared equal yet diverged under a later ``then``.
    Provenance is now derived from the composed topology, so these regressions must hold.
    """

    def test_identity_wire_counterexample_no_longer_breaks_congruence(self):
        # The exact adversarial counterexample: f ~ f;id under the quotient, and that equality must
        # survive post-composition with g (deps must agree: 1 == 1, not 1 vs 0).
        f, g = _f(), _g()
        idB = identity_diagram(H2C)
        assert canonicalize(f) == canonicalize(f.then(idB))  # identity law
        assert canonicalize(f.then(g)) == canonicalize(f.then(idB).then(g))  # congruence
        assert len(f.then(g).apex.provenance.deps) == 1
        assert len(f.then(idB).then(g).apex.provenance.deps) == 1  # the wire no longer launders it

    def test_close_agrees_across_an_interposed_identity_wire(self):
        # f;g and (f;id);g are the same morphism; both must close to the SAME Reaction (P3/P4),
        # where before, (f;id);g crashed as "not a linear chain".
        f, g = _f(), _g()
        idB = identity_diagram(H2C)
        direct = f.then(g).close()
        through_wire = f.then(idB).then(g).close()
        assert direct == through_wire
        assert canonical_digest(direct) == canonical_digest(through_wire)

    def test_congruence_battery_left_and_right(self):
        # Several known-equal pairs, post-composed on both sides, must stay equal under the quotient.
        f, g = _f(), _g()
        idIn = identity_diagram(f.external_input())
        idOut = identity_diagram(f.external_output())
        equal_pairs = [
            (f, idIn.then(f)),          # left identity
            (f, f.then(idOut)),          # right identity
        ]
        for a, b in equal_pairs:
            assert canonicalize(a) == canonicalize(b)
            assert canonicalize(a.then(g)) == canonicalize(b.then(g))          # right-compose
            assert canonicalize(g.then(a)) == canonicalize(g.then(b))          # left-compose (g;a defined: g cod = H+H = f dom)


class TestConservationDecorationAgreesWithTheVerdict:
    """birdperson's cross-check: the additive decoration and the direct boundary count must agree.

    Two truths computing the same invariant by different routes, with no tripwire between them, is a
    latent divergence. On a saturated diagram, ``is_balanced`` must hold iff the verdict is CONSERVING.
    """

    def test_conserving_step_agrees(self):
        d = OpenChemDiagram.single_step(H2C, HH)  # H2 -> H + H, saturated, balanced
        assert d.is_saturated
        assert d.apex.conservation.is_balanced
        assert d.conservation_status() is ConservationStatus.CONSERVING

    def test_violating_step_agrees(self):
        d = OpenChemDiagram.single_step(Config.atoms("H"), Config.atoms("O"))  # H -> O, unbalanced
        assert d.is_saturated
        assert not d.apex.conservation.is_balanced
        assert d.conservation_status() is ConservationStatus.VIOLATED

    def test_composite_route_agrees(self):
        d = _f().then(_g())  # (H+H -> H2) ; (H2 -> H+H), saturated, balanced overall
        assert d.is_saturated
        assert d.apex.conservation.is_balanced
        assert d.conservation_status() is ConservationStatus.CONSERVING
