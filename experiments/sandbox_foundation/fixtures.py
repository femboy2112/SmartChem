"""Small SYNTHETIC systems shared by the probes, the tests and run_probes.py.  Nothing here is real chemistry:
species names are abstract labels, rate constants are made-up user inputs."""
from __future__ import annotations

from .twocell import Mechanism, ReactionRate, System


def tracer_system(D=0.5, V=(1.0, 2.0), boundaries=None) -> System:
    """Passive tracer 'T'.  g = D*1/1 = D m^3/s; dt_max = min(V)/g."""
    kw = {} if boundaries is None else {"species_boundaries": boundaries}
    return System(("T",), V, (100.0, 200.0), (D,), 1.0, 1.0, 0.0, **kw)


def thermal_system(C=(10.0, 30.0), k=2.0, thermal_boundaries=None) -> System:
    """Two conducting regions, no species.  G = k*1/1 W/K; dt_max = min(C)/G."""
    kw = {} if thermal_boundaries is None else {"thermal_boundaries": thermal_boundaries}
    return System((), (1.0, 1.0), C, (), 1.0, 1.0, k, **kw)


def isomer_mechanism(kf=1.5, kr=0.5, **rate_overrides) -> Mechanism:
    """SYNTHETIC P <-> Q.  Rows of E: X, Y, charge.  P and Q are 'isomers' with charge +1."""
    rate = ReactionRate(**{"k_f": kf, "k_r": kr, **rate_overrides})
    return Mechanism.from_net(("P", "Q"), [[-1.0], [1.0]], ("X", "Y", "charge"),
                     [[2, 2], [1, 1], [1, 1]], (rate,), label="SYNTHETIC-isomerization")


def bimolecular_mechanism(k=2.0) -> Mechanism:
    """SYNTHETIC R+ + S- -> RS (irreversible, second order).  Charge: +1 -1 -> 0."""
    return Mechanism.from_net(("R+", "S-", "RS"), [[-1.0], [-1.0], [1.0]], ("X", "Y", "charge"),
                     [[1, 0, 1], [0, 1, 1], [1, -1, 0]], (ReactionRate(k_f=k, reversible=False),),
                     label="SYNTHETIC-bimolecular")


def single_cell_system(mech: Mechanism, V=(1.0, 1.0)) -> System:
    """Reaction-only system (no diffusion) around a mechanism."""
    S = len(mech.species)
    return System(mech.species, V, (1.0, 1.0), (0.0,) * S, 1.0, 1.0, 0.0, mechanism=mech)


def composite_mechanism(kf=1.5, kr=0.5) -> Mechanism:
    """SYNTHETIC P <-> Q plus a passive tracer T (zero N row).  Rows of E: X, Tunit, charge."""
    return Mechanism.from_net(("P", "Q", "T"), [[-1.0], [1.0], [0.0]], ("X", "Tunit", "charge"),
                     [[2, 2, 0], [0, 0, 1], [1, 1, 0]], (ReactionRate(k_f=kf, k_r=kr),),
                     label="SYNTHETIC-composite")


def composite_system(D=(0.5, 1.0, 0.25), V=(1.0, 2.0), kf=1.5, kr=0.5) -> System:
    """P,Q,T diffusing across the face with distinct D.  dt_max = min(V)/max(g) = 1.0 s (D defaults)."""
    return System(("P", "Q", "T"), V, (1.0, 1.0), D, 1.0, 1.0, 0.0, mechanism=composite_mechanism(kf, kr))
