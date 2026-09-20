"""Diels-Alder [4+2] retro-disconnection family on the rule_calculus kernel -- structural, opt-in, Problem A only.

This module compiles ONE new benign reaction family (all-carbon Diels-Alder) onto the fixed-vertex
:mod:`smartchem.rule_calculus` kernel.  It enumerates GUARDED retro-DA disconnections of a target bond graph and
derives the class witness FROM THE MATCH (not a self-declared name).  It asserts structural type-validity only: a
witness means "this is a structurally valid [4+2] retro-Diels-Alder disconnection", NEVER that the forward reaction is
feasible, selective, or endo/exo-resolved (Problem B stays with :mod:`smartchem.experiment.feasibility`).

Design + boundaries: ``docs/research/RULE_CALCULUS_DIELS_ALDER_FAMILY_v0.1.md``.  This layer touches no default
provider registry, no production gate, and no existing recognizer.  Everything here fails CLOSED: a match that does not
pass every guard is DROPPED (honest coverage loss), never coerced into a witness.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .category import Config, ConservationError, Molecule, Reaction
from .contracts import Digestible
from .decompiler import DecompositionEdge, Formula
from .reaction_center import ReactionCenter
from .rule_calculus import BondGraph, BondRule, Edge, RewriteWitness, RuleError, enumerate_matches, verify
from .rule_calculus_bridge import _config, _joined, valence_sane
from .structure_descent import ScissionError
from .transform_provider import TransformProvider

# Forward [4+2]: diene C0=C1-C2=C3  +  dienophile C4=C5  ->  cyclohexene ring C0-C1=C2-C3-C4-C5-C0.
# Per-atom bond-order sums are preserved (2,3,3,2,2,2) both sides -- a pericyclic reaction conserves valence, so it
# lives natively in the degree-locked fixed-vertex fragment (proven in the feasibility spike).
_C6 = ("C",) * 6
_FORWARD = BondRule(
    "diels-alder-[4+2]-carbocyclic-v1",
    BondGraph(_C6, frozenset({Edge(0, 1, 2), Edge(1, 2, 1), Edge(2, 3, 2), Edge(4, 5, 2)})),
    BondGraph(_C6, frozenset({Edge(0, 1, 1), Edge(1, 2, 2), Edge(2, 3, 1),
                              Edge(3, 4, 1), Edge(4, 5, 1), Edge(0, 5, 1)})),
)
#: The disconnection direction R -> L: a cyclohexene adduct -> diene + dienophile.
RETRO_DA: BondRule = _FORWARD.reverse()
#: The class label the witness carries.  It is EMITTED only when the match's own net bond change matches this family's
#: signature AND the independent verifier agrees -- it is never asserted from the rule id alone (see :func:`class_witness`).
DA_CLASS = "diels-alder-[4+2]-carbocyclic"

# The diene carbons {0,1,2,3} and dienophile carbons {4,5} in the rule's own vertex numbering.
_DIENE = frozenset({0, 1, 2, 3})
_DIENOPHILE = frozenset({4, 5})

#: Neutral (uncharged) valence -- the total bond order an atom bears with NO formal charge (lone pairs filled by
#: implicit H).  The reaction-centre lock in :func:`_guarded_retro` bounds every MATCHED atom by THIS, not by the
#: charge-AGNOSTIC ceiling ``valence_sane`` uses (:data:`~smartchem.rule_calculus_bridge._MAX_COORDINATION`).  For
#: CARBON the two coincide (4 == 4), so the bound is a strict NO-OP for the all-carbon families (their frozen probes
#: stay byte-identical); for a heteroatom the ceiling EXCEEDS the neutral valence (O: 3 vs 2, N: 5 vs 3), and that
#: gap is exactly the room an oxa/aza retro used to emit a formally-charged oxocarbenium/iminium posed as a neutral
#: carbonyl/imine -- a TYPE false-vouch the round-9 adversary gate (evil-morty + dalembert) proved end-to-end.
#: Bounding the centre heteroatom by its NEUTRAL valence closes it with ZERO loss on real neutral cases (an ether O
#: stays bond-order 2; an N-substituted tetrahydropyridine N stays bond-order 3).  SULFUR (thia-DA, :data:`THIA_DA`)
#: is the round-9 kill ONE ELEMENT OVER: its charge-agnostic ceiling is 6 (hypervalent sulfate/sulfone), but a neutral
#: thioether/thiocarbonyl S bears bond order 2, and the gap is exactly the room a thia retro used to emit a
#: formally-charged thiocarbenium/sulfonium posed as a neutral thiocarbonyl -- a measured false-vouch (an S-methylated
#: dihydrothiopyran, ring S at bond order 3, retro'd to the garbage fragments ``C2S + C4`` WITHOUT this bound, DROPPED
#: WITH it).  So ``S: 2`` is not optional book-keeping, it is load-bearing the moment thia is in scope, and it is a
#: NO-OP on the real neutral thiopyran (which disconnects to ``CH2S + C4H6`` either way).  C/N/O/S are the [4+2] centre
#: atoms today; an unlisted label is unconstrained here (still gated by the charge-agnostic ceiling upstream),
#: deferred to its own future family's gate.
#:
#: SCOPE (honest, per dalembert's boundary probe): this bounds only the six MATCHED CENTRE atoms, so it closes the
#: fiction it targets -- a formally-charged oxocarbenium/iminium/thiocarbenium ON A MATCHED CENTRE drawn neutral (a
#: :class:`BondRule` preserves degree, so a matched atom bounded here is bounded in the emitted fragment too).  It
#: does NOT certify that an emitted fragment is neutral at EVERY atom: a NON-matched spectator substituent may still
#: carry a formal charge (a net-neutral, valence-sane molecule can hold a charge-separated substituent -- an O at
#: degree 3 -- since the graph carries only NET molecular charge, the same declared ``valence_sane`` boundary that
#: admits CO/ozone).  That is NOT a reaction-TYPE false-vouch (the [4+2] relation is genuine and the substituent is a
#: spectator on both sides), and it is not what guard 2c claims to close.  Certifying whole-fragment neutrality would
#: be a MEASURED tradeoff (it would false-reject a genuine charge-separated-neutral substituent), so it stays a future
#: labeled option, never a silent tightening.
_NEUTRAL_VALENCE: dict[str, int] = {"C": 4, "N": 3, "O": 2, "S": 2}

def _synthesis_center(rule: BondRule) -> ReactionCenter:
    """The coordinate-free reaction centre of ``rule`` in the SYNTHESIS (left->right) direction, DERIVED from the
    rule's own edge delta so it TRACKS the rule rather than a hand-typed constant that could silently drift when
    the family widens (dalembert's reinforcement): a bond whose order changes is BROKEN at its old order and FORMED
    at its new order; ``n_components`` counts the connected clusters of the changed-bond graph over the vertices."""
    left, right = rule.left, rule.right
    formed = [(right.labels[e.i], right.labels[e.j], e.order) for e in right.edges - left.edges]
    broken = [(left.labels[e.i], left.labels[e.j], e.order) for e in left.edges - right.edges]
    adjacent: dict[int, set[int]] = {}
    for e in (right.edges - left.edges) | (left.edges - right.edges):
        adjacent.setdefault(e.i, set()).add(e.j)
        adjacent.setdefault(e.j, set()).add(e.i)
    seen: set[int] = set()
    components = 0
    for start in adjacent:
        if start in seen:
            continue
        components += 1
        stack = [start]
        while stack:
            v = stack.pop()
            if v not in seen:
                seen.add(v)
                stack.extend(adjacent[v] - seen)
    return ReactionCenter.of(formed, broken, components)


# The coordinate-free reaction CENTRE of the family in the SYNTHESIS direction (diene + alkene dienophile ->
# cyclohexene), derived from the FORWARD rule so the invariant is true BY CONSTRUCTION.  For this all-carbon [4+2]
# it evaluates to formed = 5x(C,C,1)+(C,C,2), broken = 3x(C,C,2)+(C,C,1), one six-carbon cluster -- a family
# invariant (every guarded match maps the same six all-carbon vertices, substituents ride OUTSIDE them), so no
# guarded DA is ever false-demoted by the oracle's exact-equality check (verified by both adversaries).
_DA_CENTER = _synthesis_center(_FORWARD)


@dataclass(frozen=True)
class DisconnectionAudit:
    """A guard-passed retro-DA disconnection: the kernel witness plus the derived class."""
    witness: RewriteWitness
    reaction_class: str
    diene_vertices: tuple[int, ...]
    dienophile_vertices: tuple[int, ...]


def _induced_edges(graph: BondGraph, vertices) -> frozenset[Edge]:
    """Edges of ``graph`` with BOTH endpoints in ``vertices`` -- the induced subgraph (the locality lock)."""
    vs = set(vertices)
    return frozenset(e for e in graph.edges if e.i in vs and e.j in vs)


def _component_of(graph: BondGraph, seeds) -> frozenset[int]:
    """Connected component(s) of ``graph`` reachable from ``seeds`` (undirected)."""
    adjacent: dict[int, set[int]] = {i: set() for i in range(len(graph.labels))}
    for e in graph.edges:
        adjacent[e.i].add(e.j)
        adjacent[e.j].add(e.i)
    seen: set[int] = set()
    stack = list(seeds)
    while stack:
        i = stack.pop()
        if i not in seen:
            seen.add(i)
            stack.extend(adjacent[i] - seen)
    return frozenset(seen)


def _match_signature(witness: RewriteWitness) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The net bond change of THIS match, read off the witness (not the rule id): (deleted orders, added orders)."""
    rule = witness.rule
    deleted = tuple(sorted(e.order for e in rule.left.edges - rule.right.edges))
    added = tuple(sorted(e.order for e in rule.right.edges - rule.left.edges))
    return deleted, added


# The [4+2] retro signature computed from the family rule itself, so the check tracks the rule, not a hand-typed constant.
_RETRO_SIGNATURE = _match_signature(RewriteWitness(RETRO_DA, RETRO_DA.left, tuple(range(6)), RETRO_DA.right))


def class_witness(witness: RewriteWitness) -> str | None:
    """The reaction CLASS derived from the actual match, or ``None`` (fail-closed) if it is not a [4+2] retro-DA.

    The label is not asserted from the rule id: it is emitted only when the match's OWN net bond-order change equals
    this family's signature.  A mismatch -- a mutated rule, a different net change -- yields ``None``.

    Delegates to the family-generic :func:`_class_witness` bound to this family's own signature/label, so the
    alkene family reads byte-identically while a sibling family (the alkyne dienophile) supplies its own pair.
    """
    return _class_witness(witness, _RETRO_SIGNATURE, DA_CLASS)


def _class_witness(witness: RewriteWitness, signature: tuple, label: str) -> str | None:
    """Generic fail-closed class witness: ``label`` is emitted only when ``witness`` both kernel-verifies AND its
    own net bond-order change equals ``signature`` -- the family-parameterized core of :func:`class_witness`, so
    a mutated rule or a different net change still yields ``None`` no matter which [4+2] family calls it."""
    if not verify(witness):
        return None
    if _match_signature(witness) != signature:
        return None
    return label


def independently_reconstructs(target: BondGraph, retro_result: BondGraph, match: tuple[int, ...],
                                forward: BondRule = _FORWARD) -> bool:
    """Independent verifier (separate representation from the enumerator's ``apply``): does re-forming the two cleaved
    sigma bonds and restoring the pi shift on ``retro_result`` reproduce ``target`` EXACTLY, by adjacency multiset?

    This never calls :func:`apply`.  It rebuilds the forward bond delta from the rule geometry and the match, applies
    it to ``retro_result`` as a pair->order table, and compares to ``target``.  A forgery that fools the enumerator
    but not this recomputation is rejected.  ``forward`` defaults to the alkene family's own rule so this stays
    byte-identical for every existing caller; a sibling family (e.g. the alkyne dienophile) passes its own rule.
    """
    try:
        if target.labels != retro_result.labels:
            return False
        # Forward delta (synthesis L->R) mapped through the match, computed from the rule geometry directly.
        deleted = {tuple(sorted((match[e.i], match[e.j]))): e.order for e in forward.left.edges - forward.right.edges}
        added = {tuple(sorted((match[e.i], match[e.j]))): e.order for e in forward.right.edges - forward.left.edges}
        table = {e.pair: e.order for e in retro_result.edges}
        for pair, order in deleted.items():        # bonds the forward reaction consumes must be present to remove
            if table.get(pair) != order:
                return False
            del table[pair]
        for pair, order in added.items():          # bonds the forward reaction forms must not already survive
            if pair in table:
                return False
            table[pair] = order
        return table == {e.pair: e.order for e in target.edges}
    except (AttributeError, TypeError, ValueError, KeyError, IndexError):
        return False


def _guarded_retro(retro_rule: BondRule, forward_rule: BondRule, retro_signature: tuple, class_label: str,
                    target: BondGraph, *, budget: int = 100000) -> tuple[tuple[DisconnectionAudit, ...], bool]:
    """The rule-parameterized GUARDED retro-[4+2] core (dalembert's ask: one enforcement point, not one per family).

    Every guard below is family-AGNOSTIC -- it reads ``retro_rule``/``forward_rule``/``retro_signature``/
    ``class_label`` rather than the alkene family's module-level constants -- so a sibling dienophile family (the
    alkyne one) rides the SAME enforcement, not a hand-copied second one that could silently drift out of guard-step.
    :func:`retro_da_disconnections` (alkene) and :func:`retro_alkyne_da_disconnections` are now both thin callers.

    Guards (each failure DROPS the match -- coverage loss, never a coerced witness), per the design doc s3:
      2. induced-subgraph exactness on the six matched centre atoms (locality lock: no extra bond forges a fake adduct);
      2b. no exocyclic MULTIPLE bond on a matched atom (the ketene/allene false-VOUCH kill);
      2c. no matched CENTRE atom over its NEUTRAL valence (:data:`_NEUTRAL_VALENCE`) -- the oxa/aza oxocarbenium/
          iminium false-VOUCH kill; a NO-OP for carbon (ceiling == neutral valence), load-bearing for a heteroatom
          whose charge-agnostic ceiling exceeds its neutral valence (guard 2b bounds bond ORDER, not the count of
          exocyclic single bonds, so it is 2c -- not 2b -- that stands between a hetero retro and a charged fragment);
      3. aromatic ADDUCTS are excluded automatically -- the induced pattern fixes the adduct's ring unsaturation
         count exactly (one C=C for the alkene family, the 1,4-diene for the alkyne family), so a fully aromatic
         ring never matches.  This constrains the ADDUCT ONLY, NOT the retro FRAGMENTS (dalembert): a guarded
         retro CAN yield an aromatic diene fragment (benzene from barrelene, family-wide), vouched as a
         structurally valid [4+2] TYPE -- its feasibility (benzene a reluctant diene, anthracene a willing one)
         is Problem B, deferred, never a type-validity claim here;
      5. the retro must GLOBALLY disconnect the target into a diene component and a disjoint dienophile component;
      + the class witness (match signature) and the independent verifier must both agree.
    """
    if type(target) is not BondGraph:
        raise RuleError("_guarded_retro expects a BondGraph target")
    if not valence_sane(target):
        return (), True  # a valence-impossible molecule has no valid chemistry: no disconnections, definitively
    receipt = enumerate_matches(retro_rule, target, budget=budget)
    audits: list[DisconnectionAudit] = []
    seen_products: set[str] = set()  # collapse symmetric matches that yield the SAME product presentation
    for w in receipt.witnesses:
        m = w.match
        # Guard 2: the six matched carbons induce EXACTLY the ring pattern (no extra bond among them).
        if _induced_edges(target, m) != frozenset(Edge(m[e.i], m[e.j], e.order) for e in retro_rule.left.edges):
            continue
        # Guard 2b (evil-morty KILL -- the cyclohexenone/ketene false-VOUCH): every matched carbon becomes an sp2
        # alkene terminus in the retro products, so NONE may carry an exocyclic MULTIPLE bond.  A ring carbonyl (C=O)
        # would retro to a KETENE (C=C=O) and an exocyclic alkene to an allene -- cumulenes, not [4+2] partners (a
        # ketene does [2+2]).  A matched carbon may bond to a non-matched atom ONLY by a single bond.  Fail-closed:
        # this also drops the rare genuine allene-forming retro-DA (acceptable coverage loss), but it forbids the
        # catastrophic ketene/enone false-VOUCH.  A norbornene-type single-atom bridge is SINGLE bonds, so it is KEPT.
        matched = set(m)
        if any(e.order != 1 for e in target.edges if (e.i in matched) != (e.j in matched)):
            continue
        # Guard 2c (round-9 evil-morty + dalembert KILL -- the oxocarbenium/iminium false-VOUCH): guard 2b bounds the
        # BOND ORDER of a crossing bond (no exocyclic multiple) but NOT the NUMBER of exocyclic single bonds, and for
        # a heteroatom the charge-agnostic ceiling (valence_sane, #83) EXCEEDS its neutral valence -- so a hetero
        # retro could emit an O at bond-order 3 / N at 4, a formally-charged oxocarbenium/iminium posed as a neutral
        # carbonyl/imine (a TYPE false-vouch).  Bound every matched CENTRE atom by its NEUTRAL valence: a NO-OP for
        # carbon (4 == its ceiling, so this never fires and the all-carbon families stay byte-identical), and for a
        # heteroatom it drops exactly the over-neutral-valence fiction while KEEPING real neutral centres (an ether O
        # at bond-order 2, an N-substituted amine N at bond-order 3).  An unlisted centre label is unconstrained here.
        if any((nv := _NEUTRAL_VALENCE.get(target.labels[v])) is not None and target.degrees[v] > nv for v in m):
            continue
        # Class witness derived from the match + kernel verify.
        cls = _class_witness(w, retro_signature, class_label)
        if cls is None:
            continue
        # Independent verifier: reconstruction reproduces the target exactly.
        if not independently_reconstructs(target, w.target, m, forward_rule):
            continue
        # Guard 5: global two-fragment split -- diene carbons and dienophile carbons land in DISJOINT components.
        diene_seeds = {m[i] for i in _DIENE}
        dienophile_seeds = {m[i] for i in _DIENOPHILE}
        diene_comp = _component_of(w.target, diene_seeds)
        dienophile_comp = _component_of(w.target, dienophile_seeds)
        if diene_comp & dienophile_comp:
            continue  # still connected (fused/bridged through external atoms) -> deferred, dropped
        if not (diene_seeds <= diene_comp and dienophile_seeds <= dienophile_comp):
            continue
        digest = w.target.digest
        if digest in seen_products:
            continue
        seen_products.add(digest)
        audits.append(DisconnectionAudit(
            witness=w, reaction_class=cls,
            diene_vertices=tuple(sorted(diene_seeds)),
            dienophile_vertices=tuple(sorted(dienophile_seeds)),
        ))
    return tuple(audits), receipt.complete


def retro_da_disconnections(target: BondGraph, *, budget: int = 100000) -> tuple[tuple[DisconnectionAudit, ...], bool]:
    """Every GUARDED retro-Diels-Alder disconnection of ``target`` (alkene dienophile family), plus an honest
    completeness flag.  A thin caller of the family-generic :func:`_guarded_retro`; see its docstring for the guards.
    """
    return _guarded_retro(RETRO_DA, _FORWARD, _RETRO_SIGNATURE, DA_CLASS, target, budget=budget)


# --------------------------------------------------------------------------------------------------------------------
# The opt-in transform + provider: plug the guarded retro-DA through the UNCHANGED route/DAG provider seam.
# It rides the duck-typed `ExperimentStep.from_transform` path exactly like `RedoxDisplacementEdge` (a multi-product,
# opt-in family already absent from the default registry); it touches no shared file and no default registry.
# --------------------------------------------------------------------------------------------------------------------

DA_RETRO_SCHEMA = "smartchem.diels-alder/retro-v1"


# --------------------------------------------------------------------------------------------------------------------
# Item F -- the ONE shared product-config law every DA family's edge + provider rides.  Historically the alkene,
# alkyne and hetero families each carried a byte-identical copy of ``forget()`` and of the provider
# ``enumerate_transforms`` body; the copies could silently drift out of step.  These two helpers hold the single
# law: (1) a retro edge's composition-level image is the formula-multiset decomposition of the adduct into its
# fragments; (2) a provider enumerates guarded retro disconnections and presents each audit's products through the
# SAME ``_config`` canonicalisation before building its family's edge.  The edge CLASSES keep their own identities
# (their qualnames are baked into the content digest, so a frozen probe would move if they merged) -- only the
# shared BODY is factored out, so this is a pure dedup with byte-identical behaviour (every DA probe hash holds).
# --------------------------------------------------------------------------------------------------------------------

def _da_forget(reactant: Molecule, products: tuple[Molecule, ...]) -> DecompositionEdge:
    """The composition-level image shared by every DA retro edge: the formula-level decomposition of the adduct
    ``reactant`` into its ``products`` (elements bucketed, molecules counted, ordered canonically by rank/repr)."""
    merged: dict[Formula, int] = {}
    for m in products:
        comp = Formula.of(m.formula, m.charge)
        if comp.is_element:
            (symbol, count), = comp.counts
            bucket = Formula.bucket(symbol)
            merged[bucket] = merged.get(bucket, 0) + count
        else:
            merged[comp] = merged.get(comp, 0) + 1
    ordered = tuple(sorted(merged.items(), key=lambda pm: (pm[0].rank, repr(pm[0]))))
    return DecompositionEdge(Formula.of(reactant.formula, reactant.charge), 1, ordered)


def _enumerate_da_transforms(reactant, budget, disconnect, make_edge) -> tuple[tuple, bool]:
    """The opt-in provider body shared by every DA family.  Boundary contract: never raise; a target this family
    cannot address (wrong type / charged / stateful / non-transportable) enumerates nothing and is complete.
    ``disconnect(graph, budget)`` returns ``(audits, complete)`` for the family's guarded retro; each audit's
    products are read back through the ONE ``_config`` canonicalisation and handed to ``make_edge(reactant,
    products)``.  Fail-closed: an edge its own double certificate refuses is DROPPED, never coerced."""
    if type(reactant) is not Molecule or reactant.charge != 0 or reactant.state:
        return (), True
    try:
        graph = _joined((reactant,))
    except (RuleError, ScissionError, TypeError, ValueError):
        return (), True   # non-transportable (charged/stateful/atomless) -> fall through, do not crash the mix
    audits, complete = disconnect(graph, budget)
    transforms = []
    for a in audits:
        products = _config(a.witness.target).species
        try:
            transforms.append(make_edge(reactant, tuple(products)))
        except ScissionError:
            continue   # the edge's own certificates refused it -> drop (fail-closed), never a coerced transform
    return tuple(transforms), complete


def _reactant_da_disconnects_to(reactant: Molecule, products: tuple[Molecule, ...]) -> bool:
    """Self-contained DA-ness certificate: does ``reactant`` admit a GUARDED [4+2] retro whose two fragments are
    exactly ``products`` (as a Config)?  Re-derived from the reactant alone, so a hand-built edge cannot carry
    fabricated fragments that merely happen to balance mass (the DA analogue of the redox electron-ledger fold).

    Cheap necessary conditions gate the enumeration first (IDENTITY-PRESERVING -- a guarded retro-DA matches a
    six-carbon ring bearing one ring C=C, so an acyclic / sub-six-carbon / alkene-free molecule cannot admit one
    and the enumeration would find nothing).  The oracle recognizer runs this in the production route-ranking hot
    path for EVERY 2->1 step (all users, not just opt-in), so this early-out keeps the common acyclic
    capped-scission fragment off the enumeration path."""
    if sum(1 for a in reactant.atoms if a == "C") < 6:
        return False
    if len(reactant.bonds) < len(reactant.atoms):  # a connected molecule is acyclic iff |bonds| < |atoms|
        return False
    if not any(b.order == 2 and reactant.atoms[b.i] == "C" and reactant.atoms[b.j] == "C" for b in reactant.bonds):
        return False
    try:
        graph = _joined((reactant,))
    except (RuleError, ScissionError, TypeError, ValueError):
        return False
    want = Config.of(*products)
    audits, _ = retro_da_disconnections(graph)
    return any(_config(a.witness.target) == want for a in audits)


@dataclass(frozen=True)
class DielsAlderRetroEdge(Digestible):
    """A retro-Diels-Alder [4+2] disconnection, stored as a DECOMPOSITION of ``reactant`` (the carbocyclic adduct)
    into ``(diene, dienophile)`` so it satisfies the uniform transform interface and reverses (via
    :meth:`ExperimentStep.from_transform`) into the forward synthesis that MAKES the adduct.  Reagentless.

    Two independent certificates run at construction, so even a hand-built edge cannot ship a fiction: (1) mass AND
    charge conservation, re-checked by building a real :class:`Reaction` (exactly as :class:`ExperimentStep` and
    :class:`RedoxDisplacementEdge` do); (2) DA-ness -- the reactant must actually admit a guarded [4+2] retro whose
    fragments are these products (:func:`_reactant_da_disconnects_to`).  Conservation ALONE does not prove a [4+2]
    (many 2-fragment splits balance mass), so the second cert is load-bearing.  Structural type-validity only
    (Problem A): NO feasibility, selectivity, endo/exo or regiochemistry is asserted.
    """

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reaction_class: str

    def __post_init__(self) -> None:
        if self.schema_version != DA_RETRO_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {DA_RETRO_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a Molecule")
        if self.reagents != ():
            raise ScissionError("a retro-Diels-Alder is reagentless")
        if (type(self.products) is not tuple or len(self.products) != 2
                or any(type(m) is not Molecule for m in self.products)):
            raise ScissionError("a retro-DA yields exactly two product Molecules (diene, dienophile)")
        if self.reaction_class != DA_CLASS:
            raise ScissionError(f"reaction_class must be {DA_CLASS!r}")
        # (1) independent conservation certificate (mass + charge), decomposition view.
        try:
            Reaction(Config.of(self.reactant), Config.of(*self.products), name="diels-alder-retro")
        except ConservationError as clash:
            raise ScissionError(f"retro-DA does not conserve mass/charge: {clash}") from clash
        # (2) DA-ness certificate: conservation alone does not prove a [4+2] -- re-derive it from the reactant.
        if not _reactant_da_disconnects_to(self.reactant, self.products):
            raise ScissionError("not a [4+2] adduct of these fragments (a fabricated DA edge is refused)")

    def equation(self) -> str:
        rhs = " + ".join(repr(m) for m in self.products)
        return f"{self.reactant!r} -> {rhs}"

    def reaction_center(self) -> ReactionCenter:
        """The coordinate-free [4+2] reaction centre in the synthesis direction -- the family invariant
        :data:`_DA_CENTER`.  ``__post_init__`` has already re-derived this edge's DA-ness, so every valid edge
        carries exactly this centre; surfacing it lets :meth:`ExperimentStep.from_transform` annotate the step and
        lets the reaction-type oracle confirm the pericyclic elementarity (span-local) instead of trusting the type."""
        return _DA_CENTER

    def forget(self) -> DecompositionEdge:
        """The composition-level image: the formula-level decomposition of the adduct into its two fragments
        (the shared item-F law, :func:`_da_forget`)."""
        return _da_forget(self.reactant, self.products)

    def __repr__(self) -> str:
        return f"DielsAlderRetroEdge({self.equation()})"


@dataclass(frozen=True)
class DielsAlderProvider(TransformProvider):
    """The all-carbon Diels-Alder [4+2] retro family as an OPT-IN provider (absent from the default registry, the
    ``RedoxHalfReactionProvider`` precedent).  Reagentless; neutral, empty-state carbocyclic targets only.  It rides
    the route/DAG seam with zero changes to shared machinery and asserts structural type-validity only (Problem A)."""

    provider_id: str = "diels-alder-retro"
    provider_version: str = "v1"
    witness_kind: str = "DIELS_ALDER"

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", DA_CLASS),
            ("mechanism", "concerted [4+2] retro-cycloaddition, 2 sigma broken / pi restored, reagentless, neutral"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "DECOMPOSITION_EDGE"),
            ("state_domain", "neutral-empty-state-carbocyclic-only"),
            ("chemical_authority", "structural-type-validity-only-problem-A"),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        return _enumerate_da_transforms(
            reactant, budget,
            lambda g, b: retro_da_disconnections(g, budget=b),
            lambda r, p: DielsAlderRetroEdge(DA_RETRO_SCHEMA, r, p, (), DA_CLASS),
        )


# --------------------------------------------------------------------------------------------------------------------
# The ALKYNE-dienophile sibling family: diene + alkyne -> 1,4-cyclohexadiene (NOT 1,3 -- the verified chemistry).
# Same degree-locked kernel, same guards (via _guarded_retro), same opt-in seam; only the dienophile bond order (a
# triple, not a double) and the forward product's second ring pi bond (the retro-DA leaves the OTHER alkyne carbon
# pair as C=C too) differ, so this is a genuinely separate rule, not a relabelling of the alkene one.
# --------------------------------------------------------------------------------------------------------------------

# Forward [4+2] (alkyne dienophile): diene C0=C1-C2=C3 + dienophile C4#C5 -> 1,4-cyclohexadiene ring, where the
# triple bond's second pi shifts INTO the ring (C4=C5 survives as a ring alkene) alongside the diene's own new
# central pi shift (C1=C2) -- both original diene pi bonds become ring sigma bonds. Degree-preserving both sides
# (2,3,3,2,3,3): the alkyne carbons carry one MORE bond-order unit than an alkene dienophile, spent on the ring C=C
# that alkene DA cannot form (an alkene dienophile has no second pi to donate).
_FORWARD_ALKYNE = BondRule(
    "diels-alder-[4+2]-alkyne-carbocyclic-v1",
    BondGraph(_C6, frozenset({Edge(0, 1, 2), Edge(1, 2, 1), Edge(2, 3, 2), Edge(4, 5, 3)})),
    BondGraph(_C6, frozenset({Edge(0, 1, 1), Edge(1, 2, 2), Edge(2, 3, 1),
                              Edge(3, 4, 1), Edge(4, 5, 2), Edge(0, 5, 1)})),
)
#: The disconnection direction R -> L: a 1,4-cyclohexadiene adduct -> diene + alkyne dienophile.
RETRO_ALKYNE_DA: BondRule = _FORWARD_ALKYNE.reverse()
#: The class label this sibling family's witness carries -- distinct from :data:`DA_CLASS` so the two never collide.
ALKYNE_DA_CLASS = "diels-alder-[4+2]-alkyne-cyclohexadiene"
_ALKYNE_RETRO_SIGNATURE = _match_signature(
    RewriteWitness(RETRO_ALKYNE_DA, RETRO_ALKYNE_DA.left, tuple(range(6)), RETRO_ALKYNE_DA.right)
)
#: The coordinate-free reaction CENTRE of the alkyne family in the SYNTHESIS direction, DERIVED from the forward
#: rule (never hand-typed) -- same discipline as :data:`_DA_CENTER`, so the oracle recognizer can compare by exact
#: equality without either family's centre drifting relative to its own rule.
_ALKYNE_DA_CENTER = _synthesis_center(_FORWARD_ALKYNE)


def retro_alkyne_da_disconnections(target: BondGraph, *,
                                    budget: int = 100000) -> tuple[tuple[DisconnectionAudit, ...], bool]:
    """Every GUARDED retro-Diels-Alder disconnection of ``target`` (alkyne dienophile family), plus an honest
    completeness flag.  A thin caller of the family-generic :func:`_guarded_retro`; see its docstring for the guards.
    """
    return _guarded_retro(RETRO_ALKYNE_DA, _FORWARD_ALKYNE, _ALKYNE_RETRO_SIGNATURE, ALKYNE_DA_CLASS, target,
                          budget=budget)


ALKYNE_DA_RETRO_SCHEMA = "smartchem.diels-alder/alkyne-retro-v1"


def _reactant_alkyne_da_disconnects_to(reactant: Molecule, products: tuple[Molecule, ...]) -> bool:
    """The alkyne-family analogue of :func:`_reactant_da_disconnects_to` -- same cheap pre-filter (a 1,4-
    cyclohexadiene adduct is cyclic, >=6 ring carbons, and carries a ring C=C, so it passes identically), but re-
    derives DA-ness through :func:`retro_alkyne_da_disconnections` so it certifies THIS family, not the alkene one."""
    if sum(1 for a in reactant.atoms if a == "C") < 6:
        return False
    if len(reactant.bonds) < len(reactant.atoms):  # a connected molecule is acyclic iff |bonds| < |atoms|
        return False
    if not any(b.order == 2 and reactant.atoms[b.i] == "C" and reactant.atoms[b.j] == "C" for b in reactant.bonds):
        return False
    try:
        graph = _joined((reactant,))
    except (RuleError, ScissionError, TypeError, ValueError):
        return False
    want = Config.of(*products)
    audits, _ = retro_alkyne_da_disconnections(graph)
    return any(_config(a.witness.target) == want for a in audits)


@dataclass(frozen=True)
class AlkyneDielsAlderEdge(Digestible):
    """A retro-Diels-Alder [4+2] disconnection of the ALKYNE-dienophile family, stored as a DECOMPOSITION of
    ``reactant`` (the 1,4-cyclohexadiene adduct) into ``(diene, alkyne dienophile)`` -- the alkyne-family sibling of
    :class:`DielsAlderRetroEdge`, cloned structure, own schema/class/certificate/centre so it can never be confused
    with (or silently substitute for) the alkene family's edge.
    """

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reaction_class: str

    def __post_init__(self) -> None:
        if self.schema_version != ALKYNE_DA_RETRO_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {ALKYNE_DA_RETRO_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a Molecule")
        if self.reagents != ():
            raise ScissionError("a retro-Diels-Alder is reagentless")
        if (type(self.products) is not tuple or len(self.products) != 2
                or any(type(m) is not Molecule for m in self.products)):
            raise ScissionError("a retro-DA yields exactly two product Molecules (diene, dienophile)")
        if self.reaction_class != ALKYNE_DA_CLASS:
            raise ScissionError(f"reaction_class must be {ALKYNE_DA_CLASS!r}")
        # (1) independent conservation certificate (mass + charge), decomposition view.
        try:
            Reaction(Config.of(self.reactant), Config.of(*self.products), name="diels-alder-alkyne-retro")
        except ConservationError as clash:
            raise ScissionError(f"retro-DA does not conserve mass/charge: {clash}") from clash
        # (2) DA-ness certificate: conservation alone does not prove a [4+2] -- re-derive it from the reactant.
        if not _reactant_alkyne_da_disconnects_to(self.reactant, self.products):
            raise ScissionError("not an alkyne [4+2] adduct of these fragments (a fabricated DA edge is refused)")

    def equation(self) -> str:
        rhs = " + ".join(repr(m) for m in self.products)
        return f"{self.reactant!r} -> {rhs}"

    def reaction_center(self) -> ReactionCenter:
        """The coordinate-free [4+2] reaction centre in the synthesis direction -- the alkyne family invariant
        :data:`_ALKYNE_DA_CENTER`, distinct from the alkene family's :data:`_DA_CENTER` (the alkyne one forms an
        extra ring C=C instead of a ring C-C), so the oracle can tell the two classes apart by exact equality."""
        return _ALKYNE_DA_CENTER

    def forget(self) -> DecompositionEdge:
        """The composition-level image: the formula-level decomposition of the adduct into its two fragments
        (the shared item-F law, :func:`_da_forget`)."""
        return _da_forget(self.reactant, self.products)

    def __repr__(self) -> str:
        return f"AlkyneDielsAlderEdge({self.equation()})"


@dataclass(frozen=True)
class AlkyneDielsAlderProvider(TransformProvider):
    """The alkyne-dienophile Diels-Alder [4+2] retro family as an OPT-IN provider (absent from the default
    registry, exactly like :class:`DielsAlderProvider`).  Reagentless; neutral, empty-state carbocyclic targets
    only.  It rides the route/DAG seam with zero changes to shared machinery and asserts structural type-validity
    only (Problem A)."""

    provider_id: str = "diels-alder-alkyne-retro"
    provider_version: str = "v1"
    witness_kind: str = "DIELS_ALDER_ALKYNE"

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", ALKYNE_DA_CLASS),
            ("mechanism", "concerted [4+2] retro-cycloaddition, alkyne dienophile -> 1,4-cyclohexadiene, "
                          "2 sigma broken / pi restored, reagentless, neutral"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "DECOMPOSITION_EDGE"),
            ("state_domain", "neutral-empty-state-carbocyclic-only"),
            ("chemical_authority", "structural-type-validity-only-problem-A"),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        return _enumerate_da_transforms(
            reactant, budget,
            lambda g, b: retro_alkyne_da_disconnections(g, budget=b),
            lambda r, p: AlkyneDielsAlderEdge(ALKYNE_DA_RETRO_SCHEMA, r, p, (), ALKYNE_DA_CLASS),
        )


# --------------------------------------------------------------------------------------------------------------------
# The HETEROATOM-dienophile [4+2] families: the FIRST non-all-carbon Diels-Alder families.  A hetero-DA is the alkene
# rule with dienophile vertex 5 RELABELED C -> heteroatom (N for the aza family, O for the oxa family).  Because the
# kernel matches by vertex LABEL, the degree pattern (2,3,3,2,2,2), every guard (via _guarded_retro), and the opt-in
# seam are shared VERBATIM with the all-carbon families -- while the label lock plus the heteroatom-bearing reaction
# centre keep every family provably disjoint (distinct centres, verified no cross-poach; an N-rule finds 0 matches on
# an all-carbon ring).  This is where the #83 charge-agnostic valence precondition first becomes LOAD-BEARING: a ring
# N/O is now an in-scope atom whose coordination ceiling (N=5, O=3) actually gates the input.
#
#   aza-DA:  diene + imine    (C=N)  ->  a tetrahydropyridine  (5C+1N ring, one ring C=C)  [C4H6 + CH3N -> C5H9N]
#   oxa-DA:  diene + carbonyl  (C=O) ->  a dihydropyran        (5C+1O ring, one ring C=C)  [C4H6 + CH2O -> C5H8O]
#
# Both are genuine, benign, thermal all-organic [4+2] cycloadditions (the parent thermal hetero-DA; a Lewis acid
# accelerates many, but the uncatalysed reaction is real).  Structural type-validity ONLY (Problem A) -- no
# feasibility, regiochemistry, or endo/exo -- exactly the all-carbon families' contract.  Product isomer VERIFIED on
# the kernel (the retro of the ring gives back diene + the hetero dienophile), never asserted (the 1,4-CHD lesson).
# --------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _HeteroDAFamily:
    """An immutable descriptor for ONE heteroatom [4+2] family (aza: X=N, oxa: X=O, thia: X=S).

    The family IS the all-carbon alkene rule with exactly ONE vertex relabeled ``C -> hetero_label``:

    * ``position == "dienophile"`` (``hetero_vertex == 5``) -- the heteroatom is the dienophile's second atom, an
      imine/carbonyl/thiocarbonyl ``C=X`` (aza -> tetrahydropyridine, oxa -> dihydropyran, thia -> dihydrothiopyran);
    * ``position == "diene"`` (``hetero_vertex == 0``) -- the heteroatom is a DIENE TERMINUS, a 1-hetero-1,3-diene
      ``X=C-C=C`` (a 1-azadiene / 1-oxadiene / 1-thiadiene; the classic inverse-electron-demand hetero-DA, an
      enone/enal acting as the 4-pi component).

    Either position shares the degree pattern ``(2,3,3,2,2,2)`` and EVERY guard in :func:`_guarded_retro` VERBATIM --
    guard 5 splits by the diene/dienophile VERTEX SETS (:data:`_DIENE` / :data:`_DIENOPHILE`, membership-agnostic to
    where the heteroatom sits) and guard 2c bounds every matched atom by its own LABEL's neutral valence -- so the
    generic guarded core needs no change to carry a diene-position family.

    Its ``center`` -- DERIVED from ``forward`` via :func:`_synthesis_center` so it TRACKS the rule -- carries
    ``(C, hetero_label, .)`` bond pairs no DIFFERENT-heteroatom family's centre carries.  CAUTION, the diene<->
    dienophile centre COLLISION (verified on the kernel): a diene-position and a dienophile-position family of the
    SAME heteroatom have the IDENTICAL synthesis centre -- the formed/broken ``(C,X,.)`` multiset is invariant to
    WHERE in the six-vertex ring the single X sits.  So the oracle's exact-equality centre check (Layer B) is a
    NECESSARY filter but NOT a separator for those two; Layer A (the family's own re-derivation) is, and it separates
    them cleanly because the two adducts are distinct REGIO-isomers -- X adjacent to the ring C=C for the diene
    family, X isolated from it for the dienophile family -- each matching ONLY its own relabeled rule (proven: an
    aza-diene adduct yields nothing under the aza-dienophile rule and vice versa)."""

    hetero_label: str
    class_label: str
    schema: str
    provider_id: str
    witness_kind: str
    forward: BondRule
    retro: BondRule
    signature: tuple
    center: ReactionCenter
    hetero_vertex: int
    position: str


def _hetero_family(hetero_label: str, class_label: str, schema: str, provider_id: str,
                   witness_kind: str, *, hetero_vertex: int = 5) -> _HeteroDAFamily:
    """Build a :class:`_HeteroDAFamily` for ``hetero_label`` at ``hetero_vertex``: the alkene [4+2] rule geometry
    with that one vertex's label swapped to the heteroatom.  ``hetero_vertex == 5`` (default) is the dienophile
    position (aza/oxa/thia); ``hetero_vertex == 0`` is the diene-terminus position (1-hetero-diene).  ``retro`` /
    ``signature`` / ``center`` are all DERIVED here so a family can never drift from its own rule."""
    if hetero_vertex not in (0, 5):
        raise RuleError("hetero_vertex must be 0 (diene terminus) or 5 (dienophile second atom)")
    position = "diene" if hetero_vertex == 0 else "dienophile"
    labels = tuple(hetero_label if i == hetero_vertex else "C" for i in range(6))
    forward = BondRule(
        f"diels-alder-[4+2]-{hetero_label}-{position}-heterocyclic-v1",
        BondGraph(labels, frozenset({Edge(0, 1, 2), Edge(1, 2, 1), Edge(2, 3, 2), Edge(4, 5, 2)})),
        BondGraph(labels, frozenset({Edge(0, 1, 1), Edge(1, 2, 2), Edge(2, 3, 1),
                                     Edge(3, 4, 1), Edge(4, 5, 1), Edge(0, 5, 1)})),
    )
    retro = forward.reverse()
    signature = _match_signature(RewriteWitness(retro, retro.left, tuple(range(6)), retro.right))
    return _HeteroDAFamily(hetero_label, class_label, schema, provider_id, witness_kind,
                           forward, retro, signature, _synthesis_center(forward), hetero_vertex, position)


#: The aza-Diels-Alder family (imine dienophile -> tetrahydropyridine): the first NON-all-carbon [4+2] family.
AZA_DA = _hetero_family("N", "diels-alder-[4+2]-aza-tetrahydropyridine",
                        "smartchem.diels-alder/aza-retro-v1", "diels-alder-aza-retro", "DIELS_ALDER_AZA")
#: The oxa-Diels-Alder family (carbonyl dienophile -> dihydropyran): the aza family's sibling, O in place of N.
OXA_DA = _hetero_family("O", "diels-alder-[4+2]-oxa-dihydropyran",
                        "smartchem.diels-alder/oxa-retro-v1", "diels-alder-oxa-retro", "DIELS_ALDER_OXA")
#: The thia-Diels-Alder family (thiocarbonyl dienophile -> 3,6-dihydro-2H-thiopyran): the third heteroatom
#: dienophile family (S in place of O), and the family whose neutral-valence guard 2c bound (S: 2 in
#: :data:`_NEUTRAL_VALENCE`) is LOAD-BEARING against a thiocarbenium/sulfonium false-vouch (S ceiling 6 >> neutral 2).
THIA_DA = _hetero_family("S", "diels-alder-[4+2]-thia-dihydrothiopyran",
                         "smartchem.diels-alder/thia-retro-v1", "diels-alder-thia-retro", "DIELS_ALDER_THIA")

# ---- item B: the DIENE-position (inverse-electron-demand) hetero families -- the heteroatom is a diene terminus,
# vertex 0, a 1-hetero-1,3-diene X=C-C=C.  These SHARE a synthesis centre with their same-heteroatom dienophile
# sibling (the (C,X,.) multiset is position-invariant), so they are the first families the oracle separates by
# Layer A ALONE (see :class:`_HeteroDAFamily`).  aza-diene (a 1-azadiene) and oxa-diene (a 1-oxadiene / enone) are
# the canonical, historically important inverse-demand classes; thia-diene rides the same factory for free.
#: The 1-azadiene family (aza-DA with the N at the diene terminus): diene + alkene -> a 2,3,4,5-tetrahydropyridine.
AZA_DIENE_DA = _hetero_family("N", "diels-alder-[4+2]-aza-diene-tetrahydropyridine",
                              "smartchem.diels-alder/aza-diene-retro-v1", "diels-alder-aza-diene-retro",
                              "DIELS_ALDER_AZA_DIENE", hetero_vertex=0)
#: The 1-oxadiene family (inverse-electron-demand oxa-DA, an enone/enal as the 4-pi diene): -> a dihydropyran isomer.
OXA_DIENE_DA = _hetero_family("O", "diels-alder-[4+2]-oxa-diene-dihydropyran",
                              "smartchem.diels-alder/oxa-diene-retro-v1", "diels-alder-oxa-diene-retro",
                              "DIELS_ALDER_OXA_DIENE", hetero_vertex=0)

#: Per-family synthesis centres (mirroring :data:`_DA_CENTER` / :data:`_ALKYNE_DA_CENTER`), so the oracle recognizer
#: and the cross-poach tests can pin each family by exact equality without reaching into the descriptor.  NOTE the
#: diene<->dienophile collision: ``_AZA_DA_CENTER == AZA_DIENE_DA.center`` (and likewise oxa) BY CONSTRUCTION -- these
#: are NOT a separator between those two families (Layer A is; see :class:`_HeteroDAFamily`).
_AZA_DA_CENTER = AZA_DA.center
_OXA_DA_CENTER = OXA_DA.center
_THIA_DA_CENTER = THIA_DA.center


def hetero_da_disconnections(family: _HeteroDAFamily, target: BondGraph, *,
                             budget: int = 100000) -> tuple[tuple[DisconnectionAudit, ...], bool]:
    """Every GUARDED retro-[4+2] disconnection of ``target`` for the heteroatom ``family``, plus an honest
    completeness flag.  A thin caller of the family-generic :func:`_guarded_retro` (the SAME enforcement the
    all-carbon families use), specialized only by the family's own relabeled rule / signature / class."""
    return _guarded_retro(family.retro, family.forward, family.signature, family.class_label, target, budget=budget)


def _reactant_hetero_da_disconnects_to(family: _HeteroDAFamily, reactant: Molecule,
                                       products: tuple[Molecule, ...]) -> bool:
    """The hetero-family analogue of :func:`_reactant_da_disconnects_to`: does ``reactant`` admit a GUARDED hetero
    [4+2] retro (for THIS family) whose two fragments are exactly ``products``?  Re-derived from the reactant alone,
    so a hand-built edge cannot smuggle fabricated fragments that merely balance mass.

    The cheap pre-filter is the all-carbon one with the carbon floor dropped to FIVE (a hetero adduct ring is 5 C +
    1 heteroatom, not 6 C) and a heteroatom-presence early-out added.  All four conditions are IDENTITY-PRESERVING:
    a valid hetero adduct is cyclic, carries >=5 carbons, holds >=1 atom of the family's heteroatom, and retains the
    all-carbon ring C=C the retro leaves behind, so a molecule missing any of these cannot admit this family's retro
    and the enumeration would find nothing anyway."""
    if sum(1 for a in reactant.atoms if a == "C") < 5:
        return False
    if family.hetero_label not in reactant.atoms:
        return False
    if len(reactant.bonds) < len(reactant.atoms):  # a connected molecule is acyclic iff |bonds| < |atoms|
        return False
    if not any(b.order == 2 and reactant.atoms[b.i] == "C" and reactant.atoms[b.j] == "C" for b in reactant.bonds):
        return False
    try:
        graph = _joined((reactant,))
    except (RuleError, ScissionError, TypeError, ValueError):
        return False
    want = Config.of(*products)
    audits, _ = hetero_da_disconnections(family, graph)
    return any(_config(a.witness.target) == want for a in audits)


@dataclass(frozen=True)
class HeteroDielsAlderEdge(Digestible):
    """A retro-Diels-Alder [4+2] disconnection of a HETEROATOM-dienophile family (aza or oxa), stored as a
    DECOMPOSITION of ``reactant`` (the heterocyclic adduct) into ``(diene, hetero-dienophile)``.

    ONE generic edge serves BOTH hetero families (they differ only by the one relabeled vertex).  It carries its
    ``family`` descriptor as a ``compare=False`` field, so the descriptor is EXCLUDED from the content digest and
    from equality (:func:`smartchem.contracts.canonical_payload` skips non-comparing fields): an aza edge and an oxa
    edge are already distinguished by their differing ``schema_version`` / ``reaction_class`` / ``reactant`` /
    ``products``, so dropping the descriptor from identity is sound AND keeps the digest a pure function of the
    chemistry.  Same double certificate as the all-carbon edges -- (1) mass+charge conservation via a real
    :class:`Reaction`, (2) family-specific DA-ness re-derived from the reactant
    (:func:`_reactant_hetero_da_disconnects_to`) -- so even a hand-built edge cannot ship a fiction.  Structural
    type-validity only (Problem A)."""

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reaction_class: str
    family: _HeteroDAFamily = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.schema_version != self.family.schema:
            raise ScissionError(f"schema_version must be exactly {self.family.schema!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a Molecule")
        if self.reagents != ():
            raise ScissionError("a retro-Diels-Alder is reagentless")
        if (type(self.products) is not tuple or len(self.products) != 2
                or any(type(m) is not Molecule for m in self.products)):
            raise ScissionError("a retro-DA yields exactly two product Molecules (diene, dienophile)")
        if self.reaction_class != self.family.class_label:
            raise ScissionError(f"reaction_class must be {self.family.class_label!r}")
        # (1) independent conservation certificate (mass + charge), decomposition view.
        try:
            Reaction(Config.of(self.reactant), Config.of(*self.products), name="diels-alder-hetero-retro")
        except ConservationError as clash:
            raise ScissionError(f"retro-DA does not conserve mass/charge: {clash}") from clash
        # (2) DA-ness certificate: conservation alone does not prove a [4+2] -- re-derive it for THIS family.
        if not _reactant_hetero_da_disconnects_to(self.family, self.reactant, self.products):
            raise ScissionError("not a hetero [4+2] adduct of these fragments (a fabricated DA edge is refused)")

    def equation(self) -> str:
        rhs = " + ".join(repr(m) for m in self.products)
        return f"{self.reactant!r} -> {rhs}"

    def reaction_center(self) -> ReactionCenter:
        """This family's heteroatom-bearing [4+2] synthesis centre (:attr:`_HeteroDAFamily.center`), distinct from
        every all-carbon and sibling-hetero family's centre, so the oracle tells the classes apart by exact
        equality."""
        return self.family.center

    def forget(self) -> DecompositionEdge:
        """The composition-level image: the formula-level decomposition of the adduct into its two fragments
        (the shared item-F law, :func:`_da_forget`)."""
        return _da_forget(self.reactant, self.products)

    def __repr__(self) -> str:
        return f"HeteroDielsAlderEdge({self.equation()})"


@dataclass(frozen=True)
class HeteroDielsAlderProvider(TransformProvider):
    """A heteroatom-dienophile Diels-Alder [4+2] retro family as an OPT-IN provider (absent from the default
    registry, like every DA provider).  ONE generic provider parameterized by its ``family`` descriptor; the typed
    identity fields (:attr:`provider_id` / :attr:`witness_kind`) and the manifest are read from the family, so aza
    and oxa get distinct identities out of a single class.  Reagentless; neutral, empty-state targets only;
    structural type-validity only (Problem A)."""

    family: _HeteroDAFamily

    @property
    def provider_id(self) -> str:
        return self.family.provider_id

    @property
    def provider_version(self) -> str:
        return "v1"

    @property
    def witness_kind(self) -> str:
        return self.family.witness_kind

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", self.family.class_label),
            ("mechanism", f"concerted [4+2] retro-cycloaddition, {self.family.hetero_label}-dienophile "
                          "(hetero-Diels-Alder), 2 sigma broken / pi restored, reagentless, neutral"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "DECOMPOSITION_EDGE"),
            ("state_domain", "neutral-empty-state-heterocyclic-only"),
            ("chemical_authority", "structural-type-validity-only-problem-A"),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        return _enumerate_da_transforms(
            reactant, budget,
            lambda g, b: hetero_da_disconnections(self.family, g, budget=b),
            lambda r, p: HeteroDielsAlderEdge(self.family.schema, r, p, (), self.family.class_label, self.family),
        )


@dataclass(frozen=True)
class AzaDielsAlderProvider(HeteroDielsAlderProvider):
    """The aza-Diels-Alder (imine dienophile -> tetrahydropyridine) opt-in provider -- :data:`AZA_DA` bound into the
    generic :class:`HeteroDielsAlderProvider`."""

    family: _HeteroDAFamily = AZA_DA


@dataclass(frozen=True)
class OxaDielsAlderProvider(HeteroDielsAlderProvider):
    """The oxa-Diels-Alder (carbonyl dienophile -> dihydropyran) opt-in provider -- :data:`OXA_DA` bound into the
    generic :class:`HeteroDielsAlderProvider`."""

    family: _HeteroDAFamily = OXA_DA


@dataclass(frozen=True)
class ThiaDielsAlderProvider(HeteroDielsAlderProvider):
    """The thia-Diels-Alder (thiocarbonyl dienophile -> dihydrothiopyran) opt-in provider -- :data:`THIA_DA` bound
    into the generic :class:`HeteroDielsAlderProvider`.  The third heteroatom-dienophile family (S)."""

    family: _HeteroDAFamily = THIA_DA


@dataclass(frozen=True)
class AzaDieneDielsAlderProvider(HeteroDielsAlderProvider):
    """The 1-azadiene Diels-Alder opt-in provider (the heteroatom in the DIENE, not the dienophile) --
    :data:`AZA_DIENE_DA` bound into the generic :class:`HeteroDielsAlderProvider`.  Shares a synthesis centre with
    :class:`AzaDielsAlderProvider`; the oracle keeps them apart by Layer A (see :class:`_HeteroDAFamily`)."""

    family: _HeteroDAFamily = AZA_DIENE_DA


@dataclass(frozen=True)
class OxaDieneDielsAlderProvider(HeteroDielsAlderProvider):
    """The 1-oxadiene (inverse-electron-demand) Diels-Alder opt-in provider -- :data:`OXA_DIENE_DA` bound into the
    generic :class:`HeteroDielsAlderProvider`.  Shares a synthesis centre with :class:`OxaDielsAlderProvider`;
    separated by Layer A."""

    family: _HeteroDAFamily = OXA_DIENE_DA
