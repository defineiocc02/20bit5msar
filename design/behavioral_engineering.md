> 历史设计草案：2026-10-27已建立并实际运行新的行为模型。当前接口和验证范围以根目录README、current/src及CHECKPOINT为准；本文包含未实施设想，不作为当前集成/运行证明。

# SAR20 行为级工程最小入口方案

日期：2026-10-26。状态：设计草案，未构建、未编译、未运行新模型。本次只新增本文档；不修改 current、不操作 Windows。目标是便于改参数、看波形、定位行为错误的 Simulink 工程。原高精度 MNA 模型、历史 raw/as-run 与其验收结论封存为参考，不作为新模型运行前置条件。

## 1. 用户操作与唯一主图

保留项目根目录唯一公开 MATLAB 入口 `SAR20.m`，唯一活动主图建议为 `model/SAR20_Behavioral.slx`，内部模型名不同于入口函数名，避免名称解析冲突。所有构建函数均为内部函数，不提供平行用户入口。不另建 ideal/nonideal/debug 三套主图：同一图通过参数运行不同配置。原 current/PoolCt 不加入新工程 path，也不作为复制重建的底座。

```matlab
SAR20                    % 打开主图；不隐式更改配置
SAR20('apply')           % 读取 JSON，重新派生参数，写 Model Workspace，保存
SAR20('check')           % update/compile，检查连接和配置；不仿真
SAR20('run')             % 用已应用配置真实运行，记录原码与身份
```

初次缺少主图时由 apply 调用内部 builder 创建；主图已存在时正常改参数，不重建整个图。结构变化（例如端口数）由同一 apply 的显式结构版本迁移处理；不能因 record_length、seed 或 NI 开关变化要求解锁 source revision。apply 连续执行、N8→N256→N8、NI开关往返必须正常；没有硬编码模型或源码 SHA 白名单。

run发现JSON与已应用配置不同，明确提示先apply；不要静默修改后开始长仿真。允许MATLAB调试器直接停进组件函数；GUI Run使用已保存的Model Workspace配置，并在图上说明其不自动读JSON。若直接编辑GUI模型，保存后允许运行，并记录新的模型SHA；源码变化也只记录，不因版本变化拒跑。所有动作保留用户未保存修改保护及运行中模型保护，不清会话、不关闭其他模型。

## 2. 单一参数与seed来源

`config/parameters.json`是用户配置；一个纯函数 `src/sar20_config.m`负责默认值、单位、范围和派生。它每次从JSON及显式seed重新生成完整配置，不从旧p_f0/p_source反推本轮参数。派生结果以一个结构 `SAR20_P`保存到主图Model Workspace；run再保存实际resolved配置。必要的块参数可以引用它的字段，不维持31个互相绑定的影子变量。

建议最小配置分组：

- timing：采样率、行为主tick、tracking_count；采样/比较/更新事件的时间关系由此派生。
- capture：record_length、warmup_records；调试默认N8，明确请求后才跑长记录。
- stimulus：DC或正弦、幅度/频率/offset/phase；不因FFT自动偷偷调频。
- device：CDAC实际/标称权重、RA增益/带宽/非线性、比较器等明确行为参数。
- nonideal：sample_kTC_enabled、temperature_K、CMP noise/offset、mismatch、jitter、settling等分别控制；未实现项报错，不能接受后静默忽略。
- seeds：master_seed与明确的芯片失配、采样噪声、比较器、jitter、DEM/dither子流seed。不同源不用共同全局rng推进。
- debug：选定sample_id、日志级别（normal/trace）；日志级别不改变信号通路或随机数调用。
- calibration：先保留off；需要实现时只接公共原码/ID/epoch和明确外部参考，禁止读取模拟真值。

seed只在配置/模型初始化时确定；Outputs与多次求值不能抽新随机数，Update或明确事件只提交一次。关闭某项NI不改变其他项的流；sample_kTC关闭保持temperature_K=298.15，表示无该项注入，不用T=0代替。器件失配由独立chip seed生成，record_length变化只延伸同一ID日历，不重新抽芯片。配置原件与resolved配置分开保存，保留默认值来源，无隐藏恢复工厂。

