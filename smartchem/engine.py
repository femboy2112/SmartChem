from typing import Optional
from .atoms import Species
from .lattice import Poset
from .comonad import Situated
from .monad import Reaction, ThermoEffect

def propose_bond(situated_reactants: Situated[Species]) -> Reaction[Species]:
    """
    The Categorical Functor F: Multi-Electron State Search using Exact Thermodynamics.
    """
    reactants = situated_reactants.extract()
    env = situated_reactants.env

    atoms_list = list(reactants.comp_dict.keys())
    
    if len(atoms_list) == 1:
        # Homonuclear bond (O2, H2, Metallic Matrix)
        a = b = atoms_list[0]
        count_a = reactants.comp_dict[a] // 2
        count_b = reactants.comp_dict[a] - count_a
        if count_a == 0:
            return Reaction.pure(reactants)
    else:
        # Star Graph Topology (Find the Central Metal / Most electropositive atom)
        atoms_sorted_by_en = sorted(atoms_list, key=lambda atom: atom.mulliken_en)
        central_atom = atoms_sorted_by_en[0]
        ligands = atoms_sorted_by_en[1:]
        
        # For simplicity in this toy model, we treat all ligands as a single 'pseudo-acceptor' pool
        # This simulates the Ligand Field mathematically.
        a = central_atom
        # We'll just grab the primary ligand for heuristic properties
        b = ligands[0]
        
        count_a = reactants.comp_dict[a]
        # Sum all ligand counts
        count_b = sum(reactants.comp_dict[L] for L in ligands)

    has_external_energy = env.external_energy_ev > 0.0
    
    # ---------------------------------------------------------
    # Ligand Field Endofunctor (d-orbital Back-Bonding)
    # Transition metals (Groups 3-12) can back-donate to ligands, suppressing HSAB mismatch.
    is_d_block_catalyst = 3 <= a.group <= 12
    ligand_field_stabilization = 0.0
    hsab_modifier = 1.0
    
    if is_d_block_catalyst and len(atoms_list) >= 2:
        # The metal shares its d-electrons, drastically reducing hardness mismatch
        hsab_modifier = 0.05  # 95% reduction in mismatch penalty!
        # Back-bonding provides massive thermodynamic stabilization
        ligand_field_stabilization = 15.0 * (count_b / max(1, count_a)) 
    # ---------------------------------------------------------
    
    if a != b and not has_external_energy:
        # We apply the modified HSAB penalty to the Lattice Gate
        energy = Poset.charge_transfer_energy(a, b)
        penalty = Poset.hsab_penalty(a, b) * hsab_modifier * 0.1  # 0.1 is the thermodynamic scaling factor
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
        
        if ionization_cost_ev == float('inf') or affinity_gain_ev == -float('inf'):
            continue 

        # 1. Ionic Mechanism
        atomic_cost_ev = ionization_cost_ev - affinity_gain_ev
        solv_donor = situated_reactants.born_solvation_energy_ev(+e_per_donor, donor.radius_pm) * donor_count
        solv_acceptor = situated_reactants.born_solvation_energy_ev(-e_per_acceptor, acceptor.radius_pm) * acceptor_count
        ionic_h = atomic_cost_ev + solv_donor + solv_acceptor
        
        # 2. Covalent / Exchange Mechanism
        if donor == acceptor:
            # Fixed scaling: 0.1 is the exact value that correctly maps H2 to 4.5eV and F2 to 1.6eV
            base_covalent = (donor.mulliken_en * donor.hardness) * n * 0.1
        else:
            # Orbital overlap decays with distance. C-F is short and strong. Pb-F is long and weak.
            overlap_factor = 200.0 / (donor.radius_pm + acceptor.radius_pm)
            base_covalent = -Poset.charge_transfer_energy(donor, acceptor) * n * 15.0 * overlap_factor
            
        # The Lone Pair Repulsion Functor (Pauli Exclusion)
        # Groups 15, 16, 17 have tightly packed non-bonding electrons that violently repel
        lp_donor = max(0, donor.group - 14)
        lp_acceptor = max(0, acceptor.group - 14)
        repulsion_constant = 12000.0
        dist_pm = donor.radius_pm + acceptor.radius_pm
        pauli_repulsion = (lp_donor * lp_acceptor * repulsion_constant) / (dist_pm ** 2)
        
        # Promotion Functor: Captures the Inert Pair Effect by penalizing covalent sharing 
        # based on the ionization cost required to promote electrons into bonding orbitals.
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
        if total_atoms > 6: # Increased to 6 for octahedral metal complexes
            steric_penalty = (total_atoms ** 2) * 2.0
            if env.pressure_atm > 100_000:
                steric_penalty -= (env.pressure_atm / 100_000) * 1.5
            steric_penalty = max(0.0, steric_penalty)

        hsab_penalty = Poset.hsab_penalty(donor, acceptor) * (n ** 1.5) * hsab_modifier
        
        delta_h_ev = bonding_h + (hsab_penalty * 0.1) + steric_penalty - env.external_energy_ev - ligand_field_stabilization

        
        # Entropy change (dimerization)
        delta_s_ev_k = -0.002 
        
        effect = ThermoEffect(delta_h_ev, delta_s_ev_k)
        product = Species.from_dict({a: reactants.comp_dict[a], b: reactants.comp_dict[b]}, charge=0)
        print(f"DEBUG LOOP: n={n} covalent_h={covalent_h} ionic_h={ionic_h} pauli={pauli_repulsion}")
        outcomes.append(((product, n, mechanism_name), effect))

    # Pick the state (n) that minimizes delta_g (maximum stability)
    best_outcome = None
    best_effect = None
    best_dg = float('inf')
    
    for (prod, n, mech), effect in outcomes:
        dg = effect.get_delta_g(env.temperature_k)
        if dg < best_dg:
            best_dg = dg
            best_outcome = (prod, n, mech)
            best_effect = effect
            
    if best_dg > 0 or best_outcome is None:
        return Reaction.pure(reactants)
        
    final_product, final_n, final_mech = best_outcome
    return Reaction([(final_product, best_effect)], metadata={"transfer_n": final_n, "mechanism": final_mech})

