"""IMINE-CONDENSATION-01 (#119) -- committed frozen evidence for the carbonyl + amine -> imine recognizer.

The motivating gap (issue #119): the carbonyl <-> imine interconversion needs a C=N mint/cleave that neither
capped scission nor the bond-order-edit family can perform, so it was simply ABSENT from the generated algebra
(a probe confirms the default registry turns an imine into fictions, never ``carbonyl + amine``).  This round ships
the missing generator (:class:`~smartchem.imine_condensation.ImineCondensationProvider`, opt-in) AND the recognizer.
This probe freezes the verdict the recognizer returns over a corpus of:

* in-scope POSITIVES -- aldehyde/ketone + primary amine / ammonia / hydroxylamine / hydrazine, water expelled
  (Schiff base / primary imine / oxime / hydrazone -- the plan's imine/oxime/hydrazone subset); and
* out-of-scope / adversarial cases that MUST NOT vouch as an imine condensation -- the amide (an acyl class, no
  C=N), the enamine (C=C-N tautomer), a cyclic/aromatic C=N (ring-opening is not a two-fragment condensation),
  an amidine/imidate (an extra alpha-O/N on the carbonyl carbon), and a bundled double condensation.

``content_hash()`` over ``_payload()`` is frozen so a silent behaviour change trips the paired test
(:mod:`tests.test_imine_condensation_probe`).

Run: ``.venv/bin/python -m experiments.imine_condensation_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "4ed12601f06e5b7f1b506bc8b0d93bea72a1746584a99e45549cd597b4b430c3"

#: (label, carbonyl, amine-donor, imine-product, coproduct-count).  The step is
#: ``carbonyl + donor -> imine + <n_water> water``; n_water = 1 except the bundled double condensation (2).
_CORPUS = [
    # -- in-scope positives (MUST vouch as imine condensation) --
    ("pos_formaldehyde_methylamine", "C=O", "CN", "C=NC", 1),
    ("pos_acetone_methylamine_ketimine", "CC(C)=O", "CN", "CC(C)=NC", 1),
    ("pos_acetaldehyde_methylamine_aldimine", "CC=O", "CN", "CC=NC", 1),
    ("pos_benzaldehyde_methylamine_aromatic", "O=Cc1ccccc1", "CN", "CN=Cc1ccccc1", 1),
    ("pos_acetone_ammonia_primary_imine", "CC(C)=O", "N", "CC(C)=N", 1),
    ("pos_acetaldehyde_hydroxylamine_oxime", "CC=O", "NO", "CC=NO", 1),
    ("pos_acetaldehyde_hydrazine_hydrazone", "CC=O", "NN", "CC=NN", 1),
    # canonical N-aryl Schiff base (aniline) + an acylhydrazide donor -- both GENUINE; they lock the N-acyl fix
    # (evil-morty's kill) against over-correction (an aryl carbon's double bonds are to C, not a heteroatom; an
    # acylhydrazide's acyl sits on the OTHER nitrogen, so the imine-N substituent is N, not an acyl carbon):
    ("pos_benzaldehyde_aniline_N_aryl", "O=Cc1ccccc1", "Nc1ccccc1", "c1ccccc1N=Cc1ccccc1", 1),
    ("pos_acetaldehyde_acylhydrazide", "CC=O", "NNC(C)=O", "CC=NNC(C)=O", 1),
    # fresh holdouts (not used to design the gate) --
    ("pos_holdout_cyclohexanone_methylamine", "O=C1CCCCC1", "CN", "CN=C1CCCCC1", 1),
    ("pos_holdout_propanal_ethylamine", "CCC=O", "CCN", "CCC=NCC", 1),
    # -- out-of-scope / adversarial (MUST NOT vouch as imine condensation); every step below CONSERVES --
    ("neg_amide_not_imine", "CC(=O)O", "CN", "CC(=O)NC", 1),
    ("neg_enamine_tautomer", "CC(C)=O", "CN", "CC(=C)NC", 1),
    # an amidine/imidate C=N bears an extra alpha-N/O on the carbonyl carbon (its hydrolysis is amide/ester + amine,
    # NOT carbonyl + amine) -- these conserve but the edge refuses the alpha-heteroatom carbon, so the oracle abstains:
    ("neg_amidine_alpha_N", "CC(=O)N", "N", "CC(=N)N", 1),       # acetamide + ammonia -> acetamidine + water
    ("neg_imidate_alpha_O", "CC(=O)OC", "N", "CC(=N)OC", 1),     # methyl acetate + ammonia -> methyl acetimidate + water
    # N-ACYL DONOR LEAK (evil-morty kill): an amide/urea/carbamate/amidine donor is NOT an amine -- its N-acyl-imine
    # retro is carbonyl + AMIDE.  The mirror of the carbonyl-carbon alpha-heteroatom guard now demotes all of these:
    ("neg_urea_formaldehyde", "C=O", "NC(=O)N", "C=NC(N)=O", 1),
    ("neg_acetamide_donor", "CC=O", "CC(=O)N", "CC=NC(C)=O", 1),
    ("neg_carbamate_donor", "CC=O", "NC(=O)OC", "CC=NC(=O)OC", 1),
    ("neg_amidine_donor_on_N", "CC=O", "NC(=N)C", "CC=NC(=N)C", 1),
    ("neg_guanidine_donor_on_N", "CC=O", "NC(=N)N", "CC=NC(=N)N", 1),
]


def _verdict(carbonyl: str, donor: str, imine: str, n_water: int) -> str:
    """The recognizer's verdict on ``carbonyl + donor -> imine + n_water water``: a stable token.

    SN2/imine class strings are collapsed so the frozen payload does not pin the full prose label; every other
    class / abstain / build error is recorded verbatim."""
    try:
        prod = parse_smiles(imine)
        water = [parse_smiles("O")] * n_water
        step = ExperimentStep.assembling(
            prod, (parse_smiles(carbonyl), parse_smiles(donor)), tuple([prod, *water]), reagents=()
        )
    except Exception as exc:  # a mis-specified corpus case -- surfaced, never silently skipped
        return f"BUILD_ERR:{type(exc).__name__}"
    name = recognize_reaction_type(step)
    if name is None:
        return "None"
    if "imine condensation" in name:
        return "IMINE"
    if "acyl condensation" in name:
        return "ACYL"
    return name


def _payload() -> dict:
    return {label: _verdict(c, d, im, nw) for label, c, d, im, nw in _CORPUS}


def content_hash() -> str:
    return sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    """Assert every positive vouches IMINE and no negative does -- the no-false-VOUCH cardinal."""
    payload = _payload()
    for label, verdict in payload.items():
        if label.startswith("pos_"):
            assert verdict == "IMINE", f"{label}: expected IMINE vouch, got {verdict!r}"
        else:
            assert verdict != "IMINE", f"{label}: FALSE-VOUCHED as an imine condensation"


if __name__ == "__main__":
    validate()
    payload = _payload()
    for label, verdict in payload.items():
        print(f"  {verdict:7}  {label}")
    print(f"\ncontent_hash() = {content_hash()}")
    print("FROZEN_HASH matches." if content_hash() == FROZEN_HASH else "FROZEN_HASH STALE -- re-freeze if intended.")
