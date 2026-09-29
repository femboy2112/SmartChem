"""0.9.5 barrier S7 / S8 / S9 -- ONE material identity, ONE name fold, no fake sourced labels on stock claims.

* **S7** -- the stock/requirement STRUCTURE key is ``"struct:" + resonance_identity(m)`` from ONE authority
  (:func:`smartchem.experiment.stock.structure_key`). The pre-0.9.5 literal-bond-order key split alternate Kekule
  placements of ortho-disubstituted and fused aromatics, and the material axis then BLOCKED a bottle that was the very
  molecule the route asked for (C7-2: a false-BLOCKED, not a false-UNKNOWN -- Wave-A Lane D).
* **S8** -- one name normaliser (strip + casefold + collapse internal whitespace) owned by ``stock.py``.
* **S9** (B-narrow) -- stock-side component ``states`` and ``StockMaterial.phase_evidence`` refuse SOURCE_QUOTED /
  DERIVED / CLAMPED: a stock claim is the operator's declaration, and those kinds name a source record the slot
  cannot carry. Stock ``IntervalEvidence`` keeps its sourced kinds.

The Kekule controls are built by GRAPH SURGERY, never by SMILES spelling: the parser already resonance-canonicalises,
so two SMILES spellings agree under the OLD key too -- a vacuous control. Each surgery test first asserts the old
literal key really splits the set (so the control can fail), then that the one key unifies it.
"""
from __future__ import annotations

import importlib
import itertools
import json
from fractions import Fraction

import pytest

import smartchem.capability.requirements as requirements_mod
import smartchem.capability.waste as waste_mod
import smartchem.experiment.stock as stock_mod
from smartchem.capability.assess import _edge, _material_axis
from smartchem.capability.enums import CapabilityStatus
from smartchem.capability.quantity import QuantityDemand
from smartchem.capability.requirements import MaterialRequirement, name_resolves_to
from smartchem.category import Bond, Molecule
from smartchem.contracts import canonical_digest, canonical_payload
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.experiment.stock import (
    MATERIAL_COMPONENT_SCHEMA,
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
    is_structure_key,
    normalize_material_name,
    structure_key,
)
from smartchem.material_spec import (
    CompositionConstraint,
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    HydrationState,
    MaterialSpecification,
    SaturationState,
    StateClaim,
    Tolerance,
)
from smartchem.smiles import SmilesError, parse_smiles

# ``smartchem.capability`` re-exports the ``assess`` FUNCTION under the submodule's name; fetch the module itself.
assess_mod = importlib.import_module("smartchem.capability.assess")


def _literal_key(m: Molecule) -> str:
    """The pre-0.9.5 stock key, reproduced verbatim as the reference the migration is measured against."""
    try:
        return "struct:" + canonical_digest(m.canonical())
    except NotImplementedError:
        return "struct-asgiven:" + canonical_digest(m)


# -- graph surgery: every alternate Kekule placement of a molecule, WITHOUT the parser --------------------------------

def _ring_bonds(m: Molecule) -> "list[Bond]":
    """Bonds on a cycle: the endpoints stay connected once the bond is removed."""
    bonds = sorted(m.bonds, key=lambda b: (b.i, b.j))
    out = []
    for b in bonds:
        adj: "dict[int, set[int]]" = {}
        for c in bonds:
            if c is not b:
                adj.setdefault(c.i, set()).add(c.j)
                adj.setdefault(c.j, set()).add(c.i)
        seen, stack = {b.i}, [b.i]
        while stack:
            for v in adj.get(stack.pop(), ()):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if b.j in seen:
            out.append(b)
    return out


def _alternate_kekule(m: Molecule) -> "list[Molecule]":
    """Every OTHER single/double assignment of the ring bonds that preserves each atom's total bond order -- a genuine
    resonance form of the same constitution, materialised as a raw ``Molecule`` (the fragment-surgery path)."""
    ring = [b for b in _ring_bonds(m) if b.order in (1, 2)]
    assert len(ring) <= 14, "enumerator bound"
    total: "dict[int, int]" = {}
    for b in ring:
        total[b.i] = total.get(b.i, 0) + b.order
        total[b.j] = total.get(b.j, 0) + b.order
    rest = [b for b in m.bonds if b not in ring]
    alts = []
    for combo in itertools.product((1, 2), repeat=len(ring)):
        t: "dict[int, int]" = {}
        for b, o in zip(ring, combo):
            t[b.i] = t.get(b.i, 0) + o
            t[b.j] = t.get(b.j, 0) + o
        if t != total:
            continue
        bonds = frozenset(rest + [Bond(b.i, b.j, o) for b, o in zip(ring, combo)])
        if bonds != frozenset(m.bonds):
            alts.append(Molecule(m.atoms, bonds, m.charge, m.state))
    return alts


