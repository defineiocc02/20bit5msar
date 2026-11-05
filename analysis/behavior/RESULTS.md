# 当前实际行为结果：动态、局部静态与调试

本页保留2026-10-28的Windows MATLAB R2024a历史实验，并在下方补充2026-10-30的Bank接入与N256结果。唯一工作入口为SAR20.m，历史模型与as-run源码保留；实际当前状态见[检查点](../../CHECKPOINT.md)。

[2026-10-28 SHA6319历史导图](current_figures/metadata.json)含顶层、ADC六阶段、FPGA、Transport与校准层，早于Bank接入；[ID4单样本导览](designer_map_20261028/id4_designer_map.png)按112407保存的N1/DC原始日志说明一次码为何为524285，图是阅读辅助，不冒充修改后的SLX界面。[导览说明](designer_map_20261028/README_PROJECT.md)区分实际日志、待提交状态与由RAW/P重算的名义贡献。最新图形仍有连线拥挤问题，视觉整理尚未验收。

## 2026-10-30：主图Bank接入及受限N256

Bank A/B行为路由已接入唯一主图，工厂默认OFF。[预登记三案](n256_20261030/RESULTS.md)在同一固定行为芯片、RX、M8、τDAC=0和失配/DEM/dither开启条件下，比较名义重构、Frozen和Bank ON；两槽预装同一组h。256码SNDR依次为101.296943、116.867326、116.867326dB；Frozen与Bank ON的256个整数码逐位一致，Bank在ID4由版本1切换至版本2，记录fault为0。实验条件、各自原始run和频谱见上述结果页，[三案控制回执](../../runs/work_20261030T141338Z/receipt.json)保存实际功能门。

