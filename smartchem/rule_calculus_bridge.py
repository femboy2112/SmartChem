"""Opt-in replay audit on the existing capped-scission provider/search seam.

No default registry, reaction recognizer, ranking, serialization or admission
policy is changed. This adapter is deliberately neutral/unlabelled-state only:
refuse a state we cannot transport instead of silently erasing it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Bond, Config, Molecule, Reaction
from .experiment.step import ExperimentStep
from .experiment.reaction_type_oracle import recognize_reaction_type
from .open_chem_diagram import OpenChemDiagram
from .structure_descent import CappedScission, ScissionError
from .transform_provider import CappedScissionProvider
from .rule_calculus import BondGraph, BondRule, Edge, RewriteWitness, RuleError, apply, verify

#: Maximum coordination (total bond order) an atom of each element can bear in ANY accessible neutral-or-ionic
#: state -- a charge-AGNOSTIC ceiling.  It is DELIBERATELY not a neutral-only max: the graph carries only NET
#: molecular charge, never per-atom formal charge (dalembert), so a net-neutral CHARGE-SEPARATED species must
#: pass -- carbon monoxide ``[C-]#[O+]`` (O at degree 3), ozone, a dative amine-borane R3N->BH3 (B at degree 4).
#: So each ceiling is the max over charge states (O reaches 3 as O+, B reaches 4 as borate, the halogens reach 7
#: as perchlorate/periodate), and the gate refuses only a valence impossible in EVERY state (pentavalent carbon,
#: hexavalent oxygen) -- the actual fail-open dalembert found -- with no false-reject of real chemistry.
_MAX_COORDINATION: dict[str, int] = {
    "H": 1, "B": 4, "C": 4, "N": 5, "O": 3, "F": 1,
    "P": 6, "S": 6, "Cl": 7, "Br": 7, "I": 7,
}


def valence_sane(graph: BondGraph) -> bool:
    """Fail-closed valence precondition: no atom's degree exceeds its element's maximal coordination.

    dalembert's finding (the Diels-Alder round): the domain-neutral kernel and :class:`Molecule`
    DELIBERATELY do not enforce chemical valence -- kernel labels are opaque -- so a valence-impossible
    species (e.g. a pentavalent carbon) is silently processed.  This is the chemistry-aware seam, so the
    precondition belongs HERE, not in the valence-agnostic kernel.  Because a :class:`BondRule` preserves
    every atom's degree, a valence-insane PRODUCT can only arise from a valence-insane SOURCE, so a single
    check on the joined source graph is sufficient (certified by dalembert).

    SCOPE (honest, per dalembert's refutation of the naive neutral-max rule).  The check is charge-AGNOSTIC:
    it uses :data:`_MAX_COORDINATION`, the ceiling over ALL charge states, so it refuses only valences
    impossible in EVERY state and never false-rejects a real net-neutral charge-separated molecule (CO,
    ozone, amine-boranes) or a real hypervalent (sulfate, perchlorate, hypervalent iodine).  It therefore
    does NOT catch a species impossible only AS A NEUTRAL but possible as an ion (a hand-built neutral
    ammonium, N at degree 4): distinguishing that from CO needs per-atom formal charge, which the graph does
    not carry -- so it is an information-theoretic boundary, not a claim of complete valence validation.
    Such species do not arise from the parser (it assigns them a charge, which is refused upstream).  An
    element with no tabulated ceiling (a metal, an opaque non-element label) is likewise unconstrained.
    """
    for label, degree in zip(graph.labels, graph.degrees):
        ceiling = _MAX_COORDINATION.get(label)
        if ceiling is not None and degree > ceiling:
            return False
    return True


def _joined(molecules: tuple[Molecule, ...]) -> BondGraph:
    graph = BondGraph(())
    for molecule in molecules:
        if type(molecule) is not Molecule or molecule.charge != 0 or molecule.state:
            raise RuleError("bridge supports only neutral species with empty state labels")
        if not molecule.atoms:
            raise RuleError("charge/energy carriers need a different bridge")
        graph = graph.tensor(BondGraph(molecule.atoms, frozenset(
            Edge(b.i, b.j, b.order) for b in molecule.bonds
        )))
    if not valence_sane(graph):
        raise RuleError("valence-impossible species: an atom exceeds its maximal normal valence")
    return graph


def _config(graph: BondGraph) -> Config:
    """Independent connected-component reconstruction of neutral endpoint species."""
    adjacent = {i: set() for i in range(len(graph.labels))}
    for e in graph.edges:
        adjacent[e.i].add(e.j)
        adjacent[e.j].add(e.i)
    remaining = set(adjacent)
    molecules = []
    while remaining:
        start = min(remaining)
        stack, component = [start], set()
        while stack:
            i = stack.pop()
            if i not in component:
                component.add(i)
                stack.extend(adjacent[i] - component)
        remaining -= component
        ordered = sorted(component)
        local = {old: new for new, old in enumerate(ordered)}
        molecules.append(Molecule(
            tuple(graph.labels[i] for i in ordered),
            frozenset(Bond(local[e.i], local[e.j], e.order) for e in graph.edges
                      if e.i in component and e.j in component),
        ))
    return Config.of(*molecules)


@dataclass(frozen=True)
class ScissionAudit:
    transform: CappedScission
    decomposition: RewriteWitness
    synthesis: RewriteWitness
    recognized_class: str | None

    def open(self) -> OpenChemDiagram:
        """Structural endpoint projection only; preserves the existing step semantics."""
        if not verify(self.synthesis):
            raise RuleError("invalid synthesis witness")
        return OpenChemDiagram.from_reaction(Reaction(
            _config(self.synthesis.source), _config(self.synthesis.target), name="experiment-step"
        ))

    @property
    def readiness(self) -> str:
        return "FORMAL_CANDIDATE"


def audit_scission(scission: CappedScission) -> ScissionAudit:
    """Extract a local span and independently replay BOTH structural directions.

    Class membership is read from the existing oracle, not from the rule's ID.
    The verifier checks the rewrite; it does NOT prove that oracle correct.
    """
    if type(scission) is not CappedScission:
        raise RuleError("expected the existing CappedScission type")
    source = _joined((scission.reactant,) + scission.reagents)
    deleted = frozenset(Edge(b.i, b.j, b.order) for b in scission.cut)
    added = frozenset(Edge(b.i, b.j, b.order) for b in scission.caps)
    support = tuple(sorted({i for e in deleted | added for i in e.pair}))
    local = {old: new for new, old in enumerate(support)}
    left_edges = frozenset(e for e in source.edges if e.i in local and e.j in local)
    right_edges = (left_edges - deleted) | added

    def local_graph(edges):
        return BondGraph(tuple(source.labels[i] for i in support), frozenset(
            Edge(local[e.i], local[e.j], e.order) for e in edges
        ))

    rule = BondRule("capped-scission-structural-replay-v1", local_graph(left_edges), local_graph(right_edges))
    decomposition = apply(rule, source, support)
    synthesis = apply(rule.reverse(), decomposition.target, support)
    if not verify(decomposition) or not verify(synthesis) or synthesis.target != source:
        raise RuleError("independent replay/reversal failed")
    if _config(decomposition.target) != Config.of(*scission.products):
        raise RuleError("independently reconstructed products disagree with the generator")
    step = ExperimentStep.from_transform(scission)
    if _config(synthesis.source) != Config.of(*step.reactants):
        raise RuleError("synthesis input projection disagrees")
    if _config(synthesis.target) != Config.of(*step.products):
        raise RuleError("synthesis output projection disagrees")
    return ScissionAudit(scission, decomposition, synthesis, recognize_reaction_type(step))


@dataclass(frozen=True)
class AuditedCappedScissionProvider(CappedScissionProvider):
    """A real opt-in registry consumer, not a replacement for chemistry evidence.

    Same transforms on the supported state domain, extra verification work.
    Failed replay refuses; it never silently drops a transform then says complete.
    """
    provider_id: str = "audited-capped-scission"
    provider_version: str = "v1"

    @property
    def capability_manifest(self) -> tuple:
        return super().capability_manifest + (
            ("structural_replay", "fixed-vertices-v1"),
            ("state_domain", "neutral-empty-state-only"),
            ("chemical_authority", "unchanged-existing-oracle"),
        )

    def enumerate_audited(self, reactant, reagents, *, budget):
        # Match the existing neutral-provider contract in a mixed registry.
        if type(reactant) is Molecule and reactant.charge != 0:
            return (), True
        transforms, complete = super().enumerate_transforms(reactant, reagents, budget=budget)
        try:
            # Check even an empty result: unsupported state must not masquerade as
            # a complete empty chemistry search under this provider's manifest.
            _joined((reactant,) + tuple(reagents))
            audits = tuple(audit_scission(t) for t in transforms)
        except (RuleError, NotImplementedError) as error:
            raise ScissionError(f"rule-calculus replay refused: {error}") from error
        return audits, complete

    def enumerate_transforms(self, reactant, reagents, *, budget):
        audits, complete = self.enumerate_audited(reactant, reagents, budget=budget)
        return tuple(a.transform for a in audits), complete
