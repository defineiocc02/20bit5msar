# 可读性重构：第十三批（behavior_transport_configuration）

日期：2026-10-31。

## 本轮改动

**`current/src/model/behavior_transport_configuration.m`**：85 → 125 行，多语句 4 → 0

推导传输层公共参数与初值，**不重建调度**。

### 函数头重写成四节

原文 10 行注释混着"它拥有什么/它不碰什么/ON 怎么办/OFF 怎么办"。现在分四块：

- **OWNS** — `enabled/core/public_en/startup_en/kind_by_group/log` 与唯一的 `P.xTX0`（97 doubles）。**故意没有 `transport.xTX0` 别名，也没有 RefQueue。**
- **NEVER TOUCHES** — `groups/calendar/cycles/stop/plan` 以及任何 FE/BK/SAR 状态。事件时序来自标准 Clock，**绝不来自 kind 表或样本 ID 算术**。
- **ON** — 重放一段有界的公开 EN 前史（结束在 -Ts 之前），再验证推导出的 epoch 等于 `P.epoch`。**隐藏 epoch 绝不被写进 RX。**
- **OFF** — 持有不透明的既有 finite-97 初值，缺失时用有限零。**Enabled 数字子系统不得执行，所以 OFF 完全不重放也不初始化内核。**

"绝不来自 kind 表或样本 ID 算术"这条尤其重要——这是这类传输层最容易写错的地方（用 ID 推时间看似方便，但那会把协议耦合进时序）。

### 给三处逻辑加了说明

- 分组 token 分类（`cnv`/`raw_latch`/`frame_ready` 互斥）
- 前史生成的三个步骤（`count`/`last`/`times`/`levels`），说明**末级电平取 `public_en`**，让前史收敛到本次 run 自己的协议而不是硬编码常数

## 验证

**Token 级**：初版比对报 3 条差异，追查后确认全部是**续行符 `...`**（我把过长的 `assert` 拆成多行）。用 `difflib` 做结构 diff 后确认：

```
old tokens=200 new tokens=203
insert: 3 处，全部是语法性的续行标记
```

**代码逻辑完全等价。**

**运行时**：利用"每个 run 的 `parameters.mat` 里存的是历史真实 P"，对 **25 个真实 P** 做对比：

| 阶段 | 覆盖 | 结果 |
|---|---|---|
| 改完未部署 | **25 个真实 P** | **0 差异，全部成功（err=0）** |
| 部署后 | 新版 vs 备份单例（transport ON） | `same: true`，路径不同 |
| 部署哈希 | 本地 == 远端 | `de7dae4c…` |

## 结果

| 检查 | 结果 |
|---|---|
| 结构 diff | 仅 3 处续行符，逻辑等价 |
| 运行时（25 真实 P） | **0 差异** |
| 模型 SHA | `f358f226…` 未变 |

## 十五批累计

14 个文件 + 本轮 1 个 = **15 个文件**，累计消除 **148 处**单行多语句。

## 踩坑（新增 1 条）

20. **Token 级比对对续行符会误报**：把长 `assert` 拆成多行会引入 `...`，在按语句切分的比对里被当成"新增语句"。
    **应对：用 `difflib` 做序列 diff，只关注插入/删除的真实内容**，不要只看计数。
