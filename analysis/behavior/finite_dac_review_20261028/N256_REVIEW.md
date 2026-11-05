# 三组公开 N256：独立 RAW 与 FFT 回读

三次公开入口保存的仿真结果均为 complete，每组实际 RX ready 记录恰有 ID 4–259、epoch 1 的 256 条，valid 均为 1。`simout.mat` 的实际 RX RAW6、code20 和 ready 时间与该组 `selected.mat` 逐位一致；同一运行里 ADC raw_latch 与 RX 的同 ID/epoch RAW6 逐位一致。

使用实际选中 code20 重新计算的五项指标如下；计算采用相干矩形窗、单边谱，SNR 排除 H2–H10，THD 包含 H2–H10，ENOB 不做输入幅度修正。

| τDAC | SNR (dB) | SNDR (dB) | SFDR (dB) | THD (dB) | ENOB (bit) |
|---|---:|---:|---:|---:|---:|
| off / 0 | 110.150096 | 109.827136 | 123.088592 | −121.273976 | 17.951352 |
| 0.1 ns | 110.177259 | 109.844923 | 122.888028 | −121.172095 | 17.954306 |
| 1 ns | 107.249369 | 106.913367 | 118.614808 | −118.194717 | 17.467337 |

各组 `spectrum.mat` 五项值与自身 summary 存档值的二进制浮点一致；NumPy 独立 FFT 对这些保存值的最大绝对差为 `7.41e-11`（对应指标单位分别为 dB 或 bit），原始逐项差值均列在 JSON。没有设立新的频谱数值容差。相对 off，0.1 ns 有 1 个输出码不同、最大 1 count；1 ns 有 57 个输出码不同、最大 5 counts。

公共输入为 Fs 5 MHz、Fin 97.65625 kHz、bin 5、峰值幅度 3.650563842595822 V、相位 0.731 rad、差分 FSR 8.192 V。三组保存的完整 P 相对 off 只有 `P.front.tau_dac_s`、`P.backend.dac_coupling.enabled`、`P.backend.dac_coupling.tau_dac_s` 和 `P.ni.dac_settling` 四处不同。有限 RA（A0=10000、UGB=1.2 GHz）和寄生效应保留；本组三组都关闭 AZ、kTC、失配、DEM、dither、jitter、训练与 frozen 校准。

三组 source manifest 的 87 个文件内容 SHA 完全一致；三组 as-run SLX 的原生连线和 solver 配置相同，也均含 FE-old→RaAdvance 第四输入边和已检查的 guard 对话框。SLX 和 ZIP 容器本身的 SHA 各异，不以容器字节不同推断源码不同。与 083206 scratch 候选相比，as-run `behavior_prepare_configuration.m` 新增寄生覆盖标记派生，`behavior_backend_step.m` 新增 AZ 近极点分支；三组 P 均为 AZ off，因此这三次不验证新增 AZ 分支。

完整文件 SHA、每组 256×6 RAW、20-bit code 和 RX 时间的规范化内容 SHA、由 code/Fs/Fin/FSR 组成的 FFT 输入 SHA、参数差异及逐项数值差见 [n256_three_independent.json](n256_three_independent.json)。其报告 SHA-256 为 `c6fa62610cd5aed1f3e79db0f298d0a0460bdda0c7616b2da88f0470fd419c0e`。`simout.mat` 和 `spectrum.mat` 的 SHA 是本次回读时计算的，summary 没有在生成时记录这两个文件的 SHA，因而不能据此证明传输前未改变；频谱输入关系由实际 code、元数据及独立重算频谱核对，不能说存档中已有独立频谱输入签名。

该报告可在项目根目录运行下列只读脚本重建；需要 Python 的 NumPy、h5py、SciPy：

```sh
python3 analysis/behavior/finite_dac_review_20261028/verify_n256_three.py \
  --off runs/behavior_59a2b584-fa64-48ef-8608-80ce71bbf10b \
  --tau01 runs/behavior_96ebc182-7e6f-43d4-8eea-0d81960769b3 \
  --tau1 runs/behavior_47c22b65-fdff-402b-b315-ea0599df6891 \
  > /tmp/sar20_n256_independent.json
```

本报告没有重新仿真，也没有修改 current 或 Windows。它验证三次现有行为模型输出及其频谱计算，不证明内部完整状态、连续波形极值、INL/DNL、多频多样本统计、PVT、晶体管或硅片性能，也不证明完整论文指标。有限 τ 是设计敏感性参数，不是实测建立时间。
