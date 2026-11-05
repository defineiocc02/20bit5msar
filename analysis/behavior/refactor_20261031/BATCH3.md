# 可读性重构：第三批（指标核心 behavior_spectrum）

日期：2026-10-31。

## 先查清了"哪些文件不能改"

前两批我误以为只有 4 个文件被哈希锁定。本轮系统排查后发现**实际是 9 个**：

| 被锁文件 | 锁定位置 |
|---|---|
| `sar20_bank_owner_step` | `sar20_pp_verify_v3_qualification.m` |
| `sar20_bank_owner_init` | 同上 |
| `sar20_bank_sha256` | 同上 |
| `sar20_bank_certificate_sha256` | 同上 |
| **`behavior_frozen_step`** | **`sar20_pp_parameters.m` (source_check)** |
| **`behavior_frozen_setup`** | 同上 |
| **`behavior_public_cal_features`** | 同上 |
| **`behavior_calendar`** | 同上 |
| **`behavior_sar_step`** | 同上 |

后 5 个是"已资格 M8 算法"的一部分，报错信息明确写着
`Resolved %s source differs from qualified M8 algorithm`。
**改了就会让校准资格校验失败。**

这个边界必须一开始就查清，否则会白改——我上一轮已经因为 `behavior_frozen_step` 踩过一次。

## 本轮改动

**`current/src/analysis/behavior_spectrum.m`**：47 → 70 行，多语句 7 → 0

这是**指标核心**：`SAR20.m` 用它算所有 SNDR/SFDR/THD/ENOB。

改动：
- 7 处单行多语句展开
- 补 header，明确写出每个量的定义（bin / signal / nd / harmonics / noise / SNDR / THD / ENOB）
- 给两处关键计算加注释：代码中心重建、单边功率加倍、**谐波折回**（`mod` + `min(h,N-h)`）

注释里特别说明了谐波为什么要折回：**否则 H2..H10 会被重复计数**。
这条正是我前几轮曾经误判"2 MHz 指标失效"的地方。

## 验证：两层

**第一层：Token 级等价（静态）**
把注释和所有空白去掉，把 `;` 与换行统一成语句分隔符，逐语句比较：

```
old statements=84  new statements=84
identical: True
```

这是最强的静态证明——**源码在语义层面一个 token 都没变**。

**第二层：运行时数值比对（动态）**

用真实保存的码序列跑两个实现（原版 vs 新版），比对 7 个指标
（snr/sndr/sfdr/thd/enob/dc/residual_rms）+ harmonic_bins：

| 阶段 | 覆盖 | 结果 |
|---|---:|---|
| 改完未部署（独立目录加载） | **117 个真实 run** | **0 差异** |
| 部署后复验（真实路径 vs 备份） | **117 个真实 run** | **0 差异** |

117 个 run 覆盖了不同输入频率（19.5k / 97.7k / 1.99M 等）、不同记录长度（256 / 2048）、
以及各种非理想组合——只要指标数学有丝毫变化，至少会在其中一个上暴露。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 84 == 84，**完全一致** |
| 运行时指标（117 run × 7 指标） | **0 差异** |
| `which()` 路径不同 | ✅ |
| 断言 ID 保留 | ✅ |
| 部署哈希 | 本地 == 远端 `c6c2cf78…` |
| 模型 SHA | `f358f226…` 未变 |
| 生产状态 | factory OFF 未变 |

## 三批累计

| 文件 | 行数变化 | 多语句 |
|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 |
| `behavior_sample_explain` | 423→513 | 23→0 |
| `behavior_sample_plot` | 454→508 | 32→0 |
| `behavior_spectrum` | 47→70 | 7→0 |

**4 个文件，累计消除 80 处单行多语句。**

## 剩余可改但风险更高的

`behavior_calibration_workflow`(24)、`behavior_frontend_step`(18)、
`behavior_backend_step`(9)、`behavior_applied_note`(15)。

其中 `calibration_workflow` 会真跑仿真、`frontend_step`/`backend_step` 是仿真内核，
改完必须跑整图对比 SNDR，成本远高于本轮。

## 本轮踩坑（新增 3 条）

6. **MATLAB 函数缓存**：改了文件但同会话里仍跑旧版。必须 `clear functions; rehash toolboxcache; clear <fname>;`
7. **`load` 不能读 JSON**：`summary.json` 要用 `jsondecode(fileread(...))`。
8. **metadata 字段名不同**：`behavior_spectrum` 期望 `p.stimulus`，但保存的 P 里叫 `p.input`，
   需要转换（`input` 的字段名恰好兼容）。
