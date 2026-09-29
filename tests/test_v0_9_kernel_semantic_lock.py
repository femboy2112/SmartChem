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
import textwrap
from fractions import Fraction

import pytest

import smartchem.data.derived_evidence as de
from smartchem.contracts import canonical_digest
import smartchem.material_spec as ms
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
    # D24.9 (Wave-C' C3): re-pinned ONCE, pre-release, because three beyond-PRECISION_DP vectors were ADDED to this
    # member (no kernel code changed -- every pre-existing vector and every AST pin is unchanged).
    "IDENTITY_SOURCE_QUOTED_V1": "f0f15be9433c962d387104fd3ace82a2e8ebf0144b805b0d8e1c45bceb4102a8",
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
    "IntervalEvidence.recompute": "4ace78e516cc31866eb6c3cdf1fcfa0d35b5ce6933fae6158ae0a9c703d20c2f",
    # D24.9 (Wave-C' C3): the helpers the recompute path ALSO runs through. Adversary C drifted the unpinned
    # ``TypedInput.exact`` (half-even rounding to 6 dp) and every pin above still passed while a V1 record flipped
    # a bottle from UNKNOWN to a pure-material FIT. Checked identical on CPython 3.10, 3.11, 3.12 and 3.13.
    "TypedInput.exact": "32ac7854c90a54376fef106c5ab72b38ba7155ab5d061b8d6f9266c92a00c12d",
    "IntervalEvidence.interval": "14e199ae050251d412a0849e47a96aa5d87c20e424adb5fb1a855ae11c32f126",
    "IntervalEvidence.verify": "d44041ad39b2822c0e6021552f2d9c2691a648eac516324da74f71708b78f558",
    "IntervalEvidence.build": "2020c48bf8d5d4dd4f06b52bbb21d7d8e1731c2a8a27ebb95bc734872741dd7c",
    "exact_fraction": "b70b591ab0becd7986564c44655364dd794b039b48314cc421d29a3c0186d0f6",
}

_HELPERS = {
    "_scaled": de._scaled,
    "_round_outward": de._round_outward,
    "canonical_decimal": de.canonical_decimal,
    "IntervalEvidence.recompute": IntervalEvidence.recompute,
    "TypedInput.exact": TypedInput.exact.fget,
    "IntervalEvidence.interval": IntervalEvidence.interval.fget,
    "IntervalEvidence.verify": IntervalEvidence.verify,
    "IntervalEvidence.build": IntervalEvidence.build.__func__,
    "exact_fraction": ms.exact_fraction,
}

#: D24.9 (Wave-C' C3): which FUNCTION each member runs, by module-qualified ``__qualname__`` -- a swap of two kernels'
#: functions (e.g. pointing a member at another member's arithmetic) is a V1 semantic change even when every AST pin
#: and every per-function digest is untouched. FROZEN.
PINNED_KERNEL_FUNCTIONS = {
    "IDENTITY_SOURCE_QUOTED_V1": "smartchem.data.derived_evidence._k_identity",
    "SOLUBILITY_PER_100G_SOLVENT_TO_MASS_FRACTION_V1": "smartchem.data.derived_evidence._k_solubility",
    "COMPLEMENT_V1": "smartchem.data.derived_evidence._k_complement",
    "CLAMP_TO_UNIT_INTERVAL_V1": "smartchem.data.derived_evidence._k_clamp",
    "ASSUMED_BAND_V1": "smartchem.data.derived_evidence._k_band",
    "USER_DECLARED_V1": "smartchem.data.derived_evidence._k_identity",
    "UNKNOWN_V1": "smartchem.data.derived_evidence._k_unknown",
}


def _qualified(fn) -> str:
    return f"{fn.__module__}.{fn.__qualname__}"


