"""V1.0-CONTRACT-01: the EXECUTABLE 1.0 public-contract freeze -- COMPATIBILITY.md's prose, made machine-checkable.

COMPATIBILITY.md section 2 promises a *stable surface*: a fixed set of public Python entry points, CLI verbs, verdict
vocabularies, and wire schema ids whose MEANING will not move without a declared MAJOR.  Prose cannot fail a build.
This harness reads that surface STRAIGHT OUT OF THE LIVE CODE (never a hand-copied list) and freezes it; ``--check``
re-derives it and prints every drifted key.  ``tests/test_v1_0_public_contract.py`` runs the check in CI.

What is frozen (and ONLY this -- the stable surface, not the sprawling ``smartchem.__init__`` export set):

* the 11 public entry-point functions in ``smartchem.service`` -- each as its ordered PUBLIC parameter list
  (name, kind, normalised default).  Annotations are NOT frozen (``dict | None`` vs ``Optional[dict]`` is a
  Python-version repr detail, not a call-semantics change); leading-underscore params are NOT frozen (section 2.2:
  private layout is not contractual); a non-literal default (a sentinel, a record) is normalised to
  ``<default:TypeName>`` so no memory address ever enters the freeze;
* the three verification types in ``smartchem.verification`` (``VerificationPolicy`` / ``VerificationBudget`` /
  ``VerifiedLoad``) as their public constructor parameter lists, plus the existence of the budget-exhaustion signal
  ``VerificationBudgetExceeded`` and the one explicit unbounded licence ``VerificationBudget.unlimited``;
* the DEFAULT verification budget's exact counters (section 4: a MINOR may raise, never lower -- so a changed
  default is a deliberate contract event, never a silent one);
* the CLI verb set: the CONTRACT verbs (``plan`` / ``recompile`` / ``decompile`` / ``compile``) and the
  present-but-NON-contract verbs (``synthesize`` / ``audit``), extracted from the live ``_dispatch`` source so a
  renamed or newly-added verb cannot slip past;
* the stable verdict vocabularies (``outcome`` + its exit codes, search-space status, readiness tiers IN ORDER,
  process/route fit, capability status, transport mode), each read from its authoritative definition;
* the wire schema ids of the CURRENT generation and the read-only legacy v0.8 generation.

The freeze is version-INDEPENDENT by construction: ``smartchem.__version__`` is deliberately NOT part of the compared
document (a package bump must not move this surface -- that is the whole point).  Provenance lives under ``_meta`` and
is never compared.

Run:  .venv/bin/python experiments/v1_0_public_contract.py --write   # (re)freeze -- only on a sanctioned surface change
      .venv/bin/python experiments/v1_0_public_contract.py --check   # recompute, diff, exit 1 on drift
      .venv/bin/python experiments/v1_0_public_contract.py --print   # print the live document, do not touch disk
"""
from __future__ import annotations

import argparse
import dataclasses
import inspect
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FREEZE_JSON = REPO / "docs" / "research" / "V1_0_PUBLIC_CONTRACT_FREEZE.json"

CONTRACT_SCHEMA = "smartchem.release/v1_0-public-contract-v1"

# The 11 public entry-point functions, in COMPATIBILITY.md section 2 order.
SERVICE_FUNCTIONS = (
    "build_recompile_request",
    "build_decompile_request",
    "run_compilation",
    "response_to_payload",
    "load_response",
    "load_response_text",
    "response_from_payload",
    "deserialize_response",
    "request_to_payload",
    "request_from_payload",
    "response_schema",
)

VERIFICATION_TYPES = ("VerificationPolicy", "VerificationBudget", "VerifiedLoad")

CONTRACT_CLI_VERBS = ("plan", "recompile", "decompile", "compile")


