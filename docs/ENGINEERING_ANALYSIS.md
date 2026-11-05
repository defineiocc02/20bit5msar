# SAR20-5 行为级工程全面分析

> 分析日期：2026-11-05　｜　对象：`sar20_5_simulink_20261020`　｜　性质：**只读分析 + 仓库整理**，未运行 MATLAB、未改动 `current/`、`config/`、SLX 或任何仿真结果
>
> 一句话结论：**这不是一个跑不通的工程，而是一个「证据链比模型厚、候选比生产多、目标比验收清楚」的工程。论文复现尚未发生，当前 99.133 dB 基线不可归因，是最需要优先解决的实质问题。**

---

## 0. 摘要：五条核心判断

| # | 判断 | 证据强度 |
|---|---|---|
| 1 | 成电 CICC 2026 **未复现**，而且工程内尚未定义「复现」的判据；99.133 dB 与论文 100 dB 数字接近但口径完全不同 | 确证：全库无论文对照报告；`design/behavioral_acceptance.md:63` 自述无误差预算与验收目标 |
| 2 | 生产模型自 `91973cf7…` 起**零净变化**，11-05 全天大量真实工作全部停留在私有候选/封存 ZIP | 确证：与 `_preserved/before_debug_ui_20261105_mac/` 逐 SHA 比对 116 个 `.m`/`.slx` 全一致 |
| 3 | 当前 normal 基线是**所有非理想项联合一次 N256**，无法分离任一单源贡献；参数多为工程假设 | 确证：`NORMAL_NONIDEALITY_COVERAGE.md` 三态表与 `:27` 声明 |
| 4 | 工程存在 **5 套并行目标口径**、**至少 5 个互相冲突的状态源**，且此前不是 git 仓库 | 确证：docs/ 与 state/ 逐文件核对；`git rev-parse` 失败 |
| 5 | 真正阻碍推进的是「无法判定收益」→「不敢晋升」的闭环：基线不归因 → 改动无法验收 → 只能封存新候选 → 生产停滞 | 推断，但与时间线上 8 次「未晋升/封存/回滚」一致 |

**方法**：四个方向并行只读取证（历史与目标、源码架构、性能证据、治理状态），所有数字来自工程内已落盘文件；工具的中间输出不写回生产目录。证据层级定义见 §1.2。

---

## 1. 范围、方法与证据层级

### 1.1 取证范围

| 方向 | 覆盖 |
|---|---|
| 历史与目标 | `CHECKPOINT.md` 全文 665 行（219 KB，倒序追加）、`design/` 5 篇、`docs/ALIGNMENT.md` / `SPEC.md` / `MODEL_PLAN.md` / `READ_GRAPH.md` / `PARAMETERS.md` / `CAAZ_ADI.md` |
| 架构 | `current/src/` 全部 108 个 `.m`、`config/*.m`、`SAR20.m`、`README.md` 架构段、非理想覆盖表 |
| 性能 | `CHECKPOINT.md` 中 49 行含指标的记录、`release_receipt.json`、`DYNAMIC_ACTUAL_256.json`、`summary.json`、各 `RESULTS.md` |
| 治理 | 目录/文件/体积统计、`state/`、`release.json`、`_preserved/`、封存索引、工具链实测 |

### 1.2 证据层级（本报告统一口径）

| 层级 | 含义 | 本工程代表 |
|---|---|---|
| L0 静态审计 | 哈希、清单、源码级比对，不运行任何求解器 | 119 项逐 SHA 核对；9 组同配置分组确定性检验 |
| L1 函数门 | 纯数学/隔离核验证，未接 ADC 主图 | 采样 RC+kT/C 7168 点、OU+AZ+DAC、10 V 范围等 5 门 |
| L2 smoke / N8 | 整图短记录，验证事件与码，不产生频谱 | N8 plain / tap / 私有 CAAZ 两 N8 |
| L3 整图 N256 | 公开入口真实仿真 + FFT 指标 | 当前 normal `behavior_12d08121…` |
| L4 归档形式验证 | 历史 as-run 重放、冻结系数、holdout 回执 | `accepted=false` 的 calibration 链 |
| L5 代理物理证据 | 行为级非理想代理、条件漂移 | RA OU 密集观测、σVX/σVY 代理 |
| L6 PEX / 硅 / 功耗面积 | 需电路实现与工艺 | **本工程完全没有** |
| L7 signoff | 完整 PVT、DNL/INL、多频多种子 | **本工程完全没有** |

