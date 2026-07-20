"""
The categorical layer is not about chemistry, and this file is the evidence.

The claim is easy to make and easy to get wrong. An audit can confirm that `category.py`
imports only the standard library and that atom symbols are opaque strings, and both of
those were true while the structure still could not express a radiating antenna -- because
the thing that foreclosed it was not an import, it was that the conserved signature and
the state label were the same field.

So this file does not audit. It instantiates the category on three systems that are not
chemistry and runs the real laws over them:

    radiation   an object carrying energy and no matter, and emission as a morphism
    circuits    Kirchhoff's current law as the conservation the constructor enforces
    networks    a labelled graph whose vertices are components and whose edges are wires

If any of these stopped working, the layer would have quietly become chemistry-only.

The boundary is here too, and stated rather than implied: the *structure* hosts these
systems, and the *energy models* do not. No oracle in this repository can price an
excitation or a photon, and each declines rather than returning a confident zero. That
gap is real and is the honest next piece of work; a category that can express a thing its
oracles cannot value is exactly the right way round for a layer whose whole design claim
is that the two are independent.
"""
from __future__ import annotations

import ast

import pytest

from smartchem.category import (
    Bond,
    Config,
    ConservationError,
    Molecule,
    Reaction,
    conserves,
    identity,
    tensor_obj,
)
from smartchem.oracle.base import carries_unmodelled_physics
from smartchem.oracle.heuristic import HeuristicOracle


# ======================================================================================
# Radiation
# ======================================================================================
class TestRadiationIsExpressible:
    """
    An antenna is the same matter in a different energy state, plus energy leaving. Both
    halves of that need to be sayable.
    """

    def test_a_quantum_carries_energy_and_no_matter(self):
        photon = Molecule.quantum("hv")
        assert photon.formula == {}
        assert photon.charge == 0
        # it contributes nothing to a configuration's conserved signature
        alone = Config.of(Molecule.atom("Na"))
        with_photon = Config.of(Molecule.atom("Na"), photon)
        assert alone.formula == with_photon.formula
        assert alone.charge == with_photon.charge
        # but it is still a distinct object: the configurations are NOT equal
        assert alone != with_photon

    def test_emission_is_a_legal_morphism(self):
        """
        The case that motivated the `state` field. Before it, the only way to mark an
        excited atom was to change its symbol -- which changes `formula`, so emission was
        rejected as mass-violating when no mass had gone anywhere.
        """
        excited = Molecule.atom("Na", state="excited")
        ground = Molecule.atom("Na")
        photon = Molecule.quantum("hv")

        emission = Reaction(Config.of(excited), Config.of(ground, photon), name="emission")
        assert conserves(emission)

        absorption = Reaction(Config.of(ground, photon), Config.of(excited))
        assert conserves(absorption)
        assert emission.dom == absorption.cod and emission.cod == absorption.dom

    def test_changing_state_is_free_but_changing_matter_is_not(self):
        """The separation the field exists to create, asserted from both sides."""
        excited = Molecule.atom("Na", state="excited")
        ground = Molecule.atom("Na")
        assert excited != ground                            # distinct objects
        assert excited.formula == ground.formula            # same conserved signature

        Reaction(Config.of(excited), Config.of(ground))     # state change: allowed
        with pytest.raises(ConservationError):
            Reaction(Config.of(ground), Config.of(Molecule.atom("K")))   # matter: not

    def test_state_survives_canonicalisation(self):
        """Canonical relabelling reorders atoms; it must not launder the state away."""
        excited = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}),
                           state="excited")
        assert excited.canonical().state == "excited"
        assert excited.canonical() != Molecule(("O", "H", "H"),
                                               frozenset({Bond(0, 1), Bond(0, 2)}))

    def test_two_states_of_one_species_order_deterministically(self):
        """
        `Config` sorts its species to a canonical tuple. If `state` were left out of that
        sort key, two species differing only in state would tie, the stable sort would
        preserve input order, and `Config.of(a, b) != Config.of(b, a)` -- silently
        breaking every equality that rides on configurations.
        """
        ground = Molecule.atom("Na")
        excited = Molecule.atom("Na", state="excited")
        assert Config.of(ground, excited) == Config.of(excited, ground)

    def test_a_cascade_composes(self):
        """Two emissions in sequence: the structure has to carry a multi-step process."""
        top = Molecule.atom("Na", state="3p")
        mid = Molecule.atom("Na", state="3s*")
        low = Molecule.atom("Na")
        first = Reaction(Config.of(top), Config.of(mid, Molecule.quantum("hv1")))
        second = Reaction(Config.of(mid, Molecule.quantum("hv1")),
                          Config.of(low, Molecule.quantum("hv1"), Molecule.quantum("hv2")))
        cascade = first.then(second)
        assert conserves(cascade)
        assert cascade.dom == Config.of(top)


