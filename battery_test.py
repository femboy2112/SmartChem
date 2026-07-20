from smartchem.electrochem import GalvanicCell

def simulate_flashlight():
    print("=== MACROSCOPIC ELECTROCHEMISTRY: AA BATTERY SIMULATION ===\n")
    
    print("--- Scenario A: Incandescent Flashlight (Constant Resistance) ---")
    battery_a = GalvanicCell()
    hours = 0
    while battery_a.current_voltage() > 0.8:
        # Tick 1 hour
        dt = 3600
        battery_a.tick_discharge("incandescent", 10.0, dt)
        battery_a.tick_corrosion(dt)
        hours += 1
        print(f"Hour {hours}: V_open={battery_a.current_voltage():.2f}V, Zn remaining={battery_a.moles_zn / 0.0428 * 100:.1f}%, Temp={battery_a.temperature_k:.1f}K")
    print(f"Incandescent Flashlight died after {hours} hours.\n")
    
    print("--- Scenario B: LED Flashlight (Constant Power, 0.2W) ---")
    battery_b = GalvanicCell()
    hours = 0
    while battery_b.current_voltage() > 0.8:
        dt = 3600
        delivered = battery_b.tick_discharge("led", 0.2, dt)
        battery_b.tick_corrosion(dt)
        if delivered == 0.0:
            break # Voltage sagged too much to drive the LED
        hours += 1
        print(f"Hour {hours}: V_open={battery_b.current_voltage():.2f}V, Zn remaining={battery_b.moles_zn / 0.0428 * 100:.1f}%, Temp={battery_b.temperature_k:.1f}K")
    print(f"LED Flashlight died after {hours} hours.\n")
    
    print("--- Scenario C: Storage Corrosion (Room Temp, 25C) ---")
    battery_c = GalvanicCell(temperature_k=298.15)
    days = 0
    while not battery_c.tick_corrosion(86400): # 1 day
        days += 1
        if days > 10000:
            print("Battery survived 10,000 days (>27 years) without leaking.")
            break
    if days <= 10000:
        print(f"Battery ruptured after {days} days at Room Temp.")
        
    print("\n--- Scenario D: Storage Corrosion (Car Trunk in Summer, 60C) ---")
    battery_d = GalvanicCell(temperature_k=333.15)
    days = 0
    while not battery_d.tick_corrosion(86400):
        days += 1
        if days > 10000:
            print("Battery survived 10,000 days (>27 years) without leaking.")
            break
    if days <= 10000:
        print(f"Battery ruptured after {days} days at 60C (140F)!")

if __name__ == "__main__":
    simulate_flashlight()
