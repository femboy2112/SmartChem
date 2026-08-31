"""
Declared validity domains, machine-checked. Brick 1 of ``THE_COMPILER.md`` section VII.

The claim under test is deliberately one-directional and the tests are shaped around that
asymmetry, because getting it backwards is how a domain turns into a lie::

    not domain.admits(m)   IMPLIES   oracle.energy(m) is None        <- SOUNDNESS, tested
    domain.admits(m)       IMPLIES   oracle.energy(m) is not None    <- NOT claimed

Soundness is the property with teeth: it says a declared refusal is a real refusal. The
converse is false for two separately-reported reasons (a convergence failure nobody can
predict, and a lookup the constraint language cannot express), and a test asserting it
would be asserting something the design explicitly disclaims.

A soundness test can pass vacuously if no sampled species is ever outside a domain, so
every soundness case below counts its exclusions and fails if the count is zero. That guard
matters more than the assertion it protects: the same gap -- a completeness class that
tested no completeness -- shipped a real defect in ``stoichiometry.py`` on the same day
this file was written.
"""
from __future__ import annotations

import pytest

from smartchem.category import Bond, Molecule
from smartchem.domain import EVERYTHING, NOTHING, Domain, DomainContradiction
from smartchem.oracle.base import BaseOracle, domain_of
from smartchem.oracle.caching import CachingOracle
from smartchem.oracle.heuristic import HeuristicOracle
from smartchem.oracle.photon import PhotonOracle

H2 = Molecule.diatomic("H", "H")
CO = Molecule.diatomic("C", "O")
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))
PHOTON = Molecule.carrier()
ELECTRON = Molecule.carrier(charge=-1)

#: A deliberately mixed sample: matter and non-matter, neutral and charged, ground and
#: excited, in and out of every bundled oracle's coverage.
SAMPLE = (
    Molecule.atom("H"),
    Molecule.atom("C"),
    Molecule.atom("Xx"),                      # not an element anyone tabulates
    H2,
    CO,
    H2O,
    Molecule(("C", "H", "H", "H", "H"),
             frozenset({Bond(0, i, 1) for i in (1, 2, 3, 4)})),
    Molecule.atom("Na", state="*"),
    Molecule.atom("H", charge=1),
    PHOTON,
    Molecule.carrier("589nm"),
    ELECTRON,
)


class TestTheAlgebra:
    """Intersection, emptiness and the witness that checks emptiness independently."""

    def test_none_on_an_axis_is_the_universe_not_the_empty_set(self):
        """The distinction the whole optional-field design exists for."""
        unrestricted = Domain(label="a", elements=None)
        forbidden = Domain(label="b", elements=frozenset(), min_atoms=1)
        assert unrestricted.admits(H2)
        assert not forbidden.admits(H2)
        assert not unrestricted.is_empty
        assert forbidden.is_empty

    def test_intersection_admits_exactly_what_both_admit(self):
        left = Domain(label="l", min_atoms=1, max_atoms=3, charges=frozenset({0, 1}))
        right = Domain(label="r", min_atoms=2, charges=frozenset({0}))
        both = left & right
        for molecule in SAMPLE:
            assert both.admits(molecule) == (left.admits(molecule) and right.admits(molecule))

    def test_intersection_unions_the_caveats_rather_than_intersecting_them(self):
        """A pair is no more predictable than its least predictable half."""
        left = Domain(label="l", runtime_refusals=("solver may diverge",))
        right = Domain(label="r", unexpressed_refusals=("table keyed by formula",))
        both = left & right
        assert both.runtime_refusals == ("solver may diverge",)
        assert both.unexpressed_refusals == ("table keyed by formula",)
        assert not both.is_exact
        assert left.is_exact is False and right.is_exact is False

    def test_intersection_is_commutative_on_membership(self):
        left = Domain(label="l", max_atoms=2, elements=frozenset({"H", "O"}))
        right = Domain(label="r", min_atoms=1, elements=frozenset({"O", "C"}))
        for molecule in SAMPLE:
            assert (left & right).admits(molecule) == (right & left).admits(molecule)

    @pytest.mark.parametrize("domain", [
        EVERYTHING,
        NOTHING,
        Domain(label="d", min_atoms=1, max_atoms=2, elements=frozenset({"H"})),
        Domain(label="d", min_atoms=0, max_atoms=0, elements=frozenset()),
        Domain(label="d", charges=frozenset()),
        Domain(label="d", states=frozenset()),
        Domain(label="d", min_atoms=3, max_atoms=2),
    ])
    def test_witness_and_the_emptiness_algebra_agree(self, domain):
        """
        The independent second derivation. Disagreement raises rather than resolves.

        ``is_empty`` reasons over the constraint sets; ``witness`` picks a value on each
        axis and builds a real ``Molecule`` through the ordinary constructor, connectivity
        validation included. Same discipline as ``stoichiometry.py``'s use of ``Reaction``.
        """
        found = domain.witness()                      # raises DomainContradiction on conflict
        assert (found is None) == domain.is_empty
        if found is not None:
            assert domain.admits(found)

    def test_a_zero_atom_domain_with_no_elements_is_not_empty(self):
        """The coupling worth spelling out: no atoms required means no element needed."""
        photonic = Domain(label="p", min_atoms=0, max_atoms=0, elements=frozenset())
        assert not photonic.is_empty
        assert photonic.witness() is not None
        assert photonic.witness().atoms == ()

    def test_contradiction_is_a_distinct_error_type(self):
        assert issubclass(DomainContradiction, AssertionError)


