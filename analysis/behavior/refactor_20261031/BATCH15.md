# 可读性重构：第十六批（十一个 1–2 处多语句的纯函数）

日期：2026-10-31。

## 本轮改动（11 个文件，23 处 → 0）

| 文件 | 行数 | 多语句 |
|---|---|---|
| `public_calibration_config` | 83 | 1→0 |
| `behavior_frontend_init` | 113 | 1→0 |
| `behavior_record_ready_summary` | 17 | 2→0 |
| `behavior_bank_validate_rows` | 25 | 2→0 |
| `behavior_jitter_parameters` | 30 | 2→0 |
| `behavior_transport_unpack` | 32 | 2→0 |
| `behavior_bank_record_gate` | 33 | 2→0 |
| `behavior_control_stage` | 66 | 2→0 |
| `behavior_reference_queue_step` | 85 | 2→0 |
| `behavior_ra_noise_validate_backend` | 114 | 2→0 |
| `behavior_cal_collector_step` | 128 | 2→0 |

除了拆行，给几处关键逻辑补了说明：

- **`behavior_frontend_init` 的 Fisher-Yates 交换**：说明这是"把当前槽与 keyed 伙伴交换"，否则三行 swap 看不出意图
- **`behavior_record_ready_summary` 的 ready 语义**：`1 = published`、`0 = 明确未就绪`、**其他值一律算 unknown**
- **`behavior_transport_unpack` 的 commit time**：说明"只有 tag 有效且 ready 置位才写 commit time，否则保持 Inf，这样它不能伪装成一次真实提交"
- **`behavior_jitter_parameters` 的字段拷贝**：说明是"逐字段拷入归一化结构，未知多余字段被保留而非静默丢弃"

## 验证

**Token 级**：11 个文件**全部 IDENTICAL**（无一处需要人工判断差异）。

**运行时**：

| 分组 | 覆盖 | 结果 |
|---|---|---|
| P 驱动 3 个函数 | 12 个真实 P × 3 | 0 差异 |
| `record_ready_summary` | 40 组手造 V 结构（含 %invalid、%unknown 混合） | 0 差异 |
| `transport_unpack` | 40 组 97 词输入 | 0 差异 |
| **合计** | **116 用例** | **0 差异** |

**11 个 `__old` 副本全部确认加载**（`per.loaded` 字段全 true），排除"两调用命中同一函数"的假阳性。

**部署**：11/11 哈希 MATCH。

## 一次测试自身的错误（已修正）

初版测试对 `behavior_ra_noise_validate_backend` 用 `a=feval(...)` 绑定返回值，**但它没有输出参数**，新版报 `MATLAB:TooManyOutputs`，造成 12 条假差异。

修正为"不绑定返回值、只比对错误 identifier"后归零。**这是测试代码的问题，不是重构的问题。**

## 结果

| 检查 | 结果 |
|---|---|
| Token 级 | 11 个全部 IDENTICAL |
| 运行时（116 用例） | **0 差异** |
| 部署哈希 | 11/11 MATCH |
| 模型 SHA | `f358f226…` 未变 |

## 十八批累计

**39 个文件，累计消除 184 处单行多语句。**

## 纯函数剩余：9 个、92 处

| 文件 | 多语句 | 为什么不再是低风险 |
|---|---:|---|
| `sar20_pp_verify_v3_qualification` | 2 | **在冻结校验链上**，改动会牵动 v3 资格校验，主动跳过 |
| `behavior_dac_forcing_from_frontend` | 5 | 需 backend 实时状态（`xFE`+`bk` 须来自真实区间） |
| `sar20_pp_parameters` | 7 | 校准参数校验，需完整资格上下文 |
| `behavior_transport_step(_pp)` | 16 | 传输协议状态机，需真实 RX 数据序列 |
| `summarize_adi_cases` | 13 | 需 8 个身份匹配的配对 run |
| `sar20_pp_step` | 15 | 校准状态机 |
| `validate_behavior_adi_case` | 16 | 缺 `adi_wire_log58`（实测 40 个 run 均为 0） |
| `behavior_frontend_step` | 18 | 前端电荷核心，须跑整图比 SNDR |

**这 9 个都不属于"低风险"范畴了。**
