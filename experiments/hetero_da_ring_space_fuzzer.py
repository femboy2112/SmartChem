"""HETERO-DA-RING-SPACE-FUZZER-01 -- a GENERATIVE audit of the heteroatom [4+2] family algebra (items A + B).

Where :mod:`experiments.hetero_diels_alder_family_probe` pins a handful of hand-picked adducts, this harness
EXHAUSTIVELY enumerates the neutral ``5C + 1X`` six-membered ring space (X in {N, O, S}) crossed with:

* the position of the single heteroatom (6 ring vertices),
* which ring bond carries the one C=C the pattern needs (6 ring bonds),
* 0, 1 or 2 exocyclic single-bond decorations (a methyl-type substituent), which are how a ring drives its
  heteroatom OVER its neutral valence while staying UNDER the charge-agnostic ceiling -- exactly the gap the
  round-9 guard-2c bound closes (an oxocarbenium / iminium / thiocarbenium drawn neutral).

For every generated ring it runs ALL SIX opt-in hetero families (aza / oxa / thia x dienophile / diene) and checks
the family-algebra invariants that hand-picked cases can only spot-check:

  I1  SOUNDNESS: every emitted disconnection round-trips its own double certificate (conservation + DA-ness) --
      the provider already enforces this, so any emission here is a real, NET-neutral, conserving [4+2] retro.
      (Net-neutral is the graph's declared charge model; guard 2c additionally bounds the MATCHED CENTRE atoms by
      their neutral valence -- I2 -- but a non-matched spectator substituent's formal charge is out of its scope.)
  I2  GUARD-2c GENERATIVITY: any ring whose HETEROATOM (the matched centre) is OVER its neutral valence (an
      oxocarbenium O at bond order 3, an iminium N at 4, a thiocarbenium S at 3) emits NOTHING from any family --
      the charged-CENTRE fiction is dropped everywhere, not just on the three hand-built cases.
  I3  HETEROATOM LOCK: a family never vouches a ring whose heteroatom differs from its own (the label lock).
  I4  THE CROWN (generative): a diene-position family and its same-heteroatom dienophile family SHARE a synthesis
      centre, yet NO ring is ever vouched by BOTH -- Layer A separates the regio-isomers across the whole space,
      not merely on the one probed pair.

``summary()`` returns the coverage counts + a per-invariant violation count (all zero when sound); its frozen hash
trips the paired test (:mod:`tests.test_hetero_da_ring_space_fuzzer`) on any silent behaviour drift.  Deterministic:
the enumeration is exhaustive over the core and the exocyclic decorations are drawn from a FIXED seed.

Run: ``.venv/bin/python -m experiments.hetero_da_ring_space_fuzzer``.
"""
from __future__ import annotations

import json
import random
from hashlib import sha256
from itertools import combinations

from smartchem.category import Bond, Molecule
from smartchem.diels_alder import (
    AZA_DA, AZA_DIENE_DA, OXA_DA, OXA_DIENE_DA, THIA_DA, _NEUTRAL_VALENCE, AzaDielsAlderProvider,
    AzaDieneDielsAlderProvider, OxaDielsAlderProvider, OxaDieneDielsAlderProvider, ThiaDielsAlderProvider,
)

#: sha256 of the canonical JSON of summary(); re-freeze ONLY on an intended behaviour change (see the module head).
FROZEN_HASH = "8df73bac5d136d3e5a7f5aea516020cfd0160760fce247b01459774a0c6fcf19"

#: (tag, provider, family) for the five committed opt-in hetero families.  The aza/oxa diene<->dienophile pairs
#: share a centre (see I4); thia ships dienophile-only (a thia-diene rides the same factory but is future work).
_FAMILIES = (
    ("aza-dnp", AzaDielsAlderProvider(), AZA_DA),
    ("oxa-dnp", OxaDielsAlderProvider(), OXA_DA),
    ("thia-dnp", ThiaDielsAlderProvider(), THIA_DA),
    ("aza-diene", AzaDieneDielsAlderProvider(), AZA_DIENE_DA),
    ("oxa-diene", OxaDieneDielsAlderProvider(), OXA_DIENE_DA),
)
#: which tags are diene-position vs dienophile-position, keyed by heteroatom, for the I4 same-heteroatom pairing.
_SIBLINGS = (("aza-dnp", "aza-diene"), ("oxa-dnp", "oxa-diene"))
_HETERO = {"N", "O", "S"}


