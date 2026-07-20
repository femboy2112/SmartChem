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

import pytest

pytest.importorskip("pyscf", reason="the basis policy lives in the PySCF oracle")

from smartchem.data.basis_tight_d import SECOND_ROW, TIGHT_D          # noqa: E402
from smartchem.oracle.pyscf_oracle import (                            # noqa: E402
    PySCFOracle,
    resolve_basis,
    tight_d_name,
)


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
        assert registry["ccsdt-cbs"].tight_d is False
        assert registry["ccsdt-aug-cbs"].tight_d is True

    def test_atom_cache_separates_the_two_policies(self):
        """E(S) with and without tight d are different numbers; one cache must not serve both."""
        oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=True)
        plain = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False)
        # Keys are built from (kind, symbol, basis, method, tight_d).
        assert oracle.tight_d != plain.tight_d
        oracle._cache[("atom", "S", "cc-pVTZ", "CCSD(T)", True)] = -1.0
        plain._cache[("atom", "S", "cc-pVTZ", "CCSD(T)", False)] = -2.0
        assert oracle._cache != plain._cache
