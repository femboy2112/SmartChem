#!/usr/bin/env python3
"""Reproducible release build for SmartChem (0.9.5 S-release).

Builds the wheel and the sdist from a CLEAN ``git archive`` export of one commit (default
HEAD) -- never the working tree, so untracked/ignored cruft (stale ``*.egg-info``, editable
finders, scratch files) cannot leak into an artifact.  ``SOURCE_DATE_EPOCH`` is the commit
time.  The wheel is byte-reproducible straight from setuptools; the sdist is not (setuptools
stamps its GENERATED members -- PKG-INFO, setup.cfg, egg-info, directories -- and the gzip
header with the wall clock and the builder's uname), so the sdist is repacked canonically:
members sorted, mtime = SOURCE_DATE_EPOCH, uid/gid 0, uname/gname "", normalised modes,
gzip header mtime 0 with no embedded name.

Writes to ``--out``: the two artifacts, ``SHA256SUMS`` and ``release_manifest.json`` (file
list + per-file sha256 for both artifacts).  Nothing in the manifest depends on the clock.

    python scripts/build_release.py --out /some/dir/outside/the/repo

Identity caveat (honest): the wheel bytes are stable for a FIXED builder.  The WHEEL file
records ``Generator: setuptools (X)``, and the build requirement is ``setuptools>=77``
(unpinned), so a different setuptools may legitimately change the wheel.  The manifest
records the resolved generator so a mismatch is visible.  Needs ``uv`` on PATH.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    done = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(
            f"build_release: {' '.join(cmd)} failed ({done.returncode})\n{done.stdout}\n{done.stderr}"
        )
    return done.stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_tree(repo: Path, ref: str, dest: Path) -> tuple[str, int]:
    """Extract ``ref`` from the repo's object store into ``dest``; return (commit, commit time)."""
    commit = _run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=repo).strip()
    epoch = int(_run(["git", "log", "-1", "--format=%ct", commit], cwd=repo).strip())
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit], cwd=repo, capture_output=True
    )
    if archive.returncode != 0:
        raise SystemExit(f"build_release: git archive failed: {archive.stderr.decode()}")
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(dest, filter="data")
    return commit, epoch


def repack_sdist_canonically(src: Path, dst: Path, epoch: int) -> None:
    """Rewrite ``src`` (.tar.gz) to ``dst`` with every clock/owner/order degree of freedom fixed."""
    with tarfile.open(src, "r:gz") as tar:
        members = sorted(tar.getmembers(), key=lambda m: m.name)
        payload = {m.name: tar.extractfile(m).read() for m in members if m.isfile()}
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as out:
        for member in members:
            member.mtime = epoch
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            member.pax_headers = {}
            if member.isdir():
                member.mode = 0o755
            elif member.isfile():
                member.mode = 0o755 if member.mode & 0o111 else 0o644
            out.addfile(member, io.BytesIO(payload[member.name]) if member.isfile() else None)
    with open(dst, "wb") as fh:
        # filename="" -> no FNAME field; mtime=0 -> no clock in the gzip header.
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, compresslevel=9, mtime=0) as gz:
            gz.write(raw.getvalue())


def _wheel_files(path: Path) -> list[dict[str, object]]:
    with zipfile.ZipFile(path) as zf:
        return [
            {"path": i.filename, "sha256": _sha256(zf.read(i)), "size": i.file_size}
            for i in sorted(zf.infolist(), key=lambda i: i.filename)
            if not i.is_dir()
        ]


def _wheel_generator(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith(".dist-info/WHEEL"):
                for line in zf.read(name).decode().splitlines():
                    if line.startswith("Generator:"):
                        return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def _sdist_files(path: Path) -> list[dict[str, object]]:
    with tarfile.open(path, "r:gz") as tar:
        return [
            {"path": m.name, "sha256": _sha256(tar.extractfile(m).read()), "size": m.size}
            for m in sorted(tar.getmembers(), key=lambda m: m.name)
            if m.isfile()
        ]


def build(repo: Path, ref: str, out: Path) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    if out.resolve().is_relative_to(repo.resolve()):
        raise SystemExit("build_release: --out must be outside the repository (never commit build outputs)")
    with tempfile.TemporaryDirectory(prefix="smartchem-release-") as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src"
        src.mkdir()
        commit, epoch = export_tree(repo, ref, src)
        env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
        built = tmp_path / "built"
        _run(["uv", "build", "--sdist", "--wheel", "--out-dir", str(built), str(src)], env=env)
        wheels = sorted(built.glob("*.whl"))
        sdists = sorted(built.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise SystemExit(f"build_release: expected 1 wheel + 1 sdist, got {wheels} {sdists}")
        for stale in list(out.glob("*.whl")) + list(out.glob("*.tar.gz")):
            stale.unlink()
        wheel = out / wheels[0].name
        shutil.copyfile(wheels[0], wheel)
        sdist = out / sdists[0].name
        repack_sdist_canonically(sdists[0], sdist, epoch)
    artifacts = {
        wheel.name: _wheel_files(wheel),
        sdist.name: _sdist_files(sdist),
    }
    manifest = {
        "commit": commit,
        "source_date_epoch": epoch,
        "wheel_generator": _wheel_generator(wheel),
        "artifacts": {
            name: {
                "sha256": _sha256((out / name).read_bytes()),
                "size": (out / name).stat().st_size,
                "files": files,
            }
            for name, files in artifacts.items()
        },
    }
    (out / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sums = "".join(f"{manifest['artifacts'][n]['sha256']}  {n}\n" for n in sorted(artifacts))
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True, help="output directory (outside the repo)")
    ap.add_argument("--ref", default="HEAD", help="commit-ish to export and build (default HEAD)")
    ap.add_argument("--repo", type=Path, default=REPO)
    args = ap.parse_args(argv)
    manifest = build(args.repo, args.ref, args.out)
    for name, info in manifest["artifacts"].items():
        print(f"{info['sha256']}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
