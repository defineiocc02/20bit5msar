# SAR20-5 项目计划（当前唯一路线）

> 版本：2026-11-05　｜　状态：**提案，未执行**　｜　对象：`sar20_5_simulink_20261020`
>
> 本文件取代散落在 `CHECKPOINT.md`、`docs/MODEL_PLAN.md`、`docs/ENGINEERING_ANALYSIS.md §8` 中的路线表述，是**当前唯一有效的计划口径**。
> 本文只定义「接下来做什么、按什么判据算完成」；**不构成对任何模型/源码改动的授权**。
> 配套阅读：[README.md](../README.md)（工程说明书）· [ENGINEERING_ANALYSIS.md](ENGINEERING_ANALYSIS.md)（诊断证据）· [**ENGINEERING_GUIDANCE.md**](ENGINEERING_GUIDANCE.md)（2026-11-06 基于真实 SLX 结构的优先级判断、8 项效应重分类与改动落点）· [CITATION.cff](../CITATION.cff)（引用边界）。
>
> ⚠️ **2026-11-06 口径修正**：`ENGINEERING_GUIDANCE.md §3.4` 把此前笼统的「8 项未实现效应」按源码实况重分为 A/B/C/D 四类——其中 B 类有 flag 与守卫但内核禁止开启（不需新建 SLX 块），D 类生产源码零命中（需从零设计）。本文 N 系列的实施顺序以该分类为准；「均需改 SLX」的旧表述作废。

---

## 0. 计划的边界与阅读方式

| 项 | 说明 |
|---|---|
| **已经完成的** | normal N256 基线发布（L3）、零 MATLAB 探针（L0）、全面分析、仓库入口与完整归档推送、**Rev0.3 设计约束闭环（M0.5，`design/budget/`，79 项校验全绿）** |
| **本计划不做的** | 不新增特性、不改 `current/`、不改 SLX、不改仿真结果、不生成新的「已达标」结论 |
| **必须显式授权的** | 任何 `current/src/`、`config/`、`*.slx` 的改动；任何 Windows 侧仿真调度；任何架构级改动（M3/M4/N 系列） |
| **不需要授权但要遵守纪律的** | 只读取证、离线探针、文档与 `CURRENT.json`（M0）——改前备份、改后校验链接与 SHA |
| **形态** | 仓库原生 Markdown，由 GitHub 直接渲染；本机无 `xelatex`/`pdflatex`/`latexmk`，本轮不产出 LaTeX→PDF，也不假称可复现 PDF |

**一句话目标**：把「一次不可归因的联合运行」变成「可逐项归因、可与论文同口径比较的证据」，然后再谈晋升与扩展。

---

## 1. 为什么需要这份计划：根因链

```
目标频繁切换
  → 每次切换留下「未晋升候选」
    → 为保护候选建立 SHA / 回执 / 封存 / 回滚体系
      → 证据链膨胀 + 状态源分裂（5 套口径、5 个状态源）
        → 恢复成本升高、口径需反复用自然语言澄清
          → 下次更倾向「再开一个隔离候选」而非「晋升到生产」
            → 生产零净变化（11-05 逐 SHA 比对 116 个文件 0 差异）
同时：
基线不可归因 → 改动收益无法判定 → 不敢验收 → 只能封存 → 强化上一环
```

三个已发生过的**口径设计返工**（详见 `ENGINEERING_ANALYSIS.md §3`），本计划用前置门避免重演：

1. SLX 哈希 = f(模型结构 + 内嵌 P)，不是「模型结构指纹」；
2. N8 约 3 s 但 `not_run_short_capture`，N256 才是频谱 run（64.6–140 s，中位 74.4 s）；
3. 按 6 个顶层字段分组会得出「SNDR 跨度 52.9 dB」的假象，必须按整份 `parameters.json` SHA-256 分组。

---

## 2. 先裁决口径，再谈完成

工程并行存在 5 套口径（产品规格 Rev0.3 / Rev0.1-0.2 历史 / 行为验收合同 / 调度草案 / 论文 normal 工作点）。计划的第一步不是选一套，而是**机器可读地写明当前生效的是哪一套、什么算完成**：

| 口径 | 在本计划中的角色 |
|---|---|
| E 论文 normal（FSR 10 V、N256、联合非理想 ON） | **M1/M2 的固定实验口径**，所有 ΔdB 只在它内部比较 |
| A 产品规格 Rev0.3（FSR 8.192 V、SNR≥100 / SINAD≥98 / THD≤−105 dBc、LVDS 32-bit/N−2） | **M2 之后才能讨论是否达标**；当前 FSR/接口/校准均不同，禁止用 99.133 dB 判达标 |
| C 行为验收合同（里程碑 A/B、11 项检查、`budget_missing`） | 提供「缺预算不得报达标」的硬规则，是 M1 噪声预算的验收依据 |
| B / D 与 `docs/DEFINITIONS/ProductRev0.5/` | 历史输入快照，仅作追溯，不参与当前完成判定 |

**裁决规则（写进 `CURRENT.json`）**：同一张表里只列「当前生效口径」；跨口径的数字禁止放在同一列比较；任何 ΔdB 必须附 `config_sha256` 或整份 `parameters.json` 的 SHA-256。

