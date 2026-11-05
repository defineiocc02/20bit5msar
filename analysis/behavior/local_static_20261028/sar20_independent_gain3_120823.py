#!/usr/bin/env python3
"""Read-only audit of actual gain3 scratch and pinned historical endpoints."""
import hashlib,json,math,sys,zipfile
from pathlib import Path
import h5py,numpy as np
ROOT=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(ROOT/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import decode,need,pdiff,read_calendar,read_logs,same,sha,val
job=ROOT/'runs/az_probe_20261028T120823Z';run=job/'gain3_result';fine=ROOT/'runs/az_probe_20261028T115303Z/resume_result';pre=ROOT/'runs/az_probe_20261028T110315Z/static_result';gain=ROOT/'runs/az_probe_20261028T113441Z/gain_result'
R=json.loads((run/'receipt.json').read_text());O=json.loads((job/'receipt.json').read_text());fr=json.loads((fine/'receipt.json').read_text());gr=json.loads((gain/'receipt.json').read_text())
need(R['status']=='three_actual_scratch_points_complete_independent_review_required' and R['stage']=='complete' and O['status']=='isolated_gain3_result_preserved' and O['result_status']==R['status'] and sha(run/'receipt.json')==O['result_receipt_sha256'],'terminal receipt')
need(R['new_simulations_started']==R['new_simulations_saved']==O['new_simulations_started']==O['new_simulations_saved']==3 and not R['repeated_saved_baselines'],'new experiment count')
need(sha(run/'sar20_gain3_scratch_job.m')==R['job_sha256']==O['source_sha256'],'job source pin')
need(sha(run/'sandbox/models/SarGain3.slx')==sha(fine/'SarAdc_factory.slx')==sha(pre/'SarAdc_factory.slx')==R['model_sha256']==O['current_model_sha256_before']==O['current_model_sha256_after'],'identical saved SLX pin')
need(sha(run/'source_manifest.json')==sha(fine/'source_manifest.json')==R['source_manifest_sha256'] and sha(run/'source.zip')==sha(fine/'source.zip')==R['source_zip_sha256'],'source pins')
manifest=json.loads((run/'source_manifest.json').read_text())['files'];pins={v['path'].replace('\\','/'):v['sha256'] for v in manifest};need(len(pins)==len(manifest),'source duplicate')
with zipfile.ZipFile(run/'source.zip') as z:
 need(len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(pins),'source inventory')
 for name,h in pins.items():need(hashlib.sha256(z.read(name)).hexdigest()==h,'source file SHA '+name)
need(sha(fine/'receipt.json')==R['old_fine_receipt_sha256'] and sha(gain/'receipt.json')==R['old_gain_receipt_sha256'],'prior receipt pins')
for row in R['prior_pins']:
 path=row['path'].replace('\\','/');idx=path.lower().find('/runs/');need(idx>=0,'prior path not project-relative');path=ROOT/path[idx+1:];need(sha(path)==row['sha256'],'prior file pin '+str(path))
need(fr['status']=='actual_refined_multicode_windows_no_missing_code_claim' and gr['status']=='four_actual_a0_points_complete_review_required','prior status')
base=fine/'point_003/P.mat';Z=fine/'Pzero_reconstructed.mat';oldpt=gain/'point_04_Ainf_zero';offset=-1.9073486328125e-9
with h5py.File(base) as f:
 times,groups,budget=read_calendar(f);ticks=[float(f[x][()].item()) for x in f['P/adc_groups/tick'][()].ravel()]
 dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v','d2_weights_ra_v','tracking_step_ra_v']}
 need(val(f,'P/input/offset_v')==offset and val(f,'P/backend/ra/A0')==1e4 and val(f,'P/backend/ra/UGB_hz')==1.2e9,'baseline P')
with h5py.File(Z) as f:need(val(f,'Pzero/input/offset_v')==0 and val(f,'Pzero/backend/ra/A0')==1e4,'reconstructed prior zero P')
with h5py.File(oldpt/'P.mat') as f:need(val(f,'P/input/offset_v')==0 and math.isinf(val(f,'P/backend/ra/A0')) and not val(f,'P/ni/ra_finite_gain'),'saved Inf zero P')

def signal_struct(path):
 with h5py.File(path) as h:
  seq=[h[x] for x in h['#subsystem#/MCOS'][()].ravel()];s=h['signals'];names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];out=[]
  for i,d in enumerate(seq):
   if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
   ns,t=seq[i-11],seq[i-9]
   if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
   count=int(ns[()].item())
   if count>0 and t.shape==(1,count) and (count==1 or d.shape[-1]==count):
    cls=d.attrs.get('MATLAB_class',b'');cls=cls.decode() if isinstance(cls,bytes) else str(cls)
    out.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,count)).T,'class':cls})
  need(len(names)==len(out)==9,'unsupported 9 native series');return dict(zip(names,out))

