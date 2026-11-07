# Vinegar world, vented vs sealed (OPERATION XXIII): a sample projection

`vinegar_world.html` is one self-contained, deterministic HTML file. It uses no network and no external libraries.
It was written by

```
PYTHONPATH=. .venv/bin/python -m experiments.sandbox_foundation.vinegar_world_viz \
    --out experiments/sandbox_foundation/benchmarks/vinegar_world_xxiii/vinegar_world.html
```

Re-running that command produces a byte-identical file (sha256
`193909dcb6d5da9d123ef3377326b3126a4e00cc2c3d4413ad04bad6cfff3cb1` at commit time). It sits on the research-only
API `smartchem-sim-2.0a0-research` (`sim_api_v2alpha.py`). That API is not stable, not in the wheel, and not covered
by COMPATIBILITY.md.

**This is a projection of a computed model. No animated phenomenon certifies itself. The kinetics are ASSUMED. It is
not a safety certification.** The rising glyphs are an ILLUSTRATION: their rate is proportional to the modeled Henry
flux, and bubble geometry is not modeled. Pressure is p_CO2 = n·R·T/V_gas, computed from the modeled CO2(g)
inventory. Air is not modeled, so this is the CO2 partial pressure above the initial headspace, not the total
pressure.

## Scenario

Both regimes use the same declared chemistry: the flagship `default` inventories (0.5 mol HAc in A; 0.2 mol
NaHCO3(s) + 0.1 mol dissolved in B; 1 L per cell and 1 L of headspace; 25 °C). The schedule is `separate` (closed,
20 s) followed by `mixing` (bulk exchange, 280 s), with dt = 2 s. The only difference between regimes is the export
boundary on the headspace.

End state at t = 300 s (default resolution):

| quantity | vented | sealed |
|---|---|---|
| CO2(g) headspace (mol) | 0.00332 | 0.1093 |
| p_CO2 (atm) | 0.081 | 2.675 |
| DIC, A + B (mol) | 0.0115 | 0.1907 |
| pH_B (activity) | 4.813 | 4.790 |
| C exported (mol) | 0.2852 (= receipt ledger) | 0 |
| solid NaHCO3 | 0 (gone during `separate`) | 0 |

The difference emerges from the boundary alone. In the sealed run the headspace back-pressure throttles the Henry
flux (B→gas) until it reaches equilibrium (about 2e-10 mol/s at the end). More inorganic carbon stays dissolved, and
pH ends about 0.022 lower; the acetate buffer near its pKa keeps the pH shift small. The sealed headspace reaching
about 2.7 atm of CO2 is a computed number from ASSUMED kinetics. It is **computational only — not a laboratory safety
certification**.

> **Physical warning (not a model output).** Do not reproduce the sealed scenario with real materials. Vinegar and
> baking soda in a sealed container generate CO2 pressure that can burst bottles, jars and lids and throw fragments.
> The model's ~2.7 atm is a computed projection under assumed kinetics. It is neither an upper bound nor a safe
> design value, and nothing in this repository certifies any vessel, quantity or procedure as safe.
