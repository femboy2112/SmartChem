"""smartchem/capability/equipment_resolver.py -- the CLOSED apparatus-string resolver (FREEZE decision 4).

**Ooh, a lookup table! Look at me, I resolve strings!** My one job, and I will do it with the manic
cheer of a thing that was born ninety seconds ago specifically to do it: take a sourced apparatus string
like ``"Buchner funnel"`` and hand back the ONE :class:`~smartchem.capability.enums.EquipmentCapability`
it means -- or, if I've genuinely never seen the string before, hand back ``None`` and refuse to guess.
No fuzzy matching. No ``"still" in name`` substring cleverness that would let "boiling stones" get
mistaken for a fractional-distillation rig (that's exactly the M5 mutation this table exists to kill). A
closed alias table is a promise: every entry is something a human read off a real source, and everything
NOT in the table stays unrecognized, on purpose, forever, until someone adds it deliberately.

The table is built from the ACTUAL apparatus strings in ``smartchem/decompiler_conditions.py`` across the
whole 5-route corpus (``ProcedureEvidence.apparatus`` per-operation tuples AND the whole-step
``ProcessRequirements.equipment`` cross-check tuples -- decision 2's "+ ProcessRequirements.equipment
cross-check"). A handful of corpus strings are deliberately left OUT of the alias table -- not oversights,
but consumables/generic tools that are not distinctive CAPABILITY items in the closed
:class:`~smartchem.capability.enums.EquipmentCapability` vocabulary: ``"boiling stones"`` (anti-bumping
granules, a consumable, not apparatus), ``"glass rod"`` (a generic stirring tool every bench has),
``"test tube clamp"``/``"test tube rack"``/``"pipet"``/``"watch glass"``/``"dropper"`` (generic small
labware, not one of the 12 corpus-forced members). Those are named on a SEPARATE, equally closed
:data:`CONSUMABLE_WHITELIST` -- being on it is a deliberate, documented "this is real evidence and
genuinely not a capability", never a resolver blind spot.

That distinction matters past this module's door: a string on NEITHER the alias table nor the whitelist
is not a vetted consumable -- it is an apparatus this table has simply never met, and a caller
(:mod:`~smartchem.capability.requirements`, then :mod:`~smartchem.capability.assess`) MUST treat it as an
open question, never as "no requirement". :func:`classify_apparatus_strings` is the three-way cut that
keeps those two silences from ever being confused with each other again.
"""
from __future__ import annotations

from typing import Iterable

from .enums import EquipmentCapability

__all__ = [
    "CONSUMABLE_WHITELIST",
    "classify_apparatus_strings",
    "resolve_apparatus",
    "resolve_apparatus_strings",
]


