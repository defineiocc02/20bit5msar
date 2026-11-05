# AD7961 引脚候选下的数字协议草案

版本：Rev 0.2 candidate，等待产品规格冻结  
范围：只定义 CNV/CLK/D/DCO/EN 的数字边界；不是已实现的新 RTL，也不是 LVDS、电气、CDC 或模拟时序签核。

## 目标与兼容边界

以 AD7961 的 32 引脚 LFCSP、5 V + 1.8 V 电源域、LVDS CNV/CLK 输入和 LVDS D/DCO 输出为外部接口参考。允许 FPGA 采集与校准程序重写；目标是引脚方向、信号电平族和板级连线可复用，不承诺 AD7961 的数据格式、启动延迟、EN 测试字节或时序完全 drop-in。AD7961 没有 CS、SDI、RESET 或 BUSY 引脚，不能把 D/DCO/CLK/CNV 这些已定义方向的引脚改作控制输入。

接口方向按候选器件手册定义：CNV±、CLK±为 LVDS 输入；D±、DCO±为 LVDS 输出；DCO±回送 CLK± 的相位；EN[3:0] 为 1.8 V 数字输入。实际产品仍需冻结 LVDS 电压、输出共模/摆幅、输入门限、终端、传播延迟与封装 pin map。

## 固定采样 slot 与帧

外部 FPGA 每 200 ns 产生一个 CNV 上升沿。每个 CNV 上升沿定义一个且仅一个 slot；CNV 域锁存此前至少 10 ns 已稳定的输出 bundle，并递增 32-bit slot ID。SCK 域在本 slot 的第一个数据下降沿比较快照 ID 与最近已消费 ID；即使整槽或连续多槽没有 CLK，较新的 ID 仍可被识别并在下一数据下降沿装载最新 slot。相关 ID、整字总线和边沿日历必须遵守固定的 CNV→首数据下降沿 setup 合同（≥10 ns）；这是受约束的跨域边界，不是已证明的通用异步 CDC。为了避免计数回绕别名，最长无 CLK 消费窗口必须小于 `2^32` 个 CNV slot；长时间停采前先进入 EN=0000 复位计数器。主机按 CNV slot 计数，不能按成功读出的帧数计数。CLK 读帧中断、缺少或时钟数错误时，只将当前 slot 标为损坏/无效并等待下一个 CNV；不排队重试、不压缩、不重复旧样本、不移动后续样本。

| 产品模式 | CLK 周期 | 每 slot 数据位 | 字段及位序 | 对齐 |
|---|---:|---:|---|---|
| 16 位标准码 | 8 ns（125 MHz） | 16 | 有符号二补码标准 16-bit code，MSB first | 输出 slot k 携带采样 slot k−1（N−1） |
| 20 位 Pipe-SAR | 4 ns（250 MHz） | 32 | `W[31:0]={D1[10:0],D2[11:0],DT[7:0],VALID}`，MSB first；VALID=`W[0]` | 输出 slot k 携带采样 slot k−2（N−2） |

20 位输出中的 31-bit raw word 为 `W[31:1]`。主机仅在 `VALID=1` 时重建样本。若对应 N−2 结果尚未完成或 slot 缺失，必须在原 slot 发送 `VALID=0`，不得发送最近旧数据。`BANK`、pair index 与残差极性 `s[n]` 由 FPGA 的 CNV slot ID、固定 N−2 延迟及冻结的确定性调度表推导；不要让它们跟随收到的有效帧计数。若模拟架构需要无法由 slot ID 推导的独立 OVR/BANK/POL 信息，32-bit 主帧不足以无损表达，应另行提规格，而不是在本草案中暗加字段。

EN=0000 期间，EN 生成的内部 `state_reset_n` 复位 CNV 序号、快照与移位状态；FPGA 同时停止 CNV/CLK 并清 slot ID。恢复 EN=1010 后从 slot 0 重新计数。该内部复位合同不增加封装 RESET 引脚，EN 变化必须在 CNV/CLK 停止时进行。主机丢弃启动阶段帧；20 位模式先以 `VALID=0` 明确无效的前两 slot，16 位模式没有 VALID 位，主机启动时丢弃前两帧。最终丢帧数须跟模拟流水线有效时序一起冻结。

## 首边沿、移位和采样日历

CLK 在 slot 之间保持低电平。CNV 上升沿记为 `t=0`。首个 CLK 上升沿 `R0` 是前导边沿，不代表 payload 位，不计入 payload 位数。其后的第一个数据下降沿观察到新 slot ID，锁存 bundle 并推出 MSB；随后的 DCO 上升沿采样该位。每个后续下降沿推进到下一位。这样第一位总是由第一个数据下降沿启动，避免把前导上升沿误记为 MSB 的采样边沿。20-bit 的首个数据下降沿为 CNV+10 ns，可能与 CNV 高脉冲重叠；SCK 域不能以“CNV 仍为高电平”作为帧状态门控或异步清零条件。

| 事件 | 16 位 / 125 MHz | 20 位 / 250 MHz |
|---|---:|---:|
| CNV slot 边界 | 0 ns | 0 ns |
| 前导上升沿 R0 | +8 ns | +8 ns |
| 首个数据下降沿，推出 MSB | +12 ns | +10 ns |
| MSB 采样上升沿 | +16 ns | +12 ns |
| 最后一位采样上升沿 | +136 ns | +136 ns |
| CLK 回到低电平，帧结束 | +140 ns | +138 ns |
| 到下一 200 ns CNV 的静默时间 | 60 ns | 62 ns |

