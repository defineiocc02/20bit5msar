# RA 带限噪声：隔离行为候选

**2026-10-31 已接入生产主图并通过公开入口 N8 回归**（见文末「生产接入」一节）；以下第 1–3 节仍是接入前在固定 a190 模型副本上的隔离证据。全部是 Windows MATLAB/Simulink 的实际仿真，不是晶体管、PDK 或芯片测量。

噪声以固定工作点差分 VX 的稳态 RMS 参数 \(\sigma_{VX}\) 定义。区间内在单极点、无限 slew、固定旧命令条件下，现有 VX 沿确定性方程推进后加入 OU 创新，再进入 CINC/CT 观察与反馈；重复 Outputs 使用相同事件键，不推进 MATLAB 全局 RNG。`sigma_vx_rms=1 mV` 和 seed 20261030 是测试假设，不是论文识别的电路参数。

## N8 物理与状态验证

[实际任务](../../../runs/work_20261030T154306Z/)包含候选 OFF、同 tap OFF、σ=0、ON 和 ON-repeat：默认 OFF 与旧参考的 32 路日志/3 根输出位同；同 tap 下 OFF 与 σ=0 位同；ON 与同 seed 重跑位同。12 个周期逐事件回读实际命令，分别核得每周期 12 次 D2、8 次 tracking 比较、7 次 tracking 反馈；实际 VY、判决和反馈对应。首区间预期及实际变化分别为 ΔVX=75.723967969927/75.723967969926 µV、ΔVY=58.9673988085084/58.9673988085071 µV。

[全事件回放及限制](ALL_EVENTS_REVIEW.md)：576 个事件 CT 矩阵回算 VY 最大误差 4.42×10⁻¹⁷ V，575 个连续 RA 区间回算 VX 最大误差 2.78×10⁻¹⁷ V。这些比较使用后验浮点容差、保存波形及根据时间/源码语义重建的随机键，键并非独立硬件探针。本配置的净 CINC kick 均为零，不能称为实测了非零 kick。

## 同模型、同参数 N256 对照

Fs=5 MS/s、Fin=97.65625 kHz/bin 5、N=256、epoch 1、transport ON、Bank/训练/Frozen/AZ/有限 DAC/采样 kT/C/失配/DEM/dither/jitter/比较器噪声 OFF，有限 RA 增益/带宽与固定寄生仍在。相同 a190 SLX 和 109 源码；OFF 保留相同 σ、seed 和所有其他参数，仅将两个噪声标志置 false。顺序为 **先 ON、后 OFF**，各运行一次。

| RA OU | SNR (dB) | SNDR (dB) | SFDR (dB) | THD (dBc) | ENOB (bit) |
|---|---:|---:|---:|---:|---:|
| OFF | 110.150096 | 109.827136 | 123.088592 | −121.273976 | 17.951352 |
| ON | 101.729052 | 101.194257 | 115.434863 | −110.554881 | 16.517318 |

[两案实际频谱](ou_matched_pair_spectra.png)。单次 SNDR 差为 −8.632879 dB；这只是固定输入、单 seed、256 点下的影响，不能当 M1/M8 tracking 降噪收益、PSD 统计或论文 7 dB 的复现。ON/OFF 的 32 路日志时间、实际事件/ready 时间和 256 个选中 ID 对齐；260 条 RX-ready 均有效。

[ON 原件](../../../runs/work_20261030T161056Z/result/on256/)和[OFF 原件](../../../runs/work_20261030T162714Z/result/off256/)均包含 P、完整 simout、selected 和 spectrum；[同图对照回执](../../../runs/work_20261030T162714Z/outer_receipt.json)记录模型/源码与结果身份。独立后验会区分 Bank OFF 根口 `CodeValid=0` 与 RX RAW 自身 valid=1。

[ID138 舍入边界](ID138_ROUNDING_REVIEW.md)：不同浮点求和顺序可在半 LSB 处得到相差 1 码的离线结果；实际 MATLAB 记录未被改写，不靠放宽整数码容差通过。当前候选与 Bank/Frozen/训练资格、AZ、有限 DAC 和有限 slew 联合仍被拒绝，且未完成多 seed 噪声统计；关闭/零幅不能计为本次噪声开启覆盖。

