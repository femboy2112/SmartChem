"""Move 3 -- the provider algebra as a generating set of the open SMC (the honest categorical framing).

The categorical-reorientation arc's Move 3 asked to formalize the transform-provider registry as "the free
open-monoidal category on typed generators; IR-COMMUTE is the coherence law".  Two independent pre-build design
bearings (a soundness review + a YAGNI review) converged that most of that phrasing is an OVER-CLAIM, and that the
categorical structure the arc wanted *already exists and is already live* -- so the honest deliverable is a
formalization pinned by falsifiable laws over the existing structure, NOT a new algebraic runtime.  The corrections,
verbatim in the laws below (full argument: ``docs/research/PROVIDER_ALGEBRA_AS_SMC_GENERATORS_v0.1.md``):

* NOT "the free category": we cannot claim freeness as *proven* (no proof of the absence of imposed relations).
  What is provable, and what these tests pin, is a **semantics functor** ``F`` from the registry's generating
  morphisms into the open SMC (``smartchem.open_chem_diagram.OpenChemDiagram`` over ``smartchem.open_core``), whose
  action on a single generator application (an ``EnumeratedTransform``) is ``ExperimentStep.from_transform(t).open()``.
* NOT "IR-COMMUTE is the coherence law": IR-COMMUTE (``tests/test_ir_commute.py``) is a per-family cross-producer
  **forgetful NATURALITY square** at the Formula layer (``forget(D_structure) ⊆ D_formula(forget)``), a statement
  BETWEEN two functors, never an associativity/interchange law WITHIN the monoidal category.  The genuine SMC
  coherence (interchange, braid, hexagon) already lives in and is already tested on ``open_core`` /
  ``OpenChemDiagram`` (``tests/test_open_chem_diagram.py``, ``tests/test_open_diagram.py``); Move 3 does NOT re-prove
  it.  Law 3 here restates IR-COMMUTE's *spirit* at the correct (Molecule) altitude: the ``open`` functor and the
  ``forget`` functor agree, per generator, on the underlying reaction.
* NOT "typed generators" in the hom-restricting sense: the ``(witness_kind, projection_kind)`` pairs a provider
  declares are **provenance tags**, not composition-gating hom-types (a heterolytic scission's products can feed a
  capped scission -- composition at the Molecule altitude is total).  Law 1 pins that this provenance never enters
  the functor's compared image (the R24 congruence discipline, ``a-quotient-must-be-a-congruence``).

What genuinely EARNS its place: the registry (``TransformProviderRegistry.enumerate``) is already the sole seam of
the bounded search (3 live call sites, AST-guarded by ``tests/test_provider_locality.py``), and ``route.open()`` /
``dag.open()`` (the functor's action on words) is already live in the M2 ranker (``meta_compile``).  These laws are
falsifiable guards over that live structure -- not a decorative parallel abstraction (the zero-call-sites failure
mode the arc's own history, ``THE_DIFFERENCE.md``, was falsified for).
"""
from __future__ import annotations

from collections import Counter

from smartchem.bond_order_edit import BondOrderEditProvider
from smartchem.experiment.step import ExperimentStep
from smartchem.open_chem_diagram import canonicalize
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    CappedScissionProvider,
    TransformProviderRegistry,
)

ETHANE = parse_smiles("CC")
WATER = parse_smiles("O")


def _lift(transform):
    """F on a single generator application: an ``EnumeratedTransform``'s transform -> its open-SMC image.

    This is the on-generators action of the semantics functor.  It is deliberately NOT a new shipped combinator
    (no live consumer wants an ``EnumeratedTransform``->diagram lift that ``ExperimentStep.open()`` does not already
    serve); it is the existing bridge ``ExperimentStep.from_transform(t).open()`` named for the laws.
    """
    return ExperimentStep.from_transform(transform).open()


def _species_multiset(molecules) -> Counter:
    return Counter(repr(m) for m in molecules)


