# SAR20 隔离候选：覆盖摘要与零幅 dither

本目录是仅供审阅的 `/tmp` 副本。没有写入生产目录、启动或连接 MATLAB/Simulink，也没有加载或保存主图。**测试脚本已准备，但没有执行；不得将本候选称为已通过 MATLAB 数值验证。**

隔离树建立后，其他并行工作更新了生产中的 `current/src/analysis/behavior_spectrum.m`；本目录保留复制时的旧频谱文件。两者哈希见清单，频谱文件不在本任务补丁内。**不要用整棵隔离树覆盖生产目录。**

## 改动

- `config/adc_parameters.m`：工厂摘要中的 `sample_settling` 只计算大于零且有限的采样时间常数；`Inf` 仍是物理保持配置。
- `behavior_prepare_configuration.m` 与 `behavior_ra_noise_guard.m`：无论 RA OU 噪声开关状态如何，应用配置时均根据同一套物理值派生摘要；调用实际后端参数入口时检查陈旧标签。配置中未实现的参考恢复或比较器噪声摘要为 true 时拒绝。重新应用时可补齐缺失摘要并按物理值更新。`az`、`dac_settling`、`parasitic`、`sample_ktc`、`jitter` 和已有 `ra_noise` 在进入 guard 前就被重新派生，旧值即使为 NaN 也会被覆盖；`ra_finite_gain`、`ra_finite_bandwidth`、`sample_settling`、`cap_mismatch` 若已有非布尔值，guard 会拒绝。
- `public_calibration_config.m`：公共配置投影接受 `dither_enabled=true` 且幅度 0；保留原始使能、seed 和 0 幅度，前后端连接一致性校验不变。
- `behavior_training_configuration.m`：上述零激励配置仅用于普通路径，训练、Frozen 和 Bank 使能均明确拒绝。后端参数 guard 在直接使用模型工作区配置时检查前后端 enable、seed 和幅度是否仍一致，并阻止准备后把普通零幅配置改为训练、Frozen 或 Bank。
- `behavior_cal_collector_step.m`：训练收集器直接以 enabled 配置初始化时，沿用原特征生成器对 dither 的准入规则，在接收任何数据行之前拒绝启用但幅度为零的配置；禁用收集器仍接受零激励的普通配置。

OU OFF 时，实际与名义 CT 网络可以分别采用 10+2 或 6+6 的12位切分；不同切分按非名义网络计入 `cap_mismatch` 摘要，并不证明实际器件随机失配。二元素 `bridge_f` 只通过侧索引参与 CT 和 replica 计算，行、列向量值相同时不单独计作失配；CINC 和其他向量不做该归一化，因为未纳入本次等价范围。OU ON 沿用原有的同形资格门。

`P.ni` 反映配置中的启用参数，不证明每个受影响物理片在某次有限记录中都被使用；寄生项仍只指现有的前端 Cp 与启用的 RA 输出负载，并不代表完整 CT 寄生。原有不支持的非理想组合没有放宽。

`behavior_public_cal_features.m`、`behavior_public_cal_fit.m`、前端/后端物理核、Bank 资格代码和 `nominal.mat` 未修改。公共投影能表示零幅，并不表示零幅具备训练资格；原特征生成器仍拒绝 enabled 零幅，拟合、秩门、信息边界和冻结缓存资格未放宽。

兼容性：OU OFF 下检查摘要现在也会发现旧配置的字段缺失或陈旧值。重新准备可从实际参数补齐缺失字段并重算；未被提前重新派生的畸形字段与虚假的未实现项应修正后再准备。任何主图导入前均应验证历史配置与资格，不能把此静态候选直接当成可部署版本。

## 预备的测试

`tests/test_ni_candidate.m` 是一个纯函数级测试。它分别使用隔离候选与保留原语义的重命名基线，覆盖 OU OFF/ON 的配置派生、旧摘要负例、正有限/Inf、采样 kT/C、孔径、前后端失配、零幅和非零 dither、非法前后端连接、直接篡改后的拒绝、零幅收集器直接初始化时的拒绝及非零正例、OU OFF 不同 CT 切分的前后端对照，以及 N8/684 列欠秩与参考隔离。脚本包含前端一步及 RA 一步的物理参数/状态对照；它不执行 SLX 仿真，也不代表完整波形、动态性能、PVT 或产品验收。

将来获得运行许可后，在一个**新开的** MATLAB 进程中执行，例如：

```matlab
addpath('/tmp/sar20_ni_candidate.yAbWvD/tests');
test_ni_candidate
```

测试需有 MATLAB JVM（现有 RA OU 的 SHA-256 键依赖 JVM）。如在其他机器运行，复制整个候选目录，并按复制后的路径添加 `tests/`；脚本从自身目录定位源代码。首次执行之前应先核对 `MANIFEST.json` 与本机源代码身份。预期末行是 `PASS: isolated NI/dither unit tests, OU OFF+ON. No Simulink simulation performed.`；未见该行或任一异常均不能宣称通过。仅在上述函数级测试通过后，再安排受控的隔离主图编译、OFF/ON 短记录及物理/输出回归。

`candidate.patch` 是审阅用差异；`MANIFEST.json` 记录原文件和候选 SHA-256。`baseline/` 的四个文件仅重命名入口与相应内部调用，供脚本同进程对照；它们不覆盖生产代码。
