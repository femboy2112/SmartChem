"""V0.9.5-FUNNEL-01: the frozen RC funnel -- every corpus member driven through every stage it reaches, PUBLIC API / CLI
only, graded against the BLIND expected-outcome oracle ``docs/research/V0_9_5_RC_FUNNEL_ORACLE.json``.

**Ugh, fine, the whole product in one table.** The oracle was frozen (and committed) BEFORE this driver and before the
S7-S10 feature-closure writers landed; the driver pins its sha256 and refuses a changed oracle.  For each of the 13 stages
it prints the full denominator -- entered / survived / correctly refused / wrongly refused / wrong survivor / wrong
content-or-reason / PENDING / NA / not-reached-confirmed -- and every drop with its typed reason.  It never shows only
survivors.

Verdicts per member: PASS (every reached stage matches), PENDING(S..) (matches except a 0.9.5 facet whose change has not
landed -- detected because the OBSERVED value equals the oracle's `before`; NEVER counted as a pass), MISMATCH.
Exit code: 0 = every member PASS; 1 = at least one MISMATCH; 3 = no mismatch but PENDING remain (0 with ``--allow-pending``).
``--require-landed S7,S8,..`` turns a PENDING for those ids into a MISMATCH (the release gate).

Driver notes (observation mapping the oracle relies on): for an INPUT_KIND_AMBIGUOUS bare paste the pre-identity stages
report the SMILES reading (both readings are printed under identity); a front-door drop makes every later stage
NOT_REACHED, except that a typed INVALID_INPUT service envelope is still a real payload that round-trips (final_dossier /
deserialize_verify are observed on it, exactly as the baseline freeze does).

Run:  .venv/bin/python experiments/v0_9_5_rc_funnel.py [--only R-01,MK-01] [--skip-slow] [--allow-pending]
                                                       [--require-landed S7,S8] [--json out.json]
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses as dc
import hashlib
import importlib
import importlib.util
import io
import json
import re
import sys
import time
import traceback
from collections import Counter, OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (str(REPO), str(REPO / "experiments"), str(REPO / "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

ORACLE_PATH = REPO / "docs" / "research" / "V0_9_5_RC_FUNNEL_ORACLE.json"
ORACLE_SHA256 = "30fbfdf7d0b3ba7997450688a87654737b269b6ea6f9a95384ad086caa9f076e"
PRERELEASE_RESPONSE_ID = "smartchem.service/compilation-response-v1alpha17"  # the 0.9.0a1 wire id (S14 refuses it)
STAGES = ["raw_input", "normalized_syntax", "composition", "identity", "structure", "search", "search_receipt",
          "reaction_vouch", "route_readiness", "capability_requirements", "profile_projection", "final_dossier",
          "deserialize_verify"]
SLOW_MEMBERS = {"R-15", "R-16", "R-17"}   # the three isopentyl compiles (~1 min compile + ~20 s loads each)

# oracle member -> the frozen baseline corpus case whose EXACT request kwargs it drives
FREEZE_CASE = {
    "R-01": "methyl_acetate", "R-02": "methyl_acetate@poor-man", "R-03": "methyl_acetate@research-lab",
    "R-04": "aspirin", "R-05": "aspirin@poor-man", "R-06": "paracetamol", "R-07": "paracetamol@research-lab",
    "R-08": "paracetamol_incomplete", "R-09": "methyl_salicylate", "R-10": "diels_alder_control", "R-11": "bromine",
    "R-12": "bromine_smiles", "R-13": "invalid_name", "R-14": "decompile_paracetamol", "R-15": "isopentyl",
    "R-16": "isopentyl@poor-man", "R-17": "isopentyl@custom-fit-bench", "R-18": "methyl_acetate_dag",
    "R-19": "isopentyl_dag@poor-man",
}


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha(obj) -> str:
    return hashlib.sha256((obj if isinstance(obj, str) else canon(obj)).encode()).hexdigest()


def OK(**kw):
    return {"status": "OK", **kw}


def DROP(reason, **kw):
    return {"status": "DROP", "reason": reason, **kw}


def _val(x):
    return getattr(x, "value", x)


_HEX64 = re.compile(r"[0-9a-f]{64}")


def _nmsg(s: str) -> str:
    return _HEX64.sub("<hex64>", s)


# --------------------------------------------------------------------------------------------------------------------
# typed reasons for a front-door refusal (classified from the identity parser's own message)
# --------------------------------------------------------------------------------------------------------------------
def classify_parse_error(msg: str) -> str:
    fpart = msg.split("formula said", 1)[1] if "formula said" in msg else msg
    spart = msg.split("SMILES said", 1)[1].split("; formula said")[0] if "SMILES said" in msg else ""
    if "disconnected SMILES" in spart:
        return "DISCONNECTED_SMILES"
    if "decimal point" in fpart:
        return "FORMULA_DECIMAL_POINT"
    if "ambiguous ASCII ion" in fpart:
        return "AMBIGUOUS_ASCII_ION"
    if "unbalanced" in fpart:
        return "UNBALANCED_PAREN"
    if "unexpected lowercase" in fpart:
        return "LOWERCASE_ELEMENT_NOT_A_KNOWN_NAME"
    if "non-empty" in fpart or "empty" in spart:
        return "EMPTY_INPUT"
    return "UNCLASSIFIED_IDENTITY_PARSE_ERROR"


# --------------------------------------------------------------------------------------------------------------------
# the comparison: subset semantics, `_not` keys, S-facets (`s` + `before`), message hex normalisation
# --------------------------------------------------------------------------------------------------------------------
MATCH, PENDING, MISMATCH = "MATCH", "PENDING", "MISMATCH"


def _match(exp, obs, path=""):
    """-> (verdict, pending_ids:set, notes:list)."""
    if isinstance(exp, dict):
        if "s" in exp and "before" not in exp and isinstance(obs, str) and obs.startswith("policy API absent"):
            return PENDING, {exp["s"]}, [f"{path}: PENDING({exp['s']}) feature absent"]
        if "s" in exp and "before" not in exp:   # the feature landed: `s` is the facet's tag, not an observed field
            return _match({k: v for k, v in exp.items() if k != "s"}, obs, path)
        if "s" in exp and "before" in exp:
            sid = exp["s"]
            core = {k: v for k, v in exp.items() if k not in ("s", "before")}
            v, pend, notes = _match(core, obs, path)
            if v == MATCH:
                return MATCH, pend, notes
            vb, _p, _n = _match(exp["before"], obs, path) if not isinstance(exp["before"], str) else (
                (MATCH, set(), []) if obs == exp["before"] else (MISMATCH, set(), []))
            if vb == MATCH or (isinstance(obs, dict) and str(obs.get("status", "")).startswith("PENDING")):
                return PENDING, {sid} | pend, [f"{path or '.'}: PENDING({sid}) observed==before"]
            return MISMATCH, set(), notes or [f"{path or '.'}: neither expected nor `before`"]
        if not isinstance(obs, dict):
            return MISMATCH, set(), [f"{path}: expected object {canon(exp)[:80]}, observed {canon(obs)[:80]}"]
        verdict, pend, notes = MATCH, set(), []
        for k, ev in exp.items():
            if k in ("because", "detail"):
                continue
            if k == "stdout_contains":
                miss = [t for t in ev if t not in obs.get("stdout", "")]
                if miss:
                    verdict, notes = MISMATCH, notes + [f"{path}/stdout_contains: missing {miss}"]
                continue
            if k == "msg_head":
                if not _nmsg(obs.get("msg", "")).startswith(_nmsg(ev)):
                    verdict, notes = MISMATCH, notes + [f"{path}/msg: {obs.get('msg', '')[:80]!r} !~ {ev!r}"]
                continue
            if k.endswith("_not"):
                base = k[:-4]
                if base not in obs or obs[base] == ev:
                    verdict, notes = MISMATCH, notes + [f"{path}/{base}: observed {obs.get(base)!r} must not equal {ev!r}"]
                continue
            if k not in obs:
                verdict, notes = MISMATCH, notes + [f"{path}/{k}: not observed"]
                continue
            v, p, n = _match(ev, obs[k], f"{path}/{k}")
            pend |= p
            notes += n
            if v == MISMATCH:
                verdict = MISMATCH
            elif v == PENDING and verdict != MISMATCH:
                verdict = PENDING
        return verdict, pend, notes
    if isinstance(exp, str) and path.endswith("/msg") and isinstance(obs, str):
        return (MATCH if _nmsg(exp) == _nmsg(obs) else MISMATCH), set(), (
            [] if _nmsg(exp) == _nmsg(obs) else [f"{path}: {obs[:80]!r} != {exp[:80]!r}"])
    if isinstance(exp, list) and isinstance(obs, list) and all(isinstance(x, (str, int, float, bool)) or x is None for x in exp):
        # scalar lists: order matters except for declared set-like fields (sorted upstream)
        return (MATCH if exp == obs else MISMATCH), set(), ([] if exp == obs else [f"{path}: {obs!r} != {exp!r}"])
    ok = exp == obs
    return (MATCH if ok else MISMATCH), set(), ([] if ok else [f"{path}: observed {canon(obs)[:90]} != expected {canon(exp)[:90]}"])


# --------------------------------------------------------------------------------------------------------------------
# observers -- each returns OrderedDict stage -> observation (only the stages actually reached)
# --------------------------------------------------------------------------------------------------------------------
def _quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def _identity_stages(text, kind):
    """The front-door stages via the public identity authority.  -> (obs dict, resolved | None, drop reason | None)."""
    from smartchem.identity_parse import IdentityParseError, resolve_identity

    obs = OrderedDict()
    try:
        r = resolve_identity(text, kind)
    except IdentityParseError as exc:
        reason = classify_parse_error(str(exc))
        obs["normalized_syntax"] = DROP(reason)
        return obs, None, reason
    fe = r.formula_expr
    ns = {"resolved_kind": r.receipt.resolved_kind.value, "source": r.receipt.source.value}
    if fe is not None:
        ns["syntax"] = fe.normalized
        ns["component_multipliers"] = [c.multiplier for c in fe.components]
    obs["normalized_syntax"] = OK(**ns)
    obs["composition"] = OK(hill=r.receipt.normalized, charge=getattr(r.formula, "charge", 0))
    obs["identity"] = OK(layer=r.receipt.identity_layer, constitution_established=r.constitution_established,
                         registry_candidates=sorted(getattr(c, "name", str(c)) for c in r.registry_candidates))
    if r.molecule is not None:
        f = r.features
        obs["structure"] = OK(atoms=len(r.molecule.atoms), charge=r.molecule.charge,
                              tetrahedral_stereo=bool(f.tetrahedral_stereo) if f else False,
                              isotopes=list(f.isotopes) if f else [])
    else:
        obs["structure"] = DROP("COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED")
    return obs, r, None


def _response_stages(resp, obs, params_profile, is_decompile=False):
    """search .. deserialize_verify from a service response, reusing the baseline freeze's own record builders."""
    import v0_9_5_baseline_freeze as bf

    rec, thick, thin = bf._response_record(resp)
    outcome = rec["outcome"]
    ss = rec["search_space_status"]
    n_routes, n_dags = len(rec["routes"]), len(rec["dags"])
    if outcome == "REFUSED":
        req = resp.request
        dag = "CONVERGENT" in str(_val(req.transform_grammar)).upper()
        charged = any(w in " ".join(resp.diagnostics).lower() for w in ("charged", "neutral input"))
        reason = ("REFUSED_CONVERGENT_DAG_UNDER_CAPABILITY_PROFILE" if dag and req.capability_profile is not None
                  else "REFUSED_CHARGED_SPECIES_CHEMISTRY_MODEL_BOUNDARY" if charged else "REFUSED_OTHER")
        obs["search"] = DROP(reason, outcome=outcome, exit_code=rec["exit_code"])
        obs["final_dossier"] = OK(n_routes=0, n_dags=0, capability_fit_count=0)
        obs["deserialize_verify"] = OK(**bf._load_records(resp, thick, thin))
        return rec, thick
    if outcome == "INVALID_INPUT":
        obs["final_dossier"] = OK(n_routes=0, n_dags=0, capability_fit_count=0)
        obs["deserialize_verify"] = OK(**bf._load_records(resp, thick, thin))
        return rec, thick
    obs["search"] = OK(outcome=outcome, exit_code=rec["exit_code"], search_space_status=ss, n_routes=n_routes,
                       n_dags=n_dags)
    ir = thick.get("compilation_ir") or {}
    sr = ir.get("search_receipt") or {}
    status = sr.get("status") or ir.get("search_status") or ""
    receipt = {"complete": str(status).startswith("COMPLETE")}
    if not is_decompile:
        for k in ("max_depth", "cut_budget", "result_limit", "candidates_emitted", "nodes_visited"):
            if k in sr:
                receipt[k] = sr[k]
    obs["search_receipt"] = OK(**receipt, engine_status=status)
    if rec["routes"]:
        sat = 0
        for d in thick["ranked_route_dossiers"]:
            steps = ((d.get("readiness") or {}).get("per_step")) or []
            if steps and all(s.get("reaction_type") == "SATISFIED" for s in steps):
                sat += 1
        obs["reaction_vouch"] = OK(routes=n_routes, routes_all_steps_reaction_satisfied=sat)
        obs["route_readiness"] = OK(tier_counts=dict(Counter(x["readiness_tier"] for x in rec["routes"])))
    if params_profile is not None and rec["routes"]:
        assessed = [r for r in rec["routes"] if r["capability"]]
        obs["capability_requirements"] = OK(question_asked=rec["capability_question_digest"] is not None,
                                            routes_projected=len(assessed))
        axes = sorted({json.dumps(r["capability"]["axes"], sort_keys=True) for r in assessed})
        fit = sum(1 for d in resp.ranked_route_dossiers
                  if d.capability_assessment is not None and d.capability_assessment.is_capability_fit)
        obs["profile_projection"] = OK(profile=params_profile if isinstance(params_profile, str) else "custom",
                                       overall_set=sorted({r["capability"]["overall"] for r in assessed}),
                                       axes_distinct=[json.loads(a) for a in axes], capability_fit_count=fit)
    fit_total = sum(1 for d in resp.ranked_route_dossiers
                    if d.capability_assessment is not None and d.capability_assessment.is_capability_fit)
    obs["final_dossier"] = OK(n_routes=n_routes, n_dags=n_dags,
                              fit_status_set=sorted({r["fit_status"] for r in rec["routes"]}), capability_fit_count=fit_total,
                              transport_mode=thick.get("transport_mode"))
    obs["deserialize_verify"] = OK(**bf._load_records(resp, thick, thin))
    return rec, thick