keep=['back_log','code_log','control_log','event_log','front_log','raw_log','ready_log','record_log','record_ready_log'];node_kind=['fine_decide','ra_start','d2_prepare','d2_end','tracking_end','raw_latch','release']
expected_t=np.array([i*2e-7+x for i in range(5) for x in times])

def components(row):
 d1,d2,dt=map(int,row[:3]);c,f=divmod(d1,32);ref=float(dig['vref_v']);v1=(32*c+2*f-1039)*ref/1024-17*ref/1024
 db=np.array([(d2>>i)&1 for i in range(11,-1,-1)]);ds=np.array([2*((dt>>i)&1)-1 for i in range(7,-1,-1)])
 d2ra=dig['d2_offset_ra_v']+np.sum(np.asarray(dig['d2_weights_ra_v']).ravel()*db);dtra=dig['tracking_step_ra_v']*np.sum(np.arange(8,0,-1)*ds)/8
 v2=d2ra/dig['ra_gain'];vt=dtra/dig['ra_gain'];return {'d1_v':float(v1),'d2_v':float(v2),'dt_v':float(vt),'voltage_v':float((v1+v2)+vt),'d2_ra_v':float(d2ra),'dt_ra_v':float(dtra)}

def inspect(L,x,label):
 need(set(keep)<=set(L),label+' missing logs');e=L['event_log']['data'];t=L['event_log']['time']
 need(e.shape==(240,2) and np.array_equal(e[:,0],np.repeat(np.arange(5),48)) and np.array_equal(e[:,1],np.tile(np.arange(1,49),5)) and same(t,expected_t),label+' event calendar')
 for k in keep:need(same(t,L[k]['time']),label+' logger time '+k)
 ready=L['ready_log']['data'][:,0];rready=L['record_ready_log']['data'][:,0];need(np.all(np.isin(ready,[0,1])) and same(ready,rready),label+' ready')
 ix=np.flatnonzero(ready==1);need(len(ix)==5 and np.array_equal(e[ix,0],np.arange(5)) and np.all(e[ix,1]==47),label+' ready events')
 raw=L['raw_log']['data'][ix];rec=L['record_log']['data'][ix];codes=L['code_log']['data'][ix,0];held=L['front_log']['data'][ix,0]
 need(same(raw,rec) and np.array_equal(raw[:,3],np.arange(5)) and np.all(raw[:,4:6]==1) and np.all(held==x),label+' raw valid/held')
 need(all(decode(r,dig)==int(c) for r,c in zip(raw,codes)),label+' decode')
 nodes={}
 for kind in node_kind:
  gs=[i+1 for i,g in enumerate(groups) if kind in g]
  if kind in ['fine_decide','d2_prepare']:gs=gs[:1]
  need(len(gs)==1,label+' node group '+kind);i=int(np.flatnonzero((e[:,0]==4)&(e[:,1]==gs[0]))[0])
  nodes[kind]={'time_s':float(t[i]),'front7':L['front_log']['data'][i].tolist(),'backend8':L['back_log']['data'][i].tolist(),'control13':L['control_log']['data'][i].tolist()}
 gs=[i+1 for i,g in enumerate(groups) if 'ta_compare' in g];need(len(gs)==8 and [int(ticks[g-1]) for g in gs]==list(range(300,340,5)),label+' TA calendar')
 ta=[]
 for k,g in enumerate(gs):
  i=int(np.flatnonzero((e[:,0]==4)&(e[:,1]==g))[0]);ctrl=L['control_log']['data'][i];back=L['back_log']['data'][i];front=L['front_log']['data'][i]
  decision=(int(ctrl[6])>>(7-k))&1;final=(int(raw[-1,2])>>(7-k))&1
  need(decision==final==int(back[1]>=0),label+' TA observed sign/bit '+str(k))
  ta.append({'index':k,'tick':int(ticks[g-1]),'time_s':float(t[i]),'front7':front.tolist(),'backend8':back.tolist(),'control13':ctrl.tolist(),'decision':decision,'final_raw_bit':final})
 return {'raw6':raw[-1].astype(int).tolist(),'code20':int(codes[-1]),'all_ready_raw6':raw.astype(int).tolist(),'all_ready_code20':codes.astype(int).tolist(),'all_ready_time_s':t[ix].tolist(),'ready_s':float(t[ix[-1]]),'held_input_v':float(held[-1]),'components':components(raw[-1]),'nodes':nodes,'ta':ta}

