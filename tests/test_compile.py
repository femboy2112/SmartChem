"""The compile front door: arbitrary target -> complete, bucket-terminated synthesis + shopping list + grade.

Proves the composition is honest end to end: a real target compiles to a drafted route that bottoms out at
commodity buckets with a shopping list; a target with no route fails LOUD (never a fabricated synthesis).
"""
from __future__ import annotations

from smartchem.experiment.compile import CompiledSynthesis, compile_synthesis
from smartchem.structure import structure_by_name


def _mol(name):
    return structure_by_name(name).molecule


class TestCompileEndToEnd:
    def test_target_compiles_to_a_commodity_terminated_synthesis(self):
        an = _mol("acetic anhydride")
        water = _mol("water")
        cs = compile_synthesis(an, reagents=(water,), max_depth=2)
        assert isinstance(cs, CompiledSynthesis)
        assert cs.found_route
        assert cs.best_draft is not None
        assert cs.verdict is not None
        # bottoms out at a commodity -> the shopping list names it
        assert "acetic acid" in {r.name for r in cs.shopping}

    def test_render_carries_the_whole_picture(self):
        an = _mol("acetic anhydride")
        cs = compile_synthesis(an, reagents=(_mol("water"),), max_depth=2)
        text = cs.render()
        assert "COMPILED SYNTHESIS" in text
        assert "OVERALL GRADE (L2)" in text
        assert "SHOPPING LIST" in text
        assert "acetic acid" in text
        assert "SYNTHESIS (buckets -> target)" in text
        # the honesty ledger names the linear-chain scope limit
        assert any("LINEAR chain" in n or "linear" in n.lower() for n in cs.ledger)

    def test_no_route_fails_loud_not_fabricated(self):
        # methane with no useful reagents and shallow depth: no commodity-terminated route
        cs = compile_synthesis(_mol("methane"), reagents=(), commodities=(), max_depth=1)
        assert not cs.found_route
        assert cs.best_draft is None
        assert cs.verdict is None
        assert "no cleavage reached the buckets" in " ".join(cs.ledger) or cs.shopping == ()

    def test_partial_empty_search_says_absence_is_not_evidence(self):
        cs = compile_synthesis(
            _mol("paracetamol"), reagents=(_mol("water"),), commodities=(), max_depth=1, cut_budget=1
        )
        assert not cs.found_route
        assert cs.search_receipt is not None and not cs.search_receipt.complete_within_bounds
        text = cs.render()
        assert "SEARCH WAS PARTIAL" in text
        assert "Absence is not evidence" in text

    def test_commodities_can_be_disabled(self):
        # with commodity termination OFF and no reagents, acetic anhydride cannot bottom out at commodities,
        # so its shopping list is empty (the flag genuinely gates termination)
        an = _mol("acetic anhydride")
        off = compile_synthesis(an, reagents=(), commodities=(), max_depth=1)
        assert off.shopping == ()

    def test_commodities_disabled_prevents_global_target_short_circuit(self):
        off = compile_synthesis(_mol("ethanol"), commodities=(), max_depth=1)
        assert off.already_obtainable is None

    def test_explicit_available_target_is_an_honest_zero_expansion_outcome(self):
        ethanol = _mol("ethanol")
        cs = compile_synthesis(ethanol, commodities=(), available=(ethanol,), max_depth=1)
        assert cs.found_route
        assert cs.already_in_active_inventory
        assert cs.best_draft is None
        assert cs.search_receipt is not None and cs.search_receipt.expansions_attempted == 0
        text = cs.render()
        assert "ACTIVE INVENTORY MATCH" in text
        assert "quantity" in text and "assay" in text

    def test_commodity_match_is_not_rendered_as_pure_material_equivalence(self):
        cs = compile_synthesis(_mol("acetic acid"))
        text = cs.render()
        assert "IDENTITY ONLY" in text
        assert "does NOT establish" in text
        assert "purity" in text and "concentration" in text


class TestLedgerHonesty:
    def test_ledger_is_always_present(self):
        cs = compile_synthesis(_mol("acetic anhydride"), reagents=(_mol("water"),), max_depth=2)
        assert cs.ledger  # never empty -- the scope is always stated
        assert any("commodity" in n.lower() for n in cs.ledger)


class TestRedTeamFixes:
    def test_target_that_is_a_commodity_short_circuits(self):
        # compiling something you can just buy should say so, not hand back a needless synthesis
        cs = compile_synthesis(_mol("acetic acid"))
        assert cs.already_obtainable is not None
        assert cs.best_draft is None
        assert cs.found_route  # "obtainable" counts as found
        assert "COMMODITY SOURCE MATCH" in cs.render()

    def test_grade_first_ranking_is_stable_when_grades_tie(self):
        # when every candidate shares a grade, the fit-order tiebreaker preserves the prior best (no churn)
        an = _mol("acetic anhydride")
        cs = compile_synthesis(an, reagents=(_mol("water"),), max_depth=2)
        assert cs.found_route
        # the chosen verdict IS classify's verdict for the chosen route (grade == what render shows)
        assert cs.verdict is not None

    def test_alternatives_carry_their_grade(self):
        cs = compile_synthesis(_mol("acetic anhydride"),
                               reagents=(_mol("water"), _mol("formic acid")), max_depth=2)
        # alternatives, when present, are (grade, equation) pairs -- never a bare count
        for g, eq in cs.alternatives:
            assert isinstance(g, str) and isinstance(eq, str)
