"""A difficulty-graded ladder that drives the structure decompiler on real chemicals and audits
whether its output is REALITY-RESPECTING -- in the exact, W3-bounded sense the repo means by that.

The question this answers
-------------------------
"Can we recompile any chemical into its constituent fragments and byproducts, and is the output
actually reality-respecting on molecules of increasing difficulty?"  Not "does the reaction happen"
(W3 forbids that claim) -- but the facts the engine DOES assert must hold on every real molecule:

* **Conservation.** Every atom and every unit of charge is conserved across every edge.
* **Valence integrity.** Each fragment is a valence-consistent sub-graph; cutting conserves valence
  atom-by-atom (recomputed by the independent :func:`verify_valence_integrity`, a second path).
* **Structural fidelity.** The fragments are the actual connected pieces of the cut parent, not
  invented graphs (enforced in the edge constructor; re-asserted here via ``disconnects``).
* **The forgetful commuting square.** Every structure edge projects to a VALID formula-level v1 edge
  (:meth:`ScissionEdge.forget`) -- atoms conserved at composition level, >=2 products, strict descent.
* **Honest labelling.** Every open-valence fragment classifies RADICAL, every charged product ION,
  never a reactive fragment dressed as a bottle-able compound (:func:`species_class`).
* **Honest termination.** A graph labelled ``COMPLETE`` must not silently claim to have reached
  single atoms when it actually dead-ended at an irreducible ring core (the honesty audit below).

Why the per-edge conservation is checked at the GRAPH level, not re-proved per edge
-----------------------------------------------------------------------------------
``ScissionEdge.__post_init__`` already re-derives partition/fidelity/valence/atom-conservation from
its stored fields -- so an edge that *exists* is conservation-sound by construction, and re-checking
the same certificate here would be a check derived from its own subject (the repo's recurring
anti-pattern).  So this harness audits what the constructor does NOT: (a) a fully independent
valence recompute on a sample, (b) the forget() projection actually constructing, (c) cross-edge and
graph-level honesty (does COMPLETE really reach atoms?), and (d) hard NON-VACUITY -- that each
molecule that structurally CAN decompose actually produced edges, so a green run can never be green
over an empty subject.

Self-reporting gate
-------------------
Prints a per-tier table and a violations section, then exits non-zero if any HARD invariant failed
(conservation, forget, labelling, non-vacuity, parser formula) so it can be run as a gate.  HONESTY
findings (a COMPLETE graph that stops at a ring core) are surfaced separately -- they drove the
``irreducible_cores`` fix; once the label is honest they are expected and reported, not failures.

    .venv/bin/python experiments/structure_decompiler_ladder.py

W3 unchanged: not one line here predicts that any of these cleavages occurs, at what rate, or which
is favoured.  It certifies that the enumerated fragments conserve, are valence-valid, and are
honestly labelled -- structure, never physics.
"""

from __future__ import annotations

import re
import sys
from collections import Counter

from smartchem.category import Molecule
from smartchem.decompiler import Formula
from smartchem.decompiler_boundary import SpeciesClass, species_class
from smartchem.smiles import SmilesError, parse_smiles
from smartchem.structure_descent import (
    ELECTRON,
    _mol_key,
    ionic_edges,
    scission_edges,
    structure_decompose,
    verify_valence_integrity,
)

# --------------------------------------------------------------------------------------------------
# The ladder: chemicals of increasing difficulty. Each stresses a distinct axis of the machinery.
# mode: "descend" -> homolytic bond-graph descent; "descend2" -> max_cut_bonds=2 (ring-opening);
#       "ionic" -> heterolysis + redox of a neutral; "redox" -> redox of a bare charged species.
# depth: bound the descent (COMPLETE_TO_DEPTH) for drug-sized targets whose full descent is huge.
# --------------------------------------------------------------------------------------------------
Entry = tuple  # (tier, name, smiles_or_none, formula, mode, cut, depth)