def check_obs_mat(path,X,name):
 with h5py.File(path) as f:
  for key in ['raw6','code20','all_ready_raw6','all_ready_code20','all_ready_time_s','ready_s','held_input_v']:
   need(np.array_equal(np.asarray(val(f,'obs/'+key)).ravel(),np.asarray(X[key]).ravel()),name+' observed '+key)
  for kind,n in X['nodes'].items():
   for key,v in n.items():need(np.array_equal(np.asarray(val(f,'obs/nodes/'+kind+'/'+key)).ravel(),np.asarray(v).ravel()),name+' observed node '+kind+'/'+key)
  for i,row in enumerate(X['ta']):
   for key,v in row.items():
    ds=f['obs/ta/'+key];ref=ds[()].ravel()[i];got=f[ref][()].ravel()
    need(np.array_equal(got,np.asarray(v).ravel()),name+' observed TA '+str(i)+'/'+key)
  for key,v in X['components'].items():need(val(f,'obs/digital_components/'+key)==v,name+' observed digital '+key)

def compare_receipt(X,C,name):
 for key in ['raw6','code20','all_ready_raw6','all_ready_code20','all_ready_time_s','ready_s','held_input_v']:
  if key in C:need(np.array_equal(np.asarray(X[key]).ravel(),np.asarray(C[key]).ravel()),name+' receipt '+key)
 for key,v in X['components'].items():need(v==C['digital_components'][key],name+' components '+key)
 for kind,n in X['nodes'].items():
  target=C.get('actual_nodes',C.get('nodes'))[kind]
  for key,v in n.items():need(np.array_equal(np.asarray(v).ravel(),np.asarray(target[key]).ravel()),name+' receipt node '+kind+'/'+key)
 for i,row in enumerate(X['ta']):
  for key,v in row.items():need(np.array_equal(np.asarray(v).ravel(),np.asarray(C['ta'][i][key]).ravel()),name+' receipt TA '+str(i)+'/'+key)

allout={};neg=signal_struct(fine/'point_003/signals.mat');zero=read_logs(pre/'preflight_capped_simout.mat');infzero=read_logs(oldpt/'simout.mat')
for name,L,x,key in [('A1e4_negative',neg,offset,'prior_A1e4_negative'),('A1e4_zero',zero,0.,'prior_A1e4_zero'),('Ainf_zero',infzero,0.,'prior_Ainf_zero')]:
 X=inspect(L,x,name);compare_receipt(X,R[key],name);allout[name]=X
