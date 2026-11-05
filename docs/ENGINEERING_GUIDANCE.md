# SAR20-5 工程分析与指导意见

> **本文地位**：基于 2026-11-06 对当前生产模型 `91973cf7…` 的 **L0 静态结构取证** 所作的判断与行动建议。
> 它取代此前散落在 `CHECKPOINT.md`、`ENGINEERING_ANALYSIS.md §8` 中关于「8 项未实现效应」和「哪里能改」的粗略表述；
> 里程碑的**执行**仍以 [`PROJECT_PLAN.md`](PROJECT_PLAN.md) 为准，本文负责回答「为什么先做这个、改哪里、怎么验」。
>
> 取证来源：`analysis/model_map/model_map.json`（由 SLX ZIP/XML 解析）、`current/src/**/*.m`、`design/budget/error_budget_rev03.json`。
> **本文不含任何新仿真结果**；能声称与不能声称见 §5。

---

## 0. 一句话结论

**这个工程的瓶颈不在「跑不通」，也不在「看不懂结构」，而在「同一个 `.m` 被 4–9 个块跨阶段复用、32 路日志的读取器已失效、状态源三方冲突」，导致任何单次运行都无法归因到单个物理误差源。**
因此第一优先级不是补 8 项非理想效应，而是**先把可观测性与单源消融通道修通**；补效应必须排在其后，且其中一部分根本不需要从零写。

---

## 1. 结构分析：三个反直觉的比例失衡

| 观察 | 数据 | 含义 |
|---|---|---|
| **观测面比计算面还厚** | `Diagnostics` **26 块**，超过最大的计算阶段 `Sar1TrialRaCt` **20 块**；全图 **32 个 ToWorkspace**，其中 **23 个挤在 EventStep**（占该层 59 块的 39%） | 模型被当成「证据生产机」用；结构复杂度主要来自记录而非计算 |
| **数字链比模拟核心复杂 2.5 倍** | `Fpga` **50 块 / 38 连线**，`Adc` **20 块 / 21 连线** | 名义重构、dither、校准、冻结候选全在片外；看 ADC 只看懂了全图不到 1/3 |
| **一处源码改动会跨阶段扩散** | 33 个 M-S-Function 块只对应 **16 个入口**：`behavior_wiring_sfun` ×9 跨 **5 个阶段**，`behavior_backend_sfun` / `behavior_frontend_sfun` 各 ×4 跨 **4 个阶段**，`behavior_control_stage_sfun` ×3 | **改一个 `.m` 会同时影响最多 9 个块、5 个计算阶段**；这是「改不动、不敢改、改了判不了」的结构性根因 |

**直接推论**：任何「改源码试试看」的做法在这个模型上代价极高。优先用 `apply` 改参数、不要动 `.m`；确需动 `.m` 时，必须先列出该文件被复用的全部块与阶段（源码地图页签可查），并做全阶段回归。

### 顶层接口契约（真实连线，可作为回归锚点）

```
Driver:1      → EventStep:1
Calendar:1    → EventStep:2
SystemTime:1  → EventStep:3
EventStep:1   → Code20
EventStep:2   → CodeValid
EventStep:3   → CodeMeta
```

顶层只有 6 条线、`EventStep` 是唯一枢纽。这 6 条连接是**改动后最便宜的第一道结构回归**：任一改动若改变了顶层端口映射，立即判失败。

---

## 2. 语义与时序：状态在哪里、顺序是什么

- **状态**：整图 6 个 UnitDelay，只有 Adc 内 `SampleCharge[148]` / `RaCtState[149]` / `SarState[150]` 是模拟状态 owner；另 3 个（`BankOwnerState[454]` / `TxRxState[415]` / `ReferenceHistory[418]`）是数字或仪器记忆。
  别名 `FE353/RA48/SAR51` 与文档里的 `[353]/[48]/[51]` 是**状态向量宽度（double 个数）**，不是 SID。
