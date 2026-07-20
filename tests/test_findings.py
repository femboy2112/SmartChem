"""
One regression test per defect found in the 2026-07-20 adversarial review.

Every test here is marked ``xfail(strict=True)`` while its defect is unfixed. That is a
deliberate ratchet:

  * today  -> the test XFAILs. The suite is green, and ``pytest -rx`` lists exactly what
              is known-broken, with the reason.
  * fixed  -> the test XPASSes, and ``strict=True`` turns an unexpected pass into a
              FAILURE. That forces the marker to be removed in the same commit as the fix.

So a defect cannot be quietly fixed without updating this file, and it cannot be quietly
left broken without showing up in the report. Remove the marker when you fix the defect;
never remove the test.

Findings are numbered to match the review. See also ``tests/test_laws.py`` for the
structural laws that make several of these defects unconstructible rather than merely
absent.
"""
from __future__ import annotations

import io
import contextlib
import subprocess
import sys
from pathlib import Path

import pytest

from smartchem.atoms import PT, Species
from smartchem.comonad import Env, Situated
from smartchem.monad import Reaction, ThermoEffect
from smartchem.engine import propose_bond
from smartchem.lattice import Poset
from smartchem.data import bonds, CHEMICAL_ACCURACY_EV

REPO = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------
def quiet(fn, *a, **k):
    """Run fn with stdout suppressed. The current engine prints from its hot path."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*a, **k)


def predicted_bond_ev(species: Species, env: Env | None = None) -> float | None:
    """Predicted bond energy in eV (positive = bound), or None if refused."""
    r = quiet(propose_bond, Situated(species, env or Env.standard()))
    prod, eff = r.outcomes[0]
    if eff.delta_h_ev == 0.0 and eff.delta_s_ev_k == 0.0:
        return None
    return -eff.delta_h_ev


def species_of(*symbols: str) -> Species:
    counts: dict = {}
    for s in symbols:
        atom = PT[s]
        counts[atom] = counts.get(atom, 0) + 1
    return Species.from_dict(counts)


def atom_count(s: Species) -> int:
    return sum(s.comp_dict.values())


# ----------------------------------------------------------------------------------
# Finding 1 — mass is not conserved (engine.py:140)
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F1: engine.py:140 builds the product from only "
                                       "two elements; the rest are silently dropped")
def test_f1_mass_conserved_three_elements():
    reactants = species_of("Fe", "O", "Cl")
    r = quiet(propose_bond, Situated(reactants, Env.standard()))
    product = r.outcomes[0][0]
    assert atom_count(product) == atom_count(reactants), (
        f"{reactants} -> {product}: {atom_count(reactants)} atoms in, "
        f"{atom_count(product)} out"
    )


@pytest.mark.xfail(strict=True, reason="F1: same defect, nitrogen-fixation case")
def test_f1_mass_conserved_nitrogen_fixation():
    reactants = Species.from_dict({PT["Mo"]: 1, PT["N"]: 2, PT["H"]: 2})
    r = quiet(propose_bond, Situated(reactants, Env.standard()))
    product = r.outcomes[0][0]
    assert atom_count(product) == atom_count(reactants)


@pytest.mark.xfail(strict=True, reason="F1: element identity must survive, not just count")
def test_f1_element_identity_conserved():
    reactants = species_of("Fe", "O", "Cl")
    r = quiet(propose_bond, Situated(reactants, Env.standard()))
    product = r.outcomes[0][0]
    assert set(product.comp_dict) == set(reactants.comp_dict)


# ----------------------------------------------------------------------------------
# Finding 2 — the environment comonad has no effect on most species
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F2: min(ionic,covalent) picks the covalent branch, "
                                       "which has no solvation term at all")
def test_f2_solvent_changes_ionic_bond_energy():
    nacl = species_of("Na", "Cl")
    vac = predicted_bond_ev(nacl, Env.standard())
    aq = predicted_bond_ev(nacl, Env.aqueous())
    assert vac is not None and aq is not None
    assert abs(vac - aq) > 0.01, (
        f"dielectric 1.0 -> 80.1 changed nothing: vacuum={vac:.4f} water={aq:.4f}"
    )


@pytest.mark.xfail(strict=True, reason="F2: energy must be monotone in dielectric for "
                                       "species with charge separation")
def test_f2_energy_monotone_in_dielectric():
    nacl = species_of("Na", "Cl")
    eps_values = [1.0, 10.0, 40.0, 80.1, 109.0]
    energies = [
        predicted_bond_ev(nacl, Env(298.15, 1.0, "test", eps, float("inf")))
        for eps in eps_values
    ]
    assert all(e is not None for e in energies)
    assert len(set(round(e, 6) for e in energies)) > 1, (
        f"identical across dielectric 1.0-109.0: {energies}"
    )


# ----------------------------------------------------------------------------------
# Finding 3 — catalysis is printed, not computed (network.py:77)
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F3: network.py:77 prints the closing step "
                                       "unconditionally; there is no returnable proof")
def test_f3_catalysis_returns_verifiable_evidence():
    from smartchem.network import ReactionGraph

    graph = ReactionGraph(Env.standard())
    mo = Species.from_dict({PT["Mo"]: 1})
    n2 = Species.from_dict({PT["N"]: 2})
    h2 = Species.from_dict({PT["H"]: 2})
    graph.seed([mo, n2, h2])
    quiet(graph.expand, max_iterations=2)
    result = quiet(graph.find_catalytic_cycles, catalyst=mo, substrate=n2, reactant=h2)

    # A catalytic cycle claim must be checkable: the catalyst must appear in both the
    # source and the target of the composite morphism. A bare True is not evidence.
    assert not isinstance(result, bool), (
        "find_catalytic_cycles returned a bare bool; a cycle claim must carry the "
        "morphism chain that closes it"
    )


# ----------------------------------------------------------------------------------
# Finding 4 — the certificate does not survive composition
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F4: Reaction.bind constructs Reaction(new_outcomes) "
                                       "without carrying metadata forward")
def test_f4_certificate_survives_bind():
    r = Reaction([(1, ThermoEffect(0.0, 0.0))],
                 metadata={"mechanism": "Ionic", "transfer_n": 3})
    composed = r.bind(lambda x: Reaction([(x, ThermoEffect(0.0, 0.0))]))
    assert composed.metadata is not None, "metadata dropped by bind"
    assert composed.metadata.get("mechanism") == "Ionic"


# ----------------------------------------------------------------------------------
# Finding 5 — bond energies are wrong, and some bonds are refused outright
# ----------------------------------------------------------------------------------
@pytest.mark.parametrize("formula", ["CO", "NO", "HCl"])
@pytest.mark.xfail(strict=True, reason="F5: these bonds are refused entirely; CO is the "
                                       "strongest known diatomic bond")
def test_f5_strong_bonds_are_not_refused(formula):
    ref = next(b for b in bonds() if b.formula == formula)
    got = predicted_bond_ev(species_of(*ref.atoms))
    assert got is not None, f"{formula} (D0 = {ref.d0_ev} eV) predicted not to bond at all"


@pytest.mark.xfail(strict=True, reason="F5: measured MAE is 3.28 eV against a claimed "
                                       "1 kcal/mol (0.043 eV)")
def test_f5_mae_reaches_chemical_accuracy():
    errors = []
    for ref in bonds():
        try:
            got = predicted_bond_ev(species_of(*ref.atoms))
        except (KeyError, IndexError):
            continue
        if got is None:
            continue
        errors.append(abs(got - ref.d0_ev))
    assert errors, "no reference bond could be evaluated at all"
    mae = sum(errors) / len(errors)
    assert mae < CHEMICAL_ACCURACY_EV, (
        f"MAE = {mae:.3f} eV ({mae * 23.0605:.1f} kcal/mol) over n={len(errors)}; "
        f"chemical accuracy is {CHEMICAL_ACCURACY_EV} eV"
    )


@pytest.mark.xfail(strict=True, reason="F5: NaCl is the textbook ionic compound and is "
                                       "predicted at ~3x its real strength")
def test_f5_ionic_bond_magnitude():
    ref = next(b for b in bonds() if b.formula == "NaCl")
    got = predicted_bond_ev(species_of("Na", "Cl"))
    assert got is not None
    assert abs(got - ref.d0_ev) < 1.0, f"NaCl predicted {got:.2f} eV vs {ref.d0_ev} eV"


# ----------------------------------------------------------------------------------
# Finding 6 — valency is hardcoded despite the documented claim
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F6: Atom.valence_cap is a hardcoded group/period "
                                       "rule and takes no Env, so it cannot respond to one")
def test_f6_valence_responds_to_environment():
    import inspect
    sig = inspect.signature(PT["C"].__class__.valence_cap.fget)
    assert "env" in sig.parameters, (
        "valence_cap takes no environment; THE_DIFFERENCE.md claims an extreme environment "
        "can shift carbon to 5 bonds, which is structurally impossible as written"
    )


# ----------------------------------------------------------------------------------
# Finding 7 — right answer, wrong mechanism
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F7: the Na+ refusal comes from valence_cap at "
                                       "engine.py:74, which skips the loop before the "
                                       "ionization arithmetic at line 80 ever runs")
def test_f7_sodium_refusal_is_energetic_not_a_cap():
    # Na has a 47 eV second ionization energy; Mg's is 15 eV. If the refusal were
    # energetic, raising the cap would not license Na(2+) while Mg(2+) stays licensed
    # purely on the strength of a cheaper ionization.
    na_cost = PT["Na"].ionization_cost(2)
    mg_cost = PT["Mg"].ionization_cost(2)
    assert na_cost > mg_cost  # sanity: the data really does say this

    mg_bonds = predicted_bond_ev(Species.from_dict({PT["Mg"]: 1, PT["F"]: 2}))
    assert mg_bonds is not None  # Mg is permitted...

    # ...and the reason Na is not must be visible in the energy, not the cap.
    assert PT["Na"].valence_cap > 1, (
        "Na is refused by a hardcoded cap of 1, not by its 52 eV double-ionization cost"
    )


# ----------------------------------------------------------------------------------
# Finding 8 — the lattice gate disagrees with the engine, and is dead code
# ----------------------------------------------------------------------------------
@pytest.mark.parametrize("symbol", ["H", "O", "N", "F", "Cl"])
@pytest.mark.xfail(strict=True, reason="F8: charge transfer is identically 0 for A-A pairs, "
                                       "so is_favorable says False for every homonuclear "
                                       "bond while the engine happily forms them")
def test_f8_lattice_gate_agrees_with_engine(symbol):
    atom = PT[symbol]
    engine_bonds = predicted_bond_ev(Species.from_dict({atom: 2})) is not None
    lattice_says = Poset.is_favorable(atom, atom)
    assert lattice_says == engine_bonds, (
        f"{symbol}2: engine bonds={engine_bonds} but Poset.is_favorable={lattice_says}"
    )


# ----------------------------------------------------------------------------------
# Finding 9 — photolysis cannot distinguish allotropes
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F9: avg_hardness is a per-atom average, so it is "
                                       "identical for O2, O3, O4... Real O3 is 1.10 eV "
                                       "and O2 is 5.12 eV")
def test_f9_ozone_distinguished_from_dioxygen():
    from smartchem.engine import verify_photolysis

    o = PT["O"]
    uv = Env.upper_atmosphere()
    o2_res = quiet(verify_photolysis, Situated(Species.from_dict({o: 2}), uv))
    o3_res = quiet(verify_photolysis, Situated(Species.from_dict({o: 3}), uv))
    # O3 dissociates at 1.1 eV; O2 needs 5.1 eV. A 5.0 eV photon must split exactly one.
    assert (o3_res is not None) != (o2_res is not None), (
        "a 5 eV photon treats O2 and O3 identically"
    )


# ----------------------------------------------------------------------------------
# Finding 10 — band gap formula is dimensionally invalid
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F10: (Z * chi)/eta is dimensionless (eV/eV) and is "
                                       "subtracted from hubbard_u in eV")
def test_f10_band_gap_is_dimensionally_consistent():
    # A dimensionally sound gap must be invariant under a change of energy unit: scale
    # every input energy by k and the gap must scale by exactly k.
    from smartchem.engine import verify_crystal_lattice
    from smartchem.atoms import Atom

    base = PT["Si"]
    k = 2.0
    scaled = Atom(
        symbol="Si", atomic_number=base.atomic_number, group=base.group,
        period=base.period,
        ie_list_ev=tuple(v * k for v in base.ie_list_ev),
        ea_list_ev=tuple(v * k for v in base.ea_list_ev),
        radius_pm=base.radius_pm, mass_amu=base.mass_amu,
    )
    eg1 = quiet(verify_crystal_lattice,
                Situated(Species.from_dict({base: 1}), Env.standard()), 4)
    eg2 = quiet(verify_crystal_lattice,
                Situated(Species.from_dict({scaled: 1}), Env.standard()), 4)
    assert abs(eg2 - k * eg1) < 1e-9 * max(1.0, abs(eg1)), (
        f"scaling all energies by {k} changed the gap by {eg2 / eg1 if eg1 else float('nan'):.4f}x, "
        f"not {k}x -- the formula mixes units"
    )


# ----------------------------------------------------------------------------------
# Finding 11 — the product is always the reactants
# ----------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="F11: propose_bond returns an endomorphism on the "
                                       "composition bag; no bond topology is ever built")
def test_f11_product_carries_bond_topology():
    r = quiet(propose_bond, Situated(species_of("Na", "Cl"), Env.standard()))
    product = r.outcomes[0][0]
    assert hasattr(product, "bonds"), (
        "product has no bond structure; it is the same composition bag as the reactants"
    )


# ----------------------------------------------------------------------------------
# Finding 12 — hygiene and crash surface
# ----------------------------------------------------------------------------------
def test_f12_no_duplicate_periodic_table_keys():
    """He is defined twice in atoms.py; the second wins and silently has mass 0.0."""
    import re
    src = (REPO / "smartchem" / "atoms.py").read_text()
    keys = re.findall(r'^\s*"([A-Za-z]{1,3})":\s*Atom\(', src, re.M)
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"duplicate periodic table entries: {dupes}"


def test_f12_no_debug_prints_in_engine():
    src = (REPO / "smartchem" / "engine.py").read_text()
    offenders = [
        line.strip()
        for line in src.splitlines()
        if "DEBUG" in line and "print" in line
    ]
    assert not offenders, f"debug prints left in the engine: {offenders}"


@pytest.mark.parametrize(
    "label,env",
    [
        ("zero dielectric", Env(298.15, 1.0, "x", 0.0, float("inf"))),
        ("zero wavelength", Env(298.15, 1.0, "x", 1.0, 0.0)),
    ],
)
@pytest.mark.xfail(strict=True, reason="F12: ZeroDivisionError on degenerate environments")
def test_f12_degenerate_environments_do_not_crash(label, env):
    quiet(propose_bond, Situated(species_of("Na", "Cl"), env))


@pytest.mark.xfail(strict=True, reason="F12: IndexError on an empty species")
def test_f12_empty_species_does_not_crash():
    quiet(propose_bond, Situated(Species.from_dict({}), Env.standard()))


@pytest.mark.xfail(strict=True, reason="F12: ThermoEffect.equilibrium_constant divides by "
                                       "temp_k with no guard")
def test_f12_zero_temperature_does_not_crash():
    ThermoEffect(-1.0, 0.0).equilibrium_constant(0.0)


@pytest.mark.xfail(strict=True, reason="F12: Reaction is frozen but holds a list and a "
                                       "dict, so it is unhashable")
def test_f12_reaction_is_hashable():
    hash(Reaction([(1, ThermoEffect(0.0, 0.0))], metadata={"a": 1}))


@pytest.mark.xfail(strict=True, reason="F12: adversarial.py:31 passes external_energy_ev, "
                                       "which Env no longer accepts")
def test_f12_shipped_scripts_run():
    failures = []
    for script in sorted(REPO.glob("*.py")):
        proc = subprocess.run(
            [sys.executable, script.name],
            cwd=REPO, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            last = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "?"
            failures.append(f"{script.name}: {last}")
    assert not failures, "scripts in the repo root exit non-zero:\n  " + "\n  ".join(failures)
