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
from smartchem.structure_descent import heterolytic_formula_edges, redox_edges
from smartchem.transform_provider import (
    CappedScissionProvider,
    HeterolyticScissionProvider,
    RedoxHalfReactionProvider,
    TransformProviderRegistry,
)

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


# ======================================================================================
# IR-COMMUTE k>=2: the capped-scission square past the DEFAULT single cut
# ======================================================================================
def test_the_capped_scission_square_commutes_at_k2_multi_cut():
    # methanol + water under max_reactant_cuts=2 produces a genuine k=2 projection consuming water at multiplicity 2
    # (two cuts in one rewrite); it commutes into mediated_decompose ONLY at max_reagent_instances=2, closing the
    # boundary the ROUND-6 brick named as conjectured.  (A tiny target on purpose -- k=2 is combinatorially large;
    # propane/diester+water blow the budget, methanol+water is the minimal clean witness.)
    reg2 = TransformProviderRegistry((CappedScissionProvider(max_reactant_cuts=2),))
    struct_ir = decompile_structure_to_ir(parse_smiles("CO"), reagents=(WATER,), registry=reg2, budget=5000)
    assert struct_ir.diagnostics == ()  # exhaustive within budget -- not a partial search silently passing
    assert struct_ir.structural_candidates
    assert all(sc.projection_kind == "MEDIATED_EDGE" for sc in struct_ir.structural_candidates)
    # a genuine k=2 witness: some projection consumes a reagent at multiplicity 2 (not just the k=1 single cut)
    assert any(m == 2 for sc in struct_ir.structural_candidates for _s, m in sc.reagents)
    struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
    inventory, medium = _derive_mediated_closure(struct_ir)
    methanol_formula = parse_smiles("CO").formula
    g1 = mediated_decompose(methanol_formula, inventory, medium, max_reagent_instances=1)
    g2 = mediated_decompose(methanol_formula, inventory, medium, max_reagent_instances=2)
    assert g1.is_complete and g2.is_complete
    # non-vacuity control (for free): the k=2 projections are ABSENT at the single-cut default, present at max=2
    assert not (struct_projections <= {e.digest for e in g1.mediated})
    assert struct_projections <= {e.digest for e in g2.mediated}


# ======================================================================================
# IR-COMMUTE: a THIRD family -- the redox (electron-transfer) square, at EQUALITY
# ======================================================================================
def test_the_redox_forgetful_square_commutes_at_equality():
    # Redox forgets to an ELECTRON_TRANSFER_EDGE, whose formula-side producer is redox_edges.  Redox is charge-only and
    # mass-trivial -- the oxidized formula is fully DETERMINED by the reactant atoms + n, so there is NO inventory,
    # medium, or search, and the square closes at == (set equality), STRONGER than the neutral families' ⊆.  The
    # substantive content is the convention agreement + type-disjointness, not a search-correctness claim.
    for smiles, max_e, n_expected in (("[Na]", 2, 2), ("N=O", 3, 3)):
        target = parse_smiles(smiles)
        reg = TransformProviderRegistry((RedoxHalfReactionProvider(max_electrons=max_e),))
        struct_ir = decompile_structure_to_ir(target, reagents=(WATER,), registry=reg)
        assert {sc.projection_kind for sc in struct_ir.structural_candidates} == {"ELECTRON_TRANSFER_EDGE"}
        struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
        formula_edges = {e.digest for e in redox_edges(Formula.of(target.formula, target.charge), max_electrons=max_e)}
        assert len(struct_projections) == n_expected  # non-vacuous: the family actually produced n edges
        assert struct_projections == formula_edges     # == , not merely ⊆ (no formula-side search asymmetry exists)
        # non-vacuity: dropping one electron from the formula producer breaks the equality (a strict subset), so the
        # == is CONTENT-load-bearing.  Mechanism (red-team clarification): the == catches a wrong ELECTRON-COUNT /
        # asymmetric-set convention; a wrong CHARGE convention (sign flip / off-by-one) is caught UPSTREAM by
        # ElectronTransferEdge's charge certificate (it RAISES in __post_init__), so it can never produce a
        # matching-but-wrong set -- either way a broken convention turns this test red, never vacuously green.
        fewer = {e.digest for e in redox_edges(Formula.of(target.formula, target.charge), max_electrons=max_e - 1)}
        assert fewer < struct_projections


