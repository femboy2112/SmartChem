"""AROMATIC-CARBONYL-KEKULIZE-01: the exocyclic-pi donor rule kekulizes the conjugated-carbonyl aromatic class.

Pins the R46 fix: an aromatic atom bearing an exocyclic multiple bond (e.g. a ring carbonyl ``c(=O)``) is a
pi-DONOR, so the whole conjugated-carbonyl family -- every purine, every pyrimidinone nucleobase, quinones,
tropone -- now kekulizes to the correct isomer instead of failing closed.  The fix is valence-forced and additive:
it never fires on a molecule that already parsed (proven below), so it cannot regress an existing identity.
"""
from __future__ import annotations

import pytest

from experiments import aromatic_carbonyl_kekulizer_probe as probe
from smartchem.contracts import canonical_digest
from smartchem.smiles import SmilesError
from smartchem.smiles import parse_smiles as M

_TRUE_INCHIKEYS = {
    "caffeine": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
    "theophylline": "ZFXYFBGIUFBOJW-UHFFFAOYSA-N",
    "theobromine": "YAPQBXQYLJRXSA-UHFFFAOYSA-N",
    "xanthine": "LRFVTYWOQMYALW-UHFFFAOYSA-N",
    "guanine": "UYTPUPDQBNUYGX-UHFFFAOYSA-N",
    "uracil": "ISAKRJDGNUQOIC-UHFFFAOYSA-N",
    "cytosine": "OPTASPLRGRRNAP-UHFFFAOYSA-N",
    "thymine": "RWQNBRDOKXIBIV-UHFFFAOYSA-N",
    "hypoxanthine": "FDGQSTZJBFJUBT-UHFFFAOYSA-N",
    "tropone": "QVWDCTQRORVHHT-UHFFFAOYSA-N",
}


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_rdkit_default_caffeine_output_now_parses():
    # the headline: RDKit's DEFAULT aromatic caffeine SMILES -- the spelling that used to raise -- parses to the
    # same identity as the explicit-Kekulé form a user would find on Wikipedia.
    aromatic = M("Cn1c(=O)c2c(ncn2C)n(C)c1=O")
    kekule = M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C")
    assert canonical_digest(aromatic.canonical()) == canonical_digest(kekule.canonical())


@pytest.mark.parametrize("name", list(probe._FAMILY))
def test_family_member_aromatic_spelling_matches_kekule_identity(name):
    aromatic, kekule = probe._FAMILY[name]
    assert canonical_digest(M(aromatic).canonical()) == canonical_digest(M(kekule).canonical()), name


def test_identity_still_discriminates_isomers():
    # the fix widened the ACCEPTED set; it did not blur identity.  theobromine (3,7) != theophylline (1,3).
    assert probe.identity_discriminates()["decoy_matches_theophylline"] is False


@pytest.mark.parametrize("smiles", probe._PREEXISTING)
def test_preexisting_spellings_are_unchanged(smiles):
    # the exocyclic-pi rule NEVER fires on a molecule that already parsed (none has an aromatic exocyclic-pi
    # acceptor -- it would be valence-5, already refused), so every prior identity is byte-for-byte unchanged.
    assert canonical_digest(M(smiles).canonical())[:16] == probe.additive_no_regression()[smiles]


def test_unkekulisable_aromatic_still_fails_closed():
    # widening the accepted set must not defeat the guard: an aromatic ring with no valid Kekulé assignment raises.
    with pytest.raises(SmilesError):
        M("c1cc1")


@pytest.mark.parametrize("smiles", probe._FAIL_CLOSED_DECOYS)
def test_hypervalent_heteroatom_decoys_fail_closed(smiles):
    # evil-morty R46: the element-blind first cut let a NON-neutral-carbon exocyclic-pi atom (neutral n(=O), N-oxide
    # [n+]) reach an invalid hypervalence -- a fail-closed REFUSE became a silent wrong/invalid parse.  The donor rule
    # is now restricted to a NEUTRAL CARBON (valence-4 hard wall); every such decoy must raise.
    with pytest.raises(SmilesError):
        M(smiles)


@pytest.mark.parametrize("smiles", ["[O-][n+]1ccccc1", "[nH+]1ccccc1", "c1cc[nH+]cc1"])
def test_legit_charged_aromatics_still_parse(smiles):
    # the neutral-carbon narrowing + BEFORE-charge ordering must not regress the R41 charge whitelist: a
    # charge-separated pyridine N-oxide and pyridinium (no exocyclic-pi on the charged atom) still parse.
    assert M(smiles) is not None


@pytest.mark.parametrize("smiles", ["N=c1cccc[nH]1", "c1cc[nH]c(=NN=Cc2ccccc2)c1", "O=c1[nH]c(=NC)cc[nH]1"])
def test_nonterminal_exocyclic_pi_seam_is_consistent_with_rdkit(smiles):
    # dalembert R46 seam: a non-terminal exocyclic pi-system on a neutral ring carbon is the one place the
    # min-placement demand-pin is held by an incidental fact.  It does not crack: our identity equals RDKit's
    # INDEPENDENT kekulization of the same string.  DEV-VENV oracle; skipped on the committed baseline.
    Chem = pytest.importorskip("rdkit.Chem")
    ours = canonical_digest(M(smiles).canonical())
    rk_kekule = canonical_digest(M(Chem.MolToSmiles(Chem.MolFromSmiles(smiles), kekuleSmiles=True)).canonical())
    assert ours == rk_kekule, smiles


def test_exocyclic_pi_rule_is_valence_forced_not_a_heuristic():
    # the load-bearing safety claim: a ring carbon with BOTH an exocyclic double and a ring double is valence-5,
    # which the parser refuses -- so treating the exocyclic-pi carbon as an acceptor could only ever raise, never
    # silently mis-parse.  benzoquinone drawn aromatic exercises exactly this: it now kekulizes to p-benzoquinone.
    aromatic = M("O=c1ccc(=O)cc1")
    kekule = M("O=C1C=CC(=O)C=C1")
    assert canonical_digest(aromatic.canonical()) == canonical_digest(kekule.canonical())


@pytest.mark.parametrize("name", list(probe._FAMILY))
def test_family_member_is_the_true_compound_by_inchikey(name):
    # DEV-VENV oracle: bind each NAME to the external PubChem reality anchor, on BOTH spellings.  Skipped on the
    # committed baseline.  Guards against a mislabelled tautomer/isomer sneaking in under a real compound's name.
    Chem = pytest.importorskip("rdkit.Chem")
    from rdkit.Chem.inchi import MolToInchiKey
    aromatic, kekule = probe._FAMILY[name]
    assert MolToInchiKey(Chem.MolFromSmiles(kekule)) == _TRUE_INCHIKEYS[name], (name, "kekule")
    assert MolToInchiKey(Chem.MolFromSmiles(aromatic)) == _TRUE_INCHIKEYS[name], (name, "aromatic")
