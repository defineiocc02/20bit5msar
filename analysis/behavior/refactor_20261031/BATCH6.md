# 可读性重构：第六批（behavior_az_schedule）

日期：2026-10-31。

## 本轮改动

**`current/src/backend/behavior_az_schedule.m`**：74 → 98 行，多语句 5 → 0

纯函数：给定样本 ID、epoch 与相位偏移，决定 AZ 是否开启、极性、以及用了哪个写窗口。
输入只需标量与结构体，**可以穷举测试全部状态组合**。

### 重组了函数头

原文把写窗口、hold、chopping、极性作用域混在一段里。现在分成四节：

- **WRITE WINDOW** — `[0, RA-start=31.25 ns)`，要求 RA off，并强调这是行为级相位分配**不是实测电路写入时刻**
- **HOLD MODES** — 写偶数 ID、保留配对奇数帧、`pair_id = floor(id/2)`
- **CHOPPING** — POL 按 `[+1,-1,-1,+1]` 循环；**返回的极性作用于完整物理 Qres**，而 CT D2/TA 符号**不参与**，仍留在后端比较器的负反馈坐标里
- **WHAT THIS FUNCTION DOES NOT DO** — 无 RNG、无状态、无事件创建

极性作用域这一条最容易搞错（改错会导致 D2/TA 符号被重复翻转），现在写清了。

## 验证：两层

**第一层：Token 级等价**
```
old statements=162  new statements=162
identical: True
```

**第二层：穷举状态组合**

| 维度 | 取值 |
|---|---|
| AZ 模式 | 5 种（off / ordinary / chop / hold / hold_chop） |
| 样本 ID | 0..7（覆盖 chopping 4 相与 hold 奇偶） |
| epoch | 0..1 |
| ra_on | 0/1 |
| release | 0/1 |
| 相位偏移 | 6 个（负值 / 0 / 窗口内 / 恰在边界 / 边界前一瞬 / 超窗） |

**共 1920 个组合**，比对全部字段含 char（`write_window_source`）与 logical，
并**同时比对错误路径的 identifier**（例如 RA 与 AZ 窗口重叠必须抛同一个错）。

| 阶段 | 结果 |
|---|---|
| 改完未部署 | **1920 组合 0 差异** |
| 部署后复验 | **1920 组合 0 差异** |

穷举验证比抽样强得多：这个函数的每条分支都被覆盖到了。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 162 == 162，完全一致 |
| 穷举 1920 组合（含错误路径） | **0 差异** |
| 部署哈希 | 本地 == 远端 `60b245e3…` |
| 模型 SHA | `f358f226…` 未变 |

## 七批累计

| 文件 | 行数 | 多语句 |
|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 |
| `behavior_sample_explain` | 423→513 | 23→0 |
| `behavior_sample_plot` | 454→508 | 32→0 |
| `behavior_spectrum` | 47→70 | 7→0 |
| `behavior_record_view` | 69→129 | 8→0 |
| `behavior_decode` | 87→109 | 6→0 |
| `behavior_az_schedule` | 74→98 | 5→0 |

**7 个文件，累计消除 99 处单行多语句。**

## 踩坑（新增 1 条，同一问题第二次）

12. **heredoc 写 entry.m 再次丢内容**：`cat > entry.m <<EOF` 写了 4 行，实际只剩 `az_final;`。
    改用 `printf '%s\n' "..." "..." > file` 后正常，并**回读确认**再触发任务。
    **这个坑已经踩了两次，后续一律用 printf + 回读校验。**
