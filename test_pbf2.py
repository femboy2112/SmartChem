from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.engine import verify_reaction, propose_bond

def test_pbf2():
    env = Env.standard()
    print("\n--- Testing PbF2 ---")
    pb_f2 = Species.from_dict({PT["Pb"]: 1, PT["F"]: 2})
    reaction = verify_reaction(Situated(pb_f2, env))

if __name__ == "__main__":
    test_pbf2()
