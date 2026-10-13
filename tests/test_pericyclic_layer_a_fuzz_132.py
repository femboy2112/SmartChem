"""Regression lock for PERICYCLIC-LAYER-A-FUZZ-132 (OPERATION #132 -- pericyclic content-determinism).

The committed evidence that dropping the pericyclic Layer-B/-C centre read introduces NO false-vouch: Layer A (each
family's own guarded re-derivation) is a sound SOLE gate and a clean SEPARATOR over all 14 pericyclic families, so a
step that passes Layer A is a genuine member and recognising it centre-lessly is correct, not a forgery.
"""
from __future__ import annotations

import experiments.pericyclic_layer_a_fuzz_132 as fuzz


def test_layer_a_is_a_sound_sole_gate_and_separator():
    m = fuzz.measure_layer_a()
    assert m["diagonal_ok"], "a genuine member failed its OWN family's Layer A"
    assert not m["offdiagonal_fires"], f"cross-poach: a member passed another family's Layer A: {m['offdiagonal_fires']}"
    assert not m["fiction_fires"], f"a curated fiction fired Layer A (false-vouch surface): {m['fiction_fires']}"
    assert not m["nonconserving_fires"], f"Layer A fired on a non-conserving pairing: {m['nonconserving_fires']}"
    # the gate discriminates (it does not fire on everything): random firings are a small minority of trials.
    assert m["random_firings"] < m["random_trials"] // 10, f"Layer A fired far too often: {m['random_firings']}"


def test_centreless_pericyclics_are_content_deterministically_recognized():
    r = fuzz.measure_recognition()
    assert r["all_recognized"], f"a centre-less genuine pericyclic step was not recognized: {r['rows']}"
    # each of the 14 maps to a DISTINCT class name (the separation is real, not a collapse to one label).
    classes = [k for _n, k in r["rows"]]
    assert len(set(classes)) == 14, f"recognized classes collapsed/collided: {classes}"


def test_charge_separated_and_radical_adducts_are_rejected():
    # #132 hardening (evil-morty): a net-neutral charge-separated zwitterion or an odd-electron radical is NOT a
    # closed-shell pericyclic partner, so no recognizer may vouch a step carrying one (the false-vouch it found).
    h = fuzz.measure_hardening()
    assert h["all_rejected"], f"a charge-separated/radical adduct passed the closed-shell guard: {h['rows']}"
    assert h["end_to_end_recognized"] is None, (
        f"the end-to-end charge-separated kill still vouches: {h['end_to_end_recognized']}")


def test_validate_is_green():
    assert fuzz.validate() is True
