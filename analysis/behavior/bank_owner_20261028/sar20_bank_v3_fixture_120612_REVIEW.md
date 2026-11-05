# BankOwner v3 原生 fixture 与资格工件独立复核

结论：120612Z 的原生**合成 fixture**通过，证据支持 v3 纯函数在被测场景的状态和公开数值逻辑；它没有绑定实际模型或真实资格，生产 `code_valid` 保持 false。资格 JSON 是历史 M8 行为仿真证据汇总，不自动授权同图 BANK。

- **冻结身份与测试范围**：120612Z 镜像 ZIP 内 frozen manifest SHA `5e0161e272190337510ed25e3c5c0cf4c9f85ef1102a3ad3e0238bf14cdaaec9`；6 个候选文件及 runner 的 SHA 与 manifest 一致，6 个候选文件也与原生回执一致；3 个公开解码依赖的回执 SHA 与训练源码归档一致。fixture 断言覆盖模拟 LOAD/QUALIFY/PUBLISH/RETIRE、命令重复/冲突、future ID、invalid0、错 epoch/跳号、合成 τ/双解码拒绝，及 no-ready/valid0 的 pre/pre/模拟提交/post 一致性。不同合成 h、epoch 1/2/3、DEM on/off 与公开参考计算也经过断言。证书、h、记录和 P 均为合成数据；这不是 Simulink 实际 Outputs/Update 接线、真实排空或真实资格测试。checkcode 仍有 3 条 ALIGN、18 条 ASGLU、1 条 NOCOMMA 提示。
- **运行时源边界**：wrapper 只强制验证 manifest 文件本身的 SHA；runner 记录候选 `which`/SHA，未在运行前按 manifest 对各源码 SHA 逐项 assert，也未运行后重核。这里的逐项匹配是对归档和回执的事后核验；公开依赖同路径的 MATLAB 缓存新鲜度未由 `which`/磁盘 SHA 证明。
- **失败、清理及 RNG**：120503Z 因 `sar20_bank_sha256` 已缓存而在 preflight 拒绝，未进入 fixture。失败后 wrapper 无条件 `clear` 六个候选函数名；120548Z 分项记录六名均未加载、未解析，不能说失败前的同名缓存被原样恢复，原缓存路径也未记录。120612Z 内层报告执行前后 RNG 相同；wrapper 报告 path 恢复、候选目录过滤后的缓存列表为空，主模型前后 SHA 均 `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`、stopped/clean。这些是原生回执，不是本次实时检查；wrapper 未独立证明完整工作区及所有同名依赖缓存状态。

资格工件 `/tmp/sar20_az/rx_long_calibration/pingpong_main_v1/qualification_rx1024_v3.json` SHA `91aa3245b12187c85ca89f337e4a766ead11d7e471b1f76b450b79634bf4b573`，与 120612Z ZIP 副本相同。其历史 train/freeze/evaluate/先前独立审计的哈希及 holdout 聚合指标一致；本次只读核对了训练 P、holdout P 和冻结缓存的**公共投影**：声明 profile 字段相等、plan 2056×8 相同，h SHA `a634c9…`，plan SHA `323658…`。文件声称训练独立 SVD 满秩 684；此轮没有重算 SVD。它没有包含实际认证签名或生成器源码 SHA，且状态为 `NOT_ACCEPTED`/activation none。

**不得扩写的声明**：当前生成器对旧 `selected.mat` 和 `public_holdout_result.mat` 进行 SHA 时会打开并读取文件字节；它不解码或将逐点值用于训练，但 `consumed_holdout_rows_reopened=false` 不能解释为从未重新打开旧文件。若边界禁止任何旧 holdout 文件读入，应只引用已封存回执/审计的摘要。历史原生 `check_holdout_preimage` 曾对完整 P 做不透明 `isequaln`，包含物理字段；旧流程未把 actual C 用作拟合参考，但不能声称整条历史证明链从未比较过 actual C。

静态查看正在形成的 `sar20_pp_parameters.m`/`sar20_pp_step.m`：该路径按固定 Q JSON SHA 设置 `PINNED_REAL_RX_M8_QUALIFIED` 并允许 `code_valid=true`，没有走 v3 BankOwner 的分离训练/资格证书与可信 allowlist；Q 自述未来同芯片身份仍需独立绑定。两 slot 当前又被要求同一个 h SHA，只可证明不同版本的路由，不能证明不同系数的真实切换。不得仅据本 fixture 或该 JSON 开启有效码；须补可信来源/芯片绑定、实际 P 门及同图验证。现有 M8 资格也不适用于 M1。

原件：`runs/az_probe_20261028T120503Z/`、`...T120548Z/`、`...T120612Z/`。核验脚本 `/tmp/sar20_v3_fixture_qualification_audit.py` SHA `a088452e922b69d5df8b6e5a50947dce27e3ca78ec8360ed44d1524d4dc74e7c`；结果 `/tmp/sar20_v3_fixture_qualification_audit.json` SHA `bacaf9436191d45f2872965126de0b336b5d23b7731ba80ba9dc189fd8928300`。本次未重跑 MATLAB，未读取旧 holdout 逐点文件，未操作 Windows/current。
