> 历史设计草案：2026-10-27已建立并实际运行新的行为模型。当前接口和验证范围以根目录README、current/src及CHECKPOINT为准；本文包含未实施设想，不作为当前集成/运行证明。

# 18/8/8/2电容池前端：事件驱动行为接口

本文是当前SAR20-5主图的前端替换设计草案，未实现、未仿真。交付目标是清晰、可逐事件调试的系统行为模型：保留18个物理slice的采样与预充电记忆、实际支路权重误差、公开pool/DEM/dither映射；停止为此前端在每250 ps求解1540个节点。当前`current/`、Windows模型和N256运行不因本文改变。RA、SAR2/TA及LVDS仍是现有主图的独立责任，不另造一个ADC工程。

## 1. 最小模块与边界

一个`PoolFrontendBehavior`负责模拟域采样、电容权重和一级DAC电荷；沿用现有SAR1控制/比较决定流程，不用Python或理想量化器替换真实D1/D2/DT。

| 输入 | 内容和单位 | 使用边界 |
|---|---|---|
| `Event` | `kind,time_s,sample_id,epoch`，及该事件的reset/phase/active资格 | 由现有调度和寄存器边界产生；同一事件只能提交一次 |
| `AnalogInput` | 模拟输入函数或其声明的分段/正弦参数，V | 仅模拟采样模块读取；不连数字重构/校准 |
| `DacCommand` | 已寄存的`coarse=0..63,fine=0..31,valid` | 保持当前prepare/decide/寄存器时序，不能从trial预测已提交决定 |
| `PublicCfg` | 公开plan、pool/DEM seed、dither seed及输入等效幅度、Vref标称、采样时序 | 不含actual C、held、内部残差或训练答案 |
| `AnalogCfg` | 每slice实际38支路F、Cp、采样建立参数、噪声开关及显式模拟seed | 仅模拟模块读取；来自同一冻结芯片，不重新抽失配 |

| 输出 | 消费者 | 约束 |
|---|---|---|
| `FrontAnalog` | CMP1/残差移交接口 | `q_residual_c,Csample_total_f,Ctop_total_f,valid,id,epoch`；模拟信号，不向数字校准开放 |
| `CoarseAnalog` | 既有Coarse6b路径 | 采用该路径现有模拟采样坐标；本文不以池加权结果擅自更换coarse输入定义 |
| `PublicContext` | 记录/数字算法 | `id,epoch,valid,conv_ids,acq_ids,DEM版本/seed,dither输入等效值`；均能从公开配置与标签重建 |
| `AnalogTrace` | 只读调试记录 | 每slice相位、aperture、保留电压/电荷、各电荷分项；禁止回接数字算法 |

`ExternalXref={valid,id,epoch,value_v}`直接进入数字校准模块；不作为前端模拟模块返回的“参考输入”。前端不提供任何ground-truth校准目标。

## 2. 公开18/8/8/2所有权

对当前转换ID `n`：

- `conv_ids = plan(n+1,:)`，8个正在转换的物理片。
- `acq_ids = plan(n+2,:)`，8个为下一ID采样的片；有效pool工作时二者不相交。
- 其余2个片为parked，保留上次模拟记忆，不因未选中而清零。
- ID0的预采样采用`plan(1,:)`；下一采样组在ID n的CNV开窗时标记目标ID n+1。
- plan从同一公开seed延长并保留完整旧前缀，不能按VALID数量压缩或遇漏帧推进错误日历。

每片相位至少为`PARKED/ACQUIRE/HELD_CONVERT`。phase与capture标签分开：仅相位正确且capture标签等于本次`(id,epoch)`的8片可以参与转换。epoch进入DEM相位及记录配对，不选择另一行plan。

`sample_id=0`合法；负ID仅能作为无效启动占位。reset取消数字事务/capture有效性，不隐式擦除全部模拟电压。只有明确的power-on或物理reset事件才能按声明的初值/复位响应改变模拟记忆。

## 3. 最小模拟状态

每个slice保存以下独立状态，18片共约几十个浮点值，不保存1540节点或每支路连续未知量。

