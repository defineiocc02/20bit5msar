# Fig. 1 / Fig. 2：真实 N8 模型事件记录

本目录是唯一最终出图集合，数据直接来自保存的 single-bank 5 MS/s N8 tap 仿真，不是论文数据或晶体管/芯片测量。

- `fig01_tracking_M8_actual`：ID 5 的 M=8 端点轨迹和 8 次 TA 判决、7 次反馈。没有 M 扫描，也没有噪声抑制或 SNR 性能结论。
- `fig02_timing_actual`：该样本的 48 组调度事件；`t_open` 是已保存状态元数据，不是实际开关波形。AZ 关闭。
- `fig02_nodes_actual`：该样本的 Vres、VX、VY 事件端点。连线仅便于阅读，不表示已仿真连续时间波形。
- 三图均提供 PNG、PDF 和 SVG。`events_sample.csv` 保留 48 条事件的完整时间与数值；`decisions_sample.csv` 保留 12 次 D2 和 8 次 TA 判决。
- `figure_manifest.json` 的路径相对此目录，记录输入及图表 SHA-256、精确 P 关键参数、数据范围及限制。原始记录的 SHA 显示在每张图中。

当前记录：ID 5，epoch 1，CNV 绝对时刻 1.000000 µs；D1/D2/DT = 1924/2471/213，TA 决策序列 11010101。当前输入峰值 3.65056 V，差分满量程 8.192 V；A0 = 10000，UGB = 1.2 GHz，模型 Cf = 0.864 pF，AZ/噪声/DEM/dither/jitter 关闭，采样及 DAC 时间常数为零。

绘图脚本为上一级 `../plot_actual_n8.py`，样式助手为 `../author_style.py`。脚本核对固定输入和源的 SHA，从原始 MAT 读取，不调用 MATLAB 或修改原始数据；目标目录必须是全新或空目录。例如，以下命令可从任意当前工作目录运行：

```sh
SAR20_ROOT="/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020"
"$SAR20_ROOT/dependencies/analysis_env/bin/python" "$SAR20_ROOT/analysis/behavior/single_bank_1039_20261104/figures/fig01_02_actual_n8_20261104/plot_actual_n8.py" --out /tmp/sar20_fig01_02_reproduce --sample-id 5
```

如目标路径已存在，换一个不存在的路径。脚本生成图、CSV 和数据清单；本 README 与交付路径字段在渲染后附加。图仅显示事件端点；完整前端状态及返回电荷未由这些 N8 日志直接观测。
