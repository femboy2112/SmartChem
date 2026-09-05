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
* ``UNKNOWN`` -- no sourced selectivity reaches this reactant set, or the product did not resolve to a
  registered isomer. A sparse registry cannot establish that alternative products do not exist.
* ``NOT_APPLICABLE`` -- reserved for an explicit justification that no selectivity question applies.
  The current evidence schema has no such justification, so this producer never infers it from registry size.

Independence (why this is not self-certifying)
----------------------------------------------
The selectivity fact comes from a SEPARATE sourced table, indexed by the reactant composition but fired only
against STRUCTURAL identity on BOTH sides -- the product resolves to a registered isomer, and every reactant
must resolve to an isomer the record NAMES (EVD-KEY-01: composition is not identity, so a keyless or
partial-names record never borrows a verdict across same-composition isomers) -- never from the route's own
declaration.  The table is injectable per call (:meth:`SelectivityTable.with_records`) so any
chemical's sourced selectivity can be brought without editing the seed: the universal-engine / sourced-data
split, exactly as for stability and conditions.  The seed is tiny and every record carries a provenance;
the point is the mechanism, not coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import gcd
from collections import Counter

from ..category import Molecule
from ..contracts import Digestible, EvidenceStatus
from ..decompiler import Formula
from ..provenance import SourceCitation, SourceReview
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
    NOT_APPLICABLE = "NOT_APPLICABLE"  # reserved: requires an explicit non-applicability justification


def _composition(molecule: Molecule) -> CompositionKey:
    return Formula.of(molecule.formula, molecule.charge).counts


