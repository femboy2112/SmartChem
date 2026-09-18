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


def _is_sp3_nonaromatic_carbon(idx: int, atoms, adjacency: "dict[int, list[tuple[int, int]]]") -> bool:
    """A carbon whose every bond is single -- an sp3, non-aromatic carbon.  A kekulized aromatic ring carbon
    carries an order-2 bond and a carbonyl carbon its C=O, so BOTH are excluded (representation-robust: the
    check reads bond orders, never explicit H)."""
    return atoms[idx] == "C" and all(order == 1 for _n, order in adjacency.get(idx, ()))


def _oxygen_heavy_neighbours(molecule: Molecule) -> "tuple[tuple, dict]":
    adjacency: "dict[int, list[tuple[int, int]]]" = {}
    for bond in molecule.bonds:
        adjacency.setdefault(bond.i, []).append((bond.j, bond.order))
        adjacency.setdefault(bond.j, []).append((bond.i, bond.order))
    return molecule.atoms, adjacency


def _ether_oxygen_counts(molecule: Molecule) -> int:
    """The number of dialkyl ETHER oxygens: an O with exactly two heavy neighbours, BOTH single-bonded sp3
    non-aromatic carbons.  This EXCLUDES an ester's -O- (one neighbour is the carbonyl C, which bears a C=O),
    an anhydride's bridging O (its neighbour is a carbonyl C), and an aryl ether's aromatic-C neighbour -- so an
    ester/acid is never miscounted as an ether.  Heavy-neighbour census only (no explicit-H dependence, mirroring
    :func:`_acyl_group_counts`)."""
    atoms, adjacency = _oxygen_heavy_neighbours(molecule)
    ethers = 0
    for o, element in enumerate(atoms):
        if element != "O":
            continue
        heavy = [(n, order) for n, order in adjacency.get(o, ()) if atoms[n] != "H"]
        if len(heavy) == 2 and all(order == 1 for _n, order in heavy) and all(
            _is_sp3_nonaromatic_carbon(n, atoms, adjacency) for n, _o in heavy
        ):
            ethers += 1
    return ethers


def _alcohol_counts(molecule: Molecule) -> int:
    """The number of ALCOHOL oxygens: an O with exactly one heavy neighbour, a single-bonded sp3 non-aromatic
    carbon.  This EXCLUDES a phenol's aromatic-C hydroxyl, a carboxyl -O-H (its neighbour is the carbonyl C), a
    peroxide O (its heavy neighbour is another O, not C), and an ether O (two heavy neighbours).  Counts a neutral
    -O-H or a deprotonated alkoxide equally (no explicit-H dependence)."""
    atoms, adjacency = _oxygen_heavy_neighbours(molecule)
    alcohols = 0
    for o, element in enumerate(atoms):
        if element != "O":
            continue
        heavy = [(n, order) for n, order in adjacency.get(o, ()) if atoms[n] != "H"]
        if len(heavy) == 1 and heavy[0][1] == 1 and _is_sp3_nonaromatic_carbon(heavy[0][0], atoms, adjacency):
            alcohols += 1
    return alcohols


def _ether_shape_and_net_change(step: ExperimentStep) -> bool:
    """The ETHERIFICATION shape + net class-identity, WITHOUT the R57 whole-molecule clause (iii).

    True iff the ELEMENTARY INTERMOLECULAR shape holds -- exactly 2 non-water reactants -> exactly 1 non-water
    product, water net-produced -- AND (i) a dialkyl ether-O is net-FORMED and (ii) an sp3 alcohol is net-CONSUMED.
    Factored out of :func:`_is_intermolecular_etherification` so the R58 reaction-TYPE oracle can pair it with the
    span-LOCAL reaction-centre check in place of clause (iii): clause (iii) ("no ether among the reactants") is a
    whole-molecule blacklist that FALSE-DEMOTES a genuine etherification whose reactant merely CONTAINS an unrelated
    ether elsewhere (``methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water``, a production k=1 miss --
    [[a-whole-set-count-classifier-is-fooled-by-non-locality]]).  The span reads the actual centre and needs no such
    blacklist."""
    non_water_reactants = [m for m in step.reactants if not _is_water(m)]
    non_water_products = [m for m in step.products if not _is_water(m)]
    if len(non_water_reactants) != 2 or len(non_water_products) != 1:
        return False
    if sum(_is_water(m) for m in step.products) - sum(_is_water(m) for m in step.reactants) <= 0:
        return False
    r_alcohol = sum(_alcohol_counts(m) for m in step.reactants)
    r_ether = sum(_ether_oxygen_counts(m) for m in step.reactants)
    p_alcohol = sum(_alcohol_counts(m) for m in step.products)
    p_ether = sum(_ether_oxygen_counts(m) for m in step.products)
    return (p_ether - r_ether) > 0 and (p_alcohol - r_alcohol) < 0


