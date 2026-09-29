"""REACTION-CENTER-01 (R58): a coordinate-free distillation of a derived step's rewrite span.

Why this module exists (the R58 root fix).  The generator derives each reaction as a bond-level
rewrite -- a :class:`~smartchem.structure_descent.CappedScission` records exactly which bonds are
BROKEN (``cut``) and FORMED (``caps``) to turn one molecule into its fragments, valence-certified
atom-by-atom.  Until now :meth:`~smartchem.experiment.step.ExperimentStep.from_transform` DISCARDED
that span and rebuilt the step from its reactant/product multisets alone, so the reaction-TYPE
recognizers (:mod:`smartchem.experiment.reaction_type_oracle`) had to INFER what happened from a
WHOLE-MOLECULE functional-group census.  A whole-molecule count is non-local: it is fooled both ways
(the R56/R57 locality debt, [[a-whole-set-count-classifier-is-fooled-by-non-locality]]) --

* it FALSE-DEMOTES a real reaction whose reactant merely CONTAINS an unrelated instance of the
  product group elsewhere (``methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water`` is a genuine
  etherification the R57 "no reactant ether" clause wrongly sank because a spectator methoxy is
  present -- a PRODUCTION, k=1 miss); and
* it FALSE-VOUCHES a bundled multi-cut step whose independent sub-reactions forge the same NET
  group signature (``THF + 2 water -> ethane + a triol`` reads as "ether formed, alcohol consumed"
  yet forms a C-C bond and an O-O peroxide -- reachable once the single-cut config is relaxed).

Reading the actual rewrite morphism closes both.  Carried onto the step, this descriptor lets a
recognizer confirm the reaction CENTER is a single, connected, elementary dehydrative condensation
rather than trusting a count -- turning the generator's ``max_reactant_cuts = 1`` single-cut
invariant from a BORROWED assumption into a CHECKED structural fact (config-robust).

Coordinate-free BY CONSTRUCTION.  The span's ``cut``/``caps`` are :class:`~smartchem.category.Bond`
objects indexed into the scission's JOINED reactant+reagents atom space, and those indices do NOT
survive the canonicalisation that products undergo -- so they cannot be serialised and reconstructed.
This descriptor stores only the ELEMENT-PAIR and bond-order of each formed/broken bond, plus the
number of connected components of the reaction centre.  Element symbols and small ints round-trip
through the replay payload with no coordinate reconstruction, so a live step and its replayed twin
read IDENTICALLY (the R58 live==replay obligation).

What a recognizer reads it for.  A single elementary dehydrative condensation -- esterification,
amidation, thioesterification, or dialkyl etherification -- has an invariant reaction-centre
signature (verified against the generator's own spans): a new ``C-X`` bond and a water ``O-H`` are
FORMED, the acid/alcohol ``C-O`` and the nucleophile's ``X-H`` are BROKEN, all in ONE connected
component, for a nucleophile ``X`` in ``{O, N, S}`` (the ether/ester case is ``X = O``, where the
two heteroatoms coincide).  A bundled step breaks or forms extra bonds, or splits into more than one
component, so it fails :meth:`is_elementary_condensation`.  The recognizer still identifies the CLASS
by functional-group census (ester vs dialkyl ether vs amide, which share a centre signature); the
centre supplies the ELEMENTARITY the census cannot see locally.
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "REACTION_CENTER_SCHEMA",
    "ReactionCenter",
    "ReactionCenterError",
]

REACTION_CENTER_SCHEMA = "smartchem/reaction-center-v1"

#: A single formed/broken bond as ``(element_lo, element_hi, order)`` -- the element pair is sorted so
#: ``C-O`` and ``O-C`` are the same key, and the order is the bond order.  This is the whole alphabet
#: the descriptor speaks; it deliberately carries NO atom index (see the module docstring).
BondKind = "tuple[str, str, int]"


class ReactionCenterError(ValueError):
    """A reaction-centre descriptor is not a well-formed, coordinate-free record."""


def _normalise_bond(bond: "tuple[str, str, int]") -> "tuple[str, str, int]":
    if type(bond) is not tuple or len(bond) != 3:
        raise ReactionCenterError("a bond kind must be a (element, element, order) triple")
    a, b, order = bond
    if type(a) is not str or type(b) is not str or not a or not b:
        raise ReactionCenterError("bond elements must be non-empty strings")
    if type(order) is not int or order <= 0:
        raise ReactionCenterError("bond order must be a positive integer")
    lo, hi = sorted((a, b))
    return (lo, hi, order)


def _normalise_bonds(bonds) -> "tuple[tuple[str, str, int], ...]":
    return tuple(sorted(_normalise_bond(b) for b in bonds))


@dataclass(frozen=True)
class ReactionCenter:
    """The coordinate-free reaction centre of one derived step, in the SYNTHESIS direction.

    * ``formed`` -- the multiset (a sorted tuple) of bonds FORMED assembling the target, each a
      sorted ``(element, element, order)`` kind;
    * ``broken`` -- the multiset of bonds BROKEN;
    * ``n_components`` -- the number of connected components of the graph whose edges are the formed
      and broken bonds (``1`` iff every changed bond touches one common cluster: a single centre).

    It is derived data (see :meth:`~smartchem.structure_descent.CappedScission.reaction_center`) and
    is carried on :class:`~smartchem.experiment.step.ExperimentStep` as a NON-identity annotation --
    it does not enter the step's content digest, so two steps that differ only in how the generator
    discovered them remain the same step.
    """

    schema_version: str
    formed: "tuple[tuple[str, str, int], ...]"
    broken: "tuple[tuple[str, str, int], ...]"
    n_components: int

    def __post_init__(self) -> None:
        if self.schema_version != REACTION_CENTER_SCHEMA:
            raise ReactionCenterError(
                f"schema_version must be exactly {REACTION_CENTER_SCHEMA!r}"
            )
        for name in ("formed", "broken"):
            seq = getattr(self, name)
            if type(seq) is not tuple:
                raise ReactionCenterError(f"{name} must be a tuple of (element, element, order) kinds")
            if _normalise_bonds(seq) != seq:
                raise ReactionCenterError(
                    f"{name} must be normalised: each bond's elements sorted, the tuple sorted"
                )
        if type(self.n_components) is not int or self.n_components < 1:
            raise ReactionCenterError("n_components must be a positive integer")

    @classmethod
    def of(cls, formed_bonds, broken_bonds, n_components: int) -> "ReactionCenter":
        """Build a normalised descriptor from raw formed/broken bond kinds and a component count."""
        return cls(
            REACTION_CENTER_SCHEMA,
            _normalise_bonds(formed_bonds),
            _normalise_bonds(broken_bonds),
            n_components,
        )

    def is_elementary_condensation(
        self, nucleophiles: "tuple[str, ...]" = ("O", "N", "S")
    ) -> bool:
        """Is this centre a SINGLE, connected, elementary dehydrative condensation onto ``nucleophiles``?

        True iff the centre is one connected component (``n_components == 1``) whose changed bonds are
        EXACTLY those of one acyl/etherification condensation for some nucleophile ``X`` in
        ``nucleophiles``: a ``C-X`` bond and a water ``O-H`` FORMED, the acid/alcohol ``C-O`` and the
        nucleophile's ``X-H`` BROKEN.  For ``X = O`` (esterification / etherification) the two collapse
        to ``{C-O, O-H}`` formed and ``{C-O, O-H}`` broken.

        Callers pass ``("O",)`` for the dialkyl-etherification centre and the default ``("O","N","S")``
        for the acyl family (esterification/amidation/thioesterification).  The class itself
        (dialkyl ether vs ester vs amide) is disambiguated by the functional-group census, which they
        share a centre signature; this method supplies only the elementarity the census cannot see
        locally.  A bundled multi-cut step forms/breaks extra bonds or splits into >1 component and so
        is rejected -- the config-robust replacement for the borrowed single-cut assumption.
        """
        if self.n_components != 1:
            return False
        for x in nucleophiles:
            formed = _normalise_bonds((("C", x, 1), ("H", "O", 1)))
            broken = _normalise_bonds((("C", "O", 1), ("H", x, 1)))
            if self.formed == formed and self.broken == broken:
                return True
        return False

    def to_payload(self) -> dict:
        """A JSON-compatible payload for the replay envelope (lists of ``[element, element, order]``)."""
        return {
            "schema_version": self.schema_version,
            "formed": [list(b) for b in self.formed],
            "broken": [list(b) for b in self.broken],
            "n_components": self.n_components,
        }

    @classmethod
    def from_payload(cls, payload) -> "ReactionCenter":
        """Rebuild a descriptor from :meth:`to_payload`; ``__post_init__`` re-validates normalisation."""
        if type(payload) is not dict:
            raise ReactionCenterError("a reaction-centre payload must be a dict")
        expected = {"schema_version", "formed", "broken", "n_components"}
        if set(payload) != expected:
            raise ReactionCenterError("reaction-centre payload must contain exactly the versioned fields")
        # X-high D26.7 (Wave-C'' RC-v): the payload's OWN version is checked -- ``cls.of`` stamps the current id, so an
        # unchecked payload of any other (or a bogus) version was silently relabelled current on decode.
        if payload["schema_version"] != REACTION_CENTER_SCHEMA:
            raise ReactionCenterError(
                f"reaction-centre payload schema_version must be exactly {REACTION_CENTER_SCHEMA!r}, got "
                f"{payload['schema_version']!r} (D26.7)")
        return cls.of(
            (tuple(b) for b in payload["formed"]),
            (tuple(b) for b in payload["broken"]),
            payload["n_components"],
        )
