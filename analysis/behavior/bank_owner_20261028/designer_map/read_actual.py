#!/usr/bin/env python3
"""Inspect saved 133342 models/P/logs and actual wiring; never run MATLAB."""
from pathlib import Path
import hashlib,json,sys,zipfile,xml.etree.ElementTree as ET
import h5py,numpy as np
R=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');B=R/'runs/az_probe_20261028T133342Z';sys.path.insert(0,str(R/'analysis/behavior/finite_dac_review_20261028'));from verify_as_run import val,read_logs,fingerprint
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt=json.loads((B/'receipt.json').read_text());model=B/'SarPP.slx';assert sha(model)==receipt['on_s']['model_sha256']=='82ede85bdc7c6a6ac5b1837e6f21c29711de9ee8ab2c26f151672dae76f9a99a';assert receipt['main_integrated'] is False
case_names=['factory_base','factory_off','rx_nominal','rx_old_frozen','rx_bank_on'];cases=[]
for name in case_names:
 path=B/name; rr=json.loads((path/'receipt.json').read_text());model_path=next(path.glob('*.slx'));p=path/'parameters.mat';assert sha(p)==rr['parameters_sha256'] and sha(model_path)==rr['model_sha256'] and sha(path/'simout.mat')==rr['simout_sha256']
 with h5py.File(p) as f:
  v=lambda key:val(f,'P/'+key)
  a={'name':name,'P_sha256':sha(p),'model_sha256':sha(model_path),'N':int(v('N')),'first_id':int(v('first_id')),'epoch':int(v('epoch')),'transport_on':bool(v('transport/enabled')),'bank_on':bool(v('bank/enabled')),'training_on':bool(v('training/enabled')),'cal_collector_on':bool(v('cal_cfg/enabled')),'frozen_on':bool(v('frozen/enabled')),'tau_dac_all_zero':bool(np.all(v('front/tau_dac_s')==0)),'dac_coupling':bool(v('backend/dac_coupling/enabled')),'az_mode':v('backend/az/mode'),'mismatch':bool(v('front/mismatch_enabled')),'dem':bool(v('front/dem_enabled')),'dither':bool(v('front/dither_enabled')),'ktc':bool(v('front/ktc_enabled')),'jitter':bool(v('front/jitter/enabled')),'frequency_hz':float(v('input/frequency_hz'))}
  assert a['N']==8 and a['first_id']==4 and a['epoch']==1 and not a['training_on'] and not a['cal_collector_on'] and a['tau_dac_all_zero'] and not a['dac_coupling']
  if name=='rx_bank_on':
   bank=f['P/bank'];s=bank['slots'];refs=s['cache'][()].reshape(-1);a['same_slot_cache']=fingerprint(f,f[refs[0]],{})==fingerprint(f,f[refs[1]],{});vr=s['version'][()].reshape(-1);a['versions']=[int(f[i][()].item()) for i in vr];a['initial_slot']=int(v('bank/initial_slot'));a['lead_samples']=int(v('bank/lead_samples'));a['command_schedule']=np.asarray(v('bank/command_schedule')).tolist();assert a['same_slot_cache'] and a['versions']==[1,2] and a['command_schedule']==[[147,1,1,2,2,4]]
 cases.append(a)
