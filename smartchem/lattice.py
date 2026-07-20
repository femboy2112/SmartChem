from .atoms import Atom

class Poset:
    """
    The Lattice of Chemical Potential and Hardness.
    Instead of simplistic electronegativity, we use absolute Mulliken electronegativity (chemical potential)
    and Chemical Hardness (HSAB theory).
    """
    
    @staticmethod
    def leq(a: Atom, b: Atom) -> bool:
        """
        Partial Order: `a <= b` means `b` exerts a stronger pull on electrons than `a`.
        (b is the oxidizer, a is the reducer).
        """
        return a.mulliken_en <= b.mulliken_en
    
    @staticmethod
    def charge_transfer_energy(donor: Atom, acceptor: Atom) -> float:
        """
        Distance Metric: The theoretical energy required/released (in eV) to transfer partial charge.
        ΔN = (χ_acceptor - χ_donor) / (2 * (η_acceptor + η_donor))
        ΔE = - (χ_acceptor - χ_donor)^2 / (4 * (η_acceptor + η_donor))
        This acts as our precise cognitive surprise / Goldilocks mapping.
        """
        chi_diff = acceptor.mulliken_en - donor.mulliken_en
        eta_sum = acceptor.hardness + donor.hardness
        
        # If chi_diff is negative, the roles are reversed, no spontaneous transfer in this direction.
        if chi_diff <= 0:
            return 0.0
            
        return -(chi_diff ** 2) / (4.0 * eta_sum)

    @staticmethod
    def hsab_penalty(a: Atom, b: Atom) -> float:
        """
        Hard-Soft Acid-Base (HSAB) penalty.
        Hard likes Hard, Soft likes Soft.
        A large difference in hardness incurs an energy penalty for bonding.
        """
        return abs(a.hardness - b.hardness)

    @staticmethod
    def is_favorable(a: Atom, b: Atom) -> bool:
        """
        Lattice Gate: 
        Checks if the orbital interactions (FMO) are favorable based on Mulliken potential and HSAB match.
        We expect a minimum stabilization energy to consider it not 'inert'.
        """
        # Determine roles
        if a.mulliken_en < b.mulliken_en:
            donor, acceptor = a, b
        else:
            donor, acceptor = b, a
            
        stabilization_ev = Poset.charge_transfer_energy(donor, acceptor)
        penalty_ev = Poset.hsab_penalty(donor, acceptor)
        
        # Net orbital stabilization must overcome HSAB mismatch
        net_ev = abs(stabilization_ev) - (penalty_ev * 0.1) # HSAB is a kinetic/stability modifier
        
        # We need a non-negative driving force for a spontaneous lattice match
        return net_ev > 0.0
