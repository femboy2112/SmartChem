"""IR-COMMUTE-01: the cross-producer forgetful relation  forget(D_structure(S)) ⊆ D_formula(forget(S) | closure).

The existing ``tests/test_ir_struct.py::TestForgetfulSquare`` enforces the forgetful square PER CANDIDATE (each
structural candidate's stored projection == forget of its OWN edge).  This lifts it to a CROSS-PRODUCER guarantee:
the STRUCTURE decompile of S, forgotten to the formula layer, is a SUBSET of the FORMULA decompile of forget(S)
(audit section 7.3 / B0).

Honest scope of the relation (not an ``==`` between two fully-independent producers -- red-team fold):
  * it is ``⊆``, NOT ``==``: the formula descent runs to the elemental floor (it also emits e.g. ``C2H6 -> 2 C + 6 H``)
    while the structure descent is single-step, so the structural projections are a SUBSET of the formula candidates,
    never the whole set -- ``==`` is strictly wrong here and ``⊆`` is the forced, honest relation;
  * the RHS is parameterized by the LHS: the formula-side inventory is DERIVED from the structural products (the
    formula descent is selective, not generative, so it cannot discover a precursor the structure side found).  What
    this therefore proves precisely is that the CANONICALIZATION/BUCKETING CONVENTION of ``BondOrderEdit.forget()``
    agrees BYTE-FOR-BYTE with that of ``decompiler.admissible_edges`` (both must yield the same edge digest) -- a
    real cross-producer convention cross-check, within a common closure, not a claim of two independent oracles.

The reconciliation the square needs, made explicit here:
  * the registry is PINNED to the bond-order family -- it is the one family whose ``forget()`` yields a formula-layer
    ``DecompositionEdge``, the only edge type ``decompile_to_ir`` emits (capped scission forgets to a MediatedEdge,
    which has no wired formula producer -- see the boundary note in the wrong-family control below);
  * ``decompile_to_ir`` is SELECTIVE over a declared inventory (it cannot discover a novel precursor), while the
    structure descent is GENERATIVE -- so the formula-side inventory is DERIVED from the structural products, giving
    both producers the same closure;
  * the formula descent runs to the elemental floor while the structure descent is single-step, so the relation is
    a SUBSET (the structural projections all appear among the formula candidates), not raw set equality.

Multi-family lift (IR-COMMUTE, this round): the CAPPED-SCISSION family is now closed too, against a DIFFERENT
formula-layer producer.  A capped scission forgets to a ``MEDIATED_EDGE`` (not the ``DECOMPOSITION_EDGE`` that
``decompile_to_ir`` emits), so its formula-side oracle is ``decompiler_mediated.mediated_decompose`` -- the recursive
mediated descent, the analogue of ``decompile_to_ir``.  Fed the SAME derived closure (inventory from the structural
products) PLUS a ``medium`` derived from the structural reagents (a capped scission draws a reagent from a declared
reservoir), the capped-scission structural projections are a SUBSET of that producer's ``.mediated`` edges.  The
two families forget to DISTINCT edge TYPES -- capped scission to a reagent-drawn ``MEDIATED_EDGE``, bond order to an
own-atoms ``DECOMPOSITION_EDGE`` -- which is WHY they need distinct producers (``mediated_decompose`` vs
``decompile_to_ir``).  That type distinction is asserted on ``projection_kind``, NOT on a cross-producer digest
non-subset: a digest ``⊄`` across the two producers is over-determined by the canonical class tag
(``contracts.canonical_payload`` embeds the fully-qualified class -- ``contracts.py:149``), so their digest namespaces
are disjoint by construction regardless of whether either ``forget()`` convention is correct.  The convention
agreement is therefore proven ONLY by the same-class POSITIVE subsets (capped ⊆ mediated, bond order ⊆ plain), never
by a vacuous cross-class ⊄ (the honesty the wrong-family control below already carries, applied here too).

Boundary (named, not hidden): this closes the square for BOND_ORDER_EDIT and CAPPED_SCISSION under the DEFAULT
single-cut registry (``max_reactant_cuts == 1``, matching ``mediated_decompose``'s default ``max_reagent_instances``).
The k>=2 multi-cut / mixed-reagent-type case is CONJECTURED to close by the same recipe (bump ``max_reagent_instances``
to the provider's cut count, widen the derived medium) but is NOT verified here -- it is combinatorially large and off
the DEFAULT-registry lane.  The heterolytic/redox families still have NO formula-layer producer at all (an
``ElectronTransferEdge``/charged edge has no mediated or plain descent wired), so extending the square to those
remains the IR-FORGET-01 follow-on.
"""
from __future__ import annotations