LADDER: list[Entry] = [
    # Tier 0 -- trivial: one heavy atom, only X-H bonds. Descent = hydrogen stripping to atoms.
    (0, "water",             "O",                 "H2O",     "descend", 1, None),
    (0, "ammonia",           "N",                 "H3N",     "descend", 1, None),
    (0, "methane",           "C",                 "CH4",     "descend", 1, None),
    (0, "hydrogen chloride", "Cl",                "ClH",     "descend", 1, None),
    (0, "hydrogen sulfide",  "S",                 "H2S",     "descend", 1, None),
    (0, "carbon dioxide",    "O=C=O",             "CO2",     "descend", 1, None),
    # Tier 1 -- small chains and functional groups: multiple heavy-atom bridges.
    (1, "ethane",            "CC",                "C2H6",    "descend", 1, None),
    (1, "ethanol",           "CCO",               "C2H6O",   "descend", 1, None),
    (1, "acetic acid",       "CC(=O)O",           "C2H4O2",  "descend", 1, None),
    (1, "methylamine",       "CN",                "CH5N",    "descend", 1, None),
    (1, "formaldehyde",      "C=O",               "CH2O",    "descend", 1, None),
    (1, "dimethyl ether",    "COC",               "C2H6O",   "descend", 1, None),
    # Tier 2 -- unsaturation + heteroatoms: double/triple bonds, mixed valence.
    (2, "ethylene",          "C=C",               "C2H4",    "descend", 1, None),
    (2, "acetylene",         "C#C",               "C2H2",    "descend", 1, None),
    (2, "acetaldehyde",      "CC=O",              "C2H4O",   "descend", 1, None),
    (2, "hydrogen cyanide",  "C#N",               "CHN",     "descend", 1, None),
    (2, "acetone",           "CC(=O)C",           "C3H6O",   "descend", 1, None),
    # Tier 3 -- single rings: THE honesty axis. A ring bond is not a bridge, so max_cut_bonds=1
    #           strips H and dead-ends at the carbon ring -- COMPLETE must not lie about atoms.
    (3, "cyclopropane",      "C1CC1",             "C3H6",    "descend", 1, None),
    (3, "cyclohexane",       "C1CCCCC1",          "C6H12",   "descend", 1, None),
    (3, "benzene",           "c1ccccc1",          "C6H6",    "descend", 1, None),
    # ... and the same rings with max_cut_bonds=2 (ring-opening enabled), depth-bounded.
    (3, "cyclopropane/open",  "C1CC1",            "C3H6",    "descend2", 2, 2),
    (3, "benzene/open",       "c1ccccc1",         "C6H6",    "descend2", 2, 1),
    # Tier 4 -- substituted aromatics: a breakable substituent bond on a ring.
    # phenol/aniline stay full-descent (a mixed case: atom terminals from -OH/-NH2 AND a ring core);
    # toluene/styrene/benzoic acid are depth-bounded -- their full atomic descent is many seconds of
    # aromatic H-stripping that adds no new invariant, only wall-clock.
    (4, "phenol",            "Oc1ccccc1",         "C6H6O",   "descend", 1, None),
    (4, "aniline",           "Nc1ccccc1",         "C6H7N",   "descend", 1, None),
    (4, "toluene",           "Cc1ccccc1",         "C7H8",    "descend", 1, 2),
    (4, "benzoic acid",      "OC(=O)c1ccccc1",    "C7H6O2",  "descend", 1, 2),
    (4, "styrene",           "C=Cc1ccccc1",       "C8H8",    "descend", 1, 2),
    # Tier 5 -- drug-sized (depth-bounded COMPLETE_TO_DEPTH): the litmus target and friends.
    (5, "benzaldehyde",      "O=Cc1ccccc1",       "C7H6O",   "descend", 1, 2),
    (5, "salicylic acid",    "OC(=O)c1ccccc1O",   "C7H6O3",  "descend", 1, 2),
    (5, "aspirin",           "CC(=O)Oc1ccccc1C(=O)O", "C9H8O4", "descend", 1, 2),
    (5, "paracetamol",       "CC(=O)Nc1ccc(O)cc1", "C8H9NO2", "descend", 1, 2),
    # Tier 6 -- fused / heteroaromatic-as-Kekule: strains the canonicaliser + parser.
    (6, "naphthalene",       "c1ccc2ccccc2c1",    "C10H8",   "descend", 1, None),
    (6, "pyridine(Kekule)",  "C1=CC=NC=C1",       "C5H5N",   "descend", 1, None),
    # Tier 7 -- ionic / electromagnetic bridge: heterolysis + redox, charge conservation.
    (7, "HCl (ionic)",       "Cl",                "ClH",     "ionic", 1, None),
    (7, "water (ionic)",     "O",                 "H2O",     "ionic", 1, None),
    (7, "Fe2+ (redox)",      None,                "Fe",      "redox", 1, None),  # bare cation
    (7, "Na (redox)",        None,                "Na",      "redox", 1, None),
]


