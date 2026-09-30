"""0.9.5 verification core: the ONE load policy, the out-of-band receipt, the per-load context, the deterministic work
budget and the bounded process-level enumeration cache (barrier ``docs/research/V0_9_5_ARCHITECTURE_FREEZE.md``
§2-§5).  A pure module: it imports nothing from :mod:`smartchem.service` at module level (the service imports IT);
the service's own type names appear only under ``TYPE_CHECKING``.

The laws this module exists to hold:

1. **A budget never skips a check.**  :class:`VerificationBudget` counts deterministic work (never clocks).  A
   :class:`WorkMeter` checks BEFORE it records, and exhaustion raises :class:`VerificationBudgetExceeded` -- a
   refusal meaning "verification did not complete".  Nothing here clamps, degrades or omits the work it bounds; the
   only way to lift a limit is an explicit ``VerificationBudget(...)`` or :meth:`VerificationBudget.unlimited`.
2. **The receipt is out of band.**  :class:`VerificationReceipt` / :class:`VerifiedLoad` are issued only through this
   module's private factories (the loader calls them).  They cannot be produced from a payload, by
   ``dataclasses.replace``, by ``copy``/``deepcopy`` (which return the SAME object), by pickle, or by splatting JSON
   into the constructor.  Boundary, stated plainly: in-process code that reaches the private token (or uses
   ``object.__new__``) can forge one -- no weaker than today, where in-process code can build a
   ``CompilationResponse`` directly.  The threat closed is a receipt that travels and is believed.
3. **The enumeration cache key is the full argument VALUE plus the registry's content digest**:
   ``(registry.digest, target, tuple(reagents), budget)`` -- the literal target Molecule (atoms, bonds, charge, state),
   because emitted transforms embed literal atom order.  A provider rule/guard change moves ``registry.digest`` and
   misses structurally.  In-process code patching is invisible to ANY key, so :meth:`EnumerationCache.clear` is a
   required part of the design, not a convenience.
"""
from __future__ import annotations

import dataclasses
import functools
import hmac
import re
import sys
import threading
from collections import OrderedDict, namedtuple
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Iterator

# The declared, digest-bound transport modes, imported from their one home (0.9.5 I1) -- no longer a hand-kept mirror
# of the service's copy.  The private aliases keep this module's spelling; "the two agree" now holds by identity.
from .transport_integrity import TRANSPORT_CANONICAL_VERIFIED as _TRANSPORT_CANONICAL_VERIFIED
from .transport_integrity import TRANSPORT_THIN_ADVISORY as _TRANSPORT_THIN_ADVISORY
from .transport_integrity import _TRANSPORT_MODES

if TYPE_CHECKING:  # pragma: no cover - type names only; a runtime import would be circular
    from .category import Molecule
    from .service import CompilationResponse
    from .transform_provider import EnumeratedTransform, TransformProviderRegistry

__all__ = [
    "DigestRule",
    "ENUMERATION_CACHE",
    "EnumerationCache",
    "EnumerationCacheStats",
    "PinState",
    "SchemaGeneration",
    "SearchOutputTrust",
    "SignatureState",
    "UNPINNED",
    "Unpinned",
    "VerificationBudget",
    "VerificationBudgetExceeded",
    "VerificationContext",
    "VerificationPolicy",
    "VerificationReceipt",
    "VerifiedLoad",
    "WorkLedger",
    "WorkMeter",
    "cached_enumerate",
    "charge_canonical_work",
    "count_payload_nodes",
    "current_context",
    "enumeration_cache_key",
    "predicted_enumeration_work",
    "set_enumeration_cache_enabled",
    "work_transparent_cache",
]


# ---------------------------------------------------------------------------------------------------------------------
# UNPINNED -- "capability pin not supplied" (distinct from None, which PINS the question as NOT_REQUESTED)
# ---------------------------------------------------------------------------------------------------------------------

class Unpinned:
    """The type of :data:`UNPINNED`: the capability-question pin was NOT supplied.

    ``None`` is a pin (to NOT_REQUESTED: a consumer who asked no capability question refuses an answer that carries
    one); ``UNPINNED`` is the absence of a pin.  A singleton: construction, ``copy``, ``deepcopy`` and pickle all
    return the one instance, so ``is UNPINNED`` stays a sound test everywhere -- including after a policy round-trips
    through pickle.  (An ``object()`` sentinel would unpickle into a stranger and quietly become a pin.)
    """

    __slots__ = ()
    _instance: "Unpinned | None" = None

    def __new__(cls) -> "Unpinned":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNPINNED"

    def __reduce__(self) -> str:
        # a string reduce value names the module global: pickle and copy both resolve it back to the singleton.
        return "UNPINNED"


UNPINNED = Unpinned()


def _is_unpinned(value: object) -> bool:
    """``value`` means "no capability pin": :data:`UNPINNED`, or the service's legacy ``_NO_CAPABILITY_PIN`` sentinel.

    The service module is consulted through ``sys.modules`` only -- never imported -- because a caller that has not
    imported the service cannot be holding its sentinel.  (Once the adapter aliases ``_NO_CAPABILITY_PIN = UNPINNED``
    the second arm is the first arm; until then it keeps today's spelling mapping correctly.)
    """
    if value is UNPINNED:
        return True
    service = sys.modules.get(__name__.rpartition(".")[0] + ".service")
    return service is not None and value is getattr(service, "_NO_CAPABILITY_PIN", UNPINNED)


_HEX64 = re.compile(r"[0-9a-f]{64}")

#: Mirrors ``smartchem.transport_integrity._PRODUCER_KEY_MIN_BYTES`` (a test pins the two equal): the HMAC key floor.
_KEY_MIN_BYTES = 16


def _require_digest(owner: str, value: object) -> None:
    if type(value) is not str:
        raise TypeError(f"{owner} must be a str digest, got {type(value).__name__}; refused")
    if _HEX64.fullmatch(value) is None:
        raise ValueError(f"{owner} must be 64 lowercase hex characters (a sha256 hexdigest) -- {value!r} could never "
                         f"match one; refused")


def _require_bool(owner: str, value: object) -> None:
    if type(value) is not bool:
        raise TypeError(f"{owner} must be a bool, got {type(value).__name__}; refused")


# ---------------------------------------------------------------------------------------------------------------------
# The verification budget (§5): deterministic counters, charged BEFORE the work, never a clamp
# ---------------------------------------------------------------------------------------------------------------------

#: Every budget counter, in the barrier's order.
_BUDGET_COUNTERS = ("payload_nodes", "dossiers", "replay_steps", "steps_per_dossier", "enumeration_targets",
                    "work_per_target", "work_total", "reexecutions", "canonical_work")
#: Counters bounding ONE item (a dossier, a target) rather than a running total: checked via
#: :meth:`WorkMeter.check_item`, and the ledger records the MAXIMUM item seen, not a sum.
_PER_ITEM_COUNTERS = frozenset({"steps_per_dossier", "work_per_target"})
#: Counters RECORDED where the work happens but REFUSED later (0.9.5 S16): canonicalisation runs under code that
#: swallows ``ValueError``s (``requirements._resolved_name_key`` would even cache the swallow as "unresolved") and inside
#: the reaction-type oracle, which the barrier (§5) forbids a budget to interrupt.  So its overflow is STICKY: it is
#: raised by the next checked charge of any counter, and by :meth:`VerificationContext.activate` when the load ends --
#: never from inside a canonicalisation.  See :meth:`WorkMeter.charge_canonical`.
_DEFERRED_COUNTERS = frozenset({"canonical_work"})
_CUMULATIVE_COUNTERS = frozenset(_BUDGET_COUNTERS) - _PER_ITEM_COUNTERS - _DEFERRED_COUNTERS

#: Only :meth:`VerificationBudget.unlimited` holds this; it is the one licence for a ``None`` (= no limit) counter.
_UNLIMITED_LICENCE = object()

