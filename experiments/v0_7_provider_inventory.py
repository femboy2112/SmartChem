"""V0.7-INVENTORY-01: the transform provider/family inventory (Production Chemical Algebra, Round I).

Before abstraction, the ground truth.  0.7's job is to make the provider/rule architecture -- not
capped-scission-only defaults plus a parallel recognition catalogue -- the actual generative spine of
ordinary SmartChem use.  That requires knowing, per family, EXACTLY what exists: a generator, a provider,
whether it is a production default or opt-in, whether it is strict-rank or lateral, its reaction-centre
witness, its independent class recognizer, and how its grammar IDENTITY is declared today.

This harness produces that inventory two ways so it cannot drift into fiction:

* **LIVE-INTROSPECTED** columns come from instantiating each provider and reading its real
  ``identity`` / ``capability_manifest`` / ``witness_kind`` and testing membership in
  :data:`~smartchem.transform_provider.DEFAULT_TRANSFORM_REGISTRY`.  These are not inferred from class
  names -- they are what the objects actually report at runtime.
* **SOURCE-CITED** columns (route-capable vs decompile-only, strict-rank vs lateral, oracle recognition,
  generator location, soundness boundary) are architectural facts that a provider object does not expose;
  each is annotated with the ``module:line`` it was read from, never guessed.

Run (prints the table + writes the committed artifact next to this file):

    .venv/bin/python experiments/v0_7_provider_inventory.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    CappedScissionProvider,
    HeterolyticScissionProvider,
    RedoxHalfReactionProvider,
)

_ARTIFACT = Path(__file__).with_name("RESULTS_v0_7_provider_inventory.md")


@dataclass(frozen=True)
class Annotation:
    """The SOURCE-CITED architectural facts a provider object does not expose (each with its cite)."""

    generator: str            # where the structural rewrite is produced
    default_or_optin: str     # "DEFAULT" | "opt-in" | "no-provider (registry-excluded)"
    descent: str              # "strict-rank" | "lateral/rank-flat" | "reagentless-charged"
    route_capable: str        # "route+DAG" | "decompile-only"
    oracle_class: str         # which of the 17 recognizer classes, or "NONE (unrecognized)"
    boundary: str             # the stated soundness boundary
    cite: str                 # module:line the row was read from


# The families that CAN be introspected as live providers (no-arg dataclasses), each paired with its
# source-cited annotation.  Import paths are only added when the provider constructs cleanly with no args.
def _live_providers():
    from smartchem.bond_order_edit import BondOrderEditProvider
    from smartchem.diels_alder import (
        AlkyneDielsAlderProvider,
        AzaDielsAlderProvider,
        AzaDieneDielsAlderProvider,
        DielsAlderProvider,
        OxaDielsAlderProvider,
        OxaDieneDielsAlderProvider,
        ThiaDielsAlderProvider,
        ThiaDieneDielsAlderProvider,
    )
    from smartchem.redox_displacement import RedoxDisplacementProvider
    from smartchem.rule_calculus_bridge import AuditedCappedScissionProvider

    return [
        (CappedScissionProvider(), Annotation(
            "structure_descent.capped_scissions", "DEFAULT", "strict-rank", "route+DAG",
            "acyl/ether/N-alkylation (via centre)", "neutral-only, reagent-mediated, k=1",
            "transform_provider.py:107")),
        (DielsAlderProvider(), Annotation(
            "retro_da_disconnections", "opt-in", "strict-rank (2->1)", "route+DAG",
            "class 4 (DA alkene)", "empty-state carbocyclic; 3-cert (conservation+DA-ness+budget)",
            "diels_alder.py:469")),
        (AlkyneDielsAlderProvider(), Annotation(
            "retro_alkyne_da_disconnections", "opt-in", "strict-rank (2->1)", "route+DAG",
            "class 5 (DA alkyne)", "empty-state; alkyne dienophile", "diels_alder.py:614")),
        (AzaDielsAlderProvider(), Annotation(
            "hetero_da_disconnections", "opt-in", "strict-rank", "route+DAG",
            "class 6 (aza-DA)", "heterocyclic; (C,N,.) centre", "diels_alder.py:907")),
        (OxaDielsAlderProvider(), Annotation(
            "hetero_da_disconnections", "opt-in", "strict-rank", "route+DAG",
            "class 7 (oxa-DA)", "(C,O,.) centre", "diels_alder.py:915")),
        (ThiaDielsAlderProvider(), Annotation(
            "hetero_da_disconnections", "opt-in", "strict-rank", "route+DAG",
            "class 8 (thia-DA)", "(C,S,.) centre; guard-2c S:2 load-bearing", "diels_alder.py:923")),
        (AzaDieneDielsAlderProvider(), Annotation(
            "hetero_da_disconnections", "opt-in", "strict-rank", "route+DAG",
            "class 9 (aza-diene DA)", "Layer-A-only separation from aza-DA (shared centre)",
            "diels_alder.py:931")),
        (OxaDieneDielsAlderProvider(), Annotation(
            "hetero_da_disconnections", "opt-in", "strict-rank", "route+DAG",
            "class 10 (oxa-diene DA)", "Layer-A-only separation", "diels_alder.py:940")),
        (ThiaDieneDielsAlderProvider(), Annotation(
            "hetero_da_disconnections", "opt-in", "strict-rank", "route+DAG",
            "class 13 (thia-diene DA)", "Layer-A-only separation", "diels_alder.py:949")),
        (HeterolyticScissionProvider(), Annotation(
            "structure_descent.heterolytic_scissions", "opt-in", "reagentless-charged", "decompile-only",
            "NONE (unrecognized)", "widens DECOMPILE algebra only; charged ions", "transform_provider.py:143")),
        (RedoxHalfReactionProvider(), Annotation(
            "structure_descent.redox_couples", "opt-in", "reagentless-charged", "decompile-only",
            "NONE (unrecognized)", "charge-only; never claims spontaneity/potential", "transform_provider.py:172")),
        (RedoxDisplacementProvider(), Annotation(
            "combine_half_reactions", "opt-in", "reagentless-charged", "decompile-only",
            "NONE (unrecognized)", "certifies EXISTS, not that it occurs (enumerates unfavourable too)",
            "redox_displacement.py:367")),
        (BondOrderEditProvider(), Annotation(
            "bond_order_edits", "opt-in", "strict-rank (mass-reducing)", "route+DAG",
            "NONE (unrecognized)", "certifies EXISTS, not that dehydrogenation runs", "bond_order_edit.py:214")),
        (AuditedCappedScissionProvider(), Annotation(
            "CappedScissionProvider + rule_calculus.apply/verify replay", "opt-in", "strict-rank", "route+DAG",
            "delegates to the 17 via recognize_reaction_type", "fails closed (ScissionError re-raise), not a chemistry-evidence replacement",
            "rule_calculus_bridge.py:158")),
    ]


# The 6 lateral families have NO provider by construction (LateralRewriteEdge.forget() RAISES; strict-rank
# W1 at decompiler.py:342 makes a rank-flat isomerization unsound inside the recursive descent).  They are
# reachable only through lateral_search.py's standalone bounded BFS, never the registry seam.  Listed as
# source-cited rows (they cannot be instantiated as TransformProviders, so they are annotation-only).
_LATERAL_ONLY = [
    ("cope-[3,3]", "class 11", "lateral_rewrite.py:83"),
    ("claisen-[3,3]", "class 12", "lateral_rewrite.py:86"),
    ("aza-claisen-[3,3]", "class 14", "lateral_rewrite.py:89"),
    ("thia-claisen-[3,3]", "class 15", "lateral_rewrite.py:94"),
    ("electrocyclization-4pi", "class 16", "lateral_rewrite.py:136"),
    ("electrocyclization-6pi", "class 17", "lateral_rewrite.py:139"),
]


def _oracle_class_count() -> int:
    """LIVE count of the reaction-type oracle's recognizers (its positive whitelist)."""
    from smartchem.experiment import reaction_type_oracle as oracle

    recognizers = getattr(oracle, "_RECOGNIZERS", None)
    return len(recognizers) if recognizers is not None else -1


