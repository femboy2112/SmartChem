"""Wave D (Round VII) -- the living chamber's OBSERVATION BOUNDARY.

Ooh yeah -- and SmartChem still draws nothing.  This publishes a renderer-neutral, strict-JSON frame for a
``living_chamber.ChamberState`` plus a tiny headless presenter, so the LibGibson side (its own repo, epic #125) can
show two chambers, their pH values, and the membrane transfer ledger WITHOUT ever mistaking a model prediction for a
sensor reading.

It reuses the Wave A2 honesty contract verbatim (``snapshot.ModelRunReceipt``): the per-cell aqueous equilibrium is
source-backed, but the TRANSPORT conductances are CALLER-DECLARED, so the weakest link of the composed model is
unsourced -- the run's admission level is therefore SYNTHETIC, ``supported_prediction`` is False, and
``observed_measurement`` is structurally False (a simulation carries no external observation source and can never
report a physical measurement).  Each cell still carries its OWN aqueous verdict + caveats as evidence, so a reader
sees that the chemistry is admitted even though the composed transport prediction is not.

STRICT JSON: the frame contains only finite floats, ints, strings, bools, nulls, lists and objects -- never a bare
NaN/Infinity -- so ``json.dumps(frame, allow_nan=False)`` succeeds and any strict cross-language consumer can read it.
Missing / unsupported quantities (a temperature field, an electric potential) serialise to null, NEVER to 0.
"""
from __future__ import annotations

import json
import math

from experiments.sandbox_foundation.living_chamber import ChamberState
from experiments.sandbox_foundation.snapshot import ModelRunReceipt, QuantityKind, _canon, numerics_verified

K = QuantityKind
SCHEMA = "living-chamber-frame-v1"

# tolerances the frame's numerics block is judged against (the chamber genuinely achieves far tighter -- charge ~1e-18,
# component identity ~0); chosen to reflect what the step achieves across the regime, never widened to pass a fixture.
_CHARGE_TOL_M = 1e-10
_COMPONENT_TOL_MOL = 1e-9
_ASSUMPTIONS = (
    "isothermal 298.15 K (the sourced Ka/Kw/Davies data is 25 C)",
    "fast local aqueous equilibrium -- an ALGEBRAIC projection, not a kinetic rate law",
    "neutral acetic-acid transport ONLY; no ion or charge transport (Nernst-Planck deferred, interface.py E3)",
    "transport conductances are CALLER-DECLARED, not source-verified",
    "explicit-Euler transport; no a-posteriori truncation-error bound vs the exact solution")


class ChamberFrameError(ValueError):
    """A chamber frame violates the observation contract; a presenter must refuse it rather than draw it."""


# documented field set for the LibGibson interactive-instrument epic #125 (what a consumer can rely on):
LIBGIBSON_FRAME_FIELDS = {
    "schema_version": "str frame schema id (reject unknown)",
    "tick, time_s": "CANONICAL model tick (int) and physical time (s)",
    "global_totals_mol": "CANONICAL conserved {acetate, sodium} summed over the closed world (mol)",
    "cells[].totals_mol": "CANONICAL per-cell conserved components {acetate, sodium} (mol)",
    "cells[].concentrations_mol_per_L": "MODEL_DERIVED {HAc, Ac-, H+, OH-, Na+, NaAc} (mol/L)",
    "cells[].pH / pH_activity / pH_concentration": "MODEL_DERIVED, activity-based pH primary; NEVER a sensor reading",
    "cells[].verdict, caveats": "the aqueous solver's own claim status + honest qualifiers",
    "cells[].charge_residual_M": "local electroneutrality residual (mol/L)",
    "membranes[]": "oriented (tail, head), g_HAc, valve, conductance, last_transfer_mol, last_flux_mol_per_s",
    "receipt": "admission + numerics_disclosure + supported_prediction + observed_measurement(False) + label (A2)",
    "trust": "the 5-key receipt-derived verdict, re-derivable by the consumer",
    "unsupported": "quantities the model does NOT supply -> {kind: UNSUPPORTED, value: null}, never a fabricated 0",
}


def _model_identity(state: ChamberState) -> str:
    w = state.world
    return _canon("living-chamber-v1",
                  [[float(c.n_acetate_mol), float(c.n_sodium_mol), float(c.volume_m3), float(c.temperature_K),
                    c.activity_model, bool(c.include_ion_pair)] for c in w.chambers],
                  [[int(m.tail), int(m.head), float(m.g_HAc_m3_per_s), float(m.valve)] for m in w.membranes],
                  int(state.tick))