## 3. 主图结构与行为抽象

主图建议按信号链展开：Stimulus/Driver → Sample/CDAC1 → SAR1 → RA/AZ → SAR2/Tracking → RawRecord → DigitalReconstruct → LVDS/Host。Scheduler/Reset在上方，日志在下方。每个子系统边界用具名bus或字段表表达控制、sample_id/epoch、原码与valid；不把1540节点/5178字状态向量公开成跨模块接口。

MathWorks SAR例程可保留的内容是采样保持、比较器、试探寄存器、DAC反馈、时钟/触发和可视化的闭环结构。在目标已授权MATLAB中定位实际库块并读取mask/端口；不要把原厂8/10位普通SAR整块宣称为两级20位架构。现有 `build_sar20_vendor_stage1.m` 的源码明确保留native Sample and Hold/Relational Operator、替换SA-register/DAC路径，可作为结构参考；不复用其历史profileEvidenceJson/SHA/绝对scratch路径前置流程。

SIMSAR在现有文档中只有论文方法/结构参考与许可边界（docs/SPEC.md第7节）；本轮未发现可直接复用的已授权SIMSAR源。可采用模块化误差注入与闭环行为建模思路，自行实现所需组件，不能把未取得的库列为必需运行依赖。

模拟行为使用电荷守恒/位权求和、采样保持、有限增益及一阶settling、明确噪声与饱和等可解释公式。RA/CT需要保留跨事件记忆与反馈因果，不能简单把每拍输出强制设成理想目标；每个模型写清状态、更新事件、适用范围。行为时间步只需解析该层级的决策/建立事件，不继承62.5ps BE子步和MNA残差预算。精细晶体管/PEX/物理电荷研究另属验证，不进入日常参数迭代的必经路径。

数字域保留12次D2、M8的8比较/7实际更新、公共原码帧、ID/epoch、dither加回和已定义的数字滤波/定点饱和语义；M1作为同图显式配置。复用前逐项核对旧函数的符号、位权和同沿优先级，不以旧归档结果替代新图验证。

## 4. 当前代码的复用边界

| 现有组件 | 新工程处理 |
|---|---|
| SAR20.m根目录定位、stopped/Dirty保护、作用域path恢复、run目录与可见错误 | 保留模式，删除release/contract/MIGRATION闭环前置；只加载src与需要的SATK工具 |
| `current/matlab/build_sar20_model.m`、vendor baseline/stage1/paper_chain | 借用图形层级、SATK add/configure/connect用法；旧复制模型、硬编码profile/hash/绝对路径和自动smoke行为不原样调用 |
| `current/matlab/sar20_sfun.m` 或 `current/model/cicc/matlab/sar20_cached_sfun.m` | 选择一个wrapper模式；保留Outputs预测/Update提交及每实例状态。先用易调试MATLAB行为函数，不叠加两个wrapper、不引入MEX |
| scheduler、sar1/sar2、driver/frontend、DAC、RA/AZ的 *_step | 从最直接版本选取公式/顺序，移入单一src并去重；原MATLAB组件不因存在而自动视为适配新接口 |
| `sar20_counter_word/normal/dither_value/make_slice_plan` | 可复用显式seed/ID算法，选择单一实现；检查rng无副作用与任意短/长记录前缀一致 |
| `runtime_work/native_decode_r1/decode_*_specs.m`、`pool_decode_specs.m`中的Math/Frame/History/Output | 可保留原生块的公开原码解码结构与定点公式。builder只负责建图，允许compile后检查；移除MNA/历史reference支路绑定 |
| LVDS tx/rx与product host的step函数 | 在需要保留完整产品链时复用；公开原码/ID→整字→RX连接清楚，不让物理真值进入解码器 |
| `current/design/ports.json` | 作为旧接口证据；整理新图真正用到的bus字段，不能继续把历史numeric DWork宽度当全工程不可变约束 |
| `dependencies/toolkit`中的model_edit/read/check及所需common | 继续作为建图工具依赖；不扩展为仿真数值核，目标主机安装/路径正确即可 |