---

## 3. 证据层级与晋升门（全计划统一）

| 层级 | 含义 | 允许得出的结论 | 本计划对应 |
|---|---|---|---|
| L0 | 静态审计 / 离线复算 | 身份一致、解码链未坏 | 探针、`CURRENT.json` 校验 |
| L1 | 隔离函数门 | 单个数学核正确 | 已有 5 门；M1 预算复核 |
| L2 | N8 smoke | 事件与码正确，无频谱 | M3 回归第一道门 |
| L3 | 整图 N256 | 一次真实行为谱 | M1/M2 主战场（多 run） |
| L4 | 归档形式验证 | 冻结系数/holdout 在归档条件成立 | M2 校准复核（不得升级） |
| L5 | 代理物理证据 | 趋势性观察 | M1 消融（**仍是代理**） |
| L6 | PEX / 硅 / 功耗面积 | 物理实现指标 | **本计划不产生** |
| L7 | signoff | PVT/DNL/INL/多频多种子 | **本计划不产生** |

> **硬规则**：① 下层证据不得升级为上层结论；② 代理证据不得写成 signoff；③ 「能声称 / 不能声称」必须成对出现在每个里程碑的 checkpoint 里；④ 未经实测的门一律写 `not_run`，不允许用审计项冒充验收结果。

---

## 4. 里程碑总览

| 里程碑 | 目标 | 主要产物 | 改模型/SLX | 授权 | 前置 | 完成判据（一句话） |
|---|---|---|---|---|---|---|
| **M0** | 单一真相源 | `CURRENT.json`、旧状态源 archive 标注、链接/SHA 校验脚本 | 否 | 文档级，无需 | 无 | 新会话 1 分钟内确定「当前是什么、什么算完成」 |
| **M0.5** ✅ **已落地 2026-11-05** | **让工程能指导电路设计** | [`design/budget/`](../design/budget/ERROR_BUDGET_REV03.md) 四件套：Rev0.3 误差预算、12 个模块规格、参数绑定 CSV、校验脚本 | 否 | 无需（口径已由用户定为 Rev0.3） | 无 | `verify_budget.py` 79 项全绿；每模块有可执行数值上限与验证门；状态诚实标 `NOT_CLOSED` |
| **M1** | 让基线可归因 | 单源消融矩阵、逐项 ΔSNDR 表、输入参考噪声预算 | **否**（参数注入） | 需 Windows 仿真调度授权 | M0 | 每个已实现非理想项有独立 ΔSNDR，预算表可与论文分项比较 |
| **M2** | 同口径论文对照 | 20k 点谱、M1/M8 的 7 dB 对照、校准/holdout 复核结论 | **否**（参数级） | 需授权 | M1 通过 | 能明确回答「复现到什么程度、差在哪几项、各差多少 dB」 |
| **M3** | 候选晋升 | 生产 SLX SHA 改变、完整回归、文档同步 | **是** | **显式授权 + 范围/备份/回滚方案** | M2 通过 | `apply → 冷开 → N8 位门 → N256 回归 → README/CURRENT 同步` 全过 |
| **M4** | 架构扩展 | ADI v2 18-pool / 双 QDAC、10 MS/s | **是，架构级** | 用户另行同意 | M3 + 新里程碑定义 | 按新里程碑单独定义 |
| **N 系列** | 补齐未实现非理想 | 8 项缺口的实现与验证 | **是，需改 SLX** | 显式授权，逐项里程碑 | M2 之后评估 | 每项独立验收门（见 §9） |

**优先级：M0 → M1 → M2；M3 之前不要开新特性线。** M1/M2 产出的是「能不能判定收益」这一晋升决策的前提；缺了它，M3 无论选哪个候选都只能再次封存。

### 4.1 依赖关系

```
M0.5 ✅ ──> M1 ──> M2 ──> M3 ──> M4
   │                        ▲
   └──> M0 ─────────────────┘（单一真相源可与 M1 并行，不阻塞预算）
                │
                └──> N 系列（需改 SLX，另行授权，不得抢先晋升）
```

**M0.5 与 M0 互不依赖**：M0.5 已按用户裁定以 Rev0.3 为口径独立完成，改的是设计输入与约束，不碰状态源；M0 的 `CURRENT.json` 应在 `acceptance_basis` 中引用 M0.5 的预算表，而不是另写一套指标。

---

## 5. M0 · 机器可读单一真相源

### 5.1 目标

消除 5 个互相竞争的状态源，让任何新会话/新 agent 在 1 分钟内确定当前状态，而不是读 219 KB 倒序日志后靠自然语言猜。

### 5.2 `CURRENT.json` 字段设计（草案）