> 报告中所有「不能声称」都基于这一点：**下层证据不得升级为上层结论**。工程自己也大量使用了这类边界声明（见 §4.4）。

---

## 2. 工程定位：五套并行的目标口径

同一个工程同时承担 5 套不同的验收口径，且互相声明「不替代」。这是理解后续所有混乱的起点。

| 口径 | 出处 | 关键量化约束 | 当前满足情况 |
|---|---|---|---|
| **A 产品规格 / 接口合同 Rev0.3** | `docs/SPEC.md`、`ALIGNMENT.md` | 180 nm、5 MS/s、FSR **8.192 V**、SNR ≥100 dB / SINAD ≥98 dB / THD ≤−105 dBc、INL ≤±4 ppm、DNL <1 LSB20、AD7961 CP-32-7、单 LVDS 250 MHz、32-bit 帧、N−2 读槽 | 当前 normal 用 FSR 10 V、无 LVDS、无校准、无静态线性度；**口径不同，不能判达标** |
| **B Rev0.1/0.2 历史对齐** | `ALIGNMENT.md:11-37` | 4 lane 50 MHz、BANK/OVR sideband、6+15 DT 等 | 已明确「保留迁移过程，不能覆盖 Rev0.3」 |
| **C 新行为模型验收合同** | `design/behavioral_acceptance.md` | 里程碑 A（8 码）→ B（256 码）；11 项自动检查；`budget_missing` 即不得报达标 | A/B 有真实运行，但 `:63` 明确「尚无误差分配，也没有 SNDR/功耗验收目标」 |
| **D 行为工程/调度草案** | `design/` 其余 4 篇 | 唯一入口/单一参数源、warm `sim()` ≤5 s、48 唯一事件时刻/slot | 草案自述「包含未实施设想，不作为当前集成/运行证明」 |
| **E 当前工作点（论文 normal）** | `README.md`、`CHECKPOINT.md` 11-04/05 | 5 MS/s、FSR **10 V**（来自对论文 5 Vp 的解释假设）、单物理前端、N=256、非理想联合 ON | 唯一已晋升成果：SNDR 99.132766 dB |

**互不替代的直接声明**：`README.md:64`「当前论文单bank/10V估计配置不替代未来产品电压与外部接口合同」；`design/behavioral_acceptance.md:15`「不把旧核性能当作新模型达标门槛」；`docs/PARAMETERS.md:202`「历史直通 RAW 证据不能充当本次 RX 结果」。

> **判断**：口径多不是问题，问题是**没有一处机器可读地写明「当前生效的是哪一套、什么算完成」**。于是每次讨论都要靠自然语言重新划界——`CHECKPOINT.md` 中数十处「不能称 XX」「不冒称」正是这种补丁。

---

## 3. 时间线：目标漂移与「未晋升」循环

`CHECKPOINT.md` 为倒序追加，最新在文件头部。按日期还原：

