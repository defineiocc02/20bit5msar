# 有限 DAC→RA：独立只读核验与晋升后入口

2026-10-28 最新回读：用户报告主图已晋升后，三组公开入口 N256 的实际 RAW 与 FFT 已独立回读，见 [N256_REVIEW.md](N256_REVIEW.md) 和 `n256_three_independent.json`。以下 083206 及四次旧归档说明保留各自的历史证据边界；本独立回读没有修改 `current`，没有运行 MATLAB 或 SSH。

2026-10-28 补充：`runs/az_probe_20261028T083206Z/receipt.json` 报告新 guard 绑定 scratch 的 off、enabled/零 τ、1 ns 三个 N8 均对其 022517/023003 原始仿真的 30 个 timeseries 做了 Time/Data 类型、维数和逐字节相等断言。回执中的三个 30 项名称清单与本机旧 simout 解析结果各自完全一致；其中含实际 ADC/RX、front/back/control 和 `dac_ra_pre_log`。本机在审阅时仅有新回执与 status，没有新 run 的 simout、P、SLX、candidate 原件，故这仍是**native 断言回执**，没有独立重算新旧数据；也未证实新输出不存在额外 logger 或内部完整 FE353/BK48 每一步状态。

此 job 把旧 saved P 直接 `assignin` 至 scratch ModelWorkspace 后仿真，并未执行公开 `SAR20('apply',P)` 与 `SAR20('run')`；新 helper 的 native `which` SHA 为 `9381e030d7c7a6c80c0acb9dc4d0b44d4b5f0de8f1eb56fb605c840e3add25cb`，不同于 024439 的 `0647b6…`。不可用本目录历史 `source_pins_024439.json` 默认为新 guard 的身份：应先获取并只读核对 083206 的实际 candidate 源、3 组 P/SLX/simout 及其 SHA，再单独 pin 新 helper。随后需要产品公开入口的真实 as-run 核验；N256 有限 τ 与更广覆盖也仍待实际记录。083206 receipt SHA `08b05051ec4babad14d8eccff87342ed7efe56b9f3761723eceec8475052273b`；本机审阅的 native job 文件 SHA `939ab4a394d77e7a9c533c3d096747f42283dadf1c3cd9fdbec920ff16e5054b`，不能据此冒充独立函数调用轨迹。

## 四次归档的实际覆盖

| 归档 | 可确认的范围 | 边界 |
|---|---|---|
| `runs/az_probe_20261027T020421Z` | 实际参数驱动核级 native 门；off/全零各 96 次 state48/obs8 位比较是 native 断言；20 个单区间 partial 可回读。原 `independent_native.json` 的 Decimal90 最大绝对 VX 差约 `2.776e-17 V`。 | 非 ADC 仿真；96 次逐条内部历史未保存、不能独立逐条重放；不包含完整事件环、RAW 或有限 AZ。等极点附近直接闭式差分会有消去误差，需看原报告的高精度结果。 |
| `runs/az_probe_20261027T022517Z` | scratch 加旧 FE→RaAdvance 第四输入边及 pre-CINC 观测；off 与 enabled/零 τ 的实际 N8 各与旧主图 29 路 Time/Data/class/shape 位一致。 | 实际 SLX 对话框仍是 `'advance',P.backend`，不是 024439 的新绑定；不能以 scratch 等同主图晋升。 |
| `runs/az_probe_20261027T023003Z` | scratch 实跑统一 `0.1/1/5 ns` 与 `Inf`，每组 8 条 RX ready、ID/epoch/valid=1；实际 48 组时轴和 ADC→RX RAW6 核对通过。新的条件式独立 expm 最大差依次为 `2.026e-15/1.890e-14/1.232e-14 V`；Inf hold 为 0。 | 以实际 FE 两端点反推单指数目标，仅检验 RA 耦合、不是独立 FE 物理真值；未设置新的数值容差或宣布解析通过。Inf 是不建立负例，即使 valid=1 也不是有限建立性能或覆盖。无独立逐次比较器计数历史、无 committed-reset 状态历史。 |
| `runs/az_probe_20261027T024439Z` | scratch 的 RaAdvance 对话框改用 `behavior_dac_backend_parameters(P)`；原生 compile 和 stale binding、训练、frozen、注册 bench 的拒绝门有真实回执。 | `ADC_simulation_run=false`；与 023003 的有限 τ ADC 仿真不是同一次执行，不能拼成带新绑定的仿真通过。024439 保存的对应 10 个候选源 pin 在 `source_pins_024439.json`。 |

023003 的 5 个物理候选源与 024439 同名源 SHA 一致；绑定 helper 首次出现在 024439，其保存源码与实际绑定 gate 源相同。两归档没有独立保存每个调用函数的 MATLAB `which` 追踪，pin 表仅证明保存源内容身份。

