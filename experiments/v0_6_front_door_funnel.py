"""The SmartChem 1.0 release FUNNEL harness -- v0.6 front-door stages (FUNNEL-01).

This is the permanent measurement instrument the 1.0 program (section 0.9.5) will extend.  For a stable
corpus of human chemical inputs it records, per case, how far each travels down the front-door funnel:

    input -> syntax represented -> composition resolved -> identity layer -> ambiguity classified
          -> structure represented -> structural-planning eligible

and produces BOTH per-case records and aggregate stage denominators.  It is deliberately NOT tuned to
maximise any percentage: a refusal (a malformed or parametric input) is a CORRECT front-door outcome, and
"structure represented / planning eligible = False" for a bare formula is the v0.6 identity law working, not
a failure.  The meter is built to be trustworthy first.

Run (prints the table + writes the committed artifact next to this file):

    .venv/bin/python experiments/v0_6_front_door_funnel.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from smartchem.identity_parse import IdentityParseError, InputKind, resolve_identity

_ARTIFACT = Path(__file__).with_name("RESULTS_v0_6_front_door_funnel.md")


@dataclass(frozen=True)
class Case:
    case_id: str
    raw_input: str
    requested_kind: InputKind
    note: str = ""  # what the case exercises (documentation only)


@dataclass
class FunnelRow:
    case_id: str
    raw_input: str
    requested_kind: str
    # stage flags (the funnel):
    syntax_represented: bool = False
    composition_resolved: bool = False
    identity_layer: str = "NONE"
    ambiguity_classified: bool = False
    structure_represented: bool = False
    structural_planning_eligible: bool = False
    # detail:
    normalized: str = ""
    composition: str = ""
    resolved_kind: str = ""
    registry_candidates: tuple[str, ...] = field(default_factory=tuple)
    refusal_reason: str = ""
    receipt_digest: str = ""


# -- the stable v0.6 front-door corpus (design corpus) -------------------------------------------------------
# Spans: ASCII / Unicode formulas, hydrates/adducts, charges, bracket ions, registered names, SMILES,
# same-formula isomers, an InChI formula sublayer, and the typed boundary refusals (malformed / parametric).
CORPUS: tuple[Case, ...] = (
    Case("f-water", "H2O", InputKind.AUTO, "ASCII formula, one registered isomer"),
    Case("f-caffeine", "C8H10N4O2", InputKind.AUTO, "ASCII formula, registered"),
    Case("f-caffeine-uni", "C₈H₁₀N₄O₂", InputKind.AUTO, "Unicode subscripts"),
    Case("f-ammsulfate", "(NH4)2SO4", InputKind.AUTO, "nested group"),
    Case("f-ammsulfate-uni", "(NH₄)₂SO₄", InputKind.AUTO, "Unicode nested group"),
    Case("f-cuso4-hyd", "CuSO4·5H2O", InputKind.AUTO, "middle-dot hydrate"),
    Case("f-cuso4-hyd-uni", "CuSO₄·5H₂O", InputKind.AUTO, "Unicode hydrate"),
    Case("f-cuso4-hyd-sp", "CuSO4 . 5 H2O", InputKind.AUTO, "spaced ASCII-dot hydrate"),
    Case("f-cacl2-hyd", "CaCl2·2H2O", InputKind.AUTO, "hydrate"),
    Case("f-alum", "Al2(SO4)3", InputKind.AUTO, "nested group x3"),
    Case("f-ferrocyanide-K", "K4[Fe(CN)6]", InputKind.AUTO, "square-bracket group"),
    Case("f-sulfate-ion", "SO4^2-", InputKind.FORMULA, "caret charge"),
    Case("f-sulfate-ion-uni", "SO₄²⁻", InputKind.FORMULA, "Unicode superscript charge"),
    Case("f-ammonium", "NH4+", InputKind.FORMULA, "bare-sign charge"),
    Case("f-ammonium-brk", "[NH4]+", InputKind.FORMULA, "bracket ion"),
    Case("f-ferrocyanide-ion", "[Fe(CN)6]4-", InputKind.FORMULA, "bracket-ion magnitude"),
    Case("f-ethanol-iso", "C2H6O", InputKind.AUTO, "AMBIGUITY: ethanol vs dimethyl ether"),
    Case("f-paracetamol-formula", "C8H9NO2", InputKind.FORMULA, "formula of paracetamol"),
    Case("n-paracetamol", "paracetamol", InputKind.AUTO, "registered NAME -> constitution"),
    Case("n-water", "water", InputKind.NAME, "explicit NAME"),
    Case("n-acetic-anhydride", "acetic anhydride", InputKind.AUTO, "registered NAME"),
    Case("s-paracetamol", "CC(=O)Nc1ccc(O)cc1", InputKind.AUTO, "SMILES -> constitution"),
    Case("s-methyl-acetate", "smiles:CC(=O)OC", InputKind.AUTO, "explicit smiles: prefix"),
    Case("s-methanol-CO", "CO", InputKind.AUTO, "SMILES methanol (NOT stolen as formula)"),
    Case("i-water", "InChI=1S/H2O/h1H2", InputKind.AUTO, "InChI formula sublayer"),
    Case("b-polymer", "(C2H4)n", InputKind.AUTO, "PARAMETRIC: refused, not coerced"),
    Case("b-interval", "C6H(12±2)O6", InputKind.AUTO, "PARAMETRIC interval: refused"),
    Case("b-bare-number", "2", InputKind.AUTO, "malformed: no atoms"),
    Case("b-empty-group", "()", InputKind.FORMULA, "malformed: empty group"),
    Case("b-dangling-sep", "CuSO4·", InputKind.FORMULA, "malformed: dangling separator"),
    Case("b-unknown-elt", "Xx2", InputKind.FORMULA, "malformed: unknown element"),
    Case("b-prose", "not a formula", InputKind.AUTO, "malformed: prose"),
)


def run_case(case: Case) -> FunnelRow:
    row = FunnelRow(case.case_id, case.raw_input, case.requested_kind.value)
    try:
        resolved = resolve_identity(case.raw_input, case.requested_kind)
    except IdentityParseError as exc:
        # a typed refusal is a CORRECT front-door outcome: the input never reached composition.
        row.refusal_reason = str(exc)
        return row
    row.syntax_represented = True
    row.composition_resolved = resolved.formula is not None
    row.identity_layer = resolved.receipt.identity_layer
    row.resolved_kind = resolved.receipt.resolved_kind.value
    row.normalized = resolved.receipt.normalized
    row.receipt_digest = resolved.receipt.digest
    if resolved.formula is not None:
        row.composition = "".join(f"{s}{n if n > 1 else ''}" for s, n in resolved.formula.counts)
        if getattr(resolved.formula, "charge", 0):
            row.composition += f"^{abs(resolved.formula.charge)}{'+' if resolved.formula.charge > 0 else '-'}"
    row.structure_represented = resolved.structure_perceived
    row.structural_planning_eligible = resolved.constitution_established
    # ambiguity is CLASSIFIED whenever composition is known: either a constitution is established, or it is a
    # composition-only identity whose (non-exhaustive) registry candidate set has been resolved.
    row.registry_candidates = tuple(getattr(c, "name", repr(c)) for c in resolved.registry_candidates)
    row.ambiguity_classified = row.composition_resolved
    return row


def run_funnel(corpus: "tuple[Case, ...]" = CORPUS) -> "tuple[list[FunnelRow], dict[str, int]]":
    rows = [run_case(c) for c in corpus]
    agg = {
        "total": len(rows),
        "syntax_represented": sum(r.syntax_represented for r in rows),
        "composition_resolved": sum(r.composition_resolved for r in rows),
        "ambiguity_classified": sum(r.ambiguity_classified for r in rows),
        "structure_represented": sum(r.structure_represented for r in rows),
        "structural_planning_eligible": sum(r.structural_planning_eligible for r in rows),
        "typed_refusal": sum(bool(r.refusal_reason) for r in rows),
    }
    return rows, agg


def render_markdown(rows: "list[FunnelRow]", agg: dict[str, int]) -> str:
    lines = [
        "# v0.6 Human Chemical Front Door -- release funnel",
        "",
        "Generated by `experiments/v0_6_front_door_funnel.py` (deterministic; re-run to refresh).",
        "This is the permanent 1.0 funnel instrument; a REFUSAL of a malformed/parametric input is a correct",
        "outcome, and `structure/eligible = -` for a bare formula is the identity law, not a miss.",
        "",
        "## Aggregate denominators",
        "",
        f"- cases: **{agg['total']}**",
        f"- syntax represented: **{agg['syntax_represented']}** (rest are typed refusals: {agg['typed_refusal']})",
        f"- composition resolved: **{agg['composition_resolved']}**",
        f"- ambiguity classified: **{agg['ambiguity_classified']}**",
        f"- structure represented: **{agg['structure_represented']}**",
        f"- structural-planning eligible: **{agg['structural_planning_eligible']}**",
        "",
        "## Per-case funnel",
        "",
        "| case | input | req | syn | comp | layer | ambig | struct | eligible | composition | candidates / refusal |",
        "|------|-------|-----|-----|------|-------|-------|--------|----------|-------------|----------------------|",
    ]

    def mark(b: bool) -> str:
        return "Y" if b else "-"

    for r in rows:
        detail = ", ".join(r.registry_candidates) if r.registry_candidates else ""
        if r.refusal_reason:
            detail = "REFUSED: " + r.refusal_reason.split(";")[0][:60]
        lines.append(
            f"| {r.case_id} | `{r.raw_input}` | {r.requested_kind} | {mark(r.syntax_represented)} | "
            f"{mark(r.composition_resolved)} | {r.identity_layer} | {mark(r.ambiguity_classified)} | "
            f"{mark(r.structure_represented)} | {mark(r.structural_planning_eligible)} | "
            f"{r.composition or '-'} | {detail or '-'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    rows, agg = run_funnel()
    md = render_markdown(rows, agg)
    _ARTIFACT.write_text(md, encoding="utf-8")
    print(md)
    print(f"[wrote {_ARTIFACT}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
