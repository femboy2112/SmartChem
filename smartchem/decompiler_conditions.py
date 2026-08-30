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

from .conditions import ConditionEnvelope
from .contracts import EvidenceStatus
from .decompiler import Formula

__all__ = ["reaction_conditions", "SEED_CONDITIONS"]


def _composition_key(formula: Formula) -> tuple[tuple[str, int], ...]:
    return formula.counts


def _reaction_signature(edge) -> tuple:
    """Scale-independent identity of a reaction: (reactant, {reagents}, {products}) by composition."""
    reagents = tuple(sorted(_composition_key(r) for r, _ in getattr(edge, "reagents", ())))
    products = tuple(sorted(_composition_key(p) for p, _ in edge.products))
    return (_composition_key(edge.reactant), reagents, products)


def _sig(reactant: str, reagents: tuple[str, ...], products: tuple[str, ...]) -> tuple:
    return (
        Formula.parse(reactant).counts,
        tuple(sorted(Formula.parse(r).counts for r in reagents)),
        tuple(sorted(Formula.parse(p).counts for p in products)),
    )


#: Sourced conditions, keyed by scale-independent reaction signature. Tiny by design; every entry
#: is provenance-bearing and `EXPERIMENTAL` (a decorator never claims a certified-lane status).
SEED_CONDITIONS: dict[tuple, ConditionEnvelope] = {
    # Paracetamol hydrolysis -> 4-aminophenol + acetic acid. Only what the literature states is
    # claimed: an acidic aqueous medium. No temperature/catalyst value is fabricated.
    _sig("C8H9NO2", ("H2O",), ("C6H7NO", "C2H4O2")): ConditionEnvelope(
        medium="aqueous, acidic",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="lit: acidic amide hydrolysis of paracetamol (RSC Anal. Methods c3ay40747k)",
    ),
    # Anhydrous backbone C8H9NO2 -> C6H7NO + C2H2O. Its REVERSE (assembly) is the ketene
    # acetylation of 4-aminophenol -- ketene acetylates the amine to give paracetamol. Ketene is
    # an acutely toxic reactive gas generated and consumed in situ; N- vs O-selectivity is a
    # structure-level concern this formula-level edge does not resolve.
    _sig("C8H9NO2", (), ("C6H7NO", "C2H2O")): ConditionEnvelope(
        medium="ketene generated and consumed in situ (not storable)",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance=(
            "reverse (assembly) direction: ketene acetylation of 4-aminophenol; ketene is acutely "
            "toxic and generated in situ (NJ RTK / CAMEO; see hazards). Formula-level edge does not "
            "distinguish N- vs O-acetylation"
        ),
    ),
    # Mediated C8H9NO2 + C2H4O2 -> C6H7NO + C4H6O3. Its REVERSE (assembly) is the standard lab
    # synthesis: 4-aminophenol + acetic anhydride -> paracetamol + acetic acid.
    _sig("C8H9NO2", ("C2H4O2",), ("C6H7NO", "C4H6O3")): ConditionEnvelope(
        medium="aqueous or neat; addition/temperature controlled",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance=(
            "reverse (assembly) direction: standard acetic-anhydride acetylation of 4-aminophenol "
            "(ACS J. Chem. Educ. teaching synthesis); acetic anhydride reacts violently with water, "
            "so addition and temperature are controlled in practice"
        ),
    ),
}


def reaction_conditions(edge) -> ConditionEnvelope:
    """The sourced conditions for an edge, or the loud `unknown()` default if none are tabulated."""
    return SEED_CONDITIONS.get(_reaction_signature(edge), ConditionEnvelope.unknown())