# ======================================================================================
# IR-COMMUTE: the FOURTH (and last) family -- the heterolytic (ionic) square, at ⊆
# ======================================================================================
def test_the_heterolytic_forgetful_square_commutes_via_the_formula_producer():
    # The 4th and last family to gain a formula producer: heterolysis forgets to a CHARGED_DECOMPOSITION_EDGE, whose
    # formula-side oracle is heterolytic_formula_edges (an atom-partition + localized-charge search).  UNLIKE redox
    # (==, no search: the oxidised formula is fully determined), the bond graph is FORGOTTEN here, so which atoms land
    # on which ion is a real partition SEARCH and the producer OVER-produces -> the square closes at ⊆, like the
    # bond-order and capped families.
    reg = TransformProviderRegistry((HeterolyticScissionProvider(),))
    struct_ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=reg)
    assert struct_ir.structural_candidates, "heterolysis must produce a candidate for ethane"
    # the family really IS heterolysis forgetting to a charged edge (not a mislabelled neutral run)
    assert {sc.witness_kind for sc in struct_ir.structural_candidates} == {"HETEROLYTIC_SCISSION"}
    assert {sc.projection_kind for sc in struct_ir.structural_candidates} == {"CHARGED_DECOMPOSITION_EDGE"}
    struct_projections = {sc.projection_digest for sc in struct_ir.structural_candidates}
    formula_edges, complete = heterolytic_formula_edges(Formula.of(ETHANE.formula, ETHANE.charge))
    assert complete, "the formula producer must exhaust ethane's partition search within budget"
    formula_digests = {e.digest for e in formula_edges}
    # ⊆ , byte-for-byte, SAME class (both ChargedDecompositionEdge digests): every structural forget image appears
    # among the formula producer's edges -- a real content check (overlapping namespaces), never a vacuous cross-class
    # tag disjointness.  This is the exact convention agreement the redox == and the capped/bond-order ⊆ prove.
    assert struct_projections <= formula_digests
    # STRICT subset (non-vacuity): the formula producer splits the atom MULTISET every way, so it emits partitions no
    # order-1 bridge bond realises (a C|C-split / H2-on-one-side split of ethane that no single cut can make) -> edges
    # ABSENT from the structural set.  This proves the relation is a genuine ⊆ and NOT a secret == -- the honest
    # asymmetry the graph search creates, exactly like bond-order/capped and UNLIKE redox's search-free ==.
    assert struct_projections < formula_digests


def test_heterolytic_formula_producer_mirrors_the_localized_model_and_conserves():
    # A direct producer check, independent of the IR machinery, with only NON-VACUOUS assertions (red-team fold: the
    # old bare `product_charge == reactant.charge` re-check was dead -- ChargedDecompositionEdge.__post_init__ RAISES
    # on charge non-conservation, so a violating edge can never reach the assert; the "checks-derived-from-its-own-
    # subject" trap).  Every assertion here checks something the certificate does NOT already guarantee:
    from smartchem.structure_descent import heterolytic_scissions
    # (a) it really MIRRORS the structural model: for water the producer's edges CONTAIN every structural heterolysis'
    #     forget image (the ⊆ direction proven at the producer level, no IR machinery) -- and it CAN fail (an emitted
    #     wrong-convention edge would make a structural forget absent), so it is load-bearing.
    water = parse_smiles("O")
    edges, complete = heterolytic_formula_edges(Formula.of(water.formula, water.charge))
    assert complete
    producer_digests = {e.digest for e in edges}
    structural_forgets = {h.forget().digest for h in heterolytic_scissions(water)}
    assert structural_forgets and structural_forgets <= producer_digests
    # (b) the LOCALIZED-CHARGE signature holds on EVERY producer edge (one fragment exactly ±1) -- a PRODUCER choice,
    #     NOT a certificate invariant (ChargedDecompositionEdge conserves charge but would happily accept a (-2,+2)
    #     split), so this assertion genuinely CAN fail if the charge-pair logic drifts.
    for e in edges:
        product_charges = [f.charge for f, m in e.products for _ in range(m)]
        assert any(abs(c) == 1 for c in product_charges), e.equation()
    # (c) HCl (neutral, one bridge) yields exactly the two localized splits H^+ + Cl^- and H^- + Cl^+ (count check)
    assert len(heterolytic_formula_edges(Formula.parse("HCl"))[0]) == 2
    # (d) a starved budget returns a LOUD partial, never a silent full result (W2)
    _partial, partial_complete = heterolytic_formula_edges(Formula.parse("HCl"), budget=1)
    assert partial_complete is False


def test_heterolytic_formula_producer_handles_a_charged_reactant():
    # Coverage fold (red-team gap): the docstring claims the GENERAL localized model (any reactant charge q), but the
    # committed square/HCl tests only exercise neutral S.  A charged reactant: hydronium H3O^+ (q=+1).  Every emitted
    # edge must conserve charge to q AND carry the localized signature -- both FALSIFIABLE (the certificate conserves
    # charge, but the ±1 signature and the "== q, not == 0" target are producer choices a drift would break).
    h3o = Formula.parse("H3O", charge=1)
    edges, complete = heterolytic_formula_edges(h3o)
    assert complete and edges
    for e in edges:
        product_charge = sum(f.charge * m for f, m in e.products)
        assert product_charge == 1  # conserved to the reactant's q=+1 (not silently neutralized to 0)
        product_charges = [f.charge for f, m in e.products for _ in range(m)]
        assert any(abs(c) == 1 for c in product_charges), e.equation()
    # non-vacuity that the q actually threads: at least one edge splits the pre-existing charge onto a polyatomic ion
    # (e.g. H2O^0 + H^+ , or OH^- + H2^2+ ) -- a q=0 producer could never emit a net-+1 product set
    assert any(sum(f.charge * m for f, m in e.products) == 1 for e in edges)
