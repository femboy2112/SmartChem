"""E5 depth -- isomer-keyed regiochemical selectivity for candidate synthesis routes.

The retrosynthesis (E5) enumerates conservation-valid assemblies, and several may build the *same product
formula* by *different regiochemistry*.  ``decompiler_conditions.py`` says so in as many words: its
conditions are keyed by composition, so a formula-level edge "does not distinguish N- vs O-acetylation".
Paracetamol (the N-acetyl amide) and 4-aminophenyl acetate (the O-acetyl ester) share the formula
``C8H9NO2``; a formula key cannot tell which one a step makes.  The structure layer *can*
(:func:`~smartchem.structure.resolve_structure` names the specific isomer), and there is a SOURCED
regiochemical fact -- acetylation of 4-aminophenol is N-selective, so the amide is the major product and
the ester the minor one.  This module surfaces that fact in the route ranking.

The governing frame (reproduce KNOWN chemistry, never invent NEW physics), read exactly
--------------------------------------------------------------------------------------
Regiochemical selectivity is precisely "which isomer Nature prefers".  That is not a forbidden prediction:
where an ESTABLISHED / SOURCED selectivity fact reaches it, we emit the verdict, labelled ``KNOWN_SOURCED``
with its provenance -- reproducing known chemistry, the same discipline the PySCF oracle uses to *compute*
an atomization energy rather than look one up.  Where no sourced fact reaches it, the verdict is
``UNKNOWN`` (loud), never a fabricated preference.  The one refusal that survives: we never assert a
regiochemistry that contradicts a sourced fact, and we never manufacture one where none exists.

The verdicts, and the non-vacuity guard (W2)
--------------------------------------------
* ``FAVORED`` -- SOURCED: this step makes the MAJOR isomer of the product formula for this reaction.
* ``DISFAVORED`` -- SOURCED: a *different* registered isomer is the major product; this step makes a minor
  one (a real, sourced demerit -- the reaction preferentially gives something else).
* ``UNKNOWN`` -- two or more registered isomers of the product formula compete, but no sourced selectivity
  reaches this reactant set (a loud gap), or the product did not resolve to a registered isomer.
* ``NOT_APPLICABLE`` -- the product formula has a single registered isomer: there is no regiochemical
  selectivity question at all.  A ``FAVORED`` verdict is NEVER manufactured where no isomers compete -- the
  repo's recurring "vacuous green over an empty subject" guard, applied to selectivity.

Independence (why this is not self-certifying)
----------------------------------------------
The selectivity fact comes from a SEPARATE sourced table, keyed by the reactant composition and matched
against the product's STRUCTURAL identity (resolved independently through the registry) -- never from the
route's own declaration.  The table is injectable per call (:meth:`SelectivityTable.with_records`) so any
chemical's sourced selectivity can be brought without editing the seed: the universal-engine / sourced-data
split, exactly as for stability and conditions.  The seed is tiny and every record carries a provenance;
the point is the mechanism, not coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..category import Molecule
from ..contracts import Digestible, EvidenceStatus
from ..decompiler import Formula
from ..structure import known_compounds, resolve_structure
from .bucket import Bucket, Quantity, unknown
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "SelectivityStatus",
    "SelectivityRecord",
    "SelectivityTable",
    "StepSelectivity",
    "RouteSelectivity",
    "selectivity_of_step",
    "verify_selectivity",
    "SEED_SELECTIVITY_RECORDS",
    "DEFAULT_SELECTIVITY",
]

#: A scale-independent composition multiset key: a sorted tuple of formula ``counts``.
CompositionKey = tuple


class SelectivityStatus(str, Enum):
    """The regiochemical selectivity verdict for one assembly step (which isomer it makes)."""

    FAVORED = "FAVORED"                # sourced: this step makes the MAJOR isomer of the product formula
    DISFAVORED = "DISFAVORED"          # sourced: a different registered isomer is the major product
    UNKNOWN = "UNKNOWN"                # isomers compete, but no sourced selectivity (a loud gap)
    NOT_APPLICABLE = "NOT_APPLICABLE"  # a single registered isomer -- no selectivity question


def _composition(molecule: Molecule) -> CompositionKey:
    return Formula.of(molecule.formula, molecule.charge).counts


def _reactant_key(reactants: tuple[Molecule, ...]) -> CompositionKey:
    """The scale-independent multiset of reactant compositions (order-independent)."""
    return tuple(sorted(_composition(m) for m in reactants))


def _formulas_key(*formula_strings: str) -> CompositionKey:
    return tuple(sorted(Formula.parse(f).counts for f in formula_strings))


@dataclass(frozen=True)
class SelectivityRecord(Digestible):
    """A SOURCED regiochemical fact: for a reactant composition forming a product formula, which registered
    isomer is the MAJOR product.  Keyed structurally on the product (by the major isomer's registered name),
    scale-independent on the reactants."""

    reactant_key: CompositionKey
    product_formula: CompositionKey
    major_isomer_name: str
    provenance: str
    status: EvidenceStatus = EvidenceStatus.EXPERIMENTAL

    def __post_init__(self) -> None:
        if not isinstance(self.major_isomer_name, str) or not self.major_isomer_name:
            raise ValueError("major_isomer_name must be a non-empty registered name")
        if not isinstance(self.provenance, str) or not self.provenance:
            raise ValueError("a selectivity record must carry a provenance (no unsourced preference)")
        if not isinstance(self.status, EvidenceStatus):
            raise TypeError("status must be an EvidenceStatus")


@dataclass(frozen=True)
class SelectivityTable(Digestible):
    """An immutable set of sourced selectivity records, injectable per call for any chemical.

    Mirrors :class:`~smartchem.data.stability.StabilityTable`: the compiler holds a table, not the module
    dict, so a caller can EXTEND coverage with :meth:`with_records` and pass the result in.  Records are
    deduplicated by ``(reactant_key, product_formula, major_isomer_name)``; a later record wins a collision.
    """

    records: tuple[SelectivityRecord, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(r) is not SelectivityRecord for r in self.records
        ):
            raise TypeError("records must be a tuple of SelectivityRecord values")

    def with_records(self, *records: SelectivityRecord) -> "SelectivityTable":
        by_key: dict[tuple, SelectivityRecord] = {
            (r.reactant_key, r.product_formula, r.major_isomer_name): r for r in self.records
        }
        for r in records:
            if type(r) is not SelectivityRecord:
                raise TypeError("with_records takes SelectivityRecord values")
            by_key[(r.reactant_key, r.product_formula, r.major_isomer_name)] = r
        ordered = tuple(sorted(by_key.values(), key=lambda r: (r.product_formula, r.major_isomer_name)))
        return SelectivityTable(ordered)

    def lookup(self, reactants: tuple[Molecule, ...], product_formula: CompositionKey) -> SelectivityRecord | None:
        """The sourced selectivity record for this reactant set forming ``product_formula``, or ``None``."""
        key = _reactant_key(reactants)
        for r in self.records:
            if r.reactant_key == key and r.product_formula == product_formula:
                return r
        return None


@dataclass(frozen=True)
class StepSelectivity(Digestible):
    """The regiochemical selectivity of one assembly step, with its sourced finding (or a loud gap)."""

    status: SelectivityStatus
    reason: str
    finding: Quantity

    def __post_init__(self) -> None:
        if not isinstance(self.status, SelectivityStatus):
            raise TypeError("status must be a SelectivityStatus")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")


@dataclass(frozen=True)
class RouteSelectivity(Digestible):
    """The regiochemical selectivity of a whole route: one :class:`StepSelectivity` per step, and a verdict.

    Verdict precedence (honest, not optimistic): a single SOURCED ``DISFAVORED`` step dominates; then any
    ``UNKNOWN`` competitive step keeps the route from being cleanly favored; a route is ``FAVORED`` only
    when every competitive step is sourced-favored and at least one exists; otherwise ``NOT_APPLICABLE``
    (no step poses a selectivity question).
    """

    route: ExperimentRoute
    per_step: tuple[StepSelectivity, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.per_step) is not tuple or any(type(s) is not StepSelectivity for s in self.per_step):
            raise TypeError("per_step must be a tuple of StepSelectivity values")
        if len(self.per_step) != len(self.route.steps):
            raise ValueError(f"expected {len(self.route.steps)} step selectivities, got {len(self.per_step)}")

    @property
    def verdict(self) -> str:
        statuses = [s.status for s in self.per_step]
        if any(s is SelectivityStatus.DISFAVORED for s in statuses):
            return "DISFAVORED"
        if any(s is SelectivityStatus.UNKNOWN for s in statuses):
            return "UNKNOWN"
        if any(s is SelectivityStatus.FAVORED for s in statuses):
            return "FAVORED"
        return "NOT_APPLICABLE"

    @property
    def disfavored_reasons(self) -> tuple[str, ...]:
        return tuple(s.reason for s in self.per_step if s.status is SelectivityStatus.DISFAVORED)

    def explain(self) -> str:
        lines = [f"selectivity: {self.verdict}"]
        for idx, s in enumerate(self.per_step):
            if s.status is not SelectivityStatus.NOT_APPLICABLE:
                lines.append(f"  step {idx + 1}: {s.reason}")
        return "\n".join(lines)


def selectivity_of_step(step: ExperimentStep, *, table: SelectivityTable) -> StepSelectivity:
    """The regiochemical selectivity of one assembly step: does it make the sourced major isomer?

    NOT_APPLICABLE when the product formula has a single registered isomer (no competition); UNKNOWN when
    isomers compete but no sourced fact reaches this reactant set (or the product does not resolve); FAVORED
    / DISFAVORED against a sourced record.  Never a fabricated preference.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    target = step.target
    formula = Formula.of(target.formula, target.charge)
    isomers = known_compounds(formula)
    if len(isomers) < 2:
        return StepSelectivity(
            SelectivityStatus.NOT_APPLICABLE,
            f"{formula!r}: a single registered isomer -- no regiochemical selectivity question",
            unknown("selectivity", "", "no isomeric competition for this product formula"),
        )

    rec = table.lookup(step.reactants, formula.counts)
    if rec is None:
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            f"UNKNOWN: {len(isomers)} registered isomers of {formula!r} compete, but no sourced selectivity "
            f"for this reactant set (inject a sourced record to resolve which isomer this reaction favors)",
            unknown("selectivity", "", f"{len(isomers)} isomers compete; no sourced regiochemical fact"),
        )

    named = resolve_structure(target)
    if named is None:
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            f"UNKNOWN: a sourced selectivity exists (major product: {rec.major_isomer_name}), but this step's "
            f"product does not resolve to a registered isomer, so it cannot be compared",
            unknown("selectivity", "", "product structure did not resolve; cannot compare to the major isomer"),
        )

    if named.name == rec.major_isomer_name:
        return StepSelectivity(
            SelectivityStatus.FAVORED,
            f"FAVORED: {named.name} is the SOURCED major product of this reaction ({rec.provenance})",
            Quantity("selectivity", f"major:{named.name}", "", Bucket.KNOWN_SOURCED, rec.provenance),
        )
    return StepSelectivity(
        SelectivityStatus.DISFAVORED,
        f"DISFAVORED: the SOURCED major product of this reaction is {rec.major_isomer_name}, but this step "
        f"makes {named.name} -- the minor isomer ({rec.provenance})",
        Quantity(
            "selectivity", f"minor:{named.name} (sourced major: {rec.major_isomer_name})", "",
            Bucket.KNOWN_SOURCED, rec.provenance,
        ),
    )