#: Lane D's measured split set: ortho-disubstituted benzenes + a fused aromatic (para/meta/mono flips are graph-
#: isomorphic and were never split, so they would be vacuous here).
_KEKULE_SPLIT = {
    "o-xylene": "Cc1ccccc1C",
    "catechol": "Oc1ccccc1O",
    "salicylic acid": "OC(=O)c1ccccc1O",
    "methyl salicylate": "COC(=O)c1ccccc1O",
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "o-cresol": "Cc1ccccc1O",
    "phthalic acid": "OC(=O)c1ccccc1C(=O)O",
    "2-aminophenol": "Nc1ccccc1O",
    "naphthalene": "c1ccc2ccccc2c1",
}


def _salicylic_pair() -> "tuple[Molecule, Molecule]":
    sal = parse_smiles(_KEKULE_SPLIT["salicylic acid"])
    flipped = next(a for a in _alternate_kekule(sal) if _literal_key(a) != _literal_key(sal))
    return sal, flipped


# -- T1: alternate Kekule spellings share ONE key (kills "key splits Kekule") ----------------------------------------

@pytest.mark.parametrize("name", sorted(_KEKULE_SPLIT))
def test_t1_graph_surgery_kekule_alternates_share_one_key(name):
    parsed = parse_smiles(_KEKULE_SPLIT[name])
    alts = _alternate_kekule(parsed)
    forms = [parsed, *alts]
    # the control is live: the literal key really split this set before 0.9.5
    assert len({_literal_key(f) for f in forms}) >= 2, f"{name}: the old key never split -- a vacuous control"
    assert len({structure_key(f) for f in forms}) == 1, f"{name}: one resonance structure, more than one key"
    assert structure_key(parsed) == _literal_key(parsed)  # the parsed form's key did not move


def _bottle(identity, *, phase=Phase.SOLID, material_id="b"):
    comp = (MaterialComponent.of_molecule(identity, "active", 1.0, 1.0) if isinstance(identity, Molecule)
            else MaterialComponent.known(identity, "active", 1.0, 1.0))
    return StockMaterial(STOCK_MATERIAL_SCHEMA, material_id, material_id, (comp,), phase, "fixture",
                         quantity=StockQuantity.of("500", "g"))


def _req(identity=None, name=None, specification=None):
    return MaterialRequirement(identity=identity, phase=None, quantity=QuantityDemand.unstated(1), role="fixture",
                               evidence_source="fixture", name=name,
                               specification=specification if specification is not None else MaterialSpecification())


@pytest.mark.parametrize("bottle_form,req_form", [("parsed", "flipped"), ("flipped", "parsed")])
def test_t1_end_to_end_flipped_salicylic_acid_is_not_blocked_on_the_material_axis(bottle_form, req_form):
    """Lane D's e2e: before 0.9.5 BOTH directions read BLOCKED ("absent from ... every declared bottle")."""
    sal, flipped = _salicylic_pair()
    pick = {"parsed": sal, "flipped": flipped}
    axis = _material_axis((_req(identity=pick[req_form]),), (_bottle(pick[bottle_form]),))
    assert axis.status is not CapabilityStatus.BLOCKED, axis.reasons
    # and the same-form baseline agrees with it: the flip changed nothing the axis can see
    same = _material_axis((_req(identity=sal),), (_bottle(sal),))
    assert axis.status is same.status


def test_t1_the_end_to_end_control_still_blocks_a_different_isomer():
    """Discriminating control: 4-hydroxybenzoic acid is NOT salicylic acid, however the latter's ring is drawn."""
    _sal, flipped = _salicylic_pair()
    para = parse_smiles("OC(=O)c1ccc(O)cc1")
    axis = _material_axis((_req(identity=flipped),), (_bottle(para),))
    assert axis.status is CapabilityStatus.BLOCKED


# -- T2: constitutional isomers stay distinct (kills "key merges isomers", e.g. a formula / skeleton key) ------------

