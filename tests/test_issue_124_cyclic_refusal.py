"""ISSUE #124: an ancestor precursor must not be silently treated as stocked (phantom self-supply).

Both route searchers computed the still-needed precursors as
``[m for k, m in distinct.items() if k not in on_hand and k not in ancestors]`` -- a precursor that is one of
the branch's OWN ancestors was dropped from ``missing`` and the branch treated as complete. Under the W1
strict-rank capped-scission grammar an ancestor can never reappear as a precursor, so the clause was dead; but
with a rank-flat / REVERSIBLE provider (what #104/#123 would add) a backwards cycle A <- B <- A becomes a
"complete" route with NO external feed -- a phantom self-supply (which then crashes the linearity invariant).

The fix refuses the cyclic branch instead of folding the ancestor into "available". This test uses a minimal
deterministic reciprocal fake provider (A <-> B isomerization) to drive the otherwise-unreachable case, and pins:
  * an UNSTOCKED reversible search returns NO route/DAG (no self-supplying closed path, no crash);
  * a STOCKED positive control still returns a route (the provider genuinely works -- the empty case is not vacuous);
  * the guard is a no-op on the real W1 grammar (a capped-scission search is unaffected).
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from smartchem.decompiler import Formula
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import TransformProvider, TransformProviderRegistry, ProviderUse
from smartchem.experiment.routes import search_routes, search_dags, _ident, DEFAULT_TRANSFORM_REGISTRY

ETHANOL = parse_smiles("CCO")          # C2H6O
DME = parse_smiles("COC")              # C2H6O: a constitutional isomer -- the rank-flat reciprocal partner
_PARTNER = {_ident(ETHANOL): DME, _ident(DME): ETHANOL}   # key on CONSTITUTION, not the formula repr


@dataclass(frozen=True)
class _ReversibleTransform:
    reactant: object
    products: tuple
    reagents: tuple = ()

    @property
    def digest(self) -> str:
        return f"reversible:{_ident(self.reactant)}->{_ident(self.products[0])}"

    def forget(self):
        # minimal edge-like for the condition-seed lookup (_reaction_signature reads Formula sides)
        return SimpleNamespace(
            reactant=Formula.of(self.reactant.formula, self.reactant.charge), reactant_multiplicity=1,
            reagents=(), products=[(Formula.of(p.formula, p.charge), 1) for p in self.products])


@dataclass(frozen=True)
class _ReciprocalProvider(TransformProvider):
    """A fake rank-flat family offering A->B and B->A, the reversible case W1 precludes today."""
    provider_id: str = "reciprocal-isomerization-TEST"
    provider_version: str = "v0"
    witness_kind: str = "RECIPROCAL_TEST"
    supported_uses = frozenset({ProviderUse.LINEAR_ROUTE, ProviderUse.CONVERGENT_DAG})

    @property
    def capability_manifest(self) -> tuple:
        return (("family", "reciprocal-isomerization-TEST"),
                ("mechanism", "rank-flat reversible isomerization (test fixture)"),
                ("witness_kind", self.witness_kind), ("projection_kind", "NONE"))

    def enumerate_transforms(self, reactant, reagents, *, budget):
        partner = _PARTNER.get(_ident(reactant))
        if partner is None:
            return (), True
        return (_ReversibleTransform(reactant, (partner,)),), True


_REG = TransformProviderRegistry((_ReciprocalProvider(),))


def test_unstocked_reversible_search_refuses_the_phantom_cycle():
    # no external stock: A can only be "made" from B which can only be "made" from A -- a closed self-supply.
    # It must yield NOTHING (and must not raise), not a phantom route.
    linear = search_routes(ETHANOL, registry=_REG, reagents=(), available=(), max_depth=6, max_routes=10)
    assert linear.routes == ()
    assert linear.receipt.status.value == "COMPLETE_WITHIN_BOUNDS"
    dag = search_dags(ETHANOL, registry=_REG, reagents=(), available=(), max_depth=6, max_dags=10)
    assert dag.dags == ()
    assert dag.receipt.status.value == "COMPLETE_WITHIN_BOUNDS"


def test_stocked_positive_control_still_finds_a_route():
    # with the reciprocal partner available as external stock, the ONE-step route A-from-B is found -- proving
    # the fake provider works and the empty unstocked result above is a genuine refusal, not a broken fixture.
    linear = search_routes(ETHANOL, registry=_REG, reagents=(), available=(DME,), max_depth=6, max_routes=10)
    assert len(linear.routes) >= 1
    # the one step consumes the STOCKED partner, not an ancestor conjured out of the cycle
    step = linear.routes[0].steps[-1]
    assert any(_ident(m) == _ident(DME) for m in step.reactants)


def test_the_cyclic_guard_is_a_noop_on_the_w1_capped_scission_grammar():
    # the real W1 grammar never produces a back-edge, so the guard changes nothing: a stocked capped-scission
    # route search still returns its routes.
    target = parse_smiles("CCOC(C)=O")         # ethyl acetate
    res = search_routes(target, registry=DEFAULT_TRANSFORM_REGISTRY,
                        reagents=(parse_smiles("O"),),
                        available=(parse_smiles("CCO"), parse_smiles("CC(=O)O")), max_depth=3, max_routes=10)
    assert len(res.routes) >= 1
