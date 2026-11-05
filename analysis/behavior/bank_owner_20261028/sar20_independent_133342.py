#!/usr/bin/env python3
"""Read-only archived 133342 scratch audit; never runs a model or reads live state."""
import hashlib,json,pathlib,re,sys,zipfile
import h5py,numpy as np
sys.path.extend(['/Users/zhaoyi/.cache/uv/archive-v0/0MqkZ2DmAs_9CoXi/lib/python3.12/site-packages','/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020/analysis/behavior/finite_dac_review_20261028'])
from verify_as_run import read_logs, fingerprint, same, at
ROOT=pathlib.Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');J=ROOT/'runs/az_probe_20261028T133342Z';OLD=ROOT/'runs/az_probe_20261028T132220Z';ORIG=ROOT/'runs/az_probe_20261028T130247Z';FROZEN=pathlib.Path('/tmp/sar20_pp_finalize_132220_v1_20261028.zip')
def need(ok,msg):
 if not ok: raise AssertionError(msg)
def H(b):return hashlib.sha256(b).hexdigest()
def sha(p):return H(p.read_bytes())
def read(p):return json.loads(p.read_text())
R=read(J/'receipt.json');E=read(J/'entry_final.json');pre=read(J/'entry_preflight.json');S=read(J/'source_manifest_actual.json')
need(R['status']=='SCRATCH_N8_FINALIZED_PREQUALIFIED_ROUTER_PASS_NOT_INTEGRATED' and R['stage']=='complete' and not R['main_integrated'],'terminal status')
need(E['status']=='exit_state_verified' and E['critical_ok'] and E['inner_cleanup_ok'] and not E['owned_scratch_still_loaded'] and not E['candidate_cache_after'] and not E['new_candidate_cache_remaining'],'cleanup')
for key in ['path_restored','cwd_restored','rng_unchanged','main_model_file_unchanged','main_model_stopped_clean','main_public_workspace_unchanged','main_decodeP_unchanged','main_capture_variable_unchanged','main_logger_inventory_unchanged','main_model_parameters_unchanged']:
 need(E[key], 'exit '+key)
need(not E['main_private_P_compared'] and not E['production_or_satk_cache_cleared'],'exit scope')
need(R['current_model_sha256']=='63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6' and R['current_model_unchanged'] and R['prior_artifacts_unchanged'],'main and prior')
need(not R['prior_preflight_rerun'] and R['prior_preflight_reused'] and not R['previous_functionname_or_wiring_edits_repeated'] and not R['consumed_holdout_rows_opened'],'prior scope')
need(sha(FROZEN)=='5aae17832d31dd112aebe5462d687f65e336f07ae6007757be521732fd1ce33b','frozen zip')
with zipfile.ZipFile(FROZEN) as z,zipfile.ZipFile(J/'candidate.zip') as a:
 prefix='pingpong_132220_finalize_v1/'; manifest=json.loads(z.read(prefix+'manifest.json'));lock=json.loads(z.read(prefix+'source_lock.json'));prod=json.loads(z.read(prefix+'production_source_lock.json'));satk=json.loads(z.read(prefix+'satk_source_lock.json'));runner=z.read(prefix+'run_pp_finalize_n8.m').decode();
 namesa=a.namelist();need(len(namesa)==len(set(namesa)),'candidate archive duplicate')
 actual={n for n in namesa if n.startswith(prefix)};expected={n for n in z.namelist() if n.startswith(prefix)};need(actual<=expected and all(a.read(n)==z.read(n) for n in actual),'as-run candidate bytes')
 missing=sorted(expected-actual);need(len(actual)==34 and len(missing)==6,'candidate inventory')
 need(a.read('jobs/pp_finalize_132220_n8_job.m')==z.read('entry/pp_finalize_132220_n8_job.m'),'wrapper as-run')
 need(H(a.read('jobs/pp_finalize_132220_n8_job.m'))=='333c9052025ad178083ee3eb22b505a4feeedd2c481a5ba2ea1f05945e7c4445','entry digest')
 need(pre['entry_sha256']==H(z.read(prefix+'run_pp_finalize_n8.m'))=='5d4352d4c985664eafe8cc9fd7be628126353e2eb52cb8cdff3e6a87f522abec' and pre['manifest_sha256']==H(z.read(prefix+'manifest.json')),'entry receipt field')
 for field,lockf in [('candidate',lock),('production',prod),('satk_files',satk)]:
  def rowkey(x):return (x['path'].replace('\\','/').lower(),x['sha256'])
  got=S[field];want=lockf['files'];need(len(got)==len(want),'manifest length '+field)
  gotitems={(p,h) for p,h in map(rowkey,got)};need(len(gotitems)==len(got),'manifest duplicate '+field)
  for q in want:
   rp=q['path'].replace('\\','/').lower();needle=('/'+rp,q['sha256']);need(sum(p.endswith(needle[0]) and h==needle[1] for p,h in gotitems)==1,'source identity '+field+' '+rp)
 for x in lock['files']:need(prefix+x['path'] in actual and H(a.read(prefix+x['path']))==x['sha256'],'asrun locked source '+x['path'])
 # Recheck the 132220 and 130247 pins without touching their sources.
 n0=runner.index("names={'receipt.json'"); n1=runner.index('    pins={',n0); n2=runner.index('    for k=1:numel(names)',n1)
 rel=re.findall(r"'([^']+)'",runner[n0:n1]);pins=re.findall(r"'([0-9a-f]{64})'",runner[n1:n2]);need(len(rel)==len(pins)==13,'prior pins inventory')
 for name,pin in zip(rel,pins):need(sha(OLD/name)==pin,'prior pin '+name)
 for name,pin in [('receipt.json','d3080e24d295d611d4a93daadd8eee7c1fb1ff363597aec81d1ed13a7eb6142e'),('partial/SarPP_partial.slx','5413a38f33d813b3f5ac390828c030a53d7b862926554f905a5f6d86da62e325'),('pure_preflight/fixture_not_qualified.json','218589323cbe80b7ed077e3ee36f1663e7cb5f8f4e4ad02c938ad8a5c2c5a6b9')]:need(sha(ORIG/name)==pin,'original pin '+name)
