#!/usr/bin/env python3
"""Offline audit of preserved SAR20 gain experiment.  Reads only archived files."""
import hashlib,json,math,sys,zipfile
from pathlib import Path
import h5py,numpy as np
root=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(root/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import decode,fingerprint,need,pdiff,read_calendar,read_logs,same,sha,val
job=root/'runs/az_probe_20261028T113441Z';run=job/'gain_result'
prior=root/'runs/az_probe_20261028T112407Z/zero_result'
pre=root/'runs/az_probe_20261028T110315Z/static_result'
R=json.loads((run/'receipt.json').read_text());O=json.loads((job/'receipt.json').read_text());Z=json.loads((prior/'receipt.json').read_text())
need(R['stage']=='complete' and R['status']=='four_actual_a0_points_complete_review_required','gain receipt not complete')
need(sha(run/'receipt.json')==O['result_receipt_sha256'] and O['result_status']==R['status'],'outer receipt pin differs')
need(sha(run/'sar20_ra_gain_probe_job.m')==R['asrun_job_sha256']==O['job_source_sha256'],'job pin differs')
need(sha(run/'SarAdc_factory.slx')==sha(prior/'SarAdc_factory.slx')==sha(pre/'SarAdc_factory.slx')==R['model_sha256']==O['current_model_sha256_before']==O['current_model_sha256_after'],'SLX pin differs')
need(sha(run/'source_manifest.json')==R['source_manifest_sha256'] and sha(run/'source.zip')==R['source_zip_sha256'],'source pins differ')
need(sha(prior/'source_manifest.json')==sha(run/'source_manifest.json') and sha(prior/'source.zip')==sha(run/'source.zip'),'baseline and new source archive differ')
manifest=json.loads((run/'source_manifest.json').read_text())['files']
pins={a['path'].replace('\\','/'):a['sha256'] for a in manifest}
need(len(pins)==len(manifest),'duplicate manifest path')
with zipfile.ZipFile(run/'source.zip') as z:
 names=z.namelist();need(len(names)==len(set(names)) and set(names)==set(pins),'source zip inventory differs')
 for name,h in pins.items():need(hashlib.sha256(z.read(name)).hexdigest()==h,'source hash differs '+name)
neg=prior/'point_001';Pbase=neg/'P.mat';sigbase=neg/'signals.mat';z0=pre/'preflight_capped_simout.mat';pzero=prior/'Pzero_reconstructed.mat'
need(sha(Pbase)==R['prior_negative_P_sha256']==Z['points'][0]['P_mat_sha256'],'baseline negative P differs')
need(sha(sigbase)==R['prior_negative_signals_sha256']==Z['points'][0]['signals_sha256'],'baseline negative signals differ')
need(sha(z0)==R['prior_zero_simout_sha256']==Z['reused_anchors']['zero']['capped_simout_sha256'],'baseline zero simout differs')
need(sha(pzero)==Z['reused_anchors']['zero']['Pzero_reconstructed_sha256'],'reconstructed Pzero pin differs')

def reconstructed_zero_diff(a,b):
 with h5py.File(a) as f,h5py.File(b) as g:
  fm={};gm={};out=[]
  def walk(x,y,path):
   if fingerprint(f,x,fm)==fingerprint(g,y,gm):return
   if isinstance(x,h5py.Group) and isinstance(y,h5py.Group):
    for k in sorted(set(x)|set(y)):
     if k not in x or k not in y:out.append(path+'/'+k)
     else:walk(x[k],y[k],path+'/'+k)
   else:out.append(path)
  walk(f['Pzero'],g['P'],'P');return out
reconstructed_diff=reconstructed_zero_diff(pzero,Pbase)
need(set(reconstructed_diff)=={'P/input/offset_v','P/front/input/offset_v','P/xFE0'},'reconstructed zero P vs actual negative P differs')
with h5py.File(Pbase) as f:
 times,groups,budget=read_calendar(f)
 dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v','d2_weights_ra_v','tracking_step_ra_v']}
 need(val(f,'P/backend/ra/A0')==10000 and val(f,'P/backend/ra/UGB_hz')==1.2e9 and val(f,'P/ni/ra_finite_gain')==1,'base gain/UGB differs')

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
  need(len(names)==len(out)==9,'unsupported baseline negative 9 timeseries format');return dict(zip(names,out))

keep=['back_log','code_log','control_log','event_log','front_log','raw_log','ready_log','record_log','record_ready_log']
node_kind=['fine_decide','ra_start','d2_prepare','d2_end','tracking_end','raw_latch','release']
expected_t=np.array([i*2e-7+x for i in range(5) for x in times])

def components(row):
 d1,d2,dt=map(int,row[:3]);c,f=divmod(d1,32);ref=float(dig['vref_v'])
 v1=(32*c+2*f-1039)*ref/1024-17*ref/1024
 b=np.array([(d2>>i)&1 for i in range(11,-1,-1)]);bs=np.array([2*((dt>>i)&1)-1 for i in range(7,-1,-1)])
 d2ra=dig['d2_offset_ra_v']+np.sum(np.asarray(dig['d2_weights_ra_v']).ravel()*b)
 dtra=dig['tracking_step_ra_v']*np.sum(np.arange(8,0,-1)*bs)/8
 v2=d2ra/dig['ra_gain'];vt=dtra/dig['ra_gain'];v=(v1+v2)+vt
 return {'d1_v':float(v1),'d2_v':float(v2),'dt_v':float(vt),'voltage_v':float(v),'d2_ra_v':float(d2ra),'dt_ra_v':float(dtra)}

def inspect(L,expected,off,label):
 need(set(keep)<=set(L),label+' logger missing')
 ev=L['event_log']['data'];t=L['event_log']['time']
 need(ev.shape==(240,2) and np.array_equal(ev[:,0],np.repeat(np.arange(5),48)) and np.array_equal(ev[:,1],np.tile(np.arange(1,49),5)) and same(t,expected_t),label+' event calendar')
 for name in keep:need(same(t,L[name]['time']),label+' mismatched time axis '+name)
 ready=L['ready_log']['data'][:,0];rr=L['record_ready_log']['data'][:,0]
 need(np.all(np.isin(ready,[0,1])) and same(ready,rr),label+' ready invalid')
 ix=np.flatnonzero(ready==1);need(len(ix)==5 and np.all(ev[ix,1]==47) and np.array_equal(ev[ix,0],np.arange(5)),label+' ready positions')
 raw=L['raw_log']['data'][ix];rec=L['record_log']['data'][ix];code=L['code_log']['data'][ix,0]
 need(same(raw,rec) and np.array_equal(raw[:,3],np.arange(5)) and np.all(raw[:,4]==1) and np.all(raw[:,5]==1),label+' record/raw mismatch')
 need(np.array_equal(raw[-1],expected) and all(decode(r,dig)==int(c) for r,c in zip(raw,code)),label+' selected or 5-code decode mismatch')
 need(L['front_log']['data'][ix[-1],0]==off,label+' held input differs')
 nodes={}
 for kind in node_kind:
  matches=[j+1 for j,g in enumerate(groups) if kind in g]
  if kind in ['fine_decide','d2_prepare']:matches=matches[:1]
  need(len(matches)==1,label+' node groups '+kind)
  i=int(np.flatnonzero((ev[:,0]==4)&(ev[:,1]==matches[0]))[0])
  nodes[kind]={'time_s':float(t[i]),'front7':L['front_log']['data'][i].tolist(),'backend8':L['back_log']['data'][i].tolist(),'control13':L['control_log']['data'][i].tolist()}
 return {'raw6':raw[-1].tolist(),'code20':int(code[-1]),'all_ready_raw6':raw.tolist(),'all_ready_code20':code.tolist(),'held_input_v':float(L['front_log']['data'][ix[-1],0]),'ready_s':float(t[ix[-1]]),'components':components(raw[-1]),'nodes':nodes}

base_lo=inspect(signal_struct(sigbase),[1039,3417,42,4,1,1],-3.0517578125e-8,'base negative')
base_hi=inspect(read_logs(z0),[1040,2374,42,4,1,1],0.,'base zero')
need(base_lo['code20']==524285 and base_hi['code20']==524289,'baseline code changed')
allout={'base_negative':base_lo,'base_zero':base_hi};pdiffs={};logs_meta={};residuals={}
for i,item in enumerate(R['points'],1):
 name=item['name'];folder=run/f'point_{i:02d}_{name}'
 need(item['status']=='valid' and item['error']=='' and item['rng_unchanged'],name+' native status')
 for f,key in [('P.mat','P_sha256'),('simout.mat','simout_sha256'),('observed.mat','observed_sha256')]:need(sha(folder/f)==item[key],name+' SHA '+f)
 iszero=name.endswith('_zero');isinf=name.startswith('Ainf');off=0. if iszero else -3.0517578125e-8;gain=math.inf if isinf else 2e4
 with h5py.File(folder/'P.mat') as f:
  need(val(f,'P/backend/ra/A0')==gain and val(f,'P/backend/ra/UGB_hz')==1.2e9 and bool(val(f,'P/ni/ra_finite_gain'))==(not isinf),name+' gain/UGB/flag')
  need(val(f,'P/input/offset_v')==off and val(f,'P/front/input/offset_v')==off and val(f,'P/input/amplitude_v')==0 and val(f,'P/N')==1 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and val(f,'P/n_cycles')==5 and val(f,'P/Ts_s')==2e-7,name+' P input/window')
 pds=pdiff(Pbase,folder/'P.mat');want={'P/backend/ra/A0'}|({'P/ni/ra_finite_gain'} if isinf else set())|({'P/front/input/offset_v','P/input/offset_v','P/xFE0'} if iszero else set());need(set(pds)==want,name+' unexpected P field diff '+str(pds));pdiffs[name]=pds
 L=read_logs(folder/'simout.mat');logs_meta[name]={n:len(q['time']) for n,q in L.items()}
 X=inspect(L,item['raw6'],off,name);allout[name]=X
 need(len(L)==30,name+' missing native logger')
 for log,key in [('d1_log','d1_v'),('d2_log','d2_v'),('dt_log','dt_v')]:
  need(same(L[log]['time'],L['event_log']['time']),name+' contribution logger axis '+log)
  ri=np.flatnonzero(L['ready_log']['data'][:,0]==1)
  for row,rawrow in zip(ri,X['all_ready_raw6']):
   need(L[log]['data'][row,0]==components(rawrow)[key],name+' actual contribution logger '+log)
 need(X['code20']==item['code20'],name+' code receipt')
 with h5py.File(folder/'observed.mat') as f:
  for k in ['raw6','all_ready_raw6','all_ready_code20']:
   need(np.array_equal(np.asarray(val(f,'obs/'+k)).ravel(),np.asarray(X[k]).ravel()),name+' observed '+k)
  for k in ['code20','held_input_v','ready_s']:need(val(f,'obs/'+k)==X[k],name+' observed '+k)
  for kind in node_kind:
   for key,value in X['nodes'][kind].items():
    observed=np.asarray(val(f,'obs/nodes/'+kind+'/'+key)).ravel();need(np.array_equal(observed,np.asarray(value).ravel()),name+' observed nodes '+kind+'/'+key)
    need(np.array_equal(observed,np.asarray(item['actual_nodes'][kind][key]).ravel()),name+' receipt nodes '+kind+'/'+key)
  residuals[name]={}
  for k,v in X['components'].items():
   obs=val(f,'obs/digital_components/'+k);need(obs==item['digital_components'][k],name+' observed vs receipt contribution '+k)
   residuals[name][k]=float(v-obs)
need(R['final_checks']['model_source_workspace_unchanged'] and R['final_checks']['cwd_restored'] and R['final_checks']['path_restored'] and not R['final_checks']['issues'],'native final check reports issue')
print(json.dumps({'verifier_sha256':sha(Path(__file__)),'receipt_sha256':sha(run/'receipt.json'),'job_sha256':sha(run/'sar20_ra_gain_probe_job.m'),'model_sha256':R['model_sha256'],'source_manifest_sha256':R['source_manifest_sha256'],'source_zip_sha256':R['source_zip_sha256'],'verified_source_file_count':len(pins),'calendar_budget':budget,'P_fields_diff_vs_negative_1e4':pdiffs,'reconstructed_zero_P_diff_vs_negative_1e4':reconstructed_diff,'actual_d1_d2_dt_at_all_ready_equals_public_decode':True,'logs':logs_meta,'native_final_checks':R['final_checks'],'independent_components_minus_native_v':residuals,'points':allout,'scope':'Old zero P reconstructed after original run. Native final checks assert restoration; no independent access to live workspace. The source archive pin and reported path check do not supply full per-call trace.'},indent=2,ensure_ascii=False,allow_nan=False))