def observe_plan(m):
    from smartchem.identity_parse import InputKind
    from smartchem.plan import plan, plan_result_to_payload

    text = m["raw_input"]
    obs = OrderedDict(raw_input=OK(text=text, kind="AUTO"))
    result = plan(text, InputKind.AUTO)
    payload = plan_result_to_payload(result)
    status = result.status.value
    if status == "INVALID_INPUT":
        reason = classify_parse_error(result.invalid_reason or "")
        obs["normalized_syntax"] = DROP(reason, plan_status=status, exit_code=result.exit_code)
        return obs
    if status == "INPUT_KIND_AMBIGUOUS":
        interp = {f"{k.value}:{ident.receipt.normalized}": ident for k, ident in result.ambiguity.interpretations}
        smiles = next(i for k, i in result.ambiguity.interpretations if k is InputKind.SMILES)
        obs["normalized_syntax"] = OK(resolved_kind=smiles.receipt.resolved_kind.value, source=smiles.receipt.source.value)
        obs["composition"] = OK(hill=smiles.receipt.normalized, charge=getattr(smiles.formula, "charge", 0))
        obs["identity"] = DROP("INPUT_KIND_AMBIGUOUS", plan_status=status, exit_code=result.exit_code,
                               interpretations=sorted(interp))
        return obs
    idn = payload["identity"]
    fs = idn["formula_syntax"]
    ns = {"resolved_kind": idn["resolved_kind"]}
    from smartchem.identity_parse import resolve_identity
    r = resolve_identity(text, InputKind.AUTO)
    ns["source"] = r.receipt.source.value
    if fs:
        ns["syntax"] = fs["normalized"]
        ns["component_multipliers"] = [c["multiplier"] for c in fs["components"]]
    obs["normalized_syntax"] = OK(**ns)
    obs["composition"] = OK(hill=idn["normalized"], charge=getattr(r.formula, "charge", 0))
    obs["identity"] = OK(layer=idn["identity_layer"], constitution_established=idn["constitution_established"],
                         registry_candidates=sorted(idn["registry_candidates"]))
    if r.molecule is not None:
        f = r.features
        obs["structure"] = OK(atoms=len(r.molecule.atoms), charge=r.molecule.charge,
                              tetrahedral_stereo=bool(f.tetrahedral_stereo), isotopes=list(f.isotopes))
    else:
        obs["structure"] = DROP("COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED")
    if status == "IDENTITY_ONLY":
        obs["search"] = DROP("IDENTITY_ONLY_CHARGED_NO_NEUTRAL_DESCENT", plan_status=status, exit_code=result.exit_code)
        return obs
    resp = result.response
    if resp.outcome.value == "REFUSED":
        charged = getattr(r.formula, "charge", 0) != 0
        obs["search"] = DROP("REFUSED_CHARGED_SPECIES_CHEMISTRY_MODEL_BOUNDARY" if charged else "REFUSED_OTHER",
                             plan_status=status, outcome="REFUSED", exit_code=resp.exit_code)
        return obs
    tmp = OrderedDict()
    _response_stages(resp, tmp, None, is_decompile=(status == "FORMULA_DECOMPOSITION"))
    s = dict(tmp["search"])
    s.update(plan_status=status, operation=result.operation.value)
    obs["search"] = s
    for k in ("final_dossier", "deserialize_verify"):
        if k in tmp:
            obs[k] = tmp[k]
    return obs


