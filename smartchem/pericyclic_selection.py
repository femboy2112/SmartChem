"""Woodward-Hoffmann selection rules for the recognized pericyclic reaction types -- the stereochemical/topological
annotation layer, derived as a THEOREM-CONSTANT, needing no geometry oracle.

Once a reaction's TYPE and pi-electron count are perceived (the reaction-type oracle already fixes "thermal [4+2], 6
electrons" or "electrocyclization, 4 electrons"), the Woodward-Hoffmann rule DETERMINES its allowed stereochemical
mode -- it is not a measurement, it is a consequence of the aromatic-transition-state theorem (a thermal ground-state
pericyclic reaction proceeds through the AROMATIC TS: a Hueckel array, all-suprafacial / disrotatory, is aromatic
with 4n+2 electrons; a Moebius array, one-antarafacial / conrotatory, is aromatic with 4n; a photochemical reaction
runs through the excited state and inverts the allowed TS).  So this layer attaches a PROVABLE constant to the
already-recognized reaction TYPE, carrying the electron-count witness -- no 3D coordinates, no conformer, no
transition-state energetics.

WHAT THIS BUILDS (the sound piece) and WHAT IT DEFERS.
* BUILT -- the WH selection constant for every recognized pericyclic class: suprafacial/antarafacial for the
  cycloaddition ([4+2]) and sigmatropic ([3,3]) families, con/disrotatory for the electrocyclizations, each with the
  thermal AND the photochemical (inverted) mode and the 4n / 4n+2 witness.  It attaches to the reaction TYPE
  (:func:`selection_for_family` / :func:`selection_for_class`), NOT to the coordinate-free, atom-identity-free
  :class:`~smartchem.reaction_center.ReactionCenter` (which cannot host a facial descriptor).
* DEFERRED (verified, with the discharge path named).
  - ENDO/EXO SELECTION (the Alder endo rule -- which diastereomer a [4+2] prefers): a genuine VERIFIED-DEFER.  It is
    a kinetic transition-state preference (secondary-orbital overlap), Problem B, and needs a stereo-aware
    transition-state/geometry oracle that does NOT exist in-tree (``smartchem.geometry`` makes ONE non-stereospecific
    VSEPR conformer for energy input and explicitly disclaims stereochemistry).  No pure-graph / coordinate-free model
    can express a TS facial preference, so predicting endo vs exo is out of scope here by structure theorem.
  - ENDO/EXO DESCRIPTION (naming the diastereomer of a stereo-SPECIFIED adduct): graph+parity-sound and would reuse
    the existing CIP parity engine (:func:`smartchem.smiles.cip_labels_by_atom`), but the pericyclic pipeline carries
    NO product stereo today (the DA edge is built from stereo-free Molecules; ``identity.stereo_loss`` BLOCKS any
    ``@``/``@@`` before it reaches a step), so there is no stereo INPUT to describe.  Enabling it is a stereo-threading
    job, NOT a new geometry oracle -- a scoped defer with a clear, geometry-free discharge path.

Structural type-validity ONLY (Problem A): the WH mode says which stereochemistry is thermally ALLOWED by orbital
symmetry, NEVER that a given substrate is feasible, fast, or that a specific product stereochemistry was formed.
"""
from __future__ import annotations

from dataclasses import dataclass

from .diels_alder import (
    ALKYNE_DA_CLASS, AZA_DA, AZA_DIENE_DA, DA_CLASS, OXA_DA, OXA_DIENE_DA, THIA_DA, THIA_DIENE_DA,
)
from .lateral_rewrite import AZA_CLAISEN, CLAISEN, COPE, ELECTRO_4PI, ELECTRO_6PI, THIA_CLAISEN

#: The three pericyclic archetypes this layer annotates.
CYCLOADDITION = "cycloaddition"
SIGMATROPIC = "sigmatropic"
ELECTROCYCLIZATION = "electrocyclization"