| 日期 | 主要目标 | 真实产出 | 切换后被封存 / 回滚 / 未晋升 |
|---|---|---|---|
| 10-26 建库 | 行为模型基线 | 六主图 N8 孔径、两组 N256、2048 训练 / 1024 holdout | 原 1540 节点 MNA 模型与历史 raw 封存；LVDS 仍未接主图 |
| 10-27 LVDS | 传输链接回主图 | 011447Z 晋升；主图 RX N256 SNDR 109.827136 | `pending_finite_dac`/`pending_bank` ZIP「均不是已接入功能」；训练后验拒绝；文档候选 pending |
| 10-28 训练/holdout | RX 长训练 + Bank | 2048 训练 RMS 1.756988 µV；预登记 holdout SNDR 117.458169 | **14:49 UTC 用户要求「暂时中止」**；Bank N256 协议未执行；v1/v2/v4 冻结未跑；`accepted=false` |
| 10-30 噪声 / Bank | RA OU、DEM×dither、Bank 三案 | 6 seed 统计、四案 N256、基础 N256 | 多次「恢复不是字节回滚」、视觉/坐标门未过、`NOT_ACCEPTED`；缓存字节原态无法恢复 |
| 10-31 可读性重构 | 39 文件 184 处多语句 | 十六批纯函数重构，源码 102 文件 / 9426 行 | **内核改动首次尝试整图门未过，完整回滚**，102 文件 0 差异；两个候选判定不可行放弃 |
| 11-04 normal 工作点 | 用户改「预期正常工作点」，禁止再追加压力性能 | 五项函数门、N8/tap/N256/ideal 六 case 全 passed；SNDR 99.132766 | 96.915 dB 压力点留历史；ADI 组件暂存不接入；M1/M8、FG38 候选未建图 |
| 11-05 上午 | 授权「以成电为底座开发 PKU CAAZ 与 ADI」 | 私有图 `63283fd` 两组 N8 PASS；frozen backend054 函数门 | FrameAvg `PARTIAL_SAVED`；ADI 558 仅候选；10 MS/s 待同意 |
| 11-05 白天 | 改「可视化与调试能力建设」 | N8 smoke PASS；分类导航初稿模型 `9626ccf9` 并真导出截图 | graph1 在 SDK 拒绝 `ContentPreviewEnabled` 处停止；UI/sample 为中断草稿 |
| 11-05 傍晚 | **用户明确暂停，清理收尾后停止** | 13 个任务注销、210 文件封 ZIP、119 项逐 SHA 复核 | 生产 SLX 仍 `91973cf7…`，**尚未部署任何调试候选** |

**三次关键认知纠正**（`CHECKPOINT.md:141-150, 340-347`）：

1. **SLX 哈希认知纠正**：`apply` 会把 P 内嵌进 SLX 并 `save_system`，所以「SLX 哈希 = f(模型结构 + 内嵌 P)」，205 个 run 有 205 个哈希；此前十几轮写「模型未变」是错的。
2. **仿真成本纠正**：N=8 约 3 s 但**算不出 SNDR**（`not_run_short_capture`）；N=256 才是频谱 run，64.6–140 s（中位 74.4 s）。
3. **确定性纠正**：按 6 个顶层字段分组得到「SNDR 跨度 52.9 dB」的假象；改用整份 `parameters.json` SHA-256 分组后得 9 组真同配置（21 个 run），5 项指标最大跨度 `0.000e+00`。教训原文：「比数值之前，先证明两次比的是同一个东西」。

> **判断**：这三次纠正都是**验证口径设计错误，不是被测对象有问题**——这类返工在一次次目标切换中反复出现，是「无机器可读验收规格」的直接成本。

---

## 4. 架构与实现盘点

### 4.1 规模

| 项 | 数值 |
|---|---|
| 生产源码 | `current/src/` **108 个 `.m` / 10 264 行 / 9 个子目录** |
| 生产模型 | `current/models/SarAdc.slx`，492 760 B，SHA `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` |
| 工程总体 | **596 MB / 8 874 文件**（其中生产源码+模型约 1.3 MB） |
| 主要体积 | `analysis/` 294 MB（behavior 213 MB、52 个实验目录）；`dependencies/` 227 MB（`analysis_env` venv 184 MB + SATK 43 MB）；`docs/` 71 MB（PAPERS 59 MB） |
| 可再生垃圾 | 940 个 `.pyc`、多处 `__pycache__`、`.DS_Store` |

源码分布（按职责）：`analysis` 16/2414、`calibration` 24/1964、`control` 12/737、`digital` 6/247、`frontend` 10/817、`model` 12/1503、`physics` 11/1109、`reference` 7/164、`transport` 10/1309。

### 4.2 模型骨架（已确证）

- 唯一入口 `SAR20.m`（`open` / `setup` / `apply` / `check` / `run` / `sample` / `calibration`；`calibration` 当前显式抛错）。
- 唯一模型 `SarAdc.slx`；三个标准 UnitDelay 状态 owner：**FE353 / RA48(BK48) / SAR51(SC51)**，无第二套电荷记忆。
- 固定 **48 组事件 / 73 tokens**：CNV 0、coarse 12.5 ns、RA 31.25 ns、12 次 D2（45…72.5 ns）、8 次 TA 比较（75…83.75 ns）、RawReady 86.25 ns、release 90 ns、guard 后 92 ns 下一采集。
- **12 D2 / 8 TA 比较 / 7 次物理反馈**；第 8 次比较无物理更新但 RAW LSB 仍有数字权重 1，故 SINC² 除以 **8** 而非 `sum(weights)=36`（`behavior_decode.m:21-23`）。RA 后无新增 S/H。
- RAW 顺序 `[D1, D2, DT, sample_id, epoch, valid]`，11/12/8 位原始判决字；顶层 `CodeValid` 是旧 Bank 资格输出，**不能当采样有效性**。
- FPGA 域按公开 D1/D2/DT 与名义系数重构，片外训练参考不得读取内部电容/held/残差。

