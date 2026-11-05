# SAR20：一页读图、调参和复跑（6319 审阅候选）

[已导出主图及 applied P](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/current_figures/metadata.json>)对应 SLX SHA `63190994…`：N=8、5 MS/s，DAC τ=0/coupling off，AZ、训练、冻结和 transport off。图上文字是**已保存配置**，不随工厂文件编辑实时变化。有限 DAC 耦合已接主图；下例的 1 ns 是设计试验值，不是工艺测量值。

**读图。** 顶层 `Driver/SineCfg` 是 `[offset, amplitude, frequency, phase]` 配置，不是采样后的波形；`Calendar/Event` 是 `[sample ID, group]`。打开 `EventStep → Adc`，按 `SampleRaAdvance → DacCtFeedback → Sar1TrialRaCt → ResidueCtCompare → SarDecisionTracking → ChargeReturnRaReset` 读一次事件：旧态推进 → 到期反馈 → 新 trial/RA 命令 → 比较 → 判决 → 返回和复位。六块是计算阶段，不是六套独立电路。

只找三份片内 owner：`SampleCharge[353]` 保存前端电荷、`RaCtState[48]` 保存同一 RA/AZ/CT、`SarState[51]` 保存控制。候选值须到对应 UnitDelay 才成为下一事件旧态。`SampleRaAdvance/FE_old` 同时进入 `Sample` 与 `RaAdvance` 第四口；有限 DAC 使旧电荷在事件间建立，并驱动**同一个** RA。`RaAdvance.obs8` 是反馈前端点，`BackLog` 为后续阶段；`RA_cmp` 是 obs8 而非比较 bit，`FE_return` 是返回命令而非已返回电荷。

看输出时区分 `Adc.Ready`（ADC RawReady）和 `EventStep/RecordReady`（FPGA 实际收帧就绪）：transport off 走 ADC 直通，on 走 TX/公开 pin/RX，同 ID/epoch 再取输出。不要把示例的 RX 时刻当成新的模拟计算端点。

**调参复跑。** 从保存 P 构造一次 N8 的 τ=1 ns 对照（训练/冻结关闭；示例会暂时保存新 P，结束恢复原 P）：

```matlab
cd('D:/Academic/Projects/sar20m1/SAR20')
SAR20
ws = get_param('SarAdc','ModelWorkspace'); p0 = getVariable(ws,'P'); p = p0;
assert(p.N==8 && p.first_id<=5 && p.first_id+p.N>5 && ...
       ~p.training.enabled && ~p.frozen.enabled);
p.front.tau_dac_s(:)=1e-9;              % 18 个物理片，单位 s
p.backend.dac_coupling.enabled=true;      % apply 时重新绑定
p.backend.ra.slew_v_per_s=Inf; p.debug.dac_enabled=true;  % 完整 RApre 仅 N8
try
    SAR20('apply',p); SAR20('check'); r=SAR20('run');
    SAR20('sample',5,r.run_path);
catch err
    SAR20('apply',p0); rethrow(err);
end
SAR20('apply',p0);
```

`check` 是模型更新/编译检查，`run` 才保存实际运行记录；GUI Run 使用保存 P，不自动重读工厂或生成同样的证据目录。`sample` 当前不自动纳入 `dac_ra_pre_log`：从 `r.run_path/simout.mat` 的 `simout.get('dac_ra_pre_log')` 查看，按实际 event 时间和 ID/epoch 对齐，不能按行号混配 parent 的额外传输事件。`P.ni` 是摘要而不是物理开关，部分派生规则尚未收敛；τ、coupling、slew 和校准条件要看真实字段。恢复 `p0` 恢复配置，不保证 SLX 文件字节及 SHA 仍与实验前相同。

设计对照只对本次设置和记录负责；完整参数说明及限制见[现行参数表](</Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/docs/PARAMETERS.md>)。图形和代码的可读性修订建议见同目录 `READABILITY_AUDIT_candidate.md`，均尚未实施。
