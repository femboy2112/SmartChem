"""Cross-field coherence between the three formula-keyed tables and the structure registry.

Hazards and thermochemistry are keyed by FORMULA but are isomer-specific claims; the review layer
attaches them to a formula-level node on the strength of the structure registry resolving that formula
to one named compound. That coupling is only sound if the tables AGREE on which compound a formula is.
Nothing enforced that until here. This is the repo's recurring "declarative auditor trusts the field it
polices" lesson made into a guard: a hazard/thermo record whose name contradicts the registered isomer
would silently mislabel a chemist's hazards, and this test fires on exactly that.
"""

from smartchem.data.decompiler_thermo import DECOMPILER_THERMO, THERMO_GAPS
from smartchem.data.hazards import HAZARD_REFS
from smartchem.decompiler import Formula
from smartchem.structure import known_compounds


def _registered_names(formula_str: str) -> set[str]:
    """All names (common + synonyms + iupac) of every compound registered for a formula."""
    names: set[str] = set()
    for st in known_compounds(Formula.parse(formula_str)):
        names.update(st.all_names)
    return names


class TestHazardNamesMatchTheRegisteredIsomer:
    def test_every_hazard_record_agrees_with_the_structure_registry(self):
        for ref in HAZARD_REFS:
            registered = _registered_names(ref.formula)
            if registered:  # only where the registry actually pins an isomer
                assert ref.name in registered, (
                    f"hazard record {ref.formula} names {ref.name!r} but the structure registry "
                    f"resolves that formula to {registered}"
                )

    def test_a_hazard_formula_licences_attachment_by_pinning_exactly_one_isomer(self):
        # hazards_for is keyed by formula string and attaches by formula; that is only sound while a
        # formula resolves to ONE registered isomer. The day a second isomer is registered for a
        # hazard-keyed formula, this guard fires -- forcing an isomer-aware redesign, not a silent
        # mis-attachment (the crack the adversarial pass flagged).
        for ref in HAZARD_REFS:
            n = len(known_compounds(Formula.parse(ref.formula)))
            assert n <= 1, (
                f"formula {ref.formula} now has {n} registered isomers; a single formula-keyed "
                f"hazard record can no longer be attached unambiguously"
            )


class TestThermoNamesMatchTheRegisteredIsomer:
    def test_every_thermo_record_agrees_with_the_structure_registry(self):
        for ref in DECOMPILER_THERMO:
            registered = _registered_names(ref.formula)
            if registered:
                assert ref.name in registered, (
                    f"thermo record {ref.formula} names {ref.name!r} but the structure registry "
                    f"resolves that formula to {registered}"
                )

    def test_a_thermo_formula_licences_attachment_by_pinning_exactly_one_isomer(self):
        for ref in DECOMPILER_THERMO:
            n = len(known_compounds(Formula.parse(ref.formula)))
            assert n <= 1, (
                f"formula {ref.formula} now has {n} registered isomers; a single formula-keyed "
                f"thermo value can no longer be attached unambiguously"
            )


class TestGapsAndKeysAreWellFormed:
    def test_thermo_gap_keys_are_canonical_formulas(self):
        for key in THERMO_GAPS:
            assert repr(Formula.parse(key)) == key

    def test_a_formula_is_not_both_a_usable_value_and_a_documented_gap(self):
        # a composition claimed UNKNOWN in THERMO_GAPS must not also carry a stored usable value
        stored = {r.formula for r in DECOMPILER_THERMO}
        assert stored.isdisjoint(set(THERMO_GAPS))