- **候选值靠端口传，不靠寄存器**：`DacCtFeedback` in=9/out=5、`Sar1TrialRaCt` in=9/out=6、`ChargeReturnRaReset` in=8/out=4。六个阶段的输出只是下一状态的**候选**，最终只经那 3 个 UnitDelay 供下一事件使用。
- **执行顺序 ≠ 层次树顺序**：SLX 里 Adc 的 7 个子系统按字母存储（`derived.adc_tree_is_alphabetical = true`）。真实顺序见 §3.4 表；第 7 个 `Diagnostics` **in=8 / out=0、没有任何出线**——这从结构上证明了它只读观察、物理上无法回接控制路径（`READ_GRAPH.md §40` 的规则有结构证据）。
- **同一时钟沿优先级**：由 `[tick, priority]` 决定，同一时刻允许多类事件，不能只按 time 去重。73 个事件 / 48 组唯一时刻，0–90 ns；`ta_compare=8` / `ta_feedback=7` 是数据核对结果，不是引用结论。
- **92 ns guard / 138 ns 收槽 / transport ON 约 538 ns** 属 `READ_GRAPH.md §54` 的调度与解释页时间线，**不在** `behavior_calendar.m` 日历内，不要把 RX 时刻当成新的模拟端点。

---

## 3. 详细分析：四个真正卡住的地方

### 3.1 可观测性是断的（最高优先级）

32 个 ToWorkspace 产生 32-logger 的 `simout.mat`，而 `analysis/mat_reader.py::read_logger_plan` 对它报
`indexed 0 logger data arrays for 32 SimulationOutput variables`。
`analysis/local_debug/sar20_probe.py` 只是**绕过**它（改读 `parameters.mat` / `selected.mat` / `parameters.json`），原工具**未修**。

> 后果：后续任何单源消融实验，即使仿真跑完，事件级日志也读不出来 → **消融做了等于没做**。这是所有后续里程碑的前置依赖。

### 3.2 状态源三方冲突

`release.json`（10-26）/ `state/SESSION_READY.json`（10-27）/ `state/applied_config.json`（唯一与当前 SLX 对得上）互相竞争，
`CHECKPOINT.md` 是 219 KB 倒序追加、含多个互相竞争的「最新」段。`CURRENT.json`（M0）尚未创建。

### 3.3 基线不可归因

99.133 dB / ENOB 16.17 bit 是**所有已开启非理想项联合一次运行**的结果，无法分离任一单源贡献
（`NORMAL_NONIDEALITY_COVERAGE.md` 明载）。同时：
- 当前工作点是 10 V FSR、calibration/transport/DEM/dither/jitter 全 OFF；Rev0.3 产品口径是 8.192 V，两者噪声功率差 **1.49×**；
- 预算 `closure.verdict = NOT_CLOSED`：已建模 77%、**18% 完全无模型**（AZ 8% + 参考/驱动 10%）、另 22% 依赖未经实测的 tracking 收益；
- `spec.yml:57` 的 28 pF「每半边 / 差分总和」定义 TBD，若为总和则每半边 ~14 pF、采样预算跳到 ~88%，直接不闭合。

### 3.4 修正旧口径：8 项「未实现效应」其实是四种不同状态

此前一律表述为「8 项未实现、均需改 SLX」过于粗糙。源码静态取证显示应分四类：

| 类别 | 项 | 源码证据 | 真实成本 |
|---|---|---|---|
| **A. 内核已实现、当前 OFF** | `ra_noise` | `behavior_backend_step.m:52,139,152-158` 有 OU 噪声计算；`behavior_ra_noise_validate_backend.m` 校验 `sigma_vx_rms` / `seed_u64` | **最低**：可能有现成参数通道，需先核实是否已被计入正常覆盖表 |
| **B. 有 flag 与 schema、内核硬守卫为 false** | `az_noise` / `reference_noise` / `nonlinear_ra` / `replica_delay` | `behavior_backend_step.m:434-438` 显式 `assert(~p.ni.…, 'NI %s is not implemented in this deterministic kernel.')`；`behavior_backend_parameters.m:36-37` 已预留全部 flag | **中**：去掉守卫 + 在 `behavior_backend_step.m` 补物理项；**不需要新建 SLX 块** |
| **C. 有独立配置/守卫模块、但物理层无注入点** | `comparator_noise` / `reference_recovery` | `behavior_comparator_configuration.m`（166 行）有 `derive/check` 双模式与 `sar1_noise_rms_v` / `sar2_noise_rms_v` / `tie_decision` / `seed_u64`；`behavior_ra_noise_guard.m`（364 行）对 `reference_recovery` 直接 `error('… not implemented')`。但 `ResidueCtCompare` **in=2 / out=1 / sfun=0**，是纯原生比较块 | **高**：必须改 SLX 增加注入点，但配置链已写好，不是从零写模块 |
| **D. 生产源码零命中、只在文档里** | `timing_mismatch` / `dac_sampling_bw` / `online_shuffler` | `current/src/**/*.m` 全文无匹配，仅 `PROJECT_PLAN.md` / `ENGINEERING_ANALYSIS.md` 提及 | **最高**：确需从零设计 + 改 SLX |

