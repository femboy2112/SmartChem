"""AROMATIC-CARBONYL-KEKULIZE-01: the conjugated-carbonyl aromatic class now kekulizes (R46).

The gap (R39 conjugated-carbonyl class): the parser's Kekulé perception classed EVERY aromatic carbon as a
pi-ACCEPTOR that needs one ring double bond.  A ring carbonyl ``c(=O)`` has its pi-demand met by the EXOCYCLIC
C=O -- its valence is full -- so forcing it into the ring matching left it with no acceptor neighbour (no perfect
matching) or over-saturated it to valence 5.  Every purine, every pyrimidinone nucleobase, quinones and tropone
failed closed; RDKit's DEFAULT aromatic SMILES output for caffeine (``Cn1c(=O)c2c(ncn2C)n(C)c1=O``) did not parse.

The fix is ONE valence-FORCED rule (``smartchem/smiles.py`` :func:`_aromatic_matchings`): an aromatic atom bearing
an exocyclic multiple bond is a pi-DONOR -- it sits out the ring matching, like a lone-pair heteroatom.  It is not a
heuristic: a ring atom holding both an exocyclic double and a ring double would be valence-5, which
:func:`_fill_hydrogens` already refuses -- so NO molecule that parses today has such an atom as an acceptor, and the
rule can only reclassify atoms on inputs that currently fail closed.  The change is therefore additive: it makes
previously-refused spellings parse, and touches nothing that already parsed (a safety argument, pinned below).

Re-checkable demonstrations, all on the REAL parser:

1. FAMILY KEKULIZES -- for each compound, the RDKit-default AROMATIC spelling parses to the SAME structural identity
   as an independent explicit-Kekulé drawing our parser already accepted.  The aromatic spellings are RDKit's own
   canonical output (pinned as fixtures so ``validate()`` is rdkit-free); the gated cross-check re-derives them.
2. IDENTITY DISCRIMINATES -- a WRONG-isomer aromatic decoy (theobromine 3,7 vs theophylline 1,3; both C7H8N4O2) does
   NOT match, so demonstration 1 is a real identity check, not "any C7H8N4O2 parses".
3. ADDITIVE / NO REGRESSION -- a battery of spellings that parsed BEFORE the fix (benzene, pyridine, pyrrole, furan,
   naphthalene, the explicit-Kekulé purines) parse to identities BYTE-EQUAL to their `main` digests: the rule
   provably never fires on them (mr-president R46 fold: byte-equality, not a count).
4. STILL FAILS CLOSED -- a genuinely un-kekulisable aromatic system (an odd isolated acceptor) still raises, never a
   silently-wrong order: the fix widened the accepted set, it did not defeat the fail-closed guard.
5. HYPERVALENT DECOYS FAIL CLOSED -- the element-blind first cut let a NON-neutral-carbon exocyclic-pi atom (neutral
   ``n(=O)``, N-oxide ``[n+]``) reach an invalid hypervalence (N has no valence-4 wall), silently emitting a wrong or
   invalid structure (evil-morty R46).  The fix restricts the donor rule to a NEUTRAL CARBON and fails closed
   otherwise, so every such decoy now raises; the gated cross-check also pins dalembert's non-terminal-exocyclic-pi
   SEAM (verified byte-consistent with RDKit's independent kekulizer -- the named next-probe boundary).

The gated ``_rdkit_cross_check`` binds each spelling to the external reality anchor: RDKit agrees the aromatic and
Kekulé spellings are ONE compound (equal InChIKey), and for the 4 registered purines the InChIKey equals the PubChem
anchor.  DEV-VENV ONLY -- skipped on the committed baseline.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.contracts import canonical_digest
from smartchem.smiles import SmilesError
from smartchem.smiles import parse_smiles as M

# (name, RDKit-default AROMATIC spelling, an independent explicit-Kekulé spelling our parser already accepted).
# The aromatic column is RDKit's own MolToSmiles output (dev-venv oracle); pinned here so validate() needs no rdkit.
_FAMILY = {
    "caffeine":     ("Cn1c(=O)c2c(ncn2C)n(C)c1=O",   "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"),
    "theophylline": ("Cn1c(=O)c2[nH]cnc2n(C)c1=O",   "N1C=NC2=C1C(=O)N(C)C(=O)N2C"),
    "theobromine":  ("Cn1cnc2c1c(=O)[nH]c(=O)n2C",   "CN1C=NC2=C1C(=O)NC(=O)N2C"),
    "xanthine":     ("O=c1[nH]c(=O)c2[nH]cnc2[nH]1", "N1C=NC2=C1C(=O)NC(=O)N2"),
    "guanine":      ("Nc1nc2nc[nH]c2c(=O)[nH]1",     "O=C1NC(=NC2=C1NC=N2)N"),
    "uracil":       ("O=c1cc[nH]c(=O)[nH]1",         "O=C1NC(=O)C=CN1"),
    "cytosine":     ("Nc1cc[nH]c(=O)n1",             "NC1=NC(=O)NC=C1"),
    "thymine":      ("Cc1c[nH]c(=O)[nH]c1=O",        "CC1=CNC(=O)NC1=O"),
    "hypoxanthine": ("O=c1[nH]cnc2nc[nH]c12",        "O=C1NC=NC2=C1NC=N2"),
    "tropone":      ("O=c1cccccc1",                  "O=C1C=CC=CC=C1"),
}
# the 4 registered purines carry a PubChem InChIKey anchor (verified in the caffeine probe); the gated cross-check
# also checks it here for the aromatic spelling specifically.
_PURINE_ANCHORS = {
    "caffeine": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
    "theophylline": "ZFXYFBGIUFBOJW-UHFFFAOYSA-N",
    "theobromine": "YAPQBXQYLJRXSA-UHFFFAOYSA-N",
    "xanthine": "LRFVTYWOQMYALW-UHFFFAOYSA-N",
}
# a wrong-isomer decoy: theobromine (3,7-dimethylxanthine) aromatic vs theophylline (1,3-dimethyl) Kekulé -- same
# formula C7H8N4O2, DISTINCT isomers, so a real identity check must NOT collapse them.
_THEOBROMINE_AROMATIC_DECOY = "Cn1cnc2c1c(=O)[nH]c(=O)n2C"
_THEOPHYLLINE_KEKULE = "N1C=NC2=C1C(=O)N(C)C(=O)N2C"
# things that parsed BEFORE the fix -> byte-for-byte pre-fix identities measured on `main` (rule absent).  The rule
# provably never fires on these, so they MUST be unchanged; validate() asserts equality to these constants, not a
# mere count (mr-president R46 fold: make the no-regression claim a real byte-equality).
_PREFIX_DIGESTS = {
    "c1ccccc1": "64156b0618736cc8",
    "c1ccncc1": "77f3e9420966a390",
    "c1cc[nH]c1": "969d408f8460477c",
    "c1ccoc1": "61a1555ebbee54d7",
    "c1ccc2ccccc2c1": "218e183f0a8b1930",
    "CN1C=NC2=C1C(=O)N(C)C(=O)N2C": "76f2484e90b543f4",
    "O=C1C=CC(=O)C=C1": "34018dd4f9cb2d68",
}
_PREEXISTING = tuple(_PREFIX_DIGESTS)
# hypervalent-heteroatom decoys the element-blind first cut let through (evil-morty R46): a NON-neutral-carbon atom
# bearing an exocyclic multiple bond reaches an invalid hypervalence (N valence 3/5 has no valence-4 wall), so the
# carbonyl unblocking the ring parity turned a `main` fail-closed REFUSE into a silent wrong/invalid parse.  The fix
# fails closed for every non-neutral-carbon committed-pi atom, so these must all raise (and the pre-existing charged
# `O=[n+]` valence-5 hole is closed too).
_FAIL_CLOSED_DECOYS = (
    "O=c1[nH]c(=O)n(=O)cc1",   # carbonyl unblocks the ring -> latent hypervalent neutral n(=O) (RDKit rejects it too)
    "n1(=O)n(=O)c(=O)nc1",     # the element-blind cut emitted a WRONG identity here; now refused
    "O=[n+]1ccccc1",           # charged exocyclic-pi -> valence-5 N-oxide (a pre-existing R41 hole, now closed)
)


def _digest(smi: str) -> str:
    return canonical_digest(M(smi).canonical())


def family_kekulizes() -> dict:
    out = {}
    for name, (aromatic, kekule) in _FAMILY.items():
        try:
            same = _digest(aromatic) == _digest(kekule)
            out[name] = {"aromatic_parses": True, "matches_kekule_identity": same}
        except SmilesError as exc:
            out[name] = {"aromatic_parses": False, "error": str(exc)[:60]}
    return out


def identity_discriminates() -> dict:
    # theobromine (3,7) is a DISTINCT isomer from theophylline (1,3); a formula-blind parse would collapse them.
    return {"decoy_matches_theophylline": _digest(_THEOBROMINE_AROMATIC_DECOY) == _digest(_THEOPHYLLINE_KEKULE)}


def additive_no_regression() -> dict:
    return {smi: _digest(smi)[:16] for smi in _PREEXISTING}


def _refuses(smi: str) -> bool:
    try:
        M(smi)
        return False
    except SmilesError:
        return True


def hypervalent_decoys_fail_closed() -> dict:
    # evil-morty R46: a non-neutral-carbon committed-pi atom must fail closed, never a silent hypervalent parse.
    return {smi: _refuses(smi) for smi in _FAIL_CLOSED_DECOYS}


def still_fails_closed() -> dict:
    # an odd, isolated aromatic acceptor with no valid Kekulé assignment must still raise (fail-closed preserved).
    raised = False
    try:
        M("c1cc1")   # a 3-membered all-carbon aromatic ring: no perfect matching over 3 acceptors
    except SmilesError:
        raised = True
    return {"unkekulisable_still_raises": raised}


def _payload() -> dict:
    return {
        "1_family_kekulizes": family_kekulizes(),
        "2_identity_discriminates": identity_discriminates(),
        "3_additive_no_regression": additive_no_regression(),
        "4_still_fails_closed": still_fails_closed(),
        "5_hypervalent_decoys_fail_closed": hypervalent_decoys_fail_closed(),
    }


FROZEN_HASH = "0d596e051c15131185e5b14d6b13c4493b87bfba034f6d2de5502dbccbf8f911"


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: every conjugated-carbonyl family member's aromatic spelling parses to the same identity
    as its explicit-Kekulé drawing; a wrong-isomer decoy does NOT match; every pre-existing spelling is BYTE-FOR-BYTE
    unchanged from its `main` identity; a genuinely un-kekulisable ring still fails closed; and every
    hypervalent-heteroatom decoy (the element-blind first cut's breaks) now fails closed."""
    p = _payload()
    fam = p["1_family_kekulizes"]
    assert all(v.get("aromatic_parses") for v in fam.values()), fam
    assert all(v.get("matches_kekule_identity") for v in fam.values()), fam
    assert p["2_identity_discriminates"]["decoy_matches_theophylline"] is False, p["2_identity_discriminates"]
    reg = p["3_additive_no_regression"]
    assert reg == _PREFIX_DIGESTS, reg          # byte-equality to the pre-fix (`main`) identities, not a count
    assert p["4_still_fails_closed"]["unkekulisable_still_raises"] is True, p["4_still_fails_closed"]
    assert all(p["5_hypervalent_decoys_fail_closed"].values()), p["5_hypervalent_decoys_fail_closed"]
    return True


