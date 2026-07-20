from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple

@dataclass(frozen=True)
class Atom:
    symbol: str
    atomic_number: int
    group: int
    period: int
    ie_list_ev: Tuple[float, ...]  # Successive ionization energies (IE1, IE2, IE3...)
    ea_list_ev: Tuple[float, ...]  # Successive electron affinities (EA1, EA2...). Positive means energy released.
    radius_pm: float
    mass_amu: float = 0.0

    def __repr__(self):
        return f"{self.symbol}"
    
    def __eq__(self, other):
        if not isinstance(other, Atom):
            return False
        return self.symbol == other.symbol
        
    def __hash__(self):
        return hash(self.symbol)

    @property
    def mulliken_en(self) -> float:
        """Absolute chemical potential based on 1st IE and 1st EA."""
        return (self.ie_list_ev[0] + self.ea_list_ev[0]) / 2.0

    @property
    def hardness(self) -> float:
        """Chemical hardness (resistance to polarization)."""
        return (self.ie_list_ev[0] - self.ea_list_ev[0]) / 2.0

    def ionization_cost(self, n: int) -> float:
        """Energy required to remove n electrons."""
        if n == 0: return 0.0
        if n > len(self.ie_list_ev):
            return float('inf') # Wall off un-tabulated high oxidation states
        return sum(self.ie_list_ev[:n])

    def affinity_gain(self, n: int) -> float:
        """Energy released by gaining n electrons. (Negative if it costs energy)."""
        if n == 0: return 0.0
        if n > len(self.ea_list_ev):
            return -float('inf')
        return sum(self.ea_list_ev[:n])
        
    @property
    def valence_cap(self) -> int:
        """The maximum number of electrons this atom can share in covalent bonds."""
        if self.group == 18:
            return 8 if self.period > 2 else 0 # Xe can bond, Ne/He cannot
        if 13 <= self.group <= 17:
            val_e = self.group - 10
            # Period 2 elements obey the octet rule strictly
            if self.period <= 2:
                return 8 - val_e
            # Period 3+ can expand octet up to their valence
            return val_e
        if 1 <= self.group <= 2:
            return self.group
        # d-block (3-12) can share many, usually bounded by 6-8 in typical complexes
        return 6

@dataclass(frozen=True)
class Species:
    composition: FrozenSet[tuple[Atom, int]]
    charge: int = 0
    
    @classmethod
    def from_dict(cls, comp_dict: Dict[Atom, int], charge: int = 0):
        return cls(frozenset(comp_dict.items()), charge)

    @property
    def comp_dict(self) -> Dict[Atom, int]:
        return dict(self.composition)

    def __repr__(self):
        if not self.composition:
            return "Vacuum"
        parts = [f"{atom}{count if count > 1 else ''}" for atom, count in self.composition]
        base = "".join(parts)
        if self.charge > 0:
            return f"{base}+{self.charge}"
        elif self.charge < 0:
            return f"{base}{self.charge}"
        return base

    def __add__(self, other: 'Species') -> 'Species':
        new_comp = dict(self.composition)
        for atom, count in other.composition:
            new_comp[atom] = new_comp.get(atom, 0) + count
        return Species.from_dict(new_comp, self.charge + other.charge)

    def beta_decay(self, original_atom: Atom, new_atom: Atom) -> 'Species':
        """
        Subatomic Morphism: Beta Decay
        A nucleus decays, changing its atomic number (Z -> Z+1 or Z-1).
        This instantly rewrites the molecular topology.
        """
        if original_atom not in self.comp_dict:
            return self
            
        new_dict = dict(self.comp_dict)
        # One atom decays
        new_dict[original_atom] -= 1
        if new_dict[original_atom] == 0:
            del new_dict[original_atom]
            
        new_dict[new_atom] = new_dict.get(new_atom, 0) + 1
        # The electron/positron emission changes the total charge
        # Beta minus decay: n -> p + e- + v. The new atom has +1 proton.
        # But wait, if it ejects an electron, the molecular charge becomes +1.
        return Species.from_dict(new_dict, self.charge + 1)

