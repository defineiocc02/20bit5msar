# 固定 A/B 前端与采集保护时段：隔离候选，未部署

## 状态和范围

该目录是从当前项目只读复制的独立源码/配置/SLX 快照；生产工程未改，本轮未启动 MATLAB 或 Simulink。它是待实际运行的候选，不是已经验证的修复，也不是面积、功耗、PDK 或硬件签核结论。原 I2 模式保持默认，I1 显式选择。`5 ns` 只作为测试示例，不是已测或已签核非重叠时间。

Rev0.5 `contract/SPEC.md` 第 45–57 行要求先固定 A/B，采集有效时间扣除开销，18/8/8/2 为后续研究。11 月 4 日 N256 实际运行的 P（fixture SHA `f30b3cfa...`）中，DEM=0，但 264 行计划仅首行与固定 A/B 对应，物理片 17/18 分别出现 118/114 次；这是已运行的 I2 证据，不是 I1 通过证据。

## 两个模式及配置

- 历史 P 未包含 `schedule_mode` 时仍走旧 `pool_i2`；旧 `make_plan` 字节完全相同，旧分支的前端推进算术顺序保留。`schedule_mode='pool_i2'` 时 guard 必须为 0。静态相同不等于真实 MATLAB 全输出逐位相同，后者尚未测试。
- 通过被隔离的 MATLAB 环境构造示例（未运行）：

```matlab
P = adc_parameters();
P.front.schedule_mode = 'fixed_ab_i1';
P.front.acq_guard_s = 5e-9;       % 假设，不代表电路测量
P.front.plan = [];                % 显式要求重新派生，拒绝沿用旧池计划
P = behavior_prepare_configuration(P);
```

I1 要求 guard 在初始 `−Ts` 及本次全部计划 CNV 的 binary64 绝对时刻均能表示为 `CNV < CNV + guard < 下一 CNV`，不足或过大在 prepare 时拒绝；有效 jitter 孔径还须晚于接通时刻。I1 的 ID0/2/... 使用片 1–8、ID1/3/... 使用片 9–16，片 17/18 永远不参与；这是在原 18 片数值状态上模拟两个固定电容组，不是对实际物理电容实现或面积的证明。转换 ID n 的组，恰是上一 CNV 为 ID n 开始采集的组；相邻 ID 组无交集。同 ID 原字、RA、CT、返回依旧沿用原接口和标签。

## 保护时段与物理因果

- CNV 时间、原一级 SAR、RA 开始、D2/TA 比较与反馈、86.25 ns RAW、90 ns release 事件均不改。CNV n 先捕获/转入 ID n，并为 ID n+1 预留另一组；其物理采集从 `t_n + guard` 开始，下一名义孔径为 `t_n + Ts`，因此名义有效采集窗口为 `Ts - guard`。起始 ID0 亦从 `-Ts + guard` 物理接通。
- 预留但未物理接通期间，该组 signal/tail/bias 保留已有电荷，目标 metadata 可更新；跨过接通点时，使用接通时刻起的一阶解析 RC 推进到实际事件端点。guard 在现有状态中的 `acquire_open_s` 保存，不新增全局事件，也不把前端时间推进到未来。`phase==1` 在 guard 内表示**组已预留**，须结合 `acquire_open_s` 判定是否已物理接通。
- `tau_sample=0` 表示在物理接通时理想跟踪源，正有限值使用解析 RC，Inf 表示保持；tail/bias 以相同开始时刻使用各自 precharge tau。信号源在 guard 内变化时不提前改写保留电荷。极短时间有限 RC 和正弦边界数值准确性仍需 MATLAB 验证；使用前需覆盖 tau=0、Inf、跨/恰等接通边界、源变化和非有限输入拒绝。
- release 沿原路径先读取实际后端 `Vtop`，按原极性转换后返还 `B_return=B_pre−C_group·Vtop`；I1 到下一次轮到该组时，以上一次返回的 B 为采集初值。当前日历下同一固定组的上次 release 到下次 CNV 的间隔为 `200−90=110 ns`，到新实际采集接通为 `110 ns + guard`。
- jitter 仍是已有的充分建立信号端点近似；实际孔径须严格晚于开采时间；有限 RC 与 jitter 仍被拒绝，未新增完整时钟抖动。kTC 与有限采样 RC 组合仍受原约束。正 guard 不代表已经对开关注入、kickback 或驱动器非线性建模。
- `frontend_step('reset')` 仍要求先释放 active 转换组，再清标签/相位而保留电荷。现有控制 stage 明确不实现完整运行期 EN/reset/epoch 切换；选择 I1/I2 是重新 prepare/apply 的离线配置，重建初始条件，不是无缝在线切换。不得把本候选说成对完整复位协议的实现。

