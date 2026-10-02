"""0.9.5 A15 -- Wave D capability/evidence fixes (hostile non-author review).

The governing laws, restated so the tests below can be read against them:

* ``stock.collapse_material_name`` (whitespace only) CERTIFIES an identity; ``stock.normalize_material_name``
  (casefold) is a POSSIBLE match only.
* One-sided: a name may FORCE containment or a hazard category, never CLEAR one.
* S17 law 9: a case-only match resolves only a string that does not read as a formula -- one predicate,
  ``stock.reads_as_formula``, owned beside the two folds.

Findings, each pinned below with its witness and the fix's honest control:

* **F2 (P0)** -- S18's casefold handed ``"WAtEr"`` (W+At+Er) water's EMPTY hazard record and GROCERY catalyst tier, and
  the synthetic DME route with a CATALYST use spelled ``WAtEr`` reached overall CAPABILITY_FIT. Fix: a folded hazard hit
  is returned only when the match certifies (any record certifies: an empty one clears, a GHS one replaces UNKNOWN);
  every catalyst key goes through the same certification against its honest spelling; the hazard scan's name dedups
  moved to the exact fold.
* **F10** -- the exact-spelling ledger was a hand list of six single-word keys: ``"CoNC H2SO4"`` (a cobalt formula)
  read as HARDWARE sulfuric acid. Fix: the case rule runs on EVERY key (whole string and token by token).
* **F7** -- procurement vouched a typed CATALYST use by its display name (H2SO4 labelled ``"water"`` -> GROCERY).
* **F8** -- a typed use covering an envelope catalyst string deleted the HAZARDOUS the string alone derived.
* **Residual (L3 on USE_STREAM)** -- ROUTED(AQUEOUS_NEUTRAL) discharged the spent stream of a species with no hazard
  record; L3 covered only BYPRODUCT/RESIDUAL.

The case-variant instrument (:func:`_parses`) is the formula grammar called directly, calibrated on known readings
before any reading counts -- it is not the predicate under test.
"""
from __future__ import annotations

import dataclasses as dc
import itertools
import random
import re
from pathlib import Path

import pytest

import smartchem.experiment.catalyst_availability as ca
import smartchem.experiment.stock as stock_mod
import smartchem.structure as structure_mod
from smartchem.capability.assess import _edge
from smartchem.capability.enums import CapabilityStatus, WasteCapability
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.capability.waste import derive_waste
from smartchem.data import material_library
from smartchem.data.hazards import HAZARD_REFS, hazards_for_named
from smartchem.data.reagents import COMMODITY_REAGENTS, Availability
from smartchem.experiment.catalyst_availability import catalyst_availability
from smartchem.experiment.stock import Phase, StockQuantity, collapse_material_name, is_structure_key
from smartchem.formula_expr import FormulaSyntaxError, parse_formula_expr
from smartchem.identity_parse import resolve_identity
from smartchem.procedure_evidence import OperationKind, ProcedureMaterialRole
from smartchem.stream_disposition import DispositionValue, SubjectKind, species_key
from smartchem.structure import structure_by_name

from tests.test_v0_9_5_disposition_consumption import (
    _H2SO4,
    _UNRECORDED_CAT,
    _assess,
    _d,
    _dme,
    _exact_profile,
    _micro,
    _op,
    _statuses,
    _subject_of,
    _with,
    _witness_dispositions,
)
from tests.test_v0_9_5_evidence_soundness import (
    _dme_with_h2so4,
    _name_req,
    _named_bottle,
    _rendered,
    _with_catalysts,
)
from tests.test_v0_9_round_v_zero_fit_theorem import _METHANOL, _WATER, _maximal_profile, _pure, _use

_AN, _HAZ = WasteCapability.AQUEOUS_NEUTRAL, WasteCapability.HAZARDOUS


# =====================================================================================================================
# the instrument: the formula grammar itself, calibrated on known readings
# =====================================================================================================================

def _parses(text: str) -> bool:
    try:
        parse_formula_expr(text)
    except (FormulaSyntaxError, ValueError):
        return False
    return True


