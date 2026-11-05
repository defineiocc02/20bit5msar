from pathlib import Path
from hashlib import sha256
import difflib
import json
import shutil

root = Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
out = Path('/tmp/sar20_reading_patch_6319')
expected_model = '63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6'
def digest(data):
    return sha256(data).hexdigest()
assert digest((root/'current/models/SarAdc.slx').read_bytes()) == expected_model

paths = [
    'README.md', 'docs/PARAMETERS.md',
    'current/src/model/behavior_dac_coupling_configuration.m',
    'current/src/physics/behavior_backend_stage.m',
    'current/src/physics/behavior_backend_step.m',
    'current/src/control/behavior_sar_step.m',
    'current/src/transport/sar20_lvds_rx_step.m',
    'config/make_adi_cases.m', 'config/adc_parameters.m',
]
original = {p:(root/p).read_bytes() for p in paths}
text = {p:original[p].decode('utf-8') for p in paths}

def replace(p, old, new):
    assert text[p].count(old) == 1, (p, old[:100], text[p].count(old))
    text[p] = text[p].replace(old, new, 1)

r='README.md'
replace(r, '默认N8、`P.transport.enabled=false`、DAC建立关闭。',
           '默认N8、`P.transport.enabled=false`、DAC耦合off且τDAC=0（理想即时建立；DAC本身仍工作）。')
replace(r, '18/8/8/2池、DEM、物理dither及公开加回已完成整图对照 |',
           '18/8/8/2片池、DEM、物理dither及公开加回已完成整图对照；片池不是校准系数乒乓Bank |')
replace(r, '| 仍未完成 | 乒乓bank、全时钟抖动/有限RC联合、参考恢复/比较器等关键非理想、全范围DNL/INL；',
           '| 仍未完成 | 校准系数乒乓Bank尚未接入；当前固定M8，[M1仅完成隔离scratch的N8功能对照](analysis/behavior/m1_m8_20261028/sar20_independent_m1_114345_REVIEW.md)；全时钟抖动/有限RC联合、参考恢复/比较器等关键非理想、全范围DNL/INL仍未完成；')
replace(r, '6位Flash预转换+5次细SAR形成10位有效DT量化；后续为12次D2、8次tracking比较及7次物理更新，RA后没有新增采样保持。',
           '6位Flash预转换与5次细SAR形成10位有效一级量化；后续当前固定M8，含12次D2、8次tracking比较及7次物理更新，RA后没有新增采样保持。')
replace(r, 'DAC关闭时SNDR', 'DAC耦合关闭且τDAC=0时SNDR')
replace(r, '不能当成已完成长RX校准。开启采样kTC',
           '不能当作RX路径训练证据；当前独立RX训练与holdout见本页表格及结果页。开启采样kTC')
replace(r, '旧直通RAW的长训练/holdout不能据此迁移到RX。',
           '旧直通RAW的长训练/holdout不能当作RX路径训练证据；当前RX长训练与独立holdout另见本页表格及结果页。')
marker='\n\n同一主图另完成[AZ保持斩波＋混合18片τ的N8实跑]'
insert=('\n\n[事件查找候选的N256隔离对照](analysis/behavior/event_lookup_20261028/REVIEW.md)'
        '仅有一对旧→新无profile计时：136.147900→136.908603秒，30路Time/Data逐位一致；'
        '本次没有提速，候选未进入current。[真实profiler回执](runs/az_probe_20261028T122805Z/validation/receipt.json)'
        '记录一次插桩N256、耗时182.056秒；各函数含子时间重叠，插桩和无profile耗时不能用来计算加速比。'
        '该profiler回执状态标记独立回读待完成，后续独立证据另核。\n\n同一主图另完成[AZ保持斩波＋混合18片τ的N8实跑]')
replace(r, marker, insert)
old=('当前主图另以31个真实DC仿真点在正侧约7.8–31.3µV定位三个相邻跃迁，得到码524290/524291的[条件局部DNL区间](analysis/behavior/RESULTS.md)；旧局部窗口与A0对照仍是历史证据。完整DNL/INL、零点跳码排除、更多噪声/失配/抖动及乒乓bank尚未完成。当前RX长训练/独立holdout的通过范围见结果页，不能外推到有限DAC＋校准、所有芯片或工艺。原论文与定义保留在`docs/`；未测项目不填0，关闭或0/Inf配置不计入覆盖。')
new=('当前主图以31个DC仿真点在正侧约7.8–31.3µV定位三个相邻跃迁，得到码524290/524291的[条件局部DNL区间](analysis/behavior/RESULTS.md)。'
     '[近零固定端点A0对照](analysis/behavior/local_static_20261028/sar20_independent_gain3_120823_REVIEW.md)中，−LSB/4096与0V端点码差在A0=1e4/1e5/Inf时分别为4/1/1；'
     '新点来自复制图，旧锚来自原图，尚无同A0跨环境逐位门。这支持有限增益影响该条件下的端点码差，不证明唯一根因或窗内缺码。'
     '完整DNL/INL、零点窗内单调性与缺码排除、更多噪声/失配/抖动及乒乓Bank尚未完成。'
     '当前RX长训练/独立holdout的通过范围见结果页，不能外推到有限DAC＋校准、所有芯片或工艺。原论文与定义保留在`docs/`；未测项目不填0，关闭或0/Inf配置不计入覆盖。')
replace(r, old, new)

