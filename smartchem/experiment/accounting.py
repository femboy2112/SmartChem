"""E3 -- the physical-accounting attach layer: heat, temperature, pressure, time, solvent -- each labelled.

E3 attaches the per-step physical numbers a chemist reads off a procedure, under the oracle's discipline:
each is either reproduced from a SOURCE / an ESTABLISHED validated model, or emitted as a LOUD ``UNKNOWN``.
Nothing is invented.

* **Heat** is the one genuinely-broad established computation the repo owns: the reaction enthalpy at 0 K by
  Hess's law over SOURCED formation enthalpies (:func:`smartchem.data.reference.reaction_energy_ev`,
  NIST/CCCBDB).  It is ``KNOWN_SOURCED`` when every species is in the reference, and ``UNKNOWN`` the moment
  one is not -- so a drug-sized target with no tabulated dfH is honestly ``UNKNOWN``, not guessed.
* **Temperature / pressure / time / medium / catalysts** are read off the step's DECLARED
  :class:`~smartchem.conditions.ConditionEnvelope`.  A declared field (which already required a sourced
  provenance to exist) is ``KNOWN_SOURCED``; an undeclared field is ``UNKNOWN``.  The envelope machinery
  guarantees conditions are sourced or absent, never fabricated.

The boundary E3 does NOT cross (this is the wall)
-------------------------------------------------
E3 never computes a **rate**, a **time-to-completion**, or a **yield** below the E2 ceiling.  Those need a
kinetics/feasibility model the repo does not have and would have to invent -- the forbidden "new physics".
The 100%-efficiency ceiling (E2, ``CONSERVATION``) is the only outcome number, and it is an upper bound, not
a prediction.  E3 stops at *sourced state* and *established thermochemistry*.

Universal: any step flows through; unsourced fields simply come back ``UNKNOWN``.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category import Molecule
from ..conditions import ConditionEnvelope, Interval
from ..contracts import Digestible
from ..data.reference import KJ_PER_EV
from ..decompiler_review import molecule_dfh_0k_range_kj
from .bucket import Bucket, Quantity, unknown
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "StepAccounting",
    "PhysicalAccounting",
    "account_step",
    "account_route",
]


def _interval_quantity(interval: Interval | None, envelope: ConditionEnvelope, label: str) -> Quantity:
    """A KNOWN_SOURCED quantity from a declared interval, or a loud UNKNOWN if the field is undeclared."""
    if interval is None:
        return unknown(label, "", f"no sourced {label} declared for this step")
    return Quantity(
        label=label,
        value=f"[{interval.lo}, {interval.hi}]",
        unit=interval.unit,
        bucket=Bucket.KNOWN_SOURCED,
        provenance=envelope.provenance or "declared condition envelope",
    )


def _heat_quantity(step: ExperimentStep) -> Quantity:
    """Reaction enthalpy at 0 K (eV) by Hess's law over sourced dfH, or UNKNOWN if any species is missing.

    Resolution is ISOMER-CORRECT and complete: each species goes through the review layer's
    :func:`molecule_dfh_0k_range_kj`, which reads the 0 K formation enthalpy off the *structure* over the
    full reference (so it never confuses a molecule with a same-composition isomer, and correctly excludes
    a species whose only value is a 298 K number -- paracetamol -- from a 0 K balance).  A species known
    only at the formula level contributes a dfH INTERVAL, so the reaction enthalpy is reported as an
    interval too, never a fake exact number.  ONE species without any sourced 0 K dfH makes the whole
    enthalpy ``UNKNOWN`` -- a partial sum would be a fabricated number wearing a real label.
    """
    def side_range(mols: tuple[Molecule, ...]) -> tuple[float, float] | None:
        lo = hi = 0.0
        for m in mols:
            rng = molecule_dfh_0k_range_kj(m)
            if rng is None:
                return None
            lo += rng[0]
            hi += rng[1]
        return (lo, hi)

    products_kj = side_range(step.products)
    reactants_kj = side_range(step.reactants)
    if products_kj is None or reactants_kj is None:
        return unknown("reaction enthalpy (0 K)", "eV",
                       "at least one species has no sourced 0 K formation enthalpy (isomer-resolved)")
    # interval subtraction: dH in [ prod_lo - react_hi , prod_hi - react_lo ]
    lo_ev = (products_kj[0] - reactants_kj[1]) / KJ_PER_EV
    hi_ev = (products_kj[1] - reactants_kj[0]) / KJ_PER_EV
    exact = abs(hi_ev - lo_ev) < 1e-9
    provenance = (
        "Hess's law over NIST/CCCBDB formation enthalpies (established model; 0 K, gas-phase, ideal; "
        "isomer-resolved) -- a screening estimate, negative = exothermic"
    )
    if not exact:
        provenance += "; interval spans a formula-level isomer ambiguity"
    return Quantity(
        label="reaction enthalpy (0 K)",
        value=round(lo_ev, 6) if exact else f"[{round(lo_ev, 6)}, {round(hi_ev, 6)}]",
        unit="eV",
        bucket=Bucket.KNOWN_SOURCED,
        provenance=provenance,
    )


@dataclass(frozen=True)
class StepAccounting(Digestible):
    """The bucket-labelled physical accounting for one step: heat + the sourced-or-unknown conditions."""

    step: ExperimentStep
    heat: Quantity
    temperature: Quantity
    pressure: Quantity
    duration: Quantity
    medium: Quantity
    catalysts: Quantity

    def quantities(self) -> tuple[Quantity, ...]:
        return (self.heat, self.temperature, self.pressure, self.duration, self.medium, self.catalysts)

    @property
    def is_exothermic(self) -> bool | None:
        """True/False from the sourced heat sign, or ``None`` when it is UNKNOWN or the sign is ambiguous.

        A formula-level isomer ambiguity makes the enthalpy an interval; if that interval straddles zero
        the sign is genuinely undetermined, so this returns ``None`` rather than guessing a direction.
        """
        if self.heat.bucket is Bucket.UNKNOWN:
            return None
        value = self.heat.value
        if isinstance(value, str):  # an interval "[lo, hi]"
            lo, hi = (float(x) for x in value.strip("[]").split(","))
            if hi < 0:
                return True
            if lo > 0:
                return False
            return None  # straddles zero: sign undetermined
        return value < 0

    def render(self) -> str:
        lines = [f"accounting for {self.step.target!r}:"]
        lines.extend(f"    {q.render()}" for q in self.quantities())
        return "\n".join(lines)


@dataclass(frozen=True)
class PhysicalAccounting(Digestible):
    """The per-step physical accounting for a whole route."""

    route: ExperimentRoute
    per_step: tuple[StepAccounting, ...]

    def __post_init__(self) -> None:
        if len(self.per_step) != len(self.route.steps):
            raise ValueError("per_step must have one StepAccounting per route step")

    def render(self) -> str:
        return "\n".join(sa.render() for sa in self.per_step)


def account_step(step: ExperimentStep) -> StepAccounting:
    """Attach the sourced/established physical accounting to one step (UNKNOWN where unsourced)."""
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    env = step.envelope
    medium = (
        Quantity("medium", env.medium, "", Bucket.KNOWN_SOURCED, env.provenance or "declared envelope")
        if env.medium else unknown("medium", "", "no sourced solvent/medium declared")
    )
    catalysts = (
        Quantity("catalysts", list(env.catalysts), "", Bucket.KNOWN_SOURCED,
                 env.provenance or "declared envelope")
        if env.catalysts else unknown("catalysts", "", "no sourced catalyst declared")
    )
    return StepAccounting(
        step=step,
        heat=_heat_quantity(step),
        temperature=_interval_quantity(env.temperature, env, "temperature"),
        pressure=_interval_quantity(env.pressure, env, "pressure"),
        duration=_interval_quantity(env.duration, env, "duration"),
        medium=medium,
        catalysts=catalysts,
    )


def account_route(route: ExperimentRoute) -> PhysicalAccounting:
    """Attach the physical accounting to every step of a route."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    return PhysicalAccounting(route, tuple(account_step(s) for s in route.steps))
