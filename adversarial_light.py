from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_photolysis, verify_reaction

def test_radiation():
    print("=== RADIATION & PHOTOLYSIS TEST ===\n")
    
    o = PT["O"]
    cl = PT["Cl"]
    
    # Let's test Ozone (O3) in the stratosphere
    print("--- Test 1: Ozone Depletion (Stratosphere UV) ---")
    o3 = Species.from_dict({o: 3})
    
    # 1a. Stratosphere without UV light (simulated by setting photon_wavelength_nm to inf)
    env_dark = Env(220.0, 0.01, "Stratosphere", 1.0, float('inf'))
    res_dark = verify_photolysis(Situated(o3, env_dark))
    if not res_dark:
        print("Dark Stratosphere: O3 remains stable.")
        
    # 1b. Stratosphere with UV light (248 nm)
    env_uv = Env.upper_atmosphere() # 248 nm photon
    res_uv = verify_photolysis(Situated(o3, env_uv))
    
    print("\n--- Test 2: Chlorine Gas Cleavage (Cl2 -> 2Cl) ---")
    cl2 = Species.from_dict({cl: 2})
    # Cl2 is relatively weak. Let's see if a 400nm (visible/violet) photon breaks it.
    env_violet = Env(298.15, 1.0, "Vacuum", 1.0, 400.0)
    res_violet = verify_photolysis(Situated(cl2, env_violet))
    
    # 1c. Nitrogen Gas Cleavage (N2 is incredibly strong, shouldn't break with 400nm)
    # We didn't add N2 to PT yet, let's just use O2.
    print("\n--- Test 3: O2 Stability under Violet Light ---")
    o2 = Species.from_dict({o: 2})
    res_o2 = verify_photolysis(Situated(o2, env_violet))

if __name__ == "__main__":
    test_radiation()