#: all 2^n case variants are enumerated for a string (or token) with at most this many letters; beyond it, a seeded
#: sample plus the specific confusables (the brief's "seeded sample otherwise").
_EXHAUSTIVE_LETTERS = 12
_SAMPLE = 64


def _case_variants(text: str) -> "list[str]":
    letters = [i for i, c in enumerate(text) if c.isalpha()]
    out = []
    for mask in range(1 << len(letters)):
        chars = list(text)
        for bit, i in enumerate(letters):
            chars[i] = chars[i].upper() if mask >> bit & 1 else chars[i].lower()
        out.append("".join(chars))
    return out


def _variants(honest: str, seed: int) -> "set[str]":
    """Every case variant of ``honest`` when it is short; otherwise every case variant of each TOKEN (others kept
    honest), a seeded random sample of whole-string variants, and the upper / lower / title spellings."""
    letters = sum(c.isalpha() for c in honest)
    if letters <= _EXHAUSTIVE_LETTERS:
        return set(_case_variants(honest))
    tokens = honest.split(" ")
    out = {honest.upper(), honest.lower(), honest.title()}
    for i, token in enumerate(tokens):
        if sum(c.isalpha() for c in token) <= _EXHAUSTIVE_LETTERS:
            for v in _case_variants(token):
                out.add(" ".join(tokens[:i] + [v] + tokens[i + 1:]))
    rng = random.Random(seed)
    for _ in range(_SAMPLE):
        out.add("".join(c.upper() if c.isalpha() and rng.random() < 0.5 else c.lower() for c in honest))
    return out


def _formula_shaped(variant: str, honest: str) -> bool:
    """Does ``variant``'s letter case carry meaning against ``honest`` -- the whole string, or a token spelled
    differently from the honest token, reads as a formula?"""
    if _parses(variant):
        return True
    return any(a != b and _parses(a) for a, b in zip(variant.split(" "), honest.split(" ")))


#: the confusables the review named (and a few siblings), checked whatever the sampler drew
_CONFUSABLES = ("WAtEr", "W At Er", "CoNC H2SO4", "CoNC. H2SO4", "CONC. H2SO4", "CONC H2SO4", "CoNC. HCl", "RaNeY Ni",
                "raney NI", "SAlICYLiC AcID", "sulfuric AcID", "Na2Co3", "K2Co3", "NaHCo3", "PTO2", "PDCl2", "TICl4")


def test_the_instrument_is_calibrated_on_known_readings():
    for formula in ("WAtEr", "CoNC H2SO4", "CONC. H2SO4", "Na2Co3", "PTO2", "NI", "AcID", "H2SO4"):
        assert _parses(formula), formula
    for word in ("water", "Water", "WATER", "conc. H2SO4", "Conc. H2SO4", "sulfuric acid", "SULFURIC ACID", "raney"):
        assert not _parses(word), word
    assert "WAtEr" in _variants("water", 0) and len(_variants("water", 0)) == 32
    assert _formula_shaped("raney NI", "Raney Ni") and not _formula_shaped("Raney Ni", "Raney Ni")
    assert _formula_shaped("CoNC H2SO4", "conc H2SO4") and not _formula_shaped("Conc H2SO4", "conc H2SO4")


# =====================================================================================================================
# (a) one owner of "reads as formula", beside the two folds
# =====================================================================================================================

def test_one_owner_of_the_formula_test():
    root = Path(stock_mod.__file__).resolve().parent.parent
    defs = [str(p.relative_to(root)) for p in root.rglob("*.py")
            if "def reads_as_formula(" in p.read_text(encoding="utf-8")
            or "def _reads_as_formula(" in p.read_text(encoding="utf-8")]
    assert defs == ["experiment/stock.py"], defs
    assert not hasattr(structure_mod, "_reads_as_formula")  # structure imports the owner's; no module-level copy
    assert stock_mod.reads_as_formula("WAtEr") and not stock_mod.reads_as_formula("water")
    assert structure_by_name("WAtEr") is None and structure_by_name("Water").name == "water"  # S17 law 9 unchanged


