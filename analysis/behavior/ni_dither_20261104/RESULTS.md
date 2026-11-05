# 零幅 dither 与非理想覆盖摘要：隔离函数测试

2026-11-04 在 Windows MATLAB R2024a 的现有 PID 27628 会话执行 `test_ni_candidate`，未加载主 SLX，也未运行 Simulink。候选和测试独立于生产源码；结果只表示函数级测试通过。

- 零幅 dither：普通路径可准备；启用训练/收集的零幅配置按已声明条件拒绝。前后端 dither 设置不一致的负例被拒绝。
- NI 摘要：按实际参数重算并检查有限增益、有限采样建立、失配等；采样 τ=Inf 表示保持，不计作有限建立。OU OFF 的两种 CT 分段及 bridge 向量形状、OU ON 原有约束等在函数测试范围内检查。
- 旧/新默认参数及部分前端和 RA 纯函数状态对照通过；这不等于完整图形模型、所有状态或真实历史 P 已逐位通过。
- MATLAB 回执 `matlab_receipt.json` 状态 passed，`controller.log` 中记录实际测试 PASS；task-owned MATLAB path 和全局 RNG 检查通过。只针对测试缓存做处理，未重启 MATLAB；临时计划任务已移除，原任务未变。

候选补丁 SHA-256 `32414a8a16efd91b40a0a06e85b27a15f0414ddb33b0ac8b7f6d7b84133c4abe`，测试 SHA-256 `8a643e63a645d8f5519a9be3e0681227dbbd7e1cb88608c915113764891947b3`；完整隔离快照 `candidate_test_snapshot.zip` SHA-256 `5a376643b15dcfa4962d51c2101ad8c627f9b598d66c11741a9cca99fe715c2d`。

## 隔离主图 N8

Windows PID 27628 使用当前主图副本（SHA `d4e7fc99…4a6a0`）、本候选六文件和真实历史 N8 P 实际运行。默认案的 **32 路 timeseries、3 个根输出、RAW、最终码和时间全部逐位相同**；结果与对比清单位于 `n8_sandbox/`。`default_simout.mat` SHA 为 `caaf2361b7833dad64ca970731df8ffb8388d8258cf847cefe7177e16287d346`，候选 source ZIP SHA 为 `55d25f1bc13197fa04765f354454bfe499078152345886d1c20000f9b87730d8`。

之后同步开启模拟/数字 dither 但把幅度设为 0，实际再运行 N8：RAW、码、时间与全部观察值数值相同；仅 `front_log` 的 336 个浮点数存在 +0/−0 的位型差异，其余日志和根输出逐位相同。不得称零幅案完全逐位相同，也没有自行放宽比较标准。`zero_simout.mat` SHA 为 `3193155ac98505aafc33d7fe5c244d6d68de8e5d1a4ebf6b2a68d83e69846bdc`。两次 N8 只验证短记录，不产生频谱或 DNL/INL。

首次隔离项目构建漏掉四个配置辅助文件，主图仿真前报 `NI8:sourceHash`，现场见 `failed_n8_preflight/`；从真实 N8 source.zip 重建新副本后才完成上述两次运行。原始输入和结果未覆盖，任务 path/cwd/RNG 记录恢复，隔离模型和临时任务已关闭。

## 生产接入及正式入口验证

三份真实历史 P（N256、RA OU OFF、RA OU ON）经候选实际参数入口均直接接受；重新准备后，除 NI 摘要外的 P 按 `isequaln` 相同。见 `historical_p_compat_receipt.json`；这是函数级检查，不等于三个配置均完成新主图仿真。

六个候选源码已安装到 Mac 和 Windows 工作版本，逐项哈希与清单一致。安装前 Mac 六文件备份为 `production_before.tar.gz`，Windows 备份/替换日志在 `D:/Temp/SAR20NIINSTALL_20261104_qfhxXr/`；六次文件替换并非整体原子事务。隔离快照中的旧频谱文件没有覆盖当前 `f567aab4…` 版本。

安装后正式 `SAR20('run')` 实际完成 factory N8：`production_n8_run/` 是 Windows `behavior_af9806da-1b90-4e91-8d64-d4af792ffb3e` 的镜像，8 文件两端 SHA 一致。与安装前 `behavior_0a3cc913…` 的同一保存 P 和 SLX 比较，32 路 timeseries 的 Time/Data、3 根输出、RAW/码/时间全部逐位相同；实际仿真 24.8736 s。新 source.zip 的109项与当次 manifest 逐项 SHA 一致，其中六个 NI 源和频谱源均为当前安装版本；完整比较见 `production_smoke/comparison.json`。RNG、path、cwd 检查通过，主图未保存；旧 latest 指针保留于 `production_smoke/latest_before.json`。

正式烟测第一版 wrapper 漏掉路径比较 helper，在加载模型/创建 run 前报错；实际错误保留 `failed_live_preflight/`，第二版使用新任务目录继续完成，未覆盖旧错误。N8 不能提供频谱或全范围 DNL/INL。

比较器噪声候选与已部署 NI 的资格门及共同配置文件仍需单独融合和验证，不能将其视作已开启的非理想。

参数说明已在 Mac 与 Windows 更新：分别保留旧版 `PARAMETERS.before.md` 和 `PARAMETERS.windows_before.md`；Windows 旧文档原本缺少 RA OU 一行，已按当前源码补上。两端文档的证据路径按本机位置分别书写，不能用文件哈希相同作为同步标准。
