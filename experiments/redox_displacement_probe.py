"""REDOX-DISPLACE-01 committed demonstration: the coupled half-reaction combiner reaches 1:2.

A MEASURED claim lives in a committed harness, not a throwaway script.  The claim here: the two-species
redox displacement combiner ENUMERATES ``Cl2 + 2 Br- -> Br2 + 2 Cl-`` -- the exact reaction the DOW
litmus's synthesis needs and the exact reaction recon PROVED no prior mechanism can produce
(single-species ``redox_edges`` is charge-only on identical atoms; ``capped_scissions`` ties cuts 1:1
and refuses charged input).  It also demonstrates electron-count balancing on a NON-trivial LCM case
(``2 Fe3+ + Sn2+ -> 2 Fe2+ + Sn4+``), so the 1:2 is not hardcoded.

The demonstration is deterministic, so its output is tamper-pinned by a frozen digest: re-run
``python -m experiments.redox_displacement_probe`` after an INTENTIONAL mechanism change and set
``FROZEN_HASH`` to the printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.category import Molecule
from smartchem.contracts import canonical_digest
from smartchem.experiment.step import ExperimentStep
from smartchem.redox_displacement import (
    HalfReactionCouple,
    RedoxDisplacementProvider,
    DISPLACEMENT_SCHEMA,
    combine_half_reactions,
    halogen_couple,
)
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY, TransformProviderRegistry

#: The committed tamper pin over the demonstration's canonical output digests.  Regenerate ONLY on an
#: intentional change: ``python -m experiments.redox_displacement_probe`` and paste the printed value.
FROZEN_HASH = "8ceea741909539b86e198879c7f8648ddf2b484af2535f0f0176a5ce3ea6ab82"


def dow_displacement():
    """The DOW displacement as a transform: Cl2 oxidises bromide to elemental Br2 (the target)."""
    cl, br = halogen_couple("Cl"), halogen_couple("Br")
    br2 = Molecule.diatomic("Br", "Br")
    return combine_half_reactions(reduction=cl, oxidation=br, target=br2)


def nontrivial_lcm_displacement():
    """A non-trivial electron balance (LCM(1,2)=2): 2 Fe3+ + Sn2+ -> 2 Fe2+ + Sn4+ (target Sn4+)."""
    fe = HalfReactionCouple(DISPLACEMENT_SCHEMA, "Fe",
                            (Molecule.atom("Fe", charge=3),), (Molecule.atom("Fe", charge=2),), 1)
    sn = HalfReactionCouple(DISPLACEMENT_SCHEMA, "Sn",
                            (Molecule.atom("Sn", charge=4),), (Molecule.atom("Sn", charge=2),), 2)
    return combine_half_reactions(reduction=fe, oxidation=sn, target=Molecule.atom("Sn", charge=4))


def enumerated_via_registry():
    """The displacement, enumerated through the UNCHANGED registry seam (an opt-in wider algebra)."""
    cl, br = halogen_couple("Cl"), halogen_couple("Br")
    registry = TransformProviderRegistry(
        DEFAULT_TRANSFORM_REGISTRY.providers + (RedoxDisplacementProvider(couples=(cl, br)),)
    )
    br2, cl2 = Molecule.diatomic("Br", "Br"), Molecule.diatomic("Cl", "Cl")
    transforms, complete = registry.enumerate(br2, (cl2,), budget=64)
    return transforms, complete, registry


def content_hash() -> str:
    dow = dow_displacement()
    lcm = nontrivial_lcm_displacement()
    payload = {
        "dow_edge": dow.digest,
        "dow_forget": dow.forget().digest,
        "dow_synthesis": ExperimentStep.from_transform(dow).digest,
        "lcm_edge": lcm.digest,
        "lcm_electrons": lcm.electrons_transferred,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the demonstration does not hold: the DOW displacement is enumerated, conserves, and is
    1:2; the non-trivial LCM balances; and the family is absent from the DEFAULT registry."""
    dow = dow_displacement()
    synth = ExperimentStep.from_transform(dow)
    # 1:2 stoichiometry, exact species (the reaction no prior mechanism could produce).
    from collections import Counter
    lhs = Counter((tuple(sorted(m.formula.items())), m.charge) for m in synth.reactants)
    rhs = Counter((tuple(sorted(m.formula.items())), m.charge) for m in synth.products)
    assert lhs == Counter({((("Cl", 2),), 0): 1, ((("Br", 1),), -1): 2}), f"unexpected LHS {dict(lhs)}"
    assert rhs == Counter({((("Br", 2),), 0): 1, ((("Cl", 1),), -1): 2}), f"unexpected RHS {dict(rhs)}"
    assert dow.electrons_transferred == 2
    # non-trivial LCM: the reduction couple is scaled x2 (2 Fe3+ / 2 Fe2+), electrons_transferred == 2.
    lcm = nontrivial_lcm_displacement()
    assert lcm.electrons_transferred == 2
    lcm_synth = ExperimentStep.from_transform(lcm)
    fe3 = sum(1 for m in lcm_synth.reactants if m.formula == {"Fe": 1} and m.charge == 3)
    assert fe3 == 2, f"expected 2 Fe3+ on the LHS (LCM scaling), got {fe3}"
    # enumerated through the UNCHANGED registry; DEFAULT stays capped-only.
    transforms, complete, _ = enumerated_via_registry()
    assert complete is True
    assert any(et.witness_kind == "REDOX_DISPLACEMENT" for et in transforms), "displacement not enumerated"
    assert DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",), "DEFAULT registry mutated"


def report() -> dict:
    dow = dow_displacement()
    return {
        "dow_synthesis": ExperimentStep.from_transform(dow).equation(),
        "dow_electrons_transferred": dow.electrons_transferred,
        "nontrivial_lcm_synthesis": ExperimentStep.from_transform(nontrivial_lcm_displacement()).equation(),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
        "default_registry_unchanged": DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",),
    }


if __name__ == "__main__":
    validate()
    r = report()
    for key, value in r.items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
    print(f"canonical_digest of the DOW edge: {canonical_digest(dow_displacement())}")
