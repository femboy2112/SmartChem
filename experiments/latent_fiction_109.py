"""CHEM-ALG-01 #109 -- permanent negative controls for conserved-but-fictional routes.

Capped scission is an unguarded sigma-metathesis (A-B + X-Y -> A-X + B-Y), so with the wrong
helper in the pool it emits CONSERVED CHEMICAL FICTIONS: formula-balanced steps that are not
real reactions (e.g. methanol + acetone -> butanone + water). The fail-closed promise is that
NO public consumer ever VOUCHES such a route. #109 makes that a permanent, cross-mode control.

FINDING (Observed, 2026-10-28; corroborated by an independent evil-morty runtime probe): no
live public-API false-VOUCH exists. A conserved fiction is DEMOTED (readiness_tier =
FORMAL_CANDIDATE, not REACTION_VOUCHED; admissible_route_digests = ()) in LINEAR mode, and NOT
ADMITTED (admissible_dag_digests = (); fit_status never "FITS") in CONVERGENT-DAG mode.

LATENT HOLE (Conjectured -- documented here as scoped future work, NOT closed): the convergent
DAG path is genuinely ORACLE-BLIND. search_dags / rank_dags / dag_bench_fit never consult the
reaction-type oracle, and RankedDAGSummary carries no readiness field. What contains a fiction
TODAY is the UNRELATED "undeclared-conditions => UNKNOWN fit" wall -- dag_bench_fit returns FITS
only with zero gaps under a constraining box, and generated steps declare no conditions, so
every generated DAG pins to fit_status=UNKNOWN and never reaches admissible_dag_digests. The
moment a DAG step ever carries declared conditions sufficient to clear those gaps, a conserved
fiction reaches admissible_dag_digests with the oracle never consulted = a true false-VOUCH.
A DAG-mode oracle/fiction surface (or an enforced "generated DAG steps declare no conditions"
invariant) is the real fix; it is scoped but not built here. THIS control locks the current
behaviour so any regression -- a DAG fiction reaching FITS, or a linear fiction reaching
REACTION_VOUCHED -- goes red before release.

Run: ``.venv/bin/python -m experiments.latent_fiction_109`` (exit 0 iff every control holds).
``validate()`` is imported by tests/test_latent_fiction_109.py as a permanent control.
"""
from __future__ import annotations

from dataclasses import dataclass

from smartchem.process_constraints import ProcessBounds
from smartchem.service import TransformGrammar, build_recompile_request, run_compilation

_BOX = ProcessBounds.low_touch()  # a generous, achievable process box

# Conserved FICTIONS the capped-scission generator emits and the oracle demotes. Each is
# formula-balanced but not a real reaction; charged/organometallic fictions (PhMgBr, Suzuki
# boronate) are refused UPSTREAM at the charge/element gate and never reach these consumers.
_FICTIONS = [
    ("butanone", "CCC(C)=O"),            # methanol + acetone -> butanone + water (the classic)
    ("ethyl_acetoacetate", "CCOC(=O)CC(C)=O"),  # all generated cuts are unrecognized fictions
]
# A genuine recognized reaction, so the "demoted" assertions below are NON-VACUOUS: the pipeline
# really can and does VOUCH a real reaction in linear mode -- it just never vouches a fiction.
_REAL = ("ethyl_acetate", "CCOC(C)=O")   # esterification: AcOH + EtOH -> ethyl acetate + water


def _run(smi: str, grammar):
    return run_compilation(build_recompile_request("smiles:" + smi, grammar=grammar, process=_BOX))


@dataclass(frozen=True)
class _Verdict:
    label: str
    linear_vouched: int        # routes reaching REACTION_VOUCHED in linear mode
    linear_admissible: int     # len(admissible_route_digests)
    dag_fits: int              # dag dossiers with fit_status == "FITS"
    dag_admissible: int        # len(admissible_dag_digests)


def _probe(label: str, smi: str) -> _Verdict:
    lin = _run(smi, TransformGrammar.CAPPED_SCISSION_LINEAR)
    dag = _run(smi, TransformGrammar.CAPPED_SCISSION_CONVERGENT)
    return _Verdict(
        label=label,
        linear_vouched=sum(1 for d in lin.ranked_route_dossiers if d.readiness_tier == "REACTION_VOUCHED"),
        linear_admissible=len(lin.admissible_route_digests),
        dag_fits=sum(1 for d in dag.ranked_dag_dossiers if d.fit_status == "FITS"),
        dag_admissible=len(dag.admissible_dag_digests),
    )


def run() -> dict:
    return {
        "fictions": [_probe(lbl, smi) for lbl, smi in _FICTIONS],
        "real": _probe(*_REAL),
    }


def validate() -> tuple[bool, dict]:
    data = run()
    fics = data["fictions"]
    real = data["real"]
    # Every fiction: never vouched in linear, never admissible in either mode, never FITS in DAG.
    fiction_clean = all(
        v.linear_vouched == 0 and v.linear_admissible == 0 and v.dag_fits == 0 and v.dag_admissible == 0
        for v in fics
    )
    # Non-vacuity: the REAL reaction genuinely reaches REACTION_VOUCHED in linear mode.
    real_vouched = real.linear_vouched >= 1
    summary = {
        "fictions_checked": len(fics),
        "fiction_never_vouched_or_admitted": fiction_clean,
        "real_reaction_vouched_in_linear": real.linear_vouched,
    }
    return (fiction_clean and real_vouched), summary


def main() -> int:
    data = run()
    print(f"{'target':<20}{'lin_vouched':>12}{'lin_adm':>9}{'dag_FITS':>10}{'dag_adm':>9}")
    for v in data["fictions"] + [data["real"]]:
        tag = " (REAL)" if v.label == _REAL[0] else " (fiction)"
        print(f"{v.label + tag:<20}{v.linear_vouched:>12}{v.linear_admissible:>9}{v.dag_fits:>10}{v.dag_admissible:>9}")
    ok, summary = validate()
    print(f"\nsummary: {summary}")
    print("VALIDATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
