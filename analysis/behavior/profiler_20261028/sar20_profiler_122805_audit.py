#!/usr/bin/env python3
"""Offline 30-stream and profiler counter audit; no simulation."""
import hashlib,json,sys,zipfile
from pathlib import Path
import h5py,numpy as np
ROOT=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(ROOT/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import decode,need,read_logs,same,sha,val
J=ROOT/'runs/az_probe_20261028T122805Z';D=J/'validation';B=ROOT/'runs/az_probe_20261028T121500Z/validation/n256';archive=ROOT/'runs/behavior_47c22b65-fdff-402b-b315-ea0599df6891';fine=ROOT/'runs/az_probe_20261028T115303Z/resume_result'
R=json.loads((D/'receipt.json').read_text());O=json.loads((J/'receipt.json').read_text());old_job=json.loads((B.parent/'receipt.json').read_text());old_case=next(x for x in old_job['cases'] if x['name']=='n256')
need(R['status']=='profiled_scratch_N256_complete_pending_independent_review' and R['stage']=='finished' and O['native_status']==R['status'] and O['status']=='native_profile_result_preserved' and sha(D/'receipt.json')==O['native_receipt_sha256'],'profile result status/pin')
need(sha(J/'frozen_candidate.zip')==O['frozen_zip_sha256'],'frozen entry archive')
with zipfile.ZipFile(J/'frozen_candidate.zip') as z:
 p='sar20_profile_n256_scratch_v2/';m=json.loads(z.read(p+'SOURCE_PINS.json'));need(len(z.namelist())==3 and set(z.namelist())=={p+'SOURCE_PINS.json',p+'README.md',p+'profile_n256_scratch.m'},'frozen inventory')
 for r in m['files']:need(hashlib.sha256(z.read(p+r['path'])).hexdigest()==r['sha256'],'frozen source '+r['path'])
 need(hashlib.sha256(z.read(p+'profile_n256_scratch.m')).hexdigest()==R['entry_sha256']==O['entry_sha256'],'profile entry source')
need(sha(D/'parameters.mat')==sha(B/'parameters.mat')==R['P_sha256']==old_case['input_P_sha256'],'P pin')
need(sha(D/'SarLookup.slx')==sha(B/'SarLookup.slx')==R['scratch_input_sha256']==old_case['model_sha256'],'scratch SLX pin')
need(sha(B/'old_simout.mat')==R['old_reference_sha256']==old_case['old_simout_sha256'] and sha(D/'simout.mat')==R['simout_sha256'],'simout pin')
need(sha(fine/'SarAdc_factory.slx')==R['main_model_sha256']==O['current_model_sha256_before']==O['current_model_sha256_after'],'main factory snapshot')
manifest=json.loads((archive/'source_manifest.json').read_text())['files'];canon=lambda rows:{x['path'].replace('\\','/'):x['sha256'] for x in rows};pins=canon(manifest)
need(len(pins)==len(manifest)==87 and pins==canon(R['project_source_manifest'])==canon(old_job['source_manifest']) and sha(archive/'source_manifest.json')=='008981fd68c840e2a52c25bdea7609f7684220d8a0ccbd00e0f29fbce4b8710e','archived 87 source manifest')
with zipfile.ZipFile(archive/'source.zip') as z:
 need(len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(pins),'source archive inventory')
 for n,h in pins.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'archive source hash '+n)
need(pins['current/src/control/behavior_event_source.m']==R['event_source_sha256'],'original event source pin')
with h5py.File(D/'parameters.mat') as f:
 need(val(f,'P/N')==256 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and val(f,'P/n_cycles')==262 and val(f,'P/Ts_s')==2e-7 and val(f,'P/input/frequency_hz')==97656.25 and val(f,'P/transport/enabled') and np.all(val(f,'P/front/tau_dac_s')==1e-9) and val(f,'P/backend/dac_coupling/enabled') and not val(f,'P/digital/dither_enabled') and val(f,'P/digital/az_mode')=='off','run configuration')
 g=f['P/groups'];times=[float(f[x][()].item()) for x in g['time_s'][()].ravel()];need(len(times)==49,'group count')
 dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v','d2_weights_ra_v','tracking_step_ra_v']}