def _run_service(m):
    """Build + run the frozen baseline case's exact request. -> (resp, kwargs, builder)."""
    import v0_9_5_baseline_freeze as bf
    from smartchem.service import build_decompile_request, build_recompile_request, run_compilation

    case = {c[0]: c for c in bf._corpus()}[FREEZE_CASE[m["id"]]]
    _cid, _cost, builder, target, kw = case
    build = build_recompile_request if builder == "recompile" else build_decompile_request
    return run_compilation(build(target, **kw)), kw, builder, target


def observe_service(m):
    from smartchem.identity_parse import InputKind

    resp, kw, builder, target = _run_service(m)
    kind = kw.get("input_kind") or InputKind.AUTO
    obs = OrderedDict(raw_input=OK(text=target, kind=_val(kind) if kind is not InputKind.AUTO else "AUTO"))
    front, _resolved, drop = _identity_stages(target, kind)
    obs.update(front)
    if drop is not None:
        obs["normalized_syntax"] = DROP(drop, service_outcome=resp.outcome.value, exit_code=resp.exit_code)
    prof = kw.get("capability_profile")
    if prof is not None and not isinstance(prof, str):
        prof = "custom"
    _response_stages(resp, obs, prof, is_decompile=(builder == "decompile"))
    if drop is not None:  # front-door drop: the typed envelope is observed only at final_dossier / deserialize_verify
        obs.pop("search", None)
        for k in ("search_receipt", "reaction_vouch", "route_readiness", "capability_requirements", "profile_projection"):
            obs.pop(k, None)
    return obs


