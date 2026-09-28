"""Round V X-high (barrier D19) -- the derivation-kernel SEMANTIC LOCK.

A stored :class:`~smartchem.data.derived_evidence.IntervalEvidence` names its kernel by ID only; the arithmetic is code
that the record's digest never sees. Lane A-PHASE proved the hazard: swap ``SOLUBILITY_..._V1``'s arithmetic for one
that differs only above s = 40 and the shipped NaCl record (s = 36) still verifies, still digests the same, and the ID
never moves. These tests make that silent edit LOUD: the frozen known-answer vectors replay at import, and every
member's declared semantics + every kernel function's AST are pinned here as hex literals.

**If a test in this file fails, do NOT update the literal.** A V1 kernel is immutable (the 1.0 compatibility contract in
the module docstring): mint ``X_V2`` with its own vectors and leave ``X_V1`` alone. Retiring a member is allowed;
changing one is not.
"""
from __future__ import annotations

import ast
import dataclasses as dc
import inspect
from fractions import Fraction

import pytest

import smartchem.data.derived_evidence as de
from smartchem.contracts import canonical_digest
from smartchem.data.derived_evidence import (
    KERNEL_KNOWN_ANSWERS,
    KERNELS,
    DerivationKernel,
    InputUnit,
    IntervalEvidence,
    TypedInput,
    kernel_ast_digest,
    kernel_semantic_descriptor,
    verify_kernel_known_answers,
)
from smartchem.material_spec import ConcentrationBasis, EvidenceKind

#: canonical_digest(kernel_semantic_descriptor(member)) -- name, input patterns/units/kinds, output kind, bases,
#: parent requirement, PRECISION_DP and the frozen vectors. FROZEN: a mismatch is a V1 semantic change.
PINNED_SEMANTIC_DESCRIPTORS = {
    "IDENTITY_SOURCE_QUOTED_V1": "02a8080e6227bd3113d3eb05ecfa52e0512716ed80bb8e6dd9b2db48c70f9240",
    "SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1": "5e0ec9e47baa9a1a1825ad223aa196c913b017ea913f86e2472433e8456d153f",
    "COMPLEMENT_V1": "209b77bb0103fd3a90f60bb69c1f880e8611ae3576375e668f75d3f43aef1641",
    "CLAMP_TO_UNIT_INTERVAL_V1": "49ca5ce4dc416d3a566991ee238cb5d07d4f8b52a13aa46c146f439eb5955f2e",
    "ASSUMED_BAND_V1": "797a34d2d79c0608d6290375711395095bb2addc3c45ef7b6d356f98b0d3a7cd",
    "USER_DECLARED_V1": "fbaceaec7e1b88df9cdb5a4b458087248ad0a409962af40d1ca9f76bbeb9ebde",
    "UNKNOWN_V1": "31f591eb21479b22304835f46c02e947065e22fa713144df8469dc93eb23cf47",
}

#: kernel_ast_digest(fn) -- the canonical, Python-version-portable AST (comments/formatting/docstrings excluded) of
#: every kernel function and every arithmetic helper a stored record is re-verified through. FROZEN.
PINNED_AST_DIGESTS = {
    "_k_identity": "dabc9841837bdd58b63f6882bff4bd9ee345700b3c09a382778a9e1915efacb0",
    "_k_solubility": "814fafd3bcb666bdcb5262f36f798740b6b8661d2dcda227c62e30e0a829808a",
    "_k_complement": "2f869c929420da0177f6aa3cb6d60e21148f10300d162576aa85148071dcc2ba",
    "_k_clamp": "41f4c44cf1b346fcc14e631706c720462018991c08095bb18f6b44dc7c2ba924",
    "_k_band": "e3c3675dc4e783a9eebf8b8ff1761e43343bfbb701cd6f751e50aef45d9967ba",
    "_k_unknown": "80646979d6909002e8c6a0837c5a30e92c951698c54f046c6959c924e5389840",
    "_scaled": "4e20cb3946624e4b50ec49558454fb676abd962d2136ebda527cd8a7812a3368",
    "_round_outward": "3acf2d08265c915fd7a5a200080143259cff106f4bf7d2f9de3a10e890c92a3b",
    "canonical_decimal": "b904a20cfec3e03fd13e6a7cbe0def85007b1c0f65edf9e47ba5deaa093763ef",
    "recompute": "4ace78e516cc31866eb6c3cdf1fcfa0d35b5ce6933fae6158ae0a9c703d20c2f",
}

