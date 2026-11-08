"""OPERATION XXV-1 (#165) -- the calcite standard-state verdict and the computed four-rung claim ladder.

The verdict is DERIVED from ``CalciteParams.standard_state_basis``; the ladder is COMPUTED from spec + structural law +
receipts; both are hashed into the evidence identity.  These are mutation tests: flip the basis and the verdict, the
ladder and the digest must all move; try to inject a label and the API must refuse it.
"""
from __future__ import annotations

import dataclasses
import itertools

import pytest

from experiments.sandbox_foundation import admissibility as adm
from experiments.sandbox_foundation import sim_api_v2alpha as api

W = "calcite_closed_dissolution"
LEGACY, MOLAR = "as_tabulated_molal", "converted_to_molar"
INIT = (api.SpeciesInventory("cell", "CaCO3(s)", "solid", 0.01),
        api.SpeciesInventory("cell", "H2O", "pure_liquid", 55.34),
        api.SpeciesInventory("cell", "H+", "aqueous", 1e-7),
        api.SpeciesInventory("cell", "OH-", "aqueous", 1e-7))
CA = ("Ca+2", "CaCO3(aq)", "CaHCO3+", "CaOH+")
FROZEN_LEGACY_CA_M = 1.2300896033886228e-4      # XXIII-S4 harness value (test_xxiii_s4_solid_equilibrium.py)


def _spec(basis, **kw):
    sched = api.BoundarySchedule((api.BoundaryPhase("dissolve", 6000.0, 60, "closed", False),))
    return api.SimulationSpec(model=api.ModelSpec(W, api.CalciteParams(standard_state_basis=basis, **kw)),
                              initial=INIT, schedule=sched, solver=api.SolverOptions(rtol=1e-10, atol=1e-18))


@pytest.fixture(scope="module")
def runs():
    return {b: api.run(_spec(b)) for b in (LEGACY, MOLAR)}


def test_new_scenarios_default_to_the_source_consistent_basis():
    p = api.CalciteParams()
    assert p.standard_state_basis == MOLAR
    assert api.standard_state_verdict(p) is api.StandardStateVerdict.SOURCE_CONSISTENT_MOLAR
    assert api.standard_state_verdict(api.CalciteParams(standard_state_basis=LEGACY)) is \
        api.StandardStateVerdict.LEGACY_REPLAY_BASIS_MISMATCH


def test_the_xxiii_harness_default_is_untouched():
    import inspect

    from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import run_solid_equilibrium_xxiii as h
    assert inspect.signature(h.build_calcite_world).parameters["standard_state_basis"].default == LEGACY


def test_flipping_the_basis_moves_verdict_ladder_and_digests(runs):
    lad = {b: runs[b].validation_ladder for b in runs}
    ids = {b: runs[b].identities for b in runs}
    dom = adm.WITHIN_DECLARED_FORMULA_DOMAIN
    assert lad[MOLAR][dom]["standard_state_verdict"] == "SOURCE_CONSISTENT_MOLAR" and lad[MOLAR][dom]["holds"] is True
    assert lad[LEGACY][dom]["standard_state_verdict"] == "LEGACY_REPLAY_BASIS_MISMATCH"
    assert lad[LEGACY][dom]["holds"] is False
    ref = adm.COMPARED_TO_REFERENCE_IMPLEMENTATION
    assert lad[MOLAR][ref]["holds"] is True and lad[LEGACY][ref]["holds"] is False
    for d in ("model_digest", "run_digest", "evidence_digest"):
        assert ids[MOLAR][d] != ids[LEGACY][d], d
    # the evidence identity carries the SAME verdict and rungs the ladder reports -- relabelling one moves the digest
    for b in runs:
        ev = ids[b]["evidence"]["calcite_evidence_identity"]
        assert ev["standard_state_basis"] == b
        assert ev["standard_state_verdict"] == lad[b][dom]["standard_state_verdict"]
        assert ev["claim_rungs"][dom] == api._plain(lad[b][dom])
        assert ev["claim_rungs"][ref] == api._plain(lad[b][ref])


def test_the_basis_is_the_only_evidence_factor_that_moved():
    ev = {b: api.spec_identities(_spec(b))["evidence"]["calcite_evidence_identity"] for b in (LEGACY, MOLAR)}
    moved = {k for k in ev[MOLAR] if ev[MOLAR][k] != ev[LEGACY][k]}
    assert moved == {"standard_state_basis", "standard_state_verdict", "claim_rungs"}


def test_a_caller_cannot_inject_a_verdict_or_a_ladder(runs):
    res = runs[LEGACY]
    with pytest.raises(TypeError):
        api.CalciteParams(standard_state_verdict="SOURCE_CONSISTENT_MOLAR")
    fields = {f.name: getattr(res, f.name) for f in dataclasses.fields(res) if f.init}
    forged = {k: {"holds": True} for k in adm.CLAIM_LADDER}
    with pytest.raises(TypeError):
        api.SimulationResult(**fields, validation_ladder=forged)
    with pytest.raises(ValueError):
        dataclasses.replace(res, validation_ladder=forged)
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.validation_ladder = forged
    with pytest.raises(TypeError):
        res.validation_ladder[adm.WITHIN_DECLARED_FORMULA_DOMAIN] = {"holds": True}
    with pytest.raises(TypeError):
        res.validation_ladder[adm.WITHIN_DECLARED_FORMULA_DOMAIN]["holds"] = True
    # re-labelling the spec re-derives the ladder from the NEW spec; it never keeps a stale one
    relabelled = dataclasses.replace(res, spec=runs[MOLAR].spec)
    assert relabelled.validation_ladder[adm.WITHIN_DECLARED_FORMULA_DOMAIN]["holds"] is True
    assert res.validation_ladder[adm.WITHIN_DECLARED_FORMULA_DOMAIN]["holds"] is False


