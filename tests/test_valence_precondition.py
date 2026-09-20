"""VALENCE-PRECONDITION-01: a charge-agnostic valence ceiling at the chemistry-aware rule-calculus seam.

dalembert (the Diels-Alder round adversary) found a fail-OPEN: the domain-neutral kernel and ``Molecule``
deliberately do not enforce chemical valence, so a valence-impossible species (a pentavalent carbon) is
silently processed.  The fix is a fail-closed ``valence_sane`` precondition wired into the ``_joined``
Molecule->graph adapter and the reusable ``retro_da_disconnections`` core.

The gate is a CHARGE-AGNOSTIC ceiling (max coordination over all charge states), NOT a neutral-only max --
because the graph carries only net molecular charge, not per-atom formal charge, a net-neutral
charge-separated species (carbon monoxide, ozone) is graph-identical to an impossible neutral and MUST
pass.  So the gate refuses only valences impossible in EVERY charge state (the actual fail-open), never a
real molecule.  These are the ordinary acceptance gates; the adversarial gate (evil-morty/dalembert) ran
SEPARATELY and both its kills are pinned below.  Design: docs/research/RULE_CALCULUS_VALENCE_PRECONDITION_v0.1.md.
"""
from __future__ import annotations

from smartchem.category import Bond, Molecule
from smartchem.diels_alder import DielsAlderProvider, retro_da_disconnections
from smartchem.rule_calculus import BondGraph, Edge, RuleError
from smartchem.rule_calculus_bridge import _MAX_COORDINATION, AuditedCappedScissionProvider, _joined, valence_sane
from smartchem.smiles import parse_smiles


def _g(labels, edges):
    return BondGraph(tuple(labels), frozenset(Edge(*e) for e in edges))


def _pentavalent_carbon() -> Molecule:
    return Molecule(("C", "F", "F", "F", "F", "F"), frozenset({Bond(0, k, 1) for k in range(1, 6)}))


# --- the ceiling is charge-agnostic (max over charge states), not a neutral-only max ---

def test_ceiling_is_the_charge_agnostic_maximum():
    assert _MAX_COORDINATION["C"] == 4 and _MAX_COORDINATION["O"] == 3   # O reaches 3 as O+ (CO/oxocarbenium)
    assert _MAX_COORDINATION["N"] == 5 and _MAX_COORDINATION["S"] == 6 and _MAX_COORDINATION["P"] == 6
    assert _MAX_COORDINATION["B"] == 4                                   # borate / amine-borane
    assert _MAX_COORDINATION["Cl"] == 7 == _MAX_COORDINATION["Br"] == _MAX_COORDINATION["I"]  # perchlorate/periodate


def test_untabulated_and_opaque_labels_are_unconstrained():
    assert _MAX_COORDINATION.get("Fe") is None and _MAX_COORDINATION.get("X") is None
    assert valence_sane(_g("XYZ", [(0, 1, 3), (1, 2, 3)])) is True       # opaque labels pass unconstrained


# --- reject only valences impossible in EVERY charge state ---

def test_valence_sane_rejects_impossible_in_any_state():
    assert valence_sane(_g("CF", [(0, 1, 5)])) is False                  # pentavalent carbon (the finding)
    assert valence_sane(_g("OCC", [(0, 1, 2), (0, 2, 2)])) is False      # oxygen degree 4 (impossible in any state)
    assert valence_sane(_g("NCCCCCC", [(0, k, 1) for k in range(1, 7)])) is False  # nitrogen degree 6


def test_valence_sane_accepts_real_hypervalent_species():
    assert valence_sane(_g("SOOOO", [(0, 1, 2), (0, 2, 2), (0, 3, 1), (0, 4, 1)])) is True  # sulfate S degree 6
    assert valence_sane(_g("PClClClClCl", [(0, k, 1) for k in range(1, 6)])) is True         # PCl5, P degree 5
    assert valence_sane(_g("NN", [(0, 1, 3)])) is True                                        # N2, N degree 3


# --- dalembert KILL 2 regression: net-neutral charge-separated reals must NOT be false-rejected ---

def test_carbon_monoxide_and_ozone_are_not_false_rejected():
    # CO is net-neutral (`[C-]#[O+]`), O at degree 3; it appears across seven test files.  A neutral-only
    # max would refuse it (O>2); the charge-agnostic ceiling (O<=3) accepts it -- at both the adapter and a
    # real provider entry point (dalembert proved the AuditedCappedScissionProvider hard-raised before the fix).
    for smiles in ("[C-]#[O+]", "[O-][O+]=O"):
        mol = parse_smiles(smiles)
        assert mol.charge == 0
        _joined((mol,))                                                   # must NOT raise
        AuditedCappedScissionProvider().enumerate_audited(mol, (), budget=1000)  # must NOT raise


# --- evil-morty KILL 1 regression: hypervalent halogen / iodine reagents must NOT be false-rejected ---

def test_hypervalent_iodine_and_halogen_reagents_are_not_false_rejected():
    # Hypervalent-iodine oxidants (Dess-Martin / PhI(OAc)2 family) and hypervalent halogens are real neutral
    # chemistry the parser only expresses via bracket atoms; the OpenSMILES implicit-H table (Cl/Br/I = 1)
    # would false-reject them -- the charge-agnostic ceiling (halogens = 7) does not.
    for smiles in ("F[I](F)(F)(F)F", "O=[Cl](=O)O[H]", "C[I](OC(C)=O)OC(C)=O", "F[Br](F)F"):
        mol = parse_smiles(smiles)
        assert mol.charge == 0
        _joined((mol,))                                                   # must NOT raise


def test_o_in_ring_at_valence_two_is_not_false_rejected():
    chx = [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1)]
    assert valence_sane(_g(list("CCCCC") + ["O"], chx)) is True


# --- the gate is wired fail-closed at both seams ---

def test_joined_refuses_a_valence_impossible_molecule():
    try:
        _joined((_pentavalent_carbon(),))
        raise AssertionError("a pentavalent carbon must be refused by the Molecule->graph adapter")
    except RuleError:
        pass


def test_da_provider_drops_a_valence_impossible_input_without_raising():
    transforms, complete = DielsAlderProvider().enumerate_transforms(_pentavalent_carbon(), (), budget=100000)
    assert transforms == () and complete is True


def test_retro_core_refuses_an_impossible_graph_definitively():
    audits, complete = retro_da_disconnections(_g("CF", [(0, 1, 5)]))
    assert audits == () and complete is True


# --- the honest boundary (dalembert KILL 1): neutral-only-impossibles are NOT caught, by design ---

def test_charge_blindness_boundary_is_documented():
    # A hand-built NEUTRAL ammonium (N degree 4) is impossible as a neutral but possible as N+.  With no
    # per-atom formal charge in the graph it is indistinguishable from a valid ion, so the charge-agnostic
    # ceiling ADMITS it (N<=5).  This is the disclosed information-theoretic boundary, not a silent bug; it
    # does not arise from the parser (which assigns the charge, refused upstream).  Pinned so a future
    # "we close this too" claim must confront the missing datum.
    neutral_ammonium = Molecule(("N", "H", "H", "H", "H"), frozenset({Bond(0, k, 1) for k in range(1, 5)}))
    assert neutral_ammonium.charge == 0
    assert valence_sane(_joined((neutral_ammonium,))) is True


# --- regression: the gate is a no-op on valid chemistry (the parent DA still fires) ---

def test_the_valence_gate_does_not_disturb_the_parent_da():
    chx = _g("C" * 6, [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1)])  # cyclohexene
    audits, complete = retro_da_disconnections(chx)
    assert complete and len(audits) == 1