#: MEASURED 2026-09-29 by ``count_payload_nodes`` on honest canonical (thick) payloads (Wave-B ``rc-verification-core``):
#: the recipe payload -- ``build_recompile_request("isopentyl acetate", helper_reagents=("water", "acetic acid"),
#: stock_materials=("isopentyl alcohol",))`` + ``run_compilation`` + ``response_to_payload`` -- is 29,259 nodes
#: (234,431 bytes, 27 routes); the same + ``isopentyl_capability_fit_bench()`` is 43,838.  The honest MAXIMUM is the
#: 100-DAG convergent isopentyl payload (Lane B "c", ``ProcessBounds.quick()``, default max_results): 174,907 nodes.
#: 8 x 174,907 = 1,399,256 -> rounded up to 2**21 (12.0x that maximum, 71.7x the recipe).  Sizing to 8x the recipe
#: alone (2**18) would have left that honest DAG payload 1.5x headroom -- a false refusal waiting for a profile.
#: A node budget bounds decode work only; it never inspects what the nodes say.
_DEFAULT_PAYLOAD_NODES = 1 << 21

#: 0.9.5 S16 -- canonicalisation is verification work.  One unit = one candidate permutation evaluated (block path),
#: one atom re-refined at an individualisation search node (a node costs the molecule's atom count), or one node of
#: the Kekule placement search (``smiles._min_constitution_placement``) -- see ``Molecule.canonical``.  Each distinct
#: cached computation is charged its cold work ONCE per load (see the distinct-once section below), so the total is a
#: pure function of the payload.  MEASURED 2026-09-30 by ``experiments/v0_9_5_canonical_differential.py --service full
#: --perf`` on 105 honest loads -- the 22 frozen service cases and the verification-performance payloads (plain thick,
#: pinned + verified-admission thick, thin, pinned re-execution), each cold (every process cache cleared), warm and
#: after ENUMERATION_CACHE.clear(): the three agree on every load.  Maximum 3,054,611 (isopentyl_dag, pinned
#: re-execution); isopentyl re-execution 2,791,909, isopentyl plain thick 2,199,665.  8 x 3,054,611 -> 2**25 (11.0x).
#: (Charging every call instead measured 1,774,137,801 and forced 2**34: the thousands of cache hits an honest load
#: makes, each priced at its cold cost, admitted hours of cold hostile canonicalisation under the default.)
_DEFAULT_CANONICAL_WORK = 1 << 25


@dataclass(frozen=True)
class VerificationBudget:
    """Deterministic ceilings on the work ONE load may do (§5); ``None`` = no limit, licensed only by :meth:`unlimited`.

    The defaults are the barrier's conservative table: every frozen honest payload sits far below them, the C7-1
    hostile (``W = 473,200`` on one target) is refused on ``work_per_target``.  The budget bounds the ORDER of work,
    not a wall-clock number -- cold cost per work unit varies ~150x across honest targets (Lane B), so a clock budget
    would make the verdict machine-dependent.  Raising it is always explicit: ``VerificationBudget(...)`` with larger
    integers, or :meth:`unlimited`.
    """

    payload_nodes: "int | None" = _DEFAULT_PAYLOAD_NODES
    dossiers: "int | None" = 256
    replay_steps: "int | None" = 4096
    steps_per_dossier: "int | None" = 32
    enumeration_targets: "int | None" = 128
    work_per_target: "int | None" = 32_768
    work_total: "int | None" = 131_072
    reexecutions: "int | None" = 1
    canonical_work: "int | None" = _DEFAULT_CANONICAL_WORK
    _licence: InitVar[object] = None

    def __post_init__(self, _licence: object) -> None:
        for name in _BUDGET_COUNTERS:
            limit = getattr(self, name)
            if limit is None:
                if _licence is _UNLIMITED_LICENCE:
                    continue
                raise ValueError(f"VerificationBudget.{name}=None would lift the limit implicitly; an unbounded "
                                 f"budget is only VerificationBudget.unlimited() (explicit), otherwise pass a positive "
                                 f"int; refused")
            if type(limit) is not int:
                raise TypeError(f"VerificationBudget.{name} must be a positive int, got {type(limit).__name__}; "
                                f"refused")
            if limit <= 0:
                raise ValueError(f"VerificationBudget.{name} must be a positive int, got {limit}; a zero or negative "
                                 f"limit refuses every payload, it bounds nothing; refused")

    @classmethod
    def default(cls) -> "VerificationBudget":
        """The one conservative default every caller gets unless it raises the budget explicitly."""
        return cls()

    @classmethod
    def unlimited(cls) -> "VerificationBudget":
        """Every counter ``None``: no limit.  The ONLY route to an unbounded budget -- say it out loud or do not get it."""
        return cls(**dict.fromkeys(_BUDGET_COUNTERS), _licence=_UNLIMITED_LICENCE)


class VerificationBudgetExceeded(ValueError):
    """A load's deterministic work would exceed its :class:`VerificationBudget`: verification did NOT complete.

    A ``ValueError`` (the loader's refusal class, so ``pytest.raises(ValueError)`` still reads a refusal) that is
    deliberately NOT a ``DAGError``/``CeilingError`` -- ``service._route_shopping_requirements`` swallows those two,
    and a swallowed budget refusal would be a skipped check wearing a pass.  Callers on a broad ``except Exception``
    path must re-raise it first.
    """

    def __init__(self, counter: str, limit: int, consumed: int) -> None:
        self.counter = counter
        self.limit = limit
        self.consumed = consumed
        super().__init__(
            f"verification budget exceeded: {counter} consumed {consumed} > limit {limit}; verification did not "
            f"complete; raise the budget explicitly (VerificationBudget(...)) only if you trust this payload's size")

    def __reduce__(self):
        # the default BaseException reduce replays ``args`` (the message) into __init__ and would fail to unpickle.
        return (type(self), (self.counter, self.limit, self.consumed))


@dataclass(frozen=True)
class WorkLedger:
    """The frozen final counters of one load's :class:`WorkMeter`, with the budget they were charged against.

    Cumulative counters are totals; ``steps_per_dossier`` and ``work_per_target`` are the MAXIMUM single item seen.
    """

    budget: VerificationBudget
    payload_nodes: int = 0
    dossiers: int = 0
    replay_steps: int = 0
    steps_per_dossier: int = 0
    enumeration_targets: int = 0
    work_per_target: int = 0
    work_total: int = 0
    reexecutions: int = 0
    canonical_work: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.budget, VerificationBudget):
            raise TypeError(f"WorkLedger.budget must be a VerificationBudget, got {type(self.budget).__name__}; refused")
        for name in _BUDGET_COUNTERS:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"WorkLedger.{name} must be a non-negative int, got {value!r}; refused")

    def within(self, budget: VerificationBudget) -> bool:
        """Would this much work have completed under ``budget``?  (Every counter at or under its limit.)"""
        if not isinstance(budget, VerificationBudget):
            raise TypeError(f"within() takes a VerificationBudget, got {type(budget).__name__}; refused")
        return all(getattr(budget, n) is None or getattr(self, n) <= getattr(budget, n) for n in _BUDGET_COUNTERS)


def _require_amount(amount: object) -> int:
    if type(amount) is not int or amount < 0:
        raise ValueError(f"a work amount must be a non-negative int, got {amount!r}; refused")
    return amount


def count_payload_nodes(payload: object, *, stop_after: "int | None" = None) -> int:
    """The number of JSON value nodes in ``payload`` (every dict, list/tuple and scalar counts 1; keys ride their value).

    Iterative (no recursion, so nesting depth cannot exhaust the stack) and early-stopping: with ``stop_after`` the
    walk returns as soon as the count exceeds it (the returned count is then a lower bound, > ``stop_after``), so an
    oversized payload is refused without being walked in full.  A shared sub-object is counted once per occurrence
    (the decoder walks it once per occurrence too); a CYCLIC payload -- impossible from JSON, possible from an
    in-process dict -- is refused rather than walked forever.
    """
    count = 0
    on_path: set[int] = set()
    stack: list[tuple[object, bool]] = [(payload, False)]
    while stack:
        node, leaving = stack.pop()
        if leaving:
            on_path.discard(id(node))
            continue
        count += 1
        if stop_after is not None and count > stop_after:
            return count
        if isinstance(node, dict):
            children = node.values()
        elif isinstance(node, (list, tuple)):
            children = node
        else:
            continue
        if id(node) in on_path:
            raise ValueError("the payload is cyclic (a container contains itself); refused")
        if stop_after is not None and count + len(children) > stop_after:
            # every child is at least one more node: the limit is already passed, so do not even queue them
            # (a flat million-element list would otherwise be pushed in full just to be refused).
            return count + len(children)
        on_path.add(id(node))
        stack.append((node, True))
        stack.extend((child, False) for child in children)
    return count


