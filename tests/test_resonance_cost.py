"""ROUND-12 item 1: the resonance-identity COST investigation, made executable.

The ROUND-11 DoS guards on :func:`smartchem.smiles.resonance_canonical` cap HEAVY-ATOM COUNT
(``_RESONANCE_MAX_HEAVY``) and PLACEMENT COUNT (``_RESONANCE_MAX_MATCHINGS``); above either, a molecule keeps
its plain literal-bond-order identity (no cross-Kekulé unification, but always a VALID identity).  ROUND-12
asked whether a *cheaper* placement could LIFT those caps.  The investigation refuted the two "obvious" cheap
wins; these tests pin the refutation so nobody re-walks the dead paths, and double as the fused-aromatic
unification regression net for whoever eventually builds the robust fix.

1. **The "canonicalise the DRAWN Kekulé form" shortcut is UNSOUND.**  Naphthalene has NON-ISOMORPHIC Kekulé forms
   (central bond double vs single) that are the SAME molecule; their plain ``canonical()`` digests DIFFER, so
   canonicalising whichever form was drawn gives the WRONG identity for one of them.  Only enumerate-every-placement-
   and-take-the-minimum recovers ONE identity.  ``test_the_drawn_kekule_form_is_not_the_resonance_identity`` pins this.
   (A cheaper *constitution-signature* PARTITION -- canonicalise the sigma skeleton coloured by per-atom pi-demand,
   no enumeration -- is actually SOUND: it unifies naphthalene's forms exactly as enumeration does, because a
   resonance class IS determined by (sigma skeleton, per-atom pi-demand, H, charge).  So the barrier to a cheap win
   is NOT partition-unsoundness; it is that such a key emits DIFFERENT digest VALUES -- every fixture/frozen digest
   keyed on ``resonance_identity`` would move -- and reproducing the enumeration's SAME minimum VALUE cheaply still
   needs the placement search.  So this file does NOT claim the constitution signature is unsound; it claims only the
   drawn-form shortcut is.)

2. **No cheap PREDICTIVE proxy bounds the per-placement cost** (measured, ROUND-12).  Per-placement
   ``Molecule.canonical()`` cost is driven by an interaction of molecule SIZE, PLACEMENT COUNT, and residual
   SYMMETRY -- a large asymmetric fused system grinds despite low symmetry, while a highly symmetric one (coronene)
   is fast; a symmetry-only gate both misses the former and mis-ranks the latter.  The only robust guard is a
   running work-meter *inside* the canonicaliser, which conflicts with ``Molecule.canonical()``'s ``lru_cache`` and
   is therefore a MEASURED core change -- named as a next-step, deliberately NOT gambled here.  The safe ROUND-11
   caps are retained unchanged; this file adds no new production code, only the tripwires.
"""
from smartchem.category import Bond, Molecule
from smartchem.contracts import canonical_digest
from smartchem.smiles import parse_smiles, resonance_identity
from smartchem.structure import resolve_structure

# naphthalene C10H8 sigma skeleton: C0..C9 with C8,C9 the shared bridgeheads (no H); C0..C7 peripheral (1 H each).
_NAPHTHALENE_SIGMA = [(0, 1), (1, 2), (2, 3), (3, 8), (8, 9), (9, 0), (8, 7), (7, 6), (6, 5), (5, 4), (4, 9)]


def _naphthalene_kekule(doubles: list[tuple[int, int]]) -> Molecule:
    """A naphthalene ``Molecule`` built by DIRECT graph surgery (never through the parser, so it is NOT
    pre-resonance-canonicalised) with the given C-C bonds drawn double and every peripheral carbon carrying its H."""
    dset = {frozenset(e) for e in doubles}
    bonds = [Bond(i, j, 2 if frozenset((i, j)) in dset else 1) for (i, j) in _NAPHTHALENE_SIGMA]
    bonds += [Bond(k, 10 + k, 1) for k in range(8)]      # C0..C7 each bear one explicit H (H10..H17)
    return Molecule(tuple(["C"] * 10 + ["H"] * 8), frozenset(bonds), 0)


