# 正常工作点：非理想三态核对

本表核对**实际 prepare 的 P、主图 N8 的保存 P、原始回执及5项函数门**。该联合正常点已经过一次 Simulink 主图 N8 运行，输出8条有效记录；探针运行的3个根输出与普通运行相同。这是行为模型单点证据，尚未单独量化每一种非理想的作用，也不是参数扫描或工艺验证。所有数值均为行为配置及其明确假设，不是 PDK／论文标称。

| 模块 | 已实现的范围 | 此次实际准备参数 | 已验证／已扫描的边界 |
|---|---|---|---|
| 输入与几何 | 已实现单阵列；FSR10由独立范围配置派生 | 5 MS/s；N=8；FSR=10 V；Fin=97.65625 kHz；峰值 4.45625469 V；Cf=864 fF | 10 V范围函数门及本联合P的主图N8已运行；5 Vp的差分口径仍是假设。 |
| 采集／guard | 单阵列同一状态先release再采集 | guard=2 ns；采集窗108 ns；τsample=0.563041298 ns | 有限RC+kT/C函数门及该联合配置的主图N8；未对guard或采样τ做本正常点扫描。 |
| 采样 kT/C | 单bank有限RC随机创新与历史状态 | ON；T=298.15 K；seed=20261027；实际信号C=27.6471028 pF/half；平衡近似σ=17.2563616 µV rms | 函数门 7168 点：归一方差=0.9803、lag-1=0.35627（理论0.36788）；非此P的统计或PDK证明。 |
| 一级C固定失配 | 显式实际C参与模拟电荷；不输入数字权重 | ON；σunit假设=0.06804138%；seed=20261104；8个数值段逐列一致，38列=0 | 已联合运行一颗假设芯片；没有此profile多chip/梯度/PN独立失配扫描。 |
| 前端／RA负载寄生 | 前端Cp计入Ctop；RA输出负载进入kick分母 | 前端Cp=100 fF/half；RA输出=0.5 pF/half；Ctop=28.1520649 pF/half | 两个数均为未提取假设；输出负载不是完整RA负载极点。 |
| DAC有限建立 | 旧FE状态驱动RA解析耦合 | ON；τDAC=0.5 ns；coupling=true | OU+AZ+finiteDAC函数门和联合P主图N8；未单独量化本次DAC效应或做工艺扫描。 |
| RA有限增益、带宽与失调 | 单极点、有限A0及输入差分Vos | A0=10000；UGB=1.2 GHz；NG=33.5834085；τ=4.45413789 ns；Vos=+1 mV | 有限参数及Vos为设计假设；非电路辨识；1mV普通AZ曾作另一个N8对照。 |
| 普通 AZ | 输入参考有限写入与保持；无随机AZ噪声 | ordinary ON；write τ=1 ns；leak τ=10 ms；sense扰动=0 | 普通AZ在旧条件有N8；本P的10 ms保持未单独扫描；不证明1/f或3级环放。 |
| RA OU噪声 | 固定极点带限OU；事件键重复确定 | ON；σVX=0.51278539 mV rms；seed=20261104；假设ENBW=56.1276 MHz、1.25 ns相关系数≈0.755302 | A1通道热噪声代理；函数门与联合P主图N8已运行；不等于全部RA噪声或本P PSD验证。 |
| 二级/TA比较器 | 已实现VY输入参考、逐决策噪声候选 | ON；σVY=0.286928737 mV rms；seed=20261105；固定offset=0未注入 | 比较器函数门与联合P主图N8已运行；sigma来自假设100 fF等效噪声电容，不是再生锁存器实测。 |
| 一级细／Flash比较器 | 无该配置噪声覆盖；Flash随机噪声未实现 | SAR1细noise=0、offset=0；粗Flash noise=0、offset=0 | 关闭或未实现，不能因SAR2噪声开启而计入。 |
| CT CINC与replica | 主/副独立网络及反馈kick路径 | ON；名义900 fF；主=900.075 fF，副=899.925 fF/half | 确定性一σ配对示例；其他CT电容名义；本联合N8已运行，尚无该P同事件归因的kick量化或扫描。 |
| 参考与驱动噪声 | 固定参考源；恢复/噪声无当前实现 | 前端Vref=5 V；CT Vref=1.8 V；随机参考噪声OFF | 动态参考恢复/噪声和驱动噪声未建；标称设置不等于测得误差为0。 |
| 孔径/全时钟jitter | 有限RC+jitter联合未获资格 | OFF；0.5 ps是单独预算，不在本P启用 | 不算覆盖；不把旧25 ps压力案迁移到正常点。 |
| RA slew／非线性 | 有限slew近似在其他条件有代码，联合有限DAC未获资格 | slew=+Inf；非线性RA OFF | 不是有限slew覆盖；没有晶体管动态和FIA储能模型。 |
| 数字校准／传输 | 名义权重、直接RAW | training、frozen、Bank、transport、DEM、dither均OFF | 论文芯片采用片外LMS；当前不应称已复现校准结果。 |
| tracking | 固定M8日历与SINC²名义重构 | 每周期12次D2、8次TA比较、7次反馈 | 探针检查记录阶段next/control及命令线计数12/8/7，并非独立已提交状态历史；不把理论9 dB或论文7 dB当已验证收益。 |