# =====================================================================================================================
# F2 (P0) -- WAtEr: the hazard leg, the catalyst leg, and the false CAPABILITY_FIT
# =====================================================================================================================

def _f2_route(name: str):
    """The DME witness + an identity-less CATALYST use spelled ``name`` + the witness dispositions + ROUTED(AQUEOUS_
    NEUTRAL) on the catalyst residual (probe p10_water_case.py)."""
    base = _dme()
    ops = list(base.steps[0].envelope.procedure.operations)
    ops[0] = dc.replace(ops[0], material_uses=ops[0].material_uses
                        + (_use(name, ProcedureMaterialRole.CATALYST, None, qty="1"),))
    r = _rendered(base, ops)
    water, op3 = _subject_of(r, SubjectKind.BYPRODUCT), _subject_of(r, SubjectKind.OP_STREAM)
    methanol = _subject_of(r, SubjectKind.RESIDUAL, core=species_key(_METHANOL, "methanol"))
    cat = _subject_of(r, SubjectKind.RESIDUAL, core=species_key(None, name))
    return _with(r, _d(water), _d(op3), _d(methanol, DispositionValue.CONSUMED_COMPLETELY), _d(cat))


def _f2_bench(name: str):
    bottle = dc.replace(_named_bottle(name, mid="bench-bottle", phase=Phase.LIQUID),
                        quantity=StockQuantity.of("500", "mL"))
    return dc.replace(_exact_profile(), material_inventory=(_pure("methanol-pure", _METHANOL), bottle),
                      procurement=frozenset({Availability.GROCERY}))


def test_f2_the_water_case_lookups_no_longer_certify():
    assert hazards_for_named("WAtEr") is None             # pre-fix: water's EMPTY record (a clearance)
    assert catalyst_availability("WAtEr") is None         # pre-fix: GROCERY (a vouch)
    assert structure_by_name("WAtEr") is None
    assert resolve_identity("WAtEr").receipt.normalized == "AtErW"  # it IS a formula: W + At + Er


@pytest.mark.parametrize("name", ["WAtEr", "W At Er"])
def test_f2_the_false_capability_fit_is_gone(name):
    """Pre-fix FAILS for ``WAtEr``: overall CAPABILITY_FIT on the exact bench (probe p10). ``W At Er`` was already
    honest (no fold hit) and stays so."""
    route = _f2_route(name)
    a = _assess(route, _f2_bench(name))
    assert a.overall is not CapabilityStatus.FIT and not a.is_capability_fit, _statuses(a)
    assert a.waste.status is CapabilityStatus.UNKNOWN and a.containment.status is CapabilityStatus.UNKNOWN
    assert a.procurement.status is CapabilityStatus.BLOCKED  # a declared, unrecognized catalyst BLOCKS
    reqs = compile_capability_requirements(route)
    assert any(repr(name) in u for u in reqs.hazard_unresolved)
    assert any("no hazard record" in u and "(L3)" in u for u in derive_waste(route)[2])


def test_f2_control_the_honest_spelling_reaches_fit_on_the_same_bench():
    """The probe discriminates: real water on the same bench is FIT, so the WAtEr verdict is the name's doing."""
    a = _assess(_f2_route("water"), _f2_bench("water"))
    assert a.overall is CapabilityStatus.FIT and a.is_capability_fit, _statuses(a)


def test_f2_the_hazard_scan_dedups_on_the_exact_spelling():
    """Two identity-less uses spelled "water" and "WAtEr" now get DIFFERENT hazard answers, so the scan must not merge
    them under the casefold (it would let water's record answer for W+At+Er and drop the UNKNOWN)."""
    route = _micro(_op(uses=(_use("water", ProcedureMaterialRole.CATALYST), _use("WAtEr", ProcedureMaterialRole.CATALYST))))
    unresolved = compile_capability_requirements(route).hazard_unresolved
    assert any("'WAtEr'" in u for u in unresolved), unresolved
    assert not any("'water'" in u for u in unresolved)


