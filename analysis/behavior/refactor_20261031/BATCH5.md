# 可读性重构：第五批（behavior_decode，数字重建核心）

日期：2026-10-31。

## 本轮改动

**`current/src/digital/behavior_decode.m`**：87 → 109 行，多语句 6 → 0

这是**数字重建核心**：把公共 RAW 字（D1/D2/DT）还原成 20 位码与输入电压。
被 2 处调用，是整条数字链的入口。

### 补写了一条最容易误读的设计

原代码这一行：

```matlab
weights=(8:-1:1).';
statistic=sum(weights.*dtSigns);
dtWeighted=statistic/8;
```

任何人第一次读都会问：**为什么除以 8 而不是 sum(weights)=36？**

现在写清了：

```
% NOTE ON THE /8: the plain average would divide by sum(weights)=36. This chain
% divides by 8 because decision eight has no physical update while its raw LSB
% still carries digital weight one. That is deliberate, not a normalisation bug.
```

这条注释的价值在于：它是一个**看起来像 bug 的正确实现**。不写清楚，后来者很可能"修"坏它。

### 其他改动
- 6 处单行多语句展开
- 函数头补 DECODE CHAIN 全链路说明（D1→c/f→d1Dac，D2→d2RA，DT→dtWeighted，AZ→极性，voltage 求和）

## 验证：两层

**第一层：Token 级等价**

```
old statements=187  new statements=187
identical: True
```

**第二层：运行时数值 + 结构比对**

用**真实保存的 RAW 字**（来自 245 个 run 的 `summary.raw_words`）+ **真实保存的解码参数**（`parameters.digital`）跑两个实现：

| 阶段 | 覆盖 | 结果 |
|---|---:|---|
| 改完未部署 | **7976 个 RAW 字** | **0 差异** |
| 部署后复验 | **7976 个 RAW 字** | **0 差异** |

比对全部输出字段（含 `dt_weights`、`dt_signs` 数组、`clip` 逻辑标志、
`invalid_semantics` 字符串）。7976 个真实样本覆盖了各种 D1/D2/DT 组合、
不同 dither 与 AZ 配置。

## 结果

| 检查 | 结果 |
|---|---|
| Token 级语句序列 | 187 == 187，完全一致 |
| 运行时（7976 RAW 字 × 全字段） | **0 差异** |
| `which()` 路径不同 | ✅ |
| 部署哈希 | 本地 == 远端 `168b4250…` |
| 模型 SHA | `f358f226…` 未变 |

## 六批累计

| 文件 | 行数 | 多语句 |
|---|---|---|
| `behavior_sample_debug` | 167→315 | 18→0 |
| `behavior_sample_explain` | 423→513 | 23→0 |
| `behavior_sample_plot` | 454→508 | 32→0 |
| `behavior_spectrum` | 47→70 | 7→0 |
| `behavior_record_view` | 69→129 | 8→0 |
| `behavior_decode` | 87→109 | 6→0 |

**6 个文件，累计消除 94 处单行多语句。**

## 踩坑（新增 1 条）

11. **`fwrite(fid, data)` 少写 fid 会报 `MATLAB:minrhs`**——在测试脚本里生成临时函数时踩到。
    另外：`entry.m` 用多行 heredoc 写入宿主侧脚本时，若脚本本身很长、
    中途有 `%` 注释，容易在传输或解析时出问题；**改成独立函数文件 + 错误捕获**最稳妥。
