from dataclasses import dataclass
from typing import Generic, TypeVar, Callable, List, Tuple
import math

T = TypeVar('T')
U = TypeVar('U')

@dataclass(frozen=True)
class ThermoEffect:
    """
    Thermodynamic footprint of a state change.
    All energies in eV (electron-volts) for atomic scale consistency.
    1 eV ≈ 96.485 kJ/mol
    """
    delta_h_ev: float  # Enthalpy (heat)
    delta_s_ev_k: float # Entropy (disorder) in eV/K
    
    def get_delta_g(self, temp_k: float) -> float:
        """Gibbs Free Energy: ΔG = ΔH - TΔS"""
        return self.delta_h_ev - (temp_k * self.delta_s_ev_k)
    
    def __add__(self, other: 'ThermoEffect') -> 'ThermoEffect':
        return ThermoEffect(
            self.delta_h_ev + other.delta_h_ev, 
            self.delta_s_ev_k + other.delta_s_ev_k
        )
    
    def is_spontaneous(self, temp_k: float) -> bool:
        """Thermodynamic gate: spontaneous if ΔG < 0."""
        return self.get_delta_g(temp_k) < 0
        
    def equilibrium_constant(self, temp_k: float) -> float:
        """K_eq = exp(-ΔG / kT), where k = 8.617e-5 eV/K"""
        k_b = 8.617333262145e-5
        delta_g = self.get_delta_g(temp_k)
        exponent = -delta_g / (k_b * temp_k)
        # Prevent overflow for extremely favorable reactions
        if exponent > 500:
            return float('inf')
        if exponent < -500:
            return 0.0
        return math.exp(exponent)

@dataclass(frozen=True)
class Reaction(Generic[T]):
    """
    The Effect Monad T.
    A computation that produces a set of possible states and a thermodynamic footprint.
    """
    outcomes: List[Tuple[T, ThermoEffect]]
    metadata: dict = None

    @staticmethod
    def pure(value: T) -> 'Reaction[T]':
        """No reaction; zero thermodynamic effect."""
        return Reaction([(value, ThermoEffect(0.0, 0.0))])

    def bind(self, f: Callable[[T], 'Reaction[U]']) -> 'Reaction[U]':
        """
        Chain reactions, accumulating the thermodynamic effect.
        """
        new_outcomes = []
        for val, eff in self.outcomes:
            next_reaction = f(val)
            for next_val, next_eff in next_reaction.outcomes:
                new_outcomes.append((next_val, eff + next_eff))
        return Reaction(new_outcomes)
