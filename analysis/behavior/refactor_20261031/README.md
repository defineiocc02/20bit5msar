# 可读性重构：第一个样板文件

日期：2026-10-31。文件：`current/src/analysis/behavior_sample_debug.m`

## 为什么选它做样板

| 判据 | 结果 |
|---|---|
| 在 Simulink 模型里？ | **否**（SLX 无引用） |
| 在冻结校验链里？ | **否**（不属于 4 个硬编码 SHA 文件） |
| 调用者 | 只有 `behavior_sample_explain.m`、`behavior_sample_plot.m` 两个分析工具 |
| 单行多语句 | **18 处** |
| 原规模 | 167 行 |

风险最低，适合先证明流程。

## 改了什么

**只改格式与说明，不改任何逻辑。**

1. **18 处单行多语句 → 0 处**
   原来形如 `function yes=slot_in_transition(t,k),yes=...;end` 这种一行塞多个语句的写法，
   MATLAB 调试器无法在中间下断点，出错行号也指不准。现在每句一行。

2. **补充函数头说明**
   原文只有 5 行注释。新增说明了：返回什么、两个独立轴（ADC 执行 vs record 就绪）、
   以及**刻意不做什么**（不插值、不造假物理行、不做理想重建、不做验收判定）。

3. **局部函数补一行注释**
   5 个 local function 各自说明输入/输出契约。

4. **长表达式拆行**
   多处 `&&` 长条件拆成多行，失败时能看出是哪个条件不成立。

## 怎么验证的

**先建基线，再改，最后对比。**

1. **录基线**：写回归脚本 `sar20_debug_regress.m`，把函数输出压成一个可 diff 的标量/字符串摘要
   （32 个字段，覆盖 record 选择、branch 值、Bank 判定、所有 reason 字符串）。
   用两个真实 run 做输入：一个普通 256 记录、一个含 Bank 的 8 记录。

2. **改完后对比**：把新实现以 `behavior_sample_debug__new` 的临时函数名加载到**独立目录**，
   与原实现同输入并跑，做**深度递归比较**（含结构、NaN、char）。
   并额外验证两者 `which()` 路径确实不同，排除"其实调了同一个函数"。

3. **部署后再验一次**：把新文件装进 Windows 真实路径，重跑同一回归，与基线比对。

## 结果

| 检查 | 结果 |
|---|---|
| 结构/深度对比（改前 vs 改后，同输入） | **0 处差异** |
| `which()` 路径不同（排除同函数） | 确认不同 |
| 部署后回归 vs 基线（2 case × 32 字段） | **全部 IDENTICAL** |
| 函数数量 | 5 → 5（结构未变） |
| 单行多语句 | 18 → **0** |
| 模型 SHA | `f358f226…` 未变 |
| 生产状态 | factory OFF 未变 |

## 文件

- `behavior_sample_debug.m.orig` — 改动前原件（167 行）
- `sar20_debug_regress.m` — 回归脚本，输出可 diff 摘要
- `baseline_before.json` / `baseline_after.json` — 改动前后实测
- `compare.py` — 对比工具
- README.md — 本文

## 下一步可做

同一套流程可以推广到其余文件。按性价比排序：

| 文件 | 多语句 | 风险 |
|---|---:|---|
| `behavior_sample_explain.m` | 23 | 低（纯分析） |
| `behavior_calibration_workflow.m` | 24 | 中 |
| `behavior_sample_plot.m` | 32 | 低（纯绘图） |
| `behavior_frontend_step.m` | 18 | **中高**（仿真内核） |
| `behavior_backend_step.m` | 9 | **高**（RA/AZ 物理核心） |

前三个安全，后两个要更谨慎。
