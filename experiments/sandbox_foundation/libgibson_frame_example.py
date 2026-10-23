"""Wave G/F -- the FROZEN LibGibson frame example, now a typed, receipted, end-to-end observation contract.

Ooh yeah, can do -- but SmartChem does NOT draw anything.  This module publishes renderer-neutral observation
frames so the LibGibson side can learn what a frame MEANS without ever interpreting pixels as scientific
measurements.  It demonstrates:
  * canonical model tick + physical timestamp; geometry; BOUNDARY IDENTITY (oriented interfaces + boundary material);
  * the MODEL digest vs the EVIDENCE/ADMISSION digest, independent;
  * F1 -- a `ModelRunReceipt` travelling in the frame: admission level / verdict, numerical assumptions (solver,
    tolerances, residuals, convergence status) and both identities.  A frame reader can tell an admitted,
    numerically-verified quantity from an unadmitted / unverified one without re-deriving anything;
  * F2 -- EVERY quantity is typed exactly one of CANONICAL / MODEL_DERIVED / UNSUPPORTED / ILLUSTRATION.  Missing or
    unsupported data is an explicit null (never 0); illustration is flagged `measurement: false`;
  * F3 -- an end-to-end demo: a NEUTRAL tracer pair crossing a CONFIGURABLE selective membrane (Wave E's
    `interface.three_chamber_membrane`), evolved over real model ticks (a valve opens mid-run), each tick serialised
    to JSON text and consumed by a HEADLESS mock presenter that imports no LibGibson and cannot reach the model;
  * F4 -- the runtime-contract invariants: presentation-frequency independence and NO write-back (red-team #15).

The frame is a plain JSON-serialisable dict (no numpy, no renderer handles), so it survives the process boundary to
LibGibson unchanged.  The sandbox stays headless and fully functional with no LibGibson present.

WHERE CONTROL INPUT LIVES (the #15 design rule): user input (a valve click, a geometry edit) is a COMMAND to the
SmartChem-owned model (`ModelRun.set_valve`), which is recorded in the trajectory.  A frame is read-only output; the
frame/snapshot types expose no handle to the model, and `ModelRun.snapshot()` is built from private copies.
"""
from __future__ import annotations

import json
import math

import numpy as np

from experiments.sandbox_foundation.interface import Apparatus, three_chamber_membrane, transport
from experiments.sandbox_foundation.mechanism_types import AdmissionLevel
from experiments.sandbox_foundation.snapshot import (
    MODEL_VALUE_KINDS, ModelRunReceipt, PhysicalWorldSnapshot, QuantityKind, _canon, absent_receipt_dict,
    ascii_render, compute_digests, numerics_verified, trust_label)

K = QuantityKind


class FrameContractError(ValueError):
    """A frame violates the typing contract; a presenter must refuse it rather than draw it."""


# ------------------------------------------------------------------------------------------- the original example
def example_snapshot() -> tuple:
    """A representative 3-cell / 2-interface frame.  Returns (snapshot, interfaces) where interfaces are the
    oriented (tail, head) cell pairs of the two internal faces.  One cell/species is marked MISSING to exercise
    the invalid mask (e.g. a sensor dropout / an unmodelled region).  Carries NO receipt: the frame will say so."""
    species = ("acetate", "tracer")
    cell_volumes_m3 = [1.0e-6, 1.5e-6, 2.0e-6]
    amounts_mol = np.array([[3.0e-3, 0.0],
                            [1.0e-3, 2.0e-3],
                            [0.0, 1.0e-3]])
    valid_mask = np.array([[True, True],
                           [True, False],     # the 'tracer' in cell 1 is MISSING (not measured) -> reads NaN
                           [True, True]])
    interfaces = ((0, 1), (1, 2))             # a 3-cell chain: two oriented internal faces
    snap = PhysicalWorldSnapshot(
        species, cell_volumes_m3, amounts_mol, valid_mask,
        units={"amount": "mol", "volume": "m^3", "time": "s", "concentration": "mol/m^3"},
        model_tick=7, physical_time_s=0.35,
        conservation_diagnostics={"note": "SYNTHETIC example; totals over VALID cells only"},
        numerical_uncertainty={"amount_abs_mol": 1.0e-12},
        boundary_material=("inert wall", "inert wall"),
        evidence={"provenance": "SYNTHETIC example frame", "sources": [], "admission": "none (illustrative)"},
        display_hints={"colormap": "viridis", "sep": " | "})
    return snap, interfaces