同图配对中可追踪的实际 ID4：组31时两案 D1=1900、D2当前字=3280；下一组 OFF 的 VY 为 −1.357 µV，ON 为 +309.969 µV，对应 D2 位由 0 变 1。随后闭环反馈继续分叉，最终 OFF RAW `[1900,3283,234]`、码 963400，ON RAW `[1900,3285,131]`、码 963404。按保存的 CT 电容矩阵和各自 reset 基线重算的 VY 差与实际差相差约 9.6×10⁻¹⁸ V；后续码差包含多次反馈，不全部归因于这一项创新。

## 2026-10-31：生产接入与公开入口 N8 回归

隔离候选共 12 个文件（8 替换 + 4 新增，105→109 源）已冻结为发布包 [`release_20261031/`](release_20261031/)，并装入两端主图。断线复审时发现三个文件在首次 manifest 快照**之后**又被修改（两个新增守卫、一个守卫单测），因此先做重新冻结：旧值、原因与证据全部保留在 `release_20261031/MANIFEST.json` 的 `refreeze` 段，未覆盖历史。重新冻结前，在真实 MATLAB 27628 会话对**实际 ON/OFF P** 跑了守卫与标签合同测试，全部通过（`guard_on`、`guard_off`、`guard_selftest`、`label_selftest`，12 个函数均解析到暂存候选，路径/cwd/RNG 复原）。

| 身份 | 值 |
|---|---|
| 冻结后发布 manifest | `d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1` |
| 基线 manifest | `0d9dbb7132357967d0d9a930911436898d038b3f2d2c1e38fb3f088dd9356642` |
| 安装前模型 / 状态 | `a190eae2…adbe9f` / `4098360e…82fd92` |
| Windows 安装前备份 | `D:/Temp/SAR20OUMain_20261030T171030Z/backup`，115 文件，清单 `23d98f9a…a1334` |
| Mac 安装前备份 | `evidence/ra_ou_install_20261031/backup`，115 文件，清单 `7c25d418…29611` |

公开入口烟测（安装后、同一条 a190 系主图；只跑 N8）：

| 案 | 运行 | 单次耗时 | ID4 raw / 码 | 日志与根输出 |
|---|---|---:|---|---|
| OFF | `runs/behavior_9b3a15ae-46fc-47a3-9f43-78644083048a` | 4.5946 s | `[1900,3283,234]` / 963400 | 32 路日志 + 3 根输出与历史 OFF N8 逐位相同 |
| ON | `runs/behavior_1fd9057b-cfd0-4166-a5ba-05f21927b19c` | 4.0955 s | `[1900,3285,131]` / 963404 | 同上，与隔离 ON N8 逐位相同 |

- σ=0 只做标注/apply/check，明确记为「零激励，不计噪声覆盖」，不产生仿真覆盖。
- 结束恢复 OFF：模型 stopped/clean，path/cwd/RNG 复原（全部由烟测内部断言）。
- 两次运行 `source.zip` 均 109 条，逐条字节 SHA 与发布清单一致；独立离线复核 37 项全过（`install_20261031/independent_offline_review.json`）。
- 烟测后主图身份变为模型 `b2465488…071ee`、状态 `b1b7396a…8eb45`；`apply` 会保存模型工作区 P 并写 state，属预期身份变更。两端已镜像。

**边界：** 本节只证明 RA OU 开启/关闭下公开入口的 N8 判决与时序未被新噪声核改变、可正常 apply/check/run；未重跑 N256、未做 PSD 或多 seed 统计，不是 PDK/硅或产品签核。回滚路径为 `evidence/ra_ou_install_20261031/backup` + `tools/sar20_ou_install.py rollback`。

## 2026-10-31：生产入口 N256 OFF/ON 实际动态

安装后从**公开入口** `SAR20('apply')`→`check`→`run` 重跑同一对 256 点配置（Fs=5 MS/s、bin 5、epoch 1、transport ON；两案仅两个 RA 噪声使能位不同，σVX=1 mV、seed 20261030 均为测试假设）。两次都是真实 Simulink 运行，`SAR20('run')` 对 N≥256 自动用实际输出码算频谱。

