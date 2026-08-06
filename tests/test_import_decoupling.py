"""The public API is served lazily (PEP 562): importing a light subpackage must not drag
in numpy/scipy, and every re-export must still resolve.

This guards the decoupling that makes ``smartchem.evidence`` usable as a standalone
dependency (an external project can run the probe-evidence auditor without paying for, or
depending on, the numeric domain stack), plus the completeness and fail-closed behaviour of
the lazy export table.

Independence note (this project's governing rule: a check derived from its own subject
checks nothing). The *behavioural* identity of the 388 re-exports — each name resolving to
the correct object — is proven by the full test suite, which imports real symbols and
asserts real behaviour without ever consulting the lazy export table. These tests guard the
orthogonal properties that suite does not: import-time decoupling, table/``__all__`` sync,
completeness of resolution, and fail-closed attribute access.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

import smartchem


def _heavy_modules_after(statement: str) -> set[str]:
    """Run ``statement`` in a clean interpreter; return the numpy/scipy modules it loaded."""
    script = textwrap.dedent(
        f"""
        import sys
        {statement}
        heavy = sorted(
            m for m in sys.modules
            if m == "numpy" or m.startswith(("numpy.", "scipy", "scipy."))
        )
        print("\\n".join(heavy))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], check=False, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
    return {line for line in completed.stdout.split() if line}


def test_importing_evidence_bridge_does_not_load_numpy():
    # The whole point of the bridge: a decoupled, stdlib-only import path for consumers.
    assert _heavy_modules_after("import smartchem.evidence") == set()


def test_importing_contracts_does_not_load_numpy():
    assert _heavy_modules_after("import smartchem.contracts") == set()


def test_importing_package_root_does_not_load_numpy():
    # Bare ``import smartchem`` runs the lazy __init__: stdlib only, no domain firehose.
    assert _heavy_modules_after("import smartchem") == set()


def test_every_public_name_resolves():
    unresolved = []
    for name in smartchem.__all__:
        try:
            getattr(smartchem, name)
        except AttributeError as error:
            unresolved.append(f"{name}: {error}")
    assert not unresolved, unresolved


def test_export_table_and_all_stay_in_lockstep():
    # Drift between __all__ and the lazy table = a silently missing or unroutable export.
    assert set(smartchem.__all__) == set(smartchem._ATTR_SOURCE)


def test_dir_covers_public_api():
    assert set(smartchem.__all__) <= set(dir(smartchem))


def test_bare_submodule_attribute_access_resolves():
    # `smartchem.runtime_registry` without a prior explicit import still resolves to the
    # submodule (not every submodule is re-exported by name; the __getattr__ fallback
    # handles this without masking a genuine ImportError inside a submodule).
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import smartchem; "
            "assert smartchem.runtime_registry.__name__ == 'smartchem.runtime_registry'",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_unknown_attribute_raises_attribute_error():
    try:
        smartchem.definitely_not_a_real_symbol
    except AttributeError:
        return
    raise AssertionError("a bogus attribute did not raise AttributeError")


def test_dir_hides_lazy_loader_machinery():
    # dir() advertises exactly the public API, not module-private machinery that the lazy
    # loader keeps in globals (_EXPORTS, _ATTR_SOURCE, importlib, ...).
    listed = set(dir(smartchem))
    assert listed == set(smartchem.__all__)
    assert "_EXPORTS" not in listed
    assert "importlib" not in listed


def test_pickle_round_trips_through_lazy_boundary():
    # A consumer pickling a SmartChem object across a process boundary must round-trip:
    # unpickling resolves the class by its real __module__ (a direct submodule import),
    # independent of the top-level lazy __getattr__.
    script = textwrap.dedent(
        """
        import pickle
        import smartchem
        original = smartchem.Config.atoms("C", "O")
        restored = pickle.loads(pickle.dumps(original))
        assert restored == original, (restored, original)
        print("round-trip-ok")
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], check=False, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
    assert "round-trip-ok" in completed.stdout
