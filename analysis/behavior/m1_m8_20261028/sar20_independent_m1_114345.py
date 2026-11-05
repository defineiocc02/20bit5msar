#!/usr/bin/env python3
"""Independent offline audit of archived M1/M8 N8 scratch; never access live model."""
from pathlib import Path
import hashlib,io,json,math,sys,zipfile
import h5py,numpy as np
from scipy.io import loadmat
ROOT=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(ROOT/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import at,fingerprint,graph,need,pdiff,read_logs,same,sha,val
JOB=ROOT/'runs/az_probe_20261028T114345Z';D=JOB/'m1_validation'
R=json.loads((D/'receipt.json').read_text());O=json.loads((JOB/'receipt.json').read_text());entry=json.loads((D/'entry_receipt.json').read_text())
need(O['status']=='native_v3_scratch_result_preserved' and R['status']=='scratch_actual_N8_m8_bit_gate_m1_physical_gate_complete' and O['validation_status']==R['status'] and R['stage']=='finished','native status')
need(not R['main_integrated'] and not R['long_m8_gate_requested'] and R['long_m8_gate']=='not_requested','scope flags')
need(sha(JOB/'frozen_candidate.zip')==O['archive_sha256'] and sha(D/'candidate_asrun.zip')==R['candidate_zip_sha256'],'archive hash')
need(O['current_model_sha256_before']==O['current_model_sha256_after']==R['main_model_sha_expected']==sha(D/'graph_change/before.slx'),'main snapshot hash')
with zipfile.ZipFile(D/'candidate_asrun.zip') as z,zipfile.ZipFile(JOB/'frozen_candidate.zip') as frozen:
 names=z.namelist();fnames=frozen.namelist();need(len(names)==len(set(names)) and len(fnames)==len(set(fnames)),'duplicate zip members')
 pins_bytes=z.read('SOURCE_PINS.json');pins=json.loads(pins_bytes);psha=hashlib.sha256(pins_bytes).hexdigest()
 need(psha==R['external_pins_sha256']==entry['external_pins_sha256'],'source pins hash')
 need(pins['base_model_sha256']==R['main_model_sha_expected'],'base model pin')
 need(set(names)=={x['candidate'] for x in pins['files']}|{'SOURCE_PINS.json'},'source inventory mismatch')
 need(set('candidate/'+n for n in names)<=set(fnames),'frozen inventory mismatch')
 for n in names:need(z.read(n)==frozen.read('candidate/'+n),'frozen vs as-run bytes '+n)
 for p in pins['files']:need(hashlib.sha256(z.read(p['candidate'])).hexdigest()==p['candidate_sha256'],'candidate source hash '+p['candidate'])
 need(hashlib.sha256(z.read('validation/validate_m1_m8_native.m')).hexdigest()==entry['validator_sha256'],'validator pin')
 need(hashlib.sha256(frozen.read('entry/run_m1_m8_v3.m')).hexdigest()==O['entry_sha256']==entry['wrapper_sha256'],'wrapper pin')
 source_hashes={x['candidate']:x['candidate_sha256'] for x in pins['files']};source_file_count=len(names)
source_base=ROOT/'runs/behavior_47c22b65-fdff-402b-b315-ea0599df6891'
main_manifest=json.loads((source_base/'source_manifest.json').read_text())['files']
base_summary=json.loads((source_base/'summary.json').read_text());need(sha(source_base/'source.zip')==base_summary['source_zip_sha256'],'archived base source zip SHA')
with zipfile.ZipFile(source_base/'source.zip') as basezip:
 basefiles={x['path'].replace('\\','/'):x['sha256'] for x in main_manifest};need(len(basefiles)==len(main_manifest) and set(basezip.namelist())==set(basefiles),'archived base source inventory')
 for path,digest in basefiles.items():need(hashlib.sha256(basezip.read(path)).hexdigest()==digest,'archived base source SHA '+path)
canon=lambda rows:{x['path'].replace('\\','/'):x['sha256'] for x in rows}
need(canon(main_manifest)==canon(R['current_source_manifest']),'native expected main source manifest differs archived manifest')
for p in pins['files']:
 if p['base']:need(canon(main_manifest)[p['base']]==p['base_sha256'],'candidate baseline pin '+p['base'])
oldb,olde,oldc=graph(D/'graph_change/before.slx');newb,newe,newc=graph(D/'graph_change/after.slx')
need(set(oldb)==set(newb) and olde==newe and oldc==newc,'scratch graph block/edges/config differ')
changed={k:(oldb[k],newb[k]) for k in oldb if oldb[k]!=newb[k]}
need(set(changed)=={'189','191','192'},'scratch graph changed other blocks')
expected_changes={'189':('Gain','8:-1:1',"behavior_tracking_param(P,DecodeP,'weights')"),'191':('Bias','-36',"behavior_tracking_param(P,DecodeP,'bias')"),'192':('Gain','DecodeP.tracking_step_ra_v/(8*DecodeP.ra_gain)',"DecodeP.tracking_step_ra_v/(behavior_tracking_param(P,DecodeP,'M')*DecodeP.ra_gain)")}
for sid,(key,a,b) in expected_changes.items():
 x,y=changed[sid];need(x[:2]==y[:2] and x[2].get(key)==a and y[2].get(key)==b and {k for k in set(x[2])|set(y[2]) if x[2].get(k)!=y[2].get(k)}=={key},'scratch graph parameter '+sid)
ref={'off':('behavior_c5a4d0b8-7e34-4a92-b698-5bf72067ab09','dc674b7cf13f31fd3f8c226437e6cb837053545f3786fd7eff36c4bd52654555','225355ef3b1a8cf6c9e921ad0e36e7478cb71afa776b11f75966edf5138e4f85'),
     '1ns':('behavior_8165ddcc-971e-49a6-938b-ad2fb6dd9603','a2142dc1d8d79b0625b3ff86ef11ee68296930d77adcb03efb37aeb341a447c2','cf2d9a1edab4b1eaf658e05972f481c68ed07a5b809a20502e5451bdac7d7f41')}
ref_logs={}
for name,(folder,ph,sh) in ref.items():
 q=ROOT/'runs'/folder;need(sha(q/'parameters.mat')==ph and sha(q/'simout.mat')==sh,'reference pinned data '+name)
 sm=json.loads((q/'summary.json').read_text());need(sm['status']=='complete' and sm['simulation_completed'] and sm['config_sha256']==ph,'reference terminal '+name)
 ref_logs[name]=read_logs(q/'simout.mat')

def calendar(f):
 g=f['P/groups'];ts=[float(f[x][()].item()) for x in g['time_s'][()].ravel()];tick=[float(f[x][()].item()) for x in g['tick'][()].ravel()];types=[]
 for x in g['events'][()].ravel():
  typ=f[x]['type'];types.append([''.join(map(chr,f[r][()].ravel())) for r in typ[()].ravel()] if h5py.check_dtype(ref=typ.dtype) is not None else [''.join(map(chr,typ[()].ravel()))])
 need(len(types)==len(ts)==len(tick)==49,'group inventory');return ts,tick,types

def decode_digital(row,dig,M):
 d1,d2,dt=map(int,row[:3]);c,f=divmod(d1,32);v1=(32*c+2*f-1039)*dig['vref_v']/1024-17*dig['vref_v']/1024
 db=np.array([(d2>>i)&1 for i in range(11,-1,-1)]);d2v=(dig['d2_offset_ra_v']+np.sum(np.asarray(dig['d2_weights_ra_v']).ravel()*db))/dig['ra_gain']
 if M==1:
  need(dt in (0,128),'valid M1 DT padding');dtweight=2*(dt//128)-1
 else:
  b=np.array([(dt>>i)&1 for i in range(7,-1,-1)]);dtweight=np.sum(np.arange(8,0,-1)*(2*b-1))/8
 dtv=dig['tracking_step_ra_v']*dtweight/dig['ra_gain'];unsat=((v1+d2v)+dtv)*(2**20/dig['fsr_diff_v'])+2**19
 rounded=math.floor(unsat+.5) if unsat>=0 else math.ceil(unsat-.5)
 return int(np.clip(rounded,0,2**20-1)),float(dtv)

results={};Ls={};Pdiffs={}
for case in R['cases']:
 name=case['name'];M=int(case['M']);tau='off' if name.endswith('off') else '1ns';dir=D/name
 need(case['actual_error']=='','simulation error '+name)
 modelb,modele,modelc=graph(dir/'SarM1.slx')
 need(set(modelb)==set(newb) and modele==newe and modelc==newc,name+' case graph/solver differs')
 case_changed={k for k in newb if newb[k]!=modelb[k]}
 need(case_changed=={'105','123'},name+' case graph block changes')
 for k in case_changed:
  x,y=newb[k],modelb[k];need(x[:2]==y[:2] and {v for v in set(x[2])|set(y[2]) if x[2].get(v)!=y[2].get(v)}=={'AttributesFormatString'},name+' unexpected case parameter '+k)
 for file,key in [('SarM1.slx','model_sha256'),('parameters.mat','parameters_sha256'),('simout.mat','simout_sha256'),('actual_observation.mat','observation_sha256')]:need(sha(dir/file)==case[key],name+' hash '+file)
 with h5py.File(dir/'parameters.mat') as f,h5py.File(dir/'actual_observation.mat') as o:
  with zipfile.ZipFile(dir/'SarM1.slx') as model:
   mx=model.read('simulink/modelWorkspace.mxarray');need(mx[:4]==b'\x00\x01IM' and mx[4:8]==b'\x00'*4,name+' unsupported workspace format')
   header=b'MATLAB 5.0 MAT-file'.ljust(116,b' ')+b'\x00'*8+mx[:4]
   ws=loadmat(io.BytesIO(header+mx[8:]),struct_as_record=False,squeeze_me=True)['__function_workspace__'][0,0]
  def getpath(o,path):
   for key in path.split('/'):o=getattr(o,key)
   return o
  def equal_data(a,b):
   a=np.asarray(a).squeeze();b=np.asarray(b).squeeze()
   if a.shape!=b.shape:return False
   if a.dtype.kind=='f' and b.dtype.kind=='f' and a.dtype==b.dtype:return a.tobytes()==b.tobytes()
   return np.array_equal(a,b)
  ws_fields=['N','first_id','epoch','n_cycles','Ts_s','input/amplitude_v','input/frequency_hz','input/offset_v','input/phase_rad',
   'front/plan','front/tau_dac_s','backend/dac_coupling/enabled','backend/dac_coupling/tau_dac_s','backend/ra/A0','backend/ra/UGB_hz',
   'transport/enabled','debug/adi_enabled','debug/adi_max_points','xFE0','xBK0','xSC0','xTX0','xREF0']
  digkeys=['schema','vref_v','fsr_diff_v','ra_gain','d2_weights_ra_v','d2_offset_ra_v','tracking_step_ra_v','dither_enabled','dither_seed','dither_amplitude_v','calibration_mode','tracking_mode','az_mode','coefficient_source']+(['tracking_count'] if M==1 else [])
  ws_fields+=['digital/'+k for k in digkeys]
  if M==1:ws_fields+=['control/tracking_count']
  for key in ws_fields:
   actual=np.asarray(getpath(ws.P,key)).squeeze();stored=np.asarray(val(f,'P/'+key)).squeeze();need(equal_data(actual,stored),name+' model workspace vs saved P '+key)
  for key in digkeys:
   need(equal_data(getpath(ws.DecodeP,key),val(f,'P/digital/'+key)),name+' DecodeP workspace '+key)
  need(np.asarray(ws.TrainCaptureFile).size==0,name+' unexpected capture')
  need(fingerprint(f,f['P'],{})==fingerprint(o,o['actual/P'],{}),name+' observation P differs')
  need(val(f,'P/N')==8 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and val(f,'P/n_cycles')==14 and val(f,'P/Ts_s')==2e-7 and val(f,'P/input/frequency_hz')==97656.25,name+' P window')
  need(val(f,'P/transport/enabled') and val(f,'P/debug/adi_enabled') and math.isinf(val(f,'P/debug/adi_max_points')) and not val(f,'P/training/enabled') and not val(f,'P/cal_cfg/enabled') and not val(f,'P/frozen/enabled'),name+' P controls')
  need(not val(f,'P/digital/dither_enabled') and val(f,'P/digital/az_mode')=='off',name+' decode flags')
  need(np.all(np.asarray(val(f,'P/front/tau_dac_s'))==(0. if tau=='off' else 1e-9)) and np.all(np.asarray(val(f,'P/backend/dac_coupling/tau_dac_s'))==(0. if tau=='off' else 1e-9)) and val(f,'P/backend/dac_coupling/enabled') and bool(val(f,'P/ni/dac_settling'))==(tau=='1ns'),name+' DAC tau')
  need((M==1 and val(f,'P/control/tracking_count')==1 and val(f,'P/digital/tracking_count')==1) or (M==8 and 'P/control/tracking_count' not in f and 'P/digital/tracking_count' not in f),name+' M')
  ts,ticks,types=calendar(f)
  for i,g in enumerate(ws.P.groups):
   ge=np.atleast_1d(g.events);gt=[x.type for x in ge]
   need(g.time_s==ts[i] and g.tick==ticks[i] and gt==types[i],name+' model workspace event '+str(i+1))
  dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v','d2_weights_ra_v','tracking_step_ra_v']}
  expected=np.array([cy*2e-7+t for cy in range(14) for t in ts]);budget={k:sum(x.count(k) for x in types) for k in ['d2_decide','ta_compare','ta_feedback','ta_idle']}
  need([budget[k] for k in ['d2_decide','ta_compare','ta_feedback']]==[12,M,M-1],name+' calendar budget')
  if M==1:
   need(budget['ta_idle']==14 and [ticks[i] for i,x in enumerate(types) if 'ta_idle' in x]==list(range(305,340,5)) and ticks[[i for i,x in enumerate(types) if 'ta_compare' in x][0]]==300 and ticks[[i for i,x in enumerate(types) if 'tracking_end' in x][0]]==340,name+' M1 idle schedule')
 L=read_logs(dir/'simout.mat');Ls[name]=L;need(len(L)==30,name+' logger count')
 e=L['event_log']['data'];te=L['event_log']['time'];need(e.shape==(686,2) and np.array_equal(e[:,0],np.repeat(np.arange(14),49)) and np.array_equal(e[:,1],np.tile(np.arange(1,50),14)) and same(te,expected),name+' event inventory/time')
 for key in ['raw_log','ready_log','record_log','record_ready_log','code_log','back_log','control_log','dt_log']:
  need(same(te,L[key]['time']),name+' event logger time '+key)
 tw=L['adi_wire_log']['time'];w=L['adi_wire_log']['data'];need(w.shape==(672,58),name+' ADI inventory')
 E=at(L['event_log'],tw,name+' ADI-event');B=at(L['back_log'],tw,name+' ADI-back');C=at(L['control_log'],tw,name+' ADI-control')
 need(np.array_equal(E[:,0],np.repeat(np.arange(14),48)) and np.array_equal(E[:,1],np.tile(np.arange(1,49),14)),name+' ADI cycle/group')
 cumulative=np.cumsum(np.array([[x.count(k) for k in ['d2_decide','ta_compare','ta_feedback']] for x in types[:48]]),axis=0)
 group_compare=[i+1 for i,x in enumerate(types) if 'ta_compare' in x][0]
 for cy in range(14):
  rows=np.flatnonzero(E[:,0]==cy);need(np.array_equal(w[rows,51:54],cumulative),name+' observed physical counters cycle '+str(cy))
  if M==1:
   need(np.all(w[rows,44:51]==0),name+' TA feedback signs cycle '+str(cy))
   g=E[rows,1];q=rows[g==group_compare][0];latched=C[q,6]
   need(latched in (0,128) and (latched/128)==float(B[q,1]>=0) and np.all(C[rows[g<group_compare],6]==0) and np.all(C[rows[g>=group_compare],6]==latched),name+' physical compare/DT '+str(cy))
 adcix=np.flatnonzero(L['ready_log']['data'][:,0]==1);rxix=np.flatnonzero(L['record_ready_log']['data'][:,0]==1)
 need(np.all(np.isin(L['ready_log']['data'],[0,1])) and np.all(np.isin(L['record_ready_log']['data'],[0,1])) and len(adcix)==14 and len(rxix)==12,name+' ready count')
 adc=L['raw_log']['data'][adcix];rx=L['record_log']['data'][rxix];codes=L['code_log']['data'][rxix,0];dtlog=L['dt_log']['data'][rxix,0]
 need(np.array_equal(e[adcix,1],np.full(14,47)) and np.array_equal(adc[:,3],np.arange(14)) and np.all(adc[:,4:6]==1) and np.array_equal(e[rxix,1],np.full(12,49)) and np.array_equal(rx[:,3],np.arange(12)) and np.all(rx[:,4:6]==1) and same(rx,adc[:12]),name+' ADC/RX ID-valid word join')
 z=[decode_digital(row,dig,M) for row in rx];need(np.array_equal(codes,np.array([v[0] for v in z])) and np.array_equal(dtlog,np.array([v[1] for v in z])),name+' RX public decode/dt')
 select=(rx[:,3]>=4)&(rx[:,3]<=11);need(np.count_nonzero(select)==8,name+' selected window')
 with h5py.File(dir/'actual_observation.mat') as o:
  for key,data in [('all_ready_raw6',rx),('all_ready_time_s',te[rxix]),('window_raw6',rx[select]),('window_code20',codes[select]),('window_time_s',te[rxix][select])]:
   need(np.array_equal(np.asarray(val(o,'actual/'+key)).ravel(),np.asarray(data).ravel()),name+' observed '+key)
  for key in ['actual_event_time_gate','actual_adi_time_gate','actual_counter_gate','exact_ids_epoch','graph_decode_gate']:need(val(o,'actual/'+key)==1,name+' observed gate '+key)
  if M==1:
   for key in ['actual_ta_signs_zero','dt_word_gate','actual_decision_trace_gate','actual_idle_hit_gate','declared_schedule_gate']:need(val(o,'actual/'+key)==1,name+' observed gate '+key)
 need(np.array_equal(rx[select],np.array(case['records'])) and np.array_equal(codes[select],np.array(case['code20'])) and np.array_equal(te[rxix][select],np.array(case['record_time_s'])),name+' receipt values')
 if M==8:
  old=ref_logs[tau];legacy=set(old)-{'adi_wire_log'}
  need(len(legacy)==29 and legacy==set(L)-{'adi_wire_log'},name+' logger inventory')
  for k in legacy:need(old[k]['class']==L[k]['class'] and old[k]['storage_shape']==L[k]['storage_shape'] and same(old[k]['time'],L[k]['time']) and same(old[k]['data'],L[k]['data']),name+' logger bits '+k)
  need({x['name'] for x in case['legacy_bit_logs']}==legacy and all(x['time_bits'] and x['data_bits'] for x in case['legacy_bit_logs']),name+' receipt logger gate')
  diff=pdiff(ROOT/'runs'/ref[tau][0]/'parameters.mat',dir/'parameters.mat');need(set(diff)=={'P/debug/adi_enabled','P/debug/adi_max_points'},name+' M8 P changes');Pdiffs[name]=diff
 else:
  diff=pdiff(D/('m8_'+tau)/'parameters.mat',dir/'parameters.mat');need(set(diff)=={'P/adc_groups/events','P/cal_cfg/public_cfg/tracking_mode','P/calendar/type','P/control/tracking_count','P/digital/tracking_count','P/groups/events','P/schedule/groups/events'},name+' M1 P changes');Pdiffs[name]=diff
 results[name]={'M':M,'tau_dac_s':0. if tau=='off' else 1e-9,'calendar_budget':budget,'codes':codes[select].astype(int).tolist(),'raw6':rx[select].astype(int).tolist(),'record_times_s':te[rxix][select].tolist(),'ADC_ready_count':len(adcix),'RX_ready_count':len(rxix),'actual_counter_checked_cycles':14,'actual_ADI_points':len(tw),'model_workspace_core_P_and_DecodeP_checked':True,'model_sha256':case['model_sha256'],'P_sha256':case['parameters_sha256'],'simout_sha256':case['simout_sha256'],'observation_sha256':case['observation_sha256']}
for tau in ['off','1ns']:
 a=Ls['m8_'+tau];b=Ls['m1_'+tau];wa=a['adi_wire_log']['data'];wb=b['adi_wire_log']['data'];ea=at(a['event_log'],a['adi_wire_log']['time'],'m8 first');eb=at(b['event_log'],b['adi_wire_log']['time'],'m1 first');xa=at(a['back_log'],a['adi_wire_log']['time'],'m8 back');xb=at(b['back_log'],b['adi_wire_log']['time'],'m1 back');ca=at(a['control_log'],a['adi_wire_log']['time'],'m8 control');cb=at(b['control_log'],b['adi_wire_log']['time'],'m1 control')
 ia=np.flatnonzero((ea[:,0]==0)&(ea[:,1]==38))[0];ib=np.flatnonzero((eb[:,0]==0)&(eb[:,1]==38))[0]
 need(same(xa[ia],xb[ib]) and int(ca[ia,6])//128==int(cb[ib,6])//128,'cold first comparison '+tau)
 need(np.any(wa[ia+1,44:51]!=0) and np.all(wb[ib+1,44:51]==0),'cold first feedback divergence '+tau)
need(R['main_file_unchanged'] and R['global_rng_unchanged'] and R['main_workspace_unchanged'] and R['main_status']=='stopped' and R['main_dirty']=='off' and R['environment_cleanup']=='complete','native final guard')
text=(JOB/'events.jsonl').read_text();need('cleanupDone' in text and 'restoreDone' in text and 'onCleanup' in text,'expected recorded cleanup warnings absent')
out={'verifier_sha256':sha(Path(__file__)),'receipt_sha256':sha(D/'receipt.json'),'outer_receipt_sha256':sha(JOB/'receipt.json'),'frozen_candidate_sha256':sha(JOB/'frozen_candidate.zip'),'asrun_candidate_sha256':sha(D/'candidate_asrun.zip'),'source_pins_sha256':psha,'candidate_verified_files':source_file_count,'base_runtime_verified_files':len(main_manifest),'factory_main_sha256':R['main_model_sha_expected'],'scratch_graph_delta_SIDs':list(changed),'scratch_graph_blocks':len(oldb),'scratch_graph_edges':len(olde),'case_graph_diff_vs_installed_only_annotation_SIDs':['105','123'],'P_differences':Pdiffs,'M8_legacy_29_time_and_data_bits_equal':True,'M1_M8_cold_precompare_equal_and_following_feedback_differs':True,'cases':results,'native_final_checks':{'main_file_unchanged':R['main_file_unchanged'],'global_rng_unchanged':R['global_rng_unchanged'],'main_workspace_unchanged':R['main_workspace_unchanged'],'status':R['main_status'],'dirty':R['main_dirty'],'environment_cleanup':R['environment_cleanup']},'warnings':'Native command log includes two onCleanup destructor warnings for destroyed cleanupDone and restoreDone. Offline cannot independently establish live state.','scope':'Actual N8 scratch only, 29 legacy logs excluding enabled ADI observer; no current M1 integration, N256 performance or PDK claim.'}
print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