def chamber_numerics(state: ChamberState) -> dict:
    """The numerics block: the two residuals the state's quality is CHECKED on (local charge closure and the
    component-identity A E(b) = b), each against a declared tolerance.  The disclosure (via ModelRunReceipt) names
    these as the checked residuals and flags the explicit-Euler truncation error as unbounded."""
    charge = max((float(sp.charge_balance_residual) for sp in state.specs), default=0.0)
    comp = max((state.world.chambers[i].component_identity_residual(state.specs[i])
                for i in range(len(state.world.chambers))), default=0.0)
    return {
        "solver": "aqueous_equilibrium.solve (two independent routes) + explicit-Euler neutral-HAc transport",
        "convergence_status": "NOT_ITERATIVE",
        "tolerances": {"charge_residual_M": _CHARGE_TOL_M, "component_identity_mol": _COMPONENT_TOL_MOL},
        "residuals": {"charge_residual_M": charge, "component_identity_mol": comp},
        "assumptions": list(_ASSUMPTIONS),
    }


def chamber_receipt(state: ChamberState) -> ModelRunReceipt:
    """A transport-model receipt: the composed model's admission is SYNTHETIC because the conductances are
    caller-declared (even though the per-cell equilibrium is source-backed) -- so supported_prediction is False and
    observed_measurement is False.  numerically_verified is computed from the residuals vs tolerances above."""
    return ModelRunReceipt.unadmitted_transport(_model_identity(state), chamber_numerics(state))


def _finite(x) -> float:
    """Coerce to a finite float or raise -- the frame must never carry a bare NaN/Infinity (strict-JSON contract)."""
    v = float(x)
    if not math.isfinite(v):
        raise ChamberFrameError(f"non-finite value {x!r} cannot enter a strict-JSON chamber frame")
    return v


def chamber_frame(state: ChamberState) -> dict:
    """Serialise a ChamberState into a renderer-neutral, strict-JSON frame dict (see module docstring +
    LIBGIBSON_FRAME_FIELDS).  Every numeric is finite; unsupported quantities are null, never 0."""
    w = state.world
    receipt = chamber_receipt(state).to_dict()
    last = {e.face: e for e in state.ledger}
    cells = []
    for i, (ch, sp) in enumerate(zip(w.chambers, state.specs)):
        cells.append({
            "index": i,
            "volume_m3": _finite(ch.volume_m3),
            "temperature_K": _finite(ch.temperature_K),
            "totals_mol": {"acetate": _finite(ch.n_acetate_mol), "sodium": _finite(ch.n_sodium_mol)},
            "concentrations_mol_per_L": {
                "HAc": _finite(sp.hac_M), "Ac-": _finite(sp.ac_minus_M), "H+": _finite(sp.h_plus_M),
                "OH-": _finite(sp.oh_minus_M), "Na+": _finite(sp.na_plus_M), "NaAc": _finite(sp.naac_M)},
            "c_HAc_mol_per_m3": _finite(ch.c_hac_mol_per_m3(sp)),
            "pH": _finite(sp.pH), "pH_activity": _finite(sp.pH_activity),
            "pH_concentration": _finite(sp.pH_concentration), "ionic_strength_M": _finite(sp.ionic_strength_M),
            "verdict": str(sp.verdict), "caveats": [str(c) for c in sp.caveats],
            "charge_residual_M": _finite(sp.charge_balance_residual),
            "kinds": {"totals_mol": K.CANONICAL.value, "concentrations_mol_per_L": K.MODEL_DERIVED.value,
                      "pH": K.MODEL_DERIVED.value},
        })
    membranes = []
    for k, m in enumerate(w.membranes):
        e = last.get(k)
        membranes.append({
            "face": k, "tail": int(m.tail), "head": int(m.head),
            "g_HAc_m3_per_s": _finite(m.g_HAc_m3_per_s), "valve": _finite(m.valve),
            "conductance_m3_per_s": _finite(m.conductance),
            "last_transfer_mol": _finite(e.amount_mol) if e is not None else 0.0,
            "last_flux_mol_per_s": _finite(e.flux_mol_per_s) if e is not None else 0.0})
    totals = w.totals()
    return {
        "schema_version": SCHEMA,
        "tick": int(state.tick), "time_s": _finite(state.time_s),
        "model_identity": _model_identity(state),
        "global_totals_mol": {"acetate": _finite(totals[0]), "sodium": _finite(totals[1])},
        "cells": cells, "membranes": membranes,
        "receipt": receipt,
        "trust": {key: receipt[key] for key in ("label", "admitted", "numerically_verified",
                                                "supported_prediction", "observed_measurement")},
        "unsupported": {"temperature_field_K": {"kind": K.UNSUPPORTED.value, "unit": "K", "value": None},
                        "electric_potential_V": {"kind": K.UNSUPPORTED.value, "unit": "V", "value": None}},
        "assumptions": list(_ASSUMPTIONS),
    }


