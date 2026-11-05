# SAR20-5 行为级工程

同一主SLX已接入公开LVDS、有限DAC→RA解析耦合和受限的Bank A/B行为路由；工厂配置默认N8、transport OFF、Bank OFF、DAC建立关闭。[图像metadata](analysis/behavior/current_figures/metadata.json)对应2026-10-28的旧模型，早于Bank接入；当前模型以实际SLX文件为准，运行状态见[检查点](CHECKPOINT.md)。

**唯一入口 `SAR20.m`；唯一开发模型 `current/models/SarAdc.slx`；参数工厂 `config/adc_parameters.m`。** 实际仿真在 Windows MATLAB R2024a，目录 `D:/Academic/Projects/sar20m1/SAR20`。Mac同步工作版本与证据，未宣称在Mac原生运行。

模型按采样、切换、比较和反馈事件推进少量状态；不再求解细网格MNA。原始判决、输出码和频谱来自实际仿真。

产品设计输入以[Rev0.5合同](docs/DEFINITIONS/ProductRev0.5/contract/SPEC.md)为准。`docs/SPEC.md`与`docs/spec.yml`保留Rev0.3历史；实际已应用参数/时序以模型P及各run的parameters.mat为准，不能把合同中的候选相位表当作本次执行记录。

| 现在看什么 | 当前事实 |
|---|---|
| 唯一开发/运行/调参 | `current/models/SarAdc.slx` / `SAR20.m` / `config/adc_parameters.m`；实际核在`current/src` |
| 已接主通路 | 6b预转换＋SAR1、真实DAC残差、32×名义RA/AZ、CINC/12D2/8TA7、数字重构；18/8/8/2池、DEM、物理dither及公开加回已完成整图对照 |
| 已记录的实际结果 | DAC τ=1ns、RX N256得SNDR106.913dB；τ0的RX长训练2048条满684秩、单次拟合后冻结，1024条独立输入holdout通过原误差门，冻结码SNDR117.458dB。[条件与原件](analysis/behavior/RESULTS.md) |
| 已接数字扩展 | 片外TrainRef、仅公开RAW/Ref训练、不可变h解码及支持双槽预装的Bank；工厂默认训练、冻结、Bank均OFF。2026-10-30的[Bank三案N256](analysis/behavior/n256_20261030/RESULTS.md)在同一行为芯片、两槽同h时，Bank码与Frozen码逐位一致；资格仍为`NOT_ACCEPTED` |
| 已接孔径误差 | 同一采样电荷上的公共/局部jitter及18片固定skew；真实八片孔径可查。仅充分建立的signal endpoint近似，其他时序仍名义 |
| 仍未完成 | Bank不同h切换、后台训练、真实drain/槽复用和下游时钟合同；全时钟抖动/有限RC联合、参考恢复/比较器等关键非理想、全范围DNL/INL；AZ＋混合DAC的N8区间已做独立公式核验，N256联合性能待补；RX holdout只限同一固定芯片与声明理想参考，系数仍未产品接受 |
| 已接传输 | 同一SLX默认transport off直出；`P.transport.enabled=true`后apply，按公开pin TX/RX在N−2槽输出record；ADC状态/48事件不改 |

证据版本不能串用：**101.91 dB SNDR**来自旧 NativeCt 固定A/B、冻结校准分支的256点记录；旧 PoolCt 的8点短验证没有可继承的频谱性能。早期独立352态组件、684参数函数、静态检查或重放也不等于接入整张ADC图。当前状态以上述唯一主图的实际 `SAR20('run')`、保存的SLX/P/source/raw及各自验证回执为准。