def _reactant_ether_count(step: ExperimentStep) -> int:
    """The number of dialkyl ether-O among the step's reactants (the R57 clause-(iii) quantity)."""
    return sum(_ether_oxygen_counts(m) for m in step.reactants)


def _is_intermolecular_etherification(step: ExperimentStep) -> bool:
    """Does this step dehydratively couple two alcohols into a dialkyl ether? (the R57 whole-molecule predicate)

    Fires iff :func:`_ether_shape_and_net_change` holds AND clause (iii): NO ether-O is present among the reactants.
    Within the shape, forming an sp3 C-O-C ether while consuming an sp3 C-O-H alcohol and expelling water is the net
    signature of a real Williamson-type / acid-dehydrative etherification, and clause (iii) demotes the
    formula-conserving bundled fiction that REUSES an existing ether (glycol + dimethyl ether -> dimethoxyethane +
    water).  DERIVED graph surgery, target-independent.

    This is the R57 predicate, retained UNCHANGED as the span-ABSENT fallback for the R58 oracle (a hand-built step
    or a non-scission transform carries no reaction centre) and pinned by the R57 tests.  When a step DOES carry a
    reaction centre, the oracle reads it instead (:mod:`smartchem.experiment.reaction_type_oracle`): the span-local
    check both DROPS clause (iii) -- recovering genuine etherifications whose reactant contains an unrelated ether --
    and hardens the k=1 locality into a CHECKED structural fact (config-robust), the R58 root fix."""
    return _ether_shape_and_net_change(step) and _reactant_ether_count(step) == 0


def _methanol_specific_alcohol_count(molecule: Molecule) -> int:
    """The number of METHANOL oxygens: an alcohol-O (one heavy neighbour, a single-bonded sp3 non-aromatic
    carbon) whose carbinol carbon bears NO OTHER heavy neighbour -- i.e. literally CH3-OH, nothing longer.

    Strictly TIGHTER than :func:`_alcohol_counts`, and the tightening is the whole point.  A general alcohol
    census lets ethanol, isopropanol, phenol -- any O-bearing donor -- stand in as the departing group, and that
    is exactly how a formula-conserving fake sneaks a fake methyl transfer past the shape check.  Requiring the
    carbinol carbon to be a terminal CH3 (its single heavy neighbour is this very O) admits ONLY methanol: it
    EXCLUDES higher n-alkyl alcohols (their carbinol carbon carries a second heavy neighbour) and the aromatic
    phenol-O of the phenol+ammonia->aniline fake (aromatic carbon, not sp3).  No explicit-H dependence -- reads
    bond topology, mirroring :func:`_alcohol_counts`."""
    atoms, adjacency = _oxygen_heavy_neighbours(molecule)
    methanols = 0
    for o, element in enumerate(atoms):
        if element != "O":
            continue
        heavy = [(n, order) for n, order in adjacency.get(o, ()) if atoms[n] != "H"]
        if len(heavy) != 1 or heavy[0][1] != 1:
            continue
        carbon = heavy[0][0]
        if not _is_sp3_nonaromatic_carbon(carbon, atoms, adjacency):
            continue
        carbon_heavy = [n for n, _o in adjacency.get(carbon, ()) if atoms[n] != "H"]
        if carbon_heavy == [o]:  # the carbinol carbon's ONLY heavy neighbour is this O -> a lone CH3, so CH3-OH
            methanols += 1
    return methanols