| 状态 | 作用 |
|---|---|
| `v_sample_j` | ACQUIRE时为采样节点等效电压；CAPTURE后保持冻结 |
| `v_tail_pre_j` | tail15的实际等效预充电压，目标是物理`−Vd` |
| `v_bias_pre_j` | bias17的等效预充电压，目标是`+Vref` |
| `last_analog_update_s` | 解析更新的起点；停放期间状态保留 |
| `phase,target_id,target_epoch,capture_valid,capture_id,capture_epoch,aperture_s` | 下一采样目标、所有权及一次采样的资格 |

owner另保存`last_event_key`及当前转换标签/已寄存`coarse,fine`，用于事件去重和两事件之间输出；这些小状态不按每个tick复制训练矩阵。

实际`C_j[38]`是冻结参数，不是状态。`Qin/Qbias/Qdither`由上述状态与C派生，无须再复制一套可独立漂移的电荷缓存。可以缓存输出加速，但缓存不是第二个权威状态。

默认DAC转换采用事件时刻理想建立的电荷守恒，不保存38个bottom节点。需要研究DAC建立时再启用第7节的单极点电荷误差状态，并明确其额外假设。

## 4. 采样与预充：只在事件更新

采样支路权重和电荷：

```text
Csample_j = sum(C_j[1:33])
Ctail_j   = sum(C_j[34:37])
Coffset_j = C_j[38]
Ctop_j    = sum(C_j[1:38]) + Cp_j
```

对有限采样建立，使用一阶输入跟踪的解析状态转移：

```text
v(t1) = exp(−Δt/τ)*v(t0)
      + (1/τ) * integral[t0,t1]{exp(−(t1−u)/τ)*vin(u) du}
```

对声明的正弦输入可用精确正弦特解与齐次衰减计算；对常值段用`v_target+(v_old−v_target)*exp(−Δt/τ)`。不能把整段正弦的末点值当作整段常值并称为精确建立。任意未支持输入必须显式报错或提供分段积分规则，不能静默换成理想采样。

同理解析更新tail/bias预充至各自目标。最小首版可显式令其理想建立；这属于模型开关，不证明实际RC已建立。PARKED不跟踪输入；ACQUIRE从上次保留状态起步。

在CAPTURE/aperture事件，先推进到实际aperture，再冻结：

```text
Qin_j     = Csample_j * v_sample_j
Qbias_j   = −Coffset_j * v_bias_pre_j
Qdither_j = −Ctail_j   * v_tail_pre_j
```

因此充分建立时`Qbias_j=−Vref*Coffset_j`、`Qdither_j=+Vd*Ctail_j`。kTC若开启，只在一次真实CAPTURE给该片采样状态加入一次噪声，方差采用声明的采样电容口径；重复读取/重新求输出不能再抽噪声。模拟seed/lane必须显式稳定，不能使用校准答案或每250ps推进随机流。

## 5. SAR1、DEM与实际权重

支路顺序沿用现有38列：

```text
[MSB16, group32_01:31, fine16, fine8, fine4, fine2, fine1, bias17]
名义Cu = [16, 31×32, 16,8,4,2,1,17]
```

已寄存命令`c,f`的逻辑开关电平：

```text
b=floor(c/32); k=mod(c,32)
m=2*b−1
b=0: groups(1:31−k)=−1，其余0
b=1: groups(1:k)=+1，其余0
fine=2*bitget(f,5:-1:1)−1
levels=[m,groups,fine,0]
```

DEM开启时仅置换31个32Cu组：

```text
shift=mod(17*id+7*epoch+11*(slice−1)+dem_seed,31)
map=mod((0:30)+shift,31)+1
physicalGroups(map)=logicalGroups
```

同一样本的trial不能改变map；不能按actual C挑选组。MSB16、fine5支路、bias不参加该组DEM。DEM关闭时保留原逻辑组顺序，actual权重误差仍存在。

每个slice按实际权重求电荷：

```text
Qcode_j = Vref * dot(C_j[1:37], physical_levels_j[1:37])
Qres_j  = Qin_j − Qcode_j − Qbias_j − Qdither_j
```

8片按当前capture资格求和：

```text
Qres = sum(Qres_j)
Vtop_equiv = −Qres / sum(Ctop_j)
Vin_res_equiv = Qres / sum(Csample_j)
```