from smartchem.bond_order_edit import BondOrderEditProvider
from smartchem.compilation_ir import (
    DEFAULT_TRANSFORM_REGISTRY,
    decompile_structure_to_ir,
    decompile_to_ir,
)
from smartchem.decompiler import Formula
from smartchem.decompiler_mediated import mediated_decompose
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import TransformProviderRegistry

ETHANE = parse_smiles("CC")
WATER = parse_smiles("O")
BOND_ORDER = TransformProviderRegistry((BondOrderEditProvider(),))


def _derive_formula_inventory(struct_ir) -> tuple:
    """The common closure: the non-elemental product formulas the STRUCTURE descent generated, handed to the formula
    descent as its selectable inventory (it cannot discover them itself)."""
    inv = []
    for sc in struct_ir.structural_candidates:
        for species, _mult in sc.products:
            counts = species.molecule.formula
            # a MULTI-ATOM precursor.  (A single-element diatomic like H2 has sum==2 and passes too; it is inert in
            # the inventory -- its atoms bucket to the always-available element floor -- so feeding it changes nothing.)
            if sum(counts.values()) > 1:
                inv.append(Formula(tuple(counts.items())))
    return tuple(inv)


def test_the_forgetful_square_commutes_across_producers_for_the_bond_order_family():
    struct_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=BOND_ORDER)
    struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
    assert struct_projections, "the bond-order family must produce at least one structural candidate for ethane"
    inventory = _derive_formula_inventory(struct_ir)
    assert inventory, "the structural products must yield a non-elemental precursor to close the closure"
    formula_ir = decompile_to_ir(ETHANE.formula, inventory)
    formula_digests = {c.candidate_digest for c in formula_ir.candidates}
    # forget(D_structure(S)) ⊆ D_formula(forget(S)): every structural projection is a formula candidate of forget(S)
    assert struct_projections <= formula_digests


def test_dropping_the_derived_precursor_breaks_the_square():
    # NON-VACUITY: without the structurally-derived inventory, the formula descent reduces only to the elemental
    # floor -- the structural projection is ABSENT, so the subset fails.  Proves the positive test is not vacuously
    # true (the closure is load-bearing, not an artifact of everything reducing to elements).
    struct_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=BOND_ORDER)
    struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
    formula_ir = decompile_to_ir(ETHANE.formula, ())  # NO precursor inventory -> elemental floor only
    formula_digests = {c.candidate_digest for c in formula_ir.candidates}
    assert struct_projections and not (struct_projections <= formula_digests)


def test_a_different_family_does_not_commute_so_the_registry_pinning_is_load_bearing():
    # NON-VACUITY + the registry-pinning is load-bearing: the DEFAULT registry (capped scission) does NOT commute
    # into decompile_to_ir's formula edges -- its projections are NOT a subset of the formula candidates -- so the
    # relation genuinely requires the bond-order registry, not the default.
    # HONEST on the mechanism (red-team fold): this non-subset is OVER-DETERMINED; the control does not isolate ONE
    # cause.  Capped scission forgets to a MediatedEdge (a different edge/digest domain than decompile_to_ir's
    # DecompositionEdge), AND the formula descent does not generate capped scission's exact product multiset even when
    # those products ARE offered as inventory (probed).  Either alone forces the non-subset -- so this proves "a
    # different family does not commute", not "it fails purely by edge domain".
    struct_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=BOND_ORDER)
    inventory = _derive_formula_inventory(struct_ir)
    formula_digests = {c.candidate_digest for c in decompile_to_ir(ETHANE.formula, inventory).candidates}
    default_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=DEFAULT_TRANSFORM_REGISTRY)
    default_projections = {sc.projection_digest for sc in default_ir.structural_candidates}
    assert default_projections and not (default_projections <= formula_digests)


# ======================================================================================
# IR-COMMUTE multi-family lift: the CAPPED-SCISSION square, against the mediated producer
# ======================================================================================
def _derive_mediated_closure(struct_ir) -> tuple:
    """The common closure for the mediated square: the non-elemental product formulas handed to the mediated
    descent as its selectable INVENTORY, and the reagent formulas handed to it as the MEDIUM (a capped scission
    draws a reagent from a declared reservoir -- ``mediated_decompose`` filters/dedups both internally)."""
    inv = []
    for sc in struct_ir.structural_candidates:
        for species, _mult in sc.products:
            counts = species.molecule.formula
            if sum(counts.values()) > 1:
                inv.append(Formula(tuple(counts.items())))
    medium = [
        Formula(tuple(species.molecule.formula.items()))
        for sc in struct_ir.structural_candidates
        for species, _mult in sc.reagents
    ]
    return tuple(inv), tuple(medium)


