# 1.3 Reaction-Algebra Expansion (Phase III) — findings and scope (2026-10-30)

Off `main` `9e8fa5f`, branch `feat/reaction-algebra-1.3` (stacked on the #112 SN2 branch `ade0f28` to reuse the
#106 radius-1 predicate). This round's prime directive, from the execution plan: **"Prefer two fully sound new
families over five superficially working ones. The goal is increased real coverage, not an inflated recognizer
count."** Phase III names three candidate families — #116 elimination, #119 imine/carbonyl condensation, #117
enolate C–C. This note records what shipped, and the **evidenced** reason the other two are deferred rather than
half-built.

## Shipped: #119 carbonyl + amine → imine condensation (a genuinely new generator + recognizer)

A new transform family — the 22nd recognized class. See `smartchem/imine_condensation.py` (generator) and
`_imine_condensation` in `smartchem/experiment/reaction_type_oracle.py` (recognizer), with
`experiments/imine_condensation_probe.py` (frozen evidence) and `tests/test_imine_condensation_119.py`.

**Why it needed a new generator (not just a recognizer).** Capped scission and the bond-order-edit family both
rewrite only bonds reachable by breaking order-1 bonds and capping opened ends; neither can mint or cleave a C=N
double bond. A probe confirms the default registry, handed an imine + water, cuts the *adjacent* order-1 N–C bond
into fictions (`imine + water → methane + formaldoxime`, `→ methanimine + methanol`) and **never** produces the
real `carbonyl + amine` retro. So without a bespoke generator the route search can never produce a real imine
condensation, and a recognizer alone would have zero real consumers. The generator supplies the missing C=N retro;
the recognizer vouches its forward synthesis steps.

**Soundness.** The edge (`ImineCondensationEdge`) is a valence-preserving hydrolysis `imine + water → carbonyl +
amine` (the carbonyl carbon trades `=N` for `=O`; the nitrogen trades `=C` for two `N–H`; the water oxygen trades
two `O–H` for `=C`). Its certificate requires an order-2 C=N, a tetravalent carbonyl carbon bearing only C/H
besides the `=N` (excludes amidine/imidate), a neutral valence-3 nitrogen with exactly one C/H/O/N substituent
(excludes iminium), and a mass/charge-conserving split into exactly **two** closed-shell-neutral fragments each
strictly smaller than the imine (so a **cyclic/aromatic** C=N, which opens to one fragment, is refused). The
recognizer re-derives through the family's own retro (never reading `reaction_center` — content-deterministic) and
fails closed. Covers the plan's imine / oxime / hydrazone / primary-imine (ammonia) subset; the N-substituent
C/H → Schiff base, O → oxime, N → hydrazone. The provider is **opt-in** (absent from the default registry, the
Diels-Alder precedent); no default profile is flipped.

## Deferred with evidence: #116 elimination is the Phase IV (#104) obstruction, not a Phase III generator

Elimination — dehydrohalogenation `R–CH₂–CH₂–X → R–CH=CH₂ + HX`, dehydration `R–CH₂–CH₂–OH → R–CH=CH₂ + H₂O` — is
representable in the neutral graph and conserves. But it does **not** fit a size-reducing (W1) retrosynthetic
generator in the direction issue #116 names, and the reason is a structure theorem, not an implementation gap:

> **An elimination synthesizes a SMALLER product (the alkene) from a LARGER precursor (the haloalkane/alcohol).**

Measured heavy-atom counts: 2-chloropropane (4 heavy) → propene (3) + HCl (1); ethanol (3 heavy) → ethene (2) +
H₂O. The retrosynthetic descent reduces atom count toward stock, so the *only* way an elimination bond-event enters
it is as the **decompile of the larger reactant** — and read backwards (the direction `search_routes` builds), that
step is an **addition** (hydrohalogenation / hydration `alkene + HX → haloalkane`), not an elimination. This is
exactly the obstruction Phase IV / issue #104 describes ("valid transformations whose precursor has equal or
greater atom count"), and it is the same dual the bond-order-edit module already documents: its decompile reading
is *dehydrogenation*, its synthesis reading is *hydrogenation*.

Consequently, "the route search makes alkenes via elimination" is **unreachable in 1.x** without the equal-or-
greater-precursor search Phase IV is chartered to build. A recognizer that fired only on decompile-direction
elimination steps would have no route-search consumer (the zero-consumers trap). Rather than ship a mislabelled
addition family calling it "elimination," or a recognizer nothing generates, #116 is deferred to Phase IV with this
evidence — the plan's "retain the empirical result rather than force a speculative redesign." Its natural home is
the bounded lateral/event search (the `(state, inventory, depth, lateral_hops, visited)` architecture) alongside
the [3,3]-sigmatropic families, where a non-strictly-descending event is representable.

## Deferred: #117 enolate C–C formation (aldol / Knoevenagel / Michael)

Deferred, consistent with the plan's own ordering (#117 is listed last and hedged as "the smallest genuinely sound
subset … if time permits"). Two specific hazards make it the least sound to rush, exactly the profile the prime
directive says to avoid:

1. **Shared reaction-center collision.** C–C bond formation is where enolate chemistry, cross-coupling, and other
   families collide on a byte-identical reaction centre — the recurring theme behind every false-VOUCH this project
   has caught. A sound aldol recognizer needs a positive structural-context lock separating it from those, not a
   "new C–C bond" census (the R55 escape-#7 trap).
2. **The charged-species temptation (#105).** The honest aldol/Michael mechanism runs through an enolate anion;
   representing it in the neutral graph risks a fake-neutral representation purely to inflate coverage, which the
   plan explicitly forbids ("Stage advanced Henry and ionic cases behind #105").

One fully sound family (imine) beats imine + a shaky aldol. #117 awaits its own soundness gate.

## Gate

Full OOM-safe suite and hosted CI on the final SHA; `experiments/imine_condensation_probe.py` frozen; no
golden/`semantic_digest` move (the oracle is a readiness demoter — a new recognizer lifts a demotion, it does not
move identity; the imine provider is opt-in and absent from the default algebra).