## 打开、调参、复跑

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20                        % 打开当前模型
SAR20('apply')               % 修改工厂后：应用参数/初态/图上说明并保存
SAR20('check')               % 实际编译
r = SAR20('run');            % 使用已应用P，保存源码/SLX/参数/原始结果
SAR20('sample',5,r.run_path)  % 生成中文逐级解释、逐次判决表、节点图与CSV
```

修改工厂文件不会自动改变已打开模型。**apply才应用；直接点击Run和入口run均使用保存的P，不重读工厂。** 入口run才建立完整运行证据。参数在初始化时捕获，修改后需apply/重新编译，不支持运行中热调参。当前工厂默认N8、AZ/kTC关闭。

Bank ON 需要完整预装双槽及固定资格文件等绑定条件，不是单独把 `P.bank.enabled` 改成 `true` 即可；见[参数与限制](docs/PARAMETERS.md#bank-行为路由与复跑边界)。[sample解释器](current/src/analysis/behavior_sample_explain.m)现会读取实际record时刻的Bank有效标志和元数据，并区分原始`code_valid`与包含RAW、标识、版本及fault的综合检查；名义贡献只作对照，Bank内部`u/Bh/den`和最终电压未记录。[复制run的ID4报告](runs/work_20261030T151254Z/copied_run/sample_4_explain.md)及[公开入口回执](runs/work_20261030T151254Z/receipt.json)记录实际Bank码587978、名义码587981、slot/version 2/2；这是单样本日志检查，不是产品验收。sample本身未用可信回执绑定simout，不能证明文件未混档。

不带 run 路径的 `SAR20('sample',id)` 使用 `runs/latest_behavior_run.json`，其配置可能与当前P不同。sample会在所选目录写入或覆盖同ID的图、CSV和解释；请先将完整历史run复制到新的目录，再显式传入副本路径，避免覆盖原始归档：

```matlab
srcRun = fullfile(fileparts(which('SAR20')),'runs', ...
    'behavior_302c58b3-52b4-42ac-b6c9-fbe09674156e');