def verify_reaction(situated_reactants: Situated[Species]) -> Optional[Reaction]:
    reaction = propose_bond(situated_reactants)
    reactants = situated_reactants.extract()
    env = situated_reactants.env
    temp_k = situated_reactants.env.temperature_k
    solvent = situated_reactants.env.solvent_name
    
    for outcome, effect in reaction.outcomes:
        if effect.delta_h_ev == 0.0 and effect.delta_s_ev_k == 0.0:
            print(f"Reaction REFUTED: {reactants} atoms cannot bond and remain completely dissociated under {env.solvent_name} at {env.temperature_k}K.")
            return None
            
        if effect.is_spontaneous(temp_k):
            dg = effect.get_delta_g(temp_k)
            k_eq = effect.equilibrium_constant(temp_k)
            n_val = getattr(reaction, 'metadata', {}).get("transfer_n", 1)
            mech_type = getattr(reaction, 'metadata', {}).get("mechanism", "Ionic")
            
            print(f"Reaction CERTIFIED: {situated_reactants.extract()} -> {outcome} in {solvent}")
            print(f"  ├─ Mechanism: {mech_type} bonding collapsed at n={n_val} electron transfer state.")
            print(f"  └─ Thermodynamics: ΔG = {dg:.3f} eV, ΔH = {effect.delta_h_ev:.3f} eV, K_eq = {k_eq:.2e}")
            return reaction
            
        else:
            dg = effect.get_delta_g(temp_k)
            print(f"Reaction REFUTED: {situated_reactants.extract()} -> {outcome} has non-spontaneous ΔG = {dg:.3f} eV at {temp_k}K in {solvent}.")
            return None

