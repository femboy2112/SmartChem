# Lane F -- Independent Genericity Oracle: held-out SAPONIFICATION (blind prediction)

Blindness kept: I did NOT open capability/requirements.py, capability/assess.py, or any V0_9_RC_ROUND_*_AUDIT*.md.
What I read: procedure_evidence.py, experiment/stock.py, capability/profile.py, capability/enums.py,
CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md sections 4, 8 and 9, V0_9_CAPABILITY_COMPILER_PLAN_v0.1.md.

## 0. Source status
The case as specified is SYNTHESIZED. I treat all its numbers as the source's own. I looked for a public source
that matches it. The nearest real analogue is MiraCosta Chem 102 Exp. 8 (http://home.miracosta.edu/dlr/102exp8.htm).
I fetched it, and the fetch summary quotes these lines:
- "Prepare a mixture of 15 mL of 20% (5 M) sodium hydroxide and 10 mL of vegetable oil in a 150-mL flask."
- "Prepare a concentrated salt solution by dissolving 50 g of NaCl in 150 mL of distilled water"
- "Collect the precipitated soap on a Buchner funnel. Wash the soap twice with 10 mL of ice-cold distilled water."
- 30-45 min heating ("but it may take only 15-20 min"). There is NO ethanol and NO waste-disposal text.

This analogue gives three genericity probes of its own:
- (a) Its NaOH gives TWO bases, a % of unstated basis and a molarity. Neither may be derived from the other.
- (b) Its "concentrated" salt solution is a RECIPE (50 g in 150 mL), not a saturation state. It must not be
  collapsed into "saturated".
- (c) It names a Buchner funnel, so its filtration is VACUUM. The synthesized case only says "filter", so there
  the method is unspecified.
I did not use it to fill in the synthesized case.

## 1. Predicted requirement-side output, per material

Legend. Identity is STRUCT (a resolvable connected Molecule) or NAME (identity=None, name-keyed only).
Quantity state is EXACT, APPROX (an interval), LOWER_BOUND+UNKNOWN, or UNKNOWN.

| # | material (source text) | role | identity | quantity | specification | evidence |
|---|---|---|---|---|---|---|
| M1 | vegetable oil | SUBSTRATE | NAME (a mixture of triglycerides, so the identity cannot be resolved; no single Molecule may be invented, e.g. triolein) | APPROX ~5 mL (the "~" means it is not EXACT; `StockQuantity` can only express exact, so either a qualifier is added or it is None/UNKNOWN) | phase LIQUID; composition UNKNOWN (fatty-acid profile unstated) | source-authored, name only |
| M2 | 95% ethanol | SOLVENT (co-solvent; it is not a reactant) | STRUCT ethanol, plus water as the implied diluent | EXACT-as-given 10 mL | LIQUID; ethanol 0.95 with basis UNSTATED (the source does not say v/v); tolerance direction UNSTATED (the source does not say whether a floor or a band is meant) | source-authored |
| M3 | 6 M NaOH(aq) | REACTANT (stoichiometric base, used in excess) | NAME (ionic: [Na+].[OH-] is disconnected, so identity=None) | EXACT 10 mL | AQUEOUS_SOLUTION; NaOH 6 mol/L on an AMOUNT-CONCENTRATION basis (it is not a fraction, so it cannot go into a `MaterialComponent` [0,1]); dilution state is "aqueous, solvent = water" | source-authored |
| M4 | saturated NaCl solution | salting-out agent. The closed `ProcedureMaterialRole` has no fitting member. WASH is the nearest but it is wrong, because this agent precipitates the product rather than carrying impurities away. Either the vocabulary is honestly extended (e.g. PRECIPITANT/SALTING_OUT) or the misfit is recorded. It must never be REACTANT. | NAME (ionic) | EXACT 50 mL | AQUEOUS_SOLUTION; composition is a SATURATION STATE (solute NaCl, solvent water, temperature UNSTATED). No number such as 26.4% w/w or 5.4 M may be substituted | source-authored |
| M5 | ice-cold water | RINSE | STRUCT water | APPROX ~10 mL | LIQUID; grade UNSTATED (distilled vs tap); the temperature state "ice-cold" is a PROCESS demand (cooling / ICE_BATH), not a composition | source-authored |
| M6 | pH paper (verification) | no role in the vocabulary (indicator / consumable) | NAME | UNKNOWN | none | the method is outside the `MeasurementMethod` vocabulary |
| (products) | soap (a mixture of sodium carboxylates); glycerol byproduct | -- | NAME / STRUCT glycerol | UNKNOWN | -- | glycerol's fate is not assessed by the source |

Requirements that must be UNKNOWN (never FIT) against a typical lab or kitchen stock:
- M2 against "absolute ethanol" (>=99.5%). Both the basis and the tolerance direction are unstated. A 95% spec does
  not license 99.5%, and the compiler has no source-authored "or higher" to rely on, so UNKNOWN. In chemistry,
  absolute ethanol would work, but that is chemistry knowledge the generic compiler is forbidden to have.
- M3 against "NaOH pellets". The stock is SOLID while the requirement is AQUEOUS 6 mol/L, so the phases differ.
  Making the solution means dissolving to a molar target. That is a preprocessing transform the compiler must not
  invent, so the result is UNKNOWN or PREPROCESSING_REQUIRED (not FIT, and not BLOCKED either, because it is not
  provably impossible). A pellet assay in a mass fraction cannot be compared with a molarity at all.
- M4 against "table salt". The stock is SOLID and the requirement is a saturation state. Iodide or anti-caking
  additives are unknown. A saturated solution can be made from excess solid plus water, but only a source or stock
  declaration may author that fact. So UNKNOWN.
- M1 against any "vegetable oil" stock. Both sides are name-only. A name-string match is weak evidence and cannot
  verify composition. The strict answer is UNKNOWN. If an implementation FITs this, it must label the evidence
  strength NAME_DECLARED and say so. A FIT on a structure-matched basis would be a genericity bug.
- M6 / verification is UNKNOWN because the method cannot be represented. It must not become a silent
  NOT_APPLICABLE, and "lather test" must not be mapped to MASS.
- The FIT that IS allowed: M5 against a positively declared water stock (identity only, since the source states no
  grade), plus an ICE_BATH capability for the temperature.

### Waste obligations (source silent, so UNKNOWN; never AQUEOUS_NEUTRAL)
- W1: spent filtrate, which is aqueous ethanol (about 10 mL in about 70 mL, so roughly 13% v/v, which is
  flammable-adjacent) + excess NaOH (strongly alkaline, pH > 12) + NaCl + glycerol. It is ALKALINE and ETHANOLIC,
  so mapping it to AQUEOUS_NEUTRAL would be a false FIT. With no source disposal text, the verdict is UNKNOWN. The
  only thing that could make it FIT is a typed declaration of neutralize-then-drain, and the compiler may not
  derive neutralization on its own.
- W2: residual NaOH carried in the soap product. This is a hazard/verification obligation, tied to the pH test.
  It is not a waste stream, but it must stay open.
- W3: glycerol byproduct. Its fate is UNASSESSED, so it is UNKNOWN. It must never be dropped just because it
  "goes down the drain".
- W4: filter paper and residual soap solids. The source gives nothing, so UNKNOWN.

### Process demands
- HEAT on a WATER_BATH, T at or below ~373 K (the exact T is unstated); HOLD for 20-30 min, a PRESENT Interval.
  The endpoint is "until homogeneous", which is an observational endpoint.
- Agitation is continuous stirring, so attention is ACTIVE for at least the hold time.
- Whole-process elapsed time is LOWER_BOUND 20 min + UNKNOWN (cooling, salting-out, filtration and rinse times are
  unstated). It must not collapse to 30 min.
- Cooling: an ICE_BATH for the rinse water; cooling before salting is implied but unstated.
- Filtration: the method is UNSPECIFIED (gravity vs vacuum). The requirement should be a disjunction "any
  filtration". It is a genericity bug if the compiler picks VACUUM_FILTRATION (as the MiraCosta analogue would) or
  GRAVITY by default.
- Hazards that open up: NaOH 6 M is corrosive to skin and eyes, which needs PPE/containment. Ethanol is flammable
  and is being heated, so ventilation applies, but ventilation never substitutes for containment. No fume hood is
  source-mandated, so the compiler must not invent FUME_HOOD.
- Scale: ~5 mL oil gives a batch ~25 mL of liquids + 50 mL of brine. Quench is EXPLICIT_NOT_APPLICABLE only if the
  source says so; otherwise UNKNOWN. Separation is not applicable because there is no liquid-liquid step, but that
  still needs a source locator. Drying is UNKNOWN. Purification is none as stated, so it is UNKNOWN unless closed.

## 2. What an implementation will be tempted to hard-code, and the rule that forbids it
1. "95%" means v/v, or "95% ethanol" means the 95.6% azeotrope / 190 proof. Rule: a percentage of unknown basis
   stays unknown-basis. The basis is source-authored or UNSTATED.
2. Converting v/v to w/w or a mole fraction using an ethanol density table. Rule: no hidden physics in the
   compiler. A conversion must be typed, sourced evidence.
3. "M" means molar, so 6 M becomes a mass fraction via MW 40 and a solution density. Rule: molarity is its own
   basis. A cross-basis comparison is UNKNOWN unless a typed conversion is present.
4. "saturated" becomes 26.4% w/w / 36 g per 100 mL / 5.4 M. Rule: a saturation STATE is not a number. The
   compiler must not know what "saturated" means; the state is carried as a typed flag.
5. "ice-cold" becomes 273 K and an ICE_BATH via a prose scan. Rule: adjectives are authored into typed fields at
   the evidence origin, and the compiler never parses the formulation string. The same applies to "conc.",
   "glacial", "anhydrous", "neat", "aqueous" and "absolute".
6. The default phase of NaOH is SOLID; of NaCl solution, AQUEOUS; of ethanol, LIQUID. Rule: phase comes only from
   the source or stock declaration, otherwise Phase.UNKNOWN.
7. Hard-coded identities, e.g. `if name == "sodium hydroxide"`, a vegetable-oil = triolein Molecule, or water always
   FITs. Rule: no target or reagent identity is hard-coded in the compiler, and no Molecule is invented for a mixture.
8. Role inference, such as "NaOH is a base, therefore NEUTRALIZE" or "brine, therefore WASH". Rule: the role is
   what the source says. A misfit is recorded, not guessed.
9. Assuming a floor, "95% or better". Rule: tolerance semantics (FLOOR / BAND / POINT) are source-authored.
   Unstated means UNKNOWN when the stock differs.
10. A higher-assay stock satisfies a lower-assay spec (absolute ethanol for 95%, pellets for 6 M). Rule: this is
    formulation-to-identity collapse. The F43 band discipline applies.
11. Treating spent aqueous waste as AQUEOUS_NEUTRAL "because it is water". Rule: unknown is never safe, neutral or
    zero. The alkaline, ethanolic stream needs a typed disposal declaration.
12. The whole duration is the stated hold (20-30 min). Rule: a lower bound plus unknown stays a lower bound.
13. "filter" means Buchner/vacuum, or means gravity. Rule: an unspecified method is a disjunction, not a default.
14. The lather/pH tests map to an existing MeasurementMethod. Rule: an unrepresentable method gives UNKNOWN, not an
    invented mapping and not a silent N/A.
15. Using a household-product name as its composition: vodka means 40% v/v ethanol and water; drain cleaner means
    NaOH. Rule: the stock's composition is whatever the stock declaration types. Drain cleaner with undeclared
    components is [0,1] UNKNOWN.

## 3. Expected typed authoring (pseudo-data)
Minimal new types the contract forces. The existing `formulation: str` is display-only and never compared.

```python
class CompositionBasis(Enum): MASS_FRACTION; VOLUME_FRACTION; MOLE_FRACTION; AMOUNT_CONCENTRATION_MOL_PER_L;
                               MASS_CONCENTRATION_G_PER_L; UNSTATED
class Tolerance(Enum): POINT_AS_SOURCED  # no tolerance stated -> any different stock value is UNKNOWN
                       FLOOR; BAND
@dataclass(frozen=True) class CompositionClaim:
    component: Molecule | str          # structure key or declared name key (never mixed; stock.py rule)
    value: Interval                    # [lo, hi] in the basis' unit
    basis: CompositionBasis
    tolerance: Tolerance
@dataclass(frozen=True) class SaturationState:
    solute: Molecule | str; solvent: Molecule | str; temperature: Interval | None  # None = unstated
@dataclass(frozen=True) class QuantityClaim:
    value: Interval | None; unit: str; qualifier: EXACT | APPROXIMATE | LOWER_BOUND | UNKNOWN
@dataclass(frozen=True) class MaterialSpecification:
    phase: Phase                       # UNKNOWN unless authored
    composition: tuple[CompositionClaim, ...] = ()
    saturation: SaturationState | None = None
    diluent: Molecule | str | None = None
    grade: str | None = None           # opaque, compared only by exact declared equality, else UNKNOWN
    source_text: str                   # verbatim adjective, DISPLAY ONLY, never parsed
# ProcedureMaterialUse gains: specification: MaterialSpecification | None, quantity: QuantityClaim | None
```

```python
L = "synth-saponification:proc"
oil  = ProcedureMaterialUse("vegetable oil", SUBSTRATE, identity=None, evidence_source=L+"#1",
        specification=MaterialSpecification(phase=LIQUID, composition=(), source_text="vegetable oil"),
        quantity=QuantityClaim(Interval(4,6)?/None, "mL", APPROXIMATE))  # authoring the ~ band is itself a claim; if
                                                                        # the source gives no band: value=None, APPROXIMATE
etoh = ProcedureMaterialUse("95% ethanol", SOLVENT, identity=ETHANOL, evidence_source=L+"#1",
        specification=MaterialSpecification(phase=LIQUID,
          composition=(CompositionClaim(ETHANOL, Interval(0.95,0.95), UNSTATED, POINT_AS_SOURCED),),
          diluent=WATER, source_text="95% ethanol"),
        quantity=QuantityClaim(Interval(10,10), "mL", EXACT))
naoh = ProcedureMaterialUse("6 M NaOH", REACTANT, identity=None, evidence_source=L+"#1",
        specification=MaterialSpecification(phase=AQUEOUS_SOLUTION,
          composition=(CompositionClaim("sodium hydroxide", Interval(6,6), AMOUNT_CONCENTRATION_MOL_PER_L,
                                        POINT_AS_SOURCED),), diluent=WATER, source_text="6 M NaOH(aq)"),
        quantity=QuantityClaim(Interval(10,10), "mL", EXACT))
brine = ProcedureMaterialUse("saturated NaCl solution", <PRECIPITANT | WASH+recorded-misfit>, identity=None,
        evidence_source=L+"#3",
        specification=MaterialSpecification(phase=AQUEOUS_SOLUTION,
          saturation=SaturationState("sodium chloride", WATER, temperature=None), source_text="saturated NaCl"),
        quantity=QuantityClaim(Interval(50,50), "mL", EXACT))
rinse = ProcedureMaterialUse("ice-cold water", RINSE, identity=WATER, evidence_source=L+"#5",
        specification=MaterialSpecification(phase=LIQUID, composition=(), grade=None, source_text="ice-cold water"),
        quantity=QuantityClaim(None, "mL", APPROXIMATE))
# ice-cold is authored on the operation, not the material:
ops = (ADD(REACTION, uses=(oil, etoh, naoh)), HEAT/HOLD(apparatus=("water bath",), duration=present(Interval(20,30,'min')),
       agitation=present("stirring"), endpoint=present("homogeneous")), ADD(role=OTHER/WASH?, uses=(brine,)),
       FILTER(apparatus=()  # method unstated),
       ADD(WASH-role rinse, uses=(rinse,), temperature=present("ice-cold")),  # the T value is source text, NOT 273 K
       VERIFY(apparatus=() , endpoint=present("lather; pH paper")))
# whole-procedure: quench UNKNOWN; separation UNKNOWN (or N/A only with a locator); drying UNKNOWN;
# purification UNKNOWN; analytical_verification PRESENT; unresolved_omissions=("waste disposal",
#   "glycerol fate", "total elapsed time", "filtration method", "salting-out temperature", "95% basis")
```
Stock-side symmetry: `MaterialComponent` fractions carry no basis. So a basis-tagged requirement compared against
a basis-less stock fraction is UNKNOWN. A stock needs the same CompositionClaim/SaturationState typing to reach FIT.

## 4. Predicted verdicts

### (i) Fully stocked teaching lab, exactly matching positively-declared stock
The stock is: "vegetable oil" by name; 95% ethanol with the same UNSTATED basis and a point value; 6 M NaOH(aq)
with molar basis 6; saturated NaCl(aq) with the saturation state declared; distilled water. The lab has a water
bath, stirring, ice bath, both filtration kinds, PPE/containment, and pH paper.
- Material: M2, M3, M4 and M5 FIT, because the typed specifications are equal. M1 is UNKNOWN (strict) or FIT at
  NAME_DECLARED (lenient, but it must be labeled).
- Equipment: FIT on WATER_BATH, ICE_BATH and REACTION_VESSEL. Filtration FITs if the disjunction is used; if VACUUM
  is forced, that is a bug, even though a FIT would still result here.
- Process: FIT on the per-step hold of 20-30 min against the bounds. Whole-process duration is UNKNOWN (lower bound).
- Containment/hazard: FIT only against a positively declared corrosive-handling capability.
- Measurement: UNKNOWN (pH/lather is outside the method vocabulary).
- Waste: UNKNOWN (W1 alkaline ethanolic filtrate, W3 glycerol; the source is silent).
- OVERALL: UNKNOWN, not CAPABILITY_FIT and not BLOCKED. This matches the Round IV ceiling: the source
  under-specifies disposal and whole-process duration. A FIT overall would be a false-FIT signal.

### (ii) Kitchen with vodka (40% v/v), drain-cleaner NaOH, table salt
- M2 vodka. If the requirement basis is UNSTATED, the result is UNKNOWN (basis-incommensurable, and no conversion
  is allowed). If the source had authored VOLUME_FRACTION, vodka [0.40,0.40] is disjoint from 0.95, so
  INSUFFICIENT_ASSAY, which is BLOCKED on this axis. Prediction for the case as given: UNKNOWN. BLOCKED here would
  mean the implementation assumed v/v (temptation #1). Real-world truth: it is insufficient.
- M3 drain cleaner. Its composition is undeclared, NaOH in [0,1], and its phase is SOLID or UNKNOWN. That makes it
  UNKNOWN_ASSAY, so UNKNOWN; it also carries a phase mismatch and needs preprocessing.
- M4 table salt. SOLID against a saturation-state requirement, with additives undeclared, so UNKNOWN
  (preprocessing).
- M1 kitchen oil: the same as in (i), UNKNOWN or labeled name-level.
- M5 tap water: FIT on identity if declared as water (the source states no grade). "Ice-cold" is FIT via a declared
  freezer/ICE_BATH, otherwise UNKNOWN.
- Equipment: a pot water bath is FIT only if WATER_BATH is declared. Filtration is FIT if GRAVITY_FILTRATION (a
  coffee filter) is declared and the requirement is a disjunction. If VACUUM is forced it is BLOCKED, which is a
  genericity bug.
- Containment: corrosive 6 M NaOH needs a declared corrosive-handling/PPE capability, else UNKNOWN or BLOCKED per
  profile. Heating ethanol makes OUTDOOR ventilation relevant, but it never clears containment.
- Waste: UNKNOWN. Measurement: UNKNOWN.
- OVERALL: UNKNOWN, with no material axis FIT except water. BLOCKED overall only if some axis is PROVABLY unmet: a
  declared-absent heat source, or vodka with a source-authored v/v basis. It must never be FIT.

## 5. Probe checklist for the blind comparison
- P1: 95% basis surfaces as UNSTATED (not VOLUME_FRACTION).
- P2: 6 M is carried as a molar basis and never converted.
- P3: "saturated" is carried as a state, with no number.
- P4: vegetable oil has identity None and is never FIT at structure strength.
- P5: absolute ethanol / pellets / table salt / drain cleaner are all non-FIT.
- P6: vodka is UNKNOWN (BLOCKED only if v/v was authored).
- P7: the spent filtrate is not AQUEOUS_NEUTRAL, and glycerol is UNKNOWN.
- P8: the filtration method is not defaulted.
- P9: the whole-process duration is a lower bound or UNKNOWN.
- P10: the overall verdict is UNKNOWN in both worlds.
- P11: a grep of the compiler finds no "saponif", "ethanol", "NaOH", "saturated", "95" or "vodka" literals.
- P12: pH/lather are not mapped to MASS/MP/IR.
