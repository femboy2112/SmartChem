import math
from dataclasses import dataclass
from smartchem.atoms import Atom, Species

@dataclass
class GalvanicCell:
    # A standard AA battery contains ~2.8g of Zn and ~9.0g of MnO2
    moles_zn: float = 0.0428  # ~2.8g / 65.38 g/mol
    moles_mno2: float = 0.103 # ~9.0g / 86.94 g/mol
    moles_h2o: float = 0.05   # Electrolyte water
    moles_h2_gas: float = 0.0
    
    # Internal variables
    internal_resistance_ohms: float = 0.15 # Fresh alkaline AA
    casing_rupture_pressure_atm: float = 15.0 # Typical failure point for alkaline casing
    temperature_k: float = 298.15
    
    # Voltage calculation
    # E0 for Alkaline AA is nominally ~1.5V
    # Mathematically mapped from Mulliken differences and solvation:
    # E_cell = (chi_cathode - chi_anode) / F + solvation_delta
    # We will use the nominal 1.5V and apply the Nernst equation for depletion
    base_voltage: float = 1.55 
    
    def current_voltage(self) -> float:
        """Nernst Equation: E = E0 - (RT/nF)*ln(Q)"""
        # As Zn depletes and ZnO builds up, Q increases. 
        # For simplicity, we model the voltage drop primarily through internal resistance
        # and depletion of active material.
        if self.moles_zn <= 0 or self.moles_mno2 <= 0:
            return 0.0
            
        fraction_zn = self.moles_zn / 0.0428
        fraction_mn = self.moles_mno2 / 0.103
        
        # Nernstian drop
        # E = E0 + 0.059/2 * log(active_fractions)
        v_drop = (0.059 / 2) * math.log10(fraction_zn * fraction_mn + 1e-10)
        return max(0.0, self.base_voltage + v_drop)
        
    def get_internal_resistance(self) -> float:
        """Internal resistance increases as the cell discharges and dries out."""
        fraction_zn = self.moles_zn / 0.0428
        # R_int scales inversely with remaining reactants (ZnO passivation layer)
        if fraction_zn <= 0: return float('inf')
        return self.internal_resistance_ohms / (fraction_zn ** 1.5)

    def tick_discharge(self, load_type: str, load_value: float, dt_seconds: float):
        """
        Discharges the battery through a load over dt_seconds.
        load_type: "incandescent" (constant resistance, load_value in Ohms)
                   "led" (constant power, load_value in Watts)
        Returns the energy delivered in Joules.
        """
        V_open = self.current_voltage()
        if V_open <= 0:
            return 0.0
            
        R_int = self.get_internal_resistance()
        
        if load_type == "incandescent":
            R_load = load_value
            R_total = R_int + R_load
            I = V_open / R_total
            V_load = I * R_load
        elif load_type == "led":
            # P = V_load * I
            # V_load = V_open - I * R_int
            # P = (V_open - I * R_int) * I  => R_int*I^2 - V_open*I + P = 0
            P_req = load_value
            # Minimum voltage to run LED driver (e.g. 0.8V)
            if V_open < 0.8:
                return 0.0
                
            discriminant = V_open**2 - 4 * R_int * P_req
            if discriminant < 0:
                # Cannot supply the required power, voltage sags completely
                return 0.0
            
            # Take the smaller current solution for efficiency
            I = (V_open - math.sqrt(discriminant)) / (2 * R_int)
        else:
            raise ValueError("Unknown load type")
            
        # Faraday's Law: moles of electrons = I * t / F
        F = 96485.0
        moles_e = (I * dt_seconds) / F
        
        # Alkaline chemistry: 
        # Zn + 2OH- -> ZnO + H2O + 2e- (2 moles e- per mole Zn)
        # 2MnO2 + H2O + 2e- -> Mn2O3 + 2OH- (1 mole e- per mole MnO2)
        moles_zn_consumed = moles_e / 2.0
        moles_mn_consumed = moles_e
        
        # We also consume some water in the cathode (though it's regenerated at anode, net water is mostly balanced,
        # but locally it binds into ZnO and MnOOH). We'll assume a slight net loss to passivation.
        self.moles_zn = max(0.0, self.moles_zn - moles_zn_consumed)
        self.moles_mno2 = max(0.0, self.moles_mno2 - moles_mn_consumed)
        
        # Resistance heats the battery
        heat_joules = (I**2 * R_int) * dt_seconds
        # Increase temperature slightly (simplified specific heat capacity)
        self.temperature_k += (heat_joules / 5.0)  # ~5 J/K for a small AA battery
        
        return I * V_open * dt_seconds  # Total energy in Joules

    def tick_corrosion(self, dt_seconds: float) -> bool:
        """
        Parasitic side reaction: Zn + 2H2O -> Zn(OH)2 + H2 (gas)
        This happens even when the battery is off.
        Rate is heavily dependent on Temperature (Arrhenius Equation).
        Returns True if the battery ruptures (corrosion leak).
        """
        if self.moles_zn <= 0:
            return False
            
        # Standard Arrhenius kinetics for Zn corrosion in KOH
        # Activation energy ~ 50 kJ/mol
        Ea = 50000.0 
        R = 8.314
        
        # Base rate at 298K
        k_298 = 5e-12  # moles H2 per second
        
        # Exponential speedup
        k = k_298 * math.exp((-Ea / R) * (1.0/self.temperature_k - 1.0/298.15))
        
        moles_h2_produced = k * dt_seconds
        self.moles_h2_gas += moles_h2_produced
        self.moles_zn -= moles_h2_produced
        
        # Ideal gas law for internal pressure inside an AA battery void (~2 mL = 0.002 L)
        V_void = 0.002
        pressure_atm = (self.moles_h2_gas * 0.08206 * self.temperature_k) / V_void
        
        if pressure_atm > self.casing_rupture_pressure_atm:
            return True # RUPTURE!
        return False
