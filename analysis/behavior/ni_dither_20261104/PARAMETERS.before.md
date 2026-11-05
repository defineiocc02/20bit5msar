# 行为工程参数入口简表

同一主SLX的LVDS、有限DAC→RA耦合及受限Bank A/B行为路由已接入；工厂默认N8、transport OFF、Bank OFF、DAC τ=0。[截图metadata](../analysis/behavior/current_figures/metadata.json)对应Bank接入前的2026-10-28模型；当前模型以实际SLX文件为准，运行状态见[检查点](../CHECKPOINT.md)。

编辑 `config/adc_parameters.m` 后，在目标 MATLAB 运行：

```matlab
SAR20('apply'); SAR20('check'); r=SAR20('run');
SAR20('sample',4,r.run_path);
```

固定参数已在各实例setup捕获；修改后必须apply/recompile，不支持仿真中热调参。run使用已保存的Model Workspace P/DecodeP，不自动读取或应用factory修改。N8先调试；N≥256才进行实际输出码FFT，耗时须用无profile真实run报告。图上的“已应用P”是说明文字，不是可编辑参数mask。

单次设计对照可直接取已保存P，改一个明确物理量，结束后恢复同一原配置：

```matlab
SAR20
ws = get_param('SarAdc','ModelWorkspace');
p0 = getVariable(ws,'P');
p = p0; p.backend.ra.A0 = 2e4;  % 示例：有限开环增益，无量纲
SAR20('apply',p); r = SAR20('run');
SAR20('sample',4,r.run_path);
SAR20('apply',p0);             % 恢复实验前P，而非重新读取工厂
```

无参 `apply` 会读取工厂；`apply(P)` 应用显式完整配置；GUI Run只运行当前已应用P，不自动apply，也不生成SAR20的run目录/摘要。需要可追溯sample时用`r=SAR20('run')`并显式传`r.run_path`。不要同时改多个物理量后用输出变好代替因果判断。字段 `P.ni` 是报告标签，不能靠改它开启模型中没有的效应；其A0/UGB与实际C的全部派生规则尚未收敛，报告非理想时要核对真实物理字段。

有限DAC的最小对照从完整的已保存P出发，修改18片共同τ，再通过公开入口重新准备；当前已验证的有限τ配置要求训练和冻结关闭：

```matlab
s = load('runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/parameters.mat','P');
p = s.P;
p.front.tau_dac_s(:) = 1e-9;                 % 每片1 ns
p.backend.dac_coupling = struct('enabled',true);
p.debug.dac_enabled = false;                 % N256只留必要日志
SAR20('apply',p); SAR20('check'); r = SAR20('run');
SAR20('apply');                              % 恢复工厂N8/off
```

