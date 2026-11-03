"""CHEM-ALG-02 (#119): the carbonyl + amine -> imine condensation transform family -- a NEW generator.

The capped-scission family (:mod:`smartchem.structure_descent`) and the bond-order-edit family
(:mod:`smartchem.bond_order_edit`) both rewrite bonds the generator can reach by breaking ORDER-1 bonds and
capping the opened ends.  Neither can MINT or CLEAVE a C=N double bond, so the carbonyl <-> imine interconversion
-- a genuinely distinct transform family -- is simply absent from the generated algebra: a probe confirms that the
default registry, handed an imine and water, cuts the ADJACENT order-1 N-C bond into fictions
(``imine + water -> methane + formaldoxime``) and never produces the real ``carbonyl + amine`` retro.  This module
supplies that missing generator, registered through the TRANSFORM-PROVIDER-01 boundary so it composes through the
UNCHANGED bounded search (the Diels-Alder opt-in-provider precedent -- CHEM-ALG-01).

The DECOMPILE reading of an imine condensation edge is a **hydrolysis** (the microscopic reverse of the condensation):

    imine + water  ->  carbonyl + amine     (e.g.  N-methylmethanimine + H2O -> formaldehyde + methylamine)

Read backwards by :meth:`~smartchem.experiment.step.ExperimentStep.from_transform`, this is the SYNTHESIS step the
recompiler reads -- the **Schiff-base condensation** ``carbonyl + amine -> imine + water`` (the water a liberated
byproduct, exactly as capped scission liberates its coproduct).  The N-substituent generalises the amine donor over
the plan's imine / oxime / hydrazone subset: a C in {C, H} N-neighbour gives an aldimine/ketimine from a primary
amine (or ammonia, when the imine N bears only H), an O gives an oxime from hydroxylamine, an N gives a hydrazone
from a hydrazine.

The rewrite is VALENCE-PRESERVING atom-by-atom (the carbonyl carbon trades =N for =O; the nitrogen trades =C for
two N-H; the water oxygen trades two O-H for =C), so it satisfies the same structural-teeth discipline as a capped
scission -- the capped-scission ENUMERATOR merely never reaches it (order-1 cuts only).  The family is neutral and
its products are stable closed molecules (a carbonyl and an amine, not ions), so it composes cleanly into a retro
route/DAG search that terminates at stock, forgetting to a :class:`~smartchem.decompiler_mediated.MediatedEdge`.

W3 unchanged: an imine-condensation edge certifies that such a valence-preserving C=N condensation EXISTS, never
that it runs or under what conditions (imine formation is reversible and acid-catalysed -- a feasibility matter,
Problem B, deferred).  Absent a sourced conditions record it stays a ``FORMAL_CANDIDATE``, gated by the same
evidence machinery as every other family.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Config, ConservationError, Molecule, Reaction
from .contracts import Digestible, canonical_digest
from .decompiler import Formula
from .decompiler_mediated import MediatedEdge
from .diels_alder import is_closed_shell_neutral
from .structure_descent import ScissionError
from .transform_provider import ProviderUse, TransformProvider

__all__ = [
    "IMINE_CONDENSATION_SCHEMA",
    "ImineCondensationEdge",
    "imine_condensations",
    "ImineCondensationProvider",
]

IMINE_CONDENSATION_SCHEMA = "smartchem.imine-condensation/schiff-base-v1"

#: the carbonyl carbon's OTHER (non-nitrogen) neighbours: an aldimine/ketimine carbon bears only C/H besides the
#: =N (so the retro gives a plain aldehyde/ketone).  A carbon also bonded to an extra O or N is an amidine / imidate
#: / guanidine centre -- a DIFFERENT functional group whose hydrolysis is not a simple carbonyl + amine, EXCLUDED.
_CARBONYL_CARBON_NEIGHBOURS = frozenset({"C", "H"})
#: the imine nitrogen's single (non-double-bond) substituent: C/H -> amine or ammonia (the imine/Schiff-base core),
#: O -> hydroxylamine (oxime), N -> hydrazine (hydrazone).  The plan's imine/oxime/hydrazone subset.
_AMINE_NITROGEN_SUBSTITUENTS = frozenset({"C", "H", "O", "N"})

_WATER_CACHE: list = []


def _water() -> Molecule:
    """A cached neutral water molecule, the condensation coproduct the retro consumes (internally supplied, so the
    family is reagentless -- it needs no water in the pool; read backwards the water is a liberated byproduct)."""
    if not _WATER_CACHE:
        from .smiles import parse_smiles
        _WATER_CACHE.append(parse_smiles("O"))
    return _WATER_CACHE[0]


def _bond(a: int, b: int, order: int):
    from .category import Bond
    return Bond(min(a, b), max(a, b), order)


def _components(n: int, bonds) -> list[tuple[int, ...]]:
    """Connected components of the ``n``-atom graph with edge set ``bonds`` (union-find)."""
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for b in bonds:
        parent[find(b.i)] = find(b.j)
    groups: dict[int, list[int]] = {}
    for v in range(n):
        groups.setdefault(find(v), []).append(v)
    return [tuple(g) for g in groups.values()]


def _fragment(atoms: tuple[str, ...], comp: tuple[int, ...], bonds) -> Molecule:
    """The canonical product Molecule for one connected component ``comp`` of the rewired graph."""
    local = {a: k for k, a in enumerate(comp)}
    frag_atoms = tuple(atoms[a] for a in comp)
    frag_bonds = frozenset(
        _bond(local[b.i], local[b.j], b.order) for b in bonds if b.i in local and b.j in local
    )
    return Molecule(frag_atoms, frag_bonds, 0, "").canonical()


@dataclass(frozen=True)
class ImineCondensationEdge(Digestible):
    """One carbonyl <-> imine condensation, as the DECOMPILE (hydrolysis) ``imine + water -> carbonyl + amine``.

    The object IS the plan (the imine reactant and the ``(cn_c, cn_n)`` C=N bond it hydrolyses); the water reagent
    and the carbonyl/amine products are DERIVED by the valence-preserving rewrite, so there is nothing to lie about.
    The constructor is the certificate, all of it recomputed from the stored molecule:

    * the ``(cn_c, cn_n)`` bond is a genuine imine ``C=N`` (order 2, a carbon double-bonded to a nitrogen);
    * the carbonyl carbon bears, besides the ``=N``, only single bonds to C/H (an aldimine/ketimine -- NOT an
      amidine/imidate whose extra alpha-O/N makes its hydrolysis a different class);
    * the nitrogen is a neutral imine N (valence 3: the ``=C`` plus EXACTLY one single bond to a C/H/O/N
      substituent -- so the retro restores a primary amine / hydroxylamine / hydrazine / ammonia; an iminium
      N at valence 4 is excluded);
    * the rewrite (break ``C=N`` and the two water ``O-H``; form ``C=O`` and two ``N-H``) is VALENCE-PRESERVING at
      every atom, yields EXACTLY two closed products, each strictly smaller than the imine (W1 descent) and neither
      an unconsumed water, and the whole step CONSERVES mass/charge (independently, via :class:`Reaction`).

    A cyclic imine (the ``C=N`` in a ring) would rewire into ONE ring-opened molecule, not two, and is refused here
    -- the condensation shape is intermolecular (two precursors), and the intramolecular case is a separate family.
    """

    schema_version: str
    reactant: Molecule
    cn_c: int
    cn_n: int

    def __post_init__(self) -> None:
        if self.schema_version != IMINE_CONDENSATION_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {IMINE_CONDENSATION_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a smartchem.category.Molecule")
        if self.reactant.charge != 0 or not is_closed_shell_neutral(self.reactant):
            raise ScissionError("imine condensation supports closed-shell neutral species only")
        # ABSOLUTE-VALENCE PIN (own gate, not an upstream accident).  The derived carbonyl fragment is the ONE
        # product that receives none of water's explicit hydrogens, so were it ever read in a heavy-atom-only
        # representation, ``is_closed_shell_neutral``'s LENIENT implicit-H branch (``degree <= max`` -- see its
        # documented blind spots) could admit a radical carbon.  Requiring the reactant to carry EXPLICIT hydrogens
        # forces the STRICT per-atom-valence branch over it, which verifies every heavy atom exactly; since the
        # rewrite changes only the C=N->C=O (same order) and adds two N-H from water, every other product atom keeps
        # its strict-verified reactant valence.  So the edge's closed-shell soundness no longer depends on the
        # caller having routed through ``ExperimentStep``'s conservation certificate (which forces explicit-H today):
        # a future provider path that skips it cannot open this soft spot.  Honest coverage loss (a heavy-only
        # input is refused), never a false-vouch.  [[a-rederivation-via-a-valence-preserving-rewrite-needs-its-own-absolute-gate]]
        if "H" not in self.reactant.atoms:
            raise ScissionError(
                "imine condensation requires an explicit-hydrogen representation (forces strict per-atom valence; "
                "a heavy-atom-only graph is refused so no radical rides the lenient implicit-H branch)"
            )
        for name in ("cn_c", "cn_n"):
            if type(getattr(self, name)) is not int:
                raise ScissionError(f"{name} must be an int atom index")
        atoms = self.reactant.atoms
        n = len(atoms)
        if not (0 <= self.cn_c < n and 0 <= self.cn_n < n and self.cn_c != self.cn_n):
            raise ScissionError("cn_c and cn_n must be distinct in-range atom indices")
        if atoms[self.cn_c] != "C" or atoms[self.cn_n] != "N":
            raise ScissionError("the C=N bond must join a carbon (cn_c) and a nitrogen (cn_n)")
        cn_pair = {self.cn_c, self.cn_n}
        cn_bond = next((b for b in self.reactant.bonds if {b.i, b.j} == cn_pair), None)
        if cn_bond is None or cn_bond.order != 2:
            raise ScissionError("(cn_c, cn_n) is not an order-2 C=N bond of the reactant")
        # -- the carbonyl-carbon gate: besides the =N, only single bonds to C/H (an aldimine/ketimine) ----------
        c_incident = [b for b in self.reactant.bonds if self.cn_c in (b.i, b.j)]
        c_degree = sum(b.order for b in c_incident)
        if c_degree != 4:
            raise ScissionError("the imine carbon must be tetravalent (a closed-shell sp2 carbonyl precursor)")
        for b in c_incident:
            if {b.i, b.j} == cn_pair:
                continue
            other = atoms[b.j if b.i == self.cn_c else b.i]
            if b.order != 1 or other not in _CARBONYL_CARBON_NEIGHBOURS:
                raise ScissionError(
                    "the imine carbon bears a non-(C/H) or multiple bond besides the =N (amidine/imidate/vinyl -- "
                    "not a simple carbonyl + amine condensation)"
                )
        # -- the nitrogen gate: valence 3 = the =C plus EXACTLY one single bond to a C/H/O/N substituent ---------
        n_incident = [b for b in self.reactant.bonds if self.cn_n in (b.i, b.j)]
        if sum(b.order for b in n_incident) != 3:
            raise ScissionError("the imine nitrogen must be a neutral valence-3 N (an iminium N=4 is excluded)")
        singles = [b for b in n_incident if {b.i, b.j} != cn_pair]
        if len(singles) != 1 or singles[0].order != 1:
            raise ScissionError("the imine nitrogen must bear exactly one single-bond substituent besides the =N")
        sub_idx = singles[0].j if singles[0].i == self.cn_n else singles[0].i
        sub = atoms[sub_idx]
        if sub not in _AMINE_NITROGEN_SUBSTITUENTS:
            raise ScissionError(f"the imine nitrogen substituent {sub!r} is not an amine/oxime/hydrazone donor")
        # N-ACYL EXCLUSION (the MIRROR of the carbonyl-carbon alpha-heteroatom guard above).  The nitrogen donor
        # must be a TRUE amine / hydroxylamine / hydrazine, not an amide / urea / carbamate / thioamide / amidine:
        # an N-acyl(-type) imine's retro-hydrolysis is carbonyl + AMIDE, "a different functional group whose
        # hydrolysis is not a simple carbonyl + amine" -- the exact sin excluded on the carbon axis.  Checking the
        # substituent ELEMENT alone (C/H/O/N) left this leak open: an amide/urea/carbamate donor rode through as
        # "carbonyl + amine" (formaldehyde + urea, acetaldehyde + acetamide -- an N-side false-vouch).  Reject when
        # the nitrogen-substituent CARBON bears a double(+) bond to a heteroatom (C=O / C=N / C=S), which is what
        # distinguishes an acyl/amidino/thioacyl donor from a genuine amine carbon -- an sp3 alkyl, an aryl (aniline:
        # N-aryl Schiff base, its ring double bonds are to CARBON), or a vinyl carbon all pass.  A hydrazide/
        # hydroxylamine donor (substituent N or O, e.g. an acylhydrazide) is a legitimate hydrazone/oxime donor and
        # is unaffected; only the CARBON substituent carries this guard.
        if sub == "C":
            for nb in self.reactant.bonds:
                if sub_idx in (nb.i, nb.j) and nb.order >= 2:
                    other = atoms[nb.j if nb.i == sub_idx else nb.i]
                    if other in ("O", "N", "S"):
                        raise ScissionError(
                            "the nitrogen donor is an amide/carbamate/urea/amidine (an acyl/imino carbon on N); its "
                            "hydrolysis is carbonyl + amide, not carbonyl + amine -- excluded (mirror of the "
                            "carbonyl-carbon alpha-heteroatom guard)"
                        )
        # force the products (the rewrite + its conservation certificate).
        products = self.products
        if len(products) != 2:
            raise ScissionError("an imine condensation hydrolyses into exactly the carbonyl and the amine")
        if any(not is_closed_shell_neutral(p) for p in products):
            raise ScissionError("a hydrolysis product is not closed-shell neutral")
        n_react = len(self.reactant.atoms)
        if any(len(p.atoms) >= n_react for p in products):
            raise ScissionError("every product must have strictly fewer atoms than the imine (W1 descent)")
        water_canon = _water().canonical()
        if any(p.canonical() == water_canon for p in products):
            raise ScissionError("a product is an unconsumed water (pass-through); the water must be consumed")
        try:
            Reaction(Config.of(self.reactant, *self.reagents), Config.of(*products), name="imine-condensation")
        except ConservationError as clash:
            raise ScissionError(f"imine condensation does not conserve mass/charge: {clash}") from clash

    @property
    def reagents(self) -> tuple:
        """The consumed coproduct: one water (internally supplied -- the family needs none in the pool)."""
        return (_water(),)

    def _rewired(self) -> tuple[tuple[str, ...], frozenset, int]:
        """The joined (imine + water) atom list and the rewired bond set: break C=N + the two O-H, form C=O + two
        N-H.  Returns ``(atoms, bonds, n)``."""
        water = _water()
        n = len(self.reactant.atoms)
        atoms = self.reactant.atoms + water.atoms
        # water indices offset by n; water is ('H','H','O') -> H at n, n+1; O at n+2
        w_h = [n + k for k, a in enumerate(water.atoms) if a == "H"]
        w_o = next(n + k for k, a in enumerate(water.atoms) if a == "O")
        cn_pair = {self.cn_c, self.cn_n}
        bonds = {b for b in self.reactant.bonds if {b.i, b.j} != cn_pair}  # drop the C=N
        # water's own O-H bonds are simply not carried over (the two H's are rewired to N, the O to C)
        bonds.add(_bond(self.cn_c, w_o, 2))       # new carbonyl C=O
        bonds.add(_bond(self.cn_n, w_h[0], 1))    # new N-H
        bonds.add(_bond(self.cn_n, w_h[1], 1))    # new N-H
        return atoms, frozenset(bonds), n + len(water.atoms)

    @property
    def products(self) -> tuple[Molecule, ...]:
        """The derived, canonical carbonyl and amine, sorted deterministically."""
        atoms, bonds, n = self._rewired()
        mols = [_fragment(atoms, comp, bonds) for comp in _components(n, bonds)]
        return tuple(sorted(mols, key=lambda m: (len(m.atoms), repr(m))))

    def forget(self) -> MediatedEdge:
        """The forgetful image: the composition-level :class:`MediatedEdge` ``imine + water -> carbonyl + amine``."""
        def _f(m: Molecule) -> Formula:
            return Formula.of(m.formula, m.charge)

        def _merge(mols) -> tuple[tuple[Formula, int], ...]:
            counts: dict[Formula, int] = {}
            for m in mols:
                f = _f(m)
                if f.is_element:
                    (symbol, count), = f.counts
                    bucket = Formula.bucket(symbol)
                    counts[bucket] = counts.get(bucket, 0) + count
                else:
                    counts[f] = counts.get(f, 0) + 1
            return tuple(sorted(counts.items(), key=lambda pm: ((pm[0].counts, pm[0].charge), pm[1])))

        return MediatedEdge(_f(self.reactant), 1, _merge(self.reagents), _merge(self.products))

    def equation(self) -> str:
        rhs = " + ".join(repr(p) for p in self.products)
        return f"{self.reactant!r} + {self.reagents[0]!r} --hydrolyse[C{self.cn_c}=N{self.cn_n}]--> {rhs}"

    def __repr__(self) -> str:
        return f"ImineCondensationEdge({self.equation()})"


def imine_condensations(reactant: Molecule, *, budget: int = 50_000) -> tuple[tuple[ImineCondensationEdge, ...], bool]:
    """Enumerate the imine-condensation hydrolyses of ``reactant`` (one per hydrolysable ``C=N``).

    Deduplicated by the produced ``(carbonyl, amine)`` pair, canonical order.  Returns ``(edges, complete)``;
    ``complete`` is ``False`` iff ``budget`` was hit.  Never raises on a molecule with no hydrolysable C=N -- it
    returns ``((), True)``."""
    if type(reactant) is not Molecule:
        raise TypeError("reactant must be a smartchem.category.Molecule")
    if reactant.charge != 0:
        return (), True
    atoms = reactant.atoms
    out: dict[str, ImineCondensationEdge] = {}
    work = 0
    for b in sorted(reactant.bonds):
        if b.order != 2:
            continue
        pair = {atoms[b.i], atoms[b.j]}
        if pair != {"C", "N"}:
            continue
        cn_c, cn_n = (b.i, b.j) if atoms[b.i] == "C" else (b.j, b.i)
        work += 1
        if work > budget:
            return tuple(sorted(out.values(), key=lambda e: e.digest)), False
        try:
            edge = ImineCondensationEdge(IMINE_CONDENSATION_SCHEMA, reactant, cn_c, cn_n)
        except ScissionError:
            continue
        key = canonical_digest(tuple(canonical_digest(p) for p in edge.products))
        out.setdefault(key, edge)
    return tuple(sorted(out.values(), key=lambda e: e.digest)), True


@dataclass(frozen=True)
class ImineCondensationProvider(TransformProvider):
    """The imine-condensation family as an OPT-IN typed provider (#119, absent from the default registry -- the
    Diels-Alder precedent).  Reagentless (it supplies its own water, so it ignores the reagent pool) and neutral;
    rides the route/DAG seam with zero changes to shared machinery and asserts structural type-validity only."""

    provider_id: str = "imine-condensation"
    provider_version: str = "v1"
    witness_kind: str = "IMINE_CONDENSATION"
    # neutral, size-reducing (the imine disconnects into two smaller fragments, water consumed), route/DAG-admissible.
    # Like the DA families, its witness_kind has no IR _WITNESS_PROJECTION entry, so it is NOT a STRUCTURE_DECOMPILE
    # provider -- it rides search_routes via forget()/from_transform, and the oracle recognises its synthesis steps.
    supported_uses = frozenset({ProviderUse.LINEAR_ROUTE, ProviderUse.CONVERGENT_DAG})

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", "imine-condensation"),
            ("mechanism", "carbonyl + amine -> imine + water (Schiff-base condensation), neutral, water self-supplied"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "MEDIATED_EDGE"),
            ("state_domain", "neutral-closed-shell-only"),
            ("chemical_authority", "structural-type-validity-only-problem-A"),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        # reagentless: the reagent pool is ignored (water is supplied internally).
        return imine_condensations(reactant, budget=budget)
