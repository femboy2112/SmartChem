"""ROUND-12 item 4 (ID-STEREO CONFIGURATION): the chirality-PARITY perception, and its differential tripwires.

``configuration_key`` / ``SmilesFeatures.configuration_digest`` establish the CONFIGURATION half of stereo perception
the isotope work explicitly deferred (graph canonicalisation cannot see chirality -- a reflection leaves the graph
unchanged).  For each perceivable ACYCLIC tetrahedral stereocentre it captures the parity of the neighbours' written
order relative to their 1-WL colour order, XORed with the ``@``/``@@`` sense -- a spelling-invariant handedness that
distinguishes enantiomers while a meso form still matches its own mirror.

Every "same molecule" pair below is same BY CONSTRUCTION: swapping two neighbours in a SMILES flips ``@``<->``@@``
for the identical molecule (the OpenSMILES rule), so a swap-with-sense-flip pair MUST share a key; a same-order
sense-flip pair MUST differ (it is the mirror image).  Scope boundary (honest, never faked): ring stereocentres,
WL-degenerate centres, double-bond E/Z, and CIP R/S *naming* are named ID-STEREO-01 deferrals -- they contribute no
descriptor rather than a guessed one.
"""
from smartchem.smiles import configuration_key, parse_smiles, parse_smiles_features
from smartchem.contracts import canonical_digest


def _same(a: str, b: str) -> bool:
    return configuration_key(a) == configuration_key(b)


def _differ(a: str, b: str) -> bool:
    return configuration_key(a) != configuration_key(b)


# -- spelling-invariance: provably-same molecules share a configuration key --------------------------------------

def test_configuration_key_is_invariant_across_spellings_of_one_enantiomer():
    # each pair swaps two neighbours AND flips the sense -> the SAME physical molecule (OpenSMILES), so keys agree.
    assert _same("N[C@@H](C)C(=O)O", "N[C@H](C(=O)O)C")        # swap the two branches
    assert _same("N[C@@H](C)C(=O)O", "C[C@H](N)C(=O)O")        # swap N and methyl (chain re-rooted)
    assert _same("N[C@@H](C)C(=O)O", "OC(=O)[C@H](C)N")        # reverse the traversal
    assert _same("[C@H](F)(Cl)Br", "[C@@H](Cl)(F)Br")          # swap first two branches
    assert _same("[C@H](F)(Cl)Br", "F[C@@H](Cl)Br")            # move F ahead of the centre
    assert _same("C[C@H](N)c1ccccc1", "C[C@@H](c1ccccc1)N")    # a stereocentre bearing an aromatic arm


# -- enantiomers get DISTINCT identities (the core value) -------------------------------------------------------

def test_enantiomers_get_distinct_configuration_identities():
    for left, right in [
        ("N[C@@H](C)C(=O)O", "N[C@H](C)C(=O)O"),               # D- vs L-alanine
        ("[C@H](F)(Cl)Br", "[C@@H](F)(Cl)Br"),                  # bromochlorofluoromethane
        ("C[C@H](N)c1ccccc1", "C[C@@H](N)c1ccccc1"),            # 1-phenylethylamine
        ("OC[C@@H](O)C=O", "OC[C@H](O)C=O"),                    # glyceraldehyde
    ]:
        assert _differ(left, right), (left, right)


def test_configuration_refines_constitution_for_enantiomers():
    """Two enantiomers share ONE constitution (they are the same graph) but MUST carry different configuration keys --
    the exact refinement the CONFIGURATION layer exists to add over CONSTITUTION."""
    d_form, l_form = parse_smiles("N[C@@H](C)C(=O)O"), parse_smiles("N[C@H](C)C(=O)O")
    assert canonical_digest(d_form.canonical()) == canonical_digest(l_form.canonical())   # SAME constitution
    assert _differ("N[C@@H](C)C(=O)O", "N[C@H](C)C(=O)O")                          # DIFFERENT configuration


