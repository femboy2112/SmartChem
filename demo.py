#!/usr/bin/env python3
from smartchem import PT, Species, Env, Situated, verify_reaction

def main():
    print("=== SmartChem: Categorical Engine for the Periodic Table (Comprehensive) ===\n")
    
    # 1. Base atoms (Bleeding Edge: Hard/Soft Acid Base & Born Solvation)
    na = PT["Na"]
    cl = PT["Cl"]
    c = PT["C"]
    he = PT["He"]
    fe = PT["Fe"]
    o = PT["O"]
    
    # 2. Form Monoidal objects (A ⊗ B)
    reactants_1 = Species.from_dict({na: 1}) + Species.from_dict({cl: 1})
    reactants_2 = Species.from_dict({c: 1}) + Species.from_dict({he: 1})
    reactants_3 = Species.from_dict({fe: 1}) + Species.from_dict({o: 1})
    
    # 3. Context Comonad W
    env_vacuum = Env.standard()
    env_aqueous = Env.aqueous(temp_k=298.15)
    env_cryo = Env.cryogenic()
    
    # W(A ⊗ B)
    w_sys_1_vac = Situated(reactants_1, env_vacuum)
    w_sys_1_aq = Situated(reactants_1, env_aqueous)
    w_sys_2 = Situated(reactants_2, env_vacuum) 
    w_sys_3_aq = Situated(reactants_3, env_aqueous)
    w_sys_1_cryo = Situated(reactants_1, env_cryo)
    
    # 4. Gate / Oracle Evaluation
    print("Test 1: Na ⊗ Cl in Vacuum (Standard)")
    verify_reaction(w_sys_1_vac)
    
    print("\nTest 2: Na ⊗ Cl in Water (Aqueous Comonad - Solvation heavily stabilizes ions)")
    verify_reaction(w_sys_1_aq)
    
    print("\nTest 3: C ⊗ He in Vacuum (Noble gas inertness via Mulliken hardness)")
    verify_reaction(w_sys_2)
    
    print("\nTest 4: Fe ⊗ O in Water (Rusting / Oxidation)")
    verify_reaction(w_sys_3_aq)
    
    print("\nTest 5: Na ⊗ Cl in Liquid Helium (Cryogenic Entropy limit)")
    verify_reaction(w_sys_1_cryo)

if __name__ == "__main__":
    main()