不预先复制整个270文件树。实现时从选定组件递归列出实际调用集，再用path解析与一次cold compile检查缺依赖；去掉同名helper的多目录版本。必要最小新增代码约为：入口、config派生、内部builder、一个wrapper和各行为step、日志/receipt写出。其余按真实调用决定，不先建通用框架。

## 5. 从新活动路径删除的旧依赖

以下仅指新工程不再依赖；本设计不授权现在删除任何历史资料：

- pool_cached_predict/matrix/latch/sfun的MNA路径、pool_mex_be/matrix、pool_sparse/state MEX及其C/XML/buildlog。
- ct_network/forced/native/coarse_joint等只为旧连续物理网络服务的分支，以及runtime_work多轮候选与fallback解析。
- F2 workspace entry、prepare_f2_*、configure_pool_ct与capture profile中为v3/v4及5181布局服务的事务链。
- release.json/WORKSPACE_CONTRACT/source_file_pins/candidate_overrides/MIGRATION/template binding的运行门禁；旧文件封存后无需每次改源码rebase。
- 数值Dot2/KCL/BE误差预算、全节点ledger与逐位MNA等价门，不作为新行为模型验收项目。
- 旧硬编码snapshot绝对路径、旧raw与as_run读取，均不在新入口正常执行路径中。

历史文档需保留其原始事实和SHA；新工程记录明确model_kind=behavioral，不继承历史MNA性能或宣称数值等价。新旧唯一活动入口切换前先封存旧SLX/source/config/binding及原始数据位置；不恢复旧活动树。

## 6. apply与run最小记录

apply：解析并校验JSON → 确定性派生配置/chip/日历 → 给唯一主图写Model Workspace → 更新必要mask与sample time → 保存 → 写state/applied_config.json。读取旧SLX只为保护GUI修改和保留结构，不作为本轮参数的真值来源。参数apply必须可重复；失败保留错误与未成功状态，不写成功receipt。

run：检查已应用配置 → 初始化本轮组件状态与独立RNG → sim → 保存原始输出/原码 → 写运行回执。回执至少有run_id、UTC、MATLAB版本、status（started/running/complete/failed）、elapsed、simulation_completed、实际模型路径/SHA、实际resolved配置/SHA、参与执行源码路径/SHA、seed、sample IDs/epoch、raw_D1/raw_D2/raw_DT/valid及结果文件路径。SHA是运行时身份记录，不是允许执行的常量列表。若中途失败保留partial并标failed，不能从apply的not_run状态推断本次run没执行。

normal日志保存原码、最终码、ID/epoch和必要RA/held/决策结果；trace只加选定sample_id的试探量、比较值、状态提交与NI注入量。不默认保存大规模隐藏全态，不因日志等级重复推进RNG。结果使用MAT加小JSON，避免每次复制整个工程或运行树。

## 7. 下一构建里程碑的验收

先在不连接旧MNA的同一个主图做N8短run：理想DC/正负小幅、reset、一次完整12D2/8比较7更新、原码→数字重构的基本闭环；事件/符号错误先定位。随后同一JSON做apply两次、N8→N256→N8和seed/NI开关往返，确认无旧snapshot身份锁死。

kTC等NI分别检查开关真实起效、温度/单位/注入时刻正确以及关闭后其他流不变；组件公式检查与整图连线检查分开报告。不为了证明开关而先建立整个高精度电荷门框架。必要的一次接口/复位和参数重入回归即可，不复刻270文件closure体系。

完成cold compile和真实短run后再请求长动态谱/静态扫描。运行速度与指标均来自新行为模型真实run；长记录、校准训练与holdout仍各自验收。本草案不承诺任何ENOB/SNDR、硅级电路精度或与旧MNA逐位相同。