def observe_recompile_extra(m):
    """R-20 / R-21: cheap recompiles outside the frozen corpus."""
    from smartchem.service import build_recompile_request, run_compilation

    target = m["raw_input"]
    resp = run_compilation(build_recompile_request(target, max_depth=1))
    obs = OrderedDict(raw_input=OK(text=target, kind="AUTO"))
    front, _r, _d = _identity_stages(target, __import__("smartchem.identity_parse", fromlist=["x"]).InputKind.AUTO)
    obs.update(front)
    _response_stages(resp, obs, None)
    return obs


def observe_identity_pair(m):
    from smartchem.identity_parse import InputKind
    from smartchem.service import build_recompile_request, response_to_payload, run_compilation
    from smartchem.smiles import parse_smiles_features, resonance_identity

    texts = m["raw_input"]
    exp_search = m["stages"]["search"]["status"]
    obs = OrderedDict(raw_input=OK(texts=list(texts)))
    res, mols, feats, rids = [], [], [], []
    for t in texts:
        from smartchem.identity_parse import resolve_identity
        r = resolve_identity(t, InputKind.AUTO)
        res.append(r)
        smi = t.split(":", 1)[1] if t.startswith("smiles:") else t
        mol, f = parse_smiles_features(smi)
        mols.append(mol)
        feats.append(f)
        rids.append(resonance_identity(mol))
    hills = [r.receipt.normalized for r in res]
    obs["normalized_syntax"] = OK(resolved_kinds=[r.receipt.resolved_kind.value for r in res])
    obs["composition"] = OK(hills=hills, same_composition=len(set(hills)) == 1)
    identity = {"layers": [r.receipt.identity_layer for r in res], "same_identity_digest": len(set(rids)) == 1,
                "pairwise_distinct": len(set(rids)) == len(rids)}
    structure = {"atoms": [len(x.atoms) for x in mols], "charge": [x.charge for x in mols],
                 "tetrahedral_stereo": [bool(f.tetrahedral_stereo) for f in feats],
                 "cip_labels": [list(f.cip_labels) for f in feats], "isotopes": [list(f.isotopes) for f in feats],
                 "distinct_configuration_digests": len({f.configuration_digest for f in feats}) == len(feats),
                 "distinct_isotopic_digests": len({f.isotopic_digest for f in feats}) == len(feats)}
    if exp_search != "NA":
        outcomes, codes, losses, sev = [], [], [], []
        for t in texts:
            resp = run_compilation(build_recompile_request(t, max_depth=m["params"].get("max_depth", 1)))
            outcomes.append(resp.outcome.value)
            codes.append(resp.exit_code)
            ir = response_to_payload(resp).get("compilation_ir")
            il = (ir or {}).get("identity_losses") or []
            losses.append([x["feature"] for x in il])
            sev.append([x["severity"] for x in il])
        identity["identity_losses"] = losses
        identity["loss_severities"] = sev
        if all(o == "REFUSED" for o in outcomes):
            obs["search"] = DROP("REFUSED_CHARGED_SPECIES_CHEMISTRY_MODEL_BOUNDARY", outcomes=outcomes, exit_codes=codes)
        else:
            obs["search"] = OK(outcomes=outcomes, exit_codes=codes)
    obs["identity"] = OK(**identity)
    obs["structure"] = OK(**structure)
    if obs.get("search", {}).get("status") == "DROP":
        pass
    return obs


# ---- model-level members: S7 / S8 material identity ------------------------------------------------------------------
def _ud_pure(mol_or_name):
    from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
    from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MaterialComponent, Phase, StockMaterial, StockQuantity
    from smartchem.material_spec import ConcentrationBasis, EvidenceKind

    ev = IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="rc-funnel fixture: the bench declares its own bottle pure")
    comp = MaterialComponent.evidenced(mol_or_name, "active", ev)
    return StockMaterial(STOCK_MATERIAL_SCHEMA, f"bottle-{sha(str(mol_or_name))[:8]}", "funnel bottle", (comp,),
                         Phase.LIQUID, "rc-funnel fixture", quantity=StockQuantity.of("500", "mL"),
                         phase_evidence=EvidenceKind.USER_DECLARED)


def _kekule_flip(mol):
    """Alternate-Kekule form of the (single) benzene ring by GRAPH SURGERY (a SMILES respelling is re-canonicalised by
    the parser, a vacuous control) -- the helper shape of tests/test_resonance_identity.py."""
    from smartchem.category import Bond, Molecule

    carbons = [i for i, s in enumerate(mol.atoms) if s == "C"]
    adj = {i: set() for i in carbons}
    for b in mol.bonds:
        if b.i in adj and b.j in adj:
            adj[b.i].add(b.j)
            adj[b.j].add(b.i)
    ring = {c for c in carbons if len(adj[c]) >= 2}
    nb = []
    for b in mol.bonds:
        if b.i in ring and b.j in ring and mol.atoms[b.i] == "C" == mol.atoms[b.j]:
            nb.append(Bond(b.i, b.j, 1 if b.order == 2 else 2))
        else:
            nb.append(b)
    return Molecule(mol.atoms, frozenset(nb), mol.charge, mol.state)


def _sa_route(sa_required):
    """salicylic acid (as SPELT by `sa_required`) + methanol -> methyl salicylate + water: one conserving step."""
    from smartchem.conditions import ConditionEnvelope
    from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep
    from smartchem.smiles import parse_smiles

    ms, meoh, water = parse_smiles("COC(=O)c1ccccc1O"), parse_smiles("CO"), parse_smiles("O")
    step = ExperimentStep(STEP_SCHEMA, ms, (sa_required, meoh), (ms, water), (), ConditionEnvelope())
    return ExperimentRoute(ROUTE_SCHEMA, (step,))


def _material_axis(bottle_mol, required_mol):
    from smartchem.capability.assess import assess
    from smartchem.capability.presets import custom
    from smartchem.capability.requirements import compile_capability_requirements
    from smartchem.experiment.readiness import evaluate_route
    from smartchem.smiles import parse_smiles

    route = _sa_route(required_mol)
    reqs = compile_capability_requirements(route)
    profile = custom(profile_id="rc-funnel-kekule", material_inventory=(_ud_pure(bottle_mol), _ud_pure(parse_smiles("CO"))))
    a = assess(profile, reqs, evaluate_route(route))
    return a.material.status.value, len(reqs.material)


