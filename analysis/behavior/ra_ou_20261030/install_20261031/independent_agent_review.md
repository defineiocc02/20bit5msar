# SAR20 RA 噪声核生产接入 — 独立只读复核报告

**复核结论：PASS（8/8 必检项通过；必检失败项：无）**

- 工程根：`/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020`
- 复核日期：2026-10-31（Asia/Shanghai）；状态快照：2026-10-31 01:20 CST（镜像文件 mtime 01:19:26）。
- 复核方式：**只读**；全部用 Python 标准库（`hashlib`、`json`、`zipfile`、`os`、`re`）重算；未联网、未安装包、未调用 MATLAB。
- 复核范围：任务给定的 8 组必检项；另做收据/指针/v3 快照/模型条目的额外一致性核对。
- 独立声明：未将 `RESULTS.md`、`independent_offline_review.json` 或任何既有 PASS 结论作为判据；下列数值均为本次从磁盘重算。

> **时间线提示（重要）**：复核期间检测到工程状态被并发更新。`state/applied_config.json` 与 `current/models/SarAdc.slx` 在安装烟测后的 17:12:03Z 为 `b1b7…`/`b246…`（与 `smoke_receipt` 一致，复核开始时仍实读到），随后在 17:17:57Z 被更新为 `4d39…`/`dee65…`；同时新增两条 N256 运行（17:15:16Z OFF、17:16:33Z ON）。当前状态仍是 **N8 factory OFF**（RA OFF、Bank OFF、config 与 N8 OFF `parameters.json` 完全相等），第 6 项按当前文件仍 PASS；但安装烟测 receipt 的 `b246…`/`b1b7…` 已不是当前文件。详见第 6、9、10 节。

## 0. 判据口径

