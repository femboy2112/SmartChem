"""
Coordinates for polyatomic species, built from the bond graph the object already carries.

WHY THIS MODULE EXISTS
----------------------
``PySCFOracle`` declined every species with more than two atoms. That was never an
interface limit -- ``energy(molecule)`` takes full structure and always has -- it was a
missing input. PySCF needs Cartesian coordinates and there was nowhere to get them.

The obvious fix is a lookup table of experimental geometries, which is what the diatomics
use. It does not scale: it covers exactly the species someone has already tabulated, and
the point of a search layer is to ask about species nobody has tabulated.

The categorical framing supplies a better answer, and it was already sitting in the type.
``category.Molecule`` carries **bond topology**, not just atom counts -- a decision made
for an unrelated reason (so that ``Na + Cl`` and ``NaCl`` could be different objects and
the reaction between them a genuine arrow). A bond graph is precisely the input a geometry
builder needs. The structure that made conservation enforceable also makes coordinates
derivable.

THE DECOMPOSITION
-----------------
Getting a geometry splits into three parts with genuinely different computational
characters, and keeping them apart is the whole design:

    1. SEED     graph -> approximate coordinates.  Pure combinatorics, microseconds,
                no wavefunction. Exact solid geometry (the tetrahedral angle is
                arccos(-1/3), not a fitted parameter) plus tabulated bond lengths.

    2. RELAX    approximate -> stationary point.  Needs the real potential surface, so
                this is quantum chemistry -- but it needs *gradients*, and gradients are
                cheap at a low tier and unavailable at CCSD(T) anyway.

    3. CERTIFY  stationary point -> proven minimum.  The Hessian's eigenvalues settle it.
                No imaginary frequency means a genuine local minimum.

Only step 2 touches an oracle, and it does not have to be the *expensive* oracle. That is
the geometry/energy separability already measured for diatomics (see
``PySCFOracle._optimal_bond_length``), generalised from one dimension to 3N.

WHAT STEP 3 BUYS THAT WAS NOT PART OF THE PLAN
----------------------------------------------
The Hessian is needed anyway, and not for elegance. Diatomic energies are reported as
D_0 -- they subtract a zero-point energy taken from tabulated harmonic frequencies. A
polyatomic has no tabulated frequencies, so without a Hessian the only options are to
report D_e (a *different quantity*, silently) or to report nothing.

For water that gap is 0.61 eV -- 14 kcal/mol, three hundred times the chemical-accuracy
threshold this project quotes. It is not a footnote. The Hessian closes it, and the same
matrix that supplies the ZPE proves the geometry is a minimum rather than a saddle. Two
requirements, one computation.

THE PROOF-STATUS DISCIPLINE
---------------------------
Deliberately borrowed from ~/SmartASM: *candidate generation never upgrades proof status.*
The seed is a guess and is treated as one -- VSEPR is a heuristic, and a heuristic that
lands in the wrong basin would otherwise produce a confident wrong answer. So the seed
proposes and the frequency analysis disposes. An imaginary frequency means the relaxation
found a saddle, and this module says so and declines rather than pricing a transition
state as if it were a molecule.

This module is deliberately free of any PySCF import. Steps 1 and 3 are linear algebra and
graph work; the caller injects step 2 as a callable. That keeps the geometry logic
unit-testable on a machine with no quantum chemistry installed, the same way
``resolve_basis`` is.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from .atoms import PT
from .category import Molecule
from .data.reference import GEOMETRY

#: Bohr radius in Angstrom -- the length unit PySCF gradients come back in.
BOHR_TO_ANGSTROM = 0.52917721092

#: Hartree/Bohr -> eV/Angstrom, for reporting a gradient norm in usable units.
HARTREE_PER_BOHR_TO_EV_PER_ANGSTROM = 27.211386245988 / BOHR_TO_ANGSTROM

#: cm^-1 -> eV, matching ``data.reference.CM_TO_EV``.
CM_TO_EV = 1.23984198e-4

#: Multiplicative shortening applied to a seed bond length per bond order, used ONLY with
#: the covalent-radius fallback, where the radii are single-bond radii by construction so
#: the correction has a defined starting point.
#:
#: It is deliberately NOT applied to a tabulated diatomic. That was tried and it made the
#: seed worse: the table stores an experimental r_e without recording the diatomic's own
#: bond order, and CO is formally a triple bond. Scaling CO's 1.128 A down by the
#: double-bond factor for the C=O bonds of CO2 gave 0.982 A against an experimental 1.16 --
#: 15% short, and short in the wrong direction, because the correction was computed from a
#: bond-order difference that was never measured. Left unscaled the same seed is 3% off.
#: Correcting for an unmeasured quantity is worse than not correcting at all.
_ORDER_SCALE = {1: 1.00, 2: 0.87, 3: 0.78}


class GeometryError(RuntimeError):
    """No usable geometry could be produced. Declining beats guessing at coordinates."""


# ======================================================================================
# Step 1: the seed -- pure graph work, no wavefunction
# ======================================================================================
def _valence_electrons(symbol: str) -> int | None:
    """
    Valence electron count from the group number, or None for the d-block.

    This is definitional, not fitted: oxygen is group 16, therefore six valence
    electrons. The d-block returns None because its lone-pair count is not a simple
    function of the group, and guessing would corrupt the coordination geometry.
    """
    atom = PT.get(symbol)
    if atom is None:
        return None
    if 1 <= atom.group <= 2:
        return atom.group
    if 13 <= atom.group <= 18:
        return atom.group - 10
    return None


def _electron_domains(molecule: Molecule, index: int) -> int:
    """
    VSEPR electron-domain count at one atom: sigma bonds plus lone pairs.

    A multiple bond is ONE domain -- the two electron pairs of a double bond occupy the
    same region of space, which is why CO2 is linear despite carbon having a bond-order
    sum of four. So neighbours are counted, not bond orders, and the bond-order sum is
    used only to work out how many electrons are left over as lone pairs.
    """
    neighbours = sum(1 for b in molecule.bonds if index in (b.i, b.j))
    valence = _valence_electrons(molecule.atoms[index])
    if valence is None:
        return neighbours                      # d-block: no lone-pair claim made
    shared = molecule.degree(index)            # total bond ORDER at this position
    lone_pairs = max(0, (valence - shared)) // 2
    return neighbours + lone_pairs


def _ideal_directions(n: int) -> np.ndarray:
    """
    ``n`` unit vectors in the standard VSEPR arrangement for ``n`` electron domains.

    Exact solid geometry, not fitted parameters: the tetrahedral angle is arccos(-1/3)
    because that is the angle between vertices of a regular tetrahedron. Above six
    domains this raises rather than inventing an arrangement.
    """
    if n <= 1:
        return np.array([[1.0, 0.0, 0.0]])
    if n == 2:
        return np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    if n == 3:
        return np.array([[math.cos(a), math.sin(a), 0.0]
                         for a in (0.0, 2 * math.pi / 3, 4 * math.pi / 3)])
    if n == 4:
        s = 1.0 / math.sqrt(3.0)
        return np.array([[s, s, s], [s, -s, -s], [-s, s, -s], [-s, -s, s]])
    if n == 5:
        return np.array([[1.0, 0.0, 0.0],
                         [-0.5, math.sqrt(3) / 2, 0.0],
                         [-0.5, -math.sqrt(3) / 2, 0.0],
                         [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
    if n == 6:
        return np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                         [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
    raise GeometryError(f"no standard arrangement for {n} electron domains")


def seed_bond_length(a: str, b: str, order: int) -> float:
    """
    A starting length for an ``a``-``b`` bond of the given order, in Angstrom.

    Preference order, best evidence first:

    1. The experimental diatomic r_e already tabulated in ``data.reference.GEOMETRY``,
       used AS IS. A C-H bond in methane is not identical to the CH radical's, but 1.12 A
       is a far better starting point than anything derived from radii -- and, per
       ``_ORDER_SCALE``, adjusting it for bond order makes it worse rather than better.
    2. The sum of covalent radii, scaled for bond order.

    Raises rather than inventing a length for an element with no radius on file.
    """
    key = f"{a}2" if a == b else None
    if key is None:
        for candidate in (f"{a}{b}", f"{b}{a}"):
            if candidate in GEOMETRY:
                key = candidate
                break
    if key is not None and key in GEOMETRY:
        return GEOMETRY[key][0]

    ra, rb = PT.get(a), PT.get(b)
    if ra is None or rb is None:
        raise GeometryError(f"no covalent radius on file for {a}-{b}")
    return (ra.radius_pm + rb.radius_pm) / 100.0 * _ORDER_SCALE.get(order, 1.0)


def seed_coordinates(molecule: Molecule) -> np.ndarray:
    """
    Approximate Cartesian coordinates (Angstrom, shape ``(n_atoms, 3)``) from the graph.

    Breadth-first placement outward from the most connected atom. Each atom's unplaced
    neighbours are put on the VSEPR directions for its electron-domain count, rotated so
    that one direction points back along the bond to its parent -- which is what makes
    the local angles come out right rather than merely the lengths.

    This is a CANDIDATE, in the SmartASM sense. It is never returned as an answer;
    ``relax`` moves it to a stationary point and ``harmonic_analysis`` decides whether
    that point is a minimum.

    Requires a connected molecule: a disconnected graph has no determinate relative
    placement of its pieces, and inventing a separation would be inventing a number.
    """
    n = len(molecule.atoms)
    if n == 0:
        raise GeometryError("cannot build coordinates for an empty molecule")
    if n == 1:
        return np.zeros((1, 3))
    if not molecule.is_connected():
        raise GeometryError(
            "seed_coordinates needs a connected molecule; a disconnected graph fixes no "
            "relative placement of its fragments"
        )

    adjacency: dict[int, list[tuple[int, int]]] = {i: [] for i in range(n)}
    for b in molecule.bonds:
        adjacency[b.i].append((b.j, b.order))
        adjacency[b.j].append((b.i, b.order))

    coords = np.zeros((n, 3))
    placed = {max(range(n), key=lambda i: len(adjacency[i]))}
    # (atom, direction it was approached FROM) -- None for the root, which is free
    queue: list[tuple[int, np.ndarray | None]] = [(next(iter(placed)), None)]

    while queue:
        current, incoming = queue.pop(0)
        children = [(j, order) for j, order in adjacency[current] if j not in placed]
        if not children:
            continue
        directions = _ideal_directions(_electron_domains(molecule, current))
        if incoming is None:
            available = list(directions)
        else:
            # Rotate the arrangement so its first direction points back at the parent,
            # then hand the remaining directions to the children. Without this the bond
            # angles would be arbitrary even though the lengths were right.
            rotation = _rotation_taking(directions[0], -incoming)
            rotated = directions @ rotation.T
            available = list(rotated[1:])
        if len(available) < len(children):
            raise GeometryError(
                f"atom {current} ({molecule.atoms[current]}) has {len(children)} "
                f"neighbours to place but only {len(available)} free directions"
            )
        for (child, order), direction in zip(children, available):
            length = seed_bond_length(molecule.atoms[current], molecule.atoms[child],
                                      order)
            unit = direction / np.linalg.norm(direction)
            coords[child] = coords[current] + length * unit
            placed.add(child)
            queue.append((child, unit))

    return coords


def _rotation_taking(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """
    A rotation matrix carrying unit vector ``source`` onto unit vector ``target``.

    Rodrigues' formula, with the antiparallel case handled explicitly because the cross
    product vanishes there and the general formula would divide by zero.
    """
    a = source / np.linalg.norm(source)
    b = target / np.linalg.norm(target)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-12:
        if c > 0:
            return np.eye(3)
        # antiparallel: rotate by pi about any axis perpendicular to a
        perp = np.array([1.0, 0.0, 0.0])
        if abs(a[0]) > 0.9:
            perp = np.array([0.0, 1.0, 0.0])
        axis = np.cross(a, perp)
        axis /= np.linalg.norm(axis)
        return 2.0 * np.outer(axis, axis) - np.eye(3)
    kmat = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])
    return np.eye(3) + kmat + kmat @ kmat * (1.0 / (1.0 + c))


# ======================================================================================
# Step 2: relaxation -- the only part that needs an oracle
# ======================================================================================
@dataclass(frozen=True)
class RelaxResult:
    """
    Where the relaxation stopped, and whether that point is trustworthy.

    ``converged`` reports the gradient test only. It says a stationary point was reached;
    it says nothing about whether that point is a minimum. That question belongs to
    ``harmonic_analysis``, and keeping the two apart is deliberate -- a saddle point
    satisfies the gradient test perfectly.
    """
    coordinates: np.ndarray
    energy_hartree: float
    gradient_norm: float
    converged: bool
    iterations: int

    @property
    def gradient_norm_ev_per_angstrom(self) -> float:
        return self.gradient_norm * HARTREE_PER_BOHR_TO_EV_PER_ANGSTROM


def _iteration_budget(n_atoms: int) -> int:
    """
    How many L-BFGS-B iterations a molecule of this size is allowed.

    MEASURED, at HF/cc-pVDZ, counting calls to first reach the 3e-5 gradient tolerance:

        C2H5OH    9 atoms, 21 DOF     93 calls
        C3H8     11 atoms, 27 DOF     99 calls
        C3H7OH   12 atoms, 30 DOF    113 calls

    The old flat cap of 100 iterations (about 108 calls) sat *inside* that range. C3H8
    converged with ONE call of margin -- its 2515.9 s number, the one the isodesmic study
    rests on, is correct but succeeded by luck -- and C3H7OH missed by five and was
    reported as a refusal for an hour of compute. A cap chosen for "small rigid species"
    had quietly become binding across the whole size range this project now works in, and
    it does not degrade gracefully: it is a wall, not a slope.

    Scaling with atom count is the fix rather than a bigger flat number, because the driver
    is the degrees of freedom (3N-6) the optimiser has to descend. Twenty per atom is
    roughly double the measured need, and generosity is nearly free here: L-BFGS-B stops
    when it converges, so a larger budget costs NOTHING for anything that already worked.
    It only spends time on species that would otherwise have been refused -- exactly where
    spending it is worthwhile.

    The cap is kept rather than removed because it still has a real job: bounding how long
    a genuinely pathological surface can run before the answer is honestly "no".
    """
    return max(100, 20 * n_atoms)


def relax(
    coordinates: np.ndarray,
    energy_and_gradient: Callable[[np.ndarray], tuple[float, np.ndarray]],
    max_iterations: int | None = None,
    gradient_tolerance: float = 3e-5,
) -> RelaxResult:
    """
    Move coordinates to a stationary point of whatever surface the callable describes.

    ``energy_and_gradient`` takes coordinates in Angstrom, shape ``(n, 3)``, and returns
    ``(energy in Hartree, gradient in Hartree/Bohr)`` -- PySCF's native convention, so no
    unit juggling happens at the call site where it would be easy to get wrong.

    L-BFGS-B in Cartesians. Internal coordinates converge in fewer steps for large
    flexible molecules; for the small rigid species this system targets the extra
    machinery would not pay for itself, and Cartesians have the advantage of not being
    able to construct an inconsistent internal-coordinate set.

    The six translation/rotation modes are left unconstrained. They are exactly flat, so
    the optimiser simply never moves along them, and projecting them out would add a
    failure mode without removing one.

    On the default tolerance: it was 3e-4 Ha/Bohr and that was too loose to mean
    anything. MgO's *seed* -- straight from the reference table, before any optimisation --
    already had a maximum gradient component of 2.97e-4, so the relaxation reported
    ``converged=True`` after a single call without moving an atom. The reported geometry
    was the experimental one echoed back, which is the most flattering possible wrong
    answer: it agrees with the reference exactly, for no reason. 3e-5 is tight enough that
    a seed cannot pass it by luck.

    That tolerance is NOT the knob to reach for when a large molecule fails to converge.
    C3H7OH stopped at 2.02e-4 and loosening to admit it would land almost exactly back on
    the 3e-4 that let MgO's seed pass untouched. The budget was the problem; see
    ``_iteration_budget``.

    Note this function contains no chemistry at all -- it is handed a scalar field and
    finds a stationary point of it. That is what makes it testable against an analytic
    surface whose minimum is known in closed form, with no oracle in the loop.

    ON NOT RECOMPUTING THE FINAL GRADIENT
    -------------------------------------
    This used to end by calling ``energy_and_gradient(result.x)`` again to get the
    gradient for the convergence test. That call was pure waste: L-BFGS-B already returns
    ``result.jac``, and it is the gradient AT ``result.x``, not at some earlier trial
    point. Measured rather than assumed -- over 200 randomised quadratic surfaces plus
    Rosenbrock and a line-search-rejecting case, ``result.jac`` and a fresh evaluation at
    ``result.x`` agree to **0.0 exactly**, and that is pinned in
    ``tests/test_geometry.py::TestTheFinalGradientIsNotRecomputed``.

    The saving is one whole oracle call per relaxation. For a scalar field that is
    nothing; for a polyatomic it is a converged SCF plus an analytic gradient, and the
    point of writing it down is that this is the *free* kind of speedup -- the answer is
    bit-for-bit what it was, because the number was already computed and then discarded.
    """
    from scipy.optimize import minimize

    shape = coordinates.shape
    if max_iterations is None:
        max_iterations = _iteration_budget(shape[0])
    calls = {"n": 0}

    def objective(flat: np.ndarray) -> tuple[float, np.ndarray]:
        calls["n"] += 1
        energy, gradient = energy_and_gradient(flat.reshape(shape))
        # gradient arrives in Hartree/Bohr but the variable is Angstrom; the chain rule
        # is the whole conversion, and skipping it would scale every step by 1.89.
        return energy, np.asarray(gradient).reshape(-1) * BOHR_TO_ANGSTROM

    result = minimize(
        objective, coordinates.reshape(-1), jac=True, method="L-BFGS-B",
        options={"maxiter": max_iterations, "gtol": gradient_tolerance * BOHR_TO_ANGSTROM,
                 "ftol": 1e-12},
    )
    final = result.x.reshape(shape)
    # undo the Angstrom chain-rule factor the objective applied, so the convergence test
    # is made in Hartree/Bohr -- the same units the tolerance is quoted in.
    gradient = np.asarray(result.jac) / BOHR_TO_ANGSTROM
    norm = float(np.max(np.abs(gradient)))
    return RelaxResult(
        coordinates=final,
        energy_hartree=float(result.fun),
        gradient_norm=norm,
        converged=bool(norm <= gradient_tolerance),
        iterations=calls["n"],
    )


# ======================================================================================
# Step 3: certification -- is this point a minimum, and what is its zero-point energy?
# ======================================================================================
@dataclass(frozen=True)
class VibrationalAnalysis:
    """
    Harmonic frequencies at a stationary point, and the verdict they deliver.

    ``imaginary_modes`` is the certificate. A genuine local minimum has none; every
    imaginary frequency is a direction in which the energy goes DOWN, which means the
    relaxation stopped on a saddle. A saddle is a transition state, not a molecule, and
    pricing one as if it were a molecule is exactly the silent wrong answer this project
    treats as the unforgivable defect.
    """
    frequencies_cm: np.ndarray
    zero_point_energy_ev: float
    imaginary_modes: int
    #: Cartesian displacements, shape ``(n_modes, n_atoms, 3)``, ordered with
    #: ``frequencies_cm``. Carried because an imaginary mode is not merely a diagnosis --
    #: its eigenvector points DOWNHILL, so it is also the repair. See ``descend_from``.
    modes: np.ndarray | None = None

    @property
    def is_minimum(self) -> bool:
        return self.imaginary_modes == 0

    def unstable_direction(self) -> np.ndarray | None:
        """
        The Cartesian displacement along the most unstable mode, or None at a minimum.

        Normalised to unit maximum atomic displacement so a caller can scale it in
        Angstrom without knowing how the modes happen to be normalised.
        """
        if self.is_minimum or self.modes is None:
            return None
        direction = self.modes[int(np.argmin(self.frequencies_cm))]
        largest = np.max(np.abs(direction))
        return direction / largest if largest > 0 else None


def _external_modes(masses_amu: np.ndarray, coordinates: np.ndarray) -> np.ndarray:
    """
    An orthonormal basis for the translations and rotations, mass-weighted.

    Six vectors for a general molecule, five for a linear one -- but the count is not
    assumed here. The vectors are built and then orthonormalised by SVD, which discovers
    the true rank: for a linear molecule the rotation about the molecular axis comes out
    as a null vector and is dropped automatically. That is better than branching on a
    linearity test, because the test needs a tolerance and the SVD does not.
    """
    n = len(masses_amu)
    root_mass = np.sqrt(masses_amu)
    centre = (masses_amu[:, None] * coordinates).sum(axis=0) / masses_amu.sum()
    relative = coordinates - centre

    vectors = []
    for axis in range(3):                                  # three translations
        vector = np.zeros((n, 3))
        vector[:, axis] = root_mass
        vectors.append(vector.reshape(-1))
    for axis in range(3):                                  # three rotations
        unit = np.zeros(3)
        unit[axis] = 1.0
        vectors.append((root_mass[:, None] * np.cross(unit, relative)).reshape(-1))

    stacked = np.array(vectors)
    u, singular, _ = np.linalg.svd(stacked.T, full_matrices=False)
    return u[:, singular > 1e-8 * max(singular[0], 1e-30)]


def harmonic_analysis(
    masses_amu: Sequence[float],
    coordinates: np.ndarray,
    hessian_hartree_bohr2: np.ndarray,
) -> VibrationalAnalysis:
    """
    Frequencies and zero-point energy from a mass-weighted, Eckart-projected Hessian.

    ``hessian`` has shape ``(n, n, 3, 3)`` (PySCF's layout) or ``(3n, 3n)``.
    ``coordinates`` are in Angstrom; only their relative geometry matters here, since a
    uniform scale changes the rotation vectors by a constant factor and they are
    normalised immediately.

    WHY PROJECTION RATHER THAN DROPPING THE SMALLEST EIGENVALUES
    -----------------------------------------------------------
    This started out simpler: mass-weight, diagonalise, discard the six eigenvalues
    smallest in magnitude. That is the textbook shortcut and it is wrong by a small,
    entirely avoidable amount. Checked against PySCF's independently written
    ``thermo.harmonic_analysis`` on the same Hessian for water it disagreed by 15.8 cm^-1
    -- the rotational modes are only exactly zero at an exactly converged minimum, so at a
    numerically converged one they mix into the genuine vibrations and drag them.

    Projecting the external subspace out first removes the mixing rather than hoping it is
    negligible. The shortcut would have produced ZPEs that looked entirely plausible and
    were quietly a few tenths of a percent off, which is the failure mode this project
    treats as the unforgivable one.

    A negative eigenvalue gives an imaginary frequency, reported as a NEGATIVE wavenumber
    by the usual convention and counted in ``imaginary_modes``. Imaginary modes are
    excluded from the ZPE sum: the harmonic zero-point formula assumes a real oscillator
    and applying it to an unbound direction would produce a meaningless number.
    """
    masses = np.asarray(masses_amu, dtype=float)
    n = len(masses)
    hessian = np.asarray(hessian_hartree_bohr2)
    if hessian.ndim == 4:
        hessian = hessian.transpose(0, 2, 1, 3).reshape(3 * n, 3 * n)
    # symmetrise: analytic Hessians are symmetric in exact arithmetic, and enforcing it
    # lets eigvalsh be used, which cannot return spurious complex eigenvalues
    hessian = 0.5 * (hessian + hessian.T)

    inverse_sqrt_mass = np.repeat(1.0 / np.sqrt(masses), 3)
    weighted = hessian * inverse_sqrt_mass[:, None] * inverse_sqrt_mass[None, :]

    external = _external_modes(masses, np.asarray(coordinates, dtype=float))
    projector = np.eye(3 * n) - external @ external.T
    projected = projector @ weighted @ projector

    eigenvalues, eigenvectors = np.linalg.eigh(projected)
    # after projection the external modes are numerically zero; drop exactly as many as
    # the SVD said there were, so a linear molecule keeps its extra vibration
    n_external = external.shape[1]
    internal = np.argsort(np.abs(eigenvalues))[n_external:]
    vibrational = eigenvalues[internal]
    vectors = eigenvectors[:, internal]

    # sqrt(Hartree / (Bohr^2 amu)) -> cm^-1. Stated once so the unit chain lives in one
    # place; a sign-preserving sqrt reports unstable modes as negative wavenumbers.
    to_wavenumber = 5140.4871
    frequencies = np.sign(vibrational) * np.sqrt(np.abs(vibrational)) * to_wavenumber
    order = np.argsort(frequencies)
    frequencies = frequencies[order]
    # un-mass-weight: an eigenvector of the mass-weighted Hessian is not a displacement
    # until it is divided by sqrt(mass) again
    modes = (vectors[:, order].T.reshape(-1, n, 3) * inverse_sqrt_mass.reshape(n, 3))

    real = frequencies[frequencies > 0]
    return VibrationalAnalysis(
        frequencies_cm=frequencies,
        zero_point_energy_ev=float(0.5 * real.sum() * CM_TO_EV),
        imaginary_modes=int(np.sum(frequencies < 0)),
        modes=modes,
    )


def is_linear(coordinates: np.ndarray, tolerance: float = 1e-3) -> bool:
    """
    True when every atom lies on one line.

    Decided by the smallest singular value of the centred coordinates: a set of points is
    collinear exactly when its centred matrix has rank one.

    This used to be what told ``harmonic_analysis`` whether to expect five external modes
    or six. It no longer is -- the SVD in ``_external_modes`` discovers the rank itself, so
    a linear molecule keeps its extra vibration with no flag to pass and no tolerance to
    tune. What survives here is a plain predicate about a shape, which is worth having for
    checking that a seed came out the right shape at all (CO2 linear, water not).
    """
    if len(coordinates) <= 2:
        return True
    centred = coordinates - coordinates.mean(axis=0)
    singular = np.linalg.svd(centred, compute_uv=False)
    return bool(singular[1] < tolerance * max(singular[0], 1e-12))
