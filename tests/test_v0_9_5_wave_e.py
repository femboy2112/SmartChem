"""0.9.5 A18 -- the fresh non-author Wave E review of the A13-A17 fix delta (cdcdf88..90393b5), every finding pinned.

* Front door: an implicit bond between two aromatic atoms in no AROMATIC ring kekulised to a double (``c1cc1c1cc1``
  keyed as triafulvalene; a ring closed through an uppercase bridge let ``:`` do the same; ``c1CCc1`` became
  cyclobutene). An aromatic ring is now a cycle of lowercase atoms; an implicit bond outside one is single (OpenSMILES)
  and an explicit ``:`` outside one is refused.
* One parse ran the resonance placement search up to four times (isotope key, configuration, CIP, build); it runs once.
* The IR's structural-species leg built a graph of any size before refusing; it refuses past the atom ceiling first.
* The A17 DAG-height bound was big-integer work quadratic in the uncapped wire ``max_depth`` (tested in
  ``test_v0_9_5_dag_height_bound.py``); ``capability_work`` charged per bottle while the cost is per component (tested in
  ``test_v0_9_5_loader_hardening.py``).
* A huge JSON integer in a float field escaped the loaders as a bare ``OverflowError``; a cyclic in-process payload under
  the legacy schema id never terminated; a non-ASCII letter (``ſ``) certified through a case fold.
"""
from __future__ import annotations

import copy

import pytest

import smartchem.smiles as sm
from smartchem import compilation_ir as cir
from smartchem.capability.presets import isopentyl_capability_fit_bench
from smartchem.contracts import canonical_digest
from smartchem.experiment.catalyst_availability import Availability, catalyst_availability
from smartchem.experiment.stock import case_fold_match_certifies
from smartchem.service import (
    LEGACY_V08_RESPONSE_SCHEMA,
    build_recompile_request,
    request_from_payload,
    request_to_payload,
    response_from_payload,
)
from smartchem.smiles import SmilesError, parse_smiles
from smartchem.verification import MalformedPayloadError


def _key(smiles: str) -> str:
    return canonical_digest(parse_smiles(smiles).canonical())


# -- the aromatic-ring law --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("smiles", [
    "c1cc1c1cc1",            # was triafulvalene (C1=CC1=C1C=C1)
    "c1cccc1c1cccc1",        # was fulvalene
    "c1cccccc1c1cccccc1",
    "c12cc1CCc1cc12",        # the bridge's ring runs through CH2CH2 -- not an aromatic ring
    "c12cc1CCc1cc1:2",       # the same with an explicit ':'
    "c1CCc1",                # was cyclobutene
    "o1CCo1",                # a lone-pair donor on a ring only through uppercase atoms: was 1,2-dioxetane
])
def test_a_bond_outside_every_aromatic_ring_is_never_an_aromatic_double(smiles):
    with pytest.raises(SmilesError):
        parse_smiles(smiles)


@pytest.mark.parametrize("implicit, explicit", [
    ("c1ccccc1c1ccccc1", "c1ccccc1-c1ccccc1"),          # biphenyl's inter-ring bond is single, as written either way
    ("c1=cc=cc=c1", "c1ccccc1"),                          # mixed notation keeps its ring
    ("c1ccc2c(c1)CCc1ccccc12", "C1=CC=C2C(=C1)CCC1=CC=CC=C12"),
    ("c1ccc2c(c1)[nH]c1ccccc12", "C1=CC=C2C(=C1)NC1=CC=CC=C12"),
])
def test_honest_aromatic_spellings_keep_their_identity(implicit, explicit):
    assert _key(implicit) == _key(explicit)


# -- one placement search per parse -----------------------------------------------------------------------------------

def test_one_parse_runs_the_placement_search_once(monkeypatch):
    live, calls = sm._min_constitution_placement, []

    def counting(*args, **kwargs):
        calls.append(1)
        return live(*args, **kwargs)
    monkeypatch.setattr(sm, "_min_constitution_placement", counting)
    # an explicit-Kekule naphthalene with an isotope label and a stereocentre: all four layers ask for the placement
    _molecule, features = sm.parse_smiles_features("C1=CC=C2C=C([C@H](F)[13CH3])C=CC2=C1")
    assert features.isotopic_digest is not None and features.stereocentres_marked == 1
    assert len(calls) == 1
    assert sm._PLACEMENT_MEMO.get() is None          # never left set past the parse


# -- the IR's structural-species leg ----------------------------------------------------------------------------------

def test_the_species_leg_refuses_past_the_atom_ceiling_before_building():
    from smartchem.category import _MAX_CANONICAL_ATOMS
    honest = cir._structural_species_to_payload(cir.StructuralSpecies.of_molecule(parse_smiles("CC")))
    assert cir._structural_species_from_payload(copy.deepcopy(honest)).atoms
    big = copy.deepcopy(honest)
    big["atoms"] = ["C"] * (_MAX_CANONICAL_ATOMS + 1)
    with pytest.raises(ValueError, match="structural species payload carries 1,025 atoms"):
        cir._structural_species_from_payload(big)


# -- loader refusal class ---------------------------------------------------------------------------------------------

def _set_canonical_field(node, name: str, value) -> bool:
    """Set a canonical-codec field (``"fields": [[name, {"type": ..., "value": ...}], ...]``) anywhere in a payload."""
    if isinstance(node, list):
        if len(node) == 2 and node[0] == name and isinstance(node[1], dict) and "value" in node[1]:
            node[1]["value"] = value
            return True
        return any(_set_canonical_field(v, name, value) for v in node)
    if isinstance(node, dict):
        return any(_set_canonical_field(v, name, value) for v in node.values())
    return False


@pytest.mark.parametrize("leg", ["request constraints", "capability profile"])
def test_a_huge_json_integer_is_a_typed_refusal_not_a_bare_overflow(leg):
    """Wave E: 10**400 is legal JSON; float() of it raised a bare OverflowError out of every request/response loader."""
    payload = request_to_payload(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, capability_profile=isopentyl_capability_fit_bench()))
    if leg == "request constraints":
        payload["constraints"]["max_temperature_k"] = 10 ** 400
    else:
        assert _set_canonical_field(payload["capability_profile"], "max_temperature_k", 10 ** 400), "setup moved"
    with pytest.raises(MalformedPayloadError):
        request_from_payload(payload)


def test_a_cyclic_legacy_payload_terminates_in_a_refusal():
    payload: dict = {"schema_version": LEGACY_V08_RESPONSE_SCHEMA, "ranked_route_dossiers": []}
    payload["loop"] = payload
    with pytest.raises(ValueError):
        response_from_payload(payload)


# -- a non-ASCII letter never certifies through a fold ----------------------------------------------------------------

def test_a_non_ascii_letter_never_certifies_through_a_case_fold():
    assert catalyst_availability("H2SO4") is Availability.HARDWARE
    for query in ("H2ſO4", "conc. H2ſO4", "ſulfuric acid"):
        assert not case_fold_match_certifies(query, "H2SO4" if "2" in query else "sulfuric acid")
    assert catalyst_availability("H2ſO4") is None
