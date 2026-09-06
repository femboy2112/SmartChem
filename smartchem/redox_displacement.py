"""REDOX-DISPLACE-01: the coupled half-reaction combiner (a two-species redox displacement family).

The DOW-bromine litmus's enumeration wall, found by recon: ``Cl2 + 2 Br- -> Br2 + 2 Cl-`` is NOT
representable by any existing mechanism.  :func:`~smartchem.structure_descent.redox_edges` /
:class:`~smartchem.structure_descent.RedoxHalfReaction` are SINGLE-SPECIES and charge-only (the
oxidized species carries the SAME atoms as the reduced one -- a redox step there makes and breaks no
bonds and involves no second species); and :func:`~smartchem.structure_descent.capped_scissions`
ties reactant-cuts 1:1 to reagent instances (and refuses charged input outright), so it cannot reach
a 1:2 stoichiometry.  The 1:2 is NOT a stoichiometry hack -- it falls out of ELECTRON-COUNT BALANCING:
Cl2 gains 2 electrons, each Br- loses 1, so two bromide per chlorine.

This module supplies the missing primitive.  A :class:`HalfReactionCouple` is a molecular redox couple
``oxidized + n e- <-> reduced`` (e.g. ``Cl2 + 2 e- <-> 2 Cl-``), a level ABOVE the single-species
half-reaction because it relates two DIFFERENT molecular forms of an element across a bond change.
:func:`combine_half_reactions` pairs a reduction couple (the oxidant, reduced) with an oxidation couple
(the reductant, oxidised -> the target made), balances electrons by their LCM, and returns a
conservation-checked :class:`RedoxDisplacementEdge` -- a transform exposing the uniform interface
(``reactant`` / ``reagents`` / ``products`` / ``forget()`` / ``equation()`` / ``digest``) the
step-builder and the registry already consume.

Genericity (Lane B): the new family rides the UNCHANGED bounded search through a
:class:`RedoxDisplacementProvider` registered into a wider algebra -- no fork of ``search_routes`` /
``search_dags`` / ``ExperimentStep.from_transform``.  Like the heterolytic and redox families it is
DECOMPILE-ONLY and OPT-IN (absent from ``DEFAULT_TRANSFORM_REGISTRY``): its net-ionic products carry
bare ions, so it widens the decompile algebra rather than being forced through the neutral route search
(whose ``_refuse_charged_target`` guard is for neutral commodity routing).  W3 unchanged: a couple /
displacement certifies that a charge-and-mass-consistent electron transfer EXISTS, never that it
occurs, at what potential, or that a given oxidation is spontaneous (physical selectivity the engine
refuses to predict -- e.g. it will happily enumerate the thermodynamically UNfavourable direction too).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import lcm

from .category import Config, ConservationError, Molecule, Reaction
from .contracts import Digestible
from .structure_descent import ScissionError
from .transform_provider import TransformProvider

__all__ = [
    "DISPLACEMENT_SCHEMA",
    "HalfReactionCouple",
    "CoupledRedoxFormulaEdge",
    "RedoxDisplacementEdge",
    "combine_half_reactions",
    "halogen_couple",
    "RedoxDisplacementProvider",
]

DISPLACEMENT_SCHEMA = "smartchem.redox_displacement/displacement-v1"

#: The physical oxidation-state ceiling shared with the redox half-reaction certificate (Os/Ru/Xe +8),
#: so a couple can never claim to move more electrons than the reduced atoms could physically shed.
_MAX_OXIDATION_STATE_PER_ATOM = 8


def _multiset(molecules: tuple[Molecule, ...]) -> Counter:
    """A canonical-identity multiset of molecules (so ``2 Cl-`` compares by structure, not position)."""
    return Counter(m.canonical() for m in molecules)


def _atoms(molecules: tuple[Molecule, ...]) -> Counter:
    total: Counter = Counter()
    for m in molecules:
        total.update(m.formula)  # Molecule.formula is a dict of element -> count
    return total


def _charge(molecules: tuple[Molecule, ...]) -> int:
    return sum(m.charge for m in molecules)


def _monoelement(m: Molecule) -> str | None:
    """The sole element of a monoelemental species (all atoms one symbol), else None."""
    symbols = set(m.formula)  # Molecule.formula is a dict element -> count
    return next(iter(symbols)) if len(symbols) == 1 else None


def _electron_ledger(lhs: tuple[Molecule, ...], rhs: tuple[Molecule, ...]) -> dict[str, int]:
    """Per-element charge change ``rhs - lhs`` attributed to monoelemental species.

    A positive delta means that element LOST electrons (charge rose, oxidised); a negative delta means it
    GAINED electrons (reduced).  Raises if a CHARGED multi-element species is present: this family verifies
    electron transfer for monoelemental redox species (monoatomic ions and homonuclear diatomics), which is
    its whole scope; a neutral multi-element species contributes no charge and is ignored.
    """
    delta: dict[str, int] = {}
    for side, sign in ((lhs, -1), (rhs, +1)):
        for m in side:
            element = _monoelement(m)
            if element is None:
                if m.charge != 0:
                    raise ScissionError(
                        "electron-transfer verification supports monoelemental redox species only; the "
                        f"charged multi-element species {dict(m.formula)} is outside this family's scope"
                    )
                continue
            delta[element] = delta.get(element, 0) + sign * m.charge
    return delta


@dataclass(frozen=True)
class HalfReactionCouple(Digestible):
    """A molecular redox couple ``oxidized + n e- <-> reduced`` (n >= 1), written in the reduction
    direction (an oxidant gaining electrons).

    Unlike :class:`~smartchem.structure_descent.RedoxHalfReaction` (a single species whose atoms and
    bonds are IDENTICAL across the electron move), a couple relates two DIFFERENT molecular forms of an
    element across a bond change -- e.g. ``Cl2 + 2 e- <-> 2 Cl-`` -- so it can express the elemental
    <-> ionic transition a displacement turns on.  The couple is MASS-CONSERVING between its two forms
    (this round scopes to couples whose two sides differ only by charge/electrons, e.g. the halogens;
    acidic multi-species couples that need H+/H2O bookkeeping are refused, not silently mis-balanced).
    """

    schema_version: str
    element: str
    oxidized_form: tuple[Molecule, ...]
    reduced_form: tuple[Molecule, ...]
    electrons: int

    def __post_init__(self) -> None:
        if self.schema_version != DISPLACEMENT_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {DISPLACEMENT_SCHEMA!r}")
        if not isinstance(self.element, str) or not self.element.strip():
            raise ScissionError("a couple must name its redox-active element")
        object.__setattr__(self, "element", self.element.strip())
        for name in ("oxidized_form", "reduced_form"):
            seq = getattr(self, name)
            if type(seq) is not tuple or not seq or any(type(m) is not Molecule for m in seq):
                raise ScissionError(f"{name} must be a non-empty tuple of Molecule values")
        if type(self.electrons) is not int or self.electrons < 1:
            raise ScissionError("a couple transfers at least one electron")
        # mass: the two forms carry exactly the same atoms (an electron is massless) -- this scopes the
        # couple to the simple, mass-symmetric case (the halogens); an acidic couple would fail here.
        if _atoms(self.oxidized_form) != _atoms(self.reduced_form):
            raise ScissionError(
                f"couple mass not conserved between forms: oxidized atoms {dict(_atoms(self.oxidized_form))} != "
                f"reduced {dict(_atoms(self.reduced_form))} (this family scopes to mass-symmetric couples)"
            )
        if self.element not in _atoms(self.oxidized_form):
            raise ScissionError(f"the redox-active element {self.element!r} does not appear in the couple")
        # charge: oxidized + n e- -> reduced, so reduced.charge == oxidized.charge - n.
        if _charge(self.reduced_form) != _charge(self.oxidized_form) - self.electrons:
            raise ScissionError(
                f"couple charge not conserved: reduced {_charge(self.reduced_form)} != oxidized "
                f"{_charge(self.oxidized_form)} - {self.electrons} e-"
            )
        # the reduced form must actually be MORE reduced (lower total charge) than the oxidized form.
        if _charge(self.reduced_form) >= _charge(self.oxidized_form):
            raise ScissionError("the reduced form must carry less charge than the oxidized form")
        ceiling = _MAX_OXIDATION_STATE_PER_ATOM * sum(_atoms(self.oxidized_form).values())
        if self.electrons > ceiling:
            raise ScissionError(
                f"a couple transfers at most {ceiling} electrons for its atom count; got {self.electrons}"
            )

    def equation(self) -> str:
        e = f"{self.electrons} e-" if self.electrons > 1 else "e-"
        lhs = " + ".join(repr(m) for m in self.oxidized_form)
        rhs = " + ".join(repr(m) for m in self.reduced_form)
        return f"{lhs} + {e} -> {rhs}"

    def __repr__(self) -> str:
        return f"HalfReactionCouple({self.equation()})"


@dataclass(frozen=True)
class CoupledRedoxFormulaEdge(Digestible):
    """The forgetful composition image of a displacement: a balanced multi-species formula reaction with
    NET-zero electron transfer (a full redox reaction, not a half-reaction -- the electrons cancel).

    Reactants and products are canonical sorted tuples of ``(formula_items, charge, coefficient)`` so the
    edge has a stable identity independent of authoring order.  Mass and charge are conserved (checked)."""

    reactants: tuple
    products: tuple
    electrons_transferred: int

    def __post_init__(self) -> None:
        if type(self.electrons_transferred) is not int or self.electrons_transferred < 1:
            raise ScissionError("a coupled redox edge transfers at least one electron between the couples")

    def equation(self) -> str:
        def side(terms: tuple) -> str:
            parts = []
            for items, charge, coeff in terms:
                atoms = "".join(f"{el}{n}" for el, n in items) or "e"
                sign = "" if charge == 0 else (f"{charge:+d}")
                parts.append((f"{coeff} " if coeff > 1 else "") + f"[{atoms}{sign}]")
            return " + ".join(parts)
        return f"{side(self.reactants)} -> {side(self.products)}"


def _formula_terms(molecules: tuple[Molecule, ...]) -> tuple:
    """Canonicalise a molecule multiset to sorted ``(formula_items, charge, coefficient)`` terms."""
    grouped: dict[tuple, int] = {}
    for m in molecules:
        key = (tuple(sorted(m.formula.items())), m.charge)
        grouped[key] = grouped.get(key, 0) + 1
    return tuple(sorted((items, charge, coeff) for (items, charge), coeff in grouped.items()))


@dataclass(frozen=True)
class RedoxDisplacementEdge(Digestible):
    """A two-species redox displacement, written as a DECOMPOSITION of ``reactant`` (the elemental
    target) so it satisfies the uniform transform interface and reverses (via
    :meth:`ExperimentStep.from_transform`) into the synthesis that MAKES the target.

    For the DOW litmus the synthesis is ``Cl2 + 2 Br- -> Br2 + 2 Cl-`` (target ``Br2``); the stored
    decomposition view is its reverse, ``Br2 + 2 Cl- -> Cl2 + 2 Br-``.  Conservation (mass AND charge)
    is independently re-checked at construction by building a real :class:`Reaction`, exactly as
    :class:`ExperimentStep` does -- so a mis-balanced displacement is refused, not shipped.  The
    certificate ALSO ties ``electrons_transferred`` and the two element labels to the reaction's actual
    charge redistribution (:func:`_electron_ledger`), so a directly-built edge cannot carry a fabricated
    electron count, fictitious redox elements, or an identity/no-op reaction masquerading as a
    displacement (an evil-morty fold: conservation alone does not prove redox-ness).
    """

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reduction_element: str
    oxidation_element: str
    electrons_transferred: int

    def __post_init__(self) -> None:
        if self.schema_version != DISPLACEMENT_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {DISPLACEMENT_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a Molecule")
        for name in ("products", "reagents"):
            seq = getattr(self, name)
            if type(seq) is not tuple or any(type(m) is not Molecule for m in seq):
                raise ScissionError(f"{name} must be a tuple of Molecule values")
        if not self.products:
            raise ScissionError("a displacement decomposes into at least one product (the precursors)")
        if type(self.electrons_transferred) is not int or self.electrons_transferred < 1:
            raise ScissionError("a displacement transfers at least one electron between the two couples")
        if self.reduction_element == self.oxidation_element:
            raise ScissionError("a species cannot displace itself (the two couples share a redox element)")
        # the independent conservation certificate: the decomposition view reactant + reagents -> products
        # must balance mass AND charge (a displacement conserves either way it is read).
        lhs = (self.reactant,) + self.reagents
        try:
            Reaction(Config.of(*lhs), Config.of(*self.products), name="redox-displacement")
        except ConservationError as clash:
            raise ScissionError(f"redox displacement does not conserve mass/charge: {clash}") from clash
        # electron / redox verification (evil-morty fold): conservation alone does NOT prove a redox
        # displacement -- an identity Na -> Na conserves trivially, and electrons_transferred plus the
        # element labels rode UNCHECKED into the digest (a hand-built edge could carry 999 electrons or
        # fictitious elements).  Tie them to the ACTUAL charge redistribution the reaction performs.
        delta = _electron_ledger(lhs, self.products)
        oxidised = sum(d for d in delta.values() if d > 0)   # elements that lost electrons (charge rose)
        reduced = -sum(d for d in delta.values() if d < 0)   # elements that gained electrons (charge fell)
        if oxidised == 0 or reduced == 0:
            raise ScissionError(
                "not a redox displacement: no element changes charge (an identity / no-op reaction)"
            )
        if oxidised != reduced:
            raise ScissionError(f"electron ledger unbalanced: {oxidised} lost != {reduced} gained")
        if self.electrons_transferred != oxidised:
            raise ScissionError(
                f"electrons_transferred {self.electrons_transferred} != the {oxidised} electrons the "
                "reaction actually moves (a fabricated electron count is refused)"
            )
        if delta.get(self.reduction_element, 0) == 0 or delta.get(self.oxidation_element, 0) == 0:
            raise ScissionError(
                f"named redox elements {self.reduction_element!r}/{self.oxidation_element!r} are not both "
                "redox-active in this reaction (a fabricated element label is refused)"
            )
        if (delta[self.reduction_element] > 0) == (delta[self.oxidation_element] > 0):
            raise ScissionError("the reduction and oxidation elements must change charge in opposite directions")

    def equation(self) -> str:
        lhs = " + ".join(repr(m) for m in (self.reactant,) + self.reagents)
        rhs = " + ".join(repr(m) for m in self.products)
        return f"{lhs} -> {rhs}"

    def forget(self) -> CoupledRedoxFormulaEdge:
        """The composition-level image: the balanced formula reaction with net-zero electron transfer."""
        return CoupledRedoxFormulaEdge(
            _formula_terms((self.reactant,) + self.reagents),
            _formula_terms(self.products),
            self.electrons_transferred,
        )

    def __repr__(self) -> str:
        return f"RedoxDisplacementEdge({self.equation()})"


def _scale(form: tuple[Molecule, ...], factor: int) -> tuple[Molecule, ...]:
    return tuple(m for _ in range(factor) for m in form)


def combine_half_reactions(
    reduction: HalfReactionCouple,
    oxidation: HalfReactionCouple,
    *,
    target: Molecule,
) -> RedoxDisplacementEdge:
    """Pair a reduction couple (the oxidant, ``reduction``) with an oxidation couple (the reductant,
    ``oxidation``), balance electrons by their LCM, and return the displacement that MAKES ``target``.

    ``target`` is the oxidised form of the ``oxidation`` couple (the reductant's elemental form) -- the
    single species the displacement synthesises.  The reduction couple runs forward (its oxidised form is
    reduced) and the oxidation couple runs backward (its reduced form is oxidised); the electrons cancel.
    For ``reduction = Cl2/2Cl-`` (n=2), ``oxidation = Br2/2Br-`` (n=2), ``target = Br2``: LCM = 2, so
    ``Cl2 + 2 Br- -> Br2 + 2 Cl-`` -- the 1:2 stoichiometry the single-species / capped families cannot
    reach.
    """
    for couple, label in ((reduction, "reduction"), (oxidation, "oxidation")):
        if type(couple) is not HalfReactionCouple:
            raise ScissionError(f"{label} must be a HalfReactionCouple")
    if type(target) is not Molecule:
        raise ScissionError("target must be a Molecule")
    if reduction.element == oxidation.element:
        raise ScissionError("a species cannot displace itself (both couples share a redox-active element)")
    if len(oxidation.oxidized_form) != 1 or oxidation.oxidized_form[0].canonical() != target.canonical():
        raise ScissionError(
            "target must be the single oxidised form of the oxidation couple (the elemental species made)"
        )

    total_electrons = lcm(reduction.electrons, oxidation.electrons)
    a = total_electrons // reduction.electrons  # scale of the reduction (oxidant) couple
    b = total_electrons // oxidation.electrons  # scale of the oxidation (reductant) couple

    # synthesis (making the target): a*(oxidant oxidised) + b*(reductant reduced) -> a*(oxidant reduced) + b*(target)
    synth_lhs = _scale(reduction.oxidized_form, a) + _scale(oxidation.reduced_form, b)
    synth_rhs = _scale(reduction.reduced_form, a) + _scale(oxidation.oxidized_form, b)

    # the transform decomposes the target: from_transform reads products as the synth precursors (LHS) and
    # (reactant,) + reagents as the synth products (RHS).  Peel exactly one target instance off the RHS.
    remaining = list(synth_rhs)
    key = target.canonical()
    for i, m in enumerate(remaining):
        if m.canonical() == key:
            del remaining[i]
            break
    else:  # pragma: no cover - guaranteed present: target is b>=1 copies of oxidation.oxidized_form in synth_rhs
        raise ScissionError("internal: the target is absent from the synthesis products")

    return RedoxDisplacementEdge(
        DISPLACEMENT_SCHEMA,
        target,
        tuple(synth_lhs),
        tuple(remaining),
        reduction.element,
        oxidation.element,
        total_electrons,
    )


def halogen_couple(symbol: str) -> HalfReactionCouple:
    """The halogen redox couple ``X2 + 2 e- <-> 2 X-`` for ``X in {F, Cl, Br, I}`` -- the couples the
    DOW-bromine displacement pairs.  A convenience over the general :class:`HalfReactionCouple`."""
    if symbol not in {"F", "Cl", "Br", "I"}:
        raise ScissionError("halogen_couple is defined for F, Cl, Br, I")
    x2 = Molecule.diatomic(symbol, symbol, order=1)
    anion = Molecule.atom(symbol, charge=-1)
    return HalfReactionCouple(DISPLACEMENT_SCHEMA, symbol, (x2,), (anion, anion), 2)


@dataclass(frozen=True)
class RedoxDisplacementProvider(TransformProvider):
    """The two-species redox displacement family as a typed, opt-in provider (DECOMPILE-only; absent
    from ``DEFAULT_TRANSFORM_REGISTRY``, like the heterolytic and single-species redox families).

    It carries a closed set of :class:`HalfReactionCouple` s (its algebra).  When asked to decompose a
    ``reactant`` that is the oxidised (elemental) form of one of its couples, it pairs that couple (as the
    OXIDATION -- the target is made) with every OTHER couple whose oxidised form is present in the
    ``reagents`` pool (as the REDUCTION -- the available oxidant), emitting one displacement per pairing.
    Changing the couple set changes the capability manifest, hence the registry digest.
    """

    couples: tuple[HalfReactionCouple, ...] = ()
    provider_id: str = "redox-displacement"
    provider_version: str = "v1"
    witness_kind: str = "REDOX_DISPLACEMENT"

    def __post_init__(self) -> None:
        if type(self.couples) is not tuple or any(type(c) is not HalfReactionCouple for c in self.couples):
            raise ScissionError("couples must be a tuple of HalfReactionCouple values")
        if len({c.element for c in self.couples}) != len(self.couples):
            raise ScissionError("a displacement provider's couples must have distinct redox-active elements")

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", "redox-displacement"),
            ("mechanism", "two-species electron-balanced redox displacement (oxidant reduces, reductant oxidises)"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "COUPLED_REDOX_FORMULA_EDGE"),
            ("charged", True),
            ("couples", tuple(c.digest for c in self.couples)),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        # the boundary contract: never raise; a family that cannot apply enumerates nothing and is complete.
        if not self.couples:
            return (), True
        key = reactant.canonical()
        made_by = [
            c for c in self.couples
            if len(c.oxidized_form) == 1 and c.oxidized_form[0].canonical() == key
        ]
        if not made_by:
            return (), True  # the reactant is not the elemental form of any known couple
        available = _multiset(tuple(reagents)) if reagents else Counter()
        out = []
        for oxidation in made_by:
            for reduction in self.couples:
                if reduction.element == oxidation.element:
                    continue
                # the oxidant (the reduction couple's oxidised form) must actually be on hand.
                if not available or not all(available.get(m.canonical(), 0) >= n
                                            for m, n in _multiset(reduction.oxidized_form).items()):
                    continue
                out.append(combine_half_reactions(reduction, oxidation, target=reactant))
        return tuple(out), True
