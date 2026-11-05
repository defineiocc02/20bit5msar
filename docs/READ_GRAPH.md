# 按一个sample读主图

同一主SLX已接入LVDS与有限DAC→RA耦合；默认N8、transport off、DAC τ=0。[Windows ADC分层图](../analysis/behavior/current_diagrams_20261104/figures/Adc.png)与[metadata](../analysis/behavior/current_diagrams_20261104/metadata.json)对应 `d4e7fc99…` 私有副本，并非Mac本地 `f358f226…` 的模型截图；当前运行状态见[检查点](../CHECKPOINT.md)。

## 当前有限DAC主图的ID5：同一模拟记忆如何传播

[τ=0与1ns实际对照](../runs/az_probe_20261028T093124Z/ID5_COMPARE.md)使用同一输入、18片选片计划、事件日历和公开RX路径，两次均在N8打开只读RaPre探针。ID5的D1/D2/DT均为1932/2907/85，最终整数码同为979654；这只说明这个样本没有跨码门限。实际前端日志在本次CNV后12.5ns首次不同。`RaAdvance`预反馈8项在CNV已有位级差，但VX仅差2.76×10⁻⁵⁵V，是上个样本状态经复位衰减后的数值尾迹，不应误读为本次DAC切换造成的可观测RA误差；这一跨样本解释结合保存的1ns复位参数和源码推断，未记录完整已提交后端状态。到43.75ns，实际VX/VY差分别达到−4.648mV/−3.619mV。控制与事件日志在ID5的48组中完全相同。[VX/VY实际节点图](../runs/az_probe_20261028T093124Z/id5_ra_compare.png)显示有限建立改变了RA/CT轨迹；对256码频谱的影响见[本次动态结果](../analysis/behavior/RESULTS.md)。

读图从 `SampleRaAdvance` 的 `FE_old`（唯一前端UnitDelay旧态）到 `RaAdvance` 第4口开始；`RaPreLog`从其obs8分支读取，位于CINC反馈/kick和后端UnitDelay提交之前。前端 `Sample` 产生下一候选状态，RA侧不另存第二份DAC记忆。沿 `DacCtFeedback`、`SarDecisionTracking`、`ChargeReturnRaReset` 继续检查反馈和返还；数字输出按同ID/epoch的RX record读取。当前`SAR20('sample')`尚不自动将RaPreLog并入逐级说明，需同时查看上述两份实际run和对照表。

[独立逐事件复核](../analysis/behavior/finite_dac_review_20261028/ID5_093124_REVIEW.md)把RA关断时由target推算的Vtop与真正VX分开；18.75ns的59.65mV最大Vtop差不能称RA输出建立误差。ADC RawReady与RX Ready也分别标记，不把两条时间线合并。

先理解行为，再展开实现。每一级只回答三个问题：**收到什么、如何改变信号、保留什么记忆**。当前图的六个子系统按事件计算顺序分组，尚不是理想的电路功能视图；不能把 `RaAdvance/RaAzCt/RaReset` 当成三台放大器。

| 物理过程 | 行为关系与保留的状态 | 出现异常时先看什么 |
|---|---|---|
| 采样 | 输入通过有限建立得到电容电荷；capture锁定本次初值，下一轮仍使用返还后的同一电荷 | 捕获held、ID/epoch、片选；先查输入/采样，再查量化 |
| 六位预转换、SAR1、DAC1 | 粗码选择区间，细SAR逐次切电容；真实电荷差形成残差 `Qres`，不是 `理想输入−理想码` 旁路 | D1 trial、比较符号、实际Qres；交接异常先看粗/细区间边界 |
| RA/AZ | `target=Qres/Cf`；有限增益系数 `F=A0/(A0+NG)`，`NG=1+Ctop/Cf`；单极点向目标建立，AZ保留写入/泄漏记忆 | target与VX：比例偏差查A0/Cf，来不及建立查UGB，奇偶差查AZ写/保持 |
| CT、SAR2、Tracking | 实际VX驱动CINC电荷关系得到VY；真实比较产生12次D2与8次TA，反馈仅7次；切换反作用于同一VX | VY逐次符号、反馈前后变化、D2/DT原字；RA后没有新增S/H |
| 数字重构 | 默认走名义D1＋解调D2/DT＋公开dither加回；显式冻结模式用同一RAW的`(u+Bh)/den`，再round/saturate | 先核saved P与used；冻结最终电压看actual diag9，原四项只作名义对照 |
| 返回与下一轮 | release返还真实Vtop对应的电荷，信号reset按原规则处理，AZ保存状态不一并清空 | release命令与下一次采样；不能创建一套独立“理想初值”覆盖残留 |