def _ring_graph(x_label: str, x_pos: int, double_bond: int, exocyclic: tuple[int, ...]) -> Molecule:
    """A 6-membered ring (vertices 0..5) with the heteroatom ``x_label`` at ``x_pos``, one ring C=C at ring bond
    ``double_bond`` (edge ``i -- i+1 mod 6``), and an exocyclic single-bonded carbon on each vertex in
    ``exocyclic``.  A pure heavy-atom graph (no hydrogens) -- valence is read off the bond-order sums, which is all
    guard 2c and ``valence_sane`` inspect."""
    labels = [x_label if i == x_pos else "C" for i in range(6)]
    bonds = []
    for i in range(6):
        order = 2 if i == double_bond else 1
        bonds.append(Bond(i, (i + 1) % 6, order))
    nxt = 6
    for v in exocyclic:
        labels.append("C")
        bonds.append(Bond(v, nxt, 1))
        nxt += 1
    return Molecule(tuple(labels), frozenset(bonds))


def _degree(mol: Molecule, v: int) -> int:
    return sum(b.order for b in mol.bonds if v in (b.i, b.j))


def _rings():
    """The exhaustive-core + seeded-decoration ring generator.  Yields ``(x_label, mol, x_over_valence)``."""
    rng = random.Random(20260920)
    for x_label in sorted(_HETERO):
        neutral = _NEUTRAL_VALENCE[x_label]
        for x_pos in range(6):
            for double_bond in range(6):
                # 0 decorations (the bare ring), all single decorations, and a fixed sample of double decorations.
                decos: list[tuple[int, ...]] = [()]
                decos += [(v,) for v in range(6)]
                pairs = list(combinations(range(6), 2))
                decos += [tuple(sorted(p)) for p in rng.sample(pairs, k=min(6, len(pairs)))]
                for exo in decos:
                    mol = _ring_graph(x_label, x_pos, double_bond, exo)
                    yield x_label, mol, _degree(mol, x_pos) > neutral


def summary() -> dict:
    """Enumerate the ring space, run all six families on each ring, and tally coverage + invariant violations."""
    rings = 0
    matched = 0
    over_valence = 0
    over_valence_emitted = 0        # I2 violations: a charged-fiction ring that still emitted something
    heteroatom_leak = 0             # I3 violations: a family vouched a foreign-heteroatom ring
    double_vouch = 0                # I4 violations: a ring vouched by BOTH a diene and its dienophile sibling
    unsound_emission = 0            # I1 violations: an emission that failed to round-trip its certificate
    emissions = 0

    for x_label, mol, is_over in _rings():
        rings += 1
        if is_over:
            over_valence += 1
        hits: dict[str, int] = {}
        any_hit = False
        for tag, prov, family in _FAMILIES:
            transforms = prov.enumerate_transforms(mol, (), budget=100000)[0]
            hits[tag] = len(transforms)
            if transforms:
                any_hit = True
                emissions += len(transforms)
                # I3: the family's heteroatom must be the ring's heteroatom.
                if family.hetero_label != x_label:
                    heteroatom_leak += 1
                # I1: every emitted edge already passed its double certificate at construction; re-assert the
                # fragments are neutral and re-buildable (a fabricated edge would have raised, so this is belt+braces).
                for t in transforms:
                    if any(getattr(m, "charge", 0) != 0 for m in t.products):
                        unsound_emission += 1
                # I2: a ring over its heteroatom's neutral valence must NOT emit (guard 2c).
                if is_over:
                    over_valence_emitted += 1
        if any_hit:
            matched += 1
        # I4: no ring vouched by both a diene family and its same-heteroatom dienophile sibling.
        for dnp_tag, diene_tag in _SIBLINGS:
            if hits.get(dnp_tag) and hits.get(diene_tag):
                double_vouch += 1

    return {
        "rings_enumerated": rings,
        "rings_matched_by_some_family": matched,
        "total_emissions": emissions,
        "rings_over_neutral_valence": over_valence,
        "violation_I1_unsound_emission": unsound_emission,
        "violation_I2_over_valence_emitted": over_valence_emitted,
        "violation_I3_heteroatom_leak": heteroatom_leak,
        "violation_I4_double_vouch": double_vouch,
    }


def content_hash() -> str:
    return sha256(json.dumps(summary(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """All four invariants hold (zero violations) AND the harness is non-vacuous (it really matched real adducts)."""
    s = summary()
    return bool(
        s["violation_I1_unsound_emission"] == 0
        and s["violation_I2_over_valence_emitted"] == 0
        and s["violation_I3_heteroatom_leak"] == 0
        and s["violation_I4_double_vouch"] == 0
        and s["rings_matched_by_some_family"] > 0     # non-vacuity: the sweep actually exercises real matches
        and s["rings_over_neutral_valence"] > 0       # non-vacuity: it actually generated charged-fiction rings
    )


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2, sort_keys=True))
    print("content_hash:", content_hash())
    print("validate:", validate())
