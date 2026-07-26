#!/usr/bin/env python
"""
Does "a human life is an isotope with a half-life" compile? And if not, at what scale does it?

THE QUESTION
------------
``THE_COMPILER.md`` section V claims that a cross-scale specification can be checked by
intersecting the validity domains of the models its properties require, and that the three
outcomes -- empty, generous, and narrow-but-non-empty -- are all useful, the third one being
a research result rather than an error. Section V has an argument and no worked example.

This is the worked example, and the specification under test is not a chemical one:

    human:
      lifetime      : ~ isotope, half-life ~ the human lifespan
      first_decay   : death
      daughter      : the body, now unstable, decomposing

It is a good metaphor, which is exactly why it is worth compiling rather than admiring. The
question this script answers is not "is it apt" but "**on what set is it true**".

WHAT RADIOACTIVE DECAY ACTUALLY ASSERTS
---------------------------------------
The defining property is **memorylessness**. For a nucleus,

    P(decay in [t, t+dt] | survived to t) = lambda dt,   lambda constant

so the hazard is flat, survival is exponential, and **a nucleus has no age**. A one-second-old
and a billion-year-old nucleus have identical futures. Everything else people associate with
decay -- half-lives, chains, branching ratios -- is downstream of that one axiom.

WHERE THE ANALOGY COLLIDES
--------------------------
Human mortality is not memoryless and has been known not to be since Gompertz (1825): the
hazard rises roughly exponentially with age, doubling about every 8 years through adult life,
with Makeham's (1860) age-independent term added for the accidental and infectious background:

    h(t) = mu + B exp(theta t)

So the analogy fails on the model's *founding axiom*, not on a detail. Under section V that is
outcome 1, an empty intersection, and the collision is named: **memorylessness**.

WHY THAT IS NOT THE END OF IT -- THE CROSS-SCALE PART
-----------------------------------------------------
A nucleus has no internal state to degrade. An organism is a repair system, and reliability
theory (Gavrilov & Gavrilova) derives the Gompertz law from exactly that: a system with a
Poisson-distributed number of redundant elements, each failing at a CONSTANT hazard, has an
accelerating system-level hazard. Memorylessness at the part level produces
non-memorylessness at the whole level, purely from redundancy exhaustion.

Which means the metaphor is not wrong. **It is right one scale down.** A human is not an
isotope; a human is a Poisson-sized bucket of isotopes with a quorum rule. That relocation is
the output this script exists to produce, and it is the shape of result section V predicts:
the properties do not compile at the scale they were written at, and naming the scale at which
they do compile is the finding.

WHAT IS FITTED AND WHAT IS PREDICTED -- read this before quoting any number below
---------------------------------------------------------------------------------
Two parameters (lambda, m) are fitted to two facts (median lifespan, mortality-rate doubling
time). **A two-parameter fit to two facts predicts nothing**; those two outputs are
constrained by construction and are reported only to show the fit took. The parameters mu and
the quorum are inputs, not fits, and are labelled where they are set.

The three results that are NOT fitted, and are therefore the only ones worth anything here:

  1. the SHAPE -- that a constant-hazard part model yields an accelerating whole at all;
  2. the LATE PLATEAU -- the model forces h -> lambda + mu at extreme age, an asymptote
     nothing was fitted to;
  3. the MAKEHAM WINDOW -- an early age band where the constant term dominates and the
     hazard is genuinely flat, i.e. where the isotope metaphor is exactly true.

Result 3 is the point. The metaphor's validity domain turns out to be **disconnected**.

WHAT THIS IS NOT
----------------
This is not demography. It fits no life table, it is calibrated to two textbook summary
statistics, and it must not be cited as a mortality model or used to say anything about any
actual person. It is a compiler test case that happens to be about people, and the object
under test is the *metaphor*, not the population. The reported late-life plateau in humans is
contested in the literature and is deliberately not used as a calibration target here.

Exit codes: 0 the domain decomposition was computed, 2 the calibration failed to converge.
"""

from __future__ import annotations

import math
import sys

from scipy.optimize import brentq, fsolve

