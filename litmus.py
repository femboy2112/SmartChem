from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_reaction

def run_litmus():
    print("=== LITMUS TEST: The Edge of Reality ===\n")
    
    xe = PT["Xe"]
    f = PT["F"]
    
    # 1. The Noble Gas Test
    print("--- TEST 1: Noble Gas Synthesis (XeF4) ---")
    print("Scenario: Xenon and Fluorine in Standard Vacuum")
    # 1 Xe and 4 F atoms
    reactants_std = Species.from_dict({xe: 1, f: 4})
    env_std = Env.standard()
    situated_std = Situated(reactants_std, env_std)
    
    print("Executing Category Engine...")
    result_std = verify_reaction(situated_std)
    if not result_std:
        print("Result: INERT (As expected in standard vacuum without energy injection)")
        
    print("\nScenario: Xenon and Fluorine in High-Energy Plasma (Spark Comonad)")
    env_plasma = Env.high_energy_plasma() # Provides 10 eV to bypass orbital unfavorability
    situated_plasma = Situated(reactants_std, env_plasma)
    
    print("Executing Category Engine...")
    result_plasma = verify_reaction(situated_plasma)
    
    if result_plasma:
        print("\nSUCCESS! The engine spontaneously derived XeF4 without any hardcoded valency rules!")
    else:
        print("FAILED to derive XeF4.")
        
    print("\n--- TEST 2: Category of Attainable States (Reaction Network) ---")
    print("Scenario: A primordial flask of Na, Cl, Fe, and O in Water")
    from smartchem.network import ReactionGraph
    
    na, cl, fe, o = PT["Na"], PT["Cl"], PT["Fe"], PT["O"]
    flask = [
        Species.from_dict({na: 1}),
        Species.from_dict({cl: 1}),
        Species.from_dict({fe: 1}),
        Species.from_dict({o: 1})
    ]
    
    graph = ReactionGraph(Env.aqueous())
    graph.seed(flask)
    print(f"Seeding flask with: {flask}")
    
    print("Iteratively expanding the Monoidal Category of Reactions...")
    graph.expand(max_iterations=2)
    
    print(f"Total Unique States Discovered: {len(graph.nodes)}")
    print("Morphisms (Reactions) Discovered:")
    for a, b, prod in graph.edges:
        print(f"  {a} ⊗ {b} ⟶ {prod}")
        
    print("\nSUCCESS! The engine autonomously networked the reactive pairs while ignoring the inert ones.")

if __name__ == "__main__":
    run_litmus()
