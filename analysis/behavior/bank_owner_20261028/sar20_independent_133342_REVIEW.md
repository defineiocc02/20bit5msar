# 133342 N8 scratch 原件独立复核

结论：这次受控 scratch 的五案身份、OFF/ON 位门、RX 路由和 ready 时刻根输出关键门独立通过。它是 N8 行为仿真证据，不代表 current 已接入或生产接受。

- 五案 `factory_base / factory_off / rx_nominal / rx_old_frozen / rx_bank_on` 的 `parameters.mat`（含 P、DecodeP）、实际保存 SLX、source manifest、simout SHA 均与各案原生回执相符；各案保存的 DecodeP 与同案 P.digital 的结构与数据指纹相同。完整 SHA 见下方 JSON。source manifest 的 23 项候选、87 项生产、223 项 SATK 锁与冻结包一致；as-run 归档中本候选的 34 项均与冻结包逐字节一致。该归档未收录冻结包内 6 项说明/离线工具文件，且它本身是更大的归档，不能把其 SHA 当成冻结 ZIP SHA。
- 独立读取保存的 Time/Data（含原始形状、类和比特），factory base 对显式 Bank OFF 30/30 旧日志一致；RX nominal 对 Bank ON，除允许变化的 code_log 外 29/29 旧日志一致。OFF 根 Code20 对旧码逐时刻一致，CodeValid 全 0，CodeMeta 符合禁用标签约定。旧模型入口完全缺少 Bank 字段的情形未证实。
- ON 实际有 **12 个**有效 RX ready，ID 0–11、epoch 1；本次预定 N8 是其中 ID 4–11 的 8 个。ID 0–3 的 slot/version 为 1/1，ID 4–11 为 2/2。12 个 ready 的 RAW、ready 和时间与旧 Frozen 相同，Bank 码也与旧 Frozen 同时刻、同 ID/epoch 按位相同。已独立读取 yout 的 Code20、CodeValid、CodeMeta，12 个 ready 时刻与 Bank 日志相同；Bank 日志在非 ready 时 valid=0。根口非 ready 保持或独立时钟脉冲未证实。
- 两槽 h、h_by_slice、plan、public_cfg 及其摘要字段与旧 Frozen 缓存逐字段指纹相同，故本次证明版本路由和与 nominal 的码差，未证明不同 h 间切换效果。实际接收错误注入、drain、B 后台训练、N256 和生产接受均未证实。回执记录伪资格、参考电压变更、错误 M1 日历、缺 provenance、有限和无限 τ 六种模型 update 拒绝；此处复核的是原生回执及对应断言源码，非重跑异常。
- 132220 旧原件 13 项、130247 旧原件 3 项及此次负例 fixture 副本 SHA 符合冻结 pin。原生退出回执记录主 SLX `63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6` 未变、stopped/clean，任务自有 scratch 已关闭，path/cwd/RNG 恢复，新增候选缓存清空；未比较主图私有 P。相同路径的既有缓存函数内存字节未独立验证。

只读复算脚本 `/tmp/sar20_independent_133342.py`，SHA-256 `fa5197fe08e0cd18c58cbf35613b2ad868f5401389668772d0f4ff8ce2a6fbbe`；复算结果 `/tmp/sar20_independent_133342.json`，SHA-256 `006bdd379eb6e54d8f49ccbee306941a56569d75f665ecb56fa8c298481c47fe`。脚本退出码 0；未操作 Windows/current，也未重跑仿真。