# ------------------------------------------------------------------------------------------------ frame (F1 + F2)
def to_frame(snap: PhysicalWorldSnapshot, interfaces) -> dict:
    """Serialise a snapshot into a renderer-neutral, JSON-safe frame dict for LibGibson.  Authoritative numeric
    fields carry their units; invalid cells/species are null (JSON for NaN), never 0.  display_hints are included
    but are explicitly cosmetic and excluded from model_digest.  Every quantity is typed (see module docstring)."""
    conc = snap.concentration_mol_per_m3()
    amt = snap.amounts_mol
    mask = snap.valid_mask
    C = len(snap.cell_volumes_m3)
    rec = snap.receipt

    def _col(arr, s):
        return [(None if not mask[i, s] else float(arr[i, s])) for i in range(arr.shape[0])]

    def _kinds(s, valid_kind):
        return [(K.UNSUPPORTED.value if not mask[i, s] else valid_kind.value) for i in range(C)]

    receipt = rec.to_dict() if rec is not None else absent_receipt_dict()
    return {
        "schema_version": snap.schema_version,
        "model_digest": snap.model_digest,            # authoritative content identity
        "evidence_digest": snap.evidence_digest,      # admission identity, independent of the model digest
        "model_tick": snap.model_tick,
        "physical_time_s": snap.physical_time_s,
        "receipt": receipt,                           # F1: admission + numerics + both identities
        "trust": {k: receipt[k] for k in ("label", "admitted", "numerically_verified",
                                          "supported_prediction", "observed_measurement")},
        "quantity_kinds": {"model_tick": K.CANONICAL.value, "physical_time_s": K.CANONICAL.value,
                           "cell_volumes_m3": K.CANONICAL.value, "amount_mol": K.CANONICAL.value,
                           "concentration_mol_per_m3": K.MODEL_DERIVED.value},
        "geometry": {
            "n_cells": C,
            "cell_volumes_m3": [float(v) for v in snap.cell_volumes_m3],
            "interfaces": [list(e) for e in interfaces],      # oriented (tail, head) cell pairs
            "boundary_material": list(snap.boundary_material),
        },
        "species": list(snap.species),
        "fields": {
            nm: {"amount_mol": _col(amt, s),
                 "concentration_mol_per_m3": _col(conc, s),
                 "kinds": {"amount_mol": _kinds(s, K.CANONICAL),                     # per-element: CANONICAL | UNSUPPORTED
                           "concentration_mol_per_m3": _kinds(s, K.MODEL_DERIVED)}}  # MODEL_DERIVED | UNSUPPORTED
            for s, nm in enumerate(snap.species)
        },
        "invalid_mask": [[bool(not mask[i, s]) for s in range(len(snap.species))]
                         for i in range(C)],   # True = MISSING/invalid (UNSUPPORTED)
        "unsupported": {nm: {"kind": K.UNSUPPORTED.value, "unit": u, "values": [None] * C}
                        for nm, u in snap.unsupported_quantities.items()},
        "illustration": {nm: {"kind": K.ILLUSTRATION.value, "measurement": False,
                              "values": list(_jsonify_plain(v.get("values", ()))),
                              "note": str(v.get("note", "decorative; not a measurement"))}
                         for nm, v in snap.illustration.items()},
        "units": dict(snap.units),
        "conservation_diagnostics": _jsonify_plain(snap.conservation_diagnostics),
        "numerical_uncertainty": _jsonify_plain(snap.numerical_uncertainty),
        "evidence": _jsonify_plain(snap.evidence),   # carried so a renderer can recompute evidence_digest
        "display_hints": dict(snap.display_hints),    # renderer-neutral cosmetics (excluded from model_digest)
    }


def _jsonify_plain(obj):
    """Frozen (MappingProxyType / tuple) -> plain dict / list, so the frame holds NO shared mutable state."""
    from collections.abc import Mapping
    if isinstance(obj, Mapping):
        return {str(k): _jsonify_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify_plain(v) for v in obj]
    return obj


_RECEIPT_REQUIRED = ("present", "admitted", "numerically_verified", "supported_prediction",
                     "observed_measurement", "label")
