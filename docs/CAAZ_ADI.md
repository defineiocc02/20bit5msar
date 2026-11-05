# 成电底座上的 CAAZ 与 ADI

当前公开工程仍为 `91973cf76507…`、5 MS/s、ordinary AZ 的正常配置。输入侧 CAAZ 已在私有试验图 `63283fd769ac…` 真正跑通两组 N8；ADI 整图尚未接入。这里分别记录已运行的行为与正在实现的物理方案。

## 三份原文各提供什么

| 来源 | 本工程采用的部分 | 不直接迁移的部分 |
|---|---|---|
| 成电 CICC 2026 [论文](PAPERS/01_CICC2026/A_3.6mW_5MS_s_100dB-SNDR_2-Step_SAR_ADC_with_Continuous-Time_Second-Stage_and_Tracking_Averaging.pdf)、[讲稿](PAPERS/01_CICC2026/13-6_Jin.pdf) | 6b 预转换、10b 有效 DT、DAC1 电荷残差、32 倍 RA/AZ、CINC CT、12 D2、8 次 tracking/7 次物理更新 | 未披露的逐沿时刻、A0/极点、寄生、噪声及工艺参数仍是明确的模型假设 |
| 北大/清华 VLSI 2025 [论文](PAPERS/04_PKU_AZ/Wang_2025_VLSI_C32-1.pdf)、[42 页讲稿](PAPERS/04_PKU_AZ/C32_C32-1.pdf) | DAC1 采样输入前两相斩波；偶帧写 AZ、奇帧复用；完整输出恢复极性后组合 | FGA/CP-FIA 电路、2 pF CBIAS、内部增益 8、6 MS/s 及 4.3 dB 测量收益不当作成电 RA 参数 |
| ADI ISSCC 2024 [论文](<PAPERS/03_ADI_ISSCC2024/[00]_A_9.3nV_rtHz_20b_40MS_s_94.2dB_DR_Signal-Chain_Friendly_Precision_SAR_Converter.pdf>)、[讲稿](<PAPERS/03_ADI_ISSCC2024/[00_1]ISSCC2024_ppt.pdf>) | 18 片 RDAC 池、8 转换/8 采集/2 备用、独立双量化器、accepted-code follower、DEM/dither 与公开信息校准 | 40 nm 原型的开关速度、40 MS/s、功耗、面积及线性度不直接迁移到 180 nm |

旧 [CHOP_AZ_SPEC.md](CHOP_AZ_SPEC.md) 是残差端四相历史提案。本轮使用输入端两相，二者不能混用。

## 已接入试验图的信号与状态关系

新模式名为 `pku_input_hold_chop_v1`。采集组按自己的目标 sample ID/epoch 保存身份，输入极性为 `p(n)=1-2*mod(n,2)`。Driver 保留原始正弦描述符；前端对该采集组的完整差分输入换向。转换中的旧组不会改用下一组的极性。

SAR1、DAC1 与 RA 输入残差处于同一个被斩波坐标。RA 的 Qres、有限 DAC 驱动、CT 反馈和返还 Vtop 不再额外乘 p。数字端先按各自单位形成

`v_ch = V_D1 + (V_D2 + V_DT)/32`

再做 `v_in = p(n)*v_ch`，最后量化为 unsigned20。当前 dither 关闭；未来若在 chopper 后注入、模拟残差为减 d，则补偿必须是 `p(n)*(v_ch+d)`，本轮没有开放该注入路径。

成电原有 48 组事件、12 D2、8 比较/7 更新及三个状态 owner 均保留。偶帧仍在当前工程的 CNV 后 0–31.25 ns 写 AZ，奇帧保持；31.25 ns 开始 RA，45 ns 首 D2，90 ns release。这是保留成电时序的功能移植，北大原图则在采样期 AZ。信号 reset 保留 AZ 电荷；在线 epoch 中断写窗尚未完成资格验证。

斩波/AZ/选片控制属于片内 ADC；当前完整码恢复及后续配对放在 FPGA 域。外部训练参考属于片外仪器，不能读取实际电容、held 或内部残差。输入侧 chopper 的耐压、Ron、寄生、电荷注入及正负路径不对称尚未建立；不能直接用北大 1.8 V 开关替代当前 5 Vp 输入侧 IO 电路。