@pytest.mark.parametrize("constants_mode, allow_precipitation, i_max",
                         list(itertools.product(("nominal", "phreeqc_effective"), (False, True), (0.1, 0.05))))
def test_a_legacy_result_can_never_report_formula_domain_validity(constants_mode, allow_precipitation, i_max):
    p = api.CalciteParams(standard_state_basis=LEGACY, constants_mode=constants_mode,
                          allow_precipitation=allow_precipitation, ionic_strength_max=i_max)
    rungs = api._BUILDERS[W].claim_rungs(p)
    dom = rungs[adm.WITHIN_DECLARED_FORMULA_DOMAIN]
    assert dom["holds"] is False and dom["reason"] == "LEGACY_REPLAY_BASIS_MISMATCH"
    assert rungs[adm.COMPARED_TO_REFERENCE_IMPLEMENTATION]["holds"] is False
    molar = api._BUILDERS[W].claim_rungs(dataclasses.replace(p, standard_state_basis=MOLAR))
    assert molar[adm.WITHIN_DECLARED_FORMULA_DOMAIN]["holds"] is True
    # only the configuration PHREEQC was actually compared on may claim the reference rung
    assert molar[adm.COMPARED_TO_REFERENCE_IMPLEMENTATION]["holds"] is (constants_mode == "nominal")


def test_the_empirical_rung_is_false_for_both_bases_and_both_worlds(runs):
    emp = adm.EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND
    for b in runs:
        assert runs[b].validation_ladder[emp]["holds"] is False
        assert runs[b].validation_ladder[emp]["reason"] == "NO_QUALIFIED_INDEPENDENT_HOLDOUT"
    vinegar = api.run(api.SimulationSpec(model=api.ModelSpec(), initial=(api.SpeciesInventory("A", "HAc", "aqueous", 0.1),),
                                         schedule=api.BoundarySchedule((api.BoundaryPhase("p", 1.0, 1),))))
    assert vinegar.validation_ladder[emp]["holds"] is False
    assert tuple(vinegar.validation_ladder) == adm.CLAIM_LADDER


def test_the_ladder_is_four_ordered_rungs_and_rung_one_is_computed(runs):
    for b in runs:
        lad = runs[b].validation_ladder
        assert tuple(lad) == adm.CLAIM_LADDER
        r1 = lad[adm.NUMERICALLY_EXECUTABLE]
        assert r1["holds"] is True and r1["structural_conservation_holds"] is True
        assert r1["execution_identity_certified"] is True and r1["numerically_unresolved_components"] == ()
    # rung 1 follows its inputs: a receipt that did not close demotes it
    res = runs[MOLAR]
    bad = dataclasses.replace(res, receipts=(dataclasses.replace(res.receipts[0], material_balance_closed=False),))
    assert bad.validation_ladder[adm.NUMERICALLY_EXECUTABLE]["holds"] is False
    assert bad.validation_ladder[adm.NUMERICALLY_EXECUTABLE]["reason"] == "EXECUTION_NOT_CERTIFIED"


def test_legacy_replay_keeps_its_frozen_number_and_molar_moves(runs):
    ca = {b: sum(runs[b].final_frame.amount("cell", s) for s in CA) for b in runs}
    assert ca[LEGACY] == pytest.approx(FROZEN_LEGACY_CA_M, rel=1e-9)
    assert ca[MOLAR] / ca[LEGACY] - 1 == pytest.approx(-3.0e-3, abs=2e-4)      # the basis shift, not chemistry
    for b in runs:                                                              # receipts close on either basis
        rc = runs[b].receipts[0]
        assert set(rc.component_resolution.values()) == {"VERIFIED_WITHIN_RESOLUTION"}
        assert {"Ca", "C", "charge"} <= set(rc.component_resolution)


def test_provenance_and_wire_form_carry_the_basis(runs):
    for b in runs:
        prov = runs[b].spec.provenance.by_name()["standard_state_basis"]
        assert prov.tier == ("DERIVED" if b == MOLAR else "ASSUMED")
        wire = api.result_to_dict(runs[b])
        assert wire["validation_ladder"][adm.WITHIN_DECLARED_FORMULA_DOMAIN]["standard_state_basis"] == b


def test_no_tuning_the_molar_constants_are_the_tabulated_ones_transported_and_nothing_else():
    import math

    from experiments.sandbox_foundation import standard_state as ss
    b = api._BUILDERS[W]
    worlds = {basis: b._world(api.CalciteParams(standard_state_basis=basis)) for basis in (LEGACY, MOLAR)}
    rx = {basis: [r for c in w.compartments for r in c.system.reactions] for basis, w in worlds.items()}
    assert [r.name for r in rx[LEGACY]] == [r.name for r in rx[MOLAR]] and len(rx[MOLAR]) == 7
    for r_leg, r_mol in zip(rx[LEGACY], rx[MOLAR]):
        k = {nm: (getattr(r.rate_law, "ksp", None) or r.rate_law.K).value for nm, r in (("leg", r_leg), ("mol", r_mol))}
        nu = ss.aqueous_nu(r_mol.stoich, getattr(r_mol.rate_law, "unit_activity", ()))
        assert math.log10(k["mol"]) - math.log10(k["leg"]) == pytest.approx(nu * math.log10(ss.RHO_W_25C_KG_PER_L),
                                                                             abs=1e-12), r_mol.name
