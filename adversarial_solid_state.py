from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_crystal_lattice

def test_solids():
    print("=== THE INFINITE COLIMIT: SOLID STATE PHYSICS ===\n")
    
    env_std = Env.standard()
    
    # 1. Sodium Metal (BCC Lattice, Z=8)
    print("--- Test 1: Sodium (BCC Lattice, Z=8) ---")
    na = Species.from_dict({PT["Na"]: 1})
    verify_crystal_lattice(Situated(na, env_std), z_coordination=8)
    
    # 2. Diamond (sp3 Carbon, Z=4)
    print("\n--- Test 2: Carbon (Diamond Lattice, Z=4) ---")
    c = Species.from_dict({PT["C"]: 1})
    verify_crystal_lattice(Situated(c, env_std), z_coordination=4)
    
    # 3. Graphene/Graphite (sp2 Carbon, Z=3)
    print("\n--- Test 3: Carbon (Graphene Lattice, Z=3) ---")
    verify_crystal_lattice(Situated(c, env_std), z_coordination=3)
    
    # 4. Silicon (Diamond Lattice, Z=4)
    print("\n--- Test 4: Silicon (Diamond Lattice, Z=4) ---")
    si = Species.from_dict({PT["Si"]: 1})
    verify_crystal_lattice(Situated(si, env_std), z_coordination=4)
    
    # 5. Metallization of Diamond under Jupiter's Core Pressure
    print("\n--- Test 5: Diamond under Jupiter's Core Pressure (5M atm) ---")
    env_jupiter = Env(5000.0, 5_000_000, "Metallic Plasma", 1000.0, 0.0)
    verify_crystal_lattice(Situated(c, env_jupiter), z_coordination=4)

if __name__ == "__main__":
    test_solids()
