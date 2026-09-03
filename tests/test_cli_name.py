"""CLI-NAME-01: normal names accepted without private formatting -- the section-14.2 explicit-form surface.

The ONE parser (ID-PARSE-01) resolves every form; this pins the CLI SURFACE over it: the explicit value-form flags
(--name/--smiles/--inchi/--formula/--target-file) across the structure-search verbs (recompile, synthesize), the
--input-kind parity synthesize gained, the disambiguation/ambiguity matrix (more than one way, or none, is a loud
exit 2 -- never a silent guess), the section-5.4 refusal (a bare formula/InChI cannot drive a structure search),
and the ParseReceipt echo synthesize used to drop.  All via the ONE shared resolver so the verbs cannot drift.
"""
import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import main as cli_main
from smartchem.experiment.cli import main as syn_main
from smartchem.identity_parse import EXPLICIT_CLI_FORMS, InputKind, IdentityParseError, resolve_cli_target


def _run(main, argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            rc = main(argv)
        except SystemExit as exc:  # argparse errors
            rc = 2 if exc.code not in (0, None) else 0
    return rc, out.getvalue(), err.getvalue()


class TestResolveCliTargetUnit:
    """The shared resolver -- the ONE place positional / --input-kind / explicit forms are reconciled."""

    def test_positional_with_no_kind_is_auto(self):
        assert resolve_cli_target("paracetamol", None, {f: None for f, _ in EXPLICIT_CLI_FORMS}) == ("paracetamol", None)

    def test_positional_with_input_kind(self):
        forms = {f: None for f, _ in EXPLICIT_CLI_FORMS}
        assert resolve_cli_target("C8H9NO2", "formula", forms) == ("C8H9NO2", InputKind.FORMULA)

    def test_an_explicit_form_forces_its_kind(self):
        forms = {f: None for f, _ in EXPLICIT_CLI_FORMS}
        forms["name"] = "acetic anhydride"
        assert resolve_cli_target(None, None, forms) == ("acetic anhydride", InputKind.NAME)
        forms = {f: None for f, _ in EXPLICIT_CLI_FORMS}
        forms["inchi"] = "InChI=1S/H2O/h1H2"
        assert resolve_cli_target(None, None, forms) == ("InChI=1S/H2O/h1H2", InputKind.INCHI)

    def test_no_target_at_all_is_refused(self):
        with pytest.raises(IdentityParseError, match="no target given"):
            resolve_cli_target(None, None, {f: None for f, _ in EXPLICIT_CLI_FORMS})

    def test_two_explicit_forms_are_refused(self):
        forms = {f: None for f, _ in EXPLICIT_CLI_FORMS}
        forms["name"], forms["smiles"] = "X", "Y"
        with pytest.raises(IdentityParseError, match="mutually exclusive"):
            resolve_cli_target(None, None, forms)

    def test_positional_plus_a_form_is_refused(self):
        forms = {f: None for f, _ in EXPLICIT_CLI_FORMS}
        forms["name"] = "X"
        with pytest.raises(IdentityParseError, match="ONE way"):
            resolve_cli_target("paracetamol", None, forms)

    def test_a_form_plus_input_kind_is_refused(self):
        forms = {f: None for f, _ in EXPLICIT_CLI_FORMS}
        forms["name"] = "X"
        with pytest.raises(IdentityParseError, match="already fixes the input kind"):
            resolve_cli_target(None, "smiles", forms)


class TestRecompileExplicitForms:
    def test_name_form_resolves_and_searches(self):
        rc, out, _ = _run(cli_main, ["recompile", "--name", "acetic anhydride", "--max-depth", "1"])
        assert rc in (0, 3, 4)                                   # a real search ran (not a parse refusal)

    def test_smiles_form_resolves(self):
        rc, _, _ = _run(cli_main, ["recompile", "--smiles", "CC(=O)OC", "--max-depth", "1"])
        assert rc in (0, 3, 4)

    def test_bare_inchi_is_refused_for_a_structure_search(self):
        rc, out, _ = _run(cli_main, ["recompile", "--inchi", "InChI=1S/H2O/h1H2"])
        assert rc == 2                                           # formula-layer identity, section 5.4
        assert "INVALID_INPUT" in out

    def test_bare_formula_is_refused_for_a_structure_search(self):
        rc, out, _ = _run(cli_main, ["recompile", "--formula", "C8H9NO2"])
        assert rc == 2

    def test_two_forms_are_a_loud_exit_2(self):
        rc, _, _ = _run(cli_main, ["recompile", "--name", "X", "--smiles", "Y"])
        assert rc == 2

    def test_no_target_is_a_loud_exit_2(self):
        rc, _, _ = _run(cli_main, ["recompile"])
        assert rc == 2

    def test_positional_and_a_form_together_are_refused(self):
        rc, _, _ = _run(cli_main, ["recompile", "paracetamol", "--name", "X"])
        assert rc == 2

    def test_a_form_with_input_kind_is_refused(self):
        rc, _, _ = _run(cli_main, ["recompile", "--name", "paracetamol", "--input-kind", "smiles"])
        assert rc == 2

    def test_the_positional_still_works(self):
        rc, _, _ = _run(cli_main, ["recompile", "acetic anhydride", "--max-depth", "1"])
        assert rc in (0, 3, 4)

    def test_emit_request_via_a_value_form(self):
        rc, out, _ = _run(cli_main, ["recompile", "--name", "acetic anhydride", "--emit-request"])
        assert rc == 0 and out.strip().startswith("{")


class TestSynthesizeExplicitForms:
    def test_synthesize_gained_input_kind_parity(self):
        rc, out, _ = _run(syn_main, ["acetic anhydride", "--input-kind", "name", "--offline", "--max-depth", "1"])
        assert rc in (0, 3, 4)

    def test_name_form_resolves_and_echoes_the_receipt(self):
        rc, out, _ = _run(syn_main, ["--name", "acetic anhydride", "--offline", "--max-depth", "1"])
        assert rc in (0, 3, 4)
        assert "IDENTITY RESOLVED" in out and "OFFLINE_REGISTRY" in out   # the receipt echo synthesize used to drop

    def test_positional_also_echoes_the_receipt(self):
        rc, out, _ = _run(syn_main, ["CC(=O)Nc1ccc(O)cc1", "--offline", "--max-depth", "1"])
        assert "IDENTITY RESOLVED" in out

    def test_bare_inchi_is_refused(self):
        rc, _, err = _run(syn_main, ["--inchi", "InChI=1S/H2O/h1H2", "--offline"])
        assert rc == 2 and "section 5.4" in err

    def test_two_forms_are_refused(self):
        rc, _, _ = _run(syn_main, ["--name", "X", "--smiles", "Y"])
        assert rc == 2


class TestInputKindHelpIsHonest:
    """Iron rule: the --input-kind help must not claim inchi/formula are 'not yet resolved offline' -- ID-PARSE-01
    resolves them; a bare inchi/formula is refused because it names composition, not structure (section 5.4)."""

    def test_the_stale_not_yet_resolved_claim_is_gone(self):
        rc, out, _ = _run(cli_main, ["recompile", "--help"])
        assert rc == 0
        assert "not yet resolved offline" not in out
        assert "section 5.4" in out or "5.4" in out