```json
{
  "schema": "sar20-current/v1",
  "updated_utc": "<ISO-8601，由脚本写入，不手写>",
  "active_goal": {
    "id": "normal_baseline_released",
    "statement": "91973cf7 模型上的 5 MS/s 单物理前端正常 N256 基线已发布；扩展目标暂停",
    "paused": true,
    "paused_by_user_utc": "2026-11-05",
    "resume_index": "analysis/debug_ui_20261105/paused_work/PAUSE_INDEX.json"
  },
  "acceptance_basis": {
    "active": "E_paper_normal_workpoint",
    "fsr_diff_v": 10,
    "N": 256,
    "spec_rev03_is_not_active": true,
    "budget_missing": true,
    "paper_reproduction_status": "NOT_REPRODUCED"
  },
  "production": {
    "entry": "SAR20.m",
    "model": "current/models/SarAdc.slx",
    "model_sha256": "91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e",
    "source_manifest_sha256": "7b8fdf307e933a212f2f5eeee35a1f41df9b8a00d495e3cdaa4928c2b97c687f",
    "config_sha256": "aa9f8f6d97108fbfae66701e8d09db123940a1b5f1b75fc9187c9b0203aba3c3",
    "applied_state": "state/applied_config.json",
    "frozen_source_files": ["sar20_bank_owner_step", "sar20_bank_owner_init",
                            "sar20_bank_sha256", "sar20_bank_certificate_sha256"]
  },
  "authoritative_run": {
    "id": "behavior_12d08121-d679-40cd-9ee2-bc334ff42955",
    "mirror": "analysis/behavior/public_normal_20261105/release_actual/behavior_12d08121-d679-40cd-9ee2-bc334ff42955",
    "receipt": "analysis/behavior/public_normal_20261105/release_actual/release_receipt.json",
    "metrics": {"snr_db": 99.712414227270258, "sndr_db": 99.132765903966785,
                "sfdr_db": 111.78407088195453, "thd_db": -108.16556427335165,
                "enob": 16.174878057137342},
    "evidence_level": "L3",
    "attribution": "joint_all_enabled_nonidealities_single_run_NOT_attributable"
  },
  "archived_state_sources": ["release.json", "state/SESSION_READY.json",
                             "state/behavior_release_receipt.json", "state/dynamic_receipt.json",
                             "state/logging_receipt.json", "state/behavior_cleanup.json",
                             "state/short_default_restored.json", "CHECKPOINT.md"],
  "candidates": {
    "paused_archive": "analysis/debug_ui_20261105/paused_work/candidate_sources_paused.zip",
    "paused_archive_sha256": "3504a9a93a4f04c2a009be691641dc82836677697d4daf25e9c16e0d02cfe5bf",
    "classification_only_model": "9626ccf94faa8ad91092ff9ecd05d283fedff08f4abb4ff0049c8585ad4bbb89",
    "caaz_private_model": "63283fd769acdb4bdd4937df60e15b54196db01d219e830f7a010e8b60078964",
    "promoted_to_production": []
  },
  "capability_boundary": {
    "can_claim": ["架构文字对齐", "单点 N256 行为谱自洽", "同配置逐位可复现", "256/256 名义解码复算一致"],
    "cannot_claim": ["论文性能复现", "7 dB tracking 收益", "DNL/INL", "20k 点谱",
                     "功耗/面积/PDK", "多频多种子稳定性", "任何 signoff"]
  }
}
```

> ⚠️ 字段值必须**由脚本从 `state/applied_config.json`、`release_receipt.json`、`summary.json` 读取生成**，禁止手工抄 SHA（已发生过误抄 62 位导致 preflight 失败的事故）。`frozen_source_files` 与 `CHECKPOINT.md:305` 所称「9 个文件」的口径差异，标 `待确认` 后再定。

### 5.3 动作清单

| # | 动作 | 文件 | 校验 |
|---|---|---|---|
| 1 | 备份旧状态文件到 `_preserved/before_m0_<date>/` | `release.json`、`state/*.json` | 逐 SHA 读回 |
| 2 | 生成 `CURRENT.json`（脚本生成，非手抄） | 新建根目录 `CURRENT.json` | JSON schema 校验 |
| 3 | 给旧状态源加 machine-readable archive 标记（保留原值，不删历史） | 同上 | 不破坏既有 reader |
| 4 | 冻结 `CHECKPOINT.md` 为历史：顶部加「只读归档」横幅；修正废弃 `项目库/outputs/` 路径 | `CHECKPOINT.md` | 保留 665 行原文 |
| 5 | 修正 `release.json.canonical_mac_root` 指向产物外置后的有效路径 | `release.json` | 路径存在性 |
| 6 | README / README_EN 增加 `CURRENT.json` 入口；`ENGINEERING_ANALYSIS.md §8` 指向本计划 | 文档 | 链接 0 断链 |
| 7 | 新增 `tools/verify_current.py`：核对 SLX/源码/manifest SHA 与 CURRENT.json 一致 | 新建 | 全绿才算过 |

### 5.4 验收门（M0 DoD）

- [ ] `CURRENT.json` 存在且由脚本可重新生成，重复生成结果除 `updated_utc` 外一致；
- [ ] `tools/verify_current.py` 对生产 SLX、108 个 `.m`、`config/` 逐 SHA 全绿；
- [ ] 任一新会话仅读 `CURRENT.json` + `README.md §0` 即可回答：当前模型、当前 run、当前口径、是否暂停、什么算完成、哪些文件不可改；
- [ ] 所有入口文档相对链接 0 断链（按文档所在目录解析，含 `../`）；
- [ ] `current/`、`config/`、SLX、仿真结果**零改动**（`git diff --stat` 为空）。