need(sha(J/'fixture_not_qualified.json')==R['prior']['fixture_sha256'],'negative fixture copy')
need(S['production_source_count']==87 and S['satk_source_count']==223 and len(S['candidate'])==23 and S['candidate_cached_before_start']==False and S['cached_function_bytes_independently_verified']==False,'source scope')
need(R['post_load_source_satk_verified'] and R['public_workspace_identity'],'post load source/workspace gate')
C=['factory_base','factory_off','rx_nominal','rx_old_frozen','rx_bank_on']; rk=['factory_base_s','factory_off_s','nominal_s','frozen_s','on_s']; rows={}; param={};logs={}
for case,key in zip(C,rk):
 q=J/case; r=read(q/'receipt.json');need(r==R[key] and r['status']=='completed_saved','case receipt '+case)
 slx=q/('SarPPBase.slx' if case=='factory_base' else 'SarPP.slx')
 for f,k in [(q/'parameters.mat','parameters_sha256'),(slx,'model_sha256'),(q/'simout.mat','simout_sha256'),(q/'source_manifest_actual.json','source_manifest_sha256')]:need(sha(f)==r[k],case+' '+k)
 need(sha(q/'source_manifest_actual.json')==sha(J/'source_manifest_actual.json'),'case manifest identity')
 for k in ['source_integrity_before','source_integrity_after','public_after_update_matches','public_after_sim_matches']:need(r[k],case+' '+k)
 with h5py.File(q/'parameters.mat','r') as f:
  need(set(['P','DecodeP'])<=set(f),'saved P')
  dm=fingerprint(f,f['DecodeP'],{});pm=fingerprint(f,f['P/digital'],{});need(dm==pm,'DecodeP=P.digital '+case)
  param[case]={'DecodeP_fingerprint':dm,'N':int(f['P/N'][()].item()),'first_id':int(f['P/first_id'][()].item()),'epoch':int(f['P/epoch'][()].item()),'bank_enabled':bool(f['P/bank/enabled'][()].item()),'frozen_enabled':bool(f['P/frozen/enabled'][()].item())}
 rows[case]={'parameters_sha256':r['parameters_sha256'],'model_sha256':r['model_sha256'],'source_manifest_sha256':r['source_manifest_sha256'],'simout_sha256':r['simout_sha256'],'seconds':r['seconds'],**param[case]}
 logs[case]=read_logs(q/'simout.mat')
need(all(x['N']==8 and x['first_id']==4 and x['epoch']==1 for x in rows.values()),'N/first/epoch')
need([x['bank_enabled'] for x in rows.values()]==[False,False,False,False,True] and [x['frozen_enabled'] for x in rows.values()]==[False,False,False,True,False],'case modes')
with h5py.File(J/'rx_bank_on/parameters.mat') as f,h5py.File(J/'rx_old_frozen/parameters.mat') as g:
 caches=[f[r] for r in f['P/bank/slots/cache'][()].ravel()];vers=[float(f[r][()].item()) for r in f['P/bank/slots/version'][()].ravel()];need(vers==[1,2],'slots versions')
 cf=g['P/frozen/cache']; fields=['h','h_by_slice','plan','public_cfg','coefficient_sha256','public_cfg_sha256']
 for field in fields:
  h=[fingerprint(f,c[field],{}) for c in caches];h.append(fingerprint(g,cf[field],{}));need(len(set(h))==1,'cache equivalence '+field)
 cache_hash={field:fingerprint(g,cf[field],{}) for field in fields};schedule=f['P/bank/command_schedule'][()].ravel().tolist();need(schedule==[147,1,1,2,2,4],'scheduled switch')
