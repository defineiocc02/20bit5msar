# Rev0.3当前合同：AD7961兼容配置与20位斩波辅助AZ

当前外部接口已按产品任务逐脚复核，冻结为设计输入：AD7961 CP-32-7、外REF4.096/REFIN0/EN1010、单LVDS32bit@250MHz、CNV固定N−2读槽；无CS/SDI/RESET_N/BUSY或BANK/OVR侧带。前导rise8ns忽略，firstfall10ns，32次有效rise12..136ns，末fall138ns。核心31raw+VALID不变。内核0.9V改为必要内部偏置；pin21 VCM为高阻REF/2模拟输出。CAAZ仅20，按CHOP_AZ_SPEC.md。

用户允许FPGA改程序；这不是全部原厂模式/性能的无条件drop-in。精确合同见SPEC.md §6/spec.yml/io，旧四线SPI记录均属历史。以下Rev0.2及Rev0.1记录只保留迁移过程，不能覆盖本段。

# Rev0.2增补：20位斩波辅助AZ与商用引脚兼容

用户2026-10-20新要求优先于以下Rev0.1对齐记录：仅20位加入PKU VLSI2025斩波辅助AZ，详见CHOP_AZ_SPEC.md；商用ADC引脚/电压兼容、允许FPGA改程序，原自定义32脚/4lane50MHz/sideband接口已退役待新合同。31raw+VALID核心载荷保持，CAAZ内部标签不等于新增封装脚。16位不加入本AZ技术。

以下保留为历史对齐记录，不作新bond-map或新接口签核依据。

# 与聊天“调查产品”的规格对齐

对齐对象：`codex://threads/01a15810-ff21-7da0-97f9-74db157b02ce`，聊天标题“调查产品”。本次已读最新聊天摘要及本机当前手册/数字合同，未覆盖其正在编辑的文件。

## 共同依据

- 产品手册：`../sar_adc_product_definition_20261020/illustrated/manuals/SAR20-5_设计目标手册_Rev0.1.md`。
- 数字合同：`../sar_adc_product_definition_20261020/illustrated/digital/README_RTL.md`。
- 行为模型统一入口：本目录 `SPEC.md` 与 `spec.yml`。

| 主题 | 统一决定 | 原有歧义的处理 |
|---|---|---|
| 主体架构 | 成电10b DT/32×RA/11b CT/8 tracking/2b冗余 | 6+15 DT、9+12重组均退役为历史讨论 |
| ADI借鉴范围 | 只在前端A/B交替采集；18slice为后续前端候选 | 不换成ADI的9b SADC/3b flash/ADC2位数 |
| 工艺/速率 | 180nm/5MS/s | 不在首版追40MS/s或冻结8–10MS/s |
| FSR/测试幅度 | 8.192V；−1dBFS；100kHz主测 | 论文约±5V输入只作原文profile，不混用到产品指标 |
| 性能 | SNR100/SINAD98/THD−105dBc目标 | 原型100dB级SNDR不是本芯片保证；20b不是20ENOB |
| 数字分工 | 片内tracking反馈；片外SINC²/校准/重构 | 在Simulink系统中均要实现，按芯片/FPGA域分区 |
| 普通原码帧 | D1(11)+D2(12)+DT(8)+VALID=32 | 不沿用C6/F15；不加in-band SEQ/TEST/BANK/OVR |
| BANK/OVR | pin30/pin29 sideband | sample_id保留为内部/FPGA状态 |
| 时钟/延迟 | 4lane50MHz；N−2读出 | 读数延迟不等于模拟二级的DT采样/转换分段 |
| 内部时间 | 核心≤180ns目标；RA与CT重叠 | 不使用旧粗80+RA80+细DT100相位；MODEL_PLAN给候选槽，须验证 |
| 支持电路 | 精密ref/refbuffer/VCM/LDO/FDA默认片外 | 仿真以外部动态RLC/噪声模型体现，不新增必需片内精密IP |
| DEM/dither | 前端研究开关，逐项实现并验证 | 当前硬件默认关闭；启用需明确元数据/种子合同，不能偷改现有配置口 |
| 图件 | 对齐论文：Arial/Times/Cambria Math、黑线、灰/灰绿分区、VX橙/VY蓝 | 不另起一套图形风格；本轮不覆盖其他聊天的图稿 |

## 当前手册与本规格的边界

当前SAR20手册已采用CT主体与31bit原码；不需要重做SAR16部分或更改现有32脚/帧合同。本规格新增更细的Simulink状态、非理想、前端实验开关与分步验收。

产品手册给出的tACQ为完整200ns目标；行为模型计算时须扣实际非重叠与路由开销。手册核心≤180ns、提交≤370ns、N−2/50MHz均保留。MODEL_PLAN中的20ns tracking为工程候选，原文10ns仍保留对照，不能把候选写成已实现硬件时序。

后续改动优先修改本目录统一合同，再由各聊天维护各自手册、模型和图件，避免并发覆盖。其他聊天的既有RTL/TB通过记录只证明其报告范围，本线程未重新运行那些测试。
