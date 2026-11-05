# 可读性重构：第十二批（behavior_ra_noise_guard）

日期：2026-10-31。

## 本轮改动

**`current/src/model/behavior_ra_noise_guard.m`**：232 → 266 行，多语句 9 → 0

禁止复用未 "标定" 的 ON 噪声配置。这是准备配置阶段的守门员。

### 函数头重写成四种状态

原文只有三行注释。现在明确：

- **TWO MODES** — `check`（断言已有 coverage 标记自洽）/ `derive`（重算并存储）
- **LEGACY OFF** — 早于 coverage 字段的 OFF P 原样放行，旧配置还能加载；**ON 模式下 sigma=0 允许但记 coverage=false**（零应力证明的是"路径被标注"，不是"路径已启用"）
- **WHY THIS EXISTS** — 一个 ON 配置只有在它声称覆盖的非理想**恰好就是开着的那些**时才有意义。守门员从 P 重新推导日历与全部 M8 结构再比对，**过期或手改的 schedule 会被拒绝**，而不是被默默当作合格。

这几条原本完全没写，读代码只能靠猜"为什么要这么严"。

### 一处关键注释

```matlab
% Re-derive the whole calendar from the control values and compare. Anything
% that does not match is a stale or hand-edited schedule, not a valid one.
```

## 验证

**Token 级**：
```
old statements=499  new statements=499
identical: True
```

**运行时**：这个函数只需要一个 prepared P，而**每个 run 目录的 `parameters.mat` 里存的正是历史真实 P**，所以可以用真实数据做穷举。

| 阶段 | 覆盖 | 结果 |
|---|---|---|
| 改完未部署 | **30 个真实 P × 2 模式 = 60 用例** | **0 差异，全部成功（err=0）** |
| 部署后 | 新版 vs 备份最小用例 | `same: true`，路径不同 |

60 个用例覆盖了 ON/OFF 两类配置（不同非理想组合），且全部走的是**校验通过**路径。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 499 == 499，完全一致 |
| 运行时（60 用例） | **0 差异** |
| 部署哈希 | 本地 == 远端 `fca18b3b…` |
| 模型 SHA | `f358f226…` 未变 |

## 十三批累计

| 文件 | 行数 | 多语句 |
|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 |
| `behavior_sample_explain` | 423→513 | 23→0 |
| `behavior_sample_plot` | 454→508 | 32→0 |
| `behavior_spectrum` | 47→70 | 7→0 |
| `behavior_record_view` | 69→129 | 8→0 |
| `behavior_decode` | 87→109 | 6→0 |
| `behavior_az_schedule` | 74→98 | 5→0 |
| `behavior_aperture_times` | 40→73 | 6→0 |
| `behavior_public_cal_fit` | 82→116 | 7→0 |
| `behavior_holdout_result` | 81→114 | 8→0 |
| `behavior_training_result` | 113→159 | 9→0 |
| `behavior_public_dither` | 19→37 | 3→0 |
| `behavior_event_groups` | 30→55 | 3→0 |
| `behavior_ra_noise_guard` | 232→266 | 9→0 |

**14 个文件，累计消除 144 处单行多语句。**

## 踩坑（新增 1 条）

19. **大规模文件扫描容易超时静默失败**：全量扫 200+ 个 `parameters.mat` 时任务结束后无产出。
    **限制到 30 个**后稳定通过。这类穷举要**先小样本试点再放量**。
