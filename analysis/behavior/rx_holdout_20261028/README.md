# 当前主图 RX 长训练与新登记 holdout

本次实验以[训练前协议](../../../runs/az_probe_20261028T100042Z/rx_protocol.json)固定训练和新测试条件及阈值。实际[2048条 RX 训练](../../../runs/behavior_a27903ef-c1c6-4e5e-b487-d2c1d468efef/summary.json)经 Update 后 DWork 收集、一次拟合得到满秩684，训练 RMS1.756988µV。随后只对该训练进行[显式冻结](../../../runs/az_probe_20261028T102242Z/receipt.json)，并在开跑前写入[一次性 holdout 预约](../../../runs/az_probe_20261028T100042Z/holdout_consumed.json)。

[1024条实际 RX holdout](../../../runs/behavior_dc38bf72-b9b2-42e6-a9d5-6b76a32a671f/summary.json)对应 epoch3、bin29/141.6015625kHz、phase2.137；真实接收 RAW/Ref、冻结码及频谱均保留。取整前电压 RMS/max=2.625084648/7.066346750µV，整数码中心 RMS/max=3.476644920/10.093582922µV，四项分别通过原 RMS7.8125µV、max31.25µV门。冻结输出 SNDR117.458169dB，独立回读的同 RAW 名义支路 SNDR102.049939dB。[终态评价回执](../../../runs/az_probe_20261028T102427Z/receipt.json)与[独立只读核验](independent_attempt1.json)绑定协议、文件、公开计划、1024个有效 ID/epoch/ready、固定 h 和整数码；独立公开数字公式最大电压差1.3323×10⁻¹⁵V，整数码零差，未改变原1e−12V门。

复核保存的证据可使用[只读验证脚本](verify_terminal_holdout.py)；它先检查评价回执为终态，再读取允许的公开 RX/Ref/冻结数字序列。此脚本用于独立回读，不执行 ADC 仿真、拟合或修改工程。真实仿真入口仍是 `SAR20.m`。同一登记的 holdout 已被消费，不能见到答案后自动重跑并继续称为新的独立验收；新设计试验应在训练前重新登记输入、阈值和系数身份。

本次只验证一颗固定失配行为模型芯片、DEM/物理dither开启、τDAC=0、声明的理想外部参考。缓存仍是 `NOT_ACCEPTED`，未激活乒乓bank；kTC、AZ、时序误差和其他随机非理想没有在此 holdout 中联合开启。功耗、面积、PDK/PVT 和硬件参考误差不由此结果证明。