class WorkMeter:
    """The mutable per-load budget meter.  Every charge is checked BEFORE it is recorded.

    A charge that would take a counter past its limit raises :class:`VerificationBudgetExceeded` and records nothing;
    the composite charges (:meth:`charge_dossier`, :meth:`charge_enumeration`) check every counter they touch before
    recording any of them, so a refused charge never leaves a half-booked meter.
    """

    __slots__ = ("budget", "_consumed", "_exhausted")

    def __init__(self, budget: VerificationBudget) -> None:
        if not isinstance(budget, VerificationBudget):
            raise TypeError(f"a WorkMeter needs a VerificationBudget, got {type(budget).__name__}; refused")
        self.budget = budget
        self._consumed = dict.fromkeys(_BUDGET_COUNTERS, 0)
        self._exhausted: "tuple[str, int, int] | None" = None   # (counter, limit, consumed) at the first overflow

    def _gate(self, counter: str, would_be: int) -> None:
        self.raise_if_exhausted()                    # a deferred overflow refuses at the first checked charge after it
        limit = getattr(self.budget, counter)
        if limit is not None and would_be > limit:
            raise VerificationBudgetExceeded(counter, limit, would_be)

    def _cumulative(self, counter: str) -> str:
        if counter not in _CUMULATIVE_COUNTERS:
            hint = (" (a per-item counter: use check_item)" if counter in _PER_ITEM_COUNTERS
                    else " (a deferred counter: use charge_canonical)" if counter in _DEFERRED_COUNTERS else "")
            raise ValueError(f"unknown cumulative budget counter {counter!r}{hint}; refused")
        return counter

    @property
    def exhausted(self) -> bool:
        """Has a deferred counter overflowed?  Once true it stays true: the load cannot complete."""
        return self._exhausted is not None

    def raise_if_exhausted(self) -> None:
        """Raise the deferred overflow, if any -- a fresh :class:`VerificationBudgetExceeded` each time, reporting what is
        consumed NOW.  Not the first overflowing charge: a cold miss charges node by node where a warm hit charges its
        closure at once, so only the totals at the checked points between calls are the same cold and warm."""
        if self._exhausted is not None:
            counter, limit, _first = self._exhausted
            raise VerificationBudgetExceeded(counter, limit, self._consumed[counter])

    def charge_canonical(self, amount: int) -> None:
        """Record ``amount`` canonicalisation work units, BEFORE the work they bound -- and never raise here (S16).

        Canonicalisation runs beneath ``except ValueError`` handlers this module does not own (one of them memoises
        the swallow process-wide) and inside the reaction-type oracle; a refusal thrown from in there would be
        swallowed, demoted or cached, i.e. a skipped check.  So an overflow is recorded as STICKY exhaustion instead:
        every later checked charge raises it, and so does :meth:`VerificationContext.activate` at the end of the load
        whatever happened in between.  Refusal is therefore certain and deterministic; the work between the overflow
        and the next checked charge is bounded by the canonicaliser's own node ceiling per call, not by this meter.
        """
        amount = _require_amount(amount)
        would_be = self._consumed["canonical_work"] + amount
        self._consumed["canonical_work"] = would_be
        limit = self.budget.canonical_work
        if self._exhausted is None and limit is not None and would_be > limit:
            self._exhausted = ("canonical_work", limit, would_be)

    def _item(self, counter: str) -> str:
        if counter not in _PER_ITEM_COUNTERS:
            raise ValueError(f"unknown per-item budget counter {counter!r} (per-item: "
                             f"{sorted(_PER_ITEM_COUNTERS)}); refused")
        return counter

    def consumed(self, counter: str) -> int:
        if counter not in self._consumed:
            raise ValueError(f"unknown budget counter {counter!r}; refused")
        return self._consumed[counter]

    def charge(self, counter: str, amount: int = 1) -> None:
        """Add ``amount`` to the cumulative ``counter`` -- refused, recording nothing, if that would pass the limit."""
        self._cumulative(counter)
        amount = _require_amount(amount)
        would_be = self._consumed[counter] + amount
        self._gate(counter, would_be)
        self._consumed[counter] = would_be

    def check_item(self, counter: str, amount: int) -> None:
        """Check ONE item (a dossier's steps, a target's work) against the per-item ``counter``; record the maximum."""
        self._item(counter)
        amount = _require_amount(amount)
        self._gate(counter, amount)
        self._consumed[counter] = max(self._consumed[counter], amount)

    def charge_dossier(self, steps: int) -> None:
        """One reconstructed dossier of ``steps`` replay steps: per-dossier cap, then dossiers + 1, replay_steps + steps."""
        steps = _require_amount(steps)
        self._gate("steps_per_dossier", steps)
        self._gate("dossiers", self._consumed["dossiers"] + 1)
        self._gate("replay_steps", self._consumed["replay_steps"] + steps)
        self._consumed["steps_per_dossier"] = max(self._consumed["steps_per_dossier"], steps)
        self._consumed["dossiers"] += 1
        self._consumed["replay_steps"] += steps

    def charge_enumeration(self, work: int) -> None:
        """One distinct enumeration target of predicted work ``W``: per-target cap, then targets + 1, work_total + W."""
        work = _require_amount(work)
        self._gate("work_per_target", work)
        self._gate("enumeration_targets", self._consumed["enumeration_targets"] + 1)
        self._gate("work_total", self._consumed["work_total"] + work)
        self._consumed["work_per_target"] = max(self._consumed["work_per_target"], work)
        self._consumed["enumeration_targets"] += 1
        self._consumed["work_total"] += work

    def charge_payload_nodes(self, payload: object) -> int:
        """Walk ``payload`` (stopping as soon as the node limit is passed) and charge its node count; returns it."""
        limit = self.budget.payload_nodes
        remaining = None if limit is None else max(limit - self._consumed["payload_nodes"], 0)
        nodes = count_payload_nodes(payload, stop_after=remaining)
        self.charge("payload_nodes", nodes)
        return nodes

    def snapshot(self) -> WorkLedger:
        return WorkLedger(budget=self.budget, **self._consumed)


def predicted_enumeration_work(target: "Molecule", reagents) -> "tuple[int, int]":
    """``(E, W)`` for one D29.1 enumeration, computable BEFORE enumerating (Lane B, exact for capped scission).

    ``E = |bonds(target)| x max(1, sum(|bonds(r)| for each DISTINCT reagent r))`` and ``W = E x |bonds(target)|``, where
    ``bonds`` is ``Molecule.bonds`` INCLUDING bonds to hydrogen (methyl acetate: 10, water: 2 -> E = 20, W = 200).
    Distinct = by Molecule value: a duplicated reagent changes nothing the enumeration does (Lane B, measured), so it
    must not change the charge either.  Measured work = 3E on 40/40 target classes (the 3 perfect matchings of four
    open ends at ``max_reactant_cuts=1``).

    **The floor (0.9.5 S16, Wave C4 conjecture 3):** the reagent factor is ``max(1, sum(...))``, never zero.  With no
    helper reagents the plain product was 0 -- yet the certified-route algebra also carries reagentless providers
    (Diels-Alder) that enumerate matches over the target alone, so "no reagents" never meant "no work".  An empty (or
    bondless) reagent pool now charges the target's own ``E = |bonds(target)|``, ``W = |bonds(target)|**2``; every
    honest value with a bonded reagent is unchanged (the sum is already >= 1).  A bondless target still charges 0 --
    it has nothing to cut or match.
    """
    target_bonds = len(target.bonds)
    e = target_bonds * max(1, sum(len(r.bonds) for r in set(reagents)))
    return e, e * target_bonds


# ---------------------------------------------------------------------------------------------------------------------
# VerificationPolicy (§2): the ONE policy; named constructors are dataclasses.replace sugar over it
# ---------------------------------------------------------------------------------------------------------------------