_ISOMER_PAIRS = [
    ("o-xylene", "Cc1ccccc1C", "m-xylene", "Cc1cccc(C)c1"),
    ("o-xylene", "Cc1ccccc1C", "p-xylene", "Cc1ccc(C)cc1"),
    ("m-xylene", "Cc1cccc(C)c1", "p-xylene", "Cc1ccc(C)cc1"),
    ("ethanol", "CCO", "dimethyl ether", "COC"),
    ("propanal", "CCC=O", "acetone", "CC(C)=O"),
    ("1-propanol", "CCCO", "2-propanol", "CC(C)O"),
    ("methyl acetate", "COC(C)=O", "ethyl formate", "CCOC=O"),
    ("salicylic acid", "OC(=O)c1ccccc1O", "3-hydroxybenzoic acid", "OC(=O)c1cccc(O)c1"),
    ("salicylic acid", "OC(=O)c1ccccc1O", "4-hydroxybenzoic acid", "OC(=O)c1ccc(O)cc1"),
    ("catechol", "Oc1ccccc1O", "resorcinol", "Oc1cccc(O)c1"),
    ("catechol", "Oc1ccccc1O", "hydroquinone", "Oc1ccc(O)cc1"),
    ("paracetamol", "CC(=O)Nc1ccc(O)cc1", "3-acetamidophenol", "CC(=O)Nc1cccc(O)c1"),
    ("paracetamol", "CC(=O)Nc1ccc(O)cc1", "4-aminophenyl acetate", "CC(=O)Oc1ccc(N)cc1"),
]


@pytest.mark.parametrize("a_name,a,b_name,b", _ISOMER_PAIRS, ids=[f"{p[0]}|{p[2]}" for p in _ISOMER_PAIRS])
def test_t2_constitutional_isomers_keep_distinct_keys(a_name, a, b_name, b):
    ma, mb = parse_smiles(a), parse_smiles(b)
    assert ma.formula == mb.formula  # same formula: the pair a formula-keyed mutant would merge
    assert structure_key(ma) != structure_key(mb), f"{a_name} and {b_name} merged"


def test_t2_no_o_xylene_kekule_form_collides_with_m_or_p_xylene():
    """The coarsening is resonance-only: no surgery form of o-xylene reaches the m-/p- keys."""
    ortho = parse_smiles("Cc1ccccc1C")
    others = {structure_key(parse_smiles(s)) for s in ("Cc1cccc(C)c1", "Cc1ccc(C)cc1")}
    assert all(structure_key(f) not in others for f in (ortho, *_alternate_kekule(ortho)))


# -- T3: tautomers stay distinct (kills "key merges tautomers") ------------------------------------------------------

@pytest.mark.parametrize("a,b", [
    ("CC(C)=O", "CC(O)=C"),              # acetone / prop-1-en-2-ol
    ("O=C1C=CC=CN1", "Oc1ccccn1"),       # 2-pyridone / 2-hydroxypyridine
    ("CC(N)=O", "CC(O)=N"),              # acetamide / ethanimidic acid
])
def test_t3_tautomers_keep_distinct_keys(a, b):
    ma, mb = parse_smiles(a), parse_smiles(b)
    assert ma.formula == mb.formula
    assert structure_key(ma) != structure_key(mb)


# -- T4: the requirement side uses THE key (kills a literal digest reintroduced on the requirement/waste side) --------

def test_t4_requirement_waste_and_assess_import_the_one_key_and_fold():
    assert requirements_mod.structure_key is stock_mod.structure_key
    assert waste_mod.structure_key is stock_mod.structure_key
    assert requirements_mod._norm_text is stock_mod.normalize_material_name
    assert waste_mod._norm_text is stock_mod.normalize_material_name
    assert assess_mod.is_structure_key is stock_mod.is_structure_key
    for mod, private in ((requirements_mod, "_struct_digest"), (waste_mod, "_struct_digest"),
                         (assess_mod, "_STRUCTURE_KEY_PREFIXES")):
        assert not hasattr(mod, private), f"{mod.__name__}.{private} is back -- a second structure authority"


def test_t4_no_capability_module_computes_its_own_canonical_digest():
    """A reintroduced ``canonical_digest(m.canonical())`` twin is exactly how the split came back last time."""
    import inspect

    for mod in (requirements_mod, waste_mod, assess_mod):
        assert ".canonical()" not in inspect.getsource(mod), mod.__name__


def test_t4_name_resolves_to_uses_the_one_key_on_both_sides():
    sal, flipped = _salicylic_pair()
    assert name_resolves_to("salicylic acid", sal)
    assert name_resolves_to("salicylic acid", flipped)       # False under the literal digest (Lane D nr.py)
    assert not name_resolves_to("salicylic acid", parse_smiles("OC(=O)c1ccc(O)cc1"))