def validate_chamber_frame(frame: dict) -> list:
    """The contract a renderer can ENFORCE.  Returns a list of problems (empty = holds); never raises on a malformed
    frame.  Checks: strict-JSON (no NaN/Infinity, round-trips), required keys, finite pH/concentrations, UNSUPPORTED
    values are null, and -- the A2 non-negotiable -- observed_measurement is False (a simulation never observes)."""
    bad = []
    if not isinstance(frame, dict):
        return [f"frame must be a JSON object, got {type(frame).__name__}"]
    try:
        reparsed = json.loads(json.dumps(frame, allow_nan=False))   # strict round-trip: rejects NaN/Infinity
    except (ValueError, TypeError) as exc:
        return [f"frame is not strict JSON (NaN/Infinity or non-serialisable): {exc}"]
    for need in ("schema_version", "tick", "time_s", "cells", "membranes", "receipt", "trust", "unsupported",
                 "global_totals_mol"):
        if need not in reparsed:
            bad.append(f"frame lacks {need!r}")
    if bad:
        return bad
    if reparsed["schema_version"] != SCHEMA:
        bad.append(f"unknown schema_version {reparsed['schema_version']!r}")
    trust = reparsed["trust"]
    if trust.get("observed_measurement") is not False:
        bad.append("observed_measurement must be False: a simulation carries no external observation source")
    if trust.get("supported_prediction") is not False:
        bad.append("a caller-declared-transport chamber frame must not claim supported_prediction")
    # Wave F (B): recompute the trust verdict from the RECEIPT, not just the two carried booleans -- so a forged
    # receipt (edited numerics or a flipped `admitted`) that leaves trust's booleans False is still caught, closing
    # the asymmetry with libgibson_frame_example.validate_frame.
    r = reparsed.get("receipt")
    if isinstance(r, dict) and r.get("present"):
        nv = numerics_verified(r.get("numerics"))
        if trust.get("numerically_verified") != nv:
            bad.append("trust.numerically_verified disagrees with the receipt's numerics (recomputed)")
        if r.get("admitted") is not False:
            bad.append("a caller-declared-transport receipt must not be admitted")
        if trust.get("supported_prediction") is not ((r.get("admitted") is True) and nv):
            bad.append("trust.supported_prediction is not (admitted AND numerically_verified) recomputed")
    for c in reparsed["cells"]:
        for key in ("pH", "pH_activity", "charge_residual_M"):
            v = c.get(key)
            if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)):
                bad.append(f"cell {c.get('index')}: {key} must be a finite number, got {v!r}")
        for nm, v in c.get("concentrations_mol_per_L", {}).items():
            if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= -1e-15):
                bad.append(f"cell {c.get('index')}: [{nm}] must be a finite non-negative number, got {v!r}")
    for nm, q in reparsed["unsupported"].items():
        if q.get("kind") != K.UNSUPPORTED.value or q.get("value") is not None:
            bad.append(f"unsupported[{nm!r}] must be kind UNSUPPORTED with value null (never 0)")
    return bad


class ChamberPresenter:
    """A MOCK headless presenter (LibGibson's role).  Receives ONLY JSON text, holds no model handle, and NEVER
    presents a model prediction as a physical measurement.  It refuses a frame that breaks the contract."""

    def render(self, frame_text: str, *, strict: bool = True) -> str:
        try:
            frame = json.loads(frame_text)
        except (TypeError, ValueError) as exc:
            raise ChamberFrameError(f"frame is not valid JSON text: {exc}") from exc
        problems = validate_chamber_frame(frame)
        if problems and strict:
            raise ChamberFrameError("; ".join(problems))
        t = frame["trust"]
        lines = [f"tick {frame['tick']}  t={frame['time_s']:g} s  [{t['label']}]"]
        if problems:
            lines.append("  !! CONTRACT VIOLATIONS: " + "; ".join(problems))
        # this frame's transport is caller-declared -> never a supported prediction, and NEVER a measurement.
        lines.append("  ** MODEL STATE -- source-backed equilibrium under CALLER-DECLARED transport; "
                     "NOT A PHYSICAL MEASUREMENT (no external observation) **")
        for c in frame["cells"]:
            conc = c["concentrations_mol_per_L"]
            tag = f" ({'; '.join(c['caveats'])})" if c.get("caveats") else ""
            lines.append(f"  cell{c['index']}: pH={c['pH']:.4f}  HAc={conc['HAc']:.4g} Ac-={conc['Ac-']:.4g} "
                         f"Na+={conc['Na+']:.4g}  [{c['verdict']}]{tag}")
        for m in frame["membranes"]:
            lines.append(f"  face{m['face']} {m['tail']}->{m['head']}: valve={m['valve']:g}  "
                         f"last transfer={m['last_transfer_mol']:.4g} mol")
        for nm, q in frame["unsupported"].items():
            lines.append(f"  {nm}: n/a (unsupported, unit {q['unit']})")
        return "\n".join(lines)
