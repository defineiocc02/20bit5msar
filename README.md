<div align="center">

# SAR20-5 · 20-bit 5 MS/s 两级 SAR ADC 行为级模型

**Simulink 行为级工程 · 成电 CICC 2026 架构底座 · 5 MS/s 单物理前端正常工作点**

[![MATLAB](https://img.shields.io/badge/MATLAB-R2024a%20Update%206-orange)](https://www.mathworks.com/products/matlab.html)
[![Simulink](https://img.shields.io/badge/Simulink-behavioral-blue)](https://www.mathworks.com/products/simulink.html)
[![Rate](https://img.shields.io/badge/5%20MS%2Fs-Fs-brightgreen)](#-当前状态)
[![SNDR](https://img.shields.io/badge/SNDR-99.133%20dB%20%40%20N256-blueviolet)](#-当前状态)
[![ENOB](https://img.shields.io/badge/ENOB-16.17%20bit-informational)](#-当前状态)
[![Status](https://img.shields.io/badge/status-normal%20baseline%20released%20%2F%20debug%20UI%20paused-yellow)](#-当前状态)
[![Docs](https://img.shields.io/badge/docs-中文-success)](README.md)
[![English](https://img.shields.io/badge/docs-English-lightgrey)](README_EN.md)

</div>

> 📌 **先读这一句**：这是一个**行为级模型工程**，不是论文复现完成报告，更不是流片/签核结果。
> 当前唯一已晋升的成果是 `91973cf7…` 模型上的一次 N256 正常运行；成电 CICC 2026 **尚未复现**，
> 原因与差距见 [全面分析](docs/ENGINEERING_ANALYSIS.md#54-成电复现判定)。
>
> 🆕 本仓库于 **2026-11-05** 从本地工程首次推送，完整保留源码、模型、全部历史证据与设计文档。

---

## 🚀 我想……（快速导航）

| 我想做什么 | 去哪里 |
|---|---|
| **看懂这个工程到底怎么样了** | [📊 全面分析报告](docs/ENGINEERING_ANALYSIS.md)（目标体系 / 架构 / 证据总账 / 风险分级 / 路线） |
| **在 Mac 上不装 MATLAB 就能调试** | [🔍 本地只读探针](#-本地调试零-matlab) · [离线面板](analysis/local_debug/sar20_debug_report.html) |
| **在 Windows 上跑模型 / 改参数 / 复跑** | [▶️ 运行与复现](#️-运行与复现windows--matlab) |
| **看当前生效参数、指标和证据边界** | [📌 当前状态](#-当前状态) · [非理想三态表](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) |
| **看模型框图怎么读** | [docs/READ_GRAPH.md](docs/READ_GRAPH.md) · [docs/PARAMETERS.md](docs/PARAMETERS.md) |
| **看 CICC2026 / PKU CAAZ / ADI 的对照与方案** | [docs/CAAZ_ADI.md](docs/CAAZ_ADI.md) |
| **看产品规格与接口合同** | [docs/SPEC.md](docs/SPEC.md) · [docs/ALIGNMENT.md](docs/ALIGNMENT.md) |
| **断流后从哪续做** | [CHECKPOINT.md](CHECKPOINT.md)（历史日志）· [PAUSE_INDEX.json](analysis/debug_ui_20261105/paused_work/PAUSE_INDEX.json) · [RESUME.md](analysis/debug_ui_20261105/paused_work/RESUME.md) |
| **查全部参考文献** | [docs/PAPERS/INDEX.md](docs/PAPERS/INDEX.md) |
| **English version** | [README_EN.md](README_EN.md) |

---

## 📌 当前状态

| 项 | 值 |
|---|---|
| 唯一入口 | [`SAR20.m`](SAR20.m) |
| 唯一模型 | [`current/models/SarAdc.slx`](current/models/SarAdc.slx)，SHA `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` |
| 生产源码 | [`current/src/`](current/src/) 108 个 `.m`，10 264 行 |
| 权威运行 | `behavior_12d08121-d679-40cd-9ee2-bc334ff42955`（[发布回执](analysis/behavior/public_normal_20261105/release_actual/release_receipt.json)） |
| 配置 | Fs 5 MHz、Fin 97.65625 kHz / bin5、峰值 −1 dBFS、差分 FSR 10 V、N=256、seed 20261020 |
| 指标 | SNR **99.712 dB** · SNDR **99.133 dB** · SFDR **111.784 dB** · THD **−108.166 dB** · ENOB **16.175 bit** |
| 同量程 NI 关闭基线 | SNDR 109.165 dB |
| 运行环境 | Windows MATLAB R2024a Update 6，`D:/Academic/Projects/sar20m1/SAR20`；本机（macOS）无 MATLAB |

### 能声称 / 不能声称

✅ **能声称**：架构骨架与节拍文字对齐论文（6b 预转换 + 10b 有效 DT + DAC1 电荷残差 + 32× RA/AZ + CINC CT 二级 + 12 D2 + 8 TA/7 反馈，约 90 ns 转换）；单点 N256 行为谱自洽、同配置逐位可复现；公开入口 apply → 冷开 → run → sample 链路真实跑通。

❌ **不能声称**：论文性能复现、tracking averaging 的 7 dB 收益、DNL/INL、20k 点频谱、功耗/面积/PDK、多频多种子稳定性、任何 signoff。当前 ENOB 16.17 bit ≠ 20 bit。

⚠️ **2026-11-05 状态**：用户已明确暂停调试 UI 目标，全部候选封存，生产模型**未部署任何调试候选**。CAAZ 仅在私有试验图跑通两组 N8，ADI 为候选。详见 [CHECKPOINT.md](CHECKPOINT.md) 头部。

---

## 🔍 本地调试（零 MATLAB）

纯只读探针，直接读已保存的真实 run，不加载模型、不仿真、不修改任何工程文件：

```bash
cd analysis/local_debug
PY=../../dependencies/analysis_env/bin/python   # 或任意装有 h5py / numpy / scipy 的 Python

$PY sar20_probe.py info                  # 运行身份 + 生效参数 + 非理想开关矩阵
$PY sar20_probe.py decode --all          # 独立复算 256 条 code20 vs MATLAB 实测
$PY sar20_probe.py decode --id 5         # 该 sample 的完整 D1/D2/DT 解码链
$PY sar20_probe.py diff <runA> <runB>   # 逐字段定位两个 run 的参数与码差异
$PY sar20_probe.py html                 # 重新生成离线调试面板
```

也可以直接打开 [`analysis/local_debug/sar20_debug_report.html`](analysis/local_debug/sar20_debug_report.html)（单文件、离线、内嵌 256 条真实记录，点任意一行看解码链）。

实测结果：`decode --all` **256/256 逐条一致**；ID 5 分解出 D1 = 4.3408203125 V、D2 = +1.609375 mV、DT = −19.53125 µV、code = 979623，与文档逐位吻合。`diff` 约 0.2 s。

> **证据边界**：探针只做名义数字重构核算（L0 离线审计），不是仿真、不是综合、不是 signoff。
> 事件级波形与 5 路日志对齐仍须走 MATLAB `SAR20('sample', id, runPath)`；
> ⚠️ 工程内 `analysis/mat_reader.py` 的 `read_logger_plan` 对当前 32-logger 的 `simout.mat` **已失效**，请勿据此解析事件。

---

## ▶️ 运行与复现（Windows + MATLAB）

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open')                       % 打开唯一模型
% 改 config/adc_parameters.m（N / 输入）或 config/normal_parameters.m（非理想）后：
SAR20('apply')                      % 重新准备 P、更新模型工作区、保存 SLX
SAR20('check')
r = SAR20('run');                   % 公开 run：封存 SLX / P / 源码 / simout / 原码 / 指标
s = SAR20('sample', 5, r.run_path);% 单样本事件链图 + 中文解释（不加载 SLX）
```

| 修改入口 | 内容 |
|---|---|
| [`config/adc_parameters.m`](config/adc_parameters.m) | N、差分偏置、输入峰值/频率/相位（默认 N=256，调试可改 8） |
| [`config/normal_parameters.m`](config/normal_parameters.m) | 非理想开关、匹配 σ、温度、Cp、采样/DAC/AZ 时间常数、RA A0/UGB 与噪声、比较器噪声 |
| [`config/normal_10v_configuration.m`](config/normal_10v_configuration.m) | 量程与名义数字尺度关系 |

**三个常见陷阱**

1. **GUI 直接 Run 不读工厂文件**，只用当前加载的 ModelWorkspace.P，且不建立完整公开归档 —— 改了参数没生效，先查是否漏了 `apply`。
2. `N < 256` 不计算动态指标（`not_run_short_capture`），不要用 N8 讨论 SNDR。
3. MATLAB 许可证被常驻实例占用，`matlab -batch` 会立即退出；需经计划任务 `SAR20_MatlabControl` 的 COM 通道。`license('test')=1` **不代表** `checkout` 可用。

详见 [docs/PARAMETERS.md](docs/PARAMETERS.md)、[docs/READ_GRAPH.md](docs/READ_GRAPH.md)、[全面分析 §6.4](docs/ENGINEERING_ANALYSIS.md#64-恢复能力与单点依赖)。

---

## 🗂️ 目录地图

| 路径 | 内容 | 是否当前生产 |
|---|---|---|
| `SAR20.m` | **唯一公开入口**（open/apply/check/run/sample） | ✅ |
| `current/src/` `current/models/` | 108 个 MATLAB 源文件 + 唯一 SLX | ✅ |
| `config/` | 工厂参数与量程配置 | ✅ |
| `state/` | 已应用配置与历史回执（部分为 10-27 历史状态，见分析 §6.1） | ⚠️ 混合 |
| `docs/` | 规格、读图、参数、CAAZ/ADI 方案、**全面分析**、论文原文 | 文档 |
| `design/` | 2026-10-26 验收/工程/前端/调度草案（含未实施设想） | 📜 历史草案 |
| `analysis/behavior/` | 52 个实验目录，213 MB 真实 as-run 证据与图 | 📜 归档 |
| `analysis/local_debug/` | 本次新增的零 MATLAB 只读探针与离线面板 | 🆕 |
| `analysis/debug_ui_20261105/` | 11-05 被暂停的 debug UI 候选、封存 ZIP 与恢复索引 | ⏸️ 未晋升 |
| `_preserved/` | 各次改动前的源码/模型/状态备份（含本次推送前 README 备份） | 📜 可回滚 |
| `dependencies/toolkit/` | MathWorks Simulink Agentic Toolkit 2026.10.b（第三方，见 `NOTICE.md`） | 运行依赖 |
| `dependencies/analysis_env/` | 本地 Python venv（**可再生，不入库**） | 忽略 |
| `CHECKPOINT.md` | 219 KB 倒序追加的恢复日志；**最新状态在文件头部** | 📜 历史 |
| `release.json` | 2026-10-26 旧版发布元数据（口径已过期，见分析 §6.1） | 📜 历史 |

---

## 🧭 工程结论摘要

完整版见 [`docs/ENGINEERING_ANALYSIS.md`](docs/ENGINEERING_ANALYSIS.md)，这里是五条要点：

1. **成电 CICC 2026 未复现**，且工程内尚无「复现」的验收判据；99.133 dB 与论文 100 dB 口径不同。
2. **基线不可归因**：当前 N256 是所有已实现非理想项联合一次运行，无法分离任一单源贡献 —— 这是「对照两篇论文做定量分析」的根本障碍。
3. **生产零净变化**：11-05 全天大量真实工作全部停留在候选/封存，生产 SLX 仍是 `91973cf7…`。
4. **5 套目标口径 + 至少 5 个互相冲突的状态源**，此前无 git；本仓库的 `CURRENT.json` 待补（见路线 M0）。
5. **建议顺序**：M0 单一真相源 → M1 单源消融 + 输入参考噪声预算 → M2 同口径 20k 点谱与 7 dB 对照 → M3 才晋升一个候选到生产。

---

## 📚 文档索引

| 文档 | 用途 |
|---|---|
| [全面分析](docs/ENGINEERING_ANALYSIS.md) | 本次系统诊断：目标/架构/证据/治理/风险/路线 |
| [CAAZ 与 ADI](docs/CAAZ_ADI.md) | 三篇原文各提供什么、已跑通的 CAAZ N8、ADI 物理 v2 候选边界 |
| [产品规格](docs/SPEC.md) · [对齐记录](docs/ALIGNMENT.md) | 产品合同与历史迁移 |
| [模型计划](docs/MODEL_PLAN.md) · [读图](docs/READ_GRAPH.md) · [参数](docs/PARAMETERS.md) | 架构、框图、字段语义 |
| [验收合同](design/behavioral_acceptance.md) | 11 项自动检查与「缺什么不能报达标」 |
| [非理想三态表](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) | 已实现 / 已启用 / 未覆盖逐项核对 |
| [文献索引](docs/PAPERS/INDEX.md) | 27 份 PDF 的路径、来源与 SHA-256 |
| [第三方声明](NOTICE.md) | 许可与版权归属 |
| [English README](README_EN.md) | 英文版入口页（与本文结构对齐） |

---

## ⚖️ 第三方内容与许可

- `dependencies/toolkit/` 为 **MathWorks Simulink Agentic Toolkit 2026.10.b**，按其自带 `LICENSE.md`（BSD-3 变体，仅限与 MathWorks 产品一起使用）随仓库分发，版权归 The MathWorks, Inc.
- `docs/PAPERS/` 内 27 份 PDF 为 IEEE / ISSCC / CICC / 厂商数据手册 / 美国专利等**第三方文献原文**，版权归各原作者与出版方，仅作研究引用与可追溯性用途。若权利方提出异议，请通过 issue 联系移除。
- 本仓库自身代码与文档**尚未声明开源许可证**；在 LICENSE 明确之前，请勿假定可自由再分发或商用。
- 详见 [NOTICE.md](NOTICE.md)。

---

## 🧾 引用

参见 [CITATION.cff](CITATION.cff)。论文复现状态未完成时，请勿将本模型引用为论文结果的验证。

---

<div align="center">

<sub>最后整理：2026-11-05 · 生产模型 `91973cf7…` · 当前阶段：normal 基线已发布，扩展目标暂停</sub>

</div>
