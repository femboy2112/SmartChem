"""
Ab initio energy oracle backed by PySCF.

This is the high-cost electronic-structure end of the current dial. It exists to answer
an empirical question rather than a rhetorical one: how accurate and costly are specific
declared protocols on a stated reference set? The present selected seven-diatomic results
do not establish broad chemical accuracy -- see ``python -m smartchem.bench``.

What is predicted and what is supplied
--------------------------------------
    supplied  : equilibrium geometry r_e, harmonic frequency omega_e (for the ZPE)
    predicted : D_e, the electronic dissociation energy
    reported  : D_0 = D_e - ZPE

That is the standard protocol for benchmarking an *electronic* method: it isolates the
quantity being tested instead of mixing in geometry error. Set ``optimize_geometry=True``
to predict the diatomic bond length at additional cost. The current diatomic path still
uses a tabulated harmonic frequency for ZPE, so that option is not a fully predictive
thermochemistry protocol.

Basis-set extrapolation
-----------------------
In regimes already in the asymptotic tail, correlation energy is often modeled with a
leading X^-3 cardinal-number error. The Helgaker two-point formula

    E_corr(CBS) = (X^3 E_corr(X) - Y^3 E_corr(Y)) / (X^3 - Y^3)

extrapolates that assumed leading term. It does not guarantee removal of the residual error;
this repository's NaCl sequence is a counterexample to treating it as an identity.
Hartree-Fock usually converges faster, so the larger basis is used directly for that part.

Basis choice is a function of the elements -- and measuring that did not pay off
--------------------------------------------------------------------------------
The reasoning was: extrapolation only removes error the basis family is *converging
toward*, and two deficiencies survive it because they are present at every cardinal --
diffuse functions for ionic species, tight d for second-row elements (Al-Ar). Both are
properties of the elements involved, so ``resolve_basis`` computes the basis per element
rather than taking one name for the whole molecule.

The machinery is real, tested, and available (``tight_d=True``, ``aug-`` prefixes). **It
is also not recommended, because it was measured and it lost**: 2.94 kcal/mol against 1.30
for plain ``cbs(TZ,QZ)``, at 5.1x the cost. See ``_FIXED_DIATOMIC_MAE`` below.

It is kept rather than deleted for the same reason the legacy engine is kept: a negative
result you can still run is worth more than one you have to take on trust. Reproduce with
``PySCFOracle("CCSD(T)", "aug-cbs(TZ,QZ)", tight_d=True)``.

The reasoning failed at a specific, identifiable step, which is the part worth carrying
forward. The motivating probe was run at *fixed cardinal*, where augmentation genuinely
does help (NaCl -4.10 -> -1.11 kcal/mol at TZ). That result was then assumed to carry over
to the *extrapolated* tier. It does not: extrapolation weights the larger basis by 64/37
and the smaller by -27/37, so it amplifies any non-smoothness between them rather than
averaging it away. "Helps at TZ" and "helps after extrapolating from TZ and QZ" are
different claims needing different measurements.

Cost control
------------
Atomic energies dominate: a benchmark of N diatomics needs 2N atom calculations, but only
a handful of distinct elements. They are cached per (element, basis, method), so E(H) at
CCSD(T)/cc-pVQZ is computed once and reused by H2, HF, HCl, HI, OH, CH and NH.

This is also where the categorical layer earns its keep. Pruning by composition and charge
balance happens *before* any call into this module. Chemical valence and electronic-state
validity need a separate chemistry-specific validator and are not guaranteed by the core.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import logging
import math
import re
import time
import warnings
from importlib.metadata import PackageNotFoundError, version
from types import MappingProxyType

import numpy as np

#: Progress for the long calculations. A polyatomic relaxation can run forty minutes with
#: nothing to show for it, and "is it hung or still working" is not a question a caller
#: should have to answer by reading CPU time in ``ps`` -- which is exactly how the C3H7OH
#: refusal was eventually diagnosed. Silent by default (no handler, so nothing is emitted
#: unless a caller asks); ``logging.basicConfig(level=logging.INFO)`` turns it on.
_log = logging.getLogger(__name__)

from .base import BaseOracle, Estimate, carries_unmodelled_physics
from ..atoms import PT
from ..category import Molecule
from ..data.basis_tight_d import SECOND_ROW, TIGHT_D
from ..data.reference import ATOM_SPIN, GEOMETRY, zero_point_energy_ev
from ..geometry import (GeometryError, harmonic_analysis, relax, seed_coordinates)

try:
    from pyscf import gto, scf, mp, cc
except ModuleNotFoundError as exc:  # optional backend; pure configuration must still import
    # Only absence of the top-level optional package is an availability condition. If an
    # installed PySCF fails because one of its own imports is broken, surface that defect
    # instead of silently pretending the backend is not installed.
    if exc.name != "pyscf":
        raise
    gto = scf = mp = cc = None
    _PYSCF_IMPORT_ERROR: ImportError | None = exc
else:
    _PYSCF_IMPORT_ERROR = None

PYSCF_AVAILABLE = _PYSCF_IMPORT_ERROR is None
try:
    PYSCF_VERSION = version("pyscf") if PYSCF_AVAILABLE else "unavailable"
except PackageNotFoundError:  # defensive: import and package metadata should agree
    PYSCF_VERSION = "unknown"


def _require_pyscf() -> None:
    """Raise only when a real backend operation is attempted."""
    if not PYSCF_AVAILABLE:
        raise ImportError(
            "PySCFOracle requires pyscf: pip install 'smartchem[qc]'"
        ) from _PYSCF_IMPORT_ERROR

def _label(molecule: Molecule) -> str:
    """A readable formula for a log line. Never raises: this is for humans, not for keys."""
    return "".join(f"{symbol}{count if count > 1 else ''}"
                   for symbol, count in sorted(molecule.formula.items())) or "?"


HARTREE_EV = 27.211386245988

#: Cardinal number X for each correlation-consistent basis, used by the X^-3 extrapolation.
#: Diffuse augmentation does not change the cardinal -- aug-cc-pVTZ is still X=3 -- so the
#: extrapolation is unaffected by the aug- prefix.
_CARDINAL = MappingProxyType({
    "cc-pVDZ": 2, "cc-pVTZ": 3, "cc-pVQZ": 4, "cc-pV5Z": 5,
    "aug-cc-pVDZ": 2, "aug-cc-pVTZ": 3, "aug-cc-pVQZ": 4, "aug-cc-pV5Z": 5,
})

#: Matches a correlation-consistent basis name so its tight-d variant can be named.
_CC_NAME = re.compile(r"^((?:aug-)?cc-pV)([DTQ5])(Z)$")
_CBS_NAME = re.compile(
    r"^(aug-)?cbs\(\s*(DZ|TZ|QZ|5Z)\s*,\s*(DZ|TZ|QZ|5Z)\s*\)$",
    re.IGNORECASE,
)

#: Methods in increasing order of cost and accuracy.
_METHODS = ("HF", "MP2", "CCSD", "CCSD(T)")

#: Methods that can supply BOTH an analytic gradient and an analytic Hessian.
#:
#: The relaxation needs the gradient; the local-curvature check and zero-point energy
#: need the Hessian. They cannot be taken at different tiers: a Hessian is only a harmonic
#: expansion at a point where the gradient vanishes, so evaluating it on a surface other
#: than the one the geometry was relaxed on describes the curvature at a point that is not
#: stationary for it, and the frequencies mean nothing.
#:
#: PySCF gives MP2 analytic gradients but no Hessian here, so MP2 could relax but could not
#: provide the same-tier harmonic local-curvature/ZPE calculation. Hence HF alone in this
#: implementation; this is a coverage choice, not a claim that HF geometry is exact.
_GEOMETRY_METHODS = ("HF",)

#: MEASURED bias of a Hartree-Fock harmonic zero-point energy, as a fraction.
#:
#: +9.1%, from 23 of the tabulated diatomics -- every one whose elements cc-pVDZ covers --
#: against their experimental omega_e. See ``scratchpad/geom_calibrate.py``. This is the
#: aggregate displacement of an HF harmonic protocol relative to those references; the
#: sample does not separately identify electronic-method, harmonic/anharmonic, and
#: reference-convention contributions.
#:
#: It is carried as a named correction sensitivity, in ``Estimate.systematic_terms``, not
#: silently treated as an independent random draw. Its signed displacement can cancel
#: algebraically in a related-energy difference; that does not prove cancellation of the
#: unknown residual error. Coefficient uncertainty and species-residual scatter remain to
#: be calibrated before this becomes an uncertainty model.
#:
#: NOT applied as a scaling correction, deliberately. A factor fitted on 23 DIATOMICS and
#: applied to polyatomics is the identical error already made once in this file with basis
#: augmentation -- measured at fixed cardinal, assumed to carry to the extrapolated tier,
#: and it did not. The bias is reported, not silently removed.
ZPE_BIAS_FRACTION = 0.091

#: How many times to follow an imaginary mode downhill before giving up and declining.
#: Two is enough for the cases seen -- a symmetric seed typically has one symmetry to
#: break -- and a bound is required because a species whose surface keeps producing
#: saddles is one this machinery cannot resolve and must not price.
_MAX_DESCENTS = 3

#: How far to step along an unstable mode, in Angstrom of largest atomic displacement.
#: Large enough to leave the saddle's basin, small enough not to overshoot into an
#: unrelated one. The relaxation that follows does the real work; this only has to break
#: the symmetry that trapped it.
_DESCENT_STEP_ANGSTROM = 0.25

#: MEASURED mean absolute error in eV, on ONE selected species set, 2026-07-20.
#:
#: The set: NaCl, CS, HCl, Cl2, CO, HF, N2 -- chosen to span ionic, second-row and
#: first-row covalent, with N2 as a hard-correlation control. Iodine species are excluded
#: because aug-cc-pVQZ on iodine would dominate the cost without testing anything.
#:
#:   tier                    MAE eV   kcal/mol    n
#:   heuristic (legacy)      4.5455     104.83    4 of 7  (3 refused)
#:   HF/cc-pVQZ              2.5814      59.53    7
#:   CCSD(T)/cc-pVTZ         0.2186       5.04    7
#:   CCSD(T)/cc-pVQZ         0.0763       1.76    7
#:   CCSD(T)/cbs(TZ,QZ)      0.0562       1.30    7   <-- recommended
#:   CCSD(T)/aug-cbs(TZ,QZ)+d 0.1277      2.94    7   <-- FALSIFIED, see below
#:
#: A PREVIOUS version of this table was not comparable across its own rows: it reported
#: n = 3, 3, 5, 5, 10, and since CBS requires *both* TZ and QZ, n(cbs)=10 against n(qz)=5
#: is impossible from a single run. The rows came from different species sets. The
#: per-species values in it were real -- NaCl +3.38, CS -1.53 and N2 -1.19 all reproduced
#: exactly -- but the aggregate was meaningless. Hence one declared set here.
#:
#: TWO CLAIMS THAT WERE MEASURED AND FAILED
#:
#: 1. "Augmenting the basis closes the ionic and second-row gaps." False. aug-cbs+d is
#:    2.3x WORSE at 5.1x the cost. It helped CS (-1.53 -> -1.25) and HCl marginally, and
#:    hurt NaCl (+3.38 -> +12.42), Cl2, CO and HF. The motivating probe was run at FIXED
#:    cardinal, where augmentation genuinely does help; that conclusion was then carried
#:    over to the extrapolated tier without being tested there. Different question.
#:
#: 2. "CS misses because sulfur wants tight d." Overstated. At fixed TZ, diffuse is worth
#:    +2.76 kcal/mol to CS and tight d only +1.39. Borrowed from the literature pattern
#:    rather than measured. See ``smartchem/data/basis_tight_d.py``.
#:
#: AND ONE THING WORTH KNOWING ABOUT THE RECOMMENDED TIER
#:
#: For NaCl, extrapolation makes a good answer worse:
#:
#:      cc-pVTZ      -4.10 kcal/mol
#:      cc-pVQZ      +0.39            <-- nearly chemical accuracy unextrapolated
#:      cbs(TZ,QZ)   +3.38            <-- 8x worse after extrapolating
#:
#: The Helgaker formula behaves exactly as written; its premise -- that the correlation
#: energy is already in the smooth X^-3 tail by TZ -- was not adequate for this NaCl row.
#: The extrapolation displacement is carried on every Estimate and acts as a reporting
#: sensitivity floor when it survives algebraic cancellation (NaCl reports 0.13 eV rather
#: than the tier's nominal 0.0562 eV). This is not a calibrated residual-error bound.
_FIXED_DIATOMIC_MAE = MappingProxyType({
    ("HF", "cc-pVDZ", False): 2.44,
    ("HF", "cc-pVTZ", False): 2.40,
    ("HF", "cc-pVQZ", False): 2.5814,
    ("CCSD(T)", "cc-pVDZ", False): 0.57,
    ("CCSD(T)", "cc-pVTZ", False): 0.2186,
    ("CCSD(T)", "cc-pVQZ", False): 0.0763,
    ("CCSD(T)", "cbs(TZ,QZ)", False): 0.0562,
    ("CCSD(T)", "aug-cbs(TZ,QZ)", True): 0.1277,
})


def _model_inputs_sha256() -> str:
    """Digest transitive SmartChem data/code that can change an oracle result."""
    geometry_module = inspect.getmodule(relax)
    try:
        geometry_source = inspect.getsource(geometry_module).encode("utf-8")
        geometry_source_sha = hashlib.sha256(geometry_source).hexdigest()
    except (OSError, TypeError):
        geometry_source_sha = "unavailable"
    payload = {
        "atom_spin": sorted(ATOM_SPIN.items()),
        "diatomic_geometry": sorted(
            (formula, list(values)) for formula, values in GEOMETRY.items()
        ),
        "periodic_descriptors": sorted(
            (
                symbol,
                atom.symbol,
                atom.atomic_number,
                atom.group,
                atom.period,
                atom.mass_amu,
                list(atom.ie_list_ev),
                list(atom.ea_list_ev),
                atom.radius_pm,
            )
            for symbol, atom in PT.items()
        ),
        "second_row": sorted(SECOND_ROW),
        "tight_d": sorted(TIGHT_D.items()),
        "cardinals": sorted(_CARDINAL.items()),
        "fixed_diatomic_mae": sorted(
            (list(protocol), mae) for protocol, mae in _FIXED_DIATOMIC_MAE.items()
        ),
        "zpe_bias_fraction": ZPE_BIAS_FRACTION,
        "geometry_source_sha256": geometry_source_sha,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ConvergenceFailure(RuntimeError):
    """SCF or coupled-cluster failed to converge. Declining beats reporting a bad number."""


def tight_d_name(basis: str) -> str | None:
    """
    The tight-d variant of a correlation-consistent basis name, or None if there isn't one.

    ``aug-cc-pVTZ`` -> ``aug-cc-pV(T+d)Z``. Returns None for a name outside the family
    (a CBS request, or something exotic) rather than guessing at a spelling.
    """
    m = _CC_NAME.match(basis)
    if m is None:
        return None
    stem, cardinal, tail = m.groups()
    return f"{stem}({cardinal}+d){tail}"


def resolve_basis(symbols: tuple[str, ...], basis: str, tight_d: bool) -> str | dict:
    """
    What PySCF should actually be handed for these elements.

    Returns the plain name when every element wants the same set, and a per-element dict
    when a second-row element needs its tight-d variant. Pure function of its arguments --
    no SCF, no network -- so the policy is unit-testable on a machine without PySCF data
    files, which is how ``tests/test_basis_policy.py`` checks it.

    Declining is allowed here too: if no vendored (X+d) set exists at this cardinal, the
    standard set is returned rather than a silently different one.
    """
    if not tight_d or not any(s in SECOND_ROW for s in symbols):
        return basis
    plus_d = tight_d_name(basis)
    if plus_d is None or plus_d not in TIGHT_D:
        return basis
    _require_pyscf()
    return {
        s: (gto.basis.parse(TIGHT_D[plus_d], symb=s) if s in SECOND_ROW else basis)
        for s in set(symbols)
    }


def _parse_cbs_basis(basis: str) -> tuple[str, str] | None:
    """Parse the documented two-cardinal CBS grammar, rejecting unsafe near-misses."""
    if not isinstance(basis, str):
        raise TypeError("basis must be a non-empty string")
    basis = basis.strip()
    if not basis:
        raise ValueError("basis must be a non-empty string")
    match = _CBS_NAME.fullmatch(basis)
    if match is None:
        if re.match(r"^(?:aug-)?cbs", basis, re.IGNORECASE):
            raise ValueError(
                "CBS basis must have form cbs(DZ,TZ), cbs(TZ,QZ), or another "
                "strictly increasing pair from DZ/TZ/QZ/5Z"
            )
        return None
    augmented, small_alias, large_alias = match.groups()
    aliases = {"DZ": "cc-pVDZ", "TZ": "cc-pVTZ", "QZ": "cc-pVQZ", "5Z": "cc-pV5Z"}
    small_alias, large_alias = small_alias.upper(), large_alias.upper()
    small, large = aliases[small_alias], aliases[large_alias]
    if _CARDINAL[small] >= _CARDINAL[large]:
        raise ValueError("CBS cardinal numbers must be strictly increasing")
    prefix = "aug-" if augmented else ""
    return prefix + small, prefix + large


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
        tight_d: bool = False,
        geometry_tier: tuple[str, str] | None = None,
    ):
        if method not in _METHODS:
            raise ValueError(f"method must be one of {_METHODS}, got {method!r}")
        if type(optimize_geometry) is not bool:
            raise TypeError("optimize_geometry must be a boolean")
        if type(tight_d) is not bool:
            raise TypeError("tight_d must be a boolean")
        if isinstance(max_atoms, bool) or not isinstance(max_atoms, int):
            raise TypeError("max_atoms must be a positive integer")
        if max_atoms < 1:
            raise ValueError("max_atoms must be at least 1")
        if geometry_tier is not None and (
            not isinstance(geometry_tier, tuple)
            or len(geometry_tier) != 2
            or any(not isinstance(item, str) or not item for item in geometry_tier)
        ):
            raise TypeError("geometry_tier must be a (method, basis) string tuple or None")
        parsed_cbs = _parse_cbs_basis(basis)
        if parsed_cbs is not None:
            reverse = {2: "DZ", 3: "TZ", 4: "QZ", 5: "5Z"}
            prefix = "aug-" if parsed_cbs[0].startswith("aug-") else ""
            first = parsed_cbs[0].removeprefix("aug-")
            second = parsed_cbs[1].removeprefix("aug-")
            basis = (f"{prefix}cbs({reverse[_CARDINAL[first]]},"
                     f"{reverse[_CARDINAL[second]]})")
        else:
            basis = basis.strip()
        self.method = method
        self.basis = basis
        self._cbs_pair = parsed_cbs
        self.optimize_geometry = optimize_geometry
        self.max_atoms = max_atoms
        self.tight_d = tight_d
        self.backend_version = PYSCF_VERSION
        # The name records the policy, not just the basis: a result computed with tight d
        # on sulfur is not the same result as one without, and provenance has to say so.
        self.name = f"{method}/{basis}" + ("+d" if tight_d else "")
        # This is a benchmark MAE, not a calibrated probability interval. Unmeasured
        # protocol combinations fail closed instead of inheriting an invented 0.30 eV bar.
        self.fixed_diatomic_mae_ev = _FIXED_DIATOMIC_MAE.get(
            (method, basis, tight_d), float("inf")
        )
        # The measured table covers fixed-tabulated-geometry neutral diatomics only.
        # Optimized geometry and polyatomic-capable configurations are distinct protocols;
        # they cannot inherit that seven-species MAE merely because the energy tier matches.
        validated_profile = (
            not optimize_geometry and geometry_tier is None and max_atoms <= 2
        )
        self.benchmark_mae_ev = (
            self.fixed_diatomic_mae_ev if validated_profile else float("inf")
        )
        self.nominal_accuracy_ev = self.benchmark_mae_ev
        self._cache: dict[tuple, float] = {}
        # Locating the minimum and evaluating the energy at it are two different
        # questions, and only the second one needs the expensive tier. When a geometry
        # tier is named, the scan runs there and the single point runs here.
        # optimize_geometry=False on the sub-oracle is what stops this recursing.
        self.geometry_tier = geometry_tier
        self._geom_oracle = (
            PySCFOracle(geometry_tier[0], geometry_tier[1], optimize_geometry=False,
                        max_atoms=max_atoms, tight_d=tight_d)
            if geometry_tier is not None else None
        )
        if geometry_tier is not None:
            self.name += f"//{geometry_tier[0]}/{geometry_tier[1]}"

    def calculation_spec(self):
        """Complete immutable calculation identity; runtime wavefunction caches are excluded."""
        return {
            "method": self.method,
            "basis": self.basis,
            "optimize_geometry": self.optimize_geometry,
            "max_atoms": self.max_atoms,
            "tight_d": self.tight_d,
            "geometry_tier": self.geometry_tier,
            "backend_version": self.backend_version,
            "model_inputs_sha256": _model_inputs_sha256(),
        }

    # -- internals ---------------------------------------------------------------
    def _is_cbs(self) -> tuple[str, str] | None:
        """
        Return the (small, large) basis pair if this is a CBS request.

        Accepts ``cbs(TZ,QZ)`` and ``aug-cbs(TZ,QZ)``; the prefix carries through to both
        members, since extrapolating an augmented basis against a plain one would compare
        two different families and the X^-3 form would be meaningless.
        """
        return self._cbs_pair

    def _parts(
        self, atom_spec: str, symbols: tuple[str, ...], basis: str, spin: int
    ) -> tuple[float, float]:
        """(E_HF, E_corr) in Hartree. Raises ConvergenceFailure rather than guessing."""
        _require_pyscf()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            resolved = resolve_basis(symbols, basis, self.tight_d)
            mol = gto.M(atom=atom_spec, basis=resolved, spin=spin, verbose=0,
                        unit="Angstrom")
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

    def _energy(
        self,
        atom_spec: str,
        symbols: tuple[str, ...],
        spin: int,
        cache_key: tuple | None = None,
    ) -> tuple[float, float]:
        """
        ``(total energy, signed extrapolation displacement)`` in Hartree at the configured tier.

        The second value is the signed amount by which the CBS model moved the answer beyond
        the larger basis, and it is zero for a plain request. Its magnitude is a sensitivity
        diagnostic, not a proven bound on remaining basis error.
        """
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]

        pair = self._is_cbs()
        if pair is None:
            hf, corr = self._parts(atom_spec, symbols, self.basis, spin)
            total, correction = hf + corr, 0.0
        else:
            small, large = pair
            x, y = _CARDINAL[large], _CARDINAL[small]
            hf_s, corr_s = self._parts(atom_spec, symbols, small, spin)
            hf_l, corr_l = self._parts(atom_spec, symbols, large, spin)
            # HF converges exponentially: take the larger basis directly.
            # Correlation converges as X^-3: extrapolate it, and only it.
            corr_cbs = (x**3 * corr_l - y**3 * corr_s) / (x**3 - y**3)
            total = hf_l + corr_cbs
            # SIGNED: it cancels between molecule and atoms in any conserving
            # difference, exactly as the arbitrary energy zero does.
            correction = corr_cbs - corr_l

        result = (total, correction)
        if cache_key is not None:
            self._cache[cache_key] = result
        return result

    def _atom_energy(self, symbol: str) -> tuple[float, float]:
        spin = ATOM_SPIN.get(symbol)
        if spin is None:
            raise KeyError(f"no ground-state spin known for {symbol}")
        # tight_d belongs in the key: E(S) with and without tight d are different numbers,
        # and a cache that conflated them would silently mix policies across a benchmark.
        return self._energy(
            f"{symbol} 0 0 0", (symbol,), spin,
            cache_key=("atom", symbol, self.basis, self.method, self.tight_d),
        )

    def _optimal_bond_length(self, a: str, b: str, spin: int, guess: float) -> float:
        """
        Local parabolic refinement over a small scan around a supplied bond-length guess.

        The current caller supplies a tabulated experimental ``r_e`` and still uses a
        tabulated frequency for ZPE. This therefore does *not* remove experimental geometry
        input or price an unlisted species; it measures method sensitivity near a known
        structure. A predictive path needs an independent seed and a computed frequency.

        Those five do not have to be paid at this oracle's tier. Locating a minimum and
        evaluating an energy at it are separable problems: the minimum's *position* is far
        less method-sensitive than the energy's *value*, because the error a method makes
        is nearly constant across the 0.12 A window scanned here and a constant shift moves
        a parabola's vertex not at all. So when ``geometry_tier`` is set the scan is
        delegated to a cheap oracle and only the final single point is paid for here.

        MEASURED -- see ``scratchpad/geometry_tier.py`` and the table in the module
        docstring. Unlike the basis-set policy this is not an error-cancellation hope; it
        is a claim about which sub-computation the answer is actually sensitive to, and it
        was checked against optimising at the full tier rather than argued from principle.
        """
        scanner = self._geom_oracle or self
        offsets = (-0.06, -0.03, 0.0, 0.03, 0.06)
        pts = []
        for d in offsets:
            r = guess + d
            # only the energy matters for locating the minimum; the extrapolation
            # correction is a property of the tier, not of the bond length
            pts.append((r, scanner._energy(f"{a} 0 0 0; {b} 0 0 {r}", (a, b), spin)[0]))
        # Fit the three points surrounding a discrete minimum. Three globally lowest
        # samples need not be adjacent and do not by themselves prove the scan brackets it.
        pts.sort()
        minimum = min(range(len(pts)), key=lambda index: pts[index][1])
        if minimum in (0, len(pts) - 1):
            raise GeometryError("bond-length scan does not bracket a local minimum")
        (r1, e1), (r2, e2), (r3, e3) = pts[minimum - 1:minimum + 2]
        denom = (r1 - r2) * (r1 - r3) * (r2 - r3)
        if abs(denom) < 1e-12:
            raise GeometryError("bond-length parabola is numerically singular")
        aa = (r3 * (e2 - e1) + r2 * (e1 - e3) + r1 * (e3 - e2)) / denom
        bb = (r3**2 * (e1 - e2) + r2**2 * (e3 - e1) + r1**2 * (e2 - e3)) / denom
        if aa <= 0:
            raise GeometryError("bond-length scan has nonpositive fitted curvature")
        vertex = -bb / (2 * aa)
        if not r1 <= vertex <= r3:
            raise GeometryError("fitted bond minimum lies outside its three-point bracket")
        return vertex

    def _polyatomic_energy(self, molecule: Molecule) -> Estimate | None:
        """
        Experimental polyatomic path; returns no public estimate without validation.

        THE DIVISION OF LABOUR
        ----------------------
        The geometry, the curvature and the energy VALUE are three different questions
        with three different sensitivities, and this method is where that stops being an
        observation and starts being a policy:

            coordinates : cheap tier (HF). The minimum's POSITION is far less
                          method-sensitive than the energy at it -- measured, MAE 0.0255 A
                          against 23 experimental diatomic r_e.
            zero-point  : cheap tier, same surface. The selected-diatomic protocol has an
                          aggregate +9.1% displacement, carried as a named sensitivity
                          rather than corrected away or called a calibrated bound.
            energy      : THIS oracle's tier, whatever it is. No algebra substitutes for
                          the wavefunction here, and nothing in this file pretends
                          otherwise.

        So one CCSD(T)/cbs(TZ,QZ) single point sits on top of a geometry and a ZPE that
        cost a small fraction of it. That is the geometry/energy separability already
        measured for diatomics, generalised, and it is what makes a polyatomic affordable
        at all rather than merely possible.

        WHY THE ZPE MATTERS MORE THAN IT LOOKS
        --------------------------------------
        Diatomics report D_0, subtracting a ZPE from the tabulated omega_e. A polyatomic
        has no tabulated frequencies. Reporting the electronic energy alone would mean
        quietly reporting D_e in a pipeline whose every other number is D_0 -- a 0.61 eV
        error for water, which is fourteen times the chemical-accuracy threshold this
        project quotes and would look like a bad method rather than a category error.

        The mechanics remain here for research and geometry validation, but the bundled
        seven-diatomic MAE does not quantify this protocol. The public oracle therefore
        declines before backend work unless a future domain-specific validation profile
        supplies an uncertainty model. It also declines when geometry/state checks fail.
        """
        if len(molecule.atoms) > self.max_atoms or not math.isfinite(
            self.nominal_accuracy_ev
        ):
            return None
        engine = self._geometry_engine()
        if engine is None:
            return None                      # no gradient-capable tier: decline
        spin = _closed_shell_spin(molecule)
        if spin is None:
            return None                      # an element with no data: decline

        t0 = time.perf_counter()
        try:
            coordinates, zpe = engine._relaxed_geometry(molecule, spin)
            spec = "; ".join(f"{s} {x:.10f} {y:.10f} {z:.10f}"
                             for s, (x, y, z) in zip(molecule.atoms, coordinates))
            e_elec, correction = self._energy(spec, molecule.atoms, spin)
        except (ConvergenceFailure, GeometryError, KeyError, NotImplementedError):
            return None                      # a number we do not trust is worse than none
        dt = time.perf_counter() - t0

        # The observed ZPE displacement does not cancel against free atoms -- they have no
        # vibrations -- so its signed coefficient survives into atomization energy. In a
        # related-energy difference the coefficient may cancel algebraically; residual
        # model errors require a future calibrated covariance model.
        zpe_bias = ZPE_BIAS_FRACTION * zpe
        return Estimate(
            value_ev=e_elec * HARTREE_EV + zpe,
            uncertainty_ev=self.nominal_accuracy_ev,
            method=self.name + "/geom",
            seconds=dt,
            notes=(f"E_elec={e_elec * HARTREE_EV:.4f} eV, ZPE={zpe:.4f} eV "
                   f"(harmonic, {engine.name}, +{ZPE_BIAS_FRACTION:.1%} measured bias "
                   f"carried as systematic), geometry relaxed at {engine.name}, "
                   f"spin {spin} assumed from electron parity"
                   + (f", CBS correction {correction * HARTREE_EV:+.4f} eV"
                      if correction else "")),
            systematic_ev=correction * HARTREE_EV + zpe_bias,
            systematic_terms=(
                (f"basis-extrapolation:{self.method}/{self.basis}/{self.tight_d}",
                 correction * HARTREE_EV),
                ("zpe:hf-harmonic-bias", zpe_bias),
            ),
        )

    # -- polyatomic geometry -----------------------------------------------------
    def _mean_field(self, atom_spec: str, symbols: tuple[str, ...], spin: int,
                    guess: "np.ndarray | None" = None):
        """
        A converged Hartree-Fock object, for gradients and Hessians.

        ``guess`` is a density matrix to start from. Along a geometry relaxation the
        geometry changes by a fraction of an Angstrom per step, so the previous step's
        converged density is a far better starting point than the atomic-density guess
        PySCF would build from scratch, and the SCF reaches the same fixed point in
        markedly fewer cycles.

        WHY THIS DOES NOT COST ACCURACY, AND THE ONE CASE WHERE IT COULD
        ----------------------------------------------------------------
        The converged answer is *defined* by ``conv_tol``, not by the path taken to it: a
        fixed point is a fixed point whichever direction you approach it from. So the
        energy is unchanged to within 1e-11 Hartree, which is eight orders of magnitude
        below the 0.3 eV bar this oracle reports. That is the honest form of a free
        speedup -- fewer iterations to the same number, not a cheaper number.

        The case where a starting guess genuinely CAN change the answer is a system with
        more than one SCF solution, where the guess decides which one you land in. That is
        real, not hypothetical. Two things make it acceptable here and both are worth
        stating rather than waving away: for closed-shell organics near equilibrium
        multiple solutions are not the regime, and along a relaxation *following the
        previous solution is the desirable behaviour* -- it is what keeps a geometry
        optimisation on one surface instead of hopping between them mid-descent.

        It is measured anyway, because "not the regime" is an argument and not a
        measurement: ``tests/test_geometry.py::TestTheGuessDoesNotMoveTheAnswer``.
        """
        _require_pyscf()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mol = gto.M(atom=atom_spec, basis=resolve_basis(symbols, self.basis,
                                                            self.tight_d),
                        spin=spin, verbose=0, unit="Angstrom")
            mf = (scf.RHF if spin == 0 else scf.UHF)(mol)
            mf.conv_tol = 1e-11
            mf.max_cycle = 300
            # a guess of the wrong shape is a guess for a different molecule; ignore it
            # rather than let PySCF fail obscurely on a broadcast
            usable = guess if (guess is not None
                               and np.shape(guess)[-1] == mol.nao_nr()) else None
            mf.kernel(dm0=usable)
            if not mf.converged:
                # a bad guess must never turn into a refusal: retry from PySCF's own
                # initial guess before giving up, so the fast path can only ever cost
                # time, never an answer
                if usable is not None:
                    mf.kernel(dm0=None)
                if not mf.converged:
                    raise ConvergenceFailure(f"SCF did not converge for {atom_spec}")
            return mol, mf

    def _relaxed_geometry(self, molecule: Molecule, spin: int):
        """
        ``(coordinates, zero-point energy in eV)`` for a polyatomic, or raise.

        The three steps live in ``smartchem.geometry`` and are deliberately not merged:
        seed from the bond graph, relax to a stationary point, then evaluate a same-tier
        Hessian for harmonic frequencies and a local-curvature check. The latter two steps
        both evaluate a wavefunction at this oracle's selected geometry tier. Transfer of
        that geometry to a higher-level single-point method is an approximation.

        A saddle is not simply refused. An imaginary frequency's eigenvector points
        DOWNHILL, so it is both the diagnosis and the repair: displace along it and relax
        again. H2O2 is the case that forced this. Its true minimum is skewed, dihedral
        about 113 degrees, but a symmetric graph seed relaxes to the TRANS-PLANAR form --
        a perfectly converged stationary point, gradient 1.7e-5, and a transition state
        for internal rotation with one imaginary mode at -632 cm^-1. Without the
        curvature check that stationary point would have been priced as a minimum with
        nothing visibly wrong.

        Refusal remains the fallback when the descent does not reach a minimum, because
        a species whose shape this machinery cannot resolve must not be priced anyway.
        """
        symbols = molecule.atoms
        # The previous step's converged density, carried forward as the next step's SCF
        # starting guess. One array, overwritten in place -- this is a warm start, not a
        # cache, so it costs O(nao^2) memory regardless of how long the descent runs.
        warm: dict[str, np.ndarray | None] = {"dm": None}

        def energy_and_gradient(coords: np.ndarray) -> tuple[float, np.ndarray]:
            spec = "; ".join(f"{s} {x:.10f} {y:.10f} {z:.10f}"
                             for s, (x, y, z) in zip(symbols, coords))
            _, mf = self._mean_field(spec, symbols, spin, guess=warm["dm"])
            warm["dm"] = mf.make_rdm1()
            return mf.e_tot, mf.nuc_grad_method().kernel()

        def certify(coords: np.ndarray):
            spec = "; ".join(f"{s} {x:.10f} {y:.10f} {z:.10f}"
                             for s, (x, y, z) in zip(symbols, coords))
            # the relaxation just converged here, so its final density is very nearly
            # this one -- the Hessian SCF starts a step away from its own answer
            mol, mf = self._mean_field(spec, symbols, spin, guess=warm["dm"])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                hessian = mf.Hessian().kernel()
            # isotope_avg=True is load-bearing: the bare call returns integer MASS
            # NUMBERS, shifting every frequency by sqrt(1.008) and every ZPE by 0.4%.
            return harmonic_analysis(mol.atom_mass_list(isotope_avg=True), coords,
                                     hessian)

        coordinates = seed_coordinates(molecule)
        for attempt in range(_MAX_DESCENTS + 1):
            _log.info("%s: relaxation attempt %d/%d starting",
                      _label(molecule), attempt + 1, _MAX_DESCENTS + 1)
            result = relax(coordinates, energy_and_gradient)
            _log.info("%s: relaxation %s after %d calls, max|grad| %.2e Ha/Bohr",
                      _label(molecule), "converged" if result.converged else "GAVE UP",
                      result.iterations, result.gradient_norm)
            if not result.converged:
                raise GeometryError(
                    f"relaxation did not converge for {symbols}: max gradient "
                    f"{result.gradient_norm:.2e} Ha/Bohr after {result.iterations} calls")
            _log.info("%s: building the Hessian to check the stationary point",
                      _label(molecule))
            analysis = certify(result.coordinates)
            if analysis.is_minimum:
                _log.info("%s: no imaginary harmonic modes detected, ZPE %.4f eV",
                          _label(molecule), analysis.zero_point_energy_ev)
                return result.coordinates, analysis.zero_point_energy_ev
            _log.info("%s: stationary point is a saddle (%d imaginary, lowest %.1f cm^-1)"
                      "; descending along the unstable mode", _label(molecule),
                      analysis.imaginary_modes, analysis.frequencies_cm[0])
            direction = analysis.unstable_direction()
            if direction is None or attempt == _MAX_DESCENTS:
                raise GeometryError(
                    f"relaxation of {symbols} reached a saddle, not a minimum, after "
                    f"{attempt + 1} attempt(s): {analysis.imaginary_modes} imaginary "
                    f"mode(s), lowest {analysis.frequencies_cm[0]:.1f} cm^-1")
            coordinates = result.coordinates + _DESCENT_STEP_ANGSTROM * direction

    def _geometry_engine(self) -> "PySCFOracle | None":
        """
        The oracle that will supply polyatomic coordinates, or None if none can.

        A CBS request is refused: the extrapolation is a model of basis-set error in an
        ENERGY, and there is no corresponding statement about a gradient, so extrapolating
        one would be inventing a quantity.

        WHEN A TIER IS NAMED, IT IS THE ONLY CANDIDATE
        ----------------------------------------------
        If ``geometry_tier`` is set and cannot do this job, the answer is None -- there is
        deliberately no fallback to ``self``. The first version did fall back, and it was
        wrong in a way that left no trace: ``PySCFOracle("HF", ..., geometry_tier=("MP2",
        ...))`` would quietly relax a polyatomic at HF while still reporting a method
        string of ``HF/cc-pVDZ//MP2/cc-pVDZ``, which says the geometry came from MP2.

        Nothing about the number would look wrong. That is a provenance lie, and the rule
        this file already lives by covers it: declining is allowed, inventing is not, and
        substituting a different method from the one named is a way of inventing.
        """
        candidates = (self._geom_oracle,) if self._geom_oracle is not None else (self,)
        for candidate in candidates:
            if candidate.method in _GEOMETRY_METHODS and candidate._is_cbs() is None:
                return candidate
        return None

    # -- oracle interface --------------------------------------------------------
    def energy(self, molecule: Molecule) -> Estimate | None:
        """
        Total energy of this species at 0 K, in eV: electronic energy plus ZPE.

        The zero is PySCF's own (total electronic energy, so CO is around -3074 eV). That
        is fine, and the reason it is fine is the arbitrary-zero contract in ``base.py``:
        only differences across conserving morphisms are ever asked for, and conservation
        makes the per-atom offset cancel exactly.

        Including ZPE here rather than leaving it to the caller means the derived
        atomization energy comes out as D_0 directly, which is what experiment tabulates:
        free atoms have no vibrational zero-point motion, so the ZPE survives the
        subtraction untouched.

        Declines rather than guesses when it has no supported geometry/state protocol.
        A limited polyatomic HF relaxation/Hessian path exists, but it is not a conformer,
        stereochemistry, spin-state, or broadly validated thermochemistry workflow.
        """
        atoms = molecule.atoms
        if len(atoms) > self.max_atoms:
            return None
        if not math.isfinite(self.fixed_diatomic_mae_ev):
            return None                      # this energy tier has no measured validation MAE
        if molecule.charge != 0:
            # Conserving charged reactions can use one consistent electronic-energy
            # reference, but this small benchmark does not validate ionic basis, state,
            # solvation or finite-size protocols. Decline for coverage, not because total
            # energies of ions are intrinsically undefined.
            return None
        if carries_unmodelled_physics(molecule):
            return None                      # excitations and quanta; see base.py
        if any(s not in ATOM_SPIN for s in atoms):
            return None                      # no ground-state spin known; decline

        if len(atoms) == 1:
            t0 = time.perf_counter()
            try:
                e, correction = self._atom_energy(atoms[0])
            except (ConvergenceFailure, KeyError):
                return None
            return Estimate(
                value_ev=e * HARTREE_EV,
                # Do not attach the tier's validation MAE independently to every atomic
                # component: the selected atomization benchmark calibrates the molecular
                # difference as one result. Per-element reference offsets cancel exactly
                # in conserving reactions. The observed extrapolation displacement rides
                # along signed; algebraic cancellation does not prove residual-error
                # cancellation.
                uncertainty_ev=0.0,
                method=self.name,
                seconds=time.perf_counter() - t0,
                notes=f"atom {atoms[0]}, spin {ATOM_SPIN[atoms[0]]}",
                systematic_ev=correction * HARTREE_EV,
                systematic_terms=((
                    f"basis-extrapolation:{self.method}/{self.basis}/{self.tight_d}",
                    correction * HARTREE_EV,
                ),),
            )

        if len(atoms) > 2:
            return self._polyatomic_energy(molecule)

        # The local optimizer is truth-centered on a tabulated r_e and retains a tabulated
        # frequency. It is not the fixed-geometry protocol measured by the benchmark and
        # has no separate validation scale, so fail before purchasing its scan.
        if self.optimize_geometry:
            return None

        a, b = atoms
        formula = _formula_key(atoms)
        geom = GEOMETRY.get(formula)
        if geom is None and not self.optimize_geometry:
            return None                      # no geometry supplied and none requested
        zpe = zero_point_energy_ev(formula)
        if zpe is None:
            # A bond-length optimisation does not provide vibrational curvature. Reporting
            # zero here silently mixed D_e with the D_0 values used everywhere else.
            return None
        r_e, _omega, mol_spin = geom if geom else (1.5, 0.0, 0)

        t0 = time.perf_counter()
        try:
            if self.optimize_geometry:
                r_e = self._optimal_bond_length(a, b, mol_spin, r_e)
            e_mol, correction = self._energy(
                f"{a} 0 0 0; {b} 0 0 {r_e}", (a, b), mol_spin)
        except (ConvergenceFailure, GeometryError, KeyError):
            # A number we do not trust is worse than no number. Decline.
            return None
        dt = time.perf_counter() - t0

        return Estimate(
            value_ev=e_mol * HARTREE_EV + zpe,
            uncertainty_ev=self.fixed_diatomic_mae_ev,
            method=self.name + ("/opt" if self.optimize_geometry else ""),
            seconds=dt,
            notes=f"E_elec={e_mol * HARTREE_EV:.4f} eV, ZPE={zpe:.4f} eV, r_e={r_e:.4f} A"
                  + (f", CBS correction {correction * HARTREE_EV:+.4f} eV"
                     if correction else "")
                  + ("" if geom else " (geometry optimised, no reference)"),
            systematic_ev=correction * HARTREE_EV,
            systematic_terms=((
                f"basis-extrapolation:{self.method}/{self.basis}/{self.tight_d}",
                correction * HARTREE_EV,
            ),),
        )


def _closed_shell_spin(molecule: Molecule) -> int | None:
    """
    The lowest spin consistent with the electron count, or None if it cannot be counted.

    An even electron count is taken as a singlet and an odd one as a doublet. That is an
    ASSUMPTION, not a derivation -- O2 is the standard counterexample, an even-electron
    molecule with a triplet ground state -- and it is why diatomics keep using the spins
    tabulated in ``data.reference.GEOMETRY`` rather than this. It is stated in the notes
    of every estimate that relies on it so the assumption travels with the number.
    """
    electrons = -molecule.charge
    for symbol in molecule.atoms:
        atom = PT.get(symbol)
        if atom is None:
            return None
        electrons += atom.atomic_number
    return electrons % 2


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
