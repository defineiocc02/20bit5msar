# 可读性重构：第十批（behavior_training_result）

日期：2026-10-31。

## 本轮改动

**`current/src/calibration/behavior_training_result.m`**：113 → 159 行，多语句 9 → 0

读实际提交的 collector/Ref4 与 DWork 快照，解释训练结果。**本身不跑拟合**。

### 函数头重写成"两个来源 + 为什么状态索引重要"

原文把来源形式与状态语义混在一起。现在分三节：

- **TWO SOURCE FORMS** — `committed`（`.extracted` 为真 + `status7`/`snapshot2624`，即实际最终 Train DWork，**总是优先**）vs legacy（四参数形式，从 `cal_status_log`/`cal_fit_log` 读单行）。并说明 **stale Outputs 永远不能决定完成态**，所以 record graph 上会拒绝 legacy。
- **WHY THE STATUS INDEX MATTERS** — `state(4)` 选取 8 种具名结局之一；**只有当拟合产出完整 684 行解且状态是成功码时，候选系数才会被附加**，因此部分解绝不会被当作可用结果报出。
- **SCOPE** — 即使成功也只是训练候选，独立 holdout / native commit / integer reload 都在本函数之外。

### 给两处"条件附加"加了注释

```matlab
% Candidate coefficients are only carried when the fit actually produced a
% full 684-row solution (flag f(10)) AND the status is the success code.
```
```matlab
% Singular values and column scales are reported only for a non-empty SVD.
```

这两处原本是裸 `if`，读者很难看出为什么要有条件。

## 验证：Token 级 + 运行时（成功路径 + 拒绝路径）

**Token 级**：
```
old statements=381  new statements=381
identical: True
```

**运行时**：先探测哪些 run 满足前置条件（`cal_cfg.enabled` + 有 simout），
全仓库共 **4 个**：

| run | 行为 |
|---|---|
| `behavior_30bb3ff5…` | **成功路径**：`training_candidate_requires_independent_holdout` |
| 其余 3 个 | 拒绝路径：`calResult:committedMissing` |

**关键**：`30bb3ff5` 这个 run 走到了**完整解析 DWork 快照**的深度路径
（读 `status7`/`snapshot2624`、校验 684 行解、附加候选 h 与奇异值），
这是本条验证最有价值的部分——不是只跑拒绝分支。

| 阶段 | 结果 |
|---|---|
| 改完未部署（成功路径 run） | **0 差异** |
| 部署后复验（真实路径 vs 备份） | **0 差异** |
| 部署哈希 | 本地 == 远端 `66e82ae3…` |
| 模型 SHA | `f358f226…` 未变 |

## 十一批累计

| 文件 | 行数 | 多语句 | 运行时验证 |
|---|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 | 245 run |
| `behavior_sample_explain` | 423→513 | 23→0 | 2 run |
| `behavior_sample_plot` | 454→508 | 32→0 | 1 run × 59 字段 |
| `behavior_spectrum` | 47→70 | 7→0 | 117 run |
| `behavior_record_view` | 69→129 | 8→0 | 245 run |
| `behavior_decode` | 87→109 | 6→0 | 7976 RAW 字 |
| `behavior_az_schedule` | 74→98 | 5→0 | 1920 组合 |
| `behavior_aperture_times` | 40→73 | 6→0 | 8688 组合 |
| `behavior_public_cal_fit` | 82→116 | 7→0 | 40 run |
| `behavior_holdout_result` | 81→114 | 8→0 | ⚠️ 仅 Token |
| `behavior_training_result` | 113→159 | 9→0 | **成功路径 + 拒绝路径** |

**11 个文件，累计消除 129 处单行多语句。**

## 踩坑（新增 2 条）

16. **`fwrite(fid, data)` 生成临时函数副本时，如果目标目录不存在会抛错且不报出**，
    导致后续 `feval` 报 `UndefinedFunction`。**应先确认目录存在，再写文件，再 `which()` 验证路径。**
17. **改 entry.m 后立即触发任务，任务可能读到旧内容**。需要在 `scp` 之后**回读确认内容**，
    并留几秒让文件系统同步；本轮加 `sleep 4` + `Get-Content` 回读之后才稳定。