_RECEIPT_PRESENT_REQUIRED = ("model_identity", "admission_level", "admission_derived", "law_levels",
                             "admission_identities", "numerics")


def derive_trust(frame) -> dict:
    """The trust verdict RE-DERIVED from the frame's receipt alone -- never read from the carried `trust` block.
    numerically_verified is recomputed from receipt['numerics'] (tolerances vs residuals); admitted is the receipt's
    own admission stamp, honoured only if it is internally coherent (derived, and at a SOURCE_VERIFIED-or-better level).
    Anything malformed or absent derives to the safe side: unadmitted / unverified."""
    try:
        r = frame["receipt"]
        if r.get("present") is not True:
            return {"label": absent_receipt_dict()["label"], "admitted": False, "numerically_verified": False,
                    "supported_prediction": False, "observed_measurement": False}
        verified = numerics_verified(r.get("numerics"))
        level = r.get("admission_level")
        admitted = (r.get("admitted") is True and r.get("admission_derived") is True and level in (
            AdmissionLevel.SOURCE_VERIFIED.value, AdmissionLevel.BENCHMARK_VALIDATED.value))
        return {"label": trust_label(admitted, str(level), verified), "admitted": admitted,
                "numerically_verified": verified, "supported_prediction": admitted and verified,
                "observed_measurement": False}       # a simulation frame carries no external observation source
    except (KeyError, TypeError, AttributeError, IndexError, ValueError):
        return {"label": "UNREADABLE-RECEIPT(UNADMITTED+NUMERICS-UNVERIFIED)", "admitted": False,
                "numerically_verified": False, "supported_prediction": False, "observed_measurement": False}


def validate_frame(frame) -> list:
    """The contract a renderer can ENFORCE.  Returns a list of problems (empty = contract holds); NEVER raises on a
    malformed frame (a missing key is a contract violation, reported as one).  It checks (1) the 4-way typing, (2) that
    the carried `trust` block, the receipt's own derived flags and the model/evidence digests are all BOUND to the
    receipt and the frame's content -- recomputed here, not believed.  Honest limit: the digests are unkeyed hashes, so
    this detects an inconsistent or partially-edited frame, not a forger who rewrites receipt AND recomputes digests."""
    try:
        return _validate(frame)
    except (KeyError, TypeError, AttributeError, IndexError, ValueError) as exc:
        return [f"malformed frame: {type(exc).__name__}: {exc}"]