这些结果只支持已测条件下的同h版本路由，不证明不同h切换、后台训练、真实drain/槽复用、根非ready行为或产品校准验收；资格保持`NOT_ACCEPTED`。主图已通过apply/check恢复工厂OFF，但恢复后尚未再做OFF仿真。Bank ON复跑绑定资格、完整P、plan及源码，历史P中的资格文件路径是当次Windows临时绝对路径。[公开sample入口](../../runs/work_20261030T151254Z/receipt.json)已在复制run的ID4读取Bank valid/slot/version/fault，实际码587978、名义对照587981；Bank内部`u/Bh/den`及最终电压未记录，sample本身不验证simout的可信哈希。使用时应复制完整run并显式传副本路径，避免覆盖历史产物；具体边界见[参数表](../../docs/PARAMETERS.md#bank-行为路由与复跑边界)。

## 历史：A/B 预资格路由隔离图 N8（2026-10-28）

[133342 原生续跑](../../runs/az_probe_20261028T133342Z/receipt.json)从两次失败时保存的 SATK partial **新副本**完成终检和实际 N8 仿真；原失败回执/模型均保留。显式 `P.bank.enabled=false` 的工厂 OFF 两图先跑，旧30路 Time/Data 逐位一致，根输出 OFF 门通过；随后六项实际 Simulink update 对伪造资格、改CT参考、非M8日历、缺来源及有限/Inf DAC τ 均按预期拒绝。RX nominal、旧 Frozen、Bank ON 三案保存各自 P/DecodeP、SLX、simout 与源码清单。[独立原件回读](bank_owner_20261028/sar20_independent_133342_REVIEW.md)核五案身份、OFF30/ON29原始Time/Data位、12个RX ready及同ID/epoch的根Code/Valid/Meta；ID0–3为slot/version1/1，ID4–11为2/2，Bank码均与旧Frozen相同。六项异常拒绝由原生回执及断言源码复核，未重跑。外层回执核主模型文件及公开工作区、RNG、path/cwd、任务副本/候选缓存清理；这次隔离验证本身未证明旧无bank factory入口。

五案原生 `sim` 墙钟依次为显式OFF基线9.523s、显式OFF新图6.738s、RX nominal7.738s、旧Frozen8.369s、Bank ON7.960s；各只运行一次且配置不同，**不能用这些数推Bank稳定开销或与用户先前未绑定配置的8码446s作直接速度比**。本次Bank ON也仅N8，没有动态频谱。

[140306干净图默认OFF门](../../runs/az_probe_20261028T140306Z/receipt.json)从旧6319无bank的工厂配置调用候选prepare，得到显式OFF，在全新scratch中用SATK分阶段安装Bank图并实际运行N8；[独立原件回读](pp_main_clean_20261028/REVIEW.md)核新图分别对133342已保存的旧factory base和显式OFF两组30路原始Time/Data位同、实际P/DecodeP/SLX工作区、12条ready与根OFF输出，单次sim为7.269850s。候选的Bank图注更新/陈旧文字拒绝、选中RX有效位与ID/time/version拒绝门由原生回执记账，其中RX门读取133342保存的旧ON原件，不是新holdout仿真。该次未改主图文件/公开工作区；退出清了候选及复制SATK的任务缓存，但不能证明原SATK缓存字节原态恢复。**这次scratch证据本身不是生产`SAR20('apply/check/run')`的真实门**；后续主图接入及受限N256见上节。[布局差异](pp_main_clean_20261028/LAYOUT_REVIEW.md)记录当时SATK将根EventStep缩小并挪动七个旧块，不能仅据此视为视觉验收。

**上述历史证据只限隔离scratch的预资格同h双版本路由。** 后续主图已有上节所述的同h N256功能门；不同h切换、后台Train ARM/ABORT、运行中独立资格、真实drain/槽复用、故障注入传播及根非ready保持/下游时钟合同仍未由这些记录证明。`code_valid`仅针对受控固定行为仿真，不是硬件产品接受。

[物理与数字边界的独立回放](bank_owner_20261028/BANK_PHYSICAL_DIGITAL_REVIEW.md)显示：本次 N8 的 RX RAW/ready 时间与原2048训练run的 ID4–11 前缀逐位相同，故它是**训练条件重放**而不是新的独立holdout。ID4–11的8个Bank码较nominal分别为`+2,−2,+3,−1,+3,+5,+5,+5`码；两槽684h逐字节相同。实际D2/TA判决日志可核，但本案ADI逐次观察器关闭，不能把日历声明的7次物理反馈当作本案逐片已观测证据。

## 2026-10-28 RX 路径：登记训练、冻结与独立 holdout

在当时主图的 τDAC=0 配置中，先于训练写入[预登记协议](../../runs/az_probe_20261028T100042Z/rx_protocol.json)：2048条训练（epoch1/bin37/phase0.731）和新的1024条 holdout（epoch3/bin29/phase2.137），门限沿用原合同。两批使用同一固定失配芯片、DEM和物理dither，外部参考为明确声明的理想源；kTC、AZ、孔径误差及其他随机噪声关闭。

[RX实际训练](../../runs/behavior_a27903ef-c1c6-4e5e-b487-d2c1d468efef/summary.json)收齐2048条公开接收RAW与外部Ref，Terminate只读已提交的Update末态；拟合一次、684列满秩，scaled condition=2242.642，训练RMS=1.757µV，sim=1091.502s。训练期间输出保持名义码。[显式冻结候选](../../runs/az_probe_20261028T102242Z/receipt.json)将h/cfg/公开选片计划与此次训练绑定，状态仍`NOT_ACCEPTED`，未自动激活bank。新测试开跑前写入[一次性消费标记](../../runs/az_probe_20261028T100042Z/holdout_consumed.json)，失败不会以相同登记自动重跑。

[新RX holdout原始运行](../../runs/behavior_dc38bf72-b9b2-42e6-a9d5-6b76a32a671f/summary.json)为Fs5MS/s、Fin141.6015625kHz/bin29、差分峰值3.650563842595822V、phase2.137、ID4..1027/epoch3。1024条实际RX记录全部valid；冻结主输出SNR117.520212dB、SNDR117.458169dB、SFDR136.082773dB、THD−135.940052dB、ENOB19.218965。同一次真实RX RAW的名义数字支路由[独立后验回读](rx_holdout_20261028/independent_attempt1.json)计算出SNDR102.049939dB；它是同输入同芯片数字对照，不是另造理想ADC码。

| 对预登记外部参考的实际误差 | RMS / µV | 最大绝对值 / µV | 事前门 / µV |
|---|---:|---:|---:|
| 冻结重构的取整前电压 | 2.625085 | 7.066347 | RMS≤7.8125、max≤31.25 |
| 实际20位整数码中心 | 3.476645 | 10.093583 | RMS≤7.8125、max≤31.25 |

[评价回执](../../runs/az_probe_20261028T102427Z/receipt.json)记录四门均通过，公开特征独立重算电压最大差1.3323×10⁻¹⁵V、整数码零差；这只检查数字公式，模拟准确性仍由声明参考及行为模型条件限定。该次`accepted=false/activation=none`，并未自动激活Bank；后续主图Bank功能证据见上节。此次也不是独立芯片、PVT、真实参考测量或完整非理想验收。旧直通RAW的2048/1024结果保留为历史，不能与新RX测试混称。

[实际冻结码频谱](rx_holdout_20261028/holdout_spectrum.png)和[1024点参考误差](rx_holdout_20261028/holdout_error.png)由保存的 MATLAB `spectrum.mat` 与公开评价数据绘制；[图像来源回执](../../runs/az_probe_20261028T104734Z/receipt.json)与导出的当前工厂SLX SHA绑定。图上的离散频谱点与误差样本不构成连续时间波形或未测静态INL/DNL。

本轮关键非理想的证据状态按**实现 / 在指定实跑中真正开启 / 已扫描验证**区分；“配置字段存在”不算开启，τ=0、Inf保持负例、幅度0和关闭项不算有限误差覆盖：

| 效应 | 实现 | 本轮实际开启 | 本轮扫描或范围 |
|---|---|---|---|
| 采样kT/C、输入有限建立 | 有；联合模式受限 | 上述DAC频谱和RX holdout均关 | 当前有限DAC条件下未扫 |
| 前端失配、DEM、物理dither及数字抵消 | 有 | 新RX训练/holdout同一固定芯片开启 | 本轮是同一芯片的训练/独立输入验证；更多seed/梯度未扫 |
| 固定CINC输出寄生负载 | 有，0.5pF/half设计假设 | 本轮动态开启 | 未扫描负载幅值 |
| 孔径偏斜/公共与局部抖动 | 有充分建立采样端点模型 | 本轮DAC与holdout记录均关 | 先前主图有短记录/256码对照，当前联合条件未扫；全时钟抖动未实现 |
| DAC切换有限建立 | 有18片解析耦合 | 0.1/1ns N256、mixed18 N8开启 | 同图off/0.1/1ns相干谱及mixed/近极点N8区间核验；Inf仅保持负例 |
| RA有限增益/带宽、失调、slew、AZ | 有；噪声未实现 | A0=1e4/UGB1.2GHz开启；mixed N8另开Vos1mV/AZ；slew=Inf关闭 | DAC/RA/AZ区间短门已验；本轮无A0/UGB/slew/AZ多频谱扫描 |
| 参考负载与恢复、比较器随机噪声/再生/超时 | 未接入；仅粗比较器固定偏移字段 | 否 | 无；不能用`P.ni`手改或限幅标志冒充覆盖 |
| CT/replica实际失配 | 有参数路径与CINC kick；当前网络按名义 | 本轮失配关，kick开 | 未扫实际CT/replica误差或非零延迟 |
| 数字舍入/饱和及20位输出 | 有，所有码经真实重构 | 本轮开启 | 码和公式已核；未作饱和边界/全范围DNL/INL扫描 |

功耗、面积、参考电气、250MHz LVDS眼图/CDC及180nm工艺签核仍依赖电路与实现证据，行为模型不填虚构数值。

## 运行速度：事件源二分候选未晋升

[121500隔离A/B原件](../../runs/az_probe_20261028T121500Z/validation/receipt.json)在同P、同保存scratch图的 M8 路径上比较原事件源与无状态二分候选。原生纯规则先核12838个N256事件命中、边界/异常和重复调用；N8/N256均实际仿真，30路旧新日志Time/Data位级门及公开RAW/code/ID/time通过。[独立后验](event_lookup_20261028/REVIEW.md)另核logger类型、形状及N256的256个有效输出。

| 记录 | 原版sim / s | 二分sim / s | 本次差 / s | 行为门 |
|---|---:|---:|---:|---|
| N8 | 9.360369 | 8.170961 | −1.189408 | 30路与RAW逐位 |
| N256 | 136.147900 | 136.908603 | +0.760703 | 30路与256条码逐位 |

两组各只跑一次旧→新，启动/编译缓存与系统负载可能影响秒数；**本次N256没有提速，不宣称稳定速度改善，也未改current**。运行入口静态审查发现同名scratch碰撞的失败清理路径缺所有权检查，本次碰撞门已通过且正常结束；未来复用验证器须修该失败路径。下一步用真实 profiler 定位消耗，再决定最小行为等价优化。分析阶段的`behavior_sample_debug`时间轴全扫也有超线性结构，但发生在sim计时之外，不能用来解释本次136秒仿真。

[122805真实profiler原件](../../runs/az_probe_20261028T122805Z/validation/receipt.json)已在121500原版N256图/P上完成一次隔离记录，30路与未插桩原版逐位，256目标码及全部260条ready有效；MATLAB profiler执行前后均为off。[独立回读](profiler_20261028/sar20_profiler_122805_REVIEW.md)核572项累计函数表/delta，确认FunctionHistory达到500万行上限，**不能用它当完整调用顺序**。增量中的可见函数：事件源Outputs 12,838次/含子2.323s，后端S-function Outputs 50,304次/含子80.622s，`validate_inputs` 50,304次/含子26.341s，CDAC网络301,824次/含子20.146s。[行级回读](profiler_20261028/REPORT.md)指出依赖存在性断言整行50,304次/14.404s、NI flag检查行402,432次/4.577s；均是含断言及插桩的行时间，不能等同可节省秒数。函数含子时间彼此重叠，不相加；本次插桩总墙钟182.056s也不能与未插桩136.148s直接形成速度比。Profiler运行向全局既有计数追加了本次记录，before/after/delta均归档且结束状态off。下一实现候选针对每hit重复的不可变参数检查与同事件CT网络计算，均需错误边界及完整日志严格等价后才考虑进入current。

[141949 后端静态参数校验前移的真实隔离A/B](../../runs/az_probe_20261028T141949Z/validation/validation/receipt.json)在当前6319版的旧/候选scratch上先过非法参数与事件命令门，再跑同P N8/N256。候选将不变的 RA/CT/AZ/NI 参数和依赖可见性检查从每次 Outputs 移到 S-function setup，逐事件命令/dt/标签检查保留；数值核与原版逐字节相同。[独立原件回读](backend_speed_20261028/sar20_independent_141949_REVIEW.md)核N8/N256各对历史原件、旧版和候选的30路Time/Data及全部ready RAW/码/时刻逐位一致，并读回6个setup、3个事件错误及相应partial：

| 记录 | 原版 sim / s | 候选 sim / s | 本次差 / s |
|---|---:|---:|---:|
| N8 | 9.306263 | 5.378846 | −3.927417 |
| N256 | 129.078187 | 101.509580 | −27.568607 |

这仍是**单次旧→新顺序**，不能承诺稳定提速；独立缺依赖测试需另一进程，尚未完成，且该候选尚未晋升 current。最外层控制器把native receipt目录看浅一层而误报清理未确认，原回执保留；实际inner/entry清理均为complete，后续仅定向清本任务入口缓存和路径的[独立恢复回执](../../runs/az_probe_20261028T142709Z/controller_recovery.json)已保存。恢复只证明本任务入口被移除、其他路径元素顺序不变；缺运行前完整path快照，不能称全path逐字节恢复，也不能以错误的最外层状态冒充数值失败或通过。

## 当前主图的正侧局部 DC 跃迁（条件静态证据）

[实际局部实验](../../runs/az_probe_20261028T110315Z/static_result/receipt.json)在当前保存SLX `63190994…` 上运行31个独立 N1 DC 点，每点使用同一seed、片池/日历、ID0–3四次真实预热后取ID4，DAC τ=0、有限RA、无kTC/jitter/失配/DEM/dither/AZ/校准。输入从+1至+4个名义LSB20（1 LSB=7.8125µV）重新实测旧粗扫建议的端点，再对通往524290/291/292的三个相邻码跃迁各二分9次；每个最终阈值只被夹在宽度15.258789nV（1/512 LSB）的两次真实异码输入之间。预检以同P对照完整/缩减日志，保留的9路 Time/Data逐位相同；31点均保存完整RAW/valid/code、事件、控制、RA和前端日志、实际P、源清单及SLX身份。仿真只临时覆盖模型工作区P/DecodeP，没有改保存的主图，结束后P/日志配置/RNG/路径保持原样。

| 实际观察的码 | 条件码宽界 / LSB20 | 条件局部DNL界 / LSB20 |
|---|---:|---:|
| 524290 | 1.001953125…1.005859375 | +0.001953125…+0.005859375 |
| 524291 | 1.001953125…1.005859375 | +0.001953125…+0.005859375 |

这些界以**未采样区间单调、每段仅一次相邻码跃迁**为条件；两个同码边界样本不证明中间连续平台，四次预热不证明普遍稳态。范围仅正侧约7.8…31.3µV、ID4、当前固定条件；旧零点附近曾有跳码风险，本实验没有覆盖。**INL未测**，全范围DNL/无失码也未判；1/512 LSB是搜索夹逼宽度，不是硬件电压精度。[实验清理回执](../../runs/az_probe_20261028T110315Z/static_scratch_cleanup_receipt.json)只涉及已镜像证据后的任务临时副本。

[31点独立回读](local_static_20261028/independent_110315.json)核每点保存P、9路timeseries、RAW/ready/公开解码及三次二分包络；实际held与请求DC最大差6.78×10⁻²¹V，31个已测码按电压排序未见反向。每点的完整simout未单独长期留存，运行时无错与SimulationInput覆盖由原生任务回执断言；0V的全/短日志位门仅覆盖该预检点。独立回读仍不能证明未测电压上的单调性、普遍稳态或全范围线性。

[实际采样点图](local_static_20261028/observed_dc_codes.png)仅散点显示31个码与三个实测阈值夹逼带，没有在未测输入间画连续传输曲线；[绘图回执](../../runs/az_probe_20261028T111744Z/receipt.json)绑定原始静态回执的SHA。

零点续测没有复跑上述31点：沿用已核的0V预检，再在当前同一SLX以−LSB20/256（−30.517578125nV）实际运行一次N1/ID4。0V的RAW为`[1040,2374,42,4,1,1]`、code524289；负点为`[1039,3417,42,4,1,1]`、code524285，五个预热/目标样本均valid、actual held等于所请求的两个DC端点。两端仅相隔30.5176nV而输出相差4码；[原始窗口](../../runs/az_probe_20261028T112407Z/zero_result/receipt.json)保存两端身份、负点九路实际日志及全部RAW。**中间输入尚未测，不能宣称524286–524288缺码，也不能给这处DNL/INL。**

[独立逐事件回读](local_static_20261028/ZERO_112407_REVIEW.md)显示：12.5ns前端真实残差已随输入相差30.52nV；15ns首次细SAR D1写入不同，31.25ns完成一级时最终残差约0对+8mV；43.75ns RA/CT的VX/VY明显分开，47.5ns D2字首次不同。最终公开RAW按保存名义数字权重独立重构的D1/D2/DT贡献分别为0/+15.625/−11.71875µV和−8000/+7984.375/−11.71875µV，净合成电压差−31.25µV（4名义LSB）。这些分项是从最终公开RAW**重构**，D1/D2/DT三路逐事件logger在本次受限日志中没有全存；15ns比较结果由实际D1位写入反推，未独立记录Compare1输出。0V预检没有单独保存当时P，续测所用0V P是从锁定工厂源码重建并明确标注的身份，不冒充原生另存P。有限RA可能解释区间拼接敏感性，仍需同图A0压力对照，不能只由这两个端点断言唯一根因。

[单页事件链图](local_static_20261028/zero_event_chain.png)按当前真实框图的阶段名称标出实际日志、从最终RAW推算的数字贡献和未测中间码；图上默认工厂N8截图仅用于定位模块，本次两个DC端点的运行P与它不同。

随后在相同两个DC端点，用当前主图另外实跑四个 A0 敏感性点（2万、Inf各一对），复用A0=1万原件而不重跑。[实际原件](../../runs/az_probe_20261028T113441Z/gain_result/receipt.json)保留每点完整simout、P/SLX/source、五条实际预热及RAW、RA/CT节点；模型文件与工厂P未改。结果：

| RA A0（无量纲） | 负端 RAW D1/D2/DT | 0 V RAW D1/D2/DT | 两端实际码 | 端点码差 |
|---|---|---|---|---:|
| 1万（已保存基线） | 1039/3417/42 | 1040/2374/42 | 524285 → 524289 | 4 |
| 2万（本轮实跑） | 1039/3417/170 | 1040/2374/42 | 524287 → 524289 | 2 |
| Inf（本轮实跑；关闭有限开环增益） | 1039/3417/213 | 1040/2374/42 | 524288 → 524289 | 1 |

在这些固定端点中，一级D1及D2最终字未随A0改变，负端的RA/CT轨迹和tracking判决随A0改变，0V支路保持；这支持有限RA增益放大该处区间拼接误差。[新增四点独立回读](local_static_20261028/sar20_independent_gain_113441_REVIEW.md)核实际240事件、五条valid RAW、公开码和节点/源码身份。A0=Inf仍保留有限UGB=1.2GHz，端点差仍有1码，且中间电压尚未测，因此**不证明唯一根因、无缺码或零点DNL**。[固定端点的增益与判决余量报告](local_static_20261028/GAIN_MARGIN_REPORT.md)列出RA、CT和TA实际节点的逐项回读，其中约A0≥69600的0.5LSB仅是本例单项假设预算，不是整机批准规格。

在缩到−LSB20/4096的最近负端后，[120823隔离三点原件](../../runs/az_probe_20261028T120823Z/gain3_result/receipt.json)新增A0=1e5的负端/0V及A0=Inf的负端，均N1且五次实际预热/目标转换有效；A0=1e5时输出524288/524289，Inf时输出也为524288/524289。原A0=1e4两锚为524285/524289。A0=1e5与Inf的负端码虽相同，43.75ns实际VX和75ns VY仍不同。[独立回读](local_static_20261028/sar20_independent_gain3_120823_REVIEW.md)核九路与完整simout逐位、RAW/TA/参数身份；新点在同SHA的`SarGain3`副本且临时置空InitFcn，而旧A0=1e4锚来自原主图，**未做同A0跨运行环境位级等价门**。此结果只支持该固定端点的有限增益敏感性，不给完整增益预算或全范围线性结论。该隔离作业清了77个本工程函数缓存，回执记录此副作用和主模型/RNG/path恢复；缓存原字节状态不可恢复。

继续细扫时，首个新中点`−LSB20/512`的真实N1仿真得524285，P、simout、原始日志和源码保存在[113931 partial](../../runs/az_probe_20261028T113931Z/refine_result/receipt.json)。之后仅分析脚本的共享索引错误导致`held_input_v`为空，原始`front_log`中的实际孔径值并不为空。原点未重跑；[115303续跑](../../runs/az_probe_20261028T115303Z/resume_result/receipt.json)核对原失败文件后，只新增−7.62939453125、−3.814697265625、−1.9073486328125nV三个N1/DC点，实际held等于请求值，五次预热/目标RAW均valid，三个目标码均为524285。与先前0V/524289实测点形成的最窄跨4码端点窗为1.9073486328125nV，即LSB20/4096；**窗内未测，不能给缺码/DNL/INL结论**。原失败原件保留，当前主SLX前后同SHA，源、P、日志及path/cwd恢复；[独立逐值复核](local_static_20261028/sar20_independent_zero_115303_REVIEW.md)核三个新点和原失败字节复制，强调这是端点窗口、不能称单个四码跳变。[临时副本清理回执](../../runs/az_probe_20261028T115303Z/scratch_cleanup_receipt.json)证明仅删除镜像后任务scratch的33文件、9,866,676字节；原始证据仍在项目run目录。[设计者端点预算](local_static_20261028/ZERO_CROSS_DESIGN_NOTE.md)给出固定本例A0/UGB示例余量及下一组三点真实对照，不当作整机规格。

## M1/M8 隔离短门，尚未进入当前主图

[114345 原生验证](../../runs/az_probe_20261028T114345Z/m1_validation/receipt.json)在与当前主图隔离的`SarM1`副本上，以相同N8输入分别运行M8/M1和τDAC=0/1ns四组。M8两组的旧29路Time/Data逐位门通过，保持8次tracking比较和7次物理更新；M1两组实测12次D2、1次tracking比较和0次tracking更新，8条输出全valid，相关事件时刻、DT字和图上解码门通过。[独立原件回读](m1_m8_20261028/sar20_independent_m1_114345_REVIEW.md)复核每组P/SLX/原始simout、ID4–11输出码、14周期逐事件时刻、冻结源码包及M8历史29路逐位对照；主图前后SHA仍为`63190994…54ec2b6`。该证据只验证隔离N8模式选择；**当前公开运行入口仍是固定M8，M1 N256动态性能未测**。验证退出时有两条`onCleanup`析构警告；后续只读检查发现候选path为0、缓存仅剩测试入口函数，定向清除后缓存为空、主图仍停止干净。这是事后补救，不能把原执行描述成无警告。

## 当前主图：有限DAC建立的实际256码对照

`current/models/SarAdc.slx`已接入旧FE电荷状态到RA的有限DAC解析响应，并合入AZ近极点数值修正。`SAR20('apply',P)`和`SAR20('run')`在同一生产图上生成以下三组真实RX结果。共同条件：Fs=5MS/s、Fin=97.65625kHz（256点bin5）、差分峰值3.650563842595822V、phase=0.731rad、ID4..259/epoch1；同一18片映射、C、输入、控制日历、数字参数和seed。均保存256条连续valid原始接收字及整数码，训练/冻结关闭；有限RA、CINC kick和固定0.5pF/half输出负载开启，kTC/失配/DEM/dither/孔径误差/AZ/随机噪声关闭。

| DAC建立τ（18片） | SNR / dB | SNDR / dB | SFDR / dB | THD / dB | ENOB | 原始运行 |
|---|---:|---:|---:|---:|---:|---|
| off，0 | 110.150096 | 109.827136 | 123.088592 | −121.273976 | 17.951352 | [off原件](../../runs/behavior_59a2b584-fa64-48ef-8608-80ce71bbf10b/summary.json) |
| on，0.1ns | 110.177259 | 109.844923 | 122.888028 | −121.172095 | 17.954306 | [0.1ns原件](../../runs/behavior_96ebc182-7e6f-43d4-8eea-0d81960769b3/summary.json) |
| on，1ns | 107.249369 | 106.913367 | 118.614808 | −118.194717 | 17.467337 | [1ns原件](../../runs/behavior_47c22b65-fdff-402b-b315-ea0599df6891/summary.json) |

每份run均含当次SLX、`parameters.mat`、`source.zip`、`simout.mat`、全部原字/整数码及`spectrum.mat`。[三组实际频谱](finite_dac_current_20261028/spectrum_256.png)只由这些保存的256个码重算，输入文件的SHA在[图的manifest](finite_dac_current_20261028/manifest.json)。三组SLX字节SHA随保存的P而异，生产结构与源码相同；off的29路原日志与旧零τ RX N256逐位相同，[实际门](../../runs/az_probe_20261028T091000Z/receipt.json)已完成。1ns较off SNDR下降2.914dB；0.1ns比off高0.018dB，这个小差异是单条有限码频谱观察，不能解释为统计增益或单调规律。此前候选图1ns N8与当前主图1ns N8的30路日志也逐位一致。当前仅扫描了两个正有限τ值；AZ开启、混合18片τ、其它非理想组合尚未整图验，DNL/INL未测，功耗/面积/180nm签核不由行为模型给出。

[独立回读](finite_dac_review_20261028/N256_REVIEW.md)核对三组各256条RX与ADC同ID/epoch原字、保存的整数码和接收时刻；独立FFT五指标与MATLAB保存值最大原始差为7.41×10⁻¹¹。相对off，0.1ns改变1个码（最多1 count），1ns改变57个码（最多5 counts）。[同主图ID5节点对照](../../runs/az_probe_20261028T093124Z/ID5_COMPARE.md)显示即使此样本最终码未变，前端电荷与RA预反馈节点已发生变化。该独立回读中的`simout.mat`/`spectrum.mat`哈希为回读时计算；原run摘要未事先封存这两项哈希。

近1MHz又在同一当前生产图做了一对[实际N256相干记录](../../runs/az_probe_20261028T103904Z/receipt.json)：Fin=996093.75Hz/bin51、Fs5MS/s、峰值3.650563842595822V、phase0.731，18片τ分别为off/0与on/1ns，RX on、其余本组非理想同前表。off的[SNR/SNDR/SFDR/THD/ENOB](../../runs/behavior_a821241e-39dd-4709-b141-dd47975bc0c7/summary.json)为110.150096/109.827136/123.088592/−121.273976dB/17.951352；1ns的[对应值](../../runs/behavior_1ad89a39-949a-4ea0-bf59-78f15257032a/summary.json)为107.249369/106.913367/118.614808/−118.194717dB/17.467337。两组各256条valid，事件和RX时刻逐位一致；1ns改变57个码、最多5 count。bin51距严格1MHz低0.390625%，按Rev0.5扩展目标SNR≥96/SINAD≥94dB作**近频行为数值比较**时，1ns行余量分别约11.249/12.913dB。

这组结果同时暴露模型边界：实际P与前端输入频率都确为996093.75Hz，高频与先前bin5的完整码**顺序**不同，但相同τ下256码及D1/D2/DT满足固定置换 `j_low=(215·j_high+88) mod 256`（j=0对应ID4）；51≡215×5 (mod 256)，两个互素相干bin访问相同相位集合，五个FFT指标只在浮点舍入级不同。[独立逐码、RX时序及频谱复核](finite_dac_review_20261028/HIGHFREQ_103904_REVIEW.md)确认了该映射；实际采样值并非位同。这是本次关闭孔径jitter、源频响、参考动态等效应的确定性配置证据，不能外推一般频率无关。上述余量不能证明1MHz电路、全非理想、输入驱动或180nm PDK通过。

进一步的同图N8联合配置打开hold_chop、Vos=1mV、第一半AZ保持泄漏1µs和18片固定混合τDAC（0/0.1/1/5ns），[实际run](../../runs/behavior_6dc7cc07-849a-4717-b358-730170f8b547/summary.json)保存8条有效RAW与码；[后处理回执](../../runs/az_probe_20261028T093824Z/receipt.json)逐ID从真实ADI58观察核得12次D2、8次tracking比较、7次反馈。随后将AZ泄漏τ放在真实RA极点上下各1 binary64 ULP，[两组实际N8](../../runs/az_probe_20261028T094010Z/receipt.json)均完成且计数保持。[同一旧FE/BK状态的隔离只读探针与12态expm核验](finite_dac_current_20261028/AZ_DAC_JOINT_ORACLE.md)对三组各8区间给出最大原始VX差1.11×10⁻¹⁶V，新增探针前后30路日志位同；独立Decimal90闭式复算最大原始差1.67×10⁻¹⁶V。N256联合动态及多seed仍未核完，不能称AZ联合非理想全面验收。

[当前主图RX训练短门](../../runs/az_probe_20261028T094225Z/receipt.json)以τDAC=0和transport on运行8条：公开RAW6与声明的外部Ref4逐ID/epoch及CNV/RX时间配对，Terminate只读Update后Train DWork显示n=8、fit=1、秩上界8/缺维676，按欠秩拒绝且无h；训练期间码仍名义输出。工厂P/随机数/模型停止态恢复。它证明当前图的短接收与信息边界，不替代2048条RX训练、冻结、独立holdout或乒乓bank。

## LVDS接入阶段：接收、历史参考配对及实际256码

[011447Z](../../runs/az_probe_20261027T011447Z/receipt.json)已将公开引脚TX/RX、N−2接收标签、历史外部参考配对接入唯一`SarAdc.slx`；同图通过`P.transport.enabled`切换，默认off。只在原48组模拟事件之外加数字close，原始ADC采样/反馈时刻、三个模拟与控制状态owner不变。TX/RX为统一协议行为容器，不代表LVDS电气或FPGA时序签核。

公开入口实际N8：off=4.191914s、on=5.154988s、接收训练=5.510975s。off原19路位同；on实际RAW与同ID数字贡献位同直通，接收时间为sample CNV+538ns，早ADC RawReady仍为86.25ns。训练8条实际RX与历史Ref逐位配对，拟合检查只执行一次并正确因欠秩拒绝；不生成有效h。最终依据`training_committed.mat`中**Terminate只读保存的Update已提交DWork**，不能拿末Outputs或旧finalOP的n7冒充n8。[独立回执](../../runs/az_probe_20261027T011012Z/independent_committed_training.json)也确认新增观察下29路日志逐位不变，无新事件、额外拟合或Outputs提交。

[RX N256原件](../../runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/summary.json)：89.709755s，Fs5MS/s、fin97.65625kHz/bin5、峰值3.650563842595822V、phase0.731、ID4..259/epoch1。实际SNR110.150096dB、SNDR109.827136dB、SFDR123.088592dB、THD−121.273976dB、ENOB17.951352。[频谱](../../runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/Spectrum.png)与[独立核验](../../runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/independent_rx256.json)绑定本次SLX/P/源码/原始码；256条RAW、整数码、同ID数字支路和共享物理事件节点均逐位等于相同模拟配置的旧直通256记录。**这次只保留有限RA，kTC、失配、DEM、dither、AZ、jitter、随机噪声及校准关闭**；不能据此声称完整论文或全非理想性能。接入阶段当时的旧2048训练/1024 holdout仍是直通RAW；后续RX长训练及holdout见本页上节。

显示重排后的[实际N8](../../runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/summary.json)为4.923313s，29路日志与重排前逐位一致。看[ID5解释](../../runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_explain.md)：held=3.557564918V，D1/D2/DT=1932/2907/85，输入参考贡献3.552V、0.005546875V、−3.90625µV，重构3.55754296875V，最终整数码979654；实际ADC Ready1.08625µs，RX Ready1.538µs。[分尺度、共CNV原点的时序图](../../runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_timing.png)取真实观察时间，不用协议常量补点。

图像导出时的模型身份见[current_figures/metadata.json](current_figures/metadata.json)；当前模型以实际SLX文件为准。Top配置文字净区和ADC阶段尺寸已整理，系统图仍有较密的控制与诊断连线；未宣称最终视觉验收。下面保留各历史实验的原始范围，不把其结果自动迁移为RX长校准、完整非理想或工艺结论。

## 已验证：采样孔径误差已接主图，并暴露时序预算不足

采样电荷的同一状态owner中追加实际孔径与开采时间；FE旧317字前缀保持，新增36字后为353。公共jitter按sample ID/epoch共享，局部jitter按物理slice ID分别取值，固定skew为18片参数。仅在充分建立的signal capture端点评估`input(t_ap)`并写入原电荷；其他SAR/反馈/比较日历与tail/bias时序保持名义。有限RC+jitter、全时钟抖动仍未实现。

`runs/az_probe_20261026T233611Z`的六个N8已实际完成：off、common25ps、local10ps、固定18片±8ps、combined及同seed重复，seed20261029。相对off分别改变0/6/3/1/7/7个整数码。原18路在off时逐位保持，combined/repeat全部19路逐位保持；三个ADC状态owner及原连线/日历保留，仅添加无反馈的28字孔径观测。[独立核验](../../runs/az_probe_20261026T233611Z/independent_aperture.json)绑定真实8片孔径、ID/epoch、held和原件来源。

设计者可从[实际联合ID5](../../runs/behavior_2b9d513a-14ba-4073-af20-61c3906f612b/sample_5_explain.md)定位：源斜率为正，八片孔径提前42.287–79.128ps，held从3.557564918V降低30.764µV至3.557534154V，整数码979654→979650。局部10ps或固定skew单独作用虽改变held，未必跨整数门限。这是实际行为解释，不以理想目标码覆盖节点。

接着两组主图各运行256个有效码：ID4..259/epoch1、Fs5MHz、Fin97.65625kHz/bin5、Apeak3.650563842595822V/−1dBFS、phase.731。A0=1e4/UGB1.2GHz；kTC、失配、DEM/dither、AZ、校准及其他随机噪声关闭。只改变三个孔径误差参数及其enable。完整结果、SLX/P/源码和独立指标核验在[233854Z](../../runs/az_probe_20261026T233854Z/independent_dynamic.json)。

| 采样孔径配置 | SNR / dB | SNDR / dB | SFDR / dB | THD / dB | ENOB | sim / s |
|---|---:|---:|---:|---:|---:|---:|
| off | 110.150096 | 109.827136 | 123.088592 | −121.273976 | 17.951352 | 75.170551 |
| common25ps＋local10ps＋固定±8ps | 95.998292 | 95.787621 | 108.842198 | −109.034314 | 15.619206 | 75.798769 |

- off：[实际频谱及原件](../../runs/behavior_cd980f4b-c3d1-4075-aa79-339b787509e2/Spectrum.png)。held对名义输入RMS约4.92e−16V，仅为数值舍入级，不能称实际芯片零噪声。
- combined：[实际频谱及原件](../../runs/behavior_3f470e43-4e0a-4419-b609-3707cbc82335/Spectrum.png)。实际held误差RMS41.556138µV、max154.109624µV。本批不存每片完整孔径历史，不能拿seed重建值冒充观测；该RMS来自真实FrontLog。

在等C、充分建立、独立common/local小抖动假设下，随机项一阶量级为`σVin≈2πf A_rms sqrt(σcommon²+σlocal²/8)=39.991µV`。实测高约3.91%，与有限记录及固定skew共同存在时的量级相容；没有按实测反调sigma，也未宣称分布/不同seed扫描通过。固定skew是选片相关的确定性项，不直接当白噪声加入该方差式。

Rev0.5近100kHz、−1dBFS主目标为SNR≥100dB、SINAD≥98dB、THD≤−105dBc。本combined条件的SNR/SINAD分别缺4.002/2.212dB；THD在本点有约4.034dB余量。**这组时序预算不足。** 当前97.656kHz相干点及关闭多项NI的条件仍不构成严格100kHz全非理想验收，更不能借1MHz较宽目标通过本点。

两N256前8个样本的12路完整节点/事件与其N8原件逐位相同，其他物理/数字字段保持；观测关闭后每组simout约1.96MB，孔径logger仅1行NaN/232B，没有353字全状态逐事件日志。

## 历史直通RAW路径：主图2048训练与1024独立holdout

训练run=`behavior_30bb3ff5-8668-4149-a3c5-1ca5d6dabed7`，实际sim645.6741秒；TrainRef在CNV锁存独立声明的外部参考，Train在Update收满2048条公开RAW后仅拟合一次。实际684列满秩、缩放条件数2242.6416、训练RMS1.7570µV。未读actual C/held/内部残差；无正则或名义补列。训练期间输出仍为名义码。

在holdout产生前锁定h与完整2056行公开配置，h SHA=`a634c9a0c63c636a4c8966bc7d0e04d6d9ad4cf550156e6ed7ffe7806d6483ed`。holdout run=[behavior_f2d62e08-2366-48f9-be8c-a500bf015d68](../../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/summary.json)，实际sim328.4242秒。SLX SHA=`db3cf5cd3fe9733a97fdde64a91bd7753019e7ecb724ed244a4644f9d1a50750`；原始code、RAW、Ref、SLX、P及as-run源码均在此run。

实际holdout为N1024、ID4..1027/epoch2、Fs5MHz、Fin112304.6875Hz/bin23、峰值3.650563842595822V、phase1.217rad。训练为epoch1、bin37/2048、phase.731，协议与评价门在数据前固定。两批同一固定失配芯片σunit=.001/seed20261028，DEM和a_in=1mV的物理dither开启，有限RA A0=1e4/UGB1.2GHz；**kTC、AZ和其他随机噪声关闭**。理想外部参考误差为零是试验假设，不是硬件测量。

| 同一真实RAW的输出 | SNR / dB | SNDR / dB | SFDR / dB | THD / dB | ENOB |
|---|---:|---:|---:|---:|---:|
| 原名义支路 | 101.689600 | 101.608365 | 114.622332 | −118.929329 | 16.586107 |
| 固定h的实际主输出 | 117.831191 | 117.736411 | 135.474048 | −134.394369 | 19.265185 |

名义对照直接记录同一ADC的原支路线值，不是另造一组理想码。[实际频谱](../../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/holdout_spectrum.png)采用矩形相干FFT、DC排除、H2..H10分离、ENOB无幅度修正；图中dBFS按满幅正弦功率FSR²/8定义。

| 对声明外部参考的误差 | RMS / µV | 最大绝对值 / µV | 事前门 / µV |
|---|---:|---:|---|
| 实际取整前重构电压 | 2.650260 | 7.990569 | RMS≤7.8125，max≤31.25 |
| 实际整数中心 `(code−2^19)×LSB` | 3.353851 | 9.139736 | 同上 |
| 同RAW名义整数支路 | 26.590973 | 81.339205 | 仅对照 |

[1024条误差图](../../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/holdout_error.png)保留全部登记行；没有refit、增益/偏移校正、剔除异常或改变容差。独立[核验](../../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/independent_holdout.json)确认真实数据绑定、完整缓存不变、fit次数0，以及公开RAW/cfg/h独立复算整数零差。**这批独立holdout通过；仍不等于全非理想、乒乓bank、LVDS、论文全部数据或工艺验收。** 默认训练与冻结仍关闭，cache保持NOT_ACCEPTED，评价回执独立记录有限范围的通过。

调试优先看[整数误差最大的ID410](../../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/sample_410_explain.md)或[预取整误差最大的ID972](../../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/sample_972_explain.md)。两者分别对应−9.139736µV和−7.990569µV，不能混同。解释从真实采样/残差/VX/VY、12D2/8TA判决到canonical `(u+Bh)/den`和最终整数码；原四项仅保留为名义对照。

新显示与控制器成功路径去除报错字符串后，同P的N8实测4.1936119→3.7832113秒。独立核验18路Time/Data逐位相同，完整P一致；这是一对无profile计时，不宣称稳定比例。日志未泄漏完整状态或训练buffer历史：2048训练simout约12.94MB，1024holdout约7.52MB。

## 本轮ADI整图：同芯片开关对照及256码实际频谱

主模型的18片池、实际DEM组映射、tail电荷dither及同ID数字加回已完成整图开关对照。新接入的58标量观测仅分支读现有信号；独立结构核验确认原计算连线、3个状态owner及Trigger保持。实际关→开→关的12路原日志逐位相同，新增记录分别为1/576/1行。证据：`runs/az_probe_20261026T212741Z/independent_observer.json`。

八组N8为名义C/一颗固定失配C，各自DEM/dither的00、01、10、11。每组含4次实际预热，纯仿真3.611–3.883秒；全组实际wire验收及独立原件核验见`runs/az_probe_20261026T213337Z`的receipt、independent_cases、physical_interpretation及summary_review。选片、真实shift、捕获tail电荷、DAC目标、反馈符号及12/8/7计数来自实际tap；未把公开计划或图上开关当作物理观察。tap不直接观测绝对q_initial、每电容mask或release后全部B状态。

失配是明确的设计压力：unit相对σ=0.1%、局部芯片seed20261028，各N-Cu支路相对σ=0.001/√N；同一18×38矩阵用于所有开关组合，包含bias支路，不重抽/归一化。两半共用该矩阵，未涵盖PN独立失配、梯度或PDK统计。数字码权始终保持名义值，未读取actual C进行校准。

随后四组失配配置分别运行256个有效码，Fs=5MHz、Fin=97656.25Hz/bin5、差分峰值3.650563842595822V（−1dBFS）、相位0.731rad、FSR=8.192V、ID4..259/epoch1。RA A0=10000、UGB=1.2GHz，CINC/replica开；AZ/kTC/其它随机噪声/抖动/校准关闭。dither输入参考标度a=1mV、四电平±0.5a/±1.5a；DEM是31组确定性循环移位。矩形相干FFT、去DC，SNR/THD分离H2..H10，ENOB无满幅修正。

| DEM | dither | SNR / dB | SNDR / dB | SFDR / dB | THD / dB | ENOB | sim / s |
|---|---|---:|---:|---:|---:|---:|---:|
| off | off | 102.339491 | 101.121818 | 110.220192 | −107.238976 | 16.505285 | 77.1768 |
| off | on | 101.963208 | 100.702967 | 108.959374 | −106.691167 | 16.435709 | 78.2461 |
| on | off | 102.655951 | 101.340344 | 112.630586 | −107.168137 | 16.541585 | 75.2879 |
| on | on | 102.681420 | 101.283225 | 112.496875 | −106.885748 | 16.532097 | 78.5818 |

各行原码、SLX、参数、source.zip、频谱及SHA分别位于：

- 00：[真实频谱](../../runs/behavior_39e5ffae-3700-4bb0-887b-e4631c8d1a35/Spectrum.png)，run=`behavior_39e5ffae-3700-4bb0-887b-e4631c8d1a35`。
- 01：[真实频谱](../../runs/behavior_c8b7a170-f2e4-4c06-be6c-19aa193298e8/Spectrum.png)，run=`behavior_c8b7a170-f2e4-4c06-be6c-19aa193298e8`。
- 10：[真实频谱](../../runs/behavior_0d7c348e-3dd5-42f1-b4d9-f88eb344b942/Spectrum.png)，run=`behavior_0d7c348e-3dd5-42f1-b4d9-f88eb344b942`。
- 11：[真实频谱](../../runs/behavior_27f36716-ea12-45f3-8e68-e2209fd4e637/Spectrum.png)，run=`behavior_27f36716-ea12-45f3-8e68-e2209fd4e637`。

批次回执为`runs/az_probe_20261026T213624Z/receipt.json`。每组N256的前8条raw/code/time与同名N8逐位相同。四组在本次近100kHz条件下均高于SNR100/SNDR98/THD≤−105dB目标，最小对应余量约1.963/2.703/1.691dB；这些是已声明配置的行为结果，不代表全部非理想、精确100kHz、不同频率/幅度/seed或180nm签核。

本批DEM使SNDR提高约0.219dB（dither关闭）或0.580dB（dither开启）；dither在DEM关闭/开启时分别降低约0.419/0.057dB。仅一颗设计压力芯片、单频256码，不能推广收益。名义N8的DEM实际目标电荷与原码完全相同；名义dither仅ID11少1码，符合有限RA增益下数字公称加回仍有残余及量化影响的情形。

## ADI与AZ联合的实际样本

另做一个N8功能联合例：失配+DEM+dither，hold_chop、Vos1mV、写τ8ns、泄漏τ1µs、kTC关闭。`behavior_90c97b0c-9945-448a-867e-2735d45c02cf`实际sim3.7428秒，真实wire门通过。它不是上表FFT配置或新增收益对照。

[ID5完整解释](../../runs/behavior_90c97b0c-9945-448a-867e-2735d45c02cf/sample_5_explain.md)现在包含真实8片ID、DEM shift、捕获tail电荷和首次DAC目标。ID5原始Qres=+1.922914337e−13C，POL=−1后送RA为负；local/return Vtop按同POL恢复。RAW=1932/803/170，实际贡献`3.552 + 0.006828125 − 0.00000390625 − 0.0015 = 3.55732421875V`，整数码979626。完整12次D2、8次TA逐行观察及AZ保留标签都可直接看，不需要读状态索引。

## 历史阶段：短记录的校准准入与欠秩拒绝

真实N256/N8以及八组ADI-on/off公开RAW已在MATLAB通过cfg17白名单、plan/DEM/dither/POL、名义电压关系与信息边界测试。8组feature/decoder/归档整数码本次全部相同；沿用原128eps电压门。N256正确给出至少428个未辨识方向并拒绝拟合，h/frozen保持空；未读取外部参考或holdout答案。证据在213624Z/public_calibration及214435Z/adi_public_calibration。

当时仅为独立入口准入；当前已完成的主图2048训练与1024冻结holdout见本页首节。短记录欠秩拒绝仍必须保留，不能因长记录已通过就给N8/N256填名义系数。

## N256：本次结果身份

运行目录：`runs/behavior_f4da0fd7-e1a3-47d4-bfb5-a2f9dfc504e7`。实际sim **77.9400908s**；256个有效码、ID4..259、epoch1。

SLX SHA256：`d92ca0f35be6f42c84c1a8eb6f6458655c8bb31f578760bf52723d727a612f61`。该run的`SarAdc.slx/source.zip/parameters.mat/selected.mat/simout.mat/summary.json`绑定本次源文件、完整参数与原始码。本次已使用晋升后的六阶段分层主SLX重新仿真；与前一平铺版同配置的12路完整日志逐位相同，并非移用旧频谱。

| SNR | SNDR | SFDR | THD | ENOB |
|---:|---:|---:|---:|---:|
| 102.477373dB | **102.257986dB** | 115.916563dB | −115.332955dB | 16.694018bit |

实际条件：Fs5MHz、Fin97656.25Hz（bin5）、差分峰值3.650563842595822V、相位0.731rad、FSR8.192V；kTC温度298.15K、独立seed20261027、master标签20261020。AZ为hold_chop，输入失调1mV，写τ1ns，泄漏τInf，无随机AZ噪声。RA A0=10000、UGB1.2GHz、resetτ1ns；前端采样/预充/DACτ0，失配、DEM、dither、jitter与其它随机噪声关闭，校准关闭。

[实际频谱](../../runs/behavior_f4da0fd7-e1a3-47d4-bfb5-a2f9dfc504e7/Spectrum.png)与[独立核验](../../runs/behavior_f4da0fd7-e1a3-47d4-bfb5-a2f9dfc504e7/independent_spectrum.json)可直接打开。独立FFT只读取实际整数码，最大指标差约1.3e−10dB；全部37源文件pin、参数/模型/码文件SHA、valid/ID/epoch和真实时刻核验通过。

同配置短记录`behavior_bd6a67ce-47ea-4e4d-94e7-83115f6605b4`的8组raw、code和时间，与N256前缀uint64逐位相同；同seed计划的整个旧前缀保持。不能把256点当充分统计扫描。

## 采样噪声与AZ的实际节点证据

信号电容为27.151515pF/half，而28pF是包含其它顶板连接电容的工程假设。理论聚合差分kTC为17.413137µV RMS；本次256次真实孔径处的held减保存输入：RMS18.109626µV、均值−0.977901µV。约4%的波动不应通过调C/T拟合；该记录也不证明counter噪声白性/尾分布。

全部128对样本在RA启动处复用同一AZ值和写计数。Inf保持例中，TA期间该次采样噪声不重抽、不再除以sqrt(8)。实际ID0的有限写入端点为0.0009999999999999731V，下一偶帧刷新后才舍入成0.001V；不是把AZ直接赋理想补偿。输出SNDR还包含有限RA增益/建立、CT、判决和量化的作用，不能直接等同单kTC预算。

## 已过的行为保持与调试门

- 本轮只读解释功能实际native通过：`runs/az_probe_20261026T211819Z/receipt.json`；新N8 `behavior_3cc384a0-3678-4709-8beb-cded2b86023c`，sim3.704695秒。原12路完整Time/Data相对同配置f18基准逐位相同，原P/DecodeP及SLX文件SHA保持，global RNG不变。`SAR20('sample',5,runPath)`已实际生成六阶段解释及20行D2/TA观察，最终码979654；没有新增仿真状态或日志通道。
- 同run `independent_debug.json`重新读回原始MCOS日志核验20行逐次表及12路完整位相等，另核模型、参数、selected、源ZIP及源码pins；不是只复述native通过回执。
- 四模式ordinary/chop/hold/hold_chop已在同一主图；完整Qres换向、返回FE坐标恢复、数字仅D2/DT解调均由实际wire日志核验。
- 四模式×Inf/1µs泄漏及零/非零失调参考，共10个N8配置通过；独立AZ RC预测逐事件差为0，无放宽容差。这是确定性状态测试，不是随机CAAZ噪声收益。
- 固定参数捕获的单对无profile计时6.6428914→4.3252889s；非零AZ/leak另次3.8009591s。全部12组日志Time/Data逐位保持。不能把不同调用混作统计benchmark。
- 采样kTC关闭时原日志逐位保持；开启后同参数/seed重跑逐位一致、global RNG未变。kTC已注入同一B电荷，再进入q_initial、DAC残差及实际码链。
- 显式apply(P)、无参factory apply、冷SDK路径、P/DecodeP一致性及可见配置已实际验证。界面/入口修改后的N8 off3.891s、thermal-AZ3.516s也逐位保持。
- 新诊断仅14标量，N8含时间轴72KiB未压缩（并非全状态/全电荷日志）。phase、有效性、sample ID/epoch和release消费边界在图/CSV明确区分。

## 局部静态与行为归因：没有用增益理想化替换默认模型

`runs/az_probe_20261026T205330Z/local_static/local_static.json`保存62次真实主图DC运行，合计287.9574秒；每次固定ID4、四次真实预热、epoch1、N1，AZ/噪声/DEM/dither关闭。测量范围仅为零点±62.5µV及64mV±62.5µV。预声明分辨率为LSB/64=0.1220703125µV；测试后恢复原P。

已测点未发现反向跳码。两处边界均在一个分辨率区间内跨4码，中间平台未分辨，**不能填DNL=-1或宣称全局缺码**。已解析的码524289、532481的相邻阈值支持局部DNL约[0,0.0234375]LSB；第二个区间下界有约−5.54e−13LSB浮点尾差。INL仍未测。

随后仅对四个既有输入做A0=Inf归因控制，UGB仍1.2GHz，数字仍按名义32倍重构。真实结果在`runs/az_probe_20261026T211033Z/receipt.json`，每点sim约1.65–1.87秒；没有修改默认A0=10000。

| 输入 / V | A0=10000实际码 | A0=Inf控制实际码 |
|---:|---:|---:|
| −0.0000001220703125 | 524285 | 524288 |
| 0 | 524289 | 524289 |
| 0.0639998779296875 | 532477 | 532480 |
| 0.064 | 532481 | 532481 |

同一输入对照中，前端实际日志、Qres/target、NG=34、τ=4.50939005427ns和事件时刻均保持。左侧target=0.25599609375V；首/末TA的VX由0.255113052028/0.255126414807V变为0.255980436405/0.255993844617V。D2仍3417，DT由42变213，数字输出增加3码；右侧近零残差的原码保持。

这是清楚的行为因果：有限RA增益系数`F=A0/(A0+NG)`使残差被缩小，而数字仍使用名义增益32，D1换区间时产生拼接误差。预测输入等效变化约27.108µV，实际VX变化吻合。控制将两处4码跳缩为1码，支持这四点的归因；不等于已修复、全范围DNL合格或校准完成。保留默认有限增益，后续应据设计预算/公开校准处理，不偷偷以Inf替代。

## 三种状态必须分开：本轮四组ADI频谱

| 项目 | 有实现 | 本轮四组N256开启 | 已完成的实际扫描范围 |
|---|---|---|---|
| RA有限增益/带宽、reset、CINC/replica | 是 | 是 | 当前配置及A0四点归因，未完整扫带宽/replica误差 |
| AZ写/保持/POL/泄漏 | 是 | 关闭 | 既有10个N8配置、thermal-AZ N256及本轮ADI联合N8；随机AZ噪声未覆盖 |
| 采样kTC | 是，平衡capture模型 | 关闭 | 既有off/repeat/小批统计/thermal-AZ N256；不移用为本批开启项 |
| 前端有限采样/预充 | 是 | τ0关闭 | 待补；kTC+有限RC联合仍拒绝 |
| 池选择/DEM/dither | 是 | 18/8/8/2始终开启，DEM/dither逐行开关 | 名义/固定失配8组N8＋同芯片4组N256＋ADI/AZ联合N8 |
| 前端电容失配 | 是，显式C矩阵 | 是，unit σ0.1%的单颗设计压力芯片 | 与名义C及开关组合对照；更多seed/梯度/PN独立失配未扫 |
| 前端寄生、后端失配 | 有参数路径 | 关闭；Cp=0，后端实际与名义相同 | 未完成，flag不等于真实扰动 |
| 采样孔径skew/jitter | 已实现充分建立的signal endpoint近似 | 本表四组ADI频谱关闭 | 后续六N8与两N256实际门见首节；非全时钟jitter/统计扫描 |
| DAC→RA联合建立 | 已接主图 | 本表四组为τ0、未启用耦合 | 另有N8及0.1ns/1ns N256；AZ开启与混合τ整图待验 |
| 参考恢复 | 未实现 | 否 | 未验证 |
| RA/AZ/比较器随机噪声、再生/超时 | 主图未完成 | 否 | 未验证 |
| 校准训练/冻结/holdout | 已接主图，默认off | 本表四组N256关闭 | 旧直通RAW及后续固定条件RX的2048训练/1024 holdout已完成；Bank同h N256见首节，其他配置未验 |
| 公开LVDS传输 | 已接同一主图，默认off | 本表四组使用旧直通RAW | N8、N256接收及固定条件RX长训练/holdout已验证；电气与CDC未验 |
| DNL/INL、定点/饱和边界 | 两窗口局部跃迁；INL未测 | — | 仅两个已解析码宽度；不外推全范围 |

A0/UGB、CINC900fF、28pF及部分开关约定含明确设计假设。行为模型不证明180nm电路功耗、面积、稳定性、共模或工艺签核。当前仍未完整复现论文全部数据。

## 历史结果的界限

| 历史配置 | SNDR | 状态 |
|---|---:|---|
| 早期事件级基础N256，采样噪声关闭 | 109.8271dB | `behavior_ce06aab1...`归档；不是当前带kTC结果 |
| NativeCt固定A/B、冻结校准N256 | 101.91dB | 旧分支，不给当前模型背书 |
| 旧MNA N256 | 99.6528dB | 已退休细步路线；sim5621.3144s |

下一步保持事件级行为闭环，扩展已测固定条件之外的长记录校准、乒乓bank生命周期边界及其余非理想。孔径误差已接入的范围限于相关章节；全时钟抖动及有限RC联合仍未完成。局部静态拼接误差仍是已测设计限制，冻结后的静态范围还未完成。后续改动继续绑定自身SLX、参数、seed和原始数据，不继承旧配置的性能。