### 5.5 回滚

`CURRENT.json` 是新增文件，直接删除即回到现状；旧状态源只在归档标记层改动，从 `_preserved/before_m0_<date>/` 用 `cp -p` 还原；`CHECKPOINT.md` 横幅单独一行删除即可。**不涉及任何二进制模型。**

---

## 6. M1 · 单源消融 + 输入参考噪声预算

### 6.1 要解决的科学问题

`NORMAL_NONIDEALITY_COVERAGE.md:27` 明确：当前 N256 是所有已开启项的联合单点，无法分离 kT/C、C 失配、有限建立、AZ、RA 或比较器噪声各自的贡献。没有单源 ΔdB，任何 CAAZ / ADI / 校准改动都无法验收，也无法与论文的误差分项比较。

> **M1 的验收标尺来自 M0.5**：[`design/budget/error_budget_rev03.json`](../design/budget/error_budget_rev03.json) 已给出 7 个预算项的输入参考 rms 上限与 12 个模块的数值规格。M1 每个 leave-one-out case 都要报出该模块的输入参考 ΔµV，与该表 `rms_limit_uv` 对照；F 组（M1/M8）给出真实 tracking 增益，用于替换预算表中 2.24 / 2.83 的示意倍数。预算表状态 `NOT_CLOSED` 只能由 M1/M2 的实测解除。

### 6.2 固定实验口径（不得跨 case 变更）

| 项 | 值 |
|---|---|
| Fs / Ts | 5 MHz / 200 ns |
| Fin / bin | 97.65625 kHz / 相干 bin5 |
| 幅度 / 相位 | −1 dBFS（4.456254690668728 V）/ 0.731 rad |
| FSR / vref | 10 V / 5 V |
| N / first_id / epoch / seed | 256 / 4 / 1 / 20261020 |
| FFT 口径 | 矩形相干窗、DC 排除、H2–H10 折回（与现有 `DYNAMIC_ACTUAL_256.json` 一致） |
| 模型 | `91973cf7…` **保持不变**；只通过 SimulationInput 参数注入改配置 |
| 随机性 | 每个 case 固定全部种子（`ktc/chip/ra/cmp/jitter/dither/dem`），禁止只改部分 |

> **关键陷阱**：`P.ni` 是**派生摘要，不是开关**（`docs/PARAMETERS.md:26,83`），改 `P.ni.xxx` 不会关闭任何物理效应。必须改物理配置字段（`ktc_enabled`、`mismatch_enabled`、`tau_*`、`backend.ra.A0/UGB`、`backend.az.mode`、`control.comparator.*`、`backend.ra_noise.*` 等），或改 `config/normal_parameters.m` 的 6 个 `use*` 开关后重新 `apply`。**M1 优先用参数注入，避免改任何工程文件。**

### 6.3 消融矩阵设计

以 `normal_all_on`（当前基线）为参照，做两组互补消融：

| 组 | case 数 | 定义 | 回答什么 |
|---|---|---|---|
| **A：全基线** | 1 | 当前 normal P，逐位复现 99.132766 dB | 实验可重复性门 |
| **B：理想基线** | 1 | 所有已实现非理想关闭（对应 109.164977 dB） | 联合退化总量上界 |
| **C：留一关闭（leave-one-out）** | 10 | 每次只关 1 项，其余保持 normal | 该项的边际贡献 `ΔSNDR_i = SNDR_C_i − SNDR_A` |
| **D：只开一项（only-one-on）** | 10 | 从理想基线出发只开 1 项 | 该项的独立贡献 `ΔSNDR_i' = SNDR_B − SNDR_D_i`，检验 C/D 是否自洽（交互项） |
| **E：重复/确定性** | ≥2 | 同一 case 重复 2 次 + 已有 9 组同配置哈希分组 | 排除随机漂移与「比错对象」 |
| **F：tracking 对照** | 2 | M1（1 次比较/0 反馈等效）vs M8（8 比较/7 反馈），其余全同 | 首次给出 tracking averaging 的**同口径实测 ΔdB** |

C/D 的 10 项：① 采样 kT/C ② 一级 C 失配 ③ 采样 RC 建立 ④ DAC 有限建立 ⑤ 寄生 ⑥ RA 有限增益 ⑦ RA 有限带宽 ⑧ ordinary AZ ⑨ RA OU 噪声 ⑩ SAR2/TA 比较器噪声。

> C 与 D 不一致处（交互项）必须如实列出，**不得用其中一组冒充「单源贡献」**。RA 有限增益与有限带宽共用 A0/UGB，需单独设计「保持其它不变」的注入方式；若无法解耦，标 `not_separable` 而不是估算。

### 6.4 输入参考噪声预算

以 `docs/MODEL_PLAN.md:77` 与 `docs/spec.yml` `noise_budget` 的初始功率分配 A 为对话起点（采样 50%、RA 放大后滤波 15%、AZ 8%、比较器滤波后 7%、参考/驱动 10%、量化/数字 5%、余量 5%），但：

