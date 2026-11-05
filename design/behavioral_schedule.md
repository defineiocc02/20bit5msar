> 历史设计草案：2026-10-27已建立并实际运行新的行为模型。当前接口和验证范围以根目录README、current/src及CHECKPOINT为准；本文包含未实施设想，不作为当前集成/运行证明。

# SAR20 行为级模型事件调度草案

本草案用于新的独立行为级 Simulink 模型。停止围绕 getter、MEX、1540 节点矩阵或 250 ps MATLAB 包装器做局部提速；保留采样、逐次判决、下一拍反馈、tracking 和数字接口语义，把计算放在相应事件上。本文只定义调度及复用边界，尚无新模型运行或速度结果。

## 1. 已核实的起点

从 `state/current_workspace.mat` 读取的实际参数：采样周期 200 ns，控制时间量子 1.25 ns；LVDS 专项 pin 模式时间量子 250 ps。12 次 D2、8 次 TA 比较、7 个保留反馈符号分别是独立约束，不能互换。当前具体内部时间表是实现假设，约 90 ns 转换／10 ns tracking 是其论文范围，不能把整张表标成论文或 STA 证明。

N8 有 14 个 CNV slot，窗口 −200 ns 到 2750 ns；N256 有 262 slot，窗口 −200 ns 到 52350 ns。现有公共 plan 两者均为 276×8，已逐 bit 相同。新的模型沿用 sample_id/epoch 与物理 slice 的键，不因事件调用次数改变选择或随机序列。

## 2. 调度图与标准组件

建议默认图为：

`周期事件源 → 有序事件分派 → 行为状态推进/比较 → SAR控制 → 下一拍反馈提交 → 原始记录 → 帧级传输 → 原生定点解码`

- 用标准 **Function-Call Generator** 生成 `[200e-9, offset_s]` 周期事件，用 **Function-Call Subsystem / Function-Call Split** 表达同一时刻的调用顺序。相同 offset 的源合并，多个事件类型在同一事务内处理。
- 新模型用离散状态与 variable-step discrete 调度；仅保留事件源的 sample hit。不得另留 250 ps／1.25 ns 周期 MATLAB scheduler、Scope 固定采样或继承了该全局速率的 owner 使全图重新逐 tick 工作。1.25 ns 是控制日历的粒度，不是必须执行一次全图的周期。统一排序键可用原250 ps量子整数：控制事件为5的倍数，138 ns帧关闭为552；保留事件的原物理秒值，不以反复浮点加法生成时间。
- 用 **Bus Creator / Bus Selector、Selector、Assignment、Switch、Relational Operator、Sum、Gain、Unit Delay** 保留可读的控制、定点数学和状态提交。行为关系可放在被事件触发的 **MATLAB Function** 内；模型必须可独立运行，不把旧工作区脚本当隐含初始化。
- **Unit Delay** 只在其所属 function-call 事务上提交本模块状态。它不能直接替代“物理时间 +1.25 ns 的反馈”，后者必须有单独 scheduled commit 事件。
- 负时间 priming/reset 是一次明确初始化事务：输入源按真实 −200 ns 起点建立采集状态；t=0 的 aperture/CNV 仍在 t=0，不能把整个时间轴平移来省初始化。

