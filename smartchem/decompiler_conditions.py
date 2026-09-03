"""M-4b C1 — sourced condition annotation for decomposition edges (a seed table).

C0 gave the condition *algebra* (the Env comonad); this attaches *sourced* conditions to the
edges that a reference actually documents, and returns a loud `unknown()` for everything else —
which is the overwhelming majority. A conditions layer that guessed would be worse than the
formal engine that admits it knows only conservation, so this table is deliberately tiny and
every entry carries a provenance; the point is the *mechanism* (real reaction -> its real
conditions, everything else UNKNOWN), not coverage.

Matching is by the reaction's identity — the reactant composition, the multiset of reagent
compositions, and the multiset of product compositions — independent of how the equation is
scaled, so `paracetamol + H2O -> 4-aminophenol + acetic acid` is recognised however it is written.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import gcd
from types import SimpleNamespace

from .conditions import ConditionEnvelope
from .contracts import Digestible, EvidenceStatus
from .decompiler import Formula
from .provenance import SourceCitation, SourceReview

__all__ = [
    "ReactionDirection",
    "ConditionRecord",
    "assembly_conditions",
    "reaction_conditions",
    "SEED_CONDITIONS",
]


class ReactionDirection(str, Enum):
    """The direction in which a sourced condition record is licensed to fire.

    A balanced edge can always be reversed algebraically.  Its experimental conditions cannot:
    hydrolysis conditions are not amidation conditions, and a synthesis citation does not document the
    decomposition merely because the equation balances both ways.
    """

    DECOMPOSITION = "DECOMPOSITION"
    ASSEMBLY = "ASSEMBLY"


@dataclass(frozen=True)
class ConditionRecord(Digestible):
    """One provenance-bearing envelope plus the reaction direction(s) it actually documents.

    Assembly records additionally name the exact target and precursor structures.  Formula balance is a
    useful index, not chemical identity: without this structural selector a same-formula isomer could borrow
    another compound's bench conditions.
    """

    envelope: ConditionEnvelope
    directions: tuple[ReactionDirection, ...]
    assembly_target_name: str | None = None
    assembly_precursor_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.envelope) is not ConditionEnvelope or not self.envelope.is_declared:
            raise ValueError("a condition record must carry a declared ConditionEnvelope")
        if (
            type(self.directions) is not tuple
            or not self.directions
            or any(not isinstance(d, ReactionDirection) for d in self.directions)
        ):
            raise TypeError("directions must be a non-empty tuple of ReactionDirection values")
        object.__setattr__(self, "directions", tuple(sorted(set(self.directions), key=lambda d: d.value)))
        if ReactionDirection.ASSEMBLY in self.directions:
            if not isinstance(self.assembly_target_name, str) or not self.assembly_target_name:
                raise ValueError("an ASSEMBLY condition record needs an exact assembly_target_name")
            if (
                type(self.assembly_precursor_names) is not tuple
                or not self.assembly_precursor_names
                or any(not isinstance(n, str) or not n for n in self.assembly_precursor_names)
            ):
                raise ValueError("an ASSEMBLY condition record needs exact assembly_precursor_names")
            object.__setattr__(self, "assembly_precursor_names", tuple(sorted(self.assembly_precursor_names)))


def _composition_key(formula: Formula) -> tuple:
    return (formula.counts, formula.charge)


def _reaction_signature(edge) -> tuple:
    """Primitive signed stoichiometry by composition (formula index only, never structural identity)."""
    merged: dict[tuple[str, tuple], int] = {}

    def add(side: str, formula: Formula, coefficient: int) -> None:
        key = (side, _composition_key(formula))
        merged[key] = merged.get(key, 0) + coefficient

    add("L", edge.reactant, getattr(edge, "reactant_multiplicity", 1))
    for formula, coefficient in getattr(edge, "reagents", ()):
        add("L", formula, coefficient)
    for formula, coefficient in edge.products:
        add("R", formula, coefficient)
    divisor = 0
    for coefficient in merged.values():
        divisor = gcd(divisor, coefficient)
    divisor = divisor or 1
    return tuple(sorted((side, composition, coefficient // divisor) for (side, composition), coefficient in merged.items()))


def _sig(reactant: str, reagents: tuple[str, ...], products: tuple[str, ...]) -> tuple:
    edge = SimpleNamespace(
        reactant=Formula.parse(reactant),
        reactant_multiplicity=1,
        reagents=tuple((Formula.parse(r), 1) for r in reagents),
        products=tuple((Formula.parse(p), 1) for p in products),
    )
    return _reaction_signature(edge)


#: Sourced conditions, keyed by scale-independent reaction signature. Tiny by design; every entry
#: is provenance-bearing and `EXPERIMENTAL` (a decorator never claims a certified-lane status).
SEED_CONDITIONS: dict[tuple, ConditionRecord] = {
    # Paracetamol hydrolysis -> 4-aminophenol + acetic acid. Only what the literature states is
    # claimed: an acidic aqueous medium. No temperature/catalyst value is fabricated.
    _sig("C8H9NO2", ("H2O",), ("C6H7NO", "C2H4O2")): ConditionRecord(
        ConditionEnvelope(
            medium="aqueous, acidic",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance="acidic amide hydrolysis of paracetamol; DOI 10.1039/C3AY40747K",
            source=SourceCitation(
                "https://doi.org/10.1039/C3AY40747K", SourceReview.ACCEPTED
            ),
        ),
        (ReactionDirection.DECOMPOSITION,),
    ),
    # Anhydrous backbone C8H9NO2 -> C6H7NO + C2H2O. Its REVERSE (assembly) is the ketene
    # acetylation of 4-aminophenol -- ketene acetylates the amine to give paracetamol. Ketene is
    # an acutely toxic reactive gas generated and consumed in situ; N- vs O-selectivity is a
    # structure-level concern this formula-level edge does not resolve.
    _sig("C8H9NO2", (), ("C6H7NO", "C2H2O")): ConditionRecord(
        ConditionEnvelope(
            medium="ketene generated and consumed in situ (not storable)",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: ketene acetylation of 4-aminophenol; ketene is acutely toxic and "
                "generated in situ (NJ RTK / CAMEO; see hazards). Formula-level edge does not distinguish "
                "N- vs O-acetylation"
            ),
        ),
        (ReactionDirection.ASSEMBLY,),
        "paracetamol",
        ("4-aminophenol", "ketene"),
    ),
    # Mediated C8H9NO2 + C2H4O2 -> C6H7NO + C4H6O3. Its REVERSE (assembly) is the standard lab
    # synthesis: 4-aminophenol + acetic anhydride -> paracetamol + acetic acid.
    _sig("C8H9NO2", ("C2H4O2",), ("C6H7NO", "C4H6O3")): ConditionRecord(
        ConditionEnvelope(
            medium="aqueous or neat; addition/temperature controlled",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance=(
                "assembly direction: standard acetic-anhydride acetylation of 4-aminophenol "
                "(ACS J. Chem. Educ., DOI 10.1021/acs.jchemed.0c01512); acetic anhydride reacts with water, "
                "so addition and temperature are controlled in practice"
            ),
            source=SourceCitation(
                "https://doi.org/10.1021/acs.jchemed.0c01512", SourceReview.ACCEPTED
            ),
        ),
        (ReactionDirection.ASSEMBLY,),
        "paracetamol",
        ("4-aminophenol", "acetic anhydride"),
    ),
}


def reaction_conditions(
    edge, *, direction: ReactionDirection = ReactionDirection.DECOMPOSITION, losses: tuple = (),
) -> ConditionEnvelope:
    """The conditions sourced for ``edge`` in exactly ``direction``, else loud ``unknown()``.

    The default preserves the decompiler-facing API: an edge is read in its written decomposition direction.
    Retrosynthesis callers MUST request :attr:`ReactionDirection.ASSEMBLY`; algebraic reversibility is not
    experimental provenance.

    ``losses`` (EVD-KEY-01): if a section-5.3 BLOCKER forbids a ``"conditions"`` claim on this identity, no sourced
    envelope survives (section 5.3) -- ``unknown()`` is returned before the lookup.
    """
    from .identity import is_blocked
    if not isinstance(direction, ReactionDirection):
        raise TypeError("direction must be a ReactionDirection")
    if is_blocked(tuple(losses), "conditions"):
        return ConditionEnvelope.unknown()
    record = SEED_CONDITIONS.get(_reaction_signature(edge))
    if record is None or direction not in record.directions:
        return ConditionEnvelope.unknown()
    if direction is ReactionDirection.ASSEMBLY:
        # Formula-only callers cannot prove the structural selector.  Retrosynthesis must use
        # assembly_conditions(capped), which has the bond graphs needed to do so.
        return ConditionEnvelope.unknown()
    return record.envelope


def assembly_conditions(capped, *, losses: tuple = ()) -> ConditionEnvelope:
    """Conditions for reversing one structural capped scission, only after exact identity matches.

    Any unresolved structure or selector mismatch returns ``unknown()``.  This deliberately refuses a
    formula-only fallback: paracetamol and 4-aminophenyl acetate are both C8H9NO2 but are not interchangeable.

    ``losses`` (EVD-KEY-01): a section-5.3 BLOCKER for ``"conditions"`` refuses a sourced envelope (section 5.3),
    even when the structure resolves and the selector matches -- the dropped feature (stereo/isotope/charge) is one
    the sourced bench conditions may depend on.

    Expected-absence contract (ERR-EVIDENCE-01): the ONLY reasons this returns ``unknown()`` are the explicit,
    anticipated ones below -- a section-5.3 ``"conditions"`` blocker, no seed record for the reaction signature, a
    record that carries no ASSEMBLY direction, an unresolved reactant/precursor structure, or a selector-name
    mismatch.  It does NOT catch exceptions.  An unexpected fault in signature computation or structure resolution
    is an INTERNAL DEFECT, not the scientific statement "conditions unknown"; it propagates to the
    ``ERROR_INTERNAL`` / exit-70 boundary rather than being laundered into an epistemic UNKNOWN.
    """
    from .identity import is_blocked
    from .structure import resolve_structure

    if is_blocked(tuple(losses), "conditions"):
        return ConditionEnvelope.unknown()
    record = SEED_CONDITIONS.get(_reaction_signature(capped.forget()))
    if record is None or ReactionDirection.ASSEMBLY not in record.directions:
        return ConditionEnvelope.unknown()
    target = resolve_structure(capped.reactant)
    precursors = tuple(resolve_structure(m) for m in capped.products)
    if target is None or any(p is None for p in precursors):
        return ConditionEnvelope.unknown()
    names = tuple(sorted(p.name for p in precursors if p is not None))
    if target.name != record.assembly_target_name or names != record.assembly_precursor_names:
        return ConditionEnvelope.unknown()
    return record.envelope
