# Rev0.5产品定义与模型分工

本目录为产品任务的设计输入快照；未覆盖另一Simulink任务的统一spec或模型。兼容AD7961 CP-32-7引脚/电压、外REF4.096V、REFIN0、EN1010、16bit125MHz N−1及32bit250MHz N−2帧保持。当前逐脚定义与禁止连接在两份Rev0.5手册及pinout CSV。

完整重写的手册加入PD-01…12、bank×POL诊断、参考重建码、输出偏移二进制、非理想三态覆盖和外部动态负载。20位行为单点独立列示，不升级性能保证。仅20位CAAZ；16位保持单级SAR。

后续模型消费Rev0.5时，应逐项核对requirements_rev05.json及software_reconstruction；不得因此改变当前正在执行的任务、已保存物理芯片或归档raw。
