# SarPP 隔离 A 阶段：真实连接导览

![SarPP 已保存连接导览](/tmp/sar20_sarpp_133342_map/sarpp_actual_map.png)

本图是按 [133342 保存的 SarPP.slx](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T133342Z/SarPP.slx)、各案保存 P、[安装回读](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T133342Z/final_graph_readback/receipt.json) 与 [实际运行回执](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T133342Z/receipt.json)绘制的静态导览；并非原生 Simulink 截图。只画该模型存在的块和实际已连接的主要路径，省略其他诊断/控制连线。**该 A 阶段为隔离 scratch，尚未晋升 current，也不是产品/硅片签核。**

模型 SHA256 `82ede85bdc7c6a6ac5b1837e6f21c29711de9ee8ab2c26f151672dae76f9a99a`；图示 `rx_bank_on/parameters.mat` SHA256 `68b68d2e2d9aac0b52f1f5710930690b65e9c041692adafc5f4476e7b3b0c26c`。作业号为 2026-10-28 13:33:42 UTC，控制回执在 **13:35:37 UTC** 观察到完成。另有从 [已保存 P/日志及SLX回读](/tmp/sar20_sarpp_133342_map/readback.json) 与 [回读脚本](/tmp/sar20_sarpp_133342_map/read_actual.py) 得到的五案配置、34条关键边和 ID4 记录；没有对模型进行重仿真。原生回执而非本 Python 回读负责根输出 dataset 的同 ready 对应核验。

## 图中实体与状态

- `SarPP/EventStep` 是仿真事件容器。其下 `Adc`、`Transport`、`Fpga`、`BankOwner` 与 `BankOwnerState` 是同级，**BankOwner 不在 Fpga/Calibration 内部**。Adc 是片内行为模型，Fpga 与 BankOwner 是片外数字处理；`Transport` 是片内TX/片外RX统一协议行为容器，不能当成 LVDS 电气或 CDC 签核。
- `Record` 和 `RecordReady` 是两个实际 switch；该案 RX on 时分别选 `Transport.RxRaw` 和 `RxRawReady=Ready3(2)`，OFF 时分别选 `Adc.Raw` 与 `Adc.Ready`。Raw6 是 `[D1,D2,DT,id,epoch,input_valid]` 的模型行为向量，ID/epoch 不是额外的对外物理引脚。
- BankOwner 的10入/4出已由封存源和实际图确认。`BankOwnerState` 是唯一 64 字 UnitDelay 状态，y1 是旧态、BankOwner.y1 是待提交 next；**两个预装 h 槽属于只读 P/绑定参数，不是64字内的两组完整系数**。BankOwner 和已有 Train collector 的责任不同；本案 Train/Frozen均 off。
- `PinTransport.y7 → Transport.RxFault → BankOwner.u7` 是实际已连 fault 路径，回执仍明确 **fault 注入未验证**。`NoDrainAck=zeros(7,1)` 是真实存在的常量接 u10，不是已接消费端确认，也没有实现 drain/安全退休。
- `BankOwner.y2/y3/y4 → PublicCode/PublicValid/PublicMeta → 根 Code20/CodeValid/CodeMeta`；CodeMeta[9] 顺序为 `[hit,time_s,id,epoch,input_valid,slot,version,fault,command_status]`，`CodeValid` 与 Meta 中的 `input_valid` 分别表述。bank off 的代码直接透传 Fpga、该新根 CodeValid=0 是禁用 bank 的输出合同，不能读作 ADC 一定 invalid。

## 五份实际 P

每案 N=8、first_id=4、epoch1、Train/collector off、18片 τDAC=0、DAC耦合 off；模型、参数和 simout 的 SHA 均按各自回执核对。下表是否开启只描述该案，不能把它们混成同一次仿真。

| 已保存案 | transport | bank | 旧 frozen | 前端失配 / DEM / dither | 参数 SHA 前缀 | 模型 SHA 前缀 |
|---|---:|---:|---:|---|---|---|
| factory_base | off | off | off | off / off / off | `d7e54720e412` | `e45b5efcb585` |
| factory_off | off | off | off | off / off / off | `acae36f2c6cb` | `65c346a4a302` |
| rx_nominal | on | off | off | on / on / on | `f312380c0335` | `a28e19949cec` |
| rx_old_frozen | on | off | on | on / on / on | `222cfbe5c55a` | `2e61f3f21a34` |
| rx_bank_on | on | on | off | on / on / on | `68b68d2e2d9a` | `82ede85bdc7c` |

rx_bank_on：Fs=5 MS/s、fin=90.33203125 kHz，AZ/kTC/jitter off；两个版本槽 1/2 的 cache 实际相同。**保存的 SarPP 的 EventStep 说明仍写 `transport=false`、DEM/dither off，与该案保存 P 不一致。** 这些陈旧图上文字不是该案配置证据；本图与表取 P，并不修改旧 SLX 文字。

## 一条真实记录与范围

保存的 on 案中，hit147、0.600 µs 的 `BankCommand` 对 slot2/version2 登记 activation ID4，RecordReady=0，输出 meta 的 command_status=1。ID4 在 1.338 µs 到达 RX raw_ready：实际 Raw6=`[1878,3291,213,4,1,1]`，对应 code log `957226`、BankCodeValid log `1`、meta=`[342,1.338e−6,4,1,1,2,2,0,0]`。根端同 ready 的对应由原生回执核验。共12个实际 RX ready，包括 ID0–3 预热与 ID4–11 八个目标；两槽同一 h，只证明本例版本路由及对旧 Frozen 的码对照，**不证明两个独立训练出的版本**。

原生回执还报告显式 bank-off 30 路日志与对照逐位相同，以及 Bank-on 除 `code_log` 外 29 路与 RX 名义案逐位相同。它明确未覆盖：无 bank 字段的旧工厂入口兼容、后台训练/动态装载、真实消费端 drain/退休/槽复用、fault 注入传播、根非 ready 保持或下游时钟合同以及 N256。输出 `CodeValid=1` 仅对这条受控行为仿真记录，不是商业或硅片接受。
