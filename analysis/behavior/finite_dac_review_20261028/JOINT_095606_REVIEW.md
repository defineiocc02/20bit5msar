# 095606：AZ 与混合 DAC 联合区间的独立回读

三组隔离图的实际数据支持以下**有限范围**结论：每组 8 条、ID 4–11 的 RAstart→首个 D2 prepare 区间及 8 条有效 RAW 已保存；以原实际物理状态标量构造的 native expm，三组 `max |VXpre−expm|` 均为 `1.1102230246251565e−16 V`。另以 Decimal90 对同一批保存标量独立计算闭式，三组 `max |VXpre−Decimal90|` 均为 `1.6653345369377348e−16 V`。这两项是原始差值，保存报告明确未设解析容差、未宣布解析通过。

| 实际配置 | AZ 第一半 leak | near 条件条数 | 有效记录 | 与原主图同配置的旧日志逐位一致 |
|---|---:|---:|---:|---:|
| far mixed | 1 µs | 0/8 | 8/8 | 30/30 |
| minus ULP mixed | 实际 RA pole −1 ULP | 8/8 | 8/8 | 30/30 |
| plus ULP mixed | 实际 RA pole +1 ULP | 8/8 | 8/8 | 30/30 |

三组均为 transport off、AZ `hold_chop`、Vos 1 mV、AZ write τ 8 ns、第二半 leak 为 Inf；18 个 DAC 片混合 0、约 0.1、1、5 ns。三组 P 之间除第一半 AZ leak 字段外逐位一致；每组与其对应原运行的完整保存 P 也逐位一致。所说逐位日志比较包含 class、shape、实际 Time 与 Data；far plain 与原主图亦为 30/30。

独立回读检查了每次实际 ADC 的 48 事件，12 次 D2 比较、8 次 TA 比较、7 次 TA 反馈及七个实际反馈符号；还核对实际 POL、AZ pair/write 标记和第二半 Inf 保持。探针报告的 Q0/Q1、VX0/VXpre 与实际 front/back/RaPre 对应事件点相符，实际 FE endpoint 及 RA target/NG/τ/Vtop 的数值边界均有检查；三份 `analytic.mat` 的逐样本字段与真实 probe 对应，RAW/code/time 也与实际 ready 记录相符。

隔离图相对无探针图新增 2 个观测块和 6 条观测边，340 条原边均保留、solver 相同；原有 4 个块仅位置改变。所加 S-function 无声明的连续状态、DWork、Update 或反馈边。归档 source ZIP 中运行时生产函数和五个核验 helper 的内容，与回执保存的 source pin 相符。回执称原主图未改变；本次离线回读没有独立检查远端进程的实时状态。

边界：native expm 与 Decimal90 都使用 probe 保存的旧 FE/BK 状态标量；完整 FE353/BK48 历史没有作为外部数据保存，不能称为完整旧态的独立重放，也不能把 FE 端点复算称为独立电路真值。±1 ULP 的 `near` 结论来自保存极点、非零 AZ 幅值及源代码分支谓词，不是独立分支覆盖仪表；RaPre 位于本事件后续反馈/提交之前，不是最终提交状态。这些 N8 行为模型结果不覆盖完整 ADC 噪声、INL/DNL、PVT、晶体管、PEX 或硅片性能。

逐样本值、原始误差、各文件 SHA 与图差异见 [joint_095606_independent.json](joint_095606_independent.json)，SHA-256 为 `6e1b0a88dc0afa1181da90362c1f6a0f3681983615ff0943b32e619645bfba3a`。只读重算入口为 [verify_joint_095606.py](verify_joint_095606.py)，需 NumPy、h5py、SciPy；未重新仿真或操作 Windows/current。