p='docs/PARAMETERS.md'
replace(p, '正有限值需同时设`P.backend.dac_coupling.enabled=true`，由prepare绑定同一18片映射和旧FE状态到RA；RA slew须为Inf。',
           '任何非零值（包括Inf保持负例）均需设`P.backend.dac_coupling.enabled=true`，由prepare绑定同一18片映射和旧FE状态到RA；RA slew须为Inf。Inf-only不计有限建立覆盖。')
replace(p, '乒乓bank未接。未实现项应拒绝或保持明确关闭；',
           '校准系数乒乓Bank未接；主图固定M8，[M1只完成隔离scratch的N8功能对照](../analysis/behavior/m1_m8_20261028/sar20_independent_m1_114345_REVIEW.md)，其N256性能未测。未实现项应拒绝或保持明确关闭；')
replace(p, '参数捕获补丁已通过实际同图12路逐位门与参数切换；N8 6.6428914→4.3252889s是单对无profile计时，不能称统计benchmark。hold_chop有限leak复跑3.8009591s属于另一次模式验证，不与前一对混作提速比例。',
           '参数捕获补丁已通过实际同图12路逐位门与参数切换；N8 6.6428914→4.3252889s是单对无profile计时，不能称统计benchmark。hold_chop有限leak复跑3.8009591s属于另一次模式验证，不与前一对混作提速比例。'
           '另一个[事件查找候选N256单对对照](../analysis/behavior/event_lookup_20261028/REVIEW.md)为136.147900→136.908603s，本次未提速且未晋升。'
           '[122805 profiler](../runs/az_probe_20261028T122805Z/validation/receipt.json)仅用于热点定位，插桩墙钟和父子含子时间不可用作速度比；原回执标记独立回读待完成。')

p='current/src/model/behavior_dac_coupling_configuration.m'
replace(p, '% Candidate call after frontend normalization. Does not enable/modify tau_dac,\n% states, graph, event calendar or current prepare\'s finite-DAC rejection.',
           '% Called by prepare after FE normalization; binds enabled, tau[18], schema and plan.\n% Does not alter FE tau/state, the graph or the event calendar.')
p='current/src/physics/behavior_backend_stage.m'
replace(p, '% Candidate optional oldFrontend353 is read ONLY in finite-DAC active advance;\n% off/all-zero tau retains the original backend_step call/operations.',
           '% Sfun supplies OLD FE353 for enabled/nonzero-tau advance, even when RA is off.\n% The stage builds forcing only when the retained RA is on and not reset.\n% Off/all-zero tau retains the original backend_step call/operations.')
p='current/src/physics/behavior_backend_step.m'
replace(p, '%Candidate optional forcing is derived read-only from the OLD FE owner. The',
           '%Optional forcing is derived read-only from the OLD FE owner. The')
p='current/src/control/behavior_sar_step.m'
replace(p, '            s.bank=mod(s.sample_id,2);s.sample_v=physical(comparison,\'sample_v\');',
           '            % Sample-ID parity tag only; not a calibration coefficient bank.\n            s.bank=mod(s.sample_id,2);s.sample_v=physical(comparison,\'sample_v\');')
p='current/src/transport/sar20_lvds_rx_step.m'
replace(p, '        y.bank = mod(s.slot_target_id, 2);',
           '        % Public sample-ID parity tag; not a coefficient-bank selector.\n        y.bank = mod(s.slot_target_id, 2);')
p='config/make_adi_cases.m'
replace(p, '% Bank-specific kappa is reported from actual analog C for',
           '% Per-sample selected-slice kappa is reported from actual analog C for')
p='config/adc_parameters.m'
replace(p, "'Sampling/DAC initially fully settled; their finite-settling tests pending'; ...",
           "'Factory defaults use zero sampling/DAC settling time constants'; ...")
replace(p, "'No calibration and no pin-level LVDS timing claim'};",
           "'Calibration mode is explicit; no pin-level LVDS electrical timing signoff'};")

for p in paths:
    for sub, contents in [('original', original[p]), ('candidate', text[p].encode('utf-8'))]:
        path=out/sub/p
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(contents)

sets = {
  'docs_candidate.diff': paths[:2],
  'source_comments_candidate.diff': paths[2:8],
  'factory_assumptions_candidate.diff': paths[8:],
}
for filename, members in sets.items():
    diff=[]
    for p in members:
        diff.extend(difflib.unified_diff(original[p].decode().splitlines(keepends=True),
                                         text[p].splitlines(keepends=True),
                                         fromfile='a/'+p,tofile='b/'+p))
    (out/filename).write_text(''.join(diff))
# Detect concurrent changes to every source used as a patch base.
assert all((root/p).read_bytes()==original[p] for p in paths), 'source changed during candidate preparation'
assert digest((root/'current/models/SarAdc.slx').read_bytes()) == expected_model
manifest={
  'scope':'Temporary proposal only; no current/source/model write; no MATLAB/Windows operation.',
  'model_sha256':expected_model,
  'files':{p:{'base_sha256':digest(original[p]),'candidate_sha256':digest(text[p].encode())} for p in paths},
  'diffs':{name:digest((out/name).read_bytes()) for name in sets},
  'warning':'factory_assumptions_candidate.diff changes the P.assumptions string values returned by the factory, not just source comments. Apply only after identity gates and explicit review.',
  'profiler':'Native receipt pending independent readback; no speedup claim.',
  'M1_and_ping_pong':'M1 N8 is isolated scratch; coefficient ping-pong is not integrated.',
}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
