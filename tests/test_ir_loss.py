"""IR-LOSS-01 -- the ChemicalCompilationIR carries FIRST-CLASS typed section-5.3 ``IdentityLoss`` records.

Before this brick the IR carried losses as summary STRINGS; the loss's severity and affected-claims set were only
reachable by parsing that string.  Now the IR holds the typed records themselves, so:

* a machine consumer reads ``severity``/``affected_claims`` structurally (never by string-parsing);
* the loss's semantic content (its severity, its affected claims) rides the IR's own digest -- a WARNING and a
  BLOCKER over the same feature are DIFFERENT IRs;
* a tampered loss payload is refused on deserialization, exactly like every other IR record.

Acceptance (manifest 3.2): *"CCO vs COC remain distinct as input identities; the formula view announces collapse."*
"""
from __future__ import annotations

import pytest

from smartchem.compilation_ir import (
    ChemicalCompilationIR,
    decompile_to_ir,
    deserialize_ir,
    ir_from_payload,
    ir_to_payload,
    serialize_ir,
)
from smartchem.decompiler import example_inventory
from smartchem.identity import (
    IDENTITY_LOSS_SCHEMA,
    IdentityLoss,
    LossSeverity,
    formula_reduction_loss,
)
from smartchem.identity_parse import InputKind
from smartchem.service import build_decompile_request, run_compilation

INV = example_inventory()


def _cco_loss():
    return formula_reduction_loss("smiles:CCO", "C2H6O")


def _coc_loss():
    return formula_reduction_loss("smiles:COC", "C2H6O")


class TestIRCarriesTypedLossRecords:
    def test_identity_losses_are_typed_records_not_strings(self):
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        assert len(ir.identity_losses) == 1
        assert type(ir.identity_losses[0]) is IdentityLoss
        assert ir.identity_losses[0].severity is LossSeverity.BLOCKER
        # the machine reads the affected-claims SET structurally, never by parsing a string
        assert "structure-identity" in ir.identity_losses[0].affected_claims

    def test_summaries_are_the_derived_human_json_bridge(self):
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        assert ir.identity_loss_summaries == (ir.identity_losses[0].summary(),)
        assert "IDENTITY LOSS [BLOCKER]" in ir.identity_loss_summaries[0]

    def test_losses_are_carried_in_canonical_digest_order(self):
        # order in == order stored is NOT guaranteed; canonical digest order IS.
        losses = (_coc_loss(), _cco_loss())
        ir = decompile_to_ir("C2H6O", INV, identity_losses=losses)
        got = [loss.digest for loss in ir.identity_losses]
        assert got == sorted(got)

    def test_construction_rejects_unsorted_losses(self):
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(), _coc_loss()))
        assert len(ir.identity_losses) == 2
        with pytest.raises(ValueError, match="canonical .*order"):
            ChemicalCompilationIR(
                ir.schema_version, ir.tool_version, ir.operation, ir.target, ir.request_digest,
                tuple(reversed(ir.identity_losses)), ir.terminal_policy_digest, ir.transform_registry_digest,
                ir.search_status, ir.standard_status, ir.search_receipt_digest, ir.candidates, ir.diagnostics,
            )

    def test_construction_rejects_a_non_loss_in_the_tuple(self):
        ir = decompile_to_ir("C2H6O", INV)
        with pytest.raises(TypeError, match="identity_losses must be a tuple of IdentityLoss"):
            ChemicalCompilationIR(
                ir.schema_version, ir.tool_version, ir.operation, ir.target, ir.request_digest,
                ("a summary string, not a record",), ir.terminal_policy_digest, ir.transform_registry_digest,
                ir.search_status, ir.standard_status, ir.search_receipt_digest, ir.candidates, ir.diagnostics,
            )