# ======================================================================================
# Law 1 -- provenance is OUT of the functor's compared image (the R24 congruence discipline)
# ======================================================================================
class TestProvenanceIsNotInTheCategoricalIdentity:
    """The ``(provider_id, provider_version, witness_kind)`` a generator carries is provenance, not identity.  Two
    registries that emit the SAME transform under DIFFERENT provider identities must lift to the SAME canonical
    diagram.  HONEST scope (an adversarial review's point): provenance is *structurally absent* from ``F``'s domain
    -- ``from_transform`` receives only the bare transform (``.reactant/.products/.reagents``), never the
    ``EnumeratedTransform`` wrapper that carries ``provider_id`` -- so this is a FORWARD CHANGE-DETECTOR guarding that
    absence, not a proof of a congruence theorem (the congruence question does not even arise while provenance never
    enters ``F``'s input).  It reddens the day anyone threads provider provenance into the step/diagram, which is the
    edit that WOULD create the R24 congruence hazard (equal-now, diverge-after-one-compose)."""

    def test_same_transform_under_different_provenance_lifts_equal(self):
        reg_a = TransformProviderRegistry((CappedScissionProvider(provider_id="capped-A"),))
        reg_b = TransformProviderRegistry((CappedScissionProvider(provider_id="capped-B"),))
        ets_a, complete_a = reg_a.enumerate(ETHANE, (WATER,), budget=2000)
        ets_b, complete_b = reg_b.enumerate(ETHANE, (WATER,), budget=2000)
        assert complete_a and complete_b and ets_a and ets_b
        # the two presentations genuinely differ in provenance (the quotient is doing real work) ...
        assert {e.provider_id for e in ets_a} == {"capped-A"}
        assert {e.provider_id for e in ets_b} == {"capped-B"}
        # ... but they emit the SAME transforms (dedup identity is provenance-free) ...
        assert {e.transform.digest for e in ets_a} == {e.transform.digest for e in ets_b}
        # ... and F maps them to the SAME canonical image, per transform.
        by_digest_a = {e.transform.digest: e.transform for e in ets_a}
        by_digest_b = {e.transform.digest: e.transform for e in ets_b}
        for digest, t_a in by_digest_a.items():
            assert canonicalize(_lift(t_a)) == canonicalize(_lift(by_digest_b[digest]))


# ======================================================================================
# Law 2 -- F quotients symmetric cuts to their shared reaction, and is faithful on distinct reactions
# ======================================================================================
class TestTheFunctorQuotientsCutsButSeparatesReactions:
    """F sees the REACTION, not the bond-cut choice.  This is the ``comparing-fixed-representatives-fabricates-a-
    distinction`` discipline as a theorem: the four symmetric ways to cut ethane are four distinct transforms
    (distinct ``transform.digest``) but ONE reaction, so F fabricates no distinction between them -- it maps all
    four to a single canonical diagram.  Yet F is faithful where the chemistry genuinely differs: a capped scission
    and a bond-order edit of the same target are different reactions and lift to distinct diagrams."""

    def test_symmetric_cuts_collapse_to_one_diagram(self):
        reg = TransformProviderRegistry((CappedScissionProvider(),))
        ets, complete = reg.enumerate(ETHANE, (WATER,), budget=2000)
        assert complete
        transforms = [e.transform for e in ets]
        # non-vacuity: there really ARE several distinct transforms (distinct cuts), not one ...
        assert len({t.digest for t in transforms}) >= 2
        # ... yet they all describe the SAME reaction ...
        assert len({t.forget().equation() for t in transforms}) == 1
        # ... so F collapses them all to a single canonical image (no fabricated distinction).
        images = {canonicalize(_lift(t)) for t in transforms}
        assert len(images) == 1

    def test_distinct_reactions_lift_to_distinct_diagrams(self):
        capped = TransformProviderRegistry((CappedScissionProvider(),))
        bond_order = TransformProviderRegistry((BondOrderEditProvider(),))
        ets_cap, _ = capped.enumerate(ETHANE, (WATER,), budget=2000)
        ets_bo, _ = bond_order.enumerate(ETHANE, (WATER,), budget=2000)
        assert ets_cap and ets_bo
        # the two families genuinely produce different reactions ...
        cap_eq = {e.transform.forget().equation() for e in ets_cap}
        bo_eq = {e.transform.forget().equation() for e in ets_bo}
        assert cap_eq != bo_eq
        # ... and F keeps them distinct (it does not collapse real chemistry).
        cap_img = canonicalize(_lift(ets_cap[0].transform))
        bo_img = canonicalize(_lift(ets_bo[0].transform))
        assert cap_img != bo_img


