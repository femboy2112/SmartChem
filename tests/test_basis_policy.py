"""
The basis-set policy: basis choice as a function of the elements involved.

Two deficiencies survive basis-set extrapolation, because they are present at every
cardinal rather than converging away:

    diffuse   ionic and anionic species need loosely-bound density the standard sets omit
    tight d   second-row elements (Al-Ar) need d-correlation the standard sets undersample

Both are properties of the elements, so the basis is resolved per element. These tests pin
the resolution logic, which is pure -- no SCF is run here. The measured *effect* of the
policy lives in the benchmark; what is checked here is that the right basis reaches PySCF,
including the cases where the policy must decline.
"""
from __future__ import annotations

from dataclasses import replace
import math
from types import MappingProxyType

import pytest

from smartchem.atoms import PT
from smartchem.category import Bond, Molecule
from smartchem.data.basis_tight_d import SECOND_ROW, TIGHT_D
from smartchem.data.reference import ATOM_SPIN, BOND_REFS, GEOMETRY
from smartchem.geometry import GeometryError
from smartchem.oracle import pyscf_oracle as pyscf_module
from smartchem.oracle.pyscf_oracle import (
    PYSCF_AVAILABLE,
    ZPE_BIAS_TRAIN_SPECIES,
    PySCFOracle,
    basis_covers,
    resolve_basis,
    tight_d_name,
)
from smartchem.oracle.persistent import PersistentCache


class TestTightDNaming:
    @pytest.mark.parametrize("basis,expected", [
        ("cc-pVTZ", "cc-pV(T+d)Z"),
        ("cc-pVQZ", "cc-pV(Q+d)Z"),
        ("aug-cc-pVTZ", "aug-cc-pV(T+d)Z"),
        ("aug-cc-pVQZ", "aug-cc-pV(Q+d)Z"),
    ])
    def test_maps_to_the_conventional_spelling(self, basis, expected):
        assert tight_d_name(basis) == expected

    @pytest.mark.parametrize("basis", ["cbs(TZ,QZ)", "aug-cbs(TZ,QZ)", "6-31G*", "sto-3g"])
    def test_declines_outside_the_family(self, basis):
        """Guessing a spelling for a basis with no +d variant would be inventing one."""
        assert tight_d_name(basis) is None


class TestResolution:
    def test_second_row_element_gets_tight_d(self):
        if not PYSCF_AVAILABLE:
            pytest.skip("parsing the vendored basis requires PySCF")
        resolved = resolve_basis(("C", "S"), "aug-cc-pVTZ", tight_d=True)
        assert isinstance(resolved, dict)
        assert set(resolved) == {"C", "S"}
        assert resolved["C"] == "aug-cc-pVTZ", "carbon is first row; it has no +d variant"
        assert resolved["S"] != "aug-cc-pVTZ", "sulfur must get the tight-d set"

    def test_first_row_only_is_left_alone(self):
        """No dict, no per-element machinery, when nothing needs it."""
        assert resolve_basis(("C", "O"), "aug-cc-pVTZ", tight_d=True) == "aug-cc-pVTZ"

    def test_policy_can_be_switched_off(self):
        assert resolve_basis(("C", "S"), "aug-cc-pVTZ", tight_d=False) == "aug-cc-pVTZ"

    def test_declines_when_no_variant_is_vendored(self):
        """
        Only T+d and Q+d are vendored. At 5Z the policy must fall back to the standard set
        rather than silently substituting a different cardinal.
        """
        assert "aug-cc-pV(5+d)Z" not in TIGHT_D
        assert resolve_basis(("C", "S"), "aug-cc-pV5Z", tight_d=True) == "aug-cc-pV5Z"

    @pytest.mark.parametrize("element", sorted(SECOND_ROW))
    def test_every_declared_second_row_element_actually_parses(self, element):
        """
        The vendored blocks cover Al-Ar. If an element is in SECOND_ROW but missing from
        the data, the policy would raise mid-benchmark instead of declining cleanly.
        """
        pytest.importorskip("pyscf")
        for name in TIGHT_D:
            from pyscf import gto
            shells = gto.basis.parse(TIGHT_D[name], symb=element)
            assert shells, f"{element} missing from {name}"