# ---------------------------------------------------------------------------
# INPUTS -- set, not fitted. Order-of-magnitude values, labelled as such.
# ---------------------------------------------------------------------------

#: The Makeham term: age-independent background hazard, per year. Accidents, violence, acute
#: infection -- the causes that do not care how old you are. Order of magnitude of young-adult
#: all-cause mortality in a developed country (~100 per 100,000 per year). NOT fitted.
MU_PER_YEAR = 1.0e-3

#: Calibration targets. Both are textbook summary statistics, not data this script fitted.
TARGET_MEDIAN_YEARS = 80.0    #: median survival
TARGET_MRDT_YEARS = 8.0       #: mortality-rate doubling time, evaluated at TARGET_MRDT_AT
TARGET_MRDT_AT = 70.0

#: The quorum rule: the system is alive while at least this many elements work. Set, not fitted.
QUORUM = 1


# ---------------------------------------------------------------------------
# THE TWO MODELS, exactly. No sampling anywhere.
# ---------------------------------------------------------------------------

def isotope_hazard(t: float, lam: float) -> float:
    """The thing being compared against. Flat, by definition. This is the whole model."""
    return lam


def _expected_working(t: float, lam: float, m: float) -> float:
    """Expected working elements at age t.

    Poisson thinning: if the initial count is Poisson(m) and each element survives
    independently with probability exp(-lam t), the survivors are Poisson(m exp(-lam t)).
    That closure is what makes this model exactly solvable rather than a simulation.
    """
    return m * math.exp(-lam * t)


def system_hazard(t: float, lam: float, m: float) -> float:
    """Hazard of a quorum-1 redundant system whose elements each fail memorylessly.

    P(all elements failed by t) = exp(-A) with A = m exp(-lam t), so S(t) = 1 - exp(-A) and
    h = -S'/S = lam A exp(-A) / (1 - exp(-A)).
    """
    a = _expected_working(t, lam, m)
    if a > 700.0:            # exp(-a) underflows; hazard is indistinguishable from zero
        return 0.0
    ea = math.exp(-a)
    denominator = 1.0 - ea
    if denominator <= 0.0:
        return 0.0
    return lam * a * ea / denominator


def total_hazard(t: float, lam: float, m: float) -> float:
    """Makeham's constant term plus the redundancy term. Competing risks add."""
    return MU_PER_YEAR + system_hazard(t, lam, m)


def survival(t: float, lam: float, m: float) -> float:
    """Survival to age t, conditioned on being alive at t=0."""
    a = _expected_working(t, lam, m)
    numerator = 1.0 - math.exp(-a) if a < 700.0 else 1.0
    denominator = 1.0 - math.exp(-m) if m < 700.0 else 1.0
    return (numerator / denominator) * math.exp(-MU_PER_YEAR * t)


def log_hazard_slope(t: float, lam: float, m: float, step: float = 1e-4) -> float:
    """theta(t) = d ln h / dt. Identically ZERO for an isotope; that is the whole contrast."""
    high, low = total_hazard(t + step, lam, m), total_hazard(t - step, lam, m)
    if high <= 0.0 or low <= 0.0:
        return 0.0
    return (math.log(high) - math.log(low)) / (2.0 * step)


def doubling_time(t: float, lam: float, m: float) -> float:
    """Mortality-rate doubling time in years. INFINITE for a memoryless process."""
    theta = log_hazard_slope(t, lam, m)
    return math.inf if theta <= 0.0 else math.log(2.0) / theta


# ---------------------------------------------------------------------------
# CALIBRATION -- two parameters, two targets. Constrained, not predicted.
# ---------------------------------------------------------------------------

def calibrate() -> tuple[float, float]:
    def residuals(params):
        lam, log_m = params
        lam = abs(lam)
        m = math.exp(log_m)
        if lam <= 0.0 or not math.isfinite(m):
            return [1e6, 1e6]
        try:
            median = brentq(lambda t: survival(t, lam, m) - 0.5, 1e-6, 400.0)
        except ValueError:
            return [1e6, 1e6]
        return [median - TARGET_MEDIAN_YEARS,
                doubling_time(TARGET_MRDT_AT, lam, m) - TARGET_MRDT_YEARS]

    solution, _, ok, message = fsolve(residuals, [0.09, math.log(1000.0)], full_output=True)[:4]
    if ok != 1:
        raise RuntimeError(f"calibration did not converge: {message}")
    return abs(solution[0]), math.exp(solution[1])