`Qres`及电容标量交给现有RA域行为模块。若由RA模块使用固定Cf，则理想电荷放大入口为`Qres/Cf`；不在前端再乘一次RA gain。CMP1当前到底消费Vtop还是输入等效残差，接图时沿用既有端口的定义与极性，不互换单位。

上述是差分等效行为模型。当前P/N复制同C的假设可以映射到此接口；独立P/N失配、共模余量、非线性开关效应若未增加对应参数和状态，不能宣称已经覆盖。

## 6. dither物理源和数字抵消

现有公开计数器定义：

```text
d_n = sar20_dither_value(id, dither_seed, input_amplitude_v)
Vd  = d_n * 1024/15
```

前端ACQUIRE tail目标为`−Vd`，使用下一采样目标ID，不取当前正在转换的ID。数字RX nominal路径按收到的ID直接补偿输入等效`+d_n`，不补偿`Vd`，也不除RA gain。

实际电容与未充分预充导致的物理项是`sum(Qdither_j)/sum(Csample_j)`；它一般不严格等于d_n，不能用数字回写把差异强制抹平。

未来若684有效比值重构已将tail预充项包含在B中，则该路径不能再叠加nominal的`+d_n`。两种数学路径必须有清楚的mode选择与版本记录。

## 7. 可选DAC建立近似及不覆盖事项

首版默认理想电荷切换，先验证所有权、实际权重、DEM和dither符号。需要建立预算时，可增加每slice一个电荷误差状态`e_dac_j`和`last_dac_update_s`：

```text
在下一事件前：e_new = e_old * exp(−Δt/τdac_j)
命令目标电荷从Qold变Qnew：e_after = e_before + Qold−Qnew
有效Qcode = Qnew + e_dac_j
```

它假设同片各支路共享单一建立极点，只用于估计建立误差的设计敏感性。DAC_INIT的初始Qold/e必须由显式预充/拓扑事件给出；不能在每个新ID把误差随意清零。该初始化合同未闭合前，不启用此近似并声称保留了全部RC记忆。

该模型不自动覆盖支路间不同时间常数、多极点/参考恢复、glitch能量、1540节点耦合或RA内部动态。需要哪一种设计问题，就显式增加对应少量状态和观测，而不是恢复整套连续节点求解。

## 8. 事件次序与一次提交

1. `ACQUIRE_OPEN`：核对公开下一采样组/目标ID，解析推进旧相位，再切入ACQUIRE并设置输入/tail/bias目标。
2. `CAPTURE`：推进至aperture，一次性采样噪声和冻结，写入capture标签；同标签重复事件不重复采样。
3. `CONVERT_JOIN`：要求8片全部同ID/epoch且已capture，形成模拟输出；不以held.valid单一标志补造缺失片资格。
4. `DAC_COMMAND_COMMIT`：仅消费已寄存coarse/fine，按同ID的DEM图更新目标电荷；prepare与decision的同沿优先级由既有控制保证。
5. `CMP_EVALUATE`：推进可选建立状态后提供一次稳定单位/极性接口；不提前写SAR决定。
6. `RESIDUE_HANDOFF`：将同ID/epoch的Qres及所需标量交给RA/SAR2；只读调试记录另走支路。
7. `RELEASE/PARK`：释放转换所有权，保留模拟状态；以后ACQUIRE从该状态恢复。

每个事件带单调`event_ordinal`或现有等价提交键。相同time可以有多个不同事件，不能只靠time去重；重复调用同事件输出不得再推进状态/抽噪声。仅当控制门和标签一致时提交。事件内先推进旧状态，再读输出/切拓扑，最后提交新状态。

## 9. 数字校准逐项接入且可观察

数字入口只接公开RX的D1/D2/DT、ID/epoch、公开plan/DEM/dither和外部xref。模拟trace只读，不提供actual C、held、内部Vin、Qres或内部误差给算法。

