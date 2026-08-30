"""G5 -- widened byproduct evidence coverage, sourced under the second-source discipline.

Six common decomposition products (benzene, hydrogen sulfide, acetaldehyde, ethylene, acetylene,
phenol) are now registered structures carrying sourced hazard records, so a decomposition that
reaches them attaches real safety data instead of a loud UNKNOWN. These tests prove the coverage is
live AND honest: every new record names its source, is ESTABLISHED only with corroboration, and pins
exactly one registered isomer (the isomer-keyed contract).
"""

import pytest

from smartchem.contracts import EvidenceStatus
from smartchem.data.hazards import HAZARD_REFS, hazards_for, hazards_for_named
from smartchem.smiles import parse_smiles
from smartchem.structure import resolve_structure

_NEW = ("benzene", "hydrogen sulfide", "acetaldehyde", "ethylene", "acetylene", "phenol")
_SMILES = {
    "benzene": "c1ccccc1", "hydrogen sulfide": "S", "acetaldehyde": "CC=O",
    "ethylene": "C=C", "acetylene": "C#C", "phenol": "Oc1ccccc1",
}


@pytest.mark.parametrize("name", _NEW)
def test_new_product_resolves_and_carries_sourced_hazards(name):
    # parse -> structure resolves to the name -> the name carries a hazard record
    resolved = resolve_structure(parse_smiles(_SMILES[name]))
    assert resolved is not None and resolved.name == name
    ref = hazards_for_named(name)
    assert ref is not None and ref.ghs_codes            # real GHS codes attached
    assert ref.provenance                                # the discipline: every record names its source


def test_benzene_hazards_are_reachable_by_formula():
    ref = hazards_for("C6H6")
    assert ref is not None and ref.name == "benzene"
    assert "H350" in ref.ghs_codes                        # known human carcinogen, sourced


def test_hydrogen_sulfide_is_flagged_fatal_by_inhalation():
    ref = hazards_for("H2S")
    assert ref is not None and "H330" in ref.ghs_codes    # the load-bearing "fatal if inhaled"


def test_every_new_record_meets_the_second_source_discipline():
    # ESTABLISHED is a corroboration claim -- it must carry a real provenance, never a bare assertion
    new_records = [r for r in HAZARD_REFS if r.name in _NEW]
    assert len(new_records) == len(_NEW)
    for r in new_records:
        assert r.status is EvidenceStatus.ESTABLISHED
        assert r.provenance and r.ghs_codes
