# 可读性重构：第八批（behavior_public_cal_fit）

日期：2026-10-31。

## 本轮改动

**`current/src/calibration/behavior_public_cal_fit.m`**：82 → 116 行，多语句 7 → 0

全 684 参数、无正则化的**仅训练用**离线候选拟合。

### 最值得改的一行

原代码这一行把 `for` 循环和三个赋值塞在一起：

```matlab
for slot=1:8,j=F.slice_ids(row,slot);phase=F.dem_shift(row,slot)+1;counts(j,phase)=counts(j,phase)+1;end
```

这是**含循环体的多语句行**，调试器完全无法在循环体内单步。现在展开成正常循环块。

### 函数头重写成"顺序即契约"

这个函数的正确性很大程度上依赖**检查顺序**（先校验阈值 → 建特征 → n<684 提前拒绝 → 秩 → 条件数 → h 正性 → RMS）。原注释把这段散在几行里，现在列成 4 步：

```
1. thresholds validated first
2. features built; training sequence must be valid, consecutive, same epoch
3. n<684 returns an impossible-rank rejection BEFORE any reference value is read
4. rank, then condition number, then h positivity, then training RMS
```

第 3 条尤其重要：`n<684` 时**在任何参考值被读取之前**就返回。这是隐私/隔离上的设计（没有足够行数就不该碰参考数据），不写清楚会被误认为可以提前读。

## 验证：两层

**第一层：Token 级等价**
```
old statements=227  new statements=227
identical: True
```

**第二层：用真实保存数据跑**

从真实 `parameters.json` 构造合法的 public cfg（经 `public_calibration_config` 转换），
从真实 `summary.raw_words` 构造 raw 数组，然后跑两个实现：

| 阶段 | 覆盖 | 结果 |
|---|---:|---|
| 改完未部署 | **40 个真实 run** | **0 差异** |
| 部署后复验 | **40 个真实 run** | **0 差异** |

比对全部返回字段（含 `thresholds`/`public_config` 子结构、`state` 字符串、
全部 status 枚举），并同时比对错误路径 identifier。

## 一个诚实的说明：深层拟合分支没覆盖到

我尝试构造 684+ 行的合成训练集去触发 **SVD 之后的深度分支**
（秩不足 / 条件数超限 / h 非正 / RMS 超限 / DEM 覆盖不足），但两次都失败：

- 第一次：`publicCal:rawRange` —— 合成的 `sample_id` 超出 `plan_rows`
- 第二次：修正后**任务超时无产出**（684×684 的 SVD 计算量大，疑似被强杀）

**所以本轮验证只覆盖到"拒绝/边界"路径，没有覆盖真正进入 SVD 拟合的路径。**

但需要说明：本轮改动是**纯格式**（展开多语句 + 改注释），Token 级比对已证明
**227 条语句完全一致**，语义没变。40 个真实 run 的零差异是第二重佐证。
深层分支的未覆盖是验证的**已知局限**，不是已知缺陷。

若要补齐，需要单独跑一次长时间任务（684+ 行真实训练数据 + 允许几分钟 SVD）。
这已超出"低风险改进"的收益范围，故记录为待办而非本轮阻塞。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 227 == 227，完全一致 |
| 运行时（40 真实 run） | **0 差异** |
| 部署哈希 | 本地 == 远端 `c5b9508b…` |
| 模型 SHA | `f358f226…` 未变 |

## 九批累计

| 文件 | 行数 | 多语句 |
|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 |
| `behavior_sample_explain` | 423→513 | 23→0 |
| `behavior_sample_plot` | 454→508 | 32→0 |
| `behavior_spectrum` | 47→70 | 7→0 |
| `behavior_record_view` | 69→129 | 8→0 |
| `behavior_decode` | 87→109 | 6→0 |
| `behavior_az_schedule` | 74→98 | 5→0 |
| `behavior_aperture_times` | 40→73 | 6→0 |
| `behavior_public_cal_fit` | 82→116 | 7→0 |

**9 个文件，累计消除 112 处单行多语句。**

## 踩坑（新增 1 条）

14. **合成测试数据必须满足被测函数的前置约束**：`sample_id` 必须落在 `plan_rows` 内。
    第一次构造用 0..683 而某些 run 的 `plan_rows` 只有 32，直接被 `rawRange` 拒绝。
    应先扫描找到一个 `plan_rows` 足够大的 run，再按它的上限生成 id。
