# 有限 DAC 建立：实际 N8 行为与样本调试

本页读取完整ADC scratch模型`SarDac`的真实N8记录，**尚未晋升current**。zero来自`022517/dac_enabled_tau0`，四例来自`023003`；均为ID5、CNV=1µs、ADC RawReady=1.08625µs、RX=1.538µs、record valid=1。coarse_input/held均逐位相同：3.55756491800524V。τ为设计敏感性参数，非硅测值。

| τDAC（18片） | 本样本DAC/SAR1最早可见分歧 | 实际Qres：31.25→43.75ns / pC | 43.75ns RaPre VX / BackLog VY，V | 最终D1 / D2 / DT | 实际RX code（相对zero） |
|---|---|---|---|---|---:|
| 0，coupling on | 基线 | +0.151095955536 → +0.151095955536 | +0.166375237850 / +0.129558913316 | 1932 / 2907 / 85 | 979654（0） |
| 0.1ns | Qres在12.5ns先差；D1全48组相同 | −0.066116165676 → +0.151095955536 | +0.166013390112 / +0.129277137011 | 1932 / 2907 / 85 | 979654（0） |
| 1ns | Qres在12.5ns先差；D1全48组相同 | −0.070973456912 → +0.151095127961 | +0.161727393829 / +0.125939566901 | 1932 / 2907 / 85 | 979654（0） |
| 5ns | Qres在12.5ns先差；D1 raw在26.25ns先差 | −0.279062476101 → −0.282978127815 | −0.310981111174 / −0.242165693322 | 1934 / 361 / 42 | 979661（+7） |
| Inf保持负例 | Qres在12.5ns先差；D1 raw在15ns先差 | 0 → 0 | 0 / 0 | 1951 / 2374 / 42 | 998401（+18747） |

**先是DAC1/SAR1，再看RA。** 首次coarse_latch/fine_prepare在12.5ns把trial设1936：zero的实际Qres立刻为−0.717752529312pC，四个非零τ例当时仍为0。5ns在26.25ns的fine_decide处vres=+1.466042186mV，而zero为−10.435081995mV；该行D1 raw已1934对1932，早于31.25ns ra_start。Inf在15ns仍vres=0，D1 raw已1936对1920，最终细位走到31；这是永不建立的保持负例，valid=1不等于精度正确，不计finite coverage。

**末端残差相同也不代表RA相同。** 0.1ns在43.75ns的Qres与zero原始位相同，RaPre仍低0.361847738mV；1ns低4.647844021mV。实际Qres的区间历史改变了同一RA响应。0.1/1ns的D2/DT在本样本全48组也逐位相同，故实际整数码未变；这不证明其它ID/频率无误差。5ns的D2 raw从45ns首次分歧、DT从76.25ns首次分歧，最终仅余+7码，不能把+7全部归为独立RA误差。

**RaPre与BackLog不是同一相位。** `dac_ra_pre_log`来自321.y2，旧区间推进后、当前反馈/命令前；`back_log`在后续CT/DAC命令后。zero的46.25ns：VX两处均0.171098661181V，VY却从RaPre的+0.133237114482V变为BackLog的−0.006931607127V；5ns同刻为−0.249288878734→−0.109120157124V。该差含本事件反馈/切换，不能叫DAC RC卷积误差。本组active阶段VX两探针位同，不能据此说两探针同相或杜撰非零VX kick。

**“首次”边界。** 按所有原始位，RaPre/BackLog VX在本CNV 0ns就有约10⁻⁴⁹V历史衰减残量差；各例从启动起各自运行，不是从ID5完全相同模拟前态分叉。上表另列本样本新DAC命令之后Qres/判决的首次分歧；未设容差删除早期小差。

| case | model SHA前12 | parameters.mat SHA前12 |
|---|---|---|
| zero | 4f2fae6fde5a | 0bc8460d8927 |
| 0.1ns | 715e3641f200 | ed8c7a637536 |
| 1ns | 6a042b8d2c8b | 1af8e40dff52 |
| 5ns | 94d20e60f31f | bc63b7184462 |
| Inf | 208eee5a4972 | 453de359db59 |