def test_f2_the_untyped_hazard_dedup_is_exact_too():
    route = _micro(_op(materials=("water", "WAtEr")))
    unresolved = compile_capability_requirements(route).hazard_unresolved
    assert any("'WAtEr'" in u for u in unresolved), unresolved


# =====================================================================================================================
# F10 -- the case rule runs on EVERY key, multi-word keys included
# =====================================================================================================================

@pytest.mark.parametrize("spelling, tier", [
    ("CoNC H2SO4", None), ("CoNC. H2SO4", None), ("CONC. H2SO4", None), ("CONC H2SO4", None), ("CoNC. HCl", None),
    ("RaNeY Ni", None), ("raney NI", None), ("SAlICYLiC AcID", None), ("WAtEr", None),
    ("conc h2so4", "HARDWARE"), ("conc H2SO4", "HARDWARE"), ("conc. H2SO4", "HARDWARE"), ("Conc. H2SO4", "HARDWARE"),
    ("conc. HCl", "HARDWARE"), ("Raney Ni", "INDUSTRIAL"), ("HCl", "HARDWARE"), ("hcl", "HARDWARE"),
    ("Salicylic acid", "PHARMACY"), ("Water", "GROCERY"), ("WATER", "GROCERY"),
])
def test_f10_catalyst_spellings(spelling, tier):
    """Pre-fix FAILS on every formula-shaped multi-word spelling: ``CoNC H2SO4`` read as HARDWARE sulfuric acid."""
    got = catalyst_availability(spelling)
    assert (None if got is None else got.name) == tier


def test_f10_the_procurement_row_carries_no_tier_for_a_cobalt_formula():
    rows = compile_capability_requirements(_micro(catalysts=("CoNC H2SO4", "conc H2SO4"))).procurement_catalysts
    assert rows == (("CoNC H2SO4", None), ("conc H2SO4", Availability.HARDWARE)), rows


def test_f10_the_ledger_is_honest_spellings_only():
    for key, spelling in ca._CASE_EXACT_SPELLING.items():
        assert spelling.casefold() == key and key in (set(ca._COMMODITY_BY_NAME) | set(ca._CATALYST_TABLE)), key
        assert catalyst_availability(spelling) is not None, spelling  # the honest spelling resolves
        assert any(_parses(token) for token in spelling.split()), spelling  # and carries a formula token
    # a key absent from the ledger is its own honest spelling: every commodity name is a fold fixed point
    assert all(collapse_material_name(r.name).casefold() == r.name for r in COMMODITY_REAGENTS)
    # every table key with a letters-then-digit token (an unmistakable formula token: h2so4, k2co3, rucl3 -- not
    # "propan-2-ol" or "2nd") has its honest spelling recorded
    for key in set(ca._COMMODITY_BY_NAME) | set(ca._CATALYST_TABLE):
        if any(re.fullmatch(r"[a-z]+[0-9][a-z0-9]*", t) for t in key.split()):
            assert key in ca._CASE_EXACT_SPELLING, key


# =====================================================================================================================
# (d) the EXHAUSTIVE case-variant invariant
# =====================================================================================================================

def test_invariant_hazard_records():
    """For every hazard record and every case variant of its name: the lookup returns that record or nothing (never
    another record), a formula-shaped variant gets NOTHING (no record -- an empty one would clear, a GHS one would
    replace UNKNOWN with another spelling's hazards), and the exact spelling resolves."""
    exercised = set()
    for seed, ref in enumerate(HAZARD_REFS):
        assert hazards_for_named(ref.name) is ref and hazards_for_named(f"  {ref.name} ") is ref
        for v in _variants(ref.name, seed) | {c for c in _CONFUSABLES if c.casefold() == ref.name}:
            got = hazards_for_named(v)
            assert got is None or got is ref, (v, got)
            if collapse_material_name(v) != ref.name and _formula_shaped(v, ref.name):
                exercised.add(v)
                assert got is None, (v, "a formula-shaped case variant was certified")
    assert "WAtEr" in exercised  # the instrument reached the finding


