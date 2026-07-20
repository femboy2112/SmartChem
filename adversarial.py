from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_reaction
from smartchem.network import ReactionGraph

def run_adversarial():
    print("=== ADVERSARIAL PHYSICS TEST ===\n")
    
    # 1. Homonuclear Diatomics (The O2 / H2 failure)
    print("--- Test 1: Homonuclear Covalent Bonds ---")
    o = PT["O"]
    flask_o2 = Species.from_dict({o: 2}) # O + O -> O2
    res_o2 = verify_reaction(Situated(flask_o2, Env.standard()))
    print(f"O2 Formation: {'CERTIFIED' if res_o2 else 'FAILED (Inert)'}")
    
    # 2. Hypervalency / Steric Explosion (Can it form NaF10 ?)
    print("\n--- Test 2: Hypervalency Explosion (NaF10) ---")
    f = PT["F"]
    na = PT["Na"]
    flask_naf10 = Species.from_dict({na: 1, f: 10})
    res_naf10 = verify_reaction(Situated(flask_naf10, Env.standard()))
    print(f"NaF10 Formation: {'CERTIFIED (DANGER: Physics broken)' if res_naf10 else 'REFUTED (Safe)'}")
    
    # 3. Metallic Hydrogen (Deep reality edge case)
    # At extreme pressures (e.g. 5 million atm in Jupiter's core), Hydrogen becomes metallic.
    # We simulate this via a Comonad with immense external energy and dense packing.
    print("\n--- Test 3: Metallic Hydrogen Phase ---")
    h = PT["H"]
    flask_h4 = Species.from_dict({h: 4}) 
    # High pressure Comonad
    env_jupiter = Env(temperature_k=5000, pressure_atm=5_000_000, solvent_name="Metallic Plasma", solvent_dielectric=1000.0, external_energy_ev=15.0)
    res_h_metal = verify_reaction(Situated(flask_h4, env_jupiter))
    print(f"Metallic H4 Matrix: {'CERTIFIED' if res_h_metal else 'REFUTED'}")

if __name__ == "__main__":
    run_adversarial()
