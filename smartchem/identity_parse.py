"""The one target-identity parser (ID-PARSE-01, first cut) shared by the CLI and the typed service.

SVC-REQ-01 exists so that ``compile``/``synthesize``/``recompile`` cannot silently diverge.  A brick whose
whole point is *one* front door must not ship *two* parsers: if the CLI resolved ``"acetic anhydride"`` one way
and :mod:`smartchem.service` resolved it another, "equal flags across aliases" would be a lie the moment the two
string-to-:class:`~smartchem.category.Molecule` code paths drifted.  So the resolution lives here, once, and both
:mod:`smartchem.cli` and :mod:`smartchem.service` key on it.

The ``AUTO`` path is byte-for-byte the behaviour ``smartchem.cli`` shipped before this extraction (same offline
name lookup, same ``name:``/``smiles:`` prefix handling, same error messages), so nothing observable changed for
existing callers.  ``NAME`` and ``SMILES`` are the explicit overrides the standard (section 14.2) names; the
remaining forms (``INCHI``/``FORMULA``/``TARGET_FILE``) are declared but not yet resolvable here and fail *loudly*
rather than silently mis-parsing -- finishing them is the rest of ID-PARSE-01 (TODO).
"""
from __future__ import annotations

from enum import Enum

__all__ = ["InputKind", "IdentityParseError", "resolve_target", "resolve_target_with_features"]


class InputKind(str, Enum):
    """How the caller's ``target_input`` string is to be read (standard section 14.2).

    ``AUTO`` mirrors the positional CLI ergonomics: an offline registered name, else a SMILES, with an optional
    explicit ``name:``/``smiles:`` prefix.  The explicit members force one interpretation so an ambiguous string
    (a name that also happens to parse as SMILES) is never silently guessed.
    """

    AUTO = "AUTO"
    NAME = "NAME"
    SMILES = "SMILES"
    INCHI = "INCHI"
    FORMULA = "FORMULA"
    TARGET_FILE = "TARGET_FILE"


class IdentityParseError(ValueError):
    """A target string could not be resolved to a molecule at the requested identity kind.

    A :class:`ValueError` subclass so existing ``except ValueError`` call sites (the CLI's ``exit 2`` mapping) keep
    catching it, while a service that wants the *concise domain error, not a traceback* (section 14.2) can catch
    this exact type.
    """


def resolve_target(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO):
    """Resolve ``target_input`` to a :class:`~smartchem.category.Molecule` under ``input_kind``.

    Raises :class:`IdentityParseError` on an unresolvable/ambiguous string or an as-yet-unsupported kind -- never a
    raw traceback and never a silent mis-parse.
    """
    return _resolve(target_input, input_kind)[0]


def resolve_target_with_features(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO):
    """Like :func:`resolve_target`, but also return the SMILES features that were dropped (ID-STEREO-01).

    Returns ``(molecule, features)`` where ``features`` is a :class:`~smartchem.smiles.SmilesFeatures` when the
    input resolved via SMILES (so a caller can record the section-5.3 representation-loss blockers), or ``None``
    when it resolved as a registered NAME (a name carries no such per-input stereo/isotope declaration).  Shares
    the exact resolution path with :func:`resolve_target`, so the two can never disagree on the molecule.
    """
    return _resolve(target_input, input_kind)


def _resolve(target_input: str, input_kind: "InputKind | str"):
    """Shared resolution: ``(molecule, SmilesFeatures | None)``.  ``None`` features iff resolved as a NAME."""
    from .smiles import SmilesError, parse_smiles_features
    from .structure import structure_by_name

    if not isinstance(target_input, str):
        raise IdentityParseError("target_input must be a string")
    kind = InputKind(input_kind) if not isinstance(input_kind, InputKind) else input_kind

    if kind in (InputKind.INCHI, InputKind.FORMULA, InputKind.TARGET_FILE):
        # Declared by the standard (section 14.2) but not yet resolvable here.  Fail closed: a loud, typed refusal
        # is honest; a silent wrong parse is the "fabricated instead of loud UNKNOWN" sin.  ID-PARSE-01 (TODO).
        raise IdentityParseError(
            f"input_kind {kind.value} is not yet supported by the offline identity parser (ID-PARSE-01); "
            "use NAME or SMILES"
        )

    # AUTO: honour an inline name:/smiles: prefix exactly as the CLI positional form always has.
    payload = target_input
    resolved_kind = kind
    if kind is InputKind.AUTO and ":" in target_input:
        prefix, rest = target_input.split(":", 1)
        if prefix.casefold() in {"name", "smiles"}:
            resolved_kind, payload = InputKind(prefix.upper()), rest

    if resolved_kind is not InputKind.SMILES:
        named = structure_by_name(payload)
        if named is not None:
            return named.molecule, None                # a registered name declares no stereo/isotope features
        if resolved_kind is InputKind.NAME:
            raise IdentityParseError(
                f"unknown offline chemical name {payload!r}; provide SMILES (optionally smiles:...) or use "
                "a registered name"
            )

    try:
        return parse_smiles_features(payload)          # (molecule, SmilesFeatures)
    except SmilesError as exc:
        raise IdentityParseError(
            f"could not resolve {target_input!r} as an offline name or parse it as SMILES: {exc}; "
            "use name:... or smiles:... to make the input form explicit"
        ) from exc