def _recompute_path_closure() -> "set[str]":
    """Every function the recompute path can reach inside ``derived_evidence`` / ``material_spec``: start from each
    kernel fn and the IntervalEvidence recompute/verify/build/__post_init__, walk their ASTs, and follow every bare
    name that is a module-level function of either module and every attribute that names a property/method of
    TypedInput / IntervalEvidence. Returns the ``_HELPERS``-style keys, so an UNPINNED helper is loud."""
    candidates: "dict[str, object]" = {}
    for mod in (de, ms):
        for name, obj in vars(mod).items():
            if inspect.isfunction(obj) and obj.__module__ == mod.__name__:
                candidates[name] = obj
    members: "dict[str, object]" = {}
    for cls in (TypedInput, IntervalEvidence):
        for name, obj in vars(cls).items():
            if isinstance(obj, property):
                members[name] = (f"{cls.__name__}.{name}", obj.fget)
            elif isinstance(obj, classmethod):
                members[name] = (f"{cls.__name__}.{name}", obj.__func__)
            elif inspect.isfunction(obj):
                members[name] = (f"{cls.__name__}.{name}", obj)
    seen: "set[str]" = set()
    todo = [("kernel", spec.fn) for spec in KERNELS.values()] + [
        ("IntervalEvidence.recompute", IntervalEvidence.recompute), ("IntervalEvidence.verify", IntervalEvidence.verify),
        ("IntervalEvidence.build", IntervalEvidence.build.__func__),
        ("IntervalEvidence.__post_init__", IntervalEvidence.__post_init__)]
    while todo:
        label, fn = todo.pop()
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in candidates and node.id not in seen:
                seen.add(node.id)
                todo.append((node.id, candidates[node.id]))
            elif isinstance(node, ast.Attribute) and node.attr in members:
                key, target = members[node.attr]
                if key not in seen and not key.endswith(("__post_init__", "as_floats")):
                    seen.add(key)
                    todo.append((key, target))
    return seen


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

    def test_every_member_is_bound_to_its_pinned_function_by_qualified_name(self):
        """D24.9: the kernel->function map itself is pinned (``__name__`` set-equality let two members swap
        functions silently)."""
        assert {k.name: _qualified(KERNELS[k].fn) for k in DerivationKernel} == PINNED_KERNEL_FUNCTIONS

    def test_every_helper_on_the_recompute_path_is_pinned(self):
        """D24.9: the AST pin set is COMPLETE -- every module function / TypedInput-IntervalEvidence member the
        recompute path can reach (transitively) is pinned; an unpinned helper (the C3 hole) fails here."""
        reachable = _recompute_path_closure()
        kernel_fn_names = {spec.fn.__name__ for spec in KERNELS.values()}
        unpinned = sorted((reachable - kernel_fn_names) - set(PINNED_AST_DIGESTS))
        assert unpinned == [], f"helpers on the recompute path with no AST pin: {unpinned}"

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

    def test_a_pre_rounding_input_helper_is_caught_by_the_vectors_and_the_pin(self, monkeypatch):
        """Wave-C' C3 (Adversary C's exact drift): ``TypedInput.exact`` rounds half-even to PRECISION_DP BEFORE the
        kernel runs. Without the D24.9 beyond-precision vectors that edit replays every frozen vector clean (the
        gap was real); with them it is refused, and the helper's AST pin moves."""
        from decimal import ROUND_HALF_EVEN, Decimal

        def drifted_exact(self):
            return Fraction(Decimal(self.value).quantize(Decimal(1).scaleb(-de.PRECISION_DP), ROUND_HALF_EVEN))

        monkeypatch.setattr(TypedInput, "exact", property(drifted_exact))
        beyond = {v.label for v in KERNEL_KNOWN_ANSWERS if "beyond-precision" in v.label}
        assert len(beyond) == 3
        monkeypatch.setattr(de, "KERNEL_KNOWN_ANSWERS",
                            tuple(v for v in KERNEL_KNOWN_ANSWERS if v.label not in beyond))
        de.verify_kernel_known_answers()  # the pre-D24.9 vector set is BLIND to this drift -- that was the hole
        monkeypatch.setattr(de, "KERNEL_KNOWN_ANSWERS", KERNEL_KNOWN_ANSWERS)
        with pytest.raises(RuntimeError, match="beyond-precision"):
            de.verify_kernel_known_answers()
        assert kernel_ast_digest(drifted_exact) != PINNED_AST_DIGESTS["TypedInput.exact"]

    def test_the_pure_bottle_forgery_the_drift_enabled_is_refused_honestly(self):
        """The drifted V1 minted SOURCE_QUOTED [1, 1] from a quoted 0.9999995 -- a 'pure' witness from a certificate
        that proves nothing of the sort. The honest V1 keeps the outward interval, and a hand-written [1, 1]
        record over that input is refused at construction."""
        loc = "coa"
        ins = tuple(TypedInput(n, "0.9999995", InputUnit.FRACTION, EvidenceKind.SOURCE_QUOTED, loc)
                    for n in ("low", "high"))
        rec = IntervalEvidence.build(kernel=DerivationKernel.IDENTITY_SOURCE_QUOTED_V1,
                                     basis=ConcentrationBasis.MASS_FRACTION, inputs=ins, source_locators=(loc,),
                                     domain_of_validity="d")
        assert (rec.low, rec.high) == ("0.999999", "1")
        with pytest.raises(ValueError, match="recomputes"):
            IntervalEvidence(EvidenceKind.SOURCE_QUOTED, "1", "1", ConcentrationBasis.MASS_FRACTION, (loc,),
                             DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, ins, "d")

    def test_a_kernel_function_swap_is_caught_by_the_qualified_map(self, monkeypatch):
        key = DerivationKernel.IDENTITY_SOURCE_QUOTED_V1
        monkeypatch.setitem(KERNELS, key, dc.replace(KERNELS[key], fn=de._k_band))
        assert {k.name: _qualified(KERNELS[k].fn) for k in DerivationKernel} != PINNED_KERNEL_FUNCTIONS

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
