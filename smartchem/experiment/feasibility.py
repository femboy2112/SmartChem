"""M1 -- thermodynamic feasibility: the DERIVED ΔG verdict on a reaction step.

The keystone of the corrected governing frame. "Is this reaction feasible?" is not a forbidden prediction:
where sourced standard thermodynamic data (:mod:`smartchem.data.thermo`) covers every species, an ESTABLISHED
model computes the reaction's Gibbs free energy -- ΔH by Hess's law, ΔG = ΔH - TΔS -- and grades it. That is
reproducing known chemistry, exactly as the PySCF oracle *computes* an atomization energy rather than looking
one up. Where the data does not reach, the verdict is a LOUD ``UNKNOWN``, never a fabricated ΔG.

What the verdict means, and what it does NOT
--------------------------------------------
* ``FAVORABLE`` -- ΔG < 0 at the reaction temperature: thermodynamically spontaneous in the written
  direction (a DERIVED/PREDICTED fact, graded below).
* ``UNFAVORABLE`` -- ΔG > 0: endergonic in this direction *at standard state*. This is a sourced
  *disfavour*, NOT a claim of impossibility -- coupling to another reaction, non-standard concentrations, or
  removing a product (Le Chatelier) can still drive it; the equilibrium extent quantifies how far (roadmap
  M2). We say "disfavored", never "cannot happen".
* ``BORDERLINE`` -- |ΔG| within a near-equilibrium band: neither strongly driven nor forbidden.
* ``UNKNOWN`` -- a species has no sourced thermodynamic data: no ΔG is computed.

The epistemic GRADE is separate from the direction:
* ``DERIVED`` -- computed at or near the 298.15 K reference of the sourced data (interpolation).
* ``PREDICTED`` -- extrapolated far from 298.15 K via the constant-ΔH/ΔS approximation (ΔH°, S° held
  temperature-independent). A real, established approximation, but an extrapolation -- so it is flagged.

Two boundaries stated loudly. (1) Thermodynamics answers *whether*, never *how fast*: ΔG is not a rate, and
a favorable ΔG is not a yield -- kinetics is a separate, unbuilt model. (2) The computation is at standard
state (1 bar, pure phases, the data's reference phase); real conditions shift it, and a caller injects their
own sourced data to refine it. Calibrated on known cases: 2H2+O2->2H2O(l) recovers ΔG°=-474 kJ, Haber
recovers -33 kJ and its ~465 K sign-flip -- the instrument reads true before its novel outputs are believed.

Independence: the data is a SEPARATE sourced table, and the stoichiometric coefficients come from
:func:`~smartchem.experiment.ceiling._coefficient_vector` -- the same kernel-cross-checked derivation the
ceiling divides by, so feasibility and the ceiling can never disagree on the balance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..contracts import Digestible
from ..data.phase_change import DEFAULT_PHASE_CHANGE, PhaseChangeRef, PhaseChangeTable, to_condensed
from ..data.thermo import DEFAULT_THERMO, REFERENCE_TEMPERATURE_K, ThermoRef, ThermoTable
from ..data.thermo_groups import estimate_thermo
from ..decompiler import Formula
from ..structure import resolve_structure
from .bucket import Bucket, Quantity, unknown
from .ceiling import _coefficient_vector
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "FeasibilityDirection",
    "FeasibilityGrade",
    "StepFeasibility",
    "RouteFeasibility",
    "resolve_thermo",
    "feasibility_of_step",
    "verify_feasibility",
]

#: Within this many kelvin of the data's 298.15 K reference, a ΔG is DERIVED; beyond it, PREDICTED.
NEAR_REFERENCE_K = 100.0
#: |ΔG| below this (kJ/mol) is reported BORDERLINE (near-equilibrium) rather than favored/disfavored.
BORDERLINE_KJ = 5.0


class FeasibilityDirection(str, Enum):
    FAVORABLE = "FAVORABLE"        # ΔG < 0 at T
    UNFAVORABLE = "UNFAVORABLE"    # ΔG > 0 at T (endergonic in this direction, at standard state)
    BORDERLINE = "BORDERLINE"      # |ΔG| within the near-equilibrium band
    UNKNOWN = "UNKNOWN"            # a species has no sourced thermodynamic data


class FeasibilityGrade(str, Enum):
    DERIVED = "DERIVED"            # computed at/near the 298.15 K reference (interpolation)
    PREDICTED = "PREDICTED"        # extrapolated far from 298.15 K (constant ΔH/ΔS), flagged
    UNKNOWN = "UNKNOWN"            # no computation possible


def _formula_str(molecule: Molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def _label(molecule: Molecule) -> str:
    named = resolve_structure(molecule)
    return named.name if named is not None else _formula_str(molecule)


def _resolve_phase_change(molecule: Molecule, table: PhaseChangeTable) -> PhaseChangeRef | None:
    # Match ONLY by resolved structural identity (name), NEVER by bare formula: a phase change is
    # compound-specific, and formula-keying lets an ISOMER steal another compound's Δsub/Δvap -- dimethyl
    # ether (C2H6O, a gas) would borrow ethanol's (C2H6O) ΔvapH and be "corrected" to a liquid.  Same
    # formula-collision class the kinetics lookup was hardened against ([[a-reaction-key-by-formula-borrows-
    # a-rate]]); red-team-found here.  An unregistered compound simply gets no correction (stays gas).
    named = resolve_structure(molecule)
    if named is None:
        return None
    return table.for_named(named.expected_formula, named.name)


def resolve_thermo(
    molecule: Molecule, table: ThermoTable = DEFAULT_THERMO, *, derive: bool = True, condensed: bool = True,
    phase_change: PhaseChangeTable = DEFAULT_PHASE_CHANGE, phase: str | None = None,
) -> ThermoRef | None:
    """The thermo record for ``molecule``: sourced if the table covers it (named, else formula-level when
    unambiguous), else -- when ``derive`` (default) -- a group-additivity estimate
    (:mod:`smartchem.data.thermo_groups`), else ``None`` (a loud gap).

    Sourced ALWAYS wins over derived: the group estimate is the rung-2 fallback that stops feasibility from
    reflexively returning ``UNKNOWN`` for a compound whose thermo known physics can derive
    ([[known-physics-not-new-physics]]).  The group estimate is GAS-phase; when ``condensed`` (default) and a
    SOURCED sublimation/vaporization (rung C, :mod:`smartchem.data.phase_change`) exists for the compound, the
    gas estimate is corrected to its condensed standard state -- ΔfH°(cr) = ΔfH°(gas) − ΔsubH,
    S°(cr) = S°(gas) − ΔsubS -- so a crystalline drug / liquid reagent gets a condensed-phase record instead
    of a phase-mismatched gas one (this is what finally gives paracetamol a condensed-phase ΔG).  A
    gas-estimate-plus-phase-correction is a two-step estimate, so it grades ``PREDICTED``.  ``derive=False``
    restores pure-sourced behaviour; ``condensed=False`` keeps the raw gas estimate.

    ``phase`` (item 5) narrows the SOURCED lookup to one standard-state phase.  Without it, a species the table
    holds in more than one phase (Br₂ gas/liquid) is phase-ambiguous and resolves to ``None`` (UNKNOWN,
    fail-closed) rather than silently returning the wrong-phase ΔfH° -- so a caller that reasons about a
    condensed species must SAY which phase it means (the M2b carried debt, closed).
    """
    named = resolve_structure(molecule)
    if named is not None:
        hit = table.for_named(named.expected_formula, named.name, phase=phase)
        if hit is not None:
            return hit
    hit = table.for_formula(_formula_str(molecule), phase=phase)
    if hit is not None:
        return hit
    # PHASE-AMBIGUITY FAIL-CLOSED (item 5, adversarial fold): a sourced miss on a species the table holds in MORE
    # than one phase is AMBIGUITY, not absence -- do NOT fall through to the gas Benson estimate below, which ignores
    # the phase question and would silently reinstate the debt for a Benson-COVERABLE dual-phase species.  (Br₂
    # escapes the estimate today only because it is Benson-uncoverable; the guarantee must be the design's, not one
    # molecule's -- red-team Finding 1.)
    #
    # ITEM5-PHASE-RANK-01 (evil-morty R43): the guarantee must hold at the SPECIFIC-phase fallback layer too, not
    # only for ``phase is None``.  Reaching here means the sourced lookup above already MISSED for the REQUESTED
    # phase.  For a multiphase species that miss is a genuine phase gap whether the caller gave no phase (ambiguous)
    # OR a specific phase the table does not hold (e.g. "solid", or a mis-cased "Gas") -- and deriving a phase-BLIND
    # gas estimate would answer a DIFFERENT phase than the one asked, silently reinstating the wrong-phase-ΔG debt
    # one layer down ([[a-fail-closed-guarantee-must-hold-at-every-fallback-layer]]).  So fail closed for ANY missed
    # phase on a multiphase species.  (A SINGLE-phase species is not phase-ambiguous, so an untabulated specific
    # phase still derives with the gas/condensed notes -- the legitimate paracetamol condensed-derive path is
    # untouched; ``is_multiphase`` is False there.)
    if table.is_multiphase(_formula_str(molecule)):
        return None
    if derive:
        est = estimate_thermo(molecule)
        if est is not None:
            dhf, s, phase, grade, prov = (
                est.dhf_kj_per_mol, est.s_j_per_mol_k, est.phase, est.grade, est.provenance,
            )
            # THERMO-UNC-01: thread the group-additivity uncertainty bands (computed by quadrature in
            # thermo_groups.estimate_thermo) into the record -- they were previously DROPPED here, so every DERIVED
            # value read as sigma=None, indistinguishable from a sourced value that honestly has no stated sigma.
            unc_dhf: "float | None" = est.dhf_uncertainty_kj
            unc_s: "float | None" = est.s_uncertainty_j_per_k
            sigma_lb = False
            if condensed:
                pc = _resolve_phase_change(molecule, phase_change)
                if pc is not None:
                    dhf, s, phase = to_condensed(dhf, s, pc)
                    grade = "PREDICTED"  # a gas estimate + a sourced phase correction is a two-step estimate
                    # PHASE-CHANGE-SIGMA: propagate the condensed ± PER LEG in quadrature.  A leg whose phase-change
                    # correction carries a SOURCED ± (ΔH for ΔfH°, ΔS for S°) becomes a proper quadrature of the gas
                    # band and that ± -- no longer understated.  A leg whose correction ± is None keeps the gas band,
                    # so THAT leg stays a LOWER BOUND.  The record's lower-bound flag lifts ONLY when BOTH legs are
                    # sourced; else it stays True (the red-team's HIGH: a phase correction drives phase_mixed False, so
                    # the reaction-level flag alone would miss an understated leg).
                    dh_sourced = pc.uncertainty_dh_kj_per_mol is not None and unc_dhf is not None
                    ds_sourced = pc.uncertainty_ds_j_per_mol_k is not None and unc_s is not None
                    if dh_sourced:
                        unc_dhf = math.sqrt(unc_dhf ** 2 + pc.uncertainty_dh_kj_per_mol ** 2)
                    if ds_sourced:
                        unc_s = math.sqrt(unc_s ** 2 + pc.uncertainty_ds_j_per_mol_k ** 2)
                    sigma_lb = not (dh_sourced and ds_sourced)
                    caveat = (
                        f"the condensed ± is the quadrature of the gas band and the sourced ΔH/ΔS ± ({pc.provenance})"
                        if not sigma_lb else
                        "the ± is a LOWER BOUND (the phase-change correction ± is not fully sourced)"
                    )
                    prov = f"{prov}; corrected GAS->{phase} via {pc.transition.value} ({pc.provenance}); {caveat}"
            if s < 0 or not math.isfinite(s) or not math.isfinite(dhf):
                # An off-coverage group estimate can be physically invalid (a negative third-law S° for
                # a species the Benson groups cannot describe, or a non-finite value).  That is NOT
                # thermo data -- it is a loud gap.  Fail closed to None (the resolve_thermo contract is
                # ThermoRef | None; it must never raise a garbage record OR crash the caller).  A NARROW,
                # EXPLICIT guard, not a blanket try/except: a genuine band-propagation bug in the
                # quadrature above still surfaces loudly from ThermoRef rather than being masked here
                # (adversarial fold).  Anti-fabrication: a garbage estimate never becomes a verdict.
                return None
            return ThermoRef(
                _formula_str(molecule), _label(molecule), dhf, s, phase, prov, grade=grade,
                uncertainty_dhf_kj=unc_dhf, uncertainty_s_j_per_mol_k=unc_s, sigma_is_lower_bound=sigma_lb,
            )
    return None


def _temperature_of(step: ExperimentStep) -> float:
    """The step's reaction temperature (K): the declared envelope's midpoint, or the 298.15 K reference."""
    env: ConditionEnvelope = step.envelope
    if env.temperature is not None:
        return (env.temperature.lo + env.temperature.hi) / 2.0
    return REFERENCE_TEMPERATURE_K


@dataclass(frozen=True)
class StepFeasibility(Digestible):
    """The thermodynamic feasibility of one reaction step: a DERIVED ΔG and its graded verdict, or UNKNOWN."""

    direction: FeasibilityDirection
    grade: FeasibilityGrade
    temperature_k: float | None
    delta_h_kj: float | None
    delta_s_j_per_k: float | None
    delta_g_kj: float | None
    reason: str
    finding: Quantity
    missing: tuple[str, ...]
    #: THERMO-UNC-01: the 1-sigma uncertainty on ΔG (kJ/mol), propagated in quadrature from the inputs' sourced/
    #: derived sigmas -- ``None`` when ANY contributing species lacks a sigma (the honest mixed sourced/derived edge:
    #: a partial sum would understate it).  ``sigma_delta_g_is_lower_bound`` is True when >=2 species are group-
    #: additivity DERIVED, whose shared-Benson-group errors are correlated, so the independent-quadrature value
    #: UNDERSTATES the true sigma (cf. formation.DerivedFormation).  Both are ``compare=False`` metadata (like
    #: ThermoRef's sigmas), so they move no digest and no golden -- a derived uncertainty is provenance, not identity.
    sigma_delta_g_kj: "float | None" = field(default=None, compare=False)
    sigma_delta_g_is_lower_bound: bool = field(default=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.direction, FeasibilityDirection):
            raise TypeError("direction must be a FeasibilityDirection")
        if not isinstance(self.grade, FeasibilityGrade):
            raise TypeError("grade must be a FeasibilityGrade")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")

    @property
    def is_known(self) -> bool:
        return self.direction is not FeasibilityDirection.UNKNOWN


# ---- P1.3: the aqueous free-acid dehydrative-acylation DOMAIN GUARD -------------------------------------------
# The ΔG estimator grades thermodynamic DRIVE and is BLIND to the acid-base salt sink and the activation barrier of
# a DIRECT condensation of a FREE carboxylic acid into an amide/ester/thioester.  In water at ambient conditions,
# acid + amine -> the ammonium CARBOXYLATE SALT (a proton transfer), NOT the amide; direct (Fischer) amidation/
# esterification needs activation (heat with water removal, or an activated acyl donor -- anhydride / acid chloride).
# So a FAVORABLE/ESSENTIALLY_COMPLETE ΔG verdict on this class is a fabrication (acetic acid + 4-aminophenol ->
# paracetamol + water reads ΔG = -98 kJ, K ~ 1e17).  This is the R47 domain-guard pattern
# ([[a-derived-estimate-must-guard-its-domain-of-validity]]) applied to the feasibility layer: recognize the class
# by DERIVED bond-topology surgery (never a reaction lookup) and FAIL CLOSED to UNKNOWN.  The route is still FOUND;
# feasibility just stops vouching for a class it cannot.  Because equilibrium_of_step reuses this ΔG and returns
# UNKNOWN when it is None, one guard here makes BOTH the feasibility and equilibrium layers honest.
#
# The guard fires ONLY on the ELEMENTARY INTERMOLECULAR shape -- exactly 2 non-water reactants -> exactly 1 non-water
# product, with water expelled.  That shape is load-bearing (evil-morty + dalembert, R48): it structurally excludes
# (a) intramolecular ring closure (lactone/lactam, 1 reactant -- entropically favored, the ΔG IS competent, must NOT
# guard), (b) activated-donor acylation (anhydride/acid-chloride -- a 2nd product, the leaving group), and (c)
# multi-transformation BUNDLED steps whose independent sub-reactions would fool or cancel a whole-molecule count.
# Within the elementary shape, conservation forces the net functional-group change to reflect the real acyl transfer,
# so the counts are sound.  Bundled steps fail OPEN (keep the estimate); the general reaction-class recognizer over
# arbitrary steps is PR-2, and the capped-scission engine emits elementary steps.  Scoped to ONE class (PR-1).


def _is_carbonyl_carbon(idx: int, atoms, adjacency: "dict[int, list[tuple[int, int]]]") -> bool:
    return any(order == 2 and atoms[n] == "O" for n, order in adjacency.get(idx, ()))


def _acyl_group_counts(molecule: Molecule) -> "tuple[int, int, int, int]":
    """(free-acid/carboxylate, amide, ester, thioester) carbonyl-group counts, by bond topology.

    REPRESENTATION-ROBUST (dalembert R48): a carboxyl/carboxylate carbon is a carbonyl C whose singly-bonded O has
    NO heavy neighbour other than that carbon -- so -C(=O)-O-H (explicit OR implicit H) and -C(=O)-O(-) (the salt)
    both count, while an ester's -O- (heavy neighbour = the alkyl C) and an anhydride's bridging O (heavy neighbour
    = a 2nd carbonyl C) do not.  No explicit-H dependence anywhere (the fail-closed guarantee cannot rest on a
    precondition the graph may not carry -- KILL 1).  Each carbonyl carbon is scored for EVERY heteroatom
    substituent it bears (no first-match ordering), so a carbamate counts amide+ester, a carbamic acid amide+acid."""
    atoms = molecule.atoms
    adjacency: "dict[int, list[tuple[int, int]]]" = {}
    for bond in molecule.bonds:
        adjacency.setdefault(bond.i, []).append((bond.j, bond.order))
        adjacency.setdefault(bond.j, []).append((bond.i, bond.order))
    acid = amide = ester = thioester = 0
    for c, element in enumerate(atoms):
        if element != "C" or not _is_carbonyl_carbon(c, atoms, adjacency):
            continue
        for n, order in adjacency.get(c, ()):
            if order != 1:
                continue
            hetero = atoms[n]
            if hetero == "N":
                amide += 1
            elif hetero in ("O", "S"):
                heavy = [x for x, _o in adjacency.get(n, ()) if x != c and atoms[x] != "H"]
                if hetero == "O" and not heavy:
                    acid += 1  # -C(=O)-O-H / -C(=O)-O(-): carboxyl or carboxylate
                elif len(heavy) == 1 and atoms[heavy[0]] == "C" and not _is_carbonyl_carbon(heavy[0], atoms, adjacency):
                    if hetero == "O":
                        ester += 1        # -O-C(non-carbonyl): ester (a 2nd carbonyl => anhydride, excluded)
                    else:
                        thioester += 1    # -S-C(non-carbonyl): thioester
    return acid, amide, ester, thioester


def _is_water(molecule: Molecule) -> bool:
    return molecule.charge == 0 and dict(molecule.formula) == {"H": 2, "O": 1}


def _is_intermolecular_acyl_condensation(step: ExperimentStep) -> bool:
    """Does this step dehydratively acylate a free carboxylic acid onto a heteroatom nucleophile? (the guarded class)

    Fires iff the ELEMENTARY INTERMOLECULAR shape holds -- exactly 2 non-water reactants -> exactly 1 non-water
    product, with water net-produced -- AND, over that step, a free acid/carboxylate is net-consumed and an
    amide/ester/thioester carbonyl is net-formed.  DERIVED graph surgery, target-independent; see the module note
    above ``_acyl_group_counts`` for why the shape restriction makes the net counts sound."""
    non_water_reactants = [m for m in step.reactants if not _is_water(m)]
    non_water_products = [m for m in step.products if not _is_water(m)]
    if len(non_water_reactants) != 2 or len(non_water_products) != 1:
        return False
    if sum(_is_water(m) for m in step.products) - sum(_is_water(m) for m in step.reactants) <= 0:
        return False
    r_acid = r_acyl = 0
    for m in step.reactants:
        acid, amide, ester, thioester = _acyl_group_counts(m)
        r_acid += acid
        r_acyl += amide + ester + thioester
    p_acid = p_acyl = 0
    for m in step.products:
        acid, amide, ester, thioester = _acyl_group_counts(m)
        p_acid += acid
        p_acyl += amide + ester + thioester
    return (p_acid - r_acid) < 0 and (p_acyl - r_acyl) > 0


def feasibility_of_step(
    step: ExperimentStep, *, thermo: ThermoTable = DEFAULT_THERMO, temperature_k: float | None = None,
    derive: bool = True, phases: "dict[Molecule, str] | None" = None,
) -> StepFeasibility:
    """The graded ΔG feasibility verdict for one step, over sourced thermodynamic data plus (when ``derive``,
    the default) a Benson group-additivity gas-phase fallback for species the table does not cover.

    ``temperature_k`` overrides the reaction temperature (default: the step's declared envelope midpoint, or
    the 298.15 K reference).  A species whose thermo is neither sourced NOR derivable makes the whole verdict
    UNKNOWN -- loud, never a fabricated ΔG.  When a derived (gas-phase) record is used, the verdict grade
    reflects it: a PREDICTED group value caps the verdict at PREDICTED, and mixing a derived-gas record with a
    sourced-condensed one caps at PREDICTED with a loud phase-inconsistency note (the group method yields gas
    values; a cross-phase ΔG omits the Δsub/Δvap terms -- the phase trap, stated not hidden).

    ``phases`` (item 5) declares the standard-state phase of any species the thermo table holds in MORE than one
    phase (today, only Br₂ gas/liquid), keyed on canonical STRUCTURE (never formula -- ``a-reaction-key-by-
    formula-borrows-a-rate``).  A single-phase species needs no entry.  A phase-ambiguous species with no entry
    resolves to ``None`` -> the whole step verdict is a loud UNKNOWN, never the silently-wrong-phase ΔfH°: a
    caller reasoning about condensed Br₂ must SAY so (the M2b carried debt, closed).
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    temperature = temperature_k if temperature_k is not None else _temperature_of(step)
    # P1.3 DOMAIN GUARD: the aqueous free-acid dehydrative-acylation class is outside the ΔG estimator's domain of
    # validity (blind to the acid-base salt sink / the activation requirement), so FAIL CLOSED to a loud UNKNOWN
    # rather than assert a fabricated FAVORABLE/COMPLETE.  Fires even when thermo data is fully available -- that is
    # exactly the point (the estimate exists and is a lie).  See the module note above ``_acyl_group_counts``.
    if _is_intermolecular_acyl_condensation(step):
        return StepFeasibility(
            FeasibilityDirection.UNKNOWN, FeasibilityGrade.UNKNOWN, temperature, None, None, None,
            "UNKNOWN (domain guard): an intermolecular DIRECT condensation of a free carboxylic acid into an "
            "amide/ester/thioester with expulsion of water -- the ΔG estimator is blind to the acid-base salt sink "
            "(aqueous acid + amine gives the ammonium carboxylate salt, not the amide) and to the activation this "
            "class requires (heat + water removal, or an activated acyl donor -- an anhydride/acid chloride), so a "
            "computed ΔG is outside its domain of validity; failed closed rather than assert a fabricated FAVORABLE/"
            "COMPLETE verdict for a mechanism that does not proceed as written",
            unknown("delta-G-rxn", "kJ/mol",
                    "the intermolecular free-acid dehydrative-acylation class is outside the ΔG estimator's domain "
                    "of validity (blind to the acid-base salt sink / the activation requirement)"),
            (),
        )
    species, nu = _coefficient_vector(step)
    canon_phases = {k.canonical(): v for k, v in phases.items()} if phases else {}
    resolved = [
        (m, n, resolve_thermo(m, thermo, derive=derive, phase=canon_phases.get(m.canonical())))
        for m, n in zip(species, nu)
    ]
    missing = tuple(_label(m) for m, _n, r in resolved if r is None)
    if missing:
        return StepFeasibility(
            FeasibilityDirection.UNKNOWN, FeasibilityGrade.UNKNOWN, None, None, None, None,
            f"UNKNOWN: no sourced thermodynamic data for {', '.join(sorted(set(missing)))}; ΔG cannot be "
            f"computed (inject sourced ΔfH°/S° to close this gap)",
            unknown("delta-G-rxn", "kJ/mol", "a reactant/product has no sourced formation enthalpy/entropy"),
            missing,
        )

    # nu is signed reactant(+)/product(-), so ΔX_rxn = products - reactants = -Σ nu_i X_i
    delta_h = -sum(n * r.dhf_kj_per_mol for _m, n, r in resolved)
    delta_s = -sum(n * r.s_j_per_mol_k for _m, n, r in resolved)
    delta_g = delta_h - temperature * delta_s / 1000.0  # S in J/K -> kJ/K

    # Provenance of the inputs: was any ΔfH°/S° group-DERIVED rather than sourced, and did the derived
    # (gas) records mix phases with sourced (condensed) ones?  Both cap the verdict grade honestly.
    grades = [r.grade for _m, _n, r in resolved]
    derived_labels = tuple(_label(m) for m, _n, r in resolved if r.grade != "SOURCED")
    phases = {r.phase for _m, _n, r in resolved}
    phase_mixed = len(phases) > 1 and bool(derived_labels)

    grade = (
        FeasibilityGrade.DERIVED
        if abs(temperature - REFERENCE_TEMPERATURE_K) <= NEAR_REFERENCE_K
        else FeasibilityGrade.PREDICTED
    )
    if any(g == "PREDICTED" for g in grades) or phase_mixed:
        grade = FeasibilityGrade.PREDICTED  # a PREDICTED group value / cross-phase sum can't grade DERIVED
    if abs(delta_g) < BORDERLINE_KJ:
        direction = FeasibilityDirection.BORDERLINE
    elif delta_g < 0:
        direction = FeasibilityDirection.FAVORABLE
    else:
        direction = FeasibilityDirection.UNFAVORABLE

    extrap = "" if grade is FeasibilityGrade.DERIVED else (
        " [PREDICTED: extrapolated from the 298.15 K reference via constant ΔH/ΔS]"
        if abs(temperature - REFERENCE_TEMPERATURE_K) > NEAR_REFERENCE_K else ""
    )
    derived_note = "" if not derived_labels else (
        f" [group-additivity DERIVED (gas, Benson) for {', '.join(sorted(set(derived_labels)))}]"
    )
    phase_note = "" if not phase_mixed else (
        f" [PHASE-MIXED {sorted(phases)}: a group-derived GAS value is summed with a sourced condensed "
        f"value; ΔG omits the Δsub/Δvap correction -- gas-phase estimate only, not the condensed ΔG]"
    )
    disfavour = "" if direction is not FeasibilityDirection.UNFAVORABLE else (
        " (endergonic in this direction at standard state -- disfavored, NOT impossible: coupling / "
        "non-standard conditions / product removal can still drive it)"
    )
    source_desc = "sourced ΔfH°/S°" if not derived_labels else "sourced + group-derived (gas) ΔfH°/S°"

    # THERMO-UNC-01: propagate the inputs' 1σ uncertainties to σ(ΔG) in quadrature.  _coefficient_vector already
    # dedupes species + nets pure spectators to 0, so each surviving species appears once with a NET coefficient and
    # no σ is double-counted (the category.py:1071 "one number appearing twice, minus itself" hazard is pre-handled).
    # σ(ΔH)² = Σ (nu_i · σ_ΔfH_i)², σ(ΔS)² = Σ (nu_i · σ_S_i)², σ(ΔG)² = σ(ΔH)² + (T·σ(ΔS)/1000)².  Each is computable
    # ONLY if EVERY species carries that σ -- one missing (a sourced value with no published ±) makes it UNKNOWN,
    # never a partial sum that silently understates it (the honest mixed sourced/derived edge).
    dhf_sigmas = [r.uncertainty_dhf_kj for _m, _n, r in resolved]
    s_sigmas = [r.uncertainty_s_j_per_mol_k for _m, _n, r in resolved]
    sigma_dh = (
        math.sqrt(sum((n * sig) ** 2 for (_m, n, _r), sig in zip(resolved, dhf_sigmas)))
        if all(sig is not None for sig in dhf_sigmas) else None
    )
    sigma_ds = (
        math.sqrt(sum((n * sig) ** 2 for (_m, n, _r), sig in zip(resolved, s_sigmas)))
        if all(sig is not None for sig in s_sigmas) else None
    )
    sigma_dg = (
        math.sqrt(sigma_dh ** 2 + (temperature * sigma_ds / 1000.0) ** 2)
        if (sigma_dh is not None and sigma_ds is not None) else None
    )
    # σ(ΔG) is a LOWER BOUND when the independent-quadrature assumption is violated, three ways: (a) ≥2 group-
    # additivity DERIVED values share the SAME Benson group DATABASE + additivity assumption -- a common-mode
    # systematic model error the quadrature (which treats them as independent) cannot see; this holds for ANY two
    # derived estimates, NOT only ones sharing a specific group (ethanol+ethylene share ZERO groups yet are still
    # method-correlated -- the earlier "shared Benson-group anchors" wording was too narrow, red-team fold); (b) a
    # cross-phase sum omits the Δsub/Δvap term; (c) a phase-corrected input whose band was not widened for the
    # correction (``r.sigma_is_lower_bound`` -- the red-team's HIGH, else a successful phase correction drives
    # phase_mixed False and this flag would miss it).  All UNDERSTATE the true σ (cf. formation.DerivedFormation).
    sigma_lower_bound = sigma_dg is not None and (
        len(set(derived_labels)) >= 2
        or phase_mixed
        or any(r.sigma_is_lower_bound for _m, _n, r in resolved)
    )
    sigma_note = "" if sigma_dg is None else (
        f" [σ(ΔG) {'≥' if sigma_lower_bound else '≈'} {sigma_dg:.1f} kJ/mol (1σ, quadrature"
        + ("; LOWER BOUND: correlated group-model / cross-phase / phase-corrected inputs)]"
           if sigma_lower_bound else ")]")
    )

    reason = (
        f"{direction.value}: ΔG = {delta_g:.1f} kJ/mol at {temperature:.1f} K "
        f"(ΔH = {delta_h:.1f} kJ, ΔS = {delta_s:.1f} J/K; Hess's law + Gibbs over {source_desc})"
        f"{disfavour}{extrap}{derived_note}{phase_note}{sigma_note} -- thermodynamic feasibility, not a rate"
    )
    finding = Quantity(
        "delta-G-rxn", f"{delta_g:.1f}", "kJ/mol", Bucket.KNOWN_SOURCED,
        f"{grade.value} via Hess's law + ΔG=ΔH-TΔS (established) over {source_desc} at {temperature:.1f} K"
        + ("" if not derived_labels else " (Benson group additivity, gas phase, banded)"),
    )
    return StepFeasibility(
        direction, grade, temperature, delta_h, delta_s, delta_g, reason, finding, (),
        sigma_delta_g_kj=sigma_dg, sigma_delta_g_is_lower_bound=sigma_lower_bound,
    )


