# Checkpoint: RA OU + ordinary AZ + finite DAC

状态：隔离候选、数学检查和静态检查完成；MATLAB 函数和 Simulink 均未执行，无法宣称联合模式运行通过。未运行 Windows MATLAB，未修改生产，也未读取 >300 MB 文件。

基线 v2 ZIP SHA-256 `09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7`；`baseline/single_bank` 有 `BASELINE_SHA256.json` 逐项校验，所有修改在 `candidate`。候选图是 485 图 SHA-256 `48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3`。回滚：保留原生产不变，丢弃本隔离候选或从 `BASELINE_v2.zip` 重新提取。

源码限于固定 Ctop、单 bank、ordinary/off AZ、有限 DAC τ 和线性无限 slew；S-function/状态打包及 OU 产生器未更改。静态结果 `STATIC_VERIFY.json`。70 位积分 20 组的 Python 浮点转录最大差 5.551115123125783e-17；4 万 seed 的联合 AZ/DAC + OU 抽样及假设见 `JOINT_MATH_RESULT.json`。这不运行 .m，不证明随机键完全独立。

后续首次在明确授权的独立 headless MATLAB 进程执行 `candidate/tests/test_joint_ou_az_dac.m`，先核路径、基线和未载入 SarAdc；它包含旧 v2 OFF/σ=0 位比、事件键 SHA 与负例。该测试目前仅为草案，环境或运行问题未排除。运行前后保留日志，再决定隔离 485 图的应用参数验证；不能把本数学证据升级成联合仿真、论文性能或 PDK 结论。