DCO±是 CLK±的缓冲回送。接收端只在 DCO 上升沿采样 D±；D± 在每个对应的 CLK/DCO 下降沿更新。按表中日历，payload 分别为 16 和 32 个数据采样上升沿，另有一个不计入 payload 的前导上升沿。有效数据采样都在 CNV+136 ns 完成，最后下降沿将 CLK 停在低电平，16-bit 帧最晚 CNV+140 ns、20-bit 帧最晚 CNV+138 ns 结束。数字 RTL 的 `clk_p/dco_p/data_p` 仅表示 LVDS 差分对的逻辑状态；真正的 LVDS 驱动器、接收器、100 Ω 端接、板级偏斜和 FPGA I/O 约束需单独验证。

在 EN=`1010` 或 EN=`0100` 的有效模式下，LVDS 输出驱动保持使能，不按每帧开关。slot 间 CLK 保持低，DCO 持续回送低电平，D±持续驱动差分逻辑 0（D+=0、D−=1）。若没有新 CNV 而出现额外 CLK，DCO 仍只回送该 CLK，DATA 保持 0，不得重放上一帧。EN=`0000` 或非法 EN 码时才关闭 LVDS 输出并复位数字状态。

## EN 模式候选

| EN[3:0] | 产品提案 | 兼容边界 |
|---|---|---|
| `1010` | 正常采集；外部 4.096 V 接 REF，REFIN 接地，EN2=0 选较宽输入带宽，EN3=1 开启 VCM 输出 | 与 AD7961 的 EN 参考模式和 VCM 开关语义一致；REF 网络仍需按目标芯片冻结 |
| `0000` | 关断并请求系统硬复位；FPGA 停止 CNV/CLK 并复位 slot ID；EN 直接生成内部状态复位 | AD7961 手册只规定 power-down，不保证 Pipe-SAR 的 pair/bank 状态被复位；新产品必须明确清流水线和恢复等待时间 |
| `0100` | 产品自定义 I/O 测试码：16 位固定输出 `16'hA55A`；20 位固定输出 `32'hA55A5AA5`（VALID=1） | 与 AD7961 的 EN 码相同，但 AD7961 在该模式输出其原厂 test pattern，且 ADC 输出不可用；因此字节/行为不是 drop-in |

模式切换要求先停止 CNV 与 CLK，进入 EN=0000，再以 EN=1010 恢复并重新同步 slot ID。EN=0000 复位由封装 EN 引脚组合生成内部 `state_reset_n`，不依赖主机另送 RESET，也不需要 testbench 偷脉冲内部 POR。恢复等待时间由新产品数据手册给出，不直接照搬 AD7961 的唤醒时间。EN=1010/0000/0100 是唯一冻结候选；EN3 继续控制 VCM，不能挪作 BANK、RESET 或别的控制位。

## 时序预算

两种帧都以 `N×TCLK=128 ns` 计算。加上 CNV+8 ns 的前导和尾部停低边沿，帧分别在 CNV+140 ns（16 位）和 CNV+138 ns（20 位）结束。相对 200 ns 转换周期分别留下 60 ns 和 62 ns quiet time。

按 AD7961 Rev. B 的 5 MSPS 时序，`tCYC=200 ns`、`tCLKL=160 ns`；数据读出可用窗口按手册关系 `tCYC−tMSB+tCLKL` 计算为 160 ns。该候选日历的最后 CLK 边沿分别在 CNV+140 ns 和 CNV+138 ns，落在此窗口内，余量约 20 ns 和 22 ns。手册只对原器件的 16-bit 数据链路给出保证；20/32-bit 是新器件的候选时序，必须由新器件数据手册、FPGA setup/hold 约束和板级时序验证确认。

Pipe-SAR 上游时序候选：N−1 的 16 位结果相对其采样 CNV 在 170 ns 内提交；N−2 的 20 位结果在 370 ns 内提交，均至少早于其输出 slot 的 CNV 30 ns。被选择的 bundle 在输出 slot CNV 前至少稳定 10 ns。真实采样开关、EOC/decision 完成、数字跨域稳定及 bank/polarity 选择仍须独立验证。

## 独立原型的验收边界

新原型放在 `digital_pin_compat/`，与旧 SPI serializer 的 38-case 回归完全分开。它只验证帧字段、固定 slot、首边沿/末边沿、16/32 位 MSB-first、VALID=0、不重复/不压缩、EN 与 reset/测试码这些数字协议规则。结果文件为 `digital_pin_compat/results.json`，至少包含 `status`、`passed`、`failed`、`total`、`tests[]`、`protocol_revision`、`simulator`、`generated_utc`、`rtl_sha256`、`tb_sha256`、相对路径 `log`、`scope`、`limitations`；运行日志保存在 `digital_pin_compat/results/`。测试必须覆盖遗漏一个及连续多个 CNV slot 后恢复最新序号，以及仅由 EN=0000 引发内部复位。

通过数字 testbench 不代表 LVDS 摆幅/共模、FPGA 采样眼图、CDC/RDC、ADC 精度、采样时序、STA、封装寄生或硅片签核已经验证。
