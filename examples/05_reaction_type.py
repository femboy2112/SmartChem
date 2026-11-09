"""Example 05 -- the reaction-TYPE oracle names a class for a real route step, or ABSTAINs.

Shows: search_event_routes finds ethyl acetate from acetic acid + ethanol (+ water); recognize_reaction_type
names the step's class.  A conserved but unsupported step (ethanol -> ethene + water) returns None: honest
non-recognition ("not in the attested set"), never a claim that the reaction is impossible.
"""
from smartchem.experiment.event_search import search_event_routes
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles as P


def main() -> int:
    result = search_event_routes(P("CC(=O)OCC"), reagents=(P("O"),), available=(P("CC(=O)O"), P("CCO")),
                                 max_depth=2, max_routes=10)
    print(f"routes={len(result.routes)} search_complete={result.receipt.complete}")
    names = [recognize_reaction_type(step) for route in result.routes for step in route.steps]
    for route in result.routes:
        for step in route.steps:
            print(f"  {step} -> {recognize_reaction_type(step)}")
    junk = ExperimentStep.assembling(P("C=C"), (P("CCO"),), (P("C=C"), P("O")))
    print(f"unsupported step {junk} -> {recognize_reaction_type(junk)}")
    return 0 if names and None not in names and recognize_reaction_type(junk) is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