#: archetype + pi-electron count (textbook THEOREM-CONSTANTS) per recognized family ``class_label``.  Keyed off the
#: real family objects' labels (drift-proof: a renamed family moves its key with it) plus the two all-carbon DA class
#: strings.  A [4+2] cycloaddition is 6 electrons (4 diene pi + 2 dienophile pi); a [3,3] sigmatropic is 6; an
#: electrocyclization has the pi-electron count of its open polyene (butadiene 4, hexatriene 6).
_PERICYCLIC: dict[str, tuple[str, int]] = {
    DA_CLASS: (CYCLOADDITION, 6),
    ALKYNE_DA_CLASS: (CYCLOADDITION, 6),
    AZA_DA.class_label: (CYCLOADDITION, 6),
    OXA_DA.class_label: (CYCLOADDITION, 6),
    THIA_DA.class_label: (CYCLOADDITION, 6),
    AZA_DIENE_DA.class_label: (CYCLOADDITION, 6),
    OXA_DIENE_DA.class_label: (CYCLOADDITION, 6),
    THIA_DIENE_DA.class_label: (CYCLOADDITION, 6),
    COPE.class_label: (SIGMATROPIC, 6),
    CLAISEN.class_label: (SIGMATROPIC, 6),
    AZA_CLAISEN.class_label: (SIGMATROPIC, 6),
    THIA_CLAISEN.class_label: (SIGMATROPIC, 6),
    ELECTRO_4PI.class_label: (ELECTROCYCLIZATION, 4),
    ELECTRO_6PI.class_label: (ELECTROCYCLIZATION, 6),
}


@dataclass(frozen=True)
class PericyclicSelection:
    """The Woodward-Hoffmann stereochemical mode allowed for a pericyclic reaction, as a theorem-constant.

    ``aromatic_transition_state`` is the THERMAL classification: ``True`` for a 4n+2 (Hueckel-aromatic) thermal TS,
    ``False`` for a 4n (Moebius-aromatic) thermal TS.  ``thermal_mode`` / ``photochemical_mode`` are the allowed
    modes (the photochemical one inverts the thermal one).  ``rule`` is the human-readable theorem statement."""

    archetype: str
    electron_count: int
    aromatic_transition_state: bool
    thermal_mode: str
    photochemical_mode: str
    rule: str


def _mode(archetype: str, huckel_allowed: bool) -> str:
    """The stereochemical mode allowed when the Hueckel (all-suprafacial / disrotatory) TS is the allowed one
    (``huckel_allowed``) vs the Moebius (one-antarafacial / conrotatory) TS -- the descriptor AXIS depends on the
    archetype (facial for cycloaddition/sigmatropic, rotational for electrocyclization)."""
    if archetype == ELECTROCYCLIZATION:
        return "disrotatory" if huckel_allowed else "conrotatory"
    if archetype in (CYCLOADDITION, SIGMATROPIC):
        return "suprafacial-suprafacial (all-suprafacial)" if huckel_allowed else "suprafacial-antarafacial"
    raise ValueError(f"unknown pericyclic archetype {archetype!r}")


def woodward_hoffmann(archetype: str, electron_count: int) -> PericyclicSelection:
    """The Woodward-Hoffmann theorem-constant for a pericyclic reaction of ``archetype`` with ``electron_count``
    pi electrons.  A thermal (ground-state) reaction proceeds through the AROMATIC transition state: Hueckel
    (all-suprafacial / disrotatory) for 4n+2 electrons, Moebius (one-antarafacial / conrotatory) for 4n; a
    photochemical reaction runs through the excited state and inverts the allowed mode."""
    if electron_count < 2 or electron_count % 2:
        raise ValueError("a pericyclic electron count is a positive even number")
    aromatic_ts = (electron_count - 2) % 4 == 0     # 4n+2 -> Hueckel-aromatic thermal TS
    thermal_mode = _mode(archetype, aromatic_ts)
    photochemical_mode = _mode(archetype, not aromatic_ts)
    band = "4n+2 (Hueckel-aromatic thermal TS)" if aromatic_ts else "4n (Moebius-aromatic thermal TS)"
    rule = (f"thermal {electron_count}-electron {archetype}: {band} -> {thermal_mode}; "
            f"photochemical inverts -> {photochemical_mode}")
    return PericyclicSelection(archetype, electron_count, aromatic_ts, thermal_mode, photochemical_mode, rule)


def selection_for_class(class_label: str | None) -> PericyclicSelection | None:
    """The WH selection annotation for a recognized pericyclic reaction CLASS (by its family ``class_label``), or
    ``None`` if the class is not a recognized pericyclic type (e.g. a dehydrative condensation carries no WH rule)."""
    entry = _PERICYCLIC.get(class_label) if class_label is not None else None
    return None if entry is None else woodward_hoffmann(*entry)


def selection_for_family(family) -> PericyclicSelection | None:
    """The WH selection for a family descriptor (any DA or lateral family carrying a ``.class_label``), or ``None``.
    A pericyclic edge carries its family, so ``selection_for_family(edge.family)`` annotates a recognized step."""
    return selection_for_class(getattr(family, "class_label", None))
