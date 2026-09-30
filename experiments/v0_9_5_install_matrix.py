#!/usr/bin/env python3
"""0.9.5 clean-install matrix: does the BUILT artifact behave byte-for-byte like the source tree?

For every locally available supported CPython (3.10-3.13) it creates a clean venv, installs
the wheel (and the sdist), and runs a fixed command set from a cwd OUTSIDE the repo with no
PYTHONPATH, asserting the imported ``smartchem`` lives in that venv's site-packages and that
no repo path is on ``sys.path``.  Every stdout / stderr / exit code is compared byte-for-byte
with the SOURCE tree (``--source-python -m smartchem ...`` with ``PYTHONPATH=--source-tree``).
The implementation digest (S12) is one of the compared commands, so a source-vs-installed
digest disagreement fails the matrix.

    python experiments/v0_9_5_install_matrix.py --wheel W.whl [--sdist S.tar.gz] \\
        --source-tree /path/to/worktree --out OUTDIR [--work SCRATCHDIR]

Writes ``OUTDIR/install_matrix.json`` + ``install_matrix.md`` (+ ``raw/`` outputs).  Exit 0 iff
every environment agrees on every command.  Interpreters that are not available are DECLARED
in the results; an untested interpreter is never claimed.  Needs ``uv`` and network access to
PyPI (numpy/scipy are resolved fresh: the matrix is a clean-install test, not a pinned one).

    python experiments/v0_9_5_install_matrix.py --self-test --wheel W.whl --source-tree T [--work D]

``--self-test`` is the matrix's own mutation gate (barrier section 12, the three packaging mutants): a
checker that cannot see a broken install is decoration.  It installs the wheel into ONE scratch venv
(the first available supported interpreter), confirms the unmutated install agrees with the source on
the probed commands (else the gate is vacuous and fails), then injects each defect into the INSTALLED
copy and requires the matrix's own comparison to catch it: (1) ``smartchem/evidence/manifest.schema.json``
deleted -> the package-data command must differ; (2) the installed ``cli.py`` patched so ``--version``
prints another string -> installed must differ from source; (3) a sibling ``pyproject.toml`` dropped next
to the installed package -> the REAL implementation digest must NOT move (S12), while a mutant copy of
``_compiler_implementation_digest`` that folds that ambient file in MUST be seen to move.  Each defect is
undone before the next.  Exit 0 iff all three are detected; 1 if any is missed; 2 if the self-test
could not run (no interpreter / the install failed) -- never a claimed pass it did not earn.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SUPPORTED = ("3.10", "3.11", "3.12", "3.13")
UV = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
REPO_ROOTS = {Path(__file__).resolve().parent.parent, Path("/home/leah/SmartChem")}

SCHEMA_CMD = (
    "import json,smartchem.service as s; print(json.dumps(s.response_schema(), sort_keys=True))"
)
DATA_CMD = (
    "import hashlib, importlib.resources as r; "
    "p = r.files('smartchem.evidence') / 'manifest.schema.json'; "
    "b = p.read_bytes(); print(p.is_file(), len(b), hashlib.sha256(b).hexdigest())"
)
DIGEST_CMD = "import smartchem.program as p; print(p._compiler_implementation_digest())"
IMPORT_CMD = "import smartchem; print(smartchem.__version__)"
# NOT byte-compared (it differs by construction); asserted per environment instead.
LOCATION_CMD = "import sys, smartchem; print(smartchem.__file__); print(*sys.path, sep='\\n')"

# name -> (kind, args).  kind "cli": `smartchem <args>` installed / `python -m smartchem <args>`
# source.  kind "py": `python <args>`.  kind "verify": `smartchem-verify-probes <args>` installed /
# `python -m smartchem.evidence <args>` source.
COMMANDS: list[tuple[str, str, list[str]]] = [
    ("import", "py", ["-c", IMPORT_CMD]),
    ("version_script", "cli", ["--version"]),
    ("version_dash_m_cli", "py", ["-m", "smartchem.cli", "--version"]),
    ("plan_formula", "cli", ["plan", "CuSO4·5H2O"]),
    ("plan_smiles", "cli", ["plan", "--smiles", "CC(=O)OC"]),
    ("recompile_human", "cli", ["recompile", "smiles:CC(=O)OC", "--max-depth", "2"]),
    ("recompile_json", "cli", ["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--json"]),
    ("recompile_refusal_json", "cli", ["recompile", "not-a-real-name-zzz", "--json"]),
    ("decompile_json", "cli", ["decompile", "C8H9NO2", "--json"]),
    ("response_schema", "py", ["-c", SCHEMA_CMD]),
    ("package_data", "py", ["-c", DATA_CMD]),
    ("implementation_digest", "py", ["-c", DIGEST_CMD]),
    ("verify_probes_help", "verify", ["--help"]),
]
# Hard expectations independent of the source comparison (a wrong-but-equal answer still fails).
EXPECTED_RC = {"recompile_refusal_json": 2, "version_dash_m_cli": 0}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _hermetic_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
    }
    env.update(extra or {})
    return env


def _run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int = 900) -> dict[str, object]:
    done = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    return {"rc": done.returncode, "stdout": done.stdout, "stderr": done.stderr}


def find_pythons() -> tuple[dict[str, str], list[str]]:
    found: dict[str, str] = {}
    for ver in SUPPORTED:
        cands: list[str] = []
        done = subprocess.run([UV, "python", "find", ver], capture_output=True, text=True)
        if done.returncode == 0 and done.stdout.strip():
            cands.append(done.stdout.strip())
        cands.append(shutil.which(f"python{ver}") or "")
        for cand in cands:
            if cand and Path(cand).exists():
                probe = subprocess.run(
                    [cand, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                    capture_output=True, text=True,
                )
                if probe.returncode == 0 and probe.stdout.strip() == ver:
                    found[ver] = cand
                    break
    return found, [v for v in SUPPORTED if v not in found]


def make_env(python: str, root: Path, artifact: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    subprocess.run([UV, "venv", "--python", python, str(root)], check=True, capture_output=True)
    vpy = root / "bin" / "python"
    subprocess.run(
        [UV, "pip", "install", "--python", str(vpy), str(artifact)],
        check=True, capture_output=True,
    )
    return vpy


def build_argv(kind: str, args: list[str], *, python: Path | str, venv_bin: Path | None) -> list[str]:
    if kind == "py":
        return [str(python), *args]
    if kind == "cli":
        return [str(venv_bin / "smartchem"), *args] if venv_bin else [str(python), "-m", "smartchem", *args]
    if kind == "verify":
        if venv_bin:
            return [str(venv_bin / "smartchem-verify-probes"), *args]
        return [str(python), "-m", "smartchem.evidence", *args]
    raise ValueError(kind)


def run_set(python: Path | str, venv_bin: Path | None, cwd: Path, env: dict[str, str]) -> dict[str, dict]:
    return {
        name: _run(build_argv(kind, args, python=python, venv_bin=venv_bin), cwd, env)
        for name, kind, args in COMMANDS
    }


def check_location(python: Path, cwd: Path, env: dict[str, str], site_root: Path) -> str | None:
    """Return a failure string, or None.  The installed package must come from the venv."""
    out = _run([str(python), "-c", LOCATION_CMD], cwd, env)
    if out["rc"] != 0:
        return f"location probe failed rc={out['rc']}"
    lines = out["stdout"].decode().splitlines()
    # "" on sys.path means the CHILD's cwd (the neutral dir), not this process's cwd.
    where, paths = Path(lines[0]).resolve(), [(cwd / p).resolve() for p in lines[1:]]
    if site_root.resolve() not in where.parents:
        return f"smartchem imported from {where}, not from {site_root}"
    bad = [str(p) for p in paths if p in REPO_ROOTS]
    if bad:
        return f"repo root on sys.path: {bad}"
    return None


# -- --self-test: the three packaging mutants (barrier section 12) ---------------------------------------------------

#: The commands the self-test probes -- a subset of COMMANDS, compared exactly as the matrix compares them.
SELF_TEST_COMMANDS = ("package_data", "version_script", "implementation_digest")
#: The version print the CLI mutant rewrites (anchored: it must occur exactly once in the installed cli.py).
CLI_VERSION_ANCHOR = 'print(f"smartchem {__version__}")'
#: The pre-S12 defect, re-created as a MUTANT COPY of the installed ``_compiler_implementation_digest``: an ambient
#: ``<package parent>/pyproject.toml`` folded into the digest.  Anchored on the version fold (exactly once), run
#: against the installed module's own globals -- the installed file itself is never edited for this one.
MUTANT_DIGEST_CMD = (
    "import inspect, textwrap, smartchem.program as p\n"
    "src = textwrap.dedent(inspect.getsource(p._compiler_implementation_digest))\n"
    "anchor = 'digest.update(b\"\\\\0version\\\\0\")'\n"
    "assert src.count(anchor) == 1, 'mutant anchor drifted'\n"
    "src = src.replace(anchor, 'ambient = root.parent / \"pyproject.toml\"\\n    if ambient.is_file():\\n'\n"
    "                  '        digest.update(ambient.read_bytes())\\n    ' + anchor)\n"
    "g = dict(vars(p)); exec(src, g); print(g['_compiler_implementation_digest']())\n"
)


def _probe(names: tuple[str, ...], python: Path | str, venv_bin: Path | None, cwd: Path,
           env: dict[str, str]) -> dict[str, dict]:
    table = {name: (kind, args) for name, kind, args in COMMANDS}
    return {n: _run(build_argv(*table[n], python=python, venv_bin=venv_bin), cwd, env) for n in names}


def _differs(got: dict, want: dict) -> list[str]:
    """The matrix's own comparison: which of rc / stdout / stderr differ from the source reference."""
    return [k for k in ("rc", "stdout", "stderr") if got[k] != want[k]]


