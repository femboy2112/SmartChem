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
* :func:`dominates` / :func:`pareto_frontier` -- Pareto dominance with two honest rules: the DISPOSITION TIER
  DOMINATES cost (:class:`Disposition` -- CLEAN < REAL_BUT_HARD < NOT_A_REACTION; a better-disposed option beats a
  worse-disposed one at any price -- G6, the 3-valued generalization of the old clean/blocked rule that keeps a
  real-but-hard reaction strictly above a not-a-reaction fiction), and UNKNOWN axes are INCOMPARABLE (a value cannot
  claim to beat an unknown, and an unknown cannot claim to beat a value), so the frontier refuses to over-rank on
  data it does not have.  The two blocker kinds ride DISJOINT channels -- ``hard_blockers`` (real-but-hard) and
  ``fiction_blockers`` (Problem-A not-a-reaction) -- which the tier is derived from (DISPOSITION-01).
* :func:`basket_cost_vector` -- aggregate the commodity costs a route/basket consumes into one vector (cash sums,
  access is the worst leaf, a hard blocker on any leaf blocks the basket), so a route's affordability is the
  affordability of the materials it actually buys -- the shape the route-level frontier will consume.

The LIVE route-level wiring shipped (COST-VEC-01): ``service._affordability_frontier`` populates
``CompilationResponse.affordability_frontier`` from each ranked route's commodity basket on a routes-mode search.
And the coupled/partial case is now honest (COST-VEC-01-coupled): a basket that is only PARTIALLY priced reports a
``cash_floor`` -- a proven LOWER BOUND -- instead of collapsing cash to a bare UNKNOWN, and ``dominates`` treats the
cash axis as an interval so a known-cheap route can still dominate a floored-dear one without fabricating the unknown.

The quantity/stoich layer (TERM-MAT, now built): ``basket_cost_vector``'s per-unit cash prices ONE package ``unit`` of
each leaf, blind to how much a route consumes.  Given a route's per-leaf ``(molecule, moles)`` requirement it instead
emits a QUANTITY-WEIGHTED ``cash_floor`` -- moles x price_per_mol via :mod:`smartchem.experiment.units` (the sourced
molar-mass + definitional mass-unit layer) -- a per-mol-of-PRODUCT material-cost lower bound.  Its role is honest and
narrow: it is an INFORMATIONAL lower bound, NOT a cash-axis dominance discriminator.  It is always a floor (100%-yield
mol bound x UNKNOWN-assay commodity), and by the necessary-dominance discipline a floor can never dominate on cash
(only a KNOWN point cash below it can); a weighted floor's denomination ("mol product") is also INCOMPARABLE with the
per-unit path's ("metric ton") -- ``dominates`` refuses to compare cash across denominations (the ``unit`` field is
load-bearing there, a red-team fold).  So material-burden RANKING is carried by the ``material_quantity`` (mol) axis; the
weighted cash floor is the $-annotation on top.  Boundaries still standing: a mixed-CURRENCY basket reports NEITHER cash
nor floor (never sums across currencies); and the weighted floor is DARK on any route whose leaves are unpriced (today
only NaCl / Na2CO3 are priced, so organic bench routes carry no weighted cash yet -- a DATA boundary, not faked).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

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


