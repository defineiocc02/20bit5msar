# 一个样本为何得到 524285：真实层级导览候选

![ID4 真实事件与层级导览](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/designer_map_20261028/id4_designer_map.png)

图选用 [112407 负端真实记录](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T112407Z/zero_result/receipt.json)，不是理想码或合成例。保存的 P、9 路实际时序日志和工厂 SLX 在该 run 的 `point_001` 与 `zero_result` 中；本地只读脚本 [read_id4_actual.py](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/designer_map_20261028/read_id4_actual.py) 精确按实际 ID4 / group / Time 读取，[id4_actual.json](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/designer_map_20261028/id4_actual.json)保存取数结果。另有 [独立逐事件报告](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/local_static_20261028/ZERO_112407_REVIEW.md)。SVG 和 PNG 是供审阅的静态导览，不是重绘或修改后的实际 Simulink 图。

## 一个样本的数据

条件是 ID4 / epoch1、DC `−30.517578125 nV`、N=1，ID0–3 为四次实际预热；sample CNV 为 `0.8 µs`。transport off，`τDAC=τsample=0`，DAC 耦合、AZ、kTC、失配、DEM、dither、jitter、训练和冻结均 off；A0=10000、UGB=1.2 GHz，CINC 模型 on。模型 SHA `63190994…54ec2b6` 与当前14张导图的 [metadata](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/metadata.json)一致，但导图保存 P 是默认 N8/正弦；不把截图上的默认输入当成此 N1/DC run 的条件。

| 实际事件（相对CNV） | 数值与来源 | 判断边界 |
|---|---|---|
| 0 ns `cnv` | `front_log.held=−30.517578125 nV` | 已保存的行为模型观察，不是芯片测量。 |
| 15 ns `fine_decide` | `front_log.Vres=−30.517578128 nV`；`raw_log.D1=1024` | 该细位 bit4=0 是根据实际 D1 写位推断；Compare1 独立输出没有完整保存。该行的中间 D1 也不是最终 ready 记录。 |
| 31.25 ns `ra_start` | `front_log.Qres=+0.217211293 pC`；`back_log.target=+0.255999023 V`；此时 D1=1039 | target 是本阶段的目标观察，不等于 RA 输出已经到达的电压。 |
| 43.75 ns `d2_prepare` | `back_log.VX=+0.239176359 V`、`VY=+0.186250247 V` | 它们是同一阶段的实际日志值；本次 `dac_ra_pre_log` 没有完整时序，不能称这组数据是另外保存的 RaPre。 |
| 86.25 ns `raw_latch` | 实际 RAW6=`[1039,3417,42,4,1,1]`；`code_log=524285` | `ADC RawReady=record-ready=0.88625 µs`，因 transport off 没有 RX 迟到时间线。 |

只作算术核验：由最终已记录 RAW 和该 run 已保存 `P.digital` 重建输入参考名义贡献 `−8000 + 7984.375 − 11.71875 = −27.34375 µV`。在 FSR=8.192 V（名义 LSB=7.8125 µV）下，`clip(round(2^19−3.5))=524285`；实际码仍直接取 `code_log`。此次 D1/D2/DT 分量日志未完整保存，因此这些分项是重建值，不是独立测得的模拟节点。

## 预测、状态和边界

- 顶层 `Driver` 为片外输入配置，`Calendar` 是行为事件日历；`EventStep` 只是调度容器，不是芯片外形。`EventStep/Adc` 和 `EventStep/Fpga` 是真实同层块；Record 和 RecordReady 是两个真实 switch，图中各画一块。名义算术白框只是对 FPGA 多个真实标准块的分组说明，不是新增模块。
- ADC 六个实际子系统在同一事件中顺序计算，三个原始 UnitDelay：`SampleCharge[353]`、`RaCtState[48]`、`SarState[51]`拥有各自的 FE、RA/AZ/CT 和控制状态。UnitDelay 输出是之前锁存的旧状态；本事件的 stage/next 是待锁存计算候选，不能把观察值假称当前事件提交后的完整状态。本例没有单独保存完整提交态。
- `FE_old→RaAdvance.u4` 是模型真实存在的线，但本例 DAC 耦合 off 且全 τ=0，源码的旧算术分支不读取 u4。finite-DAC 开启时可能由旧 FE 状态做只读端点预测；那是其他配置，不把预测或 `Sample.next` 当成一套已提交电荷。
- `ChargeReturnRaReset` 是已有路径；该点的 return 专用 tap 没有完整记录，不能据此杜撰逐片返回或提交后值。没有新增模拟状态、RA 后采样保持、Bank 或 M1 功能；图上只画真实层级及本例数据路径。

图形本身仍是设计者说明候选，当前真实 Top/System/ADC 等截图仍有微缩、拥挤或函数名截断，不能据此称视觉验收通过。四次预热不是一般稳态或硅/PDK 验证。
