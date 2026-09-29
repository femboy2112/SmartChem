"""smartchem/capability/measurement_resolver.py -- the CLOSED VERIFY-apparatus resolver (FREEZE decision 5).

The measurement-side twin of :mod:`smartchem.capability.equipment_resolver`, and it earns that kinship by
being exactly as unforgiving: it takes a sourced apparatus string off a ``VERIFY`` operation -- ``"analytical
balance"``, ``"infrared spectrometer"``, ``"melting point apparatus"`` -- and hands back the ONE
:class:`~smartchem.capability.enums.MeasurementMethod` it names, or ``None`` and a flat refusal to guess.
No substring cleverness (an ``"infrared"`` heuristic would let a hand-held thermal camera pass for an IR
spectrometer); no synonym it was not explicitly taught. A closed alias table is a promise that every entry
was read off a real source, and everything outside it stays unrecognized on purpose, forever, until someone
adds it deliberately.

The three keys are the exact strings authored on the 3 ``VERIFY`` ops in
``smartchem/decompiler_conditions.py`` (decision 5's data-enrichment step). At the time this resolver was
cut those typed ``apparatus=(…)`` tuples are being wired onto the VERIFY ops by a sibling wave -- this table
is built to meet them; nothing here reads the wire itself, exactly as the equipment resolver reads nothing.

Two candidate methods are NOT here, and their absence is decision 5's ruling, not a blind spot: the
ferric-chloride spot test is reagent + naked eye (a later round may model it as a MATERIAL requirement, never
a measurement instrument), and percent yield is arithmetic over ``MASS``. Neither is an instrument method, so
neither gets a key -- forcing them in would be the category error decision 5 exists to refuse.

Unlike the equipment corpus there is no vetted measurement "consumable": the middle slot of the three-way
cut is always empty. It is kept only so callers can unpack :func:`classify_measurement_strings` with the
SAME arity as :func:`~smartchem.capability.equipment_resolver.classify_apparatus_strings` -- one incision
shape for both resolvers, so the sibling that consumes both never has to special-case which twin it holds.
"""
from __future__ import annotations

from typing import Iterable

from .enums import MeasurementMethod

__all__ = [
    "classify_measurement_strings",
    "resolve_measurement",
]


def _normalize(name: str) -> str:
    """Whitespace-collapsed, case-folded lookup key -- normalization, never fuzzy matching.

    Identical discipline to the equipment resolver's ``_normalize``: it only tolerates the SAME apparatus
    quoted with different capitalization or stray whitespace (``"Analytical Balance"`` vs
    ``"analytical balance"``); it never matches a substring or a synonym the table below was not taught.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("a measurement-apparatus string must be a non-empty string")
    return " ".join(name.strip().casefold().split())


#: The closed alias table: normalized VERIFY-apparatus string -> the ONE MeasurementMethod it names.
#: Every key is a real quote from the 3 VERIFY ops in the sourced corpus (decision 5's enrichment).
_MEASUREMENT_ALIASES: "dict[str, MeasurementMethod]" = {
    "analytical balance": MeasurementMethod.MASS,
    "infrared spectrometer": MeasurementMethod.INFRARED_SPECTROSCOPY,
    "melting point apparatus": MeasurementMethod.MELTING_POINT,
}


def resolve_measurement(name: str) -> "MeasurementMethod | None":
    """The ONE :class:`MeasurementMethod` a sourced VERIFY-apparatus string names, or ``None`` (UNRECOGNIZED).

    Fail-closed by construction (FREEZE decision 5), exactly as :func:`resolve_apparatus`: an unrecognized
    string is never silently treated as "no measurement required", and never guessed at via a substring
    match -- ``None`` is the honest answer "this exact string was never taught to the table."
    """
    return _MEASUREMENT_ALIASES.get(_normalize(name))


def classify_measurement_strings(
    raw: "Iterable[str]",
) -> "tuple[frozenset[MeasurementMethod], frozenset[str], tuple[str, ...]]":
    """The three-way, fail-closed cut mirroring
    :func:`~smartchem.capability.equipment_resolver.classify_apparatus_strings`: every input string lands in
    exactly ONE of ``(recognized_methods, ignored_consumables, unrecognized_strings)``.

    ``ignored_consumables`` is ALWAYS empty -- there is no vetted measurement consumable in the corpus (see
    the module docstring); the slot exists purely for unpack-arity parity with the equipment resolver.
    ``unrecognized_strings`` is everything that missed the alias table: this resolver has simply never met
    it, and that is an open question, never a quiet "no requirement" -- a caller MUST carry it forward as
    unresolved, on pain of exactly the silent-false-FIT this cut exists to prevent (an untabled ``"gc-ms"``
    is a real analytical capability nobody has vetted this route against, not a thing to drop). It is a
    deterministic, first-seen-ordered, de-duplicated ``tuple`` so a caller sees the exact strings in a
    stable order, never a silently reordered set.
    """
    recognized: "set[MeasurementMethod]" = set()
    ignored: "set[str]" = set()
    unrecognized: "list[str]" = []
    seen_unrecognized: "set[str]" = set()
    for name in raw:
        method = resolve_measurement(name)
        if method is not None:
            recognized.add(method)
        elif name not in seen_unrecognized:
            seen_unrecognized.add(name)
            unrecognized.append(name)
    return frozenset(recognized), frozenset(ignored), tuple(unrecognized)