def parse_hill(text: str) -> dict[str, int]:
    """A Hill-style formula string (``C6H6``, ``H2O``) -> element-count dict, for parser validation."""
    out: dict[str, int] = {}
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", text):
        if not sym:
            continue
        out[sym] = out.get(sym, 0) + (int(num) if num else 1)
    return out


class Findings:
    """Accumulates HARD violations (fail the gate) and HONESTY findings (surfaced, not failed)."""

    def __init__(self) -> None:
        self.hard: list[str] = []
        self.honesty: list[str] = []
        self.edges_audited = 0
        self.valence_rechecks = 0
        self.forget_checks = 0
        self.label_checks = 0
        self.charge_checks = 0

    def fail(self, name: str, msg: str) -> None:
        self.hard.append(f"[{name}] {msg}")

    def note(self, name: str, msg: str) -> None:
        self.honesty.append(f"[{name}] {msg}")


def _node_molecules(graph, target: Molecule) -> dict[str, Molecule]:
    """Every distinct node molecule in the graph, keyed by presentation-invariant identity."""
    nodes: dict[str, Molecule] = {_mol_key(target): target}
    for e in graph.edges:
        nodes[_mol_key(e.reactant)] = e.reactant
        for f in e.fragments:
            nodes[_mol_key(f.molecule)] = f.molecule
    return nodes


def _has_bridge(mol: Molecule) -> bool:
    """Whether the molecule has at least one single-cut disconnecting bond (a decomposition exists)."""
    from smartchem.structure_descent import _components

    n = len(mol.atoms)
    if n < 2 or not mol.bonds:
        return False
    for b in mol.bonds:
        if len(_components(n, mol.bonds - {b})) >= 2:
            return True
    return False


def audit_descent(name: str, mol: Molecule, cut: int, depth: int | None, f: Findings) -> str:
    """Run the descent and audit every reality-respecting invariant. Returns a one-line status."""
    graph = structure_decompose(mol, max_cut_bonds=cut, max_depth=depth)

    # (0) status is one of the three honest labels (constructor enforces; assert the contract holds)
    if graph.status not in ("COMPLETE", "COMPLETE_TO_DEPTH", "REFUSED_BUDGET"):
        f.fail(name, f"illegal status {graph.status!r}")
        return "ILLEGAL-STATUS"

    # (1) NON-VACUITY: a molecule with a disconnecting cut MUST produce >=1 edge from the target.
    target_can_split = _has_bridge(mol) or (cut >= 2 and len(mol.atoms) > 1 and bool(mol.bonds))
    root_edges = graph.edges_from(mol)
    if target_can_split and not root_edges:
        f.fail(name, "VACUOUS: target has a disconnecting cut but produced zero scission edges")
    if not target_can_split and root_edges:
        f.fail(name, "spurious: target has no disconnecting single cut yet edges were emitted")

    # (2) every edge disconnects, forgets to a valid v1 edge, conserves atoms, labels honestly.
    for e in graph.edges:
        f.edges_audited += 1
        if not e.disconnects:
            f.fail(name, f"edge does not disconnect: {e.equation()}")

        # independent valence recompute -- a SECOND path to the same fact (not the edge's own cert)
        f.valence_rechecks += 1
        if not verify_valence_integrity(e.reactant, e.cut_bonds):
            f.fail(name, f"independent valence recompute REJECTS a live edge: {e.equation()}")

        # the forgetful commuting square: forget() must construct a valid v1 DecompositionEdge and
        # conserve atoms at composition level (recomputed here from the products, not trusted).
        f.forget_checks += 1
        try:
            v1 = e.forget()
        except Exception as exc:  # noqa: BLE001 -- a forget() that raises is a hard bug to surface
            f.fail(name, f"forget() raised {type(exc).__name__}: {exc} on {e.equation()}")
            continue
        want = dict(Counter(e.reactant.atoms))
        got: Counter = Counter()
        for prod, mult in v1.products:
            for sym, c in prod.counts:
                got[sym] += c * mult
        if want != dict(got):
            f.fail(name, f"forget() breaks atom conservation: {want} != {dict(got)} on {e.equation()}")

        # honest labelling: an open-valence fragment is RADICAL(_ION), never CLOSED.
        for frag in e.fragments:
            f.label_checks += 1
            cls = species_class(frag)
            if frag.open_valence_total > 0 and cls not in (SpeciesClass.RADICAL, SpeciesClass.RADICAL_ION):
                f.fail(name, f"open-valence fragment mislabelled {cls.value} (expected RADICAL): "
                             f"{frag.formula!r}")
            if frag.open_valence_total == 0 and frag.molecule.charge == 0 and cls != SpeciesClass.CLOSED:
                f.fail(name, f"closed fragment mislabelled {cls.value}: {frag.formula!r}")

    # (3) HONEST TERMINATION: the engine must not claim it atomised a target it did not. This uses the
    #     engine's OWN accessors (reaches_single_atoms / irreducible_cores) and VERIFIES they tell the
    #     truth against a fully independent from-scratch recompute -- so an over-claim is now a HARD
    #     failure, not just a note. (The recompute always re-runs scission_edges; irreducible_cores()
    #     takes a 'no out-edge in a finished search' shortcut on COMPLETE graphs, so the two paths are
    #     genuinely independent exactly where the old over-claim lived.)
    nodes = _node_molecules(graph, mol)
    has_out = {_mol_key(e.reactant) for e in graph.edges}   # O(edges) once, not O(nodes*edges)
    indep_cores = []
    for key, m in nodes.items():
        if len(m.atoms) > 1 and m.bonds and key not in has_out:
            edges_m, complete_m = scission_edges(m, max_cut_bonds=cut)
            if complete_m and not edges_m:                 # genuinely no admissible cut -> a true core
                indep_cores.append(m)
    truly_atomised = graph.status == "COMPLETE" and not indep_cores
    if graph.reaches_single_atoms != truly_atomised:
        f.fail(name, f"reaches_single_atoms={graph.reaches_single_atoms} contradicts the independent "
                     f"recompute ({truly_atomised}); cores="
                     f"{[repr(Formula.of(m.formula, m.charge)) for m in indep_cores]}")
    engine_cores = graph.irreducible_cores()
    if graph.status == "COMPLETE" and {_mol_key(m) for m in engine_cores} != {_mol_key(m) for m in indep_cores}:
        f.fail(name, "irreducible_cores() disagrees with the independent recompute on a COMPLETE graph")
    if graph.status == "COMPLETE" and engine_cores:
        core_str = ", ".join(sorted({repr(Formula.of(m.formula, m.charge)) for m in engine_cores}))
        f.note(name, f"COMPLETE and honestly reports it did NOT atomise: bottoms out at irreducible "
                     f"core(s) {{{core_str}}}; reaches_single_atoms=False (the fix, verified)")

    return (f"{graph.status} edges={len(graph.edges)} nodes={len(nodes)} "
            f"atomised={'Y' if graph.reaches_single_atoms else 'N'} cores={len(engine_cores)}")


