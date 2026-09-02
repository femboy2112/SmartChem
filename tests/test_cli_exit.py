"""CLI-EXIT-01 -- the standard's section 14.4 exit-code table, observed through the ONE shared service, plus the
top-level guarded service that turns an uncaught internal bug into exit 70 (never a raw traceback, never exit 1).

Acceptance (manifest 3.7): *"Codes 0/2/3/4/5 observed; add controlled internal-error fixture for 70."*

| Code | Meaning                                              |
|-----:|------------------------------------------------------|
|    0 | valid request, >=1 candidate, complete               |
|    2 | invalid arguments / unparseable identity             |
|    3 | valid request, complete search, no route             |
|    4 | valid request, partial/incomplete search             |
|    5 | refused at identity/model/evidence/constraint boundary |
|   70 | internal software error                              |
"""
from __future__ import annotations

import io
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import main
from smartchem.service import EXIT_INTERNAL

# (argv, expected section-14.4 exit code).  Every code the CLI can reach through a real invocation.
_MATRIX = [
    (["recompile", "smiles:CC(=O)OC", "--max-depth", "2"], 0),   # ROUTES_FOUND: complete, >=1 candidate
    (["recompile", "water", "--max-depth", "2"], 0),             # TARGET_ALREADY_AVAILABLE: on-hand stock
    (["recompile", "C8H9NO2xxx"], 2),                            # INVALID_INPUT: unparseable identity
    (["decompile", "notaformula"], 2),                           # INVALID_INPUT on the decompile front door
    (["recompile", "methane", "--max-depth", "2", "--cut-budget", "50000"], 3),  # NO_ROUTE_COMPLETE
    (["recompile", "paracetamol", "--max-depth", "2"], 4),       # INCOMPLETE: a bound bit
    (["recompile", "smiles:[Na+]"], 5),                          # REFUSED: charged input, chemistry-model boundary
    (["recompile", "water", "--match-layer", "configuration"], 5),  # REFUSED: unperceived identity layer (ID-LAYER-02)
]


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestExitMatrixInProcess:
    @pytest.mark.parametrize("argv,expected", _MATRIX)
    def test_main_returns_the_section_14_4_code(self, argv, expected):
        code, _, _ = _cli(argv)
        assert code == expected


class TestExitMatrixSubprocess:
    """The REAL process exit code (not just main()'s return): the subprocess matrix the manifest asks for."""

    @pytest.mark.parametrize("argv,expected", _MATRIX)
    def test_process_exit_code_matches(self, argv, expected):
        proc = subprocess.run(
            [sys.executable, "-m", "smartchem", *argv], capture_output=True, text=True, timeout=120
        )
        assert proc.returncode == expected, proc.stderr

    def test_argparse_bad_argument_exits_2(self):
        # argparse raises SystemExit(2) -- a BaseException that passes THROUGH the internal-error guard untouched,
        # so a bad flag stays a section-14.4 code 2, not a laundered 70.
        proc = subprocess.run(
            [sys.executable, "-m", "smartchem", "recompile", "water", "--max-depth", "not-an-int"],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 2

    def test_help_exits_0(self):
        proc = subprocess.run(
            [sys.executable, "-m", "smartchem", "--help"], capture_output=True, text=True, timeout=120
        )
        assert proc.returncode == 0


class TestInternalErrorGuardExit70:
    """The controlled internal-error fixture: an uncaught bug becomes exit 70 with a concise message, no traceback."""

    def test_uncaught_engine_error_maps_to_70(self, monkeypatch):
        def boom(_request):
            raise RuntimeError("injected internal fault")

        # the handler does not catch RuntimeError; it escapes to main()'s top-level guard.
        monkeypatch.setattr("smartchem.service.run_compilation", boom)
        code, out, err = _cli(["recompile", "water"])
        assert code == EXIT_INTERNAL == 70
        assert "ERROR_INTERNAL" in err
        assert "RuntimeError" in err and "injected internal fault" in err
        # a concise diagnostic, NOT a raw Python traceback dumped to the user:
        assert "Traceback (most recent call last)" not in err
        assert "Traceback (most recent call last)" not in out

    def test_a_domain_error_is_NOT_laundered_into_70(self, monkeypatch):
        # a ValueError the handler already maps to exit 2 must stay 2 -- the guard is a net for the UNEXPECTED, it
        # does not swallow the mapped domain codes.
        code, _, _ = _cli(["recompile", "C8H9NO2xxx"])
        assert code == 2

    def test_the_exit_70_constant_is_the_standard_value(self):
        assert EXIT_INTERNAL == 70

    def test_cli_local_internal_constant_matches_the_service_table(self):
        # red-team CLI-EXIT-01-F2: the guard uses a LOCAL literal (not `from .service import EXIT_INTERNAL`) so it
        # can report 70 even when the escaping bug is a broken .service import. Pin the local == the service table.
        from smartchem.cli import _EXIT_INTERNAL
        assert _EXIT_INTERNAL == EXIT_INTERNAL == 70


class TestBrokenPipeIsNotAnInternalError:
    """red-team CLI-EXIT-01-F1: a downstream `| head`/`| less` close is a normal shell condition -- it must NOT be
    laundered into exit 70 or a false ERROR_INTERNAL self-diagnosis (section 14.4: 70 == internal software error)."""

    def test_downstream_pipe_close_is_not_laundered_to_70(self):
        # emit a large output, take one byte, then close the read end: the producer's next writes hit EPIPE.
        proc = subprocess.Popen(
            [sys.executable, "-m", "smartchem", "decompile", "C8H9NO2", "--max-multiplicity", "2"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        proc.stdout.read(1)
        proc.stdout.close()
        proc.wait(timeout=120)
        err = proc.stderr.read().decode()
        proc.stderr.close()
        assert proc.returncode != EXIT_INTERNAL          # NOT laundered into 70
        assert proc.returncode == 141                     # the conventional SIGPIPE code (128 + 13)
        assert "ERROR_INTERNAL" not in err                # NOT a false internal-error self-diagnosis
        assert "Traceback (most recent call last)" not in err