def verify_photolysis(situated_reactants: Situated[Species]) -> Optional[Reaction]:
    """
    Categorical Decomposition (Photolysis):
    A morphism where a complex Object is shattered into its constituent parts by the Comonad.
    """
    reactants = situated_reactants.extract()
    env = situated_reactants.env
    
    if env.photon_wavelength_nm == float('inf'):
        return None # No light, no photolysis
        
    atoms_list = list(reactants.comp_dict.keys())
    total_atoms = sum(reactants.comp_dict.values())
    
    if total_atoms <= 1:
        return None # Single atoms cannot be photolyzed
        
    # Estimate single bond dissociation energy using chemical hardness
    # (e.g., O2 is ~5 eV, Cl2 is ~2.5 eV)
    avg_hardness = sum(a.hardness * count for a, count in reactants.comp_dict.items()) / total_atoms
    avg_bond_energy_ev = avg_hardness * 0.8
    
    # If the single photon has enough energy to cleave a bond
    if env.photon_energy_ev > avg_bond_energy_ev:
        # Split into individual atoms (a radical pool)
        radical_outcomes = []
        for atom, count in reactants.comp_dict.items():
            for _ in range(count):
                radical_outcomes.append(Species.from_dict({atom: 1}))
        
        # The thermodynamic effect of photolysis is massively endothermic (it absorbs the photon)
        # but driven forward by the massive comonadic photon injection
        delta_h_ev = avg_bond_energy_ev - env.photon_energy_ev
        delta_s_ev_k = 0.002 * total_atoms # Massive entropy gain from shattering
        effect = ThermoEffect(delta_h_ev, delta_s_ev_k)
        
        dg = effect.get_delta_g(env.temperature_k)
        if dg < 0:
            print(f"Photolysis CERTIFIED: {reactants} shattered by {env.photon_wavelength_nm}nm photon!")
            print(f"  ├─ Mechanism: Homolytic Cleavage via {env.photon_energy_ev:.2f} eV photon.")
            print(f"  └─ Thermodynamics: ΔG = {dg:.3f} eV, Cohesive Barrier = {avg_bond_energy_ev:.2f} eV")
            return Reaction([(tuple(radical_outcomes), effect)], metadata={"mechanism": "Photolysis"})
    
    print(f"Photolysis REFUTED: {reactants} survives {env.photon_wavelength_nm}nm photon (Bond = {avg_bond_energy_ev:.2f} eV, Photon = {env.photon_energy_ev:.2f} eV).")
    return None

def verify_crystal_lattice(situated_reactants: Situated[Species], z_coordination: int) -> float:
    """
    Evaluates the Colimit of the Species as N -> infinity (Infinite Crystal Lattice).
    Returns the Band Gap (Eg) in eV.
    If Eg <= 0, the material is a Metal/Conductor.
    If 0 < Eg <= 3.0, the material is a Semiconductor.
    If Eg > 3.0, the material is an Insulator.
    """
    reactants = situated_reactants.extract()
    env = situated_reactants.env
    
    atoms_list = list(reactants.comp_dict.keys())
    if len(atoms_list) != 1:
        raise ValueError("Crystal lattice Colimit currently only supports elemental crystals.")
        
    a = atoms_list[0]
    
    # 1. Valence vs Coordination (Half-filled band check)
    if 13 <= a.group <= 18:
        valence_electrons = a.group - 10
    else:
        valence_electrons = a.group
        
    # If the coordination number leaves valence electrons unbound, they form a half-filled 
    # conduction band (e.g. Graphene Z=3 vs Valence=4).
    if z_coordination < valence_electrons:
        print(f"Colimit CERTIFIED: {a.symbol} at Z={z_coordination} has unbound electrons.")
        print(f"  ├─ Phase: Metal (Half-filled conduction band)")
        print(f"  └─ Band Gap: 0.00 eV")
        return 0.0
        
    # 2. The Hubbard U (Inertial Resistance to electron hopping)
    hubbard_u = a.ie_list_ev[0] - a.ea_list_ev[0]
    
    # 3. Delocalization Functor (Dispersion of the band driven by Electronegativity / Hardness)
    # The pressure comonad compresses the lattice, increasing coordination effectively
    effective_z = z_coordination
    if env.pressure_atm > 100_000:
        effective_z += (env.pressure_atm / 100_000) * 0.5
        
    delocalization_energy = (effective_z * a.mulliken_en) / a.hardness
    
    # Band Gap = Inertia - Dispersion
    eg = hubbard_u - delocalization_energy
    
    if eg <= 0:
        print(f"Colimit CERTIFIED: {a.symbol} at Z={z_coordination} disperses into a Metallic state.")
        print(f"  ├─ Phase: Metal (Conductor)")
        print(f"  └─ Band Gap: 0.00 eV (Overlap = {abs(eg):.2f} eV)")
        return 0.0
    elif eg <= 3.0:
        print(f"Colimit CERTIFIED: {a.symbol} at Z={z_coordination} forms a Semiconductor.")
        print(f"  ├─ Phase: Semiconductor")
        print(f"  └─ Band Gap: {eg:.2f} eV")
        return eg
    else:
        print(f"Colimit CERTIFIED: {a.symbol} at Z={z_coordination} forms a Mott/Covalent Insulator.")
        print(f"  ├─ Phase: Insulator")
        print(f"  └─ Band Gap: {eg:.2f} eV")
        return eg

