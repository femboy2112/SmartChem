"""OPERATION XXV-2 (#166): verify the vendored database bytes and the INSTALLED phreeqpython database bytes against the
committed ``expected_hashes.json``.

    python -m experiments.sandbox_foundation.science.verify_hashes [--root DIR] [--vendored-only] [--report OUT.json]

Exit 0 iff every pinned file exists and hashes to its pin (and, unless --vendored-only, the installed phreeqpython
distribution has the pinned version and database bytes).  Exit 1 on any mismatch or missing file; exit 2 on unusable
input.  phreeqpython is located with importlib.util.find_spec, never imported here.  Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = HERE / "expected_hashes.json"
REPO = HERE.parents[2]


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _check(path: Path, pin: str) -> dict:
    if not path.is_file():
        return {"path": str(path), "expected": pin, "actual": None, "ok": False, "problem": "MISSING"}
    got = sha256_file(path)
    return {"path": str(path), "expected": pin, "actual": got, "ok": got == pin,
            "problem": None if got == pin else "SHA256_MISMATCH"}


def verify(expected: dict, root: Path, *, installed: bool = True) -> dict:
    rows = [dict(_check(root / rel, pin), pinned_as=rel) for rel, pin in sorted(expected["vendored"].items())]
    inst = {"checked": installed}
    if installed:
        spec_ = expected["installed_phreeqpython"]
        found = importlib.util.find_spec(spec_["distribution"])
        try:
            version = importlib.metadata.version(spec_["distribution"])
        except importlib.metadata.PackageNotFoundError:
            version = None
        inst.update(version=version, version_ok=version == spec_["version"])
        if found is None or not found.submodule_search_locations:
            inst["problem"] = "NOT_INSTALLED"
            rows.append({"path": spec_["distribution"], "expected": spec_["version"], "actual": None, "ok": False,
                         "problem": "NOT_INSTALLED", "pinned_as": "installed_phreeqpython"})
        else:
            pkg = Path(list(found.submodule_search_locations)[0])
            inst["package_dir"] = str(pkg)
            for rel, pin in sorted(spec_["files"].items()):
                rows.append(dict(_check(pkg / rel, pin), pinned_as=f"installed:{rel}"))
            if not inst["version_ok"]:
                rows.append({"path": spec_["distribution"], "expected": spec_["version"], "actual": version,
                             "ok": False, "problem": "VERSION_MISMATCH", "pinned_as": "installed_phreeqpython"})
    return {"root": str(root), "installed": inst, "files": rows, "ok": all(r["ok"] for r in rows) and bool(rows)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--expected", default=str(EXPECTED))
    ap.add_argument("--root", default=str(REPO))
    ap.add_argument("--vendored-only", action="store_true")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    try:
        expected = json.loads(Path(a.expected).read_text())
        res = verify(expected, Path(a.root).resolve(), installed=not a.vendored_only)
    except (OSError, ValueError, KeyError) as exc:
        print(f"verify_hashes: INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    if a.report:
        Path(a.report).write_text(json.dumps(res, indent=2, sort_keys=True))
    for r in res["files"]:
        print(f"{'OK  ' if r['ok'] else 'FAIL'} {r['pinned_as']}" + ("" if r["ok"] else f"  [{r['problem']}]"))
    if not res["ok"]:
        print("verify_hashes: FAIL -- pinned bytes or the pinned solver distribution do not match", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
