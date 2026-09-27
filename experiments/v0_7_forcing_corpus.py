"""V0.7-FORCING-CORPUS-01: the certified route algebra widens generation across ALL EIGHT admitted Diels-Alder
families, not just the one alkene example `v0_7_forcing_vertical.py` used.

Round I's forcing vertical proved the eight forcing-vertical properties for exactly one family (the all-carbon
alkene retro-[4+2]).  This corpus reruns the load-bearing slice of that proof -- enumerated / re-derivation-
verified / class-vouched / no-cross-poach -- for EVERY family in `smartchem.algebra_profiles`'s
``certified-route-v07`` profile: alkene, alkyne, and the six heteroatom families (aza/oxa/thia at the dienophile
position, then aza/oxa/thia at the diene position).  It also reruns the hostile-near-miss and fresh-holdout
controls, and confirms the DEFAULT (legacy-capped-only) registry stays untouched throughout.

Every adduct SMILES below is COPIED from an already-committed, already-reviewed test file (grep the citation
in each family's row of ``FAMILIES``); none is invented here.  Where a family's retro fragments are needed (to
seed ``search_routes``' ``available`` precursor set), they are taken directly from that same family's own
provider re-derivation on the cited adduct -- never hand-typed -- so a fragment SMILES error cannot creep in
sideways.

Run:  .venv/bin/python experiments/v0_7_forcing_corpus.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from smartchem.algebra_profiles import resolve_algebra_profile
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY

_ARTIFACT = Path(__file__).with_name("RESULTS_v0_7_forcing_corpus.md")

#: the certified widened algebra: capped-scission + all 8 admitted DA families (never mutates the global default).
CERTIFIED = resolve_algebra_profile("certified-route-v07")

#: (name, witness_kind, adduct SMILES, class-vouch marker substring, source citation).  Every adduct SMILES is the
#: EXACT string already used as a positive adduct in the cited committed test file -- confirmed live below by
#: running the family's own provider on it and observing a witness (never hand-authored here).
FAMILIES: tuple[tuple[str, str, str, str, str], ...] = (
    ("alkene", "DIELS_ALDER", "C1CC=CCC1",
     "alkene dienophile -> cyclohexene", "tests/test_diels_alder.py"),
    ("alkyne", "DIELS_ALDER_ALKYNE", "C1=CCC=CC1",
     "alkyne dienophile -> 1,4-cyclohexadiene", "tests/test_alkyne_diels_alder.py"),
    ("aza-dienophile", "DIELS_ALDER_AZA", "C1C=CCCN1",
     "imine dienophile -> tetrahydropyridine", "tests/test_hetero_diels_alder.py"),
    ("oxa-dienophile", "DIELS_ALDER_OXA", "C1C=CCCO1",
     "carbonyl dienophile -> dihydropyran", "tests/test_hetero_diels_alder.py"),
    ("thia-dienophile", "DIELS_ALDER_THIA", "C1C=CCCS1",
     "thiocarbonyl dienophile -> dihydrothiopyran", "tests/test_hetero_diels_alder.py"),
    ("aza-diene", "DIELS_ALDER_AZA_DIENE", "N1C=CCCC1",
     "1-azadiene", "tests/test_hetero_diels_alder.py"),
    ("oxa-diene", "DIELS_ALDER_OXA_DIENE", "O1C=CCCC1",
     "1-oxadiene", "tests/test_hetero_diels_alder.py"),
    # thia-diene has NO adduct in test_hetero_diels_alder.py (only aza/oxa-diene are covered there); its adduct is
    # copied from the round that actually admitted it: tests/test_transform_algebra_expansion.py.
    ("thia-diene", "DIELS_ALDER_THIA_DIENE", "C1CCC=CS1",
     "1-thiadiene", "tests/test_transform_algebra_expansion.py"),
)

_ALL_DA_KINDS = frozenset(kind for _, kind, _, _, _ in FAMILIES)

# Hostile near-misses (guard coverage, not a design target for any family): an enone (ring carbonyl would retro
# to a fictional ketene), a saturated ring (no pi system at all), benzene (aromatic, no isolated diene/dienophile).
HOSTILE: tuple[tuple[str, str], ...] = (
    ("enone", "O=C1CCCC=C1"),
    ("saturated ring", "C1CCCCC1"),
    ("benzene", "c1ccccc1"),
)

# Fresh substituted holdouts for the two all-carbon families -- NOT used to design any family's rule, and (per
# Lane D) the two families lacking an exhaustive ring-space fuzzer unlike the six hetero siblings.  Confirmed live
# below to still enumerate their own family's retro (never asserted from prior memory).
HOLDOUTS: tuple[tuple[str, str, str], ...] = (
    ("ethyl-substituted cyclohexene", "CCC1CCC=CC1", "DIELS_ALDER"),
    ("methyl-substituted 1,4-cyclohexadiene", "CC1=CCC=CC1", "DIELS_ALDER_ALKYNE"),
)


def check(results: list, name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def _da_kinds(registry, reactant) -> tuple[dict, bool]:
    """``{witness_kind: [EnumeratedTransform, ...]}`` over every DIELS_ALDER* witness ``registry`` emits for
    ``reactant`` (reagentless), plus the aggregate completeness flag."""
    ets, complete = registry.enumerate(reactant, (), budget=100_000)
    by_kind: dict = {}
    for e in ets:
        if e.witness_kind.startswith("DIELS_ALDER"):
            by_kind.setdefault(e.witness_kind, []).append(e)
    return by_kind, complete


def run() -> list:
    r: list = []
    total_candidates = 0
    total_time = 0.0

    for name, kind, smiles, marker, source in FAMILIES:
        t0 = time.time()
        target = parse_smiles(smiles)
        by_kind, complete = _da_kinds(CERTIFIED, target)
        mine = by_kind.get(kind, [])
        others = sorted(k for k in by_kind if k != kind)

        # enumerated: the certified registry emits >=1 witness of exactly this family's kind.
        check(r, f"{name}: enumerated", len(mine) >= 1 and complete,
              f"witness_kind={kind}, n={len(mine)}, complete={complete} (adduct {smiles!r} from {source})")

        # independently/redundantly verified: the emitted edge exists at all only because its OWN __post_init__
        # (conservation + DA-ness re-derivation) already passed -- a fabricated edge is refused before it ever
        # reaches this list (proven directly in each family's own test file; re-confirmed here structurally by
        # rebuilding the synthesis step from the SAME transform and letting its independent certificate re-run).
        edge = mine[0].transform if mine else None
        step0 = None
        if edge is not None:
            fragments = edge.products
            with_da = search_routes(target, reagents=(), available=fragments, registry=CERTIFIED, max_depth=2)
            step0 = with_da.routes[0].steps[0] if with_da.routes else None
        else:
            with_da = None
        check(r, f"{name}: re-derived + reachable", edge is not None and with_da is not None
              and len(with_da.routes) >= 1,
              f"routes found under the certified registry: {len(with_da.routes) if with_da else 0}")

        # class-vouched: the oracle recognizes the generated step as THIS family (marker substring present).
        cls = recognize_reaction_type(step0) if step0 is not None else None
        check(r, f"{name}: class-vouched", cls is not None and marker.lower() in cls.lower() and "diels" in cls.lower(),
              f"oracle class={cls!r}, expected marker={marker!r}")

        # no cross-poach: no OTHER DA family's witness_kind fires on this adduct.
        check(r, f"{name}: no cross-poach", others == [],
              f"other DIELS_ALDER* witness kinds emitted for this adduct: {others} (must be empty)")

        # the DEFAULT (legacy-capped-only) registry emits nothing here.
        d_by_kind, _ = _da_kinds(DEFAULT_TRANSFORM_REGISTRY, target)
        check(r, f"{name}: default registry stays silent", d_by_kind == {},
              f"default DA witness kinds: {sorted(d_by_kind)} (must be empty)")

        total_candidates += sum(len(v) for v in by_kind.values())
        total_time += time.time() - t0

    check(r, "aggregate: 8/8 families each fired exactly their own kind",
          len({name for name, ok, _ in r if ok and name.endswith(": enumerated")}) == len(FAMILIES),
          f"{sum(1 for name, ok, _ in r if ok and name.endswith(': enumerated'))}/8 families enumerated")
    check(r, "aggregate: candidate/runtime sanity",
          total_candidates >= len(FAMILIES) and total_time < 10.0,
          f"total DA-kind candidates considered across all 8 targets={total_candidates}, "
          f"wall time={total_time * 1000:.1f}ms (budget-bounded search_routes calls included)")

    # --- hostile near-misses: zero DA witnesses under EITHER registry ---
    for name, smiles in HOSTILE:
        target = parse_smiles(smiles)
        c_by_kind, _ = _da_kinds(CERTIFIED, target)
        d_by_kind, _ = _da_kinds(DEFAULT_TRANSFORM_REGISTRY, target)
        check(r, f"hostile near-miss ({name}): certified registry emits zero DA witnesses", c_by_kind == {},
              f"certified DA witness kinds for {smiles!r}: {sorted(c_by_kind)} (must be empty)")
        check(r, f"hostile near-miss ({name}): default registry emits zero DA witnesses", d_by_kind == {},
              f"default DA witness kinds for {smiles!r}: {sorted(d_by_kind)} (must be empty)")

    # --- fresh holdouts: NOT used to design any family, still enumerate their own family's retro ---
    for name, smiles, expected_kind in HOLDOUTS:
        target = parse_smiles(smiles)
        c_by_kind, _ = _da_kinds(CERTIFIED, target)
        d_by_kind, _ = _da_kinds(DEFAULT_TRANSFORM_REGISTRY, target)
        check(r, f"fresh holdout ({name}): certified registry enumerates its family",
              expected_kind in c_by_kind and len(c_by_kind[expected_kind]) >= 1,
              f"certified DA witness kinds for {smiles!r}: {sorted(c_by_kind)} (need {expected_kind!r})")
        check(r, f"fresh holdout ({name}): default registry stays silent", d_by_kind == {},
              f"default DA witness kinds for {smiles!r}: {sorted(d_by_kind)} (must be empty)")

    return r


def render_markdown(results: list) -> str:
    lines = [
        "# v0.7 forcing corpus -- the certified route algebra widens generation across all 8 admitted DA families",
        "",
        "Generated by `experiments/v0_7_forcing_corpus.py`. Candidate registry: "
        "`smartchem.algebra_profiles.resolve_algebra_profile(\"certified-route-v07\")` "
        "(`CappedScissionProvider` + the 8 DA providers). `DEFAULT_TRANSFORM_REGISTRY` is never mutated.",
        "",
        "Adduct SMILES per family (each copied verbatim from an already-committed test file):",
        "",
        "| family | witness_kind | adduct | source |",
        "|---|---|---|---|",
    ]
    for name, kind, smiles, _marker, source in FAMILIES:
        lines.append(f"| {name} | {kind} | `{smiles}` | `{source}` |")
    lines += [
        "",
        "| property | verdict | detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    passed = sum(1 for _, ok, _ in results if ok)
    lines += ["", f"**{passed}/{len(results)} properties hold.** "
              + ("All eight admitted Diels-Alder families widen generation through the unchanged route search, "
                 "each class-vouched with no cross-poach, with the default registry stable throughout."
                 if passed == len(results)
                 else "A property FAILED -- the corpus is not sound as stated."), ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("v0.7 forcing corpus -- all 8 admitted Diels-Alder families through the unchanged route search:")
    results = run()
    md = render_markdown(results)
    _ARTIFACT.write_text(md, encoding="utf-8")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} properties hold. [wrote {_ARTIFACT}]")
    if passed != len(results):
        print("FORCING CORPUS FAILED.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
