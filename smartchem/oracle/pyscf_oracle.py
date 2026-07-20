"""
Ab initio energy oracle backed by PySCF.

This is the accurate end of the dial. It exists to answer an empirical question rather
than a rhetorical one: *how slow is chemical accuracy, actually?* Measured on this
machine over the reference diatomics -- see ``python -m smartchem.bench``.

What is predicted and what is supplied
--------------------------------------
    supplied  : equilibrium geometry r_e, harmonic frequency omega_e (for the ZPE)
    predicted : D_e, the electronic dissociation energy
    reported  : D_0 = D_e - ZPE

That is the standard protocol for benchmarking an *electronic* method: it isolates the
quantity being tested instead of mixing in geometry error. Set ``optimize_geometry=True``
to remove the geometry input at roughly 6x the cost, which makes the calculation fully
predictive.

Basis-set extrapolation
-----------------------
Correlation energy converges as X^-3 in the cardinal number of the basis, which is slow
and is where essentially all of the remaining error sits. The Helgaker two-point formula

    E_corr(CBS) = (X^3 E_corr(X) - Y^3 E_corr(Y)) / (X^3 - Y^3)

removes it. Hartree-Fock converges exponentially, so the larger basis is used directly
for that part. Extrapolating the two components separately is the whole point -- averaging
total energies would smear the fast-converging part into the slow one.

Cost control
------------
Atomic energies dominate: a benchmark of N diatomics needs 2N atom calculations, but only
a handful of distinct elements. They are cached per (element, basis, method), so E(H) at
CCSD(T)/cc-pVQZ is computed once and reused by H2, HF, HCl, HI, OH, CH and NH.

This is also where the categorical layer earns its keep. Pruning by conservation, charge
balance and valence happens *before* any call into this module, so the expensive oracle is
only ever asked about candidates that are already structurally valid.
"""
from __future__ import annotations

import time
import warnings

from .base import BaseOracle, Estimate
from ..data.reference import ATOM_SPIN, GEOMETRY, zero_point_energy_ev

try:
    from pyscf import gto, scf, mp, cc
except ImportError as exc:  # pragma: no cover - exercised by absence, not presence
    raise ImportError("PySCFOracle requires pyscf: pip install 'smartchem[qc]'") from exc

HARTREE_EV = 27.211386245988

#: Cardinal number X for each correlation-consistent basis, used by the X^-3 extrapolation.
_CARDINAL = {"cc-pVDZ": 2, "cc-pVTZ": 3, "cc-pVQZ": 4, "cc-pV5Z": 5}

#: Methods in increasing order of cost and accuracy.
_METHODS = ("HF", "MP2", "CCSD", "CCSD(T)")

#: MEASURED mean absolute error in eV on main-group diatomic BDEs, from the sweep run in
#: this repository on 2026-07-20. These are observations, not vendor claims -- reproduce
#: with ``python -m smartchem.bench``. Used only to label a tier; a fresh benchmark
#: supersedes them.
#:
#:   tier                   MAE eV   kcal/mol   sec/species   n
#:   HF/cc-pVDZ             2.4402      56.27          0.14   3
#:   CCSD(T)/cc-pVDZ        0.5745      13.25          1.31   3
#:   CCSD(T)/cc-pVTZ        0.1912       4.41          5.59   5
#:   CCSD(T)/cc-pVQZ        0.0790       1.82         23.57   5
#:   CCSD(T)/cbs(TZ,QZ)     0.0411       0.95         99.60  10   <-- chemical accuracy
#:
#: Where CBS still misses (3 of 10 outside 1 kcal/mol) is systematic and well understood,
#: not random: NaCl +3.38 kcal/mol (ionic, wants diffuse functions -- aug-cc-pVXZ),
#: CS -1.53 (second-row sulfur, wants tight d -- cc-pV(X+d)Z), N2 -1.19 (a notoriously
#: hard correlation case). The first-row covalent species land at 0.01-0.86.
_NOMINAL = {
    ("HF", "cc-pVDZ"): 2.44, ("HF", "cc-pVTZ"): 2.40, ("HF", "cc-pVQZ"): 2.39,
    ("CCSD(T)", "cc-pVDZ"): 0.57,
    ("CCSD(T)", "cc-pVTZ"): 0.19,
    ("CCSD(T)", "cc-pVQZ"): 0.08,
    ("CCSD(T)", "cbs(TZ,QZ)"): 0.041,
}


