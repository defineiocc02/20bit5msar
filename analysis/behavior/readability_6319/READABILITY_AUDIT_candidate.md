# 6319 主图可读性审读及标准块替换建议

**结论：** 当前问题主要在层级的呈现、端口语义和纯路由包装，并非缺少模拟状态。建议先修图注和过期注释；任何 S-Function 替换应另建可比较候选，不能把静态审读当作已完成改图或数值等价。此文件不修改主图或参数。

## 实际图证据

现行 `current/models/SarAdc.slx` SHA256 是 `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`；[导图 metadata](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/metadata.json>)声明同一 SHA，导图时读取保存的 ModelWorkspace P，没有运行仿真。本次读取 SLX XML 和导出图，只确认文件/图示结构及对应的源码语义。

| 真实层级与图 | 当前可见问题 | 修订建议 |
|---|---|---|
| [Top](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/Top.png>)：`SarAdc/EventStep` | 一个很大的 Triggered 容器显示极小内容预览，输入是 `SineCfg/Event/ActualTime`，主结果经内部 ToWorkspace；初看不知片内/片外边界。 | 缩小容器、关闭不可读的内容预览，注明它是事件调度边界；标注 `SineCfg` 为四项源配置、`Event` 为 ID/组号、`ActualTime` 为真实时钟。不要把外容器画成 ADC 芯片。 |
| [System](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/System.png>)：`EventStep/{Adc,Transport,RefQueue,Fpga}` | 端口名在 Adc、Transport、RefQueue、Fpga 的小块上明显相互压住；很多长连线穿过同一视区。`Adc.Ready` 与 FPGA 前的 `RecordReady` 名字相近但来源不同。 | 以 `Adc → 直通/Transport → Record/RecordReady → Fpga` 排主线，TrainRef/RefQueue 与日志各走独立辅助区；加高块并在端口旁写 `ADC RawReady` 与 `FPGA RecordReady`，保留三类 RX ready 的原义。仅变更显示文字须保持原连线与执行使能。 |
| [ADC](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/ADC.png>)：六阶段加 Diagnostics | 阶段块显示微缩内容而端口多，`ChargeReturnRaReset` 在下方回接形成长线；缩写混合了 state、obs 和 command。按图形大小难辨依赖及唯一状态。 | 关闭阶段内部微缩预览或减小占比；在块外以短注释标 `state/obs/cmd`、尺寸和单位；以可读的反馈通道回到原 UnitDelay。布局按事件依赖排，并标明三个 Delay 是两份模拟状态加一份控制状态。 |
| [SampleRaAdvance](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/SampleRaAdvance.png>) 等子层 | S-Function 图标内函数名被裁切，`FE_old`、`RA_adv`、`RA_obs` 没显示宽度；RaAdvance 与 RaPreLog 文本挤在一起。 | 适当加宽核块，保留其原 `FunctionName/Parameters`，用块旁注释说明物理职责。`FE_old → RaAdvance.u4` 标为只读旧 FE353；`RA_adv` 是 state48，`RA_obs` 是 obs8（反馈前）。 |
| [Transport](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/Transport.png>) | `PinTransport` 在一个函数中实现 TX、pin-only RX 和 97 字数字状态；图上没有单独的可连线 TX→RX 模块接口。 | 明确标注此容器当前为联合协议核，`TxRxState` 是数字记忆；`PinTrace` 是诊断输出。若未来要画成真实两块，需另行设计/验证接口，不能用说明性箭头冒充现有物理连线。 |

### 容易误读的真实端口

| 当前名称及源 | 真实含义 | 建议显示名称或旁注 |
|---|---|---|
| `SampleRaAdvance/FE_old` = `SampleCharge.y1` | 353 字 FE 旧状态；同一线送 `Sample.u1` 与 `RaAdvance.u4` | `FE_old_state353` |
| `SampleRaAdvance/RA_adv` = `RaAdvance.y1` | 48 字 RA/CT 推进候选状态 | `RA_advanced_state48` |
| `Sar1TrialRaCt/RA_cmp` = `RaAzCt.y2` | 八项模拟观测 `[VX,VY,Vtop,target,NG,tau,AZdiff,resetVX]`，不是布尔比较位 | `RA_pre_decide_obs8` |
| `DacCtFeedback/CT_due` = `CtFeedback.y1` | 48 字**同一 RA/CT**状态，而非单个 CT 电压 | `RA_CT_due_state48` |
| `ChargeReturnRaReset/FE_return` = `ReturnContext.y1` | 六项 `[time,ID,epoch,event,D1,Vtop]` 返回命令；`FE_next` 才是 353 字下一 FE 状态 | `ReturnCmd6`；保留 `FE_next_state353` |
| `Adc/Ready` 与 `EventStep/RecordReady` | 前者来自 ADC，后者按 transport 选择 ADC ready 或 RX raw_ready | `ADC_RawReady` / `FPGA_RecordReady` |