def audit_ionic(name: str, mol: Molecule, f: Findings) -> str:
    """Audit heterolysis + redox: charge conservation, mass conservation, honest ION labelling."""
    ie = ionic_edges(mol)
    n_het, n_redox = len(ie.heterolytic), len(ie.redox)

    if mol.charge == 0 and _has_bridge(mol) and n_het == 0:
        f.fail(name, "VACUOUS: neutral bridged molecule produced zero heterolytic cleavages")
    if n_redox == 0:
        f.fail(name, "VACUOUS: no redox couples emitted")

    for h in ie.heterolytic:
        f.charge_checks += 1
        # charge conserved (recomputed): anion(-1) + cation(+1) == reactant(0)
        if h.anion.charge + h.cation.charge != h.reactant.charge:
            f.fail(name, f"heterolysis breaks charge conservation: {h.equation()}")
        # mass conserved (recomputed): the ion atoms partition the reactant's
        if Counter(h.anion.atoms) + Counter(h.cation.atoms) != Counter(h.reactant.atoms):
            f.fail(name, f"heterolysis breaks mass conservation: {h.equation()}")
    for ion in ie.ions:
        f.label_checks += 1
        if species_class(ion) is not SpeciesClass.ION:
            f.fail(name, f"heterolytic product not labelled ION: {ion!r}")

    for rx in ie.redox:
        f.charge_checks += 1
        # charge conserved (recomputed): oxidized.charge - n == reduced.charge
        if rx.oxidized.charge - rx.electrons != rx.reduced.charge:
            f.fail(name, f"redox breaks charge conservation: {rx.equation()}")
        # mass conserved: electron is massless, so oxidized atoms == reduced atoms
        if rx.reduced.atoms != rx.oxidized.atoms:
            f.fail(name, f"redox changed the atom set (electron must be massless): {rx.equation()}")
        if ELECTRON.atoms != () or dict(ELECTRON.formula) != {}:
            f.fail(name, "ELECTRON is not massless -- charge has become matter")

    return f"heterolysis={n_het} redox={n_redox} ions={len(ie.ions)}"


