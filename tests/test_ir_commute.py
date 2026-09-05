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

Boundary (named, not hidden): this closes the square for the BOND_ORDER_EDIT family.  The capped-scission family has
a formula-layer mediated search (``decompiler_mediated.mediated_decompose``) that is not yet wired into
``compilation_ir``; the heterolytic/redox families have no formula-layer producer at all.  Extending the square to
those is the remaining IR-FORGET-01 follow-on.
"""
from __future__ import annotations

from smartchem.bond_order_edit import BondOrderEditProvider
from smartchem.compilation_ir import (
    DEFAULT_TRANSFORM_REGISTRY,
    decompile_structure_to_ir,
    decompile_to_ir,
)
from smartchem.decompiler import Formula
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
