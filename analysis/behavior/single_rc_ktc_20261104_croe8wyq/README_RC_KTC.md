# 单阵列有限采样 RC 与热噪声：隔离候选

**状态：静态检查和独立 Python 数学检查通过；MATLAB、Simulink、真实电路验证均未执行。** 本目录只含候选副本；基线是冻结包 `FROZEN_BASE_v2.zip`，SHA-256 为 `09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7`。保留原有 5 MS/s 单阵列限制，不启用 ADI/10M。

## 模型和边界

每次 release 后，原有 FE353 的同一份 `B_c` 保留返回电荷；`single_guard_s` 窗内保持，实际开采时刻为 release + guard。原有解析 RC 公式将已有电荷从真实开采时刻传播到名义 capture；零时常理想跟踪，正有限时常按 RC 衰减，`Inf` 保持。源变化必须通过原有 `input_change` 事件提交，先推进旧源再切换新源。没有新增事件或理想源覆盖有限 RC 状态。

在 capture，只对同一 `B_c` 一次注入新 Johnson 创新，不对此前已存在于返回电荷的随机成分重新注入。有限时常 `τ`、实际采样窗 `T_acq` 的差分创新方差为

\[\operatorname{var}(\eta)=\frac{2 k_B T}{C_{\rm sample,half}}\left(1-e^{-2T_{\rm acq}/\tau}\right).\]

`τ=0` 保留原有平衡 kTC 随机键和运算；`τ=Inf` 不产生新创新且 B 原样保留。开启单 bank kTC 时，有限采样覆盖只统计有效数值段 1–8，不由停放项 9–18 冒充。实现用 `-expm1(-2*T_acq/tau)` 抑制短采样窗的数值消失。由于噪声只在 capture 注入，采样途中的 observe 不展示即时随机轨迹；正有限 τ、正温度的开采已开始后若发生 reset，候选显式拒绝，避免丢掉未结算的噪声。采样期间温度、电容、τ、随机 seed 和拓扑参数应保持不变；S-function 参数原本是 nontunable，纯函数调用者也必须遵守此约定。

每个已提交 capture 须使用未重复的 `(ktc_seed, epoch, sample_id, 数值段)` 元组；相同元组必然重放同一噪声，用于重复 Outputs 求值的一致性，不能视作新的独立采样。FE353 不记录完整历史，因此纯函数调用方负责保证元组不复用。静态源码中事件源以 cycle 编号递增、控制阶段把 `sample_id=cycle` 并在单次 run 内固定 epoch；新 run 若仍使用相同 seed 和 epoch 会有意重放，而不能当成独立 Monte Carlo。此处是静态核对，未运行整图。

本扩展只允许**单物理 bank 的八个数值段使用相同采样 τ**。若第 j 段的单边电容为 Cj、总单边电容 C=ΣCj，则使用原有各段独立创新键时，按电荷求和得到 Σ(Cj/C)²·(2kBT/Cj)·(1−α²) = (2kBT/C)·(1−α²)，其中 α=exp(−T_acq/τ)。这不是八个 ADC。数学上的独立性是模型假设；现有有限位哈希与 Box–Muller 只是可重复的伪随机近似，不能仅凭种子不同宣称严格独立。

若开采时总电压随机分量为 X0，新创新与 X0 独立，则 `Cov(Xcapture, X0)=α Var(X0)`，`Var(Xcapture)=α² Var(X0)+(2kBT/C)(1−α²)`。实际回返 X0 可包含上次采样和后端的噪声，必须通过真实返回电荷及有限 RC 传递；文中公式不推断该电荷的实际分布。

单 bank jitter 仍关闭，任何有限 RC + jitter 仍拒绝；不声称已支持共同孔径抖动与有限 RC 的组合。也未修改基准电压、数字标度、FE353 接口或 s-function 状态所有权。普通 AZ、RA OU 等其他组合依赖各自门禁及后续联合验证，不由本次数学检查证明。

## 可估参数和结果

以基线模型的单边采样电容 27.648 pF、温度 298.15 K、5 MS/s 日历的 90 ns release 和假定 guard 5 ns，得到采样窗口 105 ns；再**假设**等效 lumped τ=5 ns，R_eff=τ/C≈180.8 Ω，差分采样创新 RMS ≈17.26 µV。该 R/τ 是未经电路提取或测量的演示值，不是工艺事实、测量值或已验证 normal 条件。真实阻值、布线、开关导通随输入变化、源阻抗及噪声应由电路/仿真或测量提供。

`independent_oracle_result.json` 记录 5 个时常的解析式与独立 Simpson 卷积最大差 4.30e-12 V；198000 个有效 ID 的原键伪随机采样中，八段合成方差为 0.9991，受控一阶反馈状态方差为 0.9964，一阶协方差为 0.3634（理论 0.3679）。这是固定 seed 的数学和伪随机有限样本检查，不是 MATLAB 执行、主图结果或电路真实性证明。

## 可复核内容

- `single_bank/tests/test_single_rc_ktc.m`：待运行的 MATLAB 纯函数测试草案，覆盖 OFF/τ=0 与冻结 v2 逐位比较、开采 guard、分段源变化、返回贡献衰减、有限时常创新、Inf、零温、重复求值、无全局 RNG 改变、非法组合、配置门禁及受控协方差。测试不得加载或运行主图。
- `single_bank/tests/static_check.py`：比较冻结包，确认限定文件差异、旧随机函数/键、353 接口和既有限制；不执行 MATLAB。
- `independent_oracle.py`：可重复的独立卷积、总方差和有限样本协方差数学检查。
- `rc_ktc_changes.patch`：相对冻结 v2 的源码差异，便于人工合并；尤其注意 `behavior_ra_noise_guard.m` 与 RA OU 候选、前端文件与公共 jitter 候选有重叠，不能直接用整文件互相覆盖。
- `single_bank/current/models/SarAdc.slx` 仍是历史 d4 模型，**不能直接作为已审计单前端主图使用**；如后续获准做整图验证，须使用独立审计过的 485 模型并重新核验 P、源码和模型绑定。

本候选不执行 Windows MATLAB、未修改生产工程、未读任何超过 300 MB 的文件。