def audit_redox_bare(name: str, symbol: str, f: Findings) -> str:
    """Redox of a bare species (metallic ionisation) -- the chemical<->EM bridge on a single atom."""
    from smartchem.structure_descent import redox_couples

    species = Molecule.atom(symbol, charge=2) if symbol == "Fe" else Molecule.atom(symbol)
    couples = redox_couples(species, max_electrons=2)
    if not couples:
        f.fail(name, "VACUOUS: no redox couples for a bare species")
    for rx in couples:
        f.charge_checks += 1
        if rx.oxidized.charge - rx.electrons != rx.reduced.charge:
            f.fail(name, f"bare redox breaks charge conservation: {rx.equation()}")
        if rx.reduced.atoms != rx.oxidized.atoms:
            f.fail(name, f"bare redox changed the atom set: {rx.equation()}")
    return f"redox_couples={len(couples)} e.g. {couples[0].equation()}"


def main() -> int:
    f = Findings()
    print("=" * 96)
    print("STRUCTURE DECOMPILER -- reality-respecting ladder (W3: structure certified, physics never)")
    print("=" * 96)
    header = f"{'tier':>4} {'chemical':<20} {'formula':<10} {'mode':<9} result"
    print(header)
    print("-" * 96)

    last_tier = -1
    for tier, name, smiles, formula, mode, cut, depth in LADDER:
        if tier != last_tier:
            print(f"--- tier {tier} " + "-" * 84)
            last_tier = tier

        # parse (where applicable) and validate the parser's formula independently.
        mol = None
        if smiles is not None:
            try:
                mol = parse_smiles(smiles)
            except SmilesError as exc:
                f.fail(name, f"parse_smiles({smiles!r}) raised SmilesError: {exc}")
                print(f"{tier:>4} {name:<20} {formula:<10} {mode:<9} PARSE-FAIL: {exc}")
                continue
            got = mol.formula
            want = parse_hill(formula)
            if dict(got) != want:
                f.fail(name, f"parser formula {dict(got)} != declared {want} ({smiles!r})")

        try:
            if mode in ("descend", "descend2"):
                result = audit_descent(name, mol, cut, depth, f)
            elif mode == "ionic":
                result = audit_ionic(name, mol, f)
            elif mode == "redox":
                result = audit_redox_bare(name, formula, f)
            else:
                f.fail(name, f"unknown mode {mode!r}")
                result = "UNKNOWN-MODE"
        except Exception as exc:  # noqa: BLE001 -- an unexpected raise on a real molecule is a finding
            f.fail(name, f"{mode} raised {type(exc).__name__}: {exc}")
            result = f"RAISED {type(exc).__name__}"

        print(f"{tier:>4} {name:<20} {formula:<10} {mode:<9} {result}")

    print("-" * 96)
    print(f"audited: {f.edges_audited} scission edges, {f.valence_rechecks} independent valence "
          f"recomputes, {f.forget_checks} forget() projections,")
    print(f"         {f.label_checks} species labels, {f.charge_checks} charge/mass conservations.")

    # NON-VACUITY of the audit itself: a green run over zero edges would be the worst kind of lie.
    if f.edges_audited < 100:
        f.fail("HARNESS", f"only {f.edges_audited} edges audited -- suspiciously few; the ladder is "
                          f"not exercising the machinery")

    print("=" * 96)
    if f.honesty:
        print(f"IRREDUCIBLE-CORE BOUNDARY ({len(f.honesty)}) -- rings the descent honestly reports it "
              f"could NOT atomise (verified against an independent recompute):")
        for msg in f.honesty:
            print(f"  ~ {msg}")
        print("=" * 96)

    if f.hard:
        print(f"HARD VIOLATIONS ({len(f.hard)}) -- reality NOT respected:")
        for msg in f.hard:
            print(f"  x {msg}")
        print("=" * 96)
        print("VERDICT: FAIL -- the decompiler emitted output that does not respect conservation, "
              "valence, labelling, or non-vacuity.")
        return 1

    print("VERDICT: PASS -- every emitted edge conserves atoms and charge, is valence-valid, forgets "
          "to a valid formula edge, and is honestly labelled; every decomposable target was "
          "non-vacuously exercised.")
    if f.honesty:
        print(f"         ({len(f.honesty)} ring target(s) correctly report reaches_single_atoms=False "
              f"with their irreducible core surfaced -- the descent never claims an atomisation it did "
              f"not achieve.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
