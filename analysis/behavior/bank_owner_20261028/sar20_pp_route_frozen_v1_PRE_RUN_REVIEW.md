# A 阶段冻结包：原生调度前只读复核

结论：冻结包字节、资格 Q 和源码锁在归档内一致；未发现阻止**受控 scratch N8 尝试**的确定性静态错误。实际 MATLAB/Simulink、当前主图、缓存和下游握手未由本次审查验证；可运行项仅是同一 h 的预资格双版本行为路由，不是 B 后台训练或产品接受。

- **完整性**：ZIP SHA `0cdb3e1c24e86e5da27fd36f27a595df96978948237ee8796f25488f0cd9a76a`；外入口 SHA `15637924cebea87731f25bf6cdc45e85e9e5e170bff99db022a4dc3709479349`。无重复/越界条目，31 个 manifest 项长度及 SHA 全符；22 个候选函数的 source-lock 均匹配，内 runner 排除在其自身缓存拒绝名单，并由外入口单独钉住。87 项 production source lock 与 115303 已归档源码清单一致；native 的 `which`、当前磁盘内容与缓存只能在实际调度时确认。
- **资格及输入**：Q v8 SHA `a9cfaaefed217e5f6d6e7e1a2faa5586e78dbf8f6808523a9c5185c19ab9778f`；Q 单次读取，哈希与解析使用相同字节，解析对象传给 v3 资格适配器。TRAIN P/冻结缓存副本在 load 前后检查整文件及回执 pin，依赖私有临时目录和受控入口；公开投影严格约束输入、日历、计划、数字/缓存字段，不提取模拟 C/held。虚拟 v3 证书和 allowlist 均由同一 Q 派生，属于内部一致性门，不是独立签名；Q 仍 NOT_ACCEPTED、无自动激活。
- **预定检查**：每案计划保存 P/DecodeP、workspace SLX、simout、各 SHA 和 source 清单，update 后及 sim 后核公开 P/资格绑定。OFF 计划做 30 路逐位门和 root code/valid/meta 检查；ON 计划核其余 29 路、RX 首 ID0、epoch/valid、ID4 版本切换、root yout 和已有冻结码。改 Q、源 P、缓存 h/plan、额外字段、τ=1 ns/Inf、M1 日历和 CT reference 的拒绝均是**待运行断言**。8/7 仅由参数和日历声明核对，当前不保留逐事件 ADI 计数，不能称新 A 图实际执行 8/7 已验证。
- **实际范围**：两个预装版本 h 相同；v3 LOAD/QUALIFY 是编译前局部虚拟事务，真实运行采用独立 64-double 路由状态。新 root Code20/CodeValid/CodeMeta 由安装器提出并待验证；drain ACK 固定 0，不能证明消费者排空或旧 bank 可安全复用。B 采集/拟合/独立资格及不同 h 切换均未实现。root CodeValid 目前只在 ready 时对齐，不能推断事件间脉冲形状或 CDC 安全。

## 调度前条件与仍需补证

1. 外部控制器应在唯一空目录精确展开 ZIP，确认无额外文件；entry 逐项核 manifest，但本身不验证目录中没有额外文件。检查主模型 stopped/clean，按实际 `ppJob:cached` 精确盘点已有同名函数，避免未授权地清除其他任务缓存；失败保留回执、不自动重试。
2. 工厂 PostLoad/InitFcn 会按 scratch 路径添加 src；完整源门早于打开模型，需在实际安装前后核路径及 SATK `model_read/edit/check` 的绑定/缓存。87 项锁不涵盖 SATK 本身；`SAR20('setup')` 的同路径缓存被入口明确豁免，不能仅凭磁盘 SHA 推断其缓存新鲜。
3. inner 完成回执在 onCleanup 恢复 path/cwd 前写出；未自证恢复后的路径、完整主工作区/日志及候选 inmem 缓存。每次仿真检查 RNG，整个 setup/fixture/negative 阶段的 RNG 不由此证明。调度后须单独只读复核会话及回执，再视授权处理该作业自有缓存或 scratch。
4. 构造后的直接私有工作区替换不在公开 guard 的检测范围；该证据依赖受控入口和不可更改的运行环境，不能扩写为对抗替换证明。不要以 actual-C 逐叶摘要补洞。

本次只读冻结 ZIP 和已有源码清单，未访问 Windows/current、未运行 MATLAB、未读取旧 holdout 逐点结果。核验脚本 `/tmp/sar20_pp_frozen_static_integrity.py` SHA `0134e196ac8180c402c79ad67742f39116f1b6931024f686efe7410a0356891c`；机读结果 `/tmp/sar20_pp_frozen_static_integrity.json` SHA `c6004527e09dcaafb1830fa0aa11c35fa3d644b61f4a1efa36566d62a98789dc`。
