# RC + kTC 单阵列隔离候选

- 基线：FROZEN_BASE_v2.zip，SHA-256 `09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7`。
- 范围：仅单阵列等采样时间常数；5 MS/s；保留 jitter、ADI 和 10M 原有限制。
- 实现：已有 B 自真实开采时刻做确定性 RC 推进；capture 增加有限窗 Johnson 创新；保持 353 接口和既有随机键；中途 reset 显式拒绝。
- 静态/独立 Python 数学检查已通过；MATLAB 函数草案及 Simulink 均未执行。
- 回滚：删除隔离目录或重新从该 ZIP 提取；原生产工程和冻结 ZIP 不更改。
- 合并：RA OU / jitter 候选可能改动相同文件，须逐块合并并重新验证；不能整文件覆盖。
- 随机键：单次 run 静态追踪为 `sample_id=cycle`；重复 run 复用相同 seed/epoch 会重放；FE353 不存历史，调用者保证键不复用。
- 最终复核修正开启 kTC 的单 bank 覆盖计算：只统计有效项 1–8；新增停放项非零负例草案。