#: Today's ``response_from_payload`` / ``deserialize_response`` trust kwargs (service.py:5927), in signature order.
_LEGACY_KWARGS = ("verification_key", "require_signature", "require_verified_admission", "expected_request_digest",
                  "expected_capability_question_digest", "require_reexecution")


@dataclass(frozen=True)
class VerificationPolicy:
    """What a consumer requires of a load.  Defaults reproduce today's ``response_from_payload`` kwargs EXACTLY, plus
    S1 (``require_canonical_transport``) off and S2 (``budget``) at the conservative default.

    Construction refuses what could never succeed: ``require_signature`` without a key (today's exact message), a key
    that is not ``bytes`` or is shorter than 16 bytes (a deliberate tightening -- a 1-byte HMAC key authenticates
    nothing), a pin that is not 64 lowercase hex (it could only ever mismatch), a non-bool flag, a non-budget budget.
    """

    verification_key: "bytes | None" = field(default=None, repr=False)
    require_signature: bool = False
    require_verified_admission: bool = False
    expected_request_digest: "str | None" = None
    expected_capability_question_digest: "str | None | Unpinned" = UNPINNED   # None == pinned to NOT_REQUESTED
    require_reexecution: bool = False
    require_canonical_transport: bool = False     # S1
    budget: VerificationBudget = VerificationBudget.default()   # S2

    def __post_init__(self) -> None:
        for flag in ("require_signature", "require_verified_admission", "require_reexecution",
                     "require_canonical_transport"):
            _require_bool(f"VerificationPolicy.{flag}", getattr(self, flag))
        key = self.verification_key
        if key is not None:
            if type(key) is not bytes:
                raise TypeError(f"VerificationPolicy.verification_key must be bytes, got {type(key).__name__}; "
                                f"refused")
            if len(key) < _KEY_MIN_BYTES:
                raise ValueError(f"VerificationPolicy.verification_key must be at least {_KEY_MIN_BYTES} bytes, got "
                                 f"{len(key)}; refused")
        if self.require_signature and key is None:
            raise ValueError("require_signature needs a verification_key")
        if self.expected_request_digest is not None:
            _require_digest("VerificationPolicy.expected_request_digest", self.expected_request_digest)
        pin = self.expected_capability_question_digest
        if pin is not UNPINNED and pin is not None:
            _require_digest("VerificationPolicy.expected_capability_question_digest", pin)
        if not isinstance(self.budget, VerificationBudget):
            raise TypeError(f"VerificationPolicy.budget must be a VerificationBudget, got "
                            f"{type(self.budget).__name__}; refused")

    @classmethod
    def advisory(cls) -> "VerificationPolicy":
        """Today's bare load: nothing beyond the loader's unconditional checks (and the default budget)."""
        return cls()

    @classmethod
    def canonical(cls) -> "VerificationPolicy":
        """Canonical transport (THIN and legacy v0.8 refused at dispatch) + verified admission."""
        return dataclasses.replace(cls(), require_canonical_transport=True, require_verified_admission=True)

    @classmethod
    def pinned(cls, request_digest: str, *, question_digest: "str | None | Unpinned" = UNPINNED
               ) -> "VerificationPolicy":
        """Pin the request (and, optionally, the capability question -- ``None`` pins it to NOT_REQUESTED)."""
        return dataclasses.replace(cls(), expected_request_digest=request_digest,
                                   expected_capability_question_digest=question_digest)

    @classmethod
    def authenticated(cls, key: bytes) -> "VerificationPolicy":
        """Require a producer signature verifying under ``key``."""
        return dataclasses.replace(cls(), verification_key=key, require_signature=True)

    @classmethod
    def paranoid(cls, request_digest: str, key: bytes, *, question_digest: "str | None | Unpinned" = UNPINNED
                 ) -> "VerificationPolicy":
        """canonical + pinned + authenticated + re-execution: everything the loader can check, checked."""
        return dataclasses.replace(cls.canonical(), expected_request_digest=request_digest,
                                   expected_capability_question_digest=question_digest, verification_key=key,
                                   require_signature=True, require_reexecution=True)

    @classmethod
    def from_legacy_kwargs(cls, **kwargs) -> "VerificationPolicy":
        """The compat shim: today's ``response_from_payload`` trust kwargs -> the equivalent policy.

        Accepts exactly those six names (an unknown one is a ``TypeError``, as a misspelt kwarg is today); the
        service's ``_NO_CAPABILITY_PIN`` sentinel maps to :data:`UNPINNED`.  S1 stays off, S2 takes the default.
        """
        unknown = sorted(set(kwargs) - set(_LEGACY_KWARGS))
        if unknown:
            raise TypeError(f"from_legacy_kwargs() got unexpected keyword argument(s) {unknown}; the legacy trust "
                            f"kwargs are {list(_LEGACY_KWARGS)}")
        if "expected_capability_question_digest" in kwargs and _is_unpinned(
                kwargs["expected_capability_question_digest"]):
            kwargs["expected_capability_question_digest"] = UNPINNED
        return cls(**kwargs)


# ---------------------------------------------------------------------------------------------------------------------
# VerificationReceipt / VerifiedLoad (§3): facets, no strength scalar; issued by the loader only
# ---------------------------------------------------------------------------------------------------------------------

class SchemaGeneration(str, Enum):
    """Which wire generation the payload was read as."""

    CURRENT = "CURRENT"
    LEGACY_V08 = "LEGACY_V08"


class DigestRule(str, Enum):
    """Which result-digest rule bound the payload: the whole-body rule, or the frozen v0.8 rule (body NOT bound)."""

    WHOLE_BODY = "WHOLE_BODY"
    FROZEN_V08 = "FROZEN_V08"


class PinState(str, Enum):
    """Whether a consumer pin was supplied (and therefore checked -- a supplied pin that fails refuses the load)."""

    CHECKED = "CHECKED"
    NOT_PINNED = "NOT_PINNED"


class SignatureState(str, Enum):
    """The producer signature: VERIFIED under the policy's key; NOT_REQUIRED_ABSENT (key given, payload unsigned,
    signature not required); NOT_CHECKED (no key -- an unsigned or signed payload alike stays producer-declared)."""

    VERIFIED = "VERIFIED"
    NOT_REQUIRED_ABSENT = "NOT_REQUIRED_ABSENT"
    NOT_CHECKED = "NOT_CHECKED"


class SearchOutputTrust(str, Enum):
    """How far the SEARCH output (outcome, IR search status...) is trusted -- the D25.3 boundary, S11.

    ADVISORY unless the loader re-executed the request (REEXECUTED: re-derived here, key-free, and the stronger
    ground when both hold) or the signature VERIFIED (AUTHENTICATED: attested by the key holder).
    """

    ADVISORY = "ADVISORY"
    REEXECUTED = "REEXECUTED"
    AUTHENTICATED = "AUTHENTICATED"


#: The module-private issuing tokens.  Holding one IS the licence to mint; nothing outside this module should.
_RECEIPT_TOKEN = object()
_VERIFIED_LOAD_TOKEN = object()

_LOADER_ONLY = ("is issued only by the loader (smartchem.service.load_response); it cannot be constructed directly, "
                "replaced, pickled or read from a payload; refused")


def _search_output_trust(reexecuted: bool, signature: SignatureState) -> SearchOutputTrust:
    if reexecuted:
        return SearchOutputTrust.REEXECUTED
    if signature is SignatureState.VERIFIED:
        return SearchOutputTrust.AUTHENTICATED
    return SearchOutputTrust.ADVISORY