class ConvergenceFailure(RuntimeError):
    """SCF or coupled-cluster failed to converge. Declining beats reporting a bad number."""


class PySCFOracle(BaseOracle):
    """
    Ab initio bond energies at a chosen (method, basis) tier.

    ``basis`` may be a single basis name, or ``"cbs(TZ,QZ)"`` to request the two-point
    extrapolation described above.
    """

    def __init__(
        self,
        method: str = "CCSD(T)",
        basis: str = "cc-pVTZ",
        optimize_geometry: bool = False,
        max_atoms: int = 2,
    ):
        if method not in _METHODS:
            raise ValueError(f"method must be one of {_METHODS}, got {method!r}")
        self.method = method
        self.basis = basis
        self.optimize_geometry = optimize_geometry
        self.max_atoms = max_atoms
        self.name = f"{method}/{basis}"
        self.nominal_accuracy_ev = _NOMINAL.get((method, basis), 0.30)
        self._cache: dict[tuple, float] = {}

    # -- internals ---------------------------------------------------------------
    def _is_cbs(self) -> tuple[str, str] | None:
        """Return the (small, large) basis pair if this is a CBS request."""
        if not self.basis.lower().startswith("cbs"):
            return None
        inner = self.basis[self.basis.index("(") + 1: self.basis.index(")")]
        small, large = (s.strip() for s in inner.split(","))
        expand = {"DZ": "cc-pVDZ", "TZ": "cc-pVTZ", "QZ": "cc-pVQZ", "5Z": "cc-pV5Z"}
        return expand.get(small, small), expand.get(large, large)

    def _parts(self, atom_spec: str, basis: str, spin: int) -> tuple[float, float]:
        """(E_HF, E_corr) in Hartree. Raises ConvergenceFailure rather than guessing."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mol = gto.M(atom=atom_spec, basis=basis, spin=spin, verbose=0, unit="Angstrom")
            mf = (scf.RHF if spin == 0 else scf.UHF)(mol)
            mf.conv_tol = 1e-10
            mf.max_cycle = 300
            mf.kernel()
            if not mf.converged:
                mf = mf.newton()
                mf.kernel()
            if not mf.converged:
                raise ConvergenceFailure(f"SCF did not converge for {atom_spec} / {basis}")
            if self.method == "HF":
                return mf.e_tot, 0.0
            if self.method == "MP2":
                return mf.e_tot, mp.MP2(mf).kernel()[0]
            mycc = cc.CCSD(mf)
            mycc.conv_tol = 1e-9
            mycc.max_cycle = 300
            mycc.kernel()
            if not mycc.converged:
                raise ConvergenceFailure(f"CCSD did not converge for {atom_spec} / {basis}")
            corr = mycc.e_corr
            if self.method == "CCSD(T)":
                corr += mycc.ccsd_t()
            return mf.e_tot, corr

    def _energy(self, atom_spec: str, spin: int, cache_key: tuple | None = None) -> float:
        """Total energy in Hartree at the configured tier, CBS-extrapolated if requested."""
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]

        pair = self._is_cbs()
        if pair is None:
            hf, corr = self._parts(atom_spec, self.basis, spin)
            total = hf + corr
        else:
            small, large = pair
            x, y = _CARDINAL[large], _CARDINAL[small]
            hf_s, corr_s = self._parts(atom_spec, small, spin)
            hf_l, corr_l = self._parts(atom_spec, large, spin)
            # HF converges exponentially: take the larger basis directly.
            # Correlation converges as X^-3: extrapolate it, and only it.
            corr_cbs = (x**3 * corr_l - y**3 * corr_s) / (x**3 - y**3)
            total = hf_l + corr_cbs

        if cache_key is not None:
            self._cache[cache_key] = total
        return total

    def _atom_energy(self, symbol: str) -> float:
        spin = ATOM_SPIN.get(symbol)
        if spin is None:
            raise KeyError(f"no ground-state spin known for {symbol}")
        return self._energy(f"{symbol} 0 0 0", spin,
                            cache_key=("atom", symbol, self.basis, self.method))

    def _optimal_bond_length(self, a: str, b: str, spin: int, guess: float) -> float:
        """
        Parabolic minimisation over a small scan. Removes the experimental geometry
        input at the cost of ~5 extra energy evaluations.
        """
        offsets = (-0.06, -0.03, 0.0, 0.03, 0.06)
        pts = []
        for d in offsets:
            r = guess + d
            pts.append((r, self._energy(f"{a} 0 0 0; {b} 0 0 {r}", spin)))
        # fit a parabola through the three lowest points
        pts.sort(key=lambda p: p[1])
        (r1, e1), (r2, e2), (r3, e3) = sorted(pts[:3])
        denom = (r1 - r2) * (r1 - r3) * (r2 - r3)
        if abs(denom) < 1e-12:
            return guess
        aa = (r3 * (e2 - e1) + r2 * (e1 - e3) + r1 * (e3 - e2)) / denom
        bb = (r3**2 * (e1 - e2) + r2**2 * (e3 - e1) + r1**2 * (e2 - e3)) / denom
        if aa <= 0:
            return guess
        return -bb / (2 * aa)

    # -- oracle interface --------------------------------------------------------
    def estimate(self, symbols: tuple[str, ...]) -> Estimate | None:
        if len(symbols) != self.max_atoms:
            return None                      # this oracle covers diatomics only, for now
        a, b = symbols
        if a not in ATOM_SPIN or b not in ATOM_SPIN:
            return None                      # no ground-state spin known; decline

        formula = _formula_key(symbols)
        geom = GEOMETRY.get(formula)
        if geom is None and not self.optimize_geometry:
            return None                      # no geometry supplied and none requested
        r_e, _omega, mol_spin = geom if geom else (1.5, 0.0, 0)

        t0 = time.perf_counter()
        try:
            if self.optimize_geometry:
                r_e = self._optimal_bond_length(a, b, mol_spin, r_e)
            e_mol = self._energy(f"{a} 0 0 0; {b} 0 0 {r_e}", mol_spin)
            e_a = self._atom_energy(a)
            e_b = self._atom_energy(b)
        except (ConvergenceFailure, KeyError, RuntimeError):
            # A number we do not trust is worse than no number. Decline.
            return None
        dt = time.perf_counter() - t0

        d_e = (e_a + e_b - e_mol) * HARTREE_EV
        zpe = zero_point_energy_ev(formula) or 0.0
        d_0 = d_e - zpe

        return Estimate(
            value_ev=d_0,
            uncertainty_ev=self.nominal_accuracy_ev,
            method=self.name + ("/opt" if self.optimize_geometry else ""),
            seconds=dt,
            notes=f"D_e={d_e:.4f} eV, ZPE={zpe:.4f} eV, r_e={r_e:.4f} A"
                  + ("" if geom else " (geometry optimised, no reference)"),
        )


def _formula_key(symbols: tuple[str, ...]) -> str:
    """
    Match the reference-table naming.

    Homonuclear is ``A2``. Heteronuclear is conventionally ordered (``CO``, not ``OC``),
    so both orders are tried against the table rather than assuming the caller supplied
    the conventional one.
    """
    a, b = symbols
    if a == b:
        return f"{a}2"
    for candidate in (f"{a}{b}", f"{b}{a}"):
        if candidate in GEOMETRY:
            return candidate
    return f"{a}{b}"
