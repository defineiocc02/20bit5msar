# 单 bank OU、ordinary AZ、有限 DAC、采样 RC/kTC 和比较器候选

**状态：隔离源码候选。合并后的 MATLAB 函数测试和 Simulink 均未执行；不能用旧候选的单项通过结果代替联合验收。** 本目录位于库外，未修改生产工程。输入与证据：

- 单 bank v2：`09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7`。原件及逐项哈希保存在本目录的 `baseline/single_bank` 和 `BASELINE_SHA256.json`。
- OU/AZ/DAC：`34e70704d9a6a4ed9d2eb794e67ee5ee738dfe99db2c8f4cc3f8ab4e9bde8631`。该旧候选有已运行 MATLAB **纯函数**回执 SHA `0ea5c11c2e47e26ce24cda2e1f9e936efdbb269ff371f51fa0f4195c6bf362a2`、报告 SHA `7cacedb73257f0bcd178e73348be11d55f6db80064f7c4c67559015fa841a715`；仅代表旧候选而非本合并树。
- 有限 RC/kTC v3：`ede479868189a4e5a712e172173db7759208a62e1bfe9d6b31e644e86756feff`；已有独立 Python 数学检查，本合并版本尚未进行 MATLAB 函数验收。
- 比较器上游：`368bc52069485dc1d14297349bddb1f669f251a62859fd8dfed2f0822de3a89b`。控制/采样四个源码逐字节继承；其旧归档事件回放不是本次图验证，single-bank 限定配置与联合 gate 是新源码。
- 485 独立图：`48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3`。真实运行前须重新 apply 并核对 ModelWorkspace 的完整 P、DecodeP、函数路径及图身份，不能复用图内旧 P 作为本次输入。

## 功能边界

联合资格限于 5 MS/s、一个物理 bank（前端八个数值段）、M8、固定 Ctop、线性无限 slew、ordinary AZ 或 AZ off、有限非负 DAC 时间常数。前八个采样段开启 kTC 时必须使用同一个采样 τ；有限 RC 与 jitter 的组合仍拒绝。训练、静态校准、Frozen、数字 Bank、DEM、dither、transport、ADI 和 10 MS/s 仍不启用。候选使用者须提供带来源的具体参数；这里的测试值只是激励，不是论文、PDK 或测量到的 normal 值。

每个 RA active 区间先从唯一旧 VX、旧 FE/AZ 状态计算有限 DAC 和 AZ 的确定性演化，再按原始事件两端点键给同一 VX 加一次 OU 创新。到期反馈先提交对应电容和 CINC，物理 VY 经原 485 图送入本次比较，CMP 在该 VY 上局部加 offset/创新并决定 RAW；新判决的物理反馈仍在现有下一 due 事件提交。固定极点的一阶 OU 噪声带宽与信号极点绑定，本候选没有独立 noiseBW。比较器模型只覆盖 SAR1 fine 与 SAR2/TA 的指定比较；Flash 前级随机噪声、比较器迟滞/延时/无效判决均不在模型中。

每次采样只在 capture 给已有 FE353 的信号电荷叠加一次有限时间热创新。释放时从实际 Vtop 返回的已有随机电荷仍通过有限 RC 衰减，不能把 kTC 重复注入。OU、CMP 和 kTC 的伪随机键各自确定；跨源创新的条件独立是行为假设，键域分离或有限样本相关接近零不能证明物理独立。反馈使后续 VX、VY 和 RAW 彼此相关，完整闭环不必服从无条件高斯分布。相同 key 必须重放同一创新，不能把重复 Outputs 计算当成新的模拟采样。

`guard=0`、单 bank、kTC ON、采样 τ=Inf 时，候选只对信号电荷跳过会造成 1 ULP 变化的 `B/C*C`；尾组按原逻辑预充。kTC OFF 保留冻结 v2 的原运算。配置标签 `sample_ktc=false` 表示没有新热创新，不表示返回电荷没有既存噪声；为保持历史行为，kTC OFF 时 `sample_settling` 仍扫描全部 18 个配置项，停放项非零可使该标签不能代表有效段实际覆盖。

## 复核和测试入口

`tests/static_check.py` 核对源、485 图、日历及码表；`tests/static_merge_check.py` 对比三套冻结输入、关键覆盖门禁、状态 ABI 与 485 图的 due→CT→VY→decide 静态连线。它们不执行 `.m`。`tests/joint_key_covariance.py` 检查固定测试键对的有限样本相关，不验证完整闭环或严格独立性。各测试的 JSON 结果以实际生成的文件为准。

独立 headless MATLAB 进程中的建议函数入口为 `test_joint_ou_az_dac`、`test_single_rc_ktc`、`test_joint_ou_rc_return` 和 `test_comparator_single`。它们包含原 v2 OFF/零σ逐位对照、相同键重复求值、固定 Ctop/时间/覆盖拒绝和受控事件测试；每项都必须在实际候选路径身份核验后执行并保存原始回执。OU 测试依赖本目录旁 `baseline/single_bank`；合并代码和这些测试目前均未执行。函数通过也不等于 485 图、N8/N256 频谱或电路结果通过。

本次候选 ZIP 和 `MANIFEST.json` 只固定源码、图和测试身份，不能作为联合仿真已通过的回执。回滚可从已保存的 OU 输入和共同 v2 基线重建独立目录，不覆盖原输入或生产工程。