## 本目录中的实际回读

`verify_native_actual.py` 复用原有独立 Decimal90 算法、只读重算 020421 的 20 个 partial，输出 `native_020421_reread.json`，不覆盖原独立报告。`scratch_off_vs_legacy_n8.json`、`scratch_zero_vs_legacy_n8.json`、`scratch_0p1ns_n8.json`、`scratch_1ns_n8.json`、`scratch_5ns_n8.json` 和 `scratch_inf_hold_n8.json` 均读取上述真实 as-run MAT、SLX 和 P；文件中 `checks_passed` 仅对应列出的 IO、时序和位比较门，`promotion_accepted` 固定为 false。`legacy_n256_reader_check.json` 对历史主图 N256 做自身基线回读，验证读取器、实际 256 条 RAW/时轴和独立 FFT；这不是有限 DAC N256，也不是晋升候选回归。该历史运行的独立 FFT 为 SNDR `109.827136 dB`、ENOB `17.951352`，只对应原先关闭 DAC 建立的那一次记录。

对一份临时复制的 scratch 数据，仅为了测试将 ID 5 的 valid 改为 0：程序退出码为 1，输出仍保留 8 条记录和该 1 条 invalid，真实 `simout.mat` 哈希未变。对旧 N256 主图以有限 DAC 候选模式调用时，因缺少旧 FE→RaAdvance 输入 4 实边而退出码 2。这两项分别是读取器负例测试，不是新的 ADC 仿真。

## 将来核验实际晋升 run

`verify_as_run.py` 只读：原始 `simout.mat` 的实际 logger、保存 `parameters.mat`、as-run `SarAdc.slx`、summary/source ZIP/manifest，完整通过后还将 `selected.mat` 与实际 ready RAW/code/time 位对照。JSON 仅输出到 stdout，错误输出到 stderr；退出码 0 为脚本所列检查通过、1 为记录/valid/summary 不通过、2 为结构或不支持的输入。脚本本身不会给出晋升验收结论。

先使用同 N、同 ID/epoch、同输入及开关的真实旧基线验证晋升后的 off 和 enabled/全零位门；有限点再使用同 N 的实际 off run 作基线。以下 `NEW_*` 和 `BASE_*` 必须替换成实际 run 路径，不能直接照搬历史 N8 当有限 N256 结果：

```sh
python3 analysis/behavior/finite_dac_review_20261028/verify_as_run.py \
  --expect off --source-pins analysis/behavior/finite_dac_review_20261028/source_pins_024439.json \
  --run runs/NEW_OFF_N8 --baseline runs/BASE_N8 > /tmp/sar20_off_n8_readback.json

python3 analysis/behavior/finite_dac_review_20261028/verify_as_run.py \
  --expect finite --source-pins analysis/behavior/finite_dac_review_20261028/source_pins_024439.json \
  --run runs/NEW_FINITE_N256 --baseline runs/NEW_OFF_N256 > /tmp/sar20_finite_n256_readback.json
```

`--expect zero` 检查 enabled/全零，`--expect hold` 仅检查全 Inf 不建立负例，不做 FFT。若实际候选源经过后续审阅而有意变更，应先记录新的证据及 pin；现有 pin 不符即停止，不能自动用当前文件替换。pin 不覆盖其他配置、入口源或运行时实际函数解析。脚本依赖 Python 的 `numpy`、`h5py`、`scipy`；本机这次使用已有 `/private/tmp/codex_schur_h5deps`，该临时路径不保证长期存在，脚本未安装或升级任何环境。

脚本限定 transport on，N8/N256，AZ/校准/训练/frozen/dither off；比对真实 48 个 ADC 组、ADC raw_latch 和晚到 RX group49（ID+2），不将两种 ready 混为一谈。新图必须保留原生边、UnitDelay/Trigger 清单和配置项；只容许新增 FE→RA 及可选 pre-CINC 观察边。P 差异限 DAC 元数据/τ、派生 NI 和观察开关，源 pin、RX 实际 valid 和必要的 ID/epoch 不满足即拒绝。48 组及 12/8/7 是事件 token 清单，不能充当独立硬件计数器证据。

仅 N8 开启完整实际 pre-CINC tap、统一 τ 且线性 RA 时才报告两个实际事件端点之间的独立矩阵指数差值；未开启探针或 N256 默认仅存尾点时明确标记未记录。所有浮点差值原样列出，不引入分析容差、不宣称模拟节点连续包络或闭环设计通过。N256 FFT 仅在全部实际记录有效且满足原项目已有相干门时计算；这不是 INL/DNL、PVT、硅或论文完整性能验收。
