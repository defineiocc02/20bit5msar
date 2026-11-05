#!/usr/bin/env python3
"""Offline validation of saved zero-window resume, original failed midpoint, and prior anchors."""
import hashlib,json,sys,zipfile
from pathlib import Path
import h5py,numpy as np
ROOT=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(ROOT/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import decode,fingerprint,need,pdiff,read_calendar,read_logs,same,sha,val
job=ROOT/'runs/az_probe_20261028T115303Z';RDIR=job/'resume_result';orig=ROOT/'runs/az_probe_20261028T113931Z/refine_result';prior=ROOT/'runs/az_probe_20261028T112407Z/zero_result';pre=ROOT/'runs/az_probe_20261028T110315Z/static_result'
R=json.loads((RDIR/'receipt.json').read_text());O=json.loads((job/'receipt.json').read_text());OLD=json.loads((orig/'receipt.json').read_text());pt=OLD['points'][0]
need(R['status']=='actual_refined_multicode_windows_no_missing_code_claim' and R['stage']=='complete' and O['result_status']==R['status'] and O['status']=='actual_zero_resume_preserved' and sha(RDIR/'receipt.json')==O['result_receipt_sha256'],'resume status/pin')
need(sha(RDIR/'sar20_zero_resume_job.m')==O['source_sha256'],'resume job pin')
need(sha(RDIR/'independent_110315.json')==O['independent_110315_sha256'] and sha(RDIR/'independent_112407.json')==O['independent_112407_sha256'],'prior independent audit pins')
need(sha(RDIR/'SarAdc_factory.slx')==sha(orig/'SarAdc_factory.slx')==sha(prior/'SarAdc_factory.slx')==sha(pre/'SarAdc_factory.slx')==R['model_sha256']==O['current_model_sha256_before']==O['current_model_sha256_after'],'factory snapshot model pin')
need(sha(RDIR/'source_manifest.json')==sha(orig/'source_manifest.json')==sha(prior/'source_manifest.json')==R['source_manifest_sha256'] and sha(RDIR/'source.zip')==R['source_zip_sha256'] and sha(orig/'source.zip')==OLD['source_zip_sha256'],'source provenance pins')
manifest=json.loads((RDIR/'source_manifest.json').read_text())['files'];pins={v['path'].replace('\\','/'):v['sha256'] for v in manifest};need(len(pins)==len(manifest),'duplicate manifest path')
with zipfile.ZipFile(RDIR/'source.zip') as a,zipfile.ZipFile(orig/'source.zip') as b:
 need(set(a.namelist())==set(b.namelist())==set(pins) and len(a.namelist())==len(set(a.namelist())) and len(b.namelist())==len(set(b.namelist())),'archive inventory')
 for name,h in pins.items():need(hashlib.sha256(a.read(name)).hexdigest()==h and a.read(name)==b.read(name),'old/new source bytes '+name)
need(OLD['status']=='failed_partial_preserved' and OLD['error_identifier']=='MATLAB:cellfun:NotAScalarOutput' and len(OLD['points'])==1 and pt['status']=='failed' and pt['simulation_error']=='' and pt['global_rng_unchanged'],'old failure classification')
original_map={'receipt.json':orig/'receipt.json','source_manifest.json':orig/'source_manifest.json','sar20_zero_refine_job.m':orig/'sar20_zero_refine_job.m','P.mat':orig/'point_001/P.mat','signals.mat':orig/'point_001/signals.mat','observed.mat':orig/'point_001/observed.mat','failed_simout.mat':orig/'point_001/failed_simout.mat'}
for name,path in original_map.items():need(sha(path)==sha(RDIR/'original_113931'/name),'copied original differs '+name)
for name,k in [('P.mat','P_mat_sha256'),('signals.mat','signals_sha256'),('observed.mat','observed_sha256'),('failed_simout.mat','failed_simout_sha256')]:need(sha(original_map[name])==pt[k],'old receipt pin '+name)
mid=R['recovered_midpoint'];need(sha(original_map['receipt.json'])==mid['original_receipt_sha256'] and sha(RDIR/'recovered_midpoint.mat')==mid['recovered_record_sha256'],'recovered original/record pin')
need(pt['held_input_v']==[] and pt['held_minus_requested_v']==[],'old held fields not empty')
with h5py.File(original_map['observed.mat']) as f:
 need(f['obs/held_input_v'].attrs.get('MATLAB_empty')==1 and f['obs/held_minus_requested_v'].attrs.get('MATLAB_empty')==1,'original MAT held field should be empty')
need(sha(prior/'point_001/P.mat')=='be1d4d1c447a474d23639d470e6031901035a0fde8da5bc93b7c95d274bf9640' and sha(prior/'point_001/signals.mat')=='735364a0e1d7fd9a6166bf6915d8ee446cef0bfa567621f3e66fc57057bf6983' and sha(pre/'preflight_capped_simout.mat')=='f2fbddd8b8f6571277e164a21665c5a32808bf78039686fc587cbb3e06c9678a','anchor pins')
with h5py.File(RDIR/'Pzero_reconstructed.mat') as a,h5py.File(prior/'Pzero_reconstructed.mat') as b:
 need(fingerprint(a,a['Pzero'],{})==fingerprint(b,b['Pzero'],{}),'reconstructed zero P differs prior')
with h5py.File(prior/'point_001/P.mat') as f:
 times,groups,budget=read_calendar(f);dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v','d2_weights_ra_v','tracking_step_ra_v']}
 need(val(f,'P/backend/ra/A0')==10000 and val(f,'P/backend/ra/UGB_hz')==1.2e9 and not val(f,'P/transport/enabled') and not val(f,'P/backend/dac_coupling/enabled'),'baseline scope')

def signals(path):
 with h5py.File(path) as h:
  seq=[h[r] for r in h['#subsystem#/MCOS'][()].ravel()];s=h['signals'];names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];out=[]
  for i,d in enumerate(seq):
   if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
   ns,t=seq[i-11],seq[i-9]
   if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
   count=int(ns[()].item())
   if count>0 and t.shape==(1,count) and (count==1 or d.shape[-1]==count):
    cls=d.attrs.get('MATLAB_class',b'');cls=cls.decode() if isinstance(cls,bytes) else str(cls)
    out.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,count)).T,'class':cls})
  need(len(names)==len(out)==9,'expected 9 saved time series');return dict(zip(names,out))
