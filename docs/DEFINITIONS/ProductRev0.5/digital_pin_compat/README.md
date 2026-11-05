# Digital pin-compat prototype

This directory contains an isolated functional model for the AD7961-style LVDS echo-clock boundary. It does not replace the old SPI prototype under `digital/`.

From this `digital_pin_compat` directory, run the 16-bit and 32-bit protocol regression:

```sh
ADC_VERILATOR=/absolute/path/to/verilator python3 scripts/run_tb.py
```

The runner uses the existing local Verilator, stages its small runtime and the sources under an ASCII temporary path, and writes the portable evidence bundle to `results.json` and `results/verilator.log`. No tool installation or new simulation environment is required.

Verilator lookup order is explicit `ADC_VERILATOR`, then `PATH`, then a bounded search up the checkout's parent directories for the archived project runtime. This command also works after unpacking the project into a shallow ASCII path, provided `ADC_VERILATOR` points to an executable.

If `ADC_VERILATOR` is present but invalid or non-executable, the runner stops with a diagnostic rather than silently falling back to another simulator.

The regression covers exact first/last edges, MSB-first bit order, valid-zero fixed frames, source snapshot stability, the two EN test words, incomplete-frame recovery, one and two unread CNV slots, EN-only asynchronous internal reset, persistent LVDS enable in active modes, idle-low echoed DCO, extra-clock echo without stale-data replay, and the 10 ns first-data-fall guard. LVDS drivers remain enabled throughout normal/test mode; EN=0000 or an unsupported EN code disables them. The test does not verify LVDS electrical behavior, general CDC/RDC, analog conversion timing, ADC precision, FPGA setup/hold, STA, package or board timing.