| 模式/阶段 | 主输出和状态行为 | 必须观察 |
|---|---|---|
| `caloff` | 原nominal数字算法；前端实际权重仍生效 | raw码、d_n、最终码、标签、mode |
| `train` | 生产使用当前active系数或明确nominal；只对新鲜合法且xref匹配帧更新shadow | 接受/拒绝理由、窗口ID、训练计数 |
| `fit/freeze_candidate` | 恰好训练结束才求解并冻结候选；欠秩/病态拒绝，不以nominal填补 | rank、条件数、候选版本和冻结时间 |
| `holdout` | 候选只读，独立未参与拟合的xref仅用于验收；不根据答案重调系数 | 固定候选版本、误差预算/结果、行数 |
| `activate` | 合格后按未来公开ID/epoch启用新版本 | activation标签、生产版本、Code版本 |

生产CalOwner不得读取验证Reference路径的watermark/退休确认。activation guard和旧bank复用只依据公开Core RX标签及已证明的协议/生产消费者时序上界；验证需要的旧版放在测试台只读档案。上界未闭合时，换bank仍是未完成事项。每个样本在处理起点锁定系数版本；跨版本pair/FIR必须flush或显式版本匹配。

公共标签Assertion在dither on/off都存在，但不能代替训练写使能；训练写使能另要求`reset_n && fresh && valid && PublicContextLegal && xref_join_ok`。本文不以旧28theta/F0路径冒充684校准，也不要求此轮先实现大矩阵；先让事件、公开数据和模式状态可逐项观察。

## 10. 复用源码与最小接图范围

以下路径相对工程根目录，均为现有源码：

| 源码 | 复用内容 | 处理方式 |
|---|---|---|
| `current/matlab/sar20_make_slice_plan.m` | 同seed公开18/8/8/2日历 | 原函数复用；必要延长须保持旧完整前缀 |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_unary_group_dem_map.m` | 31组映射及方向 | 原函数复用 |
| `current/matlab/sar20_dither_value.m` | sample ID/seed计数器 | 原函数复用；区分输入等效幅度与尾源幅度 |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_tail_dither_value.m` | d_n与1024/15比例的现有合同 | 提取/复用公式；不把5181态cfg整包传给新数字模块 |
| `current/runtime_work/pool_group_product_r1/pool_group_from_product.m` | 1039cell聚合到38支路及采样1024/tail15划分 | 只在模拟配置构建时用；实际参数不外传数字侧 |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_cached_latch.m` | 当前plan选行、capture/寄存命令事件、command_levels | 作为事件/开关语义依据，不复制1540状态 |
| `current/matlab/sar20_sar1_step.m` | SAR1 prepare/decide与D1寄存 | 保持控制/原始码流程，核对实际主图native对应块 |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_decode_specs.m` | RX Frame/History/Output/nominal定点重构 | caloff复用，之后增明确校准路径 |
| `current/runtime_work/pool_pole_precision_trial_r1/pool_decode_config.m` | 数字公开配置与原格式合同 | 避免把模拟配置整包转入算法 |
| `current/runtime_work/pool_pole_precision_trial_r1/build_pool_ct.m` | 现有主图端口和连接边 | 将新前端接到同一主图的模拟接口，不另建ADC顶层 |

后续实现的最小落点是一个前端事件执行核/状态定义、对应主图连接及只读事件trace；不在此次设计阶段编写它们。现有1540节点owner只能在明确替换的模拟支路停用，不能和行为前端同时驱动同一个残差端口。

## 11. 首轮行为验收

- 手工可读的少量ID：8转换/8采样/2停放、相邻组互斥、标签完整，包含ID0、漏帧、reset/epoch和同time多事件。
- 静态标称电荷：38支路表逐项求和，与同式独立算术检查一致；actual失配不能被数字补偿路径偷偷消除。
- DEM：固定ID/epoch跨trial图不变，开/关可切换并有明确观察值。
- dither：下一采样ID预充、物理−Vd、残差扣除及nominal数字+d_n四处符号/尺度闭合。
- 同一事件重入：状态、RNG调用次数、Qres、raw码不变化；PARKED保留记忆。
- `caloff/train/freeze/holdout`按阶段独立接入和拒绝测试，不把前端单元检查当整图动态指标。

目前只有上述接口/模型取舍已定义；尚无行为前端实现、真实主图运行、速度或SNDR结论。1540节点现有运行证据属于原物理模型，不自动转移为新行为模型的验证。
