"""Assemble a chosen structured descent into ONE gradeable synthesis -- L2 over a whole chain.

The decompiler answers *what could this compound come apart into?* one cleavage at a time; L2
(:mod:`~smartchem.experiment.classify`) grades ONE reaction, route, or DAG.  What was missing between
them was the bridge: nothing turned a *multi-level structural descent* -- a chosen set of valence-capped
cleavages, one per intermediate -- into the single :class:`~smartchem.experiment.dag.SynthesisDAG` a
classifier grades in one shot.  This module is exactly that bridge, and nothing more: it composes existing
certified objects, adding no new physics.

The backbone is the CAPPED descent, chosen deliberately
-------------------------------------------------------
There are two engines that reach real elemental terminals -- ``build_decomposition`` (formula-level,
bond-free :class:`~smartchem.decompiler.Formula`) and ``structure_decompose`` (structure-level, whose
fragments are open-valence RADICALS).  Neither yields a legitimate :class:`~smartchem.category.Molecule`
reactant a step can grade: a ``Formula`` is not a ``Molecule`` (and a bare ``C`` bucket is graphite, not an
atom -- a known-physics landmine), and a radical fragment is not a closed-shell species.  The
:class:`~smartchem.structure_descent.CappedScission` -- the valence-*capped*, closed-shell rewrite that R1
made ring-aware -- is the one descent whose products are real, gradeable molecules.  So THAT is the
backbone here: :meth:`ExperimentStep.from_capped_scission` already turns one capped cleavage into one
assembly step, and this module stacks several of them, at successive levels, into one synthesis.

The honest boundary (two halves of "the entire chain from elemental buckets")
-----------------------------------------------------------------------------
This assembles the STRUCTURED chain -- real intermediate molecules, reaching *through* the aromatic ring
(R1) -- and grades it worst-step-dominated.  It does NOT reach bare single atoms: a capped fragment is a
closed-shell molecule (ketene, phenol, an amine), never a lone ``C``/``H``/``N``/``O``.  The complementary
half -- the descent all the way to the atom buckets ``{C, H, N, O}`` -- is the FORMULA-level v1 chain
(``build_decomposition``), which reaches those terminals, conserving every edge, at L2's ``HYPOTHESIZED``
floor.  Together they are the whole chain: the formula chain proves atoms->target is conservation-complete;
this structured chain grades the chemist-legible intermediate rungs, lifting above ``HYPOTHESIZED`` exactly
where sourced thermo/selectivity reaches (R5).  Neither half is faked into being the other.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..structure_descent import CappedScission
from .dag import DAGError, SynthesisDAG
from .step import ExperimentStep

__all__ = [
    "SynthesisAssemblyError",
    "find_scission",
    "steps_from_scissions",
    "assemble_synthesis",
]


class SynthesisAssemblyError(ValueError):
    """A chosen set of cleavages does not compose into an admissible synthesis DAG."""


_ELEMENT = re.compile(r"([A-Z][a-z]?)(\d*)")


def _formula_key(counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
    """A canonical, comparable key for an element-count mapping (drops zero counts, sorts)."""
    return tuple(sorted((el, n) for el, n in counts.items() if n))


def _spec_counts(spec: "Molecule | dict[str, int] | str") -> dict[str, int]:
    """Normalise a product spec -- a Molecule, an element-count dict, or a Hill string -- to counts."""
    if type(spec) is Molecule:
        return dict(spec.formula)
    if isinstance(spec, dict):
        return {str(el): int(n) for el, n in spec.items()}
    if isinstance(spec, str):
        counts: dict[str, int] = {}
        pos = 0
        for m in _ELEMENT.finditer(spec):
            if m.start() != pos:
                raise ValueError(f"malformed formula string {spec!r} near index {pos}")
            pos = m.end()
            el, digits = m.group(1), m.group(2)
            counts[el] = counts.get(el, 0) + (int(digits) if digits else 1)
        if pos != len(spec) or not counts:
            raise ValueError(f"malformed formula string {spec!r}")
        return counts
    raise TypeError("a product spec must be a Molecule, an element-count dict, or a Hill formula string")


def find_scission(
    scissions: Iterable[CappedScission],
    *,
    products: "Sequence[Molecule | dict[str, int] | str]",
) -> tuple[CappedScission, ...]:
    """Every cleavage in ``scissions`` whose PRODUCT set matches ``products`` by formula multiset.

    ``products`` is the multiset of product formulas you want (each given as a :class:`Molecule`, an
    element-count ``dict``, or a Hill string like ``"C2H4O2"``); a scission matches iff its derived
    products are exactly that multiset of formulas.  Returned sorted by digest for determinism -- several
    distinct valence-valid cleavages can share the same product formulas (different bonds cut to the same
    pieces), so this is a tuple, never a silent single pick; the caller chooses, or asserts a unique hit.
    """
    want = sorted(_formula_key(_spec_counts(p)) for p in products)
    hits = [
        cs
        for cs in scissions
        if sorted(_formula_key(dict(m.formula)) for m in cs.products) == want
    ]
    return tuple(sorted(hits, key=lambda cs: cs.digest))


def steps_from_scissions(
    scissions: Sequence[CappedScission],
    *,
    envelopes: Sequence[ConditionEnvelope | None] | None = None,
) -> tuple[ExperimentStep, ...]:
    """Turn each capped cleavage into its assembly (synthesis) step -- a descent read backwards.

    ``envelopes`` optionally supplies a sourced :class:`~smartchem.conditions.ConditionEnvelope` per
    scission (aligned by position; ``None`` -> unknown), so a rung whose conditions are attested can be
    graded ``KNOWN``.  Conservation is inherited from each :class:`CappedScission` and independently
    re-checked by the :class:`ExperimentStep` certificate.
    """
    scissions = tuple(scissions)
    if not scissions:
        raise SynthesisAssemblyError("a synthesis needs at least one cleavage")
    if any(type(cs) is not CappedScission for cs in scissions):
        raise TypeError("scissions must be CappedScission values")
    if envelopes is not None and len(envelopes) != len(scissions):
        raise SynthesisAssemblyError("envelopes, when given, must align one-to-one with scissions")
    envs = tuple(envelopes) if envelopes is not None else (None,) * len(scissions)
    return tuple(
        ExperimentStep.from_capped_scission(cs, envelope=env)
        for cs, env in zip(scissions, envs)
    )


def assemble_synthesis(
    scissions: Sequence[CappedScission],
    *,
    envelopes: Sequence[ConditionEnvelope | None] | None = None,
) -> SynthesisDAG:
    """Assemble chosen capped cleavages into ONE :class:`SynthesisDAG` -- the object L2 grades in one shot.

    Each cleavage is one assembly step (:func:`steps_from_scissions`); the steps are handed to
    :meth:`SynthesisDAG.of`, whose constructor enforces that they form a real synthesis -- distinct
    intermediate targets, acyclic, exactly one final target, no orphan branch.  A set of cleavages that do
    NOT form such a synthesis (two cleavages of the same intermediate, a gap where an intermediate is
    neither produced nor an external input, several unconsumed products) is refused here with a
    :class:`SynthesisAssemblyError` naming the structural fault -- never silently patched.

    Pass the result to :func:`~smartchem.experiment.classify.classify` for the single graded verdict over
    the whole chain (worst-step-dominated, a ``DEGENERATE`` handoff overriding to ``REFUTED``).
    """
    steps = steps_from_scissions(scissions, envelopes=envelopes)
    try:
        return SynthesisDAG.of(*steps)
    except DAGError as exc:
        raise SynthesisAssemblyError(
            f"the chosen cleavages do not compose into one admissible synthesis: {exc}"
        ) from exc