> ⚠️ 本分类来自源码静态取证，与 `analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md` 的既有归类**尚未逐项交叉核对（待确认）**；若不一致，以源码为准并回填该表。

### 3.5 冻结边界：哪些文件绝对不能动

`sar20_pp_verify_v3_qualification.m:6` 把以下 4 个文件的 SHA-256 硬编码 pin 住：

```
sar20_bank_owner_init.m  /  sar20_bank_owner_step.m
sar20_bank_certificate_sha256.m  /  sar20_bank_sha256.m
```

同一脚本还写死 `acceptance = 'NOT_ACCEPTED'`、`activation = 'none'` —— **校准/Bank 链不会自动激活是结构性保证，不是待办事项**，不要绕过。其余约 104 个 `.m` 可改，但受 §1 的复用耦合约束。

---

## 4. 指导意见

按「依赖顺序」而非「重要性」排。每条给出动作、依据、验收门、风险与授权边界。

### P0 — 先修通道（零授权、只读、Mac 可完成，建议本周先做）

| # | 动作 | 依据 | 验收门 | 风险 |
|---|---|---|---|---|
| P0-1 | 修复 `analysis/mat_reader.py::read_logger_plan` 对 32-logger `simout.mat` 的解析，参照 `sar20_probe.py` 的读取路径 | §3.1 | 能完整列出 32 条 logger 并与 `SimulationOutput` 变量一一对应；对权威 N256 run 回放无异常 | 低；只动 analysis 工具，不碰 `current/src/`、SLX、仿真结果 |
| P0-2 | 建立 `CURRENT.json` 单一状态源，把 `release.json` / `SESSION_READY.json` 标记 archive | §3.2 | 与 `applied_config.json` + SLX SHA `91973cf7…` 一致；两份 README 与计划只引用它 | 低；纯文档/状态治理 |
| P0-3 | 冻结 `spec.yml:57` 的 28 pF 定义，重跑 `verify_budget.py` 看闭合状态变化 | §3.3 | 定义写入 spec 且预算重算可复现 | **中**：会改变预算结论，需先确认设计口径（Rev0.3 8.192 V） |

> P0-3 之前必须先回答「28 pF 是每半边还是差分总和」，这是**下一个设计评审的第一议题**；答不出来，后面所有 Cmin / Ron / 噪声分配都不可信。

### P1 — 让基线可归因（当前最高价值的实质动作；不改 SLX，需 Windows MATLAB `SAR20_MatlabControl` 计划任务通道）

- 执行 `PROJECT_PLAN.md` 的 M1：10 项 leave-one-out + only-one-on，**验收标尺用 M0.5 预算表，不是「跑通」**。
- 三条硬约束：
  1. `P.ni` 是**派生摘要不是开关** → 必须改物理配置字段，改 `P.ni` 无效；
  2. 因 16 入口复用 33 次（§1），**只改 `apply` 参数、不改 `.m`**；
  3. 每次显式传 `run_path`，不用「最新静态测试」当上一轮正弦记录；改参数后必须 `SAR20('apply')`，**不能用 GUI Run**（不读工厂文件、不建公开归档）。
- 每组必须记录：10 V normal 与 8.192 V Rev0.3 的 **1.49× 噪声功率差**、单源输入参考 µV rms、与预算分配项的对应。
- 退出条件：能给出「每一项开启/关闭对 SNDR 的独立贡献」表；给不出就不进入 P2。