keep=['back_log','code_log','control_log','event_log','front_log','raw_log','ready_log','record_log','record_ready_log']
oldlogs=signals(original_map['signals.mat']);oldsim=read_logs(original_map['failed_simout.mat'])
for n in keep:need(oldlogs[n]['class']==oldsim[n]['class'] and same(oldlogs[n]['time'],oldsim[n]['time']) and same(oldlogs[n]['data'],oldsim[n]['data']),'midpoint nine-log vs failed simulation '+n)
zero=read_logs(pre/'preflight_capped_simout.mat');zerofull=read_logs(pre/'preflight_full_simout.mat');neg=signals(prior/'point_001/signals.mat')
for n in keep:need(zero[n]['class']==zerofull[n]['class'] and same(zero[n]['time'],zerofull[n]['time']) and same(zero[n]['data'],zerofull[n]['data']),'zero full/capped mismatch '+n)
expected_t=np.array([i*2e-7+x for i in range(5) for x in times]);L={};rows={}
def inspect(logs,x,code,label):
 need(set(keep)<=set(logs),label+' missing logger');e=logs['event_log']['data'];t=logs['event_log']['time']
 need(e.shape==(240,2) and np.array_equal(e[:,0],np.repeat(np.arange(5),48)) and np.array_equal(e[:,1],np.tile(np.arange(1,49),5)) and same(t,expected_t),label+' event calendar')
 for n in keep:need(same(t,logs[n]['time']),label+' logger time '+n)
 a=logs['ready_log']['data'][:,0];b=logs['record_ready_log']['data'][:,0];need(np.all(np.isin(a,[0,1])) and same(a,b),label+' ready')
 ix=np.flatnonzero(a==1);need(len(ix)==5 and np.array_equal(e[ix,0],np.arange(5)) and np.all(e[ix,1]==47),label+' readiness')
 raw=logs['raw_log']['data'][ix];rec=logs['record_log']['data'][ix];c=logs['code_log']['data'][ix,0];held=logs['front_log']['data'][ix,0]
 need(same(raw,rec) and np.array_equal(raw[:,3],np.arange(5)) and np.all(raw[:,4:6]==1) and np.all(held==x),label+' actual valid/raw/held')
 need(np.all(c==code) and all(decode(r,dig)==int(q) for r,q in zip(raw,c)),label+' actual code/public decode')
 return {'voltage_v':x,'held_input_v':float(held[-1]),'raw6':raw[-1].astype(int).tolist(),'code20':int(c[-1]),'ready_time_s':float(t[ix[-1]]),'all_ready_raw6':raw.astype(int).tolist(),'all_ready_code20':c.astype(int).tolist(),'all_ready_time_s':t[ix].tolist()}