need(allout['A1e4_negative']['code20']==524285 and allout['A1e4_zero']['code20']==allout['Ainf_zero']['code20']==524289,'prior endpoint codes')
need(allout['A1e4_negative']['raw6']==fr['points'][2]['raw6'] and allout['Ainf_zero']['raw6']==gr['points'][3]['raw6'],'prior receipt crossjoin')
PD={}
for i,item in enumerate(R['points'],1):
 name=item['name'];folder=run/f'point_{i:02d}_{name}';x=item['input_offset_v'];gainval=math.inf if name=='Ainf_negative' else 1e5
 need(item['status']=='valid' and item['error']=='' and item['rng_unchanged'],name+' actual status')
 for f,k in [('P.mat','P_sha256'),('simout.mat','simout_sha256'),('signals.mat','signals_sha256'),('observed.mat','observed_sha256')]:need(sha(folder/f)==item[k],name+' SHA '+f)
 diff=pdiff(base,folder/'P.mat');want={'P/backend/ra/A0'}|({'P/ni/ra_finite_gain'} if math.isinf(gainval) else set())|({'P/front/input/offset_v','P/input/offset_v','P/xFE0'} if x==0 else set());need(set(diff)==want,name+' P diff '+str(diff));PD[name]=diff
 with h5py.File(folder/'P.mat') as f:
  need(val(f,'P/backend/ra/A0')==gainval and val(f,'P/backend/ra/UGB_hz')==1.2e9 and bool(val(f,'P/ni/ra_finite_gain'))==math.isfinite(gainval) and val(f,'P/input/offset_v')==val(f,'P/front/input/offset_v')==x and val(f,'P/input/amplitude_v')==0 and val(f,'P/N')==1 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and val(f,'P/n_cycles')==5,name+' P scopes')
 L=signal_struct(folder/'signals.mat');sim=read_logs(folder/'simout.mat');need(len(sim)==30,name+' full output log count')
 for n in keep:need(L[n]['class']==sim[n]['class'] and same(L[n]['time'],sim[n]['time']) and same(L[n]['data'],sim[n]['data']),name+' signal vs original simout '+n)
 X=inspect(L,x,name);allout[name]=X;compare_receipt(X,item,name);check_obs_mat(folder/'observed.mat',X,name)
 for n,key in [('d1_log','d1_v'),('d2_log','d2_v'),('dt_log','dt_v')]:
  need(same(sim[n]['time'],L['event_log']['time']),name+' contribution time '+n);ix=np.flatnonzero(L['ready_log']['data'][:,0]==1)
  for row,raw in zip(ix,X['all_ready_raw6']):need(sim[n]['data'][row,0]==components(raw)[key],name+' contribution '+n)
expect=R['actual_comparison'];need(expect['A1e4_delta']==4 and expect['A1e5_delta']==1 and expect['Ainf_delta']==1 and allout['A1e5_negative']['raw6']==allout['Ainf_negative']['raw6'] and allout['A1e5_zero']['code20']==allout['Ainf_zero']['code20']==524289 and allout['A1e5_negative']['code20']==allout['Ainf_negative']['code20']==524288,'comparison endpoints')
need(all(R[k] for k in ['final_model_source_identity','final_rng_unchanged','final_main_unchanged','final_job_unchanged']) and R['final_cleanup']['complete'] and R['final_cleanup']['scratch_closed'] and R['final_cleanup']['path_restored_exactly'] and R['final_cleanup']['cwd_restored'] and not R['final_cleanup']['issues'],'native cleanup')
need(R['project_function_cache_planned']==R['project_function_cache_cleared'] and 'not restored' in R['cache_boundary'],'cache semantics')
out={'verifier_sha256':sha(Path(__file__)),'receipt_sha256':sha(run/'receipt.json'),'model_sha256':R['model_sha256'],'source_manifest_sha256':R['source_manifest_sha256'],'source_zip_sha256':R['source_zip_sha256'],'source_file_count':len(pins),'prior_pins_verified':len(R['prior_pins']),'P_differences':PD,'calendar_budget':budget,'point_results':allout,'native_final_checks':{k:R[k] for k in ['final_model_source_identity','final_rng_unchanged','final_main_unchanged','final_job_unchanged','final_cleanup']},'cache_cleared_count':len(R['project_function_cache_cleared']),'cache_boundary':R['cache_boundary'],'scope':'New A1e5 and Inf points are scratch copy with InitFcn override; old A1e4 and zero anchors originate prior main-model runs, not rerun for scratch equivalence. Old 110315 zero P reconstructed. No global DNL, missing-code, full budget, general equivalence or silicon claim.'}
print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
