"""POOR-MAN-INGENUITY-SCISSORS-01 (R50, PR-2): the second verified defer of the poor-man ingenuity reward.

The committed probe (:mod:`experiments.poor_man_ingenuity_scissors_probe`) is the comprehensive evidence
that the ingenuity reward is unrealizable soundly on today's models -- the ingenuity scissors (ingenious =>
unconventional => unsourced; sound-reachability-for-unsourced => derived; derived => proven unsound across
the kitchen boundary).  These are the fast regression pins over the SAME live production behavior, kept
independent of the probe so a probe refactor cannot silently drop coverage.  Each assertion is a tripwire:
if it fires, a defer premise changed (a catalyst model appeared, a SEED record flipped a census target) and
the defer must be re-evaluated.
"""
from __future__ import annotations

from experiments import poor_man_ingenuity_scissors_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_kill1_local_edit_collides_across_the_kitchen_boundary():
    # THE deepest kill: the whole Fischer family shares one byte-identical atom-mapped local bond edit, yet
    # the kitchen members (pentyl/heptyl acetate) and the non-kitchen members (amino-esters: the amine
    # outcompetes -> needs protection) are the same class -- so a class keyed on the local edit cannot carry
    # the right condition envelope.  Invariance across chain length AND terminal group = unbounded radius.
    k1 = probe.radius_collision()
    assert k1["all_edits_identical"] is True
    assert k1["collision_straddles_boundary"] is True
    assert k1["kitchen_members"] and k1["not_kitchen_members"]


def test_kill2_capability_stack_is_catalyst_blind():
    # even given a perfectly honest, complete envelope with the Ru/Ir catalyst DECLARED, not one leg of the
    # named capability stack returns EXCLUDED -- so a reward gated on it would VOUCH a catalysis-required
    # reaction as poor-man-reachable (R49's KILL-1, relocated one layer down).
    k2 = probe.catalyst_blind_reward()
    assert k2["any_leg_excluded"] is False
    assert k2["equipment_names_catalyst"] is False
    assert k2["all_consumed_obtainable"] is True


def test_kill2b_seed_records_carry_no_structured_catalyst():
    # every sourced SEED record has an empty structured catalysts field (catalyst buried in free-text medium)
    # -- the authoring template a per-class table would copy, and the reason even the sourced path is blind.
    assert probe.seed_catalysts_empty()["all_catalysts_field_empty"] is True


def test_scissors_the_only_sound_signal_is_conventional_not_ingenious():
    # the flagship drug targets have NO fully-sourced route; the one target that is both sourced and
    # commodity-terminated is a conventional textbook ester (methyl salicylate).  Sound signal, zero ingenuity.
    census = probe.sourced_signal_is_conventional()
    assert census["methyl_salicylate_fully_sourced_kitchen"] is True
    assert census["caffeine_sourced"] is False
    assert census["paracetamol_sourced"] is False