class TestSoundness:
    """
    Declared-outside means really refused. The one property that gives a domain content.

    Each case counts its exclusions, because a soundness assertion over a sample that
    happens to lie entirely inside the domain proves nothing at all.
    """

    def test_photon_oracle_is_sound(self):
        oracle = PhotonOracle(589.0)
        excluded = 0
        for molecule in SAMPLE:
            if not oracle.domain.admits(molecule):
                excluded += 1
                assert oracle.energy(molecule) is None, molecule
        assert excluded >= 8, f"only {excluded} of {len(SAMPLE)} were outside; too weak"

    def test_photon_oracle_is_also_EXACT_which_is_the_stronger_claim(self):
        """
        Its domain claims ``is_exact``, so the converse must hold too -- here and nowhere else.

        This is the test that would catch an over-claimed ``is_exact``: a domain asserting
        exactness is promising the biconditional, and a promise nobody checks is a comment.
        """
        oracle = PhotonOracle(589.0)
        assert oracle.domain.is_exact
        admitted = 0
        for molecule in SAMPLE:
            if oracle.domain.admits(molecule):
                admitted += 1
                assert oracle.energy(molecule) is not None, molecule
        assert admitted >= 2, f"only {admitted} admitted; the exactness claim is untested"

    def test_heuristic_oracle_is_sound(self):
        oracle = HeuristicOracle()
        excluded = 0
        for molecule in SAMPLE:
            if not oracle.domain.admits(molecule):
                excluded += 1
                assert oracle.energy(molecule) is None, molecule
        assert excluded >= 5, f"only {excluded} of {len(SAMPLE)} were outside; too weak"

    def test_an_unvalidated_environment_declares_and_delivers_nothing(self):
        from smartchem.legacy import Env

        oracle = HeuristicOracle(
            Env(temperature_k=500.0, pressure_atm=1.0,
                solvent_name="Vacuum", solvent_dielectric=1.0)
        )
        assert oracle.domain.is_empty
        for molecule in SAMPLE:
            assert not oracle.domain.admits(molecule)
            assert oracle.energy(molecule) is None, molecule


