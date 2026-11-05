# 频谱谐波折叠检查与正式入口 N8 回归

2026-11-04，Windows MATLAB R2024a，PID 27628。该修复只改变频谱后处理；不改变 ADC 物理状态、模型连线或历史记录。

## 本次改动和处理边界

当 H2–H10 折叠后与 DC、基波或另一阶谐波落在同一个频点，`behavior_spectrum` 返回 `harmonic_alias_collision`，保存实际频率、功率和碰撞对，不生成 SNR/SNDR/SFDR/THD/ENOB 字段。`SAR20('run')` 的 `status=complete` 表示仿真完成；必须同时检查 `spectrum_status` 才能判断动态指标是否可报告。零信号仍报原有 `BehaviorSpectrum:power`。

Windows 和 Mac 工作源码 SHA-256 `f567aab44fc37579c00812b673264afa464ec99d074f07ad0fa6d6955fcd4f3e`；旧源码 `c6c2cf78780d628e7b4c7c7772e09dc5024dcee14bc717fd1147129c2153345a` 保存为本目录 `behavior_spectrum_before.m`，Windows 另保留 `D:/Temp/SAR20FFT_20261104_qfhxXr/behavior_spectrum_before.m`。原始模型和历史 raw 未被覆盖。

## MATLAB 函数回归

实际运行 `test_behavior_spectrum_collision.m`，旧、新源码仅更改函数声明名后在临时目录调用，不清除生产函数缓存：

- N=256 的 127 个基波位置中，120 个无碰撞位置与旧函数的全部结果逐字段、逐位一致；7 个碰撞位置报告不可判定。
- 旧函数在 bin 64 的 H3/H1 折叠反例仍错误输出指标，新函数报告碰撞；bin 8 合法、bin 16/32 的碰撞、无独立噪声、常数输入、短记录、非相干和非 2 次幂均按测试预期处理。
- 使用历史 `behavior_9058b834-83be-4415-946c-7f3b3ef8c7eb` 的真实 `selected.mat` 及 `spectrum.mat`：N=256/bin 5 新旧函数和已保存指标逐字段、逐位一致。这是对已有实际 ADC 码的频谱复算，不是一次新 N256 仿真。
- 正式原名 `behavior_spectrum` 在现有 MATLAB 会话经定向清除和重新解析，实际路径为 Windows 工作源码，函数体与冻结候选一致；同一历史数据和碰撞例再次通过。

原生回执：`matlab_receipt.json`、`controller.log`；原名检查和整图回执：`production_matlab_receipt.json`、`production_controller.log`。测试报告 path 已恢复、MATLAB 全局 RNG 未改变；没有重启 MATLAB。

## 本次正式主图 N8

公开入口 `SAR20('run')` 实际完成：factory N=8，Fs=5 MS/s，原始 ID 4–11，epoch 1，valid 均为 1；码为 `[963400, 979654, 989058, 991473, 986858, 975288, 956933, 932073]`，仿真耗时 24.6605 秒。`spectrum_status=not_run_short_capture`，**没有动态频谱或 DNL/INL 测量**。

Windows 原 run：`D:/Academic/Projects/sar20m1/SAR20/runs/behavior_0a3cc913-8a98-44f9-86c6-cf2ada1c9932`；8 个文件已按 SHA-256 校验镜像到 `n8_run/`。其中实际 SLX SHA 为 `d4e7fc99ab040857e535df07d73447e71c65e7d51dcadf7b17f4bad88594a6a0`，实际 `simout.mat` SHA 为 `6a6669b49daaaa918d0a344c75860e134eb90da23eb9c44a85418585b932b8e1`，source.zip 的实际频谱源码与候选 SHA 一致。所选 8 码与历史 OFF N8 记录一致；本次尚未对该历史 run 的完整 P 和 32 路状态做逐位比较。

运行按公开入口更新 Windows 的 latest 指针为本次 run；旧指针在运行前未单独备份，不应宣称已恢复。两个自建临时计划任务均在完成后移除；原 `SAR20_MatlabControl` 定义未变，状态 Ready。

## 当前主图、历史完整 P 的实际 N256

2026-11-04 通过 `SimulationInput` 临时覆盖当前主图的 P/DecodeP，未对主图执行 apply/save。输入复用历史 `behavior_9058b834...` 的完整参数：Fs 5 MS/s、Fin 97.65625 kHz/bin 5、−1 dBFS、DAC τ=1 ns、串行 RX 开启；有限 RA 增益/带宽及固定寄生开启，采样 kT/C、失配、DEM、dither、jitter、AZ、比较器噪声和校准关闭。

实际 256 条有效 ID4–259：SNR **107.249369 dB**、SNDR **106.913367 dB**、SFDR **118.614808 dB**、THD **−118.194717 dBc**、ENOB **17.467337 bit**。本次 selected RAW、最终码、时间与历史 selected 逐位一致；频谱结果 `isequaln` 相同。历史 SLX 与当前 SLX 哈希不同，这是跨快照的选中结果比较，不能声称所有内部状态已逐位验证。

本次仿真 286.876 s；运行期间 Windows 可用物理内存一度约 0.7 GB，之后自行恢复到约 23 GB。内存压力可能影响耗时，但尚未单独证明因果或完成性能剖析。当前数据由 MATLAB 直接绘图：[实际频谱](n256_run/actual_n256_spectrum_dbfs.png)。

`n256_run/` 保留当前 SLX、覆盖用 P、实际 simout、selected、spectrum、源码包、历史比较输入及原始回执。六个主要文件在 Windows 与 Mac 逐 SHA 一致；实际事件流到达请求的 stop time，主图 P/DecodeP、全局 RNG 和 path 记录未变。`controller.log` 有同名模型遮蔽警告：job 中 `SarAdc.slx` 是运行前从当前主图复制的同 SHA 快照，运行前后检查的模型 FileName 均指向主图；不能把本次环境描述为无警告。任务创建的 MATLAB 模型已关闭，原计划任务定义未改。
