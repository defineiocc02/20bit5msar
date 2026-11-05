# v7 与 A 阶段候选只读审查

结论：v7 静态代码已把资格 Q 的 SHA 校验和解析绑定到同一字节快照，并把上次遗漏的 CT reference 电压列入公开 profile。实际 A 图、篡改负门和背景 B 训练尚无本候选原生通过证据；当前只能准备固定行为 profile 的预资格路由。

- **Q 与公开证据**：`qualification_rx1024_v7.json` SHA `74f76d2491a25fcd22264d2af33c8fb421e1412b8885428b040b5c6765c0f0c6` 与代码固定值相同。`fread` 一次后对相同 bytes 做 SHA 和 JSON 解析，已解析 Q 再传给虚拟 v3，避免先前多次文件读取竞态。纯汇总审计 SHA `c6ee0458d61fc8357e39e82eeaab3250871c4c9370cd48455772d5139ddb5c77` 与 Q 相符；Q 生成器不再打开旧 holdout RAW/Ref/结果文件。原始审计汇总抽取器为生成该纯汇总曾读取原审计 JSON，其中有窗口外 warmup RAW；纯汇总不含这些逐点记录。
- **P/系数与信息边界**：本机只读对比已保存训练 P、holdout P、冻结数字缓存，Q 的 42 个公开 profile 字段一致，plan 相同且为 2056×8，h/cfg/plan 摘要及原回执门相符；旧训练日历为 D2/TA compare/反馈 12/8/7。Q 没有生产接受或独立机构签名。BANK 的 q 仅包含公开 cfg、plan、h、标签、版本/命令，不含完整 P、actual C、held 或 holdout 答案。
- **来源构造修复，仍有条件**：新版 `sar20_pp_case` 从 TRAIN/冻结 MAT 复制至独立临时目录，对复制文件在 load 前后核对固定整文件 SHA 及回执，再只改命名的公共字段；没有逐叶 actual-C 摘要。有效性依赖私有临时目录隔离及后续工作区不可被未审改写；`provenance_scope` 仍是自报，不是反篡改证明。源身份负测在脚本中定义，尚未看到 native 回执。
- **首帧与 M8**：候选要求实际进入 owner 的首条 RX-ready ID=0，然后连续、同 epoch；`sar20_pp_compare_n8` 准备验证首 ID0。参数门检查日历 8 次 compare/7 次反馈与 nominal tracking_count=7；新 A 图实际执行数尚未观测：从 TRAIN P 继承 ADI disabled/最多 1 点，预定比较器未检查逐事件物理计数。不能把历史 run 的 8/7 或新图日历直接称新图 8/7 已实跑。
- **A/B/drain 范围**：A/B 两槽预装相同 h、不同版本；A 起始、计划在 ID4 切路，仅检验预资格路由。虚拟 v3 LOAD/QUALIFY 的状态未作为实际运行时 owner；实际由独立 64-double 状态机及 UnitDelay 预测/提交。installer 将 drain ACK 置 0，不能完成真实退休或证明消费者排空；后台 B 采集、拟合、重新资格和不同 h 切换均未实现。安装器目前只替换 `Fpga → CodeLog` 的日志目的端，新增 valid/meta 日志，非完整对外产品码接口。
- **原件和冻结尚缺**：新版 runner 已在每案仿真前保存实际 P/DecodeP 和 workspace SLX，但尚无 simout SHA；所存 source 清单仅候选及 6 个依赖，不包含全部前端/后端/串行源和其缓存身份。入口只核主 SLX SHA/stopped/clean，未做主 workspace/loggers 前后快照。当前 `source_lock.json` 尚不存在、expected 仍为 `SOURCE_LOCK_HASH_INSERT`，所以此快照未冻结且直接运行会拒绝。冻结后须核入口自引用不致缓存预检自拒，完整源码/缓存绑定、每案 simout 哈希及 cleanup，再运行已定义的真实负门。

受控来源与源码/Q 固定只能支撑有限行为试验，不等于独立签发、抗替换或硬件批准；`NOT_ACCEPTED` 与用户禁止读取实际 C 的边界不变。本次只读公开字段/摘要，未运行 MATLAB、未操作 Windows/current。

可复核脚本 `/tmp/sar20_v7_static_public_audit.py` SHA `d65271522c2ffcaaa4f25d543f9896f5cb614ece19a67ab50d0831275d9be0d0`；机读结果 `/tmp/sar20_v7_static_public_audit.json` SHA `2176bbc0de728ad70d86323c43ef04b5857986ef85e07cf0df375ef6f0245887`。候选在持续更新，以上为报告时的源码快照，文件 SHA 见机读结果。