_HELPERS = {
    "_scaled": de._scaled,
    "_round_outward": de._round_outward,
    "canonical_decimal": de.canonical_decimal,
    "recompute": IntervalEvidence.recompute,
}


def _nacl_record() -> IntervalEvidence:
    """The shipped-shape saturated-NaCl record (s = 36 g / 100 g water)."""
    loc = "https://pubchem.ncbi.nlm.nih.gov/compound/5234"
    inputs = tuple(TypedInput(n, "36.0", InputUnit.G_PER_100G_SOLVENT, EvidenceKind.SOURCE_QUOTED, loc)
                   for n in ("low", "high"))
    return IntervalEvidence.build(kernel=DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
                                  basis=ConcentrationBasis.MASS_FRACTION, inputs=inputs, source_locators=(loc,),
                                  domain_of_validity="25 C")


class TestTheLockIsFrozen:
    def test_every_member_has_a_pinned_semantic_descriptor_and_it_matches(self):
        assert set(PINNED_SEMANTIC_DESCRIPTORS) == {k.name for k in DerivationKernel}
        for kernel in DerivationKernel:
            assert canonical_digest(kernel_semantic_descriptor(kernel)) == PINNED_SEMANTIC_DESCRIPTORS[kernel.name], (
                f"{kernel.value}: the declared semantics changed -- mint a _V2 member, never edit a V1 (D19)")

    def test_every_kernel_function_and_arithmetic_helper_has_a_pinned_ast(self):
        kernel_fns = {spec.fn.__name__: spec.fn for spec in KERNELS.values()}
        assert set(kernel_fns) | set(_HELPERS) == set(PINNED_AST_DIGESTS), "a kernel fn/helper is unpinned"
        for name, fn in {**kernel_fns, **_HELPERS}.items():
            assert kernel_ast_digest(fn) == PINNED_AST_DIGESTS[name], (
                f"{name}: the arithmetic changed -- mint a _V2 member, never edit a V1 (D19)")

    def test_the_registry_is_exactly_the_closed_enum_and_every_member_has_vectors(self):
        assert set(KERNELS) == set(DerivationKernel)
        covered = {v.kernel for v in KERNEL_KNOWN_ANSWERS}
        assert covered == set(DerivationKernel)
        # the kernels that CAN refuse carry at least one frozen refusal vector (a refusal is semantics too)
        refusing = {v.kernel for v in KERNEL_KNOWN_ANSWERS if v.refuses is not None}
        assert refusing >= {DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                            DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1,
                            DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1, DerivationKernel.USER_DECLARED_V1}
        labels = [v.label for v in KERNEL_KNOWN_ANSWERS]
        assert len(labels) == len(set(labels))

    def test_the_vectors_replay_clean_on_the_shipped_kernels(self):
        verify_kernel_known_answers()  # raises on any deviation

    def test_the_nacl_vector_is_the_shipped_nacl_record(self):
        nacl = next(v for v in KERNEL_KNOWN_ANSWERS if v.label == "solubility-nacl-36")
        record = _nacl_record()
        assert (record.low, record.high, record.kind) == (nacl.low, nacl.high, nacl.kind)
        assert (nacl.low, nacl.high) == ("0.264705", "0.264706")

    def test_the_module_replays_the_vectors_at_import(self):
        """Structural: the LAST top-level statement of the module is the verifier call, so a drifted kernel makes
        ``import smartchem.data.derived_evidence`` itself fail."""
        tree = ast.parse(inspect.getsource(de))
        last = tree.body[-1]
        assert isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
        assert isinstance(last.value.func, ast.Name) and last.value.func.id == "verify_kernel_known_answers"


