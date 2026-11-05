# 6319 设计者阅读入口：最小更新候选

仅供审阅：未修改工程内 README、参数、源码、SLX 或运行环境。三份补丁分开：

- `docs_candidate.diff`：README 与参数文档的文字修订；
- `source_comments_candidate.diff`：纯注释，不改非注释 MATLAB 行，但仍会改变源码 SHA；
- `factory_assumptions_candidate.diff`：改变 `adc_parameters` 返回的 `P.assumptions` 字符串，**不只是注释**，会改变 P 与源码身份。正在执行的身份门结束之前，三份都不要应用。

[manifest.json](manifest.json) 保存 6319 模型及九个原文件/候选文件的 SHA；[verification.json](verification.json)记录 `/tmp` 副本上的补丁往返、源码非注释行一致及现有证据交叉核查。候选只针对 manifest 所列原始哈希，文件若已变化须重生成/重新审阅，不能强行套用。

| 位置（原文件行号） | 原描述或缺口 | 替换意图与证据 |
|---|---|---|
| `README.md:3,86` | “DAC建立关闭”“DAC关闭时”容易被读成 DAC 不工作。 | 改为“耦合off且τDAC=0，理想即时建立；DAC本身仍工作”。有限 DAC 已接，默认仅是关闭耦合及零时间常数。 |
| `README.md:14,18,48`；`docs/PARAMETERS.md:62` | 片池与未接的乒乓Bank只在不同处提及；阅读入口未明确 M1 的集成状态。现有文档**没有**宣称 M1 已接。 | 明确片池不是校准系数Bank；主图固定 M8，M1 是隔离 scratch 的 N8 功能对照，N256性能未测。来源 [114345独立回读](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/m1_m8_20261028/sar20_independent_m1_114345_REVIEW.md>)；避免把 scratch 实测冒充主图集成。 |
| `docs/PARAMETERS.md:50` | “正有限值需 coupling”未说明 Inf 也非零。 | 按 `behavior_dac_coupling_configuration` 的实际 `enabled || all(t==0)` 和 `slew=Inf` 条件明确 Inf 需要启用；只有 0/Inf 不计有限建立覆盖。 |
| `README.md:94` | 有局部 DNL 限定，但把新近零 A0 对照笼统归入旧证据，容易把有限端点观察当全范围验证。 | 补 −LSB/4096 和 0V 的 A0=1e4/1e5/Inf 实际端点码差 4/1/1；新点在复制图、旧锚在原图，缺同 A0 跨环境逐位门。该对照支持有限增益的影响，不证明唯一根因、窗内缺码、完整 DNL/INL 或产品合格。原零点未单独保存当时 P，后续重建；详见 [A0独立回读](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/local_static_20261028/sar20_independent_gain3_120823_REVIEW.md>)。 |
| `README.md:84,88` | 历史直通 RAW 训练不能迁移到 RX 的句子与已有新 RX 训练相邻，容易读成新 RX 训练尚未完成。 | 明确旧直通结果不是 RX 证据，当前独立 RX 训练/holdout 是另一条已完成、条件受限的记录。 |
| `README.md:86后`；`docs/PARAMETERS.md:174` | 老 N8 单对较快并不证明目前 N256 提速。 | 加入 [121500独立回读](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/event_lookup_20261028/REVIEW.md>) 的 N256 旧→新单对 136.147900→136.908603 s，30路逐位相同但未提速、候选未晋升；[122805原生profiler回执](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T122805Z/validation/receipt.json>)标记独立回读待完成，插桩 182.056 s 与未插桩值不能形成速度比，含子时间不能相加。 |
| `current/src/model/behavior_dac_coupling_configuration.m:3–4` | 仍称 candidate，并声称 prepare 拒绝有限 DAC；与实际绑定相反。 | 改为 prepare 归一化后绑定 enabled、tau、schema 和 plan，不改 FE 状态或日历。 |
| `current/src/physics/behavior_backend_stage.m:11`、`behavior_backend_step.m:19` | 仍写 candidate；stage 原注释易误解第4口读取条件。 | 澄清 enabled/非零 τ 时 Sfun 供应旧 FE；只有保留命令 RA on 且非 reset 才构造区间 forcing。 |
| `current/src/control/behavior_sar_step.m:31`；`current/src/transport/sar20_lvds_rx_step.m:252`；`config/make_adi_cases.m:74` | `bank` 字段或“bank-specific kappa”可能误读为有系数乒乓。 | 前两处注明 ID 奇偶标签不是系数Bank选择；第三处准确称每个样本选片的模拟 kappa。 |
| `config/adc_parameters.m:138,140` | 仍写“Sampling/DAC finite-settling tests pending”和“No calibration”，与有限 DAC、显式训练/冻结已接入的状态混淆。 | 仅称工厂默认采样/DAC 时间常数为零，校准模式需显式配置；无 pin 电气时序 signoff。此条改变 P 字符串，单独审阅。 |

附带发现：README 链接的 `analysis/behavior/RESULTS.md:281,284–285,298` 后部历史表/后续计划仍写“AZ＋混合τ整图待验”及“RX长校准未验”，而该文件首部已有对应 N8 与受限 RX 长训练/holdout 的后续证据。为遵守本次 README/PARAMETERS/源码的限定，**未纳入补丁**；若统一结果页，可将这些行标为当时四组 ADI 的历史状态并链接首部新证据，仍保留联合 N256、不同芯片/PVT、Bank 和产品验收未完成。

本次验证只复核已存 JSON/回读及 SHA，没有重新运行 profiler、A0、N8 或 N256；不产生新的仿真、速度、精度或 DNL/INL 验收结果。
