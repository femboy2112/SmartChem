"""
The core data structures use opaque labels; this file checks that narrow syntactic fact.

The claim is easy to overstate. Standard-library imports and opaque strings do not give a
chemical category the semantics of radiation or circuits. These tests reuse the structural
types for four non-chemical-shaped examples and check only what the implementation represents:

    radiation   a zero-atom token and a state-labelled inventory transition
    circuits    equal or unequal inventories of typed charge-carrier tokens
    networks    labelled graphs that distinguish two wiring-like encodings
    electrodes  balanced half-reaction inventories with carriers on one side

They do not provide electromagnetic energy, boundary ports, current as charge per time,
Kirchhoff node equations, component terminal semantics or a network solver.

Historical note: the first three examples were once presented as evidence that "circuits
work." The electrode example exposed the narrower truth. Balanced carrier counts cannot
detect that an electron was wrongly entered in the atom inventory, because the same wrong
entry cancels on both sides. An asymmetric inventory case is therefore necessary to test the
typed-carrier distinction, even though it still does not establish circuit behavior.

The boundary is explicit: no oracle in this repository can value a represented excitation
or zero-atom quantum token, and each declines rather than returning a confident zero. The
syntax can retain those distinctions while the physical model remains unimplemented.
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
    reaction_residue,
    tensor_obj,
)
from smartchem.oracle.base import carries_unmodelled_physics
from smartchem.oracle.heuristic import HeuristicOracle


# ======================================================================================
# Radiation
# ======================================================================================
class TestRadiationShapedSyntax:
    """
    The structure can distinguish a state change and a zero-atom token. It assigns neither
    a photon energy nor antenna, field, momentum, polarization or emission semantics.
    """

    def test_a_quantum_token_has_no_atom_inventory_or_charge(self):
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

    def test_an_emission_shaped_inventory_transition_is_structurally_allowed(self):
        """
        The case that motivated the `state` field. Before it, the only way to mark an
        excited atom was to change its symbol -- which changes `formula`, so emission was
        rejected as atom-inventory-violating. Passing this constructor check does not supply
        a radiative Hamiltonian or establish that the transition is physically allowed.
        """
        excited = Molecule.atom("Na", state="excited")
        ground = Molecule.atom("Na")
        photon = Molecule.quantum("hv")

        emission = Reaction(Config.of(excited), Config.of(ground, photon), name="emission")
        assert conserves(emission)

        absorption = Reaction(Config.of(ground, photon), Config.of(excited))
        assert conserves(absorption)
        assert emission.dom == absorption.cod and emission.cod == absorption.dom

    def test_state_is_not_in_the_conserved_inventory_but_atom_labels_are(self):
        """Here, "free" means structurally unconserved, not zero energy or zero work."""
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

    def test_two_state_token_transitions_compose(self):
        """Sequential history retains two radiation-shaped transitions without pricing them."""
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
class TestOpaqueCircuitSyntax:
    """
    These examples count typed carrier objects and compare labelled graphs. A carrier count
    is not current (charge per time), and no object here denotes a boundary node or enforces
    Kirchhoff's current law.
    """

    @staticmethod
    def _carriers(n):
        return Config(tuple(Molecule.carrier("e-", charge=-1) for _ in range(n)))

    def test_equal_typed_carrier_inventories_are_conserved(self):
        transition = Reaction(
            self._carriers(3), self._carriers(3), name="balanced carrier inventory"
        )
        assert conserves(transition)

    def test_unequal_typed_carrier_inventories_are_rejected(self):
        """This rejects missing charge tokens; it does not evaluate a current balance."""
        with pytest.raises(ConservationError):
            Reaction(self._carriers(3), self._carriers(2))

    def test_labelled_graphs_distinguish_two_wiring_like_encodings(self):
        """
        Bond edges retain graph topology, so these encodings with the same labels differ.
        Component labels are treated as vertices with no terminals or constitutive laws;
        calling the examples "series" and "parallel" is mnemonic, not circuit validation.
        """
        parts = ("R", "C", "GND")
        series = Molecule(parts, frozenset({Bond(0, 1), Bond(1, 2)}))
        parallel = Molecule(parts, frozenset({Bond(0, 2), Bond(1, 2)}))
        assert series.formula == parallel.formula        # same bill of materials
        assert series != parallel                        # different networks
        rewire = Reaction(Config.of(series), Config.of(parallel), name="rewire")
        assert conserves(rewire)

    def test_the_same_labelled_graph_in_any_vertex_order_compares_equal(self):
        """Canonicalisation compares the encoding as a labelled graph."""
        a = Molecule(("R", "L", "C"), frozenset({Bond(0, 1), Bond(1, 2)}))
        b = Molecule(("C", "L", "R"), frozenset({Bond(2, 1), Bond(1, 0)}))
        assert a.canonical() == b.canonical()

    def test_object_product_counts_two_graph_components(self):
        """The formal object product is multiset union, not parallel circuit composition."""
        stage = Molecule(("R", "C"), frozenset({Bond(0, 1)}))
        both = tensor_obj(Config.of(stage), Config.of(stage))
        assert both.formula == {"R": 2, "C": 2}
        assert conserves(identity(both))


# ======================================================================================
# Electrodes -- the case the balanced tests above structurally could not fail
# ======================================================================================
class TestAnElectrodeIsAMorphism:
    """
    The regression test for the defect #22 shipped, and the reason it survived review.

    Every circuit-shaped test written for #22 had the SAME carrier count on both sides --
    ``3 e- -> 3 e-``. That checks only equality of the encoded inventories. It cannot detect
    an electron wrongly entered in the atom ledger, because the same wrong entry appears on
    both sides and cancels. The tests were all consistent with the broader historical claim
    that "circuits work," but did not establish it.

    An electrode is where the counts do not match: electrons are produced at the anode and
    consumed at the cathode, and only the external circuit makes the totals agree. That is
    the entire point of a battery, and it was never tried until the AA cell was attempted.

    The lesson generalises past this bug and is the reason this class exists rather than a
    one-line fix: a balanced example cannot test whether a carrier belongs in the correct
    inventory. Test the asymmetric case before claiming typed-carrier bookkeeping works.
    """

    # an alkaline AA cell: Zn/MnO2, nominally 1.5 V
    Zn = Molecule.atom("Zn")
    OH = Molecule(("O", "H"), frozenset({Bond(0, 1)}), charge=-1)
    H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
    ZnO = Molecule(("Zn", "O"), frozenset({Bond(0, 1)}))
    MnO2 = Molecule(("Mn", "O", "O"), frozenset({Bond(0, 1), Bond(0, 2)}))
    Mn2O3 = Molecule(("Mn", "Mn", "O", "O", "O"),
                     frozenset({Bond(0, 2), Bond(0, 3), Bond(1, 3), Bond(1, 4)}))
    e = Molecule.carrier("e-", charge=-1)

    def test_a_carrier_is_not_matter(self):
        """The one-line statement of the defect."""
        assert Molecule.carrier("e-", charge=-1).formula == {}
        assert Molecule.carrier("e-", charge=-1).charge == -1
        # the idiom #22 shipped, and why it was wrong
        assert Molecule.atom("e", charge=-1).formula == {"e": 1}

    def test_the_anode_half_reaction_constructs(self):
        """Zn + 2 OH- -> ZnO + H2O + 2 e-: carriers on ONE side only."""
        anode = Reaction(Config.of(self.Zn, self.OH, self.OH),
                         Config.of(self.ZnO, self.H2O, self.e, self.e), name="anode")
        assert conserves(anode)
        assert anode.dom.charge == -2 and anode.cod.charge == -2

    def test_the_cathode_half_reaction_constructs(self):
        """2 MnO2 + H2O + 2 e- -> Mn2O3 + 2 OH-: carriers consumed, not produced."""
        cathode = Reaction(
            Config.of(self.MnO2, self.MnO2, self.H2O, self.e, self.e),
            Config.of(self.Mn2O3, self.OH, self.OH), name="cathode")
        assert conserves(cathode)
        assert cathode.dom.charge == -2 and cathode.cod.charge == -2

    def test_the_old_idiom_still_fails_so_the_test_is_not_vacuous(self):
        """
        Guard against a green that means nothing. If ``Molecule.atom("e", ...)`` ever
        started conserving too, the two tests above would pass for the wrong reason and
        this file would stop testing the distinction it exists for.
        """
        wrong = Molecule.atom("e", charge=-1)
        with pytest.raises(ConservationError):
            Reaction(Config.of(self.Zn, self.OH, self.OH),
                     Config.of(self.ZnO, self.H2O, wrong, wrong))

    def test_charge_is_still_enforced_on_carriers(self):
        """
        Freeing carriers from the mass ledger must not free them from the charge ledger,
        or the fix would have replaced one silent hole with a worse one.
        """
        with pytest.raises(ConservationError):
            Reaction(Config.of(self.Zn, self.OH, self.OH),
                     Config.of(self.ZnO, self.H2O, self.e))     # one electron short

    def test_scheduled_half_reaction_histories_have_the_expected_residue(self):
        """
        Each half-reaction is padded by the implementation's deterministic left-first
        ``scheduled_product`` so the histories compose. Multiset residue then removes the
        carriers, water and hydroxide that occur on both endpoints. This is a typed inventory
        identity; it does not model an external circuit, current path or load.
        """
        anode = Reaction(Config.of(self.Zn, self.OH, self.OH),
                         Config.of(self.ZnO, self.H2O, self.e, self.e))
        cathode = Reaction(
            Config.of(self.MnO2, self.MnO2, self.H2O, self.e, self.e),
            Config.of(self.Mn2O3, self.OH, self.OH))
        closed = (
            anode.scheduled_product(identity(Config.of(self.MnO2, self.MnO2)))
            .then(identity(Config.of(self.ZnO)).scheduled_product(cathode))
        )
        assert conserves(closed)

        consumed, produced = reaction_residue(closed)
        # every carrier and every ion is a spectator of the overall cell reaction
        assert consumed == Config.of(self.Zn, self.MnO2, self.MnO2)
        assert produced == Config.of(self.ZnO, self.Mn2O3)

    def test_the_cell_reaction_conserves_without_mentioning_electrons(self):
        """The overall reaction: the residue above, standing on its own."""
        cell = Reaction(Config.of(self.Zn, self.MnO2, self.MnO2),
                        Config.of(self.ZnO, self.Mn2O3), name="AA cell")
        assert conserves(cell)
        assert cell.dom.charge == 0 and cell.cod.charge == 0


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

    def test_a_symbol_that_is_not_an_element_is_declined(self):
        """
        Found while measuring the species cache (#18). The heuristic oracle's free-atom
        branch returned 0.0 +/- 0.0 eV for ANY unbonded atom -- including "Xx", which is
        not an element.

        The convention "a free atom is this oracle's zero" is exact for elements it knows
        and is not a convention at all for a symbol naming nothing. Symbols are opaque by
        design, which is what makes the category domain-neutral, so nothing upstream rules
        this out and the oracle has to.

        Directly relevant to #22: the same opacity that lets an object be labelled "R" or
        "GND" is what lets a fictional element through, so the two are one issue.
        """
        oracle = HeuristicOracle()
        assert oracle.energy(Molecule.atom("Na")) is not None
        assert oracle.energy(Molecule.atom("Xx")) is None
        assert oracle.energy(Molecule.atom("GND")) is None

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
    A narrow dependency check, kept alongside the opaque-label examples. It does not confer
    non-chemical semantics. Checked against the parse tree rather than by grepping text, so
    a comment mentioning an atom cannot fail it and a real import cannot hide from it.
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

    assert modules <= {"__future__", "collections", "dataclasses", "functools", "itertools",
                       "math", "typing"}, f"category.py grew a dependency: {modules}"
