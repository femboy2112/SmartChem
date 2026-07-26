"""
The energy of a photon: the first oracle in this package that is not about chemistry.

WHY THIS EXISTS
---------------
``Molecule.quantum()`` has been a legal, composable token since the categorical layer was
written, and ``carries_unmodelled_physics`` names its gap explicitly -- "zero atoms -- a
radiated quantum, whose energy is h*nu -- and appears in none of these models." Every
bundled oracle therefore declines it, correctly, because none of them models radiation.

This oracle closes that gap for the vacuum case. It is deliberately the smallest possible
step into the electromagnetic vertical: no solver, no new types, no interface change. What
it demonstrates is that the oracle contract was in fact domain-neutral all along -- an
``EnergyOracle`` that knows nothing about atoms satisfies it unchanged.

WHY THE WAVELENGTH IS A PROPERTY OF THE ORACLE, NOT OF THE CALL
---------------------------------------------------------------
The obvious design is to read the frequency off the token: ``Molecule.quantum("532nm")``,
parsed. ``Molecule.quantum``'s own docstring forbids exactly that -- "Frequency, momentum,
polarization, medium and dispersion therefore belong in a future typed state/port model
rather than being inferred from this placeholder." ``state`` is an opaque label by
construction, and inferring physics from an opaque label is how a typo becomes a number.

So the wavelength is constructor state, which is not a workaround but the house pattern:
``PySCFOracle("CCSD(T)", "cc-pVTZ")`` does not take its method per call either. Method and
basis define *which oracle this is*; the molecule is the subject. A photon oracle is the
same shape -- ``PhotonOracle(532.0)`` is the 532 nm oracle, and a wavelength sweep is a
sweep over oracle instances.

The honest cost of that choice: one instance prices one wavelength. A properly typed port
model would carry frequency on the wire and let a single oracle price all of them. This
does not pretend to be that, and the limitation is enforced rather than papered over --
see the label check in ``energy``.

ON CLAIMING ZERO UNCERTAINTY
----------------------------
``nominal_accuracy_ev`` is 0.0 for an exactly-specified wavelength, and that is a real
claim rather than an omission. Since the 2019 SI redefinition, h, c and e are all exact by
definition, so hc/e is exact arithmetic on exact constants -- there is no measured input to
carry an error bar and no model whose approximation could be benchmarked. Every other
oracle here reports a fitted or benchmarked error because it is approximating a many-body
problem. This one is applying a definition.

What that zero does NOT cover, and what the caller owns:

  * **Vacuum only.** In a medium the energy of a mode at a given free-space wavelength is
    unchanged, but the *wavelength in the medium* is not, and dispersion makes the
    relationship frequency-dependent. Construct from frequency if the medium matters.
  * **The wavelength's own precision.** If lambda is known to finite precision, pass
    ``uncertainty_nm`` and it propagates: dE/E = -dlambda/lambda.
  * **That the token means what you think.** Nothing in the type system checks that a
    given ``Molecule.quantum`` denotes this oracle's photon rather than another one. That
    is the gap the label check narrows and only a typed port model can close.
"""

from __future__ import annotations

from ..category import Molecule
from .base import BaseOracle, Estimate

#: Planck constant times the speed of light, in eV*nm.
#:
#: Exact. h = 6.62607015e-34 J*s, c = 299792458 m/s and e = 1.602176634e-19 C are all
#: defined values in SI since the 2019 redefinition, so hc/e carries no experimental
#: uncertainty and this digit string is arithmetic, not a measurement.
#:
#: Note ``legacy.py`` uses a bare ``1240.0`` for the same quantity inside the quarantined
#: heuristic. That is 0.013% high and unsourced. It is left alone deliberately -- the
#: legacy module is frozen -- but nothing new should copy it.
HC_EV_NM = 1239.8419843320025

#: Planck constant in eV*s, for the frequency-domain constructor. Exact, same reasoning.
H_EV_S = 4.135667696923859e-15


class PhotonOracle(BaseOracle):
    """
    Prices one photon: the free-space quantum of the wavelength this instance was built for.

    Values a chargeless, atomless token and declines everything else -- which is every
    species the chemistry oracles handle. The two sets do not overlap, which is the point:
    this oracle extends coverage rather than competing for it.
    """

    def __init__(self, wavelength_nm: float, uncertainty_nm: float = 0.0) -> None:
        if not wavelength_nm > 0.0:
            # Zero or negative wavelength is not a photon this or any oracle can price,
            # and a division would hand back an infinity dressed as an energy.
            raise ValueError(f"wavelength_nm must be positive, got {wavelength_nm!r}")
        if uncertainty_nm < 0.0:
            raise ValueError(f"uncertainty_nm must be nonnegative, got {uncertainty_nm!r}")
        self.wavelength_nm = float(wavelength_nm)
        self.uncertainty_nm = float(uncertainty_nm)
        self.name = f"photon/{self.wavelength_nm:g}nm"
        #: The canonical label this oracle answers to, besides the unlabelled quantum.
        self.label = f"{self.wavelength_nm:g}nm"
        value = HC_EV_NM / self.wavelength_nm
        # dE/E = -dlambda/lambda; the sign is irrelevant to a magnitude.
        self.nominal_accuracy_ev = value * (self.uncertainty_nm / self.wavelength_nm)

    @classmethod
    def from_frequency_hz(cls, frequency_hz: float, uncertainty_hz: float = 0.0) -> "PhotonOracle":
        """
        Build from frequency -- ``E = h*nu`` -- which is the physically primary form.

        Frequency is what is conserved as a wave crosses into a medium; wavelength is not.
        A caller who cares about anything but vacuum should start here.
        """
        if not frequency_hz > 0.0:
            raise ValueError(f"frequency_hz must be positive, got {frequency_hz!r}")
        if uncertainty_hz < 0.0:
            raise ValueError(f"uncertainty_hz must be nonnegative, got {uncertainty_hz!r}")
        wavelength_nm = HC_EV_NM / (H_EV_S * frequency_hz)
        # Fractional uncertainty is preserved under the reciprocal to first order.
        uncertainty_nm = wavelength_nm * (uncertainty_hz / frequency_hz)
        return cls(wavelength_nm, uncertainty_nm)

    @property
    def frequency_hz(self) -> float:
        return HC_EV_NM / (H_EV_S * self.wavelength_nm)

    def energy(self, molecule: Molecule) -> Estimate | None:
        if molecule.atoms:
            # Matter. Not this oracle's business, and pricing it would be an invention.
            return None
        if molecule.charge != 0:
            # A charged zero-atom carrier is how this package spells an electron. An
            # electron has rest mass and is not a quantum of radiation; hc/lambda is simply
            # the wrong physics for it. Declining is the only honest answer here.
            return None
        if molecule.state and molecule.state != self.label:
            # An opaque label this oracle did not issue. It may well denote this very
            # photon, but nothing in the type system says so, and answering anyway would
            # price whatever the caller meant at whatever this instance happens to hold --
            # a wrong number produced by a naming coincidence. Decline instead.
            #
            # This is the enforced form of the design limitation in the module docstring:
            # one instance, one wavelength, and no guessing across labels.
            return None
        return Estimate(
            value_ev=HC_EV_NM / self.wavelength_nm,
            uncertainty_ev=self.nominal_accuracy_ev,
            method=self.name,
            notes=(
                f"E = hc/lambda at lambda = {self.wavelength_nm:g} nm "
                f"(nu = {self.frequency_hz:.6e} Hz), free space; "
                "hc exact by SI definition, no medium or dispersion modelled"
            ),
        )
