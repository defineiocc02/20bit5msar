# SAR ADC完整产品定义 Rev0.5

日期：2026-10-25。两款产品全文重写，保持用户确认的AD7961 CP-32-7引脚及工作电压兼容配置。性能为设计目标，外部行为结果独立列示。

主入口：[完整产品定义PDF](SAR_ADC_完整产品定义_Rev0.5.pdf)。全集含[实现指南](产品定义与实现指南_Rev0.5.pdf)、[16位手册](manuals/SAR16-5_产品规格书_Rev0.5.pdf)、[20位手册](manuals/SAR20-5_产品规格书_Rev0.5.pdf)，PDF书签可跳转分册及章节。

- 引脚：pinout16_rev05.csv、pinout20_rev05.csv；外围32脚及底部EP33。新顶视图在assets与原生canvas中。物理位置保持，逐脚重新定义本芯片连接与支持模式。
- 图件：10张自绘功能/引脚/时序/重建图，真实Analog Canvas原生工程、SVG与矢量PDF；文献和内部参考原图保留来源、页码与复用限制。
- 原码接口：16位125MHz/固定N−1、20位32位250MHz/固定N−2；禁用原厂self-clock连接，DCO+不得接地；CMOS CNV模式移除CNV差分终端。
- 内核：16位单级SAR；20位共享RA/连续CT/TA8/CAAZ。片外FDA、动态参考、稳压及FPGA，保持最小片内支持集。
- 证据：research/simulink_evidence为闭合运行快照；本修订未操作MATLAB或重跑RTL。原serializer27项结果属于归档逻辑原型，不是Pad/CDC/STA或硅签核。

## 复建

macOS：XeLaTeX、系统Arial/PingFang、合法SimSun及含pypdf的Python3。字体不随包分发。设置SAR_SIM_SUN为真实SimSun TTC绝对路径，再执行：

```sh
SAR_SIM_SUN=/absolute/path/to/simsun.ttc sh rebuild.sh
```

源码使用随包图形PDF，普通文档复建无需安装Analog Canvas。可选图形重新生成需已构建Analog Canvas、Node及Resvg；build_vendor_figures.mjs和build_pinout_rev05.mjs分别生成通用图与含旋转脚名的引脚图。引脚PDF由其独立导出器生成，不使用忽略文字旋转的旧通用导出器覆盖。

正式PDF以最终检查及对抗复审记录为准。主机参考定点实现、目标规格、行为单点与电路/工艺验证分别管理；未表征绝对最大值、Pad、功耗和热参数不填作实测值。
