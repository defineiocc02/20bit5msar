#!/usr/bin/env python3
"""Read saved point_001 timeseries only; no model access or output writes."""
from pathlib import Path
import hashlib,json,sys
import h5py,numpy as np
r=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');job=r/'runs/az_probe_20261028T112407Z/zero_result';rec=json.loads((job/'receipt.json').read_text());pt=rec['points'][0];P=job/'point_001/P.mat';mat=job/'point_001/signals.mat';model=job/'SarAdc_factory.slx'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)==pt['P_mat_sha256'] and sha(mat)==pt['signals_sha256'] and sha(model)==rec['model_sha256']
sys.path.insert(0,str(r/'analysis/behavior/finite_dac_review_20261028'));from verify_as_run import val
with h5py.File(P,'r') as f:
 assert val(f,'P/N')==1 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and val(f,'P/n_cycles')==5
 assert val(f,'P/input/amplitude_v')==0 and val(f,'P/input/offset_v')==-3.0517578125e-8
 assert not val(f,'P/transport/enabled') and not val(f,'P/training/enabled') and not val(f,'P/frozen/enabled')
 assert np.all(val(f,'P/front/tau_dac_s')==0) and np.all(val(f,'P/front/tau_sample_s')==0) and not val(f,'P/backend/dac_coupling/enabled')
 assert val(f,'P/backend/az/mode')=='off' and not val(f,'P/front/ktc_enabled') and not val(f,'P/front/dem_enabled') and not val(f,'P/front/dither_enabled') and not val(f,'P/front/mismatch_enabled') and not val(f,'P/front/jitter/enabled')
 assert val(f,'P/backend/ra/A0')==1e4 and val(f,'P/backend/ra/UGB_hz')==1.2e9 and np.isinf(val(f,'P/backend/ra/slew_v_per_s')) and val(f,'P/backend/ni/cinc_kick') and val(f,'P/digital/fsr_diff_v')==8.192
with h5py.File(mat,'r') as h:
 seq=[h[x] for x in h['#subsystem#/MCOS'][()].ravel()];s=h['signals'];names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];out=[]
 for i,d in enumerate(seq):
  if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
  ns,t=seq[i-11],seq[i-9]
  if not (isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
  count=int(ns[()].item())
  if count>0 and t.shape==(1,count) and (count==1 or d.shape[-1]==count):out.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,count)).T})
 assert len(names)==len(out)==9;L=dict(zip(names,out))
 event=L['event_log']['data'];time=L['event_log']['time'];ids=np.flatnonzero(event[:,0]==4);assert len(ids)==48 and np.array_equal(event[ids,1],np.arange(1,49))
 rows={}
 for group in [1,2,3,12,13,16,47,48]:
  i=int(ids[group-1]); t=float(time[i]);values={}
  for name in ['front_log','back_log','control_log','raw_log','ready_log','record_log','record_ready_log']:
   q=L[name];match=np.flatnonzero(q['time']==t);assert len(match)==1;values[name]=q['data'][match[0]].tolist()
  if group==47:
   q=L['code_log'];match=np.flatnonzero(q['time']==t);assert len(match)==1;values['code20']=int(q['data'][match[0],0])
  rows[str(group)]={'time_s':t,'relative_ns':(t-8e-7)*1e9,**values}
 assert rows['1']['front_log'][0]==-3.0517578125e-8
 assert rows['3']['raw_log'][0]==1024
 assert abs(rows['12']['front_log'][2]-2.1721129261363618e-13)<1e-27
 assert abs(rows['13']['back_log'][0]-0.2391763587845565)<1e-15 and abs(rows['13']['back_log'][1]-0.18625024694449563)<1e-15
 assert rows['47']['ready_log']==[1.0] and rows['47']['record_ready_log']==[1.0]
 assert rows['47']['record_log']==[1039,3417,42,4,1,1] and rows['47']['code20']==524285
 out={'schema':'id4-negative-saved-timeseries-readback/v1','model_sha256':sha(model),'P_sha256':sha(P),'signals_sha256':sha(mat),'sample_id':4,'epoch':1,'n':1,'transport':'off','dac_tau_s':0,'dac_coupling':'off','sample_tau_s':0,'az':'off','A0':10000,'ugb_hz':1.2e9,'cinc_kick':True,'cnv_s':8e-7,'rows':rows,'data_scope':'actual logged stage outputs; no independent post-Update full state, no full RaPre log','recorded_logger_names':names}
 print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