# ======================================================================================
# Circuits
# ======================================================================================
class TestCircuitsAreExpressible:
    """
    Kirchhoff's current law is a conservation law over a graph, which is the same shape
    as mass conservation -- so the constructor that makes a mass-violating reaction
    unconstructible makes a charge-non-conserving node unconstructible too, unchanged.
    """

    @staticmethod
    def _carriers(n):
        return Config(tuple(Molecule.atom("e", charge=-1) for _ in range(n)))

    def test_kirchhoff_current_law_is_the_conservation_already_enforced(self):
        node = Reaction(self._carriers(3), self._carriers(3), name="KCL at a node")
        assert conserves(node)

    def test_a_node_that_loses_current_is_unconstructible(self):
        """Not "detected and reported" -- it cannot be built, exactly like Fe + O + Cl."""
        with pytest.raises(ConservationError):
            Reaction(self._carriers(3), self._carriers(2))

    def test_components_and_wires_form_an_object_with_topology(self):
        """
        The load-bearing design decision, restated for circuits: if an object were a bag
        of components, every rewiring would be an endomorphism and a topology change could
        not be a morphism at all. A series RC and a parallel RC hold the SAME parts.
        """
        parts = ("R", "C", "GND")
        series = Molecule(parts, frozenset({Bond(0, 1), Bond(1, 2)}))
        parallel = Molecule(parts, frozenset({Bond(0, 2), Bond(1, 2)}))
        assert series.formula == parallel.formula        # same bill of materials
        assert series != parallel                        # different networks
        rewire = Reaction(Config.of(series), Config.of(parallel), name="rewire")
        assert conserves(rewire)

    def test_the_same_network_built_in_any_node_order_compares_equal(self):
        """Canonicalisation is a graph-isomorphism test; it never knew this was chemistry."""
        a = Molecule(("R", "L", "C"), frozenset({Bond(0, 1), Bond(1, 2)}))
        b = Molecule(("C", "L", "R"), frozenset({Bond(2, 1), Bond(1, 0)}))
        assert a.canonical() == b.canonical()

    def test_subcircuits_tensor(self):
        """Two independent stages side by side -- the monoidal structure, on circuits."""
        stage = Molecule(("R", "C"), frozenset({Bond(0, 1)}))
        both = tensor_obj(Config.of(stage), Config.of(stage))
        assert both.formula == {"R": 2, "C": 2}
        assert conserves(identity(both))


# ======================================================================================
# The boundary
# ======================================================================================
class TestTheOraclesDeclineWhatTheyCannotValue:
    """
    The structure reaches further than the energy models, and that asymmetry has to be
    loud. An oracle that silently returned 0.0 +/- 0.0 eV for an excited atom would be
    the one defect this repository refuses outright -- and worse, it would come out
    *coincidentally right* for an emission, because the excitation energy it does not
    know and the photon energy it also does not know cancel.
    """

    def test_an_excitation_is_declined_rather_than_priced_at_zero(self):
        oracle = HeuristicOracle()
        assert oracle.energy(Molecule.atom("Na")) is not None      # ground state: fine
        assert oracle.energy(Molecule.atom("Na", state="excited")) is None

    def test_a_quantum_is_declined_rather_than_priced_at_zero(self):
        assert HeuristicOracle().energy(Molecule.quantum("hv")) is None

    def test_the_guard_names_exactly_the_two_unmodelled_cases(self):
        assert carries_unmodelled_physics(Molecule.quantum("hv"))
        assert carries_unmodelled_physics(Molecule.atom("Na", state="excited"))
        assert not carries_unmodelled_physics(Molecule.atom("Na"))
        assert not carries_unmodelled_physics(
            Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
        )


# ======================================================================================
# The structural guarantee
# ======================================================================================
def test_the_categorical_core_imports_no_chemistry():
    """
    Weaker than the tests above, and kept anyway: they show the structure CAN host other
    domains, this shows nothing has quietly crept in that would couple it to one. Checked
    against the parse tree rather than by grepping text, so a comment mentioning an atom
    cannot fail it and a real import cannot hide from it.
    """
    import smartchem.category as category

    with open(category.__file__) as fh:
        tree = ast.parse(fh.read())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add((node.module or "").split(".")[0])

    assert modules <= {"__future__", "collections", "dataclasses", "itertools", "math",
                       "typing"}, f"category.py grew a dependency: {modules}"