**明确是工程假设、非论文披露**：全部逐沿时刻（论文只给约 90 ns 转换等总节拍）、FSR 10 V 的 5 Vp 差分口径、A0/UGB/极点、Cp 100 fF/half、σunit 0.068%、CINC 900 fF、σVX 0.512785 mV、σVY 0.286929 mV、1039×27 fF 半边电容解释、完整 DAC1 开关码本（`config/adc_parameters.m:176-181`）。

### 4.3 非理想效应三态

| 状态 | 项目 |
|---|---|
| **已实现且 ON**（当前 normal P） | kT/C、cap_mismatch、comparator_noise（仅 SAR2/TA）、ra_noise（A1 通道 OU 代理）、ra_finite_gain/bandwidth、az（ordinary，无随机 AZ 噪声）、dac_settling、parasitic（前端 Cp + 固定 RA 输出负载）、sample_settling |
| **已实现但 OFF** | jitter、dither、DEM、calibration（train/frozen/Bank）、transport、finite slew（`slew=+Inf`） |
| **未实现** | `reference_recovery`（`behavior_ra_noise_guard.m:112` 明确「not implemented」）、`reference_noise`、`nonlinear_ra`、`replica_delay`（`behavior_backend_step.m:434` 显式拒绝）、SAR1-fine / Flash 比较器噪声 |
| **源码中无实现证据** | `timing_mismatch`、`dac_sampling_bw`、`online_shuffler`（仅在 SPEC/MODEL_PLAN 作为设想出现） |

另注：`P.ni` 是**由物理配置派生的摘要，不是独立开关**（`docs/PARAMETERS.md:26,83`）；`P.debug.adi_enabled` 只开观察、不开物理功能。

### 4.4 审计锚点

- **4 个硬编码 SHA-256 冻结源文件**（不可改）：`sar20_bank_owner_step` / `sar20_bank_owner_init` / `sar20_bank_sha256` / `sar20_bank_certificate_sha256`，由 `sar20_pp_verify_v3_qualification.m` 用 `which()` + `java.security.MessageDigest` 逐字节比对；`CHECKPOINT.md:305` 另称系统排查后实际哈希锁定边界涉及 9 个文件。
- 另有 qualification 字节哈希、frozen cache（`lifecycle='frozen_for_holdout'`, `acceptance='NOT_ACCEPTED'`）、多份 `SHA256SUMS` / `MANIFEST` / receipt 分层锚点。
- 这些锚点保证的是**身份可溯**，不是物理正确性。

---

## 5. 性能证据总账

### 5.1 当前权威结果（L3，唯一已晋升）

`analysis/behavior/public_normal_20261105/release_actual/`，SLX `91973cf7…`，run `behavior_12d08121-d679-40cd-9ee2-bc334ff42955`，R2024a Update 6，`run_wall_s 117.7867422`，`selected_records 256`，`factory_p_exact / cold_p_exact / output_exact / global_rng_unchanged` 均为 `true`：

| SNR | SNDR | SFDR | THD | ENOB |
|---|---|---|---|---|
| 99.712414227270258 dB | **99.132765903966785 dB** | 111.78407088195453 dB | −108.16556427335165 dB | 16.174878057137342 bit |

同量程 NI 关闭基线：SNDR **109.16497669573319** dB（sim 59.4172631 s）。独立 NumPy 从实际 CSV 复算，最大差 `3.44e−11 dB`。配置：Fs 5 MHz、Fin 97.65625 kHz / bin5、峰值 4.45625469 V（−1 dBFS）、差分 FSR 10 V、seed 20261020、first_id 4、epoch 1、矩形相干窗、DC 排除、H2–H10 折回。