来源：[零时间常数实测](../../../runs/az_probe_20261027T022517Z/dac_enabled_tau0/simout.mat)与[有限时间常数实测](../../../runs/az_probe_20261027T023003Z/receipt.json)，逐日志**exact Time join**：Qres=FrontLog[3]（本事件FE端点），D1/2/DT=raw_log/Control13，RaPre=dac_ra_pre_log[1]，BackLog=back_log[1:2]；RX code直接取record_ready/record_log同ID/epoch时刻的code_log，未用RAW公式代替。RaPre只有672个ADC行，其它parent日志686行，未按行号混配或给49组补点。四例RAW/Q0/Q1/RaPre已逐位交叉核对原生observation.json；完整SHA、48端点与首次位差见[id5_actual_causal_data.json](id5_actual_causal_data.json)，复读脚本[inspect_id5.py](inspect_id5.py)。

仅一条样本链及N8功能/敏感性观察；没有FFT、SNDR、INL或完整硬件精度结论。独立expm差值不在本页充当FE物理或解析容差通过门。


## 八个输出码的实际敏感性

| τDAC / coupling | Δcode rows / max counts | ΔRAW words D1/D2/DT | valid | ref RMS / max (µV) | RApre / VYpre peak (V) | sim (s) | simout / numeric+time (B) |
|---|---:|---|---:|---:|---:|---:|---:|
| 0ns / off | 0 / 0 | [0, 0, 0] | 8/8 | 15.3499 / 24.3834 | 0.22432 / 0.168407 | 5.682442 | 746353 / 634374 |
| 0ns / on | 0 / 0 | [0, 0, 0] | 8/8 | 15.3499 / 24.3834 | 0.22432 / 0.168407 | 5.119122 | 746353 / 634374 |
| 0.1ns / on | 1 / 1 | [0, 1, 2] | 8/8 | 15.53 / 24.3834 | 0.22432 / 0.168407 | 6.080172 | 748417 / 634374 |
| 1ns / on | 4 / 3 | [3, 4, 5] | 8/8 | 20.7828 / 33.2049 | 0.365071 / 0.274124 | 5.182548 | 756123 / 634374 |
| 5ns / on | 7 / 132 | [7, 8, 7] | 8/8 | 359.252 / 1013.01 | 0.570113 / 0.443955 | 5.078966 | 770294 / 634374 |
| Inf negative | 8 / 23312 | [8, 8, 6] | 8/8 | 134369 / 182119 | 0 / 0.140169 | 5.100985 | 708567 / 634374 |

共同实际开关：RA A0=1e4、UGB=1.2GHz、CINC kick开启、CT输出寄生0.5pF/half；失配/kTC/DEM/dither/jitter/AZ关闭，slew=Inf；training/collector/frozen全off。dac_settling仅三个finite点为true，Inf为false。C、seed、plan、初始电荷及实际事件时轴已核相同；off与enabled/zero全部30路实际logger位一致。

验证参考是savedP.input声明正弦在实际日志CNV时刻的值，不是片内held或测量真值。全部8条保留，无gain/offset拟合、校准或FFT/INL/SNDR；Inf虽valid=1仍是不建立负例，不计有限NI覆盖和有效性能。

峰值是ID4..11的384个实际ADC事件端点绝对值最大值；表列RaAdvance pre-CINC，BackLog另一阶段峰值另存JSON。不能当连续波形包络峰值。

每例单次未profiled实际sim（含专项日志），不据此给稳定提速比或挑tau。完整8码/RAW/误差、开关及来源SHA见同名JSON。


目前唯一主模型尚未接入这一候选：`SarAdc.slx` 仍拒绝非零 DAC 时间常数。当前纯 MATLAB 配置守卫已验证，Simulink GUI 直接修改工作区后的守卫与晋升回归尚待许可证恢复；不能把本表当成当前主模型或 256 点频谱结果。