def _validate(frame) -> list:
    if not isinstance(frame, dict):
        return [f"frame must be a JSON object, got {type(frame).__name__}"]
    bad = []
    legal = {k.value for k in K}
    for need in ("receipt", "trust", "quantity_kinds", "fields", "unsupported", "illustration", "geometry",
                 "species", "invalid_mask", "evidence", "units", "conservation_diagnostics", "numerical_uncertainty",
                 "model_digest", "evidence_digest", "schema_version", "model_tick", "physical_time_s"):
        if need not in frame:
            bad.append(f"frame lacks {need!r}")
    if bad:
        return bad
    for nm, kind in frame["quantity_kinds"].items():
        if kind not in legal or kind in (K.UNSUPPORTED.value, K.ILLUSTRATION.value):
            bad.append(f"quantity_kinds[{nm!r}]={kind!r} is not a measurement kind")
    species, mask = frame["species"], frame["invalid_mask"]
    for nm in species:
        fld = frame["fields"].get(nm)
        if not isinstance(fld, dict) or not isinstance(fld.get("kinds"), dict):
            bad.append(f"fields[{nm!r}] must be an object with a 'kinds' object")
            continue
        for q in ("amount_mol", "concentration_mol_per_m3"):
            if q not in fld or q not in fld["kinds"]:
                bad.append(f"fields[{nm!r}] lacks {q!r} values or kinds")
                continue
            vals, kinds = fld[q], fld["kinds"][q]
            if not isinstance(vals, list) or not isinstance(kinds, list) or len(kinds) != len(vals):
                bad.append(f"{nm}.{q}: kinds/values must be equal-length lists")
                continue
            for i, (k, v) in enumerate(zip(kinds, vals)):
                if k not in legal:
                    bad.append(f"{nm}.{q}[{i}]: unknown kind {k!r}")
                elif k == K.UNSUPPORTED.value and v is not None:
                    bad.append(f"{nm}.{q}[{i}]: UNSUPPORTED must be null, got {v!r}")
                elif k in (K.CANONICAL.value, K.MODEL_DERIVED.value) and (
                        v is None or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)):
                    bad.append(f"{nm}.{q}[{i}]: {k} must be a finite number, got {v!r}")
                elif k == K.ILLUSTRATION.value:
                    bad.append(f"{nm}.{q}[{i}]: ILLUSTRATION cannot sit in a measurement field")
    for nm, q in frame["unsupported"].items():
        if q.get("kind") != K.UNSUPPORTED.value or any(v is not None for v in q.get("values", [])):
            bad.append(f"unsupported[{nm!r}] must be kind UNSUPPORTED with all-null values")
    for nm, q in frame["illustration"].items():
        if q.get("kind") != K.ILLUSTRATION.value or q.get("measurement") is not False:
            bad.append(f"illustration[{nm!r}] must be kind ILLUSTRATION with measurement=false")
    if bad:                                   # the binding checks below assume a structurally sound frame
        return bad

    # ---- (2a) receipt shape + the receipt's own flags re-derived from its numerics ---------------------------
    r = frame["receipt"]
    if not isinstance(r, dict) or any(k not in r for k in _RECEIPT_REQUIRED):
        return ["receipt is missing or malformed"]
    derived = derive_trust(frame)
    if r["present"] is True:
        if any(k not in r for k in _RECEIPT_PRESENT_REQUIRED):
            return ["receipt claims present but lacks its identity/admission/numerics fields"]
        if r["admitted"] is True and not derived["admitted"]:
            bad.append("receipt claims admitted but is not coherent (needs admission_derived and a "
                       "SOURCE_VERIFIED+ level)")
        if r["numerically_verified"] != derived["numerically_verified"]:
            bad.append("receipt.numerically_verified disagrees with its own numerics (recomputed)")
        if r["supported_prediction"] != derived["supported_prediction"]:
            bad.append("receipt.supported_prediction disagrees with admitted AND numerically_verified (recomputed)")
        if r.get("observed_measurement") is not False:
            bad.append("receipt.observed_measurement must be False -- a simulation carries no external observation "
                       "source and can never report a physical measurement")
        if r["label"] != derived["label"]:
            bad.append("receipt.label disagrees with the recomputed verdict")
    elif r != absent_receipt_dict():
        bad.append("an absent receipt must read exactly as the explicit unadmitted/unverified one")

    # ---- (2b) the carried trust block must EQUAL the receipt-derived verdict ----------------------------------
    if frame["trust"] != derived:
        bad.append(f"trust block {frame['trust']!r} is not the verdict derived from the receipt {derived!r}")

    # ---- (2c) masks, then both digests recomputed from the frame's own content ------------------------------
    C = len(frame["geometry"]["cell_volumes_m3"])
    if len(mask) != C or any(len(row) != len(species) for row in mask):
        return bad + ["invalid_mask shape disagrees with cells x species"]
    for s, nm in enumerate(species):
        for q in ("amount_mol", "concentration_mol_per_m3"):
            for i, k in enumerate(frame["fields"][nm]["kinds"][q]):
                if (k == K.UNSUPPORTED.value) != bool(mask[i][s]):
                    bad.append(f"{nm}.{q}[{i}]: kind disagrees with invalid_mask")
    if bad:
        return bad
    amt = [[frame["fields"][nm]["amount_mol"][i] for nm in species] for i in range(C)]
    amt = [[0.0 if v is None else v for v in row] for row in amt]
    model, evid = compute_digests(
        schema_version=frame["schema_version"], species=species, cell_volumes_m3=frame["geometry"]["cell_volumes_m3"],
        amounts_mol=amt, valid_mask=[[not m for m in row] for row in mask], units=frame["units"],
        model_tick=frame["model_tick"], physical_time_s=frame["physical_time_s"],
        conservation_diagnostics=frame["conservation_diagnostics"], numerical_uncertainty=frame["numerical_uncertainty"],
        boundary_material=frame["geometry"]["boundary_material"],
        unsupported={nm: q["unit"] for nm, q in frame["unsupported"].items()}, evidence=frame["evidence"],
        receipt_model_part=(["receipt-model", r["model_identity"], r["numerics"]] if r["present"] is True else None),
        receipt_admission_part=(["receipt-admission", r["admission_level"], r["admitted"], r["admission_derived"],
                                 r["law_levels"], r["admission_identities"]] if r["present"] is True else None))
    if frame["model_digest"] != model:
        bad.append("model_digest does not match the frame's authoritative content (recomputed)")
    if frame["evidence_digest"] != evid:
        bad.append("evidence_digest does not match the frame's evidence + receipt admission (recomputed)")
    return bad


