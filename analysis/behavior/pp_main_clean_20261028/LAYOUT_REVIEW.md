# 140306 相对 6319 的布局差异和最小恢复候选

只读解析 6319 主图与 140306 `as_run_SarPPClean.slx` 的原始 SLX XML；没有执行 MATLAB、SATK 或画布操作。坐标是模型各自层级的 `[left top right bottom]`；表中路径省略模型名。140306 as-run SHA `b2c7491416a0629b10fa5cc9c1b8f1db3f34b6bbf9154babec2076ce7aed12c7`，原主图 SHA `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6`。

## 原有块的 8 处变化：根 1 处、内部 7 处

| SID | 原层级路径 | 6319 原 Position | 140306 Position |
|---:|---|---|---|
| 105 | `/EventStep` | `[460 80 1360 300]` | `[400 170 450 220]` |
| 109 | `/EventStep/Event` | `[40 1008 70 1022]` | `[155 493 185 507]` |
| 137 | `/EventStep/CodeLog` | `[1595 610 1685 640]` | `[940 130 1030 160]` |
| 416 | `/EventStep/Transport/PinTransport` | `[145 241 200 274]` | `[145 243 200 277]` |
| 422 | `/EventStep/PublicEn` | `[495 1000 610 1030]` | `[360 355 475 385]` |
| 423 | `/EventStep/ActualTime` | `[440 898 470 912]` | `[260 338 290 352]` |
| 435 | `/EventStep/PairedReference` | `[1205 275 1255 315]` | `[1310 325 1360 365]` |
| 442 | `/EventStep/PairedRefLog` | `[1320 330 1410 360]` | `[1410 330 1500 360]` |

EventStep 从 900×220 缩为 50×50。140306 控制器日志记录多次 SATK `incremental` autolayout，和位置变化相吻合；仅凭这些证据不指定每个块究竟由哪一步移动，也不能推断线形或文字没有遮挡。

## 新增的 13 个块：没有 6319 旧坐标

| SID | 140306 路径 | 140306 Position |
|---:|---|---|
| 453 | `/EventStep/Transport/RxFault` | `[255 283 285 297]` |
| 454 | `/EventStep/BankOwnerState` | `[720 248 755 282]` |
| 455 | `/EventStep/BankOwner` | `[830 335 885 380]` |
| 456 | `/EventStep/BankCommand` | `[570 409 625 441]` |
| 457 | `/EventStep/NoDrainAck` | `[695 410 760 440]` |
| 458 | `/EventStep/PublicCode` | `[975 273 1005 287]` |
| 459 | `/EventStep/PublicValid` | `[1075 258 1105 272]` |
| 460 | `/EventStep/PublicMeta` | `[1315 258 1345 272]` |
| 461 | `/EventStep/BankCodeValidLog` | `[1175 250 1265 280]` |
| 462 | `/EventStep/BankMetaLog` | `[1415 250 1505 280]` |
| 463 | `/Code20` | `[500 173 530 187]` |
| 464 | `/CodeValid` | `[500 228 530 242]` |
| 465 | `/CodeMeta` | `[580 203 610 217]` |

若只恢复上表8个旧块，根三输出 SID463–465 会落在恢复后的 EventStep 轮廓内；SID461 的矩形会与恢复后的 SID435 重叠。纯矩形检查得到4处交叠，不包含名称、注释、连线和折点。

## 仅 `configure Position` 的12项候选

在新任务专属副本上，先以 `model_read` 确认上述 SID、父层级及当前 Position；不可编辑原证据或 current。按以下三个作用域分别调用 SATK `model_edit`，参数为这些单行 JSON 文件内容，`layout_mode='incremental'`：

- `root`：[ops_root.json](/tmp/sar20_independent_140306/ops_root.json)，恢复 SID105，并将新增 SID463/464/465 分别移至 `[1450 128 1480 142]`、`[1450 183 1480 197]`、`[1450 238 1480 252]`。
- `blk_105`：[ops_blk_105.json](/tmp/sar20_independent_140306/ops_blk_105.json)，恢复 SID109/137/422/423/435/442，并将新增 SID461 移至 `[1175 205 1265 235]`。
- `blk_393`：[ops_blk_393.json](/tmp/sar20_independent_140306/ops_blk_393.json)，恢复 SID416。

这12项均只改 `Position`，不包含 connect、delete、replace、solver、P、DecodeP 或状态修改。4个新增块的建议位置已对恢复后的旧块矩形和其他新增块矩形做离线不相交检查；这不是线路/文字视觉验收。仓库 SATK 声明的 layout mode 只有 full/incremental，实际自动布局可能再次移动其他块，必须读回；不可假定 configure 自动保持全部布局。

## 实际验收门

1. 每个 scope 的每次 `model_edit` 之前/之后保存 `model_read`、返回值及 `model_check`，失败留 partial。回读 8 个旧坐标和4个新增候选坐标，并核其他既有块 Position 未被改变；实际画布检查导线、端口、注释和文字遮挡，坐标合格不等于视觉合格。
2. 与140306 as-run比较 SID/名称/类型、所有非 Position 属性、solver 配置和全部361条源端口→目的端口；触发必须保持 `111.y2 → 105.trigger`，Clock `450.y1 → 105.u3`；BankOwner的 state 单一回路 `454.y1 → 455.u1`、`455.y1 → 454.u1` 与其 InitialCondition/SampleTime 必须不变，根 code/valid/meta 及 RX fault 所有端口不变。
3. 同一保存 P/DecodeP/TrainCaptureFile、旧源绑定和同一输入计划上编译并运行 OFF N8，保存新图/P/simout/source；对140306及133342 factory_base、factory_off 的原30路分别比较 Time/Data 类型、shape、位；对140306另比较两条 Bank valid/meta 和根 Code20/Valid/Meta。核12条ready及ID4–11原码/时刻/valid，失败停止。
4. 仅上述位置、画布、结构及真实日志门均通过，才可把布局结果作为后续主图接入候选。此提案不提前宣称已修复任何视觉问题，也不证明 Bank ON、新fault或N256。
