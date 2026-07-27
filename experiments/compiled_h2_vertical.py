"""
Run the first approved source-to-certificate chemistry program.

    OMP_NUM_THREADS=1 .venv/bin/python experiments/compiled_h2_vertical.py \
        --journal /tmp/smartchem-h2-run.json

The target is deliberately narrow: ``2 H -> H2`` at the existing public
``CCSD(T)/cc-pVTZ`` fixed-geometry protocol.  This exercises the compiler seam rather than
opening new chemistry coverage:

    source -> resolved program -> Physical IR -> request -> candidate plan
           -> explicit approval -> tracked execution -> result -> certificate

The reported scalar is an endpoint ``delta-E`` in the closed, isolated-species adapter.  It
is not Gibbs free energy, a spontaneity verdict, a rate, a mechanism, or a new validation of
the underlying oracle.  The oracle's finite reported scale comes from its existing selected
fixed-neutral-diatomic protocol; this one run does not recalibrate it.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smartchem.category import Config, Molecule, Reaction  # noqa: E402
from smartchem.contracts import InferenceKind, RunStatus   # noqa: E402
from smartchem.ledger import (                             # noqa: E402
    BindingSchema,
    Spec,
    reaction_slot,
    shepherd,
)
from smartchem.oracle.pyscf_oracle import (                # noqa: E402
    PYSCF_AVAILABLE,
    PySCFOracle,
)
from smartchem.program import (                            # noqa: E402
    SourceProgram,
    approve,
    compile_session_reaction_energy,
    execute,
    record_approval,
)

def build_session():
    """Derive the reaction menu, then let the scientist select it as a typed Reaction."""
    hydrogen = Molecule.atom("H")
    molecule = Molecule.diatomic("H", "H")
    slot = replace(
        reaction_slot(
            "reaction",
            "two neutral hydrogen atoms form one neutral H2 molecule",
            (hydrogen, molecule),
        ),
        schema=BindingSchema((Reaction,)),
    )
    spec = Spec("compiled-h2", (slot,))

    def scientist(current, holes):
        option = holes[0].derived_options[0]
        return current.bind_typed(
            "reaction",
            option.value,
            source_text=option.display,
            inference=InferenceKind.DERIVED_COMPLETE,
            derivation=option.derivation,
        )

    session = shepherd(spec, scientist)
    if not session:
        raise RuntimeError(session.explain())
    return session


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--journal",
        type=Path,
        default=Path("experiments/compiled_h2_run.json"),
        help="atomically updated in-progress/final RunRecord (JSON files are git-ignored)",
    )
    args = parser.parse_args()

    if not PYSCF_AVAILABLE:
        print("REFUSED: PySCF is unavailable; no fallback changes the approved model.")
        return 2

    oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False)
    source = SourceProgram(
        text=(
            "Compute the closed-reaction 0 K endpoint delta-E for 2 H -> H2 with the "
            "existing fixed-geometry CCSD(T)/cc-pVTZ protocol. Preserve the scalar, "
            "reported uncertainty scale, diagnostics, run record, and certificate."
        ),
        spans=("2 H -> H2", "endpoint delta-E", "CCSD(T)/cc-pVTZ"),
        scientist="user directive 2026-07-27",
    )
    session = build_session()
    candidate = compile_session_reaction_energy(
        source,
        session,
        "reaction",
        oracle,
    )
    if candidate.blockers:
        print("REFUSED AT PLANNING:")
        for blocker in candidate.blockers:
            print("  " + blocker)
        return 3

    approval = record_approval(
        candidate,
        principal="user directive 2026-07-27",
        scope=(
            "execute this exact fixed-output candidate; no fidelity, coverage, diagnostic, "
            "or retention reduction is authorized"
        ),
    )
    approved = approve(candidate, approval)

    print("PLAN")
    print(f"  source digest      {source.digest}")
    print(f"  request digest     {candidate.request.digest}")
    print(f"  shepherd digest    {candidate.request.resolved.shepherd_session_digest}")
    print(f"  plan digest        {candidate.digest}")
    print(f"  approval digest    {approval.digest}")
    print(f"  calculation digest {candidate.calculation.digest}")
    print(f"  journal             {args.journal}")
    print("  state               RUNNING (journal is replaced atomically after every transition)")

    report = execute(approved, oracle, journal_path=args.journal)
    print("\nRESULT")
    print(f"  state               {report.record.status.value}")
    print(f"  run id              {report.record.run_id}")
    print(f"  outputs             {list(report.record.output_inventory)}")
    print(f"  checkpoints         {len(report.record.checkpoints)}")
    print(f"  cache               {list(report.record.cache_state)}")
    if report.result is not None:
        value = report.result.values[0]
        print(
            f"  endpoint delta-E    {value.value:+.12f} +/- "
            f"{value.uncertainty:.12f} {value.unit}"
        )
        print(f"  method              {value.method}")
    if report.certificate is not None:
        print(f"  certificate digest  {report.certificate.digest}")
        print(f"  claim scope         {report.certificate.claim_scope.kind.value}: "
              f"{report.certificate.claim_scope.referent}")
        print(f"  evidence status     {report.certificate.evidence_status.value}")
        print("  excludes")
        for casualty in report.certificate.casualties:
            print("    - " + casualty)
    if report.record.failures:
        print("  failures")
        for failure in report.record.failures:
            print("    - " + failure)

    if args.journal.exists():
        persisted = json.loads(args.journal.read_text())
        if persisted.get("status") != report.record.status.value:
            print("FAILED: durable journal and returned RunRecord disagree")
            return 4
    return 0 if report.record.status is RunStatus.COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
