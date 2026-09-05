"""COST-VEC-01 (2b): the section-10.4 vector-affordability core -- a CostVector and a Pareto frontier.

Section 10.4 makes affordability MULTI-OBJECTIVE: a conformant cost is a VECTOR of independent axes (cash, equipment,
material quantity/waste, energy, labor/time, preprocessing, analytical, waste-disposal, supply confidence, evidence
tier), ranked by a Pareto frontier -- never collapsed into one hidden scalar -- and it "MUST NOT trade away a hard
safety, identity, legal, or equipment constraint for lower cost."  This module is that discipline, as a tested
primitive:

* :class:`CostVector` -- the axes, every one honestly ``None`` when UNKNOWN (section 10.4: "Unknown values remain
  unknown"; a bare 0 would be a fabricated free lunch).  Only the axes we have real data for are ever populated today
  (cash from a 2a :class:`~smartchem.experiment.stock.CostObservation`, access difficulty from a commodity's curated
  availability, evidence-tier rank from the compiler); the rest stay UNKNOWN, not invented.
* :func:`dominates` / :func:`pareto_frontier` -- Pareto dominance with two honest rules: a hard blocker DOMINATES cost
  (an option with an unmet hard safety/identity/legal/equipment constraint is worse than any option without one, at
  any price -- G6), and UNKNOWN axes are INCOMPARABLE (a value cannot claim to beat an unknown, and an unknown cannot
  claim to beat a value), so the frontier refuses to over-rank on data it does not have.
* :func:`basket_cost_vector` -- aggregate the commodity costs a route/basket consumes into one vector (cash sums,
  access is the worst leaf, a hard blocker on any leaf blocks the basket), so a route's affordability is the
  affordability of the materials it actually buys -- the shape the route-level frontier will consume.

The LIVE route-level wiring shipped (COST-VEC-01): ``service._affordability_frontier`` populates
``CompilationResponse.affordability_frontier`` from each ranked route's commodity basket on a routes-mode search.
And the coupled/partial case is now honest (COST-VEC-01-coupled): a basket that is only PARTIALLY priced reports a
``cash_floor`` -- a proven LOWER BOUND -- instead of collapsing cash to a bare UNKNOWN, and ``dominates`` treats the
cash axis as an interval so a known-cheap route can still dominate a floored-dear one without fabricating the unknown.

Boundary (named, not hidden): the basket is still PER-UNIT -- ``basket_cost_vector`` prices ONE ``unit`` of each leaf,
so both the exact ``cash`` and the ``cash_floor`` assume unit quantities; a route needing a sub-unit amount is not
lower-bounded by the full per-unit price (the named "quantity/stoich axis" follow-on, not yet built).  A mixed-currency
basket reports NEITHER cash nor floor (conservative -- it never sums across currencies, even though a same-currency
sub-basket floor provably exists); tightening that to a per-currency floor is a further follow-on.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Digestible

#: The numeric affordability axes, ALL minimized (lower is better/cheaper/easier).  Kept as a tuple so `dominates`
#: iterates exactly the section-10.4 axes and a new axis is added in one place.
_AXES: tuple[str, ...] = (
    "cash",                 # cash outlay, in the vector's `currency` per `unit` (from a CostObservation)
    "access_difficulty",    # supply-confidence proxy: 0 = easiest to obtain (grocery) ... larger = harder
    "evidence_tier_rank",   # 0 = most ready/established ... larger = more speculative
    "new_equipment",        # required new equipment burden
    "material_quantity",    # material quantity + package waste
    "energy",               # energy estimate
    "labor_time",           # labor / elapsed-time estimate
    "preprocessing",        # preprocessing / purification burden
    "analytical",           # analytical burden
    "waste_disposal",       # waste-treatment / disposal burden
)

#: the point-valued axes -- every axis EXCEPT cash, which is INTERVAL-valued once a ``cash_floor`` can bound it below.
_POINT_AXES: tuple[str, ...] = tuple(a for a in _AXES if a != "cash")


def _cash_interval(v: "CostVector") -> "tuple[float, float] | None":
    """The NECESSARY cost interval of ``v`` on the cash axis, or ``None`` when cash is entirely UNKNOWN.

    A known cash ``K`` is the degenerate point ``(K, K)``.  A ``cash_floor`` ``F`` (exact cash UNKNOWN) is the
    half-open bound ``(F, +inf)`` -- the true cost is AT LEAST ``F`` but unbounded above.  Dominance below uses this
    for *necessary* dominance: ``a`` is no-worse than ``b`` on cash iff ``a``'s max possible cost <= ``b``'s min
    possible cost (``a_hi <= b_lo``), so a floor can never dominate (its ``a_hi`` is ``+inf``), only be dominated by a
    known cost below it -- the compiler never claims a cost ordering it cannot guarantee."""
    if v.cash is not None:
        return (float(v.cash), float(v.cash))
    if v.cash_floor is not None:
        return (float(v.cash_floor), float("inf"))
    return None


@dataclass(frozen=True)
class CostVector:
    """A section-10.4 cost vector: independent minimized axes, each ``None`` when UNKNOWN, plus the hard-constraint
    blockers that dominate cost.  ``currency``/``unit``/``region`` label the cash axis (never enter dominance)."""

    cash: "float | None" = None
    #: COST-VEC-01-coupled: an honest LOWER BOUND on cash when the exact total is UNKNOWN -- the sum of the priced,
    #: commensurable leaves of a basket that is only PARTIALLY priced (or whose quantity is coupled/underdetermined,
    #: so you need at least one of each leaf regardless of allocation).  ``None`` when cash is either fully known
    #: (use ``cash``) or has no floor at all.  MUTUALLY EXCLUSIVE with ``cash``: a known cash carries no separate
    #: floor.  It makes the cash axis INTERVAL-valued for dominance -- ``[cash_floor, +inf)`` -- so a route with a
    #: KNOWN cheap cost can dominate one whose cost is only known to be AT LEAST some larger floor, without ever
    #: fabricating the unknown total (section 10.4 / audit 11.2: refuse the coupled scalar, report the honest range).
    cash_floor: "float | None" = None
    access_difficulty: "int | None" = None
    evidence_tier_rank: "int | None" = None
    new_equipment: "float | None" = None
    material_quantity: "float | None" = None
    energy: "float | None" = None
    labor_time: "float | None" = None
    preprocessing: "float | None" = None
    analytical: "float | None" = None
    waste_disposal: "float | None" = None
    #: unmet hard safety / identity / legal / equipment constraints; a non-empty tuple dominates cost (section 10.4).
    hard_blockers: tuple[str, ...] = ()
    currency: str = ""
    unit: str = ""
    region: str = ""

    def __post_init__(self) -> None:
        if type(self.hard_blockers) is not tuple or any(not isinstance(b, str) or not b for b in self.hard_blockers):
            raise TypeError("hard_blockers must be a tuple of non-empty reason strings")
        for axis in _AXES:
            v = getattr(self, axis)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or v != v):
                raise TypeError(f"{axis} must be a real number or None (UNKNOWN), not {v!r}")
        if self.cash_floor is not None:
            if not isinstance(self.cash_floor, (int, float)) or isinstance(self.cash_floor, bool) or self.cash_floor != self.cash_floor:
                raise TypeError(f"cash_floor must be a real number or None (UNKNOWN), not {self.cash_floor!r}")
            if self.cash_floor < 0:
                raise ValueError("cash_floor is a lower bound on a sum of non-negative prices; it cannot be negative")
            if self.cash is not None:
                raise ValueError("cash_floor and cash are mutually exclusive: a KNOWN cash carries no separate floor")

    @property
    def is_hard_blocked(self) -> bool:
        return bool(self.hard_blockers)

    def known_axes(self) -> dict[str, float]:
        return {a: float(getattr(self, a)) for a in _AXES if getattr(self, a) is not None}

    def has_cost_signal(self) -> bool:
        """Any real affordability signal: a known point axis, an honest cash floor, or a hard blocker.  A
        floor-only vector (cash UNKNOWN but bounded BELOW) carries real signal and must NOT be gated off as blank."""
        return bool(self.known_axes()) or self.cash_floor is not None or self.is_hard_blocked


def dominates(a: CostVector, b: CostVector) -> bool:
    """Does ``a`` Pareto-dominate ``b``?  True iff ``a`` is no worse than ``b`` on every comparable axis and strictly
    better on at least one -- with two honest section-10.4 rules layered on:

    * HARD BLOCKER DOMINATES COST (G6): a clean option beats a hard-blocked one at any price; a hard-blocked option
      never dominates a clean one; if both are blocked (or both clean) the numeric axes decide.  This rule takes
      PRECEDENCE over the UNKNOWN rule below: a clean vector dominates a hard-blocked one even when the clean vector's
      cost axes are entirely UNKNOWN (section 10.4 -- an unmet hard safety/identity/legal/equipment constraint is
      never traded for cost, so "not blocked, cost unknown" still beats "blocked", and the "all-unknown b is
      dominated by nothing" clause holds only among vectors of EQUAL blocked-status).
    * UNKNOWN IS INCOMPARABLE: dominance is judged against the axes ``b`` KNOWS.  To dominate ``b``, ``a`` must be
      KNOWN and no worse on EVERY axis ``b`` knows (an axis ``a`` leaves UNKNOWN where ``b`` has a value blocks
      domination -- ``a`` cannot claim to beat a dimension it does not measure), and strictly better on at least one
      of them.  An axis ``a`` knows but ``b`` does not is ignored (``a`` cannot be BEATEN by an unknown either).  So
      an all-unknown ``b`` is dominated by nothing, and the frontier never over-ranks on data it does not have.
    * CASH IS INTERVAL-VALUED (COST-VEC-01-coupled): the 9 non-cash axes are points, but cash is an interval via
      :func:`_cash_interval` -- a known cash is the point ``[K, K]``, a ``cash_floor`` is the half-open bound
      ``[F, +inf)``, and entirely-unknown cash is INCOMPARABLE like any other unknown axis.  Cash uses NECESSARY
      dominance: ``a`` is no-worse-on-cash iff ``a``'s max possible cost <= ``b``'s min (``a_hi <= b_lo``) and
      strictly better iff ``a_hi < b_lo``.  Consequently a floor (``a_hi = +inf``) can NEVER dominate on cash -- it
      can only be dominated by a KNOWN cost strictly below its floor -- so the frontier never claims a cost ordering
      it cannot guarantee (two floors, or a floor above a known, are incomparable on cash).
    """
    # hard-blocker rule first -- it overrides the cost axes entirely (a hard blocker dominates cost, G6).
    if a.is_hard_blocked and not b.is_hard_blocked:
        return False
    if b.is_hard_blocked and not a.is_hard_blocked:
        return True
    # both clean, or both blocked.  a must be no-worse on every axis b constrains, strictly better on at least one.
    strictly_better_somewhere = False
    b_constrains_something = False
    # the 9 POINT axes (everything but cash) -- unchanged point logic.
    for ax in _POINT_AXES:
        bv = getattr(b, ax)
        if bv is None:
            continue
        b_constrains_something = True
        a_raw = getattr(a, ax)
        if a_raw is None:
            return False  # a is UNKNOWN where b is known -> cannot claim no-worse -> cannot dominate
        av = float(a_raw)
        bv = float(bv)
        if av > bv:
            return False  # worse on an axis b knows -> not dominating
        if av < bv:
            strictly_better_somewhere = True
    # the cash axis is INTERVAL-valued (a cash_floor bounds it below): necessary dominance is a_hi <= b_lo.
    b_cash = _cash_interval(b)
    if b_cash is not None:
        b_constrains_something = True
        a_cash = _cash_interval(a)
        if a_cash is None:
            return False  # a's cash is entirely UNKNOWN where b's is bounded -> cannot claim no-worse
        a_lo, a_hi = a_cash
        b_lo, b_hi = b_cash
        if a_hi > b_lo:
            return False  # a could cost more than b's cheapest possible -> not necessarily no-worse
        if a_hi < b_lo:
            strictly_better_somewhere = True  # a's dearest is below b's cheapest -> necessarily strictly cheaper
    if not b_constrains_something:
        return False  # nothing b constrains -> nothing to be strictly better ON -> cannot dominate
    return strictly_better_somewhere


def pareto_frontier(items: "list") -> "list":
    """The non-dominated subset of ``items`` (order preserved).  Each item must expose a ``.cost_vector`` of type
    :class:`CostVector`.  An item is on the frontier iff no OTHER item strictly dominates it."""
    vecs = []
    for it in items:
        v = getattr(it, "cost_vector", None)
        if type(v) is not CostVector:
            raise TypeError("every item must expose a .cost_vector of type CostVector")
        vecs.append(v)
    frontier = []
    for i, it in enumerate(items):
        if not any(j != i and dominates(vecs[j], vecs[i]) for j in range(len(items))):
            frontier.append(it)
    return frontier


# access-difficulty ordinal for a commodity's curated availability (easiest-first == smallest, section reagents.py).
_ACCESS_ORDINAL = {"grocery": 0, "pharmacy": 1, "hardware": 2, "pool_garden": 3}


def basket_cost_vector(commodity_molecules: "list", *, hard_blockers: tuple[str, ...] = ()) -> CostVector:
    """Aggregate the commodity leaves a route/basket buys (each a :class:`~smartchem.category.Molecule`) into ONE
    section-10.4 vector -- the shape the route-level frontier will build from a route's terminal reagents.

    Cash is the SUM of the leaves' 2a prices (a basket costs the sum of its parts), KNOWN only if EVERY leaf is
    priced AND all agree on currency+unit -- one unpriced or incommensurable leaf drops cash to UNKNOWN rather than
    under-count the basket (fail to UNKNOWN, never fabricate a cheaper total; section 10.4).  Access difficulty is the
    WORST (hardest) leaf -- a basket is only as obtainable as its least-obtainable part -- and is UNKNOWN if any leaf
    is not a known commodity (never assume easy).  A hard blocker passed in blocks the whole basket.  Unmodeled axes
    stay UNKNOWN.  An EMPTY basket has no known cash/access (all UNKNOWN) -- a route buying nothing is not "free".
    """
    from .commodity_pricing import cost_observation_for  # forward dep, at call time to keep import light
    from ..data.reagents import commodity_for

    n_leaves = len(commodity_molecules)
    priced: "list[tuple[float, str, str]]" = []  # (amount, currency, unit) for each PRICED leaf
    worst_access: "int | None" = None
    all_known_commodity = bool(commodity_molecules)

    for mol in commodity_molecules:
        obs = cost_observation_for(mol)
        if obs is not None:
            priced.append((float(obs.amount), obs.currency, obs.unit))

        commodity = commodity_for(mol)
        if commodity is None:
            all_known_commodity = False
        else:
            access = _ACCESS_ORDINAL.get(commodity.availability.value)
            if access is None:
                # a known commodity whose availability is not mapped to an ordinal (a future Availability member):
                # its obtainability is UNKNOWN, not "easy" -- drop access to UNKNOWN rather than silently skip it
                # (fail-SAFE; `test_access_ordinal_covers_every_availability` also fails-fast on this at CI).
                all_known_commodity = False
            else:
                worst_access = access if worst_access is None else max(worst_access, access)

    # Cash is KNOWN only when EVERY leaf is priced AND all agree on currency+unit.  When SOME (but not all) priced
    # leaves are commensurable, their sum is an honest cash_floor -- a PROVEN lower bound (you need >=1 of each leaf,
    # so the true basket costs at least this), never a fabricated total for the unpriced/coupled remainder (audit
    # 11.2: refuse the coupled scalar, report the honest range).  Incommensurable priced leaves (mixed currency/unit)
    # yield NEITHER cash nor floor -- you cannot honestly sum across currencies (this also removes the old latent
    # cross-currency sum that was only masked by being discarded unless every leaf was commensurable).
    cash: "float | None" = None
    cash_floor: "float | None" = None
    currency = ""
    unit = ""
    if priced:
        currencies = {(c, u) for _, c, u in priced}
        if len(currencies) == 1:
            (currency, unit), = currencies
            total = sum(a for a, _, _ in priced)
            if len(priced) == n_leaves:
                cash = total          # every leaf priced -> the exact basket cost
            else:
                cash_floor = total    # partial -> an honest lower bound, not a fabricated total

    access_difficulty = worst_access if all_known_commodity else None
    has_cash = cash is not None or cash_floor is not None
    return CostVector(
        cash=cash,
        cash_floor=cash_floor,
        access_difficulty=access_difficulty,
        hard_blockers=tuple(hard_blockers),
        currency=currency if has_cash else "",
        unit=unit if has_cash else "",
    )


# -- the route-level frontier entry (COST-VEC-01 wiring shape) -----------------------------------------------------

# v1alpha2 (COST-VEC-01-coupled): the flattened CostVector gained a ``cash_floor`` axis (an honest partial-basket
# lower bound), so the entry's serialized shape changed -- one bump per shape change.
AFFORDABILITY_FRONTIER_ENTRY_SCHEMA = "smartchem.experiment/affordability-frontier-entry-v1alpha2"


@dataclass(frozen=True)
class AffordabilityFrontierEntry(Digestible):
    """One route's place on the section-10.4 affordability frontier: its route identity + its basket CostVector.

    ``route_digest`` is byte-identical to the matching ``RankedRouteSummary.route_digest``, so a frontier entry
    links back to the ranked route it prices.  ``cost_vector`` is the ``basket_cost_vector`` of that route's
    commodity leaves.  It is a :class:`~smartchem.contracts.Digestible` -- its digest folds in the CostVector via
    ``canonical_payload`` (which recurses into the nested dataclass), so a serialized/round-tripped frontier is
    tamper-checkable.  The entry exposes ``.cost_vector`` exactly as :func:`pareto_frontier` requires, so a tuple of
    entries is a valid frontier input directly.
    """

    schema_version: str
    route_digest: str
    cost_vector: CostVector

    def __post_init__(self) -> None:
        if self.schema_version != AFFORDABILITY_FRONTIER_ENTRY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {AFFORDABILITY_FRONTIER_ENTRY_SCHEMA!r}")
        if not isinstance(self.route_digest, str) or not self.route_digest:
            raise ValueError("route_digest must be a non-empty string")
        if type(self.cost_vector) is not CostVector:
            raise TypeError("cost_vector must be a CostVector")

    @classmethod
    def of(cls, route_digest: str, cost_vector: CostVector) -> "AffordabilityFrontierEntry":
        return cls(AFFORDABILITY_FRONTIER_ENTRY_SCHEMA, route_digest, cost_vector)
