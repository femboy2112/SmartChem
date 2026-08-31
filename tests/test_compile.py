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

    def test_commodities_can_be_disabled(self):
        # with commodity termination OFF and no reagents, acetic anhydride cannot bottom out at commodities,
        # so its shopping list is empty (the flag genuinely gates termination)
        an = _mol("acetic anhydride")
        off = compile_synthesis(an, reagents=(), commodities=(), max_depth=1)
        assert off.shopping == ()


class TestLedgerHonesty:
    def test_ledger_is_always_present(self):
        cs = compile_synthesis(_mol("acetic anhydride"), reagents=(_mol("water"),), max_depth=2)
        assert cs.ledger  # never empty -- the scope is always stated
        assert any("commodity" in n.lower() for n in cs.ledger)