- `spec.yml` 自述 `evidence: ASSUMED_INPUT_REFERRED_RANDOM_ERROR_POWER`、`physical_ktc_closed: false` —— **这是假设，不是已闭合预算**；
- 用 M1 实测的逐项 ΔSNDR 折算等效输入参考噪声电压 rms，与 `SPEC.md:75` 的 SNR 100 dB → 25.81 µV rms、SINAD 98 dB → 32.50 µV rms 对齐；
- 输出表模板：

| 非理想项 | ΔSNDR_C (dB) | ΔSNDR_D (dB) | 等效输入噪声 rms (µV) | 假设功率占比 (%) | 实测功率占比 (%) | 来源/假设标签 |
|---|---|---|---|---|---|---|
| … | … | … | … | … | … | … |

- **未覆盖项**（参考/驱动噪声、SAR1-fine/Flash 噪声、AZ 写入噪声、其他 RA 级）在表中必须显式列 `not_implemented`，不得用余量掩盖。

### 6.5 执行前置与调度

| 前置 | 说明 |
|---|---|
| 授权 | Windows 侧仿真调度需显式授权；一次 N256 约 64.6–140 s（中位 74.4 s），全矩阵约 24–26 个 N256 → **先算总机时并向用户确认** |
| 通道 | 计划任务 `SAR20_MatlabControl` COM 通道；`matlab -batch` 会因许可证占用立即退出 |
| 落盘 | 每个 case 独立 `runs/behavior_<UUID>/`，保留 `parameters.json`（用于整份 SHA 分组）、`selected.mat`、`spectrum.mat`、`summary.json` |
| checkpoint | 每完成一组（A/B/C/D/E/F）写一个 `analysis/behavior/ablation_<date>/CHECKPOINT.md`，含已完成 case、SHA、指标、失败与回滚记录；断流从最后一个 checkpoint 续做 |
| 清理 | 临时脚本一律放 `analysis/behavior/ablation_<date>/tools/` 并随产物入库；不在 `/tmp`、远程临时目录堆积 |

### 6.6 验收门（M1 DoD）

- [ ] 全基线 case 复现 99.132766 dB（容差按同配置确定性检验定，先证明比的是同一个东西）；
- [ ] 10 项已实现非理想各有 C/D 两组 ΔSNDR，不可解耦项标 `not_separable`；
- [ ] 输入参考噪声预算表产出，未实现项显式列出，且 `budget_missing` 状态可在 `CURRENT.json` 中更新；
- [ ] F 组给出 M1/M8 同口径实测 ΔdB（**首次**），并与理论 9.03 dB / 论文约 7 dB 分开陈述，不混用；
- [ ] 所有 case 的 `parameters.json` 整份 SHA 已记录；跨 case 比较只在同一 SHA 组内进行；
- [ ] `current/`、SLX、生产配置零改动；`git diff --stat` 仅含新增证据与文档。

### 6.7 回滚

参数注入不改工程文件 → 停止调度即回滚；若曾为改 `config/` 做备份，从 `_preserved/before_m1_<date>/` 还原并重新 `apply` 到 `91973cf7…` 对应 P；用 `tools/verify_current.py` 确认生产 SHA 未变。失败产物移入 `analysis/behavior/ablation_<date>/rejected/`，**不删除**（保留失败证据，但明确标注不可引用）。

---

## 7. M2 · 同口径论文对照

### 7.1 目标

把「99.133 dB 与论文 100 dB 数字接近」这句不能成立的话，换成一份能逐项回答「差在哪、差多少」的对照结论。

### 7.2 动作

| # | 动作 | 口径要求 | 判据 |
|---|---|---|---|
| 1 | 20k 点谱 | 与 M1 完全相同的 Fs/Fin/FSR/幅度/相位/seed/FFT 口径，只改记录长度 | 需先**评估机时**；N256 约 74–140 s，20k 点不得假设线性外推，先跑 1 次测成本再决定 |
| 2 | 窗与谐波口径复核 | DC 排除、H2–H10 折回；补记加窗结果作为对照，不与相干矩形窗混用 | 两种口径分表列，标注各自适用范围 |
| 3 | M1/M8 的 7 dB 收益对照 | 用 M1 的 F 组结果，在 20k 点口径下复核一次 | 明确「行为级实测 ΔdB」≠「论文硅测 7 dB」；噪声条件须写明 |
| 4 | 前景校准 / 独立 holdout 复核 | 现有 `accepted=false` 的 calibration 链与预登记 holdout 117.458 dB | 保持 `accepted=false`，除非重新走完资格链；不得把 L4 归档结果升级为 L3/L6 结论 |
| 5 | 论文对照报告 | 逐项列出「论文条件 / 工程条件 / 是否可比 / 差距 / 证据层级」 | 未绑定图表或测量条件的 `99.4 dB` 标 `待确认`，不得写入结论 |
| 6 | 复现判定更新 | 依据对照报告更新 `CURRENT.json.paper_reproduction_status` 与 `README.md §3.2` | 只允许写实测能支撑的措辞 |

