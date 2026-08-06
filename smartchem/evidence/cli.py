"""``smartchem verify-probes`` — the thin CLI over the probe-evidence auditor.

Usage (either form)::

    python -m smartchem.evidence verify-probes <manifest.json | dir/>
    smartchem-verify-probes verify-probes <manifest.json | dir/>

Exit codes are the contract for a CI gate:

* ``0`` — every audited manifest CERTIFIED.
* ``1`` — at least one manifest was REFUSED (a working refusal, not an error).
* ``2`` — a manifest could not be loaded (malformed / missing / not JSON).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

__all__ = ["main"]


def _iter_manifest_paths(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(target.glob("*.json"))
    return [target]


def _verify_probes(path: str, as_json: bool) -> int:
    # Lazy imports keep CLI startup cheap and match house style (bench.py).
    from .auditor import audit_manifest
    from .manifest_io import ManifestError, load_manifest

    target = Path(path)
    paths = _iter_manifest_paths(target)
    if not paths:
        print(f"error: {path} contains no *.json manifests", flush=True)
        return 2

    certificates = []
    exit_code = 0
    for manifest_path in paths:
        try:
            manifest = load_manifest(manifest_path)
        except ManifestError as error:
            print(f"error: {error}", flush=True)
            return 2
        certificate = audit_manifest(manifest)
        certificates.append((manifest_path, certificate))
        if not certificate.certified:
            exit_code = 1

    if as_json:
        from ..contracts import canonical_payload

        payload = [
            {"path": str(manifest_path), "certificate": canonical_payload(certificate)}
            for manifest_path, certificate in certificates
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    else:
        for manifest_path, certificate in certificates:
            print(f"# {manifest_path}", flush=True)
            print(certificate.render(), flush=True)
            print(flush=True)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="smartchem-verify-probes",
        description=(
            "Audit the epistemic contract of a probe suite (teeth, provenance "
            "independence, source locks, scope, tier boundary). Certifies HYGIENE, "
            "not physics."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser(
        "verify-probes", help="audit a manifest JSON file or a directory of them"
    )
    verify.add_argument("path", help="path to a manifest .json file or a directory")
    verify.add_argument(
        "--json",
        action="store_true",
        help="emit the certificate(s) as canonical JSON instead of text",
    )
    args = parser.parse_args(argv)
    if args.command == "verify-probes":
        return _verify_probes(args.path, as_json=args.json)
    parser.error(f"unknown command {args.command!r}")  # pragma: no cover
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
