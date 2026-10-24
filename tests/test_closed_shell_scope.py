"""Wave B -- the DOCUMENTED SCOPE of ``is_closed_shell_neutral`` (issue #105).

``is_closed_shell_neutral`` is a representation-relative heuristic with no per-atom charge / H-count / spin
model, so it cannot prove arbitrary closed-shell status. The brief's instruction was to find constructive
counterexamples and DOCUMENT the real scope rather than make an unrestricted assertion -- an adversarial pass
did exactly that. This test pins BOTH halves of the truth so the boundary is impossible to hide:

* what the guard reliably gets right (within its scope), and
* the KNOWN blind spots -- as a visible, regression-guarded characterization, explicitly NOT a false-vouch
  (it is defense-in-depth; the single-cut re-derivation + conservation certificate are the real lock, and no
  demonstrated false-VOUCH chains through it). A future #105 per-atom model is the sound fix; when it lands,
  the blind-spot assertions below become a deliberate, visible movement -- not a silent change.
"""
from __future__ import annotations

from smartchem.diels_alder import is_closed_shell_neutral as cs
from smartchem.smiles import parse_smiles as P


def test_accepts_genuine_closed_shell_neutral_within_scope():
    for smi in ("c1ccccc1", "C=C", "O", "CN(=O)=O", "CS(C)(=O)=O"):  # benzene, ethene, water, nitro(N=5), sulfone
        assert cs(P(smi)) is True, smi


def test_rejects_what_the_valence_and_charge_model_CAN_see():
    # a nonzero net charge, an out-of-table element, and an EXPLICIT-H off-valence radical/carbene are all
    # correctly rejected -- honest coverage loss, never a false-vouch.
    for smi in ("[OH-]", "[Fe]", "[CH2]", "[CH3]"):
        assert cs(P(smi)) is False, smi


def test_known_blind_spot_even_valence_diradical_is_documented():
    # O2 is a ground-state TRIPLET DIRADICAL, yet each O sits at bond-order 2 (an allowed valence), so a
    # valence-only heuristic with no spin model cannot see it. DOCUMENTED limitation (#105), not a false-vouch.
    assert cs(P("O=O")) is True


def test_known_blind_spot_no_H_radical_at_intermediate_valence_is_documented():
    # NO2 (N at bond-order 4, within {3,5}) in the no-H representation: the implicit-H branch assumes H would
    # fill N to 5 and cannot tell a bracket [N] (no implicit H, a radical) from an N. DOCUMENTED (#105).
    assert cs(P("O=[N]=O")) is True
    assert cs(P("[O-][N+]=O")) is True


def test_known_blind_spot_representation_dependence_is_documented():
    # the SAME molecule (nitromethane) flips verdict by spelling, because per-atom formal charge is not
    # carried: pentavalent-N passes, charge-separated N(4) is rejected. DOCUMENTED (#105).
    assert cs(P("CN(=O)=O")) is True
    assert cs(P("C[N+](=O)[O-]")) is False
    assert cs(P("CN(=O)=O")) != cs(P("C[N+](=O)[O-]"))
