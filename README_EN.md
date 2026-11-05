<div align="center">

# SAR20-5 · Behavioral Model of a 20-bit 5 MS/s Two-Step SAR ADC

**Simulink behavioral project · architecture baseline from UESTC CICC 2026 · 5 MS/s single-frontend normal operating point**

[![MATLAB](https://img.shields.io/badge/MATLAB-R2024a%20Update%206-orange)](https://www.mathworks.com/products/matlab.html)
[![Simulink](https://img.shields.io/badge/Simulink-behavioral-blue)](https://www.mathworks.com/products/simulink.html)
[![Rate](https://img.shields.io/badge/5%20MS%2Fs-Fs-brightgreen)](#2-current-status-and-evidence-boundary)
[![SNDR](https://img.shields.io/badge/SNDR-99.133%20dB%20%40%20N256-blueviolet)](#22-the-only-promoted-result-n256)
[![ENOB](https://img.shields.io/badge/ENOB-16.17%20bit-informational)](#22-the-only-promoted-result-n256)
[![Status](https://img.shields.io/badge/status-normal%20baseline%20released%20%2F%20expansion%20paused-yellow)](#2-current-status-and-evidence-boundary)
[![Docs](https://img.shields.io/badge/docs-English-success)](README_EN.md)
[![中文](https://img.shields.io/badge/docs-中文-lightgrey)](README.md)
[![Plan](https://img.shields.io/badge/plan-PROJECT_PLAN-important)](docs/PROJECT_PLAN.md)
[![Design](https://img.shields.io/badge/design-Error%20Budget-critical)](design/budget/ERROR_BUDGET_REV03.md)

</div>

> 📌 **Read this first**: this is a **behavioral modeling project**, not a paper-reproduction report, not a circuit netlist, and not a tape-out or signoff result.
> The only promoted result is **one N256 run** on model `91973cf7…` (SNDR 99.133 dB / ENOB 16.17 bit). The UESTC CICC 2026 paper has **not been reproduced**, and the project had not previously defined an acceptance criterion for "reproduction".
>
> This page is an **engineering reference**: objectives, architecture and timing, parameter assumptions, non-ideality coverage, running, debugging, evidence chain, known gaps and the roadmap — each with a file path you can verify.
> Full diagnosis: [ENGINEERING_ANALYSIS.md](docs/ENGINEERING_ANALYSIS.md). Executable next steps: [PROJECT_PLAN.md](docs/PROJECT_PLAN.md).
> The repository was first pushed on **2026-11-05**, preserving source, model, historical evidence, design drafts and the reference papers.

> 中文版（默认首页，内容最全）：[README.md](README.md)。Both pages are kept structurally aligned; the Chinese page is the normative entry.

---

## 0. The 30-second verdict

| | |
|---|---|
| **What it is** | A MATLAB/Simulink **behavioral** project with `SAR20.m` as the sole entry and `current/models/SarAdc.slx` as the sole production model; event-driven double voltage/charge computation of a two-step SAR + RA + CT second stage + tracking averaging |
| **What it is not** | No transistor-level circuit, no PDK, no power/area, no DNL/INL, no PVT, no verification of any paper result |
| **Does it run?** | Yes. `apply → check → run → sample` has real execution receipts; the normal N256 release was completed on Windows MATLAB R2024a Update 6 on 2026-11-04 |
| **Where it is stuck** | **Not "cannot run" but "cannot attribute"**: 99.133 dB is one joint run of all enabled non-idealities, so no single source can be isolated; changes therefore cannot be accepted, candidates keep being archived, and production shows zero net change |
| **Current phase** | On 2026-11-05 the user **paused** the expansion goal (visualization / debug UI). All candidates are sealed; production SLX is still `91973cf7…`, no debug candidate deployed |

### What can and cannot be claimed

| ✅ Can claim | ❌ Cannot claim |
|---|---|
| Architectural skeleton and timing narrative match the paper text (6b pre-conversion + 10b effective DT + DAC1 charge residue + 32× RA/AZ + CINC CT second stage + 12 D2 + 8 tracking comparisons / 7 physical feedback, ~90 ns conversion) | Paper performance reproduction (100 dB SNDR / 3.6 mW / 0.53 mm² are silicon measurements with no counterpart here) |
| The single N256 behavioral spectrum is self-consistent and bitwise reproducible for identical configuration (9 truly identical configuration groups, max metric spread `0.000e+00`) | The ~7 dB tracking-averaging benefit (no measured control; the theoretical 9.03 dB ceiling is explicitly forbidden as a "benefit") |
| The public `apply → cold open → run → sample` chain has actually been executed | DNL/INL, 20k-point spectra, multi-tone / multi-seed stability |
| The nominal digital decode chain has been independently recomputed in Python: **256/256 exact match** | Valid calibration / foreground LMS / independent holdout (`accepted=false`) |
| One L3 full-graph N256 run | Power, area, PDK, PEX, silicon, any signoff |

> ⚠️ **ENOB 16.17 bit ≠ 20 bit.** `docs/SPEC.md:43`: "A 20-bit output word is not a 20-bit ENOB."

---

## 1. Quick navigation

| I want to… | Go to |
|---|---|
| **Guide a circuit design: numeric limits per block** | [🎯 Rev0.3 design constraint chain](design/budget/ERROR_BUDGET_REV03.md) · [budget JSON](design/budget/error_budget_rev03.json) · [binding CSV](design/budget/parameter_binding.csv) · [verifier](design/budget/verify_budget.py) |
| **Judge the state of this project** | [§0 verdict](#0-the-30-second-verdict) · [Full engineering analysis](docs/ENGINEERING_ANALYSIS.md) |
| **Know what comes next and in what order** | [📋 PROJECT_PLAN.md](docs/PROJECT_PLAN.md) (M0–M4 gates, commands, rollback) |
| **Understand architecture, state, timing, why divide by 8** | [§4 Architecture](#4-architecture-and-how-it-works) · [READ_GRAPH.md](docs/READ_GRAPH.md) · [PARAMETERS.md](docs/PARAMETERS.md) |
| **See active parameters and which are assumptions** | [§5 Parameters](#5-parameters-and-configuration) · [coverage table](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) |
| **See exactly which non-idealities are implemented / missing** | [§6 Coverage](#6-non-ideality-coverage) |
| **Run / change parameters on Windows** | [§7 Running](#7-running-and-reproducing) |
| **Debug on macOS without MATLAB** | [§8.1 Zero-MATLAB probe](#81-macos-zero-matlab-read-only-probe) · [offline panel](analysis/local_debug/sar20_debug_report.html) |
| **Get single-sample event waveforms** | [§8.2 MATLAB sample](#82-matlab-event-level-sample) |
| **Audit what one run actually writes** | [§7.4 Artifacts](#74-what-one-run-writes) · [§9 Evidence map](#9-archive-and-evidence-map) |
| **Read the product spec / I/O contract / acceptance rules** | [SPEC.md](docs/SPEC.md) · [spec.yml](docs/spec.yml) · [ALIGNMENT.md](docs/ALIGNMENT.md) · [acceptance contract](design/behavioral_acceptance.md) |
| **Read what was adopted from each of the three papers** | [CAAZ_ADI.md](docs/CAAZ_ADI.md) · [27-paper index](docs/PAPERS/INDEX.md) |
| **Resume after an interrupted session** | [CHECKPOINT.md](CHECKPOINT.md) (newest at top) · [RESUME.md](analysis/debug_ui_20261105/paused_work/RESUME.md) · [PAUSE_INDEX.json](analysis/debug_ui_20261105/paused_work/PAUSE_INDEX.json) |

---

## 2. Current status and evidence boundary

### 2.1 Authoritative identity

| Item | Value | Source |
|---|---|---|
| Sole public entry | [`SAR20.m`](SAR20.m) (474 lines) | source |
| Sole production model | [`current/models/SarAdc.slx`](current/models/SarAdc.slx), 492 760 B | — |
| Production SLX SHA-256 | `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` | [state/applied_config.json](state/applied_config.json) · [release receipt](analysis/behavior/public_normal_20261105/release_actual/release_receipt.json) |
| Production source | [`current/src/`](current/src/), 108 `.m` / 10 264 lines / 9 subdirectories | [analysis §4.1](docs/ENGINEERING_ANALYSIS.md) |
| Active config SHA | `aa9f8f6d97108fbfae66701e8d09db123940a1b5f1b75fc9187c9b0203aba3c3` | `summary.json` |
| Authoritative run | `behavior_12d08121-d679-40cd-9ee2-bc334ff42955` | [run mirror](analysis/behavior/public_normal_20261105/release_actual/behavior_12d08121-d679-40cd-9ee2-bc334ff42955/) |
| 119-item active manifest | `7b8fdf307e933a212f2f5eeee35a1f41df9b8a00d495e3cdaa4928c2b97c687f` | CHECKPOINT.md:21 |
| Runtime | Windows `D:/Academic/Projects/sar20m1/SAR20`, MATLAB R2024a Update 6 (24.1.0.2689473); **no MATLAB on the macOS host** | release receipt |

### 2.2 The only promoted result (N256)

Configuration: Fs **5 MHz** (Ts 200 ns), Fin **97.65625 kHz** (coherent bin5), amplitude **4.456254690668728 V** (−1 dBFS), differential FSR **10 V**, N **256**, first_id 4, epoch 1, seed **20261020**, n_cycles 260, stop_time 51.89 µs; rectangular coherent window, DC excluded, H2–H10 folded.

| SNR | SNDR | SFDR | THD | ENOB | Wall clock |
|---|---|---|---|---|---|
| 99.712414227270258 dB | **99.132765903966785 dB** | 111.78407088195453 dB | −108.16556427335165 dB | **16.174878057137342 bit** | 117.7867422 s (`summary.json` elapsed 115.33 s) |

- Same-range non-ideality-off baseline: SNDR **109.16497669573319 dB** ([DYNAMIC_ACTUAL_256.json](analysis/behavior/normal_workpoint_20261104/DYNAMIC_ACTUAL_256.json)).
- Independent NumPy recomputation from the actual CSV differs from MATLAB by at most `3.44e−11 dB`.
- Release receipt: `factory_p_exact / cold_p_exact / output_exact / global_rng_unchanged` all `true`, `selected_records 256`, `root_outputs 3`.
- ⚠️ This is **one joint run of all enabled non-idealities**, not a per-source measurement. The coverage table states that kT/C, capacitor mismatch, finite settling, AZ, RA or comparator noise **cannot be individually isolated from it**.

### 2.3 Evidence levels (repository-wide convention)

| Level | Meaning | Present here |
|---|---|---|
| L0 | Static audit / offline recomputation | 119-item SHA check; 9 identical-config groups; 256/256 decode recomputation |
| L1 | Isolated function gates | 5 gates: sampling RC+kT/C (7168 points), OU+AZ+DAC, merged return, comparator, 10 V range |
| L2 | N8 smoke | Events and codes, **no spectrum** | N8 plain / tap / two private CAAZ N8 |
| L3 | Full-graph N256 | Real simulation + FFT | **Current normal baseline (only promoted result)**; other historical N256 under different configs |
| L4 | Archived formal verification | as-run replay, frozen coefficients, holdout | `accepted=false` calibration chain, pre-registered holdout 117.458 dB |
| L5 | Proxy physical evidence | Behavioral non-ideality proxies | RA OU observations, σVX/σVY proxies — **proxies, not physics** |
| L6 | PEX / silicon / power-area | Requires circuit implementation | **None** |
| L7 | Signoff | Full PVT, DNL/INL, multi-tone multi-seed | **None** |

> Every "cannot claim" rests on one rule: **lower-level evidence must not be promoted to a higher-level conclusion.**

### 2.4 Conflicting state sources (to be fixed in M0)

| Source | Claims | Reality |
|---|---|---|
| [`release.json`](release.json) | 2026-10-26, `R4/M8/F2/600MHz/N8`, SHA `8f12e65a…`; `canonical_mac_root` points to `项目库/outputs/` | Path retired, SHA stale, no `status` field |
| [`state/SESSION_READY.json`](state/SESSION_READY.json) | 10-27, `display_compile_N8_bits…visual_review_required` | N256 was formally released long ago; two `figures` blocks carry different SHAs |
| Other 5 `state/*.json` | All frozen at 10-26/10-27 | Historical receipts |
| [`state/applied_config.json`](state/applied_config.json) | **11-04T18:33:23Z, SHA `9197…`, `configuration_source=factory`** | ✅ **Only source matching production** |
| [CHECKPOINT.md](CHECKPOINT.md) | 219 KB / 665 lines, reverse-chronological, multiple "current authoritative" blocks | Head holds the 11-05 pause decision; the rest still references obsolete `/tmp` paths |

M0 will converge this into a machine-readable `CURRENT.json`; see [PROJECT_PLAN.md §5](docs/PROJECT_PLAN.md).

---

## 3. Objectives: one project, five acceptance baselines

| Baseline | Source | Key quantitative constraints | Status |
|---|---|---|---|
| **A Product spec / I/O contract Rev0.3** | [SPEC.md](docs/SPEC.md), [spec.yml](docs/spec.yml), [ALIGNMENT.md](docs/ALIGNMENT.md) | 180 nm, 5 MS/s / 200 ns, FSR **8.192 V**, SNR ≥100 dB / SINAD ≥98 dB / THD ≤−105 dBc, INL ≤±4 ppm, DNL <1 LSB20, AD7961 CP-32-7, single LVDS 250 MHz, 32-bit `W[31:0]` frame, fixed N−2 read slot | Current normal uses FSR 10 V, no LVDS, no calibration, no static linearity → **different baseline, cannot be judged compliant** |
| **B Rev0.1/0.2 historical alignment** | `ALIGNMENT.md:11-37` | 4 lanes × 50 MHz, BANK/OVR sideband, 6+15 DT | "Migration history only, cannot override Rev0.3" |
| **C Behavioral acceptance contract** | [behavioral_acceptance.md](design/behavioral_acceptance.md) | Milestone A (8 codes) → B (256 codes); 11 automatic checks; `budget_missing` forbids claiming compliance | A/B did run, but `:63` states no error allocation and no SNDR/power target exists |
| **D Engineering / scheduling drafts** | 4 files in [design/](design/) | Single entry, single parameter source, warm `sim()` ≤5 s, ~48 unique event instants/slot | Draft banner: "contains unimplemented ideas, not proof of current integration" |
| **E Current paper-normal working point** | This README §2 · CHECKPOINT 11-04/05 | 5 MS/s, FSR **10 V** (interpretation of the paper's 5 Vp), single physical frontend, N=256, non-idealities jointly ON | Only promoted result: SNDR 99.133 dB |

> ⚠️ [`docs/MODEL_PLAN.md`](docs/MODEL_PLAN.md) and `docs/DEFINITIONS/ProductRev0.5/` are **historical design-input snapshots**, not the current roadmap. The only active roadmap is [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

### 3.1 Paper migration boundaries

| Direction | Adopted | Not adopted / progress |
|---|---|---|
| **UESTC CICC 2026** (architecture base) | 6b pre-conversion, 10b effective DT, DAC1 charge residue, 32× RA/AZ, CINC CT, 12 D2, 8 tracking / 7 feedback | Edge timings, A0/poles, parasitics, noise and process parameters are undisclosed → all are **engineering assumptions**. 100 dB / 3.6 mW / 0.53 mm² are silicon results with no counterpart here |
| **PKU/THU VLSI 2025 CAAZ** | Input-side two-phase chopping, even-frame AZ write / odd-frame reuse, full output polarity recovery | Private test model `63283fd769ac…` passed two N8 runs (16.21 s / 19.17 s, 8 valid codes, 575 RA next→old bitwise matches); **not promoted, no SNDR**; graph-level AZ write noise OFF |
| **ADI ISSCC 2024** | 18-slice RDAC pool concept, DEM/dither, public-information calibration | Physical v2 still a candidate: 558-word FE owner, dual QDAC with 1039 Cu each, ~119.178 pF/half (the **per-half interpretation is a model assumption**); FrameAvg not built, 10 MS/s not approved |

See [CAAZ_ADI.md](docs/CAAZ_ADI.md). `docs/CHOP_AZ_SPEC.md` is a **residual-side four-phase historical proposal** and must not be confused with the input-side two-phase CAAZ.

### 3.2 Reproduction verdict

**Not reproduced — and until now the project had no acceptance criterion for deciding reproduction.**

| Paper condition | Project state | Comparable? |
|---|---|---|
| 100 dB SNDR, 3.6 mW, 0.53 mm², 5 MS/s, silicon | 99.133 dB, behavioral, no power/area, 256-point FFT | No |
| ~7 dB tracking-averaging benefit | M1/M8 control **never run**; 9.03 dB theoretical ceiling forbidden as a benefit | No |
| 20k-point spectrum | 256 points | No |
| Off-chip LMS foreground calibration | calibration / frozen / Bank / transport / DEM / dither all OFF | No |
| Edge timings, A0/poles, parasitics, noise, process | Undisclosed → engineering assumptions | No |

No paper-comparison or gap report exists anywhere in the repository; all existing `comparison.*` files compare runs with runs. `99.4 dB` appears only as a budget / "reproduce under equal conditions" phrase, **not bound to a specific figure or measurement condition (to be confirmed)**. Full evidence: [ENGINEERING_ANALYSIS.md §5.4](docs/ENGINEERING_ANALYSIS.md).

### 3.3 Design constraint chain: using this project to guide a circuit design

The sections above describe *what the project is*. If the goal is to *design silicon*, a different chain is needed: **system targets → input-referred error budget → block specs → device parameters → verification gates**. That chain was explicitly missing (`design/behavioral_acceptance.md:63`) and has now been built for the **Rev0.3 product spec**: see [🎯 ERROR_BUDGET_REV03.md](design/budget/ERROR_BUDGET_REV03.md).

| What a designer needs | Rev0.3 value | Current model |
|---|---|---|
| Input-referred noise ceiling (SNR 100 dB, −1 dBFS, FSR 8.192 V) | **25.8134 µV rms** | — |
| Harmonic ceiling (THD −105 dBc, controlling) | **14.5159 µV rms** | — |
| Sampling capacitor minimum (kT/C at 50% power) | **24.7109 pF** | 28.0521 pF → 44.04% of noise power |
| Sampling switch Ron ceiling (12.5 ns conservative window) | **35.38 Ω** | 20 Ω, τ 0.563 ns |
| Aperture jitter (100 kHz / 1 MHz extension, entire budget) | **15.92 ps / 2.52 ps** | jitter OFF |
| RA output noise / stage-2 comparator input noise | ≤**319.92 / 218.55 µV rms** (must fold back to ≤10.00 / ≤6.83 µV *after* tracking) | 512.8 / 286.9 µV rms; first-order folding exceeds the limits |
| Reference / AZ noise budget | 8.1629 / 7.3011 µV rms | **Not implemented** |
| INL / DNL | ±32.768 / <7.734 µV | No measurement |

⚠️ Three caveats: ① all figures use the **Rev0.3 8.192 V** baseline — the current normal workpoint is 10 V with a noise ceiling 1.49× larger in power, so 99.133 dB says nothing about compliance; ② `spec.yml:57` still has the 28 pF per-half / differential-total definition as TBD — if it is the total, each half is ~14 pF and the sampling allocation jumps to ~88%, invalidating the table; ③ the budget is **`NOT_CLOSED`**: 18% of noise power has no model and 22% depends on an unmeasured tracking benefit. The 79 checks in [`verify_budget.py`](design/budget/verify_budget.py) prove the *analytic chain is self-consistent*, not that any block passes.

---

## 4. Architecture and how it works

### 4.1 Signal chain

```
Stimulus/Driver → Sample/CDAC1 (18 slices × 38 columns) → SAR1 (6b coarse auxiliary + 10b effective DT)
  → DAC1 charge residue → 32× RA/AZ (ordinary) → CINC continuous-time second stage (12 D2)
  → 8 tracking comparisons / 7 physical feedback → RawRecord → FPGA nominal reconstruction (code20)
```

- **Stage 1**: 10-bit effective DT SAR with an internal 6-bit coarse auxiliary; `D1[10:0]` (11 RAW bits).
- **Interstage**: one shared 32× RA with auto-zero; **no extra S/H after RA** holds the whole second-stage conversion (`SPEC.md:18`, `READ_GRAPH.md:20`).
- **Stage 2**: CINC-coupled 11-bit continuous-time SAR, `D2[11:0]`, 2-bit interstage redundancy; 8 tracking decisions, `DT[7:0]`.
- **Digital**: FPGA/Simulink subsystem reconstructs with nominal weights; the off-chip training reference **must not read** internal capacitors, held voltages or residue.
- Top-level `CodeValid` is a legacy Bank-path per-frame eligibility flag, **not sample validity** (`READ_GRAPH.md:42`).

### 4.2 State owners and the 200 ns event calendar

Only **three standard UnitDelay state owners**, no second charge memory (`READ_GRAPH.md:44`):

| Owner | Width | Content | Source |
|---|---|---|---|
| `A/SampleCharge` (FE353) | 353 doubles | 318:335 actual aperture, 336:353 acquisition instants, 18-slice plan | [frontend/behavior_frontend_unpack.m](current/src/frontend/behavior_frontend_unpack.m) |
| `A/RaCtState` (RA48 / BK48) | 48 doubles | RA/AZ/CT continuous state | [physics/behavior_backend_unpack.m](current/src/physics/behavior_backend_unpack.m) |
| `A/SarState` (SAR51 / SC51) | 51 doubles | 1:26 scalars, 27:38 twelve D2 signs, 39:45 seven TA signs, 46:51 pending | [control/behavior_sar_pack.m](current/src/control/behavior_sar_pack.m) |

Calendar: [control/behavior_calendar.m](current/src/control/behavior_calendar.m), 200 ns period, 250 ps tick, **48 event groups / 73 tokens**.

| Time | Event |
|---|---|
| 0 ns | `cnv` |
| 12.5 ns | `coarse_latch`; 5 groups `fine_prepare 12.5+3.75k` / `fine_decide 15+3.75k` / `fine_feedback 16.25+3.75k` (k=0..4) |
| 31.25 ns | `ra_start` (AZ write window 0–31.25 ns) |
| 43.75…72.5 ns | 12 groups `d2_prepare 43.75+2.5k` / `d2_decide 45+2.5k` / `d2_feedback 46.25+2.5k` (k=0..11); `d2_end 73.75 ns` |
| 75…83.75 ns | 8 × `ta_compare 75+1.25m` (m=0..7), **only m<7 has `ta_feedback`** → 8 comparisons / 7 physical updates |
| 85 ns | `tracking_end` (next-tick visibility of TA m=7) |
| 86.25 ns | `raw_latch` (RawReady) |
| 90 ns | `release` / analog reset |
| 92 ns | next acquisition after the 2 ns guard |
| (transport ON) 138 ns | `frame_ready`, a 49th group |

> Multiple distinct events may share one instant — **never deduplicate by time alone** (`behavioral_frontend.md:180`). Same-edge priority is resolved by `[tick, priority]` sorting.

### 4.3 RAW record and nominal decode chain

RAW order `[D1, D2, DT, sample_id, epoch, valid]`, widths **11 / 12 / 8 / uint32 / uint32 / 1** (`behavior_record_view.m:28`, `behavior_decode.m:27`).

[behavior_decode.m](current/src/digital/behavior_decode.m):

```matlab
c = floor(D1/32);  f = mod(D1,32);
d1Dac = (32*c + 2*f - 1039) * p.vref_v / 1024;
d1V   = d1Dac + p.d1_bias_v;                       % normal: d1_bias_v = 0
d2V   = (p.d2_offset_ra_v + sum(p.d2_weights_ra_v .* d2_bits)) / p.ra_gain;
dtV   = (p.tracking_step_ra_v * dtWeighted) / p.ra_gain;
voltage = ((d1V + d2V) + dtV) + dither;           % POL flips d2V/dtV only, never DAC1/dither
unsat   = voltage * (2^20 / p.fsr_diff_v) + 2^19;
code    = max(0, min(2^20-1, round(unsat)));      % nearest, ties away from zero
```

Constraints: `ra_gain == 32`, `tracking_mode='finite_sinc2'`, `calibration_mode='off'`, 12 positive `d2_weights_ra_v`, `fpga.sinc2_scale == 1/8`. Digital calibration is **not implemented** and errors out if enabled.

### 4.4 Why SINC² divides by 8, not 36

`dtWeighted = sum(weights .* dtSigns) / 8` with `weights = 8:-1:1` (sum = **36**). The source comment is explicit:

> "the plain average would divide by sum(weights)=36. This chain divides by 8 because **decision eight has no physical update while its raw LSB still carries digital weight one**. That is deliberate, not a normalisation bug." (`behavior_decode.m:21-23`)

The 8th tracking comparison contributes a **digital** LSB only, with no 8th physical capacitor feedback. Changing `/8` to `/36` is a common misreading and suppresses the DT term by roughly 13 dB. No S/H after RA, 8 comparisons / 7 feedbacks, and the finite SINC² must be understood together.

### 4.5 Disclosed vs assumed

| Category | Content |
|---|---|
| **Paper/spec inputs** | Architectural skeleton, ~90 ns conversion, 8 tracking / 7 feedback, 32× RA, CT second-stage concept |
| **Engineering assumptions (not disclosed)** | All edge switch instants, FSR **10 V** interpretation ("5 Vp differential = 10 Vpp FSR"), A0=1e4 / UGB=1.2 GHz / single pole, Cp=100 fF/half, σunit≈0.068%, CINC 900 fF, σVX 0.512785 mV / σVY 0.286929 mV, 1039×27 fF per-half interpretation, the complete DAC1 switching codebook, 28 pF top-cap interpretation |
| **Provenance labels** | `normal_parameters.m:180` → `assumptions.status='EXPECTED_OPERATING_ESTIMATE_NOT_PDK_TYPICAL'`; `state/applied_config.json` lists 6 assumptions |

> Cite these numbers **together with their assumption labels**. They are not PDK statistics, not paper specifications and not silicon measurements.

---

## 5. Parameters and configuration

### 5.1 Three configuration entries

| File | Role | After editing |
|---|---|---|
| [config/adc_parameters.m](config/adc_parameters.m) | Factory baseline and editable inputs: `N`(256), `input_offset_v`(0), `input_level_dbfs`(−1), `input_frequency_hz`(97656.25), `input_phase_rad`(0.731); `single_bank_factory_base()` builds the P skeleton | `SAR20('apply')` |
| [config/normal_parameters.m](config/normal_parameters.m) | Normal non-ideal operating point: 6 switches `useSamplingMismatch / useCtMismatch / useKtc / useRaNoise / useCmp / azMode='ordinary'` plus all σ/Cp/τ/A0/UGB/temperature/seed values | `SAR20('apply')` |
| [config/normal_10v_configuration.m](config/normal_10v_configuration.m) | Range and nominal digital scale: asserts the 8.192 V baseline → builds the 10 V scale (`vref1=5`, `delta=10/1024`, `output_lsb=10/2^20`); validates weights against the archived nominal CT geometry in `nominal.mat` (tol 1e-12) | `SAR20('apply')` |

Four case builders: [make_adi_cases.m](config/make_adi_cases.m) (2×2×2 = 8 DEM/dither/mismatch cases), [make_jitter_cases.m](config/make_jitter_cases.m) (6 N8 jitter cases), [make_training_case.m](config/make_training_case.m), [make_training_protocol.m](config/make_training_protocol.m) (2048 train / 1024 holdout with thresholds). [config/nominal.mat](config/nominal.mat) is a v5 MAT holding nominal CT geometry and FPGA weights (`nominal_weight_source='DERIVED_INTEGER_NOMINAL_GEOMETRY_NO_ACTUAL_CAPACITANCE'`).

### 5.2 Active normal values

| Group | Parameter | Value | Nature |
|---|---|---|---|
| Timing | `Ts_s` / `fs_hz` | 2e-7 s / 5 MHz | contract |
| Input | `amplitude_v` / `frequency_hz` / `phase_rad` | 4.456254690668728 V / 97656.25 Hz / 0.731 | coherent bin5 |
| Range | `fsr_diff_v` / `vref_v` / `sar1.delta_v` | 10 V / 5 V / 0.009765625 V | **10 V is an assumption** |
| Sampling | `tau_sample_s` / guard / Ctop | 0.563041298 ns / 2 ns / 28.1520649 pF/half | assumption |
| kT/C | T / seed / equilibrium σ | 298.15 K / 20261027 / 17.256 µV rms | assumption |
| Mismatch | `σunit` / seed | 0.06804138 % / 20261104 | assumption, one chip |
| DAC | `tau_dac_s` / coupling | 0.5 ns / true | assumption |
| RA | A0 / UGB / NG / τ / Vos | 1e4 / 1.2 GHz / 33.5834 / 4.4541 ns / +1 mV | assumption |
| RA noise | `sigma_vx_rms` / seed | 0.51278539 mV / 20261104 | A1-channel OU proxy |
| Comparator | `sar2_noise_rms_v` / seed | 0.286928737 mV / 20261105 | **SAR2/TA only**; SAR1-fine and Flash are 0 |
| AZ | mode / write τ / leak τ | ordinary / 1 ns / 10 ms | no random AZ noise |
| Digital | `ra_gain` / `tracking_mode` / `calibration_mode` / `d1_bias_v` | 32 / finite_sinc2 / off / 0 | nominal chain |
| OFF | jitter / DEM / dither / training / cal_cfg / frozen / bank / transport | all false | see §6 |

All 33 top-level keys are in the run's `parameters.json`; the full 35-key configuration is in [state/applied_config.json](state/applied_config.json).

### 5.3 Two easily misused fields

- **`P.ni` is a summary derived from physical configuration, not a switch** (`docs/PARAMETERS.md:26,83`). Setting `P.ni.xxx=true` turns on no physical effect.
- **`P.debug.adi_enabled` enables observation only, not physics** (`docs/PARAMETERS.md:126`). When true it merely permits N8 logging of selected slices, shifts, target charge, CNV tail and control counts.

---

## 6. Non-ideality coverage

From [NORMAL_NONIDEALITY_COVERAGE.md](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) and a file-by-file check of `current/src/`.

### 6.1 Implemented and currently ON

| Effect | Implementation | Active value |
|---|---|---|
| Sampling kT/C | `frontend/behavior_frontend_step.m:85-111,322-342` | 17.256 µV rms; 7168-point gate normalized variance 0.9803 |
| Stage-1 capacitor mismatch | `config/normal_parameters.m:63-76,109-116`; `physics/behavior_backend_step.m:298-309` | σunit 0.068%, 8 identical segments |
| Comparator noise (**SAR2/TA only**) | `control/behavior_comparator_sample.m:36-53` | σVY 0.286929 mV |
| RA OU noise (A1-channel proxy) | `physics/sar20_ra_ou_increment.m:1-58` | σVX 0.512785 mV |
| RA finite gain / bandwidth | `physics/behavior_backend_step.m:267-273,88-106` | A0 1e4, UGB 1.2 GHz, NG 33.58 |
| Ordinary AZ | `control/behavior_az_schedule.m:1-94`; `behavior_backend_step.m:196-265` | ordinary, write 0–31.25 ns, POL `[+1,−1,−1,+1]` |
| DAC finite settling | `physics/behavior_dac_forcing_from_frontend.m`; `behavior_backend_step.m:350-381` | τ 0.5 ns, coupling true |
| Parasitics | `frontend/behavior_frontend_step.m:275`; `physics/behavior_backend_step.m:310-313` | front 100 fF/half, RA output 0.5 pF/half |
| Sampling RC settling | `frontend/behavior_frontend_step.m:200-249` (exact sinusoidal particular solution) | τ 0.563 ns |

### 6.2 Implemented but currently OFF (code exists)

`jitter` (`frontend/behavior_jitter_parameters.m` + 6 case builders), `dither` (`digital/behavior_public_dither.m`), `DEM` (`frontend/behavior_frontend_step.m:135-136`), `calibration/train/frozen/Bank` (24 `.m` in `current/src/calibration/`), `transport/LVDS` (10 `.m` in `current/src/transport/`), `finite slew` (clips only when `isfinite(slew_v_per_s)`; currently `Inf`).

### 6.3 Explicitly "not implemented"

| Item | Source |
|---|---|
| `reference_recovery` | `model/behavior_ra_noise_guard.m:90` throws `Reference recovery is not implemented.` |
| `az_noise` / `reference_noise` / `nonlinear_ra` / `replica_delay` | `physics/behavior_backend_step.m:434-437` |
| SAR1-fine / Flash comparator noise | `model/behavior_applied_note.m:46`, `behavior_ra_noise_guard.m:119` |
| Digital-side calibration | `digital/behavior_decode_parameters.m:20`, `behavior_decode.m:94-95` |
| Finite-RC sampling with displaced aperture | `frontend/behavior_frontend_step.m:64-66` |
| Run-time EN mode changes / same-run Bank ARM | `transport/behavior_transport_step.m:22`, `calibration/sar20_bank_owner_step.m:21` |

### 6.4 No implementation evidence in source

`timing_mismatch`, `dac_sampling_bw`, `online_shuffler` — appear only as ideas in SPEC / MODEL_PLAN (to be confirmed).

### 6.5 Consequence

`NORMAL_NONIDEALITY_COVERAGE.md:27`: "this N8 is a joint run of all listed enabled items; **it cannot separately measure the single-source contribution** of kT/C, mismatch, finite settling, AZ, RA or comparator noise. RA noise is only an A1-channel proxy, comparator noise covers only SAR2/TA; driver and reference noise, other RA stages, AZ noise and SAR1/Flash noise remain out of scope."

This is the **primary scientific problem** addressed by [M1 (single-source ablation + input-referred noise budget)](docs/PROJECT_PLAN.md): not adding features, but making the existing baseline attributable.

---

## 7. Running and reproducing

### 7.1 Environment

| Item | Requirement |
|---|---|
| Host | Windows, project root `D:/Academic/Projects/sar20m1/SAR20` (the macOS copy is a mirror plus offline analysis, no MATLAB) |
| MATLAB | R2024a Update 6 (`24.1.0.2689473 (R2024a) Update 6`) |
| Toolkit | `dependencies/toolkit/` (MathWorks Simulink Agentic Toolkit 2026.10.b); `apply` runs `require_toolkit` |
| Scheduling | The license is held by a resident GUI instance; `matlab -batch` exits immediately. Use the `SAR20_MatlabControl` scheduled task COM channel. `license('test')=1` **does not** mean `checkout` works |

### 7.2 All `SAR20.m` actions

| Action | Behavior | Loads / saves SLX | Writes |
|---|---|---|---|
| `setup` | Removes retired runtime paths, `addpath(genpath(src),config,'-begin')`, `verify_project_resolution` | neither | nothing |
| `open` | `open_system(modelFile)`; warns `SAR20:applyRequired` if `state/applied_config.json` is missing | opens (no save) | nothing |
| `apply` | `P=adc_parameters()` → `behavior_prepare_configuration(P)` → `assignin(ws,'P'/'DecodeP')` → **`save_system(...,'SaveModelWorkspace',true)`**; updates 4 block annotations | **saves SLX** | `state/applied_config.json` |
| `check` | Reads ModelWorkspace.P → `set_param(model,'SimulationCommand','update')` | loads, no save | nothing |
| `run` | `require_applied_model` → spectrum eligibility → `run_saved` real simulation and archive | loads, no save | `runs/behavior_<UUID>/`, `runs/latest_behavior_run.json` |
| `sample` | `behavior_sample_plot` + `behavior_sample_explain`; **returns before `load_system`, does not load SLX** | neither | `runs/sample_<UUID>/` |
| `calibration` | Unconditionally throws `singleBank:calibrationUnavailable` | no | nothing |

> `apply` embeds P into the SLX and saves it, so **SLX hash = f(model structure + embedded P)**; 205 runs produced 205 hashes. Earlier "model unchanged" notes predate this correction (CHECKPOINT.md:141-150).

### 7.3 Standard flow

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open')
% after editing config/adc_parameters.m (N / input) or config/normal_parameters.m (non-idealities):
SAR20('apply')
SAR20('check')
r = SAR20('run');
s = SAR20('sample', 5, r.run_path);
```

`sample` requires exactly 2 arguments: a non-negative integer `id` and a `runPath` containing `parameters.mat` / `simout.mat` / `summary.json` (each ≤300 MB); its output directory must be outside the selected run.

### 7.4 What one `run` writes

`SAR20('run')` writes to **`runs/behavior_<UUID>/`** (project root, not `analysis/`):

| File | Content |
|---|---|
| `summary.json` | Full report: status, SHAs, records, metrics, elapsed time, `error_identifier` on failure |
| `parameters.mat` | Complete resolved P (`-v7.3`) |
| `parameters.json` | Readable projection of P (`config_identity` states MAT is authoritative) |
| `SarAdc.slx` | Model copy, SHA verified against `report.model_sha256` |
| `source.zip` + `source_manifest.json` | `current/src/**/*.m` + `config/*` + `SAR20.m` with per-file SHA (117 items here) |
| `simout.mat` | Raw simulation output, written **before any capture/validation** (including failed/stopped runs) |
| `selected.mat` | `selected={raw,code20,time_s,raw_fields}` + `metadata`; validates N consecutive IDs, epoch, valid, code range |
| `spectrum.mat` | Five metrics (only when spectrum-eligible) |
| Conditional | `training*.mat/json` (cal_cfg ON), `bank_qualification.json` (bank ON) |
| `runs/latest_behavior_run.json` | Latest run path and `summary_sha256` |

`analysis/behavior/public_normal_20261105/release_actual/behavior_12d08121-…/` is the **macOS mirror** of that run (9 files). ⚠️ `release_receipt.json` in the parent directory is **not produced by `SAR20('run')`**; it comes from the Windows-side controller (script not yet located) — distinguish "entry-point artifact" from "release-process artifact".

### 7.5 Four traps

1. **GUI Run does not read the factory files** — it uses the loaded ModelWorkspace.P and creates no public archive. If an edit "did not take effect", check `apply` first.
2. **`N < 256` computes no dynamic metrics** (`not_run_short_capture`). N8 (≈3 s) is for events and codes only.
3. **`matlab -batch` exits immediately** (license held by a resident instance); `license('test')=1` is not `checkout`.
4. **Never compare N256 runs from different configurations.** Grouping by 6 top-level fields once produced a fake "52.9 dB SNDR spread"; grouping by the SHA-256 of the whole `parameters.json` yielded 9 truly identical groups with `0.000e+00` spread. Original lesson: "prove you are comparing the same thing before comparing numbers."

---

## 8. Debugging

### 8.1 macOS zero-MATLAB read-only probe

[analysis/local_debug/sar20_probe.py](analysis/local_debug/sar20_probe.py) **does not load the model, call MATLAB, simulate, or modify any project file**:

```bash
cd analysis/local_debug
PY=../../dependencies/analysis_env/bin/python   # or any Python with h5py / numpy / scipy

$PY sar20_probe.py info                  # run identity + active parameters + P.ni matrix
$PY sar20_probe.py decode --all          # recompute 256 code20 values vs MATLAB
$PY sar20_probe.py decode --id 5         # full D1/D2/DT decode chain for one sample
$PY sar20_probe.py diff <runA> <runB>   # field-by-field parameter and code diff
$PY sar20_probe.py html                 # regenerate the offline panel
```

Or open [sar20_debug_report.html](analysis/local_debug/sar20_debug_report.html) (single file, offline, 256 embedded real records).

Measured: `decode --all` **256/256 exact match**; ID 5 → D1 = 4.3408203125 V, D2 = +1.609375 mV, DT = −19.53125 µV, code = 979623. `diff` ≈0.2 s (prefers the full `parameters.json` projection; full `mat_value` expansion of P takes ~30 s, the needed subtrees ~0.002 s).

> **Evidence boundary**: this is **L0 offline recomputation**, not simulation, synthesis or signoff. Its value is as a first gate for "did a parameter/source edit break the digital decode chain".

### 8.2 MATLAB event-level `sample`

`SAR20('sample', id, runPath)` is the **only** channel for 5-way log / RAW / record alignment, event waveforms and Chinese explanations — and needs no model load. No sample report has been produced on macOS since the normal N256 release. The release receipt lists 9 logs: `raw_log / ready_log / record_log / record_ready_log / event_log / front_log / back_log / control_log / code_log`.

### 8.3 Known silent tool-chain failure

⚠️ `read_logger_plan()` in [analysis/mat_reader.py](analysis/mat_reader.py) **fails** on the current 32-logger `simout.mat`: `indexed 0 logger data arrays for 32 SimulationOutput variables`. No document previously recorded this; the original tool is **unfixed**. The new probe does not parse that layout and does not fabricate an event timeline. Do not use `read_logger_plan` for event analysis.

### 8.4 Debug decision tree

| Symptom | Check first |
|---|---|
| Parameter edit had no effect | Missing `SAR20('apply')`; `utc` / `model_sha256` in `state/applied_config.json` |
| Metrics disappeared | `N < 256`? `spectrum_eligibility` field |
| Two runs disagree | `sar20_probe.py diff` on the full `parameters.json` SHA before discussing numbers |
| Codes changed, cause unknown | `decode --all` to validate the chain, then `decode --id` for D1/D2/DT breakdown |
| Event waveforms / logs needed | `SAR20('sample', id, runPath)`; **not** `read_logger_plan` |
| Need physical non-ideality attribution | Not possible today → [M1](docs/PROJECT_PLAN.md) |

---

## 9. Archive and evidence map

| Path | Content | Status |
|---|---|---|
| [public_normal_20261105/release_actual/](analysis/behavior/public_normal_20261105/release_actual/) | Authoritative N256: release receipt, run mirror, diagrams, GUI export receipts, active manifest | ✅ Only promoted result |
| [normal_workpoint_20261104/](analysis/behavior/normal_workpoint_20261104/) | Joint N8/N256, 5 function gates, coverage table, FFT and settling plots, Windows controller scripts | Working-point evidence |
| [analysis/behavior/](analysis/behavior/) (52 experiment dirs, ~213 MB) | 10-26 → 11-05 as-run history: LVDS, training/holdout, DEM/dither, RA OU, jitter stress, readability refactor | 📜 Archive, configurations differ |
| [analysis/local_debug/](analysis/local_debug/) | Zero-MATLAB probe and offline panel | 🆕 L0 tool |
| [paused_work/](analysis/debug_ui_20261105/paused_work/) | 210 paused candidates, `candidate_sources_paused.zip` (SHA `3504a9a9…`), `PAUSE_INDEX.json`, `RESUME.md` | ⏸️ Not promoted |
| [_preserved/](_preserved/) | Pre-change backups including the original README / .gitignore in `before_github_20261105/` | 📜 Rollback |
| [CHECKPOINT.md](CHECKPOINT.md) | 219 KB / 665 lines reverse-chronological log, **newest at top** | 📜 To be frozen in M0 |

Historical full-graph results (**different configurations, never compare them**) and the per-line reading are in [ENGINEERING_ANALYSIS.md §5.2](docs/ENGINEERING_ANALYSIS.md): NI-off 109.827 dB, combined jitter 95.788 dB, finite DAC τ=1 ns 106.913 dB, 6-seed RA OU 100.655±0.414 dB, pre-registered holdout 117.458 dB (`accepted=false`).

---

## 10. Known issues and risks

| Severity | Risk | Impact |
|---|---|---|
| **High · conclusion** | Baseline not attributable (joint single point, no ablation, no input-referred noise budget) | No ΔdB of any CAAZ/ADI/calibration change can be explained; quantitative paper comparison impossible |
| **High · engineering** | Production stalled, candidates piled up (11-05 SHA comparison: 116 files, 0 differences; 8 archive/rollback events) | Work cannot become a deliverable version; rollback cost grows |
| **High · engineering** | No single source of truth (5 conflicting state sources; not a git repo until 11-05) | Recovery may pick the wrong config; a 62-digit SHA transcription error already broke a preflight |
| **Medium · technical** | Incomplete non-ideality coverage, mostly assumed parameters | 99.133 dB cannot be extrapolated or treated as PDK/paper nominal |
| **Medium · engineering** | `read_logger_plan` silently failing | Wrong conclusions if the old tool is used for event parsing |
| **Medium · reproducibility** | Single Windows / MATLAB / license point | No one-click reproduction elsewhere; CI impossible |
| **Medium · compliance** | 27 third-party PDFs + 43 MB SATK redistributed | [NOTICE.md](NOTICE.md) documents provenance and removal process |
| **Low-medium · hygiene** | ~1.3 MB of 596 MB is production | High clone/review cost; venv and pyc excluded from git but still on disk |

**Root-cause chain**: frequent goal switches → unpromoted candidates → SHA/receipt/archive machinery → evidence bloat + split state → higher recovery cost → preference for another isolated candidate instead of promotion; in parallel, "unattributable baseline → benefit cannot be judged → no promotion". See [ENGINEERING_ANALYSIS.md §7](docs/ENGINEERING_ANALYSIS.md).

---

## 11. Roadmap and plan

The complete executable plan is **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** (prerequisites, commands, acceptance gates, backups, rollback, checkpoints, authorization boundaries). **M0.5 "design constraint chain" was delivered on 2026-11-05** ([§3.3](#33-design-constraint-chain-using-this-project-to-guide-a-circuit-design)) and is the acceptance yardstick for M1; M0–M4 below remain proposals. Summary:

| Milestone | Action | Change model? | Done when |
|---|---|---|---|
| **M0** | Machine-readable `CURRENT.json` single source of truth; mark old state sources archive; fix stale paths | No | Any new session can determine "what is current / what counts as done" within 1 minute |
| **M1** | Fixed N256/seed/FSR **single-source ablation matrix** + input-referred noise budget | No (parameter injection); needs Windows scheduling authorization | Every implemented non-ideality has an independent ΔSNDR and the budget table is comparable to the paper |
| **M2** | Same-baseline 20k-point spectrum + M1/M8 7 dB control + calibration/holdout review | No (parameter level); needs authorization | Can state exactly how far reproduction got, which items differ, by how many dB |
| **M3** | Promote **one** of CAAZ / debug UI to production through N8 bit-gate → N256 regression → doc sync | **Yes, explicit authorization**; scope/backup/rollback first | Production SLX SHA changes and README / CURRENT.json are synchronized |
| **M4** | Full ADI v2 18-pool / dual QDAC, 10 MS/s | Yes, architectural + separate approval | Defined as a new milestone |

**Priority M0 → M1 → M2; do not open a new feature line before M3.** M1/M2 produce the precondition for judging any benefit; without them, M3 can only end in another archive.

> Authorization boundary: any change to `current/`, the SLX, or architecture **requires explicit authorization** and per-milestone checkpoints. This README and the plan do not themselves authorize any model change.

---

## 12. Repository map

| Path | Content | Production |
|---|---|---|
| [`SAR20.m`](SAR20.m) | Sole public entry | ✅ |
| [`current/src/`](current/src/) · [`current/models/`](current/models/) | 108 `.m` + the sole `.slx` | ✅ |
| [`current/calibration/`](current/calibration/) | Calibration-related archived data | 📜 |
| [`config/`](config/) | Factory parameters, case builders, nominal MAT | ✅ |
| [`state/`](state/) · [`release.json`](release.json) | Applied config and historical receipts | ⚠️ Mixed; only `applied_config.json` valid |
| [`docs/`](docs/) | Specs, reading guide, parameters, schemes, full analysis, project plan, papers | Docs |
| [`design/`](design/) | 2026-10-26 acceptance / engineering / frontend / scheduling drafts | 📜 Unimplemented ideas |
| [`analysis/behavior/`](analysis/behavior/) | 52 experiment directories of real as-run evidence | 📜 Archive |
| [`analysis/local_debug/`](analysis/local_debug/) | Zero-MATLAB probe and offline panel | 🆕 |
| [`analysis/debug_ui_20261105/`](analysis/debug_ui_20261105/) | Paused candidates and recovery index | ⏸️ |
| [`_preserved/`](_preserved/) | Pre-change backups | 📜 |
| [`dependencies/toolkit/`](dependencies/toolkit/) | MathWorks SATK 2026.10.b (third party) | Runtime dependency |
| `dependencies/analysis_env/` | Local Python venv (**regenerable, not in git**) | Ignored |
| [`CHECKPOINT.md`](CHECKPOINT.md) | Reverse-chronological recovery log, newest on top | 📜 History |

---

## 13. Document index

| Document | Purpose |
|---|---|
| [**ERROR_BUDGET_REV03.md**](design/budget/ERROR_BUDGET_REV03.md) | **Guide a circuit design**: Rev0.3 targets → input-referred error budget → block specs → device parameters → gates; with JSON, binding CSV and verifier |
| [**PROJECT_PLAN.md**](docs/PROJECT_PLAN.md) | **Only active roadmap**: M0–M4 gates, commands, rollback, evidence levels |
| [ENGINEERING_ANALYSIS.md](docs/ENGINEERING_ANALYSIS.md) | Systematic diagnosis: objectives / timeline / architecture / evidence ledger / governance / risk tiers |
| [CAAZ_ADI.md](docs/CAAZ_ADI.md) | What each of the three papers contributes; CAAZ N8 evidence; ADI candidate boundary |
| [SPEC.md](docs/SPEC.md) · [spec.yml](docs/spec.yml) · [ALIGNMENT.md](docs/ALIGNMENT.md) | Rev0.3 product contract, machine-readable constraints, migration history |
| [MODEL_PLAN.md](docs/MODEL_PLAN.md) · [READ_GRAPH.md](docs/READ_GRAPH.md) · [PARAMETERS.md](docs/PARAMETERS.md) | Historical design input / diagram reading / field semantics |
| [behavioral_acceptance.md](design/behavioral_acceptance.md) | Milestones A/B, 11 automatic checks, `budget_missing` rule |
| [NORMAL_NONIDEALITY_COVERAGE.md](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) | Implemented / enabled / uncovered item-by-item table |
| [PAPERS/INDEX.md](docs/PAPERS/INDEX.md) | 27 PDFs with path, provenance and SHA-256 |
| [NOTICE.md](NOTICE.md) | Third-party licenses, copyright and removal procedure |
| [中文 README](README.md) | Normative Chinese entry page |

---

## 14. Third-party content and license

- `dependencies/toolkit/` is **MathWorks Simulink Agentic Toolkit 2026.10.b**, distributed under its bundled `LICENSE.md` (BSD-3 variant restricted to use with MathWorks products/services); copyright The MathWorks, Inc.
- The **27 PDFs** in `docs/PAPERS/` are third-party literature (IEEE / ISSCC / CICC / vendor datasheets / US patents), kept per the user's explicit "upload everything, strictly complete" decision. Copyright remains with the respective authors and publishers; they are included for research citation and traceability only. Contact via issue for removal.
- This repository's own code and documents **do not yet declare an open-source license**; until a LICENSE exists, do not assume free redistribution or commercial use.
- See [NOTICE.md](NOTICE.md).

---

## 15. Citation

See [CITATION.cff](CITATION.cff). **While reproduction is incomplete, do not cite this model as validation of the paper's results.**

---

<div align="center">

<sub>Last updated 2026-11-05 · Production model `91973cf7…` · Phase: normal baseline released, expansion paused · This page and [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) define the current baseline</sub>

</div>