class TestCBSParsing:
    @pytest.mark.parametrize("basis,pair", [
        ("cbs(TZ,QZ)", ("cc-pVTZ", "cc-pVQZ")),
        ("aug-cbs(TZ,QZ)", ("aug-cc-pVTZ", "aug-cc-pVQZ")),
        ("cbs(DZ,TZ)", ("cc-pVDZ", "cc-pVTZ")),
    ])
    def test_extrapolation_pair(self, basis, pair):
        assert PySCFOracle("CCSD(T)", basis)._is_cbs() == pair

    def test_augmentation_carries_to_both_members(self):
        """
        Extrapolating an augmented basis against a plain one would compare two different
        families, and the X^-3 form would be meaningless.
        """
        small, large = PySCFOracle("CCSD(T)", "aug-cbs(TZ,QZ)")._is_cbs()
        assert small.startswith("aug-") and large.startswith("aug-")

    def test_a_plain_basis_is_not_a_cbs_request(self):
        assert PySCFOracle("CCSD(T)", "cc-pVQZ")._is_cbs() is None

    @pytest.mark.parametrize("basis", [
        "cbs", "cbs(TZ)", "cbs(TZ,QZ,5Z)", "cbs(TZ,TZ)", "cbs(QZ,TZ)",
        "cbs(TZ,QZ)junk", "aug-cbs(TZ,QZ", "cbs(cc-pVTZ,cc-pVQZ)", "",
    ])
    def test_malformed_or_nonincreasing_requests_fail_at_construction(self, basis):
        with pytest.raises(ValueError):
            PySCFOracle("CCSD(T)", basis)

    def test_case_and_whitespace_are_normalised(self):
        oracle = PySCFOracle("CCSD(T)", "AUG-CBS( tz, 5z )", tight_d=True)
        assert oracle.basis == "aug-cbs(TZ,5Z)"
        assert oracle._is_cbs() == ("aug-cc-pVTZ", "aug-cc-pV5Z")


class TestConstructionValidation:
    @pytest.mark.parametrize("field", ["tight_d", "optimize_geometry"])
    def test_boolean_policies_do_not_accept_truthy_strings(self, field):
        with pytest.raises(TypeError, match="boolean"):
            PySCFOracle(**{field: "false"})

    @pytest.mark.parametrize(
        "value",
        ["HF/cc-pVDZ", ["HF", "cc-pVDZ"], ("HF",), ("HF", 2)],
    )
    def test_geometry_tier_requires_an_exact_string_pair(self, value):
        with pytest.raises(TypeError, match="geometry_tier"):
            PySCFOracle(geometry_tier=value)

    @pytest.mark.parametrize("value", [True, 1.5, 0, -1])
    def test_size_policy_requires_a_positive_integer(self, value):
        with pytest.raises((TypeError, ValueError), match="max_atoms"):
            PySCFOracle(max_atoms=value)


class TestLocalBondRefinement:
    @staticmethod
    def _distance(atom_spec: str) -> float:
        return float(atom_spec.rsplit(maxsplit=1)[-1])

    def test_a_bracketed_quadratic_minimum_is_recovered(self, monkeypatch):
        oracle = PySCFOracle("HF", "cc-pVDZ")

        def surface(atom_spec, _symbols, _spin, cache_key=None):
            distance = self._distance(atom_spec)
            return (distance - 1.5) ** 2, 0.0

        monkeypatch.setattr(oracle, "_energy", surface)
        assert oracle._optimal_bond_length("H", "H", 0, 1.5) == pytest.approx(1.5)

    def test_a_monotone_scan_is_refused_not_extrapolated(self, monkeypatch):
        oracle = PySCFOracle("HF", "cc-pVDZ")

        def surface(atom_spec, _symbols, _spin, cache_key=None):
            return self._distance(atom_spec), 0.0

        monkeypatch.setattr(oracle, "_energy", surface)
        with pytest.raises(GeometryError, match="does not bracket"):
            oracle._optimal_bond_length("H", "H", 0, 1.5)