> 注意：ENOB **16.17 bit**，不是 20 bit。`docs/SPEC.md:43` 早已说明「20-bit 输出字不等于 20-bit ENOB」。

### 5.2 历史整图结果（不同配置，不可互相比）

| 配置 | SNDR | 性质 |
|---|---|---|
| 233854Z N256 off（kTC/失配/DEM/dither/AZ/cal 关闭） | 109.827136 dB | L3 整图 |
| combined（25 ps common + 10 ps local + ±8 ps 固定） | 95.787621 dB | L3 压力点；原文「缺 SNR 100 / SINAD 98 目标 4.002 / 2.212 dB」 |
| 新单前端 N256（FSR 8.192 V，AZ/kTC/随机噪声关） | 109.345596 dB | L3；「不是 20k 实测 / 全 NI / 论文 99.4 dB 复现」 |
| 基础 N256 / 有限 DAC τ=1 ns | 106.913367 dB | L3 |
| 有限 DAC τ=0.1 ns | 109.844923 dB | L3；0.018 dB 差「单次量化频谱观察，非统计收益」 |
| 6 seed RA OU ON（σVX=1 mV） | 均值 100.654796 dB，σ 0.413765 dB，极差 1.181661 dB | L3 统计；单 seed 101.194257 dB「偏乐观」 |
| 同图 OFF/ON 对照 | 109.827136 → 101.194257 dB（差 −8.632879 dB） | L3；原文「**不是** M1/M8 tracking 收益、PSD 统计、论文 7 dB」 |
| 预登记 RX 独立 holdout（N1024） | 117.458169 dB | L4 归档；`accepted=false / activation=none / NOT_ACCEPTED` |
| 历史 NativeCt / 旧 MNA | 101.91 dB / 99.65 dB（5621 s） | 历史旧核，「不给当前背书」 |

### 5.3 论文目标 vs 工程口径

| 论文（CICC 2026 标题与工程内引用） | 工程 | 是否可比 |
|---|---|---|
| 100 dB SNDR、3.6 mW、0.53 mm²、5 MS/s、硅实测 | 99.132766 dB、行为级、无功耗面积、256 点 FFT | **否**：测量对象与口径不同 |
| 约 7 dB tracking averaging 收益（较高噪声条件） | M1/M8 对照「仍未跑对照」；理论 9.03 dB 上限被明确禁止当收益 | **否**：无实测证据文件 |
| 20k 点频谱 | 256 点（`README.md:31`「论文 20k 点和其他窗口分析尚待扩展」） | **否** |
| 片外 LMS 前景校准 | calibration / frozen / Bank / transport / DEM / dither 全 OFF | **否** |
| 逐沿开关时刻、A0/极点/寄生/噪声/工艺参数 | 未披露 → 工程假设 | **否** |

`99.4 dB` 在工程内仅以「100k/99.4dB 单源预算」「论文 99.4dB 等条件复现」出现，**未绑定到论文具体图表或测量条件，待确认**。

### 5.4 成电复现判定

**结论：没有复现，且当前不具备判定「是否复现」的验收条件。**

确证依据：

1. 全库 `find` 无任何成电论文对照 / 差距报告；已有的 `comparison.*` 全是 run 与 run 之间比较。
2. `design/behavioral_acceptance.md:63`：「尚无新抽象模型与参考之间可接受的电压/码误差分配，也没有此次新模型的 SNDR/功耗等验收目标……不能报告系统规格达标」。
3. M1/M8 的 7 dB 收益**零实测证据**；`CHECKPOINT.md:43`「M1/M8 的 7dB/整机 2dB 收益仍未跑对照」；`README.md:62`「M1/M8 收益、前景校准/独立 holdout、多频/幅度/seed 及合格静态 DNL/INL 仍待完成」。
4. `CAAZ_ADI.md` 表格自述「未披露的逐沿时刻、A0/极点、寄生、噪声及工艺参数仍是明确的模型假设」。

**能声称**：架构骨架与节拍文字对齐（6b 预转换 + 10b 有效 DT + DAC1 电荷残差 + 32× RA/AZ + CINC CT + 12 D2 + 8 TA/7 反馈、约 90 ns 转换）；单点 N256 行为谱自洽、同配置逐位可复现；公开入口 apply→冷开→run→sample 链路真实跑通。

