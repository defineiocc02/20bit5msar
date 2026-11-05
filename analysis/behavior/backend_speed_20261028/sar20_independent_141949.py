#!/usr/bin/env python3
"""Read-only A/B archive verification; no Windows/live model access."""
import hashlib,json,pathlib,sys,zipfile
import h5py,numpy as np
sys.path.extend(['/Users/zhaoyi/.cache/uv/archive-v0/0MqkZ2DmAs_9CoXi/lib/python3.12/site-packages','/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/finite_dac_review_20261028'])
from verify_as_run import read_logs,same,at
ROOT=pathlib.Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');J=ROOT/'runs/az_probe_20261028T141949Z';D=J/'validation/validation';A=ROOT/'runs/az_probe_20261028T121500Z/validation';K=ROOT/'runs/az_probe_20261028T142709Z'
def need(x,msg):
 if not x:raise AssertionError(msg)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def hashb(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
N=read(D/'receipt.json');E=read(J/'validation/entry_receipt.json');O=read(J/'receipt.json');C=read(K/'controller_recovery.json')
need(N['status']=='backend_scratch_M8_N8_N256_complete_pending_missing_and_independent_review' and N['stage']=='finished' and N['environment_cleanup']=='complete','native status')
need(E['status']=='native_returned' and E['environment_cleanup']=='complete' and E['native_cleanup_confirmed'] and E['native_markers']['check_ok'] and all(not E['native_markers'][k] for k in ['armed_present','emergency_present','missing_armed_present','missing_unwind_present']),'entry cleanup')
need(O['status']=='unsafe_native_cleanup_preserved' and not O['native_cleanup_confirmed'] and not O['path_restored'],'outer failsafe')
need(not (J/'validation/receipt.json').exists() and (D/'receipt.json').exists(),'wrong receipt path')
need(C['status']=='owned_entry_cache_and_single_path_removed' and C['matlab_pid']==N['matlab_pid']==E['matlab_pid']==27628,'recovery status')
for key,path in [('native',D/'receipt.json'),('entry',J/'validation/entry_receipt.json'),('outer',J/'receipt.json')]:need(C['original_receipt_sha256'][key]==sha(path),'recovery prior receipt '+key)
parts=C['path_before'].split(';');after=C['path_after'].split(';');target=C['target_entry_path'].replace('/','\\').lower();ix=[i for i,v in enumerate(parts) if v.replace('/','\\').lower()==target];need(len(ix)==1 and after==parts[:ix[0]]+parts[ix[0]+1:],'target-only path removal')
need(C['pwd_before']==C['pwd_after'] and C['main_model_sha256_after']==O['current_model_sha256_before']==O['current_model_sha256_after']==N['main_model_sha_expected']=='63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6','cwd/main SHA')
need(C['target_entry_sha256']==E['wrapper_sha256'] and len(C['owned_entry_cache_before'])==1 and 'no full pre-wrapper oldPath snapshot exists' in C['scope_limit'],'recovery bounds')
need(N['main_file_unchanged'] and N['global_rng_unchanged'] and N['main_workspace_unchanged'] and N['main_status']=='stopped' and N['main_dirty']=='off' and N['target_cleanup']['status']=='clear_and_restore_verified','native main/target')
need(N['profiler_status_before']['ProfilerStatus']=='off' and N['profiler_status_after']['ProfilerStatus']=='off','profiler')
need(N['missing_dependency']['status']=='pending_separate_process','missing still pending')
Z=J/'frozen_candidate.zip';need(sha(Z)==O['frozen_zip_sha256']=='3ba1b23d7e92d25801769d4c4796cc89db934ebe311400fdf6e43fe06e4b8a38','frozen zip')
with zipfile.ZipFile(Z) as z,zipfile.ZipFile(J/'candidate.zip') as a,zipfile.ZipFile(K/'candidate.zip') as rec:
 pre='sar20_backend_validation_native_v4/';pins=json.loads(z.read(pre+'candidate/SOURCE_PINS.json'))
 need(hashb(z.read(pre+'candidate/SOURCE_PINS.json'))==N['external_pins_sha256']==E['manifest_sha256_expected'],'manifest')
 need(hashb(z.read(pre+'entry/run_backend_validation_v4.m'))==E['wrapper_sha256']==O['entry_sha256'],'entry')
 for f in pins['files']:
  path=pre+'candidate/'+f['path'];need(hashb(z.read(path))==f['sha256'],'frozen candidate '+f['path'])
  if f['path']!='validation/static_check.py':need(a.read(path)==z.read(path),'as-run candidate '+f['path'])
 need(a.read(pre+'entry/run_backend_validation_v4.m')==z.read(pre+'entry/run_backend_validation_v4.m'),'as-run entry')
 wrapper=a.read('jobs/backend_validation_v4_entry_job.m').decode();recovery=rec.read('jobs/recover_backend_v4_entry_job.m').decode()
 need("receiptFile = fullfile(outdir,'validation','receipt.json')" in wrapper and "nativeFile = fullfile(job,'validation','validation','receipt.json')" in recovery,'wrapper receipt-path diagnosis')
 need("isequaln(rng,R.rng_before)" in recovery and "afterParts=parts;" not in recovery and "expectedParts=parts;expectedParts(matched)=[];" in recovery,'recovery assertion source')
arch=read(ROOT/'runs/az_probe_20261028T115303Z/resume_result/source_manifest.json')['files']
canon=lambda rs:{x['path'].replace('\\','/'):x['sha256'] for x in rs}
need(len(arch)==len(N['source_manifest'])==87 and canon(arch)==canon(N['source_manifest']),'87 production archive source identities')
need(N['candidate_inventory']['exact_match'] and N['candidate_inventory']['links_rejected'],'native inventory')
need(N['pure_gate']['status']=='native_pure_contract_pass' and N['pure_gate']['value_snapshot_pass'] and N['pure_gate']['direct_bound_valid_state_and_output_bits'],'pure native result')
for c in N['pure_gate']['cases']:
 need(c['direct']==c['bound']==c['expected'],'pure diagnostic '+c['name'])
for group in ['negative_setup','negative_event']:
 for r in N[group]:
  q=D/group/r['name'];d=read(q/'error.json');need(d['case_name']==r['name'] and d['expected']==r['expected'] and d['error_ids']==r['error_ids'] and r['expected'] in d['error_ids'] and len(d['report'])>100,'raw error '+r['name'])
  if group=='negative_setup':
   need(d['threw'] and d['setup_origin'] and 'behavior_backend_sfun' in d['report'] and (q/'bad_P.mat').exists(),'setup origin '+r['name'])
  else:
   need(d['threw_or_captured'] and d['phase']=='sim' and 'Outputs' in d['report'] and sha(q/'SarLookup.slx')==r['graph_sha256']==d['graph_sha256'] and (q/'bad_command.mat').exists() and (q/'partial_simout.mat').exists(),'event origin '+r['name'])
setup_fields={'negative_Cf':('backend/ra/Cf_f',-1),'negative_CT_reference':('backend/ct/reference_v',-1),'NI_not_boolean':('backend/ni/cap_mismatch',2),'NI_unknown':('backend/ni/unregistered',0),'NI_unsupported':('backend/ni/ra_noise',1),'AZ_negative_tau':('backend/az/write_tau_s',-1)}
for name,(field,value) in setup_fields.items():
 with h5py.File(D/'negative_setup'/name/'bad_P.mat') as f:need(f['badP/'+field][()].ravel()[0]==value,'actual bad parameter '+name)
for name,index,value in [('invalid_sign',2,2),('invalid_tag',24,-2),('AZ_off_write',22,1)]:
 with h5py.File(D/'negative_event'/name/'bad_command.mat') as f:
  a=f['invalid'][()].ravel();expected=np.zeros(26);expected[23]=1;expected[index]=value;need(same(a,expected),'actual bad command '+name)
for row in N['partial_models']:
 path=D/'partial_models'/pathlib.PureWindowsPath(row['partial_file']).parent.name/'SarLookup.slx';need(row['status']=='saved_verified' and sha(path)==row['partial_sha256'],'partial model SHA')
print_result={}
for c in N['cases']:
 name=c['name'];q=D/'cases'/name;old=A/name;n=c['records']
 for path,pin in [(q/'parameters.mat',c['input_P_sha256']),(old/'parameters.mat',c['input_P_sha256']),(q/'SarLookup.slx',c['model_sha256']),(old/'SarLookup.slx',c['model_sha256']),(old/'old_simout.mat',c['reference_simout_sha256']),(q/'old_simout.mat',c['old_simout_sha256']),(q/'new_simout.mat',c['new_simout_sha256']),(q/'new_records.mat',c['new_records_sha256'])]:need(sha(path)==pin,name+' SHA '+path.name)
 recordpins={'n8':'a7c0d279116aed17d4e1c85d9b4df1132c057f426dbe576878e49eef6bb602ad','n256':'b5453b18eac7bf32f9529dd42cbf02c6e66045fe8902973f905268108c6f56a7'};need(sha(old/'old_records.mat')==recordpins[name],'reference records')
 with h5py.File(q/'parameters.mat') as f:
  p=f['P'];Ncase=int(p['N'][()].item());first=int(p['first_id'][()].item());epoch=int(p['epoch'][()].item());tau=np.asarray(p['front/tau_dac_s'][()]);fs=float(p['fs_hz'][()].item());freq=float(p['input/frequency_hz'][()].item());need(Ncase==n and first==4 and epoch==1 and np.all(tau==1e-9),'P case')
 logs=[read_logs(path) for path in [old/'old_simout.mat',q/'old_simout.mat',q/'new_simout.mat']];need(len(logs[0])==len(logs[1])==len(logs[2])==30 and set(logs[0])==set(logs[1])==set(logs[2]),name+' log inventory')
 for nm in logs[0]:
  a0,a1,a2=[l[nm] for l in logs]
  for z in [a1,a2]:need(z['class']==a0['class'] and z['storage_shape']==a0['storage_shape'] and same(z['time'],a0['time']) and same(z['data'],a0['data']),name+' bit '+nm)
 def rec(path,key):
  with h5py.File(path) as f:return {k:f[key][k][()] for k in f[key]}
 r0=rec(old/'old_records.mat','oldRecord');r1=rec(q/'old_records.mat','oldRecord');r2=rec(q/'new_records.mat','newRecord');need(set(r0)==set(r1)==set(r2),'record fields')
 for field in r0:need(same(r0[field],r1[field]) and same(r0[field],r2[field]),name+' record bits '+field)
 L=logs[2];rdy=L['record_ready_log'];record=L['record_log'];code=L['code_log'];t=rdy['time'];take=rdy['data'][:,0]==1;rr=at(record,t[take],'record');cc=at(code,t[take],'code');nready=len(rr)
 need(nready==c['old_all_ready_count']==c['new_all_ready_count']==n+4 and np.all(rr[:,5]==1) and np.array_equal(rr[:,3],np.arange(n+4)) and np.all(rr[:,4]==epoch),'ready count/ID/epoch/valid')
 need(same(rr.T,r2['all_ready_raw']) and same(cc.T,r2['all_ready_code20']) and same(t[take].reshape(1,-1),r2['all_ready_time_s']),'ready data vs simout')
 selected=(rr[:,3]>=first)&(rr[:,3]<first+n);need(int(selected.sum())==n and np.array_equal(rr[selected,3],np.arange(first,first+n)) and np.all(rr[selected,4]==epoch),'selected IDs')
 need(same(rr[selected].T,r2['selected_raw']) and same(cc[selected].T,r2['selected_code20']) and same(t[take][selected].reshape(1,-1),r2['selected_time_s']),'selected vs simout')
 for prefix in ['old','new']:
  timing=read(q/(prefix+'_simout_timing.json'));need(timing['stage']=='sim_returned' and timing['update_s']==c[prefix+'_update_s'] and timing['sim_s']==c[prefix+'_sim_s'],'timing receipt')
 print_result[name]={'N':n,'all_ready':nready,'selected_id_first':first,'selected_id_last':first+n-1,'epoch':epoch,'fs_hz':fs,'fin_hz':freq,'tau_s':1e-9,'p_sha256':c['input_P_sha256'],'slx_sha256':c['model_sha256'],'reference_simout_sha256':c['reference_simout_sha256'],'old_simout_sha256':c['old_simout_sha256'],'new_simout_sha256':c['new_simout_sha256'],'new_records_sha256':c['new_records_sha256'],'log_count':len(logs[0]),'all_three_30_logs_bit_equal':True,'all_ready_raw_code_time_equal':True,'old_update_s':c['old_update_s'],'old_sim_s':c['old_sim_s'],'new_update_s':c['new_update_s'],'new_sim_s':c['new_sim_s']}
out={'status':'archived_AB_independently_rechecked','cases':print_result,'frozen_zip_sha256':sha(Z),'native_receipt_sha256':sha(D/'receipt.json'),'entry_receipt_sha256':sha(J/'validation/entry_receipt.json'),'outer_receipt_sha256':sha(J/'receipt.json'),'recovery_sha256':sha(K/'controller_recovery.json'),'pure_cases':len(N['pure_gate']['cases']),'setup_negatives':[{k:r[k] for k in ['name','expected','error_ids']} for r in N['negative_setup']],'event_negatives':[{k:r[k] for k in ['name','expected','error_ids','phase']} for r in N['negative_event']],'saved_partial_models':len(N['partial_models']),'missing_dependency':N['missing_dependency'],'outer_bad_receipt_path_detected':True,'targeted_recovery_only':True,'recovery_rng_verified_by_native_assertion_not_after_snapshot':True}
print(json.dumps(out,indent=2,ensure_ascii=False))