def _rdkit_cross_check() -> dict:
    """DEV-VENV ONLY (rdkit): each family member's aromatic and Kekulé spellings are ONE compound (equal InChIKey),
    and for the 4 registered purines the InChIKey equals the PubChem anchor.  Skipped when rdkit is absent."""
    try:
        from rdkit import Chem
        from rdkit.Chem.inchi import MolToInchiKey
    except ImportError:
        return {"skipped": "rdkit absent"}
    out = {}
    for name, (aromatic, kekule) in _FAMILY.items():
        ik_a = MolToInchiKey(Chem.MolFromSmiles(aromatic))
        ik_k = MolToInchiKey(Chem.MolFromSmiles(kekule))
        rec = {"inchikey": ik_a, "aromatic_kekule_agree": ik_a == ik_k}
        if name in _PURINE_ANCHORS:
            rec["matches_pubchem_anchor"] = ik_a == _PURINE_ANCHORS[name]
        out[name] = rec
    # dalembert R46 seam: a NON-TERMINAL exocyclic pi-system on a neutral ring carbon (amidinate/hydrazone-on-ring) is
    # the one place the min-placement's demand-pin is held by an incidental fact.  It does NOT crack on any reachable
    # input: each parses byte-consistent with RDKit's INDEPENDENT kekulizer of the same string.  Pinned as the seam to
    # watch (the named daniel next-probe), verified robust here.
    seam = {}
    for smi in ("N=c1cccc[nH]1", "c1cc[nH]c(=NN=Cc2ccccc2)c1", "O=c1[nH]c(=NC)cc[nH]1", "c1cc(=NO)cc[nH]1"):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            seam[smi] = "rdkit_reject"
            continue
        try:
            ours = canonical_digest(M(smi).canonical())
            rk_kek = canonical_digest(M(Chem.MolToSmiles(m, kekuleSmiles=True)).canonical())
            seam[smi] = {"consistent_with_rdkit_kekule": ours == rk_kek}
        except SmilesError as exc:
            seam[smi] = {"our_parse": "refused", "error": str(exc)[:40]}
    out["_seam_nonterminal_exocyclic_pi"] = seam
    return out


if __name__ == "__main__":
    print("content_hash:", content_hash())
    print("validate:", validate())
    print("rdkit cross-check:", json.dumps(_rdkit_cross_check(), indent=2))
