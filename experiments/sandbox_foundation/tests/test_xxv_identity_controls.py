"""OPERATION XXV, issue #130: identity-layer controls (characterization only; no behaviour change).

Pins what the production perception layer separates, and two measured gaps a configuration-aware matcher must not
inherit. See docs/research/IDENTITY_CARRIER_DESIGN_XXV.md.

The two `test_known_gap_*` tests assert CURRENT behaviour that is a recorded defect. When either gap is repaired these
tests must fail; update them together with the design document, never silently.
"""

import pytest

from smartchem.identity import LayeredIdentity, MatchLayer, same_identity_at
from smartchem.smiles import parse_smiles, parse_smiles_features

LAYERS = (MatchLayer.FORMULA, MatchLayer.CONSTITUTION, MatchLayer.CONFIGURATION, MatchLayer.ISOTOPIC)

# (label, a, b, expected same_identity_at per layer in LAYERS order); None means the layer is not perceived
PAIRS = [
    ("enantiomers", "N[C@@H](C)C(=O)O", "N[C@H](C)C(=O)O", (True, True, False, False)),
    ("specified_vs_unmarked", "N[C@@H](C)C(=O)O", "NC(C)C(=O)O", (True, True, False, False)),
    ("E_vs_Z_marked", "C/C=C/C", "C/C=C\\C", (True, True, None, None)),
    ("perdeuteromethane", "[2H]C([2H])([2H])[2H]", "C", (True, True, True, False)),
    ("c13_ethane", "C[13CH3]", "CC", (True, True, True, False)),
    ("same_formula_constitutional_isomers", "CCO", "COC", (True, False, False, False)),
    ("charge_separated_resonance", "C[N+](=O)[O-]", "C[N+]([O-])=O", (True, True, True, True)),
    ("aromatic_vs_kekule", "[O-]C(=O)c1ccccc1", "[O-]C(=O)C1=CC=CC=C1", (True, True, True, True)),
]


def _layered(smiles):
    molecule, features = parse_smiles_features(smiles)
    return LayeredIdentity.of_molecule(molecule, features)


@pytest.mark.parametrize("label,a,b,expected", PAIRS, ids=[p[0] for p in PAIRS])
def test_layer_verdicts(label, a, b, expected):
    la, lb = _layered(a), _layered(b)
    assert tuple(same_identity_at(la, lb, layer) for layer in LAYERS) == expected


def test_controls_discriminate_a_constitution_only_matcher():
    # Non-vacuity: a matcher that keys on CONSTITUTION alone merges every pair that differs only in configuration
    # or isotope, while the finer layers separate them. If this fails, the table above no longer tests anything.
    merged_by_constitution = [
        label for label, a, b, expected in PAIRS
        if same_identity_at(_layered(a), _layered(b), MatchLayer.CONSTITUTION) and False in expected
    ]
    assert set(merged_by_constitution) == {"enantiomers", "specified_vs_unmarked", "perdeuteromethane", "c13_ethane"}


def test_known_gap_route_terminal_identity_is_constitution_only():
    # #130 as measured: route search keys terminals on a constitution-only identity, so enantiomers and
    # isotopologues are one terminal.
    from smartchem.experiment.routes import _ident
    from smartchem.experiment.stock import structure_key

    for key in (_ident, structure_key):
        assert key(parse_smiles("N[C@@H](C)C(=O)O")) == key(parse_smiles("N[C@H](C)C(=O)O"))
        assert key(parse_smiles("[2H]C([2H])([2H])[2H]")) == key(parse_smiles("C"))
        assert key(parse_smiles("CCO")) != key(parse_smiles("COC"))


@pytest.mark.parametrize("smiles", ["NC(C)C(=O)O", "CC(O)CC", "CC=CC"])
def test_known_gap_unmarked_stereogenic_element_reads_configuration_complete(smiles):
    # Recorded perception gap (design doc section 2): an UNMARKED stereogenic element is reported as fully perceived
    # (configuration_complete=True, configuration_digest=None), the same class as a genuinely achiral molecule.
    _molecule, features = parse_smiles_features(smiles)
    assert features.configuration_complete is True
    assert features.configuration_digest is None
    assert _layered(smiles).known_layer is MatchLayer.ISOTOPIC


@pytest.mark.parametrize("smiles", ["CCO", "OCC(O)CO"])
def test_achiral_molecules_read_configuration_complete(smiles):
    _molecule, features = parse_smiles_features(smiles)
    assert features.configuration_complete is True
    assert features.configuration_digest is None


def test_marked_but_unperceived_double_bond_stays_unknown():
    _molecule, features = parse_smiles_features("C/C=C/C")
    assert features.configuration_complete is False
    assert _layered("C/C=C/C").known_layer is MatchLayer.CONSTITUTION
