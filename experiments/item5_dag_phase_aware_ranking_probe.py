"""ITEM5-DAG-PHASE-01: the convergent-DAG ranker (`rank_dags`) + its dossier projection (`of_dag`) are phase-aware.

The R43 item-5 brick (ITEM5-PHASE-RANK-01) threaded ``phases`` up the LINEAR ranker (``rank_routes``) but left the
DAG ranker a documented DEFER -- the ROUND-15 ``of_dag`` re-projection fold: ``rank_routes`` returns the scored
fits that ``of_fit`` projects (rank and dossier cannot disagree), but ``rank_dags`` returns the DAGs, which
``of_dag`` RE-PROJECTS under the default tables, so exposing ``phases`` on ``rank_dags`` ALONE would rank under a
declared phase while every dossier projected the phase-blind verdict.  The fold's stated unlock was verbatim: "a
service API that carries a phase declaration into BOTH ``rank_dags`` and ``of_dag``."  This round builds exactly that
and discharges the defer.

Re-checkable demonstrations, all on the REAL ``rank_dags`` / ``dag_bench_fit`` / ``of_dag`` / ``ranked_dag_dossiers``:

1. THREADING REACHES THE DAG ROLLUP -- the SAME single-step DAG (Br2 -> 2 Br.) rolled up with ``phases=None``
   fail-closes its feasibility to UNKNOWN (a phase-blind lookup of the multiphase Br2 is refused, the R36 gate), and
   with ``phases={Br2:"gas", Br:"gas"}`` resolves to UNFAVORABLE -- the DAG twin of the linear #1.  The DAG's section-11
   STATUS is UNCHANGED by the phase (a ranking-only verdict never moves a FITS/EXCLUDED/UNKNOWN grade, exactly as
   DAG-THERMO-01 guarantees), and the EQUILIBRIUM axis stays UNKNOWN (phase-blind -- the R37 boundary, preserved).

2. THE FORCING CONSUMER (single-step) -- the SIGN-tier ranking-ORDER flip.  A Br2 DAG (phase-sensitive: UNKNOWN ->
   UNFAVORABLE) vs an unsourced, phase-INERT sibling (I2 -> 2 I., stays UNKNOWN).  ``phases=None`` -> they tie on every
   ranking tier -> discovery order [Br2, I2]; ``phases={Br2:"gas",...}`` -> the Br2 DAG sinks to the UNFAVORABLE
   feasibility tier and the order FLIPS to [I2, Br2].  This is the dual-phase ranked DAG the R43 defer was waiting for.

3. THE FORCING CONSUMER (genuinely CONVERGENT) -- the same flip on two CONVERGENT 3-step DAGs of the SAME status, so
   the feasibility tier (not the status tier) decides.  A Br2-carrying convergent DAG (Br2->2Br. ; I2->2I. ; Br.+I.->IBr,
   a real join, in-degree 2) vs a phase-inert convergent sibling (I2->2I. ; Cl2->2Cl. ; I.+Cl.->ICl).  Both are UNKNOWN
   status with equal gap counts, so ``phases=None`` -> tie -> [C, X]; ``phases={Br2:gas}`` -> C's Br2 node rolls up to
   UNFAVORABLE and C sinks -> [X, C].  Proves the reorder is real over the MULTI-NODE convergent rollup, not an artifact
   of the linear-shaped single-step fixture.

4. NO RANK-VS-DOSSIER DIVERGENCE -- ``of_dag`` re-projects the DECLARED phase.  ``of_dag(dag_Br2, box)`` (phase-blind)
   carries feasibility_verdict=UNKNOWN; ``of_dag(dag_Br2, box, phases={Br2:gas})`` carries UNFAVORABLE -- the SAME
   verdict the ranker used.  So a dossier's feasibility verdict agrees with the rank that produced it IFF both read the
   same declaration.  ``ranked_dag_dossiers`` is the seam that passes ONE dict into both: under gas its order is
   [I2, Br2] AND the Br2 dossier it emits carries UNFAVORABLE -- rank and dossier move together, structurally.  This is
   what makes the DAG ``phases`` SOUND (the exact divergence the ROUND-15 fold prevented, now closed by construction).

5. BYTE-IDENTICAL DEFAULT -- ``rank_dags(dags)`` (no ``phases`` arg) == ``rank_dags(dags, phases=None)``, and a phase
   declaration for a species a DAG does NOT carry leaves that DAG's rollup untouched (the dict is filtered per step to
   its own species).

6. THE STATUS IS PHASE-INVARIANT -- a phase moves only the ranking-only feasibility verdict, NEVER the section-11
   status.  This is why the compile path's verified-admission re-projection stays sound: ``_run_recompile`` passes no
   phases (the request carries no phase field yet -- the named follow-up, at parity with the linear ``rank_routes``
   call there), so a FITS DAG re-derives the identical phase-blind summary on load.  A phase declaration is a
   direct-caller capability (the ``ranked_dag_dossiers`` seam), not yet a request field.

RDKit-free; no oracle needed (the thermochemistry is the repo's own sourced CODATA seed -- the +161.65 kJ Br-Br
dissociation the R26 DOW-thermo add calibrated, reached through the DAG rollup here).
"""
from __future__ import annotations

