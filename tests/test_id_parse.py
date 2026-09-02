"""ID-PARSE-01 -- ONE identity parser resolves every section-14.2 form with an echoed source/policy receipt.

Before this brick, ``resolve_target`` handled NAME and SMILES and refused INCHI/FORMULA/TARGET_FILE as a loud
"not yet supported".  This proves the finished parser service (:func:`smartchem.identity_parse.resolve_identity`):

* every form resolves as far as it can be perceived HONESTLY -- NAME/SMILES to a molecule (CONSTITUTION), FORMULA
  and an InChI's formula sublayer to a FORMULA-layer identity (no fabricated structure), TARGET_FILE by dispatch;
* each resolution carries a :class:`~smartchem.identity_parse.ParseReceipt` echoing the source, the normalised
  form, the layer reached, and any dropped/unconsumed layer -- surfaced into the response ``diagnostics``;
* an InChI's declared-but-unconsumed connectivity/stereo/isotope layers become typed section-5.3 BLOCKERS (the
  same records ID-STEREO-01 built), never a silent structural claim;
* an ambiguous string is disambiguated by an explicit kind/prefix, never silently guessed;
* a bare formula/InChI (composition, not structure) is refused for a structure search (recompile) per section 5.4.
"""
from __future__ import annotations

import pytest

from smartchem.contracts import canonical_digest
from smartchem.decompiler import Formula
from smartchem.identity_parse import (
    IdentityParseError,
    InputKind,
    ParseReceipt,
    ParseSource,
    resolve_identity,
    resolve_target,
    resolve_target_with_features,
)
from smartchem.service import (
    build_decompile_request,
    build_recompile_request,
    run_compilation,
)

_PARACETAMOL_INCHI = "InChI=1S/C8H9NO2/c1-6(10)9-7-2-4-8(11)5-3-7/h2-5,10H,1H3,(H,9,10)"


class TestEveryFormResolves:
    def test_name_resolves_to_a_constitution_molecule(self):
        r = resolve_identity("water")
        assert r.structure_perceived and r.molecule is not None
        assert r.receipt.source is ParseSource.OFFLINE_REGISTRY
        assert r.receipt.resolved_kind is InputKind.NAME and r.receipt.identity_layer == "CONSTITUTION"

    def test_smiles_resolves_to_a_molecule_with_features(self):
        r = resolve_identity("smiles:CC(=O)Nc1ccc(O)cc1")
        assert r.structure_perceived and r.features is not None
        assert r.receipt.source is ParseSource.SMILES_PARSER

    def test_formula_resolves_to_a_formula_layer_identity_no_structure(self):
        r = resolve_identity("C8H9NO2", InputKind.FORMULA)
        assert not r.structure_perceived and r.molecule is None
        assert r.formula == Formula.parse("C8H9NO2")
        assert r.receipt.source is ParseSource.FORMULA_PARSER and r.receipt.identity_layer == "FORMULA"

    def test_inchi_resolves_the_formula_sublayer_and_blocks_the_dropped_connectivity(self):
        r = resolve_identity(_PARACETAMOL_INCHI)
        assert not r.structure_perceived
        assert r.formula == Formula.parse("C8H9NO2")
        assert r.receipt.source is ParseSource.INCHI_FORMULA_LAYER
        # the /c connectivity the InChI DECLARED but this parser does not consume is a real structure BLOCKER
        assert any(loss.feature == "molecular-constitution" and loss.blocks("structure-identity") for loss in r.losses)
        assert any("connectivity" in note for note in r.receipt.notes)

    def test_inchi_charge_layers_are_consumed_not_dropped(self):
        # F1 (red-team, HIGH): standard InChI carries charge ONLY in /q and /p; ignoring them collapsed every
        # cation/anion to its NEUTRAL (a soundness break -- [NH4+] would share NH3's FORMULA identity).
        from smartchem.contracts import canonical_digest
        from smartchem.decompiler import Formula
        nh4 = resolve_identity("InChI=1S/H3N/h1H3/p+1", InputKind.INCHI)      # ammonium: true formula H4N, +1
        assert nh4.formula == Formula.of({"H": 4, "N": 1}, 1)
        nh3 = resolve_identity("InChI=1S/H3N/h1H3", InputKind.INCHI)          # neutral ammonia
        assert canonical_digest(nh4.formula) != canonical_digest(nh3.formula)  # no charge collapse
        assert any("charge layer" in note for note in nh4.receipt.notes)
        # /q net charge (a bare cation) and /p deprotonation (an anion, one H removed) also resolve correctly
        assert resolve_identity("InChI=1S/Na/q+1", InputKind.INCHI).formula.charge == 1
        acetate = resolve_identity("InChI=1S/C2H4O2/c1-2(3)4/h1H3,(H,3,4)/p-1", InputKind.INCHI)
        assert acetate.formula == Formula.of({"C": 2, "H": 3, "O": 2}, -1)

    def test_inchi_per_component_charge_is_refused(self):
        with pytest.raises(IdentityParseError):
            resolve_identity("InChI=1S/2CH4/q+1;+1", InputKind.INCHI)

    def test_inchi_stereo_and_isotope_layers_become_blockers(self):
        # a contrived InChI carrying /t (tetrahedral stereo) and /i (isotope) sublayers
        r = resolve_identity("InChI=1S/C3H6O/c1-3-2/h3H,1H3,2H2/t3-/i1+1", InputKind.INCHI)
        features = {loss.feature for loss in r.losses}
        assert "stereochemistry" in features and "isotope-labeling" in features
        assert any(loss.blocks("kinetics") for loss in r.losses)

    def test_target_file_dispatches_its_contents(self, tmp_path):
        f = tmp_path / "target.smi"
        f.write_text("smiles:CCO\n")
        r = resolve_identity(str(f), InputKind.TARGET_FILE)
        assert r.structure_perceived
        assert r.receipt.source is ParseSource.TARGET_FILE
        assert any("file" in note for note in r.receipt.notes)
        # the molecule is exactly what parsing 'CCO' directly gives
        assert canonical_digest(r.molecule) == canonical_digest(resolve_target("smiles:CCO"))

    def test_target_file_with_an_explicit_formula_is_a_formula_layer_identity(self, tmp_path):
        # a file's contents resolve on the AUTO path (name-or-SMILES); a FORMULA needs an explicit 'formula:' prefix
        # (or a bare InChI= header) -- never a silent formula-vs-SMILES guess (e.g. 'CO' means different species).
        f = tmp_path / "t.formula"
        f.write_text("formula:C8H9NO2")
        r = resolve_identity(str(f), InputKind.TARGET_FILE)
        assert not r.structure_perceived and r.formula == Formula.parse("C8H9NO2")


