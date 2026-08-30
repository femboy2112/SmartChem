"""Cross-field coherence between the isomer-keyed data tables and the structure registry.

Hazards and thermochemistry are isomer-specific claims. Since isomer-keyed evidence landed, a formula
may carry SEVERAL records (ethanol and dimethyl ether both under C2H6O), and a record is attached to a
node by resolving that node's structure to a specific isomer NAME. That coupling is sound iff two
things hold, both guarded here: every record's name pins EXACTLY ONE registered isomer (so name -> one
structure), and the registered isomers of a formula have DISTINCT structure identities (so structure ->
one name). This is the repo's recurring "declarative auditor trusts the field it polices" lesson: a
record whose name matched zero or two structures, or two isomers that were secretly one graph, would
silently mislabel a chemist's hazards -- and these tests fire on exactly that.
"""

from collections import Counter

from smartchem.data.decompiler_thermo import DECOMPILER_THERMO, THERMO_GAPS
from smartchem.data.hazards import HAZARD_REFS
from smartchem.decompiler import Formula
from smartchem.structure import COMPOUND_REGISTRY, known_compounds


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

    def test_every_hazard_record_pins_exactly_one_registered_isomer_by_name(self):
        # isomer-keying makes attachment sound not by one-isomer-per-formula (the retired band-aid)
        # but by each record's NAME resolving to exactly one registered structure: structure -> name
        # -> record is then unambiguous even when a formula has several isomers.
        for ref in HAZARD_REFS:
            matches = [
                s for s in known_compounds(Formula.parse(ref.formula)) if ref.name in s.all_names
            ]
            assert len(matches) == 1, (
                f"hazard record {ref.formula}/{ref.name!r} must name exactly one registered isomer; "
                f"matched {[s.name for s in matches]}"
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

    def test_every_thermo_record_pins_exactly_one_registered_isomer_by_name(self):
        for ref in DECOMPILER_THERMO:
            matches = [
                s for s in known_compounds(Formula.parse(ref.formula)) if ref.name in s.all_names
            ]
            assert len(matches) == 1, (
                f"thermo record {ref.formula}/{ref.name!r} must name exactly one registered isomer; "
                f"matched {[s.name for s in matches]}"
            )


class TestRegisteredIsomersAreDistinct:
    def test_isomers_of_a_formula_have_distinct_structure_identities(self):
        # the whole scheme rests on structure -> ONE name: two 'isomers' that were secretly the same
        # graph would let a resolution pick the wrong record. Guard that no formula's isomers collide.
        for formula, structures in COMPOUND_REGISTRY.items():
            ids = Counter(s.structure_identity for s in structures)
            collisions = {i: c for i, c in ids.items() if c > 1}
            assert not collisions, (
                f"formula {formula!r} has isomers sharing a structure identity: a resolution could "
                f"not tell them apart"
            )


class TestGapsAndKeysAreWellFormed:
    def test_thermo_gap_keys_are_canonical_formulas(self):
        for key in THERMO_GAPS:
            assert repr(Formula.parse(key)) == key

    def test_a_formula_is_not_both_a_usable_value_and_a_documented_gap(self):
        # a composition claimed UNKNOWN in THERMO_GAPS must not also carry a stored usable value
        stored = {r.formula for r in DECOMPILER_THERMO}
        assert stored.isdisjoint(set(THERMO_GAPS))
