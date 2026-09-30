"""V0.9.5-FUZZ-01: seeded boundary fuzzers over the compiler's REPRESENTATIONS (Part 18).

**Ugh, fine -- five ways to hand the compiler something weird.** Every family has ONE declared property, a seeded
generator, and automatic shrinking of a failing input to a minimal repro.  These fuzz *representations* (formula
spellings, identity graphs, quantity vectors, wire payloads, search receipts) -- never synthesis instructions.  A found
failure is a FINDING (written to ``experiments/fuzz_repros/``), never hidden and never fixed here: this harness edits no
production code.

Families (property in brackets):

* ``frontdoor``   formula spellings (Unicode confusables, separators, charge spellings, nesting, length, malformed
                  coefficients).  [never a crash (only IdentityParseError), bounded time, and when accepted: the composition
                  equals the INTENDED composition of a meaning-preserving spelling, the render()->parse round trip is a fixed
                  point, and on the AUTO surface a different-composition SMILES reading is never chosen silently]
* ``identity``    formula-isomer pairs, atom-permutation respellings, Kekule graph-surgery pairs, stereo/isotope features.
                  [constitutional isomers stay DISTINCT; respellings/Kekule flips of ONE structure share the resonance key;
                  every stereo/isotope feature is DISCLOSED as an identity loss on the request; the stock layer must match
                  a Kekule respelling (known:S7 until landed)]
* ``allocation``  quantity knife edges, multi-component packages, mixed units, unknown quantities, duplicate packages,
                  through ``assess`` (material axis).  [NEVER FIT when a demand exceeds supply; never double-spend a package;
                  never FIT an unquantified demand] -- graded against an INDEPENDENT max-flow reference
* ``wire``        key deletion/insertion, type mutation, nested schema substitution, public-digest recomputation, transport
                  downgrade, legacy-id smuggling on a canonical payload.  [refused, or accepted only if semantically
                  identical (response_semantic_fields + result digest equal)]
* ``receipts``    search-receipt bound/count/stop-reason/completeness mutation (+ consistent multi-field rewrites).
                  [refused]   (a consistent rewrite of the ADVISORY IR status is the documented barrier-S11 boundary and is
                  classified known:S11, not new)

Run:  .venv/bin/python experiments/v0_9_5_boundary_fuzz.py [--seed 950] [--budget 1.0] [--family wire,receipts]
                                                          [--write-repros] [--json out.json]
``--budget`` scales every family's case count (1.0 = the committed default).  Exit 0 iff no NEW (non-known) finding.
"""
from __future__ import annotations

import copy
import dataclasses as dc
import hashlib
import json
import random
import re
import sys
import time
import traceback
from collections import Counter
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (str(REPO), str(REPO / "experiments")):
    if p not in sys.path:
        sys.path.insert(0, p)

REPRO_DIR = REPO / "experiments" / "fuzz_repros"
DEFAULT_CASES = {"frontdoor": 700, "identity": 90, "allocation": 500, "wire": 160, "receipts": 110}


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha(obj) -> str:
    return hashlib.sha256((obj if isinstance(obj, str) else canon(obj)).encode()).hexdigest()


class Findings:
    """Deduplicated findings; each keeps its first minimal repro."""

    def __init__(self, family: str):
        self.family = family
        self.items: "dict[str, dict]" = {}
        self.cases = 0
        self.known = Counter()
        self.notes: "list[str]" = []

    def add(self, signature: str, prop: str, repro: dict, detail: str, known: "str | None" = None, count: int = 1):
        key = f"{prop}|{signature}"
        if known:
            self.known[f"{known}: {prop}|{signature}"] += count
            return
        if key in self.items:
            self.items[key]["count"] += count
            return
        self.items[key] = {"family": self.family, "property": prop, "signature": signature, "detail": detail[:400],
                           "repro": repro, "count": count}


