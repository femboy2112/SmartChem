"""OPERATION XXI section 7 -- STRUCTURAL composition laws of the categorical -> kernel bridge.

Ooh yeah, does the bridge respect how diagrams COMPOSE?  These pin STOICHIOMETRIC / identity composition only: which
species exist, which reaction columns exist, that E N = 0, and the exact N 1 net.  They do NOT claim a numerical-dynamics
functor: every bridged reaction here carries ``RATE_UNKNOWN`` (the kernel will not integrate it), so a kinetic reading
of "composition" -- does a composed rate law equal the composite of the parts' rate laws? -- is UNDEFINED / PARTIAL
at this layer and deliberately untested.  A successful bridge is a conservation + identity certificate, nothing more.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_kernel import RATE_UNKNOWN, ConservationError
from experiments.sandbox_foundation.open_diagram_bridge import (
    BridgeError,
    _exact_net_production,
    _matrix_column_sums,
    bridge_to_kernel,
    build_demo_diagram,
    column_summed_EN,
    glue_at,
)
from smartchem.category import Config, Molecule
from smartchem.open_chem_diagram import OpenChemDiagram, identity_diagram, species_key
from smartchem.smiles import parse_smiles

ACETIC = parse_smiles("CC(=O)O")
BICARB = parse_smiles("OC(=O)[O-]")
ACETATE = parse_smiles("CC(=O)[O-]")
CARBONIC = parse_smiles("OC(=O)O")
CO2 = parse_smiles("O=C=O")
WATER = parse_smiles("O")
HYDROXIDE = parse_smiles("[OH-]")
ETHANOL = parse_smiles("CCO")
DME = parse_smiles("COC")


def _step(source: tuple, target: tuple, gid: str) -> OpenChemDiagram:
    return OpenChemDiagram.single_step(Config.of(*source), Config.of(*target), generator_id=gid)


def _s1() -> OpenChemDiagram:
    return _step((ACETIC, BICARB), (ACETATE, CARBONIC), "proton_transfer")


def _s2() -> OpenChemDiagram:
    return _step((CARBONIC,), (CO2, WATER), "dehydration")


def _s3() -> OpenChemDiagram:
    return _step((ACETATE, WATER), (ACETIC, HYDROXIDE), "hydrolysis")      # balanced: C2H5O3-, charge -1 both sides


def _sig(diagram: OpenChemDiagram) -> tuple:
    return bridge_to_kernel(diagram).signature()


def _three_step_chain() -> list:
    """The same three generators glued three genuinely different ways (a -> b via carbonic, a -> c via acetate,
    b -> c via water), each a different raw presentation of the SAME hyperedge set."""
    a, b, c = _s1(), _s2(), _s3()
    left = glue_at(glue_at(glue_at(a.tensor(b).tensor(c), CARBONIC), ACETATE), WATER)       # (a x b) x c
    right = glue_at(glue_at(glue_at(a.tensor(b.tensor(c)), WATER), CARBONIC), ACETATE)      # a x (b x c), other glue order
    shuffled = glue_at(glue_at(glue_at(c.tensor(a).tensor(b), ACETATE), WATER), CARBONIC)   # c x a x b
    return [left, right, shuffled]


# ======================================================================================
# identity
# ======================================================================================
class TestIdentity:
    def test_bridging_leaves_the_conservation_decoration_intact(self):
        d = build_demo_diagram()
        before = (d.core.decoration, d.core.decoration.net, d.net_reaction().dom, d.net_reaction().cod)
        bridged = bridge_to_kernel(d)
        assert (d.core.decoration, d.core.decoration.net, d.net_reaction().dom, d.net_reaction().cod) == before
        assert d.core.decoration.is_balanced
        assert bridged.diagram_net == bridged.kernel_net == () == tuple(d.core.decoration.net)

    def test_composing_with_an_identity_wire_changes_nothing(self):
        s1 = _s1()
        cod_wire = identity_diagram(Config.of(ACETATE, CARBONIC))
        dom_wire = identity_diagram(Config.of(ACETIC, BICARB))
        assert _sig(s1.then(cod_wire)) == _sig(s1) == _sig(dom_wire.then(s1))
        assert bridge_to_kernel(s1.then(cod_wire)).diagram_net == bridge_to_kernel(s1).diagram_net == ()

    def test_a_bare_wire_bridges_to_species_and_no_reactions(self):
        wire = bridge_to_kernel(identity_diagram(Config.of(ACETIC, BICARB)))
        assert len(wire.system.species) == 2 and wire.system.reactions == ()
        assert wire.diagram_net == wire.kernel_net == ()


# ======================================================================================
# associativity of gluing
# ======================================================================================
class TestAssociativity:
    def test_tensor_association_and_glue_order_do_not_change_the_signature(self):
        presentations = _three_step_chain()
        assert all(p.is_saturated for p in presentations)
        # raw presentations genuinely differ (>= 2 distinct cores; (a x b) x c and a x (b x c) with the SAME wiring are
        # raw-EQUAL, i.e. tensor is already strictly associative -- the glue order / tensor order supply the difference)
        assert len({p.core for p in presentations}) >= 2
        sigs = [_sig(p) for p in presentations]
        assert sigs[0] == sigs[1] == sigs[2]
        assert len(sigs[0][1]) == 3 and len(sigs[0][0]) == 7             # 3 columns; 7 species (HYDROXIDE joins the 6)

    def test_the_kernel_model_certificate_is_identical_across_presentations(self):
        certs = {bridge_to_kernel(p).system._model_certificate for p in _three_step_chain()}
        assert len(certs) == 1

    def test_the_exact_net_is_independent_of_how_it_was_glued(self):
        nets = []
        for p in _three_step_chain():
            system = bridge_to_kernel(p).system
            nets.append(dict(zip((sp.name for sp in system.species), _exact_net_production(system))))
        assert nets[0] == nets[1] == nets[2]


# ======================================================================================
# tensor / disjoint parallel composition
# ======================================================================================
class TestTensor:
    def test_disjoint_subdiagrams_bridge_to_the_union(self):
        demo = build_demo_diagram()
        iso = _step((ETHANOL,), (DME,), "isomerise")
        both = bridge_to_kernel(demo.tensor(iso))
        sig_demo, sig_iso, sig_both = _sig(demo), _sig(iso), both.signature()
        assert sig_both[0] == sig_demo[0] | sig_iso[0]
        assert sig_both[1] == sig_demo[1] | sig_iso[1]
        assert len(both.system.species) == 6 + 2 and len(both.system.reactions) == 3
        assert not (sig_demo[0] & sig_iso[0])                              # genuinely disjoint

    def test_tensor_is_commutative_on_the_signature(self):
        demo, iso = build_demo_diagram(), _step((ETHANOL,), (DME,), "isomerise")
        assert _sig(demo.tensor(iso)) == _sig(iso.tensor(demo))

    def test_distinct_parallel_reactions_are_not_merged_into_one_column(self):
        # two hyperedges with IDENTICAL stoichiometry but different generator ids are two kernel reactions.
        one = _step((CARBONIC,), (CO2, WATER), "dehydration_a")
        two = _step((CARBONIC,), (CO2, WATER), "dehydration_b")
        bridged = bridge_to_kernel(one.tensor(two))
        assert [r.name for r in bridged.system.reactions] == ["dehydration_a", "dehydration_b"]
        assert bridged.system.reactions[0].stoich == bridged.system.reactions[1].stoich
        assert bridged.system.N.shape[1] == 2
        assert len(bridged.system.species) == 3                           # shared species are shared; columns are not
        assert _exact_net_production(bridged.system) == tuple(2 * c for c in _exact_net_production(bridge_to_kernel(one).system))

    def test_a_repeated_generator_id_is_still_refused_not_silently_merged(self):
        one = _step((CARBONIC,), (CO2, WATER), "same")
        with pytest.raises(BridgeError, match="duplicate generator_id"):
            bridge_to_kernel(one.tensor(_step((CARBONIC,), (CO2, WATER), "same")))


# ======================================================================================
# conservation under gluing
# ======================================================================================
class TestConservationUnderGluing:
    @pytest.mark.parametrize("which", [0, 1, 2])
    def test_every_saturated_glued_presentation_bridges_to_a_system_with_EN_zero(self, which):
        bridged = bridge_to_kernel(_three_step_chain()[which])
        system = bridged.system
        assert not (system.E @ system.N).any()                            # the kernel's float matrices (small ints: exact)
        assert _matrix_column_sums(system) == column_summed_EN(system.reactions) == {}
        assert bridged.diagram_net == bridged.kernel_net == ()

    def test_gluing_removes_internal_species_from_the_net_but_not_from_the_system(self):
        glued = bridge_to_kernel(glue_at(_s1().tensor(_s2()), CARBONIC))
        carbonic = glued.species_of[species_key(CARBONIC)]
        assert carbonic in glued.system.species
        assert _exact_net_production(glued.system)[glued.system.species.index(carbonic)] == 0

    def test_gluing_an_unbalanced_step_into_a_balanced_network_is_still_refused(self):
        bad = _step((CO2, WATER), (ETHANOL,), "bad_hydration")             # no such balance: kernel must refuse
        with pytest.raises(ConservationError, match="bad_hydration"):
            bridge_to_kernel(glue_at(_s1().tensor(_s2()).tensor(bad), CO2))


# ======================================================================================
# port correspondence
# ======================================================================================
class TestPortCorrespondence:
    def test_a_glued_internal_port_maps_to_one_shared_species(self):
        glued = build_demo_diagram()
        bridged = bridge_to_kernel(glued)
        token = species_key(CARBONIC)
        carbonic = bridged.species_of[token]
        assert glued.core.node_ports.count(token) == 1                    # one internal node after the glue
        users = [r.name for r in bridged.system.reactions if carbonic in {s for s, _ in r.stoich}]
        assert users == ["dehydration", "proton_transfer"]                # BOTH steps point at the very same Species...
        objs = [s for r in bridged.system.reactions for s, _ in r.stoich if s == carbonic]
        assert len(objs) == 2 and objs[0] is objs[1]
        assert len([sp for sp in bridged.system.species if sp.name == carbonic.name]) == 1    # ...not two

    def test_unglued_two_nodes_still_map_to_one_species(self):
        # control: WITHOUT the glue the diagram has TWO nodes for carbonic acid (an output of s1, an input of s2),
        # yet the kernel sees one species -- the species is the token, not the node.
        unglued = _s1().tensor(_s2())
        assert unglued.core.node_ports.count(species_key(CARBONIC)) == 2
        bridged = bridge_to_kernel(unglued)
        assert len(bridged.system.species) == 6
        assert bridged.species_of[species_key(CARBONIC)] in bridged.system.species

    def test_registry_and_species_maps_are_in_bijection(self):
        for presentation in _three_step_chain():
            bridged = bridge_to_kernel(presentation)
            assert set(bridged.species_of) == {t for t, _ in presentation.registry}
            assert len(set(bridged.species_of.values())) == len(bridged.species_of)


# ======================================================================================
# two decompositions of one net transformation
# ======================================================================================
class TestDecompositions:
    """CH3COOH + HCO3-  ->  CH3COO- + CO2 + H2O, as a one-step mechanism and as the two-step demo."""

    @staticmethod
    def _one_step() -> OpenChemDiagram:
        return _step((ACETIC, BICARB), (ACETATE, CO2, WATER), "direct")

    @staticmethod
    def _net(diagram: OpenChemDiagram) -> dict:
        bridged = bridge_to_kernel(diagram)
        return {sp.name: n for sp, n in zip(bridged.system.species, _exact_net_production(bridged.system)) if n}

    def test_different_mechanisms_have_the_same_net_transformation(self):
        two_step, one_step = build_demo_diagram(), self._one_step()
        assert self._net(two_step) == self._net(one_step)
        assert two_step.net_reaction().dom == one_step.net_reaction().dom
        assert two_step.net_reaction().cod == one_step.net_reaction().cod

    def test_but_the_mechanism_is_part_of_the_kernel_signature(self):
        # HONEST scope: the reaction SET (and the intermediate species) is kernel identity, so two mechanisms for one
        # net equation do NOT share a kernel_signature -- only the net and the E N = 0 certificate are shared.
        assert _sig(build_demo_diagram()) != _sig(self._one_step())
        assert len(_sig(self._one_step())[0]) == 5 and len(_sig(self._one_step())[1]) == 1

    def test_different_ASSEMBLIES_of_one_mechanism_do_share_the_signature(self):
        sigs = {_sig(p) for p in _three_step_chain()}
        sigs |= {_sig(glue_at(_s1().tensor(_s2()), CARBONIC)), _sig(glue_at(_s2().tensor(_s1()), CARBONIC)),
                 _sig(_s1().tensor(_s2()))}
        assert len({s for s in sigs if len(s[1]) == 2}) == 1              # all the 2-step presentations agree
        assert len({s for s in sigs if len(s[1]) == 3}) == 1              # all the 3-step presentations agree


# ======================================================================================
# catalysts
# ======================================================================================
class TestCatalyst:
    def test_a_step_whose_species_all_cancel_is_refused(self):
        loop = _step((WATER,), (WATER,), "noop")
        with pytest.raises(BridgeError, match="zero net stoichiometry"):
            bridge_to_kernel(loop)
        pure_catalyst = _step((Molecule.atom("H", charge=1),), (Molecule.atom("H", charge=1),), "cat_loop")
        with pytest.raises(BridgeError, match="zero net stoichiometry"):
            bridge_to_kernel(pure_catalyst)

    def test_a_genuine_catalyst_is_absent_from_the_net_column_but_the_reaction_is_retained(self):
        proton = Molecule.atom("H", charge=1)
        ester = parse_smiles("CC(=O)OCC")
        fischer = _step((ACETIC, ETHANOL, proton), (ester, WATER, proton), "fischer")
        bridged = bridge_to_kernel(fischer)
        (reaction,) = bridged.system.reactions
        catalyst = bridged.species_of[species_key(proton)]
        assert reaction.name == "fischer"                                  # the reaction is retained
        assert catalyst not in {s for s, _ in reaction.stoich}             # ...with the catalyst out of the net column
        assert len(reaction.stoich) == 4 and all(abs(c) == 1 for _, c in reaction.stoich)
        assert catalyst in bridged.system.species                          # but still a declared species
        assert _exact_net_production(bridged.system)[bridged.system.species.index(catalyst)] == 0
        assert _matrix_column_sums(bridged.system) == {}
        assert reaction.rate_law is RATE_UNKNOWN       # catalysis as a KINETIC effect (rate dependence on H+) is undefined here

    def test_the_catalytic_and_uncatalysed_steps_share_a_column_but_not_a_species_set(self):
        proton = Molecule.atom("H", charge=1)
        ester = parse_smiles("CC(=O)OCC")
        with_cat = bridge_to_kernel(_step((ACETIC, ETHANOL, proton), (ester, WATER, proton), "fischer"))
        without = bridge_to_kernel(_step((ACETIC, ETHANOL), (ester, WATER), "fischer"))

        def column(bridged) -> set:
            return {(s.name, c) for s, c in bridged.system.reactions[0].stoich}

        assert column(with_cat) == column(without)
        assert len(with_cat.system.species) == len(without.system.species) + 1