# ---------------------------------------------------------------------------
# ENVIRONMENTAL INDUCTION -- the third collision, and the sharpest one
# ---------------------------------------------------------------------------

#: Measured environmental sensitivity of real nuclear decay constants. These are the
#: numbers that make the analogy's third failure quantitative rather than rhetorical.
#: Rutherford and Soddy established rate invariance in 1902-03, and radiometric dating is
#: built on it -- if lambda responded to chemistry, geochronology would not exist.
NUCLEAR_SENSITIVITY = (
    ("temperature, pressure, chemistry (alpha decay)",
     "< 1e-4", "tunnelling through a MeV Coulomb barrier cannot notice eV-scale chemistry"),
    ("chemical form, electron-capture nuclides (Be-7)",
     "~1e-3 to 1.5e-2", "EC needs electron density AT the nucleus, so bonding shifts it"),
    ("pressure at gigapascals",
     "< 1e-3", "compresses the electron cloud, not the nucleus"),
    ("FULL IONISATION, bound-state beta (Re-187)",
     "~1e+9", "42 Gyr neutral -> ~33 yr bare; the electron cloud is GONE"),
)


def median_of(lam: float, m: float) -> float:
    return brentq(lambda t: survival(t, lam, m) - 0.5, 1e-6, 5000.0)


