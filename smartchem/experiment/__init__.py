"""M-5 -- the Experiment Compiler: a decompiler route, verified and drafted as a runnable experiment.

The decompiler (``smartchem.structure_descent`` / ``smartchem.decompiler``) answers *what could this
compound come apart into, conserving everything?*  Read backwards, a descent is an **assembly** -- a
candidate synthesis route.  This package takes such a route and does four things a working chemist
needs, each under one governing discipline.

Universality (the load-bearing design fact)
-------------------------------------------
This is a REASONING ENGINE over whatever sourced data it is given, not an encyclopedia of a few
compounds.  The formal layers -- conservation (E0), the composability *logic* (E1), the stoichiometric
ceiling (E2), equipment-from-declared-conditions -- run on ANY :class:`~smartchem.category.Molecule` the
SMILES front door parses, with no whitelist.  The *data* layers (stability thresholds, conditions) accept
any molecule, are injectable per call (a chemist brings the compound and its sourced facts), and degrade
to a LOUD ``UNKNOWN`` on a gap -- never a crash, never a silent guess.

The rungs
---------
* **E0 -- certify the step** (:mod:`.step`): reactants -> products conserving mass and charge
  (re-verified through :class:`~smartchem.category.Reaction`), carrying a *declared* (sourced) or
  *unknown* :class:`~smartchem.conditions.ConditionEnvelope`.
* **E1 -- verify composability** (:mod:`.composability`): does each intermediate *survive the transition*
  to the next step's conditions?  Constraint satisfaction over SOURCED stability windows, never a
  prediction: ``COMPOSABLE`` / ``DEGENERATE(reason)`` / ``UNKNOWN``.
* **E2 -- the stoichiometric ceiling** (:mod:`.ceiling`): the 100%-efficiency maximum by limiting
  reagent -- exact rational conservation, an idealised UPPER BOUND labelled as one.
* **E3 -- attach the physical accounting** (:mod:`.accounting`): heat/time/pressure/solvent from SOURCED
  conditions or an ESTABLISHED validated model, ``UNKNOWN`` where unsourced.
* **E4 -- draft the procedure** (:mod:`.drafter`) and infer the **equipment** (:mod:`.equipment`), plus
  the **constraint fitter**: given a target bench (max T, max P, reagents/equipment on hand) select the
  routes that fit and refuse the ones that do not.

Every number falls in exactly one :class:`~smartchem.experiment.bucket.Bucket` and says which.
"""
from __future__ import annotations

from .bucket import Bucket, Quantity, unknown

__all__ = [
    "Bucket",
    "Quantity",
    "unknown",
]
