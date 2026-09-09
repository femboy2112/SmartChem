"""STEREO-DOSSIER-01: the perceived target stereochemistry (CIP R/S + configuration completeness) is surfaced in the
human synthesis dossier -- the first CONSUMER of the ID-STEREO-01 cip_labels / configuration perception, which were
perception-only with zero consumers before this.  Integration controls use invented metadata, never chemistry evidence.

The perception is PERCEPTION ONLY: the route search runs on the achiral constitution Molecule (the §5.3 collapse), so
these assertions check a DISCLOSURE block, never a search-identity or bench claim."""
import io
from contextlib import redirect_stderr, redirect_stdout

from smartchem.cli import main
from smartchem.experiment.compile import _target_stereo_lines, compile_synthesis
from smartchem.smiles import parse_smiles_features


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def test_parse_smiles_features_now_carries_cip_labels():
    """SmilesFeatures gains cip_labels (the same soundly-nameable R/S the standalone cip_labels() returns)."""
    # a centre with FOUR distinct-atomic-number neighbours (H, F, Cl, Br) is soundly named; anchored S (the cip_labels
    # L-alanine=S convention, cross-checked on this exact molecule in _cip_labels' docstring).
    _mol, distinct = parse_smiles_features("[C@H](F)(Cl)Br")
    assert distinct.cip_labels == ("S",) and distinct.tetrahedral_stereo
    # L-alanine: TWO carbons on the centre (CH3, COOH) -- ROUND 20's general Rule-1a digraph now NAMES it (S), the
    # common same-element case the old distinct-Z slice deferred.
    _m2, alanine = parse_smiles_features("N[C@@H](C)C(=O)O")
    assert alanine.cip_labels == ("S",) and alanine.tetrahedral_stereo
    # ROUND 35: parser-preserved written order admits a constitutional ring stereocentre.
    _m3, ring = parse_smiles_features("N[C@]1(F)CCCCO1")
    assert ring.cip_labels == ("R",) and ring.tetrahedral_stereo
    # achiral: no marker, no label.
    _m4, para = parse_smiles_features("CC(=O)Nc1ccc(O)cc1")
    assert para.cip_labels == () and not para.tetrahedral_stereo


def test_target_stereo_lines_discloses_named_deferred_and_achiral():
    _mol, named = parse_smiles_features("[C@H](F)(Cl)Br")
    lines = _target_stereo_lines(named)
    assert lines and "TARGET STEREOCHEMISTRY" in lines[0] and "PERCEPTION ONLY" in lines[0]
    assert any("soundly named" in ln and "1 of 1" in ln and "(S)" in ln for ln in lines)
    assert any("configuration perception" in ln and "COMPLETE" in ln for ln in lines)
    # A recursive pseudo-asymmetric ring pair remains an explicit deferral, never silently dropped.
    _m2, ring = parse_smiles_features("O[C@H]1CC[C@@H](C)CC1")
    deferred = _target_stereo_lines(ring)
    assert deferred and any("2 of 2" in ln and "NOT soundly named" in ln and "deferral" in ln for ln in deferred)
    # achiral target and a name/formula target (features None) disclose NOTHING (no noise on a flat molecule).
    _m3, para = parse_smiles_features("CC(=O)Nc1ccc(O)cc1")
    assert _target_stereo_lines(para) == ()
    assert _target_stereo_lines(None) == ()


def test_a_named_centre_never_hides_a_sibling_deferred_centre():
    """STEREO-DOSSIER-01 fold (evil-morty Finding 1): the deferral disclosure is INDEPENDENT of the named one, so a
    target with ONE nameable centre AND another deferred centre discloses BOTH -- never the earlier silent omission
    that read a di-stereocentre target as a mono one."""
    # One constitutional centre names while a mutually dependent pseudo ring pair remains deferred.
    _mol, feats = parse_smiles_features("Br[C@H](Cl)CO[C@H]1CC[C@@H](C)CC1")
    assert feats.stereocentres_marked == 3 and feats.cip_labels == ("S",)
    lines = _target_stereo_lines(feats)
    assert any("1 of 3" in ln and "soundly named" in ln and "NOT" not in ln for ln in lines)
    assert any("2 of 3" in ln and "NOT soundly named" in ln for ln in lines)
    # and the completeness line is explicitly SEPARATE from naming, so 'COMPLETE' can never be read as 'all named'.
    assert any("SEPARATE from the R/S naming" in ln for ln in lines)


def test_compile_synthesis_render_carries_the_block_only_when_stereo_is_perceived():
    mol, feats = parse_smiles_features("[C@H](F)(Cl)Br")
    with_stereo = compile_synthesis(mol, target_features=feats).render()
    assert "TARGET STEREOCHEMISTRY" in with_stereo and "soundly named" in with_stereo and "(S)" in with_stereo
    # the SAME dossier without the features (a name target has none) shows no stereo block -- the render is unchanged.
    without = compile_synthesis(mol, target_features=None).render()
    assert "TARGET STEREOCHEMISTRY" not in without
    # an achiral target with features present still shows nothing (the block fires on perceived stereo, not on presence).
    apara, pfeats = parse_smiles_features("CC(=O)Nc1ccc(O)cc1")
    assert "TARGET STEREOCHEMISTRY" not in compile_synthesis(apara, target_features=pfeats).render()


def test_synthesize_cli_surfaces_the_perceived_rs_to_a_chemist():
    """The end-to-end bite: a chemist running `synthesize` on a chiral SMILES SEES the perceived R/S in the dossier."""
    code, out, _err = _cli(["synthesize", "smiles:[C@H](F)(Cl)Br"])
    assert "TARGET STEREOCHEMISTRY" in out and "soundly named" in out and "(S)" in out
    # an achiral target's dossier carries no stereo block (no false stereo where none was declared).
    code2, out2, _err2 = _cli(["synthesize", "smiles:CC(=O)Nc1ccc(O)cc1"])
    assert "TARGET STEREOCHEMISTRY" not in out2
