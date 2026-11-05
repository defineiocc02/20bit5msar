<div align="center">

# SAR20-5 · 20-bit 5 MS/s 两级 SAR ADC 行为级模型

**Simulink 行为级工程 · 成电 CICC 2026 架构底座 · 5 MS/s 单物理前端正常工作点**

[![MATLAB](https://img.shields.io/badge/MATLAB-R2024a%20Update%206-orange)](https://www.mathworks.com/products/matlab.html)
[![Simulink](https://img.shields.io/badge/Simulink-behavioral-blue)](https://www.mathworks.com/products/simulink.html)
[![Rate](https://img.shields.io/badge/5%20MS%2Fs-Fs-brightgreen)](#2-当前状态与证据边界)
[![SNDR](https://img.shields.io/badge/SNDR-99.133%20dB%20%40%20N256-blueviolet)](#22-唯一已晋升的结果n256)
[![ENOB](https://img.shields.io/badge/ENOB-16.17%20bit-informational)](#22-唯一已晋升的结果n256)
[![Status](https://img.shields.io/badge/status-normal%20baseline%20released%20%2F%20expansion%20paused-yellow)](#2-当前状态与证据边界)
[![Docs](https://img.shields.io/badge/docs-中文-success)](README.md)
[![English](https://img.shields.io/badge/docs-English-lightgrey)](README_EN.md)
[![Plan](https://img.shields.io/badge/计划-PROJECT_PLAN-important)](docs/PROJECT_PLAN.md)
[![Design](https://img.shields.io/badge/设计约束-Error%20Budget-critical)](design/budget/ERROR_BUDGET_REV03.md)

</div>

> 📌 **先读这一句**：这是一个**行为级模型工程**，不是论文复现报告，不是电路网表，更不是流片／签核结果。
> 当前唯一已晋升的成果，是模型 `91973cf7…` 上的**一次 N256 正常运行**（SNDR 99.133 dB / ENOB 16.17 bit）；
> 成电 CICC 2026 **尚未复现**，且工程内此前没有定义「复现」的验收判据。
>
> 本页是**工程说明书**：从目标口径、架构时序、参数假设、非理想覆盖，到运行、调试、证据链、已知缺口和后续计划，逐节给出可核对的事实与文件位置。
> 结论性诊断见 [全面分析](docs/ENGINEERING_ANALYSIS.md)，可执行的后续步骤见 [项目计划](docs/PROJECT_PLAN.md)。
> 仓库于 **2026-11-05** 首次推送，完整保留源码、模型、历史证据、设计草案与文献。

---

## 0. 30 秒判断

| | |
|---|---|
| **是什么** | 一个以 `SAR20.m` 为唯一入口、以 `current/models/SarAdc.slx` 为唯一生产模型的 MATLAB/Simulink **行为级**工程；用事件驱动的 double 电压/电荷计算模拟两级 SAR + RA + CT 二级 + tracking averaging 的码流 |
| **不是什么** | 不是晶体管级电路、不含 PDK、不产生功耗/面积、不做 DNL/INL、不做 PVT、不是论文结果的验证 |
| **跑得通吗** | 通。`apply → check → run → sample` 公开链路有真实运行回执；2026-11-04 在 Windows MATLAB R2024a Update 6 上完成正常 N256 发布 |
| **卡在哪** | **不是跑不通，是判不了收益**：当前 99.133 dB 是所有已开启非理想项联合一次运行的结果，无法分离任一单源贡献；于是改动无法验收，只能不断封存新候选，生产模型零净变化 |
| **当前阶段** | 2026-11-05 用户已明确**暂停**扩展目标（可视化/调试 UI），全部候选封存；生产 SLX 仍是 `91973cf7…`，未部署任何调试候选 |

### 能声称 / 不能声称

| ✅ 能声称 | ❌ 不能声称 |
|---|---|
| 架构骨架与节拍**文字对齐**论文：6b 预转换 + 10b 有效 DT + DAC1 电荷残差 + 32× RA/AZ + CINC 连续时间二级 + 12 D2 + 8 次 tracking 比较/7 次物理反馈，约 90 ns 转换 | 论文性能复现（100 dB SNDR / 3.6 mW / 0.53 mm² 是硅测，本工程无对应量） |
| 单点 N256 行为谱自洽、同配置逐位可复现（9 组真同配置，5 项指标最大跨度 `0.000e+00`） | tracking averaging 的约 7 dB 收益（无实测对照；理论 9.03 dB 上限被明确禁止当收益） |
| 公开入口 `apply → 冷开 → run → sample` 链路真实跑通 | DNL/INL、20k 点频谱、多频多种子稳定性 |
| 名义数字解码链已被独立 Python 复算 **256/256 逐条一致** | 校准/前景 LMS/独立 holdout 有效（`accepted=false`） |
| 一次 L3 整图 N256 正常运行 | 功耗、面积、PDK、PEX、硅、任何 signoff |

> ⚠️ **ENOB 16.17 bit ≠ 20 bit**。`docs/SPEC.md:43` 原文：「20-bit 输出字不等于 20-bit ENOB」。20 bit 是输出码宽，不是有效精度。

---

## 1. 按任务导航

| 我想…… | 去哪里 |
|---|---|
| **拿它指导电路设计：每个模块该做到多少噪声/电容/带宽** | [🎯 设计约束闭环（Rev0.3 误差预算）](design/budget/ERROR_BUDGET_REV03.md) · [预算 JSON](design/budget/error_budget_rev03.json) · [参数绑定表](design/budget/parameter_binding.csv) · [校验脚本](design/budget/verify_budget.py) |
| **判断这个工程到底怎么样了** | [§0 30 秒判断](#0-30-秒判断) · [全面分析报告](docs/ENGINEERING_ANALYSIS.md) |
| **知道接下来该做什么、按什么顺序** | [📋 项目计划 PROJECT_PLAN.md](docs/PROJECT_PLAN.md)（M0–M4 的验收门、命令、回滚） |
| **看懂架构、状态、时序、解码为什么除以 8** | [§4 架构与工作原理](#4-架构与工作原理) · [读图](docs/READ_GRAPH.md) · [参数语义](docs/PARAMETERS.md) |
| **看当前生效参数与哪些是假设** | [§5 参数与配置](#5-参数与配置) · [非理想三态表](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) |
| **看非理想效应到底实现了什么、缺什么** | [§6 非理想效应覆盖](#6-非理想效应覆盖) |
| **在 Windows 上跑模型 / 改参数 / 复跑** | [§7 运行与复现](#7-运行与复现) |
| **在 Mac 上不装 MATLAB 就能调试** | [§8.1 零 MATLAB 探针](#81-mac-零-matlab-只读探针) · [离线面板](analysis/local_debug/sar20_debug_report.html) |
| **看单样本事件级波形** | [§8.2 MATLAB sample](#82-matlab-事件级-sample) |
| **核对一次 run 到底落了哪些证据** | [§7.4 落盘清单](#74-一次-run-落盘什么) · [§9 证据地图](#9-归档与证据地图) |
| **看产品规格 / 接口合同 / 验收判据** | [SPEC.md](docs/SPEC.md) · [spec.yml](docs/spec.yml) · [ALIGNMENT.md](docs/ALIGNMENT.md) · [验收合同](design/behavioral_acceptance.md) |
| **看三篇论文分别迁移了什么** | [CAAZ_ADI.md](docs/CAAZ_ADI.md) · [27 份文献索引](docs/PAPERS/INDEX.md) |
| **断流后从哪续做** | [CHECKPOINT.md](CHECKPOINT.md)（头部为最新）· [RESUME.md](analysis/debug_ui_20261105/paused_work/RESUME.md) · [PAUSE_INDEX.json](analysis/debug_ui_20261105/paused_work/PAUSE_INDEX.json) |
| **English version** | [README_EN.md](README_EN.md) |

---

## 2. 当前状态与证据边界

### 2.1 权威身份

| 项 | 值 | 来源 |
|---|---|---|
| 唯一公开入口 | [`SAR20.m`](SAR20.m)（474 行） | 源码 |
| 唯一生产模型 | [`current/models/SarAdc.slx`](current/models/SarAdc.slx)，492 760 B | — |
| 生产 SLX SHA-256 | `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` | [state/applied_config.json](state/applied_config.json) · [发布回执](analysis/behavior/public_normal_20261105/release_actual/release_receipt.json) |
| 生产源码 | [`current/src/`](current/src/) 108 个 `.m` / 10 264 行 / 9 个子目录 | [全面分析 §4.1](docs/ENGINEERING_ANALYSIS.md) |
| 生效配置 SHA | `aa9f8f6d97108fbfae66701e8d09db123940a1b5f1b75fc9187c9b0203aba3c3` | `summary.json` |
| 权威 run | `behavior_12d08121-d679-40cd-9ee2-bc334ff42955` | [run 目录镜像](analysis/behavior/public_normal_20261105/release_actual/behavior_12d08121-d679-40cd-9ee2-bc334ff42955/) |
| 119 项 active manifest | `7b8fdf307e933a212f2f5eeee35a1f41df9b8a00d495e3cdaa4928c2b97c687f` | CHECKPOINT.md:21 |
| 运行环境 | Windows `D:/Academic/Projects/sar20m1/SAR20`，MATLAB R2024a Update 6（24.1.0.2689473）；**Mac 侧无 MATLAB** | 发布回执 |

### 2.2 唯一已晋升的结果（N256）

配置：Fs **5 MHz**（Ts 200 ns）、Fin **97.65625 kHz**（相干 bin5）、峰值 **4.456254690668728 V**（−1 dBFS）、差分 FSR **10 V**、N **256**、first_id 4、epoch 1、seed **20261020**、n_cycles 260、stop_time 51.89 µs、矩形相干窗 / DC 排除 / H2–H10 折回。

| SNR | SNDR | SFDR | THD | ENOB | 运行墙钟 |
|---|---|---|---|---|---|
| 99.712414227270258 dB | **99.132765903966785 dB** | 111.78407088195453 dB | −108.16556427335165 dB | **16.174878057137342 bit** | 117.7867422 s（`summary.json` 内 `elapsed_s` 115.33 s） |

- 同量程 NI 关闭基线：SNDR **109.16497669573319 dB**（ENOB 17.841 bit，[DYNAMIC_ACTUAL_256.json](analysis/behavior/normal_workpoint_20261104/DYNAMIC_ACTUAL_256.json)）。
- 独立 NumPy 从实际 CSV 复算，与 MATLAB 最大差 `3.44e−11 dB`。
- 发布回执四项等价性 `factory_p_exact / cold_p_exact / output_exact / global_rng_unchanged` 均为 `true`，`selected_records 256`，`root_outputs 3`。
- ⚠️ 这是**所有已开启非理想项联合的一次运行**，不是单源测量；覆盖表原文：「不能据此分别测出 kT/C、C 失配、有限建立、AZ、RA 或比较器噪声的单源贡献」。

### 2.3 证据层级（全仓库统一口径）

| 层级 | 含义 | 本工程已有 |
|---|---|---|
| L0 静态审计 | 哈希、清单、源码比对，不跑求解器 | 119 项逐 SHA；9 组同配置确定性检验；本地探针 256/256 解码复算 |
| L1 函数门 | 隔离核数学验证，未接主图 | 5 门：采样 RC+kT/C 7168 点、OU+AZ+DAC、合并返回、比较器、10 V 范围 |
| L2 smoke / N8 | 整图短记录，验证事件与码，**不算频谱** | N8 plain / tap / 私有 CAAZ 两组 N8 |
| L3 整图 N256 | 公开入口真实仿真 + FFT | **当前 normal 基线（唯一已晋升）**；另有若干不同配置历史 N256 |
| L4 归档形式验证 | as-run 重放、冻结系数、holdout | `accepted=false` 的 calibration 链、预登记 holdout 117.458 dB |
| L5 代理物理证据 | 行为级非理想代理 | RA OU 密集观测、σVX/σVY 代理——**仍是代理，不是物理** |
| L6 PEX / 硅 / 功耗面积 | 需电路实现与工艺 | **无** |
| L7 signoff | 完整 PVT、DNL/INL、多频多种子 | **无** |

> 全仓库的「不能声称」都基于一条规则：**下层证据不得升级为上层结论**。L3 的一次联合运行不能回答 L1 的单源问题，更不能回答 L6/L7 的问题。

### 2.4 状态源冲突（M0 待修）

| 状态源 | 声称 | 实际 |
|---|---|---|
| [`release.json`](release.json) | 2026-10-26，`R4/M8/F2/600MHz/N8`，SHA `8f12e65a…`；`canonical_mac_root` 指向 `项目库/outputs/` | 该路径已废弃（产物外置），SHA 与当前不符；无 `status` 字段 |
| [`state/SESSION_READY.json`](state/SESSION_READY.json) | 10-27，`display_compile_N8_bits…visual_review_required` | 早已 N256 正式发布；文件内两个 `figures` 块给出不同 SHA |
| 其余 5 个 `state/*.json` | 全部停在 10-26/10-27 | 历史回执 |
| [`state/applied_config.json`](state/applied_config.json) | **11-04T18:33:23Z，SHA `9197…`，`configuration_source=factory`** | ✅ **唯一对得上当前生产的状态源** |
| [CHECKPOINT.md](CHECKPOINT.md) | 219 KB / 665 行倒序追加，多个「最新/当前权威续点」 | 头部是 11-05 暂停结论；下文几百行仍是旧目标与已失效 `/tmp` 路径 |

M0 计划用机器可读的 `CURRENT.json` 收敛这一局面，并把上述旧文件标注为 archive。详见 [项目计划 §5](docs/PROJECT_PLAN.md)。

---

## 3. 目标体系：同一个工程，五套口径

同一个工程同时承担 5 套验收口径，且互相声明「不替代」。这是理解后续所有混乱的起点。

| 口径 | 出处 | 关键量化约束 | 当前满足情况 |
|---|---|---|---|
| **A 产品规格／接口合同 Rev0.3** | [SPEC.md](docs/SPEC.md) · [spec.yml](docs/spec.yml) · [ALIGNMENT.md](docs/ALIGNMENT.md) | 180 nm、5 MS/s / 200 ns、FSR **8.192 V**、SNR ≥100 dB / SINAD ≥98 dB / THD ≤−105 dBc、INL ≤±4 ppm、DNL <1 LSB20、AD7961 CP-32-7、单 LVDS 250 MHz、32-bit `W[31:0]` 帧、固定 N−2 读槽 | 当前 normal 用 FSR 10 V、无 LVDS 接入、无校准、无静态线性度 → **口径不同，不能判达标** |
| **B Rev0.1/0.2 历史对齐** | `ALIGNMENT.md:11-37` | 4 lane 50 MHz、BANK/OVR sideband、6+15 DT | 明确「只保留迁移过程，不能覆盖 Rev0.3」 |
| **C 新行为模型验收合同** | [behavioral_acceptance.md](design/behavioral_acceptance.md) | 里程碑 A（8 码）→ B（256 码）；11 项自动检查；`budget_missing` 即不得报达标 | A/B 有真实运行，但 `:63` 自述「尚无误差分配，也没有 SNDR/功耗验收目标」 |
| **D 行为工程／调度草案** | [design/](design/) 其余 4 篇 | 唯一入口/单一参数源、warm `sim()` ≤5 s、约 48 唯一事件时刻/slot | 草案横幅自述「包含未实施设想，不作为当前集成/运行证明」 |
| **E 当前工作点（论文 normal）** | 本 README §2 · CHECKPOINT 11-04/05 | 5 MS/s、FSR **10 V**（来自对论文 5 Vp 的解释假设）、单物理前端、N=256、非理想联合 ON | 唯一已晋升成果：SNDR 99.133 dB |

> ⚠️ `docs/MODEL_PLAN.md` 与 `docs/DEFINITIONS/ProductRev0.5/` 是**历史设计输入快照**，不是当前路线。当前路线只有一份：[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)。

### 3.1 三篇论文与工程的迁移边界

| 方向 | 采用 | 不迁移 / 当前进度 |
|---|---|---|
| **成电 CICC 2026**（架构底座） | 6b 预转换、10b 有效 DT、DAC1 电荷残差、32× RA/AZ、CINC CT、12 D2、8 tracking/7 反馈 | 论文未披露逐沿时刻、A0/极点、寄生、噪声与工艺参数 → 全部是**工程假设**。100 dB/3.6 mW/0.53 mm² 为硅测，本工程无对应量 |
| **北大/清华 VLSI 2025 CAAZ** | 输入侧两相斩波、偶帧写 AZ / 奇帧复用、完整输出极性恢复 | 私有试验图 `63283fd769ac…` 跑通两组 N8（16.21 s / 19.17 s），8 有效码、575 组 RA next→old 逐位一致；**未接入生产，未测 SNDR**；整图 AZ 写入随机噪声关闭 |
| **ADI ISSCC 2024** | 18 片 RDAC 池思路、DEM/dither、公开信息校准 | 物理 v2 仍在候选：558 字 FE owner、双 QDAC 各 1039 Cu、约 119.178 pF/half 制备电容（**每半边口径是本模型假设**）；FrameAvg 未建图，10 MS/s 未同意 |

详见 [CAAZ_ADI.md](docs/CAAZ_ADI.md)。`docs/CHOP_AZ_SPEC.md` 是**残差端四相历史提案**，与本轮输入侧两相 CAAZ 不能混用。

### 3.2 成电论文复现判定

**结论：没有复现，且此前不具备判定「是否复现」的验收条件。**

| 论文条件 | 工程现状 | 可比性 |
|---|---|---|
| 100 dB SNDR、3.6 mW、0.53 mm²、5 MS/s、硅实测 | 99.133 dB、行为级、无功耗面积、256 点 FFT | 否 |
| 约 7 dB tracking averaging 收益 | M1/M8 对照**未跑**；理论 9.03 dB 上限被禁止当收益 | 否 |
| 20k 点频谱 | 256 点 | 否 |
| 片外 LMS 前景校准 | calibration / frozen / Bank / transport / DEM / dither 全 OFF | 否 |
| 逐沿时刻、A0/极点/寄生/噪声/工艺 | 论文未披露 → 工程假设 | 否 |

全库无任何成电论文对照或差距报告；已有的 `comparison.*` 都是 run 与 run 之间的比较。`99.4 dB` 在工程内只以「预算/等条件复现」字样出现，**未绑定论文具体图表或测量条件（待确认）**。判定依据与完整证据见 [全面分析 §5.4](docs/ENGINEERING_ANALYSIS.md)。

### 3.3 设计约束闭环：怎么用它指导电路设计

前面几节回答「工程现在是什么」；若目的是**画电路**，需要另一条链：**系统指标 → 输入参考误差预算 → 模块规格 → 器件参数 → 验证门**。这条链此前在 `design/behavioral_acceptance.md:63` 被明确记为缺失，现已按 **Rev0.3 产品规格**补齐，见 [🎯 设计约束闭环](design/budget/ERROR_BUDGET_REV03.md)。

| 设计者要的数 | Rev0.3 口径下的值 | 当前模型 |
|---|---|---|
| 输入参考噪声上限（SNR 100 dB，−1 dBFS，FSR 8.192 V） | **25.8134 µV rms** | — |
| 谐波上限（THD −105 dBc，是控制项） | **14.5159 µV rms** | — |
| 采样电容下限（kT/C 占 50% 功率） | **24.7109 pF** | 28.0521 pF → 占 44.04% 功率 |
| 采样开关 Ron 上限（12.5 ns 保守窗口） | **35.38 Ω** | 20 Ω，τ 0.563 ns |
| 孔径 jitter（100 kHz / 1 MHz 扩展，独占预算） | **15.92 ps / 2.52 ps** | jitter OFF |
| RA 输出噪声 / 二级比较器输入噪声 | ≤**319.92 / 218.55 µV rms**（须 tracking 后实测折回 ≤10.00 / ≤6.83 µV） | 512.8 / 286.9 µV rms，一阶折算超预算 |
| 参考 / AZ 噪声预算 | 8.1629 / 7.3011 µV rms | **未实现** |
| INL / DNL | ±32.768 / <7.734 µV | 无测量 |

⚠️ 三点必须同时记住：① 这些数都是 **Rev0.3 8.192 V 口径**，当前 normal 是 10 V，噪声上限相差 1.49 倍功率，99.133 dB 与达标无关；② `spec.yml:57` 的 28 pF「每半边 / 差分总和」仍是 TBD，若为总和则每半边约 14 pF、采样预算跳到约 88%，整表要重做；③ 预算状态是 **`NOT_CLOSED`**：18% 功率无模型、22% 依赖未实测的 tracking 收益。[`verify_budget.py`](design/budget/verify_budget.py) 的 79 项校验只证明**解析链自洽**，不证明任何模块达标。

---

## 4. 架构与工作原理

### 4.1 信号链

```
Stimulus/Driver → Sample/CDAC1(18 片×38 列) → SAR1(6b coarse 辅助 + 10b 有效 DT)
   → DAC1 电荷残差 → 32× RA/AZ(ordinary) → CINC 连续时间二级 (12 D2)
   → 8 次 tracking 比较 / 7 次物理反馈 → RawRecord → FPGA 名义重构 code20
```

- **一级**：10-bit 有效 DT SAR，6-bit coarse 为内部高位辅助，`D1[10:0]`（RAW 11 bit）。
- **级间**：单个共享 32× RA + auto-zero；**RA 后不增加保持整个二级转换的 DT 采样器**（`SPEC.md:18`、`READ_GRAPH.md:20`）。
- **二级**：CINC 耦合 11-bit 连续时间 SAR，`D2[11:0]`，2-bit 级间冗余；8 次 tracking，`DT[7:0]`。
- **数字**：FPGA/Simulink 子系统按名义权重重构；片外训练参考**不得读取**内部电容、held 电压或残差。
- 顶层 `CodeValid` 是旧 Bank 路径的逐帧资格标志，**不能当作采样有效性**（`READ_GRAPH.md:42`）。

### 4.2 状态 owner 与 200 ns 事件日历

**只有三个标准 UnitDelay 状态 owner**，没有第二套电荷记忆（`READ_GRAPH.md:44`）：

| Owner | 宽度 | 内容 | 源码 |
|---|---|---|---|
| `A/SampleCharge`（FE353） | 353 double | 318:335 实际孔径、336:353 开采时刻、18 片电容计划 | [frontend/behavior_frontend_unpack.m](current/src/frontend/behavior_frontend_unpack.m) |
| `A/RaCtState`（RA48 / BK48） | 48 double | RA/AZ/CT 连续状态 | [physics/behavior_backend_unpack.m](current/src/physics/behavior_backend_unpack.m) |
| `A/SarState`（SAR51 / SC51） | 51 double | 1:26 标量、27:38 12 个 D2 signs、39:45 7 个 TA signs、46:51 pending | [control/behavior_sar_pack.m](current/src/control/behavior_sar_pack.m) |

事件日历见 [control/behavior_calendar.m](current/src/control/behavior_calendar.m)（周期 200 ns，tick 250 ps；**48 组事件 / 73 tokens**）：

| 时刻 | 事件 |
|---|---|
| 0 ns | `cnv` |
| 12.5 ns | `coarse_latch`；5 组 `fine_prepare 12.5+3.75k` / `fine_decide 15+3.75k` / `fine_feedback 16.25+3.75k`（k=0..4） |
| 31.25 ns | `ra_start`（AZ 写窗为 0–31.25 ns） |
| 43.75…72.5 ns | 12 组 `d2_prepare 43.75+2.5k` / `d2_decide 45+2.5k` / `d2_feedback 46.25+2.5k`（k=0..11）；`d2_end 73.75 ns` |
| 75…83.75 ns | 8 个 `ta_compare 75+1.25m`（m=0..7），**仅 m<7 有 `ta_feedback`** → 8 次比较 / 7 次物理反馈 |
| 85 ns | `tracking_end`（TA m=7 的下一拍反馈可见点） |
| 86.25 ns | `raw_latch`（RawReady） |
| 90 ns | `release` / analog reset |
| 92 ns | guard 2 ns 后下一次采集 |
| （transport ON 时）138 ns | `frame_ready`，追加第 49 组事件 |

> 同一时刻可以有多个不同事件，**不能只靠 time 去重**（`behavioral_frontend.md:180`）。相同沿上的优先级由 `[tick, priority]` 排序决定。

### 4.3 RAW 记录与名义解码链

RAW 顺序固定为 `[D1, D2, DT, sample_id, epoch, valid]`，位宽 **11 / 12 / 8 / uint32 / uint32 / 1**（`analysis/behavior_record_view.m:28`、`behavior_decode.m:27`）。

[behavior_decode.m](current/src/digital/behavior_decode.m) 的名义重构链：

```matlab
c = floor(D1/32);  f = mod(D1,32);
d1Dac = (32*c + 2*f - 1039) * p.vref_v / 1024;
d1V   = d1Dac + p.d1_bias_v;                       % normal: d1_bias_v = 0
d2V   = (p.d2_offset_ra_v + sum(p.d2_weights_ra_v .* d2_bits)) / p.ra_gain;
dtV   = (p.tracking_step_ra_v * dtWeighted) / p.ra_gain;
voltage = ((d1V + d2V) + dtV) + dither;           % POL 只翻 d2V/dtV，不翻 DAC1/dither
unsat   = voltage * (2^20 / p.fsr_diff_v) + 2^19;
code    = max(0, min(2^20-1, round(unsat)));      % nearest, ties away from zero
```

约束：`ra_gain == 32`、`tracking_mode='finite_sinc2'`、`calibration_mode='off'`、12 个正 `d2_weights_ra_v`、`fpga.sinc2_scale == 1/8`。数字侧校准**未实现**，强行开启会报错。

### 4.4 为什么 SINC² 除以 8 而不是 36

`dtWeighted = sum(weights .* dtSigns) / 8`，其中 `weights = 8:-1:1`。8 个权重之和是 **36**，但源码注释明确：

> 「the plain average would divide by sum(weights)=36. This chain divides by 8 because **decision eight has no physical update while its raw LSB still carries digital weight one**. That is deliberate, not a normalisation bug.」（`behavior_decode.m:21-23`）

即：第 8 次 tracking 比较只贡献一个**数字** LSB，没有对应的第 8 次物理电容反馈。把这个 `/8` 改成 `/36` 是常见误读，会系统性压低 DT 项约 13 dB。RA 后无 S/H、8 比较/7 反馈、有限 SINC² 三者必须一起理解。

### 4.5 哪些是论文披露，哪些是工程假设

| 类别 | 内容 |
|---|---|
| **论文/规格入口** | 架构骨架、约 90 ns 转换、8 tracking/7 反馈、32× RA、CT 二级概念 |
| **工程假设（非论文披露）** | 全部逐沿开关时刻、FSR **10 V** 的「5 Vp 差分 = 10 Vpp FSR」解释、A0=1e4 / UGB=1.2 GHz / 单极点、Cp=100 fF/half、σunit≈0.068%、CINC 900 fF、σVX 0.512785 mV / σVY 0.286929 mV、1039×27 fF 半边电容解释、完整 DAC1 开关码本、28 pF 顶层电容口径 |
| **来源标签** | `normal_parameters.m:180` 给出 `assumptions.status='EXPECTED_OPERATING_ESTIMATE_NOT_PDK_TYPICAL'`；`state/applied_config.json` 的 `assumptions` 6 条逐条列出 |

> 引用本工程任何数值时，请连同这些假设标签一起引用。它们不是 PDK 统计、不是论文标称、不是硅测。

---

## 5. 参数与配置

### 5.1 三个配置入口

| 文件 | 作用 | 改动后必须 |
|---|---|---|
| [config/adc_parameters.m](config/adc_parameters.m) | 工厂基线与用户可编辑输入：`N`(256)、`input_offset_v`(0)、`input_level_dbfs`(−1)、`input_frequency_hz`(97656.25)、`input_phase_rad`(0.731)；`single_bank_factory_base()` 生成 P 骨架 | `SAR20('apply')` |
| [config/normal_parameters.m](config/normal_parameters.m) | 正常非理想工作点：6 个开关 `useSamplingMismatch / useCtMismatch / useKtc / useRaNoise / useCmp / azMode='ordinary'`，以及全部 σ/Cp/τ/A0/UGB/温度/种子 | `SAR20('apply')` |
| [config/normal_10v_configuration.m](config/normal_10v_configuration.m) | 量程与名义数字尺度：断言基线 FSR 8.192 V → 构造 10 V 口径，`vref1=5`、`delta=10/1024`、`output_lsb=10/2^20`；用 `nominal.mat` 归档的名义 CT 几何校验权重（tol 1e-12） | `SAR20('apply')` |

另有 4 个 case 构造器：[make_adi_cases.m](config/make_adi_cases.m)（2×2×2 = 8 个 DEM/dither/失配案）、[make_jitter_cases.m](config/make_jitter_cases.m)（6 个 N8 jitter 案）、[make_training_case.m](config/make_training_case.m)、[make_training_protocol.m](config/make_training_protocol.m)（2048 训练 / 1024 holdout 与阈值）。[config/nominal.mat](config/nominal.mat) 是 v5 MAT，保存名义 CT 几何与 FPGA 权重（`nominal_weight_source='DERIVED_INTEGER_NOMINAL_GEOMETRY_NO_ACTUAL_CAPACITANCE'`）。

### 5.2 当前 normal 关键参数（生效值）

| 组 | 参数 | 值 | 性质 |
|---|---|---|---|
| 时基 | `Ts_s` / `fs_hz` | 2e-7 s / 5 MHz | 合同 |
| 输入 | `amplitude_v` / `frequency_hz` / `phase_rad` | 4.456254690668728 V / 97656.25 Hz / 0.731 | 相干 bin5 |
| 量程 | `fsr_diff_v` / `vref_v` / `sar1.delta_v` | 10 V / 5 V / 0.009765625 V | **10 V 是假设** |
| 采样 | `tau_sample_s` / `guard` / `Ctop` | 0.563041298 ns / 2 ns / 28.1520649 pF/half | 假设 |
| kT/C | T / seed / 平衡近似 σ | 298.15 K / 20261027 / 17.256 µV rms | 假设 |
| 失配 | `σunit` / seed | 0.06804138 % / 20261104 | 假设，单颗芯片 |
| DAC | `tau_dac_s` / coupling | 0.5 ns / true | 假设 |
| RA | A0 / UGB / NG / τ / Vos | 1e4 / 1.2 GHz / 33.5834 / 4.4541 ns / +1 mV | 假设 |
| RA 噪声 | `sigma_vx_rms` / seed | 0.51278539 mV / 20261104 | A1 通道 OU 代理 |
| 比较器 | `sar2_noise_rms_v` / seed | 0.286928737 mV / 20261105 | **仅 SAR2/TA**；SAR1-fine 与 Flash 为 0 |
| AZ | mode / write τ / leak τ | ordinary / 1 ns / 10 ms | 无随机 AZ 噪声 |
| 数字 | `ra_gain` / `tracking_mode` / `calibration_mode` / `d1_bias_v` | 32 / finite_sinc2 / off / 0 | 名义链 |
| 关闭 | jitter / DEM / dither / training / cal_cfg / frozen / bank / transport | 全 false | 见 §6 |

完整 33 个顶层键见 run 目录的 `parameters.json`；完整 35 键配置见 [state/applied_config.json](state/applied_config.json)。

### 5.3 两个容易误用的字段

- **`P.ni` 是由物理配置派生的摘要，不是独立开关**（`docs/PARAMETERS.md:26,83`）。改 `P.ni.xxx=true` 不会打开任何物理效应；摘要为真也不代表每片或每种组合都扫描过。
- **`P.debug.adi_enabled` 只开观察、不开物理功能**（`docs/PARAMETERS.md:126`）。true 时仅允许 N8 记录实际选片、shift、目标电荷、CNV tail 与控制计数；物理 ADI / DEM / dither 仍未开启。

---

## 6. 非理想效应覆盖

依据 [NORMAL_NONIDEALITY_COVERAGE.md](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) 与 `current/src/` 逐文件核对；「实现位置」列给出可审阅的源码入口。

### 6.1 已实现且当前 ON

| 效应 | 实现位置（示例） | 当前值 |
|---|---|---|
| 采样 kT/C | `frontend/behavior_frontend_step.m:85-111,322-342` | 17.256 µV rms；函数门 7168 点归一方差 0.9803 |
| 一级 C 固定失配 | `config/normal_parameters.m:63-76,109-116`；`physics/behavior_backend_step.m:298-309` | σunit 0.068%，8 段逐列一致 |
| 比较器噪声（**仅 SAR2/TA**） | `control/behavior_comparator_sample.m:36-53` | σVY 0.286929 mV |
| RA OU 噪声（A1 通道代理） | `physics/sar20_ra_ou_increment.m:1-58`；`behavior_backend_step.m:139-160` | σVX 0.512785 mV |
| RA 有限增益/带宽 | `physics/behavior_backend_step.m:267-273,88-106` | A0 1e4、UGB 1.2 GHz、NG 33.58 |
| 普通 AZ | `control/behavior_az_schedule.m:1-94`；`behavior_backend_step.m:196-265` | ordinary、写窗 0–31.25 ns、POL `[+1,−1,−1,+1]` |
| DAC 有限建立 | `physics/behavior_dac_forcing_from_frontend.m`；`behavior_backend_step.m:350-381` | τ 0.5 ns、coupling true |
| 寄生 | `frontend/behavior_frontend_step.m:275`；`physics/behavior_backend_step.m:310-313` | 前端 100 fF/half、RA 输出 0.5 pF/half |
| 采样 RC 建立 | `frontend/behavior_frontend_step.m:200-249`（精确正弦特解） | τ 0.563 ns |

### 6.2 已实现但当前 OFF（有代码，不是「没做」）

`jitter`（`frontend/behavior_jitter_parameters.m`、6 个 case 构造器）、`dither`（`digital/behavior_public_dither.m`）、`DEM`（`frontend/behavior_frontend_step.m:135-136`）、`calibration/train/frozen/Bank`（`current/src/calibration/` 24 个 `.m`）、`transport/LVDS`（`current/src/transport/` 10 个 `.m`）、`finite slew`（仅 `isfinite(slew_v_per_s)` 时裁剪；当前 `Inf`）。

### 6.3 明确标注「not implemented」

| 项 | 出处 |
|---|---|
| `reference_recovery` | `model/behavior_ra_noise_guard.m:90` 抛 `Reference recovery is not implemented.` |
| `az_noise` / `reference_noise` / `nonlinear_ra` / `replica_delay` | `physics/behavior_backend_step.m:434-437` `NI %s is not implemented in this deterministic kernel.` |
| SAR1-fine / Flash 比较器噪声 | `model/behavior_applied_note.m:46`、`behavior_ra_noise_guard.m:119` |
| 数字侧校准 | `digital/behavior_decode_parameters.m:20`、`behavior_decode.m:94-95` |
| 有限 RC + 位移孔径的 jitter 组合 | `frontend/behavior_frontend_step.m:64-66` |
| 运行时 EN 模式切换 / 同 run Bank ARM | `transport/behavior_transport_step.m:22`、`calibration/sar20_bank_owner_step.m:21` |

### 6.4 源码中无实现证据

`timing_mismatch`、`dac_sampling_bw`、`online_shuffler` —— 仅在 SPEC / MODEL_PLAN 作为设想出现，`current/src/` 未检索到对应实现（待确认）。

### 6.5 覆盖缺口的后果

`NORMAL_NONIDEALITY_COVERAGE.md:27` 原文：「此次 N8 是所有所列开启项的联合运行，**不能据此分别测出 kT/C、C 失配、有限建立、AZ、RA 或比较器噪声的单源贡献**。RA 噪声仅是 A1 通道代理，比较器噪声仅覆盖 SAR2/TA；驱动与参考噪声、其他 RA 级、AZ 噪声及 SAR1/Flash 噪声仍不在覆盖内。」

这正是 [M1 单源消融 + 输入参考噪声预算](docs/PROJECT_PLAN.md) 要解决的**首要科学问题**：不是再加特性，而是让现有基线变得可归因。

---

## 7. 运行与复现

### 7.1 环境前提

| 项 | 要求 |
|---|---|
| 主机 | Windows，工程根 `D:/Academic/Projects/sar20m1/SAR20`（Mac 侧仅为镜像与离线分析，无 MATLAB） |
| MATLAB | R2024a Update 6（发布回执：`24.1.0.2689473 (R2024a) Update 6`） |
| 工具链 | `dependencies/toolkit/`（MathWorks Simulink Agentic Toolkit 2026.10.b），`apply` 前 `require_toolkit` 会校验 4 个目录与 `.p/.m` 解析路径 |
| 调度 | 许可证被常驻 GUI 实例占用，`matlab -batch` 会立即退出；须经计划任务 `SAR20_MatlabControl` 的 COM 通道。`license('test')=1` **不代表** `checkout` 可用 |

### 7.2 `SAR20.m` 全部 action

| action | 行为 | 是否加载/保存 SLX | 落盘 |
|---|---|---|---|
| `setup` | 清理退役 runtime path、`addpath(genpath(src),config,'-begin')`、`verify_project_resolution` | 均否 | 无 |
| `open` | `open_system(modelFile)`；若 `state/applied_config.json` 缺失给出 `SAR20:applyRequired` 警告 | 打开（不保存） | 无 |
| `apply` | `P=adc_parameters()` → `behavior_prepare_configuration(P)` → `assignin(ws,'P'/'DecodeP')` → **`save_system(...,'SaveModelWorkspace',true)`**；更新 4 个 block 的已应用说明文字 | **保存 SLX** | `state/applied_config.json`（utc / model_sha256 / source / config） |
| `check` | 读 ModelWorkspace.P → `set_param(model,'SimulationCommand','update')` | 加载，不保存 | 无 |
| `run` | `require_applied_model` → 频谱资格检查 → `run_saved` 真实仿真与归档 | 加载，不保存 | `runs/behavior_<UUID>/`、`runs/latest_behavior_run.json` |
| `sample` | `behavior_sample_plot` + `behavior_sample_explain`，产出单样本事件链图与中文解释 | **在 `load_system` 之前 return，不加载 SLX** | `runs/sample_<UUID>/` |
| `calibration` | **无条件抛错** `singleBank:calibrationUnavailable`：「Single-bank calibration is not validated; do not freeze or apply legacy pool coefficients.」 | 否 | 无 |

> `apply` 会把 P 内嵌进 SLX 并保存，所以 **SLX 哈希 = f(模型结构 + 内嵌 P)**；205 个 run 有 205 个哈希。历史上「模型未变」的多次记录是在这一认知纠正之前写的（CHECKPOINT.md:141-150）。

### 7.3 标准流程

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open')                        % 打开唯一模型
% 改 config/adc_parameters.m（N / 输入）或 config/normal_parameters.m（非理想）后：
SAR20('apply')                       % 重新准备 P、更新 ModelWorkspace、保存 SLX
SAR20('check')                       % 实际编译 / 图更新
r = SAR20('run');                    % 真实仿真 + 完整公开归档
s = SAR20('sample', 5, r.run_path);  % 单样本事件链（不加载 SLX）
```

`sample` 要求恰好 2 个参数：`id` 为非负整数，`runPath` 为含 `parameters.mat` / `simout.mat` / `summary.json` 的目录（每个文件 ≤300 MB）；输出目录必须落在所选 run 之外。

### 7.4 一次 `run` 落盘什么

`SAR20('run')` 写入 **`runs/behavior_<UUID>/`**（工程根，非 `analysis/`）：

| 文件 | 内容 |
|---|---|
| `summary.json` | 全程 report：状态、SHA、记录、指标、耗时、失败时的 `error_identifier` |
| `parameters.mat` | 完整 resolved P（`-v7.3`） |
| `parameters.json` | P 的可读投影（`config_identity` 明确「MAT 才是全量」） |
| `SarAdc.slx` | 模型副本，SHA 与 `report.model_sha256` 校验一致 |
| `source.zip` + `source_manifest.json` | `current/src/**/*.m` + `config/*` + `SAR20.m` 逐文件 SHA（本次归档 117 项） |
| `simout.mat` | 原始仿真输出（**在任何 capture/validation 之前落盘**，含失败/停止场景） |
| `selected.mat` | `selected={raw,code20,time_s,raw_fields}` 与 `metadata`；校验 N 个连续 ID、epoch、valid、码域 |
| `spectrum.mat` | 5 项指标（仅频谱资格通过时） |
| 条件产物 | `training*.mat/json`（cal_cfg ON）、`bank_qualification.json`（bank ON） |
| `runs/latest_behavior_run.json` | 最近一次 run 路径与 `summary_sha256` |

本仓库 `analysis/behavior/public_normal_20261105/release_actual/behavior_12d08121-…/` 是该 run 的 **Mac 镜像**（9 个文件）。上层 `release_actual/` 另有 `release_receipt.json`、`ACTIVE_WORKING_MANIFEST.json`、当前框图 PNG、GUI 导出回执等——⚠️ **`release_receipt.json` 不是 `SAR20('run')` 的产物**，由 Windows 侧 controller 生成（具体脚本待确认），引用时须区分「入口产物」与「发布流程产物」。

### 7.5 四个陷阱

1. **GUI 直接 Run 不读工厂文件**，只用当前加载的 ModelWorkspace.P，也不建立完整公开归档——「改了参数没生效」先查是否漏了 `apply`。
2. **`N < 256` 不计算动态指标**（`not_run_short_capture`）。N8 ≈3 s 只用于事件与码调试，禁止用 N8 讨论 SNDR。
3. **`matlab -batch` 立即退出**（许可证被常驻实例占用）；`license('test')=1` 与 `checkout` 可用是两回事。
4. **不要拿不同配置的 N256 互相比较**。历史表里有 FSR 8.192 V / NI 关闭 / 压力 jitter / 6 seed 等多种配置；按 6 个顶层字段分组曾得出「SNDR 跨度 52.9 dB」的假象，改用整份 `parameters.json` SHA-256 分组才得到 9 组真同配置（最大跨度 `0.000e+00`）。原文教训：「比数值之前，先证明两次比的是同一个东西」。

---

## 8. 调试

### 8.1 Mac 零 MATLAB 只读探针

[analysis/local_debug/sar20_probe.py](analysis/local_debug/sar20_probe.py) **不加载模型、不调用 MATLAB、不仿真、不修改任何工程文件**，只读已保存的真实 run：

```bash
cd analysis/local_debug
PY=../../dependencies/analysis_env/bin/python   # 或任意装有 h5py / numpy / scipy 的 Python

$PY sar20_probe.py info                  # 运行身份 + 生效参数 + P.ni 开关矩阵
$PY sar20_probe.py decode --all          # 独立复算 256 条 code20 vs MATLAB 实测
$PY sar20_probe.py decode --id 5         # 单样本完整 D1/D2/DT 解码链
$PY sar20_probe.py diff <runA> <runB>   # 逐字段定位两个 run 的参数与码差异
$PY sar20_probe.py html                 # 重新生成离线调试面板
```

也可直接打开 [sar20_debug_report.html](analysis/local_debug/sar20_debug_report.html)（单文件、离线、内嵌 256 条真实记录，点任意行看解码链）。

实测：`decode --all` **256/256 逐条一致**；ID 5 分解 D1 = 4.3408203125 V、D2 = +1.609375 mV、DT = −19.53125 µV、code = 979623。`diff` 约 0.2 s（优先用 `parameters.json` 全量投影；`mat_value` 全量展开 P 约 30 s，按需子树约 0.002 s）。

> **证据边界**：这是 **L0 离线核算**，不是仿真、不是综合、不是 signoff。它的价值是「改参数/改源码后，数字解码链有没有被改坏」的第一道门。

### 8.2 MATLAB 事件级 `sample`

`SAR20('sample', id, runPath)` 是**唯一**能拿到 5 路日志 / RAW / record 对齐、事件波形与中文解释的通道，且因为分支在 `load_system` 之前 return，不需要打开模型。发布 normal N256 之后，Mac 侧未生成过任何 sample 报告。

`release_receipt.json` 记录 9 路日志名：`raw_log / ready_log / record_log / record_ready_log / event_log / front_log / back_log / control_log / code_log`。

### 8.3 已知的静默工具链失效

- ⚠️ [analysis/mat_reader.py](analysis/mat_reader.py) 的 `read_logger_plan()` 对当前 32-logger 的 `simout.mat` **已失效**，实测报 `indexed 0 logger data arrays for 32 SimulationOutput variables`。全库此前无任何文档记录此事，原工具**未修复**；新探针不解析该布局、不伪造事件时间线。请勿据此解析事件。
- `analysis/local_debug/sar20_probe.py` 绕过了这一失效，但只覆盖 `parameters.mat / selected.mat / summary.json / parameters.json / release_receipt.json`。

### 8.4 调试决策树

| 现象 | 先查 |
|---|---|
| 改了参数没生效 | 是否漏 `SAR20('apply')`；`state/applied_config.json` 的 `utc` / `model_sha256` 是否更新 |
| 指标突然不出现 | `N` 是否 < 256；`spectrum_eligibility` 字段 |
| 两个 run 数字对不上 | `sar20_probe.py diff` 先比 `parameters.json` 全量 SHA，再谈数值 |
| 数字码变了但不知谁造成 | `decode --all` 验证解码链 → 再用 `decode --id` 看 D1/D2/DT 分项 |
| 需要事件波形 / 5 路日志 | `SAR20('sample', id, runPath)`；**不要**用 `read_logger_plan` |
| 想追物理非理想来源 | 目前做不到单源归因 → 见 [M1](docs/PROJECT_PLAN.md) |

---

## 9. 归档与证据地图

| 路径 | 内容 | 性质 |
|---|---|---|
| [analysis/behavior/public_normal_20261105/release_actual/](analysis/behavior/public_normal_20261105/release_actual/) | 当前权威 N256：发布回执、run 镜像、框图、GUI 导出回执、active manifest | ✅ 唯一已晋升 |
| [analysis/behavior/normal_workpoint_20261104/](analysis/behavior/normal_workpoint_20261104/) | 正常点联合 N8 / N256、5 项函数门、非理想覆盖表、FFT 与 settling 图、Windows controller 脚本 | 工作点取证 |
| [analysis/behavior/](analysis/behavior/)（52 个实验目录，约 213 MB） | 10-26 至 11-05 的历史 as-run：LVDS、训练/holdout、DEM/dither、RA OU、压力 jitter、可读性重构等 | 📜 归档，配置各不相同 |
| [analysis/local_debug/](analysis/local_debug/) | 零 MATLAB 探针与离线面板 | 🆕 L0 工具 |
| [analysis/debug_ui_20261105/paused_work/](analysis/debug_ui_20261105/paused_work/) | 11-05 暂停的 210 个候选、`candidate_sources_paused.zip`(SHA `3504a9a9…`)、`PAUSE_INDEX.json` 恢复映射、`RESUME.md` | ⏸️ 未晋升 |
| [_preserved/](_preserved/) | 各次改动前的源码/模型/状态备份（含 `before_github_20261105/` 的 README 与 .gitignore 原件） | 📜 可回滚 |
| [CHECKPOINT.md](CHECKPOINT.md) | 219 KB / 665 行倒序追加恢复日志，**最新状态在文件头部** | 📜 历史，需 M0 冻结 |

历史整图结果（**不同配置，禁止互相比**）与逐条判读见 [全面分析 §5.2](docs/ENGINEERING_ANALYSIS.md)：NI 关闭 109.827 dB、combined jitter 95.788 dB、有限 DAC τ=1 ns 106.913 dB、6 seed RA OU 100.655±0.414 dB、预登记 holdout 117.458 dB（`accepted=false`）。

---

## 10. 已知问题与风险

| 级别 | 风险 | 影响 |
|---|---|---|
| **高·结论** | 基线不可归因（联合单点、无单源消融、无输入参考噪声预算） | 任何 CAAZ/ADI/校准改进的 ΔdB 无法解释；论文定量对照无法进行 |
| **高·工程** | 生产停滞、候选堆积（11-05 逐 SHA 比对 116 个文件 0 差异；8 次封存/回滚） | 工作无法转成可交付版本，回滚成本上升 |
| **高·工程** | 无单一真相源（5 个状态源冲突；此前无 git） | 恢复易选错配置；已发生 SHA 误抄 62 位导致 preflight 失败 |
| **中·技术** | 非理想覆盖不全、参数多为假设 | 99.133 dB 不能外推，不能当 PDK/论文标称 |
| **中·工程** | `read_logger_plan` 静默失效 | 误用旧工具解析事件会得到错误结论 |
| **中·可复现** | Windows / MATLAB / 许可证单点 | 换机无法一键复现，CI 不可能 |
| **中·合规** | 公开仓库分发 27 份第三方 PDF + 43 MB SATK | 已用 [NOTICE.md](NOTICE.md) 标注来源与许可；若权利方异议按其中流程移除 |
| **低-中·卫生** | 596 MB 中约 1.3 MB 是生产 | 克隆/审阅成本高；venv 与 pyc 已排除入库但目录仍在工作区 |

**根因链**：目标频繁切换 → 每次留下未晋升候选 → 为保护候选建立 SHA/回执/封存体系 → 证据链膨胀 + 状态源分裂 → 恢复成本升高 → 更倾向再开隔离候选而非晋升；同时「基线不可归因 → 收益无法判定 → 不敢晋升」强化这一环。详见 [全面分析 §7](docs/ENGINEERING_ANALYSIS.md)。

---

## 11. 路线与计划

完整可执行计划见 **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)**（含每个里程碑的前置、命令、验收门、备份与回滚、checkpoint、授权边界）。其中 **M0.5「设计约束闭环」已于 2026-11-05 落地**（[§3.3](#33-设计约束闭环怎么用它指导电路设计)），它是 M1 消融的验收依据；下表 M0–M4 仍为提案。摘要：

| 里程碑 | 动作 | 改模型？ | 完成判据 |
|---|---|---|---|
| **M0** | 建机器可读 `CURRENT.json` 单一真相源；旧状态源标 archive；修正失效路径 | 否 | 任一新会话 1 分钟内确定「当前是什么、什么算完成」 |
| **M1** | 固定 N256/seed/FSR 做**单源消融矩阵** + 输入参考噪声预算 | 否（参数注入）；需 Windows 调度授权 | 每个已实现非理想项有独立 ΔSNDR，预算表可与论文分项比较 |
| **M2** | 同口径 20k 点谱 + M1/M8 的 7 dB 对照 + 校准/holdout 复核 | 否（参数级）；需授权 | 能回答「复现到什么程度、差在哪几项、各差多少 dB」 |
| **M3** | 从 CAAZ 与 debug UI 中**选一个**晋升生产，走完 N8 位门 → N256 回归 → 文档同步 | **是，需显式授权**；先列范围/备份/回滚 | 生产 SLX SHA 改变且 README 与 CURRENT.json 同步 |
| **M4** | ADI v2 完整 18-pool / 双 QDAC、10 MS/s | 是，架构级 + 另行同意 | 按新里程碑单独定义 |

**优先级 M0 → M1 → M2；M3 之前不要开新特性线。** M1/M2 产出的是「能不能判定收益」这一晋升决策的前提，缺了它，M3 选哪个都只能再次封存。

> 授权边界：改 `current/`、SLX 或架构级内容**必须显式授权**并按里程碑写 checkpoint；本 README 与计划文档本身不授权任何模型改动。

---

## 12. 目录地图

| 路径 | 内容 | 当前生产 |
|---|---|---|
| [`SAR20.m`](SAR20.m) | 唯一公开入口 | ✅ |
| [`current/src/`](current/src/) · [`current/models/`](current/models/) | 108 个 `.m` + 唯一 `.slx` | ✅ |
| [`current/calibration/`](current/calibration/) | 校准相关归档数据 | 📜 |
| [`config/`](config/) | 工厂参数、case 构造器、名义 MAT | ✅ |
| [`state/`](state/) · [`release.json`](release.json) | 已应用配置与历史回执 | ⚠️ 混合，仅 `applied_config.json` 有效 |
| [`docs/`](docs/) | 规格、读图、参数、方案、全面分析、项目计划、文献 | 文档 |
| [`design/`](design/) | 2026-10-26 验收/工程/前端/调度草案 | 📜 含未实施设想 |
| [`analysis/behavior/`](analysis/behavior/) | 52 个实验目录的真实 as-run 证据 | 📜 归档 |
| [`analysis/local_debug/`](analysis/local_debug/) | 零 MATLAB 只读探针与离线面板 | 🆕 |
| [`analysis/debug_ui_20261105/`](analysis/debug_ui_20261105/) | 暂停的候选与恢复索引 | ⏸️ 未晋升 |
| [`_preserved/`](_preserved/) | 改动前备份 | 📜 可回滚 |
| [`dependencies/toolkit/`](dependencies/toolkit/) | MathWorks SATK 2026.10.b（第三方） | 运行依赖 |
| `dependencies/analysis_env/` | 本地 Python venv（**可再生，不入库**） | 忽略 |
| [`CHECKPOINT.md`](CHECKPOINT.md) | 倒序追加恢复日志，最新在头部 | 📜 历史 |

---

## 13. 文档索引

| 文档 | 用途 |
|---|---|
| [**设计约束闭环 ERROR_BUDGET_REV03.md**](design/budget/ERROR_BUDGET_REV03.md) | **指导电路设计**：Rev0.3 指标 → 输入参考误差预算 → 模块规格 → 器件参数 → 验证门；含机器可读 JSON、参数绑定 CSV 与校验脚本 |
| [**项目计划 PROJECT_PLAN.md**](docs/PROJECT_PLAN.md) | **当前唯一路线**：M0–M4 的验收门、命令、回滚、证据层级 |
| [全面分析 ENGINEERING_ANALYSIS.md](docs/ENGINEERING_ANALYSIS.md) | 系统诊断：目标/时间线/架构/证据总账/治理/风险分级 |
| [CAAZ 与 ADI](docs/CAAZ_ADI.md) | 三篇原文各提供什么、已跑通的 CAAZ N8、ADI 候选边界 |
| [产品规格 SPEC](docs/SPEC.md) · [spec.yml](docs/spec.yml) · [对齐记录](docs/ALIGNMENT.md) | Rev0.3 产品合同、机器可读约束、历史迁移 |
| [模型计划 MODEL_PLAN](docs/MODEL_PLAN.md) · [读图](docs/READ_GRAPH.md) · [参数](docs/PARAMETERS.md) | 历史设计输入 / 框图读法 / 字段语义 |
| [验收合同](design/behavioral_acceptance.md) | 里程碑 A/B、11 项自动检查、`budget_missing` 规则 |
| [非理想三态表](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) | 已实现 / 已启用 / 未覆盖逐项核对 |
| [文献索引](docs/PAPERS/INDEX.md) | 27 份 PDF 的路径、来源与 SHA-256 |
| [第三方声明](NOTICE.md) | SATK 与文献的许可、版权与移除方式 |
| [English README](README_EN.md) | 英文版入口页 |

---

## 14. 第三方内容与许可

- `dependencies/toolkit/` 为 **MathWorks Simulink Agentic Toolkit 2026.10.b**，按自带 `LICENSE.md`（BSD-3 变体，限制仅与 MathWorks 产品/服务一起使用）随仓库分发，版权归 The MathWorks, Inc.
- `docs/PAPERS/` 内 **27 份 PDF** 为 IEEE / ISSCC / CICC / 厂商数据手册 / 美国专利等第三方文献原文，按用户「全部上传，严格完整」的决定保留，版权归各原作者与出版方，仅作研究引用与可追溯性用途。若权利方提出异议，请通过 issue 联系移除。
- 本仓库自身代码与文档**尚未声明开源许可证**；在 LICENSE 明确之前，请勿假定可自由再分发或商用。
- 详见 [NOTICE.md](NOTICE.md)。

---

## 15. 引用

参见 [CITATION.cff](CITATION.cff)。**论文复现状态未完成时，请勿将本模型引用为论文结果的验证。**

---

<div align="center">

<sub>最后整理：2026-11-05 · 生产模型 `91973cf7…` · 当前阶段：normal 基线已发布，扩展目标暂停 · 本页与 [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 为当前口径</sub>

</div>
