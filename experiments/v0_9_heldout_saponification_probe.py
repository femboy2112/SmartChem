"""V0.9-HELDOUT-01: the held-out SAPONIFICATION genericity probe, graded against a BLIND oracle (Round V, Part VIII).

**I'm Mr. Meeseeks, look at me! I only use the PUBLIC door!** The oracle
(`docs/research/V0_9_RC_ROUND_V_HELDOUT_ORACLE_2026-09-28.md`, sha256 eb01d67c9b76…, written by Round-V Wave-A lane F
BEFORE any Round-V implementation agent saw a projected requirement) froze, blind, what an honest generic capability
compiler must say about a benign held-out procedure it was never fitted to. This harness:

1. AUTHORS that case -- the oracle's materials M1-M6, its stated amounts and adjectives -- as `ProcedureEvidence` +
   `ProcedureMaterialUse`s + one `ExperimentStep` through PUBLIC types only. It edits NOTHING under `smartchem/`; a
   compiler edit, a new identity or a new adjective to make this pass is an automatic FAIL (the P11 check greps for
   one).
2. COMPILES it with `compile_capability_requirements` and ASSESSES it under the oracle's two worlds -- (i) a fully
   stocked teaching lab (`research_lab()` + positively-declared matching stock) and (ii) a kitchen (`poor_man()` + a
   kitchen-like `custom()` bench, each with vodka / drain cleaner / table salt stock) -- plus the P5 "tempting stock"
   set (absolute ethanol, NaOH pellets, table salt, drain cleaner).
3. GRADES every oracle checklist item P1-P12: PASS = the correct typed projection OR an honest UNKNOWN/refusal;
   FAIL = a magic identity/adjective in the compiler, a silently dropped demand, or a certified FIT/BLOCK the oracle
   says must be UNKNOWN; DIVERGES = the verdict differs from the oracle's prediction for a reason traced to a
   documented law (reported, never hidden).

Honesty notes the results doc repeats: the case is SYNTHESIZED (the oracle says so; the nearest real page, MiraCosta
Chem 102 Exp. 8, has no ethanol) -- so `ProcedureEvidence.source` is `None` (no citation is invented) and readiness can
never reach PROCESS_SPECIFIED; every phase the case does not state is AUTHOR_INFERRED; "~5 mL" / "~10 mL" are not
exact, so their quantity is `None` (UNKNOWN), never a rounded guess. The balanced-equation VEHICLE: the SMILES layer
refuses ionic NaOH / sodium carboxylates and a mixture ("vegetable oil") has no single Molecule, so the ONE
`ExperimentStep` is the neutral hydrolysis analogue tristearin + 3 H2O -> glycerol + 3 stearic acid (a MODEL species
set, not the case's chemistry). Its two vehicle-only leaves (tristearin, water-as-reactant) are reported, and the
case verdicts are graded both RAW and with those two vehicle leaves removed.

Run:  .venv/bin/python experiments/v0_9_heldout_saponification_probe.py
"""
from __future__ import annotations

import ast
import dataclasses as dc
import hashlib
from pathlib import Path

from smartchem.capability.assess import assess
from smartchem.capability.enums import (
    CapabilityStatus,
    EquipmentCapability,
    MeasurementMethod,
    VentilationCapability,
    WasteCapability,
)
from smartchem.capability.presets import custom, poor_man, research_lab
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.constraints import PhysicalBounds
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.data.reagents import Availability
from smartchem.experiment.readiness import PROCESS_SPECIFIED, evaluate_route
from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep
from smartchem.experiment.stock import (
    MATERIAL_COMPONENT_SCHEMA,
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
)
from smartchem.material_spec import (
    CompositionConstraint,
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    MaterialSpecification,
    PhaseClaim,
    SaturationState,
    StateClaim,
    Tolerance,
)
from smartchem.procedure_evidence import (
    EvidenceField,
    OperationKind,
    OperationRole,
    ProcedureEvidence,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
)
from smartchem.process_constraints import Agitation, Attention, ProcessBounds
from smartchem.smiles import parse_smiles

_REPO = Path(__file__).resolve().parents[1]
_ORACLE = _REPO / "docs/research/V0_9_RC_ROUND_V_HELDOUT_ORACLE_2026-09-28.md"
_ORACLE_SHA256 = "eb01d67c9b761af3ae257f4cdf3c1ce119a500ccd1e78250ba9d6876c8ac95df"
_ARTIFACT = _REPO / "docs/research/V0_9_RC_ROUND_V_HELDOUT_PROBE_RESULTS_2026-09-28.md"
_CAPABILITY_DIR = _REPO / "smartchem/capability"

L = "synth-saponification (the oracle's SYNTHESIZED held-out case; no public source -- see the oracle §0)"

# -- the balanced-equation VEHICLE (model species; see the module docstring) ------------------------------------
TRISTEARIN = parse_smiles(
    "CCCCCCCCCCCCCCCCCC(=O)OCC(COC(=O)CCCCCCCCCCCCCCCCC)OC(=O)CCCCCCCCCCCCCCCCC")
STEARIC_ACID = parse_smiles("CCCCCCCCCCCCCCCCCC(=O)O")
GLYCEROL = parse_smiles("OCC(O)CO")
WATER = parse_smiles("O")
ETHANOL = parse_smiles("CCO")
_VEHICLE_ONLY_LEAVES = (TRISTEARIN, WATER)  # water is a REACTANT only in the vehicle (saponification uses OH-)


def _present(value, where: str) -> EvidenceField:
    return EvidenceField.present(value, f"{L} {where}")


