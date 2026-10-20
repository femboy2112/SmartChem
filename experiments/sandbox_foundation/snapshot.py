"""Wave G -- a domain-neutral, immutable PhysicalWorldSnapshot: the LibGibson observation boundary.

Ooh yeah, can do!  SYNTHETIC / experimental.  SmartChem supplies ONE narrow, immutable observation boundary and
its content identity; LibGibson (its own repo, epic #125) owns the renderer/TUI.  SmartChem must NOT implement
the renderer; a mock projection here is only enough to PROVE the contract.

THE CONTRACT (two separations, both load-bearing):
  1. AUTHORITATIVE physical state vs DISPLAY realization.  `model_digest` covers ONLY the authoritative scientific
     content (schema, geometry, species, amounts, masks, tick, time, units, conservation diagnostics).  Renderer-
     neutral `display_hints` (colours, labels, layout) are EXCLUDED, so a cosmetic change cannot move the model
     identity (Wave A3).
  2. MODEL identity vs EVIDENCE/ADMISSION identity.  `evidence_digest` covers which sources/checks/domains justify
     the model; it is independent of `model_digest`.  A source-revision change moves the evidence digest without
     silently reusing it as a model-identity receipt, and vice-versa.

THE NON-NEGOTIABLE PROPERTY: a snapshot is FROZEN with read-only arrays, and rendering is a PURE read.  Rendering
a snapshot zero, one or many times cannot alter the canonical model state or either digest.  The headless replay
test proves it: a trajectory with rendering at every step is byte-identical to one with no rendering at all.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

SCHEMA_VERSION = "phys-world-snapshot-v1"


def _canon(*parts) -> str:
    """Stable SHA-256 over a canonical serialization of the given parts (arrays by dtype+shape+bytes)."""
    h = hashlib.sha256()
    for p in parts:
        if isinstance(p, np.ndarray):
            a = np.ascontiguousarray(p)
            h.update(str(a.dtype).encode())
            h.update(str(a.shape).encode())
            h.update(a.tobytes())
        else:
            h.update(json.dumps(p, sort_keys=True, default=str).encode())
        h.update(b"\x1e")  # record separator
    return h.hexdigest()


@dataclass(frozen=True, eq=False)
class PhysicalWorldSnapshot:
    """An immutable observation of a physical world at one model tick.  Arrays are read-only.

    Authoritative scientific content (feeds model_digest): species, cell_volumes_m3, amounts_mol (cells x species),
    valid_mask (True = a real value; False = invalid/missing), units, model_tick, physical_time_s,
    conservation_diagnostics, numerical_uncertainty, boundary_material.
    Admission content (feeds evidence_digest): evidence (sources / checks / model domains).
    Renderer-neutral (EXCLUDED from both digests): display_hints."""
    species: tuple
    cell_volumes_m3: np.ndarray
    amounts_mol: np.ndarray
    valid_mask: np.ndarray
    units: dict
    model_tick: int
    physical_time_s: float
    conservation_diagnostics: dict = field(default_factory=dict)
    numerical_uncertainty: dict = field(default_factory=dict)
    boundary_material: tuple = ()
    evidence: dict = field(default_factory=dict)
    display_hints: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        vols = np.array(self.cell_volumes_m3, dtype=float)
        amt = np.array(self.amounts_mol, dtype=float)
        mask = np.array(self.valid_mask, dtype=bool)
        C, S = len(vols), len(self.species)
        if amt.shape != (C, S) or mask.shape != (C, S):
            raise ValueError("amounts_mol and valid_mask must both be (n_cells, n_species)")
        if not np.all(np.isfinite(vols)) or np.any(vols <= 0):
            raise ValueError("cell volumes must be finite and > 0")
        if np.any(~np.isfinite(amt) & mask):
            raise ValueError("a cell/species marked valid carries a non-finite amount")
        for a in (vols, amt, mask):
            a.setflags(write=False)
        object.__setattr__(self, "cell_volumes_m3", vols)
        object.__setattr__(self, "amounts_mol", amt)
        object.__setattr__(self, "valid_mask", mask)
        # model identity: authoritative content ONLY (display_hints and evidence excluded)
        model = _canon(self.schema_version, tuple(self.species), vols, amt, mask, self.units,
                       int(self.model_tick), float(self.physical_time_s), self.conservation_diagnostics,
                       self.numerical_uncertainty, tuple(self.boundary_material))
        evidence = _canon(self.schema_version, self.evidence)
        object.__setattr__(self, "model_digest", model)
        object.__setattr__(self, "evidence_digest", evidence)

    def concentration_mol_per_m3(self) -> np.ndarray:
        """A derived read; invalid cells/species are NaN, not a fabricated 0."""
        c = self.amounts_mol / self.cell_volumes_m3[:, None]
        return np.where(self.valid_mask, c, np.nan)

    def with_display_hints(self, **hints) -> "PhysicalWorldSnapshot":
        """A new snapshot with different COSMETIC hints only -- the model_digest is unchanged by construction."""
        return PhysicalWorldSnapshot(
            self.species, np.array(self.cell_volumes_m3), np.array(self.amounts_mol), np.array(self.valid_mask),
            self.units, self.model_tick, self.physical_time_s, self.conservation_diagnostics,
            self.numerical_uncertainty, self.boundary_material, self.evidence,
            {**self.display_hints, **hints}, self.schema_version)

    @classmethod
    def from_mesh(cls, system, state, *, model_tick: int = 0, evidence: Optional[dict] = None,
                  display_hints: Optional[dict] = None, numerical_uncertainty: Optional[dict] = None):
        """Build a snapshot from a Wave-D MeshSystem + MeshState (amounts per cell), with a conservation diagnostic
        from the mechanism's element/charge inventory where present."""
        vols = np.asarray(system.mesh.volumes_m3, float)
        amt = np.asarray(state.n, float)
        M = system.inventory_matrix
        totals = M @ amt.sum(axis=0)
        return cls(tuple(system.species), vols, amt, np.ones_like(amt, dtype=bool),
                   {"amount": "mol", "volume": "m^3", "time": "s"}, model_tick,
                   float(state.t), {"inventory_totals": totals.tolist()}, numerical_uncertainty or {}, (),
                   evidence or {}, display_hints or {})


# --------------------------------------------------------------------------------------------- mock renderer
def ascii_render(snap: PhysicalWorldSnapshot) -> str:
    """A MOCK renderer (LibGibson's job in its own repo).  A PURE read: it returns a string and touches nothing.
    display_hints may style it; the authoritative data is read from amounts_mol / valid_mask only."""
    sep = snap.display_hints.get("sep", " | ")
    rows = []
    for i in range(len(snap.cell_volumes_m3)):
        cells = []
        for s, nm in enumerate(snap.species):
            v = f"{snap.amounts_mol[i, s]:.3g}" if snap.valid_mask[i, s] else "--"
            cells.append(f"{nm}={v}")
        rows.append(sep.join(cells))
    return "\n".join(rows)
