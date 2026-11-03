"""DAG-ADMIT-BYPASS -- the convergent-DAG reaction-type admission bypass, reproduced (OPERATION Phase 3).

THE FINDING (verdict FAIL -- a fiction reaches an admissible DAG state while its chemistry is unrecognized).

Linear route search demotes a conserved-but-fictional step via the reaction-TYPE oracle: the readiness layer
runs ``route_reaction_type_blockers`` (-> ``recognize_reaction_type``) per step, so an unrecognized step is
blocked.  The CONVERGENT-DAG path does NOT: ``dag_bench_fit`` (and its projection ``RankedDAGSummary.of_dag``,
consumed by ``admissible_dag_digests``) judges a DAG on composability + the physical box + the process axis, and
NEVER consults the recognizer.  So a conserved fiction given a legally-satisfied condition envelope reaches
``FITS`` -- a positive bench verdict -- while ``recognize_reaction_type`` returns ``None`` and
``route_reaction_type_blockers`` even produces a blocker that the DAG path ignores.

This harness REPRODUCES that bypass directly (no report, no testimony -- run it).  It mirrors the genuine FITS
fixture ``tests/test_dag_rank.py::_single_step_fits_dag`` and swaps the recognized ester for a conserved fiction.

Plan Phase-3 taxonomy: this is **FAIL** -- a fictional DAG reaches an admissible state (FITS) while its
chemistry remains unrecognized.  (Contrast PASS = recognition independently prevents admission; AMBIGUOUS = the
condition-bearing case cannot be constructed.  The case IS constructible with the public API, so not AMBIGUOUS.)

PRODUCTION REACHABILITY (not just a hand-built API probe): a DAG-mode recompile of a real target emits
generator-derived capped-scission steps, some of which match no attested reaction class; those unrecognized
steps reach FITS and enter ``admissible_dag_digests`` exactly as the fiction below does.  The repair and its
contract implications are in ``docs/research/DAG_ADMISSION_BYPASS_FINDING_2026-10-29.md``.

Run: ``.venv/bin/python -m experiments.dag_admission_bypass_probe``
"""
from __future__ import annotations

from smartchem.smiles import parse_smiles
from smartchem.contracts import EvidenceStatus
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.drafter import ConstraintBox, RouteFitStatus, dag_bench_fit
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type, route_reaction_type_blockers
from smartchem.process_constraints import ProcessRequirements, Agitation, ProcessBounds

_BOX = ConstraintBox(process=ProcessBounds(max_total_minutes=70.0))
# a genuine esterification (recognized) and a conserved FICTION (EtOH + CH4 -> ethyl methyl ether + H2;
# C3H10O both sides, but no such reaction) -- each a single-step NO_TRANSITIONS DAG with a satisfying envelope.
_ESTER = ("CC(=O)OCC", ("CC(=O)O", "CCO"), ("CC(=O)OCC", "O"))
_FICTION = ("CCOC", ("CCO", "C"), ("CCOC", "[H][H]"))


def _env() -> ConditionEnvelope:
    pr = ProcessRequirements(elapsed_minutes=Interval(40, 40, "min"), active_minutes=Interval(1, 2, "min"),
                             agitation=Agitation.NONE, workup_included=True,
                             provenance="synthetic software control; no experimental claim")
    return ConditionEnvelope(temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
                             provenance="synthetic process control; no experimental claim", process=pr)


def _dag(target: str, reactants: tuple, products: tuple):
    step = ExperimentStep.assembling(parse_smiles(target), tuple(parse_smiles(s) for s in reactants),
                                     tuple(parse_smiles(s) for s in products), envelope=_env())
    return SynthesisDAG.of(step), step


def measure() -> dict:
    out = {}
    for name, (t, r, p) in (("ester", _ESTER), ("fiction", _FICTION)):
        dag, step = _dag(t, r, p)
        out[name] = {
            "status": dag_bench_fit(dag, _BOX).status,
            "recognized": recognize_reaction_type(step) is not None,
            "blockers": len(route_reaction_type_blockers(dag)),
        }
    return out


def bypass_is_live() -> bool:
    """True iff the fiction reaches FITS while unrecognized (the FAIL condition) -- and the recognized control
    also FITS (so FITS is reachable at all, i.e. the fiction's FITS is not an artefact of a broken bench)."""
    m = measure()
    return (m["fiction"]["status"] == RouteFitStatus.FITS and not m["fiction"]["recognized"]
            and m["fiction"]["blockers"] >= 1 and m["ester"]["status"] == RouteFitStatus.FITS)


def main() -> None:
    m = measure()
    print("DAG-ADMIT-BYPASS -- convergent-DAG reaction-type admission bypass\n")
    for name in ("ester", "fiction"):
        r = m[name]
        print(f"  {name:8s} dag_bench_fit={r['status'].value:12s} recognized={r['recognized']!s:5s} "
              f"route_reaction_type_blockers={r['blockers']}")
    live = bypass_is_live()
    print(f"\n  PLAN PHASE-3 VERDICT: {'FAIL -- fiction reaches FITS while unrecognized (bypass LIVE)' if live else 'bypass not live (repaired?)'}")
    print("  The DAG path grants a positive bench verdict to chemistry its own oracle rejects; the linear path does not.")


if __name__ == "__main__":
    main()