copyRun = fullfile(tempdir,['sar20_sample_' char(java.util.UUID.randomUUID())]);
assert(~isfolder(copyRun) && ~isfile(copyRun));
[ok,msg] = copyfile(srcRun,copyRun); assert(ok,'SAR20:copyRun','%s',msg);
SAR20('sample',4,copyRun);
```

用于证据时，还应依据[原始三案回执](runs/work_20261030T141338Z/receipt.json)核对副本的`simout.mat`、`parameters.mat`和`summary.json`哈希；图文本身不提供防混档证明。

复跑已保存的完整实验配置：

```matlab
s = load('runs/behavior_f4da0fd7-e1a3-47d4-bfb5-a2f9dfc504e7/parameters.mat','P');
SAR20('apply',s.P); r = SAR20('run');
SAR20('apply');              % 实验结束恢复工厂N8配置
```

## 一页读图顺序

1. `Driver`是片外激励配置[V/Hz/rad]；`Calendar`是控制时序的行为日历。
2. `EventStep`是仿真调度边界，**不是芯片边界**。其中`Adc`为片内ADC，`Fpga`为片外数字算法。图上说明来自已应用P，而非未应用的工厂文件。
3. 沿 `Sample → PreconvertSar1/DacTrial → RaAzCt → Compare2/Sar2Tracking → ChargeReturn/RaReset` 看采集、一级切换、放大/CT反馈、判决和电荷返还。6位Flash预转换+5次细SAR形成10位有效DT量化；后续为12次D2、8次tracking比较及7次物理更新，RA后没有新增采样保持。
4. ADC模拟/控制由`SampleCharge[353]`、`RaCtState[48]`、`SarState[51]`三个标准UnitDelay保存唯一状态。FE353保留旧317字前缀，追加18片实际孔径和18片开采时刻；没有复制电荷记忆。其它stage计算下一状态；片外训练参考/收集器另有明确的仪器及数字存储。比较、存储和FPGA算术采用标准块；耦合电荷、RC与CINC保留明确计算核。
5. FPGA只使用公开D1/D2/DT及ID/epoch重构，最后20位round/saturate。默认名义支路；显式冻结时使用固定h的`(u+Bh)/den`。TrainRef是Adc外的声明仪器参考，仅供训练和独立评价，不进入冻结解码。内部仍为double算法。原始`DT[7:0]`指tracking判决，不是“离散时间DT一级”的位数。
6. 日志区分pre-decide真实端点、final-next待锁存状态及post-decide/pre-ChargeReturn返回命令。ADC RawReady仍在CNV后86.25ns；transport on时，同ID的RX raw_ready在CNV后538ns，FPGA才消费record。frame_ready/raw_ready/sample_ready含义见[参数表](docs/PARAMETERS.md)；原始ADC Ready不等于接收ready。

实际框图及导出身份见[metadata](analysis/behavior/current_figures/metadata.json)；使用前将其中SLX SHA与实际模型文件核对，若不同，图片只代表对应的导出快照。六个计算阶段及独立Diagnostics已进入主模型；有限DAC的旧FE状态→RaAdvance第4口属于同一模拟记忆链，RaPre探针只观察。 [按一个样本读图](docs/READ_GRAPH.md)给出实际路径与状态所有权。历史`runs/`和`evidence/`暂时不用读代码；它们只供核验，不能当开发入口。

Diagnostics新增的ADI观测默认关闭、仅存1行NaN；专项N8可开`P.debug.adi_enabled`，sample解释会显示实际8片ID、DEM shift、捕获tail电荷和首次DAC目标。它不改变物理开关；复跑方法见[参数表](docs/PARAMETERS.md)。

## 一个实际样本为何得到这个码

先看[真实RX on的ID5解释](runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_explain.md)、[节点图](runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_az.png)及[record CSV](runs/behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50/sample_5_record.csv)：CNV为1µs，ADC RawReady为**1.08625µs**，实际RX record为**1.538µs**；同ID5/epoch1，D1=1932、D2=2907、DT=85，code=**979654**。物理图保持CNV后0…90ns，数字值按实际record时刻读取，不能拿86.25ns行号取538ns的码。无效/重复/缺失record单列诊断，不填成有效结果。

**先看[孔径误差ID5的逐级解释](runs/behavior_2b9d513a-14ba-4073-af20-61c3906f612b/sample_5_explain.md)。** 同一输入与芯片，关闭孔径误差时held=3.557564918V、code979654；开启公共25ps/局部10ps/固定±8ps后，真实八片孔径提前42.287–79.128ps，held降低30.764µV，最终code979650。输入此时正在上升，提前采样导致电压降低；较小的局部或固定skew单独作用时，电压变化不一定跨过整数码门限。

[八片孔径CSV](runs/behavior_2b9d513a-14ba-4073-af20-61c3906f612b/sample_5_aperture.csv)中的时刻来自同一主图的实际观察，表中同时保留片号、绝对秒和相对CNV的ps。顺着held→D1/Qres→VX/VY→逐次判决→最终码，可定位误差首先出现在哪一级；这里最早变化就在capture。

校准路径另看以下实际例：

先看[冻结输出ID410的逐级解释](runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/sample_410_explain.md)与[节点图](runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/sample_410_az.png)：实际held=2.09579038973622V、一级D1=1558，真实后级D2=2458/DT=170；冻结输出实际`(0.040625+66.779379670774)/31.8830454295188=2.09578488411615V`，最终整数码**792548**。式中u/Bh为RA域电压、分母无量纲；本历史off run取同RawReady行，transport on则须取同ID/epoch的actual record-ready行。每条D2/TA判决和状态观察阶段都在解释页；不会拿旧名义公式冒充校准码来源。

无需重仿真即可读取这个样本：

```matlab
SAR20('sample',410,fullfile(fileparts(which('SAR20')), ...
    'runs','behavior_f2d62e08-2366-48f9-be8c-a500bf015d68'));