import hashlib
import inspect
import json

from smartchem.experiment.dag import SynthesisDAG, dag_thermo_rollup
from smartchem.experiment.drafter import ConstraintBox, dag_bench_fit, rank_dags
from smartchem.experiment.step import ExperimentStep
from smartchem.service import RankedDAGSummary, ranked_dag_dossiers
from smartchem.smiles import parse_smiles as M

FROZEN_HASH = "68b15e1af0f4033c9117cff195aa84e82cc658cd63d6db61ad5370c508c4bfb5"

# --- species -------------------------------------------------------------------------------------------------
_BR2 = M("BrBr")   # dual-phase in DEFAULT_THERMO: gas ΔfH°=+30.91, liquid ΔfH°=0 -> is_multiphase -> phase-blind fail
_BR = M("[Br]")
_I2 = M("II")      # iodine: UNSOURCED / not phase-tabulated -> feasibility UNKNOWN, phase-INERT
_I = M("[I]")
_CL2 = M("ClCl")
_CL = M("[Cl]")
_IBR = M("[Br][I]")
_ICL = M("[Cl][I]")

_GAS = {_BR2: "gas", _BR: "gas"}


def _step(reactants, products, target):
    return ExperimentStep.assembling(target, tuple(reactants), tuple(products))


def _dag_br2_single():
    return SynthesisDAG.of(_step([_BR2], [_BR, _BR], _BR))          # Br2 -> 2 Br.  (dual-phase, single-step)


def _dag_i2_single():
    return SynthesisDAG.of(_step([_I2], [_I, _I], _I))              # I2 -> 2 I.    (phase-inert, single-step)


def _dag_br2_convergent():
    return SynthesisDAG.of(_step([_BR2], [_BR, _BR], _BR),          # Br2 -> 2 Br.
                           _step([_I2], [_I, _I], _I),              # I2  -> 2 I.
                           _step([_BR, _I], [_IBR], _IBR))          # Br. + I. -> IBr   (join, in-degree 2)


def _dag_inert_convergent():
    return SynthesisDAG.of(_step([_I2], [_I, _I], _I),              # I2  -> 2 I.
                           _step([_CL2], [_CL, _CL], _CL),          # Cl2 -> 2 Cl.
                           _step([_I, _CL], [_ICL], _ICL))          # I. + Cl. -> ICl   (join, phase-inert)


def _lab(ranked, a, b, la, lb):
    return [la if d is a else lb for d in ranked]


# 1 -- the phase declaration reaches the DAG rollup; status + equilibrium are boundaries.
def threading_reaches_dag_rollup() -> dict:
    dag = _dag_br2_single()
    box = ConstraintBox()
    none = dag_bench_fit(dag, box)
    gas = dag_bench_fit(dag, box, phases=_GAS)
    return {
        "none_feas": none.feasibility_verdict,
        "gas_feas": gas.feasibility_verdict,
        "changed": none.feasibility_verdict != gas.feasibility_verdict,
        "status_invariant": none.status.value == gas.status.value,
        "none_status": none.status.value,
        "equilibrium_stays_blind": none.equilibrium_verdict == gas.equilibrium_verdict == "UNKNOWN",
    }


# 2 -- the forcing consumer: the sign-tier ORDER flip on single-step DAGs (both UNCONSTRAINED -> feasibility decides).
def sign_tier_order_flip_single() -> dict:
    a, b = _dag_br2_single(), _dag_i2_single()
    order_none = _lab(rank_dags([a, b]), a, b, "Br2", "I2")
    order_gas = _lab(rank_dags([a, b], phases=_GAS), a, b, "Br2", "I2")
    return {"order_none": order_none, "order_gas": order_gas, "flipped": order_none != order_gas}


# 3 -- the forcing consumer on genuinely CONVERGENT DAGs of the SAME status (multi-node rollup reorders).
def sign_tier_order_flip_convergent() -> dict:
    c, x = _dag_br2_convergent(), _dag_inert_convergent()
    both_convergent = c.is_convergent and x.is_convergent
    order_none = _lab(rank_dags([c, x]), c, x, "C", "X")
    order_gas = _lab(rank_dags([c, x], phases=_GAS), c, x, "C", "X")
    return {
        "both_convergent": both_convergent,
        "order_none": order_none,
        "order_gas": order_gas,
        "flipped": order_none != order_gas,
    }


