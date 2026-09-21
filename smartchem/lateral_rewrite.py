"""Lateral-rewrite seam: [3,3] sigmatropic isomerizations (Cope + Claisen) on the rule_calculus kernel.

The FIRST non-decomposition transform family.  A retro-Diels-Alder is a RANK-DESCENDING decomposition (one adduct
-> two smaller fragments); a [3,3] sigmatropic shift is a RANK-FLAT ISOMERIZATION (one molecule -> one isomer of the
SAME formula).  The kernel accepts it natively -- a Cope/Claisen rewrite is degree-preserving, so it lives in the
fixed-vertex fragment exactly like a pericyclic cycloaddition -- but the strict-descent decompiler seam does NOT: a
``DecompositionEdge`` enforces invariant W1 ("every product has strictly smaller :attr:`Formula.rank`"), which a
rank-flat rewrite has NONE of.  That is a structure theorem, not a bug: the recursive route search's TERMINATION
rests on strict descent, so forcing an isomerization through the decompiler/conditions path is unsound.

WHAT THIS MODULE BUILDS (the seam's sound core) and WHAT IT DEFERS.
* BUILT -- the reusable lateral-rewrite machinery: the [3,3] rules (kernel-verified), a GUARDED standalone
  enumeration (:func:`sigmatropic_rewrites`), a rank-flat :class:`LateralRewriteEdge` carrying the same double
  certificate (conservation + own re-derivation) the DA edges carry, and -- via the reaction-type oracle -- a
  reachable CONSUMER: a route (hand-assembled today, or produced by a future lateral search) that contains a [3,3]
  step is VOUCHED as a real reaction TYPE instead of demoted as "unrecognized" (Problem A only -- no feasibility,
  no rate, no equilibrium position).
* DEFERRED (the epic, W1 reproduced end-to-end here) -- AUTO-DISCOVERY of isomerization routes by the recursive
  ``search_routes`` descent.  ``search_routes`` looks up sourced conditions via ``assembly_conditions`` ->
  ``transform.forget()``, and ``forget()`` must return a ``DecompositionEdge`` (W1).  A lateral edge cannot: its
  :meth:`LateralRewriteEdge.forget` RAISES on purpose, so a lateral provider must never be dropped into a
  ``search_routes`` registry -- and this module ships NO such provider (the enumeration is standalone).  If a future
  caller wires one in regardless, the raise propagates as a LOUD crash, never a silent rank-flat "route" -- the
  fail-loud surfacing of misuse; enforcing a guard at the search seam is part of the deferred epic.  Wiring
  isomerizations into the search needs a lateral conditions/search path that does not route through the
  strict-descent decompiler -- future work.  Design + boundary:
  ``docs/research/RULE_CALCULUS_LATERAL_REWRITE_SEAM_v0.1.md``.

Structural type-validity ONLY (Problem A).  A witness means "this is a structurally valid [3,3] sigmatropic
isomerization", NEVER that it is feasible, selective, or thermally allowed at a given temperature.  Everything here
fails CLOSED: a match that does not pass every guard is DROPPED (honest coverage loss), never coerced.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .category import Config, ConservationError, Molecule, Reaction
from .contracts import Digestible
from .diels_alder import _NEUTRAL_VALENCE, _match_signature, _synthesis_center, independently_reconstructs
from .reaction_center import ReactionCenter
from .rule_calculus import BondGraph, BondRule, Edge, RewriteWitness, RuleError, enumerate_matches, verify
from .rule_calculus_bridge import _config, _joined, valence_sane
from .structure_descent import ScissionError

# The 6-atom [3,3] sigmatropic array 0-1-2-3-4-5.  FORWARD (synthesis direction, reactant-isomer -> product-isomer):
#   pi 0=1, sigma 1-2, sigma 2-3 (BREAKS), sigma 3-4, pi 4=5   ->   sigma 0-1, pi 1=2, pi 3=4, sigma 4-5, sigma 0-5.
# One sigma (2-3) breaks, one sigma (0-5) forms; both pi bonds migrate; degrees are preserved (2,3,2,2,3,2) both
# sides (proven below), so the kernel accepts it.  For Cope every array atom is carbon; for Claisen atom 2 is the
# ether/carbonyl oxygen (vinyl-O-allyl -> pent-4-enal), which is why the array's centre carries a (C,O,.) pair.
_LEFT_EDGES = frozenset({Edge(0, 1, 2), Edge(1, 2, 1), Edge(2, 3, 1), Edge(3, 4, 1), Edge(4, 5, 2)})
_RIGHT_EDGES = frozenset({Edge(0, 1, 1), Edge(1, 2, 2), Edge(3, 4, 2), Edge(4, 5, 1), Edge(0, 5, 1)})


@dataclass(frozen=True)
class _SigmatropicFamily:
    """An immutable descriptor for ONE [3,3] sigmatropic family (Cope: all-carbon; Claisen: atom 2 = O).

    ``forward`` is the synthesis-direction rule (reactant isomer -> product isomer); ``retro`` its reverse (the
    disconnection the enumerator applies to a target).  ``signature`` / ``center`` are DERIVED from the rule so a
    family can never drift from it.  The ``center`` (formed/broken bond multiset + one connected component) is the
    exact-equality key the oracle uses to tell Cope from Claisen and from every DA family."""

    class_label: str
    schema: str
    provider_id: str
    witness_kind: str
    forward: BondRule
    retro: BondRule
    signature: tuple
    center: ReactionCenter


def _sigmatropic_family(labels: tuple[str, ...], class_label: str, schema: str, provider_id: str,
                        witness_kind: str) -> _SigmatropicFamily:
    """Build a family from the array ``labels`` (6 element symbols).  ``retro`` / ``signature`` / ``center`` derived."""
    forward = BondRule(f"{provider_id}-forward-v1", BondGraph(labels, _LEFT_EDGES), BondGraph(labels, _RIGHT_EDGES))
    retro = forward.reverse()
    signature = _match_signature(RewriteWitness(retro, retro.left, tuple(range(6)), retro.right))
    return _SigmatropicFamily(class_label, schema, provider_id, witness_kind,
                              forward, retro, signature, _synthesis_center(forward))


#: The all-carbon Cope [3,3] (1,5-hexadiene <-> 1,5-hexadiene; substituted substrates give a distinct isomer).
COPE = _sigmatropic_family(("C", "C", "C", "C", "C", "C"), "cope-[3,3]-sigmatropic",
                           "smartchem.lateral/cope-v1", "cope-rearrangement", "COPE_REARRANGEMENT")
#: The Claisen [3,3] (allyl vinyl ether -> pent-4-enal): array atom 2 is the O, so the O migrates into a carbonyl.
CLAISEN = _sigmatropic_family(("C", "C", "O", "C", "C", "C"), "claisen-[3,3]-sigmatropic",
                              "smartchem.lateral/claisen-v1", "claisen-rearrangement", "CLAISEN_REARRANGEMENT")
#: The aza-Claisen (3-aza-Cope) [3,3]: array atom 2 is N, so the N migrates into a C=N imine (an allyl vinyl amine
#: <-> gamma,delta-unsaturated imine).  Rides the SAME [3,3] array + guards as Claisen, one label swapped.
AZA_CLAISEN = _sigmatropic_family(("C", "C", "N", "C", "C", "C"), "aza-claisen-[3,3]-sigmatropic",
                                  "smartchem.lateral/aza-claisen-v1", "aza-claisen-rearrangement",
                                  "AZA_CLAISEN_REARRANGEMENT")
#: The thia-Claisen [3,3]: array atom 2 is S, so the S migrates into a C=S thiocarbonyl (an allyl vinyl sulfide
#: <-> gamma,delta-unsaturated thiocarbonyl).  Completes the hetero-[3,3] set {O, N, S} on the same array.
THIA_CLAISEN = _sigmatropic_family(("C", "C", "S", "C", "C", "C"), "thia-claisen-[3,3]-sigmatropic",
                                   "smartchem.lateral/thia-claisen-v1", "thia-claisen-rearrangement",
                                   "THIA_CLAISEN_REARRANGEMENT")

# --------------------------------------------------------------------------------------------------------------------
# ELECTROCYCLIZATION -- the third pericyclic archetype (after [4+2] cycloaddition and [3,3] sigmatropic).  A k-carbon
# polyene <-> its cyclic isomer: a rank-FLAT ring-open/close isomerization, so it lives on the SAME lateral seam and
# the SAME generic guards as the sigmatropic families (nothing in _SigmatropicFamily or _guarded_rewrites is
# [3,3]-specific -- both read family.retro/forward/signature/center).  The kernel's "degree" is VALENCE (bond-order
# sum), which an electrocyclization preserves at every atom (a terminus goes =CH2 valence 2 -> ring-CH2- valence 2),
# so the fixed-vertex degree-locked kernel accepts it natively (kernel-verified in the family build below).  FORWARD
# is the ring-CLOSING direction (open polyene -> ring, the productive Nazarov/electrocyclic-closure sense); the
# enumerator applies retro (ring-opening) so it fires on a RING target and yields the open polyene.
# --------------------------------------------------------------------------------------------------------------------

def _polyene_edges(k: int) -> frozenset[Edge]:
    """The linear k-carbon polyene 0=1-2=3-...  (alternating double/single, starting with a double)."""
    return frozenset(Edge(i, i + 1, 2 if i % 2 == 0 else 1) for i in range(k - 1))


def _ring_edges(k: int) -> frozenset[Edge]:
    """The k-carbon carbocycle 0-1=2-3=...  (alternating single/double, starting single) closed by the new sigma
    0-(k-1) -- the electrocyclization product of :func:`_polyene_edges` (one new sigma, the pi system shifted)."""
    return frozenset({*(Edge(i, i + 1, 1 if i % 2 == 0 else 2) for i in range(k - 1)), Edge(0, k - 1, 1)})


def _electrocyclic_family(n_pi: int, class_label: str, schema: str, provider_id: str,
                          witness_kind: str) -> _SigmatropicFamily:
    """Build a lateral family for an ``n_pi``-electron all-carbon electrocyclization (k = n_pi carbons).  ``forward``
    is ring-CLOSING (polyene -> ring); ``retro`` / ``signature`` / ``center`` are DERIVED from it, exactly like
    :func:`_sigmatropic_family`, so the family can never drift from its rule."""
    labels = ("C",) * n_pi
    forward = BondRule(f"{provider_id}-forward-v1", BondGraph(labels, _polyene_edges(n_pi)),
                       BondGraph(labels, _ring_edges(n_pi)))
    retro = forward.reverse()
    signature = _match_signature(RewriteWitness(retro, retro.left, tuple(range(n_pi)), retro.right))
    return _SigmatropicFamily(class_label, schema, provider_id, witness_kind,
                              forward, retro, signature, _synthesis_center(forward))


#: The 4-pi electrocyclization (1,3-butadiene <-> cyclobutene): 4 electrons, thermally CONROTATORY (Woodward-Hoffmann).
ELECTRO_4PI = _electrocyclic_family(4, "electrocyclization-4pi", "smartchem.lateral/electro-4pi-v1",
                                    "electrocyclization-4pi", "ELECTROCYCLIZATION_4PI")
#: The 6-pi electrocyclization ((Z)-1,3,5-hexatriene <-> 1,3-cyclohexadiene): 6 electrons, thermally DISROTATORY.
ELECTRO_6PI = _electrocyclic_family(6, "electrocyclization-6pi", "smartchem.lateral/electro-6pi-v1",
                                    "electrocyclization-6pi", "ELECTROCYCLIZATION_6PI")

#: Per-family centres (mirroring the DA families) for the oracle's exact-equality Layer-B check.
_COPE_CENTER = COPE.center
_CLAISEN_CENTER = CLAISEN.center
_AZA_CLAISEN_CENTER = AZA_CLAISEN.center
_THIA_CLAISEN_CENTER = THIA_CLAISEN.center
_ELECTRO_4PI_CENTER = ELECTRO_4PI.center
_ELECTRO_6PI_CENTER = ELECTRO_6PI.center

#: All lateral (rank-flat) families the standalone enumeration + the bounded lateral search range over.
LATERAL_FAMILIES: tuple[_SigmatropicFamily, ...] = (
    COPE, CLAISEN, AZA_CLAISEN, THIA_CLAISEN, ELECTRO_4PI, ELECTRO_6PI,
)


@dataclass(frozen=True)
class RewriteAudit:
    """A guard-passed [3,3] rewrite: the kernel witness plus the derived class."""
    witness: RewriteWitness
    reaction_class: str


def _guarded_rewrites(family: _SigmatropicFamily, target: BondGraph, *,
                      budget: int = 100000) -> tuple[tuple[RewriteAudit, ...], bool]:
    """Every GUARDED [3,3] rewrite of ``target`` for ``family`` (applying its ``retro``), plus a completeness flag.

    Guards (each failure DROPS the match -- coverage loss, never a coerced witness):
      * LOCALITY -- the six matched atoms induce EXACTLY the array's LEFT bond pattern (no extra bond among them);
      * NO EXOCYCLIC MULTIPLE bond on a matched atom (a crossing bond must be single: the array atoms change
        hybridisation, so an exocyclic pi would give a cumulene, not a clean sigmatropic product);
      * NEUTRAL VALENCE -- every matched atom stays within its NEUTRAL valence (:data:`_NEUTRAL_VALENCE`), so a
        Claisen O never appears as an over-valent oxocarbenium (the DA guard-2c bound, reused);
      * CLASS WITNESS + kernel verify + independent reconstruction reproduce ``target`` exactly;
      * SINGLE MOLECULE -- the product is ONE connected species (an isomerization, never a fragmentation);
      * NON-DEGENERATE -- the product graph differs structurally from ``target`` (a self-map is a trivial no-op,
        dropped: a route step that returns its own input is not a transformation).
    """
    if type(target) is not BondGraph:
        raise RuleError("_guarded_rewrites expects a BondGraph target")
    if not valence_sane(target):
        return (), True
    from .smiles import resonance_identity
    source_species = _config(target).species
    # a valid single-molecule target joins to one component; a disconnected input is not an isomerization substrate.
    source_id = resonance_identity(source_species[0]) if len(source_species) == 1 else None
    receipt = enumerate_matches(family.retro, target, budget=budget)
    audits: list[RewriteAudit] = []
    seen: set[str] = set()
    for w in receipt.witnesses:
        m = w.match
        # LOCALITY: the six matched atoms carry exactly the array's LEFT edges, nothing more.
        if _induced(target, m) != frozenset(Edge(m[e.i], m[e.j], e.order) for e in family.retro.left.edges):
            continue
        matched = set(m)
        # no exocyclic MULTIPLE bond on a matched atom.
        if any(e.order != 1 for e in target.edges if (e.i in matched) != (e.j in matched)):
            continue
        # NEUTRAL VALENCE on every matched atom (the DA guard-2c bound, reused for the Claisen O).
        if any((nv := _NEUTRAL_VALENCE.get(target.labels[v])) is not None and target.degrees[v] > nv for v in m):
            continue
        if not verify(w) or _match_signature(w) != family.signature:
            continue
        if not independently_reconstructs(target, w.target, m, family.forward):
            continue
        # SINGLE MOLECULE + CANONICAL non-degeneracy + CANONICAL dedup.  The raw BondGraph digest is a PRESENTATION
        # hash (the kernel makes no isomorphism-class claim), so a self-map with renumbered vertices has a DIFFERENT
        # raw digest -- a degenerate rewrite would slip through a digest check.  Compare canonical molecular identity.
        prod_species = _config(w.target).species
        if len(prod_species) != 1:
            continue
        prod_id = resonance_identity(prod_species[0])
        if prod_id == source_id:
            continue  # structurally degenerate self-map (a no-op, not a transformation)
        if prod_id in seen:
            continue
        seen.add(prod_id)
        audits.append(RewriteAudit(witness=w, reaction_class=family.class_label))
    return tuple(audits), receipt.complete


def _induced(graph: BondGraph, vertices) -> frozenset[Edge]:
    """Edges of ``graph`` with BOTH endpoints in ``vertices`` (the induced subgraph -- the locality lock)."""
    vs = set(vertices)
    return frozenset(e for e in graph.edges if e.i in vs and e.j in vs)


def sigmatropic_rewrites(family: _SigmatropicFamily, target: Molecule, *,
                         budget: int = 100000) -> tuple[Molecule, ...]:
    """The distinct isomers ``target`` reaches by ONE guarded lateral rewrite of ``family`` (structural type-validity
    only).  Family-agnostic: ``family`` may be any lateral (rank-flat) family -- a [3,3] sigmatropic (Cope, Claisen,
    aza/thia-Claisen) OR an electrocyclization (:data:`ELECTRO_4PI`, :data:`ELECTRO_6PI`) -- since every guard reads
    ``family.retro`` / ``family.forward`` / ``family.signature`` and nothing archetype-specific.  A standalone
    enumeration -- the lateral analogue of :func:`smartchem.diels_alder.retro_da_disconnections` -- returning the
    product molecules directly (each a single species, a real isomer of ``target``).  Alias: :func:`lateral_rewrites`."""
    if type(target) is not Molecule or target.charge != 0 or target.state:
        return ()
    try:
        graph = _joined((target,))
    except (RuleError, ScissionError, TypeError, ValueError):
        return ()
    audits, _ = _guarded_rewrites(family, graph, budget=budget)
    out: list[Molecule] = []
    for a in audits:
        species = _config(a.witness.target).species
        if len(species) == 1:
            out.append(species[0])
    return tuple(out)


def _reactant_rewrites_to(family: _SigmatropicFamily, reactant: Molecule, products: tuple[Molecule, ...]) -> bool:
    """Self-contained certificate: does ``reactant`` admit a GUARDED [3,3] rewrite (for THIS family) whose single
    product is exactly ``products``?  Re-derived from the reactant alone, so a hand-built edge cannot smuggle a
    fabricated isomer that merely balances mass (every isomer balances mass -- the certificate is load-bearing)."""
    if len(products) != 1:
        return False
    want = Config.of(*products)
    for isomer in sigmatropic_rewrites(family, reactant, budget=100000):
        if Config.of(isomer) == want:
            return True
    return False


class LateralRewriteError(ScissionError):
    """A lateral (rank-flat) rewrite was asked for a strict-descent decomposition image it cannot have (W1)."""


@dataclass(frozen=True)
class LateralRewriteEdge(Digestible):
    """A [3,3] sigmatropic isomerization stored as a rank-FLAT rewrite of ``reactant`` into its single isomer
    ``products`` (Cope or Claisen).  ONE generic edge serves both families (they differ only by the array's atom-2
    label); it carries its ``family`` descriptor as a ``compare=False`` field, excluded from the content digest and
    equality exactly like :class:`~smartchem.diels_alder.HeteroDielsAlderEdge` (the schema/class/reactant/product
    fields already distinguish Cope from Claisen).

    Two certificates run at construction: (1) mass+charge conservation via a real :class:`Reaction` (trivially met
    by an isomerization, but re-checked the repo's way); (2) [3,3]-ness re-derived from the reactant
    (:func:`_reactant_rewrites_to`) -- conservation ALONE proves nothing here (every isomer balances mass), so the
    second certificate is the load-bearing one.  Structural type-validity only (Problem A).

    :meth:`forget` RAISES -- a rank-flat rewrite has NO strict-descent (W1) decomposition image.  This is the honest
    boundary that keeps a lateral edge OUT of the decompiler / ``search_routes`` conditions path (see the module
    docstring); build a step from it with :meth:`ExperimentStep.from_transform`, which reads ``reactant`` /
    ``products`` / ``reaction_center`` and never calls ``forget``."""

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reaction_class: str
    family: _SigmatropicFamily = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.schema_version != self.family.schema:
            raise ScissionError(f"schema_version must be exactly {self.family.schema!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a Molecule")
        if self.reagents != ():
            raise ScissionError("a [3,3] sigmatropic rewrite is reagentless")
        if (type(self.products) is not tuple or len(self.products) != 1
                or type(self.products[0]) is not Molecule):
            raise ScissionError("a [3,3] rewrite yields exactly one product Molecule (an isomer)")
        if self.reaction_class != self.family.class_label:
            raise ScissionError(f"reaction_class must be {self.family.class_label!r}")
        try:
            Reaction(Config.of(self.reactant), Config.of(*self.products), name="sigmatropic-rewrite")
        except ConservationError as clash:
            raise ScissionError(f"[3,3] rewrite does not conserve mass/charge: {clash}") from clash
        if not _reactant_rewrites_to(self.family, self.reactant, self.products):
            raise ScissionError("not a [3,3] isomer of this reactant (a fabricated lateral edge is refused)")

    def equation(self) -> str:
        return f"{self.reactant!r} -> {self.products[0]!r}"

    def reaction_center(self) -> ReactionCenter:
        """This family's [3,3] synthesis centre (:attr:`_SigmatropicFamily.center`), distinct from every DA and
        sibling-sigmatropic centre, so the oracle tells the classes apart by exact equality."""
        return self.family.center

    def forget(self):
        """Refuse -- a rank-flat rewrite has no strict-descent decomposition image (the W1 boundary)."""
        raise LateralRewriteError(
            "a [3,3] sigmatropic rewrite is rank-flat and has no W1 strict-descent decomposition image; "
            "lateral rewrites are not decompilable through the decompiler / search_routes conditions path "
            "(a deferred epic -- see docs/research/RULE_CALCULUS_LATERAL_REWRITE_SEAM_v0.1.md)"
        )

    def __repr__(self) -> str:
        return f"LateralRewriteEdge({self.equation()})"


def guarded_isomer_edges(family: _SigmatropicFamily, target: Molecule, *,
                         budget: int = 100000) -> tuple[tuple[LateralRewriteEdge, ...], bool]:
    """Every guarded :class:`LateralRewriteEdge` of ``target`` for ``family`` PLUS an honest completeness flag (the
    flag :func:`_guarded_rewrites` already computes -- ``True`` iff the kernel match enumeration was not truncated by
    ``budget``).  The bounded lateral search (:mod:`smartchem.lateral_search`) needs the flag to state fail-closed
    whether a node's successor set was fully explored; :func:`rewrite_edges` is the flag-dropping convenience over it."""
    if type(target) is not Molecule or target.charge != 0 or target.state:
        return (), True
    try:
        graph = _joined((target,))
    except (RuleError, ScissionError, TypeError, ValueError):
        return (), True
    audits, complete = _guarded_rewrites(family, graph, budget=budget)
    edges: list[LateralRewriteEdge] = []
    for a in audits:
        species = _config(a.witness.target).species
        if len(species) != 1:
            continue
        try:
            edges.append(LateralRewriteEdge(family.schema, target, (species[0],), (), family.class_label, family))
        except ScissionError:
            continue
    return tuple(edges), complete


def rewrite_edges(family: _SigmatropicFamily, target: Molecule, *, budget: int = 100000) -> tuple[LateralRewriteEdge, ...]:
    """Build one :class:`LateralRewriteEdge` per guarded lateral isomer of ``target`` (fail-closed: an edge its own
    certificates refuse is dropped).  A standalone builder -- NOT a ``search_routes`` provider, because a lateral
    edge's ``forget`` raises (the W1 boundary); use these edges to assemble a route by hand or feed the oracle.  The
    flag-dropping convenience over :func:`guarded_isomer_edges`."""
    return guarded_isomer_edges(family, target, budget=budget)[0]


#: Archetype-agnostic alias: the same enumerator serves [3,3] sigmatropics AND electrocyclizations (see the function
#: docstring).  The bounded lateral search (:mod:`smartchem.lateral_search`) ranges over families via this name.
lateral_rewrites = sigmatropic_rewrites