@dataclass(frozen=True)
class VerificationReceipt:
    """What ONE load actually established, facet by facet -- out of band, never on the wire, never on the response.

    Every facet is recorded by the loader; ``__post_init__`` refuses a receipt whose facets contradict each other or
    the policy it claims to have been issued under (a loader-bug guard: e.g. a signature VERIFIED with no key, a pin
    CHECKED that was never supplied, work beyond the budget that supposedly bounded it).  ``satisfies(policy)`` lets a
    downstream holder assert its own requirement without reloading.
    """

    schema_generation: SchemaGeneration
    transport_mode: str
    digest_rule: DigestRule
    request_pin: PinState
    capability_pin: PinState
    signature: SignatureState
    verified_admission: bool
    replay_rederived_routes: int
    replay_rederived_dags: int
    reexecuted: bool
    legacy_migrated: bool
    search_output: SearchOutputTrust
    work: WorkLedger
    policy: VerificationPolicy
    response_result_digest: str
    _token: InitVar[object] = None

    def __post_init__(self, _token: object) -> None:
        if _token is not _RECEIPT_TOKEN:
            raise TypeError(f"VerificationReceipt {_LOADER_ONLY}")
        for name, kind in (("schema_generation", SchemaGeneration), ("digest_rule", DigestRule),
                           ("request_pin", PinState), ("capability_pin", PinState), ("signature", SignatureState),
                           ("search_output", SearchOutputTrust), ("work", WorkLedger),
                           ("policy", VerificationPolicy)):
            if not isinstance(getattr(self, name), kind):
                raise TypeError(f"VerificationReceipt.{name} must be a {kind.__name__}, got "
                                f"{type(getattr(self, name)).__name__}; refused")
        for flag in ("verified_admission", "reexecuted", "legacy_migrated"):
            _require_bool(f"VerificationReceipt.{flag}", getattr(self, flag))
        for count in ("replay_rederived_routes", "replay_rederived_dags"):
            value = getattr(self, count)
            if type(value) is not int or value < 0:
                raise ValueError(f"VerificationReceipt.{count} must be a non-negative int, got {value!r}; refused")
        if self.transport_mode not in _TRANSPORT_MODES:
            raise ValueError(f"VerificationReceipt.transport_mode must be one of {sorted(_TRANSPORT_MODES)}, got "
                             f"{self.transport_mode!r}; refused")
        _require_digest("VerificationReceipt.response_result_digest", self.response_result_digest)
        self._check_coherence()

    def _check_coherence(self) -> None:
        policy = self.policy
        legacy = self.schema_generation is SchemaGeneration.LEGACY_V08
        problems = []
        if (self.digest_rule is DigestRule.FROZEN_V08) != legacy:
            problems.append(f"digest_rule {self.digest_rule.value} does not match {self.schema_generation.value}")
        if self.legacy_migrated != legacy:
            problems.append(f"legacy_migrated={self.legacy_migrated} does not match {self.schema_generation.value}")
        if self.search_output is not _search_output_trust(self.reexecuted, self.signature):
            problems.append(f"search_output {self.search_output.value} is not what reexecuted={self.reexecuted} and "
                            f"signature {self.signature.value} establish")
        if policy.verification_key is None and self.signature is not SignatureState.NOT_CHECKED:
            problems.append(f"signature {self.signature.value} with no verification_key")
        if policy.verification_key is not None and self.signature is SignatureState.NOT_CHECKED:
            problems.append("signature NOT_CHECKED although a verification_key was supplied")
        if policy.require_signature and self.signature is not SignatureState.VERIFIED:
            problems.append(f"signature {self.signature.value} under require_signature")
        if (self.request_pin is PinState.CHECKED) != (policy.expected_request_digest is not None):
            problems.append(f"request_pin {self.request_pin.value} does not match the policy's pin")
        if (self.capability_pin is PinState.CHECKED) != (policy.expected_capability_question_digest is not UNPINNED):
            problems.append(f"capability_pin {self.capability_pin.value} does not match the policy's pin")
        if self.reexecuted != policy.require_reexecution:
            problems.append(f"reexecuted={self.reexecuted} under require_reexecution={policy.require_reexecution}")
        if self.verified_admission != policy.require_verified_admission:
            problems.append(f"verified_admission={self.verified_admission} under "
                            f"require_verified_admission={policy.require_verified_admission}")
        if policy.require_canonical_transport and (self.transport_mode != _TRANSPORT_CANONICAL_VERIFIED or legacy):
            problems.append(f"a {self.schema_generation.value} {self.transport_mode} load under "
                            f"require_canonical_transport")
        if self.transport_mode == _TRANSPORT_THIN_ADVISORY and (self.replay_rederived_routes
                                                                or self.replay_rederived_dags):
            problems.append("replayed dossiers counted on a THIN_ADVISORY load (thin carries no replay)")
        if self.work.budget != policy.budget:
            problems.append("the work ledger was charged against a different budget than the policy's")
        elif not self.work.within(policy.budget):
            problems.append("the work ledger exceeds the budget that bounded it (a completed load never does)")
        if problems:
            raise ValueError("incoherent VerificationReceipt: " + "; ".join(problems) + "; refused")

    def __reduce__(self):
        raise TypeError(f"VerificationReceipt {_LOADER_ONLY}")

    def __copy__(self) -> "VerificationReceipt":
        return self

    def __deepcopy__(self, memo) -> "VerificationReceipt":
        return self

    def satisfies(self, policy: VerificationPolicy) -> bool:
        """Does what this load established meet every requirement of ``policy``?  Fail-closed facet by facet.

        A key in ``policy`` demands the SAME key was applied here (compared in constant time); a pin demands the
        same pin was checked; the work must fit ``policy.budget`` (a stricter budget would have refused a heavier
        load).  ``receipt.satisfies(receipt.policy)`` is always True.
        """
        if not isinstance(policy, VerificationPolicy):
            raise TypeError(f"satisfies() takes a VerificationPolicy, got {type(policy).__name__}; refused")
        mine = self.policy
        if policy.verification_key is not None and (
                mine.verification_key is None
                or not hmac.compare_digest(mine.verification_key, policy.verification_key)):
            return False
        if policy.require_signature and self.signature is not SignatureState.VERIFIED:
            return False
        if policy.require_verified_admission and not self.verified_admission:
            return False
        if policy.expected_request_digest is not None and (
                self.request_pin is not PinState.CHECKED
                or mine.expected_request_digest != policy.expected_request_digest):
            return False
        if policy.expected_capability_question_digest is not UNPINNED and (
                self.capability_pin is not PinState.CHECKED
                or mine.expected_capability_question_digest != policy.expected_capability_question_digest):
            return False
        if policy.require_reexecution and not self.reexecuted:
            return False
        if policy.require_canonical_transport and (
                self.transport_mode != _TRANSPORT_CANONICAL_VERIFIED
                or self.schema_generation is not SchemaGeneration.CURRENT):
            return False
        return self.work.within(policy.budget)


def _issue_receipt(*, schema_generation: SchemaGeneration, transport_mode: str, digest_rule: DigestRule,
                   request_pin: PinState, capability_pin: PinState, signature: SignatureState,
                   verified_admission: bool, replay_rederived_routes: int, replay_rederived_dags: int,
                   reexecuted: bool, legacy_migrated: bool, work: WorkLedger, policy: VerificationPolicy,
                   response_result_digest: str) -> VerificationReceipt:
    """The ONLY constructor path for a :class:`VerificationReceipt` (the loader's).  ``search_output`` is derived
    here from ``reexecuted`` and ``signature`` -- it is a function of them, so the loader is not asked to restate it."""
    return VerificationReceipt(
        schema_generation=schema_generation, transport_mode=transport_mode, digest_rule=digest_rule,
        request_pin=request_pin, capability_pin=capability_pin, signature=signature,
        verified_admission=verified_admission, replay_rederived_routes=replay_rederived_routes,
        replay_rederived_dags=replay_rederived_dags, reexecuted=reexecuted, legacy_migrated=legacy_migrated,
        search_output=_search_output_trust(reexecuted, signature), work=work, policy=policy,
        response_result_digest=response_result_digest, _token=_RECEIPT_TOKEN)


@dataclass(frozen=True)
class VerifiedLoad:
    """A loaded response paired with the receipt of the load that produced it.

    ``__post_init__`` refuses a receipt whose ``response_result_digest`` is not this response's ``result_digest``:
    a receipt earned by another load cannot be stapled to this one.  Same unforgeability discipline as the receipt.
    """

    response: "CompilationResponse"
    receipt: VerificationReceipt
    _token: InitVar[object] = None

    def __post_init__(self, _token: object) -> None:
        if _token is not _VERIFIED_LOAD_TOKEN:
            raise TypeError(f"VerifiedLoad {_LOADER_ONLY}")
        from .service import CompilationResponse   # call-time only: the service imports this module at load time

        if not isinstance(self.response, CompilationResponse):
            raise TypeError(f"VerifiedLoad.response must be a CompilationResponse, got "
                            f"{type(self.response).__name__}; refused")
        if not isinstance(self.receipt, VerificationReceipt):
            raise TypeError(f"VerifiedLoad.receipt must be a VerificationReceipt, got "
                            f"{type(self.receipt).__name__}; refused")
        actual = self.response.result_digest
        if self.receipt.response_result_digest != actual:
            raise ValueError(f"the receipt describes response {self.receipt.response_result_digest[:12]}, not this "
                             f"response {actual[:12]}; a receipt from another load cannot be paired; refused")

    def __reduce__(self):
        raise TypeError(f"VerifiedLoad {_LOADER_ONLY}")

    def __copy__(self) -> "VerifiedLoad":
        return self

    def __deepcopy__(self, memo) -> "VerifiedLoad":
        return self