old=read_logs(B/'old_simout.mat');new=read_logs(D/'simout.mat');need(len(old)==len(new)==30 and set(old)==set(new),'30 logger inventory')
for k in old:
 a,b=old[k],new[k];need(a['class']==b['class'] and a['storage_shape']==b['storage_shape'] and same(a['time'],b['time']) and same(a['data'],b['data']),'logger bits '+k)
def struct_rows(path,group,fields):
 with h5py.File(path) as f:
  g=f[group]
  if isinstance(g,h5py.Dataset) and g.attrs.get('MATLAB_empty')==1:return []
  refs={k:g[k][()].ravel() for k in fields};n=len(next(iter(refs.values())));need(all(len(v)==n for v in refs.values()),'MAT struct shape')
  out=[]
  for i in range(n):
   row={}
   for k in fields:
    x=f[refs[k][i]];a=x[()];cls=x.attrs.get('MATLAB_class',b'')
    row[k]=''.join(map(chr,np.asarray(a).ravel())) if cls==b'char' else np.asarray(a).ravel()[0].item()
   out.append(row)
  return out
comp=struct_rows(D/'log_compare.mat','comparison',['name','time_bits','data_bits']);need(len(comp)==30 and {x['name'] for x in comp}==set(new) and all(x['time_bits'] and x['data_bits'] for x in comp),'saved log_compare')
e=new['event_log']['data'];t=new['event_log']['time'];tt=np.array([i*2e-7+x for i in range(262) for x in times]);need(e.shape==(12838,2) and np.array_equal(e[:,0],np.repeat(np.arange(262),49)) and np.array_equal(e[:,1],np.tile(np.arange(1,50),262)) and same(t,tt),'actual 262*49 event calendar')
for k in ['record_log','record_ready_log','code_log']:need(same(t,new[k]['time']),'record event axis '+k)
ready=new['record_ready_log']['data'][:,0];need(np.all(np.isin(ready,[0,1])),'ready binary');ix=np.flatnonzero(ready==1);raw=new['record_log']['data'][ix];code=new['code_log']['data'][ix,0];rt=t[ix]
need(len(ix)==260 and np.array_equal(raw[:,3],np.arange(260)) and np.all(raw[:,4:6]==1) and np.all(e[ix,1]==49) and np.array_equal(e[ix,0],raw[:,3]+2),'actual RX raw/epoch/valid/timing')
need(all(decode(a,dig)==int(c) for a,c in zip(raw,code)),'public codes')
take=(raw[:,3]>=4)&(raw[:,3]<260);need(np.count_nonzero(take)==256,'selected record count');selraw=raw[take];selcode=code[take];seltime=rt[take]
with h5py.File(D/'records.mat') as f:
 for k,arr in [('all_ready_raw',raw),('all_ready_code20',code),('all_ready_time_s',rt),('selected_raw',selraw),('selected_code20',selcode),('selected_time_s',seltime)]:
  need(np.array_equal(np.asarray(val(f,'records/'+k)).ravel(),np.asarray(arr).ravel()),'saved records '+k)
before=struct_rows(D/'profile_before.mat','beforeInfo/FunctionTable',['FunctionName','CompleteName','NumCalls','TotalTime']);after=struct_rows(D/'profile_after.mat','afterInfo/FunctionTable',['FunctionName','CompleteName','NumCalls','TotalTime']);rows=struct_rows(D/'profile_delta.mat','rows',['name','complete_name','calls','inclusive_s']);top=struct_rows(D/'profile_delta.mat','top',['name','complete_name','calls','inclusive_s']);need(len(before)==0 and len(after)==len(rows)==572 and len(top)==80,'profiler table inventory')
index={x['CompleteName']:x for x in after};need(len(index)==len(after),'duplicate CompleteName')
for x in rows:
 y=index.get(x['complete_name']);need(y is not None and x['name']==y['FunctionName'] and x['calls']==y['NumCalls'] and x['inclusive_s']==y['TotalTime'] and x['calls']>=0 and x['inclusive_s']>=0,'profile after-minus-before '+x['complete_name'])
