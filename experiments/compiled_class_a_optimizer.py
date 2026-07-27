"""Run the first plan-visible Class-A no-loss transform.

The declared separable endpoint model makes a shared spectator multiset cancel exactly:

    E(S + products) - E(S + reactants) = E(products) - E(reactants).

The harness uses a deterministic structural oracle that deliberately refuses iron.  Iron is
a regenerated spectator and must therefore be eliminated, verified, and recorded before
domain admission or any oracle call.  The transformed result is compared with the exact
spectator-free reaction.  This measures structural call counts, not wall-clock speedup, and
does not license cancellation in interacting, solvated, field-coupled, or open models.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smartchem import (
    Config,
    Molecule,
    Reaction,
    approve,
    compile_reaction_energy,
    execute,
    record_approval,
)
from smartchem.diagnosis import diagnose
from smartchem.domain import Domain
from smartchem.oracle.base import BaseOracle, Estimate


class ClassAProbeOracle(BaseOracle):
    """A deterministic calculation identity with explicit call telemetry."""

    name = "SmartChem Class-A structural probe oracle"
    nominal_accuracy_ev = 0.0

    def __init__(self) -> None:
        self.calls: list[Molecule] = []

    @property
    def domain(self) -> Domain:
        return Domain(
            label=self.name,
            min_atoms=1,
            max_atoms=2,
            elements=frozenset({"H"}),
            charges=frozenset({0}),
            states=frozenset({""}),
        )

    def calculation_spec(self) -> dict[str, object]:
        return {
            "algorithm": "deterministic Class-A structural call-count probe",
            "energies_ev": (("H", 0.0), ("H2", -4.5)),
            "refused_spectator": "Fe",
            "version": 1,
        }

    def energy(self, molecule: Molecule) -> Estimate | None:
        self.calls.append(molecule)
        if molecule == Molecule.atom("Fe"):
            return None
        if molecule == Molecule.atom("H"):
            value = 0.0
        elif molecule == Molecule.diatomic("H", "H"):
            value = -4.5
        else:
            return None
        return Estimate(
            value_ev=value,
            uncertainty_ev=0.1,
            method=self.name,
            notes="deterministic structural optimizer probe; not chemistry calibration",
        )


def reactions() -> tuple[Reaction, Reaction]:
    hydrogen = Molecule.atom("H")
    hydrogen_molecule = Molecule.diatomic("H", "H")
    iron = Molecule.atom("Fe")
    reference = Reaction(
        Config.of(hydrogen, hydrogen),
        Config.of(hydrogen_molecule),
    )
    spectator = Reaction(
        Config.of(hydrogen, hydrogen, iron),
        Config.of(hydrogen_molecule, iron),
    )
    return spectator, reference


def _run_one(reaction: Reaction, journal: Path, scope: str):
    oracle = ClassAProbeOracle()
    plan = compile_reaction_energy(
        (
            "Compute the complete closed separable endpoint energy. Apply only a "
            "verified identity-preserving spectator cancellation; retain the exact "
            "reaction-energy output contract and every non-spectator checkpoint."
        ),
        reaction,
        oracle,
    )
    approved = approve(
        plan,
        record_approval(
            plan,
            "Leah",
            scope,
        ),
    )
    return plan, oracle, execute(approved, oracle, journal_path=journal)


def run(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    spectator, reference = reactions()
    transformed = _run_one(
        spectator,
        directory / "transformed.json",
        (
            "run the verified Class-A reaction-residue transform with the complete "
            "reaction-energy output unchanged"
        ),
    )
    baseline = _run_one(
        reference,
        directory / "reference.json",
        "run the exact spectator-free reference under the same output contract",
    )
    return transformed, baseline


def summary(results: object) -> dict[str, object]:
    (plan, oracle, report), (reference_plan, reference_oracle, reference) = results
    estimate = report.result.values[0]
    expected = reference.result.values[0]
    transform = plan.transforms[0]
    raw_diagnosis = diagnose(plan.request.resolved.reaction, (ClassAProbeOracle(),))
    return {
        "status": report.record.status.value,
        "reference_status": reference.record.status.value,
        "transform": transform.name,
        "exactness_class": transform.exactness_class,
        "raw_distinct_species": len(
            set(
                plan.request.resolved.reaction.dom.species
                + plan.request.resolved.reaction.cod.species
            )
        ),
        "residual_distinct_species": len(transform.workset),
        "actual_oracle_calls": [repr(item) for item in oracle.calls],
        "reference_oracle_calls": [repr(item) for item in reference_oracle.calls],
        "spectator_was_called": Molecule.atom("Fe") in oracle.calls,
        "raw_reaction_domain_blocked": bool(raw_diagnosis.obstructions),
        "raw_reaction_domain_obstructions": tuple(
            repr(item) for item in raw_diagnosis.obstructions
        ),
        "value_ev": estimate.value,
        "reference_value_ev": expected.value,
        "uncertainty_ev": estimate.uncertainty,
        "reference_uncertainty_ev": expected.uncertainty,
        "value_and_uncertainty_identical": (
            estimate.value == expected.value
            and estimate.uncertainty == expected.uncertainty
            and estimate.systematic_terms == expected.systematic_terms
        ),
        "output_contract_digest": plan.request.output_contract.digest,
        "reference_output_contract_digest": reference_plan.request.output_contract.digest,
        "transform_digest": transform.digest,
        "plan_digest": plan.digest,
        "reference_plan_digest": reference_plan.digest,
        "certificate_digest": report.certificate.digest,
        "reference_certificate_digest": reference.certificate.digest,
        "certificate_bound_transform_inventory": tuple(
            item.name for item in plan.transforms
        ),
        "output_inventory": report.certificate.output_inventory,
        "scope": (
            "Class-A only under the closed separable endpoint-energy model; structural "
            "call count, not timing speedup or a general optimizer"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summary(run(args.journal_dir)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