**本次主图 N8 证据。** [普通运行回执](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_main_actual/normal_merged_n8/complete.json>)和[探针运行回执](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_main_actual/normal_merged_n8_tap/complete.json>)均为 passed。实际公开记录均为 ID 4–11 的8条有效码，两个 CSV 的 SHA-256 均为 `8c5f6222d031e33f70a0401473637bb64fe2ce12d9fa22f5ac4c0dc4bd24037d`；[探针对照](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_main_actual/normal_merged_n8_tap/tap_comparison.mat>)报告3个根输出一致。普通运行 [P_used.mat](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_main_actual/normal_merged_n8/P_used.mat>) SHA-256 `e42b739ed7c465845ed0e415a9f2fdfdd1afa0caaf0c18055c3f77fbfe683b61`；两份运行参数的前端、后端、控制、非理想、数字、输入和禁用项等子树与 prepared P 逐字段一致，探针仅用于观察。回执所列设置是注入的 SimulationInput／预期配置，未独立探测运行时模块对话框。探针中的 `adi_enabled` 是只读观察开关，物理 ADI、DEM 和 dither 均未开启。

此次 N8 是所有所列开启项的联合运行，不能据此分别测出 kT/C、C 失配、有限建立、AZ、RA 或比较器噪声的单源贡献。RA 噪声仅是 A1 通道代理，比较器噪声仅覆盖 SAR2／TA；驱动与参考噪声、其他 RA 级、AZ 噪声及 SAR1／Flash 噪声仍不在覆盖内。

真实参数：[normal_P.mat](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/profile/normal_P.mat>)（SHA-256 e3152a7d2cd3ee2a4faeb3e933c169f4317cfb16b63a87df75c67f2865d03674）；[assumptions.mat](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/profile/assumptions.mat>)（SHA-256 a93a899e9c914cdfcfc01bb3b334c4d86875f7eb20d84552328993c996e2ea47）；[profile回执](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/profile/complete.json>)。五项函数门的 [采样RC+kT/C](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/gates/test_single_rc_ktc/complete.json>)、[OU+AZ+DAC](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/gates/test_joint_ou_az_dac/complete.json>)、[合并返回](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/gates/test_joint_ou_rc_return/complete.json>)、[比较器](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/gates/test_comparator_single/complete.json>) 和 [10 V范围](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/gates/test_normal_10v/complete.json>) 使用同一冻结候选源码清单；函数门不代表五类非理想组合在主图的结果。

完整阶段还核对了控制器中先经零退出和后验校验再追加的 completed 记录：[执行状态](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/controller_status.json>)、[执行状态](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/recovery_status.json>)、[执行状态](</Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/normal_workpoint_20261104/windows_gate_asrun/profile_startup_status.json>)；某批次后续阶段失败不撤销其 completed 中的先前阶段。独立检查了P/assumptions哈希、11个与物理路径有关的磁盘源码字节、完整五门回执与报告哈希、实际C矩阵及8段相关性、CT与RA参数、噪声公式和零/Inf/关闭项；这不单独证明所有MATLAB传递依赖的动态which或缓存字节。离线审计未运行MATLAB；本normal P尚无参数扫描、PSD、全范围静态线性、PDK或电路级结论。前端信号C和Cp的半阵解释、等效RC与各噪声/匹配参数均按来源说明保留假设标签。
