# 单前端 5 MS/s / 1039Cu 隔离候选

**本文件是输入候选的背景说明；当前合并状态、变更和验证边界以 [README_MERGED.md](README_MERGED.md) 为准。**

本副本在 v2 单 bank 候选上增加 RA OU + ordinary AZ + 有限 DAC 的受限联合路径；本副本没有执行 MATLAB/Simulink、没有修改生产，没有启用 ADI 或 10 MS/s。数学条件、已验证内容与待执行测试见 [OU_AZ_DAC_README.md](OU_AZ_DAC_README.md)。旧 18/8/8/2 pool 的原 SLX、完整 P 与109源保持在历史 N8 归档；包里的 `production_pool_i2_n8.mat` 只作明确拒绝旧模式的负例。旧 raw 与频谱不作为本次联合路径的运行证据。

## 论文披露和模型假设

论文 Fig.2 标示单个一级 DAC1 为 `1039×27 fF`、6-bit coarse/5次fine、共享32× RA、CINC/CT SAR和8次tracking/7次更新。此候选假设一个可见等效单元为27fF，将现有8组**数值分段**并联成一组：每段Cu=27/8fF，37列权重总和1039Cu，第38列是断开的0C，C阵列=28.053pF、采样信号C=27.648pF、按Cs/32设Cf=0.864pF。两半/总差分电容口径尚未由原文完整证明，此计算不是电路网表恢复。

还假设1024Cu采Vin、15Cu采样端为VCM、粗阈值`8+16j`、比较零点按`>=0`、四舍五入与现有标称重构规则。论文没有披露完整DAC1底板表、粗码门限和差分归一。原文输入标注5Vp；当前行为模型仍用Vref=4.096V及原数字量程，不能声称已与论文输入幅度一致。RA有限增益/UGB与其他NI参数是原模型假设，普通AZ默认关闭；论文器件、噪声、离线LMS校准和性能尚未复现。不得把此函数候选称为完整论文复现。

独立数学码表来自 `/tmp/sar20_dac1_1039_oracle_pGd2km`，按其冻结清单SHA `86ed2dfec0c0ca5bcffecad80934e1886628462967568af0fe0aca52ac016262` 拷贝 `d1_codebook_2048.csv`（SHA `284598ca08207dba3332175861c8851deffa18c572141ea3e8a811c61d31e582`）；这个oracle验证的是明确列出的假设，不证明硅电路或整图。

## 单状态所有权和时序

同一 `FE353`（SampleCharge）存储一组电荷，不新增模拟owner；`RA48` 和 `SAR51` 保留现有状态/控制。所有ID都使用数值分段1–8，其余预分配条目停放，不代表额外物理ADC或实际18片pool。默认DEM/dither/jitter、数字系数Bank和旧pool训练/Frozen均关闭且setup拒绝开启；当前直出RAW，传输关闭，保留旧源但不自动启用它。旧模型P缺 `single_bank=true` 时setup拒绝，不能误把旧pool图称为单前端。

每个CNV先捕获本组并进入转换；原48组日历相对CNV不变，D1、RA、D2/TA、RawReady与release仍为原绝对时间。90ns release先用实际后端Vtop返还电荷，保留当次release的有效obs7；再预约同一组为ID n+1采样。开采时间=本次release+guard，下一CNV名义采样窗口为 `200−90−guard ns`。factory guard=0是未测的理想非重叠上界，**不表示实际开关延迟为零**。首样本冷启动从`−Ts+90 ns`预约，非一条真实的负ID转换。有限RC和正guard只在函数测试场景验证；尚未完成真实主图验证。

第38列0C在frontend init与NI nominal guard中作为断开支路，其他37列仍须正；每次FE状态输入若该组B或target非零则报错，不静默清零。release诊断对断开支路输出NaN；电荷状态和obs7不可由0/0污染。单bank下SAR控制标签固定为0；数字系数Bank是另一概念。

## 数字对齐与图安全门

`P.digital.d1_bias_v=0 V`，`behavior_decode` 将它用于单bank；旧无字段的软件参考仅保留历史 `−17Vref/1024` fallback，历史图和P不改。旧 pool 校准冻结值和Bank资格与新1039映射不兼容，公开 `SAR20('calibration',...)` 暂时明确拒绝。

本副本使用既有独立审计的 485 图，SID185 `D1CaptureBias` 绑定 `DecodeP.d1_bias_v`。图的 ModelWorkspace 内容不能仅凭图文件哈希认定为本次新参数；实际运行前仍需在隔离环境中完整核对和明确 apply 本次 P，再检查路径、图及来源。纯函数测试不加载模型。不可将本包直接覆盖生产或借用旧 as-run 输出作为本次联合运行结果。

## 验证边界

`[report,P]=test_single_bank()` 是尚未运行的 MATLAB 纯函数入口，构造并返回标准single P，并检查固定组、启动/两次采样、release→下一采样、正guard/有限RC、return obs7有限、断开支路负例、2048字与独立码表的电荷/数字关系、bank标签及旧pool/DEM/dither/jitter/Bank/10M/旧校准拒绝。P返回的是工厂零guard/理想采样配置；正guard/20ns仅为测试激励。测试不加载模型，不能替代SATK图修改、整图N8、动态/静态特性和论文对比。
