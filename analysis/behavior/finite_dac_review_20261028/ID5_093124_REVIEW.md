# 093124：ID5 的 τ=0 与 1 ns 只读复核

按两次实际 `event_log` 的 ID5、ADC group 1–48 和精确时间连接原始日志，093124 回执的行数及首次差异得到复核：front 26 行不同，RaPre 和 BackLog 各 48 行不同，control 与 event 均无数值差。这里的“行不同”指该行任意字段按 `isequaln` 语义不同，**不是每个字段都不同，也不是逐位比较结论**。

两次保存 P 只差 front τ、backend 绑定 τ 和有限建立 NI 标记；87 项 as-run 源文件 SHA 相同、340 条原生边及 solver 配置相同，块参数唯一差别是图上显示 τ 的文字。下表均为实际事件端点，差值方向为 1 ns 减 0。

| ID5 时间 | 实际事件与观测 |
|---:|---|
| 0 ns，CNV | RaPre VX 分别为 `3.547822608032956e−49`、`3.547819850016148e−49 V`，差 `−2.758016808466431e−55 V`；VY 和 target 均为 0。 |
| 12.5 ns，coarse_latch/fine_prepare | Front Qres 分别为 `−0.717752529312 pC` 和 `0 pC`；此时 RA 仍关断，RaPre VX 约 `1.32215e−54 V`，不能把 front 差当成即时 mV 级 VX 差。 |
| 18.75 ns，fine_decide | RaPre Vtop 的最大差为 `59.650170786 mV`，但 RA 仍关断；该观测由 `(VX−target)/NG` 算出，此处 target 分别为 `+1.202077376 V` 和 `−0.826028431 V`。此差不能叫 VX 差、已测物理电压或单独的 RA 建立误差。 |
| 31.25 ns，fine_feedback/ra_start | 控制进入 RA 启动；不能将本事件的后续提交阶段倒填成 RaPre。 |
| 43.75 ns，d2_prepare | RaPre VX 分别为 `166.375237850`、`161.727393829 mV`，差 `−4.647844021 mV`；VY 分别为 `129.558913316`、`125.939566901 mV`，差 `−3.619346415 mV`。 |
| 86.25 ns，raw_latch | ADC 的 RAW6 均为 `[1932,2907,85,5,1,1]`。 |
| 1.538 µs，RX ready | 两次接收到相同 RAW6，20 位码均为 `979654`；只说明此 ID 的实际数字结果相同。 |

0 ns 的微小 VX 差与跨样本状态记忆一致：ID4 release 时 RaPre VX 为 `0.2100655842127945`、`0.21006542091139077 V`。按保存的 `τ_reset=1 ns` 和随后到 ID5 CNV 的 `110 ns`，as-run 的 reset 衰减公式给出上述两项 0 ns 值，分别与实际观测逐位一致。这是**结合源码和两处实际观测的推断**；ID4 release 的 BackLog 位于最终 RaReset 提交前，完整提交状态未单独记录。

`dac_ra_pre_log` 来自 RaAdvance 端点，位于本事件后续 CINC 反馈/命令提交之前；`back_log` 位于更晚阶段，二者不可按同一物理相位替换。原 093124 代码用绝对时间窗口上下 `1e−14 s` 找行；上述复核采用实际事件 ID/group 与精确时间 join，未用窗口容差。原图连接离散端点，不足以证明连续波形极值。

完整输入 SHA、各字段首次差异和关键实际向量见 [id5_093124_independent.json](id5_093124_independent.json)，其 SHA-256 为 `cdcd5cfa1c1ec8d579b769f5a951d4a441cfd6b8b56aaeb050117fcd4765905d`；重读入口为 [verify_id5_093124.py](verify_id5_093124.py)。本报告没有重新仿真或操作 Windows/current。
