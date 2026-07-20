"""
The energy oracle interface.

The structural machinery above this layer accepts any implementation of this protocol, from
a heuristic to CCSD(T)/CBS. Method choice is explicit in provenance, but accuracy is not a
single dial: coverage, bias and uncertainty calibration depend on species, state, geometry,
conditions and method, and must be measured in the intended domain.

The primitive is the energy of a SPECIES
----------------------------------------
``energy(molecule) -> Estimate`` returns an energy estimate for one encoded chemical
species (atoms, bond topology, charge and internal-state label). This encoding is not a full
microscopic state: geometry and thermodynamic environment may be absent or supplied by an
oracle-specific procedure.

It used to be ``estimate(symbols) -> D0``, the dissociation energy of an atom *pair*. That
choice quietly determined the whole design and was wrong in three ways at once:

* the energy of a configuration became a sum over *edges* -- bond additivity, which is a
  fiction for anything polyatomic;
* bond order could not be priced, since an atom pair carries no order;
* only species present in a geometry lookup table could be asked about at all, so
  polyatomic support was structurally blocked rather than merely unimplemented.

With a species as the primitive, all three dissolve. Dissociation energy becomes a derived
quantity (``E(free atoms) - E(molecule)``) rather than the thing the interface is built on.

The arbitrary-zero contract -- and why conservation is what makes it safe
------------------------------------------------------------------------
Every oracle may choose its own zero of energy. PySCF returns total electronic energies
(CO is about -3074 eV); the legacy heuristic works relative to free atoms (CO is about
-11 eV). Both conventions can be legal. Endpoint subtraction requires a consistent reference,
units, state convention and method across the species being compared.

The current reaction-energy API asks for

    dE(f : A -> B) = E(B) - E(A)

and ``smartchem.category`` guarantees that any morphism ``f`` has the same atoms and charge
in ``A`` and ``B``. Whatever per-atom offset an oracle's zero encodes therefore appears
identically on both sides and cancels exactly.

Conservation is the precondition that makes this difference invariant under permitted
per-element reference shifts. Open systems may compare different inventories when their
reservoirs and boundary flows are explicit; the present closed-reaction type does not model
those boundaries.

Two rules every oracle obeys
----------------------------
1. **Declining is allowed; inventing is not.** An oracle that cannot cover a species
   returns None. It must never return a fabricated number to look complete. The benchmark
   reports a conditional MAE but grants no accuracy-tier verdict when any case is refused,
   so ducking the hard cases cannot earn a stronger accuracy claim.

2. **Every returned value carries a method label and a nonnegative uncertainty field.** The
   type validates representation, not statistical calibration; consumers must not interpret
   that field as a confidence interval without a documented error model and validation data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real
from typing import Mapping, Protocol, runtime_checkable

from ..category import Molecule


@dataclass(frozen=True)
class Estimate:
    """
    A single energy prediction with everything needed to judge it.

    ``systematic_terms`` carries signed model sensitivities by stable source ID. Equal
    sources combine and may cancel. Unrelated sources remain separate even when their
    signed compatibility sum is zero; their absolute magnitudes therefore survive in the
    reporting floor. ``systematic_ev`` remains that compatible signed sum.

    Two things ride in this channel, and the field is named for the property they share
    rather than for either of them -- it was called ``extrapolation_ev`` while the first
    was the only occupant, and that name became a lie the moment the second arrived:

    * how far a basis-set extrapolation moved this number beyond its largest explicit
      basis;
    * the measured bias in a zero-point energy computed at a cheap tier -- HF harmonic
      frequencies run about 9% high, worth roughly +0.055 eV on water.

    Basis-extrapolation and ZPE sensitivities therefore remain distinct. Within one named
    source the *observed correction displacements* propagate algebraically. Equal
    displacements can cancel in a difference, but that algebra does not prove that the
    unknown residual errors cancel. The sum of absolute surviving terms is reported only
    as a sensitivity magnitude, not as a statistical or worst-case bound. The ZPE bias
    coefficient likewise still needs coefficient uncertainty and species-residual scatter.

    That distinction is load-bearing and was got wrong once. Treating the per-species
    correction as an independent random error and combining it in quadrature produced
    +/-1.4 eV reported scales on a method whose measured MAE was about 0.06 eV, because it
    discarded an algebraic cancellation of roughly 97%. Calling the correction a
    calibrated residual-error distribution would be wrong in the opposite direction.
    """
    value_ev: float
    uncertainty_ev: float
    method: str
    seconds: float = 0.0
    notes: str = ""
    #: signed model-correction displacement; propagates algebraically (see class docstring)
    systematic_ev: float = 0.0
    #: associative provenance. ``method`` remains the compact display form.
    methods: frozenset[str] | None = field(default=None, repr=False)
    #: named sources; equal sources combine, while unrelated source records stay separate.
    systematic_terms: tuple[tuple[str, float], ...] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        for field_name in ("value_ev", "uncertainty_ev", "seconds", "systematic_ev"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{field_name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{field_name} must be finite")
            object.__setattr__(self, field_name, float(value))
        if self.uncertainty_ev < 0:
            raise ValueError("uncertainty_ev must be non-negative")
        if self.seconds < 0:
            raise ValueError("seconds must be non-negative")
        if not isinstance(self.method, str) or not self.method:
            raise ValueError("method must be a non-empty provenance label")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")

        if isinstance(self.methods, str) or (
            self.methods is not None and not isinstance(self.methods, (set, frozenset))
        ):
            raise TypeError("methods must be a set or frozenset of provenance labels")
        methods_were_implicit = self.methods is None
        methods = frozenset({self.method}) if methods_were_implicit else frozenset(self.methods)
        if any(not isinstance(item, str) or not item for item in methods):
            raise ValueError("methods must contain non-empty strings")
        # The additive identity deliberately carries no method provenance, so adding it
        # cannot pollute a real estimate. Every other explicit set must retain the display
        # method rather than allowing provenance to disappear during combination.
        is_identity = (
            not methods
            and self.value_ev == self.uncertainty_ev == self.seconds == self.systematic_ev == 0.0
            and not self.systematic_terms
        )
        if not methods_were_implicit and not is_identity and not methods:
            raise ValueError("a non-identity estimate must retain at least one provenance method")
        object.__setattr__(self, "methods", methods)
        # ``method`` is a compact view of the semantic provenance set, not a second
        # independent identity field. Canonicalizing it gives the full dataclass one
        # additive zero and prevents summary/detail contradictions under reassociation.
        object.__setattr__(self, "method", "+".join(sorted(methods)) if methods else "exact")

        raw_terms = (
            ((f"legacy-systematic:{self.method}", float(self.systematic_ev)),)
            if self.systematic_terms is None and self.systematic_ev != 0.0
            else (() if self.systematic_terms is None else self.systematic_terms)
        )
        if not isinstance(raw_terms, tuple):
            raise TypeError("systematic_terms must be a tuple of (source, coefficient) pairs")
        combined: dict[str, float] = {}
        for item in raw_terms:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("systematic_terms must contain (source, coefficient) pairs")
            source, coefficient = item
            if not isinstance(source, str) or not source:
                raise ValueError("systematic source IDs must be non-empty strings")
            if isinstance(coefficient, bool) or not isinstance(coefficient, Real):
                raise TypeError("systematic coefficients must be real numbers")
            coefficient = float(coefficient)
            if not math.isfinite(coefficient):
                raise ValueError("systematic coefficients must be finite")
            updated = combined.get(source, 0.0) + coefficient
            if not math.isfinite(updated):
                raise ValueError(f"combined systematic coefficient for {source!r} is not finite")
            combined[source] = updated
        terms = tuple(sorted((source, value) for source, value in combined.items() if value))
        systematic_total = sum(value for _source, value in terms)
        systematic_magnitude = sum(abs(value) for _source, value in terms)
        if not math.isfinite(systematic_total) or not math.isfinite(systematic_magnitude):
            raise ValueError("combined systematic terms must have finite total and magnitude")
        object.__setattr__(self, "systematic_terms", terms)
        object.__setattr__(self, "systematic_ev", systematic_total)

    def __add__(self, other: "Estimate") -> "Estimate":
        """
        Combine values, quadrature uncertainties, and source-aware systematic terms.

        Quadrature assumes the scalar uncertainty channels are independent. Benchmark MAE
        is not automatically a standard deviation, and correlated model errors need the
        future covariance/affine representation described in the audit roadmap.

        The operation is associative at the provenance/source level. Floating-point
        addition and ``hypot`` retain ordinary numerical roundoff.
        """
        methods = (self.methods or frozenset()) | (other.methods or frozenset())
        systematic: dict[str, float] = {}
        for source, coefficient in (self.systematic_terms or ()) + (other.systematic_terms or ()):
            systematic[source] = systematic.get(source, 0.0) + coefficient
        return Estimate(
            value_ev=self.value_ev + other.value_ev,
            uncertainty_ev=math.hypot(self.uncertainty_ev, other.uncertainty_ev),
            method=("+".join(sorted(methods)) if methods else
                    (self.method if self.method == other.method else "exact")),
            seconds=self.seconds + other.seconds,
            notes="; ".join(n for n in (self.notes, other.notes) if n),
            systematic_ev=sum(systematic.values()),
            methods=methods,
            systematic_terms=tuple(systematic.items()),
        )

    def __neg__(self) -> "Estimate":
        """Negation keeps the random uncertainty and flips the systematic correction."""
        return Estimate(
            -self.value_ev,
            self.uncertainty_ev,
            self.method,
            self.seconds,
            self.notes,
            -self.systematic_ev,
            methods=self.methods,
            systematic_terms=tuple(
                (source, -coefficient)
                for source, coefficient in (self.systematic_terms or ())
            ),
        )

    def __sub__(self, other: "Estimate") -> "Estimate":
        return self + (-other)

    def scaled(self, coefficient: Real) -> "Estimate":
        """Scale one reused modeled quantity, preserving perfect self-correlation.

        If a configuration contains ``n`` copies of the same deterministic species energy,
        its epistemic/numerical uncertainty scales as ``|n|`` rather than ``sqrt(n)``: this
        is one modeled quantity reused, not ``n`` independent samples. ``seconds`` remains
        the cost of computing that quantity once.
        """
        if isinstance(coefficient, bool) or not isinstance(coefficient, Real):
            raise TypeError("estimate coefficient must be a real number")
        coefficient = float(coefficient)
        if not math.isfinite(coefficient):
            raise ValueError("estimate coefficient must be finite")
        if coefficient == 0.0:
            return Estimate.zero()
        return Estimate(
            value_ev=coefficient * self.value_ev,
            uncertainty_ev=abs(coefficient) * self.uncertainty_ev,
            method=self.method,
            seconds=self.seconds,
            notes=self.notes,
            systematic_ev=coefficient * self.systematic_ev,
            methods=self.methods,
            systematic_terms=tuple(
                (source, coefficient * value)
                for source, value in (self.systematic_terms or ())
            ),
        )

    def with_sensitivity_floor(self) -> "Estimate":
        """
        Apply a named model-sensitivity reporting floor.

        A model correction that survived cancellation is a real statement about how much
        this answer depends on the model. If an extrapolation still moves the final number
        by 0.13 eV after the atomic references cancel, displaying only a 0.06 eV tier-average
        scale would hide that observed sensitivity. This policy is conservative relative to
        ignoring the correction, not a mathematical or statistical bound on the unknown
        residual error; calibration and covariance are still required.

        Measured motivation: NaCl at cbs(TZ,QZ) lands 3.38 kcal/mol from experiment while
        plain cc-pVQZ lands 0.39 away -- the extrapolation degraded a good answer, and the
        old flat scalar hid that model sensitivity. One selected case still does not
        validate a coverage interval.
        """
        net = self.systematic_magnitude_ev
        if net <= self.uncertainty_ev:
            return self
        return Estimate(
            self.value_ev,
            net,
            self.method,
            self.seconds,
            (f"{self.notes}; widened to surviving named sensitivity magnitude "
             f"{net:.4f} eV").lstrip("; "),
            self.systematic_ev,
            methods=self.methods,
            systematic_terms=self.systematic_terms,
        )

    def with_honest_uncertainty(self) -> "Estimate":
        """Compatibility alias for :meth:`with_sensitivity_floor`.

        The old name is retained for callers, but should not be read as a coverage claim:
        neither a CBS displacement nor a harmonic-ZPE correction is automatically a bound
        on residual error.
        """
        return self.with_sensitivity_floor()

    @property
    def systematic_magnitude_ev(self) -> float:
        """Sum of surviving named correction magnitudes; not a residual-error bound."""
        return sum(abs(value) for _source, value in (self.systematic_terms or ()))

    @property
    def systematic_bound_ev(self) -> float:
        """Compatibility alias; the value is a sensitivity magnitude, not a proven bound."""
        return self.systematic_magnitude_ev

    @staticmethod
    def zero(method: str = "exact") -> "Estimate":
        """The additive identity -- the energy of the empty configuration."""
        return Estimate(
            0.0,
            0.0,
            method,
            0.0,
            "",
            methods=frozenset(),
            systematic_terms=(),
        )

    def __repr__(self) -> str:
        return f"{self.value_ev:.4f} +/- {self.uncertainty_ev:.4f} eV [{self.method}]"


def carries_unmodelled_physics(molecule: Molecule) -> bool:
    """
    True when a species carries structure that none of the oracles here can price.

    Two cases, both of which the category can express and no energy model in this
    repository can value:

    * a non-empty ``state`` -- an electronic excitation, a mode, an operating point;
    * zero atoms -- a radiated quantum, whose energy is ``h*nu`` and appears in none of
      these models.

    Both would otherwise pass straight through the free-atom branch and come back as
    ``0.0 +/- 0.0 eV``: a confident number with nothing behind it, and worse, one that is
    *coincidentally right* for an emission (the excitation energy the model does not know
    and the photon energy it also does not know cancel to zero). Right answer, no reason.

    Making the oracles decline instead is what keeps #22 an honest boundary rather than a
    lie. The structure being able to say ``Na(excited) -> Na + photon`` is the point; the
    energetics of that morphism are simply not implemented, and an oracle that says so is
    worth more than one that returns an unearned exact zero.
    """
    return bool(molecule.state) or not molecule.atoms


@runtime_checkable
class EnergyOracle(Protocol):
    """Anything that can price a chemical species."""

    name: str
    #: Validation summary in eV when finite, otherwise unvalidated. A finite benchmark MAE
    #: is population/protocol metadata, not a species-level distribution or confidence.
    nominal_accuracy_ev: float

    def energy(self, molecule: Molecule) -> Estimate | None:
        """
        Total energy of this species in eV, on this oracle's own consistent zero.

        Returns None if the oracle does not cover the species -- an element it lacks data
        for, a size it cannot handle, a geometry it has no way to obtain. Raise only on a
        genuine internal failure, never to signal "not supported".
        """
        ...


class BaseOracle:
    """
    Convenience base. Implement ``energy``; get the derived quantities for free.

    Subclasses must keep the arbitrary-zero contract: one consistent zero for every species
    a given instance prices.
    """

    name: str = "unnamed"
    nominal_accuracy_ev: float = float("inf")

    def calculation_spec(self) -> Mapping[str, object]:
        """
        Snapshot the instance state that may determine an ``energy`` result.

        Persistent caches fingerprint this value. The conservative default includes every
        instance attribute: mutable telemetry can cause an avoidable cache miss, but omitting
        an unknown result-driving field can return a silently wrong value. Production oracles
        should override this with a small immutable, complete calculation specification.
        """
        return dict(vars(self))

    def energy(self, molecule: Molecule) -> Estimate | None:  # pragma: no cover
        raise NotImplementedError

    # -- derived ------------------------------------------------------------------
    def atomization_energy(self, molecule: Molecule) -> Estimate | None:
        """
        ``E(free atoms) - E(molecule)``, positive = bound.

        Derived, not primitive. The exact thermochemical label depends on what ``energy``
        includes: the bundled PySCF oracle includes molecular ZPE and therefore yields an
        approximate ``D_0``; an electronic-only oracle would yield ``D_e``. The benchmark
        compares its bundled-oracle result with experimental ``D_0``.

        Note this is exactly the difference the arbitrary zero cancels in: both sides
        contain the same atoms, which is the same condition ``Reaction`` enforces.
        """
        if molecule.charge != 0:
            # Neutral free atoms are not a conserving reference for an ion. A charged
            # atomization energy needs explicit ionic fragments or an electron reservoir.
            return None
        whole = self.energy(molecule)
        if whole is None:
            return None
        from collections import Counter

        total = Estimate.zero(self.name)
        for symbol, count in Counter(molecule.atoms).items():
            part = self.energy(Molecule.atom(symbol))
            if part is None:
                return None
            total = total + part.scaled(count)
        # Named correction displacements propagate through the subtraction; apply the
        # sensitivity floor only afterwards. Equal displacements can cancel algebraically,
        # which does not prove cancellation of unknown residual model errors.
        return (total - whole).with_sensitivity_floor()

    def bond_energy(self, symbols: tuple[str, ...]) -> float | None:
        """
        Back-compatible helper: atomization energy of the default diatomic graph built
        from these atoms. New benchmark code constructs the reference graph explicitly so
        bond order is not lost.
        """
        if len(symbols) == 1:
            return 0.0
        if len(symbols) != 2:
            return None
        est = self.atomization_energy(Molecule.diatomic(*symbols))
        return None if est is None else est.value_ev
