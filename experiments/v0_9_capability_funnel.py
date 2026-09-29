"""V0.9-FUNNEL-01: the capability compiler funnel + per-axis census + profile DIVERGENCE (Round V X-high).

**Ooh yeah, a census! Look at me, I count things HONESTLY!** Same discipline as `v0_8_readiness_funnel.py`: report
the REAL numbers the real code produces over the REAL forcing corpus, and never reduce the denominator to the pretty
cases. The corpus is every route `smartchem.experiment.routes.search_routes` returns for the five forcing-corpus
targets (isopentyl acetate, aspirin, paracetamol, methyl salicylate, retro-Diels-Alder), and every capability
context is reported INDEPENDENTLY:

* ``no_profile`` -- capability NOT_REQUESTED (the ordinary ``smartchem plan TARGET`` caller: no assumed bench).
  Nothing is assessed; the row exists so "routes returned" and the PROCESS_SPECIFIED count are shown next to the
  assessed contexts.
* ``research_lab()`` / ``poor_man()`` -- the two named presets (the whole closed preset registry).
* ``isopentyl_capability_fit_bench()`` -- the FULLY-DECLARED Custom bench (stocks the whole isopentyl procedure).
* ``custom_undeclared`` -- ``custom(profile_id=...)`` with NOTHING declared: the fail-closed control. A bench that
  declares nothing must certify nothing.

Four complementary views, per context:

1. **The cumulative FUNNEL** (``routes returned -> PROCESS_SPECIFIED -> assessment requested -> <axis> fit ... ->
   CAPABILITY_FIT``): a route survives a stage only if it survived every stage before it AND this one.
2. **The per-axis CENSUS**: for EVERY one of the 11 `CapabilityAssessment` axes plus ``overall``, the FULL
   ``FIT``/``BLOCKED``/``UNKNOWN``/``NOT_APPLICABLE``/``UNCONSTRAINED`` breakdown over EVERY route -- denominator
   NEVER narrowed by the funnel.
3. **The DIVERGENCE matrix** (the canonical 0.9 exit-gate evidence: "meaningful divergence among ResearchLab,
   PoorMan and Custom on the same chemistry, with justified capability outcomes"): for every route and every axis on
   which research_lab / poor_man / the Custom bench disagree, the three statuses and each profile's DECISIVE reason
   string, verbatim.
4. **Movement vs the Round-IV run** (tip `4b8f8c2`, 86/86 properties -- the last committed revision of the results
   file, BEFORE every Round-V change D1-D19) -- every census cell that moved, so a reviewer can audit each movement
   against a Round-V law (audit doc §3 / §7.2).

`search_routes` takes no profile, so "routes returned" / PROCESS_SPECIFIED are identical across contexts BY
CONSTRUCTION here; search noninterference on the real SERVICE path (semantic_digest, search receipt, candidate
order under every profile) is proven separately (audit doc §7.1, lane A-WIRE).

**Zero CAPABILITY_FIT is the expected, honest outcome** (the Round-V zero-FIT theorem, audit doc §7.2 D17: every
PROCESS_SPECIFIED route carries an unresolved spent stream, every leaf an unsized demand or an untyped residual, and
no evidence type can discharge a waste stream yet). A FIT here would be a finding, not a success.

Run:  .venv/bin/python experiments/v0_9_capability_funnel.py
"""
from __future__ import annotations

from pathlib import Path

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import assess
from smartchem.capability.enums import CapabilityStatus
from smartchem.capability.presets import custom, isopentyl_capability_fit_bench, poor_man, research_lab
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.experiment import routes as rt
from smartchem.experiment.readiness import PROCESS_SPECIFIED, evaluate_route
from smartchem.identity_parse import InputKind, resolve_target

_ARTIFACT = Path(__file__).with_name("V0_9_CAPABILITY_FUNNEL_RESULTS.md")

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

#: every axis `CapabilityAssessment` carries, in the SAME fixed order `CapabilityAssessment.axes` uses.
_ALL_AXES = (
    "material", "equipment", "physical", "process", "containment", "ventilation", "measurement",
    "waste", "procurement", "attention_care", "monetary",
)
#: the axes that GATE the overall fold (ventilation is a reserved NOT_APPLICABLE axis and attention_care is
#: informational -- both census-only).
_FUNNEL_AXES = (
    "material", "equipment", "physical", "process", "containment", "measurement", "waste", "procurement",
    "monetary",
)
#: the funnel's stage order.
_STAGES = (
    "routes returned", "PROCESS_SPECIFIED", "assessment requested",
    *(f"{axis} fit" for axis in _FUNNEL_AXES[:-1]), "monetary assessed", "CAPABILITY_FIT",
)
#: the membership axes whose verdict is a subset check of a declared profile set (dominance law, property P-i).
_MEMBERSHIP_AXES = (
    ("equipment", "equipment"),
    ("containment", "containment"),
    ("measurement", "measurement"),
    ("waste", "waste_handling"),
)


