"""The chemistry construction layer on the domain-neutral :mod:`smartchem.open_core`.

This is Rung B of the Move-1 keystone (``docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md``).
A chemistry process becomes an :class:`OpenChemDiagram` -- an open symmetric-monoidal diagram whose
boundary ports are typed by SPECIES and whose interior is a set of multi-terminal reaction
hyperedges (``N`` reactants -> ``M`` products), riding on the proven ``open_core`` composition and
``canonicalize`` quotient.  It sits *alongside* :class:`smartchem.category.Reaction`; it does not
replace or mutate it, and every closed route keeps its byte-identical ``canonical_digest`` (P2).

**Two apex quantities, of two different kinds** (fold of the pre-merge adversarial review):

* **conservation** -- the additive net ``products - reactants`` element/charge vector over the
  internal reaction hyperedges.  It is a genuine, self-contained monoid **decoration** riding the
  ``open_core`` slot: it is a homomorphic SUM over the generators, so it is independent of how the
  diagram is glued (gluing removes no hyperedge), additive under both ``then`` and ``tensor``, and
  therefore interchange-invariant and node-relabel-invariant -- safe to carry verbatim through
  ``canonicalize``.  It is *exactly the shape* a future free-energy functor ``Delta_rG`` (Hess's
  law -- an additive sum) or a survival functor (a multiplicative product) will take, which is why
  it demonstrates the slot the M2-FP rung will populate.  The closure predicate
  :meth:`OpenChemDiagram.conservation_status` is a *separate*, direct count over the saturated
  EXTERNAL boundary (mirroring ``Reaction.__post_init__``); a cross-check test pins the two to agree.

* **provenance** -- the causal DAG of generator steps (P4).  This is **NOT** a decoration: a
  dependency edge exists exactly where one step's product feeds another step's reactant, i.e. where
  two hyperedge terminals share a glued node -- which is a fact of the composed TOPOLOGY, not
  something a self-contained monoid can carry.  (An earlier draft carried a per-port frontier on a
  monoid decoration; the review proved that broke the SMC congruence -- an identity wire laundered a
  producer's frontier so ``f`` and ``f;id`` compared equal yet diverged under a later ``then``.)
  Provenance is therefore **derived from the composed core** (:func:`_derive_provenance`): it is a
  pure function of the topology, so interchange-equivalent assemblies yield equal provenance and a
  bare identity/braid wire between two steps is handled correctly (the wire's node is glued between
  producer and consumer, so the dependency is read directly).  A linear ``Reaction.path`` is one
  recoverable linearization.

**Conservation as closure, not construction (the keystone thesis).** An :class:`OpenChemDiagram`
can be built from species that do *not* balance -- it is a morphism regardless.  Balance is decided
only at :meth:`OpenChemDiagram.close`, where the diagram reduces to a real ``Reaction`` and inherits
its refusal (P3); a mass-violating *closed* diagram is thus unconstructible as a closed value,
exactly as today.  A diagram with any OPEN port is UNDECIDED -- never conserved, never violated.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import open_core
from .category import Config, Molecule, Reaction
from .open_core import (
    Decoration,
    Hyperedge,
    Interface,
    OpenDiagram,
    Terminal,
)

__all__ = [
    "ChemApex",
    "ConservationDecoration",
    "ConservationStatus",
    "OpenChemDiagram",
    "OpenDiagramError",
    "PortState",
    "Provenance",
    "StepNode",
    "braid",
    "canonicalize",
    "identity_diagram",
    "species_key",
]

_REACTION_KIND = "reaction"
_REACTANT = "reactant"
_PRODUCT = "product"


class OpenDiagramError(ValueError):
    """A chemistry open diagram cannot be built, closed, or linearised as requested."""


class PortState(str, Enum):
    """The three states a boundary/terminal node can be in (contract table)."""

    INTERNAL = "internal"   # glued to a partner: counted inside
    EXTERNAL = "external"   # a declared net input/output: counted by the closure predicate
    OPEN = "open"           # an unfilled slot: closure UNDECIDED


class ConservationStatus(str, Enum):
    """The tri-state result of the closure predicate; OPEN never collapses to VIOLATED."""

    CONSERVING = "conserving"
    VIOLATED = "violated"
    UNDECIDED = "undecided"


def species_key(molecule: Molecule) -> str:
    """The presentation-invariant port token for a species (the repo's resonance identity).

    Shared with route search / stoichiometry via :func:`smartchem.smiles.resonance_identity`, so two
    Kekule spellings of one intermediate carry the same port token and glue across a composition.
    """
    from .smiles import resonance_identity

    return resonance_identity(molecule)


# ======================================================================================
# The one genuine decoration: conservation (an additive, self-contained monoid)
# ======================================================================================
def _atoms_with_charge(config: Config) -> dict[str, int]:
    counts = dict(config.formula)
    if config.charge:
        counts["+"] = config.charge
    return counts


def _freeze(net: dict[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((symbol, count) for symbol, count in net.items() if count != 0))


@dataclass(frozen=True)
class ConservationDecoration(Decoration):
    """The additive net ``products - reactants`` element/charge vector over internal hyperedges.

    Stored as a sorted tuple of non-zero ``(symbol, count)`` pairs (charge under the ``"+"`` key) so
    equality and hashing are canonical.  ``then_combine`` and ``tensor_combine`` are both vector
    addition -- a homomorphic SUM over the generators, independent of gluing (``then`` removes no
    hyperedge, it only glues boundary nodes).  Hence the decoration is interchange-invariant and
    node-relabel-invariant, and it is the zero vector exactly when every internal step conserves.

    This is a *demonstration* of the ``open_core`` decoration slot with an additive monoid -- the
    same shape a free-energy drive functor (Hess's law: ``Delta_rG`` is an additive sum) takes.  The
    authoritative conservation VERDICT is the separate direct boundary count in
    :meth:`OpenChemDiagram.conservation_status`; the two are pinned to agree by a cross-check test.
    """

    net: tuple[tuple[str, int], ...] = ()

    @classmethod
    def identity(cls) -> "ConservationDecoration":
        return cls(())

    @classmethod
    def for_step(cls, source: Config, target: Config) -> "ConservationDecoration":
        produced = _atoms_with_charge(target)
        consumed = _atoms_with_charge(source)
        net: dict[str, int] = dict(produced)
        for symbol, count in consumed.items():
            net[symbol] = net.get(symbol, 0) - count
        return cls(_freeze(net))

    def _add(self, other: "ConservationDecoration") -> "ConservationDecoration":
        if type(other) is not ConservationDecoration:
            raise open_core.DiagramCompositionError("conservation decorations only combine with each other")
        acc = dict(self.net)
        for symbol, count in other.net:
            acc[symbol] = acc.get(symbol, 0) + count
        return ConservationDecoration(_freeze(acc))

    def then_combine(self, other: Decoration) -> Decoration:
        return self._add(other)  # type: ignore[arg-type]

    def tensor_combine(self, other: Decoration) -> Decoration:
        return self._add(other)  # type: ignore[arg-type]

    @property
    def is_balanced(self) -> bool:
        """True iff the internal chemistry produces no net matter/charge (every step conserved)."""
        return not self.net


# ======================================================================================
# Provenance: a topology-derived read, NOT a decoration (see the module docstring)
# ======================================================================================
@dataclass(frozen=True)
class StepNode:
    """One generator step, identified by its endpoints and stable generator id.

    Carries the whole ``source``/``target`` :class:`~smartchem.category.Config` so a linear
    provenance chain round-trips to ``Reaction.path``/``generator_word`` (P4).
    """

    source: Config
    target: Config
    generator_id: str


@dataclass(frozen=True)
class Provenance:
    """The causal DAG of generator steps, derived from the composed topology.

    ``nodes`` is a step per internal reaction hyperedge; ``deps`` a dependency ``producer ->
    consumer`` for each internal node shared between one step's product terminal and another step's
    reactant terminal.  Both are content-valued (``StepNode``s), so equality is node-relabel- and
    interchange-invariant.

    Boundary (tracked debt, not silent): two *structurally identical* steps (same source, target and
    generator id) in one diagram collapse to a single ``StepNode`` here.  Rung B's real closure path
    is a single step (``ExperimentStep.open().close()``), and every gate uses distinct steps, so this
    is not reached; occurrence-aware provenance is a Rung-C concern.
    """

    nodes: frozenset[StepNode] = frozenset()
    deps: frozenset[tuple[StepNode, StepNode]] = frozenset()

    def linearization(self) -> tuple[StepNode, ...]:
        """The unique total order of a linear-chain provenance, or refuse (fail-closed).

        A genuinely parallel provenance (two steps with no dependency path between them) has no
        faithful single linearisation; :meth:`OpenChemDiagram.close` only reduces linear histories.
        """
        remaining = set(self.nodes)
        incoming: dict[StepNode, set[StepNode]] = {node: set() for node in self.nodes}
        for producer, consumer in self.deps:
            if consumer in incoming:
                incoming[consumer].add(producer)
        ordered: list[StepNode] = []
        while remaining:
            ready = [node for node in remaining if not (incoming[node] & remaining)]
            if len(ready) != 1:
                raise OpenDiagramError(
                    "provenance is not a linear chain; a parallel assembly has no single Reaction.path"
                )
            node = ready[0]
            ordered.append(node)
            remaining.discard(node)
        return tuple(ordered)


def _derive_provenance(core: OpenDiagram, lookup: dict[str, Molecule]) -> Provenance:
    """Read the causal DAG off the composed topology (the congruence-safe provenance).

    Each reaction hyperedge is one step; a dependency ``X -> Y`` exists wherever a single node is a
    PRODUCT terminal of ``X`` and a REACTANT terminal of ``Y`` (they were glued in ``then``).  A
    bare identity/braid wire interposed between two steps glues their nodes together, so the
    dependency is read directly -- there is no frontier to launder.
    """
    producers_at: dict[int, list[StepNode]] = {}
    consumers_at: dict[int, list[StepNode]] = {}
    steps: list[StepNode] = []
    for edge in core.hyperedges:
        reactants = tuple(lookup[core.node_ports[t.node]] for t in edge.terminals if t.role == _REACTANT)
        products = tuple(lookup[core.node_ports[t.node]] for t in edge.terminals if t.role == _PRODUCT)
        node = StepNode(Config.of(*reactants), Config.of(*products), edge.payload)
        steps.append(node)
        for terminal in edge.terminals:
            if terminal.role == _PRODUCT:
                producers_at.setdefault(terminal.node, []).append(node)
            elif terminal.role == _REACTANT:
                consumers_at.setdefault(terminal.node, []).append(node)
    deps: set[tuple[StepNode, StepNode]] = set()
    for shared_node, producers in producers_at.items():
        for producer in producers:
            for consumer in consumers_at.get(shared_node, ()):
                if producer != consumer:
                    deps.add((producer, consumer))
    # Fail closed on a content collision rather than silently merging (Rung-B open-debt 3): two
    # structurally identical steps (same source, target, generator id) would collapse to one node in
    # the frozenset and corrupt the dependency reading.  A valid route/DAG never collides (a DAG has
    # distinct targets; a route's targets chain), so this only fires on a genuinely ambiguous input --
    # where the honest answer is a refusal, not a guess.  Occurrence-aware provenance stays future work.
    if len(steps) != len({step for step in steps}):
        raise OpenDiagramError(
            "two structurally identical generator steps share a provenance node; occurrence-aware "
            "provenance is not supported -- this diagram's causal DAG is ambiguous"
        )
    return Provenance(frozenset(steps), frozenset(deps))


@dataclass(frozen=True)
class ChemApex:
    """A read-only VIEW of a diagram's apex: the conservation decoration + derived provenance.

    This is not combined and not stored -- :meth:`OpenChemDiagram.apex` builds it on demand from the
    core's decoration and the topology-derived provenance.  A future free-energy / survival functor
    joins the ``conservation`` side (genuine additive/multiplicative decorations riding the
    ``open_core`` slot) without touching provenance or the core.
    """

    conservation: ConservationDecoration
    provenance: Provenance


# ======================================================================================
# The chemistry open diagram
# ======================================================================================
@dataclass(frozen=True)
class OpenChemDiagram:
    """An open chemistry morphism: a decorated ``open_core`` diagram plus a species registry.

    ``core`` is the structural presentation (its ``node_ports`` are species tokens, its decoration a
    :class:`ConservationDecoration`); ``registry`` maps each species token back to its ``Molecule``
    so :meth:`close` and provenance can rebuild the exact ``Config`` objects; ``name`` labels the
    (re)built reaction.
    """

    core: OpenDiagram
    registry: tuple[tuple[str, Molecule], ...]
    name: str = ""

    # -- construction ------------------------------------------------------------------
    @classmethod
    def single_step(
        cls,
        source: Config,
        target: Config,
        *,
        generator_id: str = "",
        name: str = "",
        open_reactants: frozenset[int] = frozenset(),
        open_products: frozenset[int] = frozenset(),
    ) -> "OpenChemDiagram":
        """One reaction hyperedge, ``source`` species -> ``target`` species.

        By default every reactant is an EXTERNAL input port and every product an EXTERNAL output
        port (a saturated step).  ``open_reactants``/``open_products`` name species *positions*
        (indices into ``source.species`` / ``target.species``) to leave OPEN instead -- unfilled
        slots that make the diagram non-saturated, so its conservation is UNDECIDED.  Construction
        never checks balance; that is deferred to :meth:`close`.
        """
        reactants = source.species
        products = target.species
        node_ports = tuple(species_key(m) for m in reactants) + tuple(species_key(m) for m in products)
        n_reactants = len(reactants)

        terminals = tuple(Terminal(_REACTANT, i) for i in range(n_reactants)) + tuple(
            Terminal(_PRODUCT, n_reactants + j) for j in range(len(products))
        )
        edge = Hyperedge(_REACTION_KIND, generator_id, terminals)

        input_positions = [i for i in range(n_reactants) if i not in open_reactants]
        output_positions = [j for j in range(len(products)) if j not in open_products]
        input_nodes = tuple(input_positions)
        output_nodes = tuple(n_reactants + j for j in output_positions)
        dom = Interface(tuple(node_ports[i] for i in input_nodes))
        cod = Interface(tuple(node_ports[j] for j in output_nodes))

        decoration = ConservationDecoration.for_step(source, target)
        core = OpenDiagram(dom, cod, input_nodes, output_nodes, node_ports, (edge,), decoration)
        registry = _registry_of(reactants + products)
        return cls(core, registry, name)

    @classmethod
    def from_reaction(cls, reaction: Reaction) -> "OpenChemDiagram":
        """The functor ``Reaction -> OpenChemDiagram``: EXTERNAL dom/cod ports, path -> hyperedges.

        A linear reaction becomes a chain of single-step diagrams composed with :meth:`then`, so its
        provenance is the linear dependency DAG (each step's product feeds the next step's reactant)
        and its EXTERNAL boundary is the reaction's ``dom``/``cod``.
        """
        if type(reaction) is not Reaction:
            raise TypeError("from_reaction expects a smartchem.category.Reaction")
        path = reaction.path or ()
        word = reaction.generator_word or ()
        if not path:
            # An identity reaction traverses no steps: a bare wire diagram over its object.
            return cls._wire(reaction.dom, reaction.name)
        built: OpenChemDiagram | None = None
        for (source, target), (_, _, generator_id) in zip(path, word):
            step = cls.single_step(source, target, generator_id=generator_id, name=reaction.name)
            built = step if built is None else built.then(step)
        assert built is not None
        return cls(built.core, built.registry, reaction.name)

    @classmethod
    def _wire(cls, config: Config, name: str) -> "OpenChemDiagram":
        interface = Interface(tuple(species_key(m) for m in config.species))
        core = open_core.identity(interface, decoration=ConservationDecoration.identity())
        return cls(core, _registry_of(config.species), name)

    @classmethod
    def _assemble(
        cls,
        steps: tuple["object", ...],
        flow: tuple[tuple[int, int, Molecule], ...],
        *,
        name: str = "",
    ) -> "OpenChemDiagram":
        """Compose a pipeline of steps into ONE open diagram, gluing only the shared intermediates.

        Each step becomes a single-step diagram (``ExperimentStep.open()`` -- every reactant an EXTERNAL
        input port, every product an EXTERNAL output port); all are ``tensor``'d into one diagram, and a
        single :meth:`plug_all` glues, for every ``(producer, consumer, intermediate)`` in ``flow``, one
        of the producer's product ports for that species to one of the consumer's reactant ports for it.
        The glued nodes become INTERNAL; every leaf input and byproduct stays on the EXTERNAL boundary.
        This is the general open-morphism composition the linear ``Reaction`` chain cannot express
        (a real step carries byproducts and fresh reagents, so its cod never equals the next step's dom).
        """
        if not steps:
            raise OpenDiagramError("cannot assemble an open diagram from zero steps")
        diagrams = [step.open() for step in steps]
        composite = diagrams[0]
        for diagram in diagrams[1:]:
            composite = composite.tensor(diagram)
        in_base: list[int] = []
        out_base: list[int] = []
        offset_in = 0
        offset_out = 0
        for diagram in diagrams:
            in_base.append(offset_in)
            out_base.append(offset_out)
            offset_in += len(diagram.core.dom.ports)
            offset_out += len(diagram.core.cod.ports)
        used_out: set[int] = set()
        used_in: set[int] = set()
        pairs: list[tuple[int, int]] = []
        for producer, consumer, intermediate in flow:
            token = species_key(intermediate)
            out_pos = _first_free(diagrams[producer].core.cod.ports, token, out_base[producer], used_out)
            in_pos = _first_free(diagrams[consumer].core.dom.ports, token, in_base[consumer], used_in)
            if out_pos is None or in_pos is None:
                raise OpenDiagramError(
                    f"flow {producer}->{consumer} on {intermediate!r} has no free matching port to glue"
                )
            used_out.add(out_pos)
            used_in.add(in_pos)
            pairs.append((out_pos, in_pos))
        return composite.plug_all(tuple(pairs))._named(name)

    @classmethod
    def from_route(cls, route: "object") -> "OpenChemDiagram":
        """Project an :class:`~smartchem.experiment.step.ExperimentRoute` (its ``.open()``).

        The route's linear chain glues each step's target output to the next step's reactant input; leaf
        inputs and byproducts remain EXTERNAL, the carried intermediates become INTERNAL, so a conserving
        route yields a saturated CONSERVING diagram whose provenance linearises to the step order (P4).
        """
        steps = route.steps
        flow = tuple((k, k + 1, steps[k].target) for k in range(len(steps) - 1))
        return cls._assemble(steps, flow, name=f"route->{steps[-1].target!r}")

    @classmethod
    def from_dag(cls, dag: "object") -> "OpenChemDiagram":
        """Project a :class:`~smartchem.experiment.dag.SynthesisDAG` (its ``.open()``).

        The DAG's ``edges`` (``(producer, consumer, intermediate)``) name exactly the internal gluings;
        a convergent DAG uses ``tensor`` for its parallel branches and its provenance is the branching
        causal DAG (P4).  A convergent assembly has no single linear ``Reaction.path`` -- ``close()``
        refuses it -- but :meth:`net_reaction` gives its conservation-certified overall transformation.
        """
        return cls._assemble(dag.steps, dag.edges, name=f"dag->{dag.final_target!r}")

    def _named(self, name: str) -> "OpenChemDiagram":
        return self if not name else OpenChemDiagram(self.core, self.registry, name)

    # -- composition -------------------------------------------------------------------
    def then(self, other: "OpenChemDiagram") -> "OpenChemDiagram":
        if type(other) is not OpenChemDiagram:
            raise TypeError("other must be an OpenChemDiagram")
        label = " ; ".join(part for part in (self.name, other.name) if part)
        return OpenChemDiagram(
            self.core.then(other.core),
            _merge_registries(self.registry, other.registry),
            label,
        )

    def tensor(self, other: "OpenChemDiagram") -> "OpenChemDiagram":
        if type(other) is not OpenChemDiagram:
            raise TypeError("other must be an OpenChemDiagram")
        label = " (x) ".join(part for part in (self.name, other.name) if part)
        return OpenChemDiagram(
            self.core.tensor(other.core),
            _merge_registries(self.registry, other.registry),
            label,
        )

    def plug_all(self, pairs: tuple[tuple[int, int], ...]) -> "OpenChemDiagram":
        """Glue chosen EXTERNAL output ports to input ports (partial pushout); keep the registry.

        Delegates to :meth:`smartchem.open_core.OpenDiagram.plug_all`.  This is how a tensored pipeline
        of steps composes at only its shared intermediates -- the general open-morphism composition the
        whole-vessel ``then`` cannot do when steps carry byproducts and fresh leaf inputs.
        """
        return OpenChemDiagram(self.core.plug_all(pairs), self.registry, self.name)

    # -- reads: the three port states --------------------------------------------------
    def _boundary_nodes(self) -> set[int]:
        return set(self.core.input_nodes) | set(self.core.output_nodes)

    def port_state(self, node: int) -> PortState:
        incidence = self.core.edge_incidence()[node]
        if node in self._boundary_nodes():
            return PortState.EXTERNAL
        return PortState.OPEN if incidence <= 1 else PortState.INTERNAL

    def open_nodes(self) -> tuple[int, ...]:
        """Every node in the OPEN state (an unfilled hyperedge slot).

        Uses DISTINCT-edge incidence (``edge_incidence``), not raw terminal count, so a node shared
        between two generator steps is INTERNAL while a node touched by a single step (even twice, in a
        symmetric step) is an unfilled slot -- Rung-B open-debt 5.
        """
        boundary = self._boundary_nodes()
        incidence = self.core.edge_incidence()
        return tuple(
            node
            for node in range(len(self.core.node_ports))
            if node not in boundary and incidence[node] <= 1
        )

    @property
    def is_saturated(self) -> bool:
        """True iff no port is OPEN -- the precondition for closing the diagram."""
        return not self.open_nodes()

    # -- reads: conservation as closure ------------------------------------------------
    def _boundary_config(self, nodes: tuple[int, ...]) -> Config:
        lookup = dict(self.registry)
        return Config.of(*(lookup[self.core.node_ports[node]] for node in nodes))

    def external_input(self) -> Config:
        """The declared EXTERNAL input species (the dom of the eventual reaction)."""
        return self._boundary_config(self.core.input_nodes)

    def external_output(self) -> Config:
        """The declared EXTERNAL output species (the cod of the eventual reaction)."""
        return self._boundary_config(self.core.output_nodes)

    def conservation_status(self) -> ConservationStatus:
        """UNDECIDED if any port is OPEN; else CONSERVING/VIOLATED by the EXTERNAL boundary balance.

        The balance is the same equality ``Reaction.__post_init__`` enforces
        (``dom.formula == cod.formula`` and ``dom.charge == cod.charge``) over the saturated
        boundary -- computed directly, independently of the additive conservation decoration (the two
        are pinned to agree by a cross-check test).
        """
        if not self.is_saturated:
            return ConservationStatus.UNDECIDED
        dom, cod = self.external_input(), self.external_output()
        if dom.formula == cod.formula and dom.charge == cod.charge:
            return ConservationStatus.CONSERVING
        return ConservationStatus.VIOLATED

    @property
    def is_closed_and_conserving(self) -> bool:
        """True iff no port is OPEN and the saturated EXTERNAL boundary balances."""
        return self.conservation_status() is ConservationStatus.CONSERVING

    @property
    def apex(self) -> ChemApex:
        """The read-only apex view: the conservation decoration + the topology-derived provenance."""
        decoration = self.core.decoration
        assert isinstance(decoration, ConservationDecoration)
        return ChemApex(decoration, _derive_provenance(self.core, dict(self.registry)))

    # -- closure: reduce to a real Reaction certificate (P3) ---------------------------
    def to_reaction_path(
        self,
    ) -> tuple[tuple[tuple[Config, Config], ...], tuple[tuple[Config, Config, str], ...]]:
        """Recover ``(path, generator_word)`` from the linear provenance DAG (P4 round-trip)."""
        ordered = self.apex.provenance.linearization()
        path = tuple((node.source, node.target) for node in ordered)
        word = tuple((node.source, node.target, node.generator_id) for node in ordered)
        return path, word

    def close(self) -> Reaction:
        """Reduce a saturated diagram to today's ``Reaction`` certificate, byte-for-byte (P3).

        Fail-closed: an OPEN (non-saturated) diagram is refused before any Reaction is built. On a
        saturated diagram this rebuilds the same ``Reaction`` value ``Reaction.__post_init__`` would,
        so a mass-violating *closed* diagram remains unconstructible (the ``ConservationError`` is
        re-raised exactly as today) and every conserving route keeps its byte-identical digest.
        """
        if not self.is_saturated:
            raise OpenDiagramError(
                "cannot close a diagram with OPEN ports: conservation is UNDECIDED until saturated"
            )
        path, word = self.to_reaction_path()
        if not path:
            # A bare wire closes to the identity morphism on its object.
            obj = self.external_input()
            return Reaction(obj, obj, self.name, path=())
        dom = path[0][0]
        cod = path[-1][1]
        return Reaction(dom, cod, self.name, path=path, generator_word=word)

    def net_reaction(self) -> Reaction:
        """The conservation-certified OVERALL transformation of a saturated diagram (its net equation).

        Unlike :meth:`close` (which reduces a whole-vessel LINEAR chain to its step-by-step
        ``Reaction.path`` and refuses a parallel history), :meth:`net_reaction` collapses any saturated
        diagram -- multi-step route or convergent DAG, byproducts and all -- to the single balanced
        transformation ``(all EXTERNAL inputs) -> (all EXTERNAL outputs)``.  The internal intermediates
        cancel, so a diagram whose every step conserves yields a conserving net reaction (its
        ``__post_init__`` re-derives the balance the independent way); an OPEN diagram is refused.
        This is the "closure = the whole-process net reaction" read the open-diagram backbone adds.
        """
        if not self.is_saturated:
            raise OpenDiagramError(
                "cannot take the net reaction of a diagram with OPEN ports: it is UNDECIDED until saturated"
            )
        dom = self.external_input()
        cod = self.external_output()
        if dom == cod:
            return Reaction(dom, cod, self.name, path=())
        return Reaction(dom, cod, self.name, path=((dom, cod),), generator_word=((dom, cod, "net"),))

    def __repr__(self) -> str:
        return (
            f"OpenChemDiagram({self.external_input()!r} -> {self.external_output()!r}"
            f"{'' if self.is_saturated else ' [OPEN]'})"
        )


def canonicalize(diagram: OpenChemDiagram, *, budget: int = 100_000) -> open_core.CanonicalDiagram:
    """The structural quotient over an :class:`OpenChemDiagram` (decoration-aware, fail-closed).

    Delegates to :func:`smartchem.open_core.canonicalize`; two diagrams are equal iff they have the
    same canonical hyperedge topology, the same species-typed boundary, and equal conservation
    decoration.  Provenance is a pure function of that topology, so it need not be compared
    separately -- equal canonical topology implies equal provenance, which is what makes the
    quotient a congruence (an earlier draft that compared a frontier-carrying provenance decoration
    was NOT a congruence; see the module docstring).  Above ``budget`` it raises
    :class:`~smartchem.open_core.CanonicalizationBudgetExceeded` -- never a silent pass.
    """
    if type(diagram) is not OpenChemDiagram:
        raise TypeError("canonicalize expects an OpenChemDiagram")
    return open_core.canonicalize(diagram.core, budget=budget)


def identity_diagram(config: Config) -> OpenChemDiagram:
    """The identity chemistry morphism on ``config`` -- a bare wire diagram, no reaction hyperedge."""
    return OpenChemDiagram._wire(config, "id")


def braid(left: Config, right: Config) -> OpenChemDiagram:
    """The symmetry ``left (x) right -> right (x) left`` as a chemistry wire diagram (no hyperedges)."""
    left_ports = tuple(species_key(m) for m in left.species)
    right_ports = tuple(species_key(m) for m in right.species)
    core = open_core.braid(
        Interface(left_ports), Interface(right_ports), decoration=ConservationDecoration.identity()
    )
    return OpenChemDiagram(core, _registry_of(left.species + right.species), "braid")


def _first_free(ports: tuple[str, ...], token: str, base: int, used: set[int]) -> int | None:
    """The first global boundary position ``base + local`` whose port token matches and is unused."""
    for local, port in enumerate(ports):
        position = base + local
        if port == token and position not in used:
            return position
    return None


def _registry_of(molecules: tuple[Molecule, ...]) -> tuple[tuple[str, Molecule], ...]:
    lookup: dict[str, Molecule] = {}
    for molecule in molecules:
        lookup[species_key(molecule)] = molecule
    return tuple(sorted(lookup.items()))


def _merge_registries(
    left: tuple[tuple[str, Molecule], ...],
    right: tuple[tuple[str, Molecule], ...],
) -> tuple[tuple[str, Molecule], ...]:
    lookup = dict(left)
    for key, molecule in right:
        if key in lookup and lookup[key] != molecule:
            raise OpenDiagramError("registry conflict: one species token maps to two molecules")
        lookup[key] = molecule
    return tuple(sorted(lookup.items()))
