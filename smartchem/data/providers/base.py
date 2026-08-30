"""The provider interface and the partial property record they return.

A provider fetches whatever OPEN data it has for one compound and returns a :class:`PropertyRecord` -- a
PARTIAL record (any field may be ``None``) carrying, per field, the source it came from.  The autoload layer
merges records from several providers field-wise and turns the result into a
:class:`~smartchem.data.stability.StabilityRef`.  Nothing here fabricates: a field a provider cannot source
stays ``None``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ...conditions import Interval

__all__ = ["PropertyRecord", "PropertyProvider"]


@dataclass(frozen=True)
class PropertyRecord:
    """One provider's partial, sourced view of a compound's physical properties (temperatures in kelvin).

    Every value field may be ``None`` (this provider has no sourced value for it).  ``sources`` maps a field
    name to its provenance string, ``licence`` and ``source_name`` describe redistributability, so a merged
    record can always say where each number came from.
    """

    melting: Interval | None = None
    boiling: Interval | None = None
    decomposition: Interval | None = None
    dhvap_kj_per_mol: float | None = None
    isolable: bool | None = None
    sources: dict[str, str] = field(default_factory=dict)
    licence: str = ""
    source_name: str = ""

    @property
    def is_empty(self) -> bool:
        """True iff this provider sourced no usable value at all (a clean miss)."""
        return (
            self.melting is None
            and self.boiling is None
            and self.decomposition is None
            and self.dhvap_kj_per_mol is None
            and self.isolable is None
        )


class PropertyProvider(ABC):
    """A source of open chemical-property data.  ``fetch`` returns a :class:`PropertyRecord` or ``None``.

    Implementations must be honest: a value that cannot be sourced/parsed cleanly is left ``None``, never
    guessed; and ``fetch`` returns ``None`` (a clean miss) rather than raising when a compound is simply not
    covered.  Network errors are swallowed into ``None`` too -- an unreachable provider is a miss, not a
    crash, so autoload degrades to the cache and the seed.
    """

    #: A short human name for provenance (e.g. "PubChem", "Wikidata").
    name: str = "provider"
    #: The data licence, for the redistributability note.
    licence: str = "unspecified"

    @abstractmethod
    def fetch(self, *, identifier: str, formula: str | None = None) -> PropertyRecord | None:
        """Fetch a partial property record for a compound by ``identifier``, or ``None`` on a miss.

        ``identifier`` is a name (``"aspirin"``) OR a structure string (a SMILES like ``"CC(=O)O"``) -- so an
        arbitrary molecule with no registered common name is still queryable by its structure.  Providers try
        whatever lookups they support and return ``None`` for anything they cannot resolve.
        """
        raise NotImplementedError