def _reactant_key(reactants: tuple[Molecule, ...]) -> CompositionKey:
    """The primitive, scale-independent multiset of reactant compositions (order-independent)."""
    counts = Counter(_composition(m) for m in reactants)
    divisor = 0
    for coefficient in counts.values():
        divisor = gcd(divisor, coefficient)
    divisor = divisor or 1
    return tuple(sorted(composition for composition, n in counts.items() for _ in range(n // divisor)))


def _formulas_key(*formula_strings: str) -> CompositionKey:
    counts = Counter(Formula.parse(f).counts for f in formula_strings)
    divisor = 0
    for coefficient in counts.values():
        divisor = gcd(divisor, coefficient)
    divisor = divisor or 1
    return tuple(sorted(composition for composition, n in counts.items() for _ in range(n // divisor)))


@dataclass(frozen=True)
class SelectivityRecord(Digestible):
    """A SOURCED regiochemical fact: for a reactant composition forming a product formula, which registered
    isomer is the MAJOR product.  Keyed structurally on the product (by the major isomer's registered name),
    scale-independent on the reactants.

    ``reactant_names`` isomer-keys the REACTANT side (EVD-KEY-01): a sourced verdict fires ONLY when this tuple
    covers EVERY reactant and each reactant structurally resolves (by the registry's exact canonical identity) to
    a named isomer.  Composition is NOT identity -- a composition can hide more than one starting isomer
    (4-aminophenol vs 3-aminophenol are both ``C6H7NO``), and a sourced regiochemical preference for one is not
    license to fire for another.  So a record that names NO reactants, or only SOME of them, is a loud UNKNOWN for
    any un-named reactant -- never a composition borrow (naming only a safe co-reactant does NOT bypass the check).
    The seed records name all their reactants; an injected record must do the same to fire.
    """

    reactant_key: CompositionKey
    product_formula: CompositionKey
    major_isomer_name: str
    provenance: str
    status: EvidenceStatus = EvidenceStatus.EXPERIMENTAL
    reactant_names: tuple[str, ...] = ()
    source: SourceCitation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.major_isomer_name, str) or not self.major_isomer_name:
            raise ValueError("major_isomer_name must be a non-empty registered name")
        if not isinstance(self.provenance, str) or not self.provenance:
            raise ValueError("a selectivity record must carry a provenance (no unsourced preference)")
        if not isinstance(self.status, EvidenceStatus):
            raise TypeError("status must be an EvidenceStatus")
        if self.status in (EvidenceStatus.UNSUPPORTED, EvidenceStatus.STRUCTURAL_TOY):
            raise ValueError(
                "a selectivity record is a positive experimental attestation and cannot be UNSUPPORTED or "
                "STRUCTURAL_TOY; omit the record to represent UNKNOWN"
            )
        if type(self.reactant_names) is not tuple or any(
            not isinstance(n, str) or not n for n in self.reactant_names
        ):
            raise TypeError("reactant_names must be a tuple of non-empty strings")
        if self.source is not None and type(self.source) is not SourceCitation:
            raise TypeError("source must be a SourceCitation or None")

    @property
    def is_source_attested(self) -> bool:
        """Whether this record's typed locator was explicitly accepted by data review."""
        return self.source is not None and self.source.accepted


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


def selectivity_of_step(
    step: ExperimentStep, *, table: SelectivityTable, losses: tuple = ()
) -> StepSelectivity:
    """The regiochemical selectivity of one assembly step: does it make the sourced major isomer?

    UNKNOWN when no sourced fact reaches this reactant set (or the product does not resolve); FAVORED /
    DISFAVORED against a sourced record. Registry membership is incomplete: zero or one registered isomer
    cannot establish non-applicability. An exact sourced match may still fire with sparse registry coverage.

    ``losses`` (EVD-KEY-01, the consumer half): the section-5.3 :class:`~smartchem.identity.IdentityLoss` records
    the target identity carries.  If any is a BLOCKER for the ``"selectivity"`` claim class -- because the input
    dropped a feature selectivity can depend on (a stereocentre, an isotope, a charge state) -- a SOURCED FAVORED /
    DISFAVORED verdict MUST NOT survive it (section 5.3): it is downgraded to a loud UNKNOWN naming the blocker.
    """
    from ..identity import blocking_losses
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    target = step.target
    formula = Formula.of(target.formula, target.charge)
    isomers = known_compounds(formula)
    rec = table.lookup(step.reactants, formula.counts)
    if rec is None:
        if len(isomers) < 2:
            return StepSelectivity(
                SelectivityStatus.UNKNOWN,
                f"UNKNOWN: no sourced selectivity for this reactant set forming {formula!r}; "
                f"{len(isomers)} registered isomer(s) is incomplete registry coverage, not evidence "
                "that alternative products or a selectivity question are absent",
                unknown("selectivity", "", "no sourced selectivity; registry completeness is not established"),
            )
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            f"UNKNOWN: {len(isomers)} registered isomers of {formula!r} compete, but no sourced selectivity "
            f"for this reactant set (inject a sourced record to resolve which isomer this reaction favors)",
            unknown("selectivity", "", f"{len(isomers)} isomers compete; no sourced regiochemical fact"),
        )

    if not rec.is_source_attested:
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            "UNKNOWN: a selectivity preference was declared, but it has no accepted typed source citation "
            "and cannot earn a sourced grade",
            unknown("selectivity", "", "free text or an unreviewed citation is not accepted source evidence"),
        )

    # EVD-KEY-01 (reactant-side isomer key): a sourced verdict fires only when EVERY reactant is pinned to a NAMED
    # isomer.  Composition is NOT identity -- a same-composition isomer (3-aminophenol for 4-aminophenol; both
    # C6H7NO) would BORROW the sourced verdict (the "a-reaction-key-by-formula-borrows-a-rate" fail-open, on the
    # reactant side).  The airtight close: the record's ``reactant_names`` must cover ALL of this step's reactants,
    # and each must structurally resolve (via the registry's exact canonical identity) to a named isomer.  This
    # closes THREE holes a composition-only or partial-names key leaves open (red-team folds):
    #   * a keyless (empty reactant_names) record firing on composition alone;
    #   * a PARTIAL-names record (names only the safe co-reactant) skipping the check for the ambiguous substrate --
    #     strictly WORSE than naming nothing, because naming a subset used to bypass the guard entirely;
    #   * "unique registered isomer" is NOT unique REAL isomer -- the registry undercounts (C6H7NO has three real
    #     aminophenols, one registered), so a composition-only "unique" match still borrows from the unregistered
    #     siblings.  Only an EXPLICIT name, matched to the resolved structure, avoids every registry-completeness
    #     assumption.  The default seed records already name all reactants, so this fires exactly as before for them.
    named_set = set(rec.reactant_names)
    expected = ", ".join(sorted(named_set)) if named_set else "none named"
    matched_names: set[str] = set()
    for reactant in step.reactants:
        resolved = resolve_structure(reactant)
        overlap = (set(resolved.all_names) if resolved is not None else set()) & named_set
        if not overlap:
            # this reactant resolves to NO named isomer -- a composition match cannot attribute the verdict to it
            # (it may be a same-composition isomer the source never covered), so refuse rather than borrow.  This
            # fires for a keyless record (named_set empty), a partial-names record (the unnamed reactant), and a
            # wrong reactant isomer (it does not resolve to the required name) alike.  Multiplicity is irrelevant:
            # a scale-repeated reactant is checked the same, matching the scale-invariant composition key.
            which = resolved.name if resolved is not None else repr(reactant)
            return StepSelectivity(
                SelectivityStatus.UNKNOWN,
                f"UNKNOWN: a sourced selectivity exists (major: {rec.major_isomer_name}), but reactant {which} "
                f"does not resolve to any reactant isomer the record names ({expected}) -- composition is not "
                f"identity, so firing here would borrow the verdict across same-composition isomers; name every "
                f"reactant to key it structurally (EVD-KEY-01)",
                unknown(
                    "selectivity", "",
                    f"reactant {which} is not covered by the record's reactant_names ({expected}) -- no borrow",
                ),
            )
        matched_names |= overlap
    missing = named_set - matched_names
    if missing:
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            f"UNKNOWN: a sourced selectivity exists (major: {rec.major_isomer_name}) but a required reactant "
            f"isomer ({sorted(missing)[0]}) is not present — not fired for the wrong reactant isomer",
            unknown(
                "selectivity", "",
                f"required reactant isomer {sorted(missing)[0]} did not resolve among this step's reactants",
            ),
        )

    named = resolve_structure(target)
    if named is None:
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            f"UNKNOWN: a sourced selectivity exists (major product: {rec.major_isomer_name}), but this step's "
            f"product does not resolve to a registered isomer, so it cannot be compared",
            unknown("selectivity", "", "product structure did not resolve; cannot compare to the major isomer"),
        )

    # EVD-KEY-01 (section 5.3): a sourced record matched, but if a BLOCKER loss forbids a selectivity claim on this
    # identity, the sourced verdict MUST NOT survive -- the input dropped a feature selectivity can depend on, so a
    # FAVORED/DISFAVORED here would be a sourced fact attached to an under-determined identity.  Downgrade to UNKNOWN.
    blockers = blocking_losses(tuple(losses), "selectivity")
    if blockers:
        b = blockers[0]
        return StepSelectivity(
            SelectivityStatus.UNKNOWN,
            f"UNKNOWN: a sourced selectivity exists (major product: {rec.major_isomer_name}), but a section-5.3 "
            f"BLOCKER ({b.feature}) forbids a sourced selectivity claim on this identity -- the dropped feature is "
            f"one selectivity can depend on, so the sourced record must not survive it (section 5.3)",
            unknown("selectivity", "", f"section-5.3 blocker: {b.feature} forbids a sourced selectivity claim"),
        )

    if named.name == rec.major_isomer_name:
        return StepSelectivity(
            SelectivityStatus.FAVORED,
            f"FAVORED: {named.name} is the SOURCED major product of this reaction "
            f"({rec.provenance}; {rec.source.locator})",
            Quantity(
                "selectivity", f"major:{named.name}", "", Bucket.KNOWN_SOURCED,
                f"{rec.provenance}; {rec.source.locator}",
            ),
        )
    return StepSelectivity(
        SelectivityStatus.DISFAVORED,
        f"DISFAVORED: the SOURCED major product of this reaction is {rec.major_isomer_name}, but this step "
        f"makes {named.name} -- the minor isomer ({rec.provenance}; {rec.source.locator})",
        Quantity(
            "selectivity", f"minor:{named.name} (sourced major: {rec.major_isomer_name})", "",
            Bucket.KNOWN_SOURCED, f"{rec.provenance}; {rec.source.locator}",
        ),
    )


def verify_selectivity(
    route: ExperimentRoute, *, table: SelectivityTable = None, losses: tuple = ()
) -> RouteSelectivity:
    """The regiochemical selectivity of every step of a route (against the sourced, injectable table).

    ``losses`` are the section-5.3 identity-loss records the target carries; a BLOCKER for ``"selectivity"``
    downgrades every step's sourced verdict to UNKNOWN (EVD-KEY-01), so no sourced selectivity survives a blocker.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_SELECTIVITY if table is None else table
    per_step = tuple(selectivity_of_step(s, table=tbl, losses=losses) for s in route.steps)
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
        reactant_names=("4-aminophenol", "acetic anhydride"),
        provenance=(
            "N- vs O-acetylation of 4-aminophenol: the aromatic amine is far more nucleophilic than the "
            "phenol -OH, so acetic-anhydride acetylation is N-selective and gives the amide (paracetamol) "
            "as the major product (ACS J. Chem. Educ. teaching synthesis; standard regiochemistry)"
        ),
        source=SourceCitation(
            "https://doi.org/10.1021/acs.jchemed.0c01512", SourceReview.ACCEPTED
        ),
    ),
    # Mid-1: propene + water -> C3H8O, Markovnikov addition -> propan-2-ol (major).
    SelectivityRecord(
        reactant_key=_formulas_key("C3H6", "H2O"),
        product_formula=Formula.parse("C3H8O").counts,
        major_isomer_name="propan-2-ol",
        reactant_names=("propene", "water"),
        provenance=(
            "Markovnikov selectivity: acid-catalysed hydration of propene gives propan-2-ol as the MAJOR "
            "product (OH adds to the more-substituted carbon via the more stable secondary carbocation); "
            "propan-1-ol is minor. Sourced: AUS-e-TUTE hydration-of-alkenes tutorial; rule from V. "
            "Markovnikov 1870, Annalen der Chemie 153:228-259."
        ),
        source=SourceCitation(
            "https://doi.org/10.1002/jlac.18701530204", SourceReview.ACCEPTED
        ),
    ),
    # Mid-1: nitrobenzene + nitric acid -> C6H4N2O4, meta-director -> 1,3-dinitrobenzene (major).
    SelectivityRecord(
        reactant_key=_formulas_key("C6H5NO2", "HNO3"),
        product_formula=Formula.parse("C6H4N2O4").counts,
        major_isomer_name="1,3-dinitrobenzene",
        reactant_names=("nitrobenzene", "nitric acid"),
        provenance=(
            "Meta-director selectivity: electrophilic aromatic nitration of nitrobenzene gives "
            "1,3-dinitrobenzene as the MAJOR product (93%; ortho 6%, para 1%) because the -NO2 group is a "
            "deactivating meta-director. Sourced: Buddrus 2003, Grundlagen der organischen Chemie 3rd ed. "
            "p.360 (via Wikipedia '1,3-Dinitrobenzene'); corroborated by OCLUE (Cooper & Klymkowsky) 8.11."
        ),
        source=SourceCitation(
            "https://doi.org/10.1021/jo0609475", SourceReview.ACCEPTED
        ),
    ),
)

#: A convenience default seed; extended per call for any other chemical, NOT a whitelist.
DEFAULT_SELECTIVITY = SelectivityTable(SEED_SELECTIVITY_RECORDS)