def _norm_default(d: object) -> str:
    """A DETERMINISTIC normalisation of a parameter default.

    Literals (None / bool / int / float / str, and flat tuples/lists of them) are frozen by ``repr`` -- those are
    call semantics.  Anything else (a sentinel ``object()``, a named ``UNPINNED``, a ``VerificationBudget`` record)
    becomes ``<default:TypeName>`` so a memory address never enters the freeze while a *type change* of the default
    still trips the check.
    """
    empty = inspect.Parameter.empty
    if d is empty:
        return "<required>"
    if d is None or isinstance(d, (bool, int, float, str)):
        return repr(d)
    if isinstance(d, (tuple, list)) and all(x is None or isinstance(x, (bool, int, float, str)) for x in d):
        return repr(d)
    return f"<default:{type(d).__name__}>"


def _public_params(obj: object) -> list[list[str]]:
    """The ordered PUBLIC parameter list of a callable/type: ``[name, kind, normalised-default]`` triples,
    leading-underscore (private, non-contractual) params dropped."""
    sig = inspect.signature(obj)
    out: list[list[str]] = []
    for name, p in sig.parameters.items():
        if name.startswith("_"):
            continue
        out.append([name, p.kind.name, _norm_default(p.default)])
    return out


def _cli_dispatch_verbs() -> list[str]:
    """Every verb the live CLI ``_dispatch`` recognises, read from source (the dispatch is a manual
    ``command == "x"`` chain, not an argparse registry -- so source is the authority)."""
    src = (REPO / "smartchem" / "cli.py").read_text(encoding="utf-8")
    # restrict to the _dispatch body so an unrelated string literal cannot masquerade as a verb
    body = src.split("def _dispatch(", 1)[1]
    body = body.split("\ndef ", 1)[0]
    return sorted(set(re.findall(r'command == "([a-z-]+)"', body)))


def build_contract() -> dict:
    """The live public-contract document, read entirely from code.  Deterministic; no clocks, no addresses."""
    import smartchem.service as svc
    import smartchem.verification as ver
    from smartchem.search import STANDARD_8_3_LABELS
    from smartchem.process_constraints import ProcessFitStatus
    from smartchem.capability.enums import CapabilityStatus
    from smartchem.transport_integrity import TRANSPORT_CANONICAL_VERIFIED, TRANSPORT_THIN_ADVISORY
    from smartchem.experiment.readiness import READINESS_TIERS
    from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MATERIAL_COMPONENT_SCHEMA

    # -- python entry points -------------------------------------------------------------------------------------
    functions = {name: _public_params(getattr(svc, name)) for name in SERVICE_FUNCTIONS}

    # -- verification surface ------------------------------------------------------------------------------------
    ver_types = {name: _public_params(getattr(ver, name)) for name in VERIFICATION_TYPES}
    default_budget = {
        f.name: getattr(ver.VerificationBudget(), f.name)
        for f in dataclasses.fields(ver.VerificationBudget)
        if not f.name.startswith("_")
    }

    # -- cli verbs -----------------------------------------------------------------------------------------------
    present = _cli_dispatch_verbs()
    cli = {
        "contract": list(CONTRACT_CLI_VERBS),
        "present_noncontract": sorted(v for v in present if v not in CONTRACT_CLI_VERBS),
    }

    # -- verdict vocabulary --------------------------------------------------------------------------------------
    outcome_members = [o.value for o in svc.ResponseOutcome]
    exit_by_outcome = {o.value: int(svc._EXIT_BY_OUTCOME[o]) for o in svc.ResponseOutcome}
    vocab = {
        "response_outcome": {"members": outcome_members, "exit_code": exit_by_outcome},
        "search_space_status": list(STANDARD_8_3_LABELS),
        "readiness_tiers_weakest_first": list(READINESS_TIERS),
        "process_fit_status": [s.value for s in ProcessFitStatus],
        "capability_status": [s.value for s in CapabilityStatus],
        "transport_mode": [TRANSPORT_CANONICAL_VERIFIED, TRANSPORT_THIN_ADVISORY],
    }

    # -- wire schema ids -----------------------------------------------------------------------------------------
    schemas = {
        "current": {
            "request": svc.COMPILATION_REQUEST_SCHEMA,
            "response": svc.COMPILATION_RESPONSE_SCHEMA,
            "descriptor": svc.COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR,
            "ranked_route_summary": svc.RANKED_ROUTE_SUMMARY_SCHEMA,
            "ranked_dag_summary": svc.RANKED_DAG_SUMMARY_SCHEMA,
            "stock_material": STOCK_MATERIAL_SCHEMA,
            "material_component": MATERIAL_COMPONENT_SCHEMA,
        },
        "legacy_v0_8_read_only": {
            "request": svc.LEGACY_V08_REQUEST_SCHEMA,
            "response": svc.LEGACY_V08_RESPONSE_SCHEMA,
            "ranked_route_summary": svc.LEGACY_V08_RANKED_ROUTE_SUMMARY_SCHEMA,
            "ranked_dag_summary": svc.LEGACY_V08_RANKED_DAG_SUMMARY_SCHEMA,
        },
    }

    return {
        "contract_schema": CONTRACT_SCHEMA,
        "python_entry_points": {"module": "smartchem.service", "functions": functions},
        "verification": {
            "module": "smartchem.verification",
            "types": ver_types,
            "default_budget": default_budget,
            "has_budget_exceeded": hasattr(ver, "VerificationBudgetExceeded"),
            "has_budget_unlimited": hasattr(ver.VerificationBudget, "unlimited"),
        },
        "cli_verbs": cli,
        "verdict_vocabulary": vocab,
        "wire_schema_ids": schemas,
    }


