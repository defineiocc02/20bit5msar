# RX 校准 / BankOwner v3 接图红线

历史 2048 条训练和 1024 条独立 holdout 是行为仿真证据，缓存仍 `NOT_ACCEPTED`、未激活。v3 是未绑定实际 P 的隔离诊断核，`code_valid` 恒 false；fixture 和散列均不能直接授权生产切换。

## 信息边界

- **训练**只收真实 RX `record_ready` 的公开 `[D1,D2,DT,id,epoch,valid]`、逐 ID/epoch 配对的独立声明训练 Ref、cfg17、公开 plan/DEM/dither 规则和预定阈值。历史训练为 2048 条、ID 4–2051、epoch 1、serial RX N−2；Ref 为声明的理想外部参考。
- **资格评价**在协议与候选冻结后，可独立读取新登记 holdout 的公开 RX RAW/Ref、ready 时间、ID/epoch/valid 和冻结数字输出，产出聚合判定；评价与在线 BANK 隔离。102427 的旧 holdout 已消费，其逐点 RAW/Ref/误差/码/答案不得用于新训练、参数选择、新 holdout 或 BANK；只引用旧协议、状态、汇总和证据哈希，不能冒充新图的新资格。
- **同图 BANK**只收 `hit,raw_ready,raw6,nominal_code,rx_fault,command` 和已认证的公开 cfg17、plan、h、profile、证书、版本/边界；nominal_code 来自公开 RAW 的名义解码。绝不读取 actual C（如 `P.front.C_f`/`Cp_f`）、held、Qres、VX/VY、内部模拟残差、模拟初态、理想输入/最终码或旧 holdout 逐点答案，也不可通过监视器间接使用。不要把完整 P 或其运行时散列交给 BANK；只提取明示的公共字段。冻结 `C` 是公开数字缓存，不能与实际电容混同。

## 资格与实际绑定

- **秩不足拒绝**：n<684 不生成 h；rank<684、condition>1e8、RMS>7.8125 µV、无效/非连续标签、非正或非有限 h/分母、DEM 覆盖不足均拒绝。固定 SVD 相对阈值 1e−10 及数值下限，不删行、不调门、不用 ridge/pinv/名义补缺。原回执报告 rank=684、condition≈2242.64、fit_calls=1；本次未重新拟合。
- **可信适配器是必需项**：v3 `check_certificate` 只核字段、绑定和外部 allowlist，**不会核 rank/condition、独立性或证据真实性**。训练/冻结/新登记/评价回执须先经独立可信适配器核实，再分别授权 training/qualification 摘要；不能由候选自签发、将 fixture 改标 registered 或把哈希当认证。通过资格仍不等于 `NOT_ACCEPTED` 已转为生产接受。
- **实际 P 投影绑定**：apply、compile、enable 均核真实 ModelWorkspace 的 cfg17/plan/profile、模式和 `P.front.tau_dac_s`（double[18×1] 全 0），并核 backend 派生 DAC τ/开关与图一致；非零、Inf、NaN、错形状、配置漂移一律禁止 enable。绑定 DEM/dither/seed、采样/复位/RA、参考、模型/源码及 RX 时序。v3 helper 只检查少数旗标和 τ，尚未接线，不能代替完整门。
- **身份**：历史 h SHA `a634c9a0c63c636a4c8966bc7d0e04d6d9ad4cf550156e6ed7ffe7806d6483ed`；cfg SHA `dec94f6c795fce4422231b3dd94cb51523a239b9e70de2a52e7e90b9356741af`。实际训练 P、holdout P、冻结缓存的公开 plan 均为相同 2056×8，`uint8(plan(:))` SHA `323658320b7d0362f43ff4e2ec098d2b005c43dc7657824b06fe68735999d2f6`。h/h_by_slice、cfg、plan 形状、profile、版本、protocol 和签发源一起核；plan 字节哈希本身不编码形状。chip/profile 自报不证明物理身份。新图模型 SHA 可不同，须审语义并重新资格。
- **M1 不复用**：历史校准特征及冻结核是 M8 finite-sinc2 8 位 DT；M1 scratch 标记 `unsupported_m1_no_fit`。M1 N8 门不能授权 M8 h 或旧 holdout 在 M1 上使用，须先定义兼容数学并独立训练/评价。

## 运行时和状态

- owner `first_id` 必须是**实际进入 owner 的首个 RX-ready ID**，不能直接等同分析窗口 `P.first_id`。旧 holdout 汇总 all-ready=1028、选中 1024 条 ID 4–1027；须明确定义公开预热 fence。训练 epoch 1、历史 holdout epoch 3 各按所属阶段配对；运行段 epoch 更换需外部 fence 和明确重启。
- LOAD 仅建候选、QUALIFY 仅标合格；PUBLISH 仅限 inactive 合格槽，要求 `activation_id > last_RX_id + G`，G 必须由实际时序证明。按样本自身 `(epoch,id)` 选版本；RETIRE 需可信 drain 证明且等待足够 RX 槽数。invalid0 仍推进 ID/槽数但不产生有效码；外部合同须证明这种槽计数覆盖实际流水线。错 epoch、首 ID、跳号/重复、RX fault、无证绑定不得静默回退。RAW ready 与命令同 hit 时 RAW 优先、命令 BUSY。
- Outputs 只读当前状态并丢弃 `step` 预测 next；Update 每 hit 最多提交一次。普通拒绝或跨 hit duplicate 的去重元数据也只在 Update 提交。相同有效 payload 重算一致，改变已消费 payload 锁存冲突；no-ready/valid0 未消费的 RAW/nominal 占位必须忽略。Outputs 不拟合、换槽、写 DWork、改变 RNG、读文件或打印；DEM 是 ID/epoch/seed 确定性规则，dither 是 ID/seed 确定性规则。

## 证据

协议 SHA `a0d418f409782a79e0636815e0844f93cab878abda016927ebd562ca5e7784ad`；训练、冻结、评价回执分别为 `runs/az_probe_20261028T100042Z/receipt.json`、`...T102242Z/receipt.json`、`...T102427Z/receipt.json`。v3 step SHA `6e3987cbd67f62bac1b176bff4298660e2464284f4104c7aa53d794d0b827b2d`；其静态回执标记 MATLAB fixture 未执行、实际 P 未绑定（以之后的原生回执为准）。本次只读公开参数、计划、冻结系数和汇总，未读实际 C/held/内部残差/旧 holdout 逐点答案，未运行 MATLAB 或操作 Windows/current。
