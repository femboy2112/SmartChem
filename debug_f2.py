from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import propose_bond

def debug_f2():
    f2 = Species.from_dict({PT["F"]: 2})
    env = Env.standard()
    situated = Situated(f2, env)
    
    reaction = propose_bond(situated)
    print(f"Outcomes: {reaction.outcomes}")

if __name__ == "__main__":
    debug_f2()
