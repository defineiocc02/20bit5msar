# 后端名义 CT 重复计算：提速候选

该候选仅在 CT 失配关闭时复用同一事件的名义网络结果；实际 CT 的 VX、浮置电荷和 replica 仍独立计算。模型事件、日志和主图未改。候选尚未安装。

## 已执行验证

- Windows 独立无界面 MATLAB：807 个后端合法状态场景及 5 个错误场景的新旧状态和输出逐位对照通过，含两方向 actual/replica 合成失配、有限 DAC、AZ 与 RA OU。不是 PDK 统计，也不是整图仿真。
- 独立计数测试：失配 OFF 时，后端一次推进的 CT 网络调用从 6 次变为 5 次；失配 ON 仍为 6 次。独立缺依赖测试的异常保持一致。计数有测试插桩，不能作为耗时。
- 同一完整 P 和 SLX 的隔离 N8：所有 34 个实际输出变量（包括 32 路日志、`tout` 与 `yout`）逐位相同。唯一后端源码差异为 baseline `b6fd6bcd…` / candidate `2e97bfbb…`；P SHA `a4130980…`，SLX SHA `d4e7fc99…`。一次顺序 baseline→candidate 的 `sim` 分别 33.5742 / 24.3413 秒；这不是多次配对的稳定提速结论，也不能外推 N256。

`candidate_package.zip` 为固定源码/测试包，SHA `d166f34140708bf0bcc88ec787dac7b4d4bda16894aca0e4fcf2673fb4492532`；`n8_base/`、`n8_candidate/` 保留实际参数、simout 和回执，`n8_compare/comparison.json` 保留全输出位门。单元/计数/缺依赖回执均在本目录；相关 batch 进程均自行退出，原交互 MATLAB 保留。

## 未完成

同 P 的 N256 baseline 和 candidate 均已实际完成：`n256_base/` 和 `n256_candidate/` 保留完整 P、原始 simout 及回执；`n256_compare/comparison.json` 记录 **全部实际输出变量逐位相同**。这次未插桩的单次顺序 baseline→candidate 的 `sim` 分别为 **363.2439 / 326.0978 秒**，约减少 10.2%；一次配对不能证明可重复的速度分布。实际256码频谱由比较后的 baseline 数据计算：SNR 107.249369、SNDR 106.913367、SFDR 118.614808 dB，THD −118.194717 dBc，ENOB 17.467337 bit；源 P 的 DAC τ=1 ns，多个噪声/失配项关闭。

奇异/近奇异名义网络可能因减少重复求解而减少 MATLAB 告警次数，该边界未关闭；候选只完成一组 N8 与一组 N256，仍不得直接部署或称稳定加速、完整异常语义。三个 batch 进程顺序退出后临时任务已移除，原交互 MATLAB PID27628 保留。
