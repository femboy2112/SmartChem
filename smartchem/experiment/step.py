"""E0 -- the certified experiment step, and the linear route it composes into.

An :class:`ExperimentStep` is one bench operation: a multiset of ``reactants`` (precursors plus any
ancillary ``reagents`` -- solvent, acetylating agent, ...) turning into a multiset of ``products`` (the
step's ``target`` plus byproducts), under a declared or unknown :class:`~smartchem.conditions.ConditionEnvelope`.

The certificate, and why it is not self-certifying
--------------------------------------------------
The constructor re-derives conservation the repo's way -- it builds a real
:class:`~smartchem.category.Reaction` from the reactant and product multisets, and *that* constructor
re-derives atom-count and charge balance by dictionary accumulation over ``Molecule.formula``, code that
shares nothing with this module.  A step that does not conserve raises there and is refused here.  It is
the same "check by an independent path" discipline the whole package runs on.

Universal by construction
-------------------------
Nothing here is keyed to a known compound.  Any :class:`~smartchem.category.Molecule` -- parsed from any
SMILES the front door accepts, or built by hand -- flows through E0.  The conditions are *carried*, not
looked up: the caller (a chemist, a literature reference, or a later rung) declares a sourced envelope, or
leaves it :meth:`~smartchem.conditions.ConditionEnvelope.unknown`.  A synthesis route is, precisely, a
decompiler descent read backwards, so :meth:`ExperimentStep.from_capped_scission` turns any structural
cleavage the engine derived into its assembly (synthesis) step -- consuming an existing path object rather
than re-deriving chemistry.

W3 unchanged: a certified step says the *bookkeeping* of that transformation is exact and states the
*declared* conditions.  It says nothing about whether the reaction proceeds, at what rate, or in what
yield.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..category import Config, ConservationError, Molecule, Reaction
from ..conditions import ConditionEnvelope
from ..contracts import Digestible

__all__ = [
    "STEP_SCHEMA",
    "ROUTE_SCHEMA",
    "StepError",
    "ExperimentStep",
    "ExperimentRoute",
]

STEP_SCHEMA = "smartchem.experiment/step-v1"
ROUTE_SCHEMA = "smartchem.experiment/route-v1"


class StepError(ValueError):
    """A proposed experiment step or route is not an admissible, conserving object."""


def _ident(molecule: Molecule) -> str:
    """A presentation-invariant identity for a molecule (``asgiven:`` fallback for symmetric rings).

    CANON-KEKULE-01 (item 3): resonance-canonical, shared with routes/dag/compilation_ir via
    :func:`~smartchem.smiles.resonance_identity`, so conservation and stoichiometry key on the SAME identity the
    search matches on -- and two Kekulé forms of one intermediate cancel across a reaction instead of spuriously
    imbalancing it."""
    from ..smiles import resonance_identity
    return resonance_identity(molecule)


def _multiset_subset(sub: tuple[Molecule, ...], whole: tuple[Molecule, ...]) -> bool:
    """Is ``sub`` a multiset subset of ``whole`` by canonical molecular identity?"""
    have = Counter(_ident(m) for m in whole)
    need = Counter(_ident(m) for m in sub)
    return all(have.get(k, 0) >= v for k, v in need.items())


@dataclass(frozen=True)
class ExperimentStep(Digestible):
    """One certified, conserving bench step under a declared/unknown condition envelope.

    * ``reactants`` -- the LHS multiset (precursors and any ancillary reagents), repeats carrying stoich;
    * ``products`` -- the RHS multiset (the ``target`` plus any byproducts);
    * ``target`` -- the compound this step makes; it must appear among ``products``;
    * ``reagents`` -- a multiset SUBSET of ``reactants`` flagged ancillary (a solvent, an acetylating
      agent), for the drafter's "in the presence of ..." rendering; it is not load-bearing for
      conservation, only for legibility;
    * ``envelope`` -- the sourced conditions, or :meth:`~smartchem.conditions.ConditionEnvelope.unknown`.
    """

    schema_version: str
    target: Molecule
    reactants: tuple[Molecule, ...]
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    envelope: ConditionEnvelope

    def __post_init__(self) -> None:
        if self.schema_version != STEP_SCHEMA:
            raise StepError(f"schema_version must be exactly {STEP_SCHEMA!r}")
        if type(self.target) is not Molecule:
            raise StepError("target must be a smartchem.category.Molecule")
        for name in ("reactants", "products", "reagents"):
            seq = getattr(self, name)
            if type(seq) is not tuple or any(type(m) is not Molecule for m in seq):
                raise StepError(f"{name} must be a tuple of Molecule values")
        if not self.reactants:
            raise StepError("a step must consume at least one reactant")
        if not self.products:
            raise StepError("a step must produce at least one product")
        if type(self.envelope) is not ConditionEnvelope:
            raise StepError("envelope must be a ConditionEnvelope")
        # the target is actually made by this step
        if _ident(self.target) not in {_ident(p) for p in self.products}:
            raise StepError("the step's target must appear among its products")
        # reagents are a genuine ancillary subset of the reactants
        if not _multiset_subset(self.reagents, self.reactants):
            raise StepError("reagents must be a multiset subset of reactants (they are consumed reactants)")
        # -- the independent conservation certificate: build a real Reaction and let it re-check ------
        try:
            Reaction(Config.of(*self.reactants), Config.of(*self.products), name="experiment-step")
        except ConservationError as clash:
            raise StepError(
                f"step does not conserve mass/charge and is refused: {clash}"
            ) from clash
        except NotImplementedError as clash:  # canonicalisation budget refused a pathological graph
            raise StepError(
                f"a species in this step could not be canonicalised for the conservation check: {clash}"
            ) from clash

    # -- reads -------------------------------------------------------------------------------------
    @property
    def precursors(self) -> tuple[Molecule, ...]:
        """The reactants that are NOT flagged ancillary reagents (the main inputs)."""
        remaining = list(self.reactants)
        for reagent in self.reagents:
            for i, m in enumerate(remaining):
                if _ident(m) == _ident(reagent):
                    del remaining[i]
                    break
        return tuple(remaining)

    @property
    def byproducts(self) -> tuple[Molecule, ...]:
        """The products other than one instance of the target."""
        remaining = list(self.products)
        for i, m in enumerate(remaining):
            if _ident(m) == _ident(self.target):
                del remaining[i]
                break
        return tuple(remaining)

    @property
    def is_declared(self) -> bool:
        """True iff this step carries a sourced (non-unknown) condition envelope."""
        return self.envelope.is_declared

    def consumes(self, molecule: Molecule) -> bool:
        """Does this step consume ``molecule`` as a reactant (by canonical identity)?"""
        key = _ident(molecule)
        return any(_ident(m) == key for m in self.reactants)

    def net_consumes(self, molecule: Molecule) -> bool:
        """Does the balanced equation consume a positive net amount of ``molecule``?"""
        key = _ident(molecule)
        lhs = sum(_ident(m) == key for m in self.reactants)
        rhs = sum(_ident(m) == key for m in self.products)
        return lhs > rhs

    def equation(self) -> str:
        """A human-readable balanced equation for this step."""
        lhs = " + ".join(repr(m) for m in self.reactants)
        rhs = " + ".join(repr(m) for m in self.products)
        return f"{lhs} -> {rhs}"

    def __repr__(self) -> str:
        return f"ExperimentStep({self.equation()})"

    # -- construction from existing path objects (a descent read backwards = an assembly) ----------
    @classmethod
    def assembling(
        cls,
        target: Molecule,
        reactants: tuple[Molecule, ...],
        products: tuple[Molecule, ...],
        *,
        reagents: tuple[Molecule, ...] = (),
        envelope: ConditionEnvelope | None = None,
    ) -> "ExperimentStep":
        """Build a step directly from its multisets (the general, structure-agnostic constructor)."""
        return cls(
            STEP_SCHEMA,
            target,
            tuple(reactants),
            tuple(products),
            tuple(reagents),
            envelope if envelope is not None else ConditionEnvelope.unknown(),
        )

    @classmethod
    def from_transform(
        cls,
        transform,
        *,
        envelope: ConditionEnvelope | None = None,
        reagents: tuple[Molecule, ...] = (),
    ) -> "ExperimentStep":
        """The SYNTHESIS step that assembles ``transform.reactant`` -- ANY structural transform read backwards.

        The family-agnostic step builder (TRANSFORM-PROVIDER-01): a transform is a *decomposition*
        ``reactant + reagents -> products`` (a capped scission, a bond-order edit, ...) exposing the uniform
        interface (``reactant`` / ``reagents`` / ``products``).  Its reverse assembles ``reactant``: the
        decomposition's ``products`` are the synthesis *precursors*, and its ``reactant`` plus consumed
        ``reagents`` are the synthesis *products* (the target plus liberated byproducts).  Conservation is
        inherited (a balanced reaction is balanced either way) and independently re-checked by the
        :class:`ExperimentStep` certificate, so a second transform family composes here with no bespoke branch.

        ``reagents`` optionally flags which of the synthesis precursors are ancillary (e.g. the acetylating agent)
        for the drafter; it defaults to none and never affects conservation.
        """
        synth_reactants = tuple(transform.products)
        synth_products = (transform.reactant,) + tuple(transform.reagents)
        return cls.assembling(
            transform.reactant,
            synth_reactants,
            synth_products,
            reagents=reagents,
            envelope=envelope,
        )

    @classmethod
    def from_capped_scission(
        cls,
        capped,
        *,
        envelope: ConditionEnvelope | None = None,
        reagents: tuple[Molecule, ...] = (),
    ) -> "ExperimentStep":
        """The capped-scission-named entry to :meth:`from_transform` (a :class:`CappedScission` satisfies the
        uniform transform interface).  Kept for callers that name the family explicitly."""
        return cls.from_transform(capped, envelope=envelope, reagents=reagents)


@dataclass(frozen=True)
class ExperimentRoute(Digestible):
    """A linear ordered sequence of steps: each step's target is the intermediate the next step consumes.

    The route makes :attr:`final_target` (the last step's target).  The linearity invariant -- step ``k``'s
    target appears among step ``k+1``'s reactants -- is what makes the E1 transitions well defined: the
    thing carried across the transition between two steps is the earlier step's target.  A single-step
    route is legal (it makes its target in one operation and has no transitions to check).
    """

    schema_version: str
    steps: tuple[ExperimentStep, ...]

    def __post_init__(self) -> None:
        if self.schema_version != ROUTE_SCHEMA:
            raise StepError(f"schema_version must be exactly {ROUTE_SCHEMA!r}")
        if type(self.steps) is not tuple or not self.steps or any(
            type(s) is not ExperimentStep for s in self.steps
        ):
            raise StepError("a route must be a non-empty tuple of ExperimentStep values")
        for k in range(len(self.steps) - 1):
            carried = self.steps[k].target
            if not self.steps[k + 1].net_consumes(carried):
                raise StepError(
                    f"route is not linear: step {k}'s target {carried!r} is not net-consumed by step "
                    f"{k + 1} -- merely appearing unchanged on both sides would make it a spectator, not a "
                    f"carried synthesis intermediate. Order the steps so each intermediate feeds the next"
                )

    @property
    def final_target(self) -> Molecule:
        return self.steps[-1].target

    @property
    def intermediates(self) -> tuple[Molecule, ...]:
        """The carried-forward intermediates: the target of every step but the last."""
        return tuple(s.target for s in self.steps[:-1])

    @property
    def leaf_inputs(self) -> tuple[Molecule, ...]:
        """The purchased leaf reactants: every reactant produced by NO step in the route (COST-VEC-01).

        The route's steps produce their targets AND any byproducts; a reactant that is not among ANY step's PRODUCTS
        is an EXTERNAL input the route must source (buy) -- reagents and starting materials alike.  A species a step
        liberates as a byproduct and a later step re-consumes is NOT a purchased leaf (it is made internally), so
        ``produced`` is drawn from every step's ``products``, not merely the step targets -- otherwise a re-consumed
        byproduct (e.g. water in a condensation-then-hydrolysis chain) would be double-billed as a buy.  Deduplicated
        by canonical structure identity (the same ``_ident`` the linearity invariant uses), first-appearance order
        preserved.  This is the basket ``affordability.basket_cost_vector`` prices; note it is quantity-BLIND -- one
        equivalent of each DISTINCT leaf (a per-unit lower bound, never quantity-weighted -- a named TERM-MAT
        follow-on), never a fabricated multi-equivalent total.
        """
        produced = {_ident(p) for step in self.steps for p in step.products}
        leaves: list[Molecule] = []
        seen: set[str] = set()
        for step in self.steps:
            for reactant in step.reactants:
                key = _ident(reactant)
                if key in produced or key in seen:
                    continue
                seen.add(key)
                leaves.append(reactant)
        return tuple(leaves)

    @property
    def n_transitions(self) -> int:
        return len(self.steps) - 1

    def equation_lines(self) -> tuple[str, ...]:
        return tuple(f"step {k + 1}: {s.equation()}" for k, s in enumerate(self.steps))

    @classmethod
    def of(cls, *steps: ExperimentStep) -> "ExperimentRoute":
        return cls(ROUTE_SCHEMA, tuple(steps))

    def __repr__(self) -> str:
        return f"ExperimentRoute({' ; '.join(s.equation() for s in self.steps)})"