def _custom_undeclared():
    return custom(profile_id="custom-undeclared")


#: the ASSESSED capability contexts (``no_profile`` is reported separately: nothing is assessed there).
_PROFILES = (
    ("research_lab", research_lab),
    ("poor_man", poor_man),
    ("isopentyl_capability_fit_bench", isopentyl_capability_fit_bench),
    ("custom_undeclared", _custom_undeclared),
)
#: the three contexts the 0.9 exit gate compares (ResearchLab / PoorMan / Custom on the SAME routes).
_DIVERGENCE_PROFILES = ("research_lab", "poor_man", "isopentyl_capability_fit_bench")

_STATUS_NAMES = ("FIT", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE", "UNCONSTRAINED")

#: the Round-IV census (results file as committed at `4b8f8c2`, 86/86 properties, before EVERY Round-V law D1-D19),
#: kept verbatim so every movement is auditable: {profile: {axis: (FIT, BLOCKED, UNKNOWN, NOT_APPLICABLE,
#: UNCONSTRAINED)}}. ``custom_undeclared`` did not exist in that run.
_ROUND_IV_CENSUS = {
    "research_lab": {
        "overall": (0, 0, 7, 0, 0), "material": (0, 0, 7, 0, 0), "equipment": (4, 0, 0, 3, 0),
        "physical": (3, 0, 4, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (4, 0, 3, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (3, 0, 0, 4, 0), "waste": (3, 0, 3, 1, 0),
        "procurement": (1, 0, 0, 6, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 0, 0, 7),
    },
    "poor_man": {
        "overall": (0, 7, 0, 0, 0), "material": (0, 0, 7, 0, 0), "equipment": (1, 3, 0, 3, 0),
        "physical": (3, 0, 4, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (0, 7, 0, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (2, 1, 0, 4, 0), "waste": (1, 4, 1, 1, 0),
        "procurement": (1, 0, 0, 6, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 7, 0, 0),
    },
    "isopentyl_capability_fit_bench": {
        "overall": (0, 4, 3, 0, 0), "material": (3, 2, 2, 0, 0), "equipment": (4, 0, 0, 3, 0),
        "physical": (3, 0, 4, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (4, 0, 3, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (3, 0, 0, 4, 0), "waste": (1, 4, 1, 1, 0),
        "procurement": (1, 0, 0, 6, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 0, 0, 7),
    },
}

#: the census of the X-high run BEFORE the D24 amendment (the D14-D19 tree, commit `941946a`, 32/32 properties) --
#: kept verbatim so every D24 movement is auditable. Same tuple order as ``_ROUND_IV_CENSUS``.
_PRE_D24_CENSUS = {
    "research_lab": {
        "overall": (0, 0, 7, 0, 0), "material": (0, 0, 7, 0, 0), "equipment": (1, 0, 3, 3, 0),
        "physical": (0, 0, 7, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (0, 0, 7, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (0, 0, 3, 4, 0), "waste": (0, 0, 7, 0, 0),
        "procurement": (2, 0, 0, 5, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 7, 0, 0),
    },
    "poor_man": {
        "overall": (0, 7, 0, 0, 0), "material": (0, 0, 7, 0, 0), "equipment": (1, 3, 0, 3, 0),
        "physical": (0, 0, 7, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (0, 7, 0, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (0, 1, 2, 4, 0), "waste": (0, 5, 2, 0, 0),
        "procurement": (2, 0, 0, 5, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 7, 0, 0),
    },
    "isopentyl_capability_fit_bench": {
        "overall": (0, 4, 3, 0, 0), "material": (0, 4, 3, 0, 0), "equipment": (1, 0, 3, 3, 0),
        "physical": (0, 0, 7, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (0, 0, 7, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (0, 0, 3, 4, 0), "waste": (0, 0, 7, 0, 0),
        "procurement": (2, 0, 0, 5, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 7, 0, 0),
    },
    "custom_undeclared": {
        "overall": (0, 7, 0, 0, 0), "material": (0, 0, 7, 0, 0), "equipment": (0, 4, 0, 3, 0),
        "physical": (0, 0, 7, 0, 0), "process": (0, 0, 7, 0, 0), "containment": (0, 7, 0, 0, 0),
        "ventilation": (0, 0, 0, 7, 0), "measurement": (0, 3, 0, 4, 0), "waste": (0, 5, 2, 0, 0),
        "procurement": (0, 2, 0, 5, 0), "attention_care": (0, 0, 0, 7, 0), "monetary": (0, 0, 7, 0, 0),
    },
}

#: the per-law attribution of every census movement vs the pre-D24 run (read off the reason strings).
_ADJUDICATION_D24 = (
    "**equipment + measurement NOT_APPLICABLE -> UNKNOWN on every no-procedure route (D24.17).** Routes 0, 1, 5 and 6 "
    "carry no ProcedureEvidence; each now carries the text-free note 'step s has no ProcedureEvidence: its equipment / "
    "verification demand is unread' -- the same treatment D14 (physical) and D17 (material) already gave that absence, "
    "never a NOT_APPLICABLE fold pass. This is the X-high funnel's own observation, now closed by the barrier. Route 5 "
    "(methyl salicylate) had equipment FIT from its process-record equipment list; it is now UNKNOWN (research_lab, "
    "poor_man, Custom) because the record's list does not discharge the unread procedure-level demand. Provable "
    "BLOCKs still win (custom_undeclared keeps its 4 equipment / 3 measurement BLOCKs; gated membership).",
    "**isopentyl route, poor_man equipment: FRACTIONAL_DISTILLATION no longer demanded (D24.16).** The resolver no "
    "longer maps the page's 'distillation apparatus' ('as described by your instructor') to either SIMPLE or FRACTIONAL; "
    "it is an unread equipment demand. poor_man still BLOCKS on the provable REFLUX_CONDENSER + SEPARATORY_FUNNEL gap "
    "(the census cell did not move; the named set did).",
    "**D24.1 canonical-rendering display law (reason sets grew; no census cell moved on its own).** On the isopentyl "
    "PROCESS_SPECIFIED route the op-4 / op-7 quantity prose and the procedure `scale` are not the canonical rendering "
    "of their typed uses (material unread), and the workup_isolation / separation / wash / drying / purification "
    "summaries are not the canonical rendering of their realizing ops (process unread); the analytical-verification "
    "text is a measurement demand beside the typed VERIFY methods. Every one of those axes was already UNKNOWN or "
    "BLOCKED for other reasons, so the census is unchanged -- the new reasons are the masking the round was told "
    "never to rely on.",
    "**D24.3:** the isopentyl step's `envelope.medium` sentence is back on the material axis as a text-free unread note "
    "(never a species, hazard entry or waste stream -- Part IV stands).",
    "**Unchanged:** overall verdicts (research_lab 7 UNKNOWN, poor_man 7 BLOCKED, Custom 4 BLOCKED + 3 UNKNOWN, "
    "custom_undeclared 7 BLOCKED), zero CAPABILITY_FIT, and the ResearchLab / PoorMan / Custom divergence (7/7 routes).",
)

#: the ADJUDICATED overall-verdict census per assessed context (audit doc §7 funnel adjudication): a regression pin,
#: not a target -- each value was read off the per-route reasons, never chosen.
_EXPECTED_OVERALL = {
    "research_lab": {"UNKNOWN": 7},
    "poor_man": {"BLOCKED": 7},
    "isopentyl_capability_fit_bench": {"BLOCKED": 4, "UNKNOWN": 3},
    "custom_undeclared": {"BLOCKED": 7},
}

#: the isopentyl PROCESS_SPECIFIED route under poor_man: the exact axes that BLOCK and the exact capability each
#: names as missing (the justified divergence the 0.9 exit gate asks for).
_EXPECTED_POOR_MAN_ISO_BLOCKS = {
    # D24.16: "distillation apparatus" is UNRECOGNIZED (the page says "as described by your instructor"), so
    # FRACTIONAL_DISTILLATION is no longer demanded -- the distillation op is an unread equipment demand instead.
    "equipment": "REFLUX_CONDENSER, SEPARATORY_FUNNEL",
    "containment": "FUME_HOOD",
    "measurement": "INFRARED_SPECTROSCOPY",
    "waste": "HAZARDOUS",
}


#: the per-law attribution of every census movement vs Round IV, read off the reason strings the assessments carry
#: (audit doc §3 D1-D13 = Round V first half; §7.2 D14-D19 = the X-high continuation). Hand-adjudicated text: a
#: reviewer re-derives it from the "Decisive reason" section above.
_ADJUDICATION = (
    "**physical FIT -> UNKNOWN (every context, 3 -> 0 FIT).** D14 + F-10: the aspirin/paracetamol procedures state "
    "their temperatures in PROSE ('steam bath', 'cool in an ice bath', ...) and a prose demand is no longer 'covered' "
    "by an unrelated process extremum; the isopentyl DISTILL op states no typed temperature and its whole-step peak was "
    "withdrawn (P-X2: the only number is the distillate HEAD range, a lower bound on the heat demand); a step without "
    "ProcedureEvidence (the 2-step isopentyl routes, methyl salicylate, retro-DA) leaves its LOW side unread (D14 iv) "
    "against the new 273.15 K preset floors. research_lab additionally leaves its pressure floor undeclared (P-X3: it "
    "owns VACUUM_FILTRATION, so its old 'cannot pull a vacuum' 1.0 atm floor contradicted its own equipment).",
    "**equipment FIT -> UNKNOWN (routes 2-4, research_lab and the Custom bench).** D16 per-op post-resolution guard: "
    "a hardware op that names no non-consumable apparatus (isopentyl op 3 COOL and op 8 DRY; the aspirin and "
    "paracetamol analogues) is an unread equipment demand. poor_man keeps its provable BLOCK on the named missing rigs "
    "(gated membership: a provable BLOCK always wins over an unread remainder). The no-procedure routes 0, 1, 5 and 6 "
    "moved by D24.17 (see the D24 section).",
    "**measurement FIT -> UNKNOWN (routes 2-4, research_lab and the Custom bench).** D16: a PRESENT prose endpoint "
    "('basic to litmus', 'collect the 134-143 C fraction', ...) is an unread measurement demand, and aspirin's sourced "
    "ferric-chloride purity test is now a VERIFY op with no instrument (P5b). poor_man keeps its IR BLOCK on the "
    "isopentyl route. The no-procedure routes 0, 1, 5 and 6 moved NOT_APPLICABLE -> UNKNOWN by D24.17.",
    "**containment FIT -> UNKNOWN (research_lab and the Custom bench, every route).** Round-V D13 parity: every "
    "balanced species with no hazard record and every unresolvable ionic auxiliary is hazard-UNRESOLVED (F47), so the "
    "containment a route needs cannot be determined. poor_man stays BLOCKED (no FUME_HOOD against a real H2SO4/"
    "butadiene GHS record).",
    "**waste -> UNKNOWN / BLOCKED (every context).** Round-V D9: a waste category is earned only from positive stream "
    "evidence; every SUBSTRATE/REACTANT residual and every spent workup stream is unresolved (F77/F49); X-high F-6: an "
    "untyped material introduced by any op is its own unresolved obligation. The Custom bench's waste BLOCKs vanished "
    "because Round V declared HAZARDOUS in its waste_handling -- the axis moved from a provable BLOCK to the honest "
    "evidence gap; poor_man (no HAZARDOUS handling) BLOCKS on 5 routes.",
    "**procurement NOT_APPLICABLE -> FIT (the aspirin route).** Round-V D13: a typed CATALYST use (aspirin's sulfuric "
    "acid) is a declared catalyst and enters the procurement question.",
    "**monetary UNCONSTRAINED -> UNKNOWN (research_lab, Custom bench).** Round-V D13: `budget=None` is UNDECLARED, "
    "never 'unconstrained'; every route consumes purchased materials. poor_man's declared USD budget stays UNKNOWN "
    "(route cash is unknown).",
    "**Custom-bench material FIT 3 -> 0, BLOCKED 2 -> 4.** D18: the corpus requirement phases are AUTHOR_INFERRED "
    "(only four uses carry a SOURCE_QUOTED phase) and D2's G- commensurability needs a certified draw, so the isopentyl "
    "routes read UNKNOWN (never FIT); the four non-isopentyl routes BLOCK because the bench stocks only the isopentyl "
    "procedure (a typed species absent from every declared bottle against a positive demand).",
    "**overall verdicts did NOT move** (research_lab 7 UNKNOWN, poor_man 7 BLOCKED, Custom 4 BLOCKED + 3 UNKNOWN): the "
    "X-high laws closed per-axis holes behind an already fail-closed fold -- exactly the masking the round was told "
    "not to trust.",
    "**Observation (closed by D24.17):** the pre-D24 run showed that a step with NO ProcedureEvidence yielded NO "
    "equipment and NO measurement demand (NOT_APPLICABLE, a fold pass) while D14/D17 treated the same absence as an "
    "unread physical/material demand. The barrier adopted it: see the D24 movement section.",
)


def _search(target_name, reagents, have, max_depth, tkind=InputKind.NAME):
    target = resolve_target(target_name, tkind).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _corpus_routes() -> list:
    """Every route the real search returns for the five forcing-corpus targets -- ALL of them, never just the first
    candidate, so the denominator is never quietly narrowed."""
    routes = []
    routes += _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3).routes
    routes += _search(
        "acetylsalicylic acid", ("acetic acid",), ("salicylic acid", "acetic anhydride"), 3,
    ).routes
    routes += _search("paracetamol", ("acetic acid",), ("4-aminophenol", "acetic anhydride"), 3).routes
    routes += _search("methyl salicylate", ("water",), ("salicylic acid", "methanol"), 3).routes
    routes += _search("C1=CCCCC1", ("C=C",), ("C=CC=C",), 2, tkind=InputKind.SMILES).routes  # retro-Diels-Alder
    return routes


def _axis_ok(status: CapabilityStatus) -> bool:
    """Whether an axis status lets a route PASS that funnel stage (FIT/NOT_APPLICABLE/UNCONSTRAINED pass the fold;
    BLOCKED/UNKNOWN never do)."""
    return status in (CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED)


def _route_label(route) -> str:
    targets = {"C7H14O2": "isopentyl acetate", "C9H8O4": "aspirin", "C8H9NO2": "paracetamol",
               "C8H8O3": "methyl salicylate", "C6H10": "cyclohexene (retro-DA)"}
    formula = repr(route.steps[-1].products[0])
    return f"{targets.get(formula, formula)} ({len(route.steps)} step{'s' if len(route.steps) != 1 else ''})"


def _decisive_reason(result) -> str:
    """The reason string that DECIDES an axis status, verbatim (truncated for the table): for BLOCKED the first reason
    naming the refusal, else the first reason."""
    if result.status is CapabilityStatus.BLOCKED:
        for reason in result.reasons:
            if any(key in reason for key in ("missing required capability", "BLOCKED", "exceeds", "below the",
                                              "not among", "uncertain obtainability")):
                return reason
    return result.reasons[0] if result.reasons else ""


def _clip(text: str, limit: int = 230) -> str:
    text = text.replace("|", "/").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def assess_all(routes: list) -> "tuple[list, dict]":
    """Per route: its readiness tier and one assessment per assessed context (compiled ONCE per route -- the
    requirement projection never peeks at a profile)."""
    rows = []
    for i, route in enumerate(routes):
        if i and i % 5 == 0:
            print(f"    ...{i}/{len(routes)} routes assessed", flush=True)
        req = compile_capability_requirements(route)
        readiness = evaluate_route(route)
        rows.append({
            "route": route, "tier": readiness.tier,
            "assessments": {name: assess(builder(), req, readiness) for name, builder in _PROFILES},
        })
    return rows


def compute(rows: list, name: "str | None") -> dict:
    """One context's funnel + census. ``name=None`` is the NOT_REQUESTED context (nothing assessed)."""
    funnel = {stage: 0 for stage in _STAGES}
    census = {axis: {s: 0 for s in _STATUS_NAMES} for axis in ("overall", *_ALL_AXES)}
    for row in rows:
        alive = True
        a = None if name is None else row["assessments"][name]
        if a is not None:
            census["overall"][a.overall.value] += 1
            for axis in _ALL_AXES:
                census[axis][getattr(a, axis).status.value] += 1
        for stage in _STAGES:
            if stage == "routes returned":
                ok = True
            elif stage == "PROCESS_SPECIFIED":
                ok = row["tier"] == PROCESS_SPECIFIED
            elif a is None:
                ok = False  # NOT_REQUESTED: nothing downstream of the tier is ever assessed
            elif stage == "assessment requested":
                ok = True
            elif stage == "monetary assessed":
                ok = _axis_ok(a.monetary.status)
            elif stage == "CAPABILITY_FIT":
                ok = a.overall is CapabilityStatus.FIT
            else:
                ok = _axis_ok(getattr(a, stage.rsplit(" ", 1)[0]).status)
            alive = alive and ok
            if alive:
                funnel[stage] += 1
    return {"funnel": funnel, "census": census, "assessed": name is not None}


def divergence(rows: list) -> list:
    """Every (route, axis) on which research_lab / poor_man / the Custom bench disagree, with each profile's decisive
    reason -- the exit-gate evidence."""
    out = []
    for index, row in enumerate(rows):
        for axis in ("overall", *_ALL_AXES):
            results = {n: row["assessments"][n] for n in _DIVERGENCE_PROFILES}
            statuses = {n: (r.overall if axis == "overall" else getattr(r, axis).status) for n, r in results.items()}
            if len(set(statuses.values())) > 1:
                reasons = {} if axis == "overall" else {
                    n: _decisive_reason(getattr(r, axis)) for n, r in results.items()}
                out.append({"route": index, "label": _route_label(row["route"]), "tier": row["tier"],
                            "axis": axis, "statuses": {n: s.value for n, s in statuses.items()},
                            "reasons": reasons})
    return out


def check(results: list, name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


_BLOCK_JUSTIFICATIONS = ("missing required capability", "BLOCKED", "exceeds", "below the", "not among",
                         "uncertain obtainability")


def run() -> tuple:
    routes = _corpus_routes()
    rows = assess_all(routes)
    per = {"no_profile": compute(rows, None)}
    per.update({name: compute(rows, name) for name, _ in _PROFILES})
    div = divergence(rows)
    r: list = []

    check(r, "corpus non-empty", len(routes) > 0, f"{len(routes)} routes returned")
    check(r, "corpus is exactly the 7 forcing-matrix routes (search unchanged by Round V)", len(routes) == 7,
          f"{len(routes)} routes")
    returned = {per[n]["funnel"]["routes returned"] for n in per}
    ps = {per[n]["funnel"]["PROCESS_SPECIFIED"] for n in per}
    check(r, "routes-returned identical in every capability context (incl. NOT_REQUESTED)", len(returned) == 1,
          f"{ {n: per[n]['funnel']['routes returned'] for n in per} }")
    check(r, "PROCESS_SPECIFIED count identical in every capability context", len(ps) == 1,
          f"{ {n: per[n]['funnel']['PROCESS_SPECIFIED'] for n in per} }")
    check(r, "no_profile: capability NOT_REQUESTED assesses nothing (no assumed bench)",
          per["no_profile"]["funnel"]["assessment requested"] == 0
          and sum(sum(c.values()) for c in per["no_profile"]["census"].values()) == 0,
          f"assessment requested = {per['no_profile']['funnel']['assessment requested']}")
    for name in per:
        funnel = per[name]["funnel"]
        mono = all(funnel[a] >= funnel[b] for a, b in zip(_STAGES[:-1], _STAGES[1:]))
        check(r, f"{name}: funnel monotone non-increasing over all {len(_STAGES)} stages", mono,
              " > ".join(str(funnel[s]) for s in _STAGES))
    # the zero-FIT theorem's prediction, per context.
    for name, _ in _PROFILES:
        n_fit = per[name]["funnel"]["CAPABILITY_FIT"]
        fit_overall = per[name]["census"]["overall"]["FIT"]
        check(r, f"{name}: ZERO CAPABILITY_FIT (zero-FIT theorem; no route/profile fabricates a FIT)",
              n_fit == 0 and fit_overall == 0, f"funnel FIT = {n_fit}, overall FIT census = {fit_overall}")
    # denominators never narrowed.
    for name, _ in _PROFILES:
        ok = all(sum(per[name]["census"][axis].values()) == len(routes) for axis in ("overall", *_ALL_AXES))
        check(r, f"{name}: every axis + overall census sums to the full {len(routes)}-route denominator", ok,
              ", ".join(f"{axis}={sum(per[name]['census'][axis].values())}" for axis in ("overall", *_ALL_AXES)))
    # adjudicated overall census (regression pin).
    for name, expected in _EXPECTED_OVERALL.items():
        got = {k: v for k, v in per[name]["census"]["overall"].items() if v}
        check(r, f"{name}: overall-verdict census == adjudicated {expected}", got == expected, f"got {got}")
    # P-h: nothing declared => nothing certified.
    cu_fits = {axis: per["custom_undeclared"]["census"][axis]["FIT"] for axis in _FUNNEL_AXES}
    check(r, "custom_undeclared: a bench that declares NOTHING certifies NOTHING (zero FIT on every gating axis)",
          not any(cu_fits.values()), f"FIT counts {cu_fits}")
    # P-i: declared-capability dominance on the membership axes, computed from the REAL declared sets.
    rl, pm = research_lab(), poor_man()
    rank = {CapabilityStatus.BLOCKED: 0, CapabilityStatus.UNKNOWN: 1, CapabilityStatus.FIT: 2,
            CapabilityStatus.NOT_APPLICABLE: 2, CapabilityStatus.UNCONSTRAINED: 2}
    for axis, attr in _MEMBERSHIP_AXES:
        superset = getattr(rl, attr) >= getattr(pm, attr)
        worse = [row_i for row_i, row in enumerate(rows)
                 if rank[getattr(row["assessments"]["research_lab"], axis).status]
                 < rank[getattr(row["assessments"]["poor_man"], axis).status]]
        check(r, f"dominance: research_lab declares a superset of poor_man's {attr} and is never WORSE on {axis}",
              superset and not worse, f"superset={superset}, routes where research_lab is worse: {worse}")
    # P-j: meaningful, justified divergence (the 0.9 exit gate).
    diverging_routes = sorted({d["route"] for d in div})
    check(r, "exit gate: ResearchLab / PoorMan / Custom DIVERGE on the same chemistry",
          len(diverging_routes) > 0, f"{len(diverging_routes)}/{len(routes)} routes diverge on >=1 axis; "
          f"{sum(1 for d in div if d['axis'] == 'overall')} on the overall verdict")
    unjustified = []
    for name, _ in _PROFILES:
        for row_i, row in enumerate(rows):
            a = row["assessments"][name]
            for axis in _ALL_AXES:
                res = getattr(a, axis)
                if res.status is CapabilityStatus.BLOCKED and not any(
                        k in reason for reason in res.reasons for k in _BLOCK_JUSTIFICATIONS):
                    unjustified.append((name, row_i, axis))
    check(r, "every BLOCKED axis, in every context, names the refused capability / shortfall (justified)",
          not unjustified, f"unjustified BLOCKs: {unjustified}")
    # P-k: the isopentyl PROCESS_SPECIFIED route -- the fully-declared bench refuses NOTHING (every gap is an
    # evidence gap = UNKNOWN), while poor_man BLOCKS on exactly the named missing capabilities.
    ps_rows = [row for row in rows if row["tier"] == PROCESS_SPECIFIED]
    check(r, "exactly one PROCESS_SPECIFIED route (the sourced isopentyl procedure)", len(ps_rows) == 1,
          f"{len(ps_rows)}")
    if ps_rows:
        iso = ps_rows[0]["assessments"]
        fb = iso["isopentyl_capability_fit_bench"]
        fb_blocked = [axis for axis in _ALL_AXES if getattr(fb, axis).status is CapabilityStatus.BLOCKED]
        fb_unknown = sorted(axis for axis in _ALL_AXES if getattr(fb, axis).status is CapabilityStatus.UNKNOWN)
        check(r, "isopentyl PS route under the fully-declared Custom bench: no axis BLOCKED, overall UNKNOWN",
              not fb_blocked and fb.overall is CapabilityStatus.UNKNOWN,
              f"BLOCKED={fb_blocked}; UNKNOWN={fb_unknown}; overall={fb.overall.value}")
        pmr = iso["poor_man"]
        pm_blocks = {axis: getattr(pmr, axis) for axis in _ALL_AXES
                     if getattr(pmr, axis).status is CapabilityStatus.BLOCKED}
        named = {axis: next((x.split("capability/ies: ", 1)[1] for x in res.reasons
                             if "missing required capability/ies: " in x), "")
                 for axis, res in pm_blocks.items()}
        check(r, "isopentyl PS route under poor_man BLOCKS on exactly the named missing capabilities",
              named == _EXPECTED_POOR_MAN_ISO_BLOCKS, f"got {named}")
    # D24.17: a no-procedure step never reads NOT_APPLICABLE on equipment / measurement.
    na = [(name, i, axis) for name, _ in _PROFILES for i, row in enumerate(rows) for axis in ("equipment", "measurement")
          if getattr(row["assessments"][name], axis).status is CapabilityStatus.NOT_APPLICABLE]
    check(r, "D24.17: no route reads equipment/measurement NOT_APPLICABLE (a missing procedure is an unread demand)",
          not na, f"NOT_APPLICABLE cells: {na or 'none'}")
    # D24.16: FRACTIONAL_DISTILLATION is never demanded by any corpus route (the alias is gone).
    frac = [i for i, row in enumerate(rows)
            if "FRACTIONAL_DISTILLATION" in " ".join(row["assessments"]["poor_man"].equipment.reasons)
            and "missing required" in " ".join(row["assessments"]["poor_man"].equipment.reasons)]
    check(r, "D24.16: no corpus route demands FRACTIONAL_DISTILLATION ('distillation apparatus' is unrecognized)",
          not frac, f"routes naming it as missing: {frac or 'none'}")
    return r, per, rows, div


def _census_table(census: dict) -> "list[str]":
    lines = ["| axis | " + " | ".join(_STATUS_NAMES) + " | total |", "|---|" + "---|" * (len(_STATUS_NAMES) + 1)]
    for axis in ("overall", *_ALL_AXES):
        counts = census[axis]
        lines.append(f"| {axis} | " + " | ".join(str(counts[s]) for s in _STATUS_NAMES)
                     + f" | {sum(counts.values())} |")
    return lines


def render_markdown(results: list, per: dict, rows: list, div: list) -> str:
    total = len(rows)
    lines = [
        "# v0.9 Capability Compiler -- funnel, per-axis census, profile divergence (Round V X-high)",
        "",
        "Generated by `.venv/bin/python experiments/v0_9_capability_funnel.py` (writes this file). Corpus: every route "
        "`smartchem.experiment.routes.search_routes` returns for isopentyl acetate, aspirin, paracetamol, methyl "
        f"salicylate and retro-Diels-Alder -- **{total} routes**, the same set in every capability context. The funnel "
        "is a CUMULATIVE AND; the census is NEVER narrowed (every axis sums to the full denominator). Zero "
        "CAPABILITY_FIT is the expected outcome (the Round-V zero-FIT theorem, audit doc §7.2 D17) -- a FIT here "
        "would be a finding, not a success.",
        "",
        "## Routes",
        "",
        "| # | route | readiness tier |",
        "|---|---|---|",
    ]
    for i, row in enumerate(rows):
        lines.append(f"| {i} | {_route_label(row['route'])} `{row['route'].digest[:12]}` | {row['tier']} |")
    lines += ["", "## Funnel (every context)", "",
              "| stage | " + " | ".join(per) + " |", "|---|" + "---|" * len(per)]
    for stage in _STAGES:
        lines.append(f"| {stage} | " + " | ".join(str(per[n]["funnel"][stage]) for n in per) + " |")
    lines += ["", "`no_profile` = capability NOT_REQUESTED: nothing is assessed (no assumed bench), so every stage "
              "after the readiness tier is 0 by construction.", ""]
    for name, _ in _PROFILES:
        lines += [f"## Census: `{name}`", ""] + _census_table(per[name]["census"]) + [""]

    lines += ["## Divergence: research_lab / poor_man / Custom (`isopentyl_capability_fit_bench`) on the SAME routes",
              "", f"{len({d['route'] for d in div})}/{total} routes diverge on at least one axis; "
              f"{sum(1 for d in div if d['axis'] == 'overall')} on the overall verdict.", "",
              "| route | axis | research_lab | poor_man | Custom |", "|---|---|---|---|---|"]
    for d in div:
        s = d["statuses"]
        lines.append(f"| {d['route']} {d['label']} | {d['axis']} | {s['research_lab']} | {s['poor_man']} | "
                     f"{s['isopentyl_capability_fit_bench']} |")
    lines += ["", "### Decisive reason per diverging (route, axis) -- verbatim from the assessment", ""]
    for d in div:
        if d["axis"] == "overall":
            continue
        lines.append(f"* **route {d['route']} {d['label']} -- {d['axis']}**")
        for n in _DIVERGENCE_PROFILES:
            lines.append(f"  * `{n}` {d['statuses'][n]}: {_clip(d['reasons'][n])}")
    lines += ["", "## Movement vs the Round-IV run (results file at `4b8f8c2`, before every Round-V law D1-D19)", "",
              "Only cells that moved are listed; `custom_undeclared` is new in this run. The per-law attribution of "
              "each movement is in the adjudication section below.", "",
              "| context | axis | Round IV (FIT/BLOCKED/UNKNOWN/NA/UNCONSTRAINED) | now |", "|---|---|---|---|"]
    moved = 0
    for name, old in _ROUND_IV_CENSUS.items():
        for axis, old_counts in old.items():
            new_counts = tuple(per[name]["census"][axis][s] for s in _STATUS_NAMES)
            if new_counts != old_counts:
                moved += 1
                lines.append(f"| {name} | {axis} | {'/'.join(map(str, old_counts))} | "
                             f"{'/'.join(map(str, new_counts))} |")
    if not moved:
        lines.append("| — | — | no cell moved | — |")
    lines += ["", "## Adjudication of the movement (each cell against the law its reason strings cite)", ""]
    lines += [f"* {entry}" for entry in _ADJUDICATION]
    lines += ["", "## Movement vs the pre-D24 X-high run (`941946a`, before the Wave-C′ D24 amendment)", "",
              "| context | axis | pre-D24 (FIT/BLOCKED/UNKNOWN/NA/UNCONSTRAINED) | now |", "|---|---|---|---|"]
    moved_d24 = 0
    for name, old in _PRE_D24_CENSUS.items():
        for axis, old_counts in old.items():
            new_counts = tuple(per[name]["census"][axis][s] for s in _STATUS_NAMES)
            if new_counts != old_counts:
                moved_d24 += 1
                lines.append(f"| {name} | {axis} | {'/'.join(map(str, old_counts))} | "
                             f"{'/'.join(map(str, new_counts))} |")
    if not moved_d24:
        lines.append("| — | — | no cell moved | — |")
    lines += ["", "### Attribution (D24, audit doc §7.5)", ""]
    lines += [f"* {entry}" for entry in _ADJUDICATION_D24]
    lines += ["", "## Properties checked", "", "| property | verdict | detail |", "|---|---|---|"]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {_clip(detail, 400)} |")
    passed = sum(1 for _, ok, _ in results if ok)
    lines += ["", f"**{passed}/{len(results)} properties hold.**", ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("v0.9 capability compiler funnel + census + divergence (Round V X-high):")
    results, per, rows, div = run()
    _ARTIFACT.write_text(render_markdown(results, per, rows, div), encoding="utf-8")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} properties hold. [wrote {_ARTIFACT}]")
    if passed != len(results):
        print("FUNNEL/CENSUS FAILED.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
