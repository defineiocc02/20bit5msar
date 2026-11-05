# 141949 backend A/B 与 142709 定向恢复：独立只读复核

结论：两组受控 scratch 的原生输出通过独立逐位回读；候选仍未晋升，缺依赖的独立 MATLAB 进程负例未运行。一次顺序计时不能证明稳定提速。

## 原件与输出

两案从 121500 已保存的 M8 P/SLX 原件运行，fs=5 MHz、fin=97,656.25 Hz、DAC τ=1 ns、epoch=1。独立校验两案 P、SLX、121500 旧 simout 和本次 old/new simout 的 SHA，均与冻结入口和原生回执一致。三个运行的 30 路原生 timeseries 的类、形状、实际 Time 和 Data 均逐位一致；并独立将 all-ready RAW、码、实际时间与三份记录及 simout 对应。全量 SHA 见 `/tmp/sar20_independent_141949.json`。

| 案例 | 全部有效 ready | 指定记录 | 旧仿真 s | 新仿真 s | 旧 update s | 新 update s |
|---|---:|---|---:|---:|---:|---:|
| N8 | 12，ID 0–11 | ID 4–11 | 9.3062627 | 5.3788457 | 0.3273626 | 0.2615362 |
| N256 | 260，ID 0–259 | ID 4–259 | 129.0781867 | 101.5095796 | 0.2411142 | 0.6346331 |

N8 保存的 ADI 事件日志中，ID 4–11 每个记录的最终计数均为 D2/TA compare/TA feedback = 12/8/7。计时是无 profiler 的一次 old 后 new 顺序配对，含会话和顺序效应；并非重复统计、稳定速度或完整工作流收益。

冻结 ZIP SHA `3ba1b23d7e92d25801769d4c4796cc89db934ebe311400fdf6e43fe06e4b8a38`；7 项冻结 manifest 的 SHA 相符，本次 6 个运行时 MATLAB 文件及入口与运行归档逐字节一致。更大的运行归档未包含离线 `static_check.py`，该文件在冻结 ZIP 中可核；87 项生产源清单与已归档源清单一致。运行时身份仍以对应原生 source/path/cache 检查回执为准，不额外推断缓存内存字节。

## 负例与退出

原始 `error.json` 和保存的 bad P/command 均已读回：6 项 setup 分别拒绝负 Cf、负参考电压、非布尔 NI、未知 NI、未支持 NI 和负 AZ τ；3 项仿真 Outputs 分别拒绝非法 sign、非法 tag 和 AZ 关闭时写入，均保留原始异常 ID/报告，3 个事件注入模型 SHA 与回执一致。6 个 dirty partial 的保存 SHA 亦相符。另有 native 纯函数门记录 24 个 direct/bound 负例以及值快照与有效状态/输出位级检查；这些并非覆盖所有运行状态。

native 和 entry 各自记录 cleanup complete、三个 backend 入口恢复生产路径、目标缓存已清、profiler off、主图 stopped/clean、主图与工作区未变。根 wrapper 却查找 `validation/receipt.json`，真实 native 回执位于 `validation/validation/receipt.json`，故误写 `unsafe_native_cleanup_preserved`，并保留任务入口 path/cache；这不是可忽略的根回执成功。142709 基于三份旧回执进行定向补救，记录清除自有 entry 缓存并仅移除该路径，前后 path 列表独立比较只差该项；源码断言 cwd/RNG、主图 SHA 和 backend 解析不变，但回执没有单独保存恢复后的 RNG 快照。原完整 pre-wrapper path 快照不存在，不能宣称全环境恢复。旧回执哈希在恢复后仍相符。

只读脚本 `/tmp/sar20_independent_141949.py`（SHA `b242d61b220dd1fa940c8dcbe1511da164c34f6fa5081469e2910167ed962d52`）退出码 0；结果 `/tmp/sar20_independent_141949.json`（SHA `6ff9a234d56ebf8e7c4d63d12ca5ef10c9bbc259019e4dd3cc6955a2a85c5683`）。未操作 Windows/current，也未重跑仿真。