def _n_methyl_amine_count(molecule: Molecule) -> int:
    """The number of N-METHYL amine nitrogens: an N with all-single bonds, bonded to at least one METHYL carbon
    (a single-bonded sp3 non-aromatic C whose only heavy neighbour is this N), and NOT adjacent to a carbonyl C.

    Three clauses, each excising a specific impostor.  All-single bonds excludes an sp2 imine N and a Kekulized
    aromatic N (both carry an order-2 bond) -- so an aryl amine like aniline's N never qualifies (its aromatic
    ring forces the exclusion by structure, and it bears no methyl regardless).  The methyl-carbon clause is the
    positive signature a real N-methylation net-FORMS; the phenol->aniline fake mints an aryl N-H, no methyl, so
    it never fires.  The carbonyl-neighbour exclusion keeps this DISJOINT from the acyl/amidation class -- an
    amide N sits beside a C=O, and I will not have this recognizer double-count an amidation as a methylation.
    No explicit-H dependence."""
    atoms, adjacency = _oxygen_heavy_neighbours(molecule)
    count = 0
    for n, element in enumerate(atoms):
        if element != "N":
            continue
        bonds = adjacency.get(n, ())
        if not all(order == 1 for _nb, order in bonds):
            continue
        has_methyl = adjacent_carbonyl = False
        for nb, _order in bonds:
            if atoms[nb] != "C":
                continue
            if _is_carbonyl_carbon(nb, atoms, adjacency):
                adjacent_carbonyl = True
            elif _is_sp3_nonaromatic_carbon(nb, atoms, adjacency):
                carbon_heavy = [m for m, _o in adjacency.get(nb, ()) if atoms[m] != "H"]
                if carbon_heavy == [n]:  # a terminal CH3 hung off this N
                    has_methyl = True
        if has_methyl and not adjacent_carbonyl:
            count += 1
    return count


def _methylation_shape_and_net_change(step: ExperimentStep) -> bool:
    """The N-METHYLATION shape + net class-identity, mirroring :func:`_ether_shape_and_net_change`.

    True iff the ELEMENTARY INTERMOLECULAR shape holds -- exactly 2 non-water reactants -> exactly 1 non-water
    product, water net-produced -- AND (i) a methanol-specific alcohol is net-CONSUMED and (ii) an N-methyl amine
    is net-FORMED.  The two census clauses are the conservation-lock the reaction-centre span alone cannot supply:
    real caffeine N-methylation (theophylline + methanol -> caffeine + water) and the FAKE aryl amination (phenol
    + ammonia -> aniline + water) carry a BYTE-IDENTICAL reaction centre, so the span check passes both.  The
    census separates them -- the fake consumes no methanol (phenol-O is aromatic, ammonia has no carbon) and forms
    no N-methyl amine (aniline's N is aryl, unmethylated) -- and general N-alkylation by a longer alcohol fails the
    methanol clause.  Factored out here (not inlined in the oracle) so the R58 span-local check can pair with it
    exactly as the etherification recognizer does."""
    non_water_reactants = [m for m in step.reactants if not _is_water(m)]
    non_water_products = [m for m in step.products if not _is_water(m)]
    if len(non_water_reactants) != 2 or len(non_water_products) != 1:
        return False
    if sum(_is_water(m) for m in step.products) - sum(_is_water(m) for m in step.reactants) <= 0:
        return False
    r_methanol = sum(_methanol_specific_alcohol_count(m) for m in step.reactants)
    p_methanol = sum(_methanol_specific_alcohol_count(m) for m in step.products)
    r_nmethyl = sum(_n_methyl_amine_count(m) for m in step.reactants)
    p_nmethyl = sum(_n_methyl_amine_count(m) for m in step.products)
    return (p_methanol - r_methanol) < 0 and (p_nmethyl - r_nmethyl) > 0


