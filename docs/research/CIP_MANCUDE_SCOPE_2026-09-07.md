# Bounded neutral mancude Rule-1a extension — 2026-09-07

The namer now resolves neutral aryl and heteroaryl ligands by exact duplicate atomic-number
averaging. It also fixes a shipped wrong label on an explicit Kekulé input. This is a bounded
extension of Rule 1a; it does not complete CIP.

Base: `043a3cd`, isolated worktree `SmartChem-codex-20260907`, branch
`codex/mancude-duration-sourcing-2026-09-07`. No edits were made to the original Claude worktree.

## Source contact and the decisive distinction

[IUPAC Blue Book P-92.1.4.4](https://iupac.qmul.ac.uk/BlueBook/P9.html#P-92.1.4.4)
assigns each multiple-bond duplicate the mean atomic number of its possible double-bond partners.
Its worked heterocycle gives `7`, `13/2`, and `19/3` for different local environments.
For neutral systems, this is a mean over distinct partner positions. Counting the frequency of
each partner across complete Kekulé structures can produce a different value in fused rings.
We enumerate structures to find feasible partners and average each distinct partner once.
Real atoms and ring-closure duplicates retain their actual integer atomic numbers.

[Hanson et al., JCIM 2018, DOI 10.1021/acs.jcim.8b00324](https://doi.org/10.1021/acs.jcim.8b00324)
discusses this complication in Rule 1a and Figure 3. The authors identify ambiguities beyond the
simple neutral cases, including charge delocalization and the general boundary of the rule.
That discussion does not justify treating every resonance problem with this implementation.

The authors' [validation suite, pinned source](https://github.com/cipvalidationsuite/ValidationSuite/blob/b795ce1220e970943814a8669df78dd38c29b7e1/compounds.smi)
contains the two absolute anchors used by the new dependency-free probe:

| Source ID | Source SMILES | Tetrahedral expectation |
|---|---|---|
| VS032 | `O[C@H](/C=N\C)C1=NC=CC=C1` | atom 2: S |
| VS033 | `O[C@H](/C=N\C)C=1N=CC=CC1` | atom 2: S |

The pyridyl duplicate `13/2` loses to the ordinary imine-N duplicate `7`. Both inputs now
produce `("S",)`. The suite also specifies double-bond descriptors; this probe checks only
its tetrahedral Rule-1a assignment, consistent with the namer's existing scope.

Source bytes retrieved on 2026-09-07 UTC:

- Validation suite `compounds.smi`, last modifying commit
  `b795ce1220e970943814a8669df78dd38c29b7e1`, SHA-256
  `df178635c00b6c41fad820d2609fc4ff18403c63dec4e5c3e1756a6db5858059`.
- IUPAC `P9.html`, SHA-256
  `0cec49d2506a0a53dd7e6944278a73cc36ec50111fa9a5b300d20a425ac536ac`.

## Implementation and admission boundary

`smartchem/smiles.py` adds `_cip_ring_edges` and `_cip_mancude`. An iterative bridge search
finds ring bonds from the sigma topology. This prevents a bond between two independent rings,
such as biphenyl's connecting bond, from becoming a resonance partner. Ring components are
identified after the existing index-preserving Kekulization and hydrogen fill.

Each supported unsaturated ring component must have these neutral, filled valence patterns:

| Type | Incident bond orders, including hydrogens | Ring double requirement |
|---|---|---|
| Carbon acceptor | `1,1,2` | exactly one |
| Pyridine-type N acceptor | `1,2` | exactly one |
| Fixed pyrrole-type N donor | `1,1,1` | none |
| Fixed O or S donor | `1,1` | none |

Perfect matchings cover the acceptors; donors contribute no multiple-bond duplicate. Each
acceptor's feasible partner set produces a standard-library `Fraction`. The ordinary digraph
still handles sigma bonds, ring closures and multiple-bond duplicate counts. Only the atomic
number of a multiple-bond duplicate changes, using the **owning real atom's** partner average.
The existing comparator and parity-to-R/S convention remain unchanged.

The same topology and valence path handles aromatic lowercase and explicit Kekulé SMILES.
Lowercase flags do not grant admission or bypass the checks. Neutral phenyl, pyridyl,
pyrimidinyl, furyl, thienyl, pyrrolyl, imidazolyl, naphthyl, quinolyl and indolyl families are
exercised in the committed dependency-free panel.

Bounds are per unsaturated ring component: 30 atoms, 128 complete matchings and 10,000
matching-search visits. Exceeding any bound discards that component's entire tentative partner
set. There is no truncated average. The existing digraph and comparison budgets remain in force.
These additional limits do not replace the parser's pre-existing identity/Kekulization limits.

Charged rings, exocyclic multiple bonds, untyped valences/elements, incompletely conjugated
ring systems and over-budget systems remain lazy boundaries. Their atomic number can still
decide a ranking before onward connectivity is required. Saturated rings retain their ordinary
digraph behavior. Some explicit unsaturated inputs that previously received a label are now
deferred because they fail this admission boundary; this is intentional fail-closed behavior.

The parser still refuses aromatic pyridinium `[nH+]` under its existing donor convention.
An explicit pyridinium spelling reaches the new CIP boundary and defers. This change does
not expand the parser's charged aromatic chemistry.

## Falsifiers, controls and observations

The prior fixed-Kekulé guard covered lowercase aromatic atoms but left uppercase spellings
exposed. An external accurate-CIP baseline found this concrete wrong answer:

| Input | Before | After / external expectation |
|---|---|---|
| `O[C@H](C1=CC=CC=N1)C1=NC=CN=C1` | S | R |
| Same input with `@@` | R | S |

The regression test includes both explicit and aromatic forms. The historical false-centre
pin `O[C@H](c1ccccn1)c1ccccn1` remains unnamed because its two 2-pyridyl ligands remain tied.
Mixed aromatic/explicit identical ligands also remain tied.

`experiments/cip_mancude_probe.py` contains the two source anchors and 12 ligand families,
each with aromatic/explicit naming, reflection, and all four identical-ligand spelling pairs:
96 family cases. These family labels use the existing absolute geometry convention and
the elementary priority `O > aryl C > methyl > H`. They are relational controls, not 96
independent external absolute sources.

`tests/test_cip_mancude.py` also checks exact `13/2`, `19/3` and `7` fractions; the distinction
between owner averaging and integer ring-closure duplication; a ring-to-ring bridge; charged
and exocyclic deferrals; lazy ranking past irrelevant unsupported branches; isotope-only ties;
ring-centre deferrals; and both zero and small exhaustion values for all three new bounds.

Executed from the isolated worktree, with the original environment's interpreter:

```sh
PYTHONPATH=/home/leah/SmartChem-codex-20260907 \
  /home/leah/SmartChem/.venv/bin/python -m pytest -q \
  tests/test_cip_mancude.py tests/test_cip_namer.py \
  tests/test_cip_naming.py tests/test_cip_geometry_oracle.py
```

Result: **168 passed in 17.57 s**. `git diff --check` passed. The root integration receipt
records the full-suite gate and the separate external-oracle panels. Independent review
reported 1,224 cases with 1,088 correct named outputs and 136 true ties; a fresh 1,134-case
panel reported 900 correct named outputs, 80 true ties, 101 deferrals and 53 parser refusals.
Neither panel reported a wrong named label. These panels use the same RDKit implementation
family and must not be counted as independent source families.

The older namer harness was intentionally updated: 1-phenylethylamine moves from its deferral
list to its twentieth elementary absolute anchor. Its frozen content hash changes from
`93f972617a1bb6f498c03154e3534be7ffbbc3bac2f1ac8d86486c1d57e2d9da` to
`bac7eb7bead37ed650e0641e1214697780156fdd2cc681afa4e4aaf11ed33a25`.
Its priority-extraction helper now uses the same mancude context as the namer.

## Claim ledger

| Claim | Status | Evidence and boundary | Next discriminator |
|---|---|---|---|
| Fixed explicit-Kekulé ranking can mislabel | Refuted prior behavior | Concrete pyridyl/diazinyl counterexample, independent accurate-CIP baseline | Keep both senses and both input routes in regression |
| New neutral mancude behavior preserves source anchors and tested spellings | Corroborated in the tested scope | Primary VS032/033, exact fractions, relational controls, external implementation panels | Fresh unsupported/fused regimes and independently derived priority cases |
| Exhaustion never publishes partial fractions | Observed on execution controls; explicit discard in code | Zero and small limits for all three caps | Larger hostile matching graphs within parser admission |
| General CIP is complete | Not claimed | Rules 1b/2/3/4/5 tie resolution, ring stereocentres and general charged resonance remain outside this build | Separate source-exact implementation and tests |
| Existing comparator is universally transitive/correct | UNVERIFIED | Existing branch-paired tests and finite panels remain; this change does not prove the comparator | Formal argument or a discriminating deep tie-tree counterexample |

The epistemic work was a pathway-gap plus a configuration-sensitive defect: the original
guard mistook a spelling flag for the scope boundary. The useful transport is chemically
equivalent SMILES/Kekulé spelling, with the output compared in the common R/S basis. No
phase, probability-of-truth, or physical quantum interpretation is used. Source attribution
and content survival are kept separate: IUPAC/the authors supply the rule and absolutes;
RDKit supplies an independent implementation bearing; SmartChem relational tests share
its own parser/comparator and are not independent certification.