| 配置字段/变量 | 单位 | 实际行为与边界 |
|---|---|---|
| `N`、`first_id` | 码数、零基ID | N是有效记录数，first_id以前真实运行作预热。factory同时生成足够长的同seed日历；不是回放旧码。 |
| `Ts_s` | s | 当前事件日历固定200ns/5MS/s；不是可以单独任意改变的采样率开关。改采样率须同步设计事件日历。 |
| `P.input.offset_v/amplitude_v/frequency_hz/phase_rad` | V、V、Hz、rad | 实际外部正弦/DC；幅度非负，频率不自动调谐。N256、5MS/s、97.65625kHz为相干bin5。 |
| `top_sampling_cap_f` | F/每半 | 八片总顶板电容，默认28pF为明确假设。信号电容为1024/1056比例，tail/bias另有真实负载。 |
| `options.vref_v` | V | 前端DAC参考；数字D1按同名义参考推导。CT参考另在nominal.mat。改参考需同步SAR1 delta及数字名义码权/FSR，是联合设计变更，不能把该字段当独立增益旋钮。 |
| `options.ktc_enabled/temperature_K/ktc_seed` | bool、K、uint32整数 | kTC已在实际capture向同一存储电荷注入一次；差分方差2kBT/Csample_half。这是理想源、充分建立、独立两半/片噪声的capture端点近似，不产生采集中完整随机波形。有效开启统计是enabled且T>0。关闭用false并保留298.15K；T0只是零噪声控制，不称热噪声覆盖。已通过整图关闭对照、同seed重复及256码动态验证；不是所有非理想已完成。 |
| `options.tau_sample_s` | s，0或Inf可用 | 连续正弦采样的一阶解析建立；kTC开启时必须全0，有限RC随机建立的联合模型未实现、明确拒绝。 |
| `options.tau_precharge_s` | s，0或Inf可用 | tail/bias预充一阶建立；默认0完全建立。它不表示已覆盖完整开关噪声/电荷注入。 |
| `options.tau_dac_s` / `P.front.tau_dac_s` | s，18片各一值 | 0为全建立、正有限值为DAC切换的一阶建立、Inf为保持负例。正有限值需同时设`P.backend.dac_coupling.enabled=true`，由prepare绑定同一18片映射和旧FE状态到RA；RA slew须为Inf。工厂默认0/off；不能只改单边。当前主图1ns已完成N8和N256实跑。 |
| `A.A0/UGB_hz/Cf_f/tau_reset_s` | 1、Hz、F、s | 设计者指定的单环近似与复位衰减：NG=1+Ctop/Cf，g=A0/(A0+NG)，τ=NG/(2πUGB)。这些不是从论文识别出的开环极点或稳定性。A0或UGB取Inf分别关闭相应限制；没有MNA/高精度子步。数字名义gain仍32，改变Cf不隐式用模拟真值修正数字增益。 |
| `P.backend.ra.vos_input_v/slew_v_per_s` | V、V/s | 输入失调和端点slew近似，slew=Inf关闭。不是晶体管级slew/噪声识别。 |
| `P.backend.ni.ra_noise`、`P.backend.ra_noise.sigma_vx_rms/seed_u64` | bool、V rms、uint64 | RA 带限 OU 噪声：区间内按差分 VX 固定极点稳态 RMS 加一次 OU 创新，重复 Outputs 用同一事件键、不推进全局 RNG。σ=0 是零激励诊断，不计噪声覆盖；seed 决定序列。ON 要求无限 slew、有限 UGB、DAC τ=0，且 AZ/kTC/比较器噪声/参考恢复/校准/Bank 关闭。1 mV 是测试假设，不是拟合电路参数。已接入主图并通过公开入口 N8 与 N256 回归（N256 OFF/ON SNDR 109.8271/101.1943dB）；单 seed、单频、256 点，不是 PSD 统计、跟踪收益或 PDK/硅结论。 |
| `P.backend.az.mode` | 标签 | off、ordinary、chop、hold、hold_chop；ordinary/chop逐样本写，hold类偶ID写、奇ID保留。chop类按公共ID使用POL[+−−+]；RA前完整Qres（含DAC1残差及tail-dither电荷）一起乘POL；数字仅解调D2/DT，D1原码和数字dither加回支路不翻。factory同步digital mode/NI；不得只改单边。 |
| `P.backend.az.write_tau_s/leak_tau_s` | 两半s | 输入参考感测增益假设为1，误差e=Vos−AZdiff，由参数化Vos源驱动有限写入RC；没有A1/A2内部晶体管节点或随机AZ热噪声。保存泄漏独立；AZ开启写tau须正有限，leak=Inf理想保存。信号复位不清存储，epoch变化撤销有效标签。写窗口当前固定CNV至31.25ns，不与RA读出重叠。 |
| `P.backend.az.sense_injection_half_v` | 2×K，V | 同ID选列的确定性感测扰动，不是随机AZ噪声。不得称已完成噪声统计扫描。 |
| `options.dem_enabled/dem_seed/pool_seed` | bool、整数 | 实际31个32-Cu组循环移位/18片池日历；不是独立随机或DWA。改变N只延伸同seed前缀。master `P.seed`仅标签，不自动改变这些独立seed。已做名义/固定失配的整图开关对照。 |
| `options.dither_enabled/dither_seed/dither_input_amplitude_v` | bool、整数、V | 输入参考标度a产生±0.5a/±1.5a，实际tail负预充源为−(1024/15)dn，数字同ID仅加回+dn一次。factory同步digital配置；已做真实电荷/整图对照。开关true而幅度0不算覆盖。 |
| `options.mismatch_enabled/C_f/Cp_f` | bool、18×38 F、18×1 F | 前端失配需显式非名义C_f；flag本身不生成失配。Cp为显式寄生。当前nominal.mat不含实际后端失配样本，单开backend cap_mismatch仍选同名义网络，不能称覆盖。 |
| `P.front.jitter.enabled/common_sigma_s/local_sigma_s/fixed_slice_skew_s/seed` | bool、s、s、18×1 s、uint32整数 | 默认off；公共/局部RMS非负，skew为有符号物理片偏移。seed/ID/epoch定义公共量，局部量再以物理片号为key；不是DEM观察顺序。仅移动signal端点取值，tail/bias及其余事件仍名义。enabled但RMS/skew全0是零激励对照；finiteRC+jitter拒绝。 |
| `P.backend.ni.cinc_kick` | bool | 标称2×2电荷解及瞬时delta-Q作用在同一RA输出，随后单极点恢复；默认开启。CINC900fF为明确工程选择，未做电路提取；replica匹配且瞬时，不含开关过渡及非零复制延迟。 |