class TestPySCFDomain:
    """The configured oracle's boundary, including two results that were measured."""

    def test_pyscf_oracle_is_sound(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        oracle = PySCFOracle(basis="cc-pVDZ")
        excluded = 0
        for molecule in SAMPLE:
            if not oracle.domain.admits(molecule):
                excluded += 1
                # Every one of these declines before any backend work, so this is cheap.
                assert oracle.energy(molecule) is None, molecule
        assert excluded >= 6, f"only {excluded} of {len(SAMPLE)} were outside; too weak"

    def test_the_sample_is_not_entirely_outside(self):
        """
        Positive control. Without it, an oracle whose domain admitted nothing would pass
        every soundness test in this file, perfectly, forever.
        """
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        oracle = PySCFOracle(basis="cc-pVDZ")
        assert oracle.domain.admits(H2)
        assert oracle.energy(H2) is not None

    @pytest.mark.parametrize("kwargs,ceiling", [
        ({}, 2),
        ({"max_atoms": 6}, 2),
        ({"max_atoms": 6, "geometry_tier": ("HF", "cc-pVDZ")}, 2),
        ({"optimize_geometry": True}, 1),
    ])
    def test_no_configuration_declares_a_polyatomic(self, kwargs, ceiling):
        """
        MEASURED: raising ``max_atoms`` opens a path whose own finiteness gate then shuts.

        ``_RELAXED_GEOMETRY_MAE`` is the empty dict, so ``nominal_accuracy_ev`` is infinite
        for every ``geometry_tier`` and ``_polyatomic_energy`` declines unconditionally.
        The day a measured polyatomic MAE lands in that table this test should fail, and
        that failure is the correct notification that the boundary moved.
        """
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        oracle = PySCFOracle(basis="cc-pVDZ", **kwargs)
        assert oracle.domain.max_atoms == ceiling
        assert not oracle.domain.admits(H2O)
        assert oracle.energy(H2O) is None

    def test_a_tier_with_no_measured_mae_declares_nothing(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        oracle = PySCFOracle(method="MP2", basis="cc-pVDZ")
        assert oracle.domain.is_empty
        for molecule in SAMPLE:
            assert oracle.energy(molecule) is None, molecule

    def test_the_pyscf_domain_is_honest_about_not_being_exact(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        domain = PySCFOracle(basis="cc-pVDZ").domain
        assert not domain.is_exact
        assert domain.runtime_refusals, "convergence failures must be declared"
        assert domain.unexpressed_refusals, "the formula-keyed geometry table must be declared"
        assert "NOT EXACT" in domain.explain()


class TestTheFirstCrossVerticalRefusal:
    """
    Section VII's actual acceptance test: two oracles in two verticals, composed.

    The intersection being EMPTY is not a disappointment, it is the deliverable. It says
    there is no species both oracles can price, and therefore no shared reference against
    which their two arbitrary zeros could be aligned -- which is a real obstruction to a
    cross-vertical reaction energy, stated by construction instead of rediscovered once per
    attempt. Brick 2 needs exactly this diagnosis.
    """

    def test_matter_and_radiation_do_not_overlap(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        matter = PySCFOracle(basis="cc-pVDZ").domain
        radiation = PhotonOracle(589.0).domain
        shared = matter & radiation
        assert shared.is_empty
        assert shared.witness() is None
        assert "EMPTY" in shared.explain()

    def test_and_no_sampled_species_is_priced_by_both(self):
        """The algebra says empty; confirm no actual species slips through both oracles."""
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        matter, radiation = PySCFOracle(basis="cc-pVDZ"), PhotonOracle(589.0)
        for molecule in SAMPLE:
            assert not (matter.domain.admits(molecule) and radiation.domain.admits(molecule))


class TestDefaultsAndDelegation:
    def test_an_oracle_without_a_domain_claims_nothing(self):
        class Bare:
            name = "bare"

        assert domain_of(Bare()) is EVERYTHING
        assert not EVERYTHING.is_empty
        for molecule in SAMPLE:
            assert EVERYTHING.admits(molecule)

    def test_baseoracle_default_is_the_unrestricted_domain(self):
        class Silent(BaseOracle):
            name = "silent"

            def energy(self, molecule):
                return None

        assert Silent().domain is EVERYTHING

    def test_a_cache_alters_latency_not_coverage(self):
        """A wrapper that dropped the domain would silently erase a real boundary."""
        inner = PhotonOracle(589.0)
        wrapped = CachingOracle(inner)
        assert wrapped.domain.label == inner.domain.label
        assert wrapped.domain.max_atoms == inner.domain.max_atoms
        for molecule in SAMPLE:
            assert wrapped.domain.admits(molecule) == inner.domain.admits(molecule)

    def test_domain_is_not_part_of_the_protocol(self):
        """
        Adding it would break ``isinstance`` for every third-party oracle. ``domain_of``
        exists so composition never has to care which kind it was handed.
        """
        from smartchem.oracle.base import EnergyOracle

        class Bare:
            name = "bare"
            nominal_accuracy_ev = 1.0

            def energy(self, molecule):
                return None

        assert isinstance(Bare(), EnergyOracle)


#: The element rosters, WRITTEN OUT BY HAND and deliberately not derived from the tables
#: they check. A test that iterates the table under test cannot notice that table getting
#: smaller -- it would loop over the survivors and pass. That is the exact shape of the
#: three defects this repository shipped in two days, and it is why a mutant narrowing the
#: element sets to {H, C, O} survived all 31 tests in this file.
#:
#: Measured 2026-07-26 and pinned. If a legitimate change grows a table, this fails and the
#: roster is updated in the same commit -- which is the point, because the change then has
#: to be looked at rather than absorbed.
#: 2026-08-31: "Br" added -- the element-set-breadth goal put a SOURCED bromine row into the
#: periodic table (smartchem/atoms.py: IE NIST ASD 2024, EA Blondel 1989, radius Pyykko 2009,
#: mass IUPAC/CIAAW) so halogen chemistry (Markovnikov-HX, Zaitsev) is handleable. This is the
#: guard doing its job: the roster grew, so the change was reviewed.
_HEURISTIC_ROSTER = frozenset({
    "Br", "C", "Cl", "Cu", "D", "F", "Fe", "H", "He", "I", "K", "Kr", "Mg", "Mn", "Mo",
    "N", "Na", "O", "Og", "P", "Pb", "Pd", "Pt", "Ru", "S", "Si", "T", "Xe", "Zn",
})

#: PySCF at cc-pVDZ, which is 23 and NOT the 25 of its own spin table -- see the test below.
_PYSCF_DZ_ROSTER = frozenset({
    "Al", "Ar", "B", "Be", "Br", "C", "Ca", "Cl", "Cu", "F", "Fe", "H", "He", "Li",
    "Mg", "N", "Na", "Ne", "O", "P", "S", "Si", "Zn",
})

#: Symbols no table here declares. Two are plausible-looking, one is real-but-untabulated.
_OFF_ROSTER = ("Xx", "Zz", "Rf")


class TestTheElementAxisIsProvenAndNotMerelyDeclared:
    """
    The axis a mutant walked straight through.

    Narrowing an oracle's declared element set is an UNDER-approximation, and that is the
    one direction the Brick 1 contract forbids: ``not admits(m)`` would be true while
    ``energy(m)`` still returned a number, so a caller told "this oracle cannot price
    sodium" would be told a falsehood by the only mechanism that exists to prevent them.

    Every test here reaches the tables from outside them.
    """

    def test_the_heuristic_roster_is_still_what_was_measured(self):
        assert HeuristicOracle().domain.elements == _HEURISTIC_ROSTER

    def test_every_element_the_heuristic_actually_prices_is_admitted(self):
        """
        Soundness, checked against the oracle rather than against the declaration. The
        loop runs over the hand-written roster, so an oracle that quietly stopped
        declaring half of them fails here instead of iterating its own survivors.
        """
        oracle = HeuristicOracle()
        domain = oracle.domain
        priced = 0
        for symbol in sorted(_HEURISTIC_ROSTER):
            atom = Molecule.atom(symbol)
            if oracle.energy(atom) is not None:
                priced += 1
                assert domain.admits(atom), f"{symbol} is priced and not admitted"
        assert priced == len(_HEURISTIC_ROSTER), "every roster element must be priced"

    def test_the_pyscf_roster_is_still_what_was_measured(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        assert PySCFOracle(basis="cc-pVDZ").domain.elements == _PYSCF_DZ_ROSTER

    def test_the_basis_library_gates_the_axis_and_not_the_spin_table(self):
        """
        ``I`` and ``K`` are in ``ATOM_SPIN`` and are NOT covered by cc-pVDZ, so the domain
        must exclude them. Checking the spin table instead of the basis library is not a
        hypothetical mistake -- it is the one that crashed the bench on iodine (``ac68207``)
        and it is what turned a 23-element axis into a 25-element claim once already.
        """
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import ATOM_SPIN, PySCFOracle

        domain = PySCFOracle(basis="cc-pVDZ").domain
        assert set(ATOM_SPIN) - set(domain.elements) == {"I", "K"}
        for symbol in ("I", "K"):
            assert symbol in ATOM_SPIN
            assert not domain.admits(Molecule.atom(symbol))

    def test_symbols_no_table_declares_are_refused_by_both(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        refused = 0
        for symbol in _OFF_ROSTER:
            atom = Molecule.atom(symbol)
            for domain in (HeuristicOracle().domain,
                           PySCFOracle(basis="cc-pVDZ").domain):
                assert not domain.admits(atom), f"{symbol} must not be admitted"
                assert domain.refusals(atom), f"{symbol} must come with a reason"
                refused += 1
        assert refused == 2 * len(_OFF_ROSTER)

    def test_the_two_rosters_are_not_the_same_set(self):
        """
        Guards the laziest possible mutant: one shared element table behind both oracles.
        Twelve symbols are heuristic-only and seven are PySCF-only.
        """
        assert len(_HEURISTIC_ROSTER & _PYSCF_DZ_ROSTER) == 16  # Br now in BOTH (added to the heuristic table)
        assert len(_HEURISTIC_ROSTER - _PYSCF_DZ_ROSTER) == 13
        assert len(_PYSCF_DZ_ROSTER - _HEURISTIC_ROSTER) == 7   # Br left the PySCF-only set for the overlap


class TestTheMeetIsAValueAndBehavesLikeOne:
    """
    ``Domain`` is a frozen dataclass, so it carries ``__eq__`` and ``__hash__`` whether or
    not anyone meant it to. Both of the identities below were false until 2026-07-26:
    caveats unioned in argument order, and a self-meet grew a doubled label.
    """

    def _domains(self):
        pytest.importorskip("pyscf")
        from smartchem.oracle.pyscf_oracle import PySCFOracle

        return (PhotonOracle(589.0).domain, PhotonOracle(532.0).domain,
                HeuristicOracle().domain, PySCFOracle(basis="cc-pVDZ").domain)

    def test_the_meet_is_commutative_as_a_value(self):
        domains = self._domains()
        pairs = 0
        for i, left in enumerate(domains):
            for right in domains[i + 1:]:
                pairs += 1
                assert (left & right) == (right & left)
                assert hash(left & right) == hash(right & left)
        assert pairs == 6

    def test_the_meet_is_idempotent_as_a_value(self):
        for domain in self._domains():
            assert (domain & domain) == domain

    def test_a_shared_witness_does_not_imply_a_shared_reference(self):
        """
        The claim ``__and__``'s docstring used to make as though it were sufficient. The
        intersection here is non-empty AND exact, and the two oracles still disagree.
        """
        left, right = PhotonOracle(589.0), PhotonOracle(532.0)
        shared = left.domain & right.domain
        assert not shared.is_empty and shared.is_exact
        witness = shared.witness()
        assert witness is not None
        gap = left.energy(witness).value_ev - right.energy(witness).value_ev
        assert abs(gap) == pytest.approx(0.225535, abs=1e-6)

    def test_a_persistent_cache_alters_latency_not_coverage(self, tmp_path):
        """
        The twin of ``test_a_cache_alters_latency_not_coverage``. ``PersistentCache``
        forwards ``domain`` with the same six lines and had no test at all, so a mutant
        deleting the forward survived every one of this file's tests and all 42 tests that
        touch that class.
        """
        from smartchem.oracle.persistent import PersistentCache

        inner = PhotonOracle(589.0)
        wrapped = PersistentCache(inner, path=tmp_path / "cache.json")
        assert wrapped.domain.label == inner.domain.label
        assert wrapped.domain.max_atoms == inner.domain.max_atoms
        assert wrapped.domain == inner.domain
        for molecule in SAMPLE:
            assert wrapped.domain.admits(molecule) == inner.domain.admits(molecule)