def test_invariant_catalyst_keys():
    """For every key of both catalyst tables and every case variant: the tier is the key's own or none (never another
    key's), a formula-shaped variant of the honest spelling never vouches (``None``), and the honest spelling and its
    whitespace variant resolve to the key's tier."""
    keys = sorted(set(ca._COMMODITY_BY_NAME) | set(ca._CATALYST_TABLE))
    exercised = set()
    for seed, key in enumerate(keys):
        honest = ca._CASE_EXACT_SPELLING.get(key, key)
        tier = catalyst_availability(honest)
        assert tier is not None, key
        # (outer whitespace only: catalyst_availability's own key fold strips but does not collapse an interior run --
        # a double-spaced spelling is unrecognized, the safe direction; not this barrier's to widen)
        assert catalyst_availability(f"  {honest} ") is tier, key
        for v in _variants(honest, seed) | {c for c in _CONFUSABLES if c.casefold() == key}:
            got = catalyst_availability(v)
            assert got is None or got is tier, (key, v, got)
            if collapse_material_name(v) != honest and _formula_shaped(v, honest):
                exercised.add(v)
                assert got is None, (key, v, got)
    for finding in ("WAtEr", "CoNC H2SO4", "CONC. H2SO4", "RaNeY Ni", "raney NI", "SAlICYLiC AcID", "Na2Co3"):
        assert finding in exercised, finding


def _registered_stock_name_keys() -> "set[str]":
    keys = set()
    for builder in (material_library.isopentyl_fully_declared_inventory, material_library.isopentyl_lab_inventory,
                    material_library.isopentyl_vinegar_inventory, material_library.isopentyl_wrong_phase_inventory,
                    material_library.isopentyl_insufficient_quantity_inventory):
        for bottle in builder():
            keys.update(c.identity_key for c in bottle.components if not is_structure_key(c.identity_key))
    return keys


def test_invariant_stock_name_keys():
    """For every registered NAME-keyed stock component (plus the fixture keys of the S18 cobalt finding) and every
    case variant: only the exact (whitespace-folded) spelling certifies a supply."""
    keys = _registered_stock_name_keys()
    assert keys, "the material library declares name-keyed components"
    keys |= {"water", "Co", "CO", "Na2CO3", "sulfuric acid"}
    for seed, key in enumerate(sorted(keys)):
        bottle = _named_bottle(key)
        assert bottle.active_fraction_interval(f" {key} ", case_exact=True) is not None, key
        for v in _variants(key, seed):
            if collapse_material_name(v) == key:
                continue
            assert bottle.active_fraction_interval(v, case_exact=True) is None, (key, v)
            assert bottle.spec_view(v, case_exact=True) is None, (key, v)
    edge = _edge(_name_req("WAtEr"), _named_bottle("water"))
    assert edge is not None and edge.status is CapabilityStatus.UNKNOWN and not edge.commensurable


# =====================================================================================================================
# honest controls
# =====================================================================================================================

def test_control_water_spellings_still_resolve():
    water = next(r for r in HAZARD_REFS if r.name == "water")
    for spelling in ("water", "Water", "WATER", "  water "):
        assert hazards_for_named(spelling) is water, spelling
        assert catalyst_availability(spelling) is Availability.GROCERY, spelling
        assert structure_by_name(spelling).name == "water", spelling
    # a GHS record is reached by every spelling that certifies; a token the formula grammar claims ("AcID" = Ac+I+D)
    # gets nothing -- the same answer catalyst_availability gives that string
    for spelling in ("sulfuric acid", "Sulfuric acid", "SULFURIC ACID"):
        assert hazards_for_named(spelling).ghs_codes == ("H290", "H314"), spelling
    assert hazards_for_named("sulfuric AcID") is None
    assert catalyst_availability("sulfuric AcID") is None


def test_control_h2o_behaves_exactly_as_before():
    """Measured on the base tree 1fc9068 with the same calls (probe p_ctrl.py): no record, no tier, no registry label;
    the front door reads it as the formula H2O."""
    assert hazards_for_named("H2O") is None
    assert catalyst_availability("H2O") is None
    assert structure_by_name("H2O") is None
    receipt = resolve_identity("H2O").receipt
    assert receipt.resolved_kind.value == "FORMULA" and receipt.normalized == "H2O"


