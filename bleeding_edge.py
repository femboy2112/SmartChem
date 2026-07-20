from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_phase_state, verify_crystal_lattice

def probe_reality():
    print("=== PROBING THE EDGES OF EXPERIMENTAL REALITY ===\n")
    
    o = PT["O"]
    h = PT["H"]
    og = PT["Og"]
    
    print("--- 1. Ice XVIII (Superionic Water) in Neptune's Core ---")
    water = Species.from_dict({h: 2, o: 1})
    
    env_std = Env.standard()
    print("\n[Standard Conditions]")
    verify_phase_state(Situated(water, env_std))
    
    # Neptune Core: ~100 GPa (1,000,000 atm) and ~2000 K
    env_neptune = Env(2000.0, 1_000_000.0, "Superionic Core", 0.0, 0.0)
    print("\n[Neptune Core Conditions: 2000K, 1,000,000 atm]")
    verify_phase_state(Situated(water, env_neptune))
    
    print("\n--- 2. The Island of Stability: Oganesson (Z=118) ---")
    print("Standard periodic rules dictate Og is a Noble Gas (Group 18).")
    print("Relativistic Dirac-Fock predicts it is a solid semiconductor.")
    
    og_species = Species.from_dict({og: 1})
    
    print("\n[Evaluating the Topological Colimit of Og]")
    # Group 18, so normally Z=12 (FCC or HCP like other noble gases if frozen)
    verify_crystal_lattice(Situated(og_species, env_std), z_coordination=12)

if __name__ == "__main__":
    probe_reality()