oldnames=['adc_executed_log','back_log','code_log','control_log','d1_log','d2_log','dt_log','event_log','transport_frame_log','frame_ready_log','front_log','paired_ref_log','transport_pin_trace_log','raw_log','ready_log','record_log','record_ready_log','ref_queue_log','sample_ready_log','transport_trace_rows_log','train_ref_log','adi_wire_log','aperture_log','az_commit_log','az_route_log','dac_ra_pre_log','cal_status_log','cal_fit_log','frozen_log','nominal_code_log'];need(len(set(oldnames))==30,'old names')
def eqlog(a,b,name):
 x=logs[a][name];y=logs[b][name];need(x['class']==y['class'] and x['storage_shape']==y['storage_shape'] and same(x['time'],y['time']) and same(x['data'],y['data']),a+' vs '+b+' '+name)
for n in oldnames:eqlog('factory_base','factory_off',n)
for n in oldnames:
 if n!='code_log':eqlog('rx_nominal','rx_bank_on',n)
on=logs['rx_bank_on'];fr=logs['rx_old_frozen'];nom=logs['rx_nominal'];off=logs['factory_off']
for n in ['record_log','record_ready_log']:eqlog('rx_bank_on','rx_old_frozen',n)
t=on['record_ready_log']['time'];ready=on['record_ready_log']['data'][:,0];need(np.all(np.diff(t)>0) and np.all(np.isin(ready,[0,1])),'RX time/ready')
for n in ['record_log','code_log','bank_code_valid_log','bank_meta_log']:need(same(t,on[n]['time']),'ON timeline '+n)
raw=on['record_log']['data'];valid=on['bank_code_valid_log']['data'][:,0];meta=on['bank_meta_log']['data'];code=on['code_log']['data'][:,0];sel=ready==1; rr=raw[sel]; mm=meta[sel];cc=code[sel]; v=valid[sel]
need(np.array_equal(rr[:,3],np.arange(12)) and np.all(rr[:,4]==1) and np.all(rr[:,5]==1),'ready ID/epoch/valid')
need(np.array_equal(v,rr[:,5]) and np.all(valid[~sel]==0),'nonready valid')
need(np.array_equal(mm[:,2:5],rr[:,3:6]) and np.all(mm[:,7]==0),'RX tags/fault status')
expectedslots=np.where(rr[:,3]<4,1,2);need(np.array_equal(mm[:,5],expectedslots) and np.array_equal(mm[:,6],expectedslots) and np.any(meta[:,8]==1),'version/slot/publish')
want=sel&(raw[:,3]>=4)&(raw[:,3]<12)&(raw[:,5]==1);need(int(want.sum())==8,'N8 selected')
fcode=at(fr['code_log'],t[sel],'frozen same ready')[:,0];ncode=at(nom['code_log'],t[sel],'nominal same ready')[:,0];need(same(cc,fcode),'old frozen codes bit')
delta=cc-ncode;need(np.any(delta[4:]!=0),'qualified h changes selected code')
# Root yout signals in MATLAB's serialized sigstream (no reconstructed axis).
def root_series(path):
 with h5py.File(path) as f:
  seq=[f[r] for r in f['#subsystem#/MCOS'][()].ravel()];arr=[g for g in seq if isinstance(g,h5py.Group) and {'Elements','FileName','Version'}<=set(g)];need(len(arr)==1,'yout dataset ambiguous')
  elements=arr[0]['Elements'][()].ravel();need(len(elements)==3,'root port count');out={}
  for ref in elements:
   e=f[ref];bp=''.join(chr(int(v)) for v in f[e['BlockPath'][()].ravel()[0]][()].ravel());v=e['Values'];w=int(v['SignalAttributes/Dimension'][()].item());di=int(v['DataR2'][()].item());ti=int(v['TimeR2'][()].item())
   def stream(idx,width):
    g=f['#sigstream#'][str(idx)];n=int(g['#length#'][()].item());need(int(g['#sampleSize#'][()].item())==8*width,'stream element width');b=g['#data#'][()].tobytes();need(len(b)>=n*width*8,'stream byte length');return np.frombuffer(b,dtype='<f8',count=n*width).copy().reshape(n,width)
   data=stream(di,w);tm=stream(ti,1)[:,0];need(len(tm)==len(data) and np.all(np.diff(tm)>=0),'root stream axis');out[bp.split('/')[-1]]={'time':tm,'data':data}
  need(set(out)=={'Code20','CodeValid','CodeMeta'},'root names');return out
