# v5 固定行为 profile 资格：静态审查

结论：在可信源码、受控试验入口、锁定训练 P 原件和未被篡改的 Q 字节这些前提下，v5 可作为**固定行为 profile 的一致性检查方案**。目前只有静态候选，不证明新图 native 行为通过、独立机构签发、硬件批准或防对抗篡改。

## 已核事实

- `qualification_rx1024_v5.json` SHA `9d9103c060f605f1ce2154bbec990c06812babf7dd2a0820d8da9b213f6b2056`，与 `sar20_pp_parameters` 内钉值一致。它保留既有 M8、τ0、同模拟芯片/理想外参、2048 训练及 1024 独立 holdout 的指标，`NOT_ACCEPTED`、activation none；相对 v3 仅更正旧文件读取声明和历史 whole-P 证明边界。当前生成器不再打开旧 `selected.mat` 或 `public_holdout_result.mat`，改引用锁定回执与旧独立审计的摘要。该旧审计 JSON 仍含 4 条窗口外 warmup RAW，而生成器会完整解析该 JSON；若禁止读取旧 run 的任何逐点值，应改用预先封存的纯汇总快照。
- 参数门核 Q SHA、M8 日历、τ0、公开 profile、公共 cfg/plan/h、源码路径及摘要；虚拟适配器从同一 Q 构造 training/qualification cert **和它们的 allowlist**，然后调用冻结 v3 的 LOAD/QUALIFY。它检查结构和内部绑定，不产生独立外部信任或签名。两槽当前均限定同一 h SHA，版本可不同；无法以此证明真实不同系数切换。
- v3 LOAD/QUALIFY 在局部状态 S 中执行后丢弃；真实候选 `sar20_pp_step` 使用另一个 64-double 状态机，初始选择预装槽，不能称 v3 owner 的完整生命周期已在同图运行。现有 scratch installer 将 drain ack 固定为 0，仅支持未排空/拒退情形，尚无真实消费者排空证据。

## 阻断项和建议负门

1. **资格文件读取一致性**：参数函数先 `file_sha(f)` 再独立 `fileread(f)`；verified wrapper 又再次 `fileread` 而未重验。若中途替换文件，虚拟 cert 可取未经固定 SHA 校验的第二份。应一次读入字节、验证其 SHA，并把同一解码结果传给所有检查；测试文件预先篡改、两次读取间替换和异常时无有效输出。现状不能声称抗并发替换。
2. **同芯片/配置来源**：现有 `P.bank.provenance_scope='TRAIN_P_WHITELIST_CONTROLLER_ONLY'` 是自报，并不验证实际构造路径。且公共 profile 门未检查所有可能影响电路的字段；例如 `P.backend.ct.reference_v` 未在 profile 列表中，而 backend 会将其传入 `sar20_cdac2_network`。若绕过受控入口直接修改该值，自报标签与列出的公共字段仍可保持不变。应由受控入口从锁定 TRAIN P 构造模型、限制只能改的公开字段，负测未列入的公开字段及入口被绕过；不读取/散列逐叶 actual C 来构造校准资格。无独立抗替换证明时，只能说明这一受控来源前提。
3. **锁定与篡改测试**：预登记并冻结 Q、候选源、入口及依赖，以只读副本负测 Q 一字节、h、h_by_slice、cfg、plan 及其形状、版本、τ=1 ns/Inf、公开 profile 和 M8 日历。应在真实 applied P 的 apply/compile/enable 检查，并验证错误时 code_valid 无效；不能把静态预期写成已通过的 native 门。`which` 与磁盘 SHA 不证明同路径 MATLAB 缓存新鲜度，runner 须另行证明绑定。
4. **实际时序**：首个进入 owner 的 RX-ready ID、epoch、valid0、同 hit 重算、UnitDelay 在 Update 单次提交、未来边界及独立 drain 接口均需同图原生验证；零 ACK 不能证明完整 ping-pong。Outputs 不得更新状态/RNG 或读取校准隐藏数据。

静态快照：`sar20_pp_parameters.m` SHA `4113d0a9fdbb6cda76bae8b215b1ca34b3761225b0b529d2b64aab3403a39069`，`sar20_pp_verify_v3_qualification.m` SHA `0b60694a0beb3759d78c3d6ece6d1fc0c0230451a8e9a405b934264591be64b9`，`sar20_pp_verified_parameters.m` SHA `477137a7293340d80fe5b656c06788556cc72a71edee18917976ad18c8f26cf2`。候选仍在形成，以上只描述本次读取时源码，不是冻结或原生运行证明。未运行 MATLAB，未操作 Windows/current。