行为模型只在已定义的事件端点推进解析RC/电荷关系。比较器、采样时刻、反馈延迟和舍入是可观察行为，必须保留；晶体管内部节点、细网格积分不是本工程的目标。A0、UGB等未披露值是设计假设，改变它们应产生可解释的误差变化，而不是自动重调数字码权。

**最短调试流程：** 在参数工厂改一个物理量 → `SAR20('apply')` → `r=SAR20('run')` → `SAR20('sample',4,r.run_path)`。先看held，再看D1/Qres，再看VX/VY，最后看RAW和数字贡献；首次偏离预期的位置比最终SNDR更能定位原因。不同实验始终显式传run路径，避免把最新静态测试当作上一轮正弦记录。

从`SAR20`打开唯一主图；先看图上的**已应用P**，不是参数工厂文本。无参apply读取工厂，`apply(P)`应用完整显式配置；GUI Run使用当前模型 Workspace，通常是保存的P，但可能包含手改；它不重新apply，也不执行入口run的一致性检查或run目录/摘要封存。外层`Driver`提供正弦配置，`Calendar`提供事件；`EventStep`保留原Triggered边界，内含片内`Adc`和片外`Fpga`。以下以`A=SarAdc/EventStep/Adc`、`F=SarAdc/EventStep/Fpga`缩写路径。

六个子系统是**同一组状态在一次事件内的计算阶段**，不是六套电路，也不是四个独立RA；RA推进、反馈kick、trial端点和reset先后变换同一份`RaCtState`。先按旧命令推进至事件端点，到期反馈按顺序提交；符合启用条件时，CT切换对同一 `VX` 产生kick。`VY` 参与判决，12次D2、8次TA比较中只有7次TA物理反馈，最后按实际 `Vtop` 返还电荷。颜色只辅助定位，不能据此断言每组只承担一种物理职责。

| 依赖顺序与路径 | 打开后看哪些实际块 | 核心参数/接口 |
|---|---|---|
| 1 `A/SampleRaAdvance` | `Sample`负责采样/切组；`RaAdvance`推进旧RA/AZ命令 | `P.front.plan`为片号表，`C_f/Cp_f` [F]、`tau_sample_s/tau_precharge_s` [s]；`SineCfg` [V,Hz,rad]；RA用旧命令推进到当前事件 |
| 2 `A/DacCtFeedback` | `DueFeedback → DacFeedback → CtFeedback` | 先提交到期SAR反馈，再更新DAC1残差和CT开关；物理顺序取`P.adc_groups`（旧off为`P.groups`），D2/TA符号保持负反馈坐标 |
| 3 `A/Sar1TrialRaCt` | `PreconvertSar1 → DacTrial → RaCommand → RaAzCt` | SAR1粗判决/细位trial；`P.control.sar1.delta_v` [V]；RA的`A0` [1]、`UGB_hz` [Hz]、`Cf_f` [F]；AZ mode/write/leak参数；整Qres只换向一次 |
| 4 `A/ResidueCtCompare` | `Compare1`看DAC1实际残差，`Compare2`看CT实际VY | 与0比较；SLX XML未显式保存Operator，零点规则待原生核验。不以最终理想码替代判决；这里只提供比较位，不另存模拟状态 |
| 5 `A/SarDecisionTracking` | `Sar2Tracking → RawWords` | 12次D2、8次TA比较、7次实际TA反馈；D1/D2/DT是11/12/8位raw整数。`Adc.Ready`是早RawReady，不是FPGA的record/RXready |
| 6 `A/ChargeReturnRaReset` | `ReturnContext → ChargeReturn`，以及`ResetCommand → RaReset` | 先将local vtop用同POL恢复到前端坐标并返还电荷，再提交信号reset；`P.backend.ra.tau_reset_s` [s]。RST_SIG不清AZ存储 |
| `A/Diagnostics` | AZ final-next与route探针，输出`az_commit_log[8]`、`az_route_log[6]` | 仅观察：final-next是UnitDelay输入、待锁存；route含实际Qres/返回vtop，POL是公开规则派生值。不得回接物理/控制路径 |