def verify_phase_state(situated_reactants: Situated[Species]) -> str:
    """
    Evaluates the Physical Phase of the species (Solid, Liquid, Superionic, Plasma).
    Relies on the Thermal Energy (kT) overcoming the Lattice/Cohesive Bond Barrier.
    The Pressure Comonad reduces the activation barrier for ions to hop by compressing the lattice.
    """
    reactants = situated_reactants.extract()
    env = situated_reactants.env
    
    atoms_list = list(reactants.comp_dict.keys())
    
    # Thermal energy in eV
    k_B = 8.617e-5
    thermal_energy_ev = k_B * env.temperature_k
    
    melted_atoms = set()
    solid_atoms = set()
    
    import math
    for atom in atoms_list:
        # Intermolecular / Covalent Barrier
        # For simplicity, we define the hopping barrier based on hardness and radius
        base_barrier_ev = atom.hardness * (atom.radius_pm / 100.0)
        
        # Pressure Comonad: High pressure forces atoms into a symmetric potential well.
        # Small ions (like H, radius 53pm) have their barrier completely crushed by pressure.
        pressure_gpa = env.pressure_atm / 10000.0 # 1 GPa = 10k atm
        
        if pressure_gpa > 50:
            compression_factor = (pressure_gpa / 100.0) * (50.0 / atom.radius_pm)**2
            effective_barrier = max(0.0, base_barrier_ev - (base_barrier_ev * compression_factor))
        else:
            effective_barrier = base_barrier_ev
            
        # Subatomic Functor: Quantum Tunneling
        # Lighter isotopes (like Protium H vs Deuterium D) can tunnel through the barrier.
        # Tunneling probability scales with exp(-sqrt(mass * barrier))
        mass = atom.mass_amu if atom.mass_amu > 0 else (atom.atomic_number * 2.0)
        tunneling_factor = math.exp(-math.sqrt(mass * effective_barrier))
        # Tunneling reduces the perceived thermodynamic barrier to hop
        effective_barrier = effective_barrier * (1.0 - tunneling_factor)
        
        if thermal_energy_ev > effective_barrier:
            melted_atoms.add(atom)
        else:
            solid_atoms.add(atom)
            
    print(f"\nPhase Evaluation at {env.temperature_k}K and {env.pressure_atm} atm:")
    if len(solid_atoms) == len(atoms_list):
        print(f"  └─ Phase CERTIFIED: Solid/Molecular Lattice (Covalent Bonds intact).")
        return "Solid"
    elif len(melted_atoms) == len(atoms_list):
        print(f"  └─ Phase CERTIFIED: Dense Plasma / Complete Melt.")
        return "Plasma"
    else:
        print(f"  └─ Phase CERTIFIED: SUPERIONIC! (Partial Covalent Melting)")
        print(f"      ├─ Rigid Sub-Lattice: {[a.symbol for a in solid_atoms]}")
        print(f"      └─ Liquid/Plasma Mobile Ions: {[a.symbol for a in melted_atoms]}")
        return "Superionic"