# 4 -- no rank-vs-dossier divergence: of_dag re-projects the declared phase; the seam moves both together.
def no_rank_dossier_divergence() -> dict:
    a, b = _dag_br2_single(), _dag_i2_single()
    box = ConstraintBox()
    s_none = RankedDAGSummary.of_dag(a, box)
    s_gas = RankedDAGSummary.of_dag(a, box, phases=_GAS)
    seam_gas = ranked_dag_dossiers([a, b], box, phases=_GAS)
    seam_order = ["Br2" if s.route_digest == a.digest else "I2" for s in seam_gas]
    br2_dossier = next(s for s in seam_gas if s.route_digest == a.digest)
    return {
        "of_dag_none_feas": s_none.feasibility_verdict,
        "of_dag_gas_feas": s_gas.feasibility_verdict,
        "dossier_tracks_phase": s_gas.feasibility_verdict != s_none.feasibility_verdict,
        "seam_order_gas": seam_order,
        "seam_br2_dossier_feas": br2_dossier.feasibility_verdict,
        "seam_consistent": seam_order == ["I2", "Br2"] and br2_dossier.feasibility_verdict == "UNFAVORABLE",
    }


# 5 -- the default is byte-identical, and a foreign phase declaration leaves a non-carrier DAG untouched.
def default_is_byte_identical() -> dict:
    a, b = _dag_br2_single(), _dag_i2_single()
    noarg = _lab(rank_dags([a, b]), a, b, "Br2", "I2")
    explicit_none = _lab(rank_dags([a, b], phases=None), a, b, "Br2", "I2")
    box = ConstraintBox()
    b_none = dag_bench_fit(b, box)
    b_foreign = dag_bench_fit(b, box, phases={_BR2: "gas"})
    return {
        "noarg": noarg,
        "explicit_none": explicit_none,
        "noarg_equals_none": noarg == explicit_none,
        "foreign_phase_inert": b_none.feasibility_verdict == b_foreign.feasibility_verdict,
    }


# 6 -- the DAG ranker now has a phases param (the defer discharged) AND the equilibrium rollup stays phase-blind.
def signature_and_boundaries() -> dict:
    rd = set(inspect.signature(rank_dags).parameters)
    od = set(inspect.signature(RankedDAGSummary.of_dag).parameters)
    rollup = set(inspect.signature(dag_thermo_rollup).parameters)
    bench = set(inspect.signature(dag_bench_fit).parameters)
    seam = set(inspect.signature(ranked_dag_dossiers).parameters)
    return {
        "rank_dags_has_phases": "phases" in rd,
        "of_dag_has_phases": "phases" in od,
        "dag_thermo_rollup_has_phases": "phases" in rollup,
        "dag_bench_fit_has_phases": "phases" in bench,
        "seam_has_phases": "phases" in seam,
        "defer_discharged": all("phases" in s for s in (rd, od, rollup, bench, seam)),
    }


def _payload() -> dict:
    return {
        "threading": threading_reaches_dag_rollup(),
        "flip_single": sign_tier_order_flip_single(),
        "flip_convergent": sign_tier_order_flip_convergent(),
        "no_divergence": no_rank_dossier_divergence(),
        "default_identical": default_is_byte_identical(),
        "signatures": signature_and_boundaries(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: the phase declaration reaches the DAG rollup and flips the ranking ORDER (single-step
    AND convergent, sign tier); of_dag re-projects it with no rank-vs-dossier divergence; the seam moves both together;
    the default is byte-identical; the status stays phase-invariant; and the equilibrium axis stays phase-blind."""
    t = threading_reaches_dag_rollup()
    assert t["none_feas"] == "UNKNOWN", t
    assert t["gas_feas"] == "UNFAVORABLE", t
    assert t["changed"] is True, t
    assert t["status_invariant"] is True, t
    assert t["equilibrium_stays_blind"] is True, t

    s = sign_tier_order_flip_single()
    assert s["order_none"] == ["Br2", "I2"], s
    assert s["order_gas"] == ["I2", "Br2"], s
    assert s["flipped"] is True, s

    c = sign_tier_order_flip_convergent()
    assert c["both_convergent"] is True, c
    assert c["order_none"] == ["C", "X"], c
    assert c["order_gas"] == ["X", "C"], c
    assert c["flipped"] is True, c

    d = no_rank_dossier_divergence()
    assert d["of_dag_none_feas"] == "UNKNOWN", d
    assert d["of_dag_gas_feas"] == "UNFAVORABLE", d
    assert d["dossier_tracks_phase"] is True, d
    assert d["seam_consistent"] is True, d

    b = default_is_byte_identical()
    assert b["noarg_equals_none"] is True, b
    assert b["foreign_phase_inert"] is True, b

    sig = signature_and_boundaries()
    assert sig["rank_dags_has_phases"] is True, sig
    assert sig["of_dag_has_phases"] is True, sig
    assert sig["defer_discharged"] is True, sig
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print(f"content_hash() -> {content_hash()}")