# ====================================================================================================================
# generic shrinker (ddmin over a sequence) -------------------------------------------------------------------------
# ====================================================================================================================
def ddmin(seq, fails, budget=200):
    """Minimal sub-sequence for which ``fails(sub)`` still holds (classic ddmin, bounded)."""
    seq = list(seq)
    n = 2
    steps = 0
    while len(seq) >= 2 and steps < budget:
        chunk = max(1, len(seq) // n)
        subsets = [seq[i:i + chunk] for i in range(0, len(seq), chunk)]
        reduced = False
        for i in range(len(subsets)):
            comp = [x for j, s in enumerate(subsets) if j != i for x in s]
            steps += 1
            if comp and fails(comp):
                seq, n, reduced = comp, max(n - 1, 2), True
                break
        if not reduced:
            if n >= len(seq):
                break
            n = min(len(seq), n * 2)
    return seq


# ====================================================================================================================
# F1 -- front door ---------------------------------------------------------------------------------------------------
# ====================================================================================================================
_SUB = "₀₁₂₃₄₅₆₇₈₉"
_FULL = "０１２３４５６７８９"
_SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_ELEMS = ["H", "C", "N", "O", "S", "P", "Cl", "Br", "Na", "K", "Ca", "Mg", "Fe", "Cu", "Zn", "Al", "Si", "F"]
_HOMO = {"C": "С", "O": "О", "H": "Н", "N": "Ν", "S": "Ѕ", "P": "Р", "K": "Κ"}   # Cyrillic/Greek look-alikes
_SEPS = ["·", "∙", "⋅", "•", ".", "*", " ", " ", "\t"]
_ZW = ["​", "‌", "‍", "﻿", "­"]


def _digits(n: int, style: str) -> str:
    s = str(n)
    if style == "sub":
        return "".join(_SUB[int(c)] for c in s)
    if style == "full":
        return "".join(_FULL[int(c)] for c in s)
    if style == "sup":
        return "".join(_SUP[int(c)] for c in s)
    return s


def _comp_str(atoms, style, homo):
    out = []
    for sym, cnt in atoms:
        s = _HOMO.get(sym, sym) if homo and sym in _HOMO else sym
        out.append(s + (_digits(cnt, style) if cnt > 1 else ""))
    return "".join(out)


def gen_formula(rng: random.Random):
    """-> (text, intended {sym:count} | None, intended charge | None, kind).  kind: 'valid'|'confusable'|'malformed'."""
    n_comp = rng.choice([1, 1, 1, 2, 2, 3])
    comps = []
    for _ in range(n_comp):
        atoms = [(rng.choice(_ELEMS), rng.choice([1, 1, 2, 3, 4, 6, 12])) for _ in range(rng.randint(1, 4))]
        comps.append((rng.choice([1, 1, 1, 2, 5, 12]), atoms))
    charge = rng.choice([0, 0, 0, 0, 1, -1, 2, -2, 3])
    style = rng.choice(["ascii", "ascii", "sub", "full", "sup"])
    homo = rng.random() < 0.25
    sep = rng.choice(_SEPS)
    parts = []
    intended: "dict[str, int]" = {}
    for mult, atoms in comps:
        body = _comp_str(atoms, style, homo)
        group = 1
        if rng.random() < 0.2 and len(atoms) > 1:      # a group with a multiplier: (SO4)3 style nesting
            group = rng.choice([2, 3])
            body = f"({body}){_digits(group, style)}"
        for sym, cnt in atoms:
            intended[sym] = intended.get(sym, 0) + cnt * mult * group
        parts.append((f"{_digits(mult, style)}" if mult > 1 else "") + body)
    text = sep.join(parts)
    kind = "valid"
    # charge spelling
    if charge:
        mag = abs(charge)
        sign = "+" if charge > 0 else "-"
        alt_minus = rng.choice(["-", "−", "–", "-"]) if sign == "-" else "+"
        spell = rng.choice(["caret", "caret", "plain", "bracket", "sup", "space"])
        if spell == "caret":
            text += f"^{mag if mag != 1 else ''}{alt_minus}"
        elif spell == "plain":
            text += f"{mag if mag != 1 else ''}{alt_minus}"
        elif spell == "bracket":
            text = f"[{text}]{mag if mag != 1 else ''}{alt_minus}"
        elif spell == "sup":
            text += ("".join(_SUP[int(c)] for c in str(mag)) if mag != 1 else "") + ("⁺" if sign == "+" else "⁻")
        else:
            text += f" {mag if mag != 1 else ''}{alt_minus}"
    if rng.random() < 0.12:
        pos = rng.randrange(len(text) + 1)
        text = text[:pos] + rng.choice(_ZW + [" "]) + text[pos:]
    if homo or style != "ascii" or sep not in ("·",) or charge:
        kind = "confusable"
    if rng.random() < 0.28:                          # malformed: ONE structural mutation of the (already odd) text
        op = rng.choice(["del", "dup", "ins", "zero", "big", "paren", "lead", "trail", "long"])
        i = rng.randrange(max(1, len(text)))
        if op == "del":
            text = text[:i] + text[i + 1:]
        elif op == "dup":
            text = text[:i] + text[i] + text[i:]
        elif op == "ins":
            text = text[:i] + rng.choice("()[]^+-.*0123456789 ,;/\\") + text[i:]
        elif op == "zero":
            text = text[:i] + "0" + text[i:]
        elif op == "big":
            text = text[:i] + "9" * rng.choice([6, 20, 400]) + text[i:]
        elif op == "paren":
            text = "(" * rng.randint(1, 60) + text + ")" * rng.randint(0, 60)
        elif op == "lead":
            text = rng.choice(["·", "^", "+", "5", "0", "(", "."]) + text
        elif op == "trail":
            text = text + rng.choice(["·", "^", "+", "-", "5", "(", ".", "^2", "·5"])
        else:
            text = text * rng.choice([50, 500, 3000])
        kind = "malformed"
        intended = None
    return text, intended, (charge if kind != "malformed" else None), kind


def _formula_counts(formula) -> "dict[str, int]":
    return {s: c for s, c in formula.counts}


_R2 = re.compile(r"[0-9\uff10-\uff19\u2080-\u2089][+\-\u2212\u2013]$")
_R1 = re.compile(r"\S\s+[0-9\uff10-\uff19\u2080-\u2089\u2070-\u2079\u00b2\u00b3\u00b9]")


_R1_STRICT = re.compile(r"[0-9\uff10-\uff19\u2080-\u2089]\s+[0-9\uff10-\uff19\u2080-\u2089]")


def _root_cause(text, counts, charge, intended_charge) -> str:
    """Attribute a silent mis-parse to a root cause by ABLATION (never by guessing): does removing the whitespace give
    the parser's own reading (R1), or is it the bare-trailing-sign charge rule (R2)?"""
    if intended_charge and abs(intended_charge) > 1 and abs(charge) == 1 and _R2.search(text):
        return "R2 bare trailing-sign charge: 'X3+' read as +1 with count 3"
    if any(c.isspace() for c in text) and _R1.search(text):
        return "R1 whitespace silently deleted: adjacent number tokens merge ('Zn2 5F' -> Zn25F)"
    return "R0 unclassified"


def frontdoor_property(text, intended, intended_charge, kind, auto=False):
    """-> (violated_property_id | None, detail)."""
    from smartchem.formula_expr import normalize_formula_text, parse_formula_expr
    from smartchem.identity_parse import IdentityParseError, InputKind, detect_auto_ambiguity, resolve_identity

    t0 = time.perf_counter()
    try:
        r = resolve_identity(text, InputKind.AUTO if auto else InputKind.FORMULA)
    except IdentityParseError:
        return None, "refused (typed)"
    except RecursionError as exc:
        return "P-crash", f"RecursionError: {str(exc)[:80]}"
    except Exception as exc:  # noqa: BLE001 -- the property: only IdentityParseError may escape the front door
        return "P-crash", f"{type(exc).__name__}: {str(exc)[:120]}"
    dt = time.perf_counter() - t0
    if dt > 3.0:
        return "P-slow", f"{dt:.1f}s for a {len(text)}-char input"
    counts = _formula_counts(r.formula)
    charge = getattr(r.formula, "charge", 0)
    if auto and kind != "malformed" and r.formula_expr is None:
        # AUTO chose the SMILES/NAME reading; it must agree with the intended composition OR the ambiguity must be flagged
        if intended is not None and (counts != intended or charge != (intended_charge or 0)) \
                and detect_auto_ambiguity(text) is None:
            return "P-auto-silent-misread", f"AUTO read {text!r} as {r.receipt.resolved_kind.value} {counts} (intended {intended})"
    if r.formula_expr is not None:
        fe = r.formula_expr
        try:
            again = parse_formula_expr(fe.render())
        except Exception as exc:  # noqa: BLE001
            return "P-roundtrip", f"render() of an accepted parse does not reparse: {type(exc).__name__}: {str(exc)[:80]}"
        if again.to_formula() != fe.to_formula():
            return "P-roundtrip", "render()->parse changed the composition"
        n1 = normalize_formula_text(text)
        if normalize_formula_text(n1) != n1:
            return "P-normalize-idempotent", f"normalize is not idempotent on {text!r}"
        if any(c.multiplier <= 0 for c in fe.components) or any(v <= 0 for v in counts.values()):
            return "P-nonpositive", "accepted a non-positive count/multiplier"
        if kind != "malformed" and intended is not None:
            if counts != intended or charge != (intended_charge or 0):
                return f"P-silent-misparse[{_root_cause(text, counts, charge, intended_charge)}]", (
                    f"{text!r} accepted as {counts} charge {charge}; intended {intended} charge {intended_charge}")
    return None, "accepted"


def _shrink_text(text, fails):
    chars = list(text)
    return "".join(ddmin(chars, lambda c: fails("".join(c))))


_SEED_CORPUS = [   # deterministic, human-legible cases run first (the ones a chemist actually types)
    ("CuSO4 5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0, "confusable"),
    ("Na2SO4 10H2O", {"Na": 2, "S": 1, "O": 14, "H": 20}, 0, "confusable"),
    ("CuSO4·5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0, "valid"),
    ("H₂O", {"H": 2, "O": 1}, 0, "valid"),
    ("NH4+", {"N": 1, "H": 4}, 1, "valid"),
    ("[Fe(CN)6]4-", {"Fe": 1, "C": 6, "N": 6}, -4, "valid"),
]


def fuzz_frontdoor(rng, n, out: Findings):
    best: "dict[str, dict]" = {}
    tally = Counter()

    def consider(text, intended, ich, kind, auto):
        out.cases += 1
        viol, detail = frontdoor_property(text, intended, ich, kind, auto)
        if viol is None:
            return
        tally[viol] += 1
        cur = best.get(viol)
        if cur is None or len(text) < len(cur["text"]):
            best[viol] = {"text": text, "detail": detail, "auto": auto, "kind": kind, "intended": intended, "ich": ich}

    for text, intended, ich, kind in _SEED_CORPUS:
        consider(text, intended, ich, kind, False)
    for _ in range(n):
        text, intended, ich, kind = gen_formula(rng)
        auto = rng.random() < 0.35 and kind != "malformed"
        consider(text, intended, ich, kind, auto)
    for viol, b in best.items():
        text, auto = b["text"], b["auto"]
        # shrink only on predicates that do not depend on the intended composition of the WHOLE string
        if viol in ("P-crash", "P-slow", "P-roundtrip", "P-normalize-idempotent", "P-nonpositive"):
            text = _shrink_text(text, lambda s, v=viol, a=auto: frontdoor_property(s, None, None, "malformed", a)[0] == v)
        elif viol.startswith("P-silent-misparse[R1"):
            def r1(sx, a=auto):
                from smartchem.identity_parse import IdentityParseError, InputKind, resolve_identity
                if not _R1_STRICT.search(sx):     # the HARMFUL merge only: digit, whitespace, digit ('H2 2O' -> H22O)
                    return False
                try:
                    r = resolve_identity(sx, InputKind.AUTO if a else InputKind.FORMULA)
                    r2 = resolve_identity("".join(sx.split()), InputKind.AUTO if a else InputKind.FORMULA)
                except IdentityParseError:
                    return False
                return _formula_counts(r.formula) == _formula_counts(r2.formula)
            text = _shrink_text(text, r1)
        out.add(viol, viol.split("[")[0],
                {"text": text, "text_codepoints": [f"U+{ord(c):04X}" for c in text[:40]], "kind": b["kind"],
                 "surface": "AUTO" if auto else "FORMULA",
                 "intended": b["intended"] if text == b["text"] else "(belongs to shrunk_from, not to this minimal text)",
                 "intended_charge": b["ich"] if text == b["text"] else None,
                 "shrunk_from": b["text"] if text != b["text"] else None}, b["detail"], count=tally[viol],
                # barrier A1 (F-3 adjudication): a multi-element body's single trailing digit before a bare sign is a
                # COUNT by DECLARED convention (NH4+, NO3-, H3O+, VO2+; test P0-B + tests/test_v0_9_5_front_door.py),
                # so R2 is a known, documented boundary -- not a new silent mis-parse.
                known="A1-F3-convention" if viol.startswith("P-silent-misparse[R2") else None)


def _shape(s: str) -> str:
    return "".join("d" if c.isdigit() else "a" if c.isalpha() else c for c in s)[:24]


# ====================================================================================================================
# F2 -- identity ------------------------------------------------------------------------------------------------------
# ====================================================================================================================
_ISOMER_GROUPS = [
    ("CCO", "COC"), ("CCCO", "CC(C)O", "CCOC"), ("Cc1ccccc1C", "Cc1cccc(C)c1", "Cc1ccc(C)cc1"),
    ("CC(C)=O", "CCC=O", "C=CCO"), ("CCCC", "CC(C)C"), ("CC(=O)OC", "CCOC=O", "OCCC=O"),
    ("C=CCC", "CC=CC", "C1CCC1"), ("Oc1ccccc1O", "Oc1cccc(O)c1", "Oc1ccc(O)cc1"),
    ("OC(=O)c1ccccc1O", "OC(=O)c1cccc(O)c1", "OC(=O)c1ccc(O)cc1"), ("CC(=O)O", "COC=O", "OCC=O"),
    ("Nc1ccccc1O", "Nc1cccc(O)c1", "Nc1ccc(O)cc1"), ("CCN", "CNC"), ("CCC(=O)O", "CC(=O)OC", "OCCC=O"),
]
_BENZENOIDS = ["Cc1ccccc1C", "Oc1ccccc1O", "OC(=O)c1ccccc1O", "COC(=O)c1ccccc1O", "CC(=O)Oc1ccccc1C(=O)O", "Cc1ccccc1O",
               "OC(=O)c1ccccc1C(=O)O", "Nc1ccccc1O", "c1ccccc1"]
_STEREO_ISO = ["C[C@H](O)CC", "C[C@@H](O)CC", "[2H]O[2H]", "[13CH4]", "OC(=O)[C@@H](N)C", "F/C=C/F", "F/C=C\\F", "[2H]C([2H])([2H])O",
               "CC[C@H](C)O", "CCO", "O", "C[13CH2]O"]


def _permute(mol, rng):
    from smartchem.category import Bond, Molecule

    n = len(mol.atoms)
    perm = list(range(n))
    rng.shuffle(perm)
    atoms = [None] * n
    for old, new in enumerate(perm):
        atoms[new] = mol.atoms[old]
    bonds = frozenset(Bond(*sorted((perm[b.i], perm[b.j])), b.order) for b in mol.bonds)
    return Molecule(tuple(atoms), bonds, mol.charge, mol.state)


def _kekule_flip(mol):
    from smartchem.category import Bond, Molecule

    carbons = [i for i, s in enumerate(mol.atoms) if s == "C"]
    adj = {i: set() for i in carbons}
    for b in mol.bonds:
        if b.i in adj and b.j in adj:
            adj[b.i].add(b.j)
            adj[b.j].add(b.i)
    ring = {c for c in carbons if len(adj[c]) >= 2}
    nb = []
    for b in mol.bonds:
        if b.i in ring and b.j in ring and mol.atoms[b.i] == "C" == mol.atoms[b.j] and b.order in (1, 2):
            nb.append(Bond(b.i, b.j, 1 if b.order == 2 else 2))
        else:
            nb.append(b)
    return Molecule(mol.atoms, frozenset(nb), mol.charge, mol.state)


def _pure_bottle(mol, qty="500", unit="mL"):
    from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
    from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MaterialComponent, Phase, StockMaterial, StockQuantity
    from smartchem.material_spec import ConcentrationBasis, EvidenceKind

    ev = IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
        inputs=(TypedInput("low", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="fuzz fixture: the bench declares its own bottle pure")
    return StockMaterial(STOCK_MATERIAL_SCHEMA, f"b{abs(hash(str(mol) + qty + unit)) % 10**8}", "fuzz bottle",
                         (MaterialComponent.evidenced(mol, "active", ev),), Phase.LIQUID, "fuzz fixture",
                         quantity=StockQuantity.of(qty, unit), phase_evidence=EvidenceKind.USER_DECLARED)


def fuzz_identity(rng, n, out: Findings):
    from smartchem.service import build_recompile_request, response_to_payload, run_compilation
    from smartchem.smiles import parse_smiles, parse_smiles_features, resonance_identity

    # (a) constitutional isomers must stay distinct (resonance key AND the literal canonical form)
    for group in _ISOMER_GROUPS:
        mols = [parse_smiles(s) for s in group]
        out.cases += 1
        keys = [resonance_identity(m) for m in mols]
        if len(set(keys)) != len(keys):
            i, j = next((i, j) for i in range(len(keys)) for j in range(i + 1, len(keys)) if keys[i] == keys[j])
            out.add(f"merge:{group[i]}~{group[j]}", "P-isomers-distinct", {"smiles": [group[i], group[j]]},
                    "two constitutional isomers share a resonance key")
        for i in range(len(mols)):                       # stock layer: an isomer bottle must never satisfy another isomer
            for j in range(len(mols)):
                if i != j:
                    out.cases += 1
                    if _pure_bottle(mols[i]).active_fraction_interval(mols[j]) is not None:
                        out.add(f"stock-merge:{group[i]}~{group[j]}", "P-isomers-distinct-stock",
                                {"bottle": group[i], "requirement": group[j]},
                                "a bottle of one constitutional isomer satisfies another isomer's requirement")
    # (b) respelling invariance: random atom permutations (and Kekule flips) of ONE structure keep the resonance key
    for smi in _BENZENOIDS + [s for g in _ISOMER_GROUPS for s in g]:
        m = parse_smiles(smi)
        base = resonance_identity(m)
        for _ in range(3):
            out.cases += 1
            pm = _permute(m, rng)
            if resonance_identity(pm) != base:
                out.add(f"perm:{smi}", "P-respelling-invariant", {"smiles": smi, "op": "atom-permutation"},
                        "an atom permutation of one structure changed its resonance key")
    for smi in _BENZENOIDS:
        m = parse_smiles(smi)
        flipped = _kekule_flip(m)
        out.cases += 1
        if flipped == m:
            continue                                     # no aromatic ring to flip
        if resonance_identity(flipped) != resonance_identity(m):
            out.add(f"kekule-key:{smi}", "P-kekule-resonance-key", {"smiles": smi, "op": "graph-surgery Kekule flip"},
                    "the resonance key splits two Kekule forms of one structure")
        for bottle, req, direction in ((m, flipped, "bottle=parsed,req=flipped"), (flipped, m, "bottle=flipped,req=parsed")):
            out.cases += 1
            if _pure_bottle(bottle).active_fraction_interval(req) is None:
                # today's stock key is the literal canonical() digest: the documented, adjudicated C7-2 gap (barrier S7)
                out.add(f"kekule-stock:{smi}:{direction}", "P-kekule-stock-match",
                        {"smiles": smi, "direction": direction}, "stock layer does not match a Kekule respelling",
                        known="S7")
    # (c) stereo / isotope features must be DISCLOSED as identity losses on the request
    picks = list(_STEREO_ISO)
    rng.shuffle(picks)
    for smi in picks[:max(6, n // 12)]:
        out.cases += 1
        try:
            m, f = parse_smiles_features(smi)
        except Exception:  # noqa: BLE001 -- a smiles the parser refuses is not a disclosure question
            continue
        stereo, iso = bool(f.tetrahedral_stereo or f.double_bond_stereo), bool(f.isotopes)
        if not (stereo or iso):
            continue
        try:
            resp = run_compilation(build_recompile_request(smi, input_kind=__import__("smartchem.identity_parse", fromlist=["x"]).InputKind.SMILES, max_depth=1))
        except Exception as exc:  # noqa: BLE001
            out.add(f"crash:{smi}", "P-loss-disclosed", {"smiles": smi}, f"recompile crashed: {type(exc).__name__}: {str(exc)[:100]}")
            continue
        ir = response_to_payload(resp).get("compilation_ir")
        feats = {x["feature"] for x in ((ir or {}).get("identity_losses") or [])}
        if resp.outcome.value == "REFUSED":
            continue
        if stereo and "stereochemistry" not in feats and "double-bond-stereochemistry" not in feats and not any("stereo" in x for x in feats):
            out.add(f"undisclosed-stereo:{smi}", "P-loss-disclosed", {"smiles": smi, "features_seen": sorted(feats)},
                    "stereochemistry declared but no stereo identity loss on the request")
        if iso and not any("isotope" in x for x in feats):
            out.add(f"undisclosed-isotope:{smi}", "P-loss-disclosed", {"smiles": smi, "features_seen": sorted(feats)},
                    "an isotope label was declared but no isotope identity loss is on the request")


# ====================================================================================================================
# F3 -- allocation ---------------------------------------------------------------------------------------------------
# ====================================================================================================================
def _ref_maxflow(demands, bottles, unit):
    """INDEPENDENT reference: can every demand in `unit` be served? demands = [(species_key, Fraction)], bottles =
    [(set(species_keys), Fraction)] with the bottle's capacity used ONCE across every species it carries.  Bipartite
    flow by simple augmenting-path search over Fractions (tiny graphs)."""
    nd, nb = len(demands), len(bottles)
    cap = {}
    S, T = "S", "T"
    for i, (_k, q) in enumerate(demands):
        cap[(S, ("d", i))] = q
    for j, (_sp, q) in enumerate(bottles):
        cap[(("b", j), T)] = q
    for i, (k, q) in enumerate(demands):
        for j, (sp, _c) in enumerate(bottles):
            if k in sp:
                cap[(("d", i), ("b", j))] = q
    flow = {e: Fraction(0) for e in cap}
    nodes = {S, T} | {("d", i) for i in range(nd)} | {("b", j) for j in range(nb)}
    adj = {u: [] for u in nodes}
    for (u, v) in cap:
        adj[u].append(v)
        adj[v].append(u)
    total = Fraction(0)
    while True:
        parent, queue = {S: None}, [S]
        while queue and T not in parent:
            u = queue.pop(0)
            for v in adj[u]:
                if v in parent:
                    continue
                if (u, v) in cap and cap[(u, v)] - flow[(u, v)] > 0 or (v, u) in cap and flow[(v, u)] > 0:
                    parent[v] = u
                    queue.append(v)
        if T not in parent:
            break
        path, v = [], T
        while parent[v] is not None:
            path.append((parent[v], v))
            v = parent[v]
        push = None
        for (u, v) in path:
            r = cap[(u, v)] - flow[(u, v)] if (u, v) in cap else flow[(v, u)]
            push = r if push is None else min(push, r)
        for (u, v) in path:
            if (u, v) in cap:
                flow[(u, v)] += push
            else:
                flow[(v, u)] -= push
        total += push
    return total


_SPECIES = ["CO", "CC(=O)O", "O", "CCO", "CC(C)=O"]
_UNITS = ["mL", "mL", "mL", "L", "g", "mol"]


def _qty_edge(rng, base: Fraction) -> str:
    """A decimal string near `base`: exact, one ulp above/below, or a random scale (knife edges)."""
    choice = rng.choice(["eq", "eq", "plus", "minus", "half", "double", "rand"])
    v = {"eq": base, "plus": base + Fraction(1, 10 ** rng.choice([1, 3, 9, 15])), "minus": base - Fraction(1, 10 ** rng.choice([1, 3, 9])),
         "half": base / 2, "double": base * 2, "rand": Fraction(rng.randint(1, 500), rng.choice([1, 2, 10, 100]))}[choice]
    if v <= 0:
        v = Fraction(1, 1000)
    from smartchem.capability.quantity import fraction_to_decimal

    return fraction_to_decimal(v)


def fuzz_allocation(rng, n, out: Findings):
    from smartchem.capability.assess import assess
    from smartchem.capability.enums import CapabilityStatus
    from smartchem.capability.presets import custom
    from smartchem.capability.quantity import QuantityDemand
    from smartchem.capability.requirements import MaterialRequirement, compile_capability_requirements
    from smartchem.conditions import ConditionEnvelope
    from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
    from smartchem.experiment.readiness import evaluate_route
    from smartchem.experiment.step import ROUTE_SCHEMA, STEP_SCHEMA, ExperimentRoute, ExperimentStep
    from smartchem.experiment.stock import STOCK_MATERIAL_SCHEMA, MaterialComponent, Phase, StockMaterial, StockQuantity
    from smartchem.material_spec import ConcentrationBasis, EvidenceKind
    from smartchem.smiles import parse_smiles

    mols = {s: parse_smiles(s) for s in _SPECIES}
    ms, meoh, water = parse_smiles("COC(=O)c1ccccc1O"), parse_smiles("CO"), parse_smiles("O")
    sa = parse_smiles("OC(=O)c1ccccc1O")
    step = ExperimentStep(STEP_SCHEMA, ms, (sa, meoh), (ms, water), (), ConditionEnvelope())
    route = ExperimentRoute(ROUTE_SCHEMA, (step,))
    base_reqs = compile_capability_requirements(route)
    readiness = evaluate_route(route)
    fit_seen = 0

    def ev(lo="1", hi="1"):
        return IntervalEvidence.build(
            kernel=DerivationKernel.USER_DECLARED_V1, basis=ConcentrationBasis.MASS_FRACTION,
            inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                    TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
            domain_of_validity="fuzz fixture")

    def build(case):
        reqs = []
        for k, q_by_unit, unstated in case["reqs"]:
            known = tuple((u, v) for u, v in q_by_unit)
            reqs.append(MaterialRequirement(
                identity=mols[k], phase=None,
                quantity=QuantityDemand(known, unstated) if (known or unstated) else QuantityDemand.unstated(1),
                role="reactant (leaf input)", evidence_source="fuzz fixture"))
        inv = []
        for bi, (species, qty, unit, bid) in enumerate(case["bottles"]):
            comps = tuple(MaterialComponent.evidenced(mols[s], "active", ev("0.5", "0.5") if len(species) > 1 else ev())
                          for s in species)
            inv.append(StockMaterial(STOCK_MATERIAL_SCHEMA, bid, f"fuzz bottle {bid}", comps, Phase.LIQUID, "fuzz",
                                     quantity=None if qty is None else StockQuantity.of(qty, unit),
                                     phase_evidence=EvidenceKind.USER_DECLARED))
        return dc.replace(base_reqs, material=tuple(reqs), material_unresolved=()), tuple(inv)

    def reference_infeasible(case) -> "str | None":
        """A reason the demand can NOT be soundly covered (so FIT is forbidden), else None."""
        for k, q_by_unit, unstated in case["reqs"]:
            if unstated:
                return "an unquantified use (demand real, size unknown)"
        units = sorted({u for _k, qu, _s in case["reqs"] for u, _v in qu})
        for u in units:
            demands = [(k, Fraction(v)) for k, qu, _s in case["reqs"] for (uu, v) in qu if uu == u]
            seen_ids, bottles = set(), []
            for sp, q, un, bid in case["bottles"]:          # a package declared twice under ONE id is ONE physical package
                if q is not None and un == u and bid not in seen_ids:
                    seen_ids.add(bid)
                    bottles.append((set(sp), Fraction(q)))
            need = sum(q for _k, q in demands)
            if _ref_maxflow(demands, bottles, u) < need:
                return f"unit {u}: reference max-flow < total demand {need}"
        return None

    def gen_case():
        species_pool = rng.sample(_SPECIES, k=rng.randint(1, 3))
        n_req = rng.randint(1, 3)
        reqs = []
        for _ in range(n_req):
            k = rng.choice(species_pool)
            units = rng.sample(_UNITS, k=rng.choice([1, 1, 1, 2]))
            qu = [(u, _qty_edge(rng, Fraction(rng.randint(1, 200), rng.choice([1, 4])))) for u in units]
            unstated = 1 if rng.random() < 0.12 else 0
            if rng.random() < 0.08:
                qu, unstated = [], 1
            reqs.append((k, qu, unstated))
        bottles = []
        for bi in range(rng.randint(1, 3)):
            sp = rng.sample(species_pool, k=rng.choice([1, 1, min(2, len(species_pool))]))
            u = rng.choice(_UNITS)
            q = None if rng.random() < 0.1 else _qty_edge(rng, Fraction(rng.randint(1, 300), rng.choice([1, 4])))
            bottles.append((sp, q, u, f"fz{bi}"))
        if rng.random() < 0.15:                                   # duplicate-package declaration (same id twice)
            bottles.append(bottles[0])
        return {"reqs": reqs, "bottles": bottles}

    def gen_knife():
        """Feasible-by-construction supply, then perturbed at the knife edge (exact / one ulp over / one ulp under),
        with optional split packages, a wrong-unit twin and a duplicate declaration -- so FIT is actually reachable."""
        from smartchem.capability.quantity import fraction_to_decimal

        species_pool = rng.sample(_SPECIES, k=rng.randint(1, 2))
        unit = rng.choice(["mL", "g", "L"])
        reqs, need = [], {k: Fraction(0) for k in species_pool}
        for _ in range(rng.randint(1, 3)):
            k = rng.choice(species_pool)
            q = Fraction(rng.randint(1, 120), rng.choice([1, 2, 5]))
            need[k] += q
            reqs.append((k, [(unit, fraction_to_decimal(q))], 0))
        bottles, bi = [], 0
        for k in species_pool:
            total = need[k]
            if total == 0:
                continue
            edge = rng.choice(["eq", "eq", "over", "under"])
            tiny = Fraction(1, 10 ** rng.choice([1, 4, 9, 15]))
            supply = total if edge == "eq" else total + tiny if edge == "over" else max(tiny, total - tiny)
            parts = rng.choice([1, 1, 2, 4])           # split the supply across several packages
            share = supply / parts
            for _ in range(parts):
                bottles.append(([k], fraction_to_decimal(share), unit, f"fz{bi}"))
                bi += 1
        if rng.random() < 0.2:
            bottles.append((["CO"], "50", "mL" if unit != "mL" else "g", f"fz{bi}"))   # a wrong-unit twin
        if bottles and rng.random() < 0.2:
            bottles.append(bottles[0])                                       # duplicate declaration (same id)
        return {"reqs": reqs, "bottles": bottles}

    def violated(case) -> "tuple[str, str] | None":
        try:
            reqs, inv = build(case)
            profile = custom(profile_id="fuzz-alloc", material_inventory=inv)
            a = assess(profile, reqs, readiness)
        except (ValueError, TypeError):
            return None                                       # a typed refusal of the case itself is fine
        status = a.material.status
        why = reference_infeasible(case)
        # duplicate packages: a bottle declared twice under ONE id is one physical package -- supply counted once
        return (("P-fit-exceeds-supply", f"material FIT although {why}") if status is CapabilityStatus.FIT and why else None)

    # positive controls first: the harness must be able to observe FIT at all, or the property is vacuous
    controls = [
        {"reqs": [("CO", [("mL", "10")], 0)], "bottles": [(["CO"], "500", "mL", "c0")]},
        {"reqs": [("CO", [("mL", "100")], 0)], "bottles": [(["CO"], "100", "mL", "c0")]},
        {"reqs": [("CO", [("mL", "60")], 0), ("CO", [("mL", "40")], 0)], "bottles": [(["CO"], "100", "mL", "c0")]},
    ]
    ctrl_fit = 0
    for c in controls:
        reqs, inv = build(c)
        st = assess(custom(profile_id="fuzz-ctrl", material_inventory=inv), reqs, readiness).material.status
        ctrl_fit += st is CapabilityStatus.FIT
    out.notes.append(f"positive controls reaching material FIT: {ctrl_fit}/{len(controls)}")
    if ctrl_fit == 0:
        out.notes.append("VACUOUS: no control reached material FIT, so the never-FIT-over-supply property cannot fail here")
    for _ in range(n):
        case = gen_knife() if rng.random() < 0.6 else gen_case()
        out.cases += 1
        try:
            reqs, inv = build(case)
            a = assess(custom(profile_id="fuzz-alloc", material_inventory=inv), reqs, readiness)
        except (ValueError, TypeError):
            continue
        except Exception as exc:  # noqa: BLE001
            out.add(f"crash:{type(exc).__name__}", "P-no-crash", {"case": case}, f"{type(exc).__name__}: {str(exc)[:120]}")
            continue
        fit_seen += a.material.status is CapabilityStatus.FIT
        v = violated(case)
        if v is None:
            continue
        # shrink: drop requirements / bottles while the violation persists
        def shrunk_fails(c):
            return bool(c["reqs"]) and bool(c["bottles"]) and violated(c) is not None
        reqs_min = ddmin(case["reqs"], lambda rs: shrunk_fails({"reqs": rs, "bottles": case["bottles"]}))
        bots_min = ddmin(case["bottles"], lambda bs: shrunk_fails({"reqs": reqs_min, "bottles": bs}))
        minimal = {"reqs": reqs_min, "bottles": bots_min}
        out.add(f"{v[0]}:{len(reqs_min)}r{len(bots_min)}b", v[0], {"case": minimal}, v[1])
    out.notes.append(f"random cases with material FIT observed: {fit_seen}/{out.cases - 0} (a FIT that survived the reference is fine)")


# ====================================================================================================================
# F4/F5 -- wire + receipts ----------------------------------------------------------------------------------------
# ====================================================================================================================
_BASE_CACHE: "dict[str, object]" = {}


def _bases():
    """Two honest canonical THICK payloads + the response objects they came from (cheap methyl acetate cases)."""
    if _BASE_CACHE:
        return _BASE_CACHE
    from smartchem.service import (build_recompile_request, response_semantic_fields, response_to_payload,
                                   run_compilation)

    a = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"))
    b = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="research-lab"))
    for tag, resp in (("A", a), ("B", b)):
        thick = response_to_payload(resp)
        _BASE_CACHE[tag] = {"resp": resp, "thick": thick, "thin": response_to_payload(resp, include_replay=False),
                            "sem": sha(response_semantic_fields(resp)), "digest": resp.result_digest}
    return _BASE_CACHE


def _walk(node, path=()):
    """Every (path, value) in a JSON tree, containers included."""
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, path + (i,))


def _get(root, path):
    for k in path:
        root = root[k]
    return root


def _apply(payload, edit):
    """Apply ONE atomic edit dict to a deep copy; returns the new payload (edits are JSON so repros are small)."""
    p = copy.deepcopy(payload)
    op, path = edit["op"], tuple(edit.get("path", ()))
    if op == "delete":
        parent = _get(p, path[:-1])
        del parent[path[-1]]
    elif op == "insert":
        _get(p, path)[edit["key"]] = edit["value"]
    elif op == "set":
        if not path:
            return edit["value"]
        _get(p, path[:-1])[path[-1]] = edit["value"]
    elif op == "flip_hex":
        parent = _get(p, path[:-1])
        s = parent[path[-1]]
        i = edit["index"] % len(s)
        parent[path[-1]] = s[:i] + ("0" if s[i] != "0" else "1") + s[i + 1:]
    elif op == "downgrade_thin":
        p["transport_mode"] = "THIN_ADVISORY"
        for d in p.get("ranked_route_dossiers", []):
            d.pop("replay_payload", None)
    elif op == "swap_subtree":
        _get(p, path[:-1])[path[-1]] = copy.deepcopy(edit["value"])
    else:
        raise ValueError(op)
    return p


def _refix_digest(payload):
    """A keyless attacker recomputes the PUBLIC digests after tampering: result_digest := transport-bound(base, mode, body)."""
    from smartchem.service import _payload_body_digest, _transport_bound_result_digest

    p = copy.deepcopy(payload)
    if not isinstance(p, dict) or "result_digest" not in p:
        return p
    base = _bases()["A"]["digest"]
    try:
        p["result_digest"] = _transport_bound_result_digest(base, p.get("transport_mode", "CANONICAL_VERIFIED"),
                                                            _payload_body_digest(p))
    except Exception:  # noqa: BLE001 -- an unknown mode etc.: leave the stale digest, the loader must refuse anyway
        pass
    return p


def _classify_load(payload, base):
    """-> ('refused', exc class) | ('accepted-same', ..) | ('accepted-DIFFERENT', detail) | ('crash', ...)."""
    from smartchem.service import response_from_payload, response_semantic_fields

    try:
        r = response_from_payload(copy.deepcopy(payload))
    except (ValueError, TypeError) as exc:
        return "refused", f"{type(exc).__name__}: {str(exc)[:70]}"
    except Exception as exc:  # noqa: BLE001 -- an UNTYPED escape from the loader is a robustness finding
        return "crash", f"{type(exc).__name__}: {str(exc)[:100]}"
    same = sha(response_semantic_fields(r)) == base["sem"] and r.result_digest == base["digest"]
    if not same:
        return "accepted-DIFFERENT", f"semantic fields / result digest differ (outcome {r.outcome.value})"
    if payload != base["thick"] and payload != base["thin"]:
        return "accepted-same-but-malleable", "an altered payload loads to the identical response"
    return "accepted-same", ""


def _wire_edits(rng, payload):
    """One random atomic edit (JSON dict) over the payload tree."""
    nodes = list(_walk(payload))
    kind = rng.choice(["delete", "insert", "type", "schema", "flip_hex", "enum", "int", "downgrade", "legacy", "subtree"])
    dicts = [(p, v) for p, v in nodes if isinstance(v, dict)]
    leaves = [(p, v) for p, v in nodes if p and not isinstance(v, (dict, list))]
    if kind == "delete":
        cand = [(p, v) for p, v in nodes if p]
        p, _ = rng.choice(cand)
        return {"op": "delete", "path": list(p)}
    if kind == "insert":
        p, _ = rng.choice(dicts)
        return {"op": "insert", "path": list(p), "key": rng.choice(["zzz", "schema_version", "digest", "extra"]), "value": rng.choice([1, "x", None, {}])}
    if kind == "type" and leaves:
        p, v = rng.choice(leaves)
        alt = {str: rng.choice([1, None, [], True]), int: rng.choice(["1", None, 1.5, True]),
               float: rng.choice(["1.0", None]), bool: rng.choice([1, "true", None]), type(None): rng.choice([0, "", []])}[type(v)]
        return {"op": "set", "path": list(p), "value": alt}
    if kind == "schema":
        sv = [(p, v) for p, v in leaves if isinstance(v, str) and p[-1] == "schema_version"]
        if sv:
            p, v = rng.choice(sv)
            other = rng.choice([s for _p, s in sv if s != v] + ["smartchem.service/compilation-response-v1alpha16",
                                                                "smartchem.service/ranked-route-summary-v1alpha4", ""])
            return {"op": "set", "path": list(p), "value": other}
    if kind == "flip_hex":
        hx = [(p, v) for p, v in leaves if isinstance(v, str) and len(v) == 64 and set(v) <= set("0123456789abcdef")]
        if hx:
            p, _ = rng.choice(hx)
            return {"op": "flip_hex", "path": list(p), "index": rng.randrange(64)}
    if kind == "enum":
        en = [(p, v) for p, v in leaves if isinstance(v, str) and v.isupper() and "_" in v or v in ("FITS", "UNKNOWN", "EXCLUDED")]
        if en:
            p, v = rng.choice(en)
            return {"op": "set", "path": list(p), "value": rng.choice(["FITS", "UNKNOWN", "EXCLUDED", "CANONICAL_VERIFIED", "THIN_ADVISORY", "COMPLETE_WITHIN_BOUNDS", "NOPE"])}
    if kind == "int":
        ints = [(p, v) for p, v in leaves if isinstance(v, int) and not isinstance(v, bool)]
        if ints:
            p, v = rng.choice(ints)
            return {"op": "set", "path": list(p), "value": rng.choice([v + 1, v - 1, 0, -1, 10**9])}
    if kind == "downgrade":
        return {"op": "downgrade_thin"}
    if kind == "legacy":
        return {"op": "set", "path": ["schema_version"], "value": rng.choice([
            "smartchem.service/compilation-response-v1alpha15", "smartchem.service/compilation-response-v1alpha14"])}
    if kind == "subtree":
        other = _bases()["B"]["thick"]
        keys = [k for k in payload if k not in ("result_digest",) and k in other]
        k = rng.choice(keys)
        return {"op": "swap_subtree", "path": [k], "value": other[k]}
    p, _ = rng.choice([(p, v) for p, v in nodes if p])
    return {"op": "delete", "path": list(p)}


def _fuzz_payload_family(rng, n, out: Findings, mutate_scope, prop):
    from smartchem.service import response_semantic_fields  # noqa: F401

    bases = _bases()
    base = bases["A"]
    tally, refusal_heads = Counter(), Counter()
    for i in range(n):
        edits = [mutate_scope(rng, base["thick"]) for _ in range(rng.choice([1, 1, 1, 2]))]
        recompute = rng.random() < 0.6
        out.cases += 1

        def build(es, rc=recompute):
            p = base["thick"]
            try:
                for e in es:
                    p = _apply(p, e)
            except (KeyError, IndexError, TypeError, ValueError):
                return None
            return _refix_digest(p) if rc else p

        p = build(edits)
        if p is None:
            continue
        verdict, detail = _classify_load(p, base)
        tally[verdict] += 1
        if verdict == "refused":
            refusal_heads[re.sub(r"[0-9a-f]{16,}", "<hex>", detail)[:80]] += 1
        if verdict in ("refused", "accepted-same"):
            continue

        def fails(es, v=verdict):
            q = build(es)
            return q is not None and _classify_load(q, base)[0] == v

        minimal = ddmin(edits, fails)
        sig = f"{verdict}:{minimal[0]['op']}:{'/'.join('*' if isinstance(x, int) else str(x) for x in minimal[0].get('path', []))[:60]}"
        known = None
        if verdict == "accepted-DIFFERENT" and prop == "P-receipt-refused" and _is_consistent_ir_rewrite(minimal):
            known = "S11"
        if verdict == "accepted-same-but-malleable" and any(e["op"] == "downgrade_thin" for e in minimal):
            known = "THIN-ADVISORY"     # the thin wire is advisory by contract (D-T1); canonical() refuses it at S1
        out.add(sig, prop if verdict != "crash" else "P-no-untyped-crash",
                {"base": "methyl_acetate@poor-man canonical thick payload", "edits": minimal,
                 "recompute_public_digest": recompute, "observed": verdict, "detail": detail}, detail, known=known)
    out.notes.append(f"verdicts over {sum(tally.values())} valid mutations: {dict(tally)}")
    out.notes.append("refusal guards that fired (top 6): " + "; ".join(f"{k} x{v}" for k, v in refusal_heads.most_common(6)))


def _is_consistent_ir_rewrite(edits) -> bool:
    return len(edits) > 1 and all("search" in canon(e.get("path", [])) or "status" in canon(e.get("path", [])) for e in edits)


_RECEIPT_FIELDS = ["max_depth", "cut_budget", "result_limit", "nodes_visited", "transforms_considered",
                   "candidates_emitted", "results_returned", "status", "standard_status", "search_kind",
                   "cut_budget_scope", "candidates_rejected_by_reason"]


def _receipt_edit(rng, payload):
    ir = payload["compilation_ir"]
    sr = ir["search_receipt"]
    base_path = ["compilation_ir", "search_receipt"]
    r = rng.random()
    if r < 0.55:
        k = rng.choice([f for f in _RECEIPT_FIELDS if f in sr])
        v = sr[k]
        if isinstance(v, int) and not isinstance(v, bool):
            val = rng.choice([v + 1, max(0, v - 1), 0, v * 1000, -1])
        elif isinstance(v, str):
            val = rng.choice(["COMPLETE_WITHIN_BOUNDS", "PARTIAL_DEPTH_LIMIT", "PARTIAL_CUT_BUDGET", "PARTIAL_RESULT_LIMIT",
                              "COMPLETE_WITHIN_DECLARED_SPACE", "INCOMPLETE_DEPTH_LIMIT", "INCOMPLETE_CUT_BUDGET", "GLOBAL", "DAG"])
        else:
            val = rng.choice([[], None, [["x", 1]]])
        return {"op": "set", "path": base_path + [k], "value": val}
    if r < 0.75:                                            # IR-level status fields
        k = rng.choice(["search_status", "standard_status"])
        return {"op": "set", "path": ["compilation_ir", k],
                "value": rng.choice(["COMPLETE_WITHIN_BOUNDS", "PARTIAL_DEPTH_LIMIT", "INCOMPLETE_DEPTH_LIMIT",
                                     "COMPLETE_WITHIN_DECLARED_SPACE", "PARTIAL_CUT_BUDGET"])}
    if r < 0.9:                                             # top-level completeness/outcome fields
        k = rng.choice(["search_space_status", "outcome", "exit_code", "standard_status"])
        val = {"search_space_status": rng.choice(["PARTIAL_CANDIDATE_SET", "NO_ROUTE_IN_DECLARED_SPACE", "COMPLETE_CANDIDATE_SET"]),
               "outcome": rng.choice(["INCOMPLETE", "ROUTES_FOUND", "NO_ROUTE_COMPLETE"]), "exit_code": rng.choice([0, 3, 4]),
               "standard_status": rng.choice(["COMPLETE_WITHIN_DECLARED_SPACE", "INCOMPLETE_DEPTH_LIMIT"])}[k]
        return {"op": "set", "path": [k], "value": val}
    return {"op": "delete", "path": base_path + [rng.choice([f for f in _RECEIPT_FIELDS if f in sr])]}


def fuzz_wire(rng, n, out: Findings):
    _fuzz_payload_family(rng, n, out, _wire_edits, "P-wire-refused-or-identical")


def fuzz_receipts(rng, n, out: Findings):
    # single-field mutations AND a consistent multi-field rewrite of the advisory IR status (the S11 boundary)
    def scope(r, payload):
        return _receipt_edit(r, payload)

    _fuzz_payload_family(rng, n, out, scope, "P-receipt-refused")
    # the deliberate consistent rewrite (status + standard + receipt + top-level), digests recomputed
    base = _bases()["A"]
    edits = [
        {"op": "set", "path": ["compilation_ir", "search_status"], "value": "PARTIAL_DEPTH_LIMIT"},
        {"op": "set", "path": ["compilation_ir", "standard_status"], "value": "INCOMPLETE_DEPTH_LIMIT"},
        {"op": "set", "path": ["compilation_ir", "search_receipt", "status"], "value": "PARTIAL_DEPTH_LIMIT"},
        {"op": "set", "path": ["compilation_ir", "search_receipt", "standard_status"], "value": "INCOMPLETE_DEPTH_LIMIT"},
        {"op": "set", "path": ["standard_status"], "value": "INCOMPLETE_DEPTH_LIMIT"},
    ]
    p = base["thick"]
    for e in edits:
        p = _apply(p, e)
    out.cases += 1
    verdict, detail = _classify_load(_refix_digest(p), base)
    if verdict not in ("refused",):
        out.add(f"consistent-ir-rewrite:{verdict}", "P-receipt-refused",
                {"base": "methyl_acetate@poor-man canonical thick payload", "edits": edits, "recompute_public_digest": True,
                 "observed": verdict, "detail": detail},
                "a CONSISTENT multi-field rewrite of the advisory IR search status loads", known="S11")


FAMILIES = {"frontdoor": fuzz_frontdoor, "identity": fuzz_identity, "allocation": fuzz_allocation, "wire": fuzz_wire,
            "receipts": fuzz_receipts}


def _self_test(seed, budget):
    """The fuzzer must be able to FAIL: run the allocation family against a deliberately broken flow (every requirement
    'flows' in full regardless of supply) and demand that it reports never-FIT-over-supply violations."""
    import smartchem.capability.assess  # noqa: F401 -- ensure the module is loaded (the package attribute is the FUNCTION)

    assess_mod = sys.modules["smartchem.capability.assess"]
    real = assess_mod._max_flow
    assess_mod._max_flow = lambda edges, source, sink: sum((c for (u, _v, c) in edges if u == source), Fraction(0))
    try:
        out = Findings("allocation")
        fuzz_allocation(random.Random(f"{seed}:allocation"), max(1, int(DEFAULT_CASES["allocation"] * budget)), out)
    finally:
        assess_mod._max_flow = real
    props = Counter(f["property"] for f in out.items.values())
    print(f"self-test (broken flow): {out.cases} cases, {len(out.items)} finding signature(s): {dict(props)}")
    ok = props.get("P-fit-exceeds-supply", 0) > 0
    print("self-test:", "PASS (the fuzzer catches an over-supply FIT)" if ok else "FAIL (the fuzzer is blind to over-supply)")
    return 0 if ok else 1


def main(argv):
    seed, budget = 950, 1.0
    fams = list(FAMILIES)
    write = "--write-repros" in argv
    out_json = None
    for i, a in enumerate(argv):
        if a == "--seed":
            seed = int(argv[i + 1])
        elif a == "--budget":
            budget = float(argv[i + 1])
        elif a == "--family":
            fams = argv[i + 1].split(",")
        elif a == "--json":
            out_json = argv[i + 1]
    if "--self-test" in argv:
        return _self_test(seed, budget)
    import smartchem
    print(f"smartchem {smartchem.__version__} from {Path(smartchem.__file__).parent}; seed {seed}, budget x{budget}", flush=True)
    results, new_total = {}, 0
    for fam in fams:
        rng = random.Random(f"{seed}:{fam}")
        n = max(1, int(DEFAULT_CASES[fam] * budget))
        out = Findings(fam)
        t0 = time.time()
        try:
            FAMILIES[fam](rng, n, out)
        except Exception as exc:  # noqa: BLE001 -- a harness crash is reported, not swallowed
            out.add(f"harness:{type(exc).__name__}", "P-harness", {}, "".join(traceback.format_exc().splitlines(True)[-4:]))
        results[fam] = out
        print(f"[{fam}] {out.cases} cases, {len(out.items)} NEW finding(s), {sum(out.known.values())} known-boundary hit(s) "
              f"({time.time() - t0:.0f}s)", flush=True)
        for note in out.notes:
            print(f"   note: {note}")
        for k, v in out.known.items():
            print(f"   known  {k}  x{v}")
        for k, f in out.items.items():
            print(f"   FINDING {k}  x{f['count']}: {f['detail'][:160]}")
        new_total += len(out.items)
    if write:
        REPRO_DIR.mkdir(parents=True, exist_ok=True)
        n = 0
        for fam, out in results.items():
            for k, f in out.items.items():
                n += 1
                path = REPRO_DIR / f"{fam}_{n:02d}_{sha(k)[:8]}.json"
                doc = {"family": f["family"], "property": f["property"], "signature": f["signature"], "seed": seed,
                       "count_in_run": f["count"], "detail": f["detail"], "repro": f["repro"]}
                text = json.dumps(doc, indent=1, ensure_ascii=False)
                path.write_text(text[:60000] + "\n")
                print("wrote", path.relative_to(REPO))
    if out_json:
        Path(out_json).write_text(json.dumps({fam: {"cases": o.cases, "new": list(o.items.values()),
                                                    "known": dict(o.known), "notes": o.notes}
                                              for fam, o in results.items()}, indent=1, ensure_ascii=False, default=str))
    print(f"\nTOTAL: {sum(o.cases for o in results.values())} cases, {new_total} NEW finding(s), "
          f"{sum(sum(o.known.values()) for o in results.values())} known-boundary hit(s)")
    return 1 if new_total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