# EA2 for oxygen is -7.7 eV (costs energy in vacuum), but heavily stabilized by comonad in aqueous.
# EA for He, Ne are negative (endothermic to add electron).
PT: Dict[str, Atom] = {
    "H": Atom("H", 1, 1, 1, (13.598,), (0.754,), 53.0, 1.008),
    "D": Atom("D", 1, 1, 1, (13.598,), (0.754,), 53.0, 2.014),
    "T": Atom("T", 1, 1, 1, (13.598,), (0.754,), 53.0, 3.016),
    "He": Atom("He", 2, 18, 1, (24.587, 54.417), (-0.5,), 31.0, 4.002),
    "C": Atom("C", 6, 14, 2, (11.260, 24.38, 47.88, 64.49), (1.262,), 77.0),
    "O": Atom("O", 8, 16, 2, (13.618, 35.12, 54.93), (1.461, -7.7), 73.0),
    "F": Atom("F", 9, 17, 2, (17.423, 34.97, 62.7), (3.399, -3.4), 71.0),
    "Na": Atom("Na", 11, 1, 3, (5.139, 47.286), (0.548,), 154.0),
    "Mg": Atom("Mg", 12, 2, 3, (7.646, 15.035, 80.14), (-0.4,), 130.0),
    "Cl": Atom("Cl", 17, 17, 3, (12.967, 23.81, 39.61), (3.612, -2.5), 99.0),
    "Fe": Atom("Fe", 26, 8, 4, (7.902, 16.199, 30.652, 54.8), (0.153,), 125.0),
    "Cu": Atom("Cu", 29, 11, 4, (7.726, 20.292, 36.84), (1.235,), 128.0),
    "Kr": Atom("Kr", 36, 18, 4, (14.0, 24.36, 36.95, 52.5, 64.7, 78.5), (-1.0,), 88.0),
    "Xe": Atom("Xe", 54, 18, 5, (12.13, 21.21, 32.12, 45.14, 58.1, 71.8), (-1.0,), 108.0),
    "N": Atom("N", 7, 15, 2, (14.53, 29.60, 47.45), (-0.07,), 75.0),
    "P": Atom("P", 15, 15, 3, (10.48, 19.72, 30.18), (0.74,), 106.0),
    "S": Atom("S", 16, 16, 3, (10.36, 23.33, 34.83), (2.07, 0.0), 102.0),
    "Mo": Atom("Mo", 42, 6, 5, (7.09, 16.16, 27.13, 46.4, 54.4, 68.0), (0.74,), 139.0),
    "He": Atom("He", 2, 18, 1, (24.587, 54.417), (-0.5,), 31.0),
    "Ru": Atom("Ru", 44, 8, 5, (7.36, 16.76, 28.47, 45.0, 58.0, 72.0), (1.05,), 126.0),
    "Pt": Atom("Pt", 78, 10, 6, (9.0, 18.56, 30.0, 42.0), (2.12,), 139.0),
    "Pd": Atom("Pd", 46, 10, 5, (8.34, 19.43, 32.93, 47.0), (0.56,), 137.0),
    "Si": Atom("Si", 14, 14, 3, (8.151, 16.345, 33.493, 45.141), (1.390,), 111.0),
    "Og": Atom("Og", 118, 18, 7, (8.60, 15.0), (0.056,), 152.0),
    "Zn": Atom("Zn", 30, 12, 4, (9.39, 17.96, 39.72), (-0.6,), 134.0, 65.38),
    "Mn": Atom("Mn", 25, 7, 4, (7.43, 15.64, 33.66, 51.2), (0.0,), 127.0, 54.93),
    "K": Atom("K", 19, 1, 4, (4.34, 31.81), (0.501,), 227.0, 39.09),
    "Pb": Atom("Pb", 82, 14, 6, (7.41, 15.03, 31.93, 42.32), (0.36,), 154.0, 207.2),
    "I": Atom("I", 53, 17, 5, (10.45, 19.13, 33.0), (3.059, -3.0), 133.0, 126.9),
}