这些项目前不可用：kTC+有限采样RC联合模式、全时钟抖动、finiteRC+jitter、AZ/参考/比较器随机噪声（RA 带限 OU 已接入，见上表）、非线性RA、参考恢复。有限DAC耦合已接入，校准关闭时已验证N8及0.1ns、1ns两组N256；AZ保持斩波与18片混合τ的N8功能实跑及近极点上下各1 ULP的预CINC端点独立区间核验已完成，N256联合性能待补。τDAC=0的RX长训练与新登记holdout已完成且只在其固定条件下通过，有限DAC与校准联合仍被拒绝。Bank已接入，但不同h切换、后台训练和真实drain尚未完成。未实现项应拒绝或保持明确关闭；`P.ni`是派生报告，不是独立功能开关。

## Bank 行为路由与复跑边界

工厂经prepare得到 `P.bank.enabled=false`，OFF为旧输出旁路；Bank ON是固定资格范围内的行为验证路径，并非通用产品校准开关。ON需要实际RX normal模式、M8日历和finite-sinc2、18片DAC τ全为0，旧训练及Frozen均关闭，数字旧校准模式为off。资格文件、公开配置/plan、算法源码及两个预装槽均须满足入口绑定检查；同芯片来源还依赖受控运行方，公开字段本身不能证明物理芯片身份。

| 字段 | 实际作用与边界 |
|---|---|
| `P.bank.enabled` | 默认OFF；仅改为true不能构成有效的Bank配置。 |
| `P.bank.slots` | 两个预装不可变版本，每槽含`version`与`cache`；当前资格要求两槽系数均匹配同一已锁定h，不能据此声称不同h切换已验证。 |
| `P.bank.qualification_file` | 必须是可读取且字节匹配固定资格的文件；该文件及资格状态只覆盖声明的行为配置，仍为`NOT_ACCEPTED`。 |
| `P.bank.initial_slot/lead_samples/command_schedule/provenance_scope` | 初始槽、发布提前量、预声明事件命令和受控来源声明；均须满足入口检查，不是在线训练或真实drain证明。 |

[2026-10-30 Bank三案](../analysis/behavior/n256_20261030/RESULTS.md)在同一行为芯片及同h下比较名义、Frozen和Bank ON：Frozen与Bank的256码逐位一致，ID0–3为版本1，ID4–259为版本2。三案的不同配置、实际频谱和未覆盖项见结果页；不能外推为完整乒乓校准或产品接受。已恢复工厂OFF并通过apply/check，恢复后没有再做OFF仿真。

历史Bank ON的 `parameters.mat` 将 `qualification_file` 保存为当次Windows临时目录的绝对路径；跨机或清理临时目录后不可假定该路径仍有效。要复现该配置，必须先核实际资格文件字节、绑定的完整P/plan和源码以及受控来源，再走`SAR20('apply',P)`、`SAR20('check')`、`SAR20('run')`；这不是重新完成独立holdout。

