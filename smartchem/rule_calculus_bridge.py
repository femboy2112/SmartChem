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