# ======================================================================================
# Law 3 -- forget/open naturality: the two projection functors agree per generator (IR-COMMUTE, at the SMC altitude)
# ======================================================================================
class TestForgetAndOpenAgreeOnGenerators:
    """The registry's generators carry TWO functors into TWO bases: ``forget`` -> the Formula-layer edge
    (``structure_descent``), and ``open`` -> the Molecule-altitude open SMC.  IR-COMMUTE pins the forget square at
    the Formula layer; this pins the corresponding agreement at the correct altitude: for every generator ``t``, the
    net reaction of its lifted diagram is the exact REVERSE of ``t.forget()`` (``from_transform`` reads a
    decomposition backwards into a synthesis).  HONEST scope (an adversarial review's point): both ``open`` and
    ``forget`` read the SAME ``transform.reactant/.products/.reagents``, so this is COMMON-MODE on the product
    multiset itself -- a wrong product molecule would appear identically on both sides and cancel.  What the check
    genuinely catches is the dom<->cod REVERSAL orientation of ``from_transform`` (pinned non-vacuous by the reversal
    control below) and a Molecule<->Formula altitude/``repr`` divergence; the correctness of the product molecules
    lives in the conservation certificate, not here.  A consistency/orientation datum, not an independent oracle."""

    def test_net_reaction_of_the_lift_is_the_reverse_of_forget(self):
        reg = TransformProviderRegistry((CappedScissionProvider(),))
        ets, complete = reg.enumerate(ETHANE, (WATER,), budget=2000)
        assert complete and ets
        checked = 0
        for e in ets:
            t = e.transform
            edge = t.forget()  # a Formula-layer decomposition edge: reactant + reagents -> products
            net = _lift(t).net_reaction()  # the Molecule-altitude synthesis: products -> reactant + reagents
            # forget RHS (products) == net LHS (dom); forget LHS (reactant + reagents) == net RHS (cod)
            forget_products = Counter()
            for f, mult in edge.products:
                forget_products[repr(f)] += mult
            forget_reactants = Counter({repr(edge.reactant): 1})
            for f, mult in edge.reagents:
                forget_reactants[repr(f)] += mult
            assert _species_multiset(net.dom.species) == forget_products
            assert _species_multiset(net.cod.species) == forget_reactants
            checked += 1
        assert checked >= 1  # non-vacuous: at least one generator was actually cross-checked

    def test_the_agreement_is_a_real_reversal_not_an_identity(self):
        # non-vacuity control: forget's LHS and RHS are genuinely DIFFERENT multisets (a decomposition really moves
        # mass across the arrow), so "net.dom == forget.products / net.cod == forget.reactants" is a reversal check
        # with content, not a vacuous "everything equals everything".
        reg = TransformProviderRegistry((CappedScissionProvider(),))
        ets, _ = reg.enumerate(ETHANE, (WATER,), budget=2000)
        edge = ets[0].transform.forget()
        lhs = Counter({repr(edge.reactant): 1})
        for f, mult in edge.reagents:
            lhs[repr(f)] += mult
        rhs = Counter()
        for f, mult in edge.products:
            rhs[repr(f)] += mult
        assert lhs != rhs
