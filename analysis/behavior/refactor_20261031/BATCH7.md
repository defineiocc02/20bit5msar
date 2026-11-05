# 可读性重构：第七批（behavior_aperture_times）

日期：2026-10-31。

## 本轮改动

**`current/src/frontend/behavior_aperture_times.m`**：40 → 73 行，多语句 6 → 0

这是**确定性按键哈希**实现：给定 CNV 时刻与物理 slice ID，算出每片的实际孔径时刻。
全程无 RNG 流推进，所以结果可完全复现。

### 拆开了混在一起的哈希实现

原 `normal_key` 和 `mix32` 把多步运算压在一行（`x=bitxor(x,bitshift(x,-16));x=mod(...)`），
现在每步一行，并写清：

- **域分离**：`(seed,lane,id,epoch,slice)` 五元组各自经 `mix32` 折叠，任一组成变化都会改变全部结果
- **Box-Muller**：两个独立均匀量来自同一混合态；`+0.5` 位移保证 `u,v` 严格落在 `(0,1)` 内，`log`/`cos` 不会碰到边界
- **顺序不可重排**：三轮 xor-shift / multiply

### 函数头也重写了

明确区分 **common key**（seed,id,epoch,lane 'COMM'）与 **local key**（额外加物理 slice 1..18, lane 'LOCL'），
并强调 **DEM 顺序不参与 local jitter 的键控**——只有物理 slice 索引有意义，不是旋转后的位置。
关闭路径也写清了：`p.enabled=false` 时完全绕过加法，`ta` 严格等于标称时间（含 signed zero / roundoff 影响）。

## 验证：Token 级 + 分片穷举

**Token 级**：
```
old statements=82  new statements=82
identical: True
```

**运行时穷举**（分三片跑，因为一次性跑完全矩阵会超时）：

| 分片 | 覆盖 | 组合数 | 结果 |
|---|---|---:|---|
| 1 | `enabled=false`，全维度 | 5 760 | **0 差异** |
| 3 | `enabled=true`, `common_sigma>0` | 2 880 | **0 差异** |
| 补充 | `enabled=true`, `common_sigma=0` 子集 | 48 | **0 差异** |
| | **合计** | **8 688** | **0 差异** |

维度包括：4 个时基 × 3 组 slice ID 集合 × 4 个 seed（含 0 与 2^32-1 边界）×
2 种 slice skew × `common/local` 两个 sigma 各自开/关 × 5 个 sample_id × 3 个 epoch。

比对三个输出 `ta` / `common_s` / `local_s` 全部逐元素相等，并同时比对错误路径 identifier。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 82 == 82，完全一致 |
| 运行时穷举（8 688 组合） | **0 差异** |
| 部署哈希 | 本地 == 远端 `efc2c123…` |
| 模型 SHA | `f358f226…` 未变 |

## 八批累计

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

**8 个文件，累计消除 105 处单行多语句。**

## 踩坑（新增 1 条）

13. **一次性跑超大全矩阵会超时且静默失败**：初版把 11 520 组合塞进一个函数，
    任务结束后没有产出任何 JSON（连 `try/catch` 都没走到，疑似 MATLAB 被强杀）。
    **对策：把穷举拆成小分片，每片单独跑、单独产出结果文件**。
    这轮最终用 3 个分片 + 1 个补充子集完成，每片都能独立确认。