@dataclass(frozen=True)
class RouteFeasibility(Digestible):
    """The thermodynamic feasibility of a whole route: one :class:`StepFeasibility` per step, and a verdict.

    Verdict precedence (honest, not optimistic): a sourced ``UNFAVORABLE`` step dominates; then any
    ``UNKNOWN`` (missing data) keeps the route from a clean favorable read; then ``BORDERLINE``; a route is
    ``FAVORABLE`` only when every step is favorable.
    """

    route: ExperimentRoute
    per_step: tuple[StepFeasibility, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.per_step) is not tuple or any(type(s) is not StepFeasibility for s in self.per_step):
            raise TypeError("per_step must be a tuple of StepFeasibility values")
        if len(self.per_step) != len(self.route.steps):
            raise ValueError(f"expected {len(self.route.steps)} step feasibilities, got {len(self.per_step)}")

    @property
    def verdict(self) -> str:
        d = [s.direction for s in self.per_step]
        if any(x is FeasibilityDirection.UNFAVORABLE for x in d):
            return "UNFAVORABLE"
        if any(x is FeasibilityDirection.UNKNOWN for x in d):
            return "UNKNOWN"
        if any(x is FeasibilityDirection.BORDERLINE for x in d):
            return "BORDERLINE"
        return "FAVORABLE"

    @property
    def net_delta_g_kj(self) -> float | None:
        """The route's overall thermodynamic drive: Σ of the per-step ``Δ_rG`` (M2-FP, Move 2).

        This is the **additive free-energy functor** ``G: Process -> (ℝ, +, ≤)`` -- Hess's law IS the
        functoriality, so this equals the ΔG of the route's single net reaction (shared intermediates
        cancel).  It is DISTINCT from :attr:`verdict`, the *worst-node categorical sign* ("is any step
        stuck?"); both are legitimate.  ``None`` (fail-closed) if any step's ΔG is UNKNOWN, so a partial
        sum never poses as a route drive.  A property, so it moves no digest and no golden.
        """
        contributions = [s.delta_g_kj for s in self.per_step]
        if any(value is None for value in contributions):
            return None
        return sum(contributions)

    def explain(self) -> str:
        lines = [f"feasibility (thermodynamic ΔG): {self.verdict}"]
        for idx, s in enumerate(self.per_step):
            lines.append(f"  step {idx + 1}: {s.reason}")
        return "\n".join(lines)


