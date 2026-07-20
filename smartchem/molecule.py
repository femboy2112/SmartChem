from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
from .atoms import Atom

@dataclass(frozen=True)
class Bond:
    """A verified morphism in the categorical space."""
    atom_a: Atom
    atom_b: Atom
    electron_transfer_n: int
    delta_g_ev: float
    
    def __repr__(self):
        return f"{self.atom_a.symbol}=({self.electron_transfer_n}e-)=>{self.atom_b.symbol}"

@dataclass
class Molecule:
    """
    A chemical molecule represented as a connected categorical graph.
    Objects: Atoms
    Morphisms: Bonds
    """
    atoms: List[Atom]
    bonds: List[Bond] = field(default_factory=list)
    
    @classmethod
    def from_atoms(cls, atoms: List[Atom]):
        return cls(atoms=atoms)
        
    def add_bond(self, bond: Bond):
        self.bonds.append(bond)
        
    def __repr__(self):
        if not self.bonds:
            return " ".join([a.symbol for a in self.atoms])
        return " | ".join(str(b) for b in self.bonds)

    @property
    def total_energy(self) -> float:
        """The total thermodynamic stability of the molecular graph."""
        return sum(b.delta_g_ev for b in self.bonds)
