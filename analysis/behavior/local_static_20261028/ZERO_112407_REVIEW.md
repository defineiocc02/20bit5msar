# 112407 零点两端：逐事件独立回读

实际 0 V 旧预检与新 `−LSB/256 = −30.517578125 nV` 两个端点，在固定 ID4、四次实际预热下分别输出：

| 端点 | 最终 RAW `[D1,D2,DT]` | valid | code20 |
|---|---|---:|---:|
| 0 V | `[1040,2374,42]` | 1 | 524289 |
| −30.517578125 nV | `[1039,3417,42]` | 1 | 524285 |

两端均为 transport off，实际 ADC RawReady 与 record-ready 同在 `0.88625 µs`；ID0–4 各有真实 48 组事件，五次 RAW 均 valid。已有 0 V 的 full/capped 9 路时间、数据、class、shape 位门再次读回，新点保存的 9 路与旧点时间和事件完全对齐；两套 source manifest 的 87 个文件内容相同、模型快照 SHA 一致。

| ID4 相对 CNV | 真实事件和首次分歧 |
|---:|---|
| 0 ns | front 采样值 0 vs −30.517578125 nV。BackLog VX 已有 `0` vs `4.31e−49 V` 的极小尾迹；不能把它当此次新比较导致的显著 RA 差。 |
| 12.5 ns | coarse_latch/fine_prepare，两侧 trial 均为 1040；front vres 为 0 vs `−30.517578128 nV`。 |
| 15 ns | 首次 fine_decide 后实际 D1raw 为 1040 vs 1024；这是第一级细判决写位的首次分歧。比较位由 D1 写位反推，Compare1 单独输出没有保存。 |
| 16.25 ns | 后续反馈/prepare 的 trial 首次分开，为 1048 vs 1032；此处 vres 约 −64.000000 vs +63.999969 mV。 |
| 31.25 ns | ra_start，最终 D1 下的 front Qres 为 `0` vs `+0.217211292614 pC`，对应 vres 为 0 vs `+7.999969482 mV`；需区分后续 RA 建立和此前 D1 判决。 |
| 43.75 ns | d2_prepare，实际 BackLog VX 为 0 vs `0.239176359 V`，VY 为 0 vs `0.186250247 V`。 |
| 47.5 ns | D2raw 首次分开，为 2048 vs 3072；最终 D2 为 2374 vs 3417。 |
| 86.25 ns | raw_latch，得到上表两个 valid RAW 与最终码。15 ns 起 `code_log` 的中间变化尚未 ready，不能当作已提交有效码。 |

以最终实际 public RAW 和保存 `P.digital` 权重独立重建**名义数字贡献**如下；这些贡献不是直接保存的逐事件 D1/D2/DT 分支日志，也不是模拟节点电压。

| 端点 | D1 贡献 | D2 贡献 | DT 贡献 | 名义重建电压 |
|---|---:|---:|---:|---:|
| 0 V | 0 µV | +15.625 µV | −11.71875 µV | +3.90625 µV |
| 负端点 | −8000 µV | +7984.375 µV | −11.71875 µV | −27.34375 µV |

两项重建电压差为 −31.25 µV，即 −4 名义 LSB；不能仅凭这个差额把全部误差归因于单一模拟模块，也不能把端点间隔内的三个中间码称为已证缺码。窗口内 `−30.517578125 nV < Vin < 0` 没有实测数据，当前没有该窗口的新 DNL 或 INL。

零点的 P 是 112407 从已 pin 的工厂和源码重建；110315 的零点预检没有另存原生 as-run P。此重构 P 与负点保存 P 只差输入/前端 offset 和相应 `xFE0`，但不能将其说成独立保存的旧 as-run P。新点每次保存 9 路 timeseries，未保留完整 SimulationOutput/ErrorMessage；仿真无错和 SimulationInput 覆盖来自 native 回执。四次预热也不证明一般稳态、全局单调性或 PDK/硅片性能。

逐字段首次变化、哈希和 RAW 重建见 [independent_112407.json](independent_112407.json)，SHA-256 `735eb402c282301158fbb70ad81d5ef9e273d1fee42c6d33bde8af0aac8e79ee`；可用 [verify_112407.py](verify_112407.py) 只读重算。未操作 Windows 或修改 current。