class Disposition(IntEnum):
    """The DISPOSITION channel (section-10.4 G6, refined): WHY a route is (or is not) a viable option, as a total
    order over three tiers -- the distinct disposition channel that un-flattens the shared ``hard_blockers`` tuple.

    Two KINDS of hard blocker used to share one tuple, so they were G6-sunk EQUALLY -- a route that is a genuine
    reaction merely needing an industrial catalyst (or barred by a section-11 bench bound) ranked identically to a
    route that is *no real reaction at all* (a Problem-A reaction-TYPE fiction the compiler over-generated by
    formula-conserving graph surgery).  The partial order "real-but-hard STRICTLY outranks not-a-reaction" was lost.
    This tier is that order, made explicit: a lower tier dominates a higher one at ANY cost (disposition dominates
    cost, exactly like the original 2-valued hard-blocker rule, now 3-valued).

    * ``CLEAN`` (0)          -- no hard blocker of either kind; the best tier, decided among peers by the cost axes.
    * ``REAL_BUT_HARD`` (1)  -- a genuine reaction blocked only by a real-but-hard constraint (an unobtainable
      catalyst, a section-11 bench exclusion, a safety/identity/legal/equipment bound).  A real option, just costly
      or out of reach -- it OUTRANKS a fiction, because a hard real reaction beats a formula-balanced non-reaction.
    * ``NOT_A_REACTION`` (2) -- at least one step matches NO attested reaction class (a reaction-TYPE fiction,
      Problem A): the route is not a real synthesis at all.  The worst tier, dominated by every real option.

    A vector's tier is the WORST over its blockers: any fiction blocker makes the whole route ``NOT_A_REACTION``
    (one non-reaction step voids the route), else any real-but-hard blocker makes it ``REAL_BUT_HARD``, else
    ``CLEAN``.  The tier is DERIVED from the two blocker tuples (:attr:`CostVector.disposition`), never stored
    separately, so it cannot drift out of sync with the reasons that justify it."""

    CLEAN = 0
    REAL_BUT_HARD = 1
    NOT_A_REACTION = 2


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
    blockers that dominate cost.  Known axes are finite and non-negative; ordinal ranks are integral.
    Cash compares only within matching ``currency`` and ``unit`` labels; ``region`` is descriptive metadata."""

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
    #: unmet REAL-BUT-HARD constraints (safety / identity / legal / equipment / unobtainable catalyst / section-11
    #: bench exclusion) -- a genuine reaction that is merely costly or out of reach.  A non-empty tuple dominates cost
    #: (section 10.4 G6) and puts the route in disposition tier :attr:`Disposition.REAL_BUT_HARD`.
    hard_blockers: tuple[str, ...] = ()
    #: unmet Problem-A reaction-TYPE FICTIONS -- at least one step matches no attested reaction class, so the route is
    #: no real synthesis at all.  The DISTINCT disposition channel (kept disjoint from ``hard_blockers`` so the two
    #: KINDS no longer flatten together): a non-empty tuple dominates cost AND ranks the route in the WORST tier
    #: :attr:`Disposition.NOT_A_REACTION`, strictly below any real-but-hard route (:class:`Disposition`).
    fiction_blockers: tuple[str, ...] = ()
    currency: str = ""
    unit: str = ""
    region: str = ""

    def __post_init__(self) -> None:
        for chan in ("hard_blockers", "fiction_blockers"):
            v = getattr(self, chan)
            if type(v) is not tuple or any(not isinstance(b, str) or not b.strip() for b in v):
                raise TypeError(f"{chan} must be a tuple of non-empty reason strings")
        for label in ("currency", "unit", "region"):
            if not isinstance(getattr(self, label), str):
                raise TypeError(f"{label} must be a string")
        for axis in (*_AXES, "cash_floor"):
            v = getattr(self, axis)
            if v is None:
                continue
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v != v:
                raise TypeError(f"{axis} must be a real number or None (UNKNOWN), not {v!r}")
            try:
                finite = math.isfinite(v)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError(f"{axis} must be finite; use None for UNKNOWN")
            if v < 0:
                raise ValueError(f"{axis} cannot be negative")
            if axis in ("access_difficulty", "evidence_tier_rank") and v != int(v):
                raise ValueError(f"{axis} must be an integral, non-negative rank")
        if self.cash_floor is not None and self.cash is not None:
            raise ValueError("cash_floor and cash are mutually exclusive: a KNOWN cash carries no separate floor")

    @property
    def is_hard_blocked(self) -> bool:
        """A REAL-BUT-HARD blocker is present (catalyst/section-11/safety/...).  NOT fiction -- see
        :attr:`is_fiction_blocked` for the distinct Problem-A channel and :attr:`is_blocked` for either."""
        return bool(self.hard_blockers)

    @property
    def is_fiction_blocked(self) -> bool:
        """A Problem-A reaction-TYPE fiction blocker is present (a step matches no attested reaction class)."""
        return bool(self.fiction_blockers)

    @property
    def is_blocked(self) -> bool:
        """Blocked on EITHER channel -- the route is off the clean tier for any reason."""
        return bool(self.hard_blockers) or bool(self.fiction_blockers)

    @property
    def disposition(self) -> Disposition:
        """The route's disposition tier -- the WORST over its blockers: a fiction voids the whole route
        (:attr:`Disposition.NOT_A_REACTION`), else a real-but-hard constraint makes it
        :attr:`Disposition.REAL_BUT_HARD`, else :attr:`Disposition.CLEAN`.  Derived, never stored, so it cannot
        drift from the reason tuples.  This is the ordinal :func:`dominates` uses for the G6 disposition rule."""
        if self.fiction_blockers:
            return Disposition.NOT_A_REACTION
        if self.hard_blockers:
            return Disposition.REAL_BUT_HARD
        return Disposition.CLEAN

    def known_axes(self) -> dict[str, float]:
        return {a: float(getattr(self, a)) for a in _AXES if getattr(self, a) is not None}

    def has_cost_signal(self) -> bool:
        """Any real affordability signal: a known point axis, an honest cash floor, or a blocker of EITHER kind.  A
        floor-only vector (cash UNKNOWN but bounded BELOW) carries real signal and must NOT be gated off as blank,
        and so does a fiction-demoted route (its NOT_A_REACTION disposition IS the affordability answer)."""
        return bool(self.known_axes()) or self.cash_floor is not None or self.is_blocked


def dominates(a: CostVector, b: CostVector) -> bool:
    """Does ``a`` Pareto-dominate ``b``?  True iff ``a`` is no worse than ``b`` on every comparable axis and strictly
    better on at least one -- with two honest section-10.4 rules layered on:

    * DISPOSITION DOMINATES COST (G6, 3-valued): the disposition tier (:class:`Disposition` -- CLEAN <
      REAL_BUT_HARD < NOT_A_REACTION) decides FIRST and overrides the cost axes entirely.  A better-disposed option
      beats a worse-disposed one at any price; a worse-disposed option never dominates a better-disposed one; only
      when BOTH share a tier do the numeric axes decide.  This generalizes the original 2-valued hard-blocker rule
      (clean vs blocked) to three tiers, so "real reaction, needs an industrial catalyst" (REAL_BUT_HARD) now
      STRICTLY dominates "not a real reaction at all" (NOT_A_REACTION) -- the partial order the shared ``hard_blockers``
      tuple used to flatten.  It takes PRECEDENCE over the UNKNOWN rule below: a better-disposed vector dominates a
      worse-disposed one even when its cost axes are entirely UNKNOWN (section 10.4 -- a hard constraint, or a
      not-a-reaction verdict, is never traded for cost; the "all-unknown b is dominated by nothing" clause holds only
      among vectors of EQUAL disposition tier).
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
      it cannot guarantee (two floors, or a floor above a known, are incomparable on cash).  Cash is ALSO compared
      only WITHIN one currency and denomination: the ``unit`` label ("metric ton" per package vs "mol product" for a
      quantity-weighted floor) is load-bearing here -- a different denomination is incomparable, like an unknown axis
      (red-team fold: without this, $/package and $/mol were compared as if commensurable).  Different ``currency``
      labels are likewise incomparable: no foreign-exchange conversion is supplied by this module.
    """
    # disposition rule first -- the tier overrides the cost axes entirely (disposition dominates cost, G6, 3-valued).
    # The better-disposed (lower tier) dominates; the worse-disposed never dominates; only an EQUAL tier falls through
    # to the numeric axes.  This subsumes the original 2-valued clean/blocked rule and adds the strict
    # REAL_BUT_HARD > NOT_A_REACTION order that un-flattens the two blocker kinds.
    if a.disposition != b.disposition:
        return a.disposition < b.disposition
    # same disposition tier.  a must be no-worse on every axis b constrains, strictly better on at least one.
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
        # a can claim no-worse-on-cash ONLY if its cash is bounded AND in the SAME denomination as b's (the ``unit``
        # field: "metric ton" for a per-unit package price vs "mol product" for a quantity-weighted floor).  Comparing
        # $/package against $/mol-of-product as if commensurable would be a false ordering (red-team fold: dominance
        # treated ``unit`` as decorative and let $5/ton "dominate" $10/mol) -- so a different denomination is treated
        # exactly like an UNKNOWN cash: a cannot claim no-worse, so it cannot dominate on this axis.
        if a_cash is None or (a.currency, a.unit) != (b.currency, b.unit):
            return False  # UNKNOWN or incommensurable cash -> cannot claim no-worse
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
_ACCESS_ORDINAL = {"grocery": 0, "pharmacy": 1, "hardware": 2, "pool_garden": 3, "industrial": 4}


def _weighted_cash_floor(leaf_requirements: "list") -> "tuple[float | None, str]":
    """TERM-MAT: the QUANTITY-WEIGHTED cash floor of a route's per-leaf stoichiometric requirement, or ``(None, "")``.

    ``leaf_requirements`` is the per-leaf ``(molecule, moles)`` shopping requirement (``dag_shopping_requirement``'s
    output).  Each priced+mass-convertible leaf contributes ``moles * price_per_mol`` (the molar-mass + price-unit
    layer, :mod:`smartchem.experiment.units`); the sum over those leaves is a PROVEN LOWER BOUND on the route's
    material cash for one unit of product -- and it is ALWAYS a floor, never an exact total, for three compounding
    reasons, each of which can only push the true cost UP: (1) the mol requirement is a conserved 100%-yield lower
    bound; (2) a priced commodity is UNKNOWN-assay (you need at least the pure-reagent mass of an impure commodity);
    (3) an unpriced or non-mass-denominated leaf is simply omitted (a partial basket).  A leaf priced in a currency
    different from the others yields ``(None, "")`` -- currencies are never summed.  ``(None, "")`` when NO leaf is
    priced-and-convertible (the honest UNKNOWN)."""
    from .commodity_pricing import cost_observation_for
    from .units import price_per_mol

    total = 0.0
    currency = ""
    any_priced = False
    for mol, moles in leaf_requirements:
        # a moles requirement is a finite non-negative amount; an invalid one is not an honest requirement (a shopping
        # requirement is always net>0, so this never fires on the wire) -> skip it rather than build a negative floor
        # that would crash the CostVector (its cash_floor rejects negatives) -- the guard molar_mass already has on count.
        if not isinstance(moles, (int, float)) or isinstance(moles, bool) or moles != moles or moles < 0:
            continue
        try:
            finite_moles = math.isfinite(moles)
        except OverflowError:
            finite_moles = False
        if not finite_moles:
            continue
        obs = cost_observation_for(mol)
        if obs is None:
            continue
        per_mol = price_per_mol(obs, mol.formula)  # `formula` is a property returning a dict
        if per_mol is None:
            continue  # priced but not mass-convertible (e.g. a per-litre price) -> omit (a partial basket -> floor)
        value, cur = per_mol
        if not any_priced:
            currency = cur
        elif cur != currency:
            return None, ""  # incommensurable currencies -> refuse to sum, no honest floor
        total += value * float(moles)
        any_priced = True
    if not any_priced:
        return None, ""
    return total, currency


def basket_cost_vector(
    commodity_molecules: "list", *, material_quantity: "float | None" = None,
    weighted_cash_leaves: "list | None" = None, hard_blockers: tuple[str, ...] = (),
    fiction_blockers: tuple[str, ...] = (),
) -> CostVector:
    """Aggregate the commodity leaves a route/basket buys (each a :class:`~smartchem.category.Molecule`) into ONE
    section-10.4 vector -- the shape the route-level frontier will build from a route's terminal reagents.

    Cash is the SUM of the leaves' 2a prices (a basket costs the sum of its parts), KNOWN only if EVERY leaf is
    priced AND all agree on currency+unit -- one unpriced or incommensurable leaf drops cash to UNKNOWN rather than
    under-count the basket (fail to UNKNOWN, never fabricate a cheaper total; section 10.4).  Access difficulty is the
    WORST (hardest) leaf -- a basket is only as obtainable as its least-obtainable part -- and is UNKNOWN if any leaf
    is not a known commodity (never assume easy).  A ``hard_blockers`` (real-but-hard) or ``fiction_blockers``
    (Problem-A not-a-reaction) reason passed in blocks the whole basket on its respective disposition channel; the two
    are kept DISJOINT so the frontier can rank a real-but-hard route strictly above a not-a-reaction one
    (:class:`Disposition`).  Unmodeled axes stay UNKNOWN.  An EMPTY basket has no known cash/access (all UNKNOWN) --
    a route buying nothing is not "free".

    TERM-MAT (``weighted_cash_leaves``): the per-unit package cash above prices ONE unit of each leaf, blind to HOW
    MUCH the route actually consumes -- a coarse proxy the frontier compares across routes by package COUNT, not real
    outlay.  When the caller supplies the route's per-leaf ``(molecule, moles)`` stoichiometric requirement, this
    computes the QUANTITY-WEIGHTED cash instead (:func:`_weighted_cash_floor`: moles x price_per_mol via the molar-mass
    + price-unit layer) and uses it as the ``cash_floor`` -- a physically-meaningful lower bound on the material cash
    for one unit of product, in place of the per-unit package proxy.  Its role is honest and NARROW (red-team fold, not
    an overclaim): it is an INFORMATIONAL per-product cost floor, NOT a cash-axis dominance discriminator.  It is ALWAYS
    a floor (100%-yield mol bound x UNKNOWN-assay commodity x possibly-partial coverage -- all push the true cost only
    UP), and by the necessary-dominance rule a floor never dominates on cash (two floors are incomparable, and its
    "mol product" denomination is incomparable with the per-unit "metric ton"), so it contributes NO cash ranking --
    material-burden RANKING is the ``material_quantity`` (mol) axis's job; this is the $-annotation.  It enters the
    vector with ``unit="mol product"`` and OVERRIDES the per-unit cash only when computable (>=1 priced,
    mass-convertible leaf); otherwise the per-unit path stands.  ``weighted_cash_leaves=None`` (the default) leaves the
    per-unit behaviour byte-identical -- zero churn for every existing caller.
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

    # TERM-MAT: prefer the QUANTITY-WEIGHTED cash floor when the per-leaf stoichiometric requirement is supplied and
    # yields one -- the physically-meaningful per-mol-of-product material cash, where the per-unit sum above is a
    # package-count proxy.  It is ALWAYS a floor (an INFORMATIONAL lower bound, not a dominance signal -- see the
    # docstring), so it replaces BOTH the exact cash and the per-unit floor (mutually exclusive with cash on the
    # CostVector) and is labelled "mol product".  When it is not computable (no priced, mass-convertible leaf, or mixed
    # currencies) the per-unit path above stands unchanged.
    weighted_unit = ""
    if weighted_cash_leaves is not None:
        w_floor, w_currency = _weighted_cash_floor(weighted_cash_leaves)
        if w_floor is not None:
            cash = None
            cash_floor = w_floor
            currency = w_currency
            weighted_unit = "mol product"

    access_difficulty = worst_access if all_known_commodity else None
    has_cash = cash is not None or cash_floor is not None
    # TERM-MAT / quantity axis: ``material_quantity`` (optional) is the route's total external-leaf MOLES per unit of
    # final product (a conserved 100%-efficiency LOWER BOUND from ``dag_shopping_requirement``), a stoichiometric
    # material-burden weight the per-unit cash axis is blind to -- and, being a POINT value, the axis that actually
    # RANKS material burden between routes (the quantity-weighted cash floor above is a $-annotation, not a ranker).
    # The molar-mass + price-unit layer that turns these moles into the weighted cash floor is now built
    # (:mod:`smartchem.experiment.units`, wired via ``weighted_cash_leaves``); the mol count remains the honest axis.
    return CostVector(
        cash=cash,
        cash_floor=cash_floor,
        access_difficulty=access_difficulty,
        material_quantity=material_quantity,
        hard_blockers=tuple(hard_blockers),
        fiction_blockers=tuple(fiction_blockers),
        currency=currency if has_cash else "",
        # the cash denominator label: "mol product" when a quantity-weighted floor replaced the per-unit sum, else
        # the per-leaf package unit (e.g. "metric ton").  Cash comparison requires matching currency and unit.
        unit=(weighted_unit or unit) if has_cash else "",
    )


# -- the route-level frontier entry (COST-VEC-01 wiring shape) -----------------------------------------------------

# v1alpha2 (COST-VEC-01-coupled): the flattened CostVector gained a ``cash_floor`` axis (an honest partial-basket
# lower bound), so the entry's serialized shape changed -- one bump per shape change.
# v1alpha3 (DISPOSITION-01): the CostVector gained a distinct ``fiction_blockers`` channel (Problem-A not-a-reaction),
# split out of the shared ``hard_blockers`` so the disposition tiers no longer flatten -- another shape change.
AFFORDABILITY_FRONTIER_ENTRY_SCHEMA = "smartchem.experiment/affordability-frontier-entry-v1alpha3"


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
