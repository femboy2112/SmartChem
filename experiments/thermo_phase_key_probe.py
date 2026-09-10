"""Item 5 (Lane B·C): the phase-carrying thermo key -- a committed demonstration that a species tabulated in more
than one standard-state phase resolves to the RIGHT phase, and fails CLOSED (never silently borrows the wrong
phase's ΔfH°) when a caller has not said which phase it means.

The debt (ROUND-26 M2b carried debt (a), ROADMAP item 5)
--------------------------------------------------------
Only the GAS Br₂ record was live in ``SEED_THERMO_REFS``; ``ThermoTable`` deduplicated and resolved on
``(formula, name)`` alone, phase-blind.  Br₂'s TRUE standard state is the LIQUID (Br₂(l), ΔfH° = 0 by
convention); the gas record carries ΔfH° = +30.91 kJ/mol.  So any future reaction reasoning about liquid Br₂
through the thermo layer would have silently inherited the GAS ΔfH° -- a +30.91 kJ/mol error, undetected.

The fix, and why it is a GENERAL key not a Br₂ special case
----------------------------------------------------------
``ThermoRef`` already carried a ``phase`` field; item 5 makes it part of the lookup IDENTITY.  ``with_records``
deduplicates on the ``(formula, name, phase)`` TRIPLE (so a gas and a liquid record coexist instead of one
silently overwriting the other at write time), and ``for_formula``/``for_named`` gain an optional ``phase``:
narrowed when given, and a phase-BLIND query fails closed to ``None`` whenever more than one phase-record
matches -- the SAME isomer-ambiguity honesty ``for_formula`` already applied, extended one dimension.  Every
single-phase species is byte-identical under a phase-blind query; only a genuinely dual-phase species (Br₂) is
affected, and it is affected in the SAFE direction (a loud UNKNOWN, never a wrong number).

The liquid Br₂ value is MIRRORED byte-for-byte from the already-frozen, already-cross-checked CODATA seed
(``experiments.thermo_codata_seed``: ΔfH° = 0, S° = 152.21 ± 0.30 J/mol/K), so this closes a WIRING gap; it
sources no new number ([[known-physics-not-new-physics]]).
"""
from __future__ import annotations

from experiments.thermo_codata_seed import CODATA_KEY_VALUES
from smartchem.data.thermo import DEFAULT_THERMO, SEED_THERMO_REFS, ThermoRef, ThermoTable
from smartchem.experiment.feasibility import feasibility_of_step, resolve_thermo
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


def _codata_liquid_br2():
    for r in CODATA_KEY_VALUES:
        if r.formula == "Br2" and r.phase == "liquid":
            return r
    raise AssertionError("the frozen CODATA seed no longer carries the liquid Br₂ reference state")