- 文件 SHA-256 为**原始字节**的 SHA-256；`source.zip` 条目 SHA 为**解压后条目字节**的 SHA-256。
- 期望的 109 源码清单构造：`BASELINE.json` 的 105 条 → 8 个 `replace` 路径改写为 `MANIFEST.target_sha256` → 加入 4 个 `add` 路径的 target，共 109 条。
- Windows 侧 `source_manifest.json` 使用反斜杠路径；比较时统一 `\`→`/`，zip 条目名本身为正斜杠。
- 判定值只取冻结清单（MANIFEST/BASELINE/BACKUP）与磁盘产物；`MANIFEST_PRE_REFREEZE.json`、`candidate_manifest_v3_snapshot.json` 只用于额外追溯。

### 关键身份值（本次实算，状态快照 01:20 CST）

| 对象 | SHA-256 |
| --- | --- |
| MANIFEST.json | `d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1` |
| BASELINE.json | `0d9dbb7132357967d0d9a930911436898d038b3f2d2c1e38fb3f088dd9356642` |
| MANIFEST_PRE_REFREEZE.json | `6c1691a46f05d042ceb9a44a79189e08c241c7a2ed10a8393a3785c857f56894` |
| candidate_manifest_v3_snapshot.json | `9ed7eeae767fa399c300a18c8127f5a7bef57ec776301ad54239e0a935cd399c` |
| backup/BACKUP.json | `7c25d418dcf41f663a4b3816df362b12616935a9b965ceaca05cda6e16429611` |
| state/applied_config.json（当前） | `4d391993b7b3e31107d222617fb77be06b16cd1b72d7ce0aa76d88a621ae4a2d` |
| current/models/SarAdc.slx（当前） | `dee65dacf4c0adcc5897aceb8549fc9df8dd66227c30c0a1374a631350cdeea5` |

安装烟测后的历史值（17:12:03Z，已被 17:17:57Z 更新覆盖）：`state/applied_config.json` = `b1b7396a2c99e6ecaba04dba878c2050e3b4f6e0776d57de5fdc953352c8eb45`；`current/models/SarAdc.slx` = `b246548885ed9d76ef8851ef80719125149e18be5ce1e42e4843662f8b4071ee`。复核开始时实读两者一致；当前文件已变为上表值。

## 1. 12 个安装文件与 8 个替换项原始文件

### 1.1 12 个安装文件的磁盘 SHA vs MANIFEST.target_sha256

| # | 路径 | 操作 | MANIFEST target_sha256 | 磁盘实际 SHA-256 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `config/adc_parameters.m` | replace | `949a7c863755debe859e9f4ead028ddf3ea7f4c3d1d98699083a0ce76170e540` | `949a7c863755debe859e9f4ead028ddf3ea7f4c3d1d98699083a0ce76170e540` | **PASS** |
| 2 | `current/src/model/behavior_applied_note.m` | replace | `6288c5d0f1290f2547761fe9b47f1ae011f8365f8bcb8f60ec744746a3e8b882` | `6288c5d0f1290f2547761fe9b47f1ae011f8365f8bcb8f60ec744746a3e8b882` | **PASS** |
| 3 | `current/src/model/behavior_dac_backend_parameters.m` | replace | `8d5bea354ed6b9cb9b5b4f3d72239eca087a22d3675d430360797b952e530947` | `8d5bea354ed6b9cb9b5b4f3d72239eca087a22d3675d430360797b952e530947` | **PASS** |
| 4 | `current/src/model/behavior_prepare_configuration.m` | replace | `62d944cd3bfcc3c52bdfe44b668463d9ad394e20980d5e2a820262a076734222` | `62d944cd3bfcc3c52bdfe44b668463d9ad394e20980d5e2a820262a076734222` | **PASS** |
| 5 | `current/src/model/behavior_ra_noise_guard.m` | add | `bd70171d64b49809df7e0ecf8040d6fe5ef6aa5626d65ef2faebec5aeab47ebd` | `bd70171d64b49809df7e0ecf8040d6fe5ef6aa5626d65ef2faebec5aeab47ebd` | **PASS** |
| 6 | `current/src/physics/behavior_backend_parameters.m` | replace | `e69617933908ac9e9b69b4cc66014c45df5b4d8042a4217117569a84a4390256` | `e69617933908ac9e9b69b4cc66014c45df5b4d8042a4217117569a84a4390256` | **PASS** |
| 7 | `current/src/physics/behavior_backend_sfun.m` | replace | `c1bd84e0f603079d8a94df80365e45409fc3525903e9efab68e453b2b2eadde0` | `c1bd84e0f603079d8a94df80365e45409fc3525903e9efab68e453b2b2eadde0` | **PASS** |
| 8 | `current/src/physics/behavior_backend_stage.m` | replace | `4d80a4e3e4bbbc0acb5522c6bbe5e26ca8f7ce81f0008088feb122de3c72be72` | `4d80a4e3e4bbbc0acb5522c6bbe5e26ca8f7ce81f0008088feb122de3c72be72` | **PASS** |
| 9 | `current/src/physics/behavior_backend_step.m` | replace | `b6fd6bcd73b8673542a93537a34f5a65d81a49d1a58ef6914230638fb26f4d75` | `b6fd6bcd73b8673542a93537a34f5a65d81a49d1a58ef6914230638fb26f4d75` | **PASS** |
| 10 | `current/src/physics/behavior_ra_noise_validate_backend.m` | add | `fe4ecb477708ac06903d1328d32c2c886e78892dfe9dcbe9fdefdad23d54ea9f` | `fe4ecb477708ac06903d1328d32c2c886e78892dfe9dcbe9fdefdad23d54ea9f` | **PASS** |
| 11 | `current/src/physics/sar20_ra_keyed_normal.m` | add | `a6c3117481258767394cd0d330c4c88a8d3222bf4f4ed86510cd92d5e39b796f` | `a6c3117481258767394cd0d330c4c88a8d3222bf4f4ed86510cd92d5e39b796f` | **PASS** |
| 12 | `current/src/physics/sar20_ra_ou_increment.m` | add | `3787a6f1d0b163ceb50f2a85ba705c564e4a50bfa01c5da005709913b7aecc1d` | `3787a6f1d0b163ceb50f2a85ba705c564e4a50bfa01c5da005709913b7aecc1d` | **PASS** |

**结果：12/12 PASS。** 另核对 `release_20261031/files/` 下 12 个候选源，12/12 与 `target_sha256` 相同，说明安装文件与发布包候选源字节一致。

### 1.2 8 个 replace 项的原始文件 vs MANIFEST.baseline_sha256

| 路径 | MANIFEST baseline_sha256 | backup/files 实际 SHA-256 | 同时等于 BASELINE.json | 判定 |
| --- | --- | --- | --- | --- |
| `config/adc_parameters.m` | `010a416c40f3c358e2fd0a7d207e1f773a87adfbd8db4e5c871d829f0ef41308` | `010a416c40f3c358e2fd0a7d207e1f773a87adfbd8db4e5c871d829f0ef41308` | 是 | **PASS** |
| `current/src/model/behavior_applied_note.m` | `d2b2492c14eae0dd7535ffe1e93be406cc9a512328af0e3bd971408b9a056b3b` | `d2b2492c14eae0dd7535ffe1e93be406cc9a512328af0e3bd971408b9a056b3b` | 是 | **PASS** |
| `current/src/model/behavior_dac_backend_parameters.m` | `9381e030d7c7a6c80c0acb9dc4d0b44d4b5f0de8f1eb56fb605c840e3add25cb` | `9381e030d7c7a6c80c0acb9dc4d0b44d4b5f0de8f1eb56fb605c840e3add25cb` | 是 | **PASS** |
| `current/src/model/behavior_prepare_configuration.m` | `2cb3729d59409cad60e305c87a9dbae798fc10d5f133f70580b3d48ad186b722` | `2cb3729d59409cad60e305c87a9dbae798fc10d5f133f70580b3d48ad186b722` | 是 | **PASS** |
| `current/src/physics/behavior_backend_parameters.m` | `c76dfa78b45a5ecc9eb078d1646847d79b95982d60eae55e2f0dd9458eae1778` | `c76dfa78b45a5ecc9eb078d1646847d79b95982d60eae55e2f0dd9458eae1778` | 是 | **PASS** |
| `current/src/physics/behavior_backend_sfun.m` | `4fbc0e7b356aea1b90d0c54348982c2a44fef05117650d4c0e05793aa8ecf807` | `4fbc0e7b356aea1b90d0c54348982c2a44fef05117650d4c0e05793aa8ecf807` | 是 | **PASS** |
| `current/src/physics/behavior_backend_stage.m` | `8178bb79505b90308e1c84a48e73e3d42bd4e104304f2dfd08a59a48d65d99a4` | `8178bb79505b90308e1c84a48e73e3d42bd4e104304f2dfd08a59a48d65d99a4` | 是 | **PASS** |
| `current/src/physics/behavior_backend_step.m` | `140f08d0f3084f27d21d46b72584cfbf94c984b992fd6d115412278265ce6e14` | `140f08d0f3084f27d21d46b72584cfbf94c984b992fd6d115412278265ce6e14` | 是 | **PASS** |

**结果：8/8 PASS。** `backup/files/` 中 8 个原始文件的 SHA 全部等于 MANIFEST 的 `baseline_sha256`，也全部等于 `BASELINE.json` 对应值；三方一致。

## 2. 105 个基线文件：97 个未替换 + 4 个新增

### 2.1 97 个未替换基线文件

- 基线 105 条，8 条为 `replace`，剩余 **97** 条逐文件重算。
- 按目录分布：`SAR20.m` 1 条 + `config/` 5 条 + `current/` 91 条 = 97 条。
- 结果：**97/97 与 BASELINE.json 相同，0 缺失、0 不符。**

### 2.2 4 个新增文件

| 路径 | target_sha256 | 磁盘实际 SHA-256 | 在 BASELINE.json? | 在 BACKUP.json? | backup/files 有实体? | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| `current/src/model/behavior_ra_noise_guard.m` | `bd70171d64b49809df7e0ecf8040d6fe5ef6aa5626d65ef2faebec5aeab47ebd` | `bd70171d64b49809df7e0ecf8040d6fe5ef6aa5626d65ef2faebec5aeab47ebd` | 否 | 否 | 否 | **PASS** |
| `current/src/physics/behavior_ra_noise_validate_backend.m` | `fe4ecb477708ac06903d1328d32c2c886e78892dfe9dcbe9fdefdad23d54ea9f` | `fe4ecb477708ac06903d1328d32c2c886e78892dfe9dcbe9fdefdad23d54ea9f` | 否 | 否 | 否 | **PASS** |
| `current/src/physics/sar20_ra_keyed_normal.m` | `a6c3117481258767394cd0d330c4c88a8d3222bf4f4ed86510cd92d5e39b796f` | `a6c3117481258767394cd0d330c4c88a8d3222bf4f4ed86510cd92d5e39b796f` | 否 | 否 | 否 | **PASS** |
| `current/src/physics/sar20_ra_ou_increment.m` | `3787a6f1d0b163ceb50f2a85ba705c564e4a50bfa01c5da005709913b7aecc1d` | `3787a6f1d0b163ceb50f2a85ba705c564e4a50bfa01c5da005709913b7aecc1d` | 否 | 否 | 否 | **PASS** |

**结果：4/4 PASS。** 4 个新增文件当前都存在且 SHA=target；均不在 105 条 BASELINE 中，也不在安装前 `BACKUP.json` 清单/实体中，符合“只在新状态出现”。

## 3. 两次运行的 source_manifest.json 与 source.zip

| 运行 | manifest 条数 | 唯一路径 | 缺失 | 多余 | SHA 不符 | zip 条目 | zip 字节不符 | zip SHA 与 summary 一致 | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OFF | 109 | 109 | 0 | 0 | 0 | 109 | 0 | 是 | **PASS** |
| ON | 109 | 109 | 0 | 0 | 0 | 109 | 0 | 是 | **PASS** |

- 期望清单 109 条，两案 `source_manifest.json` 均为 **109 条 / 109 个唯一路径**；**缺失 0、多余 0、SHA 不符 0**。
- `source.zip` 两案均 **109 个条目 / 109 个唯一名**；逐条目解压字节 SHA **0 不符**；zip 文件 SHA 与 `summary.source_zip_sha256` 一致。
- 两案 `source_manifest.json` 字节相同（SHA `fc7cb2a026cb989418c8e643eebd2e18f255aafad87632917271aa895e4ca1ac`）；`source.zip` SHA 不同（OFF `8cb0fc9ae2240d73b29d9e3cc7f979d41318c0a3bd9a7c875b640343d5f6e1f3`，ON `ce8ac39fbfdeaa69770c6d3364f28152bf9878ebdcb55d796d9bd7a08a0aca94`）；zip 容器字节不同，但 109 个条目解压字节一致；容器层差异未进一步归因。
- **结论：PASS。**

## 4. 两次 run 的 summary.json 与 parameters.json

### 4.1 summary.json

| 运行 | status | simulation_completed | records | sample_ids | global_rng_unchanged | all_ready_count | invalid_count | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OFF | complete | True | 8 | [4, 5, 6, 7, 8, 9, 10, 11] | True | 12 | 0 | **PASS** |
| ON | complete | True | 8 | [4, 5, 6, 7, 8, 9, 10, 11] | True | 12 | 0 | **PASS** |

- 两案 `status=complete`、`simulation_completed=true`、`records=8`、`sample_ids=[4,5,6,7,8,9,10,11]`、`global_rng_unchanged=true`；`raw_words`/`code20` 各 8 条，`record_ready_summary.invalid_count=0`。

### 4.2 parameters.json

| 运行 | 顶部 ni.ra_noise | backend.ni.ra_noise | backend.ra_noise.sigma_vx_rms | seed_u64 | bank.enabled | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| OFF | <absent> | False | <absent> | <absent> | False | **PASS** |
| ON | True | True | 0.001 | 20261030 | False | **PASS** |

- OFF：顶部 `ni` **无** `ra_noise` 键（等价 false），`backend.ni.ra_noise=false`；`bank.enabled=false`。
- ON：顶部 `ni.ra_noise=true`、`backend.ni.ra_noise=true`、`backend.ra_noise.sigma_vx_rms=0.001`、`seed_u64=20261030`；`bank.enabled=false`。
- **结论：PASS。**

## 5. summary.model_sha256 与运行目录 SarAdc.slx

| 运行 | summary.model_sha256 | SarAdc.slx 实际 SHA-256 | 字节数 | 判定 |
| --- | --- | --- | --- | --- |
| OFF | `c2c46299b88f1bb5d3ebeb2f02da96f1a0289d9908f51f7089515e5752ba044c` | `c2c46299b88f1bb5d3ebeb2f02da96f1a0289d9908f51f7089515e5752ba044c` | 459039 | **PASS** |
| ON | `41f8b0dfc6b6dd943e0f1f081cddfed4be08977be0598f6eb630da4fae7f5ab8` | `41f8b0dfc6b6dd943e0f1f081cddfed4be08977be0598f6eb630da4fae7f5ab8` | 460988 | **PASS** |

**结果：OFF/ON 两案均 PASS**；`summary.json` 的模型哈希与同目录 `SarAdc.slx` 快照逐字节一致。

## 6. 当前生产状态：state/applied_config.json 与 current/models/SarAdc.slx

> 本节按 **01:20 CST 当前文件**判定；安装烟测时的 `b1b7…`/`b246…` 历史值见顶部提示与第 10 节 O5。

| 对象 | 实际值 | 判定 |
| --- | --- | --- |
| `state/applied_config.json` → `model_sha256` | `dee65dacf4c0adcc5897aceb8549fc9df8dd66227c30c0a1374a631350cdeea5` | **PASS** |
| `current/models/SarAdc.slx` 实际 SHA-256 | `dee65dacf4c0adcc5897aceb8549fc9df8dd66227c30c0a1374a631350cdeea5` | **PASS** |
| `config.backend.ni.ra_noise` | False | **PASS** |
| `config.bank.enabled` | False | **PASS** |
| `config` 与 OFF run `parameters.json` 逐项相等 | True | **PASS** |

- `applied_config.model_sha256` = `current/models/SarAdc.slx` 实际 SHA = `dee65dacf4c0adcc5897aceb8549fc9df8dd66227c30c0a1374a631350cdeea5`，**一致**。
- 配置里 RA 噪声为 **OFF**（`backend.ni.ra_noise=false`；顶部 `ni` 无 `ra_noise` 键），Bank 为 **OFF**（`bank.enabled=false`）。`applied_config.config` 与 **N8 OFF run** 的 `parameters.json` **完全相等**（递归逐项相等）；`N`、`first_id`、`seed` 也一致（N=8、first_id=4、seed=20261020）。
- 额外核对：当前模型与 N8 OFF run 的 `SarAdc.slx` 都是 38 个 zip 条目；**36 个条目 CRC 完全相同**，仅 `metadata/coreProperties.xml`（modified `2026-10-30T17:11:39Z`→`2026-10-30T17:17:57Z`，revision `1.275`→`1.281`）和 `simulink/blockdiagram.xml`（AutoIncrement `1.275`→`1.281`）不同；`simulink/modelWorkspace.mxarray`、`simulink/systems/system_root.xml` 等其余条目与 N8 OFF 相同。即当前模型是 N8 OFF 语义的另一次重存，**不是**逐字节等同 N8 OFF run 快照。
- **结论：PASS（按第 6 项要求）；同时记录了“当前模型 vs N8 OFF run 非逐字节相同”的事实。**

## 7. ID4 交叉核对

| 运行 | ID4 在 sample_ids 的位置 | raw 前三段 | 期望 raw | code20 | 期望码 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| OFF | 0 | [1900, 3283, 234] | [1900,3283,234] | 963400 | 963400 | **PASS** |
| ON | 0 | [1900, 3285, 131] | [1900,3285,131] | 963404 | 963404 | **PASS** |

- OFF：`raw_words[0] = [1900, 3283, 234, 4, 1, 1]`，前三段 `[1900, 3283, 234]`；`code20[0] = 963400`。
- ON：`raw_words[0] = [1900, 3285, 131, 4, 1, 1]`，前三段 `[1900, 3285, 131]`；`code20[0] = 963404`。
- 两项均与任务给定期望逐项相同。**结论：PASS。**
- 数据来源说明：上述 raw/code 取自 `summary.json` 的 `raw_words`/`code20`；`selected.mat`、`simout.mat` 为 MATLAB 7.3 MAT/HDF5，标准库无法解析，因此没有从这两个二进制文件独立反解 raw/code（见第 11 节）。

## 8. backup/BACKUP.json

| 项目 | 实际值 | 判定 |
| --- | --- | --- |
| 清单条数 | 115 | **PASS** |
| 唯一路径数 | 115 | **PASS** |
| 每条均带 64 位十六进制 sha256 | True | **PASS** |
| backup/files 实体缺失数 | 0 | **PASS** |
| backup/files 实体 SHA 不符数 | 0 | **PASS** |
| BASELINE 105 条在 backup 中且 SHA 相同 | True | **PASS** |
| 当前树中未覆盖且非 4 个新增的文件数 | 0 | **PASS** |

- 路径前缀分布：`SAR20.m` 1、`config/` 6、`current/` 101、`state/` 7 = **115**。
- `state/` 7 个文件：`state/SESSION_READY.json`、`state/applied_config.json`、`state/behavior_cleanup.json`、`state/behavior_release_receipt.json`、`state/dynamic_receipt.json`、`state/logging_receipt.json`、`state/short_default_restored.json`。
- 105 条 BASELINE 全部包含在 backup 中，且 backup 记录值与 BASELINE 逐条相同（105/105）；当前树中除 4 个新增文件外，`SAR20.m`、`config/`、`current/`、`state/` 的所有文件都能在 backup 中找到（0 遗漏）。
- 115 个实体在 `backup/files/` 下均存在，逐文件 SHA 与 `BACKUP.json` 一致（0 缺失、0 不符）。
- `BACKUP.json` 自身 SHA `7c25d418dcf41f663a4b3816df362b12616935a9b965ceaca05cda6e16429611` 与 `BACKUP_RECEIPT.json` 的 `backup_manifest_sha256` 相同。
- **结论：PASS。**
- 跨主机差异（观察项）：`install_20261031/windows_BACKUP.json` 也是 115 条；与 Mac `BACKUP.json` 有 **114 个同名路径且 SHA 全同**。差异是 Windows 多 `current/src/analysis/.sar20_396aeb03f7dd4307a90b590bf6882649.tmp`，Mac 多 `current/.DS_Store`。两份备份不是逐路径镜像，但不改变 Mac `BACKUP.json` 对 current/config/state/SAR20.m 的覆盖与逐文件 SHA 判定。

## 9. 额外一致性核对（非任务必检项）

| 核对项 | 声明/预期 | 实算 | 判定 |
| --- | --- | --- | --- |
| INSTALL_RECEIPT.release_manifest_sha256 | `d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1` | `d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1` | **PASS** |
| BUILD.manifest_sha256 | `d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1` | `d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1` | **PASS** |
| BUILD.baseline_manifest_sha256 | `0d9dbb7132357967d0d9a930911436898d038b3f2d2c1e38fb3f088dd9356642` | `0d9dbb7132357967d0d9a930911436898d038b3f2d2c1e38fb3f088dd9356642` | **PASS** |
| BUILD.smoke_sha256 → sar20_ou_public_smoke.m | `5af30f4a7e4e6caf4570b4cd6252373a91937cb60e2bf285f63fbeaf4efa2210` | `5af30f4a7e4e6caf4570b4cd6252373a91937cb60e2bf285f63fbeaf4efa2210` | **PASS** |
| BACKUP_RECEIPT.backup_manifest_sha256 | `7c25d418dcf41f663a4b3816df362b12616935a9b965ceaca05cda6e16429611` | `7c25d418dcf41f663a4b3816df362b12616935a9b965ceaca05cda6e16429611` | **PASS** |
| MANIFEST.refreeze.previous_manifest_sha256 | `6c1691a46f05d042ceb9a44a79189e08c241c7a2ed10a8393a3785c857f56894` | `6c1691a46f05d042ceb9a44a79189e08c241c7a2ed10a8393a3785c857f56894` | **PASS** |
| MANIFEST.validated_v3_manifest_sha256 | `9ed7eeae767fa399c300a18c8127f5a7bef57ec776301ad54239e0a935cd399c` | `9ed7eeae767fa399c300a18c8127f5a7bef57ec776301ad54239e0a935cd399c` | **PASS** |
| re-freeze 变更集 | 声明 2 源文件 + 1 测试 | 实算 2 源文件 + 0 增删；old/new target 逐条一致；测试 SHA 均匹配 | **PASS** |
| latest_behavior_run 指向的 run 与 summary SHA 自洽 | `D:\Academic\Projects\sar20m1\SAR20\runs\behavior_ad1aae9c-d99f-495e-847c-999f885b2d13` → `8015b03fbb480e694d16dbf4247a266eba8ffef622bae20bd881fa44fe24cfcc` | 新增 N256 ON run `behavior_ad1aae9c-d99f-495e-847c-999f885b2d13` summary `8015b03fbb480e694d16dbf4247a266eba8ffef622bae20bd881fa44fe24cfcc` | **PASS** |
| 12 个 target 在 release/files/ 的实体 | 12 条 | `True` | **PASS** |
| 12 个 validated_v3_sha256 → v3 快照 | 12 条 | `True` | **PASS** |

- `MANIFEST_PRE_REFREEZE` 与当前 MANIFEST 的路径集合相同，target 只有 `behavior_ra_noise_guard.m`、`behavior_ra_noise_validate_backend.m` 两条变化，与 `refreeze.changed` 完全一致（old/new target 逐条也一致）；`refreeze.changed_tests` 的 `sar20_ou_guard_selftest.m` 新 SHA `68905866…` 与磁盘一致。
- `runs/latest_behavior_run.json` 现在指向新增 N256 ON run `behavior_ad1aae9c-d99f-495e-847c-999f885b2d13`，其 `summary_sha256` 与该 run 的 `summary.json` 实算 SHA 一致；**不再指向 N8 ON run** `behavior_1fd9057b-cfd0-4166-a5ba-05f21927b19c`（N8 ON summary SHA 为 `8606a1bb58d8eade9983954d62efe7c9621fbf4513f3e4d0d6c2a10d187d692e`）。这是并发新增运行的结果，不改变 N8 两案的产物。
- 安装烟测 receipt 记录的 `restored_state_sha256=b1b7…`、`restored_model_sha256=b246…` 对应 17:12:03Z 的安装态；复核开始时实读一致，但当前文件已变为 `4d39…`/`dee65…`，故 receipt 已不对应当前文件（见 O5）。**不把这条写成当前 PASS。**
- 除 O5 的并发状态更新外，其余收据链、re-freeze 链、v3 快照、release/files 实体与测试 SHA 均可重算并 PASS。

## 10. 发现的不一致 / 观察项（不计入 8 项必检失败）

### O5（首要）. 复核期间状态被并发更新，当前状态 ≠ 安装烟测恢复态

时间线（UTC，来自文件 `utc` 字段与 summary `utc`；本机镜像 mtime 01:19:26）：

| 时刻（UTC） | 事件 | 关键值 |
| --- | --- | --- |
| 17:12:03Z | 安装烟测后恢复 OFF：`state/applied_config.json` / `current/models/SarAdc.slx` | state `b1b7396a…`、model `b2465488…`、revision 1.278 |
| 17:15:16Z | 新增 N256 OFF run `behavior_fba2d7a5…`（不在本任务两个 N8 run 之内） | N=256、records=256、RA OFF、model `b5a9edee…` |
| 17:16:33Z | 新增 N256 ON run `behavior_ad1aae9c…`（不在本任务两个 N8 run 之内） | N=256、records=256、RA ON、model `3b1c316d…` |
| 17:17:57Z | `applied_config.utc` 更新为当前值；`current/models/SarAdc.slx` 重存 | state `4d391993…`、model `dee65dac…`、revision 1.281；N8 factory OFF |
| 01:19:26 CST | 本机镜像写入上述 state/model/latest 文件 | `latest_behavior_run` 改指 N256 ON `ad1aae9c…` |

- 当前 `state/applied_config.json` 的 `config` 与 **N8 OFF** `parameters.json` 完全相等（N=8、first_id=4、seed=20261020），RA OFF、Bank OFF；当前 `current/models/SarAdc.slx` 与 N8 OFF run 的 SLX **36/38 个 zip 条目 CRC 相同**，差异只在 `metadata/coreProperties.xml`（17:11:39Z→17:17:57Z、revision 1.275→1.281）与 `simulink/blockdiagram.xml`（AutoIncrement 1.275→1.281）。因此当前仍是 **N8 factory OFF**，第 6 项按当前文件仍 **PASS**。
- 但安装烟测 receipt 的 `restored_state_sha256=b1b7…`、`restored_model_sha256=b246…` 只对应 17:12:03Z 的安装态；当前文件是 17:17:57Z 的新态。若验收要求“当前状态必须等于安装烟测恢复值”，则当前不成立；若只要求“当前 RA OFF、Bank OFF、model_sha=current”，则成立。**这是复核期间的外部并发动作，本报告不把它判为安装失败，但必须如实记录，需 owner 确认这是预期的 N256 后续 restore。**
- 两个指定 N8 run（`9b3a15ae…`、`1fd9057b…`）的 `summary.json`、`SarAdc.slx`、`source.zip` 等未被这次更新改写；其文件 mtime 仍为 01:12。

### O1. MANIFEST 的 `difference_from_v3` 字段不完整

v3 快照 `candidate_manifest_v3_snapshot.json` 的 SHA 为 `9ed7eeae767fa399c300a18c8127f5a7bef57ec776301ad54239e0a935cd399c`，等于 MANIFEST 声明的 `validated_v3_manifest_sha256`；12 个文件的 `validated_v3_sha256` 也全部等于 v3 快照对应值（12/12）。但从 v3 到当前 target 有 **5 个文件变化**，其中 **4 个**的 `difference_from_v3` 是空字符串：

| 路径 | validated_v3_sha256 | target_sha256 | difference_from_v3 |
| --- | --- | --- | --- |
| `config/adc_parameters.m` | `a0f88f7c0dfd7818a8f5a1c80becea9ac8539a612b374f342dd4b1abc83246f7` | `949a7c863755debe859e9f4ead028ddf3ea7f4c3d1d98699083a0ce76170e540` | 空字符串 |
| `current/src/model/behavior_applied_note.m` | `d2b2492c14eae0dd7535ffe1e93be406cc9a512328af0e3bd971408b9a056b3b` | `6288c5d0f1290f2547761fe9b47f1ae011f8365f8bcb8f60ec744746a3e8b882` | `conditional ON/zero annotation; OFF text unchanged statically; native graph test pending` |
| `current/src/model/behavior_prepare_configuration.m` | `c85ff526f8940f17c404e7c37d8db008ad68cf81619b99e8f70ca29cd3ce00d9` | `62d944cd3bfcc3c52bdfe44b668463d9ad394e20980d5e2a820262a076734222` | 空字符串 |
| `current/src/model/behavior_ra_noise_guard.m` | `59105b7c59a57795608e7ec6b7e2670a7420464415551a68481ba5ebd8ebcb53` | `bd70171d64b49809df7e0ecf8040d6fe5ef6aa5626d65ef2faebec5aeab47ebd` | 空字符串 |
| `current/src/physics/behavior_ra_noise_validate_backend.m` | `a8a649891fb0a2061afa7417063756a42bd4709bf18d6b7bd8447847680ca350` | `fe4ecb477708ac06903d1328d32c2c886e78892dfe9dcbe9fdefdad23d54ea9f` | 空字符串 |

MANIFEST 的 `only_post_v3_change` 散文为：`config comments; conditional applied-P label; ON-only backend NI/M8 validation and derived/check coverage/group/control guards; numeric OU state-update kernels remain byte-identical`。它覆盖了 config comments、applied-P label、ON-only NI/M8 validation、derived/check/coverage/group/control guards 与 OU 核不变，但没有在字段层面逐项对应上述 5 个文件；尤其 `behavior_prepare_configuration.m` 没有被点名。

**事实判定：这是清单元数据的自述不完整/不一致，不是安装哈希链失败。** 12 个安装文件、105 个基线、109 个源码、115 个备份的哈希判定均不受影响。若验收口径要求“v3 之后的每个变更都必须逐项记录”，需要 owner 补充 `difference_from_v3` 或说明；本报告不替其解释。

### O2. Windows 与 Mac 备份不是逐路径镜像

两份清单都是 115 条，114 个同名路径 SHA 全同；差异仅：Windows 多 `current/src/analysis/.sar20_396aeb03f7dd4307a90b590bf6882649.tmp`，Mac 多 `current/.DS_Store`。Mac `BACKUP.json` 自身满足第 8 项；但“Windows 备份 = Mac 备份”的说法不成立（只是内容高度一致）。Windows 备份实体不在本机，无法逐字节复核其 115 个文件。

### O3. 当前模型与 N8 OFF run 快照不是逐字节相同

`current/models/SarAdc.slx` 与 N8 OFF run 的 `SarAdc.slx` 同为 459039 字节、38 个 zip 条目、36 个条目 CRC 相同；差异只在 `metadata/coreProperties.xml`（时间戳/revision）和 `simulink/blockdiagram.xml`（ModelVersionFormat）。第 6 项只要求 `applied_config.model_sha256 == current`，该要求通过；第 7 项也不依赖此。若有人把“当前模型必须逐字节等于 N8 OFF run”当作额外验收条件，则这一条不成立；按给定 8 项，它不构成失败。

### O4. 状态字段仍为“pending”文案

`MANIFEST.json.status` 仍为 `frozen_preinstall_validated_pending_guarded_install`，`INSTALL_RECEIPT.json.status` 仍为 `installed_pending_matlab_smoke`。这是冻结/安装时的阶段字段，不是安装后状态；不影响哈希判定，但若作为“已完成”状态读取会产生歧义。

## 11. 我无法验证的事项

1. **MATLAB 实际执行与公开入口调用**：只能看到 `smoke_controller.log` 的一次 `run` 记录、`smoke_receipt.json` 和两个 run 目录产物；无法从磁盘证明这两个目录确实由该 MATLAB PID/公开入口在安装后生成。`run_path` 是 Windows `D:\Academic\...` 路径，本机看到的是镜像。
2. **MAT v7.3/HDF5 内容**：`simout.mat`、`selected.mat`、`parameters.mat` 均为 MATLAB 7.3 MAT/HDF5；按“只用 Python 标准库”的限制无法解析。第 7 项的 raw/code 只从 `summary.json` 读取，未从 `selected.mat`/`simout.mat` 独立反解。已核对 `summary.config_sha256` 等于 `parameters.mat` 文件 SHA、`summary.selected_sha256` 等于 `selected.mat` 文件 SHA，但未解析其内部数组。
3. **20-bit 码的译码映射与模拟正确性**：未重跑 MATLAB，未验证 raw→code 的模型译码逻辑、模拟波形或噪声统计；只核对了记录值与给定值。
4. **v3 归档**：`MANIFEST.tested_v3_archive_sha256 = 9026cdab07b23652cba07f34bc059fa0205e87d73f746281181a9ed036013d1f` 对应的归档不在本机磁盘；只能验证 v3 manifest 快照的 SHA 与内容，不能验证该归档本身。
5. **Windows 备份实体**：只有 `windows_BACKUP.json` 清单，没有 Windows `D:/Temp/.../backup` 的 115 个文件；不能逐字节验证 Windows 侧备份。
6. **re-freeze 前的 MATLAB 合同测试**：`refreeze.preinstall_evidence` 中的 `guard_on`、`guard_off`、`guard_selftest`、`label_selftest` 只有 receipt 字段，未在本机独立复跑。
7. **安装态 `b1b7…`/`b246…` 的旧文件已被 17:17:57Z 更新覆盖**：复核开始时实读过并记录当时三项条件均满足，但现在无法对旧文件重新计算；只能依赖当次读数与 `smoke_receipt` 的 `restored_state_sha256`/`restored_model_sha256`。
8. **噪声/频谱/多 seed 统计**：未验证 PSD、SNDR/ENOB、多 seed 噪声统计或任何硅/PDK 结论；这些不在本次 8 项范围。
9. **权限/ACL/时间戳语义**：只核内容 SHA；未把文件权限、owner、mtime 当作判据，也未验证它们在两端镜像中的语义。

## 12. 最终判定

| 项 | 检查内容 | 实际值/规模 | 结果 | 判定 |
| --- | --- | --- | --- | --- |
| 1 | 12 个安装文件 SHA = MANIFEST.target_sha256 | 12/12 | **PASS** | **PASS** |
| 1b | 8 个 replace 原始 SHA = MANIFEST.baseline_sha256 | 8/8 | **PASS** | **PASS** |
| 2 | 97 个未替换基线仍 = BASELINE；4 个新增只在新状态 | 97/97；4/4 | **PASS** | **PASS** |
| 3 | 两案 source_manifest 109 条 SHA 一致；zip 条目字节一致 | 109/109；109/109 | **PASS** | **PASS** |
| 4 | summary 字段；OFF/ON parameters 的 RA/σ/seed/Bank | OFF 无/false；ON true/0.001/20261030 | **PASS** | **PASS** |
| 5 | summary.model_sha256 = run 的 SarAdc.slx | 2/2 | **PASS** | **PASS** |
| 6 | applied_config.model_sha256 = current；RA OFF；Bank OFF | model_sha `dee65…`=`dee65…`；state 文件 `4d39…`；OFF；OFF；config=N8 OFF | **PASS** | **PASS** |
| 7 | OFF/ON ID4 raw 前三段与码值 | [1900,3283,234]/963400；[1900,3285,131]/963404 | **PASS** | **PASS** |
| 8 | BACKUP 115 条、覆盖 current/config/state/SAR20.m、逐文件 SHA | 115；覆盖；115/115 | **PASS** | **PASS** |

**总判定：PASS。8/8 必检项通过，必检失败项为 0。**

非阻断观察项：**O5**（复核期间 17:17:57Z 的状态并发更新：当前 state 文件 `4d39…` / model 文件 `dee65…` 仍是 N8 factory OFF，第 6 项按当前文件 PASS，但安装烟测 receipt 的 `b1b7…`/`b246…` 已不对应当前文件）、O1（`difference_from_v3` 4 个空字段 + `prepare_configuration` 未点名）、O2（Windows/Mac 备份路径集差 1 个文件）、O3（当前模型与 N8 OFF run 仅元数据差异）、O4（pending 状态字段）。这些已如实记录，未替其解释；它们不属于任务给定的 8 项哈希/状态必检项，因此不改变 PASS 判定。若验收方把 O5 的“当前=安装烟测恢复态”、O1 的逐项追溯或 O3 的逐字节等同也列为硬性要求，需要另行裁定，本报告不能替 owner 宣布这些额外条件通过。