`SAR20('sample',id,copyRun)`现读取实际record时刻的Bank `code_valid`与`meta9`，同时检查RAW范围、同ID/epoch/valid、slot/version、fault及码范围。原始`code_valid`与综合检查结果分别显示；有唯一record时，`bank_log_join_valid`是上述综合检查结果，不仅是时间联接。D1/D2/DT/dither名义算式只作对照，Bank内部`u/Bh/den`及最终电压未记录。[复制run的ID4解释](../runs/work_20261030T151254Z/copied_run/sample_4_explain.md)及[公开入口回执](../runs/work_20261030T151254Z/receipt.json)记录Bank码587978、名义码587981、slot/version 2/2，范围仅为该实际样本。sample不会验证simout与可信回执的哈希绑定，不能证明文件未混档；证据用途须对照[原始三案回执](../runs/work_20261030T141338Z/receipt.json)自行核验输入文件身份。

sample会在所选run目录写入或覆盖同ID输出；先将完整历史run复制到新目录，再显式调用`SAR20('sample',id,copyRun)`，不要直接向原始归档写入。可复制的命令见[README](../README.md#打开调参复跑)。省略run路径时，latest指针也可能指向与当前已应用P不同的历史run。

## 复跑DEM/dither与同芯片对照

`config/make_adi_cases.m`由`SAR20('setup')`自动解析，无需加临时候选路径。下面仅运行八案例中的失配+DEM+dither案例；把索引8换为1..8可选其它组合。

```matlab
SAR20
ws = get_param('SarAdc','ModelWorkspace');
p0 = getVariable(ws,'P');
p = p0; p.front.dither_input_amplitude_v = 1e-3;
suite = make_adi_cases(p,8,.001,20261028);
p = suite.cases(8).P; p.debug.adi_enabled = true;
try
    SAR20('apply',p); r = SAR20('run');
    SAR20('sample',5,r.run_path);
catch err
    SAR20('apply',p0); rethrow(err)
end
SAR20('apply',p0);
```

案例1..4为名义C，5..8为同一颗固定失配C，每颗芯片依次00、01、10、11（DEM/dither）。σ=.001是unit相对0.1%的设计压力，不是PDK数据；N-Cu支路相对σ=.001/√N。八组共用输入/时序/名义数字码权；同芯片C固定，不重抽、不归一化。实际参数和结果全部存入各自run；使用`summarize_adi_cases(runPaths,suite)`可从八个真实N8 run重建描述性配对摘要。

`P.debug.adi_enabled`只开观察，不开物理功能。true只允许N8，记录实际选片、shift、目标电荷、CNV tail及控制计数；false仅留一行NaN。保存上限由prepare派生，勿手改`adi_max_points`。N8完整专项日志数值和时间轴约0.554MiB；N256关闭tap约6.38MiB，实际MAT文件约1.89MB，均无完整状态×事件日志。

八组N8及四组失配N256已完成整图实际对照；[结果](../analysis/behavior/RESULTS.md)明确配置和频谱。另有失配/DEM/dither+AZ/斩波的[真实ID5联合示例](../runs/behavior_90c97b0c-9945-448a-867e-2735d45c02cf/sample_5_explain.md)。这些不等于更多seed/频率、所有非理想或校准完成。

复跑某个已保存N256实验最直接：load该run的parameters.mat，`SAR20('apply',s.P); r=SAR20('run')`，结束后apply(p0)。若从工厂新建N256对照，可用`make_adi_cases(p0,256,.001,20261028)`；保持debug关闭，helper验证整个原plan前缀不变。

## 同一SLX的传输off/on

默认`P.transport.enabled=false`：原48组ADC执行，FPGA直读ADC Raw6/RawReady；Transport数字状态不推进。使用本文开头的完整P对照流程，将`p.transport.enabled=true`后`SAR20('apply',p); r=SAR20('run'); SAR20('sample',5,r.run_path)`才启用TX→公开pin→RX；结束仍恢复p0。GUI Run不自动apply/封存。仅run前切换，不表示支持运行中热切换。

ADC仍在CNV后86.25ns给早RawReady；on时sample N在N+2槽+138ns产生RX record，即距N的CNV约538ns。parent有49组，Adc第49组held；真实多跑两个CNV flush收末两样本，目标记录窗不变，不截尾补帧。时间显示以实际日志为准，不用538ns公式替代取数。32bit帧只含D1/D2/DT/VALID；RX的ID/epoch由公开CNV/EN计数恢复，不随wire传内部标签。

| 接收ready | 含义 |
|---|---|
| `frame_ready` | 闭帧/缺帧退休事件，含startup、test及无效帧；不等于ADC样本 |
| `raw_ready` | normal、非test、非resync且公开target非负的record；正ID无效槽仍为1，Raw6.valid=0必须保留 |
| `sample_ready` | raw_ready且Raw6.valid；不能用它删掉目标窗invalid后声称收满N条 |

`raw_log/ready_log`保留早ADC源；`record_log6/record_ready_log`观察实际FPGA输入（off直出/on RX raw_ready）；`paired_ref_log4`是外部仪器队列的真实输出，非close可NaN。code/d1/d2/dt/frozen按record实际消费时刻配对。sample物理图仍48事件，另列同ID/epoch的actual record候选与record CSV；负startup留在原始日志，不能重贴ID0或算有效码。新图on缺record日志硬拒，旧run仅transportoff允许legacy raw/ready。

[011447回执](../runs/az_probe_20261027T011447Z/receipt.json)已验证off原19日志位同、on ADC前缀/接收原字/数字贡献不变，以及N8 RX/pairedRef收集。公开off/on/训练单次sim为4.1919/5.1550/5.5110s，不当统计benchmark。N256接收的[实际结果与位门](../runs/behavior_c9d33df5-a215-44c8-984c-224b70fd37c1/transport_validation.json)核256原字/码与旧nominal256逐码相同；89.7097545s，SNDR109.827136dB，其余谱指标见README。该组kTC/失配/DEM/dither/AZ/jitter/cal均off，不能概括为全NI或完整论文复现。

## Signal端点孔径：先N8定位

物理开关在`P.front.jitter`；各时间输入均为秒，图上说明与sample相对量换算为ps。`first_coarse_offset_s`由prepare从真实日历派生，勿手填。实际孔径须严格位于实际开采时刻和CNV后coarse latch之间；越界报错，不钳制、不重抽。此模式要求前端充分建立；不能把名义事件时刻的有限RC电荷当实际孔径处的状态。

沿本文开头保存p0/恢复p0的单次对照方法，可将参数改为：

```matlab
p=p0; p.N=8;
p.front.jitter.enabled=true;
p.front.jitter.common_sigma_s=25e-12; p.front.jitter.local_sigma_s=10e-12;
p.front.jitter.fixed_slice_skew_s=linspace(-8e-12,8e-12,18).';
p.front.jitter.seed=20261029; p.debug.aperture_enabled=true;
% 接本文开头try/catch中的apply(p)→run→sample，再恢复p0
```

`P.debug.aperture_enabled`默认false，仅N8可true，作用是记录pure `aperture_log28`，不启用物理jitter。默认只留一行NaN；开启取actual CNV的Sample.next353，不接最终返回或旧UnitDelay状态。日志为`[ID,epoch,valid,nominalCNV,physicalIDs8,actualTap8,acquireOpen8]`，时间秒制；sample仅saved P启用jitter且实际日志有效才显示8片表及CSV，未知/NaN明确未记录。前端同一状态从317扩为353：追加18片实际孔径与18片开采时刻，未增加状态owner。

[六例主图回执](../runs/az_probe_20261026T233611Z/receipt.json)已通过off、common25ps、local10ps、固定18片±8ps、三项联合、联合同seed重复；off旧18日志逐位一致，联合重复19日志逐位一致。联合[ID5解释](../runs/behavior_2b9d513a-14ba-4073-af20-61c3906f612b/sample_5_explain.md)与CSV给出实际8片孔径。后续实际N256 off/combined的SNDR为109.827/95.788dB，后者未达到本项目近100kHz的SNR/SINAD目标，条件与原始结果见[RESULTS](../analysis/behavior/RESULTS.md)。这是当前配置的功能/动态证据，不宣称随机统计认证；full clock jitter与finiteRC+jitter仍未实现，tail/bias不随孔径移动。

## 训练、冻结与一个sample的来源

实际路径为`SarAdc/EventStep/TrainRef`（片外仪器）及`SarAdc/EventStep/Fpga/Calibration/Train`、`FrozenDecode`（片外FPGA）。TrainRef在CNV锁存`Ref4=[Vdiff,ID,epoch,valid]`；off在RawReady配对，on由外部参考队列延迟到同ID/epoch的RX record-ready配对。理想外部reference误差为0是试验假设；不读取held、残差或actual C生成答案。ADC RawReady仍不等于RX接收ready。

| 保存字段 | 实际作用 |
|---|---|
| `P.training.enabled/reference` | 默认off；on时按公开RAW/Ref收帧、收满在Update拟合一次。训练期间与拟合后主码仍直通NominalCode，不自动激活h。 |
| `P.frozen.enabled/cache` | 默认off并原样旁路；on时须training off，cache的公开配置/生命周期严格匹配。只消费固定h，不重新拟合、不读取actual C。 |
| `P.debug.adi_enabled` | 仅专项N8观察；与训练/冻结物理开关无关。 |

训练、冻结与评价仍统一由`SAR20`进入。公开freeze/evaluate已通过原生验证，1024帧RAW/code与原holdout逐位一致，结束恢复起始P；新入口train本轮未再重复2048帧，已有主图2048训练结果见下方链接。不手动操作Workspace或用临时脚本绕过绑定检查；Bank的受限行为路径见上节。

**用法一：重新训练、显式锁定、独立评价。** 从符合预注册静态协议的默认N8配置开始；三个动作互不自动调用。

```matlab
tr=SAR20('calibration','train');                % 新2048帧主图训练
lk=SAR20('calibration','freeze',tr.workflow_path); % 只锁候选，不仿真
ho=SAR20('calibration','evaluate',lk.workflow_path); % 固定h的1024帧holdout
SAR20('sample',5,fullfile(fileparts(which('SAR20')),ho.actual_run));
```

**用法二：复用已有真实训练，不重训。** 显式给出工程相对路径的原训练与事前协议；freeze只读并核身份，不补造训练回执、不重拟合。

```matlab
prior=struct('training_run','runs/behavior_30bb3ff5-8668-4149-a3c5-1ca5d6dabed7', ...
    'registered_protocol','runs/az_probe_20261026T222506Z/protocol.json');
lk=SAR20('calibration','freeze',prior);
ho=SAR20('calibration','evaluate',lk.workflow_path);
SAR20('sample',5,fullfile(fileparts(which('SAR20')),ho.actual_run));
```

每步新建`runs/calibration_<phase>_<uuid>`，返回工程相对`workflow_path`；实际仿真路径为`actual_run`。train先封存协议SHA再生成数据，Update收满拟合一次；freeze保存固定C及h/文件/公开配置SHA；evaluate只跑既定holdout，不更新h。train/evaluate正常或异常均尝试恢复真实起始P，检查回执`configuration_restored`；freeze不改模型。普通apply/run不自动训练，GUI Run不执行这些封存/门限步骤。

注册静态bench拒绝`front.jitter.enabled=true`（即使幅度全0也拒绝），不把新孔径实验混入已注册校准结论。训练自动保存`training.json/mat`；先核rows=2048、fit_calls=1、rank=684及拒绝原因。新record图的最终训练证据使用已验证的Terminate回执：`TrainCaptureFile`默认空；`SAR20('run')`仅通过SimulationInput设置本run路径，Terminate只读Update已提交的4组DWork写`training_committed.mat`，不新增事件/fit/Outputs写。finalOP与最后Outputs只作诊断，不能代替最后Update提交。[主图RX N8](../runs/behavior_2d81bd58-eba0-498d-bd3f-4d5dea99bb94/training.json)实收8条、fit一次，按rowbound拒绝（nullity下界676），h/frozen为空；[011012](../runs/az_probe_20261027T011012Z/receipt.json)是该Terminate路径的先行证明。这不等于2048训练成功。TRAIN为epoch1、fin=90332.03125Hz；HOLDOUT为epoch2、1024帧、fin=112304.6875Hz；同2056行plan、同芯片/公开配置与固定门限。不能用holdout选择h、刺激或阈值。底层`make_training_case`第三参数仅为参考来源声明，不读协议文件；workflow负责事前封存，无需用户手工串联helper。

旧**直通RAW**路径的[实际训练](../runs/behavior_30bb3ff5-8668-4149-a3c5-1ca5d6dabed7/training.json)已得到全684秩，训练RMS=1.7570µV；[固定h的实际holdout](../runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/holdout.json)通过事前门限，电压RMS=2.6503µV、最大误差=7.9906µV，无refit/gain-offset拟合。冻结输出SNDR=117.7364dB。这些是历史直通RAW证据，不能充当本次RX结果。

RX路径另以[训练前登记的协议](../runs/az_probe_20261028T100042Z/rx_protocol.json)运行2048条训练，684列满秩、训练RMS1.7570µV；显式冻结后，在新epoch3/bin29/phase2.137的[1024条实际RX holdout](../runs/behavior_dc38bf72-b9b2-42e6-a9d5-6b76a32a671f/summary.json)上得到取整前电压RMS2.6251µV/max7.0663µV，整数中心RMS3.4766µV/max10.0936µV，按原门通过，冻结输出SNDR117.4582dB。详见[结果](../analysis/behavior/RESULTS.md)和[独立后验回读](../analysis/behavior/rx_holdout_20261028/independent_attempt1.json)。仍限同一固定失配芯片、DEM/dither on、有限RA、无kTC/AZ/随机噪声、理想外部参考；不是完整论文复现或产品校准验收。该holdout的`accepted=false/activation=none`，C仍`NOT_ACCEPTED`，没有自动激活系数bank；后续Bank同h功能验证见上节。

**已有证据重放：** 也可从工程相对`runs/behavior_f2d62e08-2366-48f9-be8c-a500bf015d68/parameters.mat`读取完整P，沿本文开头的`apply(P)→run→sample→恢复p0`复跑同一固定h配置。这只复现保存实验，不替代新训练、重新锁定或独立holdout回执；不把历史artifact路径加到MATLAB path。

sample先读六阶段摘要，再读12次D2/8次TA真实逐行判决。冻结模式必须saved P enabled且actual `frozen_log`同record-ready实际时刻且同ID/epoch行used=1：最终V直接取diag9，核`V=(u+Bh)/den`和`clip(round(V×2^20/(2Vref)+2^19))`。u/Bh为RA域V，den无量纲；h哈希来自保存cache。原D1/D2/DT/dither贡献保留为名义对照，不再冒充最终calcode来源；分组诊断不替代canonical Bh或再加一次dither。数字实际值移到独立record CSV（D1/D2/DT/code、u/Bh/den/voltage/valid/used），nodes CSV保持48个ADC事件。缺失/重复/invalid及NaN保留诊断，不拿ADC原字补接收记录。`SAR20('run')`复跑保存配置并封存结果；独立holdout门限核验是既有`holdout.json`回执所记录的额外分析，不由一次普通Run自动宣布通过。

## N8→N256受控延伸

通常在factory把 `N=8` 改为256后执行上述apply/check/run，factory自动给出同seed长plan。若实验脚本直接修改已有P，必须同时扩大 `P.front.plan_rows`、清空待重建的 `P.front.plan`，再prepare，并逐项断言新plan的**整个旧长度前缀**与旧表完全相等。保持input、C、pool/DEM/dither/kTC seed、epoch和NI开关不变；通过 `SAR20('apply',P)` 统一应用P、DecodeP及可见说明，再 `SAR20('check'); r=SAR20('run');`。不要自行assign/save绕过说明一致性。实验结束用apply(p0)恢复实验前配置；只有明确要恢复工厂默认时才用无参apply，历史run目录不覆盖。

本节是Bank OFF的一般实验指引；Bank ON受资格、plan、源码和槽内容绑定，不能照此直接延长plan或改变配置后假定仍具资格。

参数捕获补丁已通过实际同图12路逐位门与参数切换；N8 6.6428914→4.3252889s是单对无profile计时，不能称统计benchmark。hold_chop有限leak复跑3.8009591s属于另一次模式验证，不与前一对混作提速比例。

**当前限制：** System布局仍在收敛，不能把日志位门当视觉验收；图像的导出模型身份查current_figures/metadata.json；当前SLX可能因保存参数而具有不同字节身份。
