"""OPERATION XIX section 5 -- the EXECUTABLE categorical -> physical bridge.

The categorical layer (``smartchem.open_chem_diagram``) says WHAT a process composes to: an open symmetric-monoidal
diagram of typed species ports and multi-terminal reaction hyperedges.  The physical layer
(``experiments.sandbox_foundation.general_kernel``) says what a process DOES: a typed ``ChemicalSystem`` with a
stoichiometric matrix N, a conservation matrix E, and a generic integrator.  Until this module the two were separate
worlds.  :func:`bridge_to_kernel` is the functor between them, and it is built to be TRUSTED LESS than the diagram:

    OpenChemDiagram  --bridge_to_kernel-->  general_kernel.ChemicalSystem

* ONE kernel ``Species`` per registry entry.  Its ``substance`` is MINTED from the Molecule's own
  ``resonance_identity`` with the ``state`` label STRIPPED, never a caller string -- so CO2(aq) and CO2(g) (different
  states, same compound) share a substance, while ethanol and dimethyl ether (both C2H6O, different constitution) do
  NOT.  That is exactly the discriminator ``InterfaceTransfer`` needs to admit a phase transfer and refuse an isomer
  laundered in as "transport".
* ONE kernel ``Reaction`` per internal hyperedge: a signed Counter over its terminals (+1 per product terminal, -1 per
  reactant terminal), zero-net species dropped (a catalyst cancels).  Gluing (``then`` / ``tensor`` / ``plug_all``)
  removes no hyperedge, so the reaction set is invariant under how the diagram was assembled.
* The KERNEL re-proves ``E N = 0`` in unbounded integers at construction.  The diagram's own conservation decoration is
  NEVER trusted: it is only CROSS-CHECKED against the column-summed E N, and ``N 1`` against the diagram's net reaction
  (external out - external in).  Two independent derivations of one quantity, pinned to agree.
* FAIL-CLOSED: an unsaturated diagram, an empty / duplicate generator id, a net-zero step, an unmappable state, an
  isomer name collision, or a typo'd override all raise :class:`BridgeError` -- never a silent guess.

Scope boundary (honest): this carries STOICHIOMETRY and IDENTITY across, nothing more.  Rate laws are caller-supplied
(``RATE_UNKNOWN`` by default, which the kernel refuses to integrate); a successful bridge is a conservation + identity
certificate, NOT a kinetics or thermodynamics claim.
"""
from __future__ import annotations

import dataclasses
import hashlib
from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType

from experiments.sandbox_foundation.general_kernel import (
    RATE_UNKNOWN,
    ChemicalSystem,
    Phase,
    RateLaw,
    Reaction,
    Species,
)
from smartchem.category import Molecule
from smartchem.open_chem_diagram import OpenChemDiagram, species_key
from smartchem.smiles import resonance_identity

__all__ = [
    "BridgeCrossCheckError",
    "BridgeError",
    "BridgeResult",
    "bridge_to_kernel",
    "build_demo_diagram",
    "column_summed_EN",
    "kernel_signature",
    "substance_of",
]

_REACTION_KIND = "reaction"
_REACTANT = "reactant"
_PRODUCT = "product"

# A Molecule.state label -> kernel Phase.  "" is "unspecified" (the caller's `phases` / the AQUEOUS default decides);
# ANY other label not listed here (an electronic excitation "*", a mode, a typo) cannot be mapped -> refuse.
_STATE_TO_PHASE = {
    "aq": Phase.AQUEOUS, "aqueous": Phase.AQUEOUS,
    "g": Phase.GAS, "gas": Phase.GAS,
    "s": Phase.SOLID, "solid": Phase.SOLID,
    "l": Phase.PURE_LIQUID, "liquid": Phase.PURE_LIQUID, "pure_liquid": Phase.PURE_LIQUID,
}
_PHASE_TAG = {Phase.AQUEOUS: "aq", Phase.GAS: "g", Phase.SOLID: "s", Phase.PURE_LIQUID: "l"}


class BridgeError(ValueError):
    """The open diagram cannot be faithfully carried into the kernel (fail-closed)."""


class BridgeCrossCheckError(BridgeError):
    """Two independent derivations of one quantity disagree -- the bridge refuses to hand back the system."""


