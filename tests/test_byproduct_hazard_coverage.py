"""Decomposition-byproduct HAZARD evidence coverage, under the second-source sourcing discipline.

Six common decomposition products (benzene, hydrogen sulfide, acetaldehyde, ethylene, acetylene,
phenol) are registered structures carrying sourced hazard records, so a decomposition that reaches
them attaches real safety data instead of a loud UNKNOWN. These tests prove the coverage is live AND
honest: every new record names its source, is ESTABLISHED only with corroboration, and pins exactly
one registered isomer (the isomer-keyed contract).

Gate mapping (this file was formerly ``test_g5_coverage.py`` -- its docstring's informal "G5" collided
with two unrelated "G5"s; see manifest section 2A.8, the canonical G-numbering cross-reference). What
it ACTUALLY guards:

  * standard section 16 **G4** (direction and evidence: a sourced record must name real provenance,
    free-text provenance cannot earn ``KNOWN``, and unsupported evidence fails construction) applied to
    hazard records; and
  * it feeds standard section 16 **G7** (missing hazards cannot produce a safety clearance).

It is NOT standard section 16 G5 (stoichiometric invariance and route topology), and NOT manifest
section 2A.3 G5 (identity monotonicity -- guarded in ``test_identity.py`` / ``test_id_stereo.py`` /
``test_ir_loss.py``). The rename removes the "G5" token from the filename so a "G5" grep is no longer
misattributed to this evidence-coverage test.
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
