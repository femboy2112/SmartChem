"""``smartchem-verify-probes`` — the thin CLI over the probe-evidence auditor.

Usage::

    python -m smartchem.evidence <manifest.json | dir/>
    smartchem-verify-probes <manifest.json | dir/>
    smartchem-verify-probes --example > my-probes.json   # emit a certifying template

The ``verify-probes`` word is an accepted **optional** leading alias, kept so the older
``smartchem-verify-probes verify-probes <path>`` form still works; it is no longer required,
so the console-script name no longer stutters.

Exit codes are the contract for a CI gate:

* ``0`` — every audited manifest CERTIFIED (or ``--example`` printed its template).
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


def _emit_example() -> int:
    """Print a known-good, certifying template manifest to stdout (``--example``)."""
    # Lazy imports keep the common verify path from paying for the template machinery.
    from .example import example_manifest
    from .manifest_io import manifest_to_mapping

    print(
        json.dumps(
            manifest_to_mapping(example_manifest()),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    import sys

    raw = list(sys.argv[1:] if argv is None else argv)
    # Back-compat: ``verify-probes`` was a REQUIRED subcommand, so the console script read
    # ``smartchem-verify-probes verify-probes <path>`` -- the double word this collapse removes.
    # It is now an OPTIONAL leading alias: strip at most one, so both the bare and the
    # legacy two-word forms parse identically.
    if raw and raw[0] == "verify-probes":
        raw = raw[1:]
    parser = argparse.ArgumentParser(
        prog="smartchem-verify-probes",
        description=(
            "Audit the epistemic contract of a probe suite (teeth, provenance "
            "independence, source locks, scope, tier boundary). Certifies HYGIENE, "
            "not physics."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="path to a manifest .json file or a directory of them",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the certificate(s) as canonical JSON instead of text",
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="print a known-good, certifying template manifest to stdout and exit",
    )
    args = parser.parse_args(raw)
    if args.example:
        if args.path is not None:
            parser.error("--example takes no path argument")
        return _emit_example()
    if args.path is None:
        parser.error("a manifest path (a .json file or a directory) is required")
    return _verify_probes(args.path, as_json=args.json)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