def test_control_the_synthetic_stream_disposition_witness_still_fits():
    a = _assess(_with(_dme(), *_witness_dispositions()))
    assert a.overall is CapabilityStatus.FIT and a.is_capability_fit, _statuses(a)


# =====================================================================================================================
# F7 -- procurement never vouches a typed identity by a display name that is not its name
# =====================================================================================================================

def _f7_route(name: str, envelope=()):
    route = _dme_with_h2so4(name=name)  # a typed CATALYST use, identity H2SO4
    if envelope:
        route = _with_catalysts(route, envelope)
    return _with(route, *_witness_dispositions())


def _f7_bench():
    return dc.replace(_exact_profile(frozenset({_AN, _HAZ})),
                      material_inventory=(_pure("methanol-pure", _METHANOL), _pure("h2so4-pure", _H2SO4)),
                      procurement=frozenset({Availability.GROCERY}))


@pytest.mark.parametrize("envelope", [(), ("water",)], ids=["use-only", "envelope-string-spelled-alike"])
def test_f7_a_display_name_does_not_vouch_for_its_identity(envelope):
    """Pre-fix FAILS: H2SO4 labelled "water" read as a GROCERY catalyst -- procurement FIT on a grocery-only bench."""
    route = _f7_route("water", envelope)
    assert compile_capability_requirements(route).procurement_catalysts == (("water", None),)
    a = _assess(route, _f7_bench())
    assert a.procurement.status is CapabilityStatus.BLOCKED and not a.is_capability_fit


def test_f7_control_the_honest_name_keeps_its_tier():
    route = _f7_route("sulfuric acid")
    assert compile_capability_requirements(route).procurement_catalysts == (("sulfuric acid", Availability.HARDWARE),)
    assert _assess(route, _f7_bench()).procurement.status is CapabilityStatus.BLOCKED  # HARDWARE, grocery bench
    wider = dc.replace(_f7_bench(), procurement=frozenset({Availability.GROCERY, Availability.HARDWARE}))
    assert _assess(route, wider).procurement.status is CapabilityStatus.FIT


def test_f7_an_identity_less_use_is_still_read_by_its_name():
    rows = compile_capability_requirements(
        _micro(_op(uses=(_use("water", ProcedureMaterialRole.CATALYST),)))).procurement_catalysts
    assert rows == (("water", Availability.GROCERY),)


# =====================================================================================================================
# F8 -- monotone: a covering typed use never deletes what the covered string's own name forces
# =====================================================================================================================

@pytest.mark.parametrize("name", ["sulfuric acid", "acetic acid", "formic acid"])
def test_f8_a_covered_string_keeps_its_name_forcing_categories(name):
    """Pre-fix FAILS: adding a typed CATALYST use spelled ``name`` whose identity is WATER under the envelope string
    ``name`` dropped HAZARDOUS -- more evidence, fewer categories (probe p20_monotone.py)."""
    base = _micro(catalysts=(name,))
    grown = _micro(_op(uses=(_use(name, ProcedureMaterialRole.CATALYST, _WATER),)), catalysts=(name,))
    base_cats, grown_cats = derive_waste(base)[0], derive_waste(grown)[0]
    assert _HAZ in base_cats and base_cats <= grown_cats, (base_cats, grown_cats)
    _cats, reasons, unresolved = derive_waste(grown)
    assert any("its own name carries sourced GHS" in r and "(A15)" in r for r in reasons), reasons
    # forcing only: the cover's empty-record residual obligation is NOT discharged by the name
    assert any(f"catalyst residual {name!r}" in u and "not consumed" in u for u in unresolved), unresolved


def test_f8_control_a_covered_string_with_no_forcing_record_adds_nothing():
    route = _with_catalysts(_dme_with_h2so4(name="catalyst q"), ("catalyst q",))
    _cats, reasons, _u = derive_waste(route)
    assert not any("(A15)" in r for r in reasons)


