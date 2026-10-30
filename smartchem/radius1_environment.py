"""RADIUS1-ENVIRONMENT-01 (#106, infra W0.3) -- a bounded radius-1 atom-environment predicate.

Why this module exists.  A :class:`~smartchem.reaction_center.ReactionCenter` is context-free: it carries
only element-pair + bond-order + component-count, so distinct reactions have byte-identical centres and
centre-equality cannot separate them (#106) -- SN2 at an sp3 carbon vs SNAr at an aromatic carbon is the
canonical collision (both FORM a ``C-O``/``C-N`` and BREAK a ``C-X``; the only difference is the local
environment of the reacting carbon).  This module supplies the missing LOCAL discriminator: for ONE atom,
the elements and bond-orders of its immediate (radius-1) neighbours -- its ``star`` -- plus the handful of
derived predicates a recogniser reads off that star.

What it is, and is NOT.  It is a VIEW computed on demand from an existing :class:`~smartchem.category.Molecule`'s
``atoms``/``bonds`` -- it adds NO field to ``Molecule``, mutates nothing, and imports no 2.0 representation
(the plan's explicit boundary: do not quietly drag an unfinished molecular model into 1.x).  It vouches
NOTHING: it reports local structure, and each consumer family (SN2 #112 first; EAS, cross-coupling, enolate
later) supplies its OWN conservation-lock + adversary pass on top.

BOUNDED BY CONSTRUCTION -- the R49--R55 do-not-retry boundary.  Every fact here is a pure function of an
atom and its radius-1 star alone; it carries NO unbounded property (feasibility, type-validity).  That is
exactly why a radius-1 predicate is *sound-able* where the R49--R55 attempts to carry an unbounded property
through a bounded feature collided: this module makes no capability claim, it only measures the local graph.

SP3 / aromaticity, via the Kekule proxy.  A :class:`~smartchem.category.Molecule` spells aromatic rings in
Kekule form -- an aromatic carbon carries exactly one order-2 ring bond -- so ``element == "C" and every
incident bond is order 1`` (:attr:`is_saturated_carbon`) excludes aromatic, vinylic AND acyl/carbonyl
carbons in one clause (each of those carries an order>=2 incident bond).  This is a radius-1 fact; a fuller
ring-aromaticity classifier (needed by EAS) is deliberately NOT built here until a consumer earns it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Molecule

__all__ = ["AtomEnvironment"]


@dataclass(frozen=True)
class AtomEnvironment:
    """The radius-1 environment of one atom of a :class:`~smartchem.category.Molecule`.

    * ``element`` -- the atom's own element symbol;
    * ``star`` -- the sorted multiset of ``(neighbour_element, bond_order)`` of its incident bonds (the whole
      radius-1 datum; coordinate-free, so it is a stable value, not tied to atom indices).

    Build with :meth:`at`.  The derived predicates (:attr:`is_saturated_carbon`, :attr:`carbon_neighbour_count`,
    :attr:`max_incident_order`) are the ones the SN2 recogniser reads; other families derive their own from
    ``star``.
    """

    element: str
    star: "tuple[tuple[str, int], ...]"

    @classmethod
    def at(cls, molecule: Molecule, index: int) -> "AtomEnvironment":
        """The radius-1 environment of atom ``index`` in ``molecule`` (raises ``IndexError`` out of range)."""
        if type(molecule) is not Molecule:
            raise TypeError("molecule must be a smartchem.category.Molecule")
        atoms = molecule.atoms
        if type(index) is not int or not (0 <= index < len(atoms)):
            raise IndexError(f"atom index {index!r} out of range for {len(atoms)} atoms")
        star = []
        for b in molecule.bonds:
            if b.i == index:
                star.append((atoms[b.j], b.order))
            elif b.j == index:
                star.append((atoms[b.i], b.order))
        return cls(atoms[index], tuple(sorted(star)))

    @property
    def max_incident_order(self) -> int:
        """The highest incident bond order (``0`` for an unbonded atom)."""
        return max((order for _elem, order in self.star), default=0)

    @property
    def is_saturated_carbon(self) -> bool:
        """``True`` iff this is a carbon whose every incident bond is order 1 (the sp3 proxy).

        Excludes aromatic (Kekule order-2), vinylic (``C=C``) and acyl/carbonyl (``C=O``) carbons alike --
        each carries an order>=2 incident bond.  An sp3 carbon is the SN2 electrophilic-carbon requirement
        and the SNAr discriminator (#106)."""
        return self.element == "C" and self.max_incident_order <= 1

    @property
    def hydrogen_count(self) -> int:
        """How many radius-1 neighbours are hydrogen.

        The sound SN2 steric gate: a backside substitution needs the reacting carbon to bear at least one H.
        A carbon with ZERO hydrogens is FULLY substituted and reacts (if at all) by SN1 -- whether the crowding
        is CARBON (a tertiary / quaternary all-carbon centre) OR HETEROATOMS (a ketal / orthoester oxocarbenium:
        ``C(C)(C)(OR)`` or ``C(OR)4``).  ``hydrogen_count >= 1`` is therefore STRICTLY STRONGER than a
        carbon-only substitution count, which reads a heteroatom-crowded SN1 centre as a benign 'secondary'
        carbon and false-vouches it (the evil-morty KILL on the #112 first cut: acetone dimethyl ketal,
        tetramethyl orthocarbonate).  It false-excludes nothing: every genuine SN2 centre (methyl / primary /
        secondary, including benzylic, allylic and alpha-alkoxy) carries at least one H."""
        return sum(1 for elem, _order in self.star if elem == "H")
