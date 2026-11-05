# v4 的 I1→I2 直接编辑风险及最小候选防护

这是对已冻结 v4 的只读设计记录；没有修改 v4、生产工程，也未运行 MATLAB。

## 可复现的静态路径

在一个已 prepare 的 I1 P 上，若直接将 `P.front.schedule_mode` 改为 `pool_i2`、将 `P.front.acq_guard_s` 改为 0、删除 `P.i1_binding`，但保留 I1 的固定 A/B `front.plan` 与已绑定的 `backend.dac_coupling.public_plan`，则两份 plan 仍相等；v4 的 `behavior_i1_guard(P,true)` 会从 pool_i2 分支返回。实际前端随即走 I2 的即时采集算法，但 plan 和 xFE0 仍来自 I1。上述为源码静态推断，尚无 MATLAB 负例运行；不应把受控 P 的函数测试当成该直接编辑已受防护。

## 后续最小防护设计（未实现）

- 在正常 prepare 的 **I1 分支**向本来就绑定采样计划的 `P.backend.dac_coupling` 增加一个 I1 来源标志，例如 `frontend_i1_bound=true`；I2 的旧 P 与 prepare 结果不新增字段。
- 在 `behavior_dac_backend_parameters(P)` 的真实 model-workspace setup 路径中，若来源标志存在，要求仍为固定 A/B I1，且完整 `i1_binding` 存在并与 mode/guard/plan 一致；如用户仅改为 I2 并删除顶层绑定，则拒绝并要求重新 apply。I1 自身也应要求该标志存在，避免只删来源标志后误当已绑定。
- 正规 I1→I2 采用 stopped 状态下的重新 prepare/apply，并清空 `front.plan` 以重建 I2 plan；现有 `behavior_dac_coupling_configuration` 重新构造 coupling struct，故重新 apply 可移除 I1 标志。合法 I2 的模型/日历/算术不变。
- 验证需实际 MATLAB：旧 I2 P 缺标志时的完整输出位级对照；I1 直接改 mode/guard 并删除顶层 binding 的拒绝；正规重 prepare I1→I2 与 I2→I1、tauDAC off/on 绑定、旧 P 兼容；另核验 coupling 附加字段不影响各实际 S-function 参数及保存/恢复。

该标志不是防篡改机制：同时人工删除所有关联标志、同步改动多份状态/参数，仍可能伪造一致性。若产品合同要求防止任意工作区多字段重写，需单独设计规范化全量重建或更强绑定，不能以这一小补丁宣称实现。