with h5py.File(D/'profile_before.mat') as f,h5py.File(D/'profile_after.mat') as g:
 need(f['beforeInfo/FunctionHistory'].attrs.get('MATLAB_empty')==1,'before history expected empty')
 history=g['afterInfo/FunctionHistory'];history_shape=list(history.shape);history_tail=history[-1,:]
 need(history_shape==[5000000,4] and np.any(history_tail!=0),'history buffer shape/end')
 calls_sum=sum(int(row['NumCalls']) for row in after)
 need(calls_sum==7796574,'profile call aggregate')
need(all(rows[i]['inclusive_s']>=rows[i+1]['inclusive_s'] for i in range(len(rows)-1)) and top==rows[:80] and top==R['profile_top'],'stored delta/top sorting/receipt')
required={}
for key in R['required_function_names']:
 hits=[r for r in rows if key.lower() in r['complete_name'].lower() and r['calls']>0];need(hits,key+' missing');required[key]=hits
need(all(R['required_function_observed']) and len(R['required_function_rows'])==sum(map(len,required.values())),'required native rows')
for k,v in required.items():
 for x in v:need(x in R['required_function_rows'],'required receipt '+k)
need(R['log_count']==30 and R['all_30_time_and_data_bits_equal'] and R['selected_records']==256 and R['all_ready_records']==260,'receipt raw summary')
need(R['profiler_status_before']['ProfilerStatus']=='off' and R['profiler_status_after']['ProfilerStatus']=='off' and O['profiler_status_after']['ProfilerStatus']=='off' and all(R[k] for k in ['main_file_unchanged','global_rng_unchanged','main_workspace_unchanged']) and R['environment_cleanup']=='complete' and O['path_restored'] and O['cwd_restored'] and O['main_status']=='stopped' and O['main_dirty']=='off' and not O['candidate_loaded_files'],'native restoration')
files={n:sha(D/n) for n in ['profile_before.mat','profile_after.mat','profile_delta.mat','records.mat','log_compare.mat']}
report={'verifier_sha256':sha(Path(__file__)),'receipt_sha256':sha(D/'receipt.json'),'model_sha256':R['main_model_sha256'],'scratch_sha256':R['scratch_input_sha256'],'P_sha256':R['P_sha256'],'old_simout_sha256':R['old_reference_sha256'],'new_simout_sha256':R['simout_sha256'],'source_files_verified':len(pins),'all_30_Time_Data_class_shape_bits_equal':True,'all_ready_records':len(ix),'selected_records':int(np.count_nonzero(take)),'selected_code_sha256_u32le':hashlib.sha256(np.asarray(selcode,dtype='<u4').tobytes()).hexdigest(),'selected_time_first_last_s':[float(seltime[0]),float(seltime[-1])],'actual_event_count':len(t),'profile_before_function_rows':len(before),'profile_after_function_rows':len(after),'profile_delta_rows':len(rows),'after_function_history_shape':history_shape,'after_function_history_last_row_nonzero':True,'sum_all_function_invocations':calls_sum,'all_delta_rows_match_after_minus_before':True,'required_function_rows':required,'top_20':top[:20],'update_unprofiled_wall_s':R['update_unprofiled_wall_s'],'sim_profiled_wall_s':R['sim_profiled_wall_s'],'prior_unprofiled_sim_wall_s':old_case['old_sim_s'],'native_profiler_status_before':R['profiler_status_before'],'native_profiler_status_after':R['profiler_status_after'],'native_restoration':{'main_file_unchanged':R['main_file_unchanged'],'main_workspace_unchanged':R['main_workspace_unchanged'],'global_rng_unchanged':R['global_rng_unchanged'],'environment_cleanup':R['environment_cleanup'],'wrapper_path_restored':O['path_restored'],'wrapper_cwd_restored':O['cwd_restored'],'wrapper_candidate_loaded_files':O['candidate_loaded_files']},'computed_file_hashes_not_pinned_by_native_receipt':files,'limits':['Profile inclusive times overlap; do not sum, attribute hardware cycles or claim stable speedup.','The profiler appends global history/counters; final off does not restore historical profiler data. FunctionHistory is full at the 5,000,000-event cap, so complete call chronology is not established.','inmem/which and source SHA do not prove same-path compiled cache freshness.','No MATLAB rerun or live Windows/current state access.']}
print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