L['zero']=zero;rows['zero']=inspect(zero,0.,524289,'zero')
L['negative']=neg;rows['negative']=inspect(neg,-3.0517578125e-8,524285,'negative')
L['midpoint']=oldlogs;rows['midpoint']=inspect(oldlogs,-1.52587890625e-8,524285,'midpoint')
for k in ['voltage_v','held_input_v','raw6','code20','all_ready_raw6','ready_time_s']:need(rows['midpoint'][k]==mid[k],'recovered midpoint mismatch '+k)
with h5py.File(RDIR/'recovered_midpoint.mat') as f:
 for k in ['voltage_v','held_input_v','raw6','code20','all_ready_raw6','ready_time_s']:
  need(np.array_equal(np.asarray(val(f,'recovered/'+k)).ravel(),np.asarray(rows['midpoint'][k]).ravel()),'recovered MAT '+k)
with h5py.File(original_map['observed.mat']) as f:
 for k in ['raw6','code20','all_ready_raw6','all_ready_code20','all_ready_time_s','ready_time_s']:
  need(np.array_equal(np.asarray(val(f,'obs/'+k)).ravel(),np.asarray(rows['midpoint'][k]).ravel()),'original observed '+k)
need(R['prior_simulations_repeated'] is False and R['original_failure_preserved'] is True and len(R['points'])==3 and O['new_point_count']==3,'resume new point count')
Pdiff={};expected_x=[-7.62939453125e-9,-3.814697265625e-9,-1.9073486328125e-9]
for i,(x,point) in enumerate(zip(expected_x,R['points']),1):
 folder=RDIR/f'point_{i:03d}';name=f'point_{i:03d}';need(json.loads((folder/'point.json').read_text())==point,name+' point receipt differs')
 need(point['index']==i and point['voltage_v']==x and point['status']=='valid' and point['simulation_error']=='' and point['global_rng_unchanged'] and point['post_sim_identity_pass'] and not point['missing_logs'],name+' status')
 for file,key in [('P.mat','P_mat_sha256'),('signals.mat','signals_sha256'),('observed.mat','observed_sha256')]:need(sha(folder/file)==point[key],name+' hash '+file)
 need(point['model_sha256']==R['model_sha256'] and point['source_manifest_sha256']==R['source_manifest_sha256'] and point['source_zip_sha256']==R['source_zip_sha256'],name+' identity')
 diff=pdiff(prior/'point_001/P.mat',folder/'P.mat');need(set(diff)=={'P/front/input/offset_v','P/input/offset_v','P/xFE0'},name+' extra P differences');Pdiff[name]=diff
 with h5py.File(folder/'P.mat') as f:
  need(val(f,'P/input/offset_v')==x and val(f,'P/front/input/offset_v')==x and val(f,'P/input/amplitude_v')==0 and val(f,'P/N')==1 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and val(f,'P/n_cycles')==5 and val(f,'P/Ts_s')==2e-7,name+' P window/input')
 L[name]=signals(folder/'signals.mat');rows[name]=inspect(L[name],x,524285,name)
 for key in ['raw6','code20','held_input_v','ready_time_s','all_ready_raw6','all_ready_code20','all_ready_time_s']:need(rows[name][key]==point[key],name+' receipt value '+key)
 with h5py.File(folder/'observed.mat') as f:
  for key in ['raw6','code20','held_input_v','ready_time_s','all_ready_raw6','all_ready_code20','all_ready_time_s']:
   need(np.array_equal(np.asarray(val(f,'obs/'+key)).ravel(),np.asarray(rows[name][key]).ravel()),name+' observed '+key)
  need(val(f,'obs/held_minus_requested_v')==0 and val(f,'obs/public_decode_code20')==524285 and val(f,'obs/event_groups_per_id')==48,name+' observed detail')