def model_values(frame: dict) -> dict:
    """The model's own reported VALUES (canonical state + model-derived predictions):
    {(species, quantity): [(cell, value)...]} for CANONICAL / MODEL_DERIVED non-null entries.  These are NOT physical
    measurements -- no external observation produced them, so a renderer must present them as model output, never as
    sensed / measured data.  Illustration and UNSUPPORTED are structurally absent."""
    problems = validate_frame(frame)
    if problems:
        raise FrameContractError("; ".join(problems))
    out = {}
    for nm, fld in frame["fields"].items():
        for q in ("amount_mol", "concentration_mol_per_m3"):
            out[(nm, q)] = [(i, v) for i, (k, v) in enumerate(zip(fld["kinds"][q], fld[q]))
                            if k in {m.value for m in MODEL_VALUE_KINDS}]
    return out


def headless_replay(snap: PhysicalWorldSnapshot, n_renders: int) -> dict:
    """Render the frame n_renders times (the LibGibson consumer's job, mocked) and confirm the authoritative model
    state and digest are byte-identical before and after -- rendering is a PURE read."""
    before_digest = snap.model_digest
    before_amounts = snap.amounts_mol.copy()
    for _ in range(max(0, int(n_renders))):
        ascii_render(snap)
    return {
        "renders": int(n_renders),
        "model_digest_unchanged": snap.model_digest == before_digest,
        "amounts_unchanged": bool(np.array_equal(snap.amounts_mol, before_amounts)),
    }


# --------------------------------------------------------------------------------------- the headless presenter (F3)
class HeadlessPresenter:
    """A MOCK presentation layer (LibGibson's role).  It receives ONLY JSON text -- the process boundary -- so it
    holds no numpy array, no snapshot, no model reference: there is structurally no object through which it could
    write back.  It refuses a frame that breaks the typing contract, banners anything not a validated measurement, and
    draws illustration with a visibly different glyph set (never as a number)."""

    def render(self, frame_text: str, *, strict: bool = True) -> str:
        """strict (default): refuse any frame that breaks the contract.  strict=False: draw it anyway but with the
        banner FORCED on and the violations listed.  Either way validated-vs-not is decided from the RECEIPT-derived
        verdict (`derive_trust`), never from the frame's carried `trust` block."""
        try:
            frame = json.loads(frame_text)
        except (TypeError, ValueError) as exc:
            raise FrameContractError(f"frame is not valid JSON text: {exc}") from exc
        problems = validate_frame(frame)
        if problems and strict:
            raise FrameContractError("; ".join(problems))
        try:
            return self._draw(frame, problems)
        except (KeyError, TypeError, AttributeError, IndexError, ValueError) as exc:
            raise FrameContractError(f"frame is not drawable: {type(exc).__name__}: {exc}") from exc

    @staticmethod
    def _draw(frame: dict, problems: list) -> str:
        t = derive_trust(frame)
        lines = [f"tick {frame['model_tick']}  t={frame['physical_time_s']:g} s  [{t['label']}]"]
        if problems:
            lines.append("  !! CONTRACT VIOLATIONS: " + "; ".join(problems))
        if problems or not t["supported_prediction"]:
            lines.append("  ** SIMULATED STATE -- NOT EVEN A SUPPORTED PREDICTION (unadmitted or numerics unverified) **")
        elif not t["observed_measurement"]:
            lines.append("  ** SUPPORTED MODEL PREDICTION -- NOT A PHYSICAL MEASUREMENT (no external observation) **")
        g = frame["geometry"]
        for i in range(g["n_cells"]):
            cells = []
            for nm in frame["species"]:
                v = frame["fields"][nm]["concentration_mol_per_m3"][i]
                cells.append(f"{nm}={'n/a' if v is None else format(v, '.4g')}")
            lines.append(f"  cell{i}: " + "  ".join(cells))
        for k, b in enumerate(g["boundary_material"]):
            lines.append(f"  face{k}: {b}")
        for nm, q in frame["illustration"].items():
            ramp = "".join(" .:-=+*#%@"[min(9, max(0, int(float(x) * 9.999)))] for x in q["values"])
            lines.append(f"  ~{nm}~ [{ramp}] (illustration, not a measurement)")
        for nm, q in frame["unsupported"].items():
            lines.append(f"  {nm}: n/a (unsupported, unit {q['unit']})")
        return "\n".join(lines)


