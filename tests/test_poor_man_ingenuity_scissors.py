"""POOR-MAN-INGENUITY-SCISSORS-01 (R50, PR-2; R51 catalyst discharge): the ingenuity reward stays deferred.

The committed probe (:mod:`experiments.poor_man_ingenuity_scissors_probe`) is the evidence that the ingenuity
reward is unrealizable soundly on today's models -- the ingenuity scissors.  The LOAD-BEARING kill is KILL-1
(the enumeration-frontier RECOGNIZER reads a bounded-radius local edit but a condition envelope is
unbounded-radius, so one class label straddles the kitchen boundary), and Blade 1 is the census (the only
per-reaction-sourced x commodity route is a conventional textbook ester).  Both are UNTOUCHED, so the reward
stays deferred.

R51: CATALYST-OBTAIN-01 built the catalyst-obtainability half of the "real substrate-aware model" the defer
waited on, deliberately DISCHARGING two SUPPORTING observations -- KILL-2b (a SEED record now carries a
structured catalyst) and the blindness KILL-2 measured (the obtainability gate now EXCLUDES a declared metal
catalyst).  These regression pins now assert the DEFER premises (KILL-1 + census) still hold AND the R51
discharges are real -- if any fires, either the defer premise moved or the catalyst gate regressed.
"""
from __future__ import annotations

from experiments import poor_man_ingenuity_scissors_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_kill1_local_edit_collides_across_the_kitchen_boundary():
    # THE load-bearing kill (untouched by R51): the whole Fischer family shares one byte-identical atom-mapped
    # local bond edit, yet kitchen members (pentyl/heptyl acetate) and non-kitchen members (amino-esters: the
    # amine outcompetes -> needs protection) are the same class -- so a class keyed on the local edit cannot carry
    # the right condition envelope.  Invariance across chain length AND terminal group = unbounded radius.
    k1 = probe.radius_collision()
    assert k1["all_edits_identical"] is True
    assert k1["collision_straddles_boundary"] is True
    assert k1["kitchen_members"] and k1["not_kitchen_members"]


def test_kill2_process_equipment_legs_stay_catalyst_agnostic_by_design():
    # R51 boundary (no longer a kill): the OLD process/equipment/consumed-reagent legs still do not EXCLUDE a
    # declared Ru/Ir catalyst -- correctly, because they judge time/equipment/stock, not catalyst obtainability.
    # The missing axis is now a SEPARATE leg (below), so this is a documented boundary, not a blindness.
    legs = probe.process_equipment_legs_are_catalyst_agnostic()
    assert legs["process_legs_exclude"] is False
    assert legs["equipment_names_catalyst"] is False
    assert legs["all_consumed_obtainable"] is True


def test_r51_catalyst_obtainability_gate_now_blocks_the_metal_catalyst():
    # the DISCHARGE of the KILL-2 blindness: the new obtainability leg EXCLUDES the declared metal catalyst the
    # old stack silently vouched, while the sourced kitchen catalyst (H2SO4 -> HARDWARE) is correctly NOT blocked.
    gate = probe.catalyst_obtainability_gate_blocks()
    assert gate["metal_catalyst_blocked"] is True
    assert gate["metal_catalyst_tier_not_kitchen"] is True
    assert gate["kitchen_catalyst_not_blocked"] is True


def test_r51_seed_record_now_carries_a_structured_kitchen_catalyst():
    # the DISCHARGE of KILL-2b: exactly one SEED record (isopentyl acetate) now carries a structured catalyst,
    # and every populated catalyst is kitchen-obtainable (so no sourced route is false-excluded).
    seed = probe.seed_catalyst_now_populated()
    assert seed["n_records_with_structured_catalyst"] >= 1
    assert seed["all_populated_catalysts_kitchen"] is True


def test_scissors_the_only_sound_signal_is_conventional_not_ingenious():
    # Blade 1 (untouched): the flagship drug targets have NO fully-sourced route; the one target that is both
    # sourced and commodity-terminated is a conventional textbook ester (methyl salicylate).  Sound, zero ingenuity.
    census = probe.sourced_signal_is_conventional()
    assert census["methyl_salicylate_fully_sourced_kitchen"] is True
    assert census["caffeine_sourced"] is False
    assert census["paracetamol_sourced"] is False