### 7.3 验收门（M2 DoD）

- [ ] 20k 点谱（或经用户同意的替代点数）产出，且口径与 M1 逐字段一致；
- [ ] 对照报告能逐项回答：架构对齐到什么程度、哪些指标可比、哪些不可比、每个可比项差多少 dB；
- [ ] 「能声称 / 不能声称」清单按新证据更新，但没有一条把 L3/L4/L5 升级为 L6/L7；
- [ ] `budget_missing` 是否解除有明确结论（解除需附误差预算表与验收目标，未解除则维持 `true`）。

### 7.4 回滚

同 M1（参数级）。对照报告若证据不足，回退为 `status: evidence_insufficient` 草稿并保留，不删除、不宣称完成。

---

## 8. M3 · 候选晋升（首次允许改模型）

### 8.1 前置决策：晋升哪一个

| 候选 | 现有证据 | 主要风险 | 建议 |
|---|---|---|---|
| **输入侧 CAAZ** | 私有图 `63283fd…` 两组 N8 PASS（16.21 / 19.17 s，8 有效码，575 组 RA next→old 逐位一致，偶写奇持）；无 SNDR | 整图 AZ 写入随机噪声关闭；输入侧 chopper 耐压/Ron/电荷注入/路径不对称未建立；极性恢复易错（只翻 D2/DT 会错） | **优先**：有真实整图证据，改动边界相对清晰 |
| **debug UI / 分类导航** | 模型 `9626ccf…` 仅分类导航初稿 + 截图；无仿真；graph1 在 SDK 拒绝 `ContentPreviewEnabled` 处停止 | 13 个任务注销、210 文件封存、草稿未完成；恢复链散在 4 处；无性能收益 | 暂缓：属工具能力，不解决科学归因问题 |
| **ADI 物理 v2** | 仍为候选；双 QDAC / 共享尾 / 动态 Ctop / 数字协议均未建图 | 架构级，M4 范围 | 不在 M3 讨论 |

### 8.2 改动前必须提交的清单（未提交不得动手）

1. **改动范围**：逐文件列出要改的 `.m` / `.slx` / `config/`，并核对 4 个 SHA-256 冻结的审计锚点文件（`sar20_bank_owner_step/init`、`sar20_bank_sha256`、`sar20_bank_certificate_sha256`）**不在范围内**；
2. **备份**：`_preserved/before_m3_<date>/` 保存 `current/`、`config/`、`state/applied_config.json`、SLX，逐 SHA 读回通过；
3. **回滚方案**：明确「字节级还原」与「重新 apply 到 `91973cf7…`」两条路径，以及 `SLX 哈希 = f(结构 + 内嵌 P)` 带来的注意点；
4. **回归通道**：`apply → check → 冷开 → N8 位门（12 D2 / 8 TA / 7 反馈、32 logger + 3 roots 逐位、global RNG 不变）→ N256 回归（与 99.132766 dB 比较）→ sample 事件级抽查`；
5. **checkpoint 与中断续做**：每个门一个 checkpoint，断流从最后 checkpoint 继续，不重跑已通过的整段。

### 8.3 验收门（M3 DoD）

- [ ] 生产 SLX SHA 实际改变，且 `CURRENT.json`、`README.md`、`README_EN.md`、`state/applied_config.json` 同步；
- [ ] N8 位门全过（逐位一致、RNG 不变），N256 回归有明确 ΔdB 且能用 M1 的单源表解释；
- [ ] 若 ΔdB 无法解释 → **判定不晋升**，回滚到 `91973cf7…`，把候选重新封存并写明原因；
- [ ] 改动范围与备份清单、回滚记录全部入库；临时脚本与临时目录清理干净。

---

## 9. M4 与 N 系列（需另行定义与授权）

### 9.1 M4：ADI v2 / 10 MS/s

当前只是候选：18 片各 `[2,31×4,2,1]Cu=129Cu` + 两组尾阵列、活动组 `8×129+7=1039Cu`、双 QDAC 各保留完整 1039Cu、FE owner 558 字、约 119.178 pF/half 制备电容（**每半边口径是本模型假设，不是作者披露，也不是两端口差模等效电容**）。`docs/CAAZ_ADI.md:54` 明确「两路 QDAC、共享尾、动态 Ctop/OU 和数字协议目前均为候选，不能称整图已完成」。

- 顺序：先 5 MS/s 验证，再评估 10 MS/s；10 MS/s 需用户另行同意；
- 不迁移 40 nm 原型的开关速度、40 MS/s、功耗、面积与线性度到 180 nm；
- 若使用非重叠双样本平均，输出为 2.5 MS/s、Nyquist 1.25 MHz，**不得称作 5 MS/s 全带宽固定降噪**。

### 9.2 N 系列：未实现非理想（均需改 SLX，逐项里程碑）

