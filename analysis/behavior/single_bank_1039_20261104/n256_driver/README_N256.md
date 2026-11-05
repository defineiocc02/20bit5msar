# 单前端 1039Cu N256 频谱驱动（未运行）

本驱动以真实函数测试 P（SHA `dfa91dda5a686563b9b0fe17c5e8d906d94e6ff9168251bc27a0830099947e4f`）、同一实际单bank N8模型 `48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3`、v2源码 manifest `2cbdffe537b694cef6107ce893ea8bca7f8ef5d95f6ff7d993f020150c6dd514` 为输入。目标是产生 **Fig.7 对照语境下的真实模型频谱**；不是论文图原数据、20k点FFT、完整非理想或工艺/芯片验收。

原P已是 `Fs=5 MS/s`、`Fin=97.65625 kHz`、`A=3.650563842595822 Vpeak differential`、`phase=0.731 rad`。它在N256恰是相干bin5，因此不调整输入。明确只将 N=8→256、plan_rows=32→264，重新prepare生成相应260周期日历/stop、公开计划和失效训练配置尺寸；`P_difference.json`列出全部字段路径，`P_diff.mat`保存每一项的旧/新原始值，`P_used.mat`另保存完整P和原P。白名单外任何差异在仿真前报错。A0、UGB、Cf、单元电容、DAC/采样/复位tau、guard、输入幅相等物理参数均不得变。

原P的普通AZ、采样kTC、RA OU、比较器和参考噪声、DEM/dither/jitter、旧池校准/Frozen/Bank和传输均关闭；有限RA A0/UGB及现有CINC配置保持原值。`tau_sample=0`、`tau_DAC=0`和`guard=0`是已测试P的理想假设，不能描述成真实器件无误差。P的Vref和差分量程仍是工程假设，不自动等同论文5Vp口径。

## 外层任务组织

外层创建全新 `D:/Temp/SAR20SBN256_<id>`，复用经逐文件SHA确认的私有runtime（不改源码），放入 `runtime/`；将此包的 `scripts/` 放入 `jobRoot/scripts/`。`inputs/`放如下真实文件：

| 文件名 | 固定SHA256 |
|---|---|
| `MANIFEST.json` | `2cbdffe537b694cef6107ce893ea8bca7f8ef5d95f6ff7d993f020150c6dd514` |
| `single_bank_P.mat` | `dfa91dda5a686563b9b0fe17c5e8d906d94e6ff9168251bc27a0830099947e4f` |
| `satk_receipt.json` | `c0502a7519395b297aca991492826799778826e563a7e877a05b993ca5bcfd49` |
| `graph_audit.json` | `27be1fa393e4bf2df1910bdbf6d759ec8cf7296adcb5e8a0f5706161a54bc8ed` |
| `n8_complete.json` | `eb77410ab643ce7484f025a3e19d4927338d317322b40623e3374ddeaa53e51b` |
| `n8_simout.mat` | `d472f01a80a832cd483783e4ceca0640a692e0094d1a64f5400411e5201a934c` |
| `n8_P_used.mat` | `236ddfb427dfc07e7f7e27dd58746deb30946891717d255b53789aa8127a1e9f` |

控制器解包前后逐文件核清单、递归拒绝reparse/symlink、绑定真实 Windows 最终路径，启动一次新的 headless MATLAB batch；不连接或关闭现有交互会话。入口：

```matlab
addpath(fullfile(jobRoot,'scripts'),'-begin');
sb256_case(jobRoot);
```

模型以SimulationInput临时覆盖P，不在图上apply/save；结束前校P/DecodeP workspace、源文件、P原件、模型字节和RNG不变。该运行是隔离图证据，不是公开 `SAR20('run')` 入口验收。失败保留P、Pdiff及已存在的simout/原码，不自动重试或覆盖。

## 结果与检查

`n256/P_used.mat`、`P_diff.mat/json`、`simout.mat`、`raw_capture.mat`、`selected.mat`、`spectrum.mat/json`、`validation.json`、`actual_spectrum_256.png/.fig` 和 `complete.json` 各自保留哈希。先核260×48实际EventLog、RAW/ready、全部260条ID/epoch/valid及所选ID4–259，再核前8条RAW/码/时刻与同模型、同物理参数的实际N8逐位相同。debug关闭时 12/8/7 是日历token，不声称已独立观察提交状态。

由项目已验证 `behavior_spectrum` 直接从256条真实整数码计算矩形窗、单边谱：SNR排除H2–H10、SNDR含畸变、SFDR取最大其他谱线、THD为H2–H10之和、ENOB=(SNDR−1.76)/6.02。MATLAB实际绘图使用相同的谱功率，dBFS参考为满量程正弦RMS功率 `(FSR/2)^2/2`；零功率点不画、原始power保存在MAT。图内标N、Fs、Fin、实际差分峰值、A0/UGB/Cf、tau/guard、seed、MATLAB版本及UTC。端点码数量单独报告，不能掩盖削顶。图是独立模型数据，不声称复制论文测量值。