def _normalize(name: str) -> str:
    """Whitespace-collapsed, case-folded lookup key -- normalization, never fuzzy matching.

    This only tolerates the SAME apparatus being quoted with different capitalization or stray
    whitespace across the corpus (e.g. ``"Buchner funnel"`` vs ``"buchner funnel"``); it never matches a
    substring or a synonym it wasn't explicitly taught (that discipline lives entirely in the table below).
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("an apparatus string must be a non-empty string")
    return " ".join(name.strip().casefold().split())


#: The closed alias table: normalized apparatus string -> the ONE EquipmentCapability it names.
#: Every key is a real quote from the sourced corpus (see the module docstring for the omitted consumables).
_APPARATUS_ALIASES: "dict[str, EquipmentCapability]" = {
    # -- reaction vessels (isopentyl acetate / aspirin / paracetamol / methyl salicylate) -----------------
    "100-ml round-bottom flask": EquipmentCapability.REACTION_VESSEL,
    "round-bottom flask": EquipmentCapability.REACTION_VESSEL,
    "125-ml erlenmeyer flask": EquipmentCapability.REACTION_VESSEL,
    "erlenmeyer flask": EquipmentCapability.REACTION_VESSEL,
    "150 ml beaker": EquipmentCapability.REACTION_VESSEL,
    "small (~10 ml) test tubes": EquipmentCapability.REACTION_VESSEL,
    # -- reflux (isopentyl acetate) -------------------------------------------------------------------
    "reflux condenser": EquipmentCapability.REFLUX_CONDENSER,
    # -- controlled heating (isopentyl acetate / methyl salicylate) -----------------------------------
    "heating mantle": EquipmentCapability.CONTROLLED_HEATING,
    "hot plate": EquipmentCapability.CONTROLLED_HEATING,
    # -- water bath: a steam bath and a beaker used AS a warm-water bath are the same open-bath heating
    # device in bench practice (aspirin / paracetamol / methyl salicylate) --------------------------------
    "steam bath": EquipmentCapability.WATER_BATH,
    "250 ml beaker (warm water bath)": EquipmentCapability.WATER_BATH,
    # -- cooling (aspirin / paracetamol) --------------------------------------------------------------
    "ice bath": EquipmentCapability.ICE_BATH,
    # -- liquid-liquid separation (isopentyl acetate) -------------------------------------------------
    "separatory funnel": EquipmentCapability.SEPARATORY_FUNNEL,
    # a boiling-RANGE fraction is collected here (134-143 C, isopentyl acetate) -- the FROZEN forcing
    # matrix names FRACTIONAL_DISTILLATION explicitly for this exact source string; this alias is a
    # contract match, not a chemistry judgment call (the frozen spec, not this module, made that ruling).
    "distillation apparatus": EquipmentCapability.FRACTIONAL_DISTILLATION,
    # -- filtration (paracetamol: gravity-filter hot through fluted paper to remove decolorizing charcoal;
    # aspirin/paracetamol: Buchner funnel + water aspirator = vacuum filtration) ----------------------
    "fluted filter paper": EquipmentCapability.GRAVITY_FILTRATION,
    "buchner funnel": EquipmentCapability.VACUUM_FILTRATION,
    "water aspirator": EquipmentCapability.VACUUM_FILTRATION,
    # -- measuring (isopentyl acetate) ----------------------------------------------------------------
    "thermometer": EquipmentCapability.THERMOMETER,
}


#: The closed consumable whitelist: normalized apparatus/tool strings that are real sourced evidence but
#: deliberately NOT one of the 12 corpus-forced EquipmentCapability members (see the module docstring for
#: the per-item rationale). Being on this list is a vetted "ignore, on purpose" -- the opposite of falling
#: through the alias table by accident. Anything NOT on either this set or the alias table is unrecognized.
CONSUMABLE_WHITELIST: "frozenset[str]" = frozenset(
    _normalize(name)
    for name in (
        "boiling stones",
        "glass rod",
        "test tube clamp",
        "test tube rack",
        "pipet",
        "watch glass",
        "dropper",
    )
)


def resolve_apparatus(name: str) -> "EquipmentCapability | None":
    """The ONE :class:`EquipmentCapability` a sourced apparatus string names, or ``None`` (UNRECOGNIZED).

    Fail-closed by construction (FREEZE decision 4): an unrecognized string is never silently treated as
    "no equipment needed" for a capability this module tracks, and it is never guessed at via a substring
    match -- ``None`` is the honest, load-bearing answer "this exact string was never taught to the table."
    """
    return _APPARATUS_ALIASES.get(_normalize(name))


def resolve_apparatus_strings(
    names: "Iterable[str]",
) -> "tuple[frozenset[EquipmentCapability], frozenset[str]]":
    """Resolve a batch of apparatus strings; returns ``(recognized_capabilities, unresolved_strings)``.

    The two return sets are disjoint by construction (every input string lands in exactly one of them),
    so a caller can see BOTH what capability the corpus's apparatus resolved to AND which exact strings
    it could not -- never silently dropping the latter into "no requirement" without a trace.
    """
    recognized: "set[EquipmentCapability]" = set()
    unresolved: "set[str]" = set()
    for name in names:
        capability = resolve_apparatus(name)
        if capability is None:
            unresolved.add(name)
        else:
            recognized.add(capability)
    return frozenset(recognized), frozenset(unresolved)


def classify_apparatus_strings(
    names: "Iterable[str]",
) -> "tuple[frozenset[EquipmentCapability], frozenset[str], frozenset[str]]":
    """The three-way, fail-closed cut ``resolve_apparatus_strings`` was never asked to make: every input
    string lands in exactly ONE of ``(recognized_capabilities, ignored_consumables, unrecognized_strings)``.

    ``ignored_consumables`` are real sourced strings that hit the vetted :data:`CONSUMABLE_WHITELIST` --
    genuinely not equipment, safe to drop without a trace. ``unrecognized_strings`` are everything else
    that missed BOTH the alias table and the whitelist: this table has simply never met them, and that is
    an open question, not a quiet "no requirement" -- a caller MUST carry them forward as unresolved, on
    pain of exactly the silent-false-FIT this cut exists to prevent (an untabled "rotary evaporator" is
    not a consumable; it is a bench capability nobody has vetted this route against).
    """
    recognized: "set[EquipmentCapability]" = set()
    ignored: "set[str]" = set()
    unrecognized: "set[str]" = set()
    for name in names:
        capability = resolve_apparatus(name)
        if capability is not None:
            recognized.add(capability)
        elif _normalize(name) in CONSUMABLE_WHITELIST:
            ignored.add(name)
        else:
            unrecognized.add(name)
    return frozenset(recognized), frozenset(ignored), frozenset(unrecognized)