## 校准边界与防护

I1 禁止复用 I2 的训练、`cal_cfg`、冻结系数及数字系数 bank；`digital.calibration_mode` 必须 off。准备配置前若显式 ON 会拒绝，准备完成后由实际 SLX `RaAdvance` 参数入口 `behavior_dac_backend_parameters` 再检查，绑定 mode/guard/plan、初始前端开采状态及初始化时 P.input / P.front.input / xFE0 中四个源值；这个核验只发生在 prepare 和运行 setup，不限制运行时 Driver 按原事件机制显式变化。I1 的禁用 collector 仍保留 cfg17 结构，但将 schedule 标签改为 `inactive_fixed_ab_i1_no_calibration`；它不表达可用 I1 校准。新采样计划需要独立的公共特征版本、重新训练和独立 holdout，本候选未提供。

## 验证与未验证

- `STATIC_ORACLE_RESULT.json` 来自已运行 `tests/static_and_oracle.py`：102 个原 `.m` 中 97 个完全未改、5 个修改，新增 1 个 I1 guard；SLX 字节与当前源快照一致。I2 的 plan 函数及推进分支算术文本逐字核过。独立 Python 积分 oracle 核了 27 个假设 RC/正弦数值案例，最大原始差 `4.58e-16 V`；还在 Python binary64 验证过极小 guard 和接近 Ts 的 guard 均有时间重合、5 ns 示例 12 周期无重合。该检查没有执行 MATLAB 候选代码。
- `tests/test_i1_candidate.m` 是准备好的函数级测试，**尚未运行**。它设计为比较原/候选 I2 前端 15 个实际事件中 state/observation 的类型、形状与位型（含 ±0 和 NaN），检查 I1 固定组、guard 内保持/开点、真实 Vtop 返回再采集、显式函数 reset、日历不变、不可表示 guard、初始输入单字段漂移和训练/冻结/Bank 拒绝。它不替代整图比较。
- 在独立 MATLAB 进程中，还须先运行上述函数测试，再对同一主图、同一个完整 P 进行 I2 默认基线/候选比较所有实际 timeseries `Time`/`Data`、根端口和 RAW/码/ID，按比特逐字段检查并保留源/model/P SHA。再做 I1 N8，逐 ID 检查 A/B 交替、组不重叠、`t_open/t_ap`、返回电荷、12 D2/8 TA/7反馈、根口和有效性；针对有限采样 RC 比较独立积分，检查 guard、reset、非理想/非法组合的拒绝。候选 I1 的完整连续链和 I2 默认逐位行为目前均未经过 MATLAB。
- 现有模型标注尚未显示 I1/guard，须以实际 P 为准。
- 本包包含原入口 `SAR20.m`、原 SLX 的隔离副本、源树、配置/nominal.mat、原前端基线及测试；不含 Simulink Agentic Toolkit，也未证明当前 MATLAB path/许可证或本包 cold compile。必须在隔离目录绑定现有依赖并检查真实函数解析，不能覆盖生产源码/SLX或历史 raw。
