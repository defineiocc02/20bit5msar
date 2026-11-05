# RA 建立区间离线只读观察器

**状态：源码和列映射已静态核对；本观察器及测试草案尚未运行 MATLAB。** 现有 normal N8 tap 只记录 8 列 RA 观察量、7 列前端观察量等，没有 FE353/RA48 完整状态。本目录不能独立生成该 N8 的真实密集曲线。新 `physical_state_tap` 的 2015 列日志需要由另一个隔离观测运行实际产生，并证明其余原始日志与无新 tap 运行一致。

## 数学与随机边界

31.25 ns 同组先提交最后一位 `fine_feedback`，再处理 `ra_start`；后端进入线性 RA 工作状态。43.75 ns 是下一组首个 `d2_prepare`，两者之间没有原 ADC 事件。观察器从**31.25 ns 组所有动作后的唯一 FE/RA 状态**重新计算每个查询时刻：它复制实际 backend 参数，只将副本的 `ra_noise.sigma_vx_rms=0`，`ni.ra_noise` 仍保持原值，并保留 Ctop、finite-DAC、AZ 和源绑定的门禁。原 OU helper 在 sigma 为零时于 SHA 前直接返回，因此内点不生成 OU 键，也不推进 MATLAB 全局 RNG。

这给出的是“给定实际起始总 VX、没有区间内新增 OU 创新的确定性漂移”；在理想一阶 OU 新创新与过去条件独立的模型假设下，它也是该区间条件均值。对已固定 seed 的原始事件仿真，它不是已观测的 OU 连续轨迹，也不是 OU bridge。其 `t→t1−` 漂移极限通常不经过真实带 OU 创新的终点，不能把两者连线画成实测波形或真实突跳。观察器没有创造中间随机样本，也没有拟合常数指数。

实际 sigma、原始 `(seed, epoch, sample_id, t0, t1)` 和原状态仅用于重放**原终点的一次已有事件键**：same-key、同平台重新计算是无状态哈希，不推进全局 RNG。重放的 `RaAdvance` state48 和 obs8 均与新日志逐位相同，观察器才返回内点漂移。任意中间时间若直接以 OU ON 调用原 stage，代码会给 `[t0,t]` 生成不同键；重复同键可重入，但把区间拆成不同键并不满足原固定 seed 的逐路径可加性。

有限 DAC 目标不是终点常值：每个 t 都用原始 FE353 的 `B_c`、`B_target_c`、各段 τ 重新计算电荷驱动，并使用现有 AZ 解析演化。`start_qres_over_cf_v` 来自实际起点命令，`recorded_endpoint_qres_over_cf_v` 来自实际终点 obs8，不相互覆盖。旧 normal ID5 的既有事件记录显示两端 Qres/Cf 约 −261.910 mV 和 +51.235 mV；这只是旧日志的事件值，不能代称尚未取得的新 2015 列状态。

## MAT/Timeseries 列绑定

新 trace 的 `layout.json` SHA-256 `fab1aa95520b2e9af897cfe93e539083c8b3afbb8524bae5eedb574559393b31`，以下列号均为 MATLAB **一基、含端点**：

| 时间行与列 | 输入字段 | 原图来源与语义 |
| --- | --- | --- |
| 同行 1:2 | sample ID、event group | `blk_116.y1` 事件二元组；行时间取 Timeseries `Time` 的原 binary64 字 |
| 31.25 ns 行 1415:1767 | `fe_after_start353` | `blk_297.y3`，FE_final_next，SampleCharge UnitDelay 输入 |
| 31.25 ns 行 1960:2007 | `ra_after_start48` | `blk_297.y1`，RA_final_next，RaCtState UnitDelay 输入 |
| 43.75 ns 行 3:355 | `fe_old_at_stop353` | `blk_148.y1`，SampleCharge UnitDelay 输出 |
| 43.75 ns 行 1768:1815 | `ra_old_at_stop48` | `blk_149.y1`，RaCtState UnitDelay 输出 |
| 43.75 ns 行 1816:1863 | `ra_advance_stop48` | `blk_232.y1`，RaAdvance 在本事件、任何后续 due/commit 前的 next state |
| 43.75 ns 行 2008:2015 | `ra_advance_obs_stop8` | `blk_232.y4`，同一次 RaAdvance 的原 obs8 |

首两份 next 必须分别逐位等于下一事件对应的 old；事件行须相邻且 sample/epoch、源文件、完整 P 和原绝对时间相同。端点比较对象是 `RaAdvance`，不能拿 `RA_due_next`、`RA_trial_next` 或 `RA_final_next` 混充。完整 layout 见同目录 `layout.json`；状态/信号 tap 是已有模型信号的观察，不是模拟节点的额外状态。

## 接口与验收

在离线、无 SarAdc 模型加载的 MATLAB 进程中，先将本目录和冻结 candidate 的源码目录加入路径，再从**同一实际运行**读取其 P 和 `physical_state_tap`：

```matlab
out = ra_dense_from_tap(P, physical_state_tap, double(sampleId), queryTimes, candidateRoot);
```

`queryTimes` 是绝对时间 double 向量，每项满足原样本 `t0 <= t < t1`；推荐包含日志中的原始 `t0`。函数按输入顺序返回，绘线前调用方须保证时间严格递增。`out.deterministic_drift_obs8` 每行依次为 VX、VY、Vtop、Qres/Cf target、噪声增益、RA 极点 τ、AZ 差分、CT reset 基线。起始 Qres/Cf 与真实终点单独记录，真实终点 `recorded_endpoint_obs8` 不并入带噪连续线。函数不返回可供提交的 state，不为每个查询调用模型 scheduler，不触发物理反馈。

必要拒绝包括：新日志缺列/重复事件、同组 next 与下组 old 不位同、状态/标签/起点时间不一致、不是原 canonical 5 MS/s 两组、single-bank/有限 DAC/ordinary AZ/无限 slew 条件不成立、起点有未结算的 CINC kick、原始端点 replay 的 state48 或 obs8 任一位不同、source/manifest/运行缓存路径不匹配、RNG 变化。FE 未用的 aperture、DEM、实际孔径及开采时间槽允许原生 NaN 哨兵，完整状态对比保留 NaN 原始位；实际物理/命令字段、RA 状态及 obs8 仍要求有限。源码身份仅核本次函数链，真实 MAT、P、日志同运行及有无观察器等价性须由外层 driver 以各文件哈希和原始日志另外证明。

按当前任务约定，实际新 N8 保存原始记录、与未加新 tap 的旧记录完成逐位对照后，在同一隔离 worker 关闭私有模型，再对真实 tap 调用观察器两次；另由外层逐位核 P、输入状态和 RNG 均未改变。`test_ra_dense_observer.m` 是未执行的合成接口草案，本轮不把它作为新增前置或真实状态证明。当前无本观察器 MATLAB、Simulink 执行回执，也没有新密集图。