class TestLossContentRidesTheIRDigest:
    """The payoff of first-class records: the loss's SEMANTIC content is part of the IR identity, not decoration."""

    def test_severity_change_moves_the_ir_digest(self):
        base = _cco_loss()  # a BLOCKER
        warned = IdentityLoss(
            IDENTITY_LOSS_SCHEMA, base.feature, base.input_representation, base.retained_representation,
            base.reason, base.affected_claims, LossSeverity.WARNING,
        )
        blocked_ir = decompile_to_ir("C2H6O", INV, identity_losses=(base,))
        warned_ir = decompile_to_ir("C2H6O", INV, identity_losses=(warned,))
        assert blocked_ir.digest != warned_ir.digest  # a WARNING and a BLOCKER are different IRs

    def test_affected_claims_change_moves_the_ir_digest(self):
        full = _cco_loss()
        narrower = IdentityLoss(
            IDENTITY_LOSS_SCHEMA, full.feature, full.input_representation, full.retained_representation,
            full.reason, ("structure-identity",), LossSeverity.BLOCKER,
        )
        assert (
            decompile_to_ir("C2H6O", INV, identity_losses=(full,)).digest
            != decompile_to_ir("C2H6O", INV, identity_losses=(narrower,)).digest
        )


class TestRoundTrip:
    def test_serialize_round_trip_preserves_the_typed_loss_and_digest(self):
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        back = deserialize_ir(serialize_ir(ir))
        assert back.digest == ir.digest
        assert back.identity_losses == ir.identity_losses
        assert type(back.identity_losses[0]) is IdentityLoss

    def test_payload_emits_a_structured_dict(self):
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        payload = ir_to_payload(ir)["identity_losses"][0]
        assert payload["severity"] == "BLOCKER"
        assert isinstance(payload["affected_claims"], list)
        assert payload["input_representation"] == "smiles:CCO"

    def test_a_tampered_loss_payload_is_refused_on_read(self):
        # the vacuous-BLOCKER fail-open: a BLOCKER that names no claim blocks nothing. It must be refused on read,
        # not silently trusted -- deserialization never constructs a loss it would have rejected at construction.
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        payload = ir_to_payload(ir)
        payload["identity_losses"][0]["affected_claims"] = []
        with pytest.raises(ValueError, match="must name at least one affected claim"):
            ir_from_payload(payload)


class TestSection54FormulaViewAnnouncesCollapse:
    """CCO vs COC (both C2H6O): the formula target collapses to ONE identity, but each input survives in its loss
    record, so the two decompilations remain distinct AND each announces the structural collapse."""

    def test_same_formula_target_but_distinct_input_identities(self):
        cco = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        coc = decompile_to_ir("C2H6O", INV, identity_losses=(_coc_loss(),))
        # the formula target collapsed to one identity ...
        assert cco.target.identity_digest == coc.target.identity_digest
        # ... yet the two IRs are DISTINCT, because each carries its own input representation in the loss record.
        assert cco.digest != coc.digest
        assert cco.identity_losses[0].input_representation == "smiles:CCO"
        assert coc.identity_losses[0].input_representation == "smiles:COC"

    def test_the_loss_announces_the_collapse_as_a_blocker(self):
        ir = decompile_to_ir("C2H6O", INV, identity_losses=(_cco_loss(),))
        loss = ir.identity_losses[0]
        assert loss.severity is LossSeverity.BLOCKER
        assert loss.blocks("structure-identity") and loss.blocks("selectivity")
        assert "reduced to its elemental formula" in loss.reason

    def test_service_path_keeps_the_inputs_distinct(self):
        # end to end through the service: two isomers' SMILES decompilations share a formula target but differ in
        # result identity (their loss records differ), so a formula match never collapses the two inputs (section 5.4).
        cco = run_compilation(build_decompile_request("CCO", input_kind=InputKind.SMILES))
        coc = run_compilation(build_decompile_request("COC", input_kind=InputKind.SMILES))
        assert cco.normalized_target.identity_digest == coc.normalized_target.identity_digest
        assert cco.result_digest != coc.result_digest
        assert cco.identity_loss_summaries != coc.identity_loss_summaries
