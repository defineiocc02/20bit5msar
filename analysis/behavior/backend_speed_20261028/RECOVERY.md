# 141949 外层回执误判：任务结束后的定向恢复门

本文件是静态核对和人工操作方案，**不是任务已结束或恢复已执行的证据**。不修改旧回执、不重跑 A/B。唯一实际任务为 `D:/Academic/Projects/sar20m1/SAR20/runs/az_probe_20261028T141949Z`，已提交控制器 PID 27628。外层已归档代码 SHA `33df57c0460b9af65cfb456f77ec254dd89400759e33034658790361a69cf601`，冻结 ZIP SHA `3ba1b23d7e92d25801769d4c4796cc89db934ebe311400fdf6e43fe06e4b8a38`。

## 实际路径和误判

| 项目 | 相对任务目录的实际路径 | 用途 |
|---|---|---|
| 最外层回执 | `receipt.json` | 保留原样；可能错误标为 `unsafe_native_cleanup_preserved` |
| v4 wrapper 回执 | `validation/entry_receipt.json` | 校验 native 已启动、退出标记及 wrapper 清理 |
| 真正的 native 回执 | `validation/validation/receipt.json` | 仿真阶段、原生位门、模型/RNG及 native 清理 |
| v4 wrapper 退出标记 | `validation/entry_cleanup_armed.flag`、`validation/entry_emergency_cleanup.txt` | 作业完成后均应不存在 |
| native 退出标记 | `validation/validation/cleanup_armed.flag`、`validation/validation/emergency_cleanup.txt` | 作业完成后均应不存在 |
| 独立 missing 的标记 | `validation/validation/missing_dependency/missing_path_armed.flag`、`missing_path_unrestored.txt` | 本次 AB未执行 missing；如意外存在，停止审查 |

提交的最外层脚本错误检查 `validation/receipt.json`，并在第一层查找 native 的 armed/emergency；因此它的 `native_cleanup_confirmed=false` 不能单独证明 native 清理失败，也不能被直接改成成功。根 wrapper 没有保存其入口前的完整 `oldPath`；外层 `az_job.m` 的 `D:/Temp/SAR20Az/jobs` 是公共作业路径，**不属于本次恢复对象**。

## 只有以下条件全部满足才执行定向恢复

1. 从同一任务 `status.json`/`events.jsonl` 和 controller.log 确认实际命令已返回，且控制者核该进程仍为 PID 27628、没有其他活动 MATLAB 作业；不能依据 PID 或早期 N8回执单独推断结束。先镜像原始回执、MAT/SLX、日志与 ZIP，并记录其 SHA。
2. 读取上述正确的两层回执。`validation/entry_receipt.json` 应为 `backend-validation-wrapper/v4`、`mode=ab`、`status=native_returned`、`native_started=true`、`native_cleanup_confirmed=true`、`environment_cleanup=complete`，其 cleanup 验证应为 verified，所有 native 标记检查应通过且全为不存在。以磁盘再独立确认两层全部 armed/emergency（含 missing 标记）均不存在。
3. 真正 native receipt 应显示 stage `finished`、状态 `backend_scratch_M8_N8_N256_complete_pending_missing_and_independent_review`、`environment_cleanup=complete`；实际 N8/N256 case 和 30路、全 ready RAW/码/时间位门需逐项核对，不能用最外层错误状态代替。`missing_dependency` 仍为 `pending_separate_process`，不冒充通过。若 native 失败、标记残留、回执未完成或字段不一致，保留现场并按原错误处理，不执行以下清理。
4. 同一 PID 下，所有已加载 model stopped、`SarLookup` 不存在；`SarAdc` 路径为当前主图、stopped/clean，文件 SHA 为 `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`；native 必须报告主 P/DecodeP/TrainCaptureFile 与运行前一致、RNG不变、profiler前后off。以实际只读查询再核 `which/inmem`：三个 `behavior_backend_sfun` / `behavior_backend_stage` / `behavior_backend_step` 应分别解析到当前 `current/src/physics`，无候选同名缓存；`validate_backend_native`、合同/缺依赖验证器也不得残留。任何异常先停。
5. 以实际路径条目和 inmem 精确检查任务入口 `D:/Temp/SAR20Az/sar20_backend_validation_native_v4/entry/run_backend_validation_v4.m`；文件 SHA `8aaf83d1f00c0dfac7a84624dfd6f0e1f608d95d1bf9cd39b4870415b13e9e89`。若有任何同名缓存来自不同路径、函数被 `mislocked`、存在不止一个同义入口路径条目，或 session 工作目录/路径有后续改变，停止而不猜测。

## 最小处理动作（由唯一控制者在上述门通过后执行）

- 为**本次恢复**新建独立 receipt，先保存当前 `path` 完整字符串、`pwd`、`which(...,'-all')`、相关 `inmem('-completenames')` 路径、PID、三个旧回执的 SHA 和主模型身份；不覆写任何原始文件。
- 若 `run_backend_validation_v4` 确实仅从上述入口文件缓存且未锁，**只定向** `clear('run_backend_validation_v4')`，随即用 `inmem('-completenames')` 复查同名缓存为空；不清 `backend_validation_v4_entry_job`、`az_job`、三个模型函数、其他函数或 classes。若清理不成功，停并保留路径。
- 若目标 `entry` 路径经规范化仅出现一次，用 `rmpath` 移除**该条**；不修改 jobs 或其余目录、不调用 `restoredefaultpath`。比较操作前后路径元素，确认仅移除了该条，其他路径顺序不变；记录本次 `pwd` 未变、三个 backend `which/inmem` 未变，以及入口 `which -all` 的变化。路径若原本已无此条，不要无谓写 path。
- 写独立恢复结果/实测快照；只在该定向操作及上述身份均复核后继续。若存在实际操作前的独立完整 `oldPath` 快照，再做逐字节比对；否则只能称“移除了本任务入口并保持其他路径顺序”，不能称完整路径已与运行前逐字节相同。

不要重新提交原任务、改写其 `receipt.json`、触碰 Windows 已有其他任务或把该外层路径误判当成数值通过。独立 missing、故障注入和 N256 后验审阅仍按原项目门单独处理。
