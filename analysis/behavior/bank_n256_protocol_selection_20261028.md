# Bank A N256 动态试验的事前协议选择

选择时间：2026-10-28 13:51 UTC。**此时没有运行 Bank A N256 仿真，也没有读取其输出码或频谱。**

本会话并行写出两份事前登记，核心输入完全一致：同一固定训练芯片与冻结 h、epoch4、ID4–259、Fs=5 MS/s、N=256、相干 bin51/996093.75 Hz、phase1.413、差分峰值3.650563842595822 V、τDAC=0，以及 nominal、旧 Frozen、Bank ON 三组对照。两份均不预设数值性能门限、不允许事后重拟合或改输入。

**唯一执行协议**定为 [bank_n256_protocol_authoritative_20261028.json](bank_n256_protocol_authoritative_20261028.json)，SHA256 `1cd68b3d3da1c1a68dd7815dda1bf2d43061c0ccdf18827c29353361637deb57`。选它是因为它在任何N256运行前明确钉住训练 P、冻结系数文件、资格工件、公开计划及各 seed 的身份，并预声明256条码、同 RX RAW/时刻、CodeValid/标签、版本边界及旧 Frozen 码的功能门。

较早的 [bank_n256_protocol_20261028.json](bank_n256_protocol_20261028.json)，SHA256 `fe0358d652030abdc53024bc6380762f35cce34b8a6279d0a0157dea3be42955`，保留为**未执行的并行草案**，不作为门限或可替换的试验配置。若唯一协议的资格/计划不允许 epoch4 或这些输入，先报告阻断；不得在看过结果后静默改用草案或修改本协议。两份协议都不把已消费的 epoch3/bin29 holdout 答案用于本次测试。