def test_t4_a_name_listed_bottle_is_a_possible_source_for_a_flipped_leaf():
    """assess D25.4 name rescue on the real key: a bottle NAME-keyed 'salicylic acid' is a possible (UNKNOWN) source for
    a nameless, Kekule-flipped leaf requirement -- not a proof of absence."""
    _sal, flipped = _salicylic_pair()
    axis = _material_axis((_req(identity=flipped),), (_bottle("salicylic acid"),))
    assert axis.status is CapabilityStatus.UNKNOWN


def test_t4_structure_key_resolves_the_implementation_by_module_global():
    """M3 patches ``stock._structure_key`` by name; the public key must follow the patch (never a captured object)."""
    m = parse_smiles("CCO")
    real = stock_mod._structure_key
    try:
        stock_mod._structure_key = lambda _m: "struct:patched"
        assert structure_key(m) == "struct:patched"
        assert requirements_mod.structure_key(m) == "struct:patched"
    finally:
        stock_mod._structure_key = real
    assert structure_key(m) == _literal_key(m)


def test_t4_asgiven_fallback_is_byte_identical_to_the_literal_key(monkeypatch):
    """A graph the canonicaliser refuses keys as ``struct-asgiven:`` + its as-given digest -- unchanged from 0.9."""
    from smartchem.smiles import resonance_canonical

    m = Molecule(("C", "C", "N", "H", "H", "H", "H", "H", "H", "H"),
                 frozenset({Bond(0, 1, 1), Bond(1, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1), Bond(0, 5, 1),
                            Bond(1, 6, 1), Bond(1, 7, 1), Bond(2, 8, 1), Bond(2, 9, 1)}), 0, "")

    def refuse(self):
        raise NotImplementedError("fixture: canonicaliser refuses")

    monkeypatch.setattr(Molecule, "canonical", refuse)
    stock_mod._structure_key.cache_clear()
    resonance_canonical.cache_clear()
    try:
        key = structure_key(m)
        assert key == "struct-asgiven:" + canonical_digest(m) == _literal_key(m)
        assert is_structure_key(key)
    finally:
        stock_mod._structure_key.cache_clear()
        resonance_canonical.cache_clear()


# -- T5: the declared identity boundary (a future refinement must be a DECLARED move) --------------------------------

def test_t5_stereoisomers_share_a_key():
    assert structure_key(parse_smiles("C[C@@H](O)CC")) == structure_key(parse_smiles("C[C@H](O)CC"))


def test_t5_isotopologues_share_a_key():
    assert structure_key(parse_smiles("O")) == structure_key(parse_smiles("[2H]O[2H]"))


def test_t5_charge_separated_and_pentavalent_nitro_stay_distinct():
    assert structure_key(parse_smiles("C[N+](=O)[O-]")) != structure_key(parse_smiles("CN(=O)=O"))


def test_t5_a_salt_is_not_one_molecule_so_it_is_name_keyed():
    with pytest.raises(SmilesError, match="one connected species"):  # the parser refuses a multi-fragment species
        parse_smiles("[Na+].[Cl-]")
    brine = _bottle("sodium chloride")
    assert not is_structure_key(brine.components[0].identity_key)
    assert brine.active_fraction_interval("Sodium  Chloride") == (1.0, 1.0)


# -- T6: no parse-origin key moves (the 69-structure sweep) ----------------------------------------------------------

def _sweep_molecules() -> "list[tuple[str, Molecule]]":
    import smartchem.data.material_library as library
    from smartchem.data.reagents import COMMODITY_REAGENTS
    from smartchem.structure import registered_structures

    out = [("registered:" + s.name, s.molecule) for s in registered_structures()]
    out += [("commodity:" + r.name, r.molecule) for r in COMMODITY_REAGENTS]
    out += [("library:" + n, v) for n in sorted(dir(library)) if isinstance(getattr(library, n), Molecule)
            for v in (getattr(library, n),)]
    return out


def test_t6_no_registered_commodity_or_library_key_moves():
    swept = _sweep_molecules()
    assert len(swept) >= 69, f"the no-move sweep shrank to {len(swept)} structures -- a thinner control"
    moved = [name for name, m in swept if structure_key(m) != _literal_key(m)]
    assert moved == [], f"parse-origin keys moved: {moved}"


# -- S8: one name fold -----------------------------------------------------------------------------------------------