标准 Function-Call Generator 支持显式 sample time；Split 可控制多个 function-call 子系统顺序，见 [MathWorks Function-Call Generator](https://www.mathworks.com/help/simulink/slref/functioncallgenerator.html) 和 [Using Function-Call Subsystems](https://www.mathworks.com/help/simulink/ug/using-function-call-subsystems.html)。实际 R2024a 图仍须通过 update diagram 和 sample-time 检查，不能仅凭草案确认零空转。

## 3. 每个 CNV 的事件表

时间均相对所属 CNV，k/m 从零开始。编排从保存的 `SAR20_P.timing` 生成，不能复制另一套会漂移的常数。

| 事件 | 保存的时刻 | 需要执行的工作 |
|---|---|---|
| CNV/aperture | 0 ns | 捕获已采集输入；确定 ID/epoch、convert/acquire slice；开启下一样本采集请求；启动 coarse |
| acquisition open | 请求时刻 + 各 slice 保存的 open delay | 建立实际采集窗口；不能把请求时刻当开关真正接通时刻 |
| coarse latch / fine prepare | 12.5 ns | 锁存 coarse，建立第一个 fine trial；同拍按原先输出/提交顺序隔离 |
| 5 次 fine prepare | 12.5+3.75k ns | 改变 trial、推进相关行为状态，不先消费未来判决 |
| 5 次 fine decide | 15+3.75k ns | 推进到比较时刻，读取比较结果，形成 pending command |
| fine feedback commit | 每次 decide +1.25 ns | 下一拍公开已提交命令；最后一次与31.25 ns fine-end/RA-start合并处理 |
| RA enable / AZ阶段切换 | 31.25 ns | 使用原状态连续推进；更新相位、AZ读写关系及保留的RA行为态 |
| 12 次 D2 prepare | 43.75+2.5k ns | 设置待比较位，当前候选电容保持neutral，前缀只含已经提交的位 |
| 12 次 D2 decide | 45+2.5k ns | 比较、记录原始位与invalid/late标志；decided_count依次1…12 |
| D2 feedback commit | 每次 decide +1.25 ns | 在下一比较前提交前缀；与下一prepare同拍时明确先反馈提交再形成新trial |
| 8 次 TA compare | 75+1.25m ns | m=0…7各进行一次真实残差比较，形成8位raw_DT |
| TA feedback commit | 每次比较 +1.25 ns | 前7次形成7槽保留反馈符号；第8次仍有比较/RAW语义，不虚构第8个保留反馈单元 |
| tracking end | 85 ns | 保留最终反馈前缀，设置done；不与最后比较混写，m=7比较在83.75 ns |
| raw latch | 86.25 ns | 锁存D1[11]、D2[12]、DT[8]、valid、sample_id/epoch等记录 |
| analog reset/release | 90 ns | 提交phase变化与必要的行为状态重置/释放；不清空所有跨样本记忆 |
| 其它保存的deadline/reset/epoch | 按配置 | 保留超时、复位域、invalid与epoch切换事件，禁止只排normal path |

TA m=7 时刻为83.75 ns，85 ns为其下一拍反馈可见点。不要把表中的8次比较缩成一次M8平均，也不要把提交提前到本次比较输入端。acquire-open、AZ写入完成等内部截止时刻若早于下个公开事件，也必须加入同一事件表。

每个 event transaction 的顺序：先用上一区间实际生效的反馈把相关行为态解析推进到当前物理时刻；按原pipeline把本tick已到期的反馈挂入可见快照；读取本时刻比较输入并产生输出与pending更新；提交本模块状态，新增反馈的到期时间是本次decision+1.25 ns；安排下一到期事件。本时刻刚产生的pending不能加入本次比较输入。同拍控制必须保留旧图的优先级，特别是 reset/epoch、CNV、coarse latch、pending反馈及新prepare。不能靠 Simulink 块默认排序猜测，也不能用新全局Unit Delay把所有路径多延一拍。

调用旧step时必须区分其 `y` 与 `xnext`：只从旧state计算一次，再明确提交。旧scheduler的一tick脉冲不能持续保持到下个稀疏事件；事件bus携带类型掩码，在每次事务开始清零pulse字段，再只置本次事件，phase等电平另存。

## 4. 现有源码的复用边界

| 现有源码（相对工程根） | 可复用内容 | 新图处理 |
|---|---|---|
| `current/matlab/sar20_scheduler_step.m` | CNV计数、reset/epoch、bank/sample_id、phase/事件优先级 | 作为事件真值与对照；不要直接留下原周期wrapper。先比较新表与原160tick/slot产生的事件序列 |
| `current/matlab/sar20_paper_timing_profile.m`、保存的`SAR20_P.timing` | 时间表与整数时间量子 | 读取保存值，生成事件日历；保留假设标签 |
| `current/matlab/sar20_sar1_step.m`、`build_sar20_vendor_stage1.m` | coarse/fine trial、D1原码、invalid/late；现有vendor-derived图的原生比较/D1寄存路径 | 仅在CNV、coarse/fine及所需提交事件执行；保留原生Relational Operator与D1 UnitDelay语义；`sar20_vendor_stage1_out_sfun`只做字段Selector，不是另一套SAR算法 |
| `current/model/cicc/matlab/sar20_sar2_step.m` | D2的12次neutral-to-bipolar和8次tracking状态机 | 保留64态语义，事件调用与下一拍反馈分离，不重写成一次理想量化 |
| `current/matlab/sar20_committed_signs.m` | 12位提交前缀与至多7个tracking符号 | 在commit时调用，原函数明确tracking count夹到7 |
| `current/matlab/sar20_make_slice_plan.m`、`sar20_az_calendar.m` | sample_id键控的slice/AZ/polarity/pair安排 | 在样本/相位事件调用，沿用保存plan/seed |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_unary_group_dem_map.m`、`pool_tail_dither_value.m` | group DEM与tail dither键控关系 | 保留明确ID/epoch/slice/seed；不因少调用wrapper改变随机次数 |
| `current/matlab/sar20_lvds_tx_step.m`、`sar20_lvds_rx_step.m` | record cache、32bit帧、N−2、reset/EN/invalid和tag逻辑 | pin模式保留原函数；帧模式复用其字段/状态规则，局部pack/decode函数不能假称已经独立导出 |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_decode_specs.m`、`pool_decode_config.m` | Frame/Math/History/Output/Commit原生块层次 | 原生子系统由frame-complete或reset触发；State UnitDelay继承其事务速率；保留fresh/invalid/reset优先级 |
| `current/model/product/matlab/product_fixed_reconstruct.m`、`sar20_product_fpga_step.m` | Q20、54位界、SINC2、pair/filter、fresh去重 | 作为数值对照；解码输入仅接收到的RAW与nominal参数，不接模拟truth/actual C |

新行为核必须在各次比较之间保留所选择的settling、有限增益、AZ、reference、noise及失配等行为态；具体覆盖由新模型另行列明。这里不沿用旧BE状态ABI，也不承诺新行为模拟与1540节点模型的每个raw bit相同。相同RAW的数字解码和相同事件的反馈语义则必须一致。

## 5. 默认帧级LVDS，pin级专项调试

帧格式严格为 `word = D1*2^21 + D2*2^9 + DT*2 + valid`，宽度11/12/8/1。sample_id/epoch/bank/polarity/pair_id等按旧接收器公开计数规则生成；它们不全在32bit线上，不能偷偷把内部模拟tag当线内字段。

默认帧模式维护原四深度record cache、commit_time与setup截止，CNV快照target为当前CNV−2（含32位计数回绕）。raw latch是提交事件；恰好截止时刻记录与CNV快照的优先级沿旧TX ingest-before-snapshot语义。当前记录不得穿越N−2 FIFO直接交给解码器。

- 每slot在CNV快照一次、在原+138 ns final-fall/frame-close时刻提交接收frame与decode事件。
- 正常关闭、missing/invalid、test word、EN中途变化、reset/resync/epoch必须有显式事件与结果；不能把“没有数据”静默改成valid。
- RX原32次capture的最后一位在+136 ns，ready在+138 ns关闭时生成。原数字层在下一owner命中才可见的部分仍排到相应owner边沿（例如从138 ns ceil到138.75 ns），不因采用frame模式提前消费。这个接收→解码可见时刻须用旧短记录确认，不能凭草案固定。
- frame模式不声明DCO边沿、preamble、差分错误、毛刺或setup/hold/CDC通过；这些只在pin debug检查。

pin debug只为选定少数sample_id启用，使用原TX/RX pin步函数及可见pin日志；先按全部真实clock/data/reset/EN边沿生成事件，必要的250 ps网格只局限这一分支。它不让模拟行为核、SAR与decoder在每个pin空转tick执行。frame与pin需要对同一组已提交RAW比较字段、N−2/tag、close_time、valid与解码输出；不能以帧模式取代pin专项证据。

## 6. 事件量估计及最小日志

一个slot的核心日历包含5次fine prepare+5次decide、12次D2 prepare+12次decide、8次TA compare，以及必要的+1.25 ns反馈提交；许多commit与下一prepare/compare重合。仅这些主事件、CNV、12.5/31.25/43.75/73.75/75/85/86.25/90 ns边界合并后约48个唯一时刻。再加入acquire-open、AZ完成、deadline、帧关闭及decode可见点，预算约50–65个唯一事件时刻/slot；准确数量由保存配置生成表并计数。

因此N8约700–910个主要event timestamps（14slot），N256约13100–17030个（262slot），另加有限初始化/复位；这不是函数调用次数，单时刻可能调用多个子系统。原轴分别有11801/210201个250 ps时刻，owner2361/42041行；这些比值只是调度数量比较，不能宣称等倍加速。pin模式每slot约数十到百级边沿，仅局部执行TX/RX。

默认只存：每sample的aperture/ID/epoch/slice、每判决的事件种类/位序/decision/invalid/late、每tracking提交的7符号前缀、raw latch、frame snapshot/complete与最终8/256码。关键模拟节点仅在上述事件或选定sample上记录。禁止默认54/59路dense To Workspace、四份256态逐tick、1368源mask或5181态全流；诊断全态是明确选中的短专项。

## 7. 首个实际8码验收与计时

先交付独立新模型，不覆盖current。保存同一输入幅度/频率/phase/offset、master/DEM/dither/noise seed、M8、first_id=4、N8、14slot及真实负时间priming，默认frame LVDS。八码必须由新行为核逐次比较产生，不能重放旧code/comparator数据充当实际仿真。

验收分开：

1. **事件语义**：对旧scheduler生成的14slot事件表比较CNV/aperture、ID/epoch、fine/D2prepare与decision、12D2/8TA/7feedback、+1.25ns可见性、RAW和reset顺序。每个sample无漏判/重复/越ID提交。
2. **数字传输/解码**：把本次真实RAW同时送frame通路与既有数字参考；相同RAW的32bit word、N−2/tag/valid、SINC2、Q20/code20及pair/filter结果逐bit相同。再对少数样本做pin专项对照。旧物理模型八码作为跨模型差异记录，不预设逐bit等价。
3. **数值真实性**：记录本轮实际事件数、每sample的关键模拟节点和比较轨迹，确保反馈确实影响下一次比较；noise仅按规定物理事件更新，RNG不随无关日志/重启观察器变化。
4. **速度**：同一唯一MATLAB、同一优先级/硬件条件，profiler关闭，标准仿真模式；先记录一次cold apply/build，再warm运行一次实际N8。首轮建议交互目标为warm `sim()`≤5s、run入口到8码及最小日志完成≤15s；这是待实测验收目标，不是当前结果或保证。若未达标，报告实测及调用/事件计数，不立即退回MEX或大矩阵微优化。

分别计时并报告：`build/update diagram`、`sim()`、`extract+gate+最小存盘`、总入口墙钟；sim计时含引擎运行/事件子系统/最小观察开销，排除建图编译和后处理。保存native MATLAB版本、model/source/config hash、优先级、实际start/stop、code8、event counts和日志未压缩字节。只做这一条实际8码主作业，完成后再决定N256；不并发启动长辅助验证或另一MATLAB。
