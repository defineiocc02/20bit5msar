# RA 行为模型普通 AZ 验证，非三级晶体管环放

唯一最终图是 `fig04_ordinary_az_n8` 的 PNG、PDF、SVG。本图直接读取普通 AZ 对照的两次实际 N8 仿真和先前零失调基线；不是论文的晶体管或芯片测试，也没有功耗曲线。

- 同一单前端图、5 MS/s；两次对照均施加输入参考 +1 mV 失调。普通 AZ 的写入时间常数为 **1 ns**、保持泄漏时间常数为 **Inf**；事件调度写入窗口为 0–31.25 ns。不是 8 ns / 1 µs 条件。
- 图 (a) 是 ID 0 的 `az_commit_log` final-next 数值与实际路由窗口；该日志在 UnitDelay 输入侧，不是独立观测的已提交状态。图 (b) 是 ID 5 的 `back_log` RA 输出 VX，取比较前事件端点。连线仅辅助阅读，不表示点间连续波形。
- 图 (c) 的柱子和圆点来自实际输出码相对零失调基线的差值：关闭 AZ 为 +133 或 +134 LSB，启用 AZ 为 0 LSB。12 个记录包含 4 个预热 ID 和 8 个选中 ID，不能称作 12 个独立选中样本或统计结论。
- 黑色虚线 133.428 LSB 是模型理论预测 `Vos × F × NG / G / LSB`；F = A0/(A0+NG)，使用保存日志 NG 和配置，不是新增仿真曲线。

`az_final_next_id0.csv`、`ra_output_id5.csv` 和 `code_difference_12.csv` 分别保存图中原始端点和 12 码差。`figure_manifest.json` 固定基线及两案原始 MAT、SLX、源码和讲稿 SHA，记录具体配置、路径差异门、输出哈希及观察限制。

复现脚本为上一级 `../plot_fig04_ordinary_az.py`；它核验原始数据身份，从任意当前工作目录可执行，不启动 MATLAB、不修改原始文件，且输出目录必须不存在或为空：

```sh
SAR20_ROOT="/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020"
"$SAR20_ROOT/dependencies/analysis_env/bin/python" "$SAR20_ROOT/analysis/behavior/single_bank_1039_20261104/figures/fig04_ordinary_az_n8_20261104/plot_fig04_ordinary_az.py" --out /tmp/sar20_fig04_az_reproduce
```

若目标已存在，改用新的目录。README 在绘图后加入，原始 MAT 与 native 回执未改动。
