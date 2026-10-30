"""SN2-RECOGNITION-01 (#112) -- committed frozen evidence for the SN2-at-sp3-carbon reaction-TYPE recognizer.

The motivating gap (from issue #112): capped scission already EMITS these when the halide-salt byproduct is in
the pool (Williamson ethers, thioethers, halide amine-alkylation), and every one read ``recognize_reaction_type
-> None`` before this recognizer -- a conserved, real reaction demoted as unrecognized.  This probe freezes the
verdict the recognizer now returns over a corpus of:

* in-scope POSITIVES -- O/N/S nucleophile, halide leaving group, sp3 non-tertiary carbon, counterion carried
  explicitly (so the neutral graph never needs a bare ion: the #105-wall-respecting SN2 subset); and
* out-of-scope / adversarial cases that MUST NOT vouch as SN2 -- the centre-identical SNAr / vinylic / acyl
  collisions, a tertiary (SN1) centre, a non-halide leaving group, and the deferred carbon-nucleophile (nitrile).

``content_hash()`` over ``_payload()`` is frozen so a silent behaviour change trips the paired test
(:mod:`tests.test_sn2_recognition_probe`).

Run: ``.venv/bin/python -m experiments.sn2_recognition_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "5f2c80f946ca86549b0f2793b10389008a1d73ee39608dd8d476a8c510c3bff2"

#: (label, target, R-X, Nu-source, coproduct).  The target is R-Nu; the step is `R-X + Nu-source -> target + coproduct`.
_CORPUS = [
    # -- in-scope positives (MUST vouch as SN2) --
    ("pos_williamson_Et2O_O_primary", "CCOCC", "CCBr", "CCO[Na]", "[Na]Br"),
    ("pos_thioether_Et2S_S_salt", "CCSCC", "CCBr", "CCS[Na]", "[Na]Br"),
    ("pos_amine_EtNHMe_N_neutral_HBr", "CCNC", "CCBr", "CN", "Br"),
    ("pos_secondary_iPrOMe_O", "COC(C)C", "CC(C)Br", "CO[Na]", "[Na]Br"),
    ("pos_benzyl_PhCH2OMe_O_benzylic", "COCc1ccccc1", "BrCc1ccccc1", "CO[Na]", "[Na]Br"),
    ("pos_holdout_propyl_methyl_ether", "CCCOC", "CCCBr", "CO[Na]", "[Na]Br"),
    ("pos_holdout_allyl_methyl_ether_Cl", "C=CCOC", "C=CCCl", "CO[Na]", "[Na]Cl"),
    ("pos_holdout_iodoethane_O_I_LG", "CCOC", "CCI", "CO[Na]", "[Na]I"),
    # -- out-of-scope / adversarial (MUST NOT vouch as SN2) --
    ("neg_MTBE_tertiary_SN1", "COC(C)(C)C", "CC(C)(C)Br", "CO[Na]", "[Na]Br"),
    ("neg_SNAr_aryl_centre", "COc1ccccc1", "Brc1ccccc1", "CO[Na]", "[Na]Br"),
    ("neg_vinylic_sp2_centre", "COC=C", "BrC=C", "CO[Na]", "[Na]Br"),
    ("neg_acyl_carbonyl_centre", "COC(C)=O", "CC(=O)Br", "CO[Na]", "[Na]Br"),
    ("neg_nonhalide_hydroxide_LG", "CCOCC", "CCO", "CCO[Na]", "[Na]O"),
    ("deferred_nitrile_carbon_nucleophile", "CCC#N", "CCBr", "[Na]C#N", "[Na]Br"),
    # -- adversary-found SN1 oxocarbenium / carbene centres (evil-morty + d'Alembert kills) --
    ("neg_ketal_oxocarbenium_evilmorty", "CC(C)(OC)OC", "CC(C)(Cl)OC", "CO[Na]", "[Na]Cl"),
    ("neg_orthocarbonate_evilmorty", "COC(OC)(OC)OC", "COC(OC)(OC)Cl", "CO[Na]", "[Na]Cl"),
    ("neg_methylal_alpha_O_dalembert", "COCOC", "ClCOC", "CO[Na]", "[Na]Cl"),
    ("neg_orthoformate_dalembert", "COC(OC)OC", "ClC(OC)OC", "CO[Na]", "[Na]Cl"),
    ("neg_dithioacetal_alpha_S_dalembert", "CSCSC", "ClCSC", "CS[Na]", "[Na]Cl"),
    ("neg_aminal_alpha_N_dalembert", "CN(C)CN(C)C", "ClCN(C)C", "CNC", "Cl"),
    ("neg_carbene_not_tetravalent_dalembert", "[C](C)OC", "[C](C)Br", "CO[Na]", "[Na]Br"),
]


def _verdict(target_smi: str, rx: str, nu: str, coproduct: str) -> str:
    """The recognizer's verdict on `R-X + Nu -> target + coproduct`: the class string, or "None"/"BUILD_ERR:...".

    SN2 verdicts are collapsed to the stable token "SN2" so the frozen payload does not pin the full prose label
    (which may be reworded without a behaviour change); every other class / abstain is recorded verbatim."""
    try:
        target = parse_smiles(target_smi)
        step = ExperimentStep.assembling(target, (parse_smiles(rx), parse_smiles(nu)),
                                         (target, parse_smiles(coproduct)), reagents=())
    except Exception as exc:  # a mis-specified corpus case -- surfaced, never silently skipped
        return f"BUILD_ERR:{type(exc).__name__}"
    name = recognize_reaction_type(step)
    if name is None:
        return "None"
    return "SN2" if "SN2 substitution" in name else name


def _payload() -> dict:
    return {label: _verdict(tgt, rx, nu, cop) for label, tgt, rx, nu, cop in _CORPUS}


def content_hash() -> str:
    return sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    """Assert every positive vouches SN2 and every negative/deferred does not -- the no-false-VOUCH cardinal."""
    payload = _payload()
    for label, verdict in payload.items():
        if label.startswith("pos_"):
            assert verdict == "SN2", f"{label}: expected SN2 vouch, got {verdict!r}"
        else:
            assert verdict != "SN2", f"{label}: FALSE-VOUCHED as SN2"


if __name__ == "__main__":
    validate()
    payload = _payload()
    for label, verdict in payload.items():
        print(f"  {verdict:5}  {label}")
    print(f"\ncontent_hash() = {content_hash()}")
    print("FROZEN_HASH matches." if content_hash() == FROZEN_HASH else "FROZEN_HASH STALE -- re-freeze if intended.")