# ----------------------------------------------------------------------------------- the model side: ModelRun (F3, F4)
_TOL = {"conservation_abs_mol": 1.0e-15, "positivity_violation_mol": 0.0, "passive_witness_excess_W": 1.0e-12}
_ASSUMPTIONS = ("isothermal", "NEUTRAL tracers only (charged transport fail-closed in interface.py E3)",
                "conductances are caller-declared, not source-verified", "no truncation-error bound vs the exact PDE",
                "passive Fick interface law; no reactions")


def membrane_world():
    """The F3 demo world: 3 chambers, two material boundaries.  X crosses both membranes; Y crosses only the left
    one (right membrane = a wall for Y); the right valve starts SHUT.  Returns (apparatus, n0 (C,S) mol)."""
    app = three_chamber_membrane(left_pass=(True, True), right_pass=(True, False), valves=(1.0, 0.0))
    n0 = np.array([[2.0e-3, 2.0e-3], [0.0, 0.0], [0.0, 0.0]])
    return app, n0


class ModelRun:
    """The SmartChem-owned model.  Holds the authoritative state PRIVATELY; presentation gets `snapshot()` (a fresh
    deeply-immutable object over private COPIES) and nothing else.  `snapshot()` is a pure read: it advances nothing,
    counts nothing, and a presenter can call it zero, one or many times per tick."""

    def __init__(self, apparatus: Apparatus, n0, dt_s: float, *, schedule=None):
        self._app = apparatus
        n = np.array(n0, dtype=float)
        n.setflags(write=False)
        self._n = n
        self._dt = float(dt_s)
        self._tick = 0
        self._t = 0.0
        self._schedule = {int(k): tuple(v) for k, v in (schedule or {}).items()}   # tick -> new valves (a model input)
        self._numerics_residuals = {}
        self._commands = []

    # -- control: the ONLY way valve state changes, and it is part of the recorded trajectory ------------
    def set_valve(self, face: int, theta: float) -> None:
        self._commands.append((self._tick, int(face), float(theta)))
        self._app = self._app.set_valve(face, theta)

    # -- evolution ----------------------------------------------------------------------------------------
    def advance(self) -> None:
        if self._tick in self._schedule:
            self._app = self._app.with_valves(self._schedule[self._tick])
        before = self._n
        with np.errstate(invalid="ignore"):                  # mesh.py forms -inf - -inf on empty cells, then masks it
            diss = self._app.dissipation(before)
        # a NaN witness is NOT "no excess" (python's max(0.0, nan) would quietly say 0.0) -> None = unverified
        excess = None if bool(np.isnan(diss).any()) else float(max(0.0, float(np.max(diss, initial=-math.inf))))
        with np.errstate(invalid="ignore"):
            after = transport(self._app, before, self._dt, policy="raise")
        after.setflags(write=False)
        self._numerics_residuals = {
            "conservation_abs_mol": float(np.max(np.abs(after.sum(axis=0) - before.sum(axis=0)))),
            "positivity_violation_mol": float(max(0.0, -float(np.min(after)))),
            "passive_witness_excess_W": excess,
        }
        self._n = after
        self._tick += 1
        self._t += self._dt

    # -- observation (pure) -----------------------------------------------------------------------------
    @property
    def interfaces(self) -> tuple:
        return tuple((int(f.tail), int(f.head)) for f in self._app.mesh.faces)

    def _model_identity(self) -> str:
        a = self._app
        return _canon("apparatus-v1", [t.name for t in a.species], list(a.mesh.volumes_m3),
                      [[int(f.tail), int(f.head), float(f.area_m2), float(f.distance_m)] for f in a.mesh.faces],
                      a.base_conductance.tolist(), float(a.T_K), self._dt)

    def _boundary_material(self) -> tuple:
        a, out = self._app, []
        for k, f in enumerate(a.mesh.faces):
            names = [t.name for t in a.species]
            passes = [nm for nm, g in zip(names, a.base_conductance[k]) if g > 0]
            walls = [nm for nm in names if nm not in passes]
            out.append(f"face {k} cells {int(f.tail)}->{int(f.head)}: passes {passes or 'none'}, "
                       f"wall for {walls or 'none'}, valve={a.valves[k]:g}")
        return tuple(out)

    def snapshot(self) -> PhysicalWorldSnapshot:
        a, n = self._app, self._n
        numerics = {"solver": "explicit-Euler passive-interface transport (interface.transport)",
                    "convergence_status": "NOT_ITERATIVE" if self._tick > 0 else "INITIAL_CONDITION",
                    "dt_s": self._dt, "substeps": 1,
                    "dt_max_s": (None if math.isinf(a.transport_dt_max()) else float(a.transport_dt_max())),
                    "tolerances": dict(_TOL), "residuals": dict(self._numerics_residuals),
                    "assumptions": list(_ASSUMPTIONS)}
        receipt = ModelRunReceipt.unadmitted_transport(self._model_identity(), numerics)
        conc = n / np.asarray(a.mesh.volumes_m3, float)[:, None]
        top = float(conc.max())
        glow = [] if top <= 0 else [float(x) for x in (conc.max(axis=1) / top)]
        return PhysicalWorldSnapshot(
            tuple(t.name for t in a.species), a.mesh.volumes_m3, n, np.ones(n.shape, dtype=bool),
            {"amount": "mol", "volume": "m^3", "time": "s", "concentration": "mol/m^3"},
            self._tick, self._t,
            conservation_diagnostics={"species_totals_mol": n.sum(axis=0).tolist()},
            numerical_uncertainty={"discretisation_error_bound": None,
                                   "note": "UNKNOWN: explicit Euler, no a-posteriori error bound"},
            boundary_material=self._boundary_material(),
            evidence={"provenance": "SYNTHETIC passive-membrane demo", "sources": [],
                      "admission": "none: caller-declared conductances"},
            display_hints={"colormap": "viridis"},
            receipt=receipt,
            illustration={"glow": {"values": glow, "note": "decorative brightness ramp; not a measurement"}},
            unsupported_quantities={"temperature_field_K": "K", "electric_potential_V": "V"})

    def trajectory_record(self) -> dict:
        """The AUTHORITATIVE record of this tick: state bytes, time, both digests, the valve configuration."""
        s = self.snapshot()
        return {"tick": self._tick, "t": self._t, "n_hex": self._n.tobytes().hex(),
                "model_digest": s.model_digest, "evidence_digest": s.evidence_digest,
                "valves": tuple(self._app.valves), "commands": tuple(self._commands)}