def _issue_verified_load(response: "CompilationResponse", receipt: VerificationReceipt) -> VerifiedLoad:
    """The ONLY constructor path for a :class:`VerifiedLoad` (the loader's)."""
    return VerifiedLoad(response=response, receipt=receipt, _token=_VERIFIED_LOAD_TOKEN)


# ---------------------------------------------------------------------------------------------------------------------
# VerificationContext (§4): one per load, installed for that load only
# ---------------------------------------------------------------------------------------------------------------------

_ACTIVE_CONTEXT: "ContextVar[VerificationContext | None]" = ContextVar("smartchem_verification_context", default=None)


class VerificationContext:
    """Per-load state: the policy, the :class:`WorkMeter`, and a memo of per-payload-object derivations.

    Created once by the loader, installed with :meth:`activate` for the duration of that load, discarded after.
    Outside a load there is no context (:func:`current_context` is ``None``) and every function computes directly.
    """

    __slots__ = ("policy", "meter", "_memo", "_canonical_memo", "_charged")

    def __init__(self, policy: VerificationPolicy) -> None:
        if not isinstance(policy, VerificationPolicy):
            raise TypeError(f"a VerificationContext needs a VerificationPolicy, got {type(policy).__name__}; refused")
        self.policy = policy
        self.meter = WorkMeter(policy.budget)
        self._memo: "dict[tuple[str, int], tuple[object, object]]" = {}
        # S16 distinct-once-per-load: node -> (value, closure) for every cached computation this load holds, and the
        # nodes whose own work this load has paid (a superset: a replayed closure pays nodes whose value is not held)
        self._canonical_memo: "dict[object, tuple[object, dict]]" = {}
        self._charged: "set[object]" = set()

    def _replay(self, closure: "dict[object, int]") -> None:
        """Charge a cache hit: every node of its closure this load has not yet paid for, its own work, once."""
        charged = self._charged
        for node, work in closure.items():
            if node not in charged:
                charged.add(node)
                if work:
                    self.meter.charge_canonical(work)

    def memo(self, kind: str, payload_obj: object, build: "Callable[[object], object]") -> object:
        """``build(payload_obj)`` once per ``(kind, payload_obj)`` for this load, keyed by the payload OBJECT's id.

        The memo holds a strong reference to ``payload_obj``, so its id cannot be recycled for another object while
        the context lives -- the key stays the object it was computed from.  A ``build`` that raises memoises nothing.
        """
        if type(kind) is not str or not kind:
            raise TypeError(f"memo kind must be a non-empty str, got {kind!r}; refused")
        key = (kind, id(payload_obj))
        hit = self._memo.get(key)
        if hit is not None:
            held, value = hit
            if held is not payload_obj:  # pragma: no cover - impossible while the strong reference is held
                raise RuntimeError("verification memo id collision (the held payload object was replaced); refused")
            return value
        value = build(payload_obj)
        self._memo[key] = (payload_obj, value)
        return value

    def reconstructed(self, kind: str) -> int:
        """How many distinct payload objects of ``kind`` this load actually built (the receipt's re-derivation counts:
        a canonical payload whose dossiers were never reconstructed is canonical in name only)."""
        return sum(1 for memo_kind, _id in self._memo if memo_kind == kind)

    @contextmanager
    def activate(self) -> "Iterator[VerificationContext]":
        """Install this context for the enclosed block; the previously active one (or none) is restored on exit.

        S16: a deferred budget overflow (canonical work) recorded anywhere in the block is raised HERE as the block
        ends -- replacing whatever the block raised, if anything, since a load that ran out of budget did not complete
        whatever else went wrong after -- so no handler inside the load can turn exhaustion into an answer.
        """
        token = _ACTIVE_CONTEXT.set(self)
        try:
            yield self
        except Exception as exc:
            if self.meter.exhausted and not isinstance(exc, VerificationBudgetExceeded):
                try:
                    self.meter.raise_if_exhausted()
                except VerificationBudgetExceeded as refusal:
                    raise refusal from exc
            raise
        finally:
            _ACTIVE_CONTEXT.reset(token)
        self.meter.raise_if_exhausted()


def current_context() -> "VerificationContext | None":
    """The context of the load in progress on THIS thread/task, or ``None`` outside a load."""
    return _ACTIVE_CONTEXT.get()


# ---------------------------------------------------------------------------------------------------------------------
# Canonicalisation work (0.9.5 S16): each distinct computation charged ONCE per load, replayed through every cache
# ---------------------------------------------------------------------------------------------------------------------
# ``Molecule.canonical()`` runs everywhere -- decode, the request re-derivation, every replayed molecule, every fragment
# an enumeration cuts -- and it used to run uncharged: a front-door hang (tetra-tert-butylmethane) was also a verifier
# hole.  Two laws make the charge honest:
#
# * DISTINCT ONCE PER LOAD.  A cached computation -- ``canonical()``, ``resonance_canonical``, the structure-key and
#   name-key caches, the enumeration cache -- is a NODE, keyed exactly as its process cache keys it.  Within one load a
#   node is charged its OWN cold work (what it charges directly, nested cached calls excluded) the first time the load
#   touches it, and 0 after.  Charging every call instead priced the thousands of cache HITS an honest load makes at
#   their cold cost: the honest re-execution maximum came to 1.77e9 units, and a default of 8x that admitted hours of
#   cold, hostile canonicalisation.  A per-load memo backs the law: within a load a node's result is never recomputed,
#   so a process-LRU eviction mid-load cannot buy an uncharged recomputation.
# * WORK-TRANSPARENT CACHES.  A process-cache hit elides the calls beneath it, so each entry keeps its CLOSURE -- every
#   distinct node its cold computation touched, with that node's own work -- and a hit charges the closure's nodes this
#   load has not paid for yet.  The charge is therefore a function of the set of nodes the load touches, which is a
#   function of the payload: identical cold, warm, or after any cache was cleared.
#
# Direct charges made outside any cached computation (the placement search of an uncached parse, the isotope key's
# search) are charged every time they run -- they re-run every time.

class _WorkFrame:
    """One open cache miss: its OWN work (charged directly while it computes), the closure ``{node: own work}`` of the
    distinct cached computations it touched, and whether its work reaches the meter (not when this load already paid
    for it -- a node recomputed after its value was only ever replayed, never held)."""

    __slots__ = ("own", "closure", "metered")

    def __init__(self, metered: bool) -> None:
        self.own = 0
        self.closure: "dict[object, int]" = {}
        self.metered = metered

    @property
    def total(self) -> int:
        """Own work plus the work of every distinct node beneath it: what a cold, first-in-load computation costs."""
        return self.own + sum(self.closure.values())


#: The open cache misses on this thread/task, innermost last.  Direct charges land on the innermost one only; a nested
#: node, once complete, hands its closure to its parent, and so upward.
_CANONICAL_WORK_FRAMES: "ContextVar[tuple[_WorkFrame, ...]]" = ContextVar("smartchem_canonical_work_frames",
                                                                          default=())