**不能声称**：论文性能复现、7 dB 收益、DNL/INL、20k 点谱、功耗/面积、PDK、多频多种子稳定性、任何 signoff。

---

## 6. 工程治理诊断

### 6.1 没有单一真相源（最高优先）

| 状态源 | 声称 | 实际 |
|---|---|---|
| `release.json` | 2026-10-26，`R4/M8/F2/600MHz/N8`，SHA `8f12e65a…` | 当前 `91973cf7…`；`canonical_mac_root` 指向已废弃的 `项目库/outputs/` |
| `state/SESSION_READY.json` | 10-27，`display_compile_N8_bits…visual_review_required` | 早已 N256 正式发布 |
| `state/applied_config.json` | 11-04，SHA `9197…` | **唯一对得上的** |
| `README.md` | normal N256 已发布 | **2026-11-05 重写后已补齐**暂停、封存、未晋升、五套口径与证据边界；但它仍不是机器可读真相源，M0 的 `CURRENT.json` 仍待建 |
| `CHECKPOINT.md` | 219 KB / 665 行倒序，含多个「最新 / 当前权威续点 / 用户最新授权」 | 头部写「用户已明确暂停」，下文几百行仍是旧目标与旧 `/tmp` 恢复路径 |

其余 5 个 `state/*.json` 全部停在 10-27。此前**不是 git 仓库**（有 `.gitignore` 无 `.git`），所以版本真相全靠自然语言手抄 SHA——`CHECKPOINT.md` 里已出现过「runtime-index SHA 误抄 62 位导致 preflight 失败」。

### 6.2 投入产出失衡

- 596 MB / 8 874 文件里，真正的产品是 108 个 `.m` + 1 个 SLX ≈ **1.3 MB**；`analysis/behavior` 213 MB 是历史证据；`dependencies/analysis_env` 184 MB 是可再生 venv（已在 `.gitignore` 中，但目录仍在）；940 个 `.pyc` 散落。
- `CHECKPOINT.md` 记录过为清理 12 个草稿、约 37 KB 做完整 SHA 记账，同时把 184 MB venv 留在工作区——**仪式化清理与真正的工程卫生脱节**。
- 11-05 全天：N8 smoke、graph1 失败、分类快照、13 个任务导出注销、210 文件封存、119 项逐 SHA 复核，全部真实，但**生产零变化**。

### 6.3 工具链静默失效（本次新发现）

- `analysis/mat_reader.py` 的 `read_logger_plan()` 对当前 32-logger 的 `simout.mat` 已失效，实测报 `indexed 0 logger data arrays for 32 SimulationOutput variables`；**全库无任何文档记录此事**。
- `mat_value` 全量展开 P 需约 30 s（大结构 `calendar` / `adc_groups` / `schedule`），按需读子树只要 0.002 s；`parameters.json` 的 33 个键与 P 逐一对齐，是全量可读投影。
- 这两个问题已由本次交付的 `analysis/local_debug/sar20_probe.py` 绕过，但**原工具未修复**。

### 6.4 恢复能力与单点依赖

- 恢复链：`PAUSE_INDEX.json`（原目录→归档前缀映射）、`candidate_sources_paused.zip`（210 文件逐 member SHA 读回通过）、`_preserved/before_debug_ui_20261105_mac/`、原始需求附件 `~/.codex/attachments/.../已粘贴的文本.txt`（实测仍存在，13 370 B）。链路完整但**入口散在 4 处**，且 `CHECKPOINT.md` 正文仍全是已失效的 `/tmp` 路径。
- 运行单点：Windows `D:/Academic/Projects/sar20m1/SAR20`、MATLAB R2024a Update 6、常驻 GUI PID 27628、计划任务 `SAR20_MatlabControl` COM 通道；`matlab -batch` 因许可证占用会立即退出。`CHECKPOINT.md` 还记录 `license('test')=1` 但 `checkout=0` 的坑。
- Mac 侧无 MATLAB；本次新增的本地探针是唯一零依赖调试通道。

---

## 7. 风险分级

