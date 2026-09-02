"""SVC-REQ-01 alias-collapse: the semantic digest keys on WHAT the target is, not HOW it was spelled.

The first SVC-REQ-01 brick made ``compile``/``recompile`` build byte-identical requests for equal FLAGS.  This
closes the boundary the ``semantic_digest`` docstring confessed: the target used to enter as the raw
``(target_input, input_kind)`` pair, so ``paracetamol`` / ``name:paracetamol`` / ``smiles:CC(=O)Nc1ccc(O)cc1`` --
which run the byte-identical search -- got THREE different digests.  Now they collapse to one, and the ParseReceipt
(provenance) is pulled out of ``diagnostics`` into its own field so ``result_digest`` collapses too.

The load-bearing safety: collapse fires ONLY for a feature-free molecule, so it can never MERGE two requests whose
IRs differ by a section-5.3 loss (a stereo/isotope/charge-declaring input keeps raw keying).  That keeps the
collapse strictly on the safe, only-SPLIT-relative-to-execution side of the section-13.1 one-way law.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from dataclasses import replace

import pytest

from smartchem.cli import main
from smartchem.identity_parse import InputKind
from smartchem.service import (
    build_decompile_request,
    build_recompile_request,
    request_from_payload,
    request_to_payload,
    response_semantic_fields,
    response_to_payload,
    run_compilation,
    serialize_request,
    deserialize_request,
    serialize_response,
    deserialize_response,
)

# three spellings of ONE molecule (paracetamol); a registry name, an explicit name: prefix, and its SMILES.
_PARA_FORMS = ["paracetamol", "name:paracetamol", "smiles:CC(=O)Nc1ccc(O)cc1"]


def _cli(argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


class TestAliasCollapse:
    def test_every_spelling_of_one_molecule_shares_one_search_identity(self):
        reqs = [build_recompile_request(s) for s in _PARA_FORMS]
        assert len({r.semantic_digest for r in reqs}) == 1, "spellings of one molecule must share a search identity"

    def test_collapse_reflects_a_genuinely_identical_search_not_a_hash_coincidence(self):
        # the digest collapse is HONEST only if the search really is the same: prove the produced IRs are byte-equal.
        irs = [run_compilation(build_recompile_request(s)).compilation_ir for s in _PARA_FORMS]
        assert all(ir is not None for ir in irs)
        assert len({ir.digest for ir in irs}) == 1

    def test_collapse_carries_through_to_the_result_digest(self):
        results = [run_compilation(build_recompile_request(s)).result_digest for s in _PARA_FORMS]
        assert len(set(results)) == 1, "equal semantic_digest MUST yield equal result_digest (one-way law)"

    @pytest.mark.parametrize("name,smiles", [
        ("dimethyl ether", "smiles:COC"),
        ("acetic anhydride", "smiles:CC(=O)OC(C)=O"),
        ("methylamine", "smiles:CN"),
    ])
    def test_the_one_way_law_holds_when_the_search_ACTUALLY_PRODUCES_ROUTES(self, name, smiles):
        # NON-VACUITY POSITIVE CONTROL (red-team false-merge-noncanonical-name-vs-smiles): the paracetamol example
        # is INCOMPLETE with zero candidates, so its result_digest collapse cannot exercise the candidate-digest
        # path -- a name-only or paracetamol-only test is VACUOUS for the real break.  These names are stored
        # NON-CANONICALLY in the offline registry while the SMILES parser canonicalises; without canonicalising the
        # search inputs, their route/candidate digests (and thus result_digest) diverge even though the digest
        # collapsed them.  Guard the REAL path: a molecule that produces >=1 route.
        n, s = run_compilation(build_recompile_request(name)), run_compilation(build_recompile_request(smiles))
        assert n.outcome.value == "ROUTES_FOUND" and n.compilation_ir.candidate_count >= 1  # the path is exercised
        assert build_recompile_request(name).semantic_digest == build_recompile_request(smiles).semantic_digest
        assert n.compilation_ir.digest == s.compilation_ir.digest, "the search must be presentation-invariant"
        assert n.result_digest == s.result_digest, "equal semantic_digest MUST yield equal result_digest under routes"

    def test_bare_and_explicit_name_prefix_collapse(self):
        assert (
            build_recompile_request("water").semantic_digest
            == build_recompile_request("name:water").semantic_digest
        )

    def test_input_kind_is_provenance_once_resolved(self):
        # "water" AUTO and "water" NAME resolve to the same molecule -> collapse; the kind (how it was named) drops.
        auto = build_recompile_request("water", input_kind=InputKind.AUTO)
        named = build_recompile_request("water", input_kind=InputKind.NAME)
        assert auto.normalized_identity and auto.normalized_identity == named.normalized_identity
        assert auto.semantic_digest == named.semantic_digest

    def test_normalized_identity_is_the_canonical_structure_digest(self):
        # it is exactly the structure identity the engine searches on (byte-equal to the IR's target digest chain).
        req = build_recompile_request("smiles:CC(=O)Nc1ccc(O)cc1")
        assert req.normalized_identity  # non-empty for a resolvable feature-free molecule
        # ...and the SAME molecule reached by name yields the SAME normalized identity.
        assert req.normalized_identity == build_recompile_request("paracetamol").normalized_identity


class TestCollapseIsSound:
    """The one-way law protection: collapse must NEVER merge two requests whose searches differ."""

    def test_different_molecules_stay_split(self):
        assert (
            build_recompile_request("name:water").semantic_digest
            != build_recompile_request("name:ethanol").semantic_digest
        )

    def test_a_stereo_declaring_smiles_does_not_collapse_with_its_flat_twin(self):
        # L-alanine (declares a stereocentre) vs alanine (flat): SAME constitution, but the stereo input carries a
        # section-5.3 loss -> it MUST keep raw keying, or the collapse would merge two different-result requests.
        flat = build_recompile_request("smiles:CC(N)C(=O)O")
        stereo = build_recompile_request("smiles:C[C@@H](N)C(=O)O")
        assert flat.normalized_identity != ""          # flat collapses
        assert stereo.normalized_identity == ""         # feature-bearing keeps raw keying
        assert flat.semantic_digest != stereo.semantic_digest

    def test_an_isotope_declaring_smiles_does_not_collapse_with_its_flat_twin(self):
        flat = build_recompile_request("smiles:CC(=O)O")
        labelled = build_recompile_request("smiles:[13CH3]C(=O)O")
        assert flat.normalized_identity != ""
        assert labelled.normalized_identity == ""        # the isotope feature blocks the collapse
        assert flat.semantic_digest != labelled.semantic_digest

    def test_a_non_target_field_still_splits_a_collapsed_target(self):
        # collapsing the TARGET must not swallow a real difference elsewhere: same molecule, different bounds -> split.
        a = build_recompile_request("paracetamol", max_depth=2)
        b = build_recompile_request("paracetamol", max_depth=3)
        assert a.normalized_identity == b.normalized_identity   # same target
        assert a.semantic_digest != b.semantic_digest           # but the search bounds differ

    def test_the_one_way_law_holds_for_the_collapsed_forms(self):
        # the whole point: equal semantic_digest => equal result_digest, EVEN THOUGH the receipts differ per spelling.
        resps = [run_compilation(build_recompile_request(s)) for s in _PARA_FORMS]
        assert len({r.semantic_digest for r in (build_recompile_request(s) for s in _PARA_FORMS)}) == 1
        assert len({r.result_digest for r in resps}) == 1
        # ...and the receipts genuinely DID differ (otherwise the exclusion below would be vacuous).
        assert len({r.parse_receipt_summary for r in resps}) == len(_PARA_FORMS)


class TestProvenanceExcludedFromResult:
    def test_the_receipt_left_diagnostics_for_its_own_field(self):
        resp = run_compilation(build_recompile_request("paracetamol"))
        assert resp.parse_receipt_summary and "IDENTITY RESOLVED" in resp.parse_receipt_summary
        assert not any("IDENTITY RESOLVED" in d for d in resp.diagnostics)

    def test_result_digest_ignores_the_receipt(self):
        # DIRECT proof of exclusion: mutate ONLY the receipt -> result_digest is unchanged (it is provenance).
        resp = run_compilation(build_recompile_request("paracetamol"))
        forged = replace(resp, parse_receipt_summary="IDENTITY RESOLVED [FORGED] via NOWHERE: X (FORMULA layer)")
        assert forged.result_digest == resp.result_digest

    def test_the_receipt_is_a_first_class_semantic_field_in_both_views(self):
        resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
        fields = response_semantic_fields(resp)
        payload = response_to_payload(resp)
        assert fields["parse_receipt"] == payload["parse_receipt_summary"] == resp.parse_receipt_summary


class TestUnresolvableFallsBackToRawKeying:
    def test_an_unresolvable_target_keys_on_the_raw_input(self):
        req = build_recompile_request("not-a-real-name-zzz")
        assert req.normalized_identity == ""            # could not resolve -> no collapse

    def test_two_distinct_unresolvable_strings_stay_split(self):
        a = build_recompile_request("not-a-real-name-aaa")
        b = build_recompile_request("not-a-real-name-bbb")
        assert a.semantic_digest != b.semantic_digest   # raw keying preserves their distinctness

    def test_an_unresolvable_target_is_still_refused_at_run(self):
        resp = run_compilation(build_recompile_request("not-a-real-name-zzz"))
        assert resp.exit_code == 2 and resp.compilation_ir is None


class TestDecompileKeepsRawKeying:
    def test_decompile_does_not_collapse_in_this_brick(self):
        # documented boundary: a decompile has no aliases and a FORMULA-layer target, so it keeps raw keying ("").
        req = build_decompile_request("C8H9NO2")
        assert req.normalized_identity == ""

    def test_decompile_input_kind_still_splits(self):
        # the pre-existing "safe one-way superset" property survives: AUTO vs FORMULA split, same search.
        a = build_decompile_request("C6H6", input_kind=InputKind.AUTO)
        b = build_decompile_request("C6H6", input_kind=InputKind.FORMULA)
        assert a.semantic_digest != b.semantic_digest
        assert run_compilation(a).compilation_ir.digest == run_compilation(b).compilation_ir.digest


class TestRoundTrip:
    def test_request_round_trip_preserves_the_normalized_identity(self):
        req = build_recompile_request("paracetamol")
        back = deserialize_request(serialize_request(req))
        assert back.normalized_identity == req.normalized_identity
        assert back.semantic_digest == req.semantic_digest

    def test_response_round_trip_preserves_the_receipt_and_result_digest(self):
        resp = run_compilation(build_recompile_request("paracetamol", max_depth=2))
        back = deserialize_response(serialize_response(resp))
        assert back.parse_receipt_summary == resp.parse_receipt_summary
        assert back.result_digest == resp.result_digest


class TestHumanJsonAgreeOnTheReceipt:
    @pytest.mark.parametrize("argv", [
        ["recompile", "smiles:CC(=O)OC", "--max-depth", "2"],
        ["recompile", "paracetamol", "--max-depth", "2"],
    ])
    def test_the_receipt_appears_in_both_the_human_render_and_json(self, argv):
        _, human = _cli(argv)
        _, jout = _cli([*argv, "--json"])
        receipt = json.loads(jout)["parse_receipt_summary"]
        assert receipt, "a resolvable target must echo a parse receipt in --json"
        assert receipt in human, "the human render must surface the same receipt (CLI-JSON-01 agreement)"


class TestRedTeamRegressions:
    """The four red-team findings (workflow wmw8d912y), each pinned so it cannot silently return."""

    def test_target_file_does_not_collapse_build_run_skew(self, tmp_path):
        # F3 (MED): normalized_identity is frozen at BUILD time, but a TARGET_FILE is re-read at RUN time. A mutable
        # file must NOT collapse with a name request, or a between-times edit would merge two different molecules.
        f = tmp_path / "target.txt"
        f.write_text("water\n")
        file_req = build_recompile_request(str(f), input_kind=InputKind.TARGET_FILE)
        assert file_req.normalized_identity == ""       # a mutable source never collapses
        assert file_req.semantic_digest != build_recompile_request("water").semantic_digest

    def test_a_forged_normalized_identity_is_refused_on_deserialize(self):
        # F4 (MED): normalized_identity is a free string in the payload; a forged value could give one molecule's
        # request another's search identity (equal semantic_digest over DIFFERENT searches, section 13.1 break).
        # Deserialize RECOMPUTES it and refuses a mismatch.
        water, ethanol = build_recompile_request("water"), build_recompile_request("ethanol")
        forged = dict(request_to_payload(ethanol))
        forged["normalized_identity"] = water.normalized_identity   # claim water's identity for an ethanol request
        with pytest.raises(ValueError, match="does not match the target's resolution"):
            request_from_payload(forged)

    def test_a_legitimate_payload_still_round_trips(self):
        # non-vacuity for the forge guard: an untampered payload must deserialize cleanly (the recompute matches).
        req = build_recompile_request("acetic anhydride", max_depth=2)
        assert request_from_payload(request_to_payload(req)).semantic_digest == req.semantic_digest

    @pytest.mark.parametrize("name,smiles", [("dimethyl ether", "smiles:COC"), ("methylamine", "smiles:CN")])
    def test_noncanonical_registry_name_matches_its_canonical_smiles_result(self, name, smiles):
        # F1/F2 (HIGH): the load-bearing soundness break. A registry name stored in non-canonical atom order and its
        # parser-canonicalised SMILES collapse; the search must be presentation-invariant so result_digests agree.
        n, s = run_compilation(build_recompile_request(name)), run_compilation(build_recompile_request(smiles))
        assert n.result_digest == s.result_digest
