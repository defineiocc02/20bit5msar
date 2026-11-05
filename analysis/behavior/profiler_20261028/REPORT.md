# 122805 N256 profiler 行级只读核对

`profile_after.mat` 保存了真实的 `ExecutedLines`。`profile_before.mat` 的 `FunctionTable` 为 MATLAB 空 struct，因此此任务的这些函数行表就是 after 的累计值；两目标函数的次数和含子时间也与 `profile_delta.mat` 相同。下列为一次 **profiler 开启时** 的行累计时间，包含该行调用的子函数和插桩开销，不是未插桩自耗时，更不是可直接兑现的加速量。

## 后端输入验证：50,304 次，函数含子 26.340897 s

源码 [behavior_backend_step.m](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/current/src/physics/behavior_backend_step.m:340)：

| 行 | 实际语句 | 执行次数 | 行累计时间 |
|---|---|---:|---:|
| 408 | `assert(exist('sar20_cdac2_network','file')==2,...)` | 50,304 | 14.404416 s |
| 367 | 逐字段读取 NI flag，`isscalar`、`ismember` 和 `assert` | 402,432 | 4.577446 s |
| 364 | NI 字段名排序与 schema 相等检查 | 50,304 | 1.115419 s |
| 353 | 三个命令标志的 `ismember` 等检查 | 50,304 | 1.045299 s |
| 350 | 12 路 D2/7 路 TA sign 的 `ismember` 检查 | 50,304 | 0.657478 s |

第 408 行的时间是整条断言及其调用的行时间，不能精确等同于 `exist` 自耗时。整个 `validate_inputs` 的 `ismember` 子调用为 553,344 次、含子 5.291209 s；这个值已包含在相关父行与函数时间中，不能叠加。第 367 行次数是 8 个 NI 字段各 50,304 次，不是独立后端调用次数。

## CT 网络：301,824 次，函数含子 20.146186 s

源码 [sar20_cdac2_network.m](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/current/src/physics/sar20_cdac2_network.m:44)：

| 行 | 实际语句 | 执行次数 | 行累计时间 |
|---|---|---:|---:|
| 82 | `alpha = mean(input_gain)` | 301,824 | 3.138706 s |
| 65 | `matrix \ (qin + qdac + qtrack + qmemory)` | 603,648 | 1.768235 s |
| 58 | D2 电荷向量的两个矩阵乘法 | 603,648 | 1.726541 s |
| 47 | 按 side 读取 `net.main_f` | 603,648 | 0.961334 s |
| 67 | `matrix \ [cs; 0]` | 603,648 | 0.903551 s |
| 52 | 构造 2×2 矩阵 | 603,648 | 0.686033 s |

`mean` 子函数为 301,824 次、含子 2.767382 s，已包含在第 82 行中。两倍次数来自每次调用处理两个 side。按实际子函数调用表，`observe` 调用 CT 网络 201,216 次/含子 14.697404 s，`switch_networks` 调用 100,608 次/含子 5.448782 s；这些是 CT 函数的调用上下文，不应与 CT 函数总时间相加。源码每次 backend step 两次 observe、一次 switch_networks，与本批实际 50,304 step 和 301,824 次网络调用相符。

## 证据与边界

- [原始 before/after/delta](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T122805Z/validation/) SHA-256 依次为 `3759b06419384439f5c75d5be15fdae9fab5cec278b051cfd40b4d5102ed118d`、`1b04ece02a31ce7d45bcfdc8d03b940a2e3a5de2ff8b7e74ab8b3c18c7f214a2`、`988563421c074d42231037b9f282093058e49aae2b3fb33d47734da61912fd80`。两目标函数 `PartialData=0`；两个源码 SHA 均与该任务 receipt 和既有 source.zip 相同。
- 该次配置与行为完整性等信息引用 [实际 receipt](/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T122805Z/validation/receipt.json)：M8 N256 scratch，30 路位同比较，profiled sim wall 182.056052 s。本次只读行表，不将 receipt 中的位门另称为本次重跑。
- 行表中第三列是该行累计时间，函数 `TotalTime` 含子函数；行汇总不一定等于函数总时间，详见 [MathWorks profile](https://www.mathworks.com/help/matlab/ref/profile.html)。保存的调用历史达到配置的 5,000,000 项上限，不能假定调用顺序记录完整；本结论基于聚合行表和函数表。
- `exist`/参数校验与 CT 求解是受插桩影响的热点候选；变更前需保留公共 kernel 的动态输入、错误顺序和失配/replica/AZ/浮点数语义，再做实际 N8/N256 完整位门与未插桩 A/B。

重现：使用项目 `dependencies/analysis_env/bin/python` 执行本目录 `extract_profile.py`；机读结果见 `profile_lines.json`。未修改 current/Windows。
