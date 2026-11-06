"""OPERATION XIX section 5 -- pins for the executable categorical -> physical bridge.

Ooh yeah, the diagram goes in, the kernel proves it.  Five headline pins (a)-(e) from the brief, then the fail-closed
refusals, each a hostile test whose control would FAIL on a bridge that trusts the diagram instead of the kernel.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from experiments.sandbox_foundation.general_coupled import CoupledError, InterfaceTransfer
from experiments.sandbox_foundation.general_kernel import (
    RATE_UNKNOWN,
    ChemicalSystem,
    ConservationError,
    MassActionIrreversible,
    Phase,
    Reaction,
)
from experiments.sandbox_foundation.open_diagram_bridge import (
    BridgeCrossCheckError,
    BridgeError,
    _build_species,
    bridge_to_kernel,
    build_demo_diagram,
    column_summed_EN,
    glue_at,
    substance_of,
)
from smartchem.category import Config, Molecule
from smartchem.open_chem_diagram import OpenChemDiagram, species_key
from smartchem.smiles import parse_smiles

ACETIC = parse_smiles("CC(=O)O")
BICARB = parse_smiles("OC(=O)[O-]")
ACETATE = parse_smiles("CC(=O)[O-]")
CARBONIC = parse_smiles("OC(=O)O")
CO2 = parse_smiles("O=C=O")
WATER = parse_smiles("O")
ETHANOL = parse_smiles("CCO")
DME = parse_smiles("COC")


def _s1() -> OpenChemDiagram:
    return OpenChemDiagram.single_step(Config.of(ACETIC, BICARB), Config.of(ACETATE, CARBONIC),
                                       generator_id="proton_transfer")


def _s2() -> OpenChemDiagram:
    return OpenChemDiagram.single_step(Config.of(CARBONIC), Config.of(CO2, WATER), generator_id="dehydration")


def _by_name(bridged, fragment: str):
    return next(sp for sp in bridged.system.species if sp.name.startswith(fragment))


# ======================================================================================
# (a) the demo bridges and the kernel proves E N = 0
# ======================================================================================
class TestADemoBridgesAndKernelProves:
    def test_demo_shape(self):
        bridged = bridge_to_kernel(build_demo_diagram())
        system = bridged.system
        assert isinstance(system, ChemicalSystem)
        assert len(system.species) == 6
        assert system.component_labels == ("C", "H", "O", "charge")
        assert [r.name for r in system.reactions] == ["dehydration", "proton_transfer"]
        assert system.E.shape == (4, 6) and system.N.shape == (6, 2)

    def test_kernel_EN_is_exactly_zero(self):
        system = bridge_to_kernel(build_demo_diagram()).system
        assert not np.any(system.E @ system.N)
        # the exact-integer authority the kernel itself proved at construction:
        for k in range(len(system.reactions)):
            for c in range(len(system.component_labels)):
                assert sum(system._E_int[c][i] * system._N_int[i][k] for i in range(6)) == 0

    def test_stoichiometry_is_the_hyperedge_counter(self):
        bridged = bridge_to_kernel(build_demo_diagram())
        reactions = {r.name: dict((s.name, c) for s, c in r.stoich) for r in bridged.system.reactions}
        assert reactions["proton_transfer"] == {"C2H4O2(aq)": -1, "CHO3-(aq)": -1, "C2H3O2-(aq)": 1, "CH2O3(aq)": 1}
        assert reactions["dehydration"] == {"CH2O3(aq)": -1, "CO2(aq)": 1, "H2O(aq)": 1}

    def test_maps_are_complete_and_consistent(self):
        d = build_demo_diagram()
        bridged = bridge_to_kernel(d)
        assert set(bridged.species_of) == {token for token, _ in d.registry}
        assert set(bridged.species_of.values()) == set(bridged.system.species)
        for name, index in bridged.hyperedge_index.items():
            assert d.core.hyperedges[index].payload == name
        assert sorted(bridged.hyperedge_index) == ["dehydration", "proton_transfer"]

    def test_glued_node_is_internal_so_carbonic_acid_has_zero_net(self):
        bridged = bridge_to_kernel(build_demo_diagram())
        n_idx = bridged.system.species.index(_by_name(bridged, "CH2O3"))
        assert (bridged.system.N @ np.ones(2))[n_idx] == 0     # produced by s1, consumed by s2

    def test_rate_laws_default_unknown_and_overridable(self):
        default = bridge_to_kernel(build_demo_diagram()).system
        assert all(r.rate_law is RATE_UNKNOWN for r in default.reactions)
        law = MassActionIrreversible(k=2.0)
        got = bridge_to_kernel(build_demo_diagram(), rate_laws={"dehydration": law}).system
        assert {r.name: r.rate_law for r in got.reactions} == {"dehydration": law, "proton_transfer": RATE_UNKNOWN}

    def test_volume_is_passed_through(self):
        assert bridge_to_kernel(build_demo_diagram(), volume_L=2.5).system.volume_L == 2.5


# ======================================================================================
# (b) gluing-invariance
# ======================================================================================
class TestBGluingInvariance:
    def test_glued_unglued_and_reordered_presentations_agree(self):
        s1, s2 = _s1(), _s2()
        glued = glue_at(s1.tensor(s2), CARBONIC)
        # a genuinely different raw presentation: the other tensor order, glued the other way round
        reordered = glue_at(s2.tensor(s1), CARBONIC)
        # NOT glued at all: carbonic acid is an EXTERNAL output of s1 AND an EXTERNAL input of s2
        unglued = s1.tensor(s2)

        assert glued.core != reordered.core                      # the quotient/bridge is doing work, not raw equality
        assert glued.is_saturated and unglued.is_saturated
        sigs = [bridge_to_kernel(x).signature() for x in (glued, reordered, unglued)]
        assert sigs[0] == sigs[1] == sigs[2]
        # even the kernel's own model certificate (species identity + order, E, N, volume) is identical, because the
        # bridge emits a canonical column order and the hyperedge order of the presentation never reaches the kernel
        certs = {bridge_to_kernel(x).system._model_certificate for x in (glued, reordered, unglued)}
        assert len(certs) == 1

    def test_net_reaction_differs_while_kernel_does_not(self):
        # the control that makes the invariance meaningful: gluing DOES change the external boundary...
        glued = glue_at(_s1().tensor(_s2()), CARBONIC)
        unglued = _s1().tensor(_s2())
        assert len(glued.core.dom) == 2 and len(unglued.core.dom) == 3
        # ...yet the kernel system (N 1 == out - in holds in both) is the same: gluing removes no hyperedge.
        assert bridge_to_kernel(glued).signature() == bridge_to_kernel(unglued).signature()

    def test_hyperedge_index_follows_the_presentation_not_the_kernel(self):
        a = bridge_to_kernel(glue_at(_s1().tensor(_s2()), CARBONIC))
        b = bridge_to_kernel(glue_at(_s2().tensor(_s1()), CARBONIC))
        assert a.hyperedge_index["proton_transfer"] != b.hyperedge_index["proton_transfer"]
        assert a.signature() == b.signature()


# ======================================================================================
# (c) a BAD step -> ConservationError naming the imbalance
# ======================================================================================
class TestCBadStepIsRefusedByTheKernel:
    @staticmethod
    def _bad() -> OpenChemDiagram:      # CH3COOH -> CH3COO- + H2O : +O +H, -1 charge
        return OpenChemDiagram.single_step(Config.of(ACETIC), Config.of(ACETATE, WATER), generator_id="bad_dissociation")

    def test_bridge_raises_conservation_error_naming_the_step_and_imbalance(self):
        with pytest.raises(ConservationError) as err:
            bridge_to_kernel(self._bad())
        message = str(err.value)
        assert "bad_dissociation" in message
        assert "'charge': -1" in message and "'H': 1" in message and "'O': 1" in message

    def test_a_bad_step_inside_a_good_network_still_refuses(self):
        mixed = _s1().tensor(self._bad())
        with pytest.raises(ConservationError, match="bad_dissociation"):
            bridge_to_kernel(mixed)

    def test_the_diagram_itself_does_not_refuse_an_open_unbalanced_step(self):
        # conservation-as-closure: the diagram is a morphism regardless; the KERNEL is where it is decided.
        assert self._bad().is_saturated
        assert not self._bad().is_closed_and_conserving


# ======================================================================================
# (d) isomer rejection -- substance is minted from the Molecule, not a caller string
# ======================================================================================
class TestDIsomerRejection:
    @staticmethod
    def _isomerisation() -> OpenChemDiagram:        # ethanol -> dimethyl ether : CONSERVING, a genuine REACTION
        return OpenChemDiagram.single_step(Config.of(ETHANOL), Config.of(DME), generator_id="isomerise")

    @staticmethod
    def _co2_phase_change() -> OpenChemDiagram:
        co2_aq = dataclasses.replace(CO2, state="aq")
        co2_g = dataclasses.replace(CO2, state="g")
        return OpenChemDiagram.single_step(Config.of(co2_aq), Config.of(co2_g), generator_id="degas")

    def test_same_formula_different_identity_get_distinct_substances_and_names(self):
        assert ETHANOL.formula == DME.formula and ETHANOL.charge == DME.charge
        assert species_key(ETHANOL) != species_key(DME)
        bridged = bridge_to_kernel(self._isomerisation())
        eth, dme = bridged.species_of[species_key(ETHANOL)], bridged.species_of[species_key(DME)]
        assert eth.composition == dme.composition and eth.charge == dme.charge
        assert eth.substance != dme.substance
        assert eth.name != dme.name                            # the Hill-name collision was disambiguated by a digest
        assert eth.name.startswith("C2H6O(aq)#") and dme.name.startswith("C2H6O(aq)#")
        assert len(bridged.system.species) == 2

    def test_substance_is_minted_from_the_molecule_not_a_caller_string(self):
        bridged = bridge_to_kernel(self._isomerisation())
        for molecule in (ETHANOL, DME):
            assert bridged.species_of[species_key(molecule)].substance == substance_of(molecule)

    def test_interface_transfer_refuses_the_isomer_pair_but_admits_the_phase_pair(self):
        iso = bridge_to_kernel(self._isomerisation())
        eth, dme = iso.species_of[species_key(ETHANOL)], iso.species_of[species_key(DME)]
        with pytest.raises(CoupledError, match="DIFFERENT substance"):
            InterfaceTransfer("launder", "c0", "c1", eth, dme, k_transfer=0.1)

        phase = bridge_to_kernel(self._co2_phase_change())
        aq = phase.species_of[species_key(dataclasses.replace(CO2, state="aq"))]
        gas = phase.species_of[species_key(dataclasses.replace(CO2, state="g"))]
        assert (aq.phase, gas.phase) == (Phase.AQUEOUS, Phase.GAS)
        assert aq != gas and aq.substance == gas.substance
        transfer = InterfaceTransfer("strip", "liquid", "headspace", aq, gas, k_transfer=0.1)
        assert transfer.species_a is aq and transfer.species_b is gas

    def test_state_is_stripped_but_constitution_and_charge_are_not(self):
        assert substance_of(dataclasses.replace(CO2, state="g")) == substance_of(CO2)
        assert substance_of(ETHANOL) != substance_of(DME)
        assert substance_of(ACETIC) != substance_of(ACETATE)       # charge is part of the identity


# ======================================================================================
# (e) the cross-check: decoration net == column-summed E N ; N 1 == net reaction
# ======================================================================================
class TestECrossChecks:
    def test_good_network_decoration_equals_column_sum_equals_zero(self):
        bridged = bridge_to_kernel(build_demo_diagram())
        assert bridged.diagram_net == bridged.kernel_net == ()
        assert build_demo_diagram().core.decoration.is_balanced
        assert column_summed_EN(bridged.system.reactions) == {}

    def test_nonzero_case_two_independent_derivations_agree(self):
        # the NON-trivial instance of the cross-check: an unbalanced step has a non-zero decoration (from Molecule
        # formulas) and a non-zero column-summed E N (from kernel Species) -- and they are the SAME vector.
        bad = OpenChemDiagram.single_step(Config.of(ACETIC), Config.of(ACETATE, WATER), generator_id="bad")
        decoration = {("charge" if s == "+" else s): c for s, c in bad.core.decoration.net}
        assert decoration == {"H": 1, "O": 1, "charge": -1}
        species_of = _build_species(dict(bad.registry), None)
        edge = bad.core.hyperedges[0]
        coeffs = {}
        for t in edge.terminals:
            tok = bad.core.node_ports[t.node]
            coeffs[tok] = coeffs.get(tok, 0) + (1 if t.role == "product" else -1)
        reaction = Reaction("bad", tuple((species_of[t], c) for t, c in coeffs.items()))
        assert column_summed_EN((reaction,)) == decoration

    def test_N_times_ones_equals_the_diagram_net_reaction(self):
        d = build_demo_diagram()
        bridged = bridge_to_kernel(d)
        net = d.net_reaction()
        out_minus_in = {}
        for m in net.cod.species:
            out_minus_in[species_key(m)] = out_minus_in.get(species_key(m), 0) + 1
        for m in net.dom.species:
            out_minus_in[species_key(m)] = out_minus_in.get(species_key(m), 0) - 1
        out_minus_in = {k: v for k, v in out_minus_in.items() if v}
        row_sums = bridged.system.N @ np.ones(len(bridged.system.reactions))
        by_token = {tok: int(row_sums[bridged.system.species.index(sp)])
                    for tok, sp in bridged.species_of.items() if row_sums[bridged.system.species.index(sp)]}
        assert by_token == out_minus_in
        assert len(by_token) == 5        # CH3COOH, HCO3-, CH3COO-, CO2, H2O -- H2CO3 cancelled

    def test_a_forged_decoration_is_caught(self):
        # control: a diagram whose decoration lies (claims balanced while a step is not) must trip the cross-check
        # BEFORE the kernel is trusted with it -- i.e. we never rely on the decoration alone.
        from smartchem.open_chem_diagram import ConservationDecoration
        good = build_demo_diagram()
        forged_core = dataclasses.replace(good.core, decoration=ConservationDecoration((("O", 1),)))
        forged = OpenChemDiagram(forged_core, good.registry, good.name)
        with pytest.raises(BridgeCrossCheckError):
            bridge_to_kernel(forged)


# ======================================================================================
# Fail-closed refusals
# ======================================================================================
class TestRefusals:
    def test_non_saturated_diagram_refused(self):
        open_step = OpenChemDiagram.single_step(Config.of(ACETIC, BICARB), Config.of(ACETATE, CARBONIC),
                                                generator_id="proton_transfer", open_products=frozenset({0, 1}))
        assert not open_step.is_saturated
        with pytest.raises(BridgeError, match="non-saturated"):
            bridge_to_kernel(open_step)

    def test_empty_generator_id_refused(self):
        anon = OpenChemDiagram.single_step(Config.of(CARBONIC), Config.of(CO2, WATER))      # generator_id == ""
        with pytest.raises(BridgeError, match="empty generator_id"):
            bridge_to_kernel(anon)

    def test_duplicate_generator_id_refused(self):
        a = OpenChemDiagram.single_step(Config.of(CARBONIC), Config.of(CO2, WATER), generator_id="step")
        b = OpenChemDiagram.single_step(Config.of(ETHANOL), Config.of(DME), generator_id="step")
        with pytest.raises(BridgeError, match="duplicate generator_id"):
            bridge_to_kernel(a.tensor(b))

    def test_net_zero_step_refused(self):
        loop = OpenChemDiagram.single_step(Config.of(WATER), Config.of(WATER), generator_id="noop")
        with pytest.raises(BridgeError, match="zero net stoichiometry"):
            bridge_to_kernel(loop)

    def test_catalyst_cancels_inside_a_step_but_stays_a_species(self):
        proton = Molecule.atom("H", charge=1)
        step = OpenChemDiagram.single_step(Config.of(ACETIC, ETHANOL, proton),
                                           Config.of(parse_smiles("CC(=O)OCC"), WATER, proton),
                                           generator_id="fischer")
        bridged = bridge_to_kernel(step)
        (reaction,) = bridged.system.reactions
        assert len(reaction.stoich) == 4                                    # the catalyst is NOT in the stoichiometry
        catalyst = bridged.species_of[species_key(proton)]
        assert catalyst in bridged.system.species and catalyst not in {s for s, _ in reaction.stoich}
        assert catalyst.charge == 1
        assert not np.any(bridged.system.E @ bridged.system.N)

    def test_unmappable_state_refused(self):
        excited = dataclasses.replace(CO2, state="*")
        step = OpenChemDiagram.single_step(Config.of(excited), Config.of(CO2), generator_id="relax")
        with pytest.raises(BridgeError, match="cannot be mapped to a kernel Phase"):
            bridge_to_kernel(step)

    def test_phase_override_applies_only_to_stateless_molecules_and_may_not_contradict(self):
        step = OpenChemDiagram.single_step(Config.of(CARBONIC), Config.of(CO2, WATER), generator_id="dehydration")
        got = bridge_to_kernel(step, phases={species_key(CO2): Phase.GAS})
        assert got.species_of[species_key(CO2)].phase is Phase.GAS
        assert got.species_of[species_key(CO2)].name == "CO2(g)"
        assert got.species_of[species_key(WATER)].phase is Phase.AQUEOUS      # the default
        gas_state = dataclasses.replace(CO2, state="g")
        stateful = OpenChemDiagram.single_step(Config.of(CARBONIC), Config.of(gas_state, WATER), generator_id="d")
        with pytest.raises(BridgeError, match="contradicts"):
            bridge_to_kernel(stateful, phases={species_key(gas_state): Phase.AQUEOUS})

    def test_two_labels_for_one_substance_in_one_phase_refused(self):
        # state "" (default AQUEOUS) and state "aq" are the SAME substance in the SAME phase: a duplicate, not two species
        co2_aq = dataclasses.replace(CO2, state="aq")
        step = OpenChemDiagram.single_step(Config.of(co2_aq), Config.of(CO2), generator_id="aliased")
        with pytest.raises(BridgeError, match="same substance in the same phase"):
            bridge_to_kernel(step)

    def test_override_and_rate_law_typos_refused(self):
        d = build_demo_diagram()
        with pytest.raises(BridgeError, match="not in the diagram registry"):
            bridge_to_kernel(d, phases={"deadbeef": Phase.GAS})
        with pytest.raises(BridgeError, match="not in the diagram"):
            bridge_to_kernel(d, rate_laws={"dehydratoin": MassActionIrreversible(k=1.0)})
        with pytest.raises(BridgeError, match="must be a RateLaw"):
            bridge_to_kernel(d, rate_laws={"dehydration": 1.0})

    def test_not_an_open_chem_diagram_refused(self):
        with pytest.raises(BridgeError):
            bridge_to_kernel(build_demo_diagram().core)   # type: ignore[arg-type]