# the two classic Kekulé structures of naphthalene: they share ONE constitution but are non-isomorphic graphs.
_FORM_CENTRAL_DOUBLE = _naphthalene_kekule([(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])   # bridgehead bond 8=9
_FORM_CENTRAL_SINGLE = _naphthalene_kekule([(9, 0), (3, 8), (1, 2), (5, 4), (7, 6)])   # bridgehead bond 8-9


def test_the_drawn_kekule_form_is_not_the_resonance_identity():
    """The naive 'canonicalise the drawn Kekulé form' shortcut is UNSOUND -- enumeration is REQUIRED to find the min.

    Both forms are the SAME molecule (naphthalene, C10H8, identical sigma skeleton / per-atom H / pi-demand), but
    their DRAWN graphs are non-isomorphic (distinct plain canonical digests), so canonicalising whichever form was
    drawn gives two different answers -- one of them WRONG.  Only the enumerate-and-minimise ``resonance_identity``
    recovers the single correct identity for both.  (This does NOT show a constitution-SIGNATURE key is unsound --
    that key would unify them correctly; see the module docstring for the real barrier, a digest-VALUE change.)
    """
    assert _FORM_CENTRAL_DOUBLE.formula == {"C": 10, "H": 8}
    assert _FORM_CENTRAL_SINGLE.formula == {"C": 10, "H": 8}
    # the drawn forms are GENUINELY non-isomorphic -- a signature-blind shortcut would pick the wrong one.
    plain_double = canonical_digest(_FORM_CENTRAL_DOUBLE.canonical())
    plain_single = canonical_digest(_FORM_CENTRAL_SINGLE.canonical())
    assert plain_double != plain_single
    # ... yet resonance identity UNIFIES them (enumerate every placement, take the minimum representative).
    res_double = resonance_identity(_FORM_CENTRAL_DOUBLE)
    res_single = resonance_identity(_FORM_CENTRAL_SINGLE)
    assert res_double == res_single


def test_fused_aromatic_identity_is_the_minimal_kekule_representative():
    """Naphthalene's resonance identity is exactly the MINIMUM of its Kekulé forms' plain canonical digests,
    and the parser lands on the same value -- so a fragment cut of naphthalene and its parsed form agree."""
    forms = [canonical_digest(_FORM_CENTRAL_DOUBLE.canonical()),
             canonical_digest(_FORM_CENTRAL_SINGLE.canonical())]
    expected = min(forms)                                  # the resonance-canonical representative = the minimum
    assert resonance_identity(_FORM_CENTRAL_DOUBLE) == expected
    assert resonance_identity(_FORM_CENTRAL_SINGLE) == expected
    assert resonance_identity(parse_smiles("c1ccc2ccccc2c1")) == expected


def test_resolve_structure_resolves_a_kekule_flipped_aromatic_fragment():
    """ROUND-12: ``resolve_structure`` keys on RESONANCE identity, so a scission FRAGMENT whose aromatic ring carries
    the OTHER Kekulé pattern still resolves to its registered parsed form.

    This is what lets the aspirin sourced-conditions record attach: the ortho-salicylate fragment cut out of aspirin
    is a Kekulé-flipped salicylic acid, which plain ``canonical()`` calls distinct (so the ROUND-11 search found the
    route but the record could not attach).  A revert of ``resolve_structure`` to plain canonical fails this loudly.
    """
    sal = parse_smiles("O=C(O)c1ccccc1O")
    ring = [i for i, s in enumerate(sal.atoms) if s == "C"
            and sum(1 for b in sal.bonds if i in (b.i, b.j) and sal.atoms[b.i] == sal.atoms[b.j] == "C") >= 2]
    ringset = set(ring)
    flipped_bonds = [
        Bond(b.i, b.j, (1 if b.order == 2 else 2)) if (b.i in ringset and b.j in ringset
                                                       and sal.atoms[b.i] == sal.atoms[b.j] == "C") else b
        for b in sal.bonds
    ]
    flipped = Molecule(sal.atoms, frozenset(flipped_bonds), sal.charge, sal.state)
    # the flip is a genuinely different graph under PLAIN canonical (that is why plain resolution missed it) ...
    assert canonical_digest(flipped.canonical()) != canonical_digest(sal.canonical())
    # ... yet both resolve to the SAME registered structure under resonance identity.
    assert resolve_structure(sal) is not None and resolve_structure(sal).name == "salicylic acid"
    assert resolve_structure(flipped) is not None
    assert resolve_structure(flipped).name == "salicylic acid"


def _perplacement_costs(smi: str) -> list[int]:
    """The per-placement ``_canonical_cost`` (a deterministic candidate count, NOT a timing) that ``resonance_canonical``
    pays canonicalising ``smi``.  Instruments the un-cached canonicaliser; restores it afterward."""
    import smartchem.category as cat
    costs: list[int] = []
    orig = getattr(cat.Molecule.canonical, "__wrapped__", cat.Molecule.canonical)

    def _rec(self):
        costs.append(cat._canonical_cost(self.atoms, self.bonds))
        return orig(self)

    saved = cat.Molecule.canonical
    cat.Molecule.canonical = _rec
    try:
        resonance_identity(parse_smiles(smi))
    finally:
        cat.Molecule.canonical = saved
    return costs


def test_round13_no_canonical_cost_proxy_separates_legit_slow_from_crafted_slow():
    """ROUND-13 item 3 (the REFUTATION tripwire): the caps are NOT lifted by a ``_canonical_cost`` work budget, because
    no such budget is a sound runtime bound.  Pinned by two structural facts (reproduced in
    experiments/resonance_cost_proxy_probe.py), so nobody re-walks the recon's dead design (A):

    1. A LEGIT PAH (triphenylene) has a per-placement PERMUTATION ``_canonical_cost`` at least as high as a crafted
       under-cap grind -- so any per-placement-cost cut that bails the grind also bails legit molecules.
    2. Real coronene is the fast one yet has an ASTRONOMICAL nominal ``_canonical_cost`` (individualisation branch), so a
       raw ``_canonical_cost`` budget would bail a FAST molecule.  ``_canonical_cost`` tracks runtime in NEITHER branch.
    """
    from smartchem.smiles import _RESONANCE_MAX_HEAVY, _RESONANCE_MAX_MATCHINGS
    from smartchem.category import _MAX_CANONICAL_CANDIDATES
    # the naive lift was NOT shipped: the ROUND-11 caps stand unchanged.
    assert (_RESONANCE_MAX_HEAVY, _RESONANCE_MAX_MATCHINGS) == (64, 128)

    def _max_perm(smi):  # the most expensive PERMUTATION-branch placement (individualisation-branch ones are exempt)
        return max((c for c in _perplacement_costs(smi) if c <= _MAX_CANONICAL_CANDIDATES), default=0)

    grind = _max_perm("c1cc2ccc3ccc4ccc5ccc1c1c2c3c4c51")       # a 20-heavy under-cap crafted grind
    triphenylene = _max_perm("c1ccc2c(c1)c1ccccc1c1ccccc21")    # a LEGIT fused PAH, also slow
    assert grind > _MAX_CANONICAL_CANDIDATES // 10              # the grind IS an expensive permutation placement ...
    assert triphenylene >= grind                                # ... yet a legit molecule out-costs it: no clean cut

    # real coronene: the FAST molecule, but its own canonical cost is astronomically above the permutation threshold,
    # so a raw _canonical_cost meter would (wrongly) bail it -- the over-charge half of the refutation.
    coronene = parse_smiles("c1cc2ccc3ccc4ccc5ccc6ccc1c1c2c3c4c5c61")
    assert _canonical_cost_of(coronene) > _MAX_CANONICAL_CANDIDATES * 1000


def _canonical_cost_of(mol) -> int:
    from smartchem.category import _canonical_cost
    return _canonical_cost(mol.atoms, mol.bonds)


def test_fused_aromatics_unify_across_spellings():
    """Regression net for any future placement optimisation: every fused aromatic below MUST keep ONE identity
    across its spellings (aromatic and explicit-Kekulé), and the three species MUST stay mutually distinct."""
    families = {
        "naphthalene": ["c1ccc2ccccc2c1", "C1=CC=C2C=CC=CC2=C1", "C1=CC2=CC=CC=C2C=C1"],
        "anthracene": ["c1ccc2cc3ccccc3cc2c1", "C1=CC=C2C=C3C=CC=CC3=CC2=C1"],
        "phenanthrene": ["c1ccc2ccc3ccccc3c2c1", "c1ccc2c(c1)ccc1ccccc12"],
    }
    identities = {}
    for name, spellings in families.items():
        ids = {resonance_identity(parse_smiles(s)) for s in spellings}
        assert len(ids) == 1, f"{name} split into {len(ids)} identities across spellings"
        identities[name] = ids.pop()
    assert len(set(identities.values())) == 3            # the three fused aromatics are distinct species
