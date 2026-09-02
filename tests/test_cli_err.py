"""CLI-ERR-01 -- ONE error-classification authority: invalid chemistry -> exit 2, model refusal -> exit 5, never a
traceback, and a genuine bug is NEVER laundered into a domain code (it re-raises to main()'s exit-70 guard).

Every command routes its raised domain exceptions through :func:`smartchem.cli._domain_exit`, so the mapping cannot
drift per command.  The InChI / formula / formula-file input kinds are DECLARED by section 14.2 but not yet resolved
offline (ID-PARSE-01): the ``--input-kind`` flag surfaces them as a loud INVALID_INPUT (exit 2), never a mis-parse.
"""
from __future__ import annotations

import io
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import _domain_exit, main
from smartchem.decompiler import DecompilerError, IdentityUnsupportedError
from smartchem.identity_parse import IdentityParseError
from smartchem.structure_descent import ScissionError


class TestCentralMapperClassification:
    """The unit-level classifier: the right section-14.4 code per exception FAMILY, most-specific first."""

    @pytest.mark.parametrize(
        "exc,expected",
        [
            (ScissionError("charged"), 5),                        # model-boundary refusal
            (IdentityUnsupportedError("charged formula"), 5),     # a DecompilerError subclass -> still a refusal
            (IdentityParseError("bad name"), 2),                  # unparseable identity
            (DecompilerError("bad formula"), 2),                  # invalid chemistry input
            (ValueError("bad value"), 2),
            (TypeError("bad type"), 2),
        ],
    )
    def test_domain_family_maps_to_its_code(self, exc, expected):
        err = io.StringIO()
        with redirect_stderr(err):
            assert _domain_exit(exc, "probe") == expected
        # concise line, never a raw traceback
        assert "Traceback (most recent call last)" not in err.getvalue()
        assert err.getvalue().startswith("probe: ")

    def test_a_refusal_is_not_mislabelled_invalid_despite_being_a_valueerror(self):
        # ScissionError/IdentityUnsupportedError are ValueError subclasses; the refusal check MUST win.
        err = io.StringIO()
        with redirect_stderr(err):
            code = _domain_exit(IdentityUnsupportedError("charged"), "probe")
        assert code == 5 and "chemistry-model boundary" in err.getvalue()

    def test_a_non_domain_error_is_re_raised_not_laundered(self):
        # the inverse of the exit-70 guard's sin: a genuine bug must NOT become a domain 2/5.
        with pytest.raises(RuntimeError):
            _domain_exit(RuntimeError("a real bug"), "probe")
        with pytest.raises(KeyError):
            _domain_exit(KeyError("missing"), "probe")


def _cli(argv):
    """Run ``main`` capturing BOTH streams: a typed recompile response render prints its INVALID/REFUSED diagnostic
    to stdout, while the central mapper's raised-exception line prints to stderr -- a robust test reads both."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue() + err.getvalue()


class TestUnsupportedInputKindsAreLoudInvalid:
    @pytest.mark.parametrize("kind", ["inchi", "formula", "target-file"])
    def test_declared_but_unresolved_kind_is_exit_2_in_process(self, kind):
        # ID-PARSE-01 FINISHED: 'paracetamol' is a NAME, so reading it as an InChI/formula/file is a wrong-payload
        # INVALID (a bad formula char, a malformed InChI, a missing file) -- still a LOUD, concise exit 2, never a
        # traceback and never a silent mis-parse.  (These kinds now RESOLVE for a well-formed payload of their form.)
        code, err = _cli(["recompile", "paracetamol", "--input-kind", kind, "--max-depth", "1"])
        assert code == 2
        assert err.strip() and "Traceback (most recent call last)" not in err

    @pytest.mark.parametrize("kind", ["inchi", "formula", "target-file"])
    def test_declared_but_unresolved_kind_is_exit_2_via_subprocess(self, kind):
        proc = subprocess.run(
            [sys.executable, "-m", "smartchem", "recompile", "paracetamol", "--input-kind", kind, "--max-depth", "1"],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 2, proc.stderr
        assert "Traceback (most recent call last)" not in proc.stderr

    def test_unsupported_kind_via_json_is_also_exit_2(self):
        code, _ = _cli(["recompile", "paracetamol", "--input-kind", "inchi", "--json", "--max-depth", "1"])
        assert code == 2

    @pytest.mark.parametrize("kind", ["inchi", "formula", "target-file"])
    def test_compile_human_path_honours_input_kind_no_silent_bypass(self, kind):
        # red-team CLIERR-COMPILE-INPUTKIND-BYPASS: the `compile` alias's HUMAN path used to ignore --input-kind and
        # AUTO-mis-parse to a confident exit-0 dossier while --json/recompile gave exit 2.  Now it honours it -> 2.
        code, err = _cli(["compile", "water", "--input-kind", kind, "--max-depth", "1"])
        assert code == 2
        assert "Traceback (most recent call last)" not in err

    def test_compile_human_and_json_agree_on_the_unsupported_kind_code(self):
        human, _ = _cli(["compile", "water", "--input-kind", "inchi", "--max-depth", "1"])
        js, _ = _cli(["compile", "water", "--input-kind", "inchi", "--json", "--max-depth", "1"])
        assert human == js == 2

    def test_explicit_smiles_input_kind_still_works(self):
        # the flag is not a blanket refuser: a supported kind resolves normally.  With explicit --input-kind smiles
        # the target is the BARE SMILES (no smiles: prefix -- that is an AUTO convenience, parsed literally here).
        code, _ = _cli(["recompile", "CC(=O)OC", "--input-kind", "smiles", "--max-depth", "1"])
        assert code in (0, 3, 4)  # a real search outcome, never a refusal/invalid


class TestBadNumericArgumentsAreExit2:
    @pytest.mark.parametrize("value", ["notanint", "inf", "1.5", "0", "-3"])
    def test_bad_max_depth_is_exit_2(self, value):
        # argparse's int/positive-int coercion is a BaseException(SystemExit(2)) -- a section-14.4 code 2, and it
        # passes THROUGH the exit-70 guard untouched, never laundered into an internal error.
        proc = subprocess.run(
            [sys.executable, "-m", "smartchem", "recompile", "water", "--max-depth", value],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 2, proc.stderr
        assert "Traceback (most recent call last)" not in proc.stderr


class TestDomainErrorsAreConciseNotTracebacks:
    @pytest.mark.parametrize(
        "argv,code",
        [
            (["recompile", "definitely-not-a-real-name", "--max-depth", "1"], 2),   # unparseable identity
            (["decompile", "notaformula"], 2),                                       # invalid formula
            (["recompile", "smiles:[Na+]", "--max-depth", "1"], 5),                  # charged: model refusal
        ],
    )
    def test_the_message_is_concise_with_no_traceback(self, argv, code):
        got, err = _cli(argv)
        assert got == code
        assert "Traceback (most recent call last)" not in err