### P2 — 口径统一（M2）

- 同口径 20k 点谱、M1/M8 的 7 dB 实测对照、多频多种子稳定性。
- **禁止**用理论 9.03 dB 上限当实测收益；`MODEL_PLAN.md:77` 要求来自闭环协方差，不能用「滤波前 / 8」捷径。
- 只有到这一步，才有资格讨论「成电 CICC 2026 是否复现」；当前判定仍是 **NOT REPRODUCED**。

### P3 — 补非理想效应（架构级，**需逐项显式授权**）

按 §3.4 的真实成本 + 预算缺口排序，而不是按编号：

1. **B 类先做**：`reference_noise`（补 18% 无模型的一半）、`az_noise` → 落点 `Sar1TrialRaCt` / `behavior_backend_step.m`，去守卫 + 补物理项，不动 SLX；
2. **A 类核实**：`ra_noise` 是否已有完整参数通道，若有则直接纳入 P1 消融矩阵；
3. **C 类**：`comparator_noise`（预算中 RA/比较器一阶折算 16.02/8.97 µV 超预算）→ 落点 `ResidueCtCompare`，**必须改 SLX**；`reference_recovery` 排在后面；
4. **D 类最后**：`dac_sampling_bw` / `timing_mismatch` / `online_shuffler`，需先有规格定义。

每项按里程碑执行并写 checkpoint：**改动范围 → 备份 → 回归通道（顶层 6 条连线 + 256 条 code20 逐条）→ 回滚方案 → 授权**，不接受边改边试；失败即回退到交接状态并清理。

### 明确不要做

- 不要拿 99.133 dB 去对标论文 100 dB / 3.6 mW / 0.53 mm²（那些是硅测，本工程无对应量）；
- 不要引用 `analysis/behavior/current_diagrams_20261104/*.png`（`d4e7fc99…` ≠ 当前 `91973cf7…`，且导出自身标记待视觉复核）；
- 不要按层次树的字母顺序理解执行顺序；
- 不要绕过 4 个 SHA 冻结锚点或 `NOT_ACCEPTED`；
- 不要把 L0 结构图、归档形式验证或代理物理证据升级为 signoff 结论。

---

## 5. 能声称 / 不能声称

| ✅ 能声称 | ❌ 不能声称 |
|---|---|
| 顶层 6 条接口连线、14 系统 / 290 块 / 203 连线、16 入口复用分布、6 个 UnitDelay 与 3 个模拟状态 owner 均来自当前 SLX 静态解析 | 模型能编译、能仿真、时序正确、视觉与 Simulink 一致 |
| `Diagnostics` 无任何出线，结构上不可能回接物理路径 | 模块在闭环中满足预算 |
| 8 项效应按源码实际状态可分为 A/B/C/D 四类，其中 B 类不需新建 SLX 块 | 任一模块已达标、SNR 100 dB / SINAD 98 dB / THD −105 dBc / INL ±4 ppm 已满足 |
| 预算解析链可复算（79 项 PASS），且 18% 噪声功率无模型是显式结论 | 99.133 dB 与 Rev0.3 合规有任何关系 |
| 顶层接口可作为最便宜的结构回归锚点 | 任何 PDK / 功耗 / 面积 / PEX / 硅 / signoff 结论 |

---

## 6. 建议检查点

| Checkpoint | 完成标志 |
|---|---|
| CP-0 | P0-1 修好且 32 路日志可读；P0-2 `CURRENT.json` 生效 |
| CP-1 | 至少 3 项单源消融给出独立贡献，且与预算分配项对得上 |
| CP-2 | 20k 点谱与 M1/M8 7 dB 对照在同一口径下完成 |
| CP-3 | B 类效应至少 1 项经授权落地并通过全阶段回归 |

断流后从最近的 CP 续做，不要重跑已通过的部分。

---

*取证方法：SLX 按 ZIP/XML 静态解析（零 MATLAB、不加载模型、不仿真）；事件日历由解析 `behavior_calendar.m` 源码展开。*
*本机无 `xelatex` / `pdflatex` / `latexmk`，故以 Markdown 交付；如需可复现 PDF，需另备 TeX 环境。*