def test_the_sense_is_load_bearing_not_a_boolean():
    """NAG tripwire (the recon's 'one-field-behind' hazard): the descriptor reads the '@'/'@@' SENSE, not a mere
    presence boolean.  '[C@H]' and '[C@@H]' differ ONLY in that sense, so if the sense were collapsed back to a bool
    both would key identically and this fails loudly -- pinning that the parity path never reverts to the old flag."""
    assert _differ("[C@H](F)(Cl)Br", "[C@@H](F)(Cl)Br")


# -- meso: a symmetric two-centre molecule is its own mirror (achiral), the subtle multi-centre case -------------

def test_meso_matches_its_mirror_but_the_chiral_diastereomers_do_not():
    meso_a = "O[C@H](C(=O)O)[C@@H](O)C(=O)O"
    meso_b = "O[C@@H](C(=O)O)[C@H](O)C(=O)O"          # the mirror image of meso -- the SAME (achiral) molecule
    rr = "O[C@H](C(=O)O)[C@H](O)C(=O)O"
    ss = "O[C@@H](C(=O)O)[C@@H](O)C(=O)O"             # (R,R) and (S,S): a genuine enantiomeric pair
    assert _same(meso_a, meso_b)                       # meso == its own mirror (achiral)
    assert _differ(rr, ss)                             # (R,R) != (S,S)
    assert _differ(meso_a, rr)                         # meso is a distinct diastereomer of (R,R)


# -- achiral / non-perceivable: reduces to constitution, never a fabricated descriptor --------------------------

def test_achiral_configuration_key_reduces_to_constitution():
    # no stereocentre: the key is constitution-equivalent (spelling-invariant), never None-or-crash.
    assert _same("CCO", "OCC")
    assert _same("CC(=O)O", "OC(C)=O")
    assert _differ("CCO", "COC")                       # still separates constitutional isomers


def test_a_false_stereocentre_carries_no_configuration_descriptor():
    """A marked centre with two identical substituents is NOT a stereocentre; it must NOT get a chirality descriptor
    (its key stays constitution-equivalent) -- a guessed parity there would be a fabricated distinction."""
    _, features = parse_smiles_features("C[C@](C)(N)O")   # two identical methyls -> not perceivable
    assert features.configuration_digest is None


def test_ring_stereocentres_are_scoped_out_to_none_never_a_guessed_parity():
    """A stereocentre ON a ring is out of the acyclic scope: its written neighbour order depends on the ring-closure
    DIGIT position, which the bond list does not preserve, so a reconstructed parity could be WRONG.  Such a centre
    must contribute NO descriptor (configuration_digest None), and configuration_key must reduce to constitution --
    so a ring centre can never be a false split OR a false conflation of enantiomers.  (evil-morty ROUND-12 caught a
    ring-OPENING centre slipping the old ``incoming>1`` guard and getting a wrong descriptor; this pins the fix.)
    """
    for smi in ["N[C@]1(F)CCCCO1", "N[C@@](F)1CCCCO1", "OC[C@H]1CCCCO1", "[C@H]1(F)CCCCO1"]:
        _, features = parse_smiles_features(smi)
        assert features.configuration_digest is None, smi
    # the two ring "enantiomer" spellings both reduce to the SAME constitution key -- no fabricated distinction.
    assert _same("N[C@]1(F)CCCCO1", "N[C@@]1(F)CCCCO1")
    # a ring SUBSTITUENT on an ACYCLIC centre is still perceived (the centre itself is not on the ring).
    _, phenyl = parse_smiles_features("C[C@H](N)c1ccccc1")
    assert phenyl.configuration_digest is not None


def test_configuration_digest_is_present_only_for_perceivable_stereocentres():
    _, chiral = parse_smiles_features("N[C@@H](C)C(=O)O")
    _, achiral = parse_smiles_features("CCO")
    assert chiral.configuration_digest is not None
    assert achiral.configuration_digest is None
    assert chiral.tetrahedral_stereo is True             # the presence flag still reads true
