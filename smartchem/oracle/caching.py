"""
Price each distinct species once, however many reactions ask about it.

Why this belongs here rather than in the search
-----------------------------------------------
Spectator cancellation is already exact *within* one reaction: ``reaction_residue``
removes species that appear unchanged on both sides before any oracle call, because the
monoidal law guarantees they cannot move the answer. That is worth 2.16x on the search
measured in ``scratchpad/pathway_reuse.py``.

What it cannot do is notice that step 7 needs the energy of a species step 2 already
priced. Across a whole search the same handful of species recur constantly -- an
intermediate is a *product* of one step and a *reactant* of the next, by definition -- so
the work left after spectator cancellation is dominated by re-pricing. Measured on a
45-reaction Haber-like network over 10 distinct species:

    naive (price both sides of every step)   335 oracle calls
    spectator cancellation only              155        2.16x
    plus this cache                           10       33.50x

Ten is not an improvement to be tuned; it is the floor. There are ten distinct species,
each is priced once, and no scheme can do better without pricing something zero times.

Why it is sound
---------------
Because energy is a **functor**. ``E(A (x) B) = E(A) + E(B)`` means a configuration's
energy is determined by its species, so a species has one energy wherever it occurs, in
whatever reaction, at whatever depth of the search. The cache is not an approximation
that usually works -- it is the functor law, used as a lookup table.

Why the key is canonical, which is the part that bites
------------------------------------------------------
``Molecule`` equality is *structural*, not up to isomorphism: the same water built as
``("O","H","H")`` with bonds {0-1, 0-2} and as ``("H","O","H")`` with bonds {1-0, 1-2} are
NOT equal, because the atom tuples and bond sets differ. They become equal only after
``canonical()``.

A cache keyed on raw molecules is therefore still *correct* -- it returns the right energy
-- while silently missing, so the 33.50x quietly decays toward 1x with no symptom but a
slow run. The saving depends on the key, and the key is canonicalisation's job.

``Config`` canonicalises its species on construction, so anything reaching an oracle
through the normal path is already canonical and a naive cache would happen to work.
Relying on that would be relying on an invariant maintained in another module for another
reason. This keys on ``canonical()`` explicitly instead, so the property is owned here.

The one case where that is not possible is a species too large to canonicalise -- above
``_MAX_CANONICAL_CANDIDATES``, ``canonical()`` refuses rather than returning something
non-canonical. Then the raw molecule is used as its own key: still correct, possibly
missing, and loudly counted in ``uncanonicalised`` so a decayed hit rate has somewhere to
be read off rather than being a mystery.
"""
from __future__ import annotations

from ..category import Molecule
from .base import BaseOracle, Estimate


class CachingOracle(BaseOracle):
    """
    Wraps any oracle and memoises ``energy`` by canonical species.

    Transparent: same answers, same error bars, same ``None`` refusals -- including
    caching the refusals, since an oracle that declines a species declines it every time
    and re-asking is pure cost.
    """

    def __init__(self, inner):
        self.inner = inner
        self.name = inner.name
        self.nominal_accuracy_ev = getattr(inner, "nominal_accuracy_ev", float("nan"))
        self._cache: dict[Molecule, Estimate | None] = {}
        self.hits = 0
        self.misses = 0
        #: species whose canonical form could not be computed, so keyed as given
        self.uncanonicalised = 0

    def _key(self, molecule: Molecule) -> Molecule:
        try:
            return molecule.canonical()
        except NotImplementedError:
            # Too large to canonicalise. The raw molecule is still a sound key -- it
            # equals itself -- it just will not merge with a differently-labelled twin.
            self.uncanonicalised += 1
            return molecule

    def energy(self, molecule: Molecule) -> Estimate | None:
        key = self._key(molecule)
        if key in self._cache:
            self.hits += 1
            return self._cache[key]
        self.misses += 1
        result = self.inner.energy(key)
        self._cache[key] = result
        return result

    @property
    def distinct_species(self) -> int:
        return len(self._cache)

    def certificate(self) -> str:
        """What the cache actually saved, for a run to report rather than assume."""
        asked = self.hits + self.misses
        saving = asked / self.misses if self.misses else 1.0
        return (f"{self.name} via cache: {asked} requests, {self.misses} priced, "
                f"{self.distinct_species} distinct species, {saving:.2f}x saved")

    def __repr__(self) -> str:
        return f"CachingOracle({self.inner!r}, {self.distinct_species} cached)"