# =====================================================================================================================
# Residual -- L3 binds a USE_STREAM: no hazard record, no species-level ROUTED discharge
# =====================================================================================================================

@pytest.mark.parametrize("use", [_use("mystery wash", ProcedureMaterialRole.WASH),
                                 _use("tert-butylbenzene", ProcedureMaterialRole.WASH, _UNRECORDED_CAT)],
                         ids=["identity-less", "typed-unrecorded"])
def test_residual_a_routed_use_stream_of_an_unassessed_species_discharges_nothing(use):
    """Pre-fix FAILS: ROUTED(AQUEOUS_NEUTRAL) discharged the spent stream with no record behind it (probe
    p_res5_use_stream.py)."""
    route = _micro(_op(uses=(use,)))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    cats, reasons, unresolved = derive_waste(_with(route, _d(stream)))
    assert any(f"spent workup stream {use.name!r}" in u and "F49" in u for u in unresolved)
    assert any("no hazard record" in u and "(L3)" in u for u in unresolved)
    assert _AN not in cats and not any("discharged" in r for r in reasons)


def test_residual_control_a_recorded_species_stream_still_discharges():
    route = _micro(_op(uses=(_use("water", ProcedureMaterialRole.WASH, _WATER),)))
    stream = _subject_of(route, SubjectKind.USE_STREAM)
    cats, reasons, unresolved = derive_waste(_with(route, _d(stream)))
    assert not any("spent workup stream 'water'" in u for u in unresolved)
    assert _AN in cats and any("spent workup stream 'water'" in r and "discharged" in r for r in reasons)


def test_residual_route_level_the_waste_axis_falls_from_fit_to_unknown():
    """The DME witness + a WASH use of an unrecorded species + ROUTED(AQUEOUS_NEUTRAL) on its stream. Measured on
    1fc9068 (probe p_ctrl.py): waste FIT, overall UNKNOWN (containment/material catch the species elsewhere). Now the
    waste axis is UNKNOWN too -- the routing no longer discharges an unassessed stream."""
    base = _dme()
    ops = list(base.steps[0].envelope.procedure.operations)
    ops[0] = dc.replace(ops[0], material_uses=ops[0].material_uses
                        + (_use("tert-butylbenzene", ProcedureMaterialRole.WASH, _UNRECORDED_CAT, qty="5"),))
    r = _rendered(base, ops)
    r = _with(r, _d(_subject_of(r, SubjectKind.BYPRODUCT)), _d(_subject_of(r, SubjectKind.OP_STREAM)),
              _d(_subject_of(r, SubjectKind.RESIDUAL), DispositionValue.CONSUMED_COMPLETELY),
              _d(_subject_of(r, SubjectKind.USE_STREAM)))
    profile = dc.replace(_exact_profile(), material_inventory=(_pure("methanol-pure", _METHANOL),
                                                               _pure("tbb", _UNRECORDED_CAT)))
    a = _assess(r, profile)
    assert a.waste.status is CapabilityStatus.UNKNOWN and not a.is_capability_fit, _statuses(a)


def test_residual_the_op_stream_boundary_is_unchanged():
    """An OP_STREAM names no species: its SOURCE_QUOTED category stays the only evidence (S18 boundary)."""
    route = _micro(_op(OperationKind.FILTER))
    stream = _subject_of(route, SubjectKind.OP_STREAM)
    _c, _r, unresolved = derive_waste(_with(route, _d(stream)))
    assert not any("op #2 FILTER/OTHER leaves a spent stream" in u for u in unresolved)


def test_every_honest_spelling_still_resolves():
    """No table key's honest spelling lost its tier and no hazard record name lost its record (the fix only ever
    refuses a case variant)."""
    assert all(hazards_for_named(r.name) is r for r in HAZARD_REFS)
    assert all(catalyst_availability(ca._CASE_EXACT_SPELLING.get(k, k)) is not None
               for k in itertools.chain(ca._COMMODITY_BY_NAME, ca._CATALYST_TABLE))
    assert _maximal_profile(()).procurement == frozenset(Availability)
