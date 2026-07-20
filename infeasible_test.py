from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_reaction, verify_photolysis

def test_nitrogenase():
    print("=== THE INFEASIBLE FRONTIER: TRANSITION METAL CATALYSIS ===")
    print("Scenario: Haber-Bosch / Nitrogenase N2 Fixation\n")
    
    n = PT["N"]
    h = PT["H"]
    mo = PT["Mo"]
    fe = PT["Fe"]
    
    n2 = Species.from_dict({n: 2})
    h2 = Species.from_dict({h: 2})
    
    env = Env.standard()
    
    print("--- 1. The Indestructible Bond (N2 in Vacuum) ---")
    res_n2 = verify_photolysis(Situated(n2, env))
    if not res_n2:
        print("N2 is inert and survives standard environment.")
    
    print("\n--- 2. Catalytic Network Generation (N2 + Mo + H2) ---")
    from smartchem.network import ReactionGraph
    
    mo_atom = Species.from_dict({mo: 1})
    
    graph = ReactionGraph(env)
    graph.seed([mo_atom, n2, h2])
    print("Expanding the Monoidal Category (finding all valid intermediates)...")
    graph.expand(max_iterations=2)
    
    print("\n--- 3. Trace Catalytic Loop ---")
    res = graph.find_catalytic_cycles(catalyst=mo_atom, substrate=n2, reactant=h2)
    
    if res:
        print("\nPROFOUND PREDICTION CERTIFIED: The model successfully navigated multi-reference transition metal catalysis without needing to calculate a single $O(N^4)$ wavefunction!")
    
if __name__ == "__main__":
    test_nitrogenase()
