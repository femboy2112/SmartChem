"""
The frozen legacy baseline. Do not build on this module.

What this is
------------
Antigravity's original engine, reduced to exactly the code path needed to reproduce its
measured accuracy, and nothing else. It exists for one reason: a baseline you can still run
is worth more than a baseline you deleted. The headline claim of this repository is that
CCSD(T)/CBS reaches 1 kcal/mol where the original heuristic reached 80; that comparison is
only checkable while the 80 is still executable.

It replaces seven modules -- ``engine.py``, ``comonad.py``, ``lattice.py``, ``monad.py``,
``network.py``, ``molecule.py``, ``electrochem.py`` -- retired on 2026-07-20.

What was dropped, and why that is the retirement
------------------------------------------------
Everything removed was either dead code or the defect itself. Both cases are listed here
rather than left to the diff, because a capability that disappears silently during a
cleanup is indistinguishable from one that was never there:

  Poset.leq, Poset.is_favorable    F8. Zero call sites, and structurally wrong: charge
                                   transfer is identically 0 for A-A pairs, so the gate
                                   said "unfavorable" for every homonuclear bond while the
                                   engine happily formed them.
  Reaction.bind                    F4. Zero call sites, and dropped ``metadata``, so the
                                   "certificate" died on first composition. Replaced by
                                   ``pathway.Pathway.bind`` over a ``Tally`` monoid.
  Situated.extend, .map            F2. Zero call sites. ``Situated`` is a Coreader (a, e),
                                   not the Store comonad the docs claimed; its ``extend``
                                   could only ever see the one environment it was handed.
                                   Replaced by ``store.Store``.
  ThermoEffect.equilibrium_constant  F12. Divides by temp_k with no guard.
  verify_reaction, verify_photolysis,
  verify_crystal_lattice, verify_phase_state  F9, F10. Reached only by demo scripts. The
                                   photolysis path could not distinguish O2 from O3
                                   (per-atom average hardness); the band-gap formula was
                                   dimensionally invalid.
  ReactionGraph (network.py)       F3. ``find_catalytic_cycles`` printed "Catalytic Loop
                                   Closed mathematically" unconditionally and computed
                                   nothing. Replaced by ``pathway.catalytic_cycles``.
  molecule.py                      Zero importers anywhere in the repository, including
                                   its own tests.
  electrochem.py                   Reached only by ``battery_test.py``.

``propose_bond`` below is byte-identical to ``engine.py:7-159`` as it stood at commit
ef4f533. That is deliberate and load-bearing: if it were re-derived, the baseline it
produces would no longer be the baseline that was published.
``tests/test_findings.py::TestBaselineIsPreserved`` pins the exact numbers.

Its known defects are NOT fixed here. They are the measurement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, Tuple, TypeVar

from .atoms import Atom, Species

T = TypeVar("T")

__all__ = ["Env", "Situated", "Poset", "ThermoEffect", "Reaction", "propose_bond"]


# ======================================================================================
# Environment -- a Coreader, despite what the original docs called it
# ======================================================================================
@dataclass(frozen=True)
class Env:
    """
    The chemical environment. Note this is ``(value, env)`` -- a Coreader, not a Store.

    The distinction is the whole of finding F2: a Coreader carries the one environment it
    was handed, so a property computed in it can only ever produce a single answer. See
    ``smartchem/store.py`` for the Store comonad that replaced it, whose ``extend`` yields
    an entire response surface.
    """
    temperature_k: float
    pressure_atm: float
    solvent_name: str
    solvent_dielectric: float
    photon_wavelength_nm: float = float("inf")   # infinity means no light

    @property
    def photon_energy_ev(self) -> float:
        """E = hc/lambda, with hc ~ 1240 eV*nm."""
        if self.photon_wavelength_nm == float("inf"):
            return 0.0
        return 1240.0 / self.photon_wavelength_nm

    @property
    def external_energy_ev(self) -> float:
        return self.photon_energy_ev

    @classmethod
    def standard(cls) -> "Env":
        return cls(298.15, 1.0, "Vacuum", 1.0, float("inf"))

    @classmethod
    def aqueous(cls, temp_k: float = 298.15) -> "Env":
        return cls(temp_k, 1.0, "Water", 80.1, float("inf"))


@dataclass(frozen=True)
class Situated(Generic[T]):
    """A species together with its environment. ``extend``/``map`` removed -- see F2."""
    value: T
    env: Env

    def extract(self) -> T:
        return self.value

    def born_solvation_energy_ev(self, charge: int, radius_pm: float) -> float:
        """
        Born solvation: E = -(z^2 * e^2)/(8*pi*eps_0*r) * (1 - 1/epsilon), in eV.

        The 1440 eV*pm constant and the +50 pm effective-radius correction are both from
        the original and are both correctly transcribed textbook physics.
        """
        if charge == 0:
            return 0.0
        born_constant = 1440.0 / 2.0
        epsilon = self.env.solvent_dielectric
        r_eff = radius_pm + 50.0
        return -(charge ** 2 * born_constant) / r_eff * (1.0 - (1.0 / epsilon))


# ======================================================================================
# The hardness/electronegativity lattice -- the two statics that are actually called
# ======================================================================================
class Poset:
    """Mulliken electronegativity and chemical hardness. ``leq``/``is_favorable`` cut, F8."""

    @staticmethod
    def charge_transfer_energy(donor: Atom, acceptor: Atom) -> float:
        """
        Parr-Pearson charge transfer:  dE = -(chi_a - chi_d)^2 / (4 * (eta_a + eta_d)).

        Correctly transcribed, and identically zero when donor and acceptor are the same
        element -- which is why it could never describe homonuclear bonding.
        """
        chi_diff = acceptor.mulliken_en - donor.mulliken_en
        eta_sum = acceptor.hardness + donor.hardness
        if chi_diff <= 0:
            return 0.0
        return -(chi_diff ** 2) / (4.0 * eta_sum)

    @staticmethod
    def hsab_penalty(a: Atom, b: Atom) -> float:
        """Hard-Soft Acid-Base mismatch: hard likes hard, soft likes soft."""
        return abs(a.hardness - b.hardness)


# ======================================================================================
# The effect monad -- minus its bind, which was the defect
# ======================================================================================
@dataclass(frozen=True)
class ThermoEffect:
    """Thermodynamic footprint of a state change. Energies in eV."""
    delta_h_ev: float
    delta_s_ev_k: float

    def get_delta_g(self, temp_k: float) -> float:
        """Gibbs free energy: dG = dH - T dS."""
        return self.delta_h_ev - (temp_k * self.delta_s_ev_k)

    def __add__(self, other: "ThermoEffect") -> "ThermoEffect":
        return ThermoEffect(
            self.delta_h_ev + other.delta_h_ev,
            self.delta_s_ev_k + other.delta_s_ev_k,
        )


@dataclass(frozen=True)
class Reaction(Generic[T]):
    """A set of possible outcomes with their thermodynamic footprints. ``bind`` cut, F4."""
    outcomes: List[Tuple[T, ThermoEffect]]
    metadata: dict = None

    @staticmethod
    def pure(value: T) -> "Reaction[T]":
        """No reaction; zero thermodynamic effect."""
        return Reaction([(value, ThermoEffect(0.0, 0.0))])


# ======================================================================================
# The engine. Verbatim from engine.py:7-159 @ ef4f533. Defects intact by design.
# ======================================================================================
def propose_bond(situated_reactants: Situated[Species]) -> Reaction[Species]:
    """
    The original bonding heuristic.

    Preserved unchanged, including every defect the review found in it: it builds the
    product from only two elements (F1), returns an endomorphism on the composition bag
    with no bond topology (F11), gates on a hardcoded ``valence_cap`` before the
    ionization arithmetic can run (F7), and carries a covalent scaling constant fitted on
    two data points (F5, the ``0.1`` below).

    Do not fix these. They are what the benchmark measures.
    """
    reactants = situated_reactants.extract()
    env = situated_reactants.env

    atoms_list = list(reactants.comp_dict.keys())

    if len(atoms_list) == 1:
        # Homonuclear bond (O2, H2, metallic matrix)
        a = b = atoms_list[0]
        count_a = reactants.comp_dict[a] // 2
        count_b = reactants.comp_dict[a] - count_a
        if count_a == 0:
            return Reaction.pure(reactants)
    else:
        # Star-graph topology: the most electropositive atom is treated as central.
        atoms_sorted_by_en = sorted(atoms_list, key=lambda atom: atom.mulliken_en)
        central_atom = atoms_sorted_by_en[0]
        ligands = atoms_sorted_by_en[1:]

        a = central_atom
        b = ligands[0]

        count_a = reactants.comp_dict[a]
        count_b = sum(reactants.comp_dict[L] for L in ligands)

    has_external_energy = env.external_energy_ev > 0.0

    # Ligand-field endofunctor (d-orbital back-bonding).
    is_d_block_catalyst = 3 <= a.group <= 12
    ligand_field_stabilization = 0.0
    hsab_modifier = 1.0

    if is_d_block_catalyst and len(atoms_list) >= 2:
        hsab_modifier = 0.05
        ligand_field_stabilization = 15.0 * (count_b / max(1, count_a))

    if a != b and not has_external_energy:
        energy = Poset.charge_transfer_energy(a, b)
        penalty = Poset.hsab_penalty(a, b) * hsab_modifier * 0.1
        if energy >= -penalty and not is_d_block_catalyst:
            return Reaction.pure(reactants)

    donor, acceptor = a, b
    donor_count, acceptor_count = count_a, count_b

    outcomes = []

    for n in range(1, 7):
        electrons_per_donor = n / donor_count
        electrons_per_acceptor = n / acceptor_count

        if not electrons_per_donor.is_integer() or not electrons_per_acceptor.is_integer():
            continue

        if electrons_per_donor > donor.valence_cap or electrons_per_acceptor > acceptor.valence_cap:
            continue

        e_per_donor = int(electrons_per_donor)
        e_per_acceptor = int(electrons_per_acceptor)

        ionization_cost_ev = donor.ionization_cost(e_per_donor) * donor_count
        affinity_gain_ev = acceptor.affinity_gain(e_per_acceptor) * acceptor_count

        if ionization_cost_ev == float("inf") or affinity_gain_ev == -float("inf"):
            continue

        # 1. Ionic mechanism
        atomic_cost_ev = ionization_cost_ev - affinity_gain_ev
        solv_donor = situated_reactants.born_solvation_energy_ev(
            +e_per_donor, donor.radius_pm) * donor_count
        solv_acceptor = situated_reactants.born_solvation_energy_ev(
            -e_per_acceptor, acceptor.radius_pm) * acceptor_count
        ionic_h = atomic_cost_ev + solv_donor + solv_acceptor

        # 2. Covalent / exchange mechanism
        if donor == acceptor:
            # The hand-fitted constant. 0.1 was chosen to map H2 to 4.5 eV and F2 to 1.6 eV
            # -- two data points. This is finding F5 in its original habitat.
            base_covalent = (donor.mulliken_en * donor.hardness) * n * 0.1
        else:
            overlap_factor = 200.0 / (donor.radius_pm + acceptor.radius_pm)
            base_covalent = -Poset.charge_transfer_energy(donor, acceptor) * n * 15.0 * overlap_factor

        # Lone-pair repulsion (Pauli exclusion)
        lp_donor = max(0, donor.group - 14)
        lp_acceptor = max(0, acceptor.group - 14)
        repulsion_constant = 12000.0
        dist_pm = donor.radius_pm + acceptor.radius_pm
        pauli_repulsion = (lp_donor * lp_acceptor * repulsion_constant) / (dist_pm ** 2)

        # Promotion functor: the inert-pair effect
        promotion_penalty = 0.0
        if donor != acceptor:
            promotion_penalty = max(0.0, atomic_cost_ev * 0.15)

        covalent_h = -base_covalent + pauli_repulsion + promotion_penalty

        bonding_h = min(ionic_h, covalent_h)
        mechanism_name = "Ionic" if bonding_h == ionic_h else "Covalent/Exchange"

        if is_d_block_catalyst:
            mechanism_name += " + Ligand Field Back-Bonding"

        total_atoms = donor_count + acceptor_count
        steric_penalty = 0.0
        if total_atoms > 6:
            steric_penalty = (total_atoms ** 2) * 2.0
            if env.pressure_atm > 100_000:
                steric_penalty -= (env.pressure_atm / 100_000) * 1.5
            steric_penalty = max(0.0, steric_penalty)

        hsab_penalty = Poset.hsab_penalty(donor, acceptor) * (n ** 1.5) * hsab_modifier

        delta_h_ev = (bonding_h + (hsab_penalty * 0.1) + steric_penalty
                      - env.external_energy_ev - ligand_field_stabilization)

        delta_s_ev_k = -0.002   # dimerization

        effect = ThermoEffect(delta_h_ev, delta_s_ev_k)
        # F1/F11 live on this line: the product is built from two elements only, as a bare
        # composition bag with no bond topology.
        product = Species.from_dict({a: reactants.comp_dict[a], b: reactants.comp_dict[b]},
                                    charge=0)
        outcomes.append(((product, n, mechanism_name), effect))

    # Pick the n that minimises delta_g. This ordinary loop is what the original called
    # "collapse of the superposition of states"; no monadic bind was ever involved.
    best_outcome = None
    best_effect = None
    best_dg = float("inf")

    for (prod, n, mech), effect in outcomes:
        dg = effect.get_delta_g(env.temperature_k)
        if dg < best_dg:
            best_dg = dg
            best_outcome = (prod, n, mech)
            best_effect = effect

    if best_dg > 0 or best_outcome is None:
        return Reaction.pure(reactants)

    final_product, final_n, final_mech = best_outcome
    return Reaction([(final_product, best_effect)],
                    metadata={"transfer_n": final_n, "mechanism": final_mech})

