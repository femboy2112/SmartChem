"""Item 6 (EM scope): open-resistor semantics -- ideal DC resistor networks as functor images of the SAME
generic open SMC (:mod:`smartchem.open_core`) that the chemistry layer rides.

The point (``electromagnetic-scope``, and the evidence Move 5's generality claim was waiting on): the chemistry
apex (``ConservationDecoration``) is an ADDITIVE monoid; a resistor network's apex is its exact boundary linear
relation, whose composition is NON-additive (series adds resistance, but the relation composes by a Schur
elimination, and the parallel law is ``1/(1/R1 + 1/R2)``).  :class:`ResistorDecoration` is the FIRST
demonstration that :class:`open_core.Decoration`'s interchange-invariance obligation is satisfiable by a
non-additive monoid -- so ``open_core`` genuinely hosts a second physical domain, not chemistry wearing a coat.

The exact-``Fraction`` boundary-relation algebra ALREADY exists and is production-tested on
:class:`smartchem.resistive_dc_schema.BoundaryLinearRelation` (series = ``.then``, juxtaposition = ``.tensor``),
cross-checked by an INDEPENDENTLY-written verifier (:mod:`smartchem.resistive_dc_verifier`).  This module is the
thin bridge that lifts that algebra onto ``open_core`` as a ``Decoration`` and a resistor generator onto an
``open_core.OpenDiagram``.  ``open_core.then``/``tensor`` then compose resistor networks and its ``canonicalize``
quotient applies -- with the composed boundary relation calibrated to the production ``blackbox_resistive_dc``
value (which the verifier certifies), never self-asserted.

Scope (bounded, sound): ideal DC resistors only (no RLC/AC).  Through the SANCTIONED operations
(``then``/``tensor``) the reachable networks are exactly SERIES chains and disjoint JUXTAPOSITIONS -- that is the
functor image built here.  Electrical PARALLEL (two resistors between the same node pair) is NOT constructible via
``then``/``tensor``: it needs a merge (a plug / compact structure) ``open_core`` does not offer in the sanctioned
set, so its CONSTRUCTION is deferred -- only its boundary RELATION (``R1||R2``) is validated, against the
independent oracle.  A general non-series-parallel bridge is deferred the same way.  Reconstructing an arbitrary
network's full ``open_core`` node/edge topology (a ``from_circuit`` over the old-core junction spec, which today
exposes only ``node_for``, plus a parallel-merge primitive) is the named next brick.

``plug_all`` is an UNENFORCED CONVENTION here, NOT a runtime guard: it is a method on the shared frozen
``OpenDiagram`` this module cannot override, and it passes the apex through UNCHANGED -- correct only for a
gluing-invariant (additive) decoration, WRONG for a boundary relation (gluing eliminates internal variables), so a
stale, wrong-width relation would ride through with no error.  The functor never calls it; a caller who composes
resistor diagrams outside ``then``/``tensor`` can fail closed with :func:`apex_matches_boundary` (a guard test
proves both the hazard and that the validator catches it).  The proper enforcement -- a gluing-invariance flag on
the ``Decoration`` contract plus a core ``plug_all`` check -- is future work in the shared ``open_core``.

The closed PR-#3 branch was NOT salvaged: its ``resistive_dc_schema`` predecessor does not exist there, so
mainline's schema/verifier split is strictly more mature.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .open_core import (
    Decoration,
    DiagramCompositionError,
    Hyperedge,
    Interface,
    OpenDiagram,
    Terminal,
)
from .resistive_dc_schema import BoundaryLinearRelation, Rational

__all__ = [
    "ResistorDecoration",
    "resistor_relation",
    "for_resistor",
    "resistor_edge",
    "apex_matches_boundary",
]

_ELECTRICAL = "electrical"
_RESISTOR_KIND = "resistor"


@dataclass(frozen=True)
class ResistorDecoration(Decoration):
    """The exact boundary linear relation of an open resistor network, riding the ``open_core`` apex.

    A NON-additive monoid: :meth:`then_combine` is series composition (``BoundaryLinearRelation.then``, a Schur
    elimination of the shared interface) and :meth:`tensor_combine` is disjoint juxtaposition
    (``BoundaryLinearRelation.tensor``).  Both are the production-tested exact-``Fraction`` operations; this class
    only adapts them to :class:`open_core.Decoration`.  Frozen, so ``==`` is the exact canonical-RREF relation
    equality.
    """

    relation: BoundaryLinearRelation

    def __post_init__(self) -> None:
        if type(self.relation) is not BoundaryLinearRelation:
            raise TypeError("ResistorDecoration wraps a BoundaryLinearRelation")

    def then_combine(self, other: Decoration) -> Decoration:
        if type(other) is not ResistorDecoration:
            raise DiagramCompositionError("cannot series-compose a resistor apex with a non-resistor decoration")
        return ResistorDecoration(self.relation.then(other.relation))

    def tensor_combine(self, other: Decoration) -> Decoration:
        if type(other) is not ResistorDecoration:
            raise DiagramCompositionError("cannot juxtapose a resistor apex with a non-resistor decoration")
        return ResistorDecoration(self.relation.tensor(other.relation))

    def parallel_combine(self, other: Decoration) -> Decoration:
        """Parallel composition of two resistor apices over a SHARED boundary (``BoundaryLinearRelation.parallel``).

        The exact ``R1||R2`` law: shared boundary potentials, summed port currents, branch currents eliminated.
        This is NOT one of the ``open_core.Decoration`` structural operations (``then``/``tensor``) -- it is a
        resistor-domain MERGE, the correct-apex counterpart to the ``plug_all`` node-merge (which leaves a stale
        apex).  It closes the item-6 deferral: parallel is now CONSTRUCTIBLE with an exact apex, not only
        reconstructible via the solver.
        """
        if type(other) is not ResistorDecoration:
            raise DiagramCompositionError("cannot parallel-compose a resistor apex with a non-resistor decoration")
        return ResistorDecoration(self.relation.parallel(other.relation))


def _rational(ohms) -> Rational:
    if type(ohms) is Rational:
        return ohms
    if type(ohms) is int and type(ohms) is not bool:
        return Rational(ohms)
    if type(ohms) is Fraction:
        return Rational(ohms.numerator, ohms.denominator)
    raise TypeError("resistance must be an exact int / Fraction / Rational (never a float)")


def resistor_relation(ohms) -> BoundaryLinearRelation:
    """The 1->1 boundary relation of one ideal resistor: ``V_dom - V_cod = R*I_dom`` and ``I_dom + I_cod = 0``.

    Calibrated to the production ``blackbox_resistive_dc`` value of a single resistor (identical canonical RREF);
    the ``R = 0`` case is exactly ``BoundaryLinearRelation.identity(1)`` (a wire).  ``R`` must be exact.
    """
    r = _rational(ohms)
    return BoundaryLinearRelation.from_equations(
        1, 1, [[Fraction(1), Fraction(-1), -r.fraction, Fraction(0)], [0, 0, 1, 1]]
    )


def for_resistor(ohms) -> ResistorDecoration:
    """A resistor's apex decoration (a :class:`ResistorDecoration`).

    Resistance must be NON-NEGATIVE: a wire (``R=0``) is valid, but a negative "resistor" is an active element
    outside the ideal-DC-resistor scope and is refused.  This closes the asymmetry an adversarial review found --
    the ingest path (``from_circuit``) enforced positivity via ``PositiveResistance`` while the compositional
    path (``resistor_edge``/``for_resistor``/``CircuitStage.resistor``) accepted a negative R, constructing,
    costing, and even certifying an active element as an ideal resistor.
    """
    r = _rational(ohms)
    if r.fraction < 0:
        raise ValueError("resistance must be non-negative (a negative resistor is an active element, out of scope)")
    return ResistorDecoration(resistor_relation(r))


def resistor_edge(ohms, *, name: str = "r") -> OpenDiagram:
    """One ideal resistor as a 1->1 ``open_core.OpenDiagram`` -- the functor image of a circuit generator.

    Two electrical nodes (node 0 = the ``a`` boundary input, node 1 = the ``b`` boundary output), one
    ``resistor`` hyperedge incident on both, and the :class:`ResistorDecoration` apex.  ``open_core.then`` /
    ``tensor`` then compose these into series / juxtaposed networks, driving the apex through
    :meth:`ResistorDecoration.then_combine` / :meth:`~ResistorDecoration.tensor_combine` -- so the boundary
    relation of the composite is computed by the exact algebra the production solver uses.  The payload carries
    the exact-``Fraction`` resistance so the generator identity is legible in the presentation.
    """
    r = _rational(ohms)
    dom = Interface((_ELECTRICAL,))
    cod = Interface((_ELECTRICAL,))
    node_ports = (_ELECTRICAL, _ELECTRICAL)                       # node 0 = a terminal, node 1 = b terminal
    edge = Hyperedge(
        _RESISTOR_KIND, f"{name}={r.numerator}/{r.denominator}", (Terminal("a", 0), Terminal("b", 1))
    )
    return OpenDiagram(dom, cod, (0,), (1,), node_ports, (edge,), for_resistor(r))


def apex_matches_boundary(diagram: OpenDiagram) -> bool:
    """True iff ``diagram`` carries a :class:`ResistorDecoration` whose relation WIDTH matches its boundary.

    The opt-in fail-closed guard against the ``plug_all`` hazard: ``plug_all`` narrows a diagram's dom/cod but
    rides the apex through UNCHANGED, so a plugged resistor diagram keeps its pre-plug relation port counts -- a
    stale, wrong-width apex.  A diagram composed only via ``then``/``tensor`` (which DO combine the apex) always
    satisfies this; a ``plug_all``-ed one does not.  A caller who cannot guarantee it stayed on ``then``/``tensor``
    should fail closed on ``not apex_matches_boundary(diagram)`` rather than trust the apex.

    **This is a WIDTH/shape consistency check, NOT an apex-CORRECTNESS check** (adversarial review, both bearings):
    it confirms the relation's port widths match the boundary, never that the relation is the physically-correct
    one for the diagram's topology.  A hand-built diagram whose apex contradicts its own topology (same widths,
    wrong relation) passes.  Apex correctness rests on how the apex was CONSTRUCTED -- ``then``/``tensor``/
    ``parallel_combine`` over verified operations, or ``from_circuit``'s solver relation -- and is cross-checked to
    the independent oracle in the probe, never by this width guard.
    """
    apex = diagram.decoration
    if type(apex) is not ResistorDecoration:
        return False
    return (
        apex.relation.dom_ports == len(diagram.dom.ports)
        and apex.relation.cod_ports == len(diagram.cod.ports)
    )