Pdiff['midpoint']=pdiff(prior/'point_001/P.mat',original_map['P.mat']);need(set(Pdiff['midpoint'])=={'P/front/input/offset_v','P/input/offset_v','P/xFE0'},'midpoint extra P diff')
with h5py.File(original_map['P.mat']) as f:need(val(f,'P/input/offset_v')==rows['midpoint']['voltage_v'] and val(f,'P/front/input/offset_v')==rows['midpoint']['voltage_v'] and val(f,'P/N')==1 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1,'midpoint P')
# Actual controller traces; no separately logged comparator output.
first={};zeroctl=L['zero']['control_log']['data'][-48:];negctl=L['negative']['control_log']['data'][-48:]
for name in ['midpoint','point_001','point_002','point_003']:
 ctl=L[name]['control_log']['data'][-48:];need(np.array_equal(ctl[:,[0,4,5,6]],negctl[:,[0,4,5,6]]),name+' negative controller branch differs')
 first[name]={}
 for col,field in [(0,'trial'),(4,'D1raw'),(5,'D2raw'),(6,'DTraw')]:
  d=np.flatnonzero(zeroctl[:,col]!=ctl[:,col])
  if len(d):
   q=int(d[0]);first[name][field]={'group':q+1,'relative_ns':times[q]*1e9,'zero':float(zeroctl[q,col]),'probe':float(ctl[q,col])}
 need(first[name]['D1raw']['group']==3 and first[name]['D2raw']['group']==16,name+' first control branch')
samples=sorted(rows.values(),key=lambda x:x['held_input_v']);need([a['code20'] for a in samples]==[524285]*5+[524289],'sample endpoint ordering')
transitions=[(a,b) for a,b in zip(samples,samples[1:]) if b['code20']-a['code20']>1]
need(len(transitions)==1,'unique sampled multicode bracket');a,b=transitions[0];span=b['held_input_v']-a['held_input_v']
w=R['narrowest_multicode_window'];need(a['voltage_v']==w['low']['voltage_v'] and b['voltage_v']==w['high']['voltage_v'] and span==w['held_span_v']==R['target_actual_held_window_v']==7.8125e-6/4096 and w['code_delta']==4,'actual narrowed bracket')
need(not R['pending_intervals'] and not R['local_widths'] and R['dnl']=='not_measured' and R['inl']=='not_measured' and R['window_codes_observed']==[524285,524289] and not R['intermediate_codes_observed'],'scope flags')
cleanup=json.loads((RDIR/'cleanup.json').read_text());need(cleanup==R['cleanup'] and cleanup['status']=='complete' and cleanup['cwd_restored'] and cleanup['path_restored_exactly'] and not cleanup['issues'] and R['model_source_workspace_loggers_unchanged'],'native cleanup or identity reports failed')
cmdlog=(job/'events.jsonl').read_text();need('onCleanup' not in cmdlog,'recorded onCleanup warning requires review')
out={'script_sha256':sha(Path(__file__)),'inner_receipt_sha256':sha(RDIR/'receipt.json'),'outer_receipt_sha256':sha(job/'receipt.json'),'cleanup_sha256':sha(RDIR/'cleanup.json'),'source_manifest_sha256':R['source_manifest_sha256'],'old_source_zip_sha256':sha(orig/'source.zip'),'new_source_zip_sha256':sha(RDIR/'source.zip'),'verified_source_files':len(pins),'verified_original_copy_files':{n:sha(p) for n,p in original_map.items()},'model_sha256':R['model_sha256'],'original_failure':{'status':OLD['status'],'identifier':OLD['error_identifier'],'point_status':pt['status'],'simulation_error':pt['simulation_error'],'held_fields_were_empty':True,'nine_saved_series_equal_failed_simout':True},'P_differences_vs_112407_actual_negative':Pdiff,'calendar_budget':budget,'samples':rows,'controller_first_vs_zero':first,'narrowest_actual_window':w,'recorded_cleanup':cleanup,'retention_scope':'New points save nine original native timeseries, P, observed and point receipt; full simout is not saved. 113931 failed simout is retained; only nine saved time series were independently compared.','nonreplay_scope':'No-replay is asserted by native receipt and guarded source; this offline audit does not independently observe the complete host execution history.','scope':'Two codes only at measured sample inputs. No interior sample within final bracket; absence of 524286-288 at sampled inputs is not proof of missing codes, code widths, monotonicity, DNL, or INL. Zero P is a later reconstruction.'}
print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
