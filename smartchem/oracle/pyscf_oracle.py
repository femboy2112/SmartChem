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

Basis choice is a function of the elements -- and measuring that did not pay off
--------------------------------------------------------------------------------
The reasoning was: extrapolation only removes error the basis family is *converging
toward*, and two deficiencies survive it because they are present at every cardinal --
diffuse functions for ionic species, tight d for second-row elements (Al-Ar). Both are
properties of the elements involved, so ``resolve_basis`` computes the basis per element
rather than taking one name for the whole molecule.

The machinery is real, tested, and available (``tight_d=True``, ``aug-`` prefixes). **It
is also not recommended, because it was measured and it lost**: 2.94 kcal/mol against 1.30
for plain ``cbs(TZ,QZ)``, at 5.1x the cost. See ``_NOMINAL`` below for the breakdown.

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

This is also where the categorical layer earns its keep. Pruning by conservation, charge
balance and valence happens *before* any call into this module, so the expensive oracle is
only ever asked about candidates that are already structurally valid.
"""
from __future__ import annotations

import re
import time
import warnings

from .base import BaseOracle, Estimate
from ..category import Molecule
from ..data.basis_tight_d import SECOND_ROW, TIGHT_D
from ..data.reference import ATOM_SPIN, GEOMETRY, zero_point_energy_ev

try:
    from pyscf import gto, scf, mp, cc
except ImportError as exc:  # pragma: no cover - exercised by absence, not presence
    raise ImportError("PySCFOracle requires pyscf: pip install 'smartchem[qc]'") from exc

HARTREE_EV = 27.211386245988

#: Cardinal number X for each correlation-consistent basis, used by the X^-3 extrapolation.
#: Diffuse augmentation does not change the cardinal -- aug-cc-pVTZ is still X=3 -- so the
#: extrapolation is unaffected by the aug- prefix.
_CARDINAL = {
    "cc-pVDZ": 2, "cc-pVTZ": 3, "cc-pVQZ": 4, "cc-pV5Z": 5,
    "aug-cc-pVDZ": 2, "aug-cc-pVTZ": 3, "aug-cc-pVQZ": 4, "aug-cc-pV5Z": 5,
}

#: Matches a correlation-consistent basis name so its tight-d variant can be named.
_CC_NAME = re.compile(r"^((?:aug-)?cc-pV)([DTQ5])(Z)$")

#: Methods in increasing order of cost and accuracy.
_METHODS = ("HF", "MP2", "CCSD", "CCSD(T)")

#: MEASURED mean absolute error in eV, on ONE declared species set, 2026-07-20.
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
#: energy is already in the smooth X^-3 tail by TZ -- does not hold for an ionic species.
#: This is no longer reported with false confidence: the extrapolation correction is
#: carried on every Estimate and widens the error bar by however much of it survives
#: cancellation (NaCl gets +/-0.13 eV rather than the tier's nominal +/-0.04).
_NOMINAL = {
    ("HF", "cc-pVDZ"): 2.44, ("HF", "cc-pVTZ"): 2.40, ("HF", "cc-pVQZ"): 2.58,
    ("CCSD(T)", "cc-pVDZ"): 0.57,
    ("CCSD(T)", "cc-pVTZ"): 0.22,
    ("CCSD(T)", "cc-pVQZ"): 0.08,
    ("CCSD(T)", "cbs(TZ,QZ)"): 0.041,
    ("CCSD(T)", "aug-cbs(TZ,QZ)+d"): 0.128,
}


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
    return {
        s: (gto.basis.parse(TIGHT_D[plus_d], symb=s) if s in SECOND_ROW else basis)
        for s in set(symbols)
    }


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
        tight_d: bool = True,
        geometry_tier: tuple[str, str] | None = None,
    ):
        if method not in _METHODS:
            raise ValueError(f"method must be one of {_METHODS}, got {method!r}")
        self.method = method
        self.basis = basis
        self.optimize_geometry = optimize_geometry
        self.max_atoms = max_atoms
        self.tight_d = tight_d
        # The name records the policy, not just the basis: a result computed with tight d
        # on sulfur is not the same result as one without, and provenance has to say so.
        self.name = f"{method}/{basis}" + ("+d" if tight_d else "")
        self.nominal_accuracy_ev = _NOMINAL.get((method, self.name.split("/", 1)[1]), 0.30)
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

    # -- internals ---------------------------------------------------------------
    def _is_cbs(self) -> tuple[str, str] | None:
        """
        Return the (small, large) basis pair if this is a CBS request.

        Accepts ``cbs(TZ,QZ)`` and ``aug-cbs(TZ,QZ)``; the prefix carries through to both
        members, since extrapolating an augmented basis against a plain one would compare
        two different families and the X^-3 form would be meaningless.
        """
        name = self.basis
        prefix = ""
        if name.lower().startswith("aug-"):
            prefix, name = "aug-", name[4:]
        if not name.lower().startswith("cbs"):
            return None
        inner = name[name.index("(") + 1: name.index(")")]
        small, large = (s.strip() for s in inner.split(","))
        expand = {"DZ": "cc-pVDZ", "TZ": "cc-pVTZ", "QZ": "cc-pVQZ", "5Z": "cc-pV5Z"}
        return prefix + expand.get(small, small), prefix + expand.get(large, large)

    def _parts(
        self, atom_spec: str, symbols: tuple[str, ...], basis: str, spin: int
    ) -> tuple[float, float]:
        """(E_HF, E_corr) in Hartree. Raises ConvergenceFailure rather than guessing."""
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
        ``(total energy, |extrapolation correction|)`` in Hartree at the configured tier.

        The second value is how far the CBS extrapolation moved the answer beyond the
        larger basis, and it is zero for a plain single-basis request. It exists because
        the extrapolation is a *model* of the remaining basis-set error, and a model that
        applies a large correction has earned a large error bar -- see ``energy``.
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
        Parabolic minimisation over a small scan. Removes the experimental geometry
        input at the cost of ~5 extra energy evaluations.

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

        Declines rather than guesses when it has no geometry. That is the whole reason
        polyatomic work is currently out of reach -- not the interface, which now expresses
        it fine, but the absence of a geometry source.
        """
        atoms = molecule.atoms
        if molecule.charge != 0:
            return None                      # ions need a different reference; decline
        if any(s not in ATOM_SPIN for s in atoms):
            return None                      # no ground-state spin known; decline

        if len(atoms) == 1:
            t0 = time.perf_counter()
            try:
                e, correction = self._atom_energy(atoms[0])
            except (ConvergenceFailure, KeyError, RuntimeError):
                return None
            return Estimate(
                value_ev=e * HARTREE_EV,
                # The atomic reference is shared by every species containing this element,
                # so its systematic error cancels in any conserving difference. The
                # extrapolation correction rides along signed, to cancel the same way.
                uncertainty_ev=0.0,
                method=self.name,
                seconds=time.perf_counter() - t0,
                notes=f"atom {atoms[0]}, spin {ATOM_SPIN[atoms[0]]}",
                extrapolation_ev=correction * HARTREE_EV,
            )

        if len(atoms) != 2:
            # Not an interface limit any more -- a missing geometry source. A polyatomic
            # needs coordinates this oracle has no way to obtain.
            return None

        a, b = atoms
        formula = _formula_key(atoms)
        geom = GEOMETRY.get(formula)
        if geom is None and not self.optimize_geometry:
            return None                      # no geometry supplied and none requested
        r_e, _omega, mol_spin = geom if geom else (1.5, 0.0, 0)

        t0 = time.perf_counter()
        try:
            if self.optimize_geometry:
                r_e = self._optimal_bond_length(a, b, mol_spin, r_e)
            e_mol, correction = self._energy(
                f"{a} 0 0 0; {b} 0 0 {r_e}", (a, b), mol_spin)
        except (ConvergenceFailure, KeyError, RuntimeError):
            # A number we do not trust is worse than no number. Decline.
            return None
        dt = time.perf_counter() - t0

        zpe = zero_point_energy_ev(formula) or 0.0
        return Estimate(
            value_ev=e_mol * HARTREE_EV + zpe,
            uncertainty_ev=self.nominal_accuracy_ev,
            method=self.name + ("/opt" if self.optimize_geometry else ""),
            seconds=dt,
            notes=f"E_elec={e_mol * HARTREE_EV:.4f} eV, ZPE={zpe:.4f} eV, r_e={r_e:.4f} A"
                  + (f", CBS correction {correction * HARTREE_EV:+.4f} eV"
                     if correction else "")
                  + ("" if geom else " (geometry optimised, no reference)"),
            extrapolation_ev=correction * HARTREE_EV,
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