ro=root_series(J/'factory_off/simout.mat');rn=root_series(J/'rx_bank_on/simout.mat')
need(same(at(ro['Code20'],off['code_log']['time'],'off root code'),off['code_log']['data']),'OFF root code')
need(np.all(ro['CodeValid']['data']==0),'OFF root valid')
om=off['bank_meta_log'];need(same(at(ro['CodeMeta'],om['time'],'off root meta'),om['data']),'OFF root meta')
need(np.all(np.isnan(om['data'][:,[0,2,3,4]])) and same(om['data'][:,1],om['time']) and np.all(om['data'][:,5:]==0),'OFF meta contract')
for name,expected in [('Code20',cc[:,None]),('CodeValid',v[:,None]),('CodeMeta',mm)]:need(same(at(rn[name],t[sel],'ON root '+name),expected),'ON ready root '+name)
need(all(x['rejected'] and x['outer_identifier']=='Simulink:Parameters:InvParamSetting' for x in R['negative_updates'].values()) and len(R['negative_updates'])==6,'negative update receipt')
need(R['explicit_off_gate']['old_30_logs_bit_equal'] and R['numeric']['on_29_other_logs_bit_equal'],'native bit gate receipt')
need(not R['numeric']['distinct_h_effect_proven'] and not R['numeric']['drain_proven'] and not R['numeric']['background_training_implemented'] and not R['numeric']['root_on_nonready_hold_or_independent_clock_pulse_verified'] and not R['numeric']['rx_fault_injection_verified'] and not R['numeric']['old_no_bank_factory_entry_proven'] and not R['numeric']['product_accepted'] and not R['numeric']['current_promoted'],'limits')
for x in ['final_root_read.txt','final_transport_read.txt','final_parent_read.txt','final_fpga_read.txt','final_calibration_read.txt','final_root_check.txt','final_transport_check.txt','final_parent_check.txt','final_fpga_check.txt','final_calibration_check.txt']:
 q=(J/'final_graph_readback'/x).read_text();need(q.startswith('status: ok') or q.startswith('status: warnings') or q.startswith('status: healthy'),'graph response '+x);need('severity: error' not in q.lower(),'graph error '+x)
G=read(J/'final_graph_readback/actual_input_route_gate.json');need(G['status']=='all_required_connections_read_back' and not G['fault_injection_tested'] and not G['consumer_drain_proven'],'graph scope')
out={'status':'independent_archived_scratch_readback_pass','receipt_sha256':sha(J/'receipt.json'),'exit_sha256':sha(J/'entry_final.json'),'candidate_archive_sha256':sha(J/'candidate.zip'),'candidate_asrun_subset_count':len(actual),'candidate_frozen_omitted_nonruntime_files':missing,'case_files':rows,'old_30_off_bit_equal':True,'on_29_noncode_bit_equal':True,'prior_132220_13_and_130247_3_pins_match':True,'ready_total':len(rr),'selected_N8':int(want.sum()),'ready_time_s':t[sel].tolist(),'ready_id':rr[:,3].astype(int).tolist(),'epoch':rr[:,4].astype(int).tolist(),'rx_valid':rr[:,5].astype(int).tolist(),'bank_code':cc.astype(int).tolist(),'nominal_code':ncode.astype(int).tolist(),'bank_minus_nominal_LSB':delta.astype(int).tolist(),'bank_slot':mm[:,5].astype(int).tolist(),'bank_version':mm[:,6].astype(int).tolist(),'all_ready_codes_equal_old_frozen':True,'all_ready_root_outputs_equal':True,'off_root_disabled_contract':True,'cache_field_fingerprints':cache_hash,'negative_update_receipt':R['negative_updates'],'source_counts':{'candidate':23,'production':87,'satk_disk':223,'satk_entry_paths':len(S['satk'])},'limits':{'private_main_P_compared':False,'same_path_cached_bytes_independently_verified':False,'nonready_root_hold_or_clock_pulse_tested':False,'actual_rx_fault_injection':False,'different_h_proven':False,'drain_proven':False,'background_training':False,'main_integrated':False,'product_accepted':False}}
print(json.dumps(out,indent=2,ensure_ascii=False))
