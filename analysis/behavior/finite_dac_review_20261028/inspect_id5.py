from pathlib import Path
import sys,json,hashlib,math
import numpy as np,h5py
sys.path.insert(0,'/tmp');from read_transport_logs import read_logs
P=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');runs=P/'runs';dest=Path('/tmp/sar20_finite_dac/readability')
folders=[runs/'az_probe_20261027T022517Z/dac_enabled_tau0']+[runs/'az_probe_20261027T023003Z'/n for n in ['dac_finite_0p1ns','dac_finite_1ns','dac_finite_5ns','dac_Inf_nonsettling_negative']]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def at(l,t):
 r=np.flatnonzero(l['Time']==t);assert len(r)==1;return l['Data'][r[0]].copy()
def bdiff(a,b):return np.asarray(a,dtype='float64').view('uint64')!=np.asarray(b,dtype='float64').view('uint64')
def first(a,b,t):
 w=np.flatnonzero(bdiff(a,b));return None if not len(w) else {'group':int(w[0]+1),'relative_ns':float((t[w[0]]-t[0])*1e9),'baseline':float(b[w[0]]),'case':float(a[w[0]])}
items=[]
for folder in folders:
 logs=read_logs(folder/'simout.mat');event=logs['event_log'];take=(event['Data'][:,0]==5)&(event['Data'][:,1]>=1)&(event['Data'][:,1]<=48);t=event['Time'][take];assert np.array_equal(event['Data'][take,1],np.arange(1,49))
 names=['raw_log','front_log','back_log','control_log','dac_ra_pre_log','az_route_log'];d={n:np.array([at(logs[n],q) for q in t]) for n in names}
 ready=logs['record_ready_log'];rr=np.flatnonzero(ready['Data'][:,0]==1);record=[]
 for row in rr:
  when=ready['Time'][row];raw=at(logs['record_log'],when)
  if raw[3]==5 and raw[4]==1:record.append({'time_s':float(when),'raw6':raw.tolist(),'code20':float(at(logs['code_log'],when)[0]),'d1_v':float(at(logs['d1_log'],when)[0]),'d2_v':float(at(logs['d2_log'],when)[0]),'dt_v':float(at(logs['dt_log'],when)[0])})
 assert len(record)==1
 with h5py.File(folder/'parameters.mat') as f:
  tau=f['P/front/tau_dac_s'][()].ravel();assert len(tau)==18 and np.all(tau==tau[0]);val=float(tau[0]);groups=f['P/adc_groups'];types=[]
  for r in groups['events'][()].ravel():
   e=f[r];tr=e['type']
   if h5py.check_dtype(ref=tr.dtype):ss=[''.join(map(chr,f[x][()].ravel())) for x in tr[()].ravel()]
   else:ss=[''.join(map(chr,tr[()].ravel()))]
   types.append(ss)
 assert len(types)==48
 summary=json.loads((folder/'summary.json').read_text())
 assert summary['model_sha256']==sha(folder/'SarDac.slx')
 item={'name':folder.name,'folder':str(folder),'tau_s':'Inf' if math.isinf(val) else val,'identity':{n:sha(folder/n) for n in ['SarDac.slx','parameters.mat','simout.mat']},'raw_record':record[0],'groups':types,'actual_CNV_s':float(t[0]),'time_s':t.tolist(),'data':{k:v.tolist() for k,v in d.items()}}
 if items:
  base=items[0];bd={k:np.array(v) for k,v in base['data'].items()};bt=np.array(base['time_s']);assert np.array_equal(t,bt)
  item['first_rawbits_difference']={
    'FrontLog_coarse_input_V':first(d['front_log'][:,0],bd['front_log'][:,0],t),
    'FrontLog_Qres_C':first(d['front_log'][:,2],bd['front_log'][:,2],t),
    'D1_trial':first(d['control_log'][:,0],bd['control_log'][:,0],t),
    'D1_raw':first(d['raw_log'][:,0],bd['raw_log'][:,0],t),
    'RaPre_VX_V':first(d['dac_ra_pre_log'][:,0],bd['dac_ra_pre_log'][:,0],t),
    'BackLog_VX_V':first(d['back_log'][:,0],bd['back_log'][:,0],t),
    'BackLog_VY_V':first(d['back_log'][:,1],bd['back_log'][:,1],t),
    'D2_raw':first(d['raw_log'][:,1],bd['raw_log'][:,1],t),
    'DT_raw':first(d['raw_log'][:,2],bd['raw_log'][:,2],t)}
 item['readout']={}
 for g in [1,2,3,4,5,6,10,11,12,13,14,16,18,32,38,39,45,47,48]:
  k=g-1;item['readout'][str(g)]={'t_ns':float((t[k]-t[0])*1e9),'events':types[k],'trial':float(d['control_log'][k,0]),'raw3':d['raw_log'][k,:3].tolist(),'Qres_C':float(d['front_log'][k,2]),'vres_V':float(d['front_log'][k,1]),'RaPre':d['dac_ra_pre_log'][k,:4].tolist(),'Back':d['back_log'][k,:4].tolist()}
 items.append(item)
# JSON permits nonfinite diagnostics but this capture contains finite actual sampled nodes.
report={'scope':'Read actual saved MATLAB Time/Data via existing verified MCOS reader; no simulation/fit/code reconstruction/tolerance','baseline':'enabled tau0 scratch; off/allzero29logs native bitgate is separate','sample_id':5,'epoch':1,'cases':items}
(dest/'id5_actual_causal_data.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for a in items:
 print(a['name'],a['raw_record'])
 print('first',a.get('first_rawbits_difference'))
 for g in ['2','3','4','5','6','12','13','14']:
  print(g,a['readout'][g])