**观察阶段不同：** `Frontend` 接 `ChargeReturn/FE_retobs`，是返还计算阶段的前端观察，仅在 release 事件实际返还；`Backend` 接 `RaAzCt/RA_cmp`，是比较前的后端观察。两者可以属于同一事件时刻，但处在不同计算阶段，不能当成同一提交阶段的成对终态；同时查看相应阶段与状态Delay。顶层 `CodeValid` 是 Bank 路径的逐帧资格标志，Bank OFF 时即使名义码旁路输出它也为 false，不能当作所有输出码的通用有效标志或产品验收；应结合实际 record 的 valid、ID/epoch 等字段。

**ADC内只找三个状态owner：** `A/SampleCharge[353]`保存18片分组电荷/采集标签：旧317字不变，追加18片实际孔径[s]与18片实际开采时刻[s]；`A/RaCtState[48]`保存唯一RA输出、AZ、CT电荷和区间命令；`A/SarState[51]`保存trial、判决与pending反馈。它们仍是原标准UnitDelay；Calendar按绝对时间查询不可变日历，不保留DWork或随机数状态。各stage输出是下一状态候选，最终经过这三个Delay才供下一事件使用。`Backend`探针在decide/reset前，不能当成最终已提交状态。片外TrainRef的CNV锁存、Train的数字收帧buffer/fit snapshot属于仪器与FPGA记忆；Transport与RefQueue也各有数字/仪器存储，不增加ADC模拟状态。

**FPGA沿`F`读：** `D1CaptureBias`支路＋`D2InputReference/D2Demod`＋`DTInputReference/DTDemod`＋公开dither，最后求和、round、饱和为code20。系数在`P.digital`，只解调CT项，D1原码和数字dither加回支路不翻。名义几何变化须同步名义码权/尺度及固定DAC1公式，单改`nominal.mat的几何`不会自动全量推导。名义码送入`F/Calibration/NominalCode`；`Calibration/Train`收集训练但始终直通名义码，随后`Calibration/FrozenDecode`按显式配置选择冻结候选或原样旁路。当前同一SLX以`P.transport.enabled`选择直出或TX/pin-only RX；默认off，开启须apply。读取以实际record为准，不从原直通码支路借答案。

**训练与冻结沿实际边界读：** `SarAdc/EventStep/TrainRef`是片外理想训练源，虽在Triggered容器内，仍在`Adc`外；参考误差为0是本次试验假设。它在CNV锁存`Ref4=[Vdiff,ID,epoch,valid]`，off在ADC RawReady配对；on由外部参考队列在RX时按同ID/epoch提供pairedRef，不能在RX重新取即时正弦或ADC节点作参考。`F/Calibration/Train`仅用公开RAW/Ref收帧并提交一次拟合；`FrozenDecode`只消费预先锁定的公开配置与h，不读actual C，也不在holdout重新拟合。默认training/frozen均off。

**一个冻结sample怎么查：** 先看解释页的capture/D1/RA/CT/return，按12次D2、8次TA表找首次异常；再核saved P的`frozen.enabled`，并按实际record-ready及同ID/epoch取`frozen_log`的used=1行。冻结表中的u和canonical Bh均为RA域V，den无量纲，最终输入参考电压直接取diag9；`V=(u+Bh)/den`，`code20=clip(round(V×2^20/(2Vref)+2^19))`。h哈希来自保存cache。diag2:6分组仅为诊断，不能替代canonical Bh再相加dither；旧D1/D2/DT/dither表仅为名义对照。独立record CSV保留actual D1/D2/DT/code及u/Bh/den/voltage/used；物理nodes CSV仅保留ADC观察，缺日志不补造校准结果。