class TestExplicitFormsAndPrefixes:
    def test_bare_inchi_header_is_auto_detected(self):
        r = resolve_identity(_PARACETAMOL_INCHI, InputKind.AUTO)
        assert r.receipt.resolved_kind is InputKind.INCHI
        assert any("InChI=" in note for note in r.receipt.notes)

    @pytest.mark.parametrize("prefix,kind", [("name", InputKind.NAME), ("formula", InputKind.FORMULA)])
    def test_inline_prefix_forces_the_kind(self, prefix, kind):
        # 'water' is a registered name; 'H2O' is a formula.  Force each explicitly.
        payload = "water" if kind is InputKind.NAME else "H2O"
        r = resolve_identity(f"{prefix}:{payload}", InputKind.AUTO)
        assert r.receipt.resolved_kind is kind

    def test_smiles_prefix_forces_smiles_even_for_a_registered_name(self):
        # 'smiles:' must NOT fall through to a name lookup -- an unparseable SMILES is a loud error, not a name.
        with pytest.raises(IdentityParseError):
            resolve_identity("smiles:water")   # 'water' is not valid SMILES

    def test_name_prefix_is_strict_and_does_not_fall_through_to_smiles(self):
        # 'name:CCO' must NOT be read as the ethanol SMILES; NAME is strict (CCO is not a registered name).
        with pytest.raises(IdentityParseError):
            resolve_identity("name:CCO")


class TestAmbiguityIsDisambiguatedNotGuessed:
    def test_auto_resolves_a_registered_name_before_trying_smiles(self):
        # the AUTO precedence (name-first, else SMILES) is ECHOED so the caller sees which interpretation won.
        r = resolve_identity("water", InputKind.AUTO)
        assert r.receipt.resolved_kind is InputKind.NAME

    def test_auto_falls_through_to_smiles_for_an_unregistered_parseable_string(self):
        r = resolve_identity("CCO", InputKind.AUTO)
        assert r.receipt.resolved_kind is InputKind.SMILES and r.structure_perceived