def _n_alkyl_amine_bond_count(molecule: Molecule) -> int:
    """The number of sp3-C--to--amine-N single BONDS: a single bond between a single-bonded sp3 non-aromatic carbon
    and an AMINE nitrogen (all-single-bond, NOT adjacent to a carbonyl C).  The general-alkyl analogue of
    :func:`_n_methyl_amine_count`, and the counting unit is the load-bearing choice.

    Count BONDS, not N ATOMS.  A general N-alkylation ``R2N-H + R'-OH -> R2N-R' + H2O`` adds exactly ONE new
    sp3 C-N bond, so a bond census rises by exactly one per alkylation -- whereas an N-atom census (the R60
    :func:`_n_methyl_amine_count`) does NOT rise when an ALREADY-alkylated secondary amine is alkylated again (the N
    was already "an N-alkyl amine" before and after).  Making the net signal LOCAL to the one bond formed is what
    lets the general class have a sound net signature at all; the R60 methyl census dodged this only because a
    terminal CH3 is a distinguishable NEW group, which no longer holds once the alkyl may be any chain.

    The N clauses mirror :func:`_n_methyl_amine_count`; only the carbon clause widens from a terminal CH3 to any
    sp3 non-aromatic C.  This admits ANY non-carbonyl nitrogen NUCLEOPHILE -- an aliphatic amine, a pyrrole-type
    heterocyclic ring N (pyrrole, imidazole/pyrazole N1, indole, the xanthine N7 of the caffeine class: lone-pair-
    donating aromatic N with NO ring C=N, so all-single-bond), and also a sulfonamide, hydrazide/hydrazine,
    hydroxylamine, or amidine/guanidine N.  Dehydrative N-alkylation onto each is a REAL reaction TYPE this
    recognizer INTENTIONALLY vouches (the operator-confirmed R63 scope; an adversary re-attack verified every
    admitted N is a genuine N-alkylation, never a fiction -- Problem A holds; caffeine is the canonical instance).
    The two clauses:
    * all-single-bond N -- excludes an sp2 imine N and a nitrile/azo/nitro/PYRIDINE-type aromatic N (all of which
      carry an order-2 bond).  It does NOT exclude a pyrrole-type aromatic N, which carries no order-2 bond -- a
      bond-order census cannot express ring aromaticity, and under the R63 direction it need not, since azole
      N-alkylation is admitted.  The phenol->aniline ARYL-amination fake stays demoted, but through the CARBON
      clause, NOT this one: aniline's exocyclic -NH2 is itself all-single-bond; it is the aromatic-ring CARBON it
      would bond to that :func:`_is_sp3_nonaromatic_carbon` rejects (an aryl C-N is not an sp3 C-N).  [The earlier
      comment "a Kekulized aromatic N carries an order-2 bond" was FALSE for pyrrole-type N and hid that gap; an
      adversary surfaced it -- see [[a-whole-set-count-classifier-is-fooled-by-non-locality]].]
    * NOT adjacent to a carbonyl C -- keeps this DISJOINT from the acyl/amidation class (an amide N sits beside a
      C=O and belongs to :func:`_is_intermolecular_acyl_condensation`).  This is the clause the R60 gate finding
      turns on: a carbonyl that MIGRATES off an N unmasks a pre-existing alkyl and forges a spurious rise -- caught
      by the reaction-centre span, NEVER trusted from this non-local count alone.
    No explicit-H dependence -- reads bond topology, mirroring :func:`_n_methyl_amine_count`."""
    atoms, adjacency = _oxygen_heavy_neighbours(molecule)
    count = 0
    for n, element in enumerate(atoms):
        if element != "N":
            continue
        bonds = adjacency.get(n, ())
        if not all(order == 1 for _nb, order in bonds):
            continue  # all-single-bond N (amine or azole): excludes imine / nitrile / pyridine-type aromatic N
        if any(atoms[nb] == "C" and _is_carbonyl_carbon(nb, atoms, adjacency) for nb, _o in bonds):
            continue  # a carbonyl-adjacent N is an amide N -> the acyl class, kept disjoint
        for nb, order in bonds:
            if order == 1 and atoms[nb] == "C" and _is_sp3_nonaromatic_carbon(nb, atoms, adjacency):
                count += 1
    return count