旧直通RAW路径已完成[2048帧训练](../runs/behavior_30bb3ff5-8668-4149-a3c5-1ca5d6dabed7/training.json)与[预注册1024帧holdout](../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/holdout.json)：holdout电压RMS=2.6503µV、最大误差=7.9906µV，实际冻结码SNDR=117.7364dB。仅对应本颗固定失配芯片、DEM/dither on、有限RA、AZ/kTC/随机噪声关闭；不是完整论文复现，也不代表所有非理想或LVDS校准验收。复跑方法见[参数入口](PARAMETERS.md)：正文仅保留SAR20的“重新训练”与“复用已有训练”两套workflow用法；公开freeze/evaluate已原生通过，1024帧RAW/code与此前holdout逐位一致。保存P重放仅作已有证据复核。

**按两条时间线定位：** 先看N的48组ADC事件，RawReady约+86.25ns、release +90ns；再看解释页的同ID/epoch实际record列，transport on通常+538ns，off仍为直出时刻。parent第49组+138ns只做传输收槽，Adc held不推进；不能给AZ/tap补一行或把RX当新的模拟端点。无效/缺失/重复record与NaN明确展示，不能valid过滤后假称完整；三种接收ready见参数表。

实际[RX on ID5](../runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_explain.md)的CNV=1µs、ADC Ready=1.08625µs、RX=1.538µs，code979654；[record CSV](../runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_record.csv)与物理nodes分开。先定位held/D1/Qres/VX/VY，再对照这条实际record，别把RX时刻当模拟新端点。

**训练末态：** 最后Outputs与finalOP可能停在末Update之前，OP只作诊断。Terminate只读已提交的4组Train DWork写`training_committed.mat`，不新增事件/fit/Outputs写；历史[011012证明](../runs/az_probe_20261027T011012Z/receipt.json)与N8结果核8条/fit一次后的欠秩拒绝。当前主图又完成[2048条RX实际训练](../runs/behavior_a27903ef-c1c6-4e5e-b487-d2c1d468efef/summary.json)、显式冻结和[新预登记1024条RX holdout](../runs/az_probe_20261028T102427Z/receipt.json)，固定条件下按原误差门通过；旧直通RAW长校准是另一份历史原件。两条路径都不自动激活bank，当前RX系数仍`NOT_ACCEPTED`。按同ID/epoch取实际RX ready后的公开RAW/Ref，再看冻结诊断及最终code，不把ADC RawReady当FPGA收到帧。

**N256池与I1：** 2026-11-04 的 N256 实际保存配置使用 18/8/8/2 池；DEM OFF 仍有池选片，264 行里片17/18各出现118/114次。固定A/B的 I1 是未部署隔离候选，已有函数级测试，尚无 I1 整图/频谱验收；历史 I2 频谱不能当成 I1 结果。详见[候选说明](../analysis/behavior/i1_ab_candidate_20261104/README_CANDIDATE_v4.md)；该说明早于函数实测，进度以[检查点](../CHECKPOINT.md)为准。

**看池/DEM/dither：** Diagnostics中的AdiWireTap只读Sample、DacTrial、SAR状态和RA命令，不反馈物理网络。默认只存一行NaN；专项N8开启`P.debug.adi_enabled`后，sample解释给出CNV实际8片ID及tail电荷、首次hasDAC的shift/目标/physicalD1。这里的physical slice ID与样本sample ID不同；首次physicalD1也不等于最终D1。可直接看[ADI＋AZ联合ID5](../runs/behavior_90c97b0c-9945-448a-867e-2735d45c02cf/sample_5_explain.md)。