def test_s8_normalize_material_name_folds_case_and_every_whitespace_run():
    assert normalize_material_name("  Sodium \t  Bicarbonate\n") == "sodium bicarbonate"
    assert normalize_material_name("baking soda") != normalize_material_name("sodium bicarbonate")  # not synonymy


def test_s8_a_double_spaced_requirement_name_finds_its_bottle():
    """Before 0.9.5 stock folded strip+casefold only: "sodium  bicarbonate" missed its bottle -> BLOCKED."""
    axis = _material_axis((_req(name="sodium  bicarbonate"),), (_bottle("sodium bicarbonate"),))
    assert axis.status is not CapabilityStatus.BLOCKED, axis.reasons
    control = _material_axis((_req(name="sodium bicarbonate"),), (_bottle("baking soda"),))
    assert control.status is CapabilityStatus.BLOCKED  # the declared world's keys stay closed


# -- S9: B-narrow -- no sourced kind on a stock state / phase claim --------------------------------------------------

_REFUSED = (EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.CLAMPED)
_ALLOWED = (EvidenceKind.USER_DECLARED, EvidenceKind.ASSUMED, EvidenceKind.AUTHOR_INFERRED, EvidenceKind.UNKNOWN)


@pytest.mark.parametrize("kind", _REFUSED, ids=lambda k: k.value)
@pytest.mark.parametrize("state", [DilutionState.NEAT, HydrationState.ANHYDROUS, SaturationState.SATURATED],
                         ids=lambda s: s.value)
def test_s9_a_component_state_refuses_a_sourced_kind(kind, state):
    with pytest.raises(ValueError, match="operator's declaration"):
        MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "brine", "active", 0.0, 1.0, states=(StateClaim(state, kind),))


@pytest.mark.parametrize("kind", _REFUSED, ids=lambda k: k.value)
def test_s9_phase_evidence_refuses_a_sourced_kind(kind):
    comp = (MaterialComponent.known("brine", "active", 0.0, 1.0),)
    with pytest.raises(ValueError, match="operator's declaration"):
        StockMaterial(STOCK_MATERIAL_SCHEMA, "b", "b", comp, Phase.AQUEOUS_SOLUTION, "p", phase_evidence=kind)


@pytest.mark.parametrize("kind", _ALLOWED, ids=lambda k: k.value)
def test_s9_the_operator_kinds_still_construct(kind):
    comp = MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "brine", "active", 0.0, 1.0,
                             states=(StateClaim(SaturationState.SATURATED, kind),))
    bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "b", "b", (comp,), Phase.AQUEOUS_SOLUTION, "p", phase_evidence=kind)
    assert bottle.phase_evidence is kind and comp.states[0].evidence is kind


@pytest.mark.parametrize("slot", ["phase_evidence", "state"])
def test_s9_a_forged_wire_stock_claim_is_refused_at_decode(slot):
    """The wire re-runs the constructors: a payload relabelling a stock claim SOURCE_QUOTED fails closed on decode."""
    from smartchem.service import _decode_canonical

    comp = MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "brine", "active", 0.0, 1.0,
                             states=(StateClaim(SaturationState.SATURATED, EvidenceKind.USER_DECLARED),))
    honest = StockMaterial(STOCK_MATERIAL_SCHEMA, "b", "b", (comp,), Phase.AQUEOUS_SOLUTION, "p",
                           phase_evidence=EvidenceKind.USER_DECLARED)
    payload = canonical_payload(honest)
    assert _decode_canonical(json.loads(json.dumps(payload))) == honest  # the honest round trip decodes

    slot_field = "phase_evidence" if slot == "phase_evidence" else "evidence"  # StateClaim.evidence

    def forge(node, field=None):
        # relabel the EvidenceKind enum node sitting in the targeted field; walk dataclass fields and tuple items
        if node.get("class") == "smartchem.material_spec.EvidenceKind" and field == slot_field:
            node["value"]["value"] = "SOURCE_QUOTED"
            return
        for name, sub in node.get("fields", ()):
            forge(sub, name)
        for item in node.get("items", ()):
            forge(item, field)

    forged = json.loads(json.dumps(payload))
    forge(forged)
    assert forged != payload
    with pytest.raises(ValueError, match="operator's declaration"):
        _decode_canonical(forged)


