# 140306 任务专属 SATK 副本盘点

Mac 本机镜像副本：`/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/runs/az_probe_20261028T140306Z/overlay_runtime/dependencies/toolkit`。

只读递归结果：1,866个普通文件、603个目录（含根目录）、41,067,301字节的逻辑文件大小，无 symlink。与项目原 `dependencies/toolkit` 逐个相对路径、大小和SHA比较：文件和目录集合均相同、无内容差异；[toolkit_inventory.json](/tmp/sar20_independent_140306/toolkit_inventory.json) 保存每个文件的大小和SHA。释放文件系统容量可能不同，不能把逻辑字节数等同可用空间变化。

任务原生回执另钉住其中223个 SATK 工具文件；140306 通用 `candidate.zip` 和冻结候选 ZIP 都没有收录该整棵工具副本。工具目录与这些源码签名的相符，不等于已经为全部1,866项建立独立压缩归档。工作时 Windows 回执中的对应副本路径为 `D:\Academic\Projects\sar20m1\SAR20\runs\az_probe_20261028T140306Z\overlay_runtime\dependencies\toolkit`；此处没有实时检查 Windows 是否仍存在或被引用。

可以考虑由主执行者先把该工具目录及完整相对路径、大小、SHA清单压缩到**新的不可覆盖归档**，逐项读回、复核全部1,866项、零符号链接及223项锁；同时保留140306的 P/SLX/simout、来源清单、receipt和frozen ZIP。只有任务结束、没有进程或路径引用，且删除前目标与清单 SHA仍相符时，才可考虑删除该任务的展开**副本**；不要删除项目原工具、其他 overlay 源或历史证据。上述是可审阅建议，未创建压缩包、未删除任何文件。