@dataclass(frozen=True)
class BridgeResult:
    """What :func:`bridge_to_kernel` hands back: the kernel system plus the maps needed to read it against the diagram.

    ``species_of`` maps each registry port token -> its kernel ``Species``; ``hyperedge_index`` maps each kernel
    reaction name (the generator id) -> the index of its hyperedge in ``diagram.core.hyperedges``.  ``diagram_net`` and
    ``kernel_net`` are the two independent element/charge net vectors (the cross-check pair)."""
    system: ChemicalSystem
    species_of: "MappingProxyType[str, Species]"
    hyperedge_index: "MappingProxyType[str, int]"
    diagram_net: tuple          # ((label, int), ...) non-zero entries of the diagram's ConservationDecoration
    kernel_net: tuple           # ((label, int), ...) non-zero entries of the column-summed E N

    def signature(self) -> tuple:
        """Presentation-independent identity of the bridged system (see :func:`kernel_signature`)."""
        return kernel_signature(self.system)


# ======================================================================================
# Identity: the substance is minted from the Molecule, never from a caller string
# ======================================================================================
def substance_of(molecule: Molecule) -> str:
    """The PHASE/STATE-STRIPPED substance identity of ``molecule`` (its own resonance identity with ``state`` cleared).

    CO2 with state "aq" and CO2 with state "g" share this value; ethanol and dimethyl ether do not.  Charge and
    constitution stay in the identity -- only the solvation/phase/electronic label is removed."""
    return "substance:" + resonance_identity(dataclasses.replace(molecule, state=""))


def _hill_name(formula: dict, charge: int) -> str:
    keys = sorted(formula)
    if "C" in formula:
        keys = ["C"] + (["H"] if "H" in formula else []) + [k for k in keys if k not in ("C", "H")]
    text = "".join(f"{k}{formula[k] if formula[k] != 1 else ''}" for k in keys)
    if charge:
        text += ("+" if charge > 0 else "-") if abs(charge) == 1 else f"{abs(charge)}{'+' if charge > 0 else '-'}"
    return text


def _phase_of(token: str, molecule: Molecule, phases: dict) -> Phase:
    declared = phases.get(token)
    if declared is not None and type(declared) is not Phase:
        raise BridgeError(f"phases[{token[:12]}...] must be a Phase, got {type(declared).__name__}")
    if molecule.state == "":
        return declared if declared is not None else Phase.AQUEOUS
    mapped = _STATE_TO_PHASE.get(molecule.state)
    if mapped is None:
        raise BridgeError(
            f"Molecule state {molecule.state!r} cannot be mapped to a kernel Phase (known: {sorted(_STATE_TO_PHASE)}); "
            f"an electronic excitation or unknown label is not a phase -- refusing rather than guessing")
    if declared is not None and declared is not mapped:
        raise BridgeError(
            f"phases override {declared} contradicts the Molecule's own state {molecule.state!r} -> {mapped}")
    return mapped


def _normalise_overrides(phases: dict | None, tokens: set) -> dict:
    out: dict = {}
    for key, value in (phases or {}).items():
        token = species_key(key) if isinstance(key, Molecule) else key
        if token not in tokens:
            raise BridgeError(f"phases names a species that is not in the diagram registry: {str(token)[:16]}...")
        out[token] = value
    return out


def _build_species(registry: dict, phases: dict | None) -> dict:
    """token -> Species, with phase from state/override, substance minted from the Molecule, names guaranteed distinct."""
    overrides = _normalise_overrides(phases, set(registry))
    drafts = {}
    for token, molecule in sorted(registry.items()):
        formula = dict(molecule.formula)
        if not formula:
            raise BridgeError(f"registry entry {token[:12]}... has no atoms (a charge carrier); the kernel needs a composition")
        phase = _phase_of(token, molecule, overrides)
        drafts[token] = (_hill_name(formula, molecule.charge) + f"({_PHASE_TAG[phase]})", formula, molecule, phase,
                         substance_of(molecule))
    # (substance, phase) is the physical identity of a kernel species; two tokens sharing it are a duplicate, not two species.
    seen: dict = {}
    for token, (_, _, _, phase, substance) in drafts.items():
        if (substance, phase) in seen:
            raise BridgeError(
                f"two registry tokens ({seen[(substance, phase)][:12]}..., {token[:12]}...) are the same substance in the "
                f"same phase ({phase.value}); an ambiguous state label would forge a duplicate species")
        seen[(substance, phase)] = token
    # isomer name collision: distinct substances that Hill-name identically get a short identity digest appended.
    by_name = Counter(name for name, *_ in drafts.values())
    species: dict = {}
    for token, (name, formula, molecule, phase, substance) in drafts.items():
        if by_name[name] > 1:
            name = f"{name}#{hashlib.sha256(substance.encode()).hexdigest()[:8]}"
        species[token] = Species.of(name, formula, molecule.charge, phase, substance=substance)
    if len({sp.name for sp in species.values()}) != len(species):
        raise BridgeError("species names still collide after digest disambiguation (8-hex digest collision)")
    return species


