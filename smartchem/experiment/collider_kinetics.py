"""DOW-BROMINE-KINETICS-01 (item 3b): a modified-Arrhenius, collider-dependent dissociation model.

The DOW-bromine litmus asks us to *predict Br2's decomposition*.  ROUND 26 answered the THERMODYNAMIC half
(``Br2 -> 2 Br*`` is endergonic at 298 K, ΔG = +161.65 kJ/mol, so Br2 is stable at the bench).  This module
answers the KINETIC half from the recovered primary, and it is a genuinely DIFFERENT rate law than the
first-order survival seed (:mod:`smartchem.experiment.stability_horizon`) consumes:

  Warshay, *Shock-Tube Investigation of Bromine Dissociation Rates* (NASA TN D-3502, 1966), shock-tube
  initial dissociation in Ar/Ne/Kr, measured 1200-1900 K:
      Br2 + M <=> 2 Br + M        -d[Br2]/dt = kD * [Br2] * [M]        (BIMOLECULAR, collider M)
      kD = A * T^(1/2) * exp(-Ea/RT)                                   (MODIFIED Arrhenius, √T prefactor)

Why a NEW sibling and not the first-order seed
-----------------------------------------------
:class:`~smartchem.data.kinetics.KineticRef` is plain Arrhenius (``k = A·exp(-Ea/RT)``) and its
``is_first_order`` is literally ``a_units == "s^-1"`` -- Warshay's √T *bimolecular* form cannot be represented
there, which is exactly the boundary the sourcing recon drew ("do not add these values to the existing
first-order seed or rename their units", ``docs/research/SOURCING_RECON_2026-09-07.md``).  So this is a
sibling model, keyed on canonical structure like every other rate, that:

  * reproduces kD at the sourced shock-tube point (:func:`dissociation_rate`) -- a TRANSCRIPTION
    self-consistency check that REUSES the fitted dataset (kD(1825 K, Ar) ~= 1.574e6 vs Warshay's Table I
    observed 1.48e6, +6.3%); it is NOT an independent validation the way N2O5's ~7% instrument check is;
  * turns the bimolecular coefficient into a *conditional derived* pseudo-first-order coefficient at a
    DECLARED collider concentration (:func:`pseudo_first_order_k`, ``k' = kD·[M]``) -- [M] is REQUIRED and
    never defaulted, because a fabricated collider concentration is a fabricated rate;
  * reads a duration-aware survival verdict off ``exp(-k' t)`` (:func:`collider_survival`).

The anti-fabrication discipline (section 10.4), stated loudly
------------------------------------------------------------
This is the whole point of the round.  Three guards keep a shock-tube fit from fabricating a bench verdict:

1. **SURVIVES is the only CERTIFIED verdict; everything else DEFERS to UNKNOWN.**  Warshay's fit is the
   FORWARD, initial-rate, reverse-omitted channel.  The irreversible ``exp(-k' t)`` therefore *undercounts*
   the true surviving fraction -- the reverse recombination ``2 Br + M -> Br2 + M`` (which Warshay dropped
   for the dilute initial-rate measurement) can only ADD Br2 back, never remove more.  So the forward
   fraction is a rigorous LOWER BOUND on the true fraction:  ``true_fraction >= forward_fraction``.  A
   SURVIVES read (forward fraction >= 99%) is thus SOUND -- the truth is at least that intact.  But a
   sub-SURVIVES forward fraction does NOT certify destruction: the omitted reverse may cap the net loss at
   the equilibrium fraction, so a ``DEGRADES`` off the irreversible model would be a fabricated refutation
   the reverse reaction would overturn.  We refuse it -- sub-SURVIVES fails CLOSED to ``UNKNOWN`` (the
   forward tendency is disclosed as a magnitude, never as a verdict).  This module NEVER emits ``DEGRADES``
   or ``MARGINAL``; the sourced RATE (:func:`dissociation_rate`) is where the fast-at-shock-T fact lives,
   reverse-free because a RATE is an initial-rate statement.

2. **SURVIVES is certified only IN or BELOW the fit window; an extrapolated refutation never occurs.**  A read
   inside the sourced 1200-1900 K window is DERIVED; outside it is a flagged PREDICTED extrapolation.  A
   SURVIVES read BELOW the window is provably conservative (colder is monotonically slower in BOTH the
   ``exp(-Ea/RT)`` factor and the ``T^n`` prefactor for ``n >= 0``, and the modelled channel is already ~14
   orders from the flip at 298 K), so the bench SURVIVES is sound as a labelled PREDICTED reading.  ABOVE the
   window that conservatism is unproven -- ``kD`` grows with T, so the forward fraction is no longer a
   guaranteed lower bound -- so an above-window SURVIVES-band read DEFERS to UNKNOWN rather than emit a
   below-window warrant it cannot stand behind.  An extrapolated *refutation* is the forbidden direction and
   cannot occur by construction (guard 1 already refuses every DEGRADES).

3. **Scope: a W3 tendency of the MODELLED collisional channel, never "Br2 is stable" unconditionally.**  A
   SURVIVES verdict says the thermal collisional dissociation channel leaves Br2 essentially intact over the
   hold; it says NOTHING about photochemical, catalysed, or aqueous fates, which are unmodelled.  The bench
   verdict is cross-referenced to the INDEPENDENT ROUND-26 thermodynamic bearing (calorimetric CODATA
   ΔfH°/S°, a different source family and a different physical quantity -- an equilibrium state function, not
   a barrier), which agrees Br2 is favoured at 298 K.  The two bearings are genuinely disjoint (the kinetic
   Ea = 131.8 kJ/mol is the empirical collisional barrier, BELOW the 192.83 kJ/mol Br-Br bond enthalpy -- the
   known collisional-Ea-below-D0 feature; ΔG is NOT derived from Ea).  Their only coupling is motivational
   (both serve the desire to unblock DOW), mitigated because SURVIVES is also the boring null ("colder ->
   nothing happens"), not a surprising narrative-confirming result.

Not built this round (tracked, not silent): the live wire-in to E1's duration gate
(:func:`~smartchem.experiment.composability._apply_duration_gate`) -- the gate's contract is first-order
s^-1 single-reactant and carries no collider concentration, and Br2's bench verdict is SURVIVES (verdict-inert
in a tightening-only gate), so wiring it would be machinery for a caller that does not exist (see ROADMAP).
The Ne/Kr collider fits are recorded in the contract doc but not seeded (no caller needs a collider comparison
this round).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..contracts import Digestible, canonical_digest
from ..smiles import parse_smiles
# Reuse -- never re-declare -- the interpretive band policy and the gas constant, so this sibling can never
# drift to a different SURVIVES edge or a different R than the first-order primitive (the shared-term hazard).
from .stability_horizon import (
    GAS_CONSTANT_J_PER_MOL_K,
    SurvivalVerdict,
    survival_verdict,
)

__all__ = [
    "COLLIDER_KINETICS_SCHEMA",
    "ColliderDissociationRef",
    "ColliderSurvival",
    "SEED_COLLIDER_REFS",
    "dissociation_rate",
    "pseudo_first_order_k",
    "collider_dissociation_for",
    "collider_survival",
]

COLLIDER_KINETICS_SCHEMA = "smartchem.experiment.collider_kinetics/collider-dissociation-v1"

_LN10 = math.log(10.0)
#: 10**x overflows a float near x ~ 308; past this the surviving fraction is 0 with no inf (mirrors
#: :func:`~smartchem.experiment.stability_horizon.surviving_fraction`).
_FLOAT_LOG_LIMIT = 300.0


@dataclass(frozen=True)
class ColliderDissociationRef(Digestible):
    """One SOURCED modified-Arrhenius, collider-dependent dissociation fit ``kD = A·T^n·exp(-Ea/RT)``.

    The rate is bimolecular (``-d[reactant]/dt = kD·[reactant]·[M]``), so ``kD`` carries second-order units
    (``L mol^-1 s^-1``) and becomes a pseudo-first-order coefficient only after multiplication by a DECLARED
    collider concentration (:func:`pseudo_first_order_k`).  Fields:

    * ``reactant_smiles`` / ``product_smiles`` -- the dissociation ``Br2 <=> 2 Br``, named by SMILES; the
      engine matches on CANONICAL STRUCTURE (never formula), direction-specific;
    * ``collider`` -- the third body M the fit was measured with, a plain element LABEL (``"Ar"``/``"Ne"``/
      ``"Kr"``), NOT a SMILES: a monatomic inert third body has no structure or isomer to canonicalise, and the
      noble-gas symbols are not even parseable, but the label still guards a caller from silently applying Ar's
      ``(A, Ea)`` under a neon concentration (it is matched by string identity);
    * ``log10_a`` -- base-10 log of the pre-exponential ``A`` (stored in log space for overflow honesty, as
      :class:`~smartchem.data.kinetics.KineticRef` does); ``t_exponent`` -- the modified-Arrhenius temperature
      exponent ``n`` (½ for Warshay's collision-theory prefactor); ``ea_kj_per_mol`` -- the activation energy;
    * ``a_units`` -- the order-dependent unit of ``A`` (``L mol^-1 s^-1 K^-n``), carried for honesty;
    * ``temperature_range_k`` -- the ``(lo, hi)`` window the fit is stated valid over (inside: DERIVED;
      outside: a flagged PREDICTED extrapolation);
    * ``provenance`` -- author + year + the measured basis (REQUIRED).
    """

    reactant_smiles: str
    product_smiles: str
    collider: str
    name: str
    ea_kj_per_mol: float
    log10_a: float
    t_exponent: float
    a_units: str
    temperature_range_k: tuple[float, float]
    provenance: str

    def __post_init__(self) -> None:
        for field_name in ("reactant_smiles", "product_smiles", "collider", "name", "a_units",
                           "provenance"):
            v = getattr(self, field_name)
            if not isinstance(v, str) or not v:
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("ea_kj_per_mol", "log10_a", "t_exponent"):
            v = getattr(self, field_name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
            if not math.isfinite(float(v)):
                raise ValueError(f"{field_name} must be finite")
        if self.ea_kj_per_mol < 0:
            raise ValueError("activation energy Ea cannot be negative")
        if self.t_exponent < 0:
            # the below-window conservative-extrapolation warrant (colder -> slower -> more survival) assumes
            # kD is monotone increasing in T, which holds only for a non-negative T^n prefactor (evil-morty).
            raise ValueError("t_exponent must be >= 0 (the below-window survival warrant assumes colder is slower)")
        rng = self.temperature_range_k
        if type(rng) is not tuple or len(rng) != 2:
            raise TypeError("temperature_range_k must be a (lo, hi) tuple")
        lo, hi = rng
        for v in rng:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError("temperature_range_k bounds must be real numbers")
        if not (0 < lo <= hi):
            raise ValueError("temperature_range_k must satisfy 0 < lo <= hi (kelvin)")


def dissociation_rate(ref: ColliderDissociationRef, temperature_k: float) -> float:
    """The bimolecular dissociation coefficient ``kD = A·T^n·exp(-Ea/RT)`` (L mol^-1 s^-1) at ``temperature_k``.

    Computed in log10 space so an enormous ``A`` never overflows a float into a fabricated ``inf`` (the same
    overflow honesty the first-order engine uses).  This is a SOURCED RATE -- reverse-free, since a coefficient
    is an initial-rate statement -- and is where the "fast at shock T" fact lives.  Raises on a non-positive
    temperature."""
    if temperature_k <= 0:
        raise ValueError("temperature must be a positive absolute temperature (K)")
    log10_kd = (
        ref.log10_a
        + ref.t_exponent * math.log10(temperature_k)
        - (ref.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * temperature_k * _LN10)
    )
    if log10_kd >= _FLOAT_LOG_LIMIT:
        return math.inf
    return 10.0 ** log10_kd


def pseudo_first_order_k(
    ref: ColliderDissociationRef, temperature_k: float, collider_mol_per_l: float
) -> float:
    """The CONDITIONAL DERIVED pseudo-first-order coefficient ``k' = kD·[M]`` (s^-1) at a DECLARED collider
    concentration.

    Warshay's law is bimolecular; a first-order survival ``exp(-k' t)`` exists only at a fixed collider
    concentration, so ``collider_mol_per_l`` is REQUIRED and must be finite and strictly positive -- a
    fabricated or absent [M] would fabricate the rate.  Returns ``inf`` if the product overflows a float."""
    if collider_mol_per_l is None or isinstance(collider_mol_per_l, bool) or not isinstance(
        collider_mol_per_l, (int, float)
    ):
        raise TypeError("collider_mol_per_l must be a real number (mol/L)")
    if not math.isfinite(float(collider_mol_per_l)) or collider_mol_per_l <= 0:
        raise ValueError("collider_mol_per_l must be a finite, strictly positive concentration (mol/L)")
    kd = dissociation_rate(ref, temperature_k)
    if kd == math.inf:
        return math.inf
    return kd * float(collider_mol_per_l)


def collider_dissociation_for(
    molecule, *, collider: str, refs: "tuple[ColliderDissociationRef, ...]" = None
) -> "ColliderDissociationRef | None":
    """The SOURCED collider-dissociation fit for ``molecule`` under collider label ``collider``, or ``None``.

    Matches a record whose REACTANT is ``molecule`` (the species being dissociated -- direction-specific, on
    CANONICAL STRUCTURE, never formula, so a same-formula isomer never inherits this fit) AND whose collider
    LABEL matches (string identity, whitespace-stripped -- a monatomic third body has no structure to
    canonicalise).  ``refs`` defaults to the Ar-only seed."""
    if refs is None:
        refs = SEED_COLLIDER_REFS
    target = canonical_digest(molecule.canonical())
    want = collider.strip()
    for rec in refs:
        if canonical_digest(parse_smiles(rec.reactant_smiles).canonical()) != target:
            continue
        if rec.collider.strip() == want:
            return rec
    return None


@dataclass(frozen=True)
class ColliderSurvival(Digestible):
    """A duration-aware survival reading for a collider-dissociating species over a hold at a declared [M].

    ``forward_fraction`` is the FORWARD-channel surviving fraction ``exp(-k' t)`` -- a rigorous LOWER BOUND on
    the true (reverse-inclusive) fraction, disclosed as a magnitude.  ``verdict`` is SURVIVES iff that lower
    bound already clears the SURVIVES band, else UNKNOWN (this model never certifies DEGRADES/MARGINAL -- see
    the module docstring).  ``grade`` is DERIVED inside the sourced window, PREDICTED when extrapolated."""

    schema: str
    compound_digest: str
    collider: str
    temperature_k: float
    hold_seconds: float
    collider_mol_per_l: float
    forward_fraction: float
    verdict: SurvivalVerdict
    grade: str
    reason: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if self.schema != COLLIDER_KINETICS_SCHEMA:
            raise ValueError(f"schema must be {COLLIDER_KINETICS_SCHEMA!r}")
        if not (0.0 <= self.forward_fraction <= 1.0):
            raise ValueError("forward_fraction must lie in [0, 1]")
        if self.verdict not in (SurvivalVerdict.SURVIVES, SurvivalVerdict.UNKNOWN):
            raise ValueError("collider survival certifies only SURVIVES or UNKNOWN (never DEGRADES/MARGINAL)")


def _forward_fraction(k_prime: float, hold_seconds: float) -> float:
    """``exp(-k' t)``, robust to an astronomically large ``k'·t`` (returns 0.0, never ``inf``)."""
    if k_prime == math.inf:
        return 0.0
    if k_prime <= 0.0:
        return 1.0
    log10_kt = math.log10(k_prime) + math.log10(hold_seconds)
    if log10_kt >= _FLOAT_LOG_LIMIT:
        return 0.0
    return math.exp(-(10.0 ** log10_kt))


def collider_survival(
    ref: ColliderDissociationRef,
    temperature_k: float,
    hold_seconds: float,
    collider_mol_per_l: float,
) -> ColliderSurvival:
    """The duration-aware survival verdict for ``ref``'s reactant held ``hold_seconds`` at ``temperature_k``
    under a DECLARED collider concentration.

    Certifies SURVIVES iff the FORWARD-channel surviving fraction ``exp(-k' t)`` already clears the SURVIVES
    band -- sound because that forward fraction is a rigorous LOWER bound on the true (reverse-inclusive)
    fraction (the omitted reverse recombination only adds the species back).  Every sub-SURVIVES case fails
    CLOSED to UNKNOWN: the omitted reverse may cap the net loss at equilibrium (so a DEGRADES would be a
    fabricated refutation), and an out-of-window sub-SURVIVES is additionally an extrapolated refutation --
    both forbidden.  This model therefore NEVER returns DEGRADES or MARGINAL; the sourced RATE
    (:func:`dissociation_rate`) carries the fast-at-shock-T fact.  Raises on a non-positive temperature/hold;
    a non-finite or non-positive [M] raises in :func:`pseudo_first_order_k`."""
    if temperature_k <= 0 or not math.isfinite(temperature_k):
        raise ValueError("temperature must be a finite, positive absolute temperature (K)")
    if hold_seconds <= 0 or not math.isfinite(hold_seconds):
        raise ValueError("hold_seconds must be a finite, positive duration")
    k_prime = pseudo_first_order_k(ref, temperature_k, collider_mol_per_l)
    fraction = _forward_fraction(k_prime, float(hold_seconds))
    band = survival_verdict(fraction)                        # the SHARED band policy (>= 99% is SURVIVES)
    lo, hi = ref.temperature_range_k
    in_window = lo <= temperature_k <= hi
    below_window = temperature_k < lo
    grade = "DERIVED" if in_window else "PREDICTED"
    compound = canonical_digest(parse_smiles(ref.reactant_smiles).canonical())
    collider = ref.collider

    # SURVIVES is CERTIFIED only where the forward-fraction lower bound is PROVEN conservative: in-window
    # (DERIVED, sourced) or BELOW-window (colder is monotone-slower for n >= 0, so kD only shrinks -> the
    # forward fraction only grows -> the SURVIVES bound holds).  ABOVE the window that argument is unproven
    # (kD grows), so an above-window SURVIVES-band read DEFERS rather than emit a below-window warrant it
    # cannot stand behind (evil-morty Finding 1 + the above-window residual).
    if band is SurvivalVerdict.SURVIVES and (in_window or below_window):
        verdict = SurvivalVerdict.SURVIVES
        warrant = (
            f"a LOWER bound on the true surviving fraction (the omitted reverse recombination only adds "
            f"'{ref.reactant_smiles}' back, so the reversible truth is at least this intact)"
        )
        if in_window:
            reason = (
                f"SURVIVES: {fraction * 100:.4f}% of the collisional dissociation channel remains over a "
                f"{hold_seconds:g} s hold at {temperature_k:.1f} K, [M] = {collider_mol_per_l:g} mol/L, by "
                f"exp(-k' t), k' = kD·[M], kD = A·T^n·exp(-Ea/RT) over the SOURCED fit of '{ref.name}' "
                f"(Ea = {ref.ea_kj_per_mol:.1f} kJ/mol, n = {ref.t_exponent:g}) -- {warrant}; a W3 tendency of "
                f"the modelled collisional channel, NOT an unconditional stability claim (photochemical/"
                f"catalysed/aqueous fates are unmodelled)"
            )
        else:                                                # below the window: the conservative extrapolation
            reason = (
                f"SURVIVES [PREDICTED: {temperature_k:.0f} K is BELOW the sourced fit window {lo:.0f}-"
                f"{hi:.0f} K]: {fraction * 100:.4f}% of the collisional dissociation channel remains over a "
                f"{hold_seconds:g} s hold, [M] = {collider_mol_per_l:g} mol/L. The extrapolation is "
                f"CONSERVATIVE in the survival direction -- colder is monotonically slower in both exp(-Ea/RT) "
                f"and the T^n prefactor (n = {ref.t_exponent:g} >= 0), the fitted Ea = {ref.ea_kj_per_mol:.1f} "
                f"kJ/mol is BELOW the Br-Br bond enthalpy so the true low-T barrier is even higher (slower "
                f"still), and the channel is already far from the SURVIVES edge at the window floor -- and is a "
                f"LOWER bound ({warrant}). Cross-referenced to the INDEPENDENT ROUND-26 thermodynamic bearing "
                f"(Br2 -> 2 Br*, ΔG298 = +161.65 kJ/mol, calorimetric CODATA -- a different source family and a "
                f"different physical quantity): both agree Br2 is stable at the bench. A W3 tendency of the "
                f"modelled collisional channel, NOT an unconditional stability claim."
            )
    else:
        verdict = SurvivalVerdict.UNKNOWN
        if band is SurvivalVerdict.SURVIVES:                 # necessarily ABOVE the window (in/below certified)
            reason = (
                f"UNKNOWN: at {temperature_k:.0f} K (ABOVE the sourced fit window {lo:.0f}-{hi:.0f} K) the "
                f"forward channel leaves {fraction * 100:.4f}% intact -- but the conservative-extrapolation "
                f"argument is proven only IN or BELOW the window (colder is slower); ABOVE it kD grows and the "
                f"model does not vouch for the lower bound, so a SURVIVES read is NOT certified here and DEFERS. "
                f"The sourced RATE is available via dissociation_rate()."
            )
        elif in_window:
            reason = (
                f"UNKNOWN: the FORWARD collisional channel alone would leave only {fraction * 100:.4f}% over a "
                f"{hold_seconds:g} s hold at {temperature_k:.1f} K -- but Warshay's initial-rate fit OMITS the "
                f"reverse recombination, which caps the net loss at the equilibrium fraction, so net "
                f"destruction is NOT certified by this irreversible model (a DEGRADES here would be a fabricated "
                f"refutation the reverse reaction overturns). The sourced RATE is available via "
                f"dissociation_rate(); this survival verdict DEFERS."
            )
        else:
            reason = (
                f"UNKNOWN: at {temperature_k:.0f} K (outside the sourced fit window {lo:.0f}-{hi:.0f} K) the "
                f"forward channel would leave only {fraction * 100:.4f}% -- a refutation resting on an "
                f"EXTRAPOLATED rate, which is fabrication (a wrong refutation), so it fails CLOSED to UNKNOWN. "
                f"Only a SURVIVES read (provably conservative in or below the window) is certified."
            )
    return ColliderSurvival(
        COLLIDER_KINETICS_SCHEMA, compound, collider, float(temperature_k), float(hold_seconds),
        float(collider_mol_per_l), fraction, verdict, grade, reason,
    )


#: The SOURCED seed -- Ar only (the collider Warshay used for the representative Table I point).  Ne/Kr fits
#: are recorded in docs/research/DOW_BROMINE_KINETICS_CONTRACT_v0.1.md but not seeded: no caller needs a
#: collider comparison this round.  Injectable per call via ``collider_dissociation_for(refs=...)``, NOT a
#: whitelist.  Filled from FETCHED, cited values (the NASA receipts), never recalled from memory.
SEED_COLLIDER_REFS: tuple[ColliderDissociationRef, ...] = (
    ColliderDissociationRef(
        reactant_smiles="BrBr",
        product_smiles="[Br]",
        collider="Ar",
        name="Br2 dissociation (Warshay, Ar collider)",
        ea_kj_per_mol=131.796,   # 31.5 kcal/mol * 4.184 kJ/kcal
        log10_a=8.338456,        # log10(2.18e8)
        t_exponent=0.5,          # Warshay's √T collision-theory prefactor
        a_units="L mol^-1 s^-1 K^-1/2",
        temperature_range_k=(1200.0, 1900.0),
        provenance=(
            "Br2 + M <=> 2 Br + M, forward dissociation, INITIAL-RATE (reverse recombination and Br2-as-"
            "collider omitted for the dilute shock-tube measurement). kD = A*T^(1/2)*exp(-Ea/RT), L mol^-1 s^-1. "
            "Ar collider: A = 2.18e8 L mol^-1 s^-1 K^-1/2 (log10 A = 8.338), Ea = 31.5 kcal/mol = 131.80 kJ/mol. "
            "Marvin Warshay, 'Shock-Tube Investigation of Bromine Dissociation Rates in Presence of Argon, "
            "Neon, and Krypton', NASA TN D-3502, July 1966, eqs (8)-(10) p.12; gas mixtures 1% Br2 / 99% noble "
            "gas, incident shocks, 1200-1900 K. Ne (A = 1.82e8, Ea = 31.3 kcal/mol) and Kr (A = 4.32e8, Ea = "
            "33.6 kcal/mol) are recorded in the contract doc, not seeded. FETCHED (SHA-256 "
            "c29f0b03e3cf7aec8da1ec9d9ca7055a5e067255f89b158cf44200c2243afdd7; see "
            "docs/research/SOURCING_RECON_2026-09-07.md). Representative Table I point (1825 K): observed kD = "
            "1.48e6; this fit gives 1.574e6 -- a TRANSCRIPTION self-consistency check that REUSES the fitted "
            "dataset, NOT an independent validation. The empirical collisional Ea (131.8) is BELOW the Br-Br "
            "bond enthalpy (192.83 kJ/mol, ROUND-26 CODATA) -- the known collisional-Ea-below-D0 feature."
        ),
    ),
)