| RA OU | 运行 | 单次耗时 | SNR (dB) | SNDR (dB) | SFDR (dB) | THD (dBc) | ENOB (bit) |
|---|---|---:|---:|---:|---:|---:|---:|
| OFF | `runs/behavior_fba2d7a5-9824-49ab-b595-100fb9e5d9d1` | 73.05 s | 110.150096 | 109.827136 | 123.088592 | −121.273976 | 17.951352 |
| ON | `runs/behavior_ad1aae9c-d99f-495e-847c-999f885b2d13` | 80.78 s | 101.729052 | 101.194257 | 115.434863 | −110.554881 | 16.517318 |

- 与隔离对照组（2026-10-30 00:28）的五个指标**逐位相同**：接入生产入口没有改变数值结果，差异仅来自 RA 噪声开关本身（ΔSNDR = −8.632879 dB）。
- 频谱由保存的实际码重算：[生产入口两案频谱](install_20261031/n256_prod_spectra.png)。
- 回执 `install_20261031/n256_prod_receipt.json` 记录了两案的 config SHA、模型 SHA 与复原状态；结束恢复 OFF，模型 stopped/clean。
- 边界：单 seed、单频、256 点、有限记录；不是 PSD 统计、M1/M8 tracking 收益、论文 7 dB 或 PDK/硅结论。

## 2026-10-31：RA OU 六 seed 统计（生产入口，N256）

同一公开入口、同一份 ON 参数，仅改 `seed_u64`，各跑一次真实 N256（Fs=5 MS/s、bin 5、σVX=1 mV、transport ON、Bank/训练/Frozen/AZ/kTC/失配/DEM/dither/jitter/比较器噪声/参考恢复关闭）。

| seed | SNDR (dB) | SFDR (dB) | ENOB (bit) | 耗时 |
|---:|---:|---:|---:|---:|
| 20261031 | 101.181770 | 115.756991 | 16.515244 | 80.93 s |
| 20261032 | 100.988429 | 114.233035 | 16.483128 | 81.08 s |
| 20261033 | 100.460406 | 113.802774 | 16.395416 | 80.16 s |
| 20261034 | 100.632795 | 113.776041 | 16.424052 | 80.76 s |
| 20261035 | 100.000110 | 113.081861 | 16.318955 | 81.16 s |
| 20261036 | 100.665268 | 113.170337 | 16.429446 | 80.55 s |

统计：n=6，均值 **100.654796 dB**，样本标准差 0.413765 dB，总体标准差 0.377714 dB，极差 1.181661 dB（100.000110–101.181770）。原先单 seed 20261030 的 101.194257 dB 落在该分布上沿，说明**单次 101.19 dB 偏乐观**；6 seed 均值比 OFF 的 109.827136 dB 低 **9.17 dB**。

- 每个 seed 的 `source.zip` 109 条与冻结清单逐条一致，`SarAdc.slx` 快照 SHA 等于其 summary 记录，`parameters.json` 的 seed/σ 与实际一致；独立核对 41 项全过（`install_20261031/independent_seeds_check.json`）。
- 原件的运行目录见 `install_20261031/seeds_20261031/runlist.txt`。
- 这批只改 seed，因此差异是 OU 随机序列本身导致的判决翻转与噪声底，不含频率/幅度变化；仍不是 PSD/长记录统计，也不代表 M1/M8 跟踪收益。

**一次作业缺陷与纠正（如实记录）：** 首个 seed 作业在汇总 `struct` 时因空 double 容器报错，第二次又因暂存目录被预创建导致 `P.mat` 路径多一层而失败；这两次都在真实仿真前失败，未改模型。随后修正并跑通六个 seed。作业结束的"恢复"曾误把上一次残留的 ON 工作区 P 写回生产（`state` 一度为 RA ON、seed=20261031），已用无参 `SAR20('apply')` 恢复出厂 OFF，并核验：`configuration_source=factory`、`P.backend.ni.ra_noise=false`、无 `ra_noise` 字段、Bank OFF、模型 SHA 与状态 SHA 自洽（模型 `5f15ad49…caebd`）。
