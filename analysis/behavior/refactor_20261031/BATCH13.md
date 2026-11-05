# 可读性重构：第十四批（四个微型纯函数）

日期：2026-10-31。

## 本轮先纠正了上一轮的错误

上一轮我判断"低风险做尽"，但筛选门槛设成了 `multi>=3`，**漏掉了所有只有 1–2 处多语句的文件**。

重新扫描后：**还有 33 个纯函数文件、共 66 处多语句**是安全的。其中 25 个文件只有 1–2 处（共 35 处），累计 1165 行。

这是本轮才发现的范围遗漏，先记录为错误判断的更正。

## 本轮改动（4 个最小文件）

| 文件 | 行数 | 多语句 |
|---|---|---|
| `behavior_public_pol` | 21 | 1→0 |
| `behavior_aperture_diagnostic` | 13 | 1→0 |
| `behavior_reference_queue_unpack` | 6 | 1→0 |
| `behavior_sar_unpack` | 28 | 1→0 |

改动都是把一行内的多语句拆开，并给关键步骤加一句说明。例如：

```matlab
% Pre-fill the 28-word observation with NaN so an invalid sample reports a
% fully populated but explicitly unknown row rather than a short vector.
```

这条注释解释了为什么先填 `nan(25,1)` —— 否则读者会以为 NaN 是没处理完。

## 验证

**Token 级**：四个文件全部 **IDENTICAL**（36 / 24 / 18 / 79 tokens）。

**运行时**：

| 函数 | 覆盖 | 结果 |
|---|---|---|
| `behavior_public_pol` | 5 种模式 × 11 个 ID × 3 个 epoch | 0 差异 |
| `behavior_sar_unpack` | 200 个合法 51 词状态（含全部 4 种 pending type） | 0 差异 |
| `behavior_reference_queue_unpack` | 100 个合法 22 词状态 | 0 差异 |
| **合计** | **465 个用例** | **0 差异** |

部署后确认：4 个文件本地/远端哈希全部 MATCH；`behavior_public_pol` 最小复验 18/18 一致。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级 | 4 个全部 IDENTICAL |
| 运行时（465 用例） | **0 差异** |
| 部署哈希 | 4/4 MATCH |
| 模型 SHA | `f358f226…` 未变 |

## 十六批累计

**19 个文件，累计消除 152 处单行多语句。**

## 剩余（本轮新发现的范围）

**纯函数、1–2 处多语句剩余 21 个文件**（不含本轮 4 个），累计约 31 处：
`behavior_cal_collector_step`(2)、`behavior_ra_noise_validate_backend`(2)、`behavior_frontend_init`(1)、
`behavior_reference_queue_step`(2)、`public_calibration_config`(1)、`behavior_control_stage`(2)、
`behavior_training_configuration`(1)、`behavior_dac_backend_parameters`(1)、
`sar20_pp_verify_v3_qualification`(2) 等。

这些都需要各自的合法输入，逐个评估。