## 本次实际 N8 证据

同一试验 SLX：`63283fd769acdb4bdd4937df60e15b54196db01d219e830f7a010e8b60078964`。两个新 headless MATLAB 进程依次运行，原 GUI 和原计划任务保留。

| 配置 | 实际仿真 | 已验证范围 |
|---|---:|---|
| ordinary CICC | 19.1708961 s，8 个有效码 | 完整原 P 不变；既有日志和三根输出对正常 N8 逐位一致 |
| 输入侧 CAAZ | 16.2114318 s，8 个有效码 | ID4–11 极性 +−交替；完整 RAW→整数码独立核对；575 组 RA next→下一 old 全状态逐位一致；偶写奇持 |

时间是各一次运行的事实，不构成稳定速度比。参数仍采用正常估计中的采样 RC/kTC、固定失配/寄生、有限 DAC、有限 RA/普通热噪声 OU 和 SAR2/TA 比较器噪声。**本次整图 AZ 写入随机噪声关闭；1/f 时变源未实现。** 后端另有真实前态重放，验证一次写入创新确实进入 VX/VY，但不能用它代替整图降噪测量。

实际 sample 5：输入极性 −1，RAW 为 `138/3427/151`。被斩波域 D1 为 −4.3505859375 V，D2/G 为 +8.171875 mV，DT/G 为 +1.953125 µV；完整和恢复极性得到约 +4.342412109375 V，实际整数码为 **979623**。只翻 D2/DT 会得到错误结果。

[实际原码与重构](../analysis/behavior/caaz_adi_20261105/single_actual/caaz/raw_signed_code.csv) · [实际 AZ 状态](../analysis/behavior/caaz_adi_20261105/single_actual/caaz/az_actual_state.csv) · [运行回执](../analysis/behavior/caaz_adi_20261105/single_actual/caaz/complete.json)。原始 P、simout 和源码包分别保留身份。此 N8 不计算 SNDR；公开 normal 的 99.133 dB 不属于新 CAAZ 或 ADI。

原始转换流仍为 5 MS/s。若使用非重叠双样本平均，输出为 2.5 MS/s、Nyquist 1.25 MHz，并有双抽头平均频响；不能称作 5 MS/s 全带宽固定降噪。标准组件 FrameAvg 候选尚待实际建图/运行。

## ADI 物理 v2 正在实现的范围

直接把 37 个权重各拆八份会出现 3.375 fF 单元，目前没有目标工艺依据。当前设计方案改为：18 片各 `[2,31×4,2,1]Cu=129Cu`，加两组交替的 `[4,2,1]Cu` 尾阵列。活动组 `8×129+7=1039Cu`。双 QDAC 各自保留完整 1039Cu；它们自己采样和 trial，RDAC 只在 coarse/fine feedback 消费 accepted word，不跟随未判定试探。

新状态计划为唯一 FE owner `[FE353;tail32;Q173]`，共558字；共享 RA48、SAR51 不复制。OFF 保留353字。FE/tail/Q 在新 ADI profile 中从 −Ts 冷开 ID0 的预历史，single/CAAZ 仍沿用 −110 ns，模型 StartTime 与原 RA 事件不变。Q guard=0、RDAC/tail guard=2 ns 均为工程设置；非标称孔径及获取窗内 descriptor 变更尚未联合资格。

按当前每半边等效解释及 Cu=27 fF，制备电容约119.178 pF/half；P/N 实物之和238.356 pF。同时采集信号约55.296 pF/half，两侧实物之和110.592 pF，未含寄生。论文正文仅写 total sampling capacitor 28 pF，未给完整 P/N 几何；每半边口径是本模型假设，不是作者明确披露，也不是两端口差模等效电容。

固定双 QDAC/尾阵列奇偶与两相 POL 绑定，失配会与斩波效应混合。后续须分别核零失配机理、正常失配、真实选片、有限建立、公开训练/冻结和独立 holdout；不通过改成四相或读取实际 C 来消除问题。ADI 的两路 QDAC、共享尾、动态 Ctop/OU 和数字协议目前均为候选，不能称整图已完成。

下一项是实际接入 FrameAvg、开启有来源的 AZ 写入噪声并在同带宽下对照；随后才把完整 ADI v2 接入同一主图配置。先验证5 MS/s，再评估10 MS/s。
