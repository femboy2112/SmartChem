"""
Mutation testing for Brick 3's termination rule: write the plausible wrong version, count
the survivors.

    python experiments/ledger_mutation_probe.py

WHY THIS EXISTS AS A COMMITTED FILE
-------------------------------------
Every "a mutant survived N of N tests" claim in this repository -- 239 of 239 for the
rendering defect, 31 for the domain under-approximation, 28 of 29 for Brick 0's sublattice
-- was measured by a throwaway script and then quoted from memory. The number is the most
informative thing a test suite can say about itself ("N passed" says nothing about what a
wrong implementation would do), and it was the one number with no reproducible instrument
behind it. This is that instrument, for one module.

WHAT A SURVIVOR MEANS, AND WHAT IT DOES NOT
---------------------------------------------
A surviving mutant is a wrong implementation the suite accepts. That is a hole, and the
repair is a test that reaches the subject by a route the subject does not control. A killed
mutant proves only that the suite notices THAT wrongness; it is not evidence of coverage in
general, and this file never reports a percentage for exactly that reason.

Each mutation carries ``why`` -- the reasoning error it embodies -- because a mutant nobody
would plausibly write proves nothing when it dies.

SAFETY
------
The module is restored in a ``finally``, and the restoration is verified byte-for-byte
before the process exits. If that check ever fails the run is a hard error, because a
mutation harness that leaves a mutant in the tree is strictly worse than no harness.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "smartchem" / "ledger.py"
SUITE = "tests/test_ledger.py"

STOICHIOMETRY = ROOT / "smartchem" / "stoichiometry.py"
STOICHIOMETRY_SUITE = "tests/test_stoichiometry.py tests/test_section_i.py"

#: (name, exact source text, replacement, the reasoning error it embodies).
#:
#: The ``old`` strings are required to appear EXACTLY ONCE in the target. A mutation that
#: silently matched twice, or zero times, would be reported as a survivor and read as a
#: hole in the suite when it was really a hole in this file.
MUTATIONS = [
    (
        "sort-not-descending",
        "reverse=True))",
        "reverse=False))",
        "Sorting the ranks ascending instead of descending. The tuple still looks like a "
        "measure and still compares, but lex order on ASCENDING tuples is not well-founded "
        "-- (1,) > (0,1) > (0,0,1) > ... -- so the loop can be driven forever.",
    ),
    (
        "sort-dropped-entirely",
        "return tuple(sorted((slot.rank for slot in self.holes()), reverse=True))",
        "return tuple(slot.rank for slot in self.holes())",
        "Taking the ranks in slot order and calling it a measure. Reads as an obvious "
        "simplification -- why sort a list you are only comparing? -- and it is the same "
        "non-termination as above, arriving by omission rather than by a wrong argument.",
    ),
    (
        "descent-not-strict",
        "        if after_ordinal < before_ordinal:\n",
        "        if after_ordinal <= before_ordinal:\n",
        "The classic off-by-one on a termination rule: accepting a round that changed "
        "nothing. Section VI.3's word is *strictly*, and <= makes every rephrase progress.",
    ),
    (
        "negative-rank-allowed",
        "if self.rank < 0:",
        "if False:",
        "Dropping the well-foundedness guard as an unnecessary constructor check. The "
        "integers are not well-founded, so one negative rank buys an infinite descent that "
        "every comparison in the module reports as honest progress.",
    ),
    (
        "widening-collapsed-into-stalling",
        "        if opened or after_ordinal > before_ordinal:\n",
        "        if False:\n",
        "Reporting a widening as a stall. The first build of this module made the sibling "
        "of this mistake with empty menus; collapsing an informative case into a failure "
        "case tells a scientist to fix the wrong thing.",
    ),
    (
        "widening-decided-by-names-only",
        "        if opened or after_ordinal > before_ordinal:\n",
        "        if opened:\n",
        "The defect an adversarial pass actually found in the committed module, restored "
        "verbatim. Deciding the HALT REASON from slot-name set differences rather than "
        "from the ordinal the halt decision was made on. The gate stays correct, so every "
        "termination test passes; a round that raises an existing hole's rank 0 -> 5 is "
        "then reported as 'it rephrased', two lines under its own ranks [0,0,0] =/=> [5].",
    ),
    (
        "rank-type-unchecked",
        "        if not isinstance(self.rank, int):\n",
        "        if False:\n",
        "Trusting the ``rank: int`` annotation, which does not run. inf then passes the "
        "sign test and makes round_bound infinite, so the loop's only backstop against a "
        "runaway responder can never fire; nan passes it too and stops the ranks being an "
        "order at all. The plausible reading is 'the sign check already covers this'.",
    ),
    (
        "responder-return-untyped",
        "        if not isinstance(following, Spec):\n",
        "        if False:\n",
        "Duck-typing the responder's return, which is what the module did until an "
        "adversary fed it an impostor. An object merely supplying ordinal()/measure() can "
        "drive the loop to a LedgerContradiction -- a message accusing the descent check "
        "of not enforcing what it claims, about machinery that was never exercised.",
    ),
    (
        "duplicate-slot-names-allowed",
        "        if len(names) == len(set(names)):\n            return\n",
        "        if True:\n            return\n",
        "Enforcing the no-duplicate-names invariant at widen() only, the way it was. A "
        "directly constructed Spec then double-counts one name in every measure, and "
        "bind() -- filtering on ``s.name == name``, not the first match -- binds both at "
        "once. Monotone, so no termination test can see it.",
    ),
    (
        "bound-always-unconditional",
        "        return all(slot.rank == 0 for slot in self.holes())",
        "        return True",
        "Claiming the round bound is a theorem for every spec. Turns a reached resource "
        "limit into a LedgerContradiction -- asserting a theorem the module does not have.",
    ),
    (
        "bound-never-unconditional",
        "        return all(slot.rank == 0 for slot in self.holes())",
        "        return False",
        "The opposite: never claiming the bound even when it is unconditional, which "
        "disarms LedgerContradiction on the one spec shape where it is provable.",
    ),
    (
        "rank-ignored-in-the-measure",
        "return tuple(sorted((slot.rank for slot in self.holes()), reverse=True))",
        "return tuple(0 for slot in self.holes())",
        "Keeping the ordinal's shape but flattening every rank to 0, i.e. cardinality "
        "wearing the new interface. Terminates fine and refuses every legitimate "
        "deepening -- the original defect, now invisible behind a passing type.",
    ),
]


#: Section I's second clause, mutated. ``StoichiometryMenu.check`` decides whether a balance
#: a SCIENTIST WROTE is admissible, so every wrong version here is a confident verdict about
#: someone else's chemistry -- the exact failure this package exists to refuse.
WRITTEN_CHECK_MUTATIONS = [
    (
        "the-empty-vector-accepted",
        "        trivial = not any(nu)\n",
        "        trivial = False\n",
        "Dropping the all-zero guard. A @ 0 == 0 exactly, on every row, in every menu that "
        "has ever existed, so a bare residual test reports the empty statement as a "
        "balanced reaction. The most plausible mutation here: it looks like a special case "
        "someone added defensively, and it is the one case the residual cannot catch.",
    ),
    (
        "verified-collapsed-into-admissible",
        "        return self.admissible and not self.unverifiable\n",
        "        return self.admissible\n",
        "Treating 'it balances' and 'the invariants could see what it balances' as one "
        "claim. Na(*) -> Na then reports VERIFIED, which is a confident statement about "
        "de-excitation derived from invariants that cannot see excitation.",
    ),
    (
        "truthiness-follows-the-weaker-claim",
        "        return self.verified\n",
        "        return self.admissible\n",
        "Making bool() agree with Session.__bool__, which IS truthy on its weaker case. "
        "Plausible by analogy and wrong: COMPILED_SUBJECT_TO is a checked result with a "
        "condition, while an unverifiable balance is silence about part of the claim.",
    ),
    (
        "charge-row-dropped-from-the-residual",
        "                         for row in self.matrix)",
        "                         for row in self.matrix[:-1])",
        "Checking the element rows and not the charge row, which composition_matrix appends "
        "last. `conserves` tests atoms AND charge, so this accepts balances that Reaction "
        "then refuses -- and the MenuContradiction path is what would catch it.",
    ),
    (
        "unverifiable-ignores-whether-it-is-touched",
        "                             if c and molecule in self.unconstrained)",
        "                             if molecule in self.unconstrained)",
        "Flagging every invariant-blind species in the candidate set rather than the ones "
        "the vector actually uses. Over-refuses: a blind species with coefficient zero is "
        "not being leaned on, and reporting it downgrades verdicts that were fine.",
    ),
    (
        "written-length-unchecked",
        "        if len(nu) != len(self.species):\n",
        "        if False:\n",
        "Trusting the caller to align their vector. zip and the row loop then read past or "
        "short of the species tuple, and the verdict is about a different vector than the "
        "one that was written.",
    ),
    (
        "coefficient-type-unchecked",
        "        if any(type(c) is not int for c in nu):\n",
        "        if False:\n",
        "Dropping the type guard outright. A float sums cleanly into the residual and "
        "yields a confident admissible/refused verdict about a vector that is not a "
        "candidate balance at all.",
    ),
    (
        "equation-checks-length-not-identity",
        "        if species is not None and tuple(species) != self.species:\n",
        "        if species is not None and len(species) != len(self.species):\n",
        "The first repair, restored verbatim -- and it is the more instructive mutant "
        "because it is not a strawman, it SHIPPED. Guarding the length stops zip "
        "truncating and leaves the worse case open: a same-length tuple in a different "
        "order renders a complete, plausible, unbalanced equation, and reordering a "
        "species list is an ordinary pipeline mistake rather than an attack.",
    ),
    (
        "unordered-coefficients-allowed",
        "        if not isinstance(coefficients, Sequence) or isinstance(coefficients, (str, bytes)):\n",
        "        if False:\n",
        "Trusting tuple() to preserve an order the container never had. A set has a "
        "length, holds ints, and passes every other guard; tuple() freezes it in HASH "
        "order, and 34 of 39 scalings of a correct balance then come back as a confident, "
        "specific, WRONG refusal with fabricated row violations.",
    ),
    (
        "int-subclasses-allowed",
        "        if any(type(c) is not int for c in nu):\n",
        "        if any(not isinstance(c, int) or isinstance(c, bool) for c in nu):\n",
        "The previous version, restored verbatim -- isinstance admits int SUBCLASSES. The "
        "weight cap and _configs each call abs() independently, so a stateful __abs__ "
        "passes the cap honestly and then allocates the huge value. Measured: declared "
        "weight 4, allocated 5,000,000 molecules, reported as a MenuContradiction -- the "
        "module accusing its own derivations when neither was wrong and the type lied.",
    ),
]


def _pytest(suite: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *suite.split(), "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, timeout=600)


def _run_suite(suite: str) -> tuple[bool, str]:
    """Run a suite. Returns (all passed, the last line of output)."""
    proc = _pytest(suite)
    lines = [line for line in proc.stdout.strip().splitlines() if line.strip()]
    return proc.returncode == 0, (lines[-1] if lines else "<no output>")


def _failed_test_names(output: str) -> list[str]:
    return sorted({line.split("::")[-1].split()[0]
                   for line in output.splitlines() if line.startswith("FAILED")})


def _probe(label: str, target: Path, suite: str, mutations: list) -> tuple[int, list[str]]:
    """Run every mutation for one target. Returns (exit hint, survivor names)."""
    original = target.read_text()

    print("\n" + "=" * 78)
    print(f"{label}")
    print("=" * 78)
    print(f"  target           : {target.relative_to(ROOT)}")
    print(f"  suite            : {suite}")

    clean_ok, clean_line = _run_suite(suite)
    print(f"  unmutated        : {clean_line}")
    if not clean_ok:
        print("  ABORTED: the suite does not pass before any mutation, so a 'killed' "
              "verdict below would be meaningless.")
        return 1, ["<suite red before mutation>"]

    survivors: list[str] = []
    try:
        for name, old, new, why in mutations:
            occurrences = original.count(old)
            print(f"\n  -- {name} " + "-" * max(0, 62 - len(name)))
            print(f"     why : {why}")
            if occurrences != 1:
                print(f"     ERROR: anchor text appears {occurrences} times, expected "
                      f"exactly 1. Not run -- a stale anchor reports as a survivor and "
                      f"would be read as a hole in the suite.")
                survivors.append(f"{name} (ANCHOR STALE)")
                continue

            target.write_text(original.replace(old, new))
            proc = _pytest(suite)
            lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
            summary = lines[-1] if lines else "<no output>"
            killers = _failed_test_names(proc.stdout)

            if proc.returncode == 0:
                print(f"     SURVIVED : {summary}")
                survivors.append(name)
            else:
                print(f"     killed by {len(killers)} test(s) : {summary}")
                for killer in killers:
                    print(f"         {killer}")
    finally:
        target.write_text(original)

    if target.read_text() != original:
        print("\n  HARD ERROR: the target was NOT restored byte-for-byte.")
        return 2, survivors

    print(f"\n  {label}: {len(mutations)} mutants, {len(survivors)} survivors, "
          f"target restored byte-identical")
    return 0, survivors


def main() -> int:
    runs = [
        ("BRICK 3 -- the termination rule", TARGET, SUITE, MUTATIONS),
        ("BRICK 4 -- section I's second clause", STOICHIOMETRY, STOICHIOMETRY_SUITE,
         WRITTEN_CHECK_MUTATIONS),
    ]
    worst, total, all_survivors = 0, 0, []
    for label, target, suite, mutations in runs:
        code, survivors = _probe(label, target, suite, mutations)
        worst = max(worst, code)
        total += len(mutations)
        all_survivors += [f"{label.split(' -- ')[0]}/{s}" for s in survivors]

    print("\n" + "=" * 78)
    print(f"  targets          : {len(runs)}")
    print(f"  mutants run      : {total}")
    print(f"  survivors        : {len(all_survivors)}"
          + ("" if not all_survivors else "  -> " + ", ".join(all_survivors)))
    print(f"  targets restored : byte-identical, verified")
    if all_survivors:
        print("  A survivor is a wrong implementation this suite accepts. It is a hole, "
              "and the repair is a test that reaches the subject by a route the subject "
              "does not control.")
    print("=" * 78)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