def charge_canonical_work(amount: int) -> None:
    """Charge ``amount`` canonicalisation work units of DIRECT work (never a nested cached call's): to the innermost
    open cache miss, which records it as its own, and to the load in progress (:meth:`WorkMeter.charge_canonical` --
    recorded now, an overflow refused at the next checked charge or the end of the load, never from in here) unless
    that miss's work is already paid for in this load.  Outside any miss, a load is charged every time: uncached work
    re-runs every time.  Outside a load, open misses still record, so an entry computed on a producer path carries its
    true work into the first load that hits it."""
    amount = _require_amount(amount)
    frames = _CANONICAL_WORK_FRAMES.get()
    context = _ACTIVE_CONTEXT.get()
    if frames:
        top = frames[-1]
        top.own += amount
        if context is not None and top.metered:
            context.meter.charge_canonical(amount)
    elif context is not None:
        context.meter.charge_canonical(amount)


@contextmanager
def _recording_canonical_work(metered: bool = True) -> "Iterator[_WorkFrame]":
    """Open a bare frame (no node, no cache): yields it; ``frame.total`` is the work the enclosed calls cost cold."""
    frame = _WorkFrame(metered)
    token = _CANONICAL_WORK_FRAMES.set(_CANONICAL_WORK_FRAMES.get() + (frame,))
    try:
        yield frame
    finally:
        _CANONICAL_WORK_FRAMES.reset(token)


def _hand_up(closure: "dict[object, int]") -> None:
    frames = _CANONICAL_WORK_FRAMES.get()
    if frames:
        frames[-1].closure.update(closure)


def _through_cache(node: object, lookup: "Callable[[], tuple | None]", compute: "Callable[[], object]",
                   store: "Callable[[object, dict], None]") -> object:
    """The one protocol every work-transparent cache follows (see the section comment).

    ``lookup()`` -> ``(value, closure)`` or ``None``; ``compute()`` -> the value; ``store(value, closure)`` retains it.
    Order: the load's own memo (charge 0), then the process cache (charge the closure's unpaid nodes), then compute
    (direct charges metered as they happen, before the work they bound).
    """
    context = _ACTIVE_CONTEXT.get()
    if context is not None:
        held = context._canonical_memo.get(node)
        if held is not None:
            _hand_up(held[1])
            return held[0]
    hit = lookup()
    if hit is not None:
        if context is not None:
            context._replay(hit[1])
            context._canonical_memo[node] = hit
        _hand_up(hit[1])
        return hit[0]
    frames = _CANONICAL_WORK_FRAMES.get()
    # already paid (replayed through an ancestor's closure, value never held) -> recompute WITHOUT metering; everything
    # beneath an unmetered frame was in that same closure, so nothing inside is metered either
    metered = (not frames or frames[-1].metered) and (context is None or node not in context._charged)
    frame = _WorkFrame(metered)
    token = _CANONICAL_WORK_FRAMES.set(frames + (frame,))
    try:
        value = compute()
    except BaseException:
        _CANONICAL_WORK_FRAMES.reset(token)
        if frames:                              # a failed computation is no node: its work is its caller's own
            frames[-1].own += frame.own
            frames[-1].closure.update(frame.closure)
        raise
    _CANONICAL_WORK_FRAMES.reset(token)
    closure = dict(frame.closure)
    closure[node] = frame.own
    if context is not None:
        context._charged.add(node)
        context._canonical_memo[node] = (value, closure)
    store(value, closure)
    _hand_up(closure)
    return value


#: ``functools.lru_cache``'s ``cache_info()`` shape, so callers that read it (the stress harness) keep reading it.
CacheInfo = namedtuple("CacheInfo", ("hits", "misses", "maxsize", "currsize"))


def work_transparent_cache(maxsize: int) -> "Callable[[Callable], Callable]":
    """``functools.lru_cache(maxsize)`` for a ONE-argument function with canonicalisation on its call path -- keyed by
    the argument's value (hash/eq, as ``lru_cache``), thread-safe, computed outside the lock, ``cache_info()`` /
    ``cache_clear()`` as ``lru_cache``, usable as a method decorator (the argument is then ``self``) -- but each call is
    a NODE of the distinct-once-per-load charge (:func:`_through_cache`): an entry keeps ``(value, closure)`` and a hit
    charges the closure's nodes the load has not paid for.  A computation that raises stores nothing; the work it
    charged before raising stays charged (to its caller), exactly as a cold call would.  ``cache_clear()`` bumps a
    generation: a value computed before the clear is never stored after it (Wave C3 C3-F4).
    """
    if type(maxsize) is not int or maxsize <= 0:
        raise ValueError(f"work_transparent_cache maxsize must be a positive int, got {maxsize!r}; refused")

    def decorate(fn: "Callable") -> "Callable":
        lock = threading.Lock()
        entries: "OrderedDict[object, tuple[object, dict]]" = OrderedDict()
        counts = {"hits": 0, "misses": 0, "generation": 0}

        def lookup(arg):
            # lock-free on purpose (the canonical() hot path): dict.get and OrderedDict.move_to_end are single atomic C
            # calls, and an entry evicted in between just stays evicted
            hit = entries.get(arg)
            if hit is not None:
                try:
                    entries.move_to_end(arg)
                except KeyError:
                    pass
                counts["hits"] += 1
            return hit

        @functools.wraps(fn)
        def wrapper(arg):
            if _ACTIVE_CONTEXT.get() is None and not _CANONICAL_WORK_FRAMES.get():
                hit = lookup(arg)                    # nothing to charge or record: the plain LRU fast path
                if hit is not None:
                    return hit[0]
            with lock:
                generation = counts["generation"]

            def compute():
                with lock:
                    counts["misses"] += 1
                return fn(arg)

            def store(value, closure):
                with lock:
                    if counts["generation"] == generation and arg not in entries:
                        entries[arg] = (value, closure)
                        if len(entries) > maxsize:
                            entries.popitem(last=False)

            return _through_cache((fn, arg), lambda: lookup(arg), compute, store)

        def cache_info() -> CacheInfo:
            with lock:
                return CacheInfo(counts["hits"], counts["misses"], maxsize, len(entries))

        def cache_clear() -> None:
            with lock:
                entries.clear()
                counts["hits"] = counts["misses"] = 0
                counts["generation"] += 1

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper

    return decorate


# ---------------------------------------------------------------------------------------------------------------------
# The bounded process-level enumeration cache (§4)
# ---------------------------------------------------------------------------------------------------------------------

#: 0.9.5 S16 (Wave C3 C3-F3) -- the enumeration cache's MEMORY bound, in :func:`retained_size` units (atoms + bonds held
#: by an entry's transforms).  MEASURED 2026-09-30 (deep ``sys.getsizeof`` of the raw transforms): Diels-Alder entries
#: 49-81 bytes/unit (cyclohexene-chain targets, 4-24 rings: 370-9,010 units, 21-727 KB); honest scission entries are
#: dominated by per-transform overhead instead (methyl acetate 16 transforms / 41 units / 9.2 KB; isopentyl acetate 82 /
#: 65 / 34 KB; aspirin 47 / 62 / 23 KB) -- that part stays bounded by ``max_transforms`` (65,536 x <= ~0.6 KB).  So
#: 2**19 units ~ 42 MB of molecules-by-value on top of <= ~39 MB of transform overhead: ~81 MB worst case, where the
#: count-only bound admitted ~0.37 GB of 24-ring entries.  An entry over 2**15 units (~2.6 MB; a 24-ring entry is 9,010)
#: is returned but never retained.
_ENUM_CACHE_MAX_SIZE = 1 << 19
_ENUM_CACHE_MAX_ENTRY_SIZE = 1 << 15


@dataclass(frozen=True)
class EnumerationCacheStats:
    hits: int
    misses: int
    entries: int
    retained_transforms: int
    retained_size: int = 0          # 0.9.5 S16 (Wave C3 C3-F3): atoms + bonds of every Molecule the entries hold


def retained_size(transforms: tuple) -> int:
    """What an enumeration entry actually keeps alive: the atoms + bonds of every distinct ``Molecule`` object reachable
    from its transforms (dataclass fields, tuples, lists, sets, dict values; each object counted once).

    Wave C3 (C3-F3): a transform COUNT is not a size -- Diels-Alder transforms carry their products by value, 20 KB per
    transform at 8 rings and 59 KB at 24, so 512 entries far under the transform bound held ~0.37 GB.  One unit is
    ~50-80 bytes retained where molecules dominate (measured on Diels-Alder entries; see ``_ENUM_CACHE_MAX_SIZE``), so
    a bound in these units is a bound in memory.  Anything that is not a Molecule or a container of one weighs 0.
    """
    from .category import Molecule   # call-time: category imports this module
    seen: set[int] = set()
    total = 0
    stack: list = list(transforms)
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if isinstance(obj, Molecule):
            total += len(obj.atoms) + len(obj.bonds)
        elif dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            stack.extend(getattr(obj, f.name) for f in dataclasses.fields(obj))
        elif isinstance(obj, (tuple, list, set, frozenset)):
            stack.extend(obj)
        elif isinstance(obj, dict):
            stack.extend(obj.values())
    return total


