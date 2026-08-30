"""M-4 v2: isomer-keyed evidence -- attach hazards/thermochemistry by STRUCTURE, not by formula.

Before this, a formula pinned at most one isomer's data, and a formula-level node was named/hazarded
with an ISOMER_ASSUMED caveat. Now a formula may carry several isomers (ethanol and dimethyl ether
both C2H6O; paracetamol and its O-acetyl ester both C8H9NO2), each with its OWN data, and:

* a structure resolution (`resolve_structure`) names the specific isomer and attaches its data;
* the formula-level path is honestly AMBIGUOUS where several isomers exist (no silent single pick);
* a structure-resolved review retires ISOMER_ASSUMED / ISOMER_AMBIGUOUS -- the isomer is KNOWN.

This is the keystone of Part 13's BUILD column: it retires the one-isomer-per-formula band-aid.
"""

from smartchem.category import Bond, Molecule
from smartchem.decompiler_review import (
    HazardFlag,
    molecule_dfh_0k_kj,
    molecule_hazards,
    molecule_name,
    review_capped_scission,
)
from smartchem.structure import known_compounds, resolve_structure
from smartchem.structure_descent import capped_scissions

WATER = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))


def _named(formula: str, name: str) -> Molecule:
    return next(s.molecule for s in known_compounds(formula) if s.name == name)


# ======================================================================================
# The C2H6O isomer pair: same formula, different data
# ======================================================================================
class TestEthanolVersusDimethylEther:
    def test_resolve_structure_names_each_isomer(self):
        assert molecule_name(_named("C2H6O", "ethanol")) == "ethanol"
        assert molecule_name(_named("C2H6O", "dimethyl ether")) == "dimethyl ether"

    def test_each_isomer_has_its_own_exact_enthalpy(self):
        # formula-level could only offer the [-217.1, -166.6] interval; structure gives the point.
        assert molecule_dfh_0k_kj(_named("C2H6O", "ethanol")) == -217.1
        assert molecule_dfh_0k_kj(_named("C2H6O", "dimethyl ether")) == -166.6

    def test_each_isomer_has_its_own_hazard_class(self):
        etoh = molecule_hazards(_named("C2H6O", "ethanol"))
        dme = molecule_hazards(_named("C2H6O", "dimethyl ether"))
        assert "H225" in etoh.ghs_codes and "LIQUID" in etoh.summary          # flammable liquid
        assert "H220" in dme.ghs_codes and "GAS" in dme.summary                # flammable gas
        assert etoh.ghs_codes != dme.ghs_codes                                 # genuinely different


# ======================================================================================
# The structure-resolved review retires the isomer caveats
# ======================================================================================
class TestStructureResolvedReview:
    def _hydrolysis(self):
        para = _named("C8H9NO2", "paracetamol")
        amino = known_compounds("C6H7NO")[0].molecule.canonical()
        acetic = known_compounds("C2H4O2")[0].molecule.canonical()
        edges, _ = capped_scissions(para, (WATER,))
        capped = next(
            e for e in edges if {p.canonical() for p in e.products} == {amino, acetic}
        )
        return review_capped_scission(capped)

    def test_naming_is_definitive_not_ambiguous(self):
        r = self._hydrolysis()
        named = r.named_equation()
        assert "C8H9NO2 (paracetamol)" in named        # the specific isomer, not "... or ..."
        assert " or " not in named

    def test_isomer_assumed_is_retired_when_structure_is_known(self):
        r = self._hydrolysis()
        # every named species is structure-resolved, so nothing is ASSUMED and nothing is AMBIGUOUS
        assert HazardFlag.ISOMER_ASSUMED not in r.hazard.flags
        assert HazardFlag.ISOMER_AMBIGUOUS not in r.hazard.flags

    def test_the_right_isomers_hazards_attach(self):
        r = self._hydrolysis()
        names = {h.name for h in r.hazard.species_hazards}
        assert {"paracetamol", "4-aminophenol", "acetic acid"} <= names
        assert HazardFlag.DOCUMENTED_HAZARD in r.hazard.flags

    def test_energetics_stay_honestly_unknown(self):
        # 4-aminophenol's sources still disagree; structure-keying does not conjure a number.
        r = self._hydrolysis()
        assert HazardFlag.ENERGETICS_UNKNOWN in r.hazard.flags


# ======================================================================================
# The exact-vs-interval contrast, through the review energy path
# ======================================================================================
class TestExactEnergyBeatsTheInterval:
    def test_structure_resolution_collapses_the_isomer_interval(self):
        # build a plain elemental-floor edge for C2H6O and score it two ways: formula-level gives an
        # interval (ISOMER_AMBIGUOUS), structure-resolved gives the exact ethanol value.
        from smartchem.decompiler import Formula, admissible_edges
        from smartchem.decompiler_review import assess_edge_energy

        edges, _ = admissible_edges(Formula.parse("C2H6O"))
        floor = next(e for e in edges if e.is_elemental_floor)
        formula_level = assess_edge_energy(floor)
        assert formula_level.assembly_lo_ev != formula_level.assembly_hi_ev   # an interval

        etoh = _named("C2H6O", "ethanol")
        resolved = assess_edge_energy(floor, structures={Formula.parse("C2H6O"): etoh})
        assert resolved.assembly_lo_ev == resolved.assembly_hi_ev             # a single exact value
        assert resolve_structure(etoh).name == "ethanol"