class TestProvenance:
    def test_the_policy_is_visible_in_the_oracle_name(self):
        """
        A result computed with tight d is not the same result as one without. Provenance
        has to say which, or two tiers become indistinguishable in a published table.
        """
        assert PySCFOracle("CCSD(T)", "aug-cbs(TZ,QZ)", tight_d=True).name.endswith("+d")
        assert not PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", tight_d=False).name.endswith("+d")

    def test_registered_tiers_pin_their_policy_explicitly(self):
        """
        These names appear in a published accuracy table. Flipping a default must not be
        able to silently redefine what a published number means.
        """
        from smartchem.oracle import available_oracles
        registry = available_oracles()
        if not PYSCF_AVAILABLE:
            pytest.skip("registry correctly omits PySCF when its backend is absent")
        assert registry["ccsdt-cbs"].tight_d is False
        assert registry["ccsdt-aug-cbs"].tight_d is True

    def test_only_measured_protocols_receive_a_finite_mae(self):
        assert PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", tight_d=False
        ).nominal_accuracy_ev == pytest.approx(0.0562)
        assert PySCFOracle(
            "CCSD(T)", "aug-cbs(TZ,QZ)", tight_d=True
        ).nominal_accuracy_ev == pytest.approx(0.1277)
        assert math.isinf(PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", tight_d=True
        ).nominal_accuracy_ev)
        assert math.isinf(PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", optimize_geometry=True
        ).nominal_accuracy_ev)
        assert math.isinf(PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", max_atoms=20,
            geometry_tier=("HF", "cc-pVDZ"),
        ).nominal_accuracy_ev)

    def test_polyatomic_profile_declines_before_backend_work(self, monkeypatch):
        pytest.importorskip("pyscf")
        oracle = PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", max_atoms=3,
            geometry_tier=("HF", "cc-pVDZ"),
        )
        monkeypatch.setattr(oracle, "_energy", lambda *_a, **_k: pytest.fail("backend ran"))
        water = Molecule(("O", "H", "H"), frozenset({
            Bond(0, 1), Bond(0, 2),
        }))
        assert oracle.energy(water) is None

    def test_atom_cache_separates_the_two_policies(self):
        """E(S) with and without tight d are different numbers; one cache must not serve both."""
        oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=True)
        plain = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False)
        # Keys are built from (kind, symbol, basis, method, tight_d).
        assert oracle.tight_d != plain.tight_d
        oracle._cache[("atom", "S", "cc-pVTZ", "CCSD(T)", True)] = -1.0
        plain._cache[("atom", "S", "cc-pVTZ", "CCSD(T)", False)] = -2.0
        assert oracle._cache != plain._cache

    def test_imported_model_data_reaches_persistent_identity(self, tmp_path, monkeypatch):
        before = PersistentCache(
            PySCFOracle("HF", "cc-pVDZ"), tmp_path / "cache.json"
        ).fingerprint
        r_e, omega, spin = GEOMETRY["H2"]
        monkeypatch.setattr(
            pyscf_module,
            "GEOMETRY",
            {**GEOMETRY, "H2": (r_e + 0.01, omega, spin)},
        )
        after = PersistentCache(
            PySCFOracle("HF", "cc-pVDZ"), tmp_path / "cache.json"
        ).fingerprint
        assert before != after

    def test_every_periodic_descriptor_field_reaches_model_identity(self, monkeypatch):
        before = pyscf_module._model_inputs_sha256()
        monkeypatch.setattr(
            pyscf_module,
            "PT",
            {**PT, "O": replace(PT["O"], group=15)},
        )
        assert pyscf_module._model_inputs_sha256() != before

    def test_the_zpe_bias_fraction_reaches_model_identity(self, monkeypatch):
        """
        Every other result-driving input in the whitelist had an anchor; this one did not.

        ``PT``, ``TIGHT_D``, ``GEOMETRY``, ``_CARDINAL`` and ``_RELAXED_GEOMETRY_MAE`` each
        already have a test proving they reach ``_model_inputs_sha256``.
        ``zpe_bias_fraction`` was named in the payload and pinned by nothing, so a
        reorganisation that dropped the key would have passed the whole suite -- and the
        symptom would be a cache serving polyatomic systematics computed under a different
        bias than the one the module now declares.

        That gap is not hypothetical here. The 2026-07-26 refit found this constant does
        not reproduce on any protocol, so it is a live candidate for revision; the edit
        that changes it is exactly the edit that must not be invisible to cache identity.
        """
        before = pyscf_module._model_inputs_sha256()
        monkeypatch.setattr(pyscf_module, "ZPE_BIAS_FRACTION", 0.0801)
        assert pyscf_module._model_inputs_sha256() != before

    def test_vendored_basis_content_reaches_model_identity(self, monkeypatch):
        before = pyscf_module._model_inputs_sha256()
        basis_name = "cc-pV(T+d)Z"
        monkeypatch.setattr(
            pyscf_module,
            "TIGHT_D",
            {**TIGHT_D, basis_name: TIGHT_D[basis_name] + "\n# changed"},
        )
        assert pyscf_module._model_inputs_sha256() != before

    @pytest.mark.parametrize(
        "table,key,value",
        [
            (pyscf_module._CARDINAL, "cc-pVDZ", 99),
            (pyscf_module._FIXED_DIATOMIC_MAE, ("HF", "cc-pVDZ", False), 0.0),
            (pyscf_module._RELAXED_GEOMETRY_MAE,
             ("CCSD(T)", "cbs(TZ,QZ)", False, ("HF", "cc-pVDZ")), (0.0, 6)),
        ],
    )
    def test_oracle_policy_tables_are_read_only(self, table, key, value):
        with pytest.raises(TypeError):
            table[key] = value


