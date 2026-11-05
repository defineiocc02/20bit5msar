# 可读性重构：第九批（behavior_holdout_result）

日期：2026-10-31。

## 本轮改动

**`current/src/calibration/behavior_holdout_result.m`**：81 → 114 行，多语句 8 → 0

冻结 holdout 评估：读实际 `RAW/code/reference`，比较冻结电压与码中心，不拟合、不调增益、不写系数。

### 保留了一处"两种读数"的设计说明

原注释只提到"pre-round voltage 和 code center"，现在写清了**为什么要两个都算**：

```
% TWO INDEPENDENT READINGS PER ROW
%   ev  pre-round frozen voltage  minus reference
%   ec  code centre (code-2^19)*LSB minus reference
% Comparing both catches a case where the frozen maths and the emitted integer
% code disagree even though either one alone looks plausible.
```

这是这个函数的核心检查逻辑，一个读数通过而另一个不通过时正是最值得报警的情形。

### 明确写出 gate 约定

```
% GATE CONVENTION
%   Predeclared gates apply to the pre-round voltage and to the code centre.
%   The FFT's DC-only +0.5 code convention is deliberately NOT used here
```

避免后来者以为漏了 FFT 的 +0.5 约定。

## 一次自我纠正

初版改写里我给两个 `assert` **补了自定义 error identifier**（`holdout:frozenFinite`、`holdout:logger`）。

Token 级比对立刻抓到这个差异——虽然只影响报错文案，但**严格说改变了错误路径的可观测行为**。
已回退，保持"只改格式"的纪律。回退后 **Token 级 296 == 296 完全一致**。

这个插曲说明：**Token 级比对不只是走形式，它真的抓到了我自己引入的行为差异。**

## 验证状态：诚实说明

| 检查 | 状态 |
|---|---|
| Token 级语句序列 | ✅ **296 == 296，完全一致** |
| 部署哈希 | ✅ 本地 == 远端 `5661394e…` |
| 运行时验证 | ❌ **未完成** |

**为什么运行时验证没做成**：

这个函数的前置条件极其严格，必须同时满足：
- `out` 是完成且无错的 SimulationOutput
- `P` 里 `frozen.enabled` 与 `training.reference.enabled` **同时为真**
- `C.lifecycle == 'frozen_for_holdout'`
- `limits` 含 `holdout_rms_limit_v`/`holdout_max_abs_limit_v`
- `opt`（即 `P.cal_cfg`）与 `P` 严格匹配
- record view 里 `reference_enabled && frozen_enabled` 都为真

全仓库只有 **3 个 run** 同时具备 reference 与 frozen。我三轮尝试：

1. 第一轮用猜的 `limits` 字段名 → `cases=0`（一个都没进来）
2. 第二轮找到真实调用点（`limits` 来自 `protocol.thresholds`）→ 脚本**静默崩溃无产出**
3. 第三轮加 try/catch 逐 run 捕获 → 仍**无产出**（疑似加载大 simout 时内存/超时）

**已知局限**：该文件的运行时行为**未做端到端验证**。
但改动是纯格式，Token 级已证明 296 条语句完全一致（含那次自我纠正后的复查），
部署哈希一致。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 296 == 296，完全一致 |
| 部署哈希 | 本地 == 远端 `5661394e…` |
| 模型 SHA | `f358f226…` 未变 |

## 十批累计

| 文件 | 行数 | 多语句 | 运行时验证 |
|---|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 | 245 run |
| `behavior_sample_explain` | 423→513 | 23→0 | 2 run |
| `behavior_sample_plot` | 454→508 | 32→0 | 1 run × 59 字段 |
| `behavior_spectrum` | 47→70 | 7→0 | 117 run |
| `behavior_record_view` | 69→129 | 8→0 | 245 run |
| `behavior_decode` | 87→109 | 6→0 | 7976 RAW 字 |
| `behavior_az_schedule` | 74→98 | 5→0 | 1920 组合 |
| `behavior_aperture_times` | 40→73 | 6→0 | 8688 组合 |
| `behavior_public_cal_fit` | 82→116 | 7→0 | 40 run |
| `behavior_holdout_result` | 81→114 | 8→0 | ⚠️ 仅 Token 级 |

**10 个文件，累计消除 120 处单行多语句。**

## 踩坑（新增 1 条）

15. **给 `assert` 补自定义 id 会改变错误路径行为**——Token 级比对能抓到，但如果不做 Token 比对就会漏掉。
    纪律：**"只改格式"就要真的只改格式**，连报错文案都不动。