名称是建议的显示文本，不是允许直接改信号名/端口的指令。真实改名可能影响以路径或名称查找的脚本、日志和导出；先核依赖。不要把这些 packed double 向量直接改为新 Bus ABI，除非单独设计、编译和等价验证。

## 纯包装可替换的范围

以下是根据 `behavior_wiring_sfun` 和 `behavior_pol_sfun` 静态推导的**可行候选**，尚未在 R2024a 实际编译或做运行等价。标准块具体能力可查 MathWorks R2024a 的 [Selector](https://www.mathworks.com/help/releases/R2024a/simulink/slref/selector.html)、[Math Function](https://www.mathworks.com/help/releases/R2024a/simulink/slref/mathfunction.html) 和 [Assertion](https://www.mathworks.com/help/releases/R2024a/simulink/slref/assertion.html)。

1. **首选 `SarDecisionTracking/RawWords`（SID 345，`behavior_wiring_sfun('raw',P)`）**：当前只将 Control13 的索引 `[5 6 7 9 10 8]` 排成 Raw6，并把索引 `4` 输出为 ready。用一个固定索引 `Selector` 生成 Raw6、另一个 `Selector` 取 ready；保持 double、尺寸、direct feedthrough、原输出顺序和采样/使能。无需新状态或计算真实码。
2. **`SampleRaAdvance/Time`（SID 323，`'clock'`）**：当前计算 `event(1)*P.Ts_s + P.groups(event(2)).time_s`。可用 `Selector`、`Constant [P.groups.time_s]`、按 event(2) 的动态索引、`Gain` 和 `Sum` 表达；保留一基组索引、48/49 组配置、原 double 乘后加顺序及错误边界。该时间仅替换此 ADC 组计算，**不能**替换 transport 的真实 `ActualTime/Clock`；transport 核明确核验 CurrentTime。
3. **`Fpga/PublicPol`（SID 215）与 `Diagnostics/AzPublicPol`（SID 359）**：前者用 `DecodeP.az_mode`，后者用 `P.digital`。其仅由公开 ID/epoch 和 mode 得到 POL；理论上可用 `Math Function(mod)`、常量 `[1 -1 -1 1]`、`Selector` 和 `Switch` 表达 chop/hold_chop，其他三种 mode 为 +1。原函数还校验两项标签均为有限、整数、0…2³²−1 且 mode 合法；如用 `Assertion` 必须确保模型配置不禁用该检查并保留错误边界，不能只做数值查表。

`CaptureContext/DueContext/TrialContext/ReturnContext` 和 `DueCharge/RaCommand/ResetCommand` 虽无持久状态，但并非无条件拼线：它们查询实际组事件、执行 AZ 排程与极性、处理 release 的零值和返回坐标。可以研究 `Selector/Switch/Mux` 透明化，但须保留原事件顺序和全部条件，不列入第一轮等价替换。`ResidueCtCompare` 已采用 Selector、Relational Operator、Data Type Conversion 和 Mux；FPGA 名义算术已大量使用 Gain/Sum/Rounding/Saturate，无需重复包装。

`behavior_frontend_sfun`、`behavior_backend_sfun` 和 `behavior_control_stage_sfun` 虽是纯 Outputs，却实现电荷、解析建立、CT kick、状态推进及事件判决；不可因“无 DWork”将它们认作简单包装。继续以 `SampleCharge`、`RaCtState`、`SarState` 为唯一片内状态 owner；Transport/RefQueue 的独立数字/仪器状态不属于新增 ADC 模拟状态。

## 注释修订和验证边界

当前 `current/src/model/behavior_dac_coupling_configuration.m:3–4` 仍写 candidate 和旧的 prepare finite-DAC rejection，而现行 `behavior_prepare_configuration.m:66–74` 在 FE 规范化后实际调用绑定。建议仅将前者换为：

```matlab
% Called by prepare after FE normalization; binds enabled, tau[18], schema and public plan.
% Does not alter FE tau/state, the graph or the event calendar.
```

`behavior_backend_stage.m:11` 与 `behavior_backend_step.m:19` 的 `Candidate` 也已过期，可改为说明 old-FE 的只读 forcing 及 RA-on、非 reset 条件；不改变函数体。

若之后实施：先保存原 SLX/参数/源码身份；图形修改核对实际连线、触发/enable、UnitDelay 初态及 logger。替换路由核则用同一 P 和事件在 N8 下比较完整日志的时间、尺寸、数据位（包括旧态、三份下一状态、Qres/RApre、RAW/ready、code），覆盖 τ0/有限 τ、AZ off/hold_chop、transport off/on 和实际 48/49 事件，并单独测无效标签/索引拒绝；同时检查 snapshot 及探针。上述是建议的验收，不是本次已运行的门。需要动态性能结论时再单独跑所需 N256；不因图像好看或 N8 功能相同声称频谱通过。