class TestTheLockDiscriminates:
    """Each test injects exactly the silent edit the lock exists to catch and shows it is CAUGHT (the honest code
    passes the same checks above)."""

    def test_arithmetic_drift_outside_the_shipped_record_region_is_caught(self, monkeypatch):
        """Lane A-PHASE's reproducer: arithmetic identical for s <= 40, different above. The shipped NaCl record (s =
        36) STILL re-verifies -- that is the gap -- but the frozen s = 60 vector refuses the edit."""
        key = DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1
        honest_fn = KERNELS[key].fn

        def drifted(inputs, parent):
            lo, hi = inputs["low"].exact, inputs["high"].exact
            if hi <= 40:
                return honest_fn(inputs, parent)
            return lo / (lo + 50), hi / (hi + 50)  # a "bug fix" that edits V1 in place

        monkeypatch.setitem(KERNELS, key, dc.replace(KERNELS[key], fn=drifted))
        assert _nacl_record().verify()  # the gap: the record region never exercises the edit
        with pytest.raises(RuntimeError, match="solubility-60"):
            verify_kernel_known_answers()
        assert kernel_ast_digest(drifted) != PINNED_AST_DIGESTS["_k_solubility"]

    def test_an_output_kind_edit_is_caught_by_the_vectors_and_the_descriptor(self, monkeypatch):
        """The Wave-C precedent (COMPLEMENT_V1's kind changed in place pre-release): flip it back to 'the parent's
        kind' and both the complement vector (expects ASSUMED over a DERIVED parent) and the pinned descriptor fail."""
        key = DerivationKernel.COMPLEMENT_V1
        monkeypatch.setitem(KERNELS, key, dc.replace(KERNELS[key], output_kind=None))
        with pytest.raises(RuntimeError, match="complement-of-nacl"):
            verify_kernel_known_answers()
        assert canonical_digest(kernel_semantic_descriptor(key)) != PINNED_SEMANTIC_DESCRIPTORS[key.name]

    def test_a_refusal_that_stops_refusing_is_caught(self, monkeypatch):
        key = DerivationKernel.CLAMP_TO_UNIT_INTERVAL_V1

        def lenient(inputs, parent):  # "helpfully" passes an in-range quote through instead of refusing it
            if "floor" in inputs:
                return max(Fraction(0), de._scaled(inputs["floor"])), Fraction(1)
            return max(Fraction(0), de._scaled(inputs["low"])), min(Fraction(1), de._scaled(inputs["high"]))

        monkeypatch.setitem(KERNELS, key, dc.replace(KERNELS[key], fn=lenient))
        with pytest.raises(RuntimeError, match="must refuse"):
            verify_kernel_known_answers()

    def test_an_admissible_unit_widening_is_caught_by_the_descriptor(self, monkeypatch):
        """F72 regression path: letting the solubility kernel admit per-VOLUME inputs is a semantic change even
        though no arithmetic moves -- the refusal vector and the descriptor both catch it."""
        key = DerivationKernel.SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1
        wider = KERNELS[key].units | {InputUnit.G_PER_100ML_SOLVENT}
        monkeypatch.setitem(KERNELS, key, dc.replace(KERNELS[key], units=wider))
        with pytest.raises(RuntimeError, match="solubility-refuses-per-volume"):
            verify_kernel_known_answers()
        assert canonical_digest(kernel_semantic_descriptor(key)) != PINNED_SEMANTIC_DESCRIPTORS[key.name]

    def test_a_member_without_vectors_is_caught(self, monkeypatch):
        kept = tuple(v for v in KERNEL_KNOWN_ANSWERS if v.kernel is not DerivationKernel.UNKNOWN_V1)
        monkeypatch.setattr(de, "KERNEL_KNOWN_ANSWERS", kept)
        with pytest.raises(RuntimeError, match="no known-answer vector"):
            de.verify_kernel_known_answers()

    def test_the_ast_digest_ignores_prose_but_sees_code(self):
        assert kernel_ast_digest(_prose_a()) == kernel_ast_digest(_prose_b())  # docstring/comment edit: not semantic
        assert kernel_ast_digest(_prose_a()) != kernel_ast_digest(_code_c())   # a code edit is


def _prose_a():
    def f(x):
        """Doc one."""
        return x + 1  # a comment
    return f


def _prose_b():
    def f(x):
        """A completely different docstring."""
        return x + 1
    return f


def _code_c():
    def f(x):
        """Doc one."""
        return x + 2
    return f