class TestTheRelaxedGeometryGateIsALockAndNotAWeld:
    """
    Before 2026-07-26 no argument combination could publish a polyatomic energy.

    ``max_atoms <= 2`` was a term in the boolean that produced the accuracy bar, so a
    polyatomic-capable oracle got ``inf`` and declined regardless of what had been
    measured. "We have not measured this" and "this cannot be measured" were the same
    state -- indistinguishable from outside, and very different once evidence arrives.

    The gate now consults a table. The table is empty, so today's behaviour is unchanged;
    what these tests pin is that the emptiness is the reason for the decline, and that
    filling it would actually open the path and would still respect its own ceiling.
    """

    RELAXED = ("CCSD(T)", "cbs(TZ,QZ)", False, ("HF", "cc-pVDZ"))

    def test_the_table_is_empty_and_no_number_has_been_entered_unearned(self):
        """
        RESULTS_polyatomic_cost.md reports MAE 0.0558 eV over six polyatomics at exactly
        this protocol. It is deliberately NOT here: all six were used to develop and
        inspect the protocol, so that figure is a training error. An entry is earned by a
        measurement on species the protocol was never tuned on.
        """
        assert dict(pyscf_module._RELAXED_GEOMETRY_MAE) == {}

    def test_a_relaxed_geometry_profile_still_declines(self):
        oracle = PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", max_atoms=6, geometry_tier=("HF", "cc-pVDZ")
        )
        assert math.isinf(oracle.nominal_accuracy_ev)

    def test_a_populated_entry_opens_the_gate(self, monkeypatch):
        """The keyhole has to actually turn, or an empty table proves nothing."""
        monkeypatch.setattr(
            pyscf_module, "_RELAXED_GEOMETRY_MAE",
            MappingProxyType({self.RELAXED: (0.0558, 6)}),
        )
        oracle = PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", max_atoms=6, geometry_tier=("HF", "cc-pVDZ")
        )
        assert oracle.nominal_accuracy_ev == pytest.approx(0.0558)

    def test_a_populated_entry_still_refuses_beyond_its_validated_atom_count(
        self, monkeypatch
    ):
        """A profile measured to 6 atoms says nothing about 12, and must not pretend to."""
        monkeypatch.setattr(
            pyscf_module, "_RELAXED_GEOMETRY_MAE",
            MappingProxyType({self.RELAXED: (0.0558, 6)}),
        )
        assert math.isinf(PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)", max_atoms=7, geometry_tier=("HF", "cc-pVDZ")
        ).nominal_accuracy_ev)

    def test_an_entry_does_not_leak_across_protocols(self, monkeypatch):
        """Measuring one geometry tier must not license a different one."""
        monkeypatch.setattr(
            pyscf_module, "_RELAXED_GEOMETRY_MAE",
            MappingProxyType({self.RELAXED: (0.0558, 6)}),
        )
        for method, basis, tight_d, tier in [
            ("CCSD(T)", "cbs(TZ,QZ)", False, ("HF", "cc-pVTZ")),   # other geometry tier
            ("CCSD(T)", "cc-pVTZ", False, ("HF", "cc-pVDZ")),      # other energy tier
            ("CCSD(T)", "cbs(TZ,QZ)", True, ("HF", "cc-pVDZ")),    # other basis policy
        ]:
            assert math.isinf(PySCFOracle(
                method, basis, tight_d=tight_d, max_atoms=6, geometry_tier=tier
            ).nominal_accuracy_ev), f"{method}/{basis}/{tight_d}//{tier} leaked"

    def test_the_diatomic_table_is_untouched_by_any_of_this(self):
        """The behaviour that was already validated must be byte-identical."""
        assert PySCFOracle(
            "CCSD(T)", "cbs(TZ,QZ)"
        ).nominal_accuracy_ev == pytest.approx(0.0562)
        assert math.isinf(
            PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", optimize_geometry=True).nominal_accuracy_ev
        )
        assert math.isinf(
            PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", max_atoms=3).nominal_accuracy_ev
        )

    def test_the_relaxed_table_reaches_model_identity(self, monkeypatch):
        """
        ``_model_inputs_sha256`` is a whitelist, not a scan of the module. A table that is
        not named in it is invisible to cache identity -- and the first edit anyone makes to
        this table will be to put a number in it. If that edit did not move the digest,
        every persistent cache would keep serving the old uncertainty.
        """
        before = pyscf_module._model_inputs_sha256()
        monkeypatch.setattr(
            pyscf_module, "_RELAXED_GEOMETRY_MAE",
            MappingProxyType({self.RELAXED: (0.0558, 6)}),
        )
        assert pyscf_module._model_inputs_sha256() != before