def verify_feasibility(
    route: ExperimentRoute, *, thermo: ThermoTable = None, temperature_k: float | None = None,
    derive: bool = True, phases: "dict[Molecule, str] | None" = None,
) -> RouteFeasibility:
    """The thermodynamic feasibility of every step of a route, over the sourced (injectable) thermo table
    plus (when ``derive``, the default) the Benson group-additivity gas-phase fallback.

    ``phases`` (item 5, threaded up) declares the standard-state phase of any species the thermo table holds
    in MORE than one phase (today, only Br₂ gas/liquid), keyed on canonical STRUCTURE (never formula --
    ``a-reaction-key-by-formula-borrows-a-rate``).  It is forwarded verbatim to every step's
    :func:`feasibility_of_step` (each step filters the dict to its own species), so a phase-ambiguous species
    with no entry makes that step -- and hence the route :attr:`~RouteFeasibility.verdict` and its additive
    :attr:`~RouteFeasibility.net_delta_g_kj` -- a loud UNKNOWN, never a silently-wrong-phase ΔG.  This is the
    linear-route mirror of :func:`~smartchem.experiment.functorial_physics.route_net_delta_g`'s DAG threading,
    closing the last phase-blind ``verify_*`` fold: a single ``phases`` declaration now flows through both the
    worst-node verdict and the Hess-sum drive.  A single-phase route needs no ``phases`` (default byte-stable)."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_THERMO if thermo is None else thermo
    per_step = tuple(
        feasibility_of_step(s, thermo=tbl, temperature_k=temperature_k, derive=derive, phases=phases)
        for s in route.steps
    )
    return RouteFeasibility(route, per_step)