def _canon(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)


def _flatten(obj: object, prefix: str = "") -> dict[str, object]:
    flat: dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flat.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flat.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        flat[prefix] = obj
    return flat


def _diff(frozen: dict, live: dict) -> list[str]:
    fa, la = _flatten(frozen), _flatten(live)
    drift: list[str] = []
    for key in sorted(set(fa) | set(la)):
        if key not in fa:
            drift.append(f"ADDED    {key} = {la[key]!r}")
        elif key not in la:
            drift.append(f"REMOVED  {key} (was {fa[key]!r})")
        elif fa[key] != la[key]:
            drift.append(f"CHANGED  {key}: {fa[key]!r} -> {la[key]!r}")
    return drift


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true", help="(re)freeze the live surface to the committed JSON")
    g.add_argument("--check", action="store_true", help="recompute, diff against the committed JSON, exit 1 on drift")
    g.add_argument("--print", dest="do_print", action="store_true", help="print the live document, touch no disk")
    args = ap.parse_args(argv)

    import smartchem

    live = build_contract()

    if args.do_print:
        print(_canon(live))
        return 0

    if args.write:
        doc = dict(live)
        doc["_meta"] = {
            "note": "Executable 1.0 public-contract freeze. _meta is provenance, never compared. "
                    "The package version is deliberately absent: a version bump must not move this surface.",
            "frozen_at_version": smartchem.__version__,
        }
        FREEZE_JSON.parent.mkdir(parents=True, exist_ok=True)
        FREEZE_JSON.write_text(_canon(doc) + "\n", encoding="utf-8")
        print(f"wrote {FREEZE_JSON.relative_to(REPO)} (frozen at {smartchem.__version__})")
        return 0

    # --check
    if not FREEZE_JSON.exists():
        print(f"ERROR: {FREEZE_JSON} does not exist; run --write first", file=sys.stderr)
        return 1
    frozen = json.loads(FREEZE_JSON.read_text(encoding="utf-8"))
    frozen.pop("_meta", None)
    drift = _diff(frozen, live)
    if drift:
        print(f"PUBLIC CONTRACT DRIFT ({len(drift)} key(s)) vs {FREEZE_JSON.relative_to(REPO)}:", file=sys.stderr)
        for line in drift:
            print("  " + line, file=sys.stderr)
        return 1
    print("public contract: NO DRIFT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