def validate() -> None:
    """Raise unless the phase-carrying key holds all of its load-bearing properties."""
    # 1. dual-phase COEXISTENCE: both Br₂ records are live (the (formula, name, phase) key kept both).
    g = DEFAULT_THERMO.for_formula("Br2", phase="gas")
    liq = DEFAULT_THERMO.for_formula("Br2", phase="liquid")
    assert g is not None and liq is not None, "both Br₂ phases must be live"
    assert (g.dhf_kj_per_mol, g.s_j_per_mol_k, g.phase) == (30.91, 245.468, "gas")
    assert (liq.dhf_kj_per_mol, liq.s_j_per_mol_k, liq.phase) == (0.0, 152.21, "liquid")

    # 2. the liquid value is the frozen CODATA reference state, mirrored byte-for-byte (no new physics).
    src = _codata_liquid_br2()
    assert (liq.dhf_kj_per_mol, liq.s_j_per_mol_k) == (src.dfh_kj, src.s_j_per_k), "liquid Br₂ drifted from CODATA"
    assert (liq.uncertainty_dhf_kj, liq.uncertainty_s_j_per_mol_k) == (src.dfh_unc_kj, src.s_unc_j_per_k)

    # 3. fail CLOSED on a phase-blind query for a dual-phase species (the debt: no silent wrong-phase borrow).
    assert DEFAULT_THERMO.for_formula("Br2") is None, "phase-blind Br₂ must be a loud None, not the gas record"
    assert DEFAULT_THERMO.for_named("Br2", "bromine") is None, "phase-blind named Br₂ must fail closed too"

    # 4. resolve_thermo, the per-step consumer, reproduces the debt scenario as NEGATIVE SPACE: a phase-blind
    #    Br₂ resolves to UNKNOWN, never the silently-wrong gas ΔfH° (+30.91).  This IS the closed debt.
    assert resolve_thermo(parse_smiles("BrBr")) is None, "resolve_thermo(Br₂) must be UNKNOWN, not a gas borrow"

    # 5. write-time SILENT-OVERWRITE closed: adding a same-(formula, name) different-phase record no longer drops
    #    the earlier one.  Under the OLD (formula, name) key this add would have deleted the gas record with no
    #    error at all -- a sharper hazard than the read-time miss.
    base = ThermoTable((ThermoRef("X2", "sample", 10.0, 100.0, "gas", "test"),))
    extended = base.with_records(ThermoRef("X2", "sample", 0.0, 80.0, "liquid", "test"))
    assert extended.for_formula("X2", phase="gas") is not None, "the gas record was silently overwritten"
    assert extended.for_formula("X2", phase="liquid") is not None, "the liquid record did not land"
    assert extended.for_formula("X2") is None, "a phase-blind query on the dual-phase species must fail closed"

    # 6. REGRESSION NET: every single-phase species in the live seed resolves IDENTICALLY under a phase-blind
    #    query -- the change is a strict superset, inert on everything but dual-phase Br₂.
    for f in {r.formula for r in SEED_THERMO_REFS} - {"Br2"}:
        assert DEFAULT_THERMO.for_formula(f) is not None, f"{f} (single-phase) regressed under phase-blind lookup"

    # 7. the phase THREADS to the per-step consumer.  resolve_thermo reaches the right phase when named; and a
    #    gas declaration keeps the R26 DOW-Br₂ dissociation verdict computable (Br₂(g) → 2 Br(g), ΔG₂₉₈ =
    #    +161.65, UNFAVORABLE) while the SAME step phase-blind is a loud UNKNOWN -- the debt closed AND the
    #    north-star result preserved through the one interface (feasibility_of_step / route forward `phases`).
    assert resolve_thermo(parse_smiles("BrBr"), phase="gas").dhf_kj_per_mol == 30.91
    assert resolve_thermo(parse_smiles("BrBr"), phase="liquid").dhf_kj_per_mol == 0.0
    br2, br = parse_smiles("BrBr"), parse_smiles("[Br]")
    step = ExperimentStep.assembling(br, (br2,), (br, br))
    gas = feasibility_of_step(step, phases={br2: "gas"})
    assert gas.delta_g_kj is not None and abs(gas.delta_g_kj - 161.65) < 0.1, "gas dissociation ΔG must be +161.65"
    assert feasibility_of_step(step).delta_g_kj is None, "a phase-blind Br₂ step must be UNKNOWN, not a gas verdict"

    # 8. the fail-closed holds at the DERIVE gate too (red-team Finding 1).  Br₂ escapes the Benson estimate only
    #    by being Benson-UNCOVERABLE; a Benson-COVERABLE dual-phase species (ethanol, injected gas+liquid) must
    #    STILL fail closed phase-blind -- the guarantee is the design's (`is_multiphase` gates the derive path),
    #    not purchased by one molecule's chemistry.
    two_phase = DEFAULT_THERMO.with_records(
        ThermoRef("C2H6O", "ethanol", -234.8, 281.6, "gas", "probe gas"),
        ThermoRef("C2H6O", "ethanol", -277.6, 160.7, "liquid", "probe liquid"),
    )
    assert resolve_thermo(parse_smiles("CCO"), two_phase) is None, "dual-phase Benson-coverable must fail closed"
    assert resolve_thermo(parse_smiles("CCO"), two_phase, phase="liquid").phase == "liquid"


def report() -> dict:
    validate()
    live_br2 = [r for r in SEED_THERMO_REFS if r.formula == "Br2"]
    return {
        "br2_phases_live": sorted(r.phase for r in live_br2),
        "phase_blind_br2_fails_closed": DEFAULT_THERMO.for_formula("Br2") is None,
        "liquid_br2_source": "experiments.thermo_codata_seed CODATA reference state (ΔfH°=0, S°=152.21±0.30)",
    }


if __name__ == "__main__":
    validate()
    print("phase-carrying thermo key: all properties hold")
    for k, v in report().items():
        print(f"  {k}: {v}")
