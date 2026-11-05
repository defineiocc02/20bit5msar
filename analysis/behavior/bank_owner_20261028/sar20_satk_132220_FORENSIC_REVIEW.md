# 132220Z 续跑失败与 partial：只读复核

结论：两块 FunctionName 配置及后续 parent wires、CodeLog cutover、三个 root Outport/线路都已执行并保存；失败发生在**第一项最终检查**，下一次不应重复这些结构操作。

- 两次 SATK FunctionName 响应均 `status: ok`；原生端口回执为 BankOwner **10 入/4 出**、BankCommand **1 入/1 出**，Parameters 保持。保存的 `SarPP_partial.slx` XML 也显式包含两项 FunctionName、Parameters 和对应 PortCounts。
- parent_wires、parent_cutover、root_outports、root_output_wires 四份响应均 `status: ok`。相对 130247 partial，XML 图解析从 287→290 blocks、341→361 edges，新增 Code20/CodeValid/CodeMeta 三个 root Outport；所有已申请的 parent/cutover/root 连接均在保存图中，旧 Fpga→CodeLog 已被 BankOwner→CodeLog 替换。这是静态图证据，尚非通过终检或仿真。
- 第一次 `final_check_blk_393.txt` 已写出 `status: healthy`，但外层随即报 `MATLAB:invalidConversion`：“无法从 onCleanup 转换为 char”。冻结续装源码第 65 行将 `model_check` 结果放入外层 `c` 并调用嵌套 `put`；`put` 第 137 行又将同名共享 `c` 赋为 `onCleanup`。返回后第 66 行 `char(c)` 与实际错误吻合。后续 blk105/123/375/root 的最终检查、逐口/selector 断言、installer 成功回执均未到达；OFF/ON/N8 仿真也未到达。

132220 的 owned `SarPP_partial.slx` SHA `a23e6c59356b3ecc7a9a3dfc2499b0af9416fe2281533b059e1c72a443c2deca` 与任务内最终 SLX 及 cleanup 记录一致；`SarPP_last_saved.slx` 仍是原 130247 partial 的 `5413a38f…fa62e325`，base 图未改且已关闭。原 130247 的 9 项固定证据在本次失败后独立重新哈希，均未变。inner/outer 回执报告任务自有图已处理、main 文件及公开 workspace/DecodeP/logger、RNG/path/cwd 恢复；未比较主私有 P，也未再次检查远端实时状态。

最小 finalize 边界：将外层检查结果与文件 onCleanup 句柄改成互不共享的变量；在新 owned scratch 中复制并钉住 `a23e…` partial，先从 **blk393/105/123/375/root 全部终检、trigger/逐口/selector/参数核验及保存**开始，再执行尚未开始的 OFF 先于 ON、负向 update 和 N8 原生门。不要再次设置两个 FunctionName、重复 parent wiring/cutover、添加 root Outport 或重做 130247 transport；不得覆盖任何旧原件。新 helper/runner 须独立冻结并记录 SHA。

身份：本次冻结续跑包入口 SHA `292e56acabc378d0938246118f2beced553694369e4a07fe44071389fe3afb81`，inner runner `1b87b6688ed2660afbd6c0a07f45c4b67ef2778cdd8b41b00d9c8bc481bef3b5`，续装源码 `066865e183ee786294ffd99c42f4ae9ef3428ad384e83e60fd1dc583c4c4c988`；23 候选、87 生产和 223 SATK 磁盘项的记录与锁相符，运行时 SATK 仍限定 4 核心入口。任务 candidate.zip 未镜像两份 README 和两份 Python 生成脚本，其共同文件均与冻结包一致，原生 entry 回执记录完整 manifest 检查通过。

核验脚本 `/tmp/sar20_satk_132220_forensic.py` SHA `4188b29333f310a27ee77af1046f729d7b6e353c6046952f112848f9e0e32ade`；结果 `/tmp/sar20_satk_132220_forensic.json` SHA `a3020348ac36c1c7ddaf6e70ea72a0e8675da0e1565fa34ebf7940e1cf42305a`。仅只读本机归档，未操作 Windows/current。
