"""OBSERVABILITY-01 committed demonstration: the three-axis observability score ranks the DOW route up.

A MEASURED claim lives in a committed harness, not a throwaway script.  The claims here:

  * Elemental Br2 (the DOW displacement product) carries redundant CHEAP, chemistry-supplied success
    signatures -- an orange-red colour AND a dense phase-separated/strippable layer (Herbert Dow blew
    it out as red vapour) -- so its observability profile is (process=2, identity=1, purity=0).
  * I2 carries fewer redundant process signals (process=1, identity=1, purity=0), so Br2 Pareto-DOMINATES
    I2 on cheap observability -- a real, non-vacuous ranking.
  * The three axes NEVER collapse: a process-strong profile does NOT dominate an identity-strong one
    (they are incomparable), so a process signal never buys an identity claim (invariants 5 & 7).
  * An unsourced product (no sourced signature) is UNKNOWN and incomparable -- never fabricated, never
    ranked below a sourced route on absent evidence (section 10.4).

The demonstration is deterministic, so its output is tamper-pinned by a frozen digest: re-run
``python -m experiments.observability_probe`` after an INTENTIONAL change and set ``FROZEN_HASH`` to the
printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.category import Molecule
from smartchem.observation.observability import (
    ObservabilityAxis,
    ObservabilityProfile,
    OBSERVABILITY_SCHEMA,
    observability_dominates,
    observability_profile,
    signatures_for,
)

#: The committed tamper pin over the demonstration's canonical outputs.  Regenerate ONLY on an
#: intentional change: ``python -m experiments.observability_probe`` and paste the printed value.
FROZEN_HASH = "0a557fb10b0f7fd86b2837d413f8229d8db593dbf38929c4f49c6b84fba18bd3"

_BR2 = Molecule.diatomic("Br", "Br")
_I2 = Molecule.diatomic("I", "I")
_UNSOURCED = Molecule.diatomic("H", "H")  # H2 is absent from the sourced table


def br2_profile() -> ObservabilityProfile:
    return observability_profile((_BR2,))


def i2_profile() -> ObservabilityProfile:
    return observability_profile((_I2,))


def _axis_split_profiles():
    """Two hand-built profiles from the REAL sourced Br2 signatures: one process-only, one identity-only
    -- to demonstrate the axes do not collapse (neither dominates the other)."""
    br2_sigs = signatures_for(_BR2)
    proc = tuple(s for s in br2_sigs if s.axis is ObservabilityAxis.PROCESS)
    ident = tuple(s for s in br2_sigs if s.axis is ObservabilityAxis.IDENTITY)
    a = ObservabilityProfile(OBSERVABILITY_SCHEMA, process=proc)      # (2,0,0), sourced computed True
    b = ObservabilityProfile(OBSERVABILITY_SCHEMA, identity=ident)    # (0,1,0), sourced computed True
    return a, b


def content_hash() -> str:
    br2, i2 = br2_profile(), i2_profile()
    unsourced = observability_profile((_UNSOURCED,))
    a, b = _axis_split_profiles()
    payload = {
        "br2_strengths": list(br2.cheap_strengths),
        "i2_strengths": list(i2.cheap_strengths),
        "br2_dominates_i2": observability_dominates(br2, i2),
        "i2_dominates_br2": observability_dominates(i2, br2),
        "unsourced_sourced": unsourced.sourced,
        "process_vs_identity_incomparable": (
            not observability_dominates(a, b) and not observability_dominates(b, a)
        ),
        "br2_digest": br2.digest,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the demonstration does not hold."""
    br2, i2 = br2_profile(), i2_profile()
    assert br2.cheap_strengths == (2, 1, 0), f"Br2 strengths {br2.cheap_strengths} != (2,1,0)"
    assert i2.cheap_strengths == (1, 1, 0), f"I2 strengths {i2.cheap_strengths} != (1,1,0)"
    assert observability_dominates(br2, i2), "Br2 must Pareto-dominate I2 on cheap observability"
    assert not observability_dominates(i2, br2), "I2 must not dominate Br2"
    # the axes do not collapse: process-only vs identity-only are incomparable.
    a, b = _axis_split_profiles()
    assert not observability_dominates(a, b) and not observability_dominates(b, a), \
        "a process-strong profile must NOT dominate an identity-strong one (axes must not collapse)"
    # fail-closed UNKNOWN: an unsourced product is incomparable both ways.
    unsourced = observability_profile((_UNSOURCED,))
    assert unsourced.sourced is False
    assert not observability_dominates(br2, unsourced) and not observability_dominates(unsourced, br2)
    # no collapsed total exists (structural refusal, invariant 7).
    assert not hasattr(br2, "overall_score") and not hasattr(br2, "total")


def report() -> dict:
    br2, i2 = br2_profile(), i2_profile()
    return {
        "br2_strengths_process_identity_purity": list(br2.cheap_strengths),
        "i2_strengths_process_identity_purity": list(i2.cheap_strengths),
        "br2_pareto_dominates_i2": observability_dominates(br2, i2),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    r = report()
    for key, value in r.items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