def _manifest_str(manifest: tuple) -> str:
    return "; ".join(f"{k}={v}" for k, v in manifest)


def build_rows():
    default_ids = set(DEFAULT_TRANSFORM_REGISTRY.provider_ids)
    rows = []
    for provider, ann in _live_providers():
        ident = provider.identity  # LIVE: (id, version, manifest)
        rows.append({
            "provider_id": ident[0],
            "provider_version": ident[1],
            "witness_kind": provider.witness_kind,
            "in_default": provider.provider_id in default_ids,          # LIVE membership test
            "manifest": _manifest_str(provider.capability_manifest),    # LIVE declared manifest
            "generator": ann.generator,
            "default_or_optin": ann.default_or_optin,
            "descent": ann.descent,
            "route_capable": ann.route_capable,
            "oracle_class": ann.oracle_class,
            "boundary": ann.boundary,
            "cite": ann.cite,
        })
    return rows


def render_markdown(rows, oracle_n: int, default_ids: tuple) -> str:
    lines = [
        "# v0.7 Production Chemical Algebra -- transform provider/family inventory",
        "",
        "Generated by `experiments/v0_7_provider_inventory.py` (deterministic; re-run to refresh). LIVE columns",
        "(id/version/witness/in_default/manifest) are read from the instantiated provider objects; the remaining",
        "columns are SOURCE-CITED architectural facts (see `cite`).",
        "",
        f"- reaction-type oracle recognizers (LIVE `_RECOGNIZERS`): **{oracle_n}**",
        f"- DEFAULT_TRANSFORM_REGISTRY members (LIVE): **{list(default_ids)}**",
        "",
        "## The gap, in one line",
        "",
        "The oracle RECOGNISES " + str(oracle_n) + " reaction classes; the DEFAULT registry GENERATES with "
        + str(len(default_ids)) + " provider(s). Recognition is a downstream demoter (never wired into",
        "generation); every non-capped family that has a provider is opt-in, and the 6 lateral families cannot",
        "enter the registry seam at all. **Chemistry recognised != chemistry generated by ordinary SmartChem.**",
        "",
        "## Providers (LIVE-introspected + source-cited)",
        "",
        "| provider_id | ver | witness | in_default | default/opt-in | descent | route? | oracle class | generator | boundary | cite |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['provider_id']}` | {r['provider_version']} | {r['witness_kind']} | "
            f"{'YES' if r['in_default'] else '-'} | {r['default_or_optin']} | {r['descent']} | "
            f"{r['route_capable']} | {r['oracle_class']} | `{r['generator']}` | {r['boundary']} | {r['cite']} |"
        )
    lines += [
        "",
        "## Lateral-only families (NO provider possible -- registry-excluded by W1)",
        "",
        "`LateralRewriteEdge.forget()` raises by design; strict-rank descent (`decompiler.py:342`) makes a",
        "rank-flat isomerization unsound inside the recursive search, so these are reachable ONLY through",
        "`lateral_search.py`'s standalone bounded BFS -- never a `TransformProvider`.",
        "",
        "| family | oracle class | cite |",
        "|---|---|---|",
    ]
    for name, cls, cite in _LATERAL_ONLY:
        lines.append(f"| {name} | {cls} | {cite} |")
    lines += [
        "",
        "## Manifests (LIVE declared capability_manifest per provider)",
        "",
    ]
    for r in rows:
        lines.append(f"- `{r['provider_id']}`: {r['manifest']}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = build_rows()
    oracle_n = _oracle_class_count()
    default_ids = DEFAULT_TRANSFORM_REGISTRY.provider_ids
    md = render_markdown(rows, oracle_n, default_ids)
    _ARTIFACT.write_text(md, encoding="utf-8")
    print(md)
    print(f"[wrote {_ARTIFACT}]")
    # A machine-checkable summary line for tests.
    optin = sum(1 for r in rows if not r["in_default"])
    print(f"[summary] providers_live={len(rows)} in_default={len(default_ids)} opt_in={optin} "
          f"lateral_only={len(_LATERAL_ONLY)} oracle_recognizers={oracle_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
