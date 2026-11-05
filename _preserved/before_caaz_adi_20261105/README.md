# SAR20-5 Simulink 行为模型

当前工程为 **5 MS/s、单物理前端、默认256码的正常工作点估计**。唯一公开入口是 [SAR20.m](SAR20.m)，唯一开发模型是 [current/models/SarAdc.slx](current/models/SarAdc.slx)。八个前端条目是同一阵列的数值分段；ADI、DEM、dither、LVDS传输和校准均未启用。

实际运行主机为 Windows MATLAB R2024a Update 6，路径 `D:/Academic/Projects/sar20m1/SAR20`。本机镜像的模型和119个工作文件与已验证Windows版本逐SHA一致；本机未运行MATLAB。2026-11-05当前SLX SHA前缀为 `91973cf76507`。

## 打开、改参数、复跑

在Windows MATLAB中运行：

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20('open')
% 改下表中的参数后：
SAR20('apply')
SAR20('check')
r = SAR20('run');
s = SAR20('sample',5,r.run_path);
```

| 修改入口 | 内容与单位 |
|---|---|
| [config/adc_parameters.m](config/adc_parameters.m) 顶部 | N、差分偏置[V]、输入峰值[dBFS]、频率[Hz]、相位[rad]；默认N=256，改8作短调试 |
| [config/normal_parameters.m](config/normal_parameters.m) 顶部 | 实体非理想开关、匹配σ、温度[K]、Cp[F]、采样/DAC/AZ时间常数[s]、RA A0/UGB和噪声、比较器噪声 |
| [config/normal_10v_configuration.m](config/normal_10v_configuration.m) | 固定量程与名义数字尺度关系，常规运行无需修改；10V差分量程来自对论文5Vp的明确解释假设 |

修改工厂文件后，**apply**才会重新准备P/初态、更新模型工作区和框图说明，并保存SLX。**公开run**读取已应用P，建立新的UUID结果目录，保留SLX、参数、源码快照、simout、原码和适用的指标。**GUI直接Run**使用当前加载模型工作区P，包括尚未保存的手动编辑；它不会重新读工厂文件，也不建立完整的公开入口归档。

短记录N<256不计算动态指标。长记录若不满足当前相干FFT条件，会保留时域结果并明确标记频谱未运行；不要据此填写零指标。当前FFT要求二次幂N、带内相干正弦；论文20k点和其他窗口分析尚待扩展。参数不支持运行中热改。

## 顺着框图阅读

按 `Driver → EventStep/Adc → EventStep/Fpga → Record` 阅读：

1. **片外Driver**提供偏置、幅度、频率和相位描述符。
2. **片内ADC**完成采样、6位预转换/SAR1、DAC1残差、32倍名义RA/AZ、CINC连续时间二级、12次D2、8次tracking比较/7次反馈。RA后没有新增S/H。FE353、RA48、SAR51分别由唯一UnitDelay保存；多级Advance/Commit包装共享同一条状态链。
3. **片外FPGA**按公开D1/D2/DT与名义系数重构；SINC²包括第8次数字贡献，但只有前7次物理tracking更新。
4. **Record**按sample ID/epoch收集有效帧。看 `RecordReady` 和RAW的valid字段；顶层 `CodeValid` 是旧系数Bank资格输出，当前未校准时它可保持0，不能拿它代替采样有效性。

RAW顺序为 `[D1, D2, DT, sample_id, epoch, valid]`，分别为11/12/8位原始判决字及配对标识。默认校准、训练、Bank及transport均OFF，旧池/Bank结果不代表当前单阵列结果。

## 本次实际结果与调试样本

当前工作模型经真实apply、冷开、编译和公开256码运行，参数、RAW/code/time、9路关键日志和3个根输出与已验证正常配置逐位一致。Fs=5MHz、Fin=97.65625kHz、峰值−1dBFS、差分FSR=10V：

| SNR | SNDR | SFDR | THD | ENOB |
|---|---|---|---|---|
| 99.712 dB | 99.133 dB | 111.784 dB | −108.166 dB | 16.175 bit |

[当前释放回执](analysis/behavior/public_normal_20261105/release_actual/release_receipt.json) · [实际运行目录镜像](analysis/behavior/public_normal_20261105/release_actual/behavior_12d08121-d679-40cd-9ee2-bc334ff42955/summary.json) · [频谱对照图](analysis/behavior/normal_workpoint_20261104/figures/normal_fft256.png)。频谱图所用早期同参数记录与本次256条RAW/code/time逐位一致；新模型、新运行及新谱分别保留身份。

ID5：RAW=`1924/2473/19`，Code20=`979623`。名义输入域分量为D1=4.3408203125V、D2=+1.609375mV、DT=−19.53125µV；相加再量化得到该整数码。这些是数字分量，不是模拟残差探针。[逐码说明](analysis/behavior/normal_workpoint_20261104/review_public_raw_20261104.QW7Dbe/normal_merged_n8_20261104/per_record.csv)。

RA在CNV后31.25ns接入，首次D2为45ns，tracking为75–83.75ns，RAW在86.25ns，release在90ns，guard后92ns开始下一采集。逐沿分配是当前设计假设，论文仅披露约90ns转换等总节拍。[RA启动细化图](analysis/behavior/ra_dense_observer_20261105_qT32fM/figures/ra_start_dense_sample5.png)区分了真实事件节点、Qres/Cf驱动和无新增OU创新的条件漂移；中间线不是实际随机轨迹。密集诊断副本与正常N8的旧输出位同，仅物理核验时保存全状态。

## 证据边界与暂不用看的目录

本次启用有限采样RC/kTC、固定DAC1/指定CINC失配、前端Cp、有限DAC建立、RA有限A0/UGB/Vos、普通AZ、A1通道热噪声OU代理及SAR2/TA比较器噪声。[非理想三态表](analysis/behavior/normal_workpoint_20261104/NORMAL_NONIDEALITY_COVERAGE.md)区分实现、实际开启和扫描；尚未完整计入driver/reference、其他RA级、随机AZ/1/f、SAR1/Flash噪声、全时钟/孔径误差和有限slew。

目前是正常参数单点行为验证；M1/M8收益、前景校准/独立holdout、多频/幅度/seed及合格静态DNL/INL仍待完成。不能由256点FFT推出DNL/INL，也不能据行为模型虚构功耗、面积或工艺签核。

首次阅读暂不用看历史 `analysis/`、`runs/`、`_preserved/`。它们保留原始数据、as-run源码和可回滚旧工作版本；当前入口只指向current。旧产品合同仍在docs中，当前论文单bank/10V估计配置不替代未来产品电压与外部接口合同。ADI及10MS/s须获用户同意后再启用。
