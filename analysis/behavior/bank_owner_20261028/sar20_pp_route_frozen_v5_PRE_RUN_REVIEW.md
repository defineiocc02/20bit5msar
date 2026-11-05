# A 阶段 v5 冻结包：调度前复核

结论：按已约定的 **SATK 223 文件磁盘 SHA + 4 核心入口 which/inmem** 口径，未发现确定性静态阻断；可调度一次受控 scratch N8。该结论不代表 native 门已通过、主图已集成、B 训练或产品接受。

- 最终 ZIP SHA `939880c6411d4207e42e282eaf2497850e9c12eb2074b9ddcfbce12d2c6097ad`、入口 SHA `4111b0cf1970d42c980ec389c666675a03bb59eb4a5b98f2e6f28e75a40230a6`、manifest SHA `2da961f6b82fc70e3e2ae1879613083579fb34154659bc34c578c755d2049789` 与指定值一致。32 项 manifest、22 个候选源、87 个生产源 pin 和 Mac 镜像的 223 个 SATK 文件逐项匹配；不据此声称所有 p-code/class 运行绑定或同路径缓存字节新鲜。
- v4→v5 的候选目录只变 README、manifest、runner、static receipt；22 个候选函数与全部数据文件不变。runner 除将成功路径的关闭统一移入 cleanup 外，cleanup 前的逻辑逐字节相同；外入口只变版本/固定哈希及 cleanup 审核。
- SAR20 调用前的路径/磁盘 gate 和回执字段、PostLoad 后首次 SATK 安装前 gate、OFF 30 路及根输出门先于 ON 的顺序均保留。dirty owned scratch 只有 partial 保存/复制及 SHA 验证成功后才关闭；失败时保留模型并尝试恢复 Dirty，outer 将 cleanup 缺失/error/partial SHA 失败纳入 critical_ok。
- Q 一次读取、SHA 与解析同一 bytes，TRAIN/冻结 MAT 副本 pin、公开投影、逐案 P/SLX/simout 保存与 SHA 保留。两个版本同一 h，ACK=0；B 后台训练、不同 h 切换、实际 drain、M1、N256 和硬件资格均未完成。

调度条件：唯一空 stage、目标会话/主图 stopped clean，按原生 gate 处理真实路径和缓存；若异常或清理失败，保留回执与 owned scratch，不自动重试。结果必须独立回读 OFF/ON 根输出和实际日志，且按限定口径报告 source/cache；同路径 MATLAB 缓存字节仍无法由磁盘 SHA 证明。

核验脚本 `/tmp/sar20_pp_frozen_v5_static_integrity.py` SHA `b6c59dbb9852b071a23b95c51c7ce59d67c4b323481324c84a51014a33670186`；机读结果 `/tmp/sar20_pp_frozen_v5_static_integrity.json` SHA `6a998b449a9afb8ce3b4e97bf02ed49c7eba4533d877c6f5e64a542a22852747`。未运行 MATLAB，未操作 Windows/current。