**看真实孔径：** `P.front.jitter`只定义signal端点孔径：公共RMS按seed/ID/epoch取值，局部RMS再按物理片号取值，固定skew也属于物理片。名义Calendar、SAR比较/反馈及tail/bias预充时刻不移动；不是全时钟抖动。充分建立下的signal电荷在实际孔径评估，同一SampleCharge仍是唯一前端记忆；finiteRC+jitter拒绝。注册静态校准bench也拒绝jitter on。

默认`P.debug.aperture_enabled=false`不生成物理孔径表。专项N8开启后，`SAR20('sample',5,r.run_path)`读actual CNV的Sample.next353，解释页与`sample_5_aperture.csv`显示8片实际ID、孔径/开采绝对秒及相对CNV ps；非CNV行NaN不是新捕获。已通过[六例主图及重复位门](../runs/az_probe_20261026T233611Z/receipt.json)，[联合ID5](../runs/behavior_2b9d513a-14ba-4073-af20-61c3906f612b/sample_5_explain.md)实际孔径偏移−79.1280…−42.2870ps（common/local RMS=25/10ps，最大固定skew=8ps）。这是N8行为/取数核验，不预报N256频谱或统计独立性。

## 历史默认物理条件的样本入口

打开[历史τ=0 N8的ID5解释](../runs/behavior_3cc384a0-3678-4709-8beb-cded2b86023c/sample_5_explain.md)，从六阶段摘要开始，再按12次D2/8次TA表检查VY与该行原始判决，最后看D1/D2/DT贡献及code20=979654。使用 `SAR20('sample',5,r.run_path)` 会为自己的实际run生成同样的解释、图和CSV，不需要读计算核源码。

这是默认AZ/kTC关闭、有限RA的调试例；下面的AZ压力例保留用于理解保持泄漏，不能混为同一配置。

## AZ压力例ID5为何是979624：有意开启保持泄漏的记录

例图来自`runs/behavior_1328fbfe-b77d-4573-88e2-610959d08b3a/sample_5_az.png`及同名nodes CSV：**N8、hold_chop、Vos=1mV、AZ write tau=8ns、leak tau=1µs、kTC关闭**。它不是N256 FFT配置；已有FFT记录`behavior_f4da0fd7-e1a3-47d4-bfb5-a2f9dfc504e7`为write tau=1ns、leak=Inf、kTC在298.15K开启。该N256已经在最终分层主图复跑；不能用这张stress图替代其性能记录。

1. **采样与AZ标签：** ID5/epoch1在1µs捕获，held为3.55756491800524V；pair2、POL=−1。它复用ID4的AZ，write_count整帧保持3，没有奇服务重写。AZdiff由CNV时839.403µV泄漏到RawReady时770.039µV，这不是理想保持或随机AZ噪声收益。
2. **SAR1与模拟闭环：** trial/比较得到D1=1932（coarse=60、fine=12）。RawReady时原Qres=+1.51095955536257e−13C，实际送RA为其负值；有限RA/AZ/CT推进后的VX=−0.169799121782364V。图中local vtop与返还坐标分开，只有90ns release才消费返回命令。
3. **D2/TA与数字恢复：** 86.25ns RawReady处D2=1195、DT=218；经过实际12/8/7日历及POL解调，日志支路为D1=3.552V、D2=+0.005328125V、DT=−0.000015625V，dither=0。不能将raw整数直接相加。
4. **最终码：** `Vhat=3.552+0.005328125−0.000015625=3.5573125V`；FSR=8.192V，所以`code20=clip(round(Vhat×2^20/8.192+2^19))=979624`。这是已记录支路的贡献恒等式，不是独立外部reference或精度验收。

**当前限制与证据：** Windows `d4e7fc99…` 图像的[导出metadata](../analysis/behavior/current_diagrams_20261104/metadata.json)标记待独立视觉复核；模型以实际SLX文件为准，导出和行为位门不等于视觉验收。历史分层的58块/102边及12日志位门属于原分层验证；本次LVDS以[011447回执](../runs/az_probe_20261027T011447Z/receipt.json)和[RX N256位门](../runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/transport_validation.json)为准，不能跨配置继承性能。
