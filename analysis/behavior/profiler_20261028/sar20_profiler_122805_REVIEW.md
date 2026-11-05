# 122805Z N256 profiler 原件独立复核

结论：该次是**一轮原源码 scratch profiling**，其 30 路保存日志与 121500 的实际旧版 N256 参考逐位一致；profiler 的 572 个累计函数条目与保存的 delta 逐项一致。它支持定位本次 MATLAB 函数累计耗时，不证明稳定提速。

- **身份与输出**：P SHA `844365f7cb953682dc35385068bd21a153c7bbd7e8f2f21459fe1b7454c957a2`、scratch SLX SHA `1c903ad632930cf169726fbca1e4231bd3444ce78588da22c1323129ac5bed79`、原参考 simout SHA `3bb0d0c44c9859f58ff1cbced2badc7adfe0fba932b9b21bda5e092364931a91` 均与 121500 原件和回执相符；87 项源码清单及归档文件逐项 SHA 一致。实际 P 为 N256、5 MS/s、97.65625 kHz、epoch 1、τDAC=1 ns、RX 开启。
- **位门**：新旧 simout 的 30 路类、存储形状、Time 和 Data 原始字节逐项相等；实际日历为 262×49=12838 事件，260 个 RX ready 全部 valid，选中 ID4–259 共 256 条码，公开 RAW 解码一致。256 个码按 little-endian uint32 编码的 SHA 为 `3fd70372aadabc480fcbac80b7c74e00807efc4b07dbb4c4bb5e3c79b69320a8`。
- **before/after/delta**：before FunctionTable 为空，after 和 delta 各 572 项；以 CompleteName 核对所有调用数及 inclusive 时间差，保存的 top80 及回执一致。三类代表记录为 event-source Outputs **12838 次 / 2.322872 s**，backend S-function Outputs **50304 次 / 80.622040 s**，`sar20_cdac2_network` **301824 次 / 20.146186 s**。这些是函数调用数及含子调用时间，父子项重叠；不能相加、解释为物理事件数或作为硬件耗时。
- **历史容量**：after 的 `FunctionHistory` HDF 数据集为 5,000,000×4，触及原 status 的 5,000,000 容量，末行非零；FunctionTable 调用数合计 7,796,574。该有界 history 不能当完整调用顺序 trace。累计 FunctionTable/delta 仍如上逐项可核；只用累计函数或行时间排序，不声称完整 trace。
- **墙钟与恢复**：本轮未 profiling 的 update 为 1.4689107 s，开启 profiler 的 sim 为 182.0560521 s；121500 另一次未 profiling 的旧 sim 为 136.1479 s。两次墙钟相差约 45.908 s，但运行条件与仪表开销未分离，不能把差值直接归因为纯 profiler 开销，也不能当稳定加速比。原生回执报告主 SLX/工作区、RNG、path/cwd 恢复，主图 stopped/clean，profiler 最终 off；这些是归档回执而非本次实时状态检查。profiler 的全局计数/历史已追加，不等同于恢复到原来的空数据。同路径已缓存代码的字节新鲜度也不能仅由 which/磁盘 SHA 确认。

`profile_before.mat`、`profile_after.mat`、`profile_delta.mat`、`records.mat` 和 `log_compare.mat` 的 SHA 由本次独立计算，未在原生内层回执中单独钉住；完整值见机读结果。原件：`runs/az_probe_20261028T122805Z/validation/`；脚本 `/tmp/sar20_profiler_122805_audit.py` SHA `d75e88abaa80addd40f462e94df2437ffce6933f48e9feac85999230dbaa6d4a`，结果 `/tmp/sar20_profiler_122805_audit.json` SHA `6173cb792474b0d21b819e1f2cf0ed13fcca7a595df8f6f86759e9fb3ff1dce5`。本次未重跑 MATLAB、未操作 Windows/current。