def _drop_pycache(module_file: Path) -> None:
    # a stale .pyc must never answer for an edited (or restored) source file -- remove this module's cached bytecode
    for pyc in (module_file.parent / "__pycache__").glob(f"{module_file.stem}.*.pyc"):
        pyc.unlink()


def self_test(args: argparse.Namespace) -> int:
    work = (args.work or Path(tempfile.mkdtemp(prefix="smartchem-matrix-selftest-"))).resolve()
    work.mkdir(parents=True, exist_ok=True)
    neutral = work / "cwd"
    neutral.mkdir(exist_ok=True)
    pythons, unavailable = find_pythons()
    if not pythons:
        print(f"SELF-TEST COULD NOT RUN: no supported interpreter available ({', '.join(unavailable)})")
        return 2
    ver, python = next(iter(pythons.items()))
    root = work / f"selftest-py{ver}"
    try:
        vpy = make_env(python, root, args.wheel)
    except subprocess.CalledProcessError as exc:
        print(f"SELF-TEST COULD NOT RUN: wheel install failed on {ver}:\n{(exc.stderr or b'').decode()[-2000:]}")
        return 2
    env, vbin = _hermetic_env(), root / "bin"
    loc = _run([str(vpy), "-c", "import smartchem; print(smartchem.__file__)"], neutral, env)
    pkg = Path(loc["stdout"].decode().strip()).resolve().parent
    if root.resolve() not in pkg.parents:
        print(f"SELF-TEST COULD NOT RUN: smartchem imported from {pkg}, not the scratch venv {root}")
        return 2

    src_env = _hermetic_env({"PYTHONPATH": str(args.source_tree.resolve())})
    reference = _probe(SELF_TEST_COMMANDS, args.source_python, None, neutral, src_env)
    rows: list[tuple[str, bool, str]] = []

    # sanity: the UNMUTATED install agrees with the source, or every "detection" below would be vacuous
    baseline = _probe(SELF_TEST_COMMANDS, vpy, vbin, neutral, env)
    drift = {n: _differs(baseline[n], reference[n]) for n in SELF_TEST_COMMANDS if _differs(baseline[n], reference[n])}
    rows.append(("baseline: the unmutated install agrees with the source", not drift, f"differs: {drift}" if drift
                 else "rc/stdout/stderr identical on every probed command"))

    # (1) runtime package data missing from the installed copy -> the package-data check must FAIL
    data = pkg / "evidence" / "manifest.schema.json"
    saved = data.read_bytes()
    data.unlink()
    try:
        got = _probe(("package_data",), vpy, vbin, neutral, env)["package_data"]
    finally:
        data.write_bytes(saved)
    diff = _differs(got, reference["package_data"])
    rows.append(("(1) manifest.schema.json deleted -> package-data check FAILED", bool(diff),
                 f"differs in {diff} (rc {got['rc']})"))

    # (2) the installed CLI diverges from the source CLI -> installed != source must be reported
    cli = pkg / "cli.py"
    original = cli.read_text(encoding="utf-8")
    if original.count(CLI_VERSION_ANCHOR) != 1:
        print(f"SELF-TEST COULD NOT RUN: CLI anchor {CLI_VERSION_ANCHOR!r} found {original.count(CLI_VERSION_ANCHOR)}x")
        return 2
    cli.write_text(original.replace(CLI_VERSION_ANCHOR, 'print(f"smartchem {__version__}+self-test-mutant")'),
                   encoding="utf-8")
    _drop_pycache(cli)
    try:
        got = _probe(("version_script",), vpy, vbin, neutral, env)["version_script"]
    finally:
        cli.write_text(original, encoding="utf-8")
        _drop_pycache(cli)
    diff = _differs(got, reference["version_script"])
    rows.append(("(2) installed cli.py --version patched -> installed != source", bool(diff),
                 f"differs in {diff}: {got['stdout'].decode().strip()!r}"))

    # (3) S12: an ambient sibling pyproject.toml must not move the REAL digest -- and a digest that reads it is caught
    ambient = pkg.parent / "pyproject.toml"
    if ambient.exists():
        print(f"SELF-TEST COULD NOT RUN: {ambient} already exists (not a clean scratch venv)")
        return 2

    def digests() -> tuple[str, str]:
        real = _probe(("implementation_digest",), vpy, vbin, neutral, env)["implementation_digest"]
        mut = _run([str(vpy), "-c", MUTANT_DIGEST_CMD], neutral, env)
        if real["rc"] != 0 or mut["rc"] != 0:
            raise RuntimeError(f"digest probe failed: real rc={real['rc']} mutant rc={mut['rc']} "
                               f"{(real['stderr'] + mut['stderr']).decode()[-800:]}")
        return real["stdout"].decode().strip(), mut["stdout"].decode().strip()

    real_before, mut_before = digests()
    ambient.write_text('[project]\nname = "not-smartchem"\nversion = "0.0.0"\n', encoding="utf-8")
    try:
        real_after, mut_after = digests()
    finally:
        ambient.unlink()
    source_digest = reference["implementation_digest"]["stdout"].decode().strip()
    s12_holds = real_before == real_after == source_digest
    rows.append(("(3a) S12: sibling pyproject.toml does NOT move the real implementation digest", s12_holds,
                 f"{real_before[:16]} -> {real_after[:16]} (source {source_digest[:16]})"))
    rows.append(("(3b) a digest copy reading the ambient pyproject.toml is DETECTED", mut_before != mut_after,
                 f"{mut_before[:16]} -> {mut_after[:16]}"))

    print(f"0.9.5 install matrix --self-test (py{ver}: {python}; wheel {args.wheel.name})")
    for label, ok, detail in rows:
        print(f"  [{'OK' if ok else 'MISSED'}] {label}\n        {detail}")
    passed = all(ok for _l, ok, _d in rows)
    print(f"\nSELF-TEST {'PASS: all three packaging mutants detected' if passed else 'FAIL'} "
          f"({sum(ok for _l, ok, _d in rows)}/{len(rows)} checks)")
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--wheel", type=Path, required=True)
    ap.add_argument("--sdist", type=Path)
    ap.add_argument("--source-tree", type=Path, required=True)
    ap.add_argument("--source-python", default="/home/leah/SmartChem/.venv/bin/python")
    ap.add_argument("--out", type=Path, help="output directory (required unless --self-test)")
    ap.add_argument("--work", type=Path, help="scratch dir for venvs (default: a fresh temp dir)")
    ap.add_argument("--self-test", action="store_true",
                    help="run the three packaging mutants against ONE scratch install instead of the matrix")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test(args)
    if args.out is None:
        ap.error("the following arguments are required: --out")
    out = args.out.resolve()
    (out / "raw").mkdir(parents=True, exist_ok=True)
    work = (args.work or Path(tempfile.mkdtemp(prefix="smartchem-matrix-"))).resolve()
    work.mkdir(parents=True, exist_ok=True)
    neutral = work / "cwd"
    neutral.mkdir(exist_ok=True)

    pythons, unavailable = find_pythons()

    # Reference: the SOURCE tree.  PYTHONPATH is the worktree; confirm it really is what loads.
    src_env = _hermetic_env({"PYTHONPATH": str(args.source_tree.resolve())})
    loc = _run([args.source_python, "-c", "import smartchem; print(smartchem.__file__)"], neutral, src_env)
    src_file = Path(loc["stdout"].decode().strip()).resolve()
    if args.source_tree.resolve() not in src_file.parents:
        raise SystemExit(f"source reference loaded {src_file}, not the tree {args.source_tree}")
    reference = run_set(args.source_python, None, neutral, src_env)

    results: dict[str, object] = {
        "artifacts": {
            p.name: _sha(p.read_bytes()) for p in (args.wheel, args.sdist) if p is not None
        },
        "source_tree": str(args.source_tree.resolve()),
        "interpreters_tested": pythons,
        "interpreters_unavailable": unavailable,
        "commands": [name for name, _, _ in COMMANDS],
        "reference": {
            n: {"rc": r["rc"], "stdout_sha256": _sha(r["stdout"]), "stderr_sha256": _sha(r["stderr"])}
            for n, r in reference.items()
        },
        "environments": {},
    }
    for name, r in reference.items():
        raw = out / "raw" / "source"
        raw.mkdir(exist_ok=True)
        (raw / f"{name}.out").write_bytes(r["stdout"])
        (raw / f"{name}.err").write_bytes(r["stderr"])
        (raw / f"{name}.rc").write_text(f"{r['rc']}\n")
    failures: list[str] = []
    for name, want in EXPECTED_RC.items():
        if reference[name]["rc"] != want:
            failures.append(f"source reference {name}: rc {reference[name]['rc']} != expected {want}")

    artifacts = [("wheel", args.wheel)] + ([("sdist", args.sdist)] if args.sdist else [])
    for ver, python in pythons.items():
        for label, artifact in artifacts:
            env_name = f"py{ver}-{label}"
            entry: dict[str, object] = {"python": python, "artifact": artifact.name}
            results["environments"][env_name] = entry
            try:
                root = work / env_name
                vpy = make_env(python, root, artifact)
            except subprocess.CalledProcessError as exc:
                entry["install_error"] = (exc.stderr or b"").decode()[-2000:]
                failures.append(f"{env_name}: install failed")
                continue
            env = _hermetic_env()
            problem = check_location(vpy, neutral, env, root)
            entry["location_check"] = problem or "OK: imported from venv site-packages, no repo on sys.path"
            if problem:
                failures.append(f"{env_name}: {problem}")
            got = run_set(vpy, root / "bin", neutral, env)
            cmds: dict[str, dict] = {}
            for cmd, r in got.items():
                same = {k: r[k] == reference[cmd][k] for k in ("rc", "stdout", "stderr")}
                ok = all(same.values())
                cmds[cmd] = {"rc": r["rc"], "match_source": ok, "differs_in": [k for k, v in same.items() if not v]}
                raw = out / "raw" / env_name
                raw.mkdir(exist_ok=True)
                (raw / f"{cmd}.out").write_bytes(r["stdout"])
                (raw / f"{cmd}.err").write_bytes(r["stderr"])
                (raw / f"{cmd}.rc").write_text(f"{r['rc']}\n")
                if not ok:
                    failures.append(f"{env_name}: {cmd} differs from source in {cmds[cmd]['differs_in']}")
            entry["commands"] = cmds
    results["failures"] = failures
    results["verdict"] = "ALL ENVIRONMENTS AGREE" if not failures else "DISAGREEMENT"
    digest_row = reference["implementation_digest"]["stdout"].decode().strip()
    results["implementation_digest_source"] = digest_row
    (out / "install_matrix.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")

    envs = list(results["environments"])
    lines = [
        "# 0.9.5 install matrix",
        "",
        f"Verdict: **{results['verdict']}**",
        f"Interpreters tested: {', '.join(f'{v} ({p})' for v, p in pythons.items()) or 'none'}",
        f"Interpreters UNAVAILABLE (not tested, not claimed): {', '.join(unavailable) or 'none'}",
        f"Implementation digest (source): `{digest_row}`",
        "",
        "| command | " + " | ".join(envs) + " |",
        "|---|" + "---|" * len(envs),
    ]
    for cmd, _, _ in COMMANDS:
        cells = []
        for e in envs:
            c = results["environments"][e].get("commands", {}).get(cmd)
            cells.append("n/a" if c is None else (f"rc={c['rc']} identical" if c["match_source"] else f"rc={c['rc']} DIFF"))
        lines.append(f"| {cmd} | " + " | ".join(cells) + " |")
    lines += ["", *[f"- FAIL: {f}" for f in failures], ""]
    (out / "install_matrix.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