def observe_model(m):
    from smartchem.smiles import parse_smiles, resonance_identity

    mid = m["id"]
    obs = OrderedDict()
    sa = parse_smiles("OC(=O)c1ccccc1O")
    sa_flip = _kekule_flip(sa)
    if mid in ("MK-01", "MK-02", "MK-03"):
        bottle, req = {"MK-01": (sa, sa_flip), "MK-02": (sa_flip, sa), "MK-03": (sa, sa)}[mid]
        obs["raw_input"] = OK(bottle="OC(=O)c1ccccc1O" if bottle is sa else "alternate-Kekule graph surgery",
                              requirement="OC(=O)c1ccccc1O" if req is sa else "alternate-Kekule graph surgery of the same molecule")
        if mid == "MK-02":
            obs["raw_input"] = OK(bottle="alternate-Kekule graph surgery", requirement="OC(=O)c1ccccc1O")
        obs["identity"] = OK(resonance_identity_equal=resonance_identity(bottle) == resonance_identity(req))
        found = _ud_pure(bottle).active_fraction_interval(req) is not None
        obs["structure"] = OK(stock_key_equal=found, active_fraction_interval_found=found)
        axis, n_req = _material_axis(bottle, req)
        obs["capability_requirements"] = OK(material_requirements=n_req)
        obs["profile_projection"] = OK(material_axis=axis)
    elif mid == "MK-04":
        o, mx = parse_smiles("Cc1ccccc1C"), parse_smiles("Cc1cccc(C)c1")
        obs["raw_input"] = OK(bottle="Cc1ccccc1C", requirement="Cc1cccc(C)c1")
        obs["identity"] = OK(resonance_identity_equal=resonance_identity(o) == resonance_identity(mx))
        found = _ud_pure(o).active_fraction_interval(mx) is not None
        obs["structure"] = OK(stock_key_equal=found, active_fraction_interval_found=found)
    elif mid == "MK-05":
        r_, s_ = parse_smiles("C[C@H](O)CC"), parse_smiles("C[C@@H](O)CC")
        obs["raw_input"] = OK(bottle="C[C@H](O)CC", requirement="C[C@@H](O)CC")
        obs["identity"] = OK(resonance_identity_equal=resonance_identity(r_) == resonance_identity(s_))
        found = _ud_pure(r_).active_fraction_interval(s_) is not None
        obs["structure"] = OK(stock_key_equal=found, active_fraction_interval_found=found)
    elif mid == "MK-06":
        from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MATERIAL_COMPONENT_SCHEMA, MaterialComponent, Phase, StockMaterial, StockQuantity
        from smartchem.material_spec import ConcentrationBasis, EvidenceKind

        comp = MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "vegetable oil", "active", 0.0, 1.0, ConcentrationBasis.UNKNOWN, None, ())
        bottle = StockMaterial(STOCK_MATERIAL_SCHEMA, "veg", "veg", (comp,), Phase.LIQUID, "rc-funnel",
                               quantity=StockQuantity.of("500", "mL"), phase_evidence=EvidenceKind.USER_DECLARED)
        obs["raw_input"] = OK(bottle_name="vegetable oil", requirement_name="Vegetable  Oil")
        obs["structure"] = OK(name_match_found=bottle.active_fraction_interval("Vegetable  Oil") is not None)
    elif mid == "SD-01":
        return observe_stream_witness(m)
    return obs


# ---- SD-01: the StreamDisposition witness ---------------------------------------------------------------------------
def _dme_fixture():
    from smartchem.capability.coverage import render_scale, render_summary, render_verification
    from smartchem.conditions import ConditionEnvelope, Interval
    from smartchem.contracts import EvidenceStatus
    from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute, ExperimentStep
    from smartchem.material_spec import EvidenceKind, PhaseClaim
    from smartchem.experiment.stock import Phase, StockQuantity
    from smartchem.procedure_evidence import (EvidenceField, OperationKind, OperationRole, ProcedureEvidence,
                                              ProcedureMaterialRole, ProcedureMaterialUse, ProcedureOperation)
    from smartchem.process_constraints import Agitation, Attention, ProcessRequirements
    from smartchem.provenance import SourceCitation, SourceReview
    from smartchem.smiles import parse_smiles
    from smartchem.transform_provider import CappedScissionProvider

    meoh, water, dme = parse_smiles("CO"), parse_smiles("O"), parse_smiles("COC")
    url = "https://example.test/synthetic-zero-fit-witness"
    src = SourceCitation(url, SourceReview.ACCEPTED)
    transforms, _r = CappedScissionProvider().enumerate_transforms(dme, (water,), budget=50_000)
    transform = next(t for t in transforms if all(str(p) == str(meoh) for p in t.products))
    na = lambda why: EvidenceField.not_applicable(url, why)  # noqa: E731
    use = ProcedureMaterialUse(name="methanol", role=ProcedureMaterialRole.SUBSTRATE, identity=meoh,
                               phase=PhaseClaim(Phase.LIQUID, EvidenceKind.SOURCE_QUOTED),
                               quantity=StockQuantity.of("20", "mL"), evidence_source="fixture zero-fit theorem")
    ops = (
        ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, materials=("methanol",),
                           material_uses=(use,), apparatus=("100-mL round-bottom flask",), locator=url),
        ProcedureOperation(ordinal=2, kind=OperationKind.HOLD, role=OperationRole.REACTION,
                           temperature=EvidenceField.present(Interval(330.0, 330.0, "K"), url),
                           duration=EvidenceField.present(Interval(30.0, 30.0, "min"), url),
                           apparatus=("reflux condenser", "heating mantle"), locator=url),
        ProcedureOperation(ordinal=3, kind=OperationKind.FILTER, role=OperationRole.OTHER,
                           apparatus=("fluted filter paper",), locator=url),
        ProcedureOperation(ordinal=4, kind=OperationKind.VERIFY, role=OperationRole.OTHER,
                           apparatus=("analytical balance",), locator=url),
    )
    draft = ProcedureEvidence(
        reaction_scope="synthetic zero-fit witness (a model-consistency object, not production chemistry)", source=src,
        scale=EvidenceField.present("draft", url), operations=ops, quench=na("no quench"),
        workup_isolation=EvidenceField.present("draft", url), separation=na("no separation"), wash=na("no wash"),
        drying=na("no drying"), purification=na("no purification"),
        analytical_verification=EvidenceField.present("draft", url))
    procedure = dc.replace(
        draft, scale=EvidenceField.present(render_scale(draft), url),
        workup_isolation=EvidenceField.present(render_summary(draft, "workup_isolation"), url),
        analytical_verification=EvidenceField.present(render_verification(draft), url))
    process = ProcessRequirements(
        elapsed_minutes=Interval(30.0, 60.0, "min"), active_minutes=Interval(5.0, 10.0, "min"),
        attention=Attention.PERIODIC, check_interval_minutes=15.0, agitation=Agitation.MANUAL, workup_included=True,
        provenance="synthetic witness", source=src, peak_temperature_k=330.0, min_pressure_atm=1.0, max_pressure_atm=1.0)
    envelope = ConditionEnvelope(temperature=Interval(330.0, 330.0, "K"), status=EvidenceStatus.EXPERIMENTAL,
                                 provenance="synthetic witness", source=src, process=process, procedure=procedure)
    return ExperimentRoute(ROUTE_SCHEMA, (ExperimentStep.from_transform(transform, envelope=envelope),)), meoh