# -- the case, authored (oracle §1 table + §3 pseudo-data, through the REAL public types) -------------------------
def build_uses() -> "dict[str, ProcedureMaterialUse]":
    """M1-M5 as typed uses. M6 (pH paper) has no role in the closed vocabulary -> it stays an untyped VERIFY-op
    material string (the oracle: 'no role in the vocabulary'), never forced into a role."""
    return {
        "M1": ProcedureMaterialUse(
            name="vegetable oil", role=ProcedureMaterialRole.SUBSTRATE, identity=None,  # a mixture: NO Molecule
            phase=PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED, "the case says only 'vegetable oil'"),
            quantity=None,  # "~5 mL": approximate -> not an exact StockQuantity -> UNKNOWN (never rounded to 5)
            evidence_source=f"{L} #1 '~5 mL vegetable oil'"),
        "M2": ProcedureMaterialUse(
            name="ethanol", role=ProcedureMaterialRole.SOLVENT, identity=ETHANOL, formulation="95%",
            phase=PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED, "the case says only '95% ethanol'"),
            quantity=StockQuantity.of("10", "mL"), evidence_source=f"{L} #1 '10 mL of 95% ethanol'",
            specification=MaterialSpecification(composition=CompositionConstraint(
                "0.95", "0.95", ConcentrationBasis.UNKNOWN, Tolerance.NOMINAL_UNSTATED_TOLERANCE,
                EvidenceKind.SOURCE_QUOTED, "'95%': basis (v/v? w/w?) and tolerance both UNSTATED by the case"))),
        "M3": ProcedureMaterialUse(
            name="sodium hydroxide", role=ProcedureMaterialRole.REACTANT, identity=None,  # ionic: no Molecule
            formulation="6 M ... (aq)",
            phase=PhaseClaim(Phase.AQUEOUS_SOLUTION, EvidenceKind.SOURCE_QUOTED, "the case writes '(aq)'"),
            quantity=StockQuantity.of("10", "mL"), evidence_source=f"{L} #1 '10 mL of 6 M NaOH(aq)'",
            specification=MaterialSpecification(
                composition=CompositionConstraint(
                    "6", "6", ConcentrationBasis.MOLAR, Tolerance.NOMINAL_UNSTATED_TOLERANCE,
                    EvidenceKind.SOURCE_QUOTED, "'6 M': an amount concentration, never a fraction"),
                states=(StateClaim(DilutionState.SOLUTION, EvidenceKind.SOURCE_QUOTED, "'(aq)'"),))),
        "M4": ProcedureMaterialUse(
            # salting-out agent: the closed ProcedureMaterialRole has NO precipitant/salting-out member. WASH is the
            # nearest; the misfit is RECORDED here (and as a 0.9.5 vocabulary item), never guessed away.
            name="sodium chloride", role=ProcedureMaterialRole.WASH, identity=None,
            formulation="saturated ... solution",
            phase=PhaseClaim(Phase.AQUEOUS_SOLUTION, EvidenceKind.AUTHOR_INFERRED,
                             "'solution' is stated, 'aqueous' is not"),
            quantity=StockQuantity.of("50", "mL"),
            evidence_source=f"{L} #3 '50 mL saturated NaCl solution' (ROLE MISFIT: a salting-out precipitant, not a "
                            "wash -- the closed vocabulary has no member for it)",
            specification=MaterialSpecification(states=(
                StateClaim(SaturationState.SATURATED, EvidenceKind.SOURCE_QUOTED, "'saturated' (temperature unstated)"),
                StateClaim(DilutionState.SOLUTION, EvidenceKind.SOURCE_QUOTED, "'solution'")))),
        "M5": ProcedureMaterialUse(
            # 'ice-cold' is a PROCESS demand (authored on the op's temperature), not a material specification
            name="water", role=ProcedureMaterialRole.RINSE, identity=WATER, phase=None,
            quantity=None,  # "~10 mL": approximate -> UNKNOWN
            evidence_source=f"{L} #5 'rinse with ~10 mL ice-cold water'"),
    }


def build_route() -> ExperimentRoute:
    u = build_uses()
    ops = (
        ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
                           materials=("vegetable oil", "ethanol", "sodium hydroxide"),
                           material_uses=(u["M1"], u["M2"], u["M3"]), locator=f"{L} #1"),
        ProcedureOperation(ordinal=2, kind=OperationKind.HOLD, role=OperationRole.REACTION,
                           apparatus=("water bath",),  # the case's own word; the exact bath T is UNSTATED
                           duration=_present(Interval(20, 30, "min"), "#2 'heat 20-30 min'"),
                           agitation=_present("stirring", "#2"), endpoint=_present("until homogeneous", "#2"),
                           locator=f"{L} #2"),
        ProcedureOperation(ordinal=3, kind=OperationKind.ADD, role=OperationRole.OTHER,
                           materials=("sodium chloride",), material_uses=(u["M4"],), locator=f"{L} #3 salting out"),
        ProcedureOperation(ordinal=4, kind=OperationKind.FILTER, role=OperationRole.OTHER,
                           apparatus=(),  # 'filter': the method (gravity vs vacuum) is UNSTATED -- never defaulted
                           locator=f"{L} #4 'collect the soap by filtration'"),
        ProcedureOperation(ordinal=5, kind=OperationKind.ADD, role=OperationRole.WASH, materials=("water",),
                           material_uses=(u["M5"],), temperature=_present("ice-cold", "#5"), locator=f"{L} #5"),
        ProcedureOperation(ordinal=6, kind=OperationKind.VERIFY, role=OperationRole.OTHER,
                           materials=("pH paper",), apparatus=(),  # M6: no MeasurementMethod represents it
                           endpoint=_present("lather; pH paper", "#6"), locator=f"{L} #6"),
    )
    unknown = EvidenceField.unknown()
    procedure = ProcedureEvidence(
        reaction_scope="held-out saponification (synthesized case)", source=None,  # no citation is invented
        scale=unknown, operations=ops, quench=unknown,
        workup_isolation=_present("collect the precipitated soap by filtration", "#4"),
        separation=unknown, wash=unknown, drying=unknown, purification=unknown,
        analytical_verification=_present("lather test; pH paper", "#6"),
        unresolved_omissions=("waste disposal", "glycerol fate", "total elapsed time", "filtration method",
                              "salting-out temperature", "95% basis"))
    step = ExperimentStep(STEP_SCHEMA, STEARIC_ACID, (TRISTEARIN, WATER, WATER, WATER),
                          (GLYCEROL, STEARIC_ACID, STEARIC_ACID, STEARIC_ACID), (),
                          ConditionEnvelope(procedure=procedure))
    return ExperimentRoute(ROUTE_SCHEMA, (step,))