def environmental_induction(lam: float, m: float) -> None:
    """How does the environment 'induce early decay' -- and by which knob?

    The model has exactly two places an insult can act, and they have different
    signatures. That difference is the whole content of this section.
    """
    baseline = median_of(lam, m)
    print()
    print("-" * 78)
    print("  ENVIRONMENTAL INDUCTION -- the third collision, and it does not relocate")
    print("-" * 78)
    print()
    print("  A nuclear decay constant is famously INVARIANT to its environment. That is not")
    print("  a convenience; radiometric dating is built on it. Measured sensitivities:")
    print()
    print(f"    {'perturbation':<48} {'d(lambda)/lambda':>17}")
    print(f"    {'-'*48} {'-'*17}")
    for label, magnitude, _why in NUCLEAR_SENSITIVITY:
        print(f"    {label:<48} {magnitude:>17}")
    print()
    for label, _magnitude, why in NUCLEAR_SENSITIVITY:
        print(f"      {label.split(',')[0]:<28} {why}")
    print()
    print("  Human hazard, by contrast, moves by FACTORS in ordinary conditions -- smoking")
    print("  ~2-3x all-cause, deprivation gaps of 10-20 years of life expectancy, famine and")
    print("  epidemic swinging it by an order of magnitude. Ordinary, not extreme.")
    print()
    print("  So the analogy fails a THIRD time, on rate invariance. And unlike memorylessness")
    print("  this failure does NOT relocate to a smaller scale: there is no level at which a")
    print("  human's parts stop caring about radiation, toxins, nutrition or infection.")
    print()
    print("  BUT the nuclear table says exactly HOW a nucleus can be induced -- look at the")
    print("  last row. Re-187 accelerates by a factor of 1e9 not because anything tuned its")
    print("  rate, but because full ionisation REMOVED ITS ELECTRON CLOUD. The environment")
    print("  cannot nudge lambda; it can only destroy structure and expose the core.")
    print()
    print("  That is precisely what an environmental insult does in the redundancy model. It")
    print("  does not tune lambda. It kills elements out of the bucket -- it lowers m. So the")
    print("  two knobs have different signatures, and the model says which one nature uses:")
    print()
    print(f"    {'insult':<34} {'median (yr)':>12} {'delta (yr)':>12} {'scaling':>12}")
    print(f"    {'-'*34} {'-'*12} {'-'*12} {'-'*12}")
    print(f"    {'baseline':<34} {baseline:>12.2f} {0.0:>12.2f} {'--':>12}")
    for factor in (0.5, 0.25, 0.125, 0.01):
        med = median_of(lam, m * factor)
        print(f"    {'redundancy m x %-6g' % factor:<34} {med:>12.2f} {med-baseline:>12.2f} "
              f"{'logarithmic':>12}")
    for factor in (2.0, 4.0, 8.0):
        med = median_of(lam * factor, m)
        print(f"    {'element rate lambda x %-6g' % factor:<34} {med:>12.2f} {med-baseline:>12.2f} "
              f"{'reciprocal':>12}")

    per_halving = math.log(2.0) / lam
    measured_halving = baseline - median_of(lam, m * 0.5)
    hard = baseline - median_of(lam, m * 0.01)
    halvings = math.log(100.0, 2.0)
    print()
    print(f"  THE EXACT STRUCTURAL RESULT, and it is not fitted. Ignoring the Makeham term,")
    print(f"  the median solves m exp(-lambda t) = ln 2, so t_median = ln(m / ln 2) / lambda")
    print(f"  and d t_median / d ln m = 1 / lambda. **Every HALVING of redundancy costs")
    print(f"  exactly one element half-life: {per_halving:.2f} yr.**")
    print()
    print(f"  The table above measures {measured_halving:.2f} yr per halving, not {per_halving:.2f}. The gap IS the")
    print(f"  Makeham term, which the closed form drops and the table keeps. Neither number")
    print(f"  is wrong; they answer slightly different questions and both are printed so the")
    print(f"  discrepancy cannot be mistaken for an error.")
    print()
    print(f"  Note what this does NOT say. Destroying 99% of the reserve costs {hard:.1f} yr --")
    print(f"  most of a life. The cost is linear in the NUMBER OF HALVINGS ({halvings:.1f} of them")
    print(f"  here), which is gentle in the FRACTION destroyed and brutal in the count. 'Robust'")
    print(f"  is the wrong reading; 'logarithmic' is the right one.")
    print()
    print("  A signature that would discriminate the two knobs, and an honest note that the")
    print("  obvious datum does NOT. Redundancy loss compresses lifespan logarithmically;")
    print("  element-rate change compresses it reciprocally. Tempting to say the observed")
    print("  10-20 year environmental gaps favour redundancy -- but a 15 year gap needs only")
    print(f"  m x {0.5**(15.0/measured_halving):.2f} OR lambda x {baseline/(baseline-15.0):.2f}, and both are unremarkable. One summary")
    print("  statistic cannot separate a logarithm from a reciprocal. Only the SHAPE of the")
    print("  hazard curve across the whole age range can, and fitting that needs a life table")
    print("  this script deliberately does not have. Recorded as an open question.")
    print()
    print("  Stated as the compiler would: the environment CAN induce early decay, but only")
    print("  by the one mechanism nuclear physics also permits -- destroying structure, never")
    print("  by tuning a rate constant. The metaphor survives this question by relocating,")
    print("  again, and the relocation is the answer rather than a rescue.")


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 78)
    print("DECAY ANALOGY -- on what set is 'a human is an isotope' true?")
    print("backs: THE_COMPILER.md section V     arithmetic: exact/analytic, no sampling")
    print("=" * 78)
    print()
    print("  NOT DEMOGRAPHY. Two parameters fitted to two textbook statistics. The object")
    print("  under test is the METAPHOR, not any population and no person.")

    try:
        lam, m = calibrate()
    except RuntimeError as exc:
        print(f"\n  CALIBRATION FAILED: {exc}")
        return 2

    element_half_life = math.log(2.0) / lam
    median = brentq(lambda t: survival(t, lam, m) - 0.5, 1e-6, 400.0)

    print()
    print("  FITTED (constrained by construction -- these predict nothing):")
    print(f"    element hazard lambda   : {lam:.6f} /yr   -> element half-life {element_half_life:.2f} yr")
    print(f"    initial redundancy m    : {m:.1f} elements (Poisson mean), quorum = {QUORUM}")
    print(f"    -> median survival      : {median:.2f} yr   (target {TARGET_MEDIAN_YEARS:.1f})")
    print(f"    -> doubling time at {TARGET_MRDT_AT:.0f}  : {doubling_time(TARGET_MRDT_AT, lam, m):.2f} yr"
          f"   (target {TARGET_MRDT_YEARS:.1f})")
    print(f"  SET, NOT FITTED:")
    print(f"    Makeham mu              : {MU_PER_YEAR:.1e} /yr (age-independent background)")

    print()
    print("  THE CONTRAST -- an isotope has theta = d ln h/dt identically ZERO at every age.")
    print()
    print(f"    {'age':>5}  {'h_total /yr':>12}  {'h_Makeham share':>16}  {'doubling time':>14}")
    print(f"    {'-'*5}  {'-'*12}  {'-'*16}  {'-'*14}")
    for age in (1, 10, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 140):
        h = total_hazard(age, lam, m)
        share = MU_PER_YEAR / h if h > 0 else 1.0
        mrdt = doubling_time(age, lam, m)
        mrdt_s = "flat (inf)" if math.isinf(mrdt) else f"{mrdt:.1f} yr"
        print(f"    {age:>5}  {h:>12.3e}  {share:>15.1%}  {mrdt_s:>14}")

    # -- the disconnected validity domain -----------------------------------
    def makeham_dominates(t: float) -> float:
        return MU_PER_YEAR - system_hazard(t, lam, m)

    try:
        crossover = brentq(makeham_dominates, 1e-6, 200.0)
    except ValueError:
        crossover = float("nan")

    plateau = MU_PER_YEAR + lam
    # age at which the hazard comes within 10% of its asymptote
    try:
        approach = brentq(lambda t: total_hazard(t, lam, m) - 0.9 * plateau, 1.0, 400.0)
    except ValueError:
        approach = float("nan")

    print()
    print("-" * 78)
    print("  THE VALIDITY DOMAIN OF THE METAPHOR -- and it is DISCONNECTED")
    print("-" * 78)
    print()
    print(f"  [A]  t < {crossover:.1f} yr        HOLDS. The constant Makeham term outweighs the")
    print( "                             redundancy term, hazard is flat, survival is")
    print( "                             exponential. In this band a person IS an isotope,")
    print(f"                             half-life ln2/mu = {math.log(2.0)/MU_PER_YEAR:.0f} yr.")
    print()
    print(f"  [B]  {crossover:.1f} < t < {approach:.0f} yr    REFUSED. Hazard doubles about every"
          f" {doubling_time(TARGET_MRDT_AT, lam, m):.0f} yr.")
    print( "                             Collides with MEMORYLESSNESS, the model's founding")
    print( "                             axiom. No half-life exists here: the survival curve")
    print( "                             is not exponential, so 'the half-life of a human'")
    print( "                             names a quantity the model cannot carry.")
    print()
    print(f"  [C]  t > {approach:.0f} yr          HOLDS AGAIN, and this is NOT fitted. The model")
    print(f"                             forces h -> mu + lambda = {plateau:.4f} /yr as")
    print( "                             redundancy runs out and the last element's own")
    print( "                             constant hazard shows through. Memorylessness")
    print(f"                             returns with half-life {math.log(2.0)/plateau:.1f} yr.")
    print( "                             (A late-life plateau IS reported in humans and is")
    print( "                             contested; it was deliberately not a fit target.)")

    # -- what this model gets WRONG. Read before quoting any age above. ------
    mrdt_60, mrdt_70, mrdt_80 = (doubling_time(a, lam, m) for a in (60.0, 70.0, 80.0))
    flat_band_hazard = isotope_hazard(0.0, MU_PER_YEAR)
    print()
    print("-" * 78)
    print("  WHERE THIS MODEL IS WRONG -- read before quoting any age above")
    print("-" * 78)
    print(f"""
  The doubling time is NOT sustained. Measured on the curve just printed:

      age 60 -> {mrdt_60:5.1f} yr        age 70 -> {mrdt_70:5.1f} yr        age 80 -> {mrdt_80:5.1f} yr

  It equals the {TARGET_MRDT_YEARS:.0f}-year target only at age {TARGET_MRDT_AT:.0f}, which is where it was
  fitted, and that is not a result. Real human mortality holds a roughly constant
  ~8-year doubling time across most of adult life. This curve accelerates far too
  abruptly at the Makeham crossover and decelerates far too early after it, so its
  Gompertz band is a point rather than a band.

  The cause is a deliberate simplification, not a bug: this is ONE redundant block with
  quorum {QUORUM}. For A = m exp(-lambda t) >> 1 the model gives theta = lambda (A - 1),
  which falls as A falls -- so theta is stationary only near A = 1. Gavrilov & Gavrilova
  derive Gompertz from a SERIES NETWORK of such blocks, which is what broadens the band.
  Building that here would add parameters and change nothing below; it is named and left.

  CONSEQUENCE, and it governs how every number above may be used:

    SURVIVES  the three-regime STRUCTURE -- flat, accelerating, plateauing -- and that
              it emerges from constant-hazard parts with no age-dependent rule anywhere.
              That is the finding, and it does not depend on the fit.
    SURVIVES  the two-scale relocation, the non-inherited daughter rate, the coupled
              ensemble. None of the three is a fitted quantity.
    DOES NOT  the boundary ages. {crossover:.1f} yr and {approach:.0f} yr are artifacts of a
              one-block model. They locate the regimes' EXISTENCE, not their edges, and
              must never be quoted as statements about people. The real Makeham/Gompertz
              crossover in humans is far earlier than {crossover:.0f}.

  For scale, band [A]'s flat hazard is exactly mu = {flat_band_hazard:.1e} /yr by construction,
  because in that band the model has nothing else in it. That is what makes it an
  isotope there, and also why band [A] is the least interesting of the three.
""")

    environmental_induction(lam, m)

    print()
    print("-" * 78)
    print("  THE ANSWER TO 'WHAT CONFIGURATION DESCRIBES A GENERAL HUMAN'")
    print("-" * 78)
    print(f"""
  isotope:                                   <- what the metaphor imports
    hazard          : lambda, constant       [MEMORYLESS -- the founding axiom]
    state           : none. A nucleus has no age and nothing to degrade.
    env_coupling    : ~0 in ordinary conditions; ~1e9 only under full ionisation
    daughter        : a nuclide, carrying its OWN constant lambda
    ensemble        : independent

  human:                                     <- what it is imported onto
    element_hazard  : {lam:.6f} /yr        [MEMORYLESS -- the metaphor is true HERE]
    redundancy      : Poisson(m = {m:.0f})     [state; a nucleus has none, and that is
                                       the entire difference]
    quorum          : n_working >= {QUORUM}
    external_hazard : {MU_PER_YEAR:.1e} /yr        [Makeham; memoryless, age-independent]
    system_hazard   : EMERGENT, not declared -- accelerating, plateauing
    memoryless      : FALSE at organism scale; TRUE at element scale
    env_coupling    : STRONG, and it acts on REDUNDANCY, not on lambda. The environment
                      cannot tune a rate; it destroys structure. Which is exactly the
                      one mechanism nuclear physics also allows -- ionisation, not heat.
    daughter        : decomposition. Rate is Arrhenius in temperature and coupled to
                      the environment, NOT inherited from the parent's lambda. A decay
                      chain passes a rate constant down; this one does not.
    ensemble        : NOT independent. Nuclei share no environment; people do.

  So: a human is not an isotope. A human is a Poisson-sized bucket of isotopes with a
  quorum rule, and the isotope model recovers the organism only at the two ends of life
  where the bucket is irrelevant -- once because the background dominates it, once
  because it is empty.

  Two places the metaphor breaks that no calibration can repair, both listed above:
  the DAUGHTER does not inherit a rate constant (decomposition is driven by the
  environment, which is why forensic post-mortem intervals are estimated in
  accumulated degree-days and not in half-lives), and the ENSEMBLE is not independent.
  Radioactive decay assumes both. Neither is a parameter that can be tuned.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
