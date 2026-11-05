# RA OU 隔离 N8：全事件独立回放

**结论：**对 `runs/work_20261030T154306Z/result` 的已保存 P、原始 `SimulationOutput` 和候选源码进行只读后验回放，在该次隔离行为模型的 12 个周期内，RA 区间、CT 电荷方程、判决与已观察反馈、公开原字及根口均与保存记录一致。本次未重新运行 MATLAB，也未修改原始 run。

这里的 `sigma_vx_rms=1 mV` 是差分 VX 一极点噪声的**测试假设**，不是电路测得或论文参数。本结果不证明论文 7 dB、噪声 PSD、跨 seed 分布、完整 DNL/INL、生产晋升或 PDK/硅片签核。

## 数据身份与运行范围

- 被观察对象：候选隔离图 `SarOUProbe.slx`，SHA-256 `a190eae2be57e24f0fb923bad7bbf4144873f28ddc97b8196fdd80a512adbe9f`；沙箱内 109 项候选源码与本目录保存的 v3 清单逐项匹配。磁盘源码身份不独立证明 MATLAB 同路径缓存中的字节一定新鲜。
- 输入与标签：5 MS/s，N8 输出选择 ID 4–11；包含预热实际收到 ID 0–11，共 12 条 ready，epoch 1，全部 valid。OU seed 为 `20261030`；kT/C、jitter、DEM、dither、AZ、比较器噪声、训练、Frozen 和 Bank 关闭。
- 原始 ON `P.mat` SHA-256 `d7e9a3757ae30330e7f09039747614145fb0701449695566629aca221bca1894`；ON `simout.mat` SHA-256 `cd8b3faf295e508bb19d1d18f900a61fa0a7d7ce981f74a47b317629310d2a00`。其余逐案 P/simout 摘要见机读结果。

## RA 创新与 CT 响应

独立脚本根据保存的事件时间、前一事件记录的 VX、目标、噪声增益、旧 ID/epoch 和固定 seed，重建每个区间的确定性推进与 OU 创新；reset/off 区间使用保存的 reset 时间常数。575 个连续区间中，432 个为 RA 活动区间、143 个为 reset/off 区间。与实际 `dac_ra_pre_log` VX 的最大绝对差为 **2.7755575615628914e−17 V**；本次后验数值门为 `1e−13 V`。

第一个活动区间为 ID0 的 31.25→43.75 ns。由实际事件时间和已保存算法语义重建的键摘要为 `c80bd46cb31a6f693b96fee51fe6ecabf87c5976cdf2e17bd7f69d2f404dcb3d`，重建高斯值为 `0.07587247825844239`。预测和实际相对零噪声的 ΔVX 分别为 **75.723967969927 µV** 和 **75.723967969926 µV**，差为 `−7.86e−19 V`。**键来自后验重建，并非运行时随机函数输入端的直接仪表记录。**

另以实际 ADI tap 的 19 路反馈符号、实际 VX 和 reset 基线，结合保存的名义 CT 电容矩阵及初始浮置电荷，独立计算两侧 2×2 电荷网络。576 个事件的 VY 最大绝对差为 **4.423544863740858e−17 V**；本次后验数值门为 `1e−12 V`。首区间由矩阵得到的两侧增益均为 `0.7787151200519143`；预测和实际 ΔVY 分别为 **58.9673988085084 µV**、**58.9673988085071 µV**。浮置电荷按候选源码中保持的初始状态使用，并非被单独探针测得。

两项容差是独立浮点回放的后验比较阈值，不是模拟误差指标，也不代表训练、统计或产品接受门限。活动区间键、旧命令和状态归属使用已保存日志加候选源码语义重建；不是对每次内部函数调用逐口取证。

本案 `cinc_kick=1`、replica 开启且 CT mismatch 关闭；576 个保存事件上 `dac_ra_pre_log.VX` 与 `back_log.VX` 逐位相同。这说明两观察口之间**未观察到非零净 VX 变化**，不证明每个内部开关冲击均为零，也不能把本次称为整图非零 CINC kick 验证。隔离 backend 非零 kick 单元回执属于单独的证据层。

## 判决、反馈与公开输出

- 576 条事件和时间与保存的 12×48 事件日历逐位一致。根据每次实际 VY 的符号及事件顺序，独立重建每个事件后的 D2/DT 全字，均与 `control_log` 一致。
- 实际 `adi_wire_log` 的计数和 19 路命令逐行一致：12 周期合计 **144 次 D2 判决、96 次 TA 判决、144 次 D2 反馈、84 次 TA 反馈**；每个 ready 的计数均为 12 D2、8 TA、7 TA 反馈。证据是实际计数和命令线，不单独测量每片内部开关或电荷冲击。
- 12 条 ADC RAW 与 record 同时刻逐位相同，ready/record_ready 一致，公开重构码逐条匹配。根 `Code20` 与 code_log 按实际时间对齐；Bank OFF 合同下 `CodeValid` 全 0，`CodeMeta` 与 Bank OFF 日志一致。不能将此处根 `CodeValid=0` 误读为 ADC 原字无效。
- 相同 tap 下 OFF 对 ON/σ=0、以及 ON 对同 seed 重复运行：各 32 路日志和三个根口的实际时间、数据、类型及形状逐位一致。候选 OFF 对旧 `ea39` 参考同样通过该 N8 位门；旧参考与候选 `a190` 不是同一 SLX 字节。
- ID4–11 中，ON 减零噪码差为 `[+4, 0, −2, −3, −3, −1, −4, +2]`。这仅说明该 seed 下的八条记录受到影响，不能从中估计噪声谱或性能收益。

原生 `cleanup.mat` 记录路径、cwd、RNG 和用户模型快照恢复/一致；其 `cache_original_bytes_restored=false`，因此不能声称旧函数缓存字节已恢复。backend 单元 `unit.mat` 的通过状态来自原生回执，不由本 Python 回放重新执行。

## 复现与交付

在项目根目录执行以下只读命令；脚本默认根据自身路径定位工程和原 run，JSON 写到工程外临时文件：

```sh
PYTHONDONTWRITEBYTECODE=1 dependencies/analysis_env/bin/python \
  analysis/behavior/ra_ou_20261030/audit_all_events_independent.py \
  > "${TMPDIR:-/tmp}/sar20_ra_ou_all_events.json"
shasum -a 256 "${TMPDIR:-/tmp}/sar20_ra_ou_all_events.json"
```

- [回放脚本](audit_all_events_independent.py)：SHA-256 `a73344211cdba2ad14825e4fe1612f7f2e864fa4e77ffacdc1392c04374c96a5`。
- [机读结果](all_events_independent.json)：包含全部 576 事件及 575 连续区间；SHA-256 `04120b9a6f1fa719e4efbdb88103d6a39527d4a409136a5713b2167e6fcf327e`。
- [v3 来源清单快照](candidate_manifest_v3_snapshot.json)：SHA-256 `9ed7eeae767fa399c300a18c8127f5a7bef57ec776301ad54239e0a935cd399c`。

脚本在工程根目录和无关的 `/tmp` 工作目录分别运行，输出 SHA 一致。它使用工程中固定摘要的 `verify_as_run.py` 读取 MATLAB 原生序列化数据，比较和方程计算均只读。
