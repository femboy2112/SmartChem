"""Wave G -- a small FROZEN experimental frame example for the LibGibson session (repo femboy2112/libgibson #125).

Ooh yeah, can do -- but SmartChem does NOT draw anything.  This module publishes ONE concrete, renderer-neutral
observation frame so the LibGibson side can learn what a frame MEANS without ever interpreting pixels as
scientific measurements.  It demonstrates, on a three-cell / two-interface world:
  * canonical model tick + physical timestamp;
  * geometry (cell volumes) and BOUNDARY IDENTITY (the oriented interfaces + the boundary material);
  * a scalar species field with explicit UNITS;
  * an explicit MISSING-DATA mask (an invalid cell/species reads NaN, never a fabricated 0);
  * the MODEL digest vs the EVIDENCE/ADMISSION digest, independent;
  * renderer-independent replay: rendering the frame any number of times cannot move the model state or digest.

The frame is a plain JSON-serialisable dict (no numpy, no renderer handles), so it survives the process boundary
to LibGibson unchanged.  The sandbox stays headless and fully functional with no LibGibson present.
"""
from __future__ import annotations

import numpy as np

from experiments.sandbox_foundation.snapshot import ascii_render, PhysicalWorldSnapshot


def example_snapshot() -> tuple:
    """A representative 3-cell / 2-interface frame.  Returns (snapshot, interfaces) where interfaces are the
    oriented (tail, head) cell pairs of the two internal faces.  One cell/species is marked MISSING to exercise
    the invalid mask (e.g. a sensor dropout / an unmodelled region)."""
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


def to_frame(snap: PhysicalWorldSnapshot, interfaces) -> dict:
    """Serialise a snapshot into a renderer-neutral, JSON-safe frame dict for LibGibson.  Authoritative numeric
    fields carry their units; invalid cells/species are null (JSON for NaN), never 0.  display_hints are included
    but are explicitly cosmetic and excluded from model_digest."""
    conc = snap.concentration_mol_per_m3()
    amt = snap.amounts_mol
    mask = snap.valid_mask

    def _col(arr, s):
        return [(None if not mask[i, s] else float(arr[i, s])) for i in range(arr.shape[0])]

    return {
        "schema_version": snap.schema_version,
        "model_digest": snap.model_digest,            # authoritative content identity
        "evidence_digest": snap.evidence_digest,      # admission identity, independent of the model digest
        "model_tick": snap.model_tick,
        "physical_time_s": snap.physical_time_s,
        "geometry": {
            "n_cells": len(snap.cell_volumes_m3),
            "cell_volumes_m3": [float(v) for v in snap.cell_volumes_m3],
            "interfaces": [list(e) for e in interfaces],      # oriented (tail, head) cell pairs
            "boundary_material": list(snap.boundary_material),
        },
        "species": list(snap.species),
        "fields": {
            nm: {"amount_mol": _col(amt, s),
                 "concentration_mol_per_m3": _col(conc, s)}
            for s, nm in enumerate(snap.species)
        },
        "invalid_mask": [[bool(not mask[i, s]) for s in range(len(snap.species))]
                         for i in range(len(snap.cell_volumes_m3))],   # True = MISSING/invalid
        "units": dict(snap.units),
        "conservation_diagnostics": dict(snap.conservation_diagnostics),
        "numerical_uncertainty": dict(snap.numerical_uncertainty),
        "display_hints": dict(snap.display_hints),    # renderer-neutral cosmetics (excluded from model_digest)
    }


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
