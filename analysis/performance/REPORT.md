# SAR20 局部矩阵复用：实际整图验收

2026-10-26。唯一工程入口仍是根目录 `SAR20.m`，参数为 `config/parameters.json`。本轮优化已通过同一步长的整图逐位门；这不代表论文性能、数值收敛或独立电荷验证已经通过。

## 实际改变

`pool_cached_predict` 在单次预测调用内复用网络矩阵模板。完整 mode 与静态 source 必须逐位一致，且两侧输入源阻抗均为零；否则走原矩阵构造路径。每个子步仍按原顺序刷新连续 driver、RA pole forcing 和 RHS。

没有跨调用保留模拟状态或随机状态，没有改变 BE、步长、事件分割、反馈延迟、12次D2或8比较/7物理更新。模拟状态仍只由原 `pool_cached_sfun` 的 Update/latch 提交。`pool_cached_matrix` 删除了未用的重复比较函数；`run_pool_ct` 只同步源码 pin。没有新模型或新增运行入口。

## 实际结果

| 同一 physics 配置 | 原源码 | 局部复用 |
|---|---:|---:|
| 有效输出码 | 8 | 8 |
| 数值仿真耗时 | 192.4924693 s | 170.1690159 s |
| 完整 logger | 59 | 59 |

这一对实际运行耗时减少 **11.60%**，提速 **1.131倍**。它是单对测量，不能作为长记录或多次重复的统计性能结论；行为级速度问题仍未解决。早先283秒的 profile 窗口只用于定位，不参与本表比较。

共同条件：Fs=5MHz、N8、M8、A0=10000、UGB=1.2GHz、内部积分上限62.5ps、owner间隔1.25ns、全局步长250ps；输入97656.25Hz、差分峰值3.650563842595822V、相位0.731rad、offset=0；master seed20261020、ID4–11/epoch1。校准关闭，sample-kTC@298.15K、18/8/8/2调度、group DEM及1mV tail dither开启。

两次运行使用同一 SLX：`15acb3f2b8ec6767bb8e9a6004ba1a97dd6101e438a2ae5783eeed1b1104f5c6`。这是短记录 physics 捕获时的模型身份，不代表随后恢复的 compact 保存身份。

全部59路的 Data/Time、原生 tout 和整个 selected 树逐位相同，无容差、无排除项。完整旧/预测态各5181字、ledger及roundoff ledger参与；隐藏采样随机状态第5179字和噪声电荷第5180–5181字另列通过。MATLAB全局rng也未改变。8个最终码均为：

```text
963377 979639 989055 991472 986860 975304 956956 932107
```

旧 compact 与 profile、旧 compact 与 physics 的共同54路也逐位通过；共同54路门不冒充59路全态门。

## 证据定位

原始大数据留在 Windows 工程，Mac仅保存本轮小型回执：

| 证据 | 位置 |
|---|---|
| 原 physics 运行 | `runs/run_tpbd8d0822_70d8_4956_9aa1_7bf0a971b706` |
| 新 physics 运行 | `runs/run_tp6204420c_7b4f_426b_9c32_bbfcf8f17d10` |
| 原 raw SHA256 | `e0c36d849c005aa32ea281c556c08844759ee4100483857bfd4e77579ad7839f` |
| 新 raw SHA256 | `7135a010223d82e62be7e3dfc11b8b917ae6c5c4469f7f5571b01064411aa3c1` |
| 原生逐位比较回执 | `cache_trial_receipt.json` |
| 两次仿真生产者结果 | `physics_reference_result.json`、`cache_trial_result.json` |
| 原始观察方式比较 | `physics_reference_receipt.json` |
| 本次源码闭包 | `cache_rebase.json`、`cache_deployment.json` |

原源码、原始码、as-run及控制源保留；历史过程中的护栏错误单独存证，没有重跑已完成的数值试验。最新子代理为gpt-6.1-sol/medium，实际Windows任务仅由主代理调度。

## 尚不能据此声称

逐位相等说明本短轨迹的缓存没有改变原有行为，不证明两边共有的物理错误不存在。独立完整 tail/kTC 电荷门仍待完成；ledger相等不代替独立KCL核验。同一步长的等价性也不证明BE时间离散收敛，步长报告中的码敏感性仍成立。

本次N8不做FFT。当前版本N256动态、真实静态跃迁、乒乓校准/holdout、jitter/skew及完整非理想扫描仍未完成。Rsource/Rref为零，参考有限恢复未开启；噪声/失调/slew等关闭项不能计入覆盖。A0、UGB及每侧电容口径仍是设计假设。旧NativeCt的101.91dB不能继承。

compact已恢复并再次实际运行：`run_tp8d3ea108_5620_44f6_b4bb_bfd421d82725`，8码耗时162.5648095s，共同54路、tout、整个selected逐位通过。该次compact SLX为`fbada84a5e775fb3e4f6ced7c1fd7c815f41840c5bd2416bed50b294677366ce`。这次162.56秒不能与另一MATLAB进程的旧208.18秒组成受控提速比较。

随后仅把record_length改为256，主任务已进入真实仿真：`run_tp4fb8520b_6c12_4e37_8581_7883ebe2064e`，当前SLX为`473438e7affa9f467ce00e19585bb63ca95d543446cbe7da602f3c2bff391e67`。Mac已同步同一SLX、参数和工作区字节，未做Mac原生仿真。当前尚无N256完成结果；不得引用旧频谱。完整状态日志仍只用于短physics核验。

残差MEX融合及公共RX标签校验草案仅封存在 `NONDEPLOYED_NEXT.zip`，尚未编译或接入，不能计为当前功能。