# ======================================================================================
# The independent conservation arithmetic (works on ANY reaction tuple, even an unbalanced one)
# ======================================================================================
def column_summed_EN(reactions) -> dict:
    """sum_k (E N)[:, k] as {label: int}, computed from species compositions + signed coefficients in plain Python ints.

    Labels are the element symbols and ``"charge"``.  For a system the kernel accepted every entry is 0; for a
    PRE-kernel (possibly unbalanced) reaction list the non-zero entries are exactly the imbalance the kernel will refuse."""
    net: Counter = Counter()
    for reaction in reactions:
        for species, coeff in reaction.stoich:
            for element, count in species.composition:
                net[element] += coeff * count
            net["charge"] += coeff * species.charge
    return {label: value for label, value in net.items() if value != 0}


def _diagram_net(diagram: OpenChemDiagram) -> dict:
    """The diagram's conservation DECORATION in kernel labels (charge is stored under '+')."""
    return {("charge" if sym == "+" else sym): count for sym, count in diagram.core.decoration.net}


def _freeze(net: dict) -> tuple:
    return tuple(sorted(net.items()))


def _species_identity(species: Species) -> tuple:
    """The full identity tuple of a kernel species (matches ``Species`` equality, minus the compare=False data_status)."""
    return (species.name, species.composition, species.charge, species.phase.value, species.substance)


def kernel_signature(system: ChemicalSystem) -> tuple:
    """A presentation-independent signature: (frozenset of species identities, frozenset of (reaction, stoich) pairs).

    Species are keyed by their FULL identity (name, composition, charge, phase, substance); reaction participants by that
    SAME full identity + coefficient (XXI-7: a bare display name would merge two distinct species that share one).
    Order of species/reactions (which differs between assemblies) is deliberately NOT part of it; rate laws are not either."""
    species = frozenset(_species_identity(s) for s in system.species)
    reactions = frozenset(
        (r.name, frozenset((_species_identity(s), c) for s, c in r.stoich)) for r in system.reactions)
    return species, reactions


