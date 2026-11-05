# 114345Z M1/M8 实际 N8 scratch 独立复核

结论：四组保存的 scratch 数值证据通过此次离线核验。M8 两组各 29 路历史日志与固定的实际 N8 参考逐位一致；M1 两组实际观测到每周期 12 次 D2、1 次 TA compare、0 次 TA feedback。该结果不代表 current 已接入 M1，也不代表 M1 的 N256 频谱或性能已经验证。

## 样本和输出码

四组均为 N8、输入频率 97,656.25 Hz、ID 4–11、epoch 1。每组观察到 14 次 ADC ready（ID 0–13）和 12 次 RX ready（ID 0–11）；对应的 12 条 RX 与同 ID ADC RAW 一致，ready 处均 valid=1。以下为 RX 选中窗口的实际 code20，全部与从实际 RAW 和各自保存的 P.digital 独立复算结果相等：

| 组别 | ID 4–11 的 code20 |
|---|---|
| M8，零 τ | 963400, 979654, 989058, 991473, 986858, 975288, 956933, 932073 |
| M8，1 ns | 963400, 979654, 989061, 991470, 986858, 975285, 956933, 932072 |
| M1，零 τ | 963399, 979653, 989057, 991473, 986857, 975287, 956933, 932073 |
| M1，1 ns | 963399, 979653, 989061, 991469, 986857, 975285, 956933, 932071 |

每组 ID 4 的 RX 时间为 1.338 µs，即相对该 ID 的 CNV 538 ns；此为 RX 事件时间，不是该样本的 ADC 原始锁存时间。两“零 τ”组的 18 路 τDAC 均为 0、有限建立标志为 false，但 `backend.dac_coupling.enabled` 仍为 true。

## 时序和物理事件

四组每组 14×49 条 event 及 14×48 条 ADI 观察行的实际时间、周期和分组与各自 P.groups 精确对齐；每个周期 ADI 实际计数逐事件与日历累计一致。M8 的 D2/TA compare/TA feedback 分别为 12/8/7，M1 为 12/1/0。

M1 的 75 ns 实际比较之后，控制 DT 锁存为 0 或 128，低 7 位为 0，并与当次 VY 的符号一致；七路反馈符号全为 0。76.25–83.75 ns 共七个 idle 命中、85 ns tracking_end。M1 日历里这七个命中各含两个 idle token，共 14 个 token；不要把 14 个 token 当成 14 个不同时间点。两种 τ 在冷启动第 0 周期的 M1/M8 首次比较前 backend 状态和首个决策一致，而下一事件的 M8 与 M1 TA 反馈实际不同；这是一条实际轨迹的对照。

## 源包、模型和逐位对照

- 冻结包 SHA-256 `d6528489665fda047d27c5781d90ae14ae05c6d51d312846e5b13bba120b9103`；实际候选包 SHA-256 `0458328b851e25e13193624a221d80fca82ba2064e78b15797ba8cb7f993de5f`。22 个候选包文件与冻结包相应内容逐字节一致，manifest 各文件 SHA 匹配；候选外部 pins SHA 为 `6ce84b8db819eae20afd62222444907c5efa258302c8da35dda159b72f70ed28`。归档基准源码包 87 个文件也逐项核对。
- 安装前工厂副本 SHA `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`。从 before/after SLX 可读取的 277 个 block、340 条边及配置项中，图安装只改变 SID 189、191、192 各一个数字参数表达式。四个实际 case SLX 相对安装后图的上述解析结果仅有 SID 105、123 的显示说明变化。各 case 的 SLX、P、simout、observation SHA 与内层回执相符；独立读取 SLX ModelWorkspace，核心 P、DecodeP 和 49 组事件与保存 P 一致（未声明全部 P 字段已离线重建比较）。
- M8 零 τ 和 1 ns 分别对比归档参考 `behavior_c5a4d0b8-7e34-4a92-b698-5bf72067ab09`、`behavior_8165ddcc-971e-49a6-938b-ad2fb6dd9603`。每对 29 路日志的类型、保存形状、Time 和 Data 字节相同；新增启用的 `adi_wire_log` 不包含在 29 路门内。相对参考 P，M8 仅两个 ADI debug 字段不同。
- 内层回执 SHA 为 `3deb20a76b6ff491b027a8362773a3bd6c0efe0aa31d2db0c7aed0eaebaa311e`；外层回执记录状态和候选包 SHA，但不单独钉住内层回执 SHA，因此这里的内层 SHA 是本次离线计算值。

## 会话清理和范围

114345Z 原生执行日志有两条 onCleanup 析构警告：`cleanupDone`、`restoreDone` 在函数退出时已销毁。虽内层回执报告 `environment_cleanup=complete`，不能据此把该次退出描述为无警告或完全恢复。

后续原件显示：114903Z 健康断言失败；115007Z 分项检查记录候选 path=0、inmem=1，唯一缓存项为任务入口 `run_m1_m8_v3.m`，生产 SAR20/frontend/backend 路径解析正确。115040Z 定向清理回执记录候选缓存从该入口变为空，主模型 SHA 仍为 6319…、stopped/clean。这是后续补救及其检查，不是 114903 健康门已经重跑通过，也不证明其他未检查状态已全部恢复。

此次所有验证在 Mac 本机只读归档完成；未仿真、未操作 Windows/current。N8 数值门与环境补救均不等于 M1 主图集成，更不能当作 N256/SNDR/ENOB、PVT 或芯片性能证据。

## 工件

- 原件：`runs/az_probe_20261028T114345Z/m1_validation/`；健康/补救原件为 `runs/az_probe_20261028T114903Z/`、`...T115007Z/`、`...T115040Z/`。
- 离线核验脚本：`/tmp/sar20_independent_m1_114345.py`，SHA-256 `7bcad6d87fbbe1656f4c446c0295aea54eed6cc6c347d265729dd09ca532f18d`。
- 完整机读结果：`/tmp/sar20_independent_m1_114345.json`，SHA-256 `66df685a5f7f8a85afe20cba55cd44d482966ff7b604cc5979ad217975d00b22`。