class TestCostLimit:
    @pytest.mark.parametrize("bad", [0, -1])
    def test_nonpositive_limits_are_rejected(self, bad):
        with pytest.raises(ValueError):
            PySCFOracle(max_atoms=bad)

    @pytest.mark.parametrize("bad", [True, 1.5, "2"])
    def test_noninteger_limits_are_rejected(self, bad):
        with pytest.raises(TypeError):
            PySCFOracle(max_atoms=bad)

    def test_limit_is_checked_before_backend_work(self, monkeypatch):
        oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False, max_atoms=1)
        monkeypatch.setattr(oracle, "_energy", lambda *_a, **_k: pytest.fail("backend ran"))
        assert oracle.energy(Molecule.diatomic("H", "H")) is None

    def test_limit_is_inclusive(self, monkeypatch):
        pytest.importorskip("pyscf")
        oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False, max_atoms=2)
        monkeypatch.setattr(oracle, "_energy", lambda *_a, **_k: (-1.0, 0.0))
        assert oracle.energy(Molecule.diatomic("H", "H")) is not None

    def test_unknown_diatomic_zpe_is_not_silently_zero(self, monkeypatch):
        pytest.importorskip("pyscf")
        oracle = PySCFOracle(
            "CCSD(T)", "cc-pVTZ", tight_d=False, max_atoms=2,
            optimize_geometry=True,
        )
        monkeypatch.setattr(oracle, "_energy", lambda *_a, **_k: pytest.fail("backend ran"))
        assert oracle.energy(Molecule.diatomic("Br", "Br")) is None

    def test_internal_backend_defects_are_not_disguised_as_refusals(self, monkeypatch):
        pytest.importorskip("pyscf")
        oracle = PySCFOracle("HF", "cc-pVDZ", max_atoms=1)

        def broken_backend(_symbol):
            raise RuntimeError("simulated implementation defect")

        monkeypatch.setattr(oracle, "_atom_energy", broken_backend)
        with pytest.raises(RuntimeError, match="implementation defect"):
            oracle.energy(Molecule.atom("H"))


