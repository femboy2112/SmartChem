"""OPERATION XXV, post-3.0 explorer checkpoint P1: renderer-neutral ExplorationSpec / ExplorationReceipt prototype.

RESEARCH PROTOTYPE, NOT THE EXPLORER. Offline, no UI dependency, no simulator execution, no production change.
The compiler is the authority: ``explore`` calls only the stable public entry points
(``build_recompile_request``, ``run_compilation``, ``response_to_payload``) and COPIES typed verdict words out of
the production wire payload. Nothing here derives chemistry, recognizes a reaction class, or estimates anything.

Design rules enforced here (and pinned by tests/test_xxv_exploration.py):
  * verdict axes stay SEPARATE and typed; there is no aggregate score and no single "true"/"safe" field;
  * a no-route answer under an incomplete search reads INCOMPLETE, never IMPOSSIBLE (the word never appears);
  * a wire field that is absent or unrecognized becomes UNKNOWN (fail closed), never a guess;
  * simulation is NOT_RUN / REFERENCED_NOT_RUN (a ref is carried, never executed); empirical validation is always
    UNVERIFIED; visualization is PROJECTION_ONLY;
  * the receipt stores its body as canonical JSON text and hands out fresh copies, so a consumer (or a renderer)
    mutating a returned dict cannot touch the receipt or its digest;
  * ``result_digest`` is version-bound (COMPATIBILITY section 2.2): the receipt digest is therefore not stable across
    package releases. The request ``semantic_digest`` is the version-stable search identity and is bound separately.

Identity scope (COMPATIBILITY section 5; docs/research/IDENTITY_CARRIER_DESIGN_XXV.md): only the CONSTITUTION layer
is supported. CONFIGURATION / ISOTOPIC are refused with a typed reason citing issue #130.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum

from smartchem.algebra_profiles import UnknownAlgebraProfileError, resolve_algebra_profile
from smartchem.category import Bond, Molecule
from smartchem.service import (
    InputKind,
    build_recompile_request,
    response_to_payload,
    run_compilation,
)
from smartchem.smiles import resonance_identity

SPEC_SCHEMA = "smartchem.research.exploration_spec/xxv-1"
RECEIPT_SCHEMA = "smartchem.research.exploration_receipt/xxv-1"
PROJECTION_SCHEMA = "smartchem.research.exploration_projection/xxv-1"

UNKNOWN = "UNKNOWN"
ISSUE_130 = "https://github.com/femboy2112/SmartChem/issues/130"

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _canon_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------------------- the spec


class RefusalReason(str, Enum):
    IDENTITY_LAYER_UNSUPPORTED = "IDENTITY_LAYER_UNSUPPORTED"
    IDENTITY_LAYER_UNKNOWN = "IDENTITY_LAYER_UNKNOWN"
    UNKNOWN_ALGEBRA_PROFILE = "UNKNOWN_ALGEBRA_PROFILE"
    BAD_TARGET = "BAD_TARGET"
    BAD_STOCK = "BAD_STOCK"
    BAD_BUDGET = "BAD_BUDGET"
    BAD_SIMULATION_REF = "BAD_SIMULATION_REF"


class ExplorationSpecRefusal(ValueError):
    """A spec the prototype will not build. ``reason`` is the typed class; ``issue`` cites the tracking issue, if any."""

    def __init__(self, reason: RefusalReason, message: str, issue: str | None = None):
        self.reason = reason
        self.issue = issue
        super().__init__(f"{reason.value}: {message}" + (f" (see {issue})" if issue else ""))


_FINER_LAYERS = frozenset({"CONFIGURATION", "ISOTOPIC"})


def _positive_int_or_none(name: str, value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or type(value) is not int or value < 1:
        raise ExplorationSpecRefusal(RefusalReason.BAD_BUDGET, f"{name} must be a positive int or None, got {value!r}")
    return value


@dataclass(frozen=True)
class ExplorationSpec:
    """Versioned declaration of one exploration. Budgets left ``None`` take the production default (recorded as such).

    ``stock`` is canonicalised to a sorted, de-duplicated tuple (bench order is not part of the production search
    identity either). ``target`` is a SMILES string and is digested as spelled; the production request additionally
    alias-collapses spellings, and that stronger identity is bound separately in the receipt.
    """

    target: str
    identity_layer: str = "CONSTITUTION"
    stock: tuple[str, ...] = ()
    algebra_profile: str = "certified-route-v07"
    max_depth: int | None = None
    max_routes: int | None = None
    cut_budget: int | None = None
    simulation_ref: str | None = None
    schema_version: str = field(default=SPEC_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if type(self.target) is not str or not self.target.strip():
            raise ExplorationSpecRefusal(RefusalReason.BAD_TARGET, "target must be a non-empty SMILES string")
        layer = self.identity_layer
        if layer in _FINER_LAYERS:
            raise ExplorationSpecRefusal(
                RefusalReason.IDENTITY_LAYER_UNSUPPORTED,
                f"identity layer {layer} is not supported: terminal/stock matching is CONSTITUTION-only and the "
                f"configuration-aware identity carrier is not built",
                ISSUE_130,
            )
        if layer != "CONSTITUTION":
            raise ExplorationSpecRefusal(
                RefusalReason.IDENTITY_LAYER_UNKNOWN,
                f"identity layer {layer!r} is not one of the declared layers; only CONSTITUTION is supported "
                f"(a layer coarser than the engine honors is refused by production, COMPATIBILITY section 5)",
            )
        if isinstance(self.stock, (str, bytes)) or any(type(s) is not str or not s.strip() for s in self.stock):
            raise ExplorationSpecRefusal(RefusalReason.BAD_STOCK, "stock must be a sequence of non-empty strings")
        object.__setattr__(self, "stock", tuple(sorted(set(self.stock))))
        try:
            resolve_algebra_profile(self.algebra_profile)
        except (UnknownAlgebraProfileError, TypeError) as exc:
            raise ExplorationSpecRefusal(RefusalReason.UNKNOWN_ALGEBRA_PROFILE, str(exc)) from None
        for name in ("max_depth", "max_routes", "cut_budget"):
            _positive_int_or_none(name, getattr(self, name))
        ref = self.simulation_ref
        if ref is not None and (type(ref) is not str or not _SHA256_HEX.fullmatch(ref)):
            raise ExplorationSpecRefusal(
                RefusalReason.BAD_SIMULATION_REF,
                "simulation_ref must be None or a lowercase sha256 hex model-identity digest",
            )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "identity_layer": self.identity_layer,
            "stock": list(self.stock),
            "algebra_profile": self.algebra_profile,
            "max_depth": self.max_depth,
            "max_routes": self.max_routes,
            "cut_budget": self.cut_budget,
            "simulation_ref": self.simulation_ref,
        }

    @property
    def digest(self) -> str:
        return _sha256(_canon_json(self.to_dict()))


# ------------------------------------------------------------------------------- copying typed words off the payload

_RECOGNITION = {
    "SATISFIED": "RECOGNIZED",
    "UNSATISFIED": "NOT_RECOGNIZED",
    "UNKNOWN": UNKNOWN,
    "NOT_APPLICABLE": "NOT_APPLICABLE",
}

_REACHABILITY_OUTCOMES = frozenset({
    "ROUTES_FOUND", "TARGET_ALREADY_AVAILABLE", "NO_ROUTE_COMPLETE", "INCOMPLETE",
    "REFUSED", "INVALID_INPUT", "INTERNAL_ERROR",
})


def _get(mapping: object, key: str) -> object:
    return mapping.get(key, UNKNOWN) if isinstance(mapping, dict) else UNKNOWN


def _hill_formula(atoms: list) -> str:
    counts: dict[str, int] = {}
    for a in atoms:
        counts[a] = counts.get(a, 0) + 1
    if "C" in counts:
        order = [e for e in ("C", "H") if e in counts] + sorted(e for e in counts if e not in ("C", "H"))
    else:
        order = sorted(counts)
    return "".join(e + (str(counts[e]) if counts[e] > 1 else "") for e in order)


def _molecule_node(graph: object) -> dict:
    """Node record for one replay-payload molecule graph. The id is the production resonance identity of the
    rebuilt graph (the same function route search keys on); a graph that cannot be rebuilt gets an UNKNOWN id."""
    try:
        atoms = list(graph["atoms"])
        mol = Molecule(
            tuple(atoms), frozenset(Bond(b[0], b[1], b[2]) for b in graph["bonds"]), graph["charge"], graph["state"],
        )
        return {"id": "m:" + resonance_identity(mol), "formula": _hill_formula(atoms), "charge": graph["charge"]}
    except Exception:  # noqa: BLE001 -- any malformed/unsupported graph degrades to UNKNOWN, never a guess
        return {"id": UNKNOWN, "formula": UNKNOWN, "charge": UNKNOWN}


def _route_record(dossier: dict) -> dict:
    readiness = _get(dossier, "readiness")
    per_step = readiness.get("per_step", []) if isinstance(readiness, dict) else []
    replay = dossier.get("replay_payload") or []
    steps = []
    for i, step in enumerate(per_step):
        wire = _get(step, "reaction_type")
        rec = {
            "status": _RECOGNITION.get(wire, UNKNOWN),
            "production_status": wire,
            "reaction_class_name": _get(step, "reaction_class_name"),
            # the wire folds a recognizer ABSTAIN and an internal recognizer fault into one UNSATISFIED word
            "abstain_vs_internal_error": UNKNOWN if wire == "UNSATISFIED" else "NOT_APPLICABLE",
        }
        reactants, products = [], []
        if i < len(replay) and isinstance(replay[i], dict):
            reactants = [_molecule_node(g) for g in replay[i].get("reactants", [])]
            products = [_molecule_node(g) for g in replay[i].get("products", [])]
        steps.append({
            "index": i,
            "recognition": rec,
            "conditions": _get(step, "conditions"),
            "process": _get(step, "process"),
            "workup_isolation": _get(step, "workup_isolation"),
            "reactants": reactants,
            "products": products,
        })
    return {
        "route_digest": _get(dossier, "route_digest"),
        "equation": _get(dossier, "equation"),
        "readiness_tier": _get(dossier, "readiness_tier"),
        "fit_status": _get(dossier, "fit_status"),
        "steps": steps,
    }


def _completeness(payload: dict) -> dict:
    outcome = _get(payload, "outcome")
    ir = payload.get("compilation_ir")
    rcpt = ir.get("search_receipt") if isinstance(ir, dict) else None
    ir_status = _get(ir, "search_status") if isinstance(ir, dict) else "NOT_RUN"
    if ir is None:
        status = "NOT_RUN" if outcome in ("REFUSED", "INVALID_INPUT") else UNKNOWN
    elif outcome == "INCOMPLETE" or (isinstance(ir_status, str) and ir_status.startswith("PARTIAL")):
        status = "INCOMPLETE"
    elif ir_status == "COMPLETE_WITHIN_BOUNDS":
        status = "COMPLETE_WITHIN_DECLARED_BOUNDS"
    else:
        status = UNKNOWN
    keys = ("max_depth", "cut_budget", "result_limit", "cut_enumeration_complete",
            "candidate_enumeration_complete", "result_limit_saturated", "stop_reason", "cut_budget_scope")
    return {
        "status": status,
        "search_space_status": _get(payload, "search_space_status"),
        "standard_status": _get(payload, "standard_status"),
        "search_status": ir_status,
        "declared_space_only": True,
        "search_receipt": {k: _get(rcpt, k) for k in keys} if isinstance(rcpt, dict) else None,
    }


def _no_route_reading(outcome: object, n_routes: int, n_dags: int) -> str:
    if n_routes or n_dags:
        return "ROUTES_PRESENT"
    return {
        "TARGET_ALREADY_AVAILABLE": "TARGET_IN_STOCK",
        "NO_ROUTE_COMPLETE": "NO_ROUTE_WITHIN_DECLARED_BOUNDS",
        "INCOMPLETE": "NO_ROUTE_OBSERVED_SEARCH_INCOMPLETE",
        "REFUSED": "NOT_SEARCHED",
        "INVALID_INPUT": "NOT_SEARCHED",
    }.get(outcome, UNKNOWN)  # type: ignore[arg-type]


# -------------------------------------------------------------------------------------------------------- the receipt


@dataclass(frozen=True)
class ExplorationReceipt:
    """A closed record of one ``explore`` call. ``digest`` is derived (``init=False``) from the schema id and the
    canonical body text; it cannot be supplied. The body is exposed only as fresh deep copies."""

    body_json: str
    schema_version: str = field(default=RECEIPT_SCHEMA, init=False)
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.body_json) is not str:
            raise TypeError("body_json must be canonical JSON text")
        object.__setattr__(self, "digest", _sha256(self.schema_version + "\n" + self.body_json))

    @property
    def body(self) -> dict:
        return json.loads(self.body_json)

    def to_dict(self) -> dict:
        return {"schema_version": self.schema_version, "digest": self.digest, **self.body}


def explore(spec: ExplorationSpec) -> ExplorationReceipt:
    """Run the production recompile search for ``spec`` and bind the answer into a receipt. Offline; read-only."""
    if type(spec) is not ExplorationSpec:
        raise TypeError("explore needs an ExplorationSpec")
    request = build_recompile_request(
        spec.target,
        input_kind=InputKind.SMILES,
        stock_materials=spec.stock,
        max_depth=spec.max_depth,
        max_routes=spec.max_routes,
        cut_budget=spec.cut_budget,
        algebra_profile=spec.algebra_profile,
    )
    payload = response_to_payload(run_compilation(request))

    outcome = _get(payload, "outcome")
    routes = [_route_record(d) for d in payload.get("ranked_route_dossiers", []) or []]
    n_dags = len(payload.get("ranked_dag_dossiers", []) or [])
    ir = payload.get("compilation_ir")

    production = {
        "request_semantic_digest": request.semantic_digest,
        "request_digest": request.digest,
        "ir_request_digest": _get(ir, "request_digest") if isinstance(ir, dict) else None,
        "ir_tool_version": _get(ir, "tool_version") if isinstance(ir, dict) else None,
        "ir_transform_registry_digest": _get(ir, "transform_registry_digest") if isinstance(ir, dict) else None,
        "response_schema_version": _get(payload, "schema_version"),
        "result_digest": _get(payload, "result_digest"),
        "result_digest_scope": "VERSION_BOUND_NOT_CROSS_RELEASE_STABLE",
        "transport_mode": _get(payload, "transport_mode"),
        "exit_code": _get(payload, "exit_code"),
    }
    axes = {
        "generation_reachability": {
            "outcome": outcome if outcome in _REACHABILITY_OUTCOMES else UNKNOWN,
            "routes_returned": len(routes),
            "dags_returned": n_dags,
            "no_route_reading": _no_route_reading(outcome, len(routes), n_dags),
        },
        "reaction_type_recognition": {
            "per_route": [
                {"route_digest": r["route_digest"], "steps": [{"index": s["index"], **s["recognition"]} for s in r["steps"]]}
                for r in routes
            ],
        },
        "search_completeness": _completeness(payload),
        "conditions_readiness": {
            "process_selection_status": _get(payload, "process_selection_status"),
            "per_route": [
                {
                    "route_digest": r["route_digest"],
                    "readiness_tier": r["readiness_tier"],
                    "fit_status": r["fit_status"],
                    "steps": [
                        {k: s[k] for k in ("index", "conditions", "process", "workup_isolation")} for s in r["steps"]
                    ],
                }
                for r in routes
            ],
        },
        "simulation": (
            {"status": "NOT_RUN", "ref": None}
            if spec.simulation_ref is None
            else {"status": "REFERENCED_NOT_RUN", "ref": spec.simulation_ref}
        ),
        "empirical_validation": {"status": "UNVERIFIED"},
        "visualization": {"status": "PROJECTION_ONLY"},
    }
    body = {
        "spec_digest": spec.digest,
        "spec": spec.to_dict(),
        "production": production,
        "axes": axes,
        "routes": routes,
    }
    return ExplorationReceipt(_canon_json(body))


# ----------------------------------------------------------------------------------------------------- the projection


def visual_projection(receipt: ExplorationReceipt) -> dict:
    """Renderer-neutral, deterministic, read-only view: molecule and reaction nodes, reactant->reaction->product edges
    (each edge carries its step's recognition label), plus the verdict axes. A pure function of the receipt: it
    reads fresh copies and returns a fresh dict every call, and it adds no field that is not in the receipt."""
    if type(receipt) is not ExplorationReceipt:
        raise TypeError("visual_projection needs an ExplorationReceipt")
    body = receipt.body
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for route in body["routes"]:
        rd = route["route_digest"]
        for step in route["steps"]:
            rid = f"r:{rd}:{step['index']}"
            rec = step["recognition"]
            label = {"status": rec["status"], "reaction_class_name": rec["reaction_class_name"]}
            nodes[rid] = {"id": rid, "kind": "REACTION", "route_digest": rd, "step": step["index"], "recognition": label}
            for role, members in (("reactant", step["reactants"]), ("product", step["products"])):
                for k, m in enumerate(members):
                    nodes.setdefault(m["id"], {"id": m["id"], "kind": "MOLECULE", "formula": m["formula"], "charge": m["charge"]})
                    src, dst = (m["id"], rid) if role == "reactant" else (rid, m["id"])
                    edges.append({
                        "id": f"e:{rid}:{role}:{k}", "source": src, "target": dst, "role": role,
                        "route_digest": rd, "recognition": dict(label),
                    })
    return {
        "schema_version": PROJECTION_SCHEMA,
        "receipt_digest": receipt.digest,
        "spec_digest": body["spec_digest"],
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": sorted(edges, key=lambda e: e["id"]),
        "axes": body["axes"],
        "status": "PROJECTION_ONLY",
    }
