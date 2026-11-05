# 可读性重构：第十五批（九个单点多语句的配置/打包函数）

日期：2026-10-31。

## 本轮改动（9 个文件，每个只有 1 处）

| 文件 | 行数 |
|---|---|
| `behavior_cal_collector_snapshot` | 38 |
| `behavior_training_configuration` | 62 |
| `behavior_dac_backend_parameters` | 60 |
| `behavior_dac_coupling_configuration` | 22 |
| `behavior_reference_configuration` | 38 |
| `behavior_reference_queue_parameters` | 15 |
| `behavior_transport_init` | 27 |
| `behavior_transport_pack` | 29 |
| `behavior_backend_pack` | 21 |

全部 **1 → 0** 处多语句。改动都是拆行，个别补一句说明（如 `reference_queue_parameters` 里说明"复制每个字段到归一化结构，未知多余字段被保留而非静默丢弃"）。

## 验证

**Token 级**：9 个文件全部等价（8 个 IDENTICAL，`transport_pack` 仅续行符差异）。

**运行时**：

| 分组 | 覆盖 | 结果 |
|---|---|---|
| 4 个 P 驱动函数 | 12 个真实 P × 4 函数 | 0 差异 |
| `reference_queue_parameters` | 50 组随机结构 | 0 差异 |
| `transport_init` | 1 次真实日历调用（实际跑通） | 0 差异 |
| `transport_pack` / `cal_collector_snapshot` | 各 1 次拒绝路径（含 identifier 比对） | 0 差异 |
| **主轮合计** | **98 用例** | **0 差异** |
| **补充轮** | **3 用例** | **0 差异** |

**验证了旧副本确实存在**：9 个 `__old.m` 全部生成（字节数正常），排除了"两个调用其实命中同一函数"的假阳性。

**部署**：9/9 文件本地/远端哈希 MATCH。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级 | 9 个全部等价 |
| 运行时（101 用例） | **0 差异** |
| 部署哈希 | 9/9 MATCH |
| 模型 SHA | `f358f226…` 未变 |

## 十七批累计

**28 个文件，累计消除 161 处单行多语句。**

## 剩余纯函数 1–2 处多语句

`behavior_frontend_init`(1)、`public_calibration_config`(1)、`behavior_public_cal_features`（锁定，跳过）、
`behavior_control_stage`(2)、`behavior_cal_collector_step`(2)、`behavior_ra_noise_validate_backend`(2)、
`behavior_reference_queue_step`(2)、`behavior_bank_record_gate`(2)、`behavior_bank_validate_rows`(2)、
`behavior_record_ready_summary`(2)、`behavior_jitter_parameters`(2)、`behavior_transport_unpack`(2)、
`sar20_pp_verify_v3_qualification`(2) 等。

下轮继续。
