"""ERR-EVIDENCE-01: a missing sourced-conditions record is an epistemic UNKNOWN; an internal provider fault is NOT.

The audit (AUDIT_GENERIC_..._2026-09-03 section 10, and section 8.2 of the sibling draft) found that the
condition lookup swallowed a broad ``Exception`` and returned ``ConditionEnvelope.unknown()`` -- laundering an
internal software fault (a bug in signature computation or structure resolution) into the SCIENTIFIC statement
"conditions unknown".  The deeper launderer was ``decompiler_conditions.assembly_conditions`` itself (its own
``except Exception``), which fires BEFORE the audit-named outer ``routes._conditions_for``; fixing only the outer
site would have been vacuous.  This brick removes BOTH blanket catches.

The contract, pinned here on all four controls the audit's probe demands:
  * POSITIVE  -- a genuinely seeded record still resolves to its sourced envelope, unchanged;
  * NULL      -- a legitimate lookup miss (no record / wrong direction / unresolved structure / blocker) is a
                 quiet ``unknown()`` that never aborts route generation;
  * MUTATION  -- an injected internal fault (AssertionError) PROPAGATES; it must NOT become ``unknown()``;
  * END-TO-END-- through the public CLI, that injected fault becomes ERROR_INTERNAL / exit 70 with a concise
                 message and no raw traceback -- never a false "conditions unknown" scientific diagnostic.
"""
import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import main
from smartchem.decompiler_conditions import assembly_conditions
from smartchem.experiment.routes import enumerate_routes, search_routes
from smartchem.identity import stereo_loss
from smartchem.service import EXIT_INTERNAL
from smartchem.smiles import parse_smiles
from smartchem.structure import known_compounds
from smartchem.structure_descent import capped_scissions

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
AMP = parse_smiles("Nc1ccc(O)cc1")
WATER = parse_smiles("O")
ACOH = parse_smiles("CC(=O)O")        # acetic acid, C2H4O2 -- the reagent of the SEEDED anhydride assembly
ANH = parse_smiles("CC(=O)OC(=O)C")   # acetic anhydride, C4H6O3


def _by_name(formula, name):
    return next(s.molecule.canonical() for s in known_compounds(formula) if s.name == name)


AMINOPHENOL = _by_name("C6H7NO", "4-aminophenol")
ANHYDRIDE = _by_name("C4H6O3", "acetic anhydride")


def _anhydride_capped():
    """The capped scission whose reverse is the SEEDED acetic-anhydride acetylation (an ASSEMBLY record).

    Decomposition read: paracetamol + acetic acid -> 4-aminophenol + acetic anhydride.
    """
    edges, complete = capped_scissions(PARA, (ACOH,))
    assert complete
    for e in edges:
        if {p.canonical() for p in e.products} == {AMINOPHENOL, ANHYDRIDE}:
            return e
    raise AssertionError("fixture: no capped scission yielded {4-aminophenol, acetic anhydride}")


def _unseeded_capped():
    """A real capped scission with NO sourced ASSEMBLY record: paracetamol hydrolysis is DECOMPOSITION-only."""
    edges, complete = capped_scissions(PARA, (WATER,))
    assert complete
    return edges[0]


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestExpectedAbsenceContract:
    """The seeded record resolves; every ANTICIPATED miss is a quiet unknown()."""

    def test_a_seeded_assembly_record_still_resolves_to_its_sourced_envelope(self):
        env = assembly_conditions(_anhydride_capped())
        assert env.is_declared                                   # POSITIVE: the known record still resolves
        assert "neat" in env.medium or "aqueous" in env.medium   # the exact seeded medium, unchanged

    def test_a_missing_record_is_a_quiet_unknown_not_a_raise(self):
        # NULL: paracetamol hydrolysis has a DECOMPOSITION record but no ASSEMBLY one -> unknown(), no exception.
        env = assembly_conditions(_unseeded_capped())
        assert not env.is_declared

    def test_a_conditions_blocker_short_circuits_to_unknown(self):
        # NULL (regression): a section-5.3 conditions BLOCKER returns unknown() BEFORE any lookup -- the blocker
        # guard sits ahead of the (now removed) try, so it still works and never touches capped.
        env = assembly_conditions(None, losses=(stereo_loss("x"),))
        assert not env.is_declared

    def test_route_search_attaches_the_seeded_envelope_and_completes(self):
        # NULL + POSITIVE at the search layer: the anhydride step is declared, the acetic-acid step is not, and
        # the whole enumeration returns normally (a miss never aborts route generation).
        routes = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        by_lhs = {s.equation().split(" -> ")[0]: s for r in routes for s in r.steps}
        assert by_lhs["C4H6O3 + C6H7NO"].envelope.is_declared        # seeded assembly
        assert not by_lhs["C2H4O2 + C6H7NO"].envelope.is_declared    # legitimate miss, quiet unknown


class TestInternalFaultPropagates:
    """An injected internal fault must NOT be laundered into unknown() at EITHER layer."""

    def test_inner_assembly_conditions_no_longer_swallows_a_fault(self, monkeypatch):
        # MUTATION at the deep root: a fault inside the signature computation used to be caught by
        # assembly_conditions' own `except Exception` and returned unknown().  It must now propagate.
        def boom(_edge):
            raise AssertionError("injected condition-provider fault")

        monkeypatch.setattr("smartchem.decompiler_conditions._reaction_signature", boom)
        with pytest.raises(AssertionError, match="injected condition-provider fault"):
            assembly_conditions(_anhydride_capped())

    def test_outer_conditions_for_no_longer_swallows_a_fault_during_search(self, monkeypatch):
        # MUTATION at the audit-named outer site: a fault raised by the provider during route enumeration used to
        # be caught by _conditions_for and turned into unknown(); the search then generated routes as if the
        # conditions were merely absent.  It must now propagate out of the search.
        def boom(_capped):
            raise AssertionError("injected condition-provider fault")

        monkeypatch.setattr("smartchem.experiment.routes.assembly_conditions", boom)
        with pytest.raises(AssertionError, match="injected condition-provider fault"):
            search_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=3)


class TestEndToEndExit70:
    """Through the public CLI, an injected provider fault is ERROR_INTERNAL/exit 70, not a false 'unknown'."""

    def test_injected_provider_fault_becomes_exit_70(self, monkeypatch):
        def boom(_capped):
            raise AssertionError("injected condition-provider fault")

        monkeypatch.setattr("smartchem.experiment.routes.assembly_conditions", boom)
        code, out, err = _cli(["recompile", "paracetamol", "--max-depth", "2"])
        assert code == EXIT_INTERNAL == 70
        assert "ERROR_INTERNAL" in err
        assert "AssertionError" in err and "injected condition-provider fault" in err
        # a concise diagnostic, NOT a raw Python traceback dumped at the user, and NOT a scientific "unknown":
        assert "Traceback (most recent call last)" not in err
        assert "Traceback (most recent call last)" not in out

    def test_a_genuine_conditions_miss_is_not_a_false_internal_error(self):
        # The other side of the split: WITHOUT any injection, a recompile whose steps have no sourced conditions
        # completes with its ordinary section-14.4 code (here 4, INCOMPLETE), never a false exit 70.
        code, _, err = _cli(["recompile", "paracetamol", "--max-depth", "2"])
        assert code != EXIT_INTERNAL
        assert "ERROR_INTERNAL" not in err
