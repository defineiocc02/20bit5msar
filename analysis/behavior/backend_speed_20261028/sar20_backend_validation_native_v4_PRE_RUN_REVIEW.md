# Backend 校验前移 native v4：调度前只读复核

**结论：静态未发现 AB 主会话确定阻断，可由唯一控制者在前置条件成立时调度一次。** 前提是主图仍为 6319、全部已加载模型 stopped、主图 clean、profiler off、`SarLookup` 名称空闲，且 87 项原源码与归档匹配。包本身的入口会再执行身份和环境检查；如 Bank 晋升改变锚点，应重新审阅绑定，不能绕过。

## 身份

- ZIP SHA256：`3ba1b23d7e92d25801769d4c4796cc89db934ebe311400fdf6e43fe06e4b8a38`。
- `candidate/SOURCE_PINS.json`：`e135ae504403407fd714b593ca7e044d820e9549a7706b00a387657f5e1ab8e6`。
- native：`800410d17c4cb09540a8fe143fb1ac6557701c0638342dc6abbee63675d352ba`。
- wrapper：`8aaf83d1f00c0dfac7a84624dfd6f0e1f608d95d1bf9cd39b4870415b13e9e89`。
- 独立读取 ZIP 提取件，manifest 列出的 7 个文件 SHA 全部一致；3 个数值候选与 v3 字节完全相同。121500 的 N8/N256 各 P、SLX、旧 simout 和 records 共 8 原件 SHA 一致；主图 SHA `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`，87 项源码文件清单及每项 SHA 与保存的原始 manifest 一致。

## v3 缺口

v4 移除了缺依赖分支中无条件恢复 path 的退出回调。新的退出回调只写 `missing_path_unrestored.txt`；临时路径开始前设置 `missingPathUnsafe`，未确认时外层清理保留路径和缓存。正常恢复前须先关闭 scratch、确认所有模型停止和无 close/cache 异常，并核恢复前后目标函数的 `which` 与 `inmem`。wrapper 也读取 missing 的 armed/unwind 标记。静态控制流已修复先前指出的无条件恢复缺口。

这是源码层审查；MATLAB 中 dirty 保存失败、中断、路径恢复或缓存故障注入尚未实证。AB 失败时保留 outdir、native/wrapper 回执及原始 partial，勿自动重试。`native_returned` 仅表示函数返回，必须检查内层状态。AB 完成仍需由同一 v4 wrapper/manifest 的已清理 AB 回执绑定，确认主进程 PID 后在新进程运行 missing，并独立后验复核；两组真实 AB 与该负例通过前不能宣称等价。

重新运行 `static_check.py` 的静态条目全部通过；MISS_HIT 检查 wrapper 与 3 个 native 验证文件均通过，不能替代 MATLAB checkcode 或 native 执行。只读访问本地 ZIP、源码及归档；未操作 Windows、MATLAB 或 current。