| 级别 | 风险 | 证据 | 影响 |
|---|---|---|---|
| **高·结论** | 基线不可归因 | 覆盖表 `:3/:27`；单源消融缺失 | 任何 CAAZ/ADI/校准改进的 ΔdB 无法解释；论文定量对照无法进行 |
| **高·工程** | 生产停滞，候选堆积 | 11-05 逐 SHA 比对 0 差异；8 次封存/回滚 | 工作无法转化为可交付版本，回滚成本持续上升 |
| **高·工程** | 无单一真相源 | 5 个状态源冲突；此前无 git | 恢复时易选错配置；已发生 SHA 误抄事故 |
| **中·技术** | 非理想覆盖不全 + 参数多为假设 | §4.3 三态表；`config/*.m` assumptions | 99.133 dB 不能外推，不能当 PDK/论文标称 |
| **中·工程** | 工具链静默失效 | `read_logger_plan` 报错 | 事件级解析若误用旧工具会得到错误结论 |
| **中·可复现** | Windows/MATLAB/许可证单点 | 计划任务 COM 通道 | 换机器无法一键复现；CI 不可能 |
| **中·合规** | 公开仓库分发 27 份第三方 PDF + 43 MB SATK | 本次按用户决定全部上传 | IEEE/ISSCC 全文可能触发 DMCA；已用 `NOTICE.md` 标注来源与许可 |
| **低-中·卫生** | 596 MB 中 1.3 MB 是生产 | 体积统计 | 克隆/审阅成本高，信噪比低 |

### 根因链（推断）

```
目标频繁切换
   → 每次切换留下「未晋升候选」
      → 为保护候选建立 SHA/回执/封存/回滚体系
         → 证据链膨胀 + 状态源分裂
            → 恢复成本升高、口径需反复澄清
               → 下次更倾向于「再开一个隔离候选」而非「晋升到生产」
                  → 生产零变化
同时：基线不可归因 → 改动收益无法判定 → 不敢晋升 → 强化上一环
```

---

## 8. 建议路线（摘要；完整计划另见独立文档）

> 📋 **本节已升级为 [docs/PROJECT_PLAN.md](PROJECT_PLAN.md)**。该文档是**当前唯一有效的计划口径**，包含每个里程碑的前置条件、具体命令、消融矩阵设计、验收门、备份与回滚方案、checkpoint 规则、风险登记册与待确认清单。本节只保留摘要，避免两处路线表述分叉。

| 里程碑 | 动作 | 是否需要改模型 / 授权 | 完成判据 |
|---|---|---|---|
| **M0** | 建机器可读 `CURRENT.json` 单一真相源；旧状态源标 archive；根 CHECKPOINT 冻结 | 否 | 任一新会话能在 1 分钟内确定「当前是什么、什么算完成」 |
| **M1** | 固定 N256 / seed / FSR，做**单源消融矩阵**（leave-one-out + only-one-on + M1/M8 对照），产出每项 ΔSNDR 表；建**输入参考噪声预算** | 否（参数注入）；需 Windows 调度授权 | 每个已实现非理想项有独立 ΔSNDR，且预算表可与论文分项比较 |
| **M2** | 同口径 20k 点谱 + M1/M8 的 7 dB 收益对照 + 前景校准/独立 holdout 复核 | 否（参数级）；需授权 | 能明确回答「论文复现到什么程度、差在哪几项、各差多少 dB」 |
| **M3** | 从 CAAZ 与 debug UI 中**选一个**晋升生产，走完 apply → 冷开 → N8 位门 → N256 回归 → README / CURRENT 同步 | **是**，需显式授权；改动前须提交范围、备份、回滚方案 | 生产 SLX SHA 改变且文档同步；ΔdB 无法解释则回滚 |
| **M4** | ADI v2 完整 18-pool / 双 QDAC、10 MS/s | 是，架构级 + 用户另行同意 | 按新里程碑单独定义 |
| **N 系列** | 补齐明确标注 `not implemented` 的非理想效应（均需改 SLX） | 是，逐项显式授权 | 每项独立函数门 + 整图门 + 单源 ΔdB |

**优先级**：M0 → M1 → M2，**M3 之前不要开新特性线**。理由：M1/M2 产出的是「能不能判定收益」这一晋升决策的前提；缺了它，M3 无论选哪个都只能再次封存。完整根因链、证据层级约束、DoD 总表与授权边界见 [PROJECT_PLAN.md](PROJECT_PLAN.md)。