def verify_selectivity(route: ExperimentRoute, *, table: SelectivityTable = None) -> RouteSelectivity:
    """The regiochemical selectivity of every step of a route (against the sourced, injectable table)."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_SELECTIVITY if table is None else table
    per_step = tuple(selectivity_of_step(s, table=tbl) for s in route.steps)
    return RouteSelectivity(route, per_step)


#: The SEED records -- sourced, litmus-focused (the paracetamol acetylation family).  4-aminophenol bears a
#: far more nucleophilic aromatic amine than its phenol -OH, so acetylation is strongly N-selective: the
#: amide (paracetamol) is the major product, the O-acetyl ester (4-aminophenyl acetate) the minor one.
#: Tiny by design; injectable per call for any chemical, NOT a whitelist.
SEED_SELECTIVITY_RECORDS: tuple[SelectivityRecord, ...] = (
    # 4-aminophenol + acetic anhydride -> C8H9NO2: N-acetylation dominates -> paracetamol (major).
    SelectivityRecord(
        reactant_key=_formulas_key("C6H7NO", "C4H6O3"),
        product_formula=Formula.parse("C8H9NO2").counts,
        major_isomer_name="paracetamol",
        provenance=(
            "N- vs O-acetylation of 4-aminophenol: the aromatic amine is far more nucleophilic than the "
            "phenol -OH, so acetic-anhydride acetylation is N-selective and gives the amide (paracetamol) "
            "as the major product (ACS J. Chem. Educ. teaching synthesis; standard regiochemistry)"
        ),
    ),
    # 4-aminophenol + acetic acid -> C8H9NO2 (+ water): the same N-selectivity for the condensation route.
    SelectivityRecord(
        reactant_key=_formulas_key("C6H7NO", "C2H4O2"),
        product_formula=Formula.parse("C8H9NO2").counts,
        major_isomer_name="paracetamol",
        provenance=(
            "N- vs O-acetylation of 4-aminophenol: the amine outcompetes the phenol -OH, so the acetic-acid "
            "condensation is likewise N-selective, giving the amide (paracetamol) as the major product "
            "(standard amine>alcohol acylation regiochemistry)"
        ),
    ),
)

#: A convenience default seed; extended per call for any other chemical, NOT a whitelist.
DEFAULT_SELECTIVITY = SelectivityTable(SEED_SELECTIVITY_RECORDS)