# ======================================================================================
# The bridge
# ======================================================================================
def bridge_to_kernel(d: OpenChemDiagram, *, rate_laws: dict | None = None, phases: dict | None = None,
                     volume_L: float = 1.0) -> BridgeResult:
    """Carry a SATURATED :class:`OpenChemDiagram` into a kernel ``ChemicalSystem`` (see the module docstring).

    ``rate_laws`` maps generator id -> ``RateLaw`` (absent -> ``RATE_UNKNOWN``, which the kernel will not integrate).
    ``phases`` maps a port token (or a Molecule) -> ``Phase`` for species whose Molecule carries no ``state``; a Molecule
    that DOES carry a state keeps the phase that state names (a contradicting override is refused).  Raises
    :class:`BridgeError` on every unfaithful input and the kernel's own ``ConservationError`` if a step is unbalanced."""
    if type(d) is not OpenChemDiagram:
        raise BridgeError("bridge_to_kernel expects an OpenChemDiagram")
    if not d.is_saturated:
        raise BridgeError(
            f"cannot bridge a non-saturated diagram: OPEN ports {d.open_nodes()} remain, so its conservation is "
            f"UNDECIDED -- saturate it (glue or declare the slots external) first")
    registry = dict(d.registry)
    species_of = _build_species(registry, phases)

    edges = d.core.hyperedges
    names = [edge.payload for edge in edges]
    if any(not name.strip() for name in names):
        raise BridgeError("a hyperedge has an empty generator_id; the kernel reaction name would be unnamed/ambiguous")
    dupes = sorted(name for name, n in Counter(names).items() if n > 1)
    if dupes:
        # the kernel does NOT enforce reaction-name uniqueness; a repeat would silently alias two distinct steps.
        raise BridgeError(f"duplicate generator_id {dupes}: the kernel does not enforce reaction-name uniqueness, so we must")
    rate_laws = dict(rate_laws or {})
    unknown = sorted(set(rate_laws) - set(names))
    if unknown:
        raise BridgeError(f"rate_laws names generator ids that are not in the diagram: {unknown}")
    for name, law in rate_laws.items():
        if not isinstance(law, RateLaw):
            raise BridgeError(f"rate_laws[{name!r}] must be a RateLaw, got {type(law).__name__}")

    reactions = []
    hyperedge_index = {}
    for index, edge in enumerate(edges):
        if edge.kind != _REACTION_KIND:
            raise BridgeError(f"hyperedge {edge.payload!r} has kind {edge.kind!r}; only {_REACTION_KIND!r} bridges")
        counts: Counter = Counter()
        for terminal in edge.terminals:
            token = d.core.node_ports[terminal.node]
            if terminal.role == _PRODUCT:
                counts[token] += 1
            elif terminal.role == _REACTANT:
                counts[token] -= 1
            else:
                raise BridgeError(f"hyperedge {edge.payload!r} has a terminal with unknown role {terminal.role!r}")
        stoich = tuple(sorted(((species_of[token], c) for token, c in counts.items() if c != 0),
                              key=lambda pair: pair[0].name))
        if not stoich:
            raise BridgeError(
                f"step {edge.payload!r} has zero net stoichiometry (every species cancels, e.g. a pure catalyst loop); "
                f"it moves nothing and would be a dead reaction column")
        reactions.append(Reaction(edge.payload, stoich, rate_laws.get(edge.payload, RATE_UNKNOWN)))
        hyperedge_index[edge.payload] = index
    reactions.sort(key=lambda r: r.name)         # canonical column order: independent of how the diagram was assembled

    # CROSS-CHECK 1 (pre-kernel, so it is non-trivial on an unbalanced step): the diagram's decoration, derived from
    # Molecule formulas, must equal the column-summed E N derived from kernel Species compositions.
    diagram_net = _diagram_net(d)
    pre_net = column_summed_EN(reactions)
    if diagram_net != pre_net:
        raise BridgeCrossCheckError(
            f"diagram decoration net {diagram_net} != column-summed E N {pre_net}: the Molecule->Species map is unfaithful")

    ordered_species = sorted(species_of.values(), key=lambda s: s.name)
    system = ChemicalSystem(ordered_species, reactions, volume_L)   # the KERNEL re-proves E N = 0 (ConservationError)

    # The kernel's own published E and N must reproduce the same column sums (and, being accepted, all zero).
    kernel_net = _matrix_column_sums(system)
    if kernel_net != pre_net:
        raise BridgeCrossCheckError(f"kernel E@N column sums {kernel_net} != reaction-level column sums {pre_net}")

    # CROSS-CHECK 2: N 1 (per-species net production summed over reactions) == the diagram's net reaction (ext out - ext in).
    net_reaction = d.net_reaction()
    external: Counter = Counter()
    for molecule in net_reaction.cod.species:
        external[species_key(molecule)] += 1
    for molecule in net_reaction.dom.species:
        external[species_key(molecule)] -= 1
    external_net = {token: c for token, c in external.items() if c != 0}
    # XXI-7: N 1 is summed in plain Python ints straight off the integer stoichiometry -- never read back through float N.
    row_sums = _exact_net_production(system)
    token_of = {sp: token for token, sp in species_of.items()}
    kernel_species_net = {token_of[sp]: row_sums[i] for i, sp in enumerate(system.species) if row_sums[i] != 0}
    if kernel_species_net != external_net:
        raise BridgeCrossCheckError(
            f"N.1 {kernel_species_net} != the diagram's net reaction (external out - in) {external_net}: "
            f"a node is produced or consumed without being glued to a partner")

    return BridgeResult(
        system=system,
        species_of=MappingProxyType(dict(species_of)),
        hyperedge_index=MappingProxyType(hyperedge_index),
        diagram_net=_freeze(diagram_net),
        kernel_net=_freeze(kernel_net),
    )