def present(run: ModelRun, calls: int, presenter: HeadlessPresenter = None) -> str:
    """The presentation side, `calls` times: snapshot -> frame -> JSON text (the process boundary) -> presenter."""
    presenter = presenter or HeadlessPresenter()
    text = ""
    for _ in range(max(0, int(calls))):
        frame = to_frame(run.snapshot(), run.interfaces)
        text = presenter.render(json.dumps(frame))
    return text


def run_demo(n_ticks: int = 12, calls_per_tick=1, *, run_factory=None) -> dict:
    """Evolve the membrane world for n_ticks, presenting `calls_per_tick` times per tick (an int, or a callable
    tick -> int), and return {"trajectory": [records], "screens": [last screen per tick]}.  The trajectory must NOT
    depend on how often (or whether) we present -- that is the F4 invariant."""
    app, n0 = membrane_world()
    make = run_factory or ModelRun
    run = make(app, n0, 20.0, schedule={6: (1.0, 1.0)})            # the right valve opens before tick 6's step
    calls = calls_per_tick if callable(calls_per_tick) else (lambda tick: calls_per_tick)
    traj, screens = [run.trajectory_record()], []
    screens.append(present(run, calls(0)))
    for _ in range(n_ticks):
        run.advance()
        traj.append(run.trajectory_record())
        screens.append(present(run, calls(run._tick)))
    return {"trajectory": traj, "screens": screens}