def _alkyl_carbinol_alcohol_count(molecule: Molecule) -> int:
    """The number of ALKYL-carbinol alcohol oxygens: an alcohol-O (one heavy neighbour, a single-bonded sp3
    non-aromatic carbon -- as :func:`_alcohol_counts`) whose carbinol carbon bears NO heavy neighbour other than
    this hydroxyl O and CARBON.

    Strictly TIGHTER than :func:`_alcohol_counts`, and the tightening is the conservation-lock's donor half.  An
    ALPHA-heteroatom carbinol -- a carbinol carbon bearing a SECOND N or O (a hemiaminal, gem-diol / carbonyl
    hydrate, or hemiacetal) -- is a MASKED CARBONYL: the carbon sits at carbonyl oxidation level, and "alkylating"
    an amine with it is really an aminal / acetal condensation via an iminium/oxocarbenium, a DIFFERENT reaction
    class.  :func:`_alcohol_counts` reads only that the leaving O's single neighbour is a bond-order-1 carbon and
    is blind to that carbon's OTHER substituents, so it counts the masked carbonyl as a genuine alcohol and lets the
    fiction VOUCH (an adversary proved exactly this: ``ammonia + aminomethanol -> methylenediamine + water`` and
    ``dimethylamine + (dimethylamino)methanol -> bis(dimethylamino)methane + water``).  Requiring the carbinol
    carbon's other heavy neighbours to be ALL carbon forbids the carbonyl oxidation level -- mirroring the
    carbonyl-neighbour discipline :func:`_acyl_group_counts` already uses -- and closes the class with NO
    genuine-case loss: a genuine beta-amino alcohol donor (ethanolamine, HO-CH2-CH2-NH2) keeps its carbinol
    carbon's neighbours = {O, C, H} and stays admitted; only geminal alpha-hetero donors are excluded.  No
    explicit-H dependence -- reads bond topology, mirroring :func:`_alcohol_counts`."""
    atoms, adjacency = _oxygen_heavy_neighbours(molecule)
    count = 0
    for o, element in enumerate(atoms):
        if element != "O":
            continue
        heavy = [(n, order) for n, order in adjacency.get(o, ()) if atoms[n] != "H"]
        if len(heavy) != 1 or heavy[0][1] != 1:
            continue
        carbon = heavy[0][0]
        if not _is_sp3_nonaromatic_carbon(carbon, atoms, adjacency):
            continue
        other = [m for m, _o in adjacency.get(carbon, ()) if atoms[m] != "H" and m != o]
        if all(atoms[m] == "C" for m in other):  # carbinol carbon is genuine alkyl (no alpha N/O/S = no masked C=O)
            count += 1
    return count


def _n_alkylation_shape_and_net_change(step: ExperimentStep) -> bool:
    """The GENERAL N-ALKYLATION shape + net class-identity (``non-carbonyl N-H + alkyl-OH -> N-alkyl + water``), the
    sp3-alcohol generalisation of :func:`_methylation_shape_and_net_change` -- the class the R60 record deferred to
    "a future round behind its own gate", hardened against two adversary kills.

    True iff the ELEMENTARY INTERMOLECULAR shape holds -- exactly 2 non-water reactants -> exactly 1 non-water
    product, water net-produced -- AND (i) an ALKYL-carbinol alcohol is net-CONSUMED
    (:func:`_alkyl_carbinol_alcohol_count`, NOT the looser :func:`_alcohol_counts` -- the donor half of the lock:
    it excludes an alpha-heteroatom carbinol / masked carbonyl, so an aminal/acetal condensation cannot pose as an
    alkylation) and (ii) an sp3-C--to--(amine-or-azole)-N bond is net-FORMED (:func:`_n_alkyl_amine_bond_count`).
    Where the R60 census demanded a METHANOL-specific donor and an N-METHYL amine, this admits any alkyl alcohol
    donor and any sp3-C-N non-carbonyl-N bond.  This whole-molecule census is NON-LOCAL and is NOT trusted alone:
    the recognizer (:func:`~smartchem.experiment.reaction_type_oracle._n_alkylation`) pairs it with the elementary
    reaction-centre span :meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation(("N",))` --
    the SAME centre signature N-methylation uses (element pairs do not change with chain length), which supplies
    the elementarity the census cannot see locally and forces the (now provably alkyl) carbinol carbon onto the
    nitrogen (the conservation-lock)."""
    non_water_reactants = [m for m in step.reactants if not _is_water(m)]
    non_water_products = [m for m in step.products if not _is_water(m)]
    if len(non_water_reactants) != 2 or len(non_water_products) != 1:
        return False
    if sum(_is_water(m) for m in step.products) - sum(_is_water(m) for m in step.reactants) <= 0:
        return False
    r_alcohol = sum(_alkyl_carbinol_alcohol_count(m) for m in step.reactants)
    p_alcohol = sum(_alkyl_carbinol_alcohol_count(m) for m in step.products)
    r_nalkyl = sum(_n_alkyl_amine_bond_count(m) for m in step.reactants)
    p_nalkyl = sum(_n_alkyl_amine_bond_count(m) for m in step.products)
    return (p_alcohol - r_alcohol) < 0 and (p_nalkyl - r_nalkyl) > 0


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
