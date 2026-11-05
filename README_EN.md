<div align="center">

# SAR20-5 · Behavioral Model of a 20-bit 5 MS/s Two-Step SAR ADC

**Simulink behavioral project · architecture baseline from UESTC CICC 2026 · 5 MS/s single-frontend normal operating point**

[![MATLAB](https://img.shields.io/badge/MATLAB-R2024a%20Update%206-orange)](https://www.mathworks.com/products/matlab.html)
[![Simulink](https://img.shields.io/badge/Simulink-behavioral-blue)](https://www.mathworks.com/products/simulink.html)
[![Rate](https://img.shields.io/badge/5%20MS%2Fs-Fs-brightgreen)](#-current-status)
[![SNDR](https://img.shields.io/badge/SNDR-99.133%20dB%20%40%20N256-blueviolet)](#-current-status)
[![ENOB](https://img.shields.io/badge/ENOB-16.17%20bit-informational)](#-current-status)
[![Status](https://img.shields.io/badge/status-normal%20baseline%20released%20%2F%20debug%20UI%20paused-yellow)](#-current-status)
[![Docs](https://img.shields.io/badge/docs-English-success)](README_EN.md)
[![中文](https://img.shields.io/badge/docs-中文-lightgrey)](README.md)

</div>

> 📌 **Read this first**: this is a **behavioral modeling project**, not a paper-reproduction report and not a tape-out or signoff result.
> The only promoted result is a single N256 run on model `91973cf7…`. The UESTC CICC 2026 paper has **not been reproduced**;
> see the [full analysis](docs/ENGINEERING_ANALYSIS.md#54-成电复现判定).
>
> 🆕 This repository was first pushed from the local project on **2026-11-05**, preserving source, model, all historical evidence, and design documents.

> 中文版（默认首页）：[README.md](README.md)。Both pages are kept structurally aligned.

---

## 🚀 Quick navigation

| I want to… | Go to |
|---|---|
| **Understand the state of this project** | [📊 Full engineering analysis](docs/ENGINEERING_ANALYSIS.md) (objectives / architecture / evidence ledger / risks / roadmap) |
| **Debug on macOS without MATLAB** | [🔍 Local read-only probe](#-local-debugging-no-matlab) · [offline panel](analysis/local_debug/sar20_debug_report.html) |
| **Run / change parameters on Windows** | [▶️ Run and reproduce](#️-run-and-reproduce-windows--matlab) |
| **Check active configuration, metrics, evidence limits** | [📌 Current status](#-current-status) · [non-ideality coverage table](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) |
| **Understand the block diagram** | [docs/READ_GRAPH.md](docs/READ_GRAPH.md) · [docs/PARAMETERS.md](docs/PARAMETERS.md) |
| **Read the CICC2026 / PKU CAAZ / ADI comparison** | [docs/CAAZ_ADI.md](docs/CAAZ_ADI.md) |
| **Read the product specification and I/O contract** | [docs/SPEC.md](docs/SPEC.md) · [docs/ALIGNMENT.md](docs/ALIGNMENT.md) |
| **Resume after an interrupted session** | [CHECKPOINT.md](CHECKPOINT.md) (historical log) · [PAUSE_INDEX.json](analysis/debug_ui_20261105/paused_work/PAUSE_INDEX.json) · [RESUME.md](analysis/debug_ui_20261105/paused_work/RESUME.md) |
| **Browse all references** | [docs/PAPERS/INDEX.md](docs/PAPERS/INDEX.md) |

---

## 📌 Current status

| Item | Value |
|---|---|
| Sole entry point | [`SAR20.m`](SAR20.m) |
| Sole model | [`current/models/SarAdc.slx`](current/models/SarAdc.slx), SHA `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` |
| Production source | [`current/src/`](current/src/), 108 `.m` files, 10 264 lines |
| Authoritative run | `behavior_12d08121-d679-40cd-9ee2-bc334ff42955` ([release receipt](analysis/behavior/public_normal_20261105/release_actual/release_receipt.json)) |
| Configuration | Fs 5 MHz, Fin 97.65625 kHz / bin5, −1 dBFS, differential FSR 10 V, N=256, seed 20261020 |
| Metrics | SNR **99.712 dB** · SNDR **99.133 dB** · SFDR **111.784 dB** · THD **−108.166 dB** · ENOB **16.175 bit** |
| Ideality-off baseline (same range) | SNDR 109.165 dB |
| Runtime | Windows MATLAB R2024a Update 6 at `D:/Academic/Projects/sar20m1/SAR20`; no MATLAB on this macOS host |

### What can and cannot be claimed

✅ **Can claim**: the architectural skeleton and timing narrative match the paper text (6b pre-conversion + 10b effective DT + DAC1 charge residue + 32× RA/AZ + CINC CT second stage + 12 D2 + 8 TA / 7 feedback, ~90 ns conversion); the single N256 behavioral spectrum is self-consistent and bitwise reproducible for identical configuration; the public `apply → cold open → run → sample` chain has actually been executed.

❌ **Cannot claim**: reproduction of the paper's performance, the 7 dB tracking-averaging gain, DNL/INL, a 20k-point spectrum, power/area/PDK data, multi-tone/multi-seed robustness, or any signoff. Current ENOB is 16.17 bit, not 20 bit.

⚠️ **Status on 2026-11-05**: the user explicitly paused the debug-UI objective; all candidates are archived and **no debug candidate has been deployed to production**. CAAZ passed only two private N8 runs; ADI remains a candidate. See the top of [CHECKPOINT.md](CHECKPOINT.md).

---

## 🔍 Local debugging (no MATLAB)

A read-only probe that reads saved real runs directly — it never loads the model, never simulates, and never modifies project files:

```bash
cd analysis/local_debug
PY=../../dependencies/analysis_env/bin/python   # or any Python with h5py / numpy / scipy

$PY sar20_probe.py info                  # run identity + active parameters + NI switch matrix
$PY sar20_probe.py decode --all          # independently recompute 256 code20 words vs MATLAB
$PY sar20_probe.py decode --id 5         # full D1/D2/DT decode chain for one sample
$PY sar20_probe.py diff <runA> <runB>   # field-by-field parameter and code differences
$PY sar20_probe.py html                 # regenerate the offline debug panel
```

Or simply open [`analysis/local_debug/sar20_debug_report.html`](analysis/local_debug/sar20_debug_report.html) — a single offline file with all 256 real records; click any row to inspect its decode chain.

Verified: `decode --all` matches **256/256** MATLAB codes; sample 5 resolves to D1 = 4.3408203125 V, D2 = +1.609375 mV, DT = −19.53125 µV, code = 979623. `diff` completes in ~0.2 s.

> **Evidence boundary**: this probe only performs nominal digital reconstruction (L0 offline audit). It is not a simulation, not synthesis, and not signoff.
> Event-level waveforms and the five aligned logs still require MATLAB `SAR20('sample', id, runPath)`.
> ⚠️ `read_logger_plan` in `analysis/mat_reader.py` **no longer works** with the current 32-logger `simout.mat`; do not use it to parse events.

---

## ▶️ Run and reproduce (Windows + MATLAB)

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open')                       % open the sole model
% Edit config/adc_parameters.m (N / stimulus) or config/normal_parameters.m (non-idealities), then:
SAR20('apply')                      % rebuild P, update model workspace, save SLX
SAR20('check')
r = SAR20('run');                   % public run: archive SLX / P / source / simout / raw codes / metrics
s = SAR20('sample', 5, r.run_path);% per-sample event-chain figure + Chinese explanation (no SLX load)
```

| Entry point | Controls |
|---|---|
| [`config/adc_parameters.m`](config/adc_parameters.m) | N, differential offset, input amplitude/frequency/phase (default N=256; use 8 for short debug) |
| [`config/normal_parameters.m`](config/normal_parameters.m) | Non-ideality switches, mismatch σ, temperature, Cp, sampling/DAC/AZ time constants, RA A0/UGB and noise, comparator noise |
| [`config/normal_10v_configuration.m`](config/normal_10v_configuration.m) | Range and nominal digital scaling |

**Three common traps**

1. **A GUI Run does not read the factory files** — it uses the currently loaded ModelWorkspace.P and creates no public archive. If an edit seems to have no effect, check whether `apply` was called.
2. `N < 256` produces no dynamic metrics (`not_run_short_capture`); never discuss SNDR from an N8 run.
3. The MATLAB license is held by a resident instance, so `matlab -batch` exits immediately; jobs must go through the `SAR20_MatlabControl` scheduled-task COM channel. `license('test')=1` does **not** imply `checkout` succeeds.

See [docs/PARAMETERS.md](docs/PARAMETERS.md), [docs/READ_GRAPH.md](docs/READ_GRAPH.md), and [analysis §6.4](docs/ENGINEERING_ANALYSIS.md#64-恢复能力与单点依赖).

---

## 🗂️ Repository map

| Path | Contents | Production? |
|---|---|---|
| `SAR20.m` | **Sole public entry point** (open/apply/check/run/sample) | ✅ |
| `current/src/`, `current/models/` | 108 MATLAB sources + the sole SLX | ✅ |
| `config/` | Factory parameters and range configuration | ✅ |
| `state/` | Applied configuration and historical receipts (some date to 10-27; see analysis §6.1) | ⚠️ mixed |
| `docs/` | Specifications, reading guide, parameters, CAAZ/ADI plan, **full analysis**, paper PDFs | docs |
| `design/` | 2026-10-26 acceptance/engineering/frontend/schedule drafts (contain unimplemented ideas) | 📜 historical |
| `analysis/behavior/` | 52 experiment directories, 213 MB of real as-run evidence and figures | 📜 archive |
| `analysis/local_debug/` | New zero-MATLAB read-only probe and offline panel | 🆕 |
| `analysis/debug_ui_20261105/` | Paused 11-05 debug-UI candidates, archive ZIP, resume index | ⏸️ not promoted |
| `_preserved/` | Pre-change source/model/state backups (including the README backup made before this push) | 📜 rollback |
| `dependencies/toolkit/` | MathWorks Simulink Agentic Toolkit 2026.10.b (third party; see `NOTICE.md`) | runtime dependency |
| `dependencies/analysis_env/` | Local Python venv (**regenerable, not committed**) | ignored |
| `CHECKPOINT.md` | 219 KB reverse-chronological recovery log; **newest state is at the top** | 📜 historical |
| `release.json` | 2026-10-26 legacy release metadata (stale; see analysis §6.1) | 📜 historical |

---

## 🧭 Summary of findings

Full version: [`docs/ENGINEERING_ANALYSIS.md`](docs/ENGINEERING_ANALYSIS.md). Five key points:

1. **The UESTC CICC 2026 paper has not been reproduced**, and no acceptance criteria for "reproduction" have been defined in the project; 99.133 dB and the paper's 100 dB are not on the same footing.
2. **The baseline is not attributable**: the current N256 run enables all implemented non-idealities at once, so no single contribution can be separated — the fundamental blocker for quantitative paper comparison.
3. **Zero net production change**: all real work on 11-05 stayed in candidates/archives; production SLX is still `91973cf7…`.
4. **Five objective frameworks and at least five conflicting state sources**, with no git until this push; `CURRENT.json` is still to be added (roadmap M0).
5. **Recommended order**: M0 single source of truth → M1 single-source ablation + input-referred noise budget → M2 same-footing 20k-point spectrum and 7 dB comparison → only then M3 promote one candidate to production.

---

## 📚 Document index

| Document | Purpose |
|---|---|
| [Full analysis](docs/ENGINEERING_ANALYSIS.md) | Systematic diagnosis: objectives / architecture / evidence / governance / risks / roadmap |
| [CAAZ and ADI](docs/CAAZ_ADI.md) | What each of the three papers contributes, the verified CAAZ N8, and the ADI v2 candidate boundary |
| [Specification](docs/SPEC.md) · [alignment record](docs/ALIGNMENT.md) | Product contract and migration history |
| [Model plan](docs/MODEL_PLAN.md) · [reading guide](docs/READ_GRAPH.md) · [parameters](docs/PARAMETERS.md) | Architecture, block diagram, field semantics |
| [Acceptance contract](design/behavioral_acceptance.md) | 11 automatic checks and what must exist before claiming compliance |
| [Non-ideality coverage](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) | Implemented / enabled / uncovered, item by item |
| [Reference index](docs/PAPERS/INDEX.md) | Paths, provenance and SHA-256 of the 27 PDFs |
| [Third-party notice](NOTICE.md) | Licenses and copyright |
| [中文 README](README.md) | Default Chinese landing page (structurally aligned) |

---

## ⚖️ Third-party content and licensing

- `dependencies/toolkit/` is the **MathWorks Simulink Agentic Toolkit 2026.10.b**, distributed under its bundled `LICENSE.md` (BSD-3 variant, licensed solely for use with MathWorks products). Copyright The MathWorks, Inc.
- The 27 PDFs under `docs/PAPERS/` are **third-party literature** (IEEE / ISSCC / CICC papers, vendor datasheets, US patents). Copyright remains with the respective authors and publishers; they are included for research citation and traceability only. Rights holders may request removal via an issue.
- The project's own code and documentation **do not yet declare an open-source license**; until a LICENSE is added, do not assume free redistribution or commercial use.
- See [NOTICE.md](NOTICE.md).

---

## 🧾 Citation

See [CITATION.cff](CITATION.cff). Until reproduction is established, do not cite this model as validation of the paper's results.

---

<div align="center">

<sub>Last organized: 2026-11-05 · production model `91973cf7…` · current phase: normal baseline released, extension objectives paused</sub>

</div>
