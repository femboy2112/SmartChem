"""DAG-ADMIT-02 -- the convergent-DAG reaction-TYPE admission GATE, demonstrated closing the bypass.

Companion to ``experiments/dag_admission_bypass_probe.py`` (which REPRODUCES the hole).  This harness shows the
REPAIR: :attr:`~smartchem.service.CompilationResponse.admissible_dag_digests` now admits a FITS DAG only when every
step is a positively-recognized reaction class, re-derived (never stored) from the thick ``replay_payload`` at the
admission point -- the convergent analogue of the linear path's readiness/frontier recognition channel, which a
``RankedDAGSummary`` otherwise lacks entirely.

Properties asserted (``validate``), each measured, none testimony:
  P1  a genuine RECOGNIZED single-step DAG (esterification) with a satisfying bench box is ADMITTED.
  P2  a conserved FICTION (EtOH + CH4 -> ethyl-methyl-ether + H2) that physically/process-FITS is WITHHELD from
      admission -- while its ``fit_status`` stays FITS (the physical/process verdict is untouched; recognition is a
      separate axis, exactly as on the linear side).
  P3  NON-VACUITY: WITHOUT the gate the fiction WOULD be admitted (its ``fit_status`` is FITS and it carries the
      right process envelope), so the gate is load-bearing.
  P4  IDENTITY-BIND: a recognized reaction's replay carried under the fiction's ``route_digest`` does NOT bind
      (``reconstruct(replay).digest != route_digest``) and cannot buy admission -- a substituted-evidence forgery.
  P5  a real-but-UNRECOGNIZED reaction (aldol, no attested recognizer) is WITHHELD, NOT relabelled impossible
      (``fit_status`` FITS preserved) -- honest coverage loss.

Run: ``.venv/bin/python -m experiments.dag_admission_recognition_gate_probe``
"""
from __future__ import annotations

from dataclasses import replace

from smartchem.smiles import parse_smiles
from smartchem.contracts import EvidenceStatus
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.drafter import ConstraintBox
from smartchem.process_constraints import ProcessRequirements, Agitation, ProcessBounds
from smartchem.service import RankedDAGSummary, _dag_dossier_steps_recognized

_BOX = ConstraintBox(process=ProcessBounds(max_total_minutes=70.0))
_ESTER = ("CC(=O)OCC", ("CC(=O)O", "CCO"), ("CC(=O)OCC", "O"))        # recognized esterification
_FICTION = ("CCOC", ("CCO", "C"), ("CCOC", "[H][H]"))                 # EtOH + CH4 -> ethyl methyl ether + H2 (conserved)
_ALDOL = ("CC(O)CC=O", ("CC=O", "CC=O"), ("CC(O)CC=O",))              # real aldol, no attested recognizer


def _env() -> ConditionEnvelope:
    pr = ProcessRequirements(elapsed_minutes=Interval(40, 40, "min"), active_minutes=Interval(1, 2, "min"),
                             agitation=Agitation.NONE, workup_included=True,
                             provenance="synthetic software control; no experimental claim")
    return ConditionEnvelope(temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
                             provenance="synthetic process control; no experimental claim", process=pr)


def _dossier(spec) -> RankedDAGSummary:
    t, r, p = spec
    step = ExperimentStep.assembling(parse_smiles(t), tuple(parse_smiles(s) for s in r),
                                     tuple(parse_smiles(s) for s in p), envelope=_env())
    return RankedDAGSummary.of_dag(SynthesisDAG.of(step), _BOX)


def measure() -> dict:
    ester, fiction, aldol = _dossier(_ESTER), _dossier(_FICTION), _dossier(_ALDOL)
    forged = replace(fiction, replay_payload=ester.replay_payload)   # ester steps under the fiction's digest
    return {
        "ester_fit": ester.fit_status,
        "ester_admits": _dag_dossier_steps_recognized(ester),
        "fiction_fit": fiction.fit_status,
        "fiction_admits": _dag_dossier_steps_recognized(fiction),
        "aldol_fit": aldol.fit_status,
        "aldol_admits": _dag_dossier_steps_recognized(aldol),
        "forged_admits": _dag_dossier_steps_recognized(forged),
    }


def validate() -> bool:
    m = measure()
    return (
        m["ester_fit"] == "FITS" and m["ester_admits"] is True                 # P1 recognized admitted
        and m["fiction_fit"] == "FITS" and m["fiction_admits"] is False        # P2 fiction withheld, fit untouched (P3)
        and m["forged_admits"] is False                                        # P4 identity-bind
        and m["aldol_fit"] == "FITS" and m["aldol_admits"] is False            # P5 unrecognized withheld, not impossible
    )


def main() -> None:
    m = measure()
    print("DAG-ADMIT-02 -- convergent-DAG reaction-type admission gate\n")
    for name in ("ester", "fiction", "aldol"):
        print(f"  {name:8s} fit_status={m[name+'_fit']:6s} admitted={m[name+'_admits']!s}")
    print(f"  forged (ester replay under fiction digest) admitted={m['forged_admits']!s}")
    print(f"\n  VERDICT: {'PASS -- the gate admits only recognized chemistry' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