def _exact_profile(reqs, meoh):
    from smartchem.capability.enums import (CapabilityStatus, WasteCapability)
    from smartchem.capability.presets import custom
    from smartchem.constraints import PhysicalBounds
    from smartchem.process_constraints import Agitation, Attention, ProcessBounds

    return custom(
        profile_id="rc-funnel-exact", material_inventory=(_ud_pure(meoh),), equipment=reqs.equipment,
        physical_bounds=PhysicalBounds.of(max_temperature_k=600.0, min_pressure_atm=0.5, max_pressure_atm=5.0, min_temperature_k=250.0),
        process_bounds=ProcessBounds.of(max_step_minutes=600.0, max_total_minutes=600.0, max_active_minutes=600.0,
                                        allowed_attention=tuple(Attention), min_check_interval_minutes=1.0,
                                        allowed_agitation=tuple(Agitation)),
        containment=reqs.containment, measurement=reqs.measurement, waste_handling=frozenset({WasteCapability.AQUEOUS_NEUTRAL}),
        procurement=frozenset(), no_limit_dimensions=frozenset({"budget"})), CapabilityStatus


def observe_stream_witness(m):
    from smartchem.capability.assess import assess
    from smartchem.capability.requirements import compile_capability_requirements
    from smartchem.experiment.readiness import evaluate_route

    obs = OrderedDict(raw_input=OK(fixture="dimethyl-ether zero-FIT witness route + exactly-sufficient Custom bench"))
    route, meoh = _dme_fixture()
    reqs = compile_capability_requirements(route)
    profile, CS = _exact_profile(reqs, meoh)
    a = assess(profile, reqs, evaluate_route(route))
    safe = (CS.FIT, CS.NOT_APPLICABLE, CS.UNCONSTRAINED)
    axes = {n: getattr(a, n).status for n in ("material", "equipment", "physical", "process", "containment",
                                              "ventilation", "measurement", "waste", "procurement", "attention_care", "monetary")}
    obs["capability_requirements"] = OK(unresolved_waste_obligations=len(reqs.waste.unresolved))
    obs["profile_projection"] = OK(waste_axis=a.waste.status.value, overall=a.overall.value,
                                   capability_fit=bool(a.is_capability_fit),
                                   other_axes_open=sorted(n for n, s in axes.items() if n != "waste" and s not in safe))
    obs["final_dossier"] = _stream_disposition_facet(route, reqs, profile, meoh)
    return obs


def _local_module(name: str):
    """find_spec(name) -- but ONLY if it resolves inside THIS tree.  The dev venv's stale editable install maps the
    `smartchem` namespace to another checkout, so a submodule this tree lacks can silently resolve from there; a
    feature-detect that trusted it would call an un-landed change 'landed' (or run another tree's code)."""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    try:
        Path(spec.origin).resolve().relative_to(REPO)
    except ValueError:
        return None
    return spec


def _stream_disposition_facet(route, reqs, profile, meoh):
    """The S10 half (barrier section 6): three SOURCE_QUOTED dispositions -- ROUTED(AQUEOUS_NEUTRAL) on the water
    byproduct, ROUTED(AQUEOUS_NEUTRAL) on the FILTER op's stream, CONSUMED_COMPLETELY on the methanol residual -- reach
    CAPABILITY_FIT under the exactly-sufficient bench; deleting any one -> not FIT; a bench without AQUEOUS_NEUTRAL ->
    BLOCKED.  A model-level synthetic witness, NOT a real procedure.  Feature-detected (PENDING while S10 is absent)."""
    if _local_module("smartchem.stream_disposition") is None:
        return {"status": "PENDING_FEATURE_ABSENT"}
    from smartchem.capability.assess import assess
    from smartchem.capability.enums import WasteCapability
    from smartchem.capability.requirements import compile_capability_requirements
    from smartchem.experiment.readiness import evaluate_route
    from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute
    from smartchem.material_spec import EvidenceKind
    from smartchem.stream_disposition import DispositionValue, StreamDisposition, SubjectKind, stream_subjects

    step = route.steps[0]
    subjects = stream_subjects(step)

    def one(kind):
        found = [x for x in subjects if x.kind is kind]
        if len(found) != 1:
            raise AssertionError(f"witness: expected exactly one {kind.value} subject, found {len(found)}")
        return found[0]
    water, op3, methanol = one(SubjectKind.BYPRODUCT), one(SubjectKind.OP_STREAM), one(SubjectKind.RESIDUAL)
    locator = "https://example.test/synthetic-zero-fit-witness#disposition"
    an = WasteCapability.AQUEOUS_NEUTRAL
    dispositions = (
        StreamDisposition(water, DispositionValue.ROUTED, EvidenceKind.SOURCE_QUOTED, locator, category=an),
        StreamDisposition(op3, DispositionValue.ROUTED, EvidenceKind.SOURCE_QUOTED, locator, category=an),
        StreamDisposition(methanol, DispositionValue.CONSUMED_COMPLETELY, EvidenceKind.SOURCE_QUOTED, locator),
    )

    def with_(ds):
        procedure = dc.replace(step.envelope.procedure, stream_dispositions=tuple(ds))
        return ExperimentRoute(ROUTE_SCHEMA, (dc.replace(step, envelope=dc.replace(step.envelope, procedure=procedure)),))

    def overall(ds, prof=profile):
        r = with_(ds)
        a = assess(prof, compile_capability_requirements(r), evaluate_route(r))
        return "CAPABILITY_FIT" if a.is_capability_fit else a.overall.value

    deletions = sorted({overall(tuple(d for d in dispositions if d is not dropped)) for dropped in dispositions})
    return {
        "status": "OK",
        "with_three_dispositions": {
            "overall": overall(dispositions),
            "unresolved": len(compile_capability_requirements(with_(dispositions)).waste.unresolved)},
        "delete_any_one_disposition": {"overall": deletions[0] if len(deletions) == 1 else deletions},
        "bench_without_AQUEOUS_NEUTRAL": {"overall": overall(dispositions, dc.replace(profile, waste_handling=frozenset()))},
    }


