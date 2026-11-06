"""Small measurement helpers shared by tests and run_probes.py (convergence order, commutators)."""
from __future__ import annotations

import numpy as np

from .twocell import OPERATORS, State, System


def state_distance(a: State, b: State) -> float:
    """Max-abs difference over amounts (mol) and, separately scaled, energies (J) -> single number: max of both."""
    dn = float(np.max(np.abs(a.n - b.n), initial=0.0))
    dU = float(np.max(np.abs(a.U - b.U), initial=0.0))
    return max(dn, dU)


def apply_ops(system: System, state: State, dt: float, sequence) -> State:
    """Apply operators left-to-right.  Item = name or (name, kwargs)."""
    for item in sequence:
        name, kw = (item, {}) if isinstance(item, str) else item
        state, _ = OPERATORS[name](system, state, dt, **kw)
    return state


def commutator(system: System, state: State, op1, op2, dt: float) -> float:
    """|| op2(op1(x)) - op1(op2(x)) ||_max.  ~0 only for operations acting on disjoint state."""
    return state_distance(apply_ops(system, state, dt, [op1, op2]), apply_ops(system, state, dt, [op2, op1]))


def assert_commute(system: System, state: State, op1, op2, dt: float, tol: float) -> None:
    c = commutator(system, state, op1, op2, dt)
    assert c <= tol, f"operations do NOT commute: commutator {c:.3e} > {tol:.1e}"


def estimate_order(dts, errors) -> float:
    """Least-squares slope of log(error) vs log(dt) -- the observed convergence order."""
    dts, errors = np.asarray(dts, float), np.asarray(errors, float)
    return float(np.polyfit(np.log(dts), np.log(errors), 1)[0])


def convergence_ok(dts, errors, lo=0.8, hi=1.3) -> bool:
    """True iff errors shrink strictly with dt and the observed order lies in the declared window [lo, hi]."""
    errors = np.asarray(errors, float)
    return bool(np.all(np.diff(errors) < 0) and lo <= estimate_order(dts, errors) <= hi)