class EnumerationCache:
    """A thread-safe weighted LRU over RAW ``registry.enumerate`` outputs ``(transforms_tuple, complete_flag)``.

    Bounds (§4): at most ``max_transforms`` retained transforms in total and ``max_entries`` entries; an output
    heavier than ``max_entry_transforms`` is returned but never retained.  0.9.5 S16 (Wave C3 C3-F3) adds the bound
    that means memory: at most ``max_retained_size`` units of :func:`retained_size` in total, and an output over
    ``max_entry_size`` is never retained.  The shape/centre reduction is NOT cached (it stays textually inside the
    D29.1 check, so source-level mutants of it still act on live code).  Disabled, the cache computes every call and
    stores nothing.  :meth:`clear` bumps a generation: a value computed before a clear is never stored after it
    (C3-F4 -- a patch-then-clear must not be undone by an enumeration that was already in flight).
    """

    def __init__(self, *, max_transforms: int = 65_536, max_entries: int = 512,
                 max_entry_transforms: int = 8_192, max_retained_size: int = _ENUM_CACHE_MAX_SIZE,
                 max_entry_size: int = _ENUM_CACHE_MAX_ENTRY_SIZE) -> None:
        for name, value in (("max_transforms", max_transforms), ("max_entries", max_entries),
                            ("max_entry_transforms", max_entry_transforms), ("max_retained_size", max_retained_size),
                            ("max_entry_size", max_entry_size)):
            if type(value) is not int or value <= 0:
                raise ValueError(f"EnumerationCache.{name} must be a positive int, got {value!r}; refused")
        if max_entry_transforms > max_transforms:
            raise ValueError("EnumerationCache.max_entry_transforms cannot exceed max_transforms (such an entry could "
                             "never be retained within the total bound); refused")
        if max_entry_size > max_retained_size:
            raise ValueError("EnumerationCache.max_entry_size cannot exceed max_retained_size (such an entry could "
                             "never be retained within the total bound); refused")
        self.max_transforms = max_transforms
        self.max_entries = max_entries
        self.max_entry_transforms = max_entry_transforms
        self.max_retained_size = max_retained_size
        self.max_entry_size = max_entry_size
        self._lock = threading.Lock()
        self._entries: "OrderedDict[object, tuple[tuple, bool]]" = OrderedDict()
        # S16: key -> (the enumeration's closure of charged nodes, retained size), beside the value, never inside it
        self._meta: "dict[object, tuple[int, int]]" = {}
        self._weight = 0
        self._size = 0
        self._hits = 0
        self._misses = 0
        self._enabled = True
        self._generation = 0

    def set_enabled(self, flag: bool) -> None:
        _require_bool("EnumerationCache.set_enabled(flag)", flag)
        with self._lock:
            self._enabled = flag

    def get_or_compute(self, key: object, compute: "Callable[[], tuple[tuple, bool]]") -> "tuple[tuple, bool]":
        """The value for ``key`` -- a NODE of the S16 distinct-once-per-load charge (:func:`_through_cache`): the load's
        memo first, then this cache (a hit charges the canonicalisations of the enumeration's closure the load has not
        paid for), then ``compute()`` -- run OUTSIDE the lock, since an enumeration can take seconds."""
        with self._lock:
            enabled = self._enabled
            generation = self._generation

        def lookup():
            with self._lock:
                hit = self._entries.get(key) if enabled else None
                if hit is not None:
                    self._entries.move_to_end(key)
                    self._hits += 1
                    return hit, self._meta[key][0]
                self._misses += 1
                return None

        def checked_compute():
            value = compute()
            if not (type(value) is tuple and len(value) == 2 and type(value[0]) is tuple and type(value[1]) is bool):
                raise TypeError("an enumeration cache value must be (transforms_tuple, complete_bool) -- immutable, so "
                                "it can be shared; refused")
            return value

        def store(value, closure):
            weight = len(value[0])
            if not enabled or weight > self.max_entry_transforms:
                return
            size = retained_size(value[0])
            if size > self.max_entry_size:
                return                                            # too big to keep: returned, never retained
            with self._lock:
                # a racing thread may have stored the equal value; a clear() since the miss makes this value stale
                if self._enabled and self._generation == generation and key not in self._entries:
                    self._entries[key] = value
                    self._meta[key] = (closure, size)
                    self._weight += weight
                    self._size += size
                    while (self._weight > self.max_transforms or self._size > self.max_retained_size
                           or len(self._entries) > self.max_entries):
                        old_key, (old_transforms, _old_flag) = self._entries.popitem(last=False)
                        _old_closure, old_size = self._meta.pop(old_key)
                        self._weight -= len(old_transforms)
                        self._size -= old_size

        return _through_cache((self, key), lookup, checked_compute, store)

    def clear(self) -> None:
        """Drop every entry, zero the counters and bump the generation.  REQUIRED around any in-process code patch (the
        mutation harness ``_patch``, provider monkeypatching): such a patch changes behaviour without changing any key,
        and the generation keeps an enumeration that was already running from re-populating the cache afterwards."""
        with self._lock:
            self._entries.clear()
            self._meta.clear()
            self._weight = 0
            self._size = 0
            self._hits = 0
            self._misses = 0
            self._generation += 1

    def stats(self) -> EnumerationCacheStats:
        with self._lock:
            return EnumerationCacheStats(hits=self._hits, misses=self._misses, entries=len(self._entries),
                                         retained_transforms=self._weight, retained_size=self._size)


#: The process-level cache the D29.1 check reads through (via :func:`cached_enumerate`).
ENUMERATION_CACHE = EnumerationCache()


def set_enumeration_cache_enabled(flag: bool) -> None:
    """Turn the process cache on/off (the stress gate's on-vs-off byte-identity comparison).  Off = always compute."""
    ENUMERATION_CACHE.set_enabled(flag)


def enumeration_cache_key(registry: "TransformProviderRegistry", target: "Molecule", reagents,
                          budget: int) -> tuple:
    """``(registry.digest, target, tuple(reagents), budget)`` -- every input ``enumerate`` is a function of, by VALUE.

    ``target`` and each reagent are literal Molecule values (atoms, bonds, charge, state; dataclass equality, NOT
    canonical identity -- the raw transforms embed literal atom order).  Reagent ORDER is kept although Lane B
    measured it inert: an over-specific key only costs a miss, an under-specific one hands back the wrong answer.
    """
    if type(budget) is not int:
        raise TypeError(f"the enumeration budget must be an int, got {type(budget).__name__}; refused")
    return (registry.digest, target, tuple(reagents), budget)


def cached_enumerate(registry: "TransformProviderRegistry", target: "Molecule", reagents, *,
                     budget: int) -> "tuple[tuple[EnumeratedTransform, ...], bool]":
    """``registry.enumerate(target, reagents, budget=budget)`` through :data:`ENUMERATION_CACHE`.

    Charges no ENUMERATION work: the caller charges that at its per-load distinct-target miss, BEFORE calling this, so
    whether a load is refused never depends on what an earlier load left in the process cache.  The canonicalisations
    the enumeration performs are charged (S16) -- as they run on a miss, replayed on a hit -- for the same reason.
    """
    reagents = tuple(reagents)
    key = enumeration_cache_key(registry, target, reagents, budget)
    return ENUMERATION_CACHE.get_or_compute(key, lambda: registry.enumerate(target, reagents, budget=budget))


# S16: fill the categorical core's work-accounting hook.  The dependency points this way on purpose -- the core
# imports nothing of this package -- and nothing can load a payload before this module has been imported.
from .category import install_work_accounting as _install_work_accounting  # noqa: E402

_install_work_accounting(charge_canonical_work, work_transparent_cache(maxsize=8192))
