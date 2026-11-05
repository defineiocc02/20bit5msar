> **2026-11-05 用户已明确暂停目标，清理收尾完成后停止。** 全部子代理已中断，无新仿真或建图排队。当前公开工程的119项source/config/model/state再次逐SHA核对与原9197基线一致；`current/models/SarAdc.slx`仍为91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e，尚未部署调试候选。
>
> 本轮候选已统一封存到 `analysis/debug_ui_20261105/paused_work/candidate_sources_paused.zip`，SHA3504a9a93a4f04c2a009be691641dc82836677697d4daf25e9c16e0d02cfe5bf；210文件逐member SHA读回通过。`PAUSE_INDEX.json`保留原目录→归档前缀映射，原临时展开目录已删除，恢复须从此索引解包，不再直接使用下文旧/tmp路径。UI/sample代码处于中断草稿，不能当已验收。原Mac基线备份在 `_preserved/before_debug_ui_20261105_mac/`；Windows原件已核备份 `D:/Academic/Projects/sar20m1/SAR20_preserved/before_debug_ui_20261105`，manifest21c627…/zip707fb3…。
>
> 已完成实际证据：①旧9197+7新观测源码旧2dialog的N8 smoke PASS，worker6516/14.050699s，32旧logger+3roots/tout位同、globalRng不变，`analysis/debug_ui_20261105/source_smoke/`含原始data/report及封存payload；不能替代新observer ON或最终N256。②首次graph1在SDK拒绝隐藏显示参数ContentPreviewEnabled处停止，无后续结构完成；实际报错/partial/recovery80a及asrun脚本包在`analysis/debug_ui_20261105/graph1_failure/`。③已从80a私有checkpoint继续，原生API仅关闭显示预览、结构仍SATK，创建8个无计算PhysicalView卡并真导出截图；model9626ccf94faa8ad91092ff9ecd05d283fedff08f4abb4ff0049c8585ad4bbb89，`analysis/debug_ui_20261105/classification_snapshot/`。这只是分类导航初稿，未接click focus/样本UI、未跑仿真、未晋升默认。原用户截图已明确这点。
>
> 尚未完成：FPGA D1/D2/DT真实封装、执行布局、新3dialog observer_log接线/6329列×默认49行(上限64)、首页/字段/历史run/事件/阶段/比较UI原生验证、受控参数pending→apply→run→restore、最终默认N256回归。旧N256无完整owner history；已计划私有旧907只读owner probe以取得真实before-state对照，但脚本未跑。下一恢复工作优先核归档中的sample/UI草稿接口和NaN/IDepoch/阶段scope语义，再从已保存分类模型9626继续未执行的FPGA scope，不重新跑失败整个stage1或重建分类卡。
>
> 已关闭本任务干净停止的SarAdc窗口；保留原MATLAB GUI27628登录会话，不退出MATLAB。13个本任务terminal计划任务已导出定义后注销，原SAR20_MatlabControl/SAR20_ReadDesktop保持；清理详情在`analysis/debug_ui_20261105/pause_cleanup/`。原raw/as-run/基线不删；超过300MB文件未纳入本次清理。


完整最近用户要求：/Users/zhaoyi/.codex/attachments/c840becd-9910-4cdf-a6bd-4832297e96ed/已粘贴的文本.txt