def _exact_net_production(system: ChemicalSystem) -> tuple:
    """(N 1)[i] for every species i, in ``system.species`` order, as plain Python ints (unbounded, so EXACT).

    Summed directly from each reaction's integer ``stoich`` coefficients -- NOT read back through the kernel's float N
    (XXI-7: a float row sum silently rounds once a partial sum passes 2**53).  The ``ChemicalSystem`` guarantees every
    stoich species is in ``system.species`` (it refuses a stranger), so the index lookup cannot miss."""
    index = {sp: i for i, sp in enumerate(system.species)}
    totals = [0] * len(system.species)
    for reaction in system.reactions:
        for species, coeff in reaction.stoich:
            totals[index[species]] += coeff
    return tuple(totals)


def _matrix_column_sums(system: ChemicalSystem) -> dict:
    """sum_k (E N)[:, k] over ``system.component_labels`` as {label: int}, in plain Python ints (EXACT at any magnitude).

    XXI-7: this used to read the kernel's float E and N and ``np.rint`` the product, which is exact only for
    |coeff| <= 2**53 -- a balanced reaction with a coefficient like 2**60 + 1 would round to a WRONG non-zero integer and
    fire a false BridgeCrossCheckError.  It now recomputes E N from the integer data (``Species.count`` per component
    label, ``Species.charge`` for the charge row, the signed ``stoich`` coefficients).  That is a different route from
    :func:`column_summed_EN` (which walks each composition) -- a component-first walk, so the pair stays a real
    cross-check -- and neither touches float numpy.  The kernel's own float E / N stay the kernel's business."""
    totals = {label: 0 for label in system.component_labels}
    for reaction in system.reactions:
        for species, coeff in reaction.stoich:
            for label in system.component_labels:
                count = species.charge if label == "charge" else species.count(label)
                totals[label] += coeff * count
    return {label: value for label, value in totals.items() if value != 0}


# ======================================================================================
# The minimal real demo network
# ======================================================================================
def build_demo_diagram() -> OpenChemDiagram:
    """Vinegar + bicarbonate, as two generator steps glued at the internal H2CO3 node.

        s1 proton_transfer:  CH3COOH + HCO3-  ->  CH3COO- + H2CO3
        s2 dehydration:      H2CO3            ->  CO2 + H2O

    ``s1 (x) s2`` then ``plug_all`` on the H2CO3 output of s1 / H2CO3 input of s2.  CH3COOH, HCO3-, CH3COO-, CO2 and H2O
    stay on the external boundary; H2CO3 becomes INTERNAL, so it cancels in the net equation."""
    from smartchem.category import Config
    from smartchem.smiles import parse_smiles

    acetic, bicarbonate = parse_smiles("CC(=O)O"), parse_smiles("OC(=O)[O-]")
    acetate, carbonic = parse_smiles("CC(=O)[O-]"), parse_smiles("OC(=O)O")
    co2, water = parse_smiles("O=C=O"), parse_smiles("O")
    s1 = OpenChemDiagram.single_step(Config.of(acetic, bicarbonate), Config.of(acetate, carbonic),
                                     generator_id="proton_transfer", name="proton_transfer")
    s2 = OpenChemDiagram.single_step(Config.of(carbonic), Config.of(co2, water),
                                     generator_id="dehydration", name="dehydration")
    return glue_at(s1.tensor(s2), carbonic)


def glue_at(tensored: OpenChemDiagram, intermediate: Molecule) -> OpenChemDiagram:
    """``plug_all`` the first free EXTERNAL output port of ``intermediate`` into the first free EXTERNAL input port of it.

    Positions are looked up by port token (never hard-coded), since ``Config`` re-sorts species and so port order is not
    the order the caller wrote."""
    token = species_key(intermediate)
    out_pos = tensored.core.cod.ports.index(token)
    in_pos = tensored.core.dom.ports.index(token)
    return tensored.plug_all(((out_pos, in_pos),))


if __name__ == "__main__":      # python -m experiments.sandbox_foundation.open_diagram_bridge
    bridged = bridge_to_kernel(build_demo_diagram())
    sys_ = bridged.system
    print(f"species ({len(sys_.species)}): {[s.name for s in sys_.species]}")
    print(f"reactions: {[r.name for r in sys_.reactions]}   components: {sys_.component_labels}")
    product = sys_.E @ sys_.N
    print(f"E@N all-zero: {bool((product == 0).all())}   shape {product.shape}")
    print(f"diagram_net={bridged.diagram_net}  kernel_net={bridged.kernel_net}")
