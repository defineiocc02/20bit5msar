# 模型结构图（Simulink 离线可视化）

> 给「打开 `SarAdc.slx` 却看不懂结构」的人看的。**[点这里直接打开交互图](sar20_model_map.html)**（单文件 HTML，双击即可，无需服务器、无需联网、无需 MATLAB）。

---

## 1. 这是什么

把当前**唯一生产模型** `current/models/SarAdc.slx` 当作 ZIP + XML 直接解析，把真实的子系统层次、块、信号连线、块内中文注释、原始坐标、S-Function 绑定源码，渲染成一张可以逐层进入的交互图。

| 项目 | 值 |
|---|---|
| 来源模型 | `current/models/SarAdc.slx` |
| 模型 SHA-256 | `91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e` |
| 解析结果 | 14 个子系统 / 290 个块 / 203 条连线 |
| S-Function | **33 个 M-S-Function 块**，指向 **16 个不同 `FunctionName` 入口**（同一入口会被复用，如 `behavior_wiring_sfun` × 9）；16/16 已解析到 `current/src/**/*.m` |
| 源码 | 108 个 `.m` / 10,372 行 |
| 事件日历 | 73 个事件 / 48 组唯一时刻（0–90 ns） |
| UnitDelay | **整图 6 个**，其中 **Adc 内 3 个**才是模拟状态 owner |

**证据层级：L0 静态解析。** 它证明「SLX 里有哪些块、怎么连、注释写了什么、S-Function 指向哪个 .m」；**不证明**模型能编译、能跑、时序正确、视觉与原图一致，也不等于任何仿真或验收结果。

---

## 2. 四个页签怎么用

| 页签 | 内容 |
|---|---|
| 🗺️ **模型框图** | 按 SLX 原始 `Position` 坐标还原布局并归一化；双击子系统进入，↑ 返回；拖动平移、滚轮缩放；点任意块，右侧显示类型、SID、端口、中文注释、绑定的 `.m`、上下游连线；左侧搜索可跨全部 14 个系统搜块名 / S-Function / 注释 / 源码路径 |
| 📄 **源码地图** | 108 个 `.m` 按目录分组，显示定义函数、绑定的 S-Function 块、静态词法近似的 `calls / called_by`（**可能有注释噪声，仅作导航**，不是 MATLAB 依赖关系分析） |
| ⏱️ **事件时间轴** | 0–90 ns 的 73 个事件按 `[tick, priority]` 排布，点事件看 `tick / priority / index / bit`；下方 4 张卡片给出状态 owner、6 阶段执行顺序、易读错点、时刻边界 |
| 🧭 **怎么读这个工程** | 一句话抓住全图、建议阅读顺序、**6 阶段真实执行顺序**、调试入口、证据边界 |

颜色：蓝=子系统，橙=S-Function，红=UnitDelay，绿=输入/输出口，灰=常数/时钟，浅蓝=其他运算块。

---

## 3. 重新生成

```bash
cd <repo root>
python3 analysis/model_map/build_model_map.py
```

只读输入：`current/models/SarAdc.slx`、`current/src/**/*.m`、`current/src/control/behavior_calendar.m`、`template.html`。
产出：`model_map.json`（机器可读结构）、`sar20_model_map.html`（把 JSON 内嵌进模板的单文件）。

- **不加载模型、不调用 MATLAB、不仿真、不修改任何生产文件。**
- 时间轴**不是手工抄录的时刻表**：`build_events()` 解析 `behavior_calendar.m` 的 `add(...)` 语句，展开 `for k=a:b` 循环与 `if m<7,add(...);end`，由源码生成事件；源码形状变化时断言会失败并中止，避免悄悄发出过期时间轴。
- 6 阶段执行顺序来自 [`docs/READ_GRAPH.md`](../../docs/READ_GRAPH.md)「依赖顺序与路径」表，写在 `COMPUTE_STAGES` 里并附来源说明。

---

## 4. 过程中核实的四处口径纠正

这几处是「看不懂」的常见来源，也是本图与旧文档措辞的差异，均已按当前 SLX 核实：

1. **UnitDelay 不是 3 个，是 6 个。**
   Adc 内 `SampleCharge[148]` / `RaCtState[149]` / `SarState[150]` 是三个**模拟状态 owner**；另有 `BankOwnerState[454]`（EventStep）、`TxRxState[415]`（Transport）、`ReferenceHistory[418]`（RefQueue）三个数字/仪器记忆。
   `docs/READ_GRAPH.md §44` 的原话是「**ADC 内**只找三个状态 owner」，不能读成「整图只有三个」。

2. **`[353] / [48] / [51]` 是状态向量宽度，不是 Block SID。**
   `FE353 / RA48 / SAR51` 这些别名同样来自 353 / 48 / 51 个 double 的宽度。当前 SLX 里三个块的真实 SID 是 148 / 149 / 150。图中方括号一律表示 **SLX Block SID**，与文档里的宽度标注含义不同。

3. **左侧层次树是字母存储顺序，不是执行顺序。**
   `Adc` 的 7 个子系统在 SLX 里按字母序存放（`ChargeReturnRaReset` … `SarDecisionTracking`），已由 `derived.adc_tree_is_alphabetical = true` 核实。真实计算顺序是
   `SampleRaAdvance → DacCtFeedback → Sar1TrialRaCt → ResidueCtCompare → SarDecisionTracking → ChargeReturnRaReset`，
   第 7 个 `Diagnostics` 只读观察、不参与物理计算。**不要按树的顺序读。**

4. **S-Function 是 33 个块 / 16 个入口。**
   旧描述「16 个 S-Function」指的是 16 个不同 `FunctionName`；SLX 里实际有 33 个 M-S-Function 块。

另外，**92 ns guard、138 ns 传输收槽、transport ON 约 538 ns** 出自 `docs/READ_GRAPH.md §54` 的调度/解释页时间线，**不属于** `behavior_calendar.m` 的 0–90 ns 日历，因此时间轴图上不画，只在卡片里注明来源。

---

## 5. 明确不能声称的事

- 本图**不引用** `analysis/behavior/current_diagrams_20261104/*.png`：其 `metadata.json` 记录的 `source_model_sha256` 是 `d4e7fc99…` 的 Windows 私有副本，与当前生产模型 `91973cf7…` 不是同一哈希；该导出图自身还标记「待独立视觉复核」。
- 块内中文注释是 SLX 保存时写入的 `AttributesFormatString`，随 `apply` 更新；参数最终以 ModelWorkspace 里**已应用的 P** 为准，不以注释或参数工厂文本为准。
- 源码调用关系是正则词法近似，可能含注释噪声，只用来导航。
- 本图不产生任何新的性能结论，不改变 99.133 dB 基线的可归因性，也不构成论文复现证据。

---

## 6. 文件清单

| 文件 | 用途 |
|---|---|
| [`sar20_model_map.html`](sar20_model_map.html) | **交付物**：单文件离线交互图，直接用浏览器打开 |
| [`model_map.json`](model_map.json) | 机器可读结构（含 `meta.derived` 全部派生统计与 `compute_stages`） |
| [`build_model_map.py`](build_model_map.py) | 生成器：解析 SLX XML、扫描源码、解析事件日历、注入模板 |
| [`template.html`](template.html) | HTML/CSS/JS 模板，`/*__MODEL_DATA__*/` 为数据注入点 |

相关入口：[仓库中文 README](../../README.md) · [English README](../../README_EN.md) · [读图文字权威口径](../../docs/READ_GRAPH.md) · [零 MATLAB 调试面板](../local_debug/sar20_debug_report.html)