| 项 | 当前状态 | 出处 |
|---|---|---|
| `reference_recovery` | 显式 `not implemented` | `model/behavior_ra_noise_guard.m:90` |
| `reference_noise` / `nonlinear_ra` / `replica_delay` / `az_noise` | 显式 `not implemented` | `physics/behavior_backend_step.m:434-437` |
| SAR1-fine / Flash 比较器噪声 | 未实现 | `model/behavior_applied_note.m:46`、`behavior_ra_noise_guard.m:119` |
| `timing_mismatch` / `dac_sampling_bw` / `online_shuffler` | 源码无实现证据（仅 SPEC/MODEL_PLAN 设想） | 待确认 |
| 有限 RC + 位移孔径 jitter 组合、运行时 EN 切换、同 run Bank ARM | 显式未实现 | `frontend/behavior_frontend_step.m:64-66` 等 |

**规则**：N 系列每一项都要单独定义「物理模型 → 参数来源 → 函数门 → 整图门 → 单源 ΔdB → 是否影响论文可比性」，且不得与 M3 的晋升混在同一批改动里。没有参数来源的项一律标 `证据不足`，不用假设值凑数。

---

## 10. 横切纪律（所有里程碑适用）

### 10.1 Checkpoint 与断流续做

- 每个里程碑一个目录 `analysis/behavior/<milestone>_<date>/CHECKPOINT.md`，倒序追加，**最新在头部**；
- 每个 checkpoint 至少含：已完成动作、产出文件 + SHA、实测数值、失败项、`能声称/不能声称`、下一步、回滚点；
- 断流后**从最后一个 checkpoint 续做**，不重跑已通过的整段，不重建已封存的候选；
- `CHECKPOINT.md`（根）在 M0 之后冻结为历史，不再追加。

### 10.2 备份 / 回滚 / 清理

| 场景 | 要求 |
|---|---|
| 改文档 / 新增证据 | 改前 `cp -p` 备份到 `_preserved/`；改后校验链接与 SHA |
| 改 `current/` / SLX | 必须先提交 §8.2 的 5 项清单并获显式授权；备份逐 SHA 读回 |
| 失败尝试 | 完整回退到交接状态并清理，产物移入 `rejected/` 保留但标注不可引用 |
| 临时文件 | 不在生产目录、`/tmp`、远程临时目录堆积；正式产物一律进仓库 |
| 结束状态 | 生产模型恢复到约定基线（或明确记录已晋升的新 SHA），`git status` 干净 |

### 10.3 证据与措辞

- 区分：静态审计 / smoke / 综合 / 归档形式验证 / 代理物理证据 / PEX / signoff；
- 不确定处写「待确认」或「证据不足」，不臆造参数、引用与图表条件；
- 结论成对给出「能声称」与「不能声称」；
- 代理证据、归档结果不得升级为 signoff；
- 任何 ΔdB 必须附 `config_sha256` / `parameters.json` SHA 与口径说明。

### 10.4 运行环境纪律

- MATLAB 仅经 `SAR20_MatlabControl` COM 通道调度；`license('test')=1` 不代表 `checkout` 可用；
- 公开入口 `SAR20('apply'|'check'|'run'|'sample')`，`calibration` 当前显式抛错；
- GUI 直接 Run 不读工厂文件、不建完整归档，不能作为回归证据；
- N8 只验事件与码，N256 才有频谱；
- Mac 侧 `analysis/local_debug/sar20_probe.py` 是 L0 只读门；`analysis/mat_reader.py::read_logger_plan` 对当前 32-logger `simout.mat` 已失效，**禁用**（原工具未修）。

---

## 11. 风险登记册

| # | 风险 | 触发条件 | 缓解 | 责任里程碑 |
|---|---|---|---|---|
| R1 | 消融矩阵机时超预期 | N256 × 24–26 次 | 先跑 1 case 实测 wall time，向用户确认总机时再铺开 | M1 |
| R2 | 「关掉一项」实际改的是派生摘要 `P.ni` | 误以为改 `P.ni` 能开关 | §6.2 硬规则 + case 前置校验 `parameters.json` 差异字段 | M1 |
| R3 | 跨 case 比错对象 | 只按 6 个顶层字段分组 | 整份 `parameters.json` SHA-256 分组，重复 case 确定性门 | M1/M2 |
| R4 | ΔdB 被误读为论文 7 dB 收益 | 把行为级对照写成硅测结论 | 对照报告强制分栏「行为级实测 / 论文硅测 / 理论上限」 | M2 |
| R5 | 20k 点谱成本不可控 | 线性外推 N256 机时 | 先测单点成本，必要时与用户约定替代点数 | M2 |
| R6 | 候选晋升后基线被污染 | 未备份 / 未走位门 | §8.2 五项清单 + 双回滚路径 + 无法解释即回滚 | M3 |
| R7 | 冻结审计锚点被改 | 重构范围未核对 | 4 个硬编码 SHA 文件列入排除清单（与 `CHECKPOINT.md:305` 的 9 文件口径差异待确认） | M3/M4 |
| R8 | 状态源再次分裂 | 新里程碑又写新「最新」 | 所有状态写入 `CURRENT.json`；根 CHECKPOINT 冻结 | 全程 |
| R9 | 第三方 PDF / SATK 合规 | 公开仓库再分发 | `NOTICE.md` + 文献索引 + 按 issue 移除流程 | 全程 |

---

## 12. 待确认清单（不臆造，逐项销项）