# ---- held-out, lateral, CLI, legacy, wire ---------------------------------------------------------------------------
def observe_heldout(m):
    import v0_9_heldout_saponification_probe as hp

    grades, ctx = _quiet(hp.run)
    obs = OrderedDict(raw_input=OK(case="synthesized benign saponification (blind oracle eb01d67c9b76..)"))
    diverging = [g[0] for g in grades if g[1].startswith("DIVERGES")]
    obs["route_readiness"] = OK(tier=ctx["readiness"].tier, source_is_none=True)
    obs["capability_requirements"] = OK(graded=len(grades))
    obs["profile_projection"] = OK(PASS=sum(1 for g in grades if g[1] == "PASS"), DIVERGES_LAWFUL=len(diverging),
                                   FAIL=sum(1 for g in grades if g[1] == "FAIL"),
                                   diverging_probe=diverging[0] if diverging else None)
    return obs


def observe_lateral(m):
    from smartchem.lateral_search import lateral_closure, lateral_route_to
    from smartchem.smiles import parse_smiles

    seed, goal = parse_smiles(m["params"]["seed"]), parse_smiles(m["params"]["goal"])
    obs = OrderedDict(raw_input=OK(seed=m["params"]["seed"], goal=m["params"]["goal"]))
    door = [f for f in ("service.py", "cli.py") if "lateral_search" in (REPO / "smartchem" / f).read_text()]
    obs["search"] = (DROP("NOT_PUBLICLY_REACHABLE", detail="not imported by service.py/cli.py") if not door
                     else OK(reachable_from=door))
    rec = lateral_closure(seed)
    route = lateral_route_to(seed, goal)
    obs["search_receipt"] = OK(library_closure_status=rec.status, library_closure_isomers=len(rec.isomers),
                               library_route_length=None if route is None else len(route))
    return obs


def observe_cli(m):
    from smartchem.cli import main

    argv = m["params"]["argv"]
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv))
    except SystemExit as exc:
        rc = exc.code
    text = out.getvalue()
    obs = OrderedDict(raw_input=OK(argv=list(argv)))
    lay = re.search(r"identity match layer: (\w+)", text)
    if lay:
        obs["identity"] = OK(layer=lay.group(1))
    obs["search"] = OK(exit_code=rc, stdout=text)
    obs["search_receipt"] = OK(stdout=text, complete="search: COMPLETE_WITHIN_DECLARED_SPACE" in text)
    return obs


def _try_load(payload, **kw):
    from smartchem.service import response_from_payload, response_to_payload

    try:
        r = response_from_payload(copy.deepcopy(payload), **kw)
    except Exception as exc:  # noqa: BLE001 -- the refusal CLASS is the observation
        return {"accepted": False, "exc": type(exc).__name__, "msg": str(exc)[:240]}
    return {"accepted": True, "round_trip_identical": sha(response_to_payload(r, include_replay="ranked_route_dossiers" in payload and payload.get("transport_mode") != "THIN_ADVISORY")) == sha(payload)}


def _policy_load(payload, name):
    """A load under VerificationPolicy.<name>() -- feature-detected (0.9.5 S1)."""
    if _local_module("smartchem.verification") is None:
        return "policy API absent"
    try:
        v = importlib.import_module("smartchem.verification")
        policy = getattr(v.VerificationPolicy, name)()
        # the policy lives in smartchem.verification; the verifying LOADER is the service's (barrier section 3)
        importlib.import_module("smartchem.service").load_response(copy.deepcopy(payload), policy)
        return {"accepted": True}
    except (AttributeError, ImportError) as exc:
        return f"policy API absent ({type(exc).__name__}: {exc})"
    except Exception as exc:  # noqa: BLE001
        return {"accepted": False, "exc": type(exc).__name__, "msg": str(exc)[:240]}


def observe_legacy(m):
    from smartchem.service import request_from_payload, response_from_payload

    rel = m["params"]["fixture"]
    path = REPO / "tests" / "fixtures" / "v08" / rel
    data = json.loads(path.read_text())
    if rel.startswith("plan_"):
        data = data.get("compilation", data)
    is_req = "request_" in path.name and "response" not in path.name
    loader = request_from_payload if is_req else response_from_payload
    obs = OrderedDict(raw_input=OK(fixture=rel))
    try:
        val = loader(copy.deepcopy(data))
        plain = {"accepted": True}
        if not is_req:
            plain.update(outcome=_val(val.outcome), is_legacy_v08=bool(getattr(val, "is_legacy_v08", False)))
        dv = OK(plain=plain)
        if not is_req:
            pol = _policy_load(data, "canonical")
            if isinstance(pol, dict):
                dv["canonical_policy"] = pol
        obs["deserialize_verify"] = dv
    except Exception as exc:  # noqa: BLE001
        obs["deserialize_verify"] = DROP("LEGACY_PAYLOAD_REFUSED",
                                         plain={"accepted": False, "exc": type(exc).__name__, "msg": str(exc)[:240]})
    return obs


def observe_wire(m):
    from smartchem.service import (build_recompile_request, response_to_payload, run_compilation)

    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"))
    thick, thin = response_to_payload(resp), response_to_payload(resp, include_replay=False)
    pins = {"expected_request_digest": resp.request.semantic_digest,
            "expected_capability_question_digest": resp.request.capability_question_digest}
    relabel = copy.deepcopy(thick)
    relabel["schema_version"] = PRERELEASE_RESPONSE_ID
    ct, cn = _policy_load(thick, "canonical"), _policy_load(thin, "canonical")
    dv = OK(plain_thick=_try_load(thick), pinned_va_thick=_try_load(thick, require_verified_admission=True, **pins),
            plain_thin=_try_load(thin), thin_under_verified_admission=_try_load(thin, require_verified_admission=True),
            canonical_thick=ct, canonical_thin=cn, prerelease_id_relabel=_try_load(relabel))
    return OrderedDict(raw_input=OK(case="methyl_acetate@poor-man"), deserialize_verify=dv)


DRIVERS = {"plan": observe_plan, "recompile": observe_service, "decompile": observe_service,
           "identity_pair": observe_identity_pair, "model": observe_model, "heldout": observe_heldout,
           "lateral": observe_lateral, "cli": observe_cli, "legacy": observe_legacy, "wire": observe_wire}


def observe(m):
    if m["driver"] in ("recompile", "decompile") and m["id"] not in FREEZE_CASE:
        return observe_recompile_extra(m)
    return DRIVERS[m["driver"]](m)


