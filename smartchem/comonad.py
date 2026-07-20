from dataclasses import dataclass
from typing import Generic, TypeVar, Callable

T = TypeVar('T')
U = TypeVar('U')

@dataclass(frozen=True)
class Env:
    """
    The chemical environment driving state changes.
    """
    temperature_k: float
    pressure_atm: float
    solvent_name: str
    solvent_dielectric: float
    photon_wavelength_nm: float = float('inf') # Infinity means no light
    
    @property
    def photon_energy_ev(self) -> float:
        """E = hc/lambda. 1240 eV*nm / wavelength"""
        if self.photon_wavelength_nm == float('inf'):
            return 0.0
        return 1240.0 / self.photon_wavelength_nm
        
    # We maintain external_energy_ev as an alias for compatibility, mapped to photon_energy
    @property
    def external_energy_ev(self) -> float:
        return self.photon_energy_ev
    
    @classmethod
    def standard(cls):
        return cls(298.15, 1.0, "Vacuum", 1.0, float('inf'))
        
    @classmethod
    def aqueous(cls, temp_k=298.15):
        return cls(temp_k, 1.0, "Water", 80.1, float('inf')) 
        
    @classmethod
    def cryogenic(cls):
        return cls(50.0, 1.0, "Liquid Helium", 1.05, float('inf'))
        
    @classmethod
    def upper_atmosphere(cls):
        # High UV energy (e.g. 248 nm photon = ~5.0 eV)
        return cls(220.0, 0.01, "Stratosphere", 1.0, 248.0)
        
    @classmethod
    def high_energy_plasma(cls):
        # Extreme spark (e.g. ~124 nm = ~10.0 eV)
        return cls(800.0, 10.0, "High Pressure Cell", 1.0, 124.0)

@dataclass(frozen=True)
class Situated(Generic[T]):
    """
    The Store Comonad W.
    Represents a species situated in an environment.
    """
    value: T
    env: Env

    def extract(self) -> T:
        """Extract the bare chemical species, ignoring context."""
        return self.value

    def extend(self, f: Callable[['Situated[T]'], U]) -> 'Situated[U]':
        """
        Extend a local property/transformation to the whole context.
        δ : W(A) → W(W(A)) applied to f : W(A) → B gives W(A) → W(B)
        """
        return Situated(f(self), self.env)
    
    def map(self, f: Callable[[T], U]) -> 'Situated[U]':
        return Situated(f(self.value), self.env)
        
    def born_solvation_energy_ev(self, charge: int, radius_pm: float) -> float:
        """
        Comonadic computation: The environment inherently stabilizes charges.
        Uses the Born Solvation equation: E = - (z^2 * e^2) / (8 * pi * e_0 * r) * (1 - 1/epsilon)
        Returns energy in eV.
        """
        if charge == 0:
            return 0.0
        # Born constant approx in eV*pm
        born_constant = 1440.0 / 2.0 
        epsilon = self.env.solvent_dielectric
        
        # radius effective for solvation is usually slightly larger, add 50 pm
        r_eff = radius_pm + 50.0 
        
        energy = - (charge**2 * born_constant) / r_eff * (1.0 - (1.0 / epsilon))
        return energy