# -- the oracle's stock worlds (every bottle declared by the bench = USER_DECLARED; nothing sourced for them) ------
def _ud(low: str, high: str, basis: ConcentrationBasis, note: str) -> IntervalEvidence:
    return IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=basis,
        inputs=(TypedInput("low", low, InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", high, InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity=f"held-out probe bench declaration: {note}")


def _bottle(material_id: str, components, phase: Phase, *, qty: str = "1000", unit: str = "mL",
            phase_declared: bool = True) -> StockMaterial:
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, material_id, material_id, tuple(components), phase,
        "held-out saponification probe bench declaration (USER_DECLARED)", quantity=StockQuantity.of(qty, unit),
        phase_evidence=EvidenceKind.USER_DECLARED if (phase_declared and phase is not Phase.UNKNOWN)
        else EvidenceKind.UNKNOWN)


def _unknown_name(name: str, role: str = "active", states=()) -> MaterialComponent:
    return MaterialComponent(MATERIAL_COMPONENT_SCHEMA, name, role, 0.0, 1.0, ConcentrationBasis.UNKNOWN, None,
                             tuple(states))


def lab_stock() -> "tuple[StockMaterial, ...]":
    """Oracle world (i): positively-declared stock matching the case's typed specs as closely as the stock types allow."""
    return (
        _bottle("vegetable oil", (_unknown_name("vegetable oil"),), Phase.LIQUID),
        _bottle("95% ethanol", (
            MaterialComponent.evidenced(ETHANOL, "active", _ud("0.95", "0.95", ConcentrationBasis.UNKNOWN,
                                                               "label '95%', basis unstated like the case")),
            _unknown_name("water", "balance")), Phase.LIQUID),
        # 6 M NaOH(aq): a MOLAR stock claim cannot be USER_DECLARED through the closed kernel registry (no molar input
        # unit) -- carried with NO evidence (UNKNOWN strength): a known 0.9.5 representation gap, recorded, not patched.
        _bottle("6 M NaOH(aq)", (MaterialComponent(
            MATERIAL_COMPONENT_SCHEMA, "sodium hydroxide", "active", 6.0, 6.0, ConcentrationBasis.MOLAR, None,
            (StateClaim(DilutionState.SOLUTION, EvidenceKind.USER_DECLARED, "bench-made 6 M solution"),)),),
            Phase.AQUEOUS_SOLUTION),
        _bottle("saturated NaCl(aq)", (_unknown_name("sodium chloride", states=(
            StateClaim(SaturationState.SATURATED, EvidenceKind.USER_DECLARED, "excess solid present"),
            StateClaim(DilutionState.SOLUTION, EvidenceKind.USER_DECLARED, "brine"))),
            _unknown_name("water", "balance")), Phase.AQUEOUS_SOLUTION),
        _bottle("distilled water", (MaterialComponent.evidenced(
            WATER, "active", _ud("1", "1", ConcentrationBasis.MASS_FRACTION, "distilled water")),), Phase.LIQUID),
    )


def kitchen_stock() -> "tuple[StockMaterial, ...]":
    """Oracle world (ii): vodka (40% v/v), drain-cleaner NaOH (undeclared composition), table salt, kitchen oil, tap
    water."""
    return (
        _bottle("kitchen vegetable oil", (_unknown_name("vegetable oil"),), Phase.LIQUID),
        _bottle("vodka 40% ABV", (
            MaterialComponent.evidenced(ETHANOL, "active", _ud("0.40", "0.40", ConcentrationBasis.VOLUME_FRACTION,
                                                               "label 40% ABV (alcohol by volume)")),
            _unknown_name("water", "balance")), Phase.LIQUID, qty="750"),
        _bottle("drain cleaner", (_unknown_name("sodium hydroxide"),), Phase.UNKNOWN, qty="500", unit="g"),
        _bottle("table salt", (_unknown_name("sodium chloride"),), Phase.SOLID, qty="500", unit="g"),
        _bottle("tap water", (MaterialComponent.unknown_molecule(WATER, "active"),), Phase.LIQUID, qty="10000"),
    )


def tempting_stock() -> "tuple[StockMaterial, ...]":
    """P5: every 'higher grade / other form' substitution the oracle forbids from certifying."""
    return (
        _bottle("absolute ethanol", (MaterialComponent.evidenced(
            ETHANOL, "active", _ud("0.995", "1", ConcentrationBasis.VOLUME_FRACTION, "absolute ethanol >=99.5% v/v")),),
            Phase.LIQUID),
        _bottle("NaOH pellets", (MaterialComponent.evidenced(
            "sodium hydroxide", "active", _ud("0.97", "1", ConcentrationBasis.MASS_FRACTION, "pellets >=97% w/w")),),
            Phase.SOLID, qty="500", unit="g"),
        _bottle("table salt", (_unknown_name("sodium chloride"),), Phase.SOLID, qty="500", unit="g"),
        _bottle("drain cleaner", (_unknown_name("sodium hydroxide"),), Phase.UNKNOWN, qty="500", unit="g"),
    )


def kitchen_custom(stock) -> "object":
    """A kitchen-like Custom bench: a stove, a pot water bath, ice, a coffee filter (gravity), a thermometer, a
    kitchen scale; OUTDOOR ventilation, NO containment, grocery/pharmacy/hardware shops, no budget declared."""
    return custom(
        profile_id="kitchen-saponification-probe", material_inventory=stock,
        equipment=frozenset({EquipmentCapability.CONTROLLED_HEATING, EquipmentCapability.WATER_BATH,
                             EquipmentCapability.ICE_BATH, EquipmentCapability.REACTION_VESSEL,
                             EquipmentCapability.GRAVITY_FILTRATION, EquipmentCapability.THERMOMETER,
                             EquipmentCapability.BALANCE}),
        physical_bounds=PhysicalBounds.of(min_temperature_k=273.15, max_temperature_k=473.15,
                                          min_pressure_atm=1.0, max_pressure_atm=1.5),
        process_bounds=ProcessBounds.of(max_step_minutes=240.0, max_total_minutes=480.0, max_active_minutes=240.0,
                                        allowed_attention=tuple(Attention), min_check_interval_minutes=5.0,
                                        allowed_agitation=tuple(Agitation)),
        ventilation=frozenset({VentilationCapability.OUTDOOR}), measurement=frozenset({MeasurementMethod.MASS}),
        procurement=frozenset({Availability.GROCERY, Availability.PHARMACY, Availability.HARDWARE}),
        provenance="held-out saponification probe: a synthetic kitchen bench (declared world, not a preset)")


# -- reading the assessment through its PUBLIC output --------------------------------------------------------------
def _material_line(assessment, label: str) -> str:
    for reason in assessment.material.reasons:
        if reason.startswith("material: ") and f" {label} -- quantity" in reason:
            return reason
    return ""


def _bottle_status(line: str, bottle_id: str) -> "str | None":
    """The per-bottle edge verdict ``<id>: <STATUS>:`` the material axis prints for one requirement, or None."""
    marker = f"{bottle_id}: "
    if marker not in line:
        return None
    rest = line.split(marker, 1)[1]
    return rest.split(":", 1)[0].strip()


def _requirement(reqs, name: str):
    return next((r for r in reqs.material if r.name == name), None)


def _case_reqs(reqs):
    """The compiled requirements with ONLY the two vehicle-only leaves removed (documented in the module docstring)."""
    vehicle = {m.canonical() for m in _VEHICLE_ONLY_LEAVES}

    def is_vehicle(r) -> bool:
        return r.role == "reactant (leaf input)" and r.identity is not None and r.identity.canonical() in vehicle

    return dc.replace(reqs, material=tuple(r for r in reqs.material if not is_vehicle(r)))


def _code_literal_hits(words: "tuple[str, ...]") -> "list[str]":
    """P11: every CODE constant (string or number, docstrings excluded) under smartchem/capability/ that carries a
    case word -- the genericity grep, done on the AST so a comment/docstring mention is not mistaken for a rule."""
    hits = []
    for path in sorted(_CAPABILITY_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    docstrings.add(id(first.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and id(node) not in docstrings:
                text = str(node.value).casefold()
                for word in words:
                    w = word.casefold()
                    if (isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
                            and w.replace(".", "", 1).isdigit()):
                        if float(node.value) in (float(w), float(w) / 100):
                            hits.append(f"{path.name}:{node.lineno} number {node.value!r}")
                    elif isinstance(node.value, str) and w in text:
                        hits.append(f"{path.name}:{node.lineno} {word!r} in {node.value[:60]!r}")
    return hits


def _raw_grep(words) -> "dict[str, list[str]]":
    """Raw substring hits (comments and docstrings included) as ``file:line`` per word -- reported, not graded (the AST
    scan above is the grade; a raw hit is usually prose, e.g. 'ethanol' inside 'methanol')."""
    hits: "dict[str, list[str]]" = {}
    for word in words:
        for path in sorted(_CAPABILITY_DIR.glob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if word.casefold() in line.casefold():
                    hits.setdefault(word, []).append(f"{path.name}:{lineno}")
    return hits


_P11_WORDS = ("saponif", "vegetable oil", "sodium hydroxide", "naoh", "soap", "glycerol", "vodka", "ethanol",
              "saturated", "95", "drain cleaner", "table salt", "lather", "ph paper", "litmus")


def run() -> "tuple[list, dict]":
    oracle_sha = hashlib.sha256(_ORACLE.read_bytes()).hexdigest()
    route = build_route()
    reqs = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    case = _case_reqs(reqs)
    lab = research_lab(material_inventory=lab_stock())
    pm = poor_man(material_inventory=kitchen_stock())
    kit = kitchen_custom(kitchen_stock())
    tempt = research_lab(material_inventory=tempting_stock())
    a = {
        "lab raw": assess(lab, reqs, readiness), "lab": assess(lab, case, readiness),
        "poor_man raw": assess(pm, reqs, readiness), "poor_man": assess(pm, case, readiness),
        "kitchen raw": assess(kit, reqs, readiness), "kitchen": assess(kit, case, readiness),
        "tempting": assess(tempt, case, readiness),
    }
    grades: list = []

    def grade(pid: str, verdict: str, claim: str, evidence: str) -> None:
        grades.append((pid, verdict, claim, evidence))
        print(f"  [{verdict}] {pid}: {claim} -- {evidence}", flush=True)

    grade("P0", "PASS" if oracle_sha == _ORACLE_SHA256 else "FAIL", "the oracle is the frozen blind prediction",
          f"sha256 {oracle_sha}")

    etoh, naoh = _requirement(reqs, "ethanol"), _requirement(reqs, "sodium hydroxide")
    brine, oil = _requirement(reqs, "sodium chloride"), _requirement(reqs, "vegetable oil")
    rinse = next((r for r in reqs.material if r.name == "water" and r.role.startswith("procedure material")), None)

    # P1 -- "95%" keeps an UNSTATED basis; against vodka (a v/v stock) it is basis-incommensurable -> UNKNOWN.
    comp = etoh.specification.composition if etoh else None
    ok = comp is not None and comp.basis is ConcentrationBasis.UNKNOWN and comp.low == "0.95"
    grade("P1", "PASS" if ok else "FAIL", "95% basis surfaces as UNSTATED (UNKNOWN), not VOLUME_FRACTION",
          f"projected composition {comp.low if comp else None}..{comp.high if comp else None} "
          f"basis={comp.basis.value if comp else None} tolerance={comp.tolerance.value if comp else None}")

    # P2 -- 6 M is a MOLAR amount concentration, carried and never converted.
    c3 = naoh.specification.composition if naoh else None
    lab_naoh = _bottle_status(_material_line(a["lab"], "sodium hydroxide"), "6 M NaOH(aq)")
    ok = c3 is not None and c3.basis is ConcentrationBasis.MOLAR and (c3.low, c3.high) == ("6", "6") \
        and lab_naoh in ("UNKNOWN",)
    grade("P2", "PASS" if ok else "FAIL", "6 M is carried on a MOLAR basis and never converted",
          f"projected {c3.low if c3 else None} {c3.basis.value if c3 else None}; vs the lab's declared 6 M NaOH(aq) "
          f"bottle -> edge {lab_naoh} (a MOLAR stock claim has no certifying kernel -- UNKNOWN, never FIT)")

    # P3 -- "saturated" is a STATE with no number.
    sat = brine.specification if brine else None
    ok = sat is not None and sat.composition is None and any(
        s.state is SaturationState.SATURATED for s in sat.states)
    grade("P3", "PASS" if ok else "FAIL", "'saturated' is carried as a state, with no number",
          f"composition={None if sat is None else sat.composition}; states="
          f"{[] if sat is None else [s.state.value for s in sat.states]}")

    # P4 -- vegetable oil is name-only (identity None) and never FIT at structure strength.
    lab_oil = _bottle_status(_material_line(a["lab"], "vegetable oil"), "vegetable oil")
    kit_oil = _bottle_status(_material_line(a["kitchen"], "vegetable oil"), "kitchen vegetable oil")
    ok = oil is not None and oil.identity is None and lab_oil != "FIT" and kit_oil != "FIT"
    grade("P4", "PASS" if ok else "FAIL", "vegetable oil has identity None and is never FIT at structure strength",
          f"requirement identity={None if oil is None else oil.identity}, key=name '{None if oil is None else oil.name}'; "
          f"lab edge {lab_oil}, kitchen edge {kit_oil}")

    # P5 -- absolute ethanol / NaOH pellets / table salt / drain cleaner never FIT.
    subs = {
        "absolute ethanol -> 95% ethanol": _bottle_status(_material_line(a["tempting"], "ethanol"), "absolute ethanol"),
        "NaOH pellets -> 6 M NaOH(aq)": _bottle_status(_material_line(a["tempting"], "sodium hydroxide"), "NaOH pellets"),
        "drain cleaner -> 6 M NaOH(aq)": _bottle_status(_material_line(a["tempting"], "sodium hydroxide"),
                                                         "drain cleaner"),
        "table salt -> saturated NaCl": _bottle_status(_material_line(a["tempting"], "sodium chloride"), "table salt"),
    }
    ok = all(v is not None and v != "FIT" for v in subs.values())
    grade("P5", "PASS" if ok else "FAIL", "absolute ethanol / pellets / table salt / drain cleaner are all non-FIT",
          "; ".join(f"{k}: {v}" for k, v in subs.items()))

    # P6 -- vodka is UNKNOWN (BLOCKED only if v/v had been source-authored).
    vodka = _bottle_status(_material_line(a["kitchen"], "ethanol"), "vodka 40% ABV")
    grade("P6", "PASS" if vodka == "UNKNOWN" else "FAIL", "vodka is UNKNOWN (the case's basis is unstated)",
          f"kitchen edge vodka -> 95% ethanol: {vodka}")

    # P7 -- the spent filtrate is never AQUEOUS_NEUTRAL; glycerol's fate stays UNKNOWN.
    cats = reqs.waste.categories
    glycerol_open = [u for u in reqs.waste.unresolved if "C3H8O3" in u or "glycerol" in u.casefold()]
    ok = WasteCapability.AQUEOUS_NEUTRAL not in cats and bool(glycerol_open) and bool(reqs.waste.unresolved)
    grade("P7", "PASS" if ok else "FAIL", "spent filtrate is not AQUEOUS_NEUTRAL, glycerol is UNKNOWN",
          f"categories={sorted(c.value for c in cats)}; {len(reqs.waste.unresolved)} unresolved obligations, glycerol: "
          f"{glycerol_open[0][:140] if glycerol_open else 'MISSING'}")

    # P8 -- the filtration method is not defaulted.
    filt = {EquipmentCapability.GRAVITY_FILTRATION, EquipmentCapability.VACUUM_FILTRATION} & reqs.equipment
    filter_unread = [u for u in reqs.equipment_unrecognized if "FILTER" in u]
    ok = not filt and bool(filter_unread)
    grade("P8", "PASS" if ok else "FAIL", "the filtration method is not defaulted",
          f"filtration capability demanded: {sorted(c.value for c in filt) or 'none'}; unread: {filter_unread}")

    # P9 -- whole-process duration is a lower bound + UNKNOWN, never collapsed to the 30-min hold.
    proc_statuses = {k: a[k].process.status.value for k in ("lab", "poor_man", "kitchen")}
    ok = all(s == "UNKNOWN" for s in proc_statuses.values())
    grade("P9", "PASS" if ok else "FAIL", "the whole-process duration is a lower bound / UNKNOWN",
          f"process axis {proc_statuses}; process record per step = {list(reqs.process)}; kitchen reasons: "
          f"{[r for r in a['kitchen'].process.reasons if 'record' in r or 'coverage' in r or 'workup' in r][:2]}")

    # P10 -- overall verdict UNKNOWN in the lab world; the kitchen world is reported with its decisive axis.
    lab_overall = a["lab"].overall.value
    kit_overall = {k: a[k].overall.value for k in ("poor_man", "kitchen")}
    kit_blocks = {k: sorted(ax for ax in ("material", "equipment", "physical", "process", "containment",
                                          "measurement", "waste", "procurement", "monetary")
                            if getattr(a[k], ax).status is CapabilityStatus.BLOCKED) for k in ("poor_man", "kitchen")}
    only_containment = all(v == ["containment"] for v in kit_blocks.values())
    ethanol_ghs = any("ethanol" in r and "GHS" in r for r in a["kitchen"].containment.reasons)
    if lab_overall == "UNKNOWN" and all(v == "UNKNOWN" for v in kit_overall.values()):
        verdict = "PASS"
    elif (lab_overall == "UNKNOWN" and all(v in ("UNKNOWN", "BLOCKED") for v in kit_overall.values())
          and only_containment and ethanol_ghs):
        verdict = "DIVERGES (lawful)"
    else:
        verdict = "FAIL"
    grade("P10", verdict, "the overall verdict is UNKNOWN in both worlds",
          f"lab {lab_overall}; kitchen {kit_overall}; BLOCKED axes {kit_blocks}; the containment BLOCK is the "
          f"Round-III D9 law 'a sourced GHS record forces FUME_HOOD' firing on the case's OWN ethanol (H225/H319): "
          f"{ethanol_ghs}")

    # P11 -- no case literal in the compiler's code.
    hits = _code_literal_hits(_P11_WORDS)
    grade("P11", "PASS" if not hits else "FAIL", "no compiler CODE literal names the case's species/adjectives",
          f"AST code-constant hits: {hits or 'none'}; raw text counts (comments/docstrings included): "
          f"{_raw_grep(_P11_WORDS)} (each a comment/docstring line, not decision logic)")

    # P12 -- pH / lather never mapped to MASS / MELTING_POINT / IR.
    verify_unread = [u for u in reqs.measurement_unrecognized if "VERIFY" in u or "endpoint" in u]
    ok = not reqs.measurement and bool(verify_unread) and \
        all(a[k].measurement.status is CapabilityStatus.UNKNOWN for k in ("lab", "kitchen"))
    grade("P12", "PASS" if ok else "FAIL", "pH/lather are not mapped to MASS/MP/IR",
          f"measurement methods demanded: {sorted(m.value for m in reqs.measurement) or 'none'}; unread: "
          f"{verify_unread}; lab measurement {a['lab'].measurement.status.value}")

    ctx = {"route": route, "reqs": reqs, "case": case, "readiness": readiness, "a": a, "oracle_sha": oracle_sha,
           "rinse": rinse}
    return grades, ctx


def _axis_table(a: dict) -> "list[str]":
    axes = ("material", "equipment", "physical", "process", "containment", "ventilation", "measurement", "waste",
            "procurement", "attention_care", "monetary")
    cols = ("lab raw", "lab", "poor_man raw", "poor_man", "kitchen raw", "kitchen", "tempting")
    lines = ["| axis | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for ax in axes:
        lines.append(f"| {ax} | " + " | ".join(getattr(a[c], ax).status.value for c in cols) + " |")
    lines.append("| **overall** | " + " | ".join(a[c].overall.value for c in cols) + " |")
    return lines


def render(grades: list, ctx: dict) -> str:
    reqs, a = ctx["reqs"], ctx["a"]
    counts = {v: sum(1 for g in grades if g[1] == v) for v in ("PASS", "DIVERGES (lawful)", "FAIL")}
    lines = [
        "# Round V (X-high) -- held-out SAPONIFICATION genericity probe: results vs the BLIND oracle",
        "",
        "Generated by `.venv/bin/python experiments/v0_9_heldout_saponification_probe.py` (writes this file). Oracle: "
        f"`docs/research/V0_9_RC_ROUND_V_HELDOUT_ORACLE_2026-09-28.md`, sha256 `{ctx['oracle_sha']}` (frozen by Wave-A "
        "lane F before any Round-V implementation agent saw a projected requirement; preserved byte-identical).",
        "",
        "**Genericity rule held: nothing under `smartchem/` was edited for this probe** -- no identity, no adjective, no "
        "resolver string, no role. The case is authored through public types only; every gap it exposes is recorded "
        "as a 0.9.5 item below, never patched.",
        "",
        "## Grades (P0 = oracle integrity; P1-P12 = the oracle's checklist)",
        "",
        f"**{counts['PASS']} PASS, {counts['DIVERGES (lawful)']} DIVERGES (lawful), {counts['FAIL']} FAIL.**",
        "",
        "| item | grade | oracle claim | evidence (real compiler output) |",
        "|---|---|---|---|",
    ]
    for pid, verdict, claim, evidence in grades:
        lines.append(f"| {pid} | {verdict} | {claim} | {evidence.replace('|', '/')} |")
    lines += [
        "",
        "## Authoring (honesty notes)",
        "",
        "* **Synthesized case.** No public source matches it (the oracle §0), so `ProcedureEvidence.source=None` -- "
        "no citation is invented -- and readiness is "
        f"`{ctx['readiness'].tier}` (never PROCESS_SPECIFIED: the HARD LAW caps every verdict at UNKNOWN).",
        "* **Phases.** Only M3's `(aq)` is SOURCE_QUOTED; M1/M2/M4 phases are AUTHOR_INFERRED (the case never states "
        "them); M5 carries no phase (the case states none). D18 then refuses to let an inferred phase certify.",
        "* **Quantities.** '~5 mL' (M1) and '~10 mL' (M5) are approximate: `quantity=None` -> `QuantityDemand` UNKNOWN, "
        "never rounded to an exact 5 / 10.",
        "* **M4 role misfit (recorded).** The salting-out brine precipitates the product; the closed "
        "`ProcedureMaterialRole` has no precipitant/salting-out member, so it is authored as WASH with the misfit written "
        "into its `evidence_source`. Never REACTANT.",
        "* **M6 pH paper.** No role and no `MeasurementMethod` represent it: it stays an untyped VERIFY-op material "
        "string (D13 -> an unresolved material requirement) with a prose endpoint (D16 -> an unread measurement demand).",
        "* **'water bath'.** Authored with the case's own words; the closed apparatus resolver does not table the bare "
        "string (it knows 'steam bath' / '250 mL beaker (warm water bath)'), so it fails closed to an unread equipment "
        "demand -- the resolver was NOT extended for the probe.",
        "* **Vehicle.** The ONE `ExperimentStep` is tristearin + 3 H2O -> glycerol + 3 stearic acid (a neutral model: "
        "the SMILES layer refuses ionic NaOH/carboxylates and a mixture has no Molecule). Its vehicle-only leaves "
        "(tristearin; water-as-reactant) are graded RAW and removed in the `lab` / `poor_man` / `kitchen` columns "
        "(`dataclasses.replace` on the compiled requirements -- the only post-processing the harness does, and it only "
        "REMOVES the two vehicle leaves). Glycerol (the case's own byproduct) is kept.",
        "",
        "## Re-run on the D24 tree (post-Wave-C′ amendment, audit doc §7.5)",
        "",
        "Re-graded after the D24 fix batch landed: **no grade moved and no per-axis verdict moved** (identical table "
        "below). D24 only ADDED unread-demand reasons the case already failed closed on: D24.1 (the "
        "`analytical_verification` text 'lather test; pH paper' is not the canonical rendering of the VERIFY ops' typed "
        "methods -> measurement unread; the `workup_isolation` summary is not the canonical rendering of its realizing "
        "op -> process unread). D24.3 / D24.4 / D24.5 / D24.6 / D24.16 / D24.17 do not touch this case (no medium, no MIX "
        "op, no state-only commensurable edge, a single step, no 'distillation apparatus', a procedure-bearing step). "
        "P11's raw-text hits are prose lines (listed with file:line in the P11 row); the AST scan of decision logic finds "
        "no case literal.",
        "",
        "## Per-axis verdicts",
        "",
        "`lab` = research_lab() + oracle world (i) stock; `poor_man` / `kitchen` = poor_man() / a kitchen-like custom() "
        "bench + oracle world (ii) stock; `tempting` = research_lab() + ONLY the four P5 substitution bottles (so the species "
        "it does not carry -- the oil, the rinse water -- BLOCK as absent; only its substitution EDGES are graded, in P5); "
        "`raw` = with the two vehicle-only leaves.",
        "",
        *_axis_table(a),
        "",
        "## Compiled requirement projection (the case's typed materials, verbatim from `compile_capability_requirements`)",
        "",
        "| requirement | role | identity | phase | quantity | specification |",
        "|---|---|---|---|---|---|",
    ]
    for r in reqs.material:
        phase = "None" if r.phase is None else f"{r.phase.phase.value} ({r.phase.evidence.value})"
        spec = r.specification
        spec_txt = "; ".join(filter(None, (
            f"composition {spec.composition.low}..{spec.composition.high} {spec.composition.basis.value} "
            f"{spec.composition.tolerance.value} ({spec.composition.evidence.value})" if spec.composition else "",
            ", ".join(f"{s.state.value} ({s.evidence.value})" for s in spec.states),
            ", ".join(f"unresolved: {t}" for t in spec.unresolved_terms)))) or "empty"
        ident = "None (name-keyed)" if r.identity is None else repr(r.identity)
        lines.append(f"| {r.name or r.label} | {r.role} | {ident} | {phase} | {r.quantity.render()} | "
                     f"{spec_txt.replace('|', '/')} |")
    lines += [
        "",
        f"Waste: categories `{sorted(c.value for c in reqs.waste.categories)}`, {len(reqs.waste.unresolved)} unresolved "
        f"obligations. Equipment demanded `{sorted(e.value for e in reqs.equipment)}`, unread "
        f"`{list(reqs.equipment_unrecognized)}`. Measurement demanded `{sorted(m.value for m in reqs.measurement)}`, "
        f"unread `{list(reqs.measurement_unrecognized)}`. Physical unread `{list(reqs.physical_unresolved)}`. Process "
        f"unread `{list(reqs.process_unresolved)}`.",
        "",
        "## Oracle divergences (reported, not hidden)",
        "",
        "* **M2 / 95% ethanol against the lab's matching '95%' bottle is UNKNOWN, not the oracle's world-(i) FIT.** Both "
        "sides carry an UNSTATED basis, and F68 (Round V D4) forbids an unknown basis from certifying anything -- "
        "stricter than the oracle, never looser (an honest UNKNOWN).",
        "* **M3 / 6 M NaOH(aq) against the lab's 6 M bottle is UNKNOWN, not FIT.** The closed kernel registry has no "
        "MOLAR input unit, so a bench cannot USER_DECLARE a molar concentration with certifying evidence (a known "
        "representation gap).",
        "* **Containment requires FUME_HOOD** (the oracle: 'the compiler must not invent FUME_HOOD'). The fume hood is "
        "not invented from an adjective: the Round-III D9 law maps ANY sourced GHS record to FUME_HOOD, and the case's "
        "own ethanol carries H225/H319. The containment vocabulary is `{FUME_HOOD}` only; the oracle's "
        "'corrosive-handling/PPE' and 'ventilation for a heated flammable' have no representation (ventilation is a "
        "RESERVED axis). Hence the kitchen worlds BLOCK on containment (P10 DIVERGES, lawfully -- the oracle's own "
        "world-(ii) containment row allows 'UNKNOWN or BLOCKED per profile').",
        "* **NaOH pellets against 6 M NaOH(aq) is a BLOCKED edge** (the oracle: 'UNKNOWN or PREPROCESSING_REQUIRED ... "
        "not BLOCKED either, because it is not provably impossible'). Both sides certify their phase (the case's `(aq)` "
        "is SOURCE_QUOTED; the bench USER_DECLARES its pellets SOLID), so D18 certifies a phase VIOLATION: the bottle "
        "AS-IS is not the required material. The compiler has no preprocessing transform (dissolve to a molar target), "
        "so it cannot say 'usable after preparation' -- a false-BLOCK risk in the SAFE direction (never a false FIT; P5 "
        "only forbids FIT). Here another bottle (drain cleaner, phase undeclared) keeps the requirement UNKNOWN; with "
        "pellets alone it would BLOCK. Recorded as 0.9.5 item 8.",
        "* **The filtration disjunction** ('any filtration') is not representable: the FILTER op names no apparatus, so "
        "equipment reads UNKNOWN (no default; P8 PASS) rather than FIT-on-either.",
        "",
        "## 0.9.5 items this probe exposes (recorded, never patched here)",
        "",
        "1. `ProcedureMaterialRole` has no PRECIPITANT / SALTING_OUT member (M4 authored as WASH + recorded misfit).",
        "2. No carrier for an APPROXIMATE quantity ('~5 mL'): `StockQuantity` is exact-only, so the honest value is None.",
        "3. MOLAR (and w/v) stock claims have no certifying kernel input unit (6 M NaOH(aq) can never be USER_DECLARED).",
        "4. No disjunctive equipment requirement ('any filtration') and the apparatus resolver does not table the bare "
        "'water bath'.",
        "5. No `MeasurementMethod` / typed endpoint carrier for pH paper / litmus / lather (the D16 endpoint carrier).",
        "6. Containment vocabulary is `{FUME_HOOD}` only (no corrosive-handling / PPE), and ventilation is RESERVED.",
        "7. A mixture substrate (vegetable oil) has no Molecule, so a balanced step needs a model species; the leaf "
        "requirement it creates cannot be matched by a name-keyed bottle (F44 keeps structure and name keys apart) -- "
        "the vehicle-leaf BLOCK in the `raw` columns.",
        "8. No PREPROCESSING edge status (dissolve / dilute / saturate a declared solid): a certified phase mismatch "
        "BLOCKS an edge that preparation could satisfy (the 1.0 program §4.3 MaterialBucket 'preprocessing needed before "
        "use' is not modelled).",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("held-out saponification probe vs the blind oracle (P0-P12):")
    grades, ctx = run()
    _ARTIFACT.write_text(render(grades, ctx), encoding="utf-8")
    fails = [g for g in grades if g[1] == "FAIL"]
    print(f"\n{sum(1 for g in grades if g[1] == 'PASS')} PASS, "
          f"{sum(1 for g in grades if g[1].startswith('DIVERGES'))} DIVERGES (lawful), {len(fails)} FAIL "
          f"[wrote {_ARTIFACT}]")
    if ctx["readiness"].tier == PROCESS_SPECIFIED:
        print("NOTE: readiness reached PROCESS_SPECIFIED on an unsourced synthesized case -- investigate", flush=True)
        return 1
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