```

下面是名义解码的对照例，配置不同：

[历史τ=0默认物理条件下的ID5逐级解释](runs/behavior_3cc384a0-3678-4709-8beb-cded2b86023c/sample_5_explain.md)来自当时的真实N8模型，AZ/kTC/DEM/dither关闭，有限RA增益和带宽保留。它含六级摘要、12次D2和8次tracking逐行观察、贡献算式，以及与模型/参数绑定的SHA。配套[节点图](runs/behavior_3cc384a0-3678-4709-8beb-cded2b86023c/sample_5_az.png)可按同一时间轴查看。

本次held=3.557564918V，一级D1=1932、残差5.564918mV，真实后级得到D2=2907、DT=85。数字分项`3.552 + 0.005546875 − 0.00000390625 = 3.55754296875V`，最终整数码**979654**。这是已记录支路的解释，不用理想输入覆盖输出。首次异常可沿held→D1/Qres→VX/VY→原始判决→数字贡献逐级定位。

## 结果、参数与边界

LVDS接入阶段的公开N8 [off](runs/behavior_f346bc5e-867f-48be-b3ac-085fa7e1bcfa/summary.json)为4.1919s，[RX on](runs/behavior_57add412-83ce-4070-8780-4e73759bf46f/summary.json)为5.1550s，[RX训练收集](runs/behavior_2d81bd58-eba0-498d-bd3f-4d5dea99bb94/summary.json)为5.5110s，均为单次真实计时，不作统计benchmark。训练收齐8条、fit调用一次后按欠秩门拒绝，无h/冻结；[Terminate证明](runs/az_probe_20261027T011012Z/receipt.json)与[主图训练结果](runs/behavior_2d81bd58-eba0-498d-bd3f-4d5dea99bb94/training.json)记录了真实Update后末态，OP仅作诊断。旧**直通RAW**的1024码冻结holdout SNDR为**117.7364dB**，同RAW名义支路101.6084dB；本组AZ/kTC/随机噪声关闭，不能当成已完成长RX校准。开启采样kTC与配对AZ/斩波的既有N256为**77.9401秒，SNDR102.2580dB，ENOB16.6940bit**。[结果、条件与未完成项](analysis/behavior/RESULTS.md)区分各配置；不能跨配置继承性能，也不是完整论文或180nm性能复现。

当前同一主图的[256码对照](analysis/behavior/RESULTS.md)：DAC关闭时SNDR **109.827136dB**，0.1ns为**109.844923dB**，1ns为**106.913367dB**。三组保存了各自SLX、完整P、源码、原字、整数码和频谱；关闭组的旧29路日志与先前[RX N256](runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/summary.json)逐位相同。1ns组有限RA和固定CINC负载仍开启，kTC/失配/DEM/dither/AZ/jitter/cal关闭；这不是全NI或完整论文复现。

**RA 带限噪声（2026-10-31 已接入主图）：** 由 `P.backend.ni.ra_noise=true` 与 `P.backend.ra_noise.sigma_vx_rms/seed_u64` 经公共入口 `SAR20('apply')` 生效。生产入口 N256 实测：OFF SNDR **109.827136dB**、ENOB 17.951352（73.05s）；ON（σVX=1mV、seed=20261030）SNDR **101.194257dB**、ENOB 16.517318（80.78s），与隔离对照五项逐位相同，[两案实际频谱](analysis/behavior/ra_ou_20261030/install_20261031/n256_prod_spectra.png)。N8 上 32 路日志与 3 根输出也分别与历史 OFF、隔离 ON 逐位相同，说明接入未改判决与时序。已补 6 个 seed 的统计：SNDR 均值 **100.654796dB**、样本标准差 0.413765dB、极差 1.181661dB，原单 seed 的 101.194257dB 位于该分布上沿；6 seed 均值比 OFF 低 9.17dB。σVX 与 seed 是测试假设，只改 seed、单频、256 点，不是 PSD 统计、M1/M8 跟踪收益或论文 7dB 复现；细节与回退见 [RA 结果页](analysis/behavior/ra_ou_20261030/RESULTS.md)。

同一主图另完成[AZ保持斩波＋混合18片τ的N8实跑](runs/az_probe_20261028T093824Z/receipt.json)及[RA/AZ近极点两侧的N8实跑](runs/az_probe_20261028T094010Z/receipt.json)，实际每ID保留12次D2、8次tracking比较及7次反馈；[隔离只读探针与独立公式核验](analysis/behavior/finite_dac_current_20261028/AZ_DAC_JOINT_ORACLE.md)将三组区间的预CINC RA端点与12态expm对照。这些短记录不产生频谱结论。[当前RX训练N8](runs/az_probe_20261028T094225Z/receipt.json)核对8条公开接收RAW与外部参考，fit一次后按欠秩拒绝，未生成h；旧直通RAW的长训练/holdout不能据此迁移到RX。

当前孔径误差N256整图对照：关闭时SNDR109.8271dB；上述combined开启时**SNR95.9983dB、SNDR95.7876dB**，实际held误差RMS41.556µV。它低于Rev0.5近100kHz主目标SNR100/SINAD98dB，暴露了这组时序参数的预算不足；单次sim75.17/75.80秒。其余多项NI仍关闭，不能宣称全非理想已达标。

**局部静态与A0：** 零点附近17个实际采样点中，16个负输入点均为524285，0V为524289；这只是有限点观察，不能断言缺码、单次跳变或全范围DNL/INL。[采样图](analysis/behavior/local_static_20261030/zero_samples.png)与[独立回读](analysis/behavior/local_static_20261030/zero15_independent.json)保留实际点。正侧码524290的局部DNL区间 **+0.001953～+0.005859 LSB** 是[条件推算](analysis/behavior/local_static_20261030/independent.json)，依赖未采样区间单调且每个包围窗只有一次相邻跃迁，这两个条件尚未证明。[A0两端对照](analysis/behavior/local_static_20261030/a0_independent.json)的实际码差在A0=1万、10万、Inf时分别为4、1、1码；其中1万复用旧`ae2d…`端点，另四点来自`a190…`，两版静态结构一致但跨版数值等价未另行实跑。结果支持有限RA增益参与此例误差，不证明它是唯一原因。

**单芯片DEM×dither：** unit σ=0.1%、seed=20261030为一颗行为失配样本的设计压力假设。Fs=5MS/s、Fin=97.65625kHz、N256、Bank/transport/校准关闭时，DEM/dither [00](runs/behavior_f6ed1267-fc88-4005-bc59-442bed4aac21/summary.json)、[01](runs/behavior_390aefe9-57d8-4f21-80d2-e362051f30bb/summary.json)、[10](runs/behavior_2d1c3ea0-ff5c-420e-aa9f-e47b46d92ceb/summary.json)、[11](runs/behavior_2f1b3c80-310e-4b05-a458-4e0b3a60d632/summary.json)的实际SNDR分别为101.568、102.050、102.027、101.971dB；[四组频谱](analysis/behavior/adi_20261030/adi_four_spectra.png)由保存的实际码重算。它不是PDK失配统计、全非理想覆盖或DEM/dither必然改善的证明。

[参数表](docs/PARAMETERS.md)列出位置、单位和有效范围。改AZ模式建议编辑工厂的`P.backend.az.mode`，后续统一派生数字模式；不要只改单边。`nominal.mat`是名义几何/尺度，不是训练系数。重新设计名义CT几何必须同步核对数字名义码权，不能假定单改电容会自动重建数字系数。

主图此前以31个真实DC仿真点在正侧约7.8–31.3µV定位三个相邻跃迁，得到码524290/524291的[条件局部DNL区间](analysis/behavior/RESULTS.md)；旧局部窗口与A0对照仍是历史证据。完整DNL/INL、零点跳码排除、更多噪声/失配/抖动及完整乒乓校准生命周期尚未完成。RX长训练/独立holdout的通过范围见结果页，不能外推到有限DAC＋校准、所有芯片或工艺。原论文与定义保留在`docs/`；未测项目不填0，关闭或0/Inf配置不计入覆盖。

此前固定失配四组N256的SNDR分别为101.122/100.703/101.340/101.283dB（DEM/dither＝00/01/10/11），单次75.3–78.6秒；本组AZ/kTC关闭，不能与上面的thermal-AZ配置混用。实际[ADI＋AZ联合ID5解释](runs/behavior_90c97b0c-9945-448a-867e-2735d45c02cf/sample_5_explain.md)可直接沿选片、电荷、VX/VY、判决到code979626阅读。联合例只作功能调试，不作为N256频谱记录。

**当前图形限制：** System图仍在做纯布局收敛，主链、日志和配置文字尚有拥挤；行为位门不等于视觉验收。每份导图须查看其各自metadata并核对模型SHA：[10月28日导图](analysis/behavior/current_figures/metadata.json)绑定旧版`63190994…`，[10月30日Bank接入导图](runs/work_20261030T125941Z/figures/metadata.json)绑定`ea39f94a…`。目前未发现与恢复后的`ae2d2b02…`模型绑定的原生截图，这两组图均不能冒充该模型的截图。
