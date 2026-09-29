"""0.9.5 release-engineering invariants (S12 digest, S13 ``-m smartchem.cli``, single-source version).

Each law has a test that FAILS on the pre-0.9.5 behaviour:
* dynamic version          -> fails while pyproject carries a hand-copied literal ``version = "..."``
* ``-m smartchem.cli``     -> fails on the silent exit-0 no-op (no ``__main__`` guard)
* digest ambient-independence / copy-invariance -> fail while ``<package parent>/pyproject.toml`` is hashed
"""
from __future__ import annotations

import importlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import smartchem
from smartchem import program as program_module

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _project_table() -> dict:
    """The parsed pyproject (tomllib is 3.11+; the regex fallback covers the 3.10 floor)."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - 3.10 only
        return {}
    return tomllib.loads(PYPROJECT)


def test_version_is_single_sourced_from_the_package():
    table = _project_table()
    if table:
        assert table["project"]["dynamic"] == ["version"]
        assert "version" not in table["project"]  # no hand-copied literal to drift
        assert table["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "smartchem.__version__"}
    else:  # pragma: no cover - 3.10 only
        assert re.search(r'^dynamic\s*=\s*\["version"\]', PYPROJECT, re.M)
        assert re.search(r'version\s*=\s*\{attr\s*=\s*"smartchem\.__version__"\}', PYPROJECT)
        project_block = PYPROJECT.split("[project.optional-dependencies]")[0]
        assert not re.search(r'^version\s*=\s*"', project_block, re.M)
    # setuptools reads `attr` by static AST scan, which needs a plain string literal assignment.
    init = (ROOT / "smartchem" / "__init__.py").read_text(encoding="utf-8")
    literal = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', init, re.M)
    assert literal and literal.group(1) == smartchem.__version__


def test_every_console_script_target_resolves_to_a_callable():
    table = _project_table()
    if table:
        scripts = table["project"]["scripts"]
    else:  # pragma: no cover - 3.10 only
        block = PYPROJECT.split("[project.scripts]")[1].split("\n[")[0]
        scripts = dict(re.findall(r'^([\w-]+)\s*=\s*"([^"]+)"', block, re.M))
    assert set(scripts) == {"smartchem", "smartchem-verify-probes"}
    for name, target in scripts.items():
        module, _, attr = target.partition(":")
        fn = getattr(importlib.import_module(module), attr, None)
        assert callable(fn), f"[project.scripts] {name} -> {target} does not resolve to a callable"


def test_python_dash_m_smartchem_cli_prints_the_version():
    done = subprocess.run(
        [sys.executable, "-m", "smartchem.cli", "--version"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 0
    assert done.stdout == f"smartchem {smartchem.__version__}\n"  # was: empty stdout, rc 0


def _copy_package_py(dest: Path) -> Path:
    """Copy only the package's ``.py`` files (all the digest may read) to ``dest/smartchem``."""
    package = ROOT / "smartchem"
    target = dest / "smartchem"
    for src in package.rglob("*.py"):
        out = target / src.relative_to(package)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out)
    return target


def _digest_as_if_located_at(monkeypatch, package_dir: Path) -> str:
    monkeypatch.setattr(program_module, "__file__", str(package_dir / "program.py"))
    return program_module._compiler_implementation_digest()


def test_implementation_digest_reads_nothing_outside_the_package(monkeypatch, tmp_path):
    copy = _copy_package_py(tmp_path / "site-packages")
    baseline = _digest_as_if_located_at(monkeypatch, copy)

    # An ambient sibling of the package (what an installed tree may or may not have) must not matter.
    (copy.parent / "pyproject.toml").write_text("[project]\nname = 'ambient'\n")
    (copy.parent / "stray.py").write_text("x = 1\n")
    assert _digest_as_if_located_at(monkeypatch, copy) == baseline

    # ... but the package's own code must (the digest still binds approval to implementation).
    (copy / "thermo.py").write_bytes((copy / "thermo.py").read_bytes() + b"\n# changed\n")
    assert _digest_as_if_located_at(monkeypatch, copy) != baseline


def test_source_tree_and_relocated_copy_have_the_same_digest(monkeypatch, tmp_path):
    """The source checkout (pyproject.toml beside the package) equals a bare relocated copy,
    i.e. what an installed wheel looks like.  Fails while the sibling pyproject.toml is hashed."""
    in_repo = program_module._compiler_implementation_digest()
    assert (ROOT / "pyproject.toml").exists()  # the ambient file really is there in the source tree
    copy = _copy_package_py(tmp_path / "site-packages")
    assert _digest_as_if_located_at(monkeypatch, copy) == in_repo


def test_source_manifest_is_package_python_files_only():
    package = Path(program_module.__file__).resolve().parent
    paths = program_module._compiler_source_paths()
    assert paths and all(p.suffix == ".py" and package in p.parents for p in paths)
    assert [p.relative_to(package).as_posix() for p in paths] == sorted(
        p.relative_to(package).as_posix() for p in paths
    )


def test_package_data_is_present_in_the_package_directory():
    schema = Path(smartchem.__file__).resolve().parent / "evidence" / "manifest.schema.json"
    assert schema.is_file()
    assert re.search(r'"smartchem\.evidence"\s*=\s*\[[^\]]*manifest\.schema\.json', PYPROJECT)


@pytest.mark.parametrize("pruned", ["tests", "experiments"])
def test_sdist_manifest_prunes_unrunnable_trees(pruned):
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert re.search(rf"^prune {pruned}\s*$", manifest, re.M)