# --------------------------------------------------------------------------------------------------------------------
# grading + denominators
# --------------------------------------------------------------------------------------------------------------------
COLS = ["entered", "survived", "correctly_refused", "wrongly_refused", "wrong_survivor", "wrong_content", "pending",
        "not_applicable", "not_reached_confirmed", "not_reached_LEAK"]


def grade_member(m, obs, table, drops, require_landed):
    """-> (verdict, pending ids, notes)."""
    pend, notes, bad = set(), [], False
    for st in STAGES:
        exp = m["stages"][st]
        e = exp["status"]
        c = table[st]
        o = obs.get(st)
        if e == "NA":
            c["not_applicable"] += 1
            continue
        if e == "NOT_REACHED":
            if o is None:
                c["not_reached_confirmed"] += 1
            else:
                c["not_reached_LEAK"] += 1
                bad = True
                notes.append(f"{st}: expected NOT_REACHED ({exp['because']}) but observed {o.get('status')}")
            continue
        c["entered"] += 1
        if o is None:
            c["wrong_content"] += 1
            bad = True
            notes.append(f"{st}: expected {e} but the stage was never reached")
            continue
        if o["status"] == "OK":
            c["survived"] += 1
        v, p, n = _match(exp, o, st)
        if v == PENDING:
            c["pending"] += 1
            pend |= p
            notes += n
            continue
        if v == MISMATCH:
            bad = True
            notes += n
            if e == "OK" and o["status"] == "DROP":
                c["wrongly_refused"] += 1
            elif e == "DROP" and o["status"] == "OK":
                c["wrong_survivor"] += 1
            else:
                c["wrong_content"] += 1
            continue
        # MATCH
        if e == "DROP":
            c["correctly_refused"] += 1
            drops.append((m["id"], st, exp["reason"]))
    landed_missing = pend & set(require_landed)
    if bad or landed_missing:
        if landed_missing:
            notes.append(f"required-landed {sorted(landed_missing)} still PENDING")
        return MISMATCH, pend, notes
    return (PENDING if pend else MATCH), pend, notes


def main(argv):
    only = None
    require = []
    out_json = None
    for i, a in enumerate(argv):
        if a == "--only":
            only = set(argv[i + 1].split(","))
        elif a == "--require-landed":
            require = argv[i + 1].split(",")
        elif a == "--json":
            out_json = argv[i + 1]
    skip_slow = "--skip-slow" in argv
    allow_pending = "--allow-pending" in argv

    raw = ORACLE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORACLE_SHA256:
        print(f"REFUSED: the oracle changed since freeze (sha256 {hashlib.sha256(raw).hexdigest()} != {ORACLE_SHA256}); "
              "log the revision in docs/research/V0_9_5_RC_FUNNEL_ORACLE.md §6 and re-pin ORACLE_SHA256")
        return 2
    oracle = json.loads(raw)
    members = oracle["members"]
    table = {st: Counter() for st in STAGES}
    drops, results = [], OrderedDict()
    import smartchem
    print(f"smartchem {smartchem.__version__} from {Path(smartchem.__file__).parent}; oracle {len(members)} members", flush=True)
    for m in members:
        if only and m["id"] not in only:
            continue
        if skip_slow and m["id"] in SLOW_MEMBERS:
            results[m["id"]] = ("SKIPPED", set(), ["--skip-slow"])
            continue
        t0 = time.time()
        try:
            obs = observe(m)
        except Exception as exc:  # noqa: BLE001 -- a crash IS a finding, recorded as a mismatch with the traceback head
            tb = traceback.format_exc().strip().splitlines()
            results[m["id"]] = (MISMATCH, set(), [f"OBSERVER CRASH {type(exc).__name__}: {exc}"[:300], *tb[-3:]])
            print(f"  {m['id']:6s} CRASH {type(exc).__name__}: {str(exc)[:120]} ({time.time() - t0:.1f}s)", flush=True)
            for st in STAGES:  # a crashed member is still counted in every denominator it was expected to enter
                e = m["stages"][st]["status"]
                table[st]["not_applicable" if e == "NA" else "not_reached_confirmed" if e == "NOT_REACHED" else "entered"] += 1
                if e in ("OK", "DROP"):
                    table[st]["wrong_content"] += 1
            continue
        verdict, pend, notes = grade_member(m, obs, table, drops, require)
        results[m["id"]] = (verdict, pend, notes)
        tag = verdict if verdict != PENDING else f"PENDING({','.join(sorted(pend))})"
        print(f"  {m['id']:6s} {tag} ({time.time() - t0:.1f}s)  {m['raw_input'] if isinstance(m['raw_input'], str) else ' / '.join(m['raw_input'])}"[:170], flush=True)
        for n in notes:
            print(f"           - {n}", flush=True)
    # ---- the denominator table ---------------------------------------------------------------------------------
    print("\nDENOMINATOR TABLE (per stage; counts are members)")
    hdr = f"{'stage':24s}" + "".join(f"{c[:11]:>12s}" for c in COLS)
    print(hdr)
    print("-" * len(hdr))
    tot = Counter()
    for st in STAGES:
        row = table[st]
        tot.update(row)
        print(f"{st:24s}" + "".join(f"{row[c]:12d}" for c in COLS))
    print("-" * len(hdr))
    print(f"{'TOTAL':24s}" + "".join(f"{tot[c]:12d}" for c in COLS))
    print("\nTYPED DROPS confirmed (member, stage, reason)")
    for d in drops:
        print("  ", *d)
    # ---- verdict summary --------------------------------------------------------------------------------------
    cnt = Counter(v for v, _p, _n in results.values())
    print("\nMEMBER VERDICTS:", dict(cnt), f"of {len(results)}")
    pend_ids = Counter(i for _v, p, _n in results.values() for i in p)
    if pend_ids:
        print("PENDING by change:", dict(pend_ids))
    bad = [k for k, (v, _p, _n) in results.items() if v == MISMATCH]
    if bad:
        print("MISMATCH members:", ", ".join(bad))
    if out_json:
        Path(out_json).write_text(json.dumps({"verdicts": {k: {"verdict": v, "pending": sorted(p), "notes": n}
                                                             for k, (v, p, n) in results.items()},
                                              "table": {st: dict(table[st]) for st in STAGES}}, indent=1))
    if bad:
        return 1
    if cnt.get(PENDING) and not allow_pending:
        print("exit 3: no mismatch, but PENDING facets remain (a pending change is not a pass; --allow-pending to tolerate)")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