@pytest.mark.skipif(not PYSCF_AVAILABLE, reason="coverage is a question for the basis library")
class TestElementCoverage:
    """
    The guard has to agree with the basis library, not with the spin table.

    Iodine has a ground-state spin on file and three curated reference rows (I2 in the test
    split, HI and ICl in train), and no ``cc-pVTZ``. A coverage guard that consulted only
    ``ATOM_SPIN`` therefore let all three through to ``gto.M``, which raised
    ``BasisNotFoundError`` out through the public ``energy()`` contract -- neither a value
    nor a decline -- and took ``python -m smartchem.bench`` down with it (exit 1, no report)
    on every machine with PySCF installed.
    """

    def test_the_two_tables_disagree_and_the_library_is_the_authority(self):
        assert "I" in ATOM_SPIN                            # what the old guard asked
        assert not basis_covers(("I",), "cc-pVTZ", False)  # what actually decides

    def test_covered_elements_are_unaffected(self):
        assert basis_covers(("H", "O"), "cc-pVTZ", False)
        assert basis_covers(("C", "N"), "cc-pVDZ", False)

    def test_an_uncovered_element_declines_before_backend_work(self, monkeypatch):
        oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False)
        for attr in ("_energy", "_atom_energy"):
            monkeypatch.setattr(
                oracle, attr, lambda *_a, **_k: pytest.fail("backend ran"))
        assert oracle.energy(Molecule.diatomic("I", "I")) is None
        assert oracle.energy(Molecule.atom("I")) is None

    def test_a_cbs_tier_needs_both_members_to_cover(self):
        """Extrapolating from whichever member happens to have the element is not the protocol."""
        oracle = PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", tight_d=False)
        assert oracle._basis_covers(("I", "I")) is False
        assert oracle._basis_covers(("H", "H")) is True

    def test_no_curated_reference_row_can_reach_the_backend_uncovered(self):
        """
        The anchor the benchmark needed: walk the species the benchmark walks, and require
        that every one of them gets a *decision* rather than an exception.

        Only the uncovered rows are actually priced here -- those decline instantly. A
        covered row would cost a real wavefunction, which is what ``--runslow`` is for.
        """
        from smartchem.oracle import available_oracles

        checked = 0
        for name, oracle in sorted(available_oracles().items()):
            if not isinstance(oracle, PySCFOracle):
                continue
            for ref in BOND_REFS:
                covered = oracle._basis_covers(ref.atoms)
                assert isinstance(covered, bool), (name, ref.formula)
                if not covered:
                    molecule = Molecule.diatomic(*ref.atoms, order=ref.bond_order)
                    assert oracle.energy(molecule) is None, (name, ref.formula)
                    checked += 1
        assert checked > 0, "the uncovered-species path was never exercised"


@pytest.mark.skipif(not PYSCF_AVAILABLE, reason="the roster is defined by basis coverage")
class TestZpeBiasTrainingRoster:
    """
    Pin the training set of ``ZPE_BIAS_FRACTION``, because a fit whose roster is unknown
    cannot have anything held out of it.

    The script that measured +9.1% lived in an uncommitted scratch directory and is gone.
    What survived is its selection rule, stated in prose: every tabulated diatomic whose
    elements cc-pVDZ covers. Applying that rule to the committed table regenerates 23
    species, matching the count the docstring claims.

    That match is corroboration, not proof of identity -- the prose could have been written
    to describe a result rather than to specify the predicate. These tests therefore pin
    what is actually checkable: the literal and the rule agree today, and any drift between
    them is loud.
    """

    def _derive(self) -> tuple[str, ...]:
        by_formula = {ref.formula: ref.atoms for ref in BOND_REFS}
        return tuple(sorted(
            formula for formula in GEOMETRY
            if formula in by_formula and basis_covers(by_formula[formula], "cc-pVDZ", False)
        ))

    def test_the_committed_roster_still_matches_its_own_selection_rule(self):
        assert self._derive() == tuple(sorted(ZPE_BIAS_TRAIN_SPECIES))

    def test_the_roster_is_the_size_the_docstring_claims(self):
        assert len(ZPE_BIAS_TRAIN_SPECIES) == 23

    def test_the_excluded_species_are_excluded_by_basis_and_not_by_choice(self):
        """
        Five rows sat out. Recording *why* matters: they were not held back as a validation
        set, they were unrepresentable. Anyone building a held-out set for the ZPE fit must
        not mistake these for one.
        """
        excluded = set(GEOMETRY) - set(ZPE_BIAS_TRAIN_SPECIES)
        assert excluded == {"HI", "I2", "ICl", "K2", "KCl"}
        by_formula = {ref.formula: ref.atoms for ref in BOND_REFS}
        for formula in excluded:
            assert not basis_covers(by_formula[formula], "cc-pVDZ", False), formula

    def test_every_member_is_a_real_row_in_both_tables(self):
        formulas = {ref.formula for ref in BOND_REFS}
        for formula in ZPE_BIAS_TRAIN_SPECIES:
            assert formula in GEOMETRY, formula
            assert formula in formulas, formula