def _interval(kind: EvidenceKind) -> IntervalEvidence:
    """One stock interval, [0.264705, 0.264706] MASS_FRACTION (saturated NaCl), under each stock interval kind."""
    mf, loc = ConcentrationBasis.MASS_FRACTION, "https://pubchem.ncbi.nlm.nih.gov/compound/5234"
    if kind is EvidenceKind.DERIVED:
        return IntervalEvidence.build(
            kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1, basis=mf,
            inputs=(TypedInput("low", "36.0", InputUnit.G_PER_100G_SOLVENT, EvidenceKind.SOURCE_QUOTED, loc),
                    TypedInput("high", "36.0", InputUnit.G_PER_100G_SOLVENT, EvidenceKind.SOURCE_QUOTED, loc)),
            source_locators=(loc,), domain_of_validity="fixture")
    if kind is EvidenceKind.SOURCE_QUOTED:
        return IntervalEvidence.build(
            kernel=DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, basis=mf,
            inputs=(TypedInput("low", "0.264705", InputUnit.FRACTION, EvidenceKind.SOURCE_QUOTED, loc),
                    TypedInput("high", "0.264706", InputUnit.FRACTION, EvidenceKind.SOURCE_QUOTED, loc)),
            source_locators=(loc,), domain_of_validity="fixture")
    return IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=mf,
        inputs=(TypedInput("low", "0.264705", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", "0.264706", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="fixture")


def test_s9_pin_stock_interval_kinds_give_identical_edge_verdicts():
    """Barrier §8 pin: stock SOURCE_QUOTED / DERIVED / USER_DECLARED intervals are edge-for-edge indistinguishable --
    every stock claim certifies exactly as the operator's word, so S9 removes a label, never a capability."""
    mf = ConcentrationBasis.MASS_FRACTION

    def spec(**kw):
        return MaterialSpecification(**kw)

    requirements = [
        _req(name="sodium chloride"),
        _req(name="sodium chloride", specification=spec(composition=CompositionConstraint(
            "0.26", "0.27", mf, Tolerance.STATED_INTERVAL, EvidenceKind.SOURCE_QUOTED))),
        _req(name="sodium chloride", specification=spec(composition=CompositionConstraint(
            "0.99", "1", mf, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED))),
        _req(name="sodium chloride", specification=spec(composition=CompositionConstraint(
            "0.2647055", "0.3", mf, Tolerance.STATED_INTERVAL, EvidenceKind.SOURCE_QUOTED))),
        _req(name="sodium chloride", specification=spec(states=(
            StateClaim(SaturationState.SATURATED, EvidenceKind.SOURCE_QUOTED),))),
    ]
    rows = {}
    for kind in (EvidenceKind.SOURCE_QUOTED, EvidenceKind.DERIVED, EvidenceKind.USER_DECLARED):
        ev = _interval(kind)
        assert ev.kind is kind and ev.interval == (Fraction("0.264705"), Fraction("0.264706"))
        declared_saturated = (StateClaim(SaturationState.SATURATED, EvidenceKind.USER_DECLARED),)
        comp = MaterialComponent.evidenced("sodium chloride", "active", ev, states=declared_saturated)
        bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "brine", "brine", (comp,), Phase.AQUEOUS_SOLUTION, "fixture",
                               quantity=StockQuantity.of("100", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)
        rows[kind] = [(e.status, e.commensurable) for e in (_edge(r, bottle) for r in requirements)]
    assert rows[EvidenceKind.SOURCE_QUOTED] == rows[EvidenceKind.DERIVED] == rows[EvidenceKind.USER_DECLARED], rows
    # non-vacuous: the matrix spans certify / refute / undetermined, not one flat answer
    assert {s for s, _c in rows[EvidenceKind.USER_DECLARED]} == {
        CapabilityStatus.FIT, CapabilityStatus.BLOCKED, CapabilityStatus.UNKNOWN}


# -- schema ids ------------------------------------------------------------------------------------------------------

def test_the_two_bumped_schema_ids_are_current_and_the_old_ones_refused():
    assert MATERIAL_COMPONENT_SCHEMA == "smartchem.experiment/material-component-v1alpha3"
    assert STOCK_MATERIAL_SCHEMA == "smartchem.experiment/stock-material-v1alpha4"
    with pytest.raises(ValueError, match="schema_version"):
        MaterialComponent("smartchem.experiment/material-component-v1alpha2", "x", "active", 0.0, 1.0)
    with pytest.raises(ValueError, match="schema_version"):
        StockMaterial("smartchem.experiment/stock-material-v1alpha3", "m", "m",
                      (MaterialComponent.known("x", "active", 0.0, 1.0),), Phase.LIQUID, "p")
