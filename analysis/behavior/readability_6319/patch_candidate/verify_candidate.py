from pathlib import Path
import hashlib
import json
import shutil
import subprocess

root=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
out=Path('/tmp/sar20_reading_patch_6319')
manifest=json.loads((out/'manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'current/models/SarAdc.slx')==manifest['model_sha256']
assert all(sha(root/p)==v['base_sha256'] for p,v in manifest['files'].items()), 'Patch base changed; regenerate before review.'
tree=out/'verify_tree'
if tree.exists():shutil.rmtree(tree)
shutil.copytree(out/'original',tree)
patch_output={}
for name in manifest['diffs']:
 assert sha(out/name)==manifest['diffs'][name]
 proc=subprocess.run(['patch','--batch','--forward','-p1','-i',str(out/name)],cwd=tree,text=True,capture_output=True,check=True)
 patch_output[name]=proc.stdout.strip()
assert all((tree/p).read_bytes()==(out/'candidate'/p).read_bytes() for p in manifest['files'])
# Changes labelled comments-only must not change any non-comment, nonempty MATLAB line.
for p in ['current/src/model/behavior_dac_coupling_configuration.m',
          'current/src/physics/behavior_backend_stage.m','current/src/physics/behavior_backend_step.m',
          'current/src/control/behavior_sar_step.m','current/src/transport/sar20_lvds_rx_step.m',
          'config/make_adi_cases.m']:
 def code(path):return [s for line in path.read_text().splitlines() if (s:=line.strip()) and not s.startswith('%')]
 assert code(out/'original'/p)==code(out/'candidate'/p),p
# Evidence constraints are read from saved artifacts; this verifier does not run MATLAB.
a0p=root/'analysis/behavior/local_static_20261028/sar20_independent_gain3_120823.json'
a0=json.loads(a0p.read_text()); points=a0['point_results']
assert points['A1e4_zero']['code20']-points['A1e4_negative']['code20']==4
assert points['A1e5_zero']['code20']-points['A1e5_negative']['code20']==1
assert points['Ainf_zero']['code20']-points['Ainf_negative']['code20']==1
abp=root/'analysis/behavior/event_lookup_20261028/review.json'
ab=json.loads(abp.read_text()); n=next(c for c in ab['case_results'] if c['case']=='n256')
assert n['old_new_all_30_bit_equal'] and n['old_new_log_count']==30
assert n['timing']['old_sim_s']==136.1479 and n['timing']['new_sim_s']==136.9086034
profilep=root/'runs/az_probe_20261028T122805Z/validation/receipt.json'
profile=json.loads(profilep.read_text()); assert profile['status']=='profiled_scratch_N256_complete_pending_independent_review'
assert profile['sim_profiled_wall_s']==182.0560521 and profile['all_30_time_and_data_bits_equal']
m1p=root/'analysis/behavior/m1_m8_20261028/sar20_independent_m1_114345.json'
m1=json.loads(m1p.read_text());assert all(m1['cases'][k]['calendar_budget']['ta_compare']==1 and m1['cases'][k]['calendar_budget']['ta_feedback']==0 for k in ('m1_off','m1_1ns'))
for link in [a0p,abp,profilep,m1p]: assert link.is_file()
# The factory-assumptions proposal intentionally alters P output: it is isolated from comment-only patches.
assert (out/'original/config/adc_parameters.m').read_bytes() != (out/'candidate/config/adc_parameters.m').read_bytes()
report={'scope':'Temporary-tree patch round trip and read-only evidence crosscheck; no model compile or simulation.',
        'model_sha256':manifest['model_sha256'],'project_file_sha256_still_matches_bases':True,
        'temporary_patch_roundtrip_pass':True,'source_comment_noncomment_lines_identical':True,
        'factory_assumptions_alters_generated_P':True,'patch_tool_output':patch_output,
        'evidence_sha256':{str(p.relative_to(root)):sha(p) for p in [a0p,abp,profilep,m1p]},
        'A0_endpoint_code_deltas':[4,1,1],
        'N256_old_new_wall_s':[n['timing']['old_sim_s'],n['timing']['new_sim_s']],
        'profiled_wall_s':profile['sim_profiled_wall_s'],'profile_pending_independent_readback':True,
        'M1_provenance':'isolated scratch N8, not current integration or N256 performance'}
(out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Temporary patch round trip, base hashes, comments-only check, and evidence checks passed.')
