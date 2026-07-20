from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_reaction, propose_bond

def test_failures():
    print("=== AGGRESSIVE PROBING ===\n")
    env = Env.standard()
    
    # Test 1: Xenon and Carbon
    print("--- Test 1: Xenon and Carbon ---")
    xe_c = Species.from_dict({PT["Xe"]: 1, PT["C"]: 1})
    reaction_1 = verify_reaction(Situated(xe_c, env))
    if reaction_1:
        print("FAIL: Model falsely predicted Xenon binds to Carbon!")
    else:
        print("PASS: Xenon and Carbon remained inert.")

    # Test 2: Fluorine Lone Pair Repulsion
    print("\n--- Test 2: F2 Bond Strength ---")
    f2 = Species.from_dict({PT["F"]: 2})
    reaction_2 = verify_reaction(Situated(f2, env))
    if reaction_2:
        for prod, eff in reaction_2.outcomes:
            print(f"F2 Bond Enthalpy predicted: {eff.delta_h_ev:.2f} eV")
            if eff.delta_h_ev < -5.0:
                print("FAIL: Model predicts F2 is insanely strong! Real F2 bond is only -1.6 eV.")

    # Test 3: Lead Inert Pair Effect (PbI4 vs PbI2)
    print("\n--- Test 3: Lead Inert Pair Effect (PbI4 vs PbI2) ---")
    pb_i4 = Species.from_dict({PT["Pb"]: 1, PT["I"]: 4})
    reaction_3 = verify_reaction(Situated(pb_i4, env))
    
    print("\n--- Test 4: PbI2 ---")
    pb_i2 = Species.from_dict({PT["Pb"]: 1, PT["I"]: 2})
    reaction_4 = verify_reaction(Situated(pb_i2, env))

if __name__ == "__main__":
    test_failures()
