from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_phase_state, verify_reaction

def test_subatomic():
    print("=== THE SUBATOMIC FUNCTOR: ISOTOPES AND TRANSMUTATION ===\n")
    
    h = PT["H"]
    d = PT["D"]
    t = PT["T"]
    he = PT["He"]
    c = PT["C"]
    o = PT["O"]
    
    env_neptune = Env(2000.0, 1_000_000.0, "Superionic Core", 0.0, 0.0)
    
    print("--- 1. The Kinetic Isotope Effect (Quantum Tunneling) ---")
    water = Species.from_dict({h: 2, o: 1})
    heavy_water = Species.from_dict({d: 2, o: 1})
    
    print("\n[H2O (Protium) under 2000K, 1M atm]")
    verify_phase_state(Situated(water, env_neptune))
    
    print("\n[D2O (Deuterium) under 2000K, 1M atm]")
    verify_phase_state(Situated(heavy_water, env_neptune))
    
    print("\n--- 2. Beta Decay Transmutation (Tritium) ---")
    tritiated_methane = Species.from_dict({c: 1, t: 4})
    print(f"Original Topology: {tritiated_methane}")
    
    print("\n[Tritium nucleus undergoes Beta Decay (n -> p + e-)]")
    # T -> He
    mutated_methane = tritiated_methane.beta_decay(t, he)
    print(f"Mutated Topology: {mutated_methane}")
    
    print("\n[Evaluating Stability of Mutated Topology]")
    env_std = Env.standard()
    verify_reaction(Situated(mutated_methane, env_std))

if __name__ == "__main__":
    test_subatomic()
