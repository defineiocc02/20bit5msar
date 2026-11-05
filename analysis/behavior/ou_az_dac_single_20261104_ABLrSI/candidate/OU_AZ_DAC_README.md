# RA OU、ordinary AZ 和有限 DAC 的隔离候选

状态：**数学和静态检查已完成；本次候选的 MATLAB 函数和 Simulink 运行均未执行**。唯一允许的新组合为 5 MS/s 单 bank、固定 Ctop、线性无限 slew、ordinary AZ 或 AZ off、有限非负 DAC τ。启用 OU 时 Inf DAC τ、chop/hold AZ、有限 slew、随机 AZ、比较器/参考噪声、旧训练/Frozen/Bank 仍由门禁拒绝。所有数值参数仍是调用者提供的行为假设；本改动没有为追求 7 dB 而调整 OU σ 或 τ。

## 条件、数学和端点顺序

单个 RA active 事件区间令 t=0 为旧态时刻，h 为原始事件时刻相减的长度，旧命令的 Ctop、Cf、A0、UGB 及由其确定的 τ 保持不变。令确定性驱动 `g(t)` 包含旧 FE 的有限 DAC 电荷变化及已存 AZ 两半的指数泄漏；它们可以依赖区间以前的转换和反馈，但必须在区间起点可由旧态确定，不能依赖当前区间未来的 OU 创新。写成

```
dX = (g(t)-X)/τ dt + σ sqrt(2/τ) dW
X(h) = exp(-h/τ) X(0) + ∫ exp(-(h-u)/τ)g(u)/τ du
     + σ sqrt(2/τ) ∫ exp(-(h-u)/τ)dW(u)
Var[innovation | old state] = σ² (1-exp(-2h/τ)).
```

因此可先在**同一个已有 VX 旧值**上计算代码中 AZ + DAC 的解析卷积，再在端点 CINC kick 之前加一次创新，之后按原逻辑计算观察、执行开关、提交原状态。OU 来源是输出端的加性行为假设；AZ 感测表是确定性的，并未给 AZ 带入 OU 采样噪声。反馈或返回电荷可以使以后区间的确定性驱动依赖以前的噪声；不能将整条闭环记录无条件称为线性高斯过程。

如果固定极点、恒定 σ、无复位/反馈且 OU 初态已经平稳，噪声分量 `Cov[N(t),N(t+Δ)]=σ² exp(-|Δ|/τ)`；零初态则需减去 `σ² exp(-(t+s)/τ)`。平稳的双边 PSD 是 `2σ²τ/(1+(2πfτ)²)`。模型的**噪声极点绑定信号极点**，这里没有独立 noise bandwidth 或额外噪声状态，不等同于经测量的 RA 噪声谱或开关噪声。

当前 `sar20_ra_keyed_normal` 用 seed、epoch、sample_id 和原始 binary64 两端点构建 SHA-256/Box–Muller 伪随机创新。其高斯、跨事件近似独立是模型假设，有限 seed 统计不是独立性证明。改变事件切分会改变键，故同 seed 不保证不同网格上同一布朗轨迹。RA-off/reset 保留原模型的无 OU 创新及复位衰减语义，不能假设跨 reset 全程平稳。

## 实现边界

- `behavior_dac_coupling_configuration` 只为新组合绑定实际单 bank 的固定 Ctop 和已有前端 plan/tau；它们是参数，不是新增状态。实际模型 P 的 gate 对绑定与前端逐项核对，`behavior_backend_step` 对命令 Ctop、有限 DAC 旧态驱动、极点、标签和极性再检查。
- `behavior_backend_stage` 的有限 DAC active 分支把原始 `eventTime` 直接传给 `behavior_backend_step`；noise OFF 及零时长沿用原调用。`sar20_ra_ou_increment`、随机键、σ、τ、48 字 RA 状态、S-function Outputs 和现有 UnitDelay 均未更改。`stage` 仍在打包前按原实现将时间对齐到原始事件字。
- 实际图路径从 OLD FE353 输入生成 forcing；直接调用 step 时调用者负责真实旧 FE 来源，结构校验不能证明手工伪造的数据来自该 FE。单 bank/5M、M8、校准、CINC 网络及其它原有门禁仍然生效。
- 图为既有 485 隔离图，SHA-256 `48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3`。应在隔离环境重新 apply 并比较 ModelWorkspace P/DecodeP；不以图内历史 workspace 或现有 N8/N256 记录冒充本联合候选运行。

## 本次验证与后续执行

`python3 tests/static_check.py`：v2 来源/图哈希、源文件变更清单、单 bank 与 2048 项独立码表静态检查。`python3 tests/joint_math_oracle.py`：Python 浮点公式转录对 70 位精度直接积分，以及 4 万 seed 的 OU 有限样本协方差检查。二者都不执行 `.m` 文件。结果及容差见同级 `STATIC_CHECK.json` 与隔离目录的 `JOINT_MATH_RESULT.json`。

`tests/test_joint_ou_az_dac.m` 是未运行的 MATLAB 函数级草案：构造真实旧 FE/AZ/RA 状态；检查同一 VX 的创新、原始事件键、ON 重复性；比较 disabled 与 σ=0 的位模式；将 disabled 与原 v2 代码同状态位比较；并测试失配元数据、有限 slew、Inf DAC、chop、随机 AZ、错误时刻和 10M 门禁。请在可控的独立 headless MATLAB/Simulink 进程、且 sibling `baseline/single_bank` 仍存在时运行：

```
addpath('/absolute/path/to/candidate/tests');
report = test_joint_ou_az_dac()
```

该测试未执行，草案可能需要由首次实际运行暴露环境或代码问题；通过后仍须单独制定并执行独立图 N8、状态/事件复核及所需 N256 对照，不能把数学检查当作全图证明。
