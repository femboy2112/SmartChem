"""CANON-KEKULE-01: the canonical identity is invariant to how the pi bonds are DRAWN (aromatic or explicit Kekule).

The resonance-canonical R2 move used to run ONLY over bonds the INPUT flagged aromatic (lowercase / ``:``); an
explicit-Kekule spelling (uppercase atoms, ``=`` bonds) carried no flags, so a FUSED aromatic written that way kept
its authored double-bond graph and got a DIFFERENT ``canonical_digest`` than its aromatic spelling -- a molecule
could fail to satisfy its OWN identity (surfaced by the STOCK-01 red-team, wg3b1u0ts).

The fix (`smiles._min_constitution_placement`) closes it WITHOUT aromaticity perception: each atom's pi-demand is
fixed by the drawn structure (so H-counts pin a LOCALISED double and a tautomer keeps its distinct H-placement),
and the identity is the constitution-minimal placement over every assignment satisfying that demand -- the exact R2
move, generalised from aromatic-flagged bonds to the whole pi-system.  Resonance forms of one molecule collapse;
genuinely different molecules never do.

These tests pin BOTH directions: aromatic-vs-Kekule spellings of one molecule share an identity (INVARIANCE), and
molecules that merely share a formula/skeleton but differ in a real, H-pinned way stay DISTINCT (NO over-collapse).
"""
import pytest

from smartchem.contracts import canonical_digest
from smartchem.smiles import isotope_refined_key, parse_smiles


def _k(smiles: str) -> str:
    return canonical_digest(parse_smiles(smiles).canonical())


# (name, aromatic spelling, an explicit-Kekule spelling of the SAME molecule)
INVARIANT_PAIRS = [
    ("benzene", "c1ccccc1", "C1=CC=CC=C1"),
    ("naphthalene", "c1ccc2ccccc2c1", "C1=CC=C2C=CC=CC2=C1"),
    ("anthracene", "c1ccc2cc3ccccc3cc2c1", "C1=CC=C2C=C3C=CC=CC3=CC2=C1"),
    ("pyridine", "c1ccncc1", "C1=CC=NC=C1"),
    ("furan", "c1ccoc1", "C1=CC=CO1"),
    ("pyrrole", "c1cc[nH]c1", "C1=CC=CN1"),
    ("toluene", "Cc1ccccc1", "CC1=CC=CC=C1"),
    ("phenol", "Oc1ccccc1", "OC1=CC=CC=C1"),
    ("styrene (aromatic ring + vinyl)", "C=Cc1ccccc1", "C=CC1=CC=CC=C1"),
    ("2-naphthol", "Oc1ccc2ccccc2c1", "OC1=CC=C2C=CC=CC2=C1"),
]


class TestKekuleInvariance:
    @pytest.mark.parametrize("name,aromatic,kekule", INVARIANT_PAIRS, ids=[p[0] for p in INVARIANT_PAIRS])
    def test_aromatic_and_kekule_spellings_share_one_identity(self, name, aromatic, kekule):
        assert _k(aromatic) == _k(kekule), f"{name}: aromatic and explicit-Kekule spellings must be ONE identity"

    def test_two_different_kekule_drawings_of_a_fused_aromatic_agree(self):
        # naphthalene has 3 non-isomorphic Kekule structures; two different explicit drawings must still collapse.
        a = "C1=CC=C2C=CC=CC2=C1"
        b = "C1=CC2=CC=CC=C2C=C1"
        assert _k(a) == _k(b)

    def test_the_isotope_refined_key_is_also_invariant(self):
        # the finer isotope key must refine constitution, so it inherits the same invariance.
        assert isotope_refined_key("c1ccc2ccccc2c1") == isotope_refined_key("C1=CC=C2C=CC=CC2=C1")


class TestNoOverCollapse:
    """The fix must NOT collapse molecules that only look similar -- H-counts pin a localised double bond."""

    @pytest.mark.parametrize("a,b,why", [
        ("C=CCC", "CC=CC", "1-butene vs 2-butene (double-bond position, H-pinned)"),
        ("CCO", "COC", "ethanol vs dimethyl ether (constitutional isomers)"),
        ("CC(=O)O", "OCC=O", "acetic acid vs glycolaldehyde (same formula, different skeleton)"),
        ("C1=CCC=CC1", "C1=CC=CCC1", "1,4- vs 1,3-cyclohexadiene (non-aromatic ring dienes)"),
        ("C1=CCCCC1", "C1CCCCC1", "cyclohexene vs cyclohexane (a real double bond is not resonance)"),
        ("CC=O", "C=CO", "acetaldehyde vs vinyl alcohol (keto/enol tautomers, different H-placement)"),
    ])
    def test_distinct_molecules_stay_distinct(self, a, b, why):
        assert _k(a) != _k(b), f"must NOT collapse: {why}"

    def test_a_localised_ring_double_bond_has_one_placement(self):
        # cyclohexene has a single H-pinned double bond; drawn at any ring position it is the SAME molecule (ring
        # symmetry), so every spelling shares one identity -- the fix is inert on a localised (non-resonance) double.
        assert _k("C1=CCCCC1") == _k("C1CCCC=C1") == _k("C1CC=CCC1")


class TestBoundDoesNotFalseTrigger:
    def test_a_large_aliphatic_has_a_unique_placement_and_does_not_blow_up(self):
        # a plain large chain has NO resonance freedom (every placement is H-pinned to one), so the enumeration is
        # linear and the bound (which REFUSES rather than truncate to a non-deterministic minimum) never fires.
        assert _k("C" * 60) == _k("C" * 60)