1. 论文 `99.4 dB` 与 `7 dB` 的确切图表 / 测量条件 —— 工程内只有引用，未见定义。
2. `CHECKPOINT.md:305` 称哈希锁定边界涉及 9 个文件，`:333` 称 4 个硬编码冻结 —— 口径未消解。
3. `release_receipt.json` 的 Windows controller 生成脚本未定位；与 `ACTIVE_WORKING_MANIFEST.json` 记录的 receipt SHA 一致性待核。
4. `timing_mismatch` / `dac_sampling_bw` / `online_shuffler` 在 `current/src/` 无实现证据，是否曾在其他分支存在待确认。
5. 两份 CICC2026 PDF 正文（除标题外）的 20k 点、实测 SNDR 等目标数字未逐页核对。
6. README 展示精度（如 99.133 dB）与 `release_receipt.json` 全精度的舍入规则未显式声明。
7. `state/SESSION_READY.json` 内两个 `figures` 块给出不同 `model_sha256`，文件内未见解释。
8. `docs/DEFINITIONS/ProductRev0.5/contract/ALIGNMENT.md` 提到的 `requirements_rev05.json` 与 `software_reconstruction` 未在该目录找到。
9. 本机无 TeX 环境；若需正式 PDF 版计划，需指定 TeX Live + ctex 环境或另行生成方式。

---

## 13. 完成定义总表（DoD）

| 里程碑 | 一句话 DoD | 证据层级 | 允许改变生产 SHA |
|---|---|---|---|
| M0 | 新会话 1 分钟内确定当前状态与完成判据 | L0 | 否 |
| **M0.5** ✅ | Rev0.3 指标已拆成模块数值上限；解析链可复算；未验证门已逐项列出 | L0/L1 解析 | 否 |
| M1 | 每个已实现非理想项有独立 ΔSNDR + 可比较的输入参考噪声预算 | L3（多 run）+ L5 代理 | 否 |
| M2 | 能明确回答论文复现到什么程度、差在哪几项、各差多少 dB | L3/L4 | 否 |
| M3 | 一个候选走完位门与 N256 回归并同步全部文档 | L2 + L3 | **是**（需授权） |
| M4 | 按新里程碑单独定义 | 待定 | 是 |
| N 系列 | 每项独立函数门 + 整图门 + 单源 ΔdB | 待定 | 是（逐项授权） |

**当前实际位置**：**M0.5 已落地**（Rev0.3 设计约束闭环，79 项校验全绿，closure = `NOT_CLOSED`）；M0、M1–M4 仍为提案；生产模型 `91973cf7…` 保持不变；扩展目标处于用户明确暂停状态。

---

## 附录 A · 关键命令

```bash
# 本地 L0 只读门（Mac，零 MATLAB）
cd analysis/local_debug
PY=../../dependencies/analysis_env/bin/python
$PY sar20_probe.py info
$PY sar20_probe.py decode --all
$PY sar20_probe.py decode --id 5
$PY sar20_probe.py diff <run_a> <run_b>
$PY sar20_probe.py html

# 仓库一致性（M0 之后）
python3 tools/verify_current.py

# Windows MATLAB：公开入口（事件级 sample 不加载 SLX）
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open'); SAR20('apply'); SAR20('check');
r = SAR20('run');
s = SAR20('sample', 5, r.run_path);
```

## 附录 B · 关键身份

| 项 | 值 |
|---|---|
| 生产 SLX | `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` |
| 生效配置 SHA | `aa9f8f6d97108fbfae66701e8d09db123940a1b5f1b75fc9187c9b0203aba3c3` |
| 权威 run | `behavior_12d08121-d679-40cd-9ee2-bc334ff42955` |
| 119 项 manifest | `7b8fdf307e933a212f2f5eeee35a1f41df9b8a00d495e3cdaa4928c2b97c687f` |
| 封存候选 ZIP | `analysis/debug_ui_20261105/paused_work/candidate_sources_paused.zip`，SHA `3504a9a93a4f04c2a009be691641dc82836677697d4daf25e9c16e0d02cfe5bf` |
| CAAZ 私有试验图 | `63283fd769acdb4bdd4937df60e15b54196db01d219e830f7a010e8b60078964`（未晋升） |
| 分类导航初稿 | `9626ccf94faa8ad91092ff9ecd05d283fedff08f4abb4ff0049c8585ad4bbb89`（未晋升） |

## 附录 C · 参考文件

[README.md](../README.md) · [ENGINEERING_ANALYSIS.md](ENGINEERING_ANALYSIS.md) · [SPEC.md](SPEC.md) · [spec.yml](spec.yml) · [ALIGNMENT.md](ALIGNMENT.md) · [MODEL_PLAN.md](MODEL_PLAN.md) · [READ_GRAPH.md](READ_GRAPH.md) · [PARAMETERS.md](PARAMETERS.md) · [CAAZ_ADI.md](CAAZ_ADI.md) · [behavioral_acceptance.md](../design/behavioral_acceptance.md) · [NORMAL_NONIDEALITY_COVERAGE.md](../analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md) · [NOTICE.md](../NOTICE.md)