---

## 9. 本次交付物与边界

| 文件 | 作用 |
|---|---|
| `README.md` / `README_EN.md` | 中文工程说明书（默认首页）与结构对齐的英文版：目标口径、架构时序、参数假设、非理想覆盖、运行/调试、证据链、风险与计划入口 |
| `docs/ENGINEERING_ANALYSIS.md` | 本报告（诊断证据） |
| `docs/PROJECT_PLAN.md` | **当前唯一有效计划**：M0–M4 与 N 系列的前置、命令、验收门、回滚、checkpoint、风险登记册与待确认清单 |
| `docs/PAPERS/INDEX.md` | 27 份第三方文献清单（标题/路径/SHA-256/来源） |
| `analysis/local_debug/sar20_probe.py` | 零 MATLAB 本地只读探针：`info` / `decode` / `diff` / `html` |
| `analysis/local_debug/sar20_debug_report.html` | 离线调试面板（256 条真实记录、任意 sample 解码链） |
| `NOTICE.md` / `CITATION.cff` | 第三方组件与文献声明、引用信息 |

探针实测：名义解码（`behavior_decode.m` 的 Python 忠实移植）独立复算 **256/256 条 code20 与 MATLAB 实测逐条一致**；ID 5 分解 D1 = 4.3408203125 V、D2 = +1.609375 mV、DT = −19.53125 µV、code = 979623，与 `README.md` 逐位吻合。`diff` 命令可逐字段定位两个 run 的参数差异（实测 0.2 s）。

> **报告形态说明**：本机无 `xelatex` / `latexmk` / `pdflatex`，因此本次以仓库原生 Markdown 交付，未生成 PDF，也不假称「可复现 LaTeX→PDF」。若需要正式 PDF 版，需在有 TeX Live + ctex 的环境编译，或另行指定生成方式。

---

## 10. 待确认事项

1. 论文 `99.4 dB` 与 `7 dB` 的确切图表/测量条件——工程内只有引用，未见定义。
2. `CHECKPOINT.md` 若干历史段落未给出当时完整 SLX SHA，仅在相邻绑定行有前缀。
3. 2026-11-05 重写后的 `README.md` 已在 §2.2 同时给出全精度指标与展示值，但两者之间的舍入规则仍未显式声明（待确认）。
4. 两份 CICC2026 PDF 正文内除标题外的目标数字（20k 点、实测 SNDR 等）本次未逐页核对。
5. `CHECKPOINT.md:305` 称哈希锁定边界实际涉及 9 个文件，而 `:333` 称 4 个文件硬编码冻结；两者口径差异未消解。

---

## 附录 A：关键命令

```bash
# 本地只读调试（Mac，零 MATLAB）
cd analysis/local_debug
PY=../../dependencies/analysis_env/bin/python   # 或用任意装有 h5py/numpy/scipy 的 Python
$PY sar20_probe.py info
$PY sar20_probe.py decode --all
$PY sar20_probe.py decode --id 5
$PY sar20_probe.py diff <run_a> <run_b>
$PY sar20_probe.py html

# Windows MATLAB（事件级调试唯一通道）
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open'); SAR20('apply'); SAR20('check');
r = SAR20('run');
s = SAR20('sample', 5, r.run_path);
```

## 附录 B：关键身份

| 项 | 值 |
|---|---|
| 生产 SLX | `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` |
| 当前 config SHA | `aa9f8f6d97108fbfae66701e8d09db123940a1b5f1b75fc9187c9b0203aba3c3` |
| 权威 run | `behavior_12d08121-d679-40cd-9ee2-bc334ff42955` |
| 119 项 manifest | `7b8fdf307e933a212f2f5eeee35a1f41df9b8a00d495e3cdaa4928c2b97c687f` |
| 封存候选 ZIP | `analysis/debug_ui_20261105/paused_work/candidate_sources_paused.zip`，SHA `3504a9a93a4f04c2a009be691641dc82836677697d4daf25e9c16e0d02cfe5bf` |
| 调试分类快照模型 | `9626ccf94faa8ad91092ff9ecd05d283fedff08f4abb4ff0049c8585ad4bbb89`（未晋升） |