def test_the_forgetful_square_commutes_for_capped_scission_via_the_mediated_producer():
    # The DEFAULT registry is the capped-scission family; its forget() yields a MEDIATED_EDGE, so its formula-side
    # oracle is mediated_decompose (NOT decompile_to_ir).  forget(D_structure_capped(S)) ⊆ mediated_decompose(forget(S)).
    struct_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=DEFAULT_TRANSFORM_REGISTRY)
    assert struct_ir.structural_candidates, "the capped-scission family must produce a candidate for ethane+water"
    # the family really IS capped scission forgetting to a mediated edge (not a mislabelled bond-order run)
    assert all(sc.witness_kind == "CAPPED_SCISSION" for sc in struct_ir.structural_candidates)
    assert all(sc.projection_kind == "MEDIATED_EDGE" for sc in struct_ir.structural_candidates)
    struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
    inventory, medium = _derive_mediated_closure(struct_ir)
    assert medium, "the structural reagents must yield a non-empty medium (a capped scission draws water)"
    graph = mediated_decompose(ETHANE.formula, inventory, medium)
    assert graph.is_complete, "the mediated descent must be complete within budget for this small target"
    mediated_digests = {e.digest for e in graph.mediated}
    # the byte-for-byte cross-producer agreement: CappedScission.forget()'s MediatedEdge convention == mediated_edges'
    assert struct_projections <= mediated_digests


def test_dropping_the_medium_breaks_the_capped_scission_square():
    # NON-VACUITY: without the reagent MEDIUM, the mediated descent cannot draw water, so the capped-scission
    # projection (C2H6 + H2O -> CH4 + CH4O) is ABSENT -- the subset fails.  Proves the medium is load-bearing and
    # the positive test is not vacuously true.
    struct_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=DEFAULT_TRANSFORM_REGISTRY)
    struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
    inventory, _medium = _derive_mediated_closure(struct_ir)
    graph_no_medium = mediated_decompose(ETHANE.formula, inventory, ())  # no reservoir -> no mediated water draw
    assert struct_projections and not (struct_projections <= {e.digest for e in graph_no_medium.mediated})


def test_the_two_families_forget_to_distinct_edge_types_each_into_its_own_producer():
    # The multi-family lift's real content is a TYPE distinction: capped scission forgets to a reagent-drawn
    # MEDIATED_EDGE, bond order to an own-atoms DECOMPOSITION_EDGE -- which is WHY they need distinct producers.
    # This is asserted on projection_kind (real content), NOT on a cross-producer digest non-subset: because
    # contracts.canonical_payload embeds the fully-qualified class (contracts.py:149), a MediatedEdge digest and a
    # DecompositionEdge digest are disjoint by construction, so "capped projections not-a-subset-of plain candidates"
    # is a VACUOUS class-tag tautology (it survives even a wholly WRONG forget() convention -- reproduced) and proves
    # nothing about conventions.  The convention agreement is proven by the same-class POSITIVE subsets below.
    capped_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=DEFAULT_TRANSFORM_REGISTRY)
    bo_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=BOND_ORDER)
    assert capped_ir.structural_candidates and bo_ir.structural_candidates
    # the SUBSTANTIVE distinction: different forgetful codomains -> different producers
    assert {sc.projection_kind for sc in capped_ir.structural_candidates} == {"MEDIATED_EDGE"}
    assert {sc.projection_kind for sc in bo_ir.structural_candidates} == {"DECOMPOSITION_EDGE"}
    # each family's convention agrees with ITS OWN producer -- the load-bearing same-class positive subsets:
    capped_projections = {sc.projection_digest for sc in capped_ir.structural_candidates}
    cap_inventory, cap_medium = _derive_mediated_closure(capped_ir)
    mediated_digests = {e.digest for e in mediated_decompose(ETHANE.formula, cap_inventory, cap_medium).mediated}
    assert capped_projections <= mediated_digests  # capped -> mediated producer (byte-for-byte, same class)

    bo_projections = {sc.projection_digest for sc in bo_ir.structural_candidates}
    bo_inventory = _derive_formula_inventory(bo_ir)
    plain_digests = {c.candidate_digest for c in decompile_to_ir(ETHANE.formula, bo_inventory).candidates}
    assert bo_projections <= plain_digests  # bond order -> plain producer (byte-for-byte, same class)
