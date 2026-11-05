# 可读性重构：第四批（behavior_record_view）

日期：2026-10-31。

## 先补了一个上一轮没查清的问题

上一轮发现 9 个文件被哈希锁定。本轮追问了一个更隐蔽的风险：

> **如果被锁定文件调用了某个未锁定的函数，而那个函数行为变了，哈希校验仍会通过，但算法行为已变。**

这是"间接锁定"风险。做法：从 9 个锁定文件出发，递归构建调用图，找出所有传递依赖。

**结果：0 个传递依赖。**

也就是说 9 个锁定文件的依赖是**自包含**的——它们只调用彼此，不依赖外部可改文件。
**锁定边界是完整的，不存在间接锁定漏洞。** 这个结论让后续改动可以放心做。

## 本轮改动

**`current/src/analysis/behavior_record_view.m`**：69 → 129 行，多语句 8 → 0

这是公共记录流的 IO 边界，被 4 处调用（包括 `behavior_sample_debug`、`behavior_sample_explain`、`behavior_sample_plot`）。

改动：
- 8 处单行多语句展开
- 函数头重写成完整契约：输入是什么、两种日志源（新图 `record_log`/`record_ready_log` vs 旧图 `raw_log`/`ready_log`）、输出各字段含义、单位
- 明确写出**刻意保留的行为**：

```
% Preserved intentionally: selected invalid/NaN words are NOT filtered out here.
% Acceptance and validity gating belong to the caller, so a failing sample still
% shows up in explanations instead of vanishing.
```

这条很重要——之前读代码时容易误以为"没过滤是 bug"，实际是设计决定。

## 验证：两层

**第一层：Token 级等价**
去注释、去空白、统一语句分隔符后逐语句比对：

```
old statements=214  new statements=214
identical: True
```

**第二层：运行时数值 + 结构比对**

| 阶段 | 覆盖 | 结果 |
|---|---:|---|
| 改完未部署 | **245 个真实 run** | **0 差异** |
| 部署后复验 | **245 个真实 run** | **0 差异** |

245 个 run 是全部带 `simout.mat` 的 run，覆盖 range 内的所有配置组合。
比对的不只是数值字段，还包括 char 字段（`readiness_boundary`、`raw_log_source` 等）与 logical 字段。

这是四批里**覆盖面最广**的一次验证。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 214 == 214，完全一致 |
| 运行时（245 run × 全字段） | **0 差异** |
| `which()` 路径不同 | ✅ |
| 部署哈希 | 本地 == 远端 `9a9f1168…` |
| 模型 SHA | `f358f226…` 未变 |
| 生产状态 | factory OFF 未变 |

## 五批累计

| 文件 | 行数 | 多语句 |
|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 |
| `behavior_sample_explain` | 423→513 | 23→0 |
| `behavior_sample_plot` | 454→508 | 32→0 |
| `behavior_spectrum` | 47→70 | 7→0 |
| `behavior_record_view` | 69→129 | 8→0 |

**5 个文件，累计消除 88 处单行多语句。**

## 踩坑（新增 2 条）

9. **递归调用图要查传递依赖**：只查直接锁定文件不够，要问"被锁文件调用了谁"。
10. **heredoc 覆盖 entry.m**：多次用 `cat > entry.m <<EOF` 时，若模板里含变量会被提前展开导致内容丢失。
    更稳的做法是每次用独立文件 `scp`，并**回读确认内容**再触发任务。
