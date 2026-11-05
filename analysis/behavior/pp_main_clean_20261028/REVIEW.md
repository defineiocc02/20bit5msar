# 140306 干净主图默认 OFF scratch：独立只读复核

结论：140306 的新 prepare **无 bank → 显式 OFF** 的隔离 N8 证据，通过本次独立文件与数值回读。当前生产图仍为 6319，生产根 `SAR20('apply/check/run')` **没有在本次执行**；这不是 current 已晋升，也不是 Bank ON/N256 新仿真或产品验收。

- 冻结 ZIP SHA `952d315aa7b6b6a10407f721cf8a52d4220a66db2b8f273cd0c94e4a66cbe57d`；39 个 stage 文件的外部清单/零 reparse 回执已保存。140306 通用 `candidate.zip` 含对应36个候选文件和两份入口副本，均与冻结 ZIP 字节相同；它未包含3份 Markdown，且还包含其他历史文件，不把整包误称仅含该候选。实际 scratch 的22项 runtime 与5项测试源码均匹配冻结锁；复制的223项 SATK pin 和当前87项6319生产源码全部哈希一致。
- `parameters.mat` SHA `34d2daa0f1414591c5c015f50871fb1c41b49468b39fd4cd1c67f2348550baf7`；全 P 的 HDF 结构指纹与133342的 factory_base、factory_off 两份保存 P相同，`P.bank` 仅 `enabled=false`；独立 `DecodeP.mat` 与 P.digital 的 HDF 指纹相同。另将 as-run SLX `modelWorkspace.mxarray` 逐字段与两份 MAT 对比：103个标量结构、367个结构数组元素、2,421个数值叶子的原始位和335个文本叶子一致；MATLAB v5 读取会压缩单例维度。`TrainCaptureFile` 为空；该 workspace 成员字节与133342两份 factory 图也相同。
- as-run SLX SHA `b2c7491416a0629b10fa5cc9c1b8f1db3f34b6bbf9154babec2076ce7aed12c7`，实际 `simout.mat` SHA `693bc054189281018b87126ea8cd7b7c1457a8955fd81349913ce215fd6073de`，都与140306 receipt一致。对133342 factory_base及factory_off各自的原30条实际 timeseries，类型、存储shape、Time及Data原始字节逐一相同；本次新图另有Bank valid/meta两条日志。
- 全部12条直通 ready 的 ID 为0–11、epoch 1、valid均1；48组×12周期，共576条实际事件时间/标签与保存 P对应。目标 ID4–11 的实际码为 `[963400, 979654, 989058, 991473, 986858, 975288, 956933, 932073]`，从各自实际 RAW 独立复算相同。真实根 Code20 对原 code_log、根 CodeValid=0 和 CodeMeta 对应 OFF 占位均重新比对通过。
- 独立图回读见原277块/340条端点变为290块/361条，原边仅移去 `Fpga.y1→CodeLog`，新同一 BankOwner 驱动CodeLog和根Code/Valid/Meta；状态反馈、实际时钟、RX fault路径和 trigger/solver已按实际SLX解析。图注保留 `Bank=OFF`；新运行的 ON 图注 update/check、故意 stale 拒绝、全ready摘要fixture由 native receipt记录通过，但没有独立留存ON图注原文、该异常原件或fixture中间数组，不能冒称本次直接回放这些操作。旧133342的实际 Bank ON日志再读到8条选中RX valid1、同ID/epoch/time及slot/version2，与该旧门一致；不是140306新ON运行。全ready摘要fixture是合成测试，本机按相同输入另用Python复算计数与旧ON标签/有效位负例；这不是重新执行MATLAB，新候选生产 SAR20 的摘要执行尚未测试。
- outer `exit_state_verified`、inner `cleanup_verified`，记录scratch已关闭、path/cwd/RNG及主SLX/公开工作区/DecodeP/logger门通过；当前主SLX重新读回仍为 `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`。主私有 P 未比较，同路径已缓存函数的内存字节也无法独立验证。

一次需准确记录的清理范围：除了明确清除原 prepare/note，退出前 overlay 内 68 个缓存路径中有56个来自**复制的 SATK**，outer 按短名记录清除了共74项（含候选业务及 copied-SATK helper）；candidate/overlay 残留回执为空，但没有全量原 SATK 缓存前后快照，不能声称所有原 SATK 缓存原态未变。此次没有触发 dirty partial 路径，其失败保全仍未实证。

**布局阻断：** SATK 将根 EventStep 从 `[460 80 1360 300]` 改为 `[400 170 450 220]`，并移动7个旧内部块；原始端口和数值通过不代表画布可读。逐 SID 旧/新位置、仅配置 Position 的建议和重新验收门见 [LAYOUT_REVIEW.md](/tmp/sar20_independent_140306/LAYOUT_REVIEW.md)。

本次工作为 Mac 本机只读归档解析；未操作 Windows/current。机读核验见 [audit.json](/tmp/sar20_independent_140306/audit.json)、[workspace_comparison.json](/tmp/sar20_independent_140306/workspace_comparison.json)，脚本为同目录 `audit.py` / `workspace_full.py`。实测只支持该 N8/default-OFF 范围；两槽不同 h、真实 fault/drain、根非ready脉冲合同和N256均不在此次通过范围。