expected={'root':{'105':'EventStep','463':'Code20','464':'CodeValid','465':'CodeMeta'},'105':{'112':'Adc','123':'Fpga','393':'Transport','433':'Record','434':'RecordReady','431':'RxRawReady','454':'BankOwnerState','455':'BankOwner','456':'BankCommand','457':'NoDrainAck','458':'PublicCode','459':'PublicValid','460':'PublicMeta','109':'Event','423':'ActualTime','422':'PublicEn'},'393':{'415':'TxRxState','416':'PinTransport','400':'RxRaw','401':'Ready3','453':'RxFault'},'375':{'383':'Train','386':'FrozenDecode'}}
checks={}
with zipfile.ZipFile(model) as z:
 for scope,targets in expected.items():
  root=ET.fromstring(z.read('simulink/systems/system_'+scope+'.xml'));blocks={q.get('SID'):q for q in root.iter('Block')};assert all(sid in blocks and blocks[sid].get('Name')==name for sid,name in targets.items())
  if scope=='105':
   assert blocks['454'].get('BlockType')=='UnitDelay' and blocks['455'].get('BlockType')=='M-S-Function';assert next(p.text for p in blocks['457'].findall('./P') if p.get('Name')=='Value')=='zeros(7,1)'
  if scope=='root':
   for sid,width in [('463','1'),('464','1'),('465','9')]:assert next(p.text for p in blocks[sid].findall('./P') if p.get('Name')=='PortDimensions')==width
  edges=set()
  for l in root.iter('Line'):
   src=next((p.text for p in l.findall('./P') if p.get('Name')=='Src'),None)
   if src:
    for p in l.iter('P'):
     if p.get('Name')=='Dst':edges.add((src,p.text))
  wanted={
   'root':[('105#out:1','463#in:1'),('105#out:2','464#in:1'),('105#out:3','465#in:1')],
   '105':[('112#out:1','393#in:2'),('112#out:2','393#in:3'),('393#out:1','433#in:1'),('112#out:1','433#in:3'),('393#out:2','431#in:1'),('431#out:1','434#in:1'),('112#out:2','434#in:3'),('433#out:1','123#in:1'),('434#out:1','123#in:2'),('433#out:1','455#in:4'),('434#out:1','455#in:5'),('123#out:1','455#in:6'),('393#out:6','455#in:7'),('422#out:1','455#in:8'),('456#out:1','455#in:9'),('457#out:1','455#in:10'),('454#out:1','455#in:1'),('455#out:1','454#in:1'),('109#out:1','455#in:2'),('109#out:1','456#in:1'),('423#out:1','455#in:3'),('455#out:2','458#in:1'),('455#out:3','459#in:1'),('455#out:4','460#in:1')],
   '393':[('416#out:1','415#in:1'),('415#out:1','416#in:1'),('416#out:2','400#in:1'),('416#out:3','401#in:1'),('416#out:7','453#in:1')],
   '375':[('383#out:1','386#in:3'),('386#out:1','382#in:1')]}
  assert all(v in edges for v in wanted[scope]),(scope,[v for v in wanted[scope] if v not in edges]);checks[scope]=[list(v) for v in wanted[scope]]
 sourcezip=B/'candidate.zip';candidates={x['name']:x for x in receipt['sources']['candidate']}
 with zipfile.ZipFile(sourcezip) as z:
  for fn in ['sar20_pp_sfun','sar20_pp_step','behavior_transport_pp_sfun']:
   data=z.read('pingpong_132220_finalize_v1/src/'+fn+'.m');assert hashlib.sha256(data).hexdigest()==candidates[fn]['sha256']
  s=z.read('pingpong_132220_finalize_v1/src/sar20_pp_sfun.m').decode();assert 'iw=[64 2 1 6 1 1 1 1 5 7];ow=[64 1 1 9];' in s
  s=z.read('pingpong_132220_finalize_v1/src/sar20_pp_step.m').decode();assert 'meta9=[hit,time,id,epoch,input_valid,slot,version,fault,command_status]' in s
log=read_logs(B/'rx_bank_on/simout.mat');rdy=log['record_ready_log'];ready=np.flatnonzero(rdy['data'][:,0]==1);assert len(ready)==12
rows=[]
for i in ready:
 t=float(rdy['time'][i]); values={}
 for name in ['record_log','bank_code_valid_log','bank_meta_log','code_log','event_log']:
  l=log[name];j=np.flatnonzero(l['time']==t);assert len(j)==1;values[name]=l['data'][j[0]].tolist()
 rows.append({'time_s':t,**values})
assert [int(v['record_log'][3]) for v in rows]==list(range(12));id4=rows[4];assert id4['record_log']==[1878,3291,213,4,1,1] and id4['bank_code_valid_log']==[1] and id4['code_log']==[957226] and id4['bank_meta_log']==[342,1.338e-6,4,1,1,2,2,0,0]
hit147=next(i for i,m in enumerate(log['bank_meta_log']['data']) if m[0]==147);publish={'time_s':float(log['bank_meta_log']['time'][hit147]),'event':log['event_log']['data'][hit147].tolist(),'meta':log['bank_meta_log']['data'][hit147].tolist(),'record_ready':float(log['record_ready_log']['data'][hit147,0]),'code_valid':float(log['bank_code_valid_log']['data'][hit147,0])};assert publish['event']==[3,1] and publish['record_ready']==0 and publish['meta'][8]==1
out={'schema':'sarpp-133342-layout-readback/v1','scope':'saved SLX/P/logs and installation receipt only; no simulation, no runtime tracing','model_sha256':sha(model),'receipt_sha256':sha(B/'receipt.json'),'status':receipt['status'],'main_integrated':receipt['main_integrated'],'cases':cases,'saved_SLX_existing_config_note':'factory transport=false/DEM off/dither off; stale for rx_bank_on saved P','verified_scope_edges':checks,'meta9':['hit','time_s','id','epoch','input_valid','slot','version','fault','command_status'],'n_ready_total':len(rows),'ids_ready':[int(x['record_log'][3]) for x in rows],'id4':id4,'publish_hit147':publish,'native_numeric':receipt['numeric'],'fault_injection_proven':False,'drain_proven':False,'background_training_implemented':False,'event_observed_utc':'2026-10-28T13:35:37.1346181Z'}
def clean(x):
 if isinstance(x,float) and np.isnan(x):return 'NaN'
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 return x
print(json.dumps(clean(out),ensure_ascii=False,indent=2,allow_nan=False))
