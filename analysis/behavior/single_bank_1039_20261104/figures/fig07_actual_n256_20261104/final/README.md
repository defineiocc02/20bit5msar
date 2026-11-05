# Fig. 7：实际 N256 行为级频谱

此目录是本次单 bank 频谱的唯一展示版本：`fig07_behavior_n256.png`、`.pdf`、`.svg` 三种格式内容相同。数据来自真实保存的 N256 码流及频谱，不是论文的 20k 点芯片实测。

真实配置：Fs = 5 MS/s、Fin = 97.65625 kHz（256 点 FFT 的第 5 个 bin）、输入 −1 dBFS；噪声和 AZ 关闭，A0 = 10000、UGB = 1.2 GHz、Cf = 0.864 pF，采样及 DAC 时间常数为零。实际结果 SNR = 109.7832 dB、SNDR = 109.3456 dB、SFDR = 122.2674 dB、THD = −119.5296 dBc、ENOB = 17.87136 bit。SNR 排除 H2–H10；ENOB 未作输入幅度校正。

图排除 DC，逐点显示全部 128 个非 DC 的单边 bin；`spectrum_non_dc.csv` 保留频率、原 MATLAB 保存功率和相应单 bin dBFS。纵轴范围依据这些非 DC 数据确定，没有裁掉最低点。原生 MATLAB 图及原始回执保存在 as-run 数据目录，原文件没有改动。

`independent_review.json` 保留逐文件 SHA、全部 P 差异与输入值、实际 260×48 事件和 260 RAW 检查、N8 前 8 条逐位比对，以及以保存的 256 个码独立计算的 FFT 指标。12/8/7 是调度日历计数；本次 debug 关闭，没有直接观测物理反馈计数或返回电荷。结果不代表噪声扫描、静态线性、工艺或芯片验收。

上一级 `../plot_fig07_n256.py` 可从原 MAT 在本机复现检查和绘图，不调用 MATLAB、不改原始文件。它要求目标目录为空或不存在，例如：

```sh
SAR20_ROOT="/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020"
"$SAR20_ROOT/dependencies/analysis_env/bin/python" "$SAR20_ROOT/analysis/behavior/single_bank_1039_20261104/figures/fig07_actual_n256_20261104/plot_fig07_n256.py" --out /tmp/sar20_fig07_reproduce
```

若目标路径已存在，请换一个不存在的路径。脚本输出图、CSV 和独立复核 JSON；本 README 在渲染后附加。