class TestRoundTrips:
    def test_name_and_smiles_of_one_species_agree_on_constitution(self):
        # 'water' the registered name and 'O' the SMILES resolve to the SAME molecule.
        # the registry stores a molecule in hand-entered order; identity is compared at canonical form (the same
        # .canonical() the pipeline's _structure_ident uses), so the two spellings collapse to ONE species.
        by_name = resolve_target("water")
        by_smiles = resolve_target("smiles:O")
        assert canonical_digest(by_name.canonical()) == canonical_digest(by_smiles.canonical())

    def test_formula_and_inchi_formula_layer_agree(self):
        by_formula = resolve_identity("C8H9NO2", InputKind.FORMULA).formula
        by_inchi = resolve_identity(_PARACETAMOL_INCHI).formula
        assert by_formula == by_inchi


class TestFailClosed:
    def test_multi_component_inchi_is_refused(self):
        with pytest.raises(IdentityParseError):
            resolve_identity("InChI=1S/C2H6O.C2H4O2/c...", InputKind.INCHI)

    def test_malformed_inchi_is_refused(self):
        with pytest.raises(IdentityParseError):
            resolve_identity("InChI=1S", InputKind.INCHI)

    def test_missing_target_file_is_refused(self, tmp_path):
        with pytest.raises(IdentityParseError):
            resolve_identity(str(tmp_path / "does-not-exist"), InputKind.TARGET_FILE)

    def test_empty_target_file_is_refused(self, tmp_path):
        f = tmp_path / "empty"
        f.write_text("   \n")
        with pytest.raises(IdentityParseError):
            resolve_identity(str(f), InputKind.TARGET_FILE)

    def test_a_formula_only_identity_is_refused_for_a_structure_search(self):
        # resolve_target MUST refuse a formula/InChI: a structure descent needs a molecule (section 5.4).
        with pytest.raises(IdentityParseError):
            resolve_target("C8H9NO2", InputKind.FORMULA)
        with pytest.raises(IdentityParseError):
            resolve_target_with_features(_PARACETAMOL_INCHI, InputKind.INCHI)


class TestServiceWiring:
    def test_recompile_response_echoes_the_resolution_receipt(self):
        resp = run_compilation(build_recompile_request("water", helper_reagents=("water",)))
        assert any("IDENTITY RESOLVED" in d for d in resp.diagnostics)

    def test_decompile_inchi_carries_the_constitution_blocker_and_descends(self):
        resp = run_compilation(build_decompile_request(_PARACETAMOL_INCHI, input_kind=InputKind.INCHI))
        features = {loss.feature for loss in resp.identity_losses}
        assert "molecular-constitution" in features
        assert any("IDENTITY RESOLVED" in d for d in resp.diagnostics)
        # it actually ran a formula descent (an IR was produced), not a refusal
        assert resp.compilation_ir is not None

    def test_decompile_formula_echoes_a_formula_layer_receipt(self):
        resp = run_compilation(build_decompile_request("C8H9NO2"))
        assert any("FORMULA_PARSER" in d for d in resp.diagnostics)

    def test_recompile_of_a_bare_formula_is_invalid_not_a_wrong_search(self):
        # a structure search on a bare formula is refused (section 5.4), never silently run on a guessed structure.
        resp = run_compilation(build_recompile_request("C8H9NO2", input_kind=InputKind.FORMULA,
                                                       helper_reagents=("water",)))
        assert resp.outcome.name == "INVALID_INPUT" or "no molecule" in " ".join(resp.diagnostics)


class TestReceiptValue:
    def test_receipt_is_a_frozen_validated_value(self):
        r = ParseReceipt(InputKind.AUTO, InputKind.NAME, ParseSource.OFFLINE_REGISTRY, "H2O", "CONSTITUTION", ())
        with pytest.raises(Exception):
            r.normalized = "x"  # frozen

    def test_receipt_rejects_a_bad_layer(self):
        with pytest.raises(ValueError):
            ParseReceipt(InputKind.AUTO, InputKind.NAME, ParseSource.OFFLINE_REGISTRY, "H2O", "ATOMIC", ())


class TestBackwardCompatibility:
    def test_resolve_target_still_returns_a_molecule_for_name_and_smiles(self):
        assert resolve_target("water") is not None
        m, f = resolve_target_with_features("smiles:CCO")
        assert m is not None and f is not None
