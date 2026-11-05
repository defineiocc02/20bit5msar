# 可读性重构：第二批（两个分析工具）

日期：2026-10-31。

## 本轮改动

| 文件 | 改前 | 改后 | 多语句 | 风险等级 |
|---|---:|---:|---:|---|
| `behavior_sample_explain.m` | 423 行 | 513 行 | 23 → **0** | 低（纯分析） |
| `behavior_sample_plot.m` | 454 行 | 508 行 | 32 → **0** | 低（纯绘图/CSV） |

加上上一轮的 `behavior_sample_debug.m`（167→315，18→0），三个低风险文件全部完成。

**只改格式与注释，未动任何逻辑。**

## 这两个文件做了什么

**`behavior_sample_explain.m`**（生成中文解释 markdown）
- 23 处单行多语句展开
- 函数头重写：说明输入从哪来、输出是什么、单位、以及**刻意不做的事**（不重建物理行、不做验收判定）
- 嵌套 `add` 函数补说明：为什么保持嵌套（避免把 `lines` 传遍每个 helper）
- `phase_rows` 补说明：按事件名匹配，**从不按时间 epsilon**

**`behavior_sample_plot.m`**（生成 CSV + 3 张 PNG/FIG）
- 32 处单行多语句展开
- 同样只改格式

## 验证方法（各自适配）

**explain 文件**：它写 markdown，所以直接**比对 markdown 全文 + 全部数值字段**。
关键处理：`generated_utc` 是每次调用时间戳，必须排除；日志正文里的时间戳用正则归一化后再比。

**plot 文件**：它产出 PNG/FIG（`exportgraphics` 输出含渲染器/字体信息，同代码两次运行也可能字节不同）+ CSV（确定性）。
所以**只比对 3 个 CSV 的内容 + 59 个 struct 字段**，不比对图片。
关键处理：两个临时 run 目录必须**同名叶子目录**，否则 `run_name` 字段会因目录名不同而产生假差异。

## 结果

| 检查 | explain | plot |
|---|---|---|
| 原实现 vs 新实现，`which()` 路径不同 | ✅ | ✅ |
| 输出内容差异 | **0**（排除时间戳） | **0**（59 字段 + 3 CSV） |
| 部署后真实路径回归 | ✅ 与基线一致 | ✅ |
| 函数数量 | 12 → 12 | 5 → 5 |
| 断言 ID 全保留 | ✅ | ✅ |
| figure/exportgraphics/writetable 计数 | — | 3/3/4 → 3/3/4 |

## 模型与生产状态

- 模型 `SarAdc.slx` SHA `f358f226…` **未变**
- 生产状态 factory / ktc=off / ra=off / N=8 **未变**

## 文件

- `behavior_sample_explain.m.orig`（423 行原件）
- `behavior_sample_plot.m.orig`（454 行原件）
- `sar20_explain_regress.m`、`sar20_plot_regress.m` — 回归脚本
- `explain_before.json` / `explain_after.json` — explain 改动前后实测
- `baseline_before.json` / `baseline_after.json` — debug 文件（上一轮）

## 踩到的坑（记录下来避免重犯）

1. **上传顺序**：`scp` 到不存在的远端目录会失败。必须先 `New-Item` 建目录再传。
2. **时间戳字段**：`generated_utc` / `export_utc` 每次调用都不同，必须从对比中排除。
3. **目录名派生字段**：`run_name` 来自 `fileparts(runPath)`，两个测试目录不同名会产生假差异。
4. **PowerShell 重定向破坏编码**：用 `>` 把 JSON 抓到本地会损坏 UTF-8 中文，必须用 `scp`。
5. **计划任务需要显式触发**：`Set-ScheduledTask` 之后 `Start-ScheduledTask` 有时不生效，需要再手动 trigger 一次。

## 剩余的仿真内核文件

| 文件 | 多语句 | 风险 |
|---|---:|---|
| `behavior_calibration_workflow.m` | 24 | 中 |
| `behavior_frontend_step.m` | 18 | 中高（仿真内核） |
| `behavior_backend_step.m` | 9 | 高（RA/AZ 物理核心） |

后两个改完不能只测函数输出，必须跑整图对比 SNDR 才能确认。
