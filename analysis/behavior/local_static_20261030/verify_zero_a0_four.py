#!/usr/bin/env python3
"""Read pinned baseline and four actual A0 endpoint simouts; print JSON only."""
from __future__ import annotations
import argparse,hashlib,json,math,sys,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
MODEL='a190eae2be57e24f0fb923bad7bbf4144873f28ddc97b8196fdd80a512adbe9f'
BASELINE='ae2d2b023362fd39b1cfaad39278b8c91fbad23d542f19df864547fb7e77e733'
PROOF='486beefb585a8d8d7f6e8606b97ac803139996021d8a25fa80c27c9cb142c4da'
STATE='4098360e7ce05a32d6c5b7eb1dab1d4560f68c8a72c035d52b79c9db4182fd92'
PINS='edeabf9ec82d33a844cf36581ed0fd3d5d5f9da27e79e76ab15daea393278e32'
CANDIDATE='96ffce561bcbe80fa7633af136dc4c4fe0c9aa9ce023cce627c4ec11cc559594'
PRIOR='54fbb2b03dce08a5fe7dbca00e62570e507b4cf22b3d7462ad38540ddad20c32'
SIX_HELPER='44ee80fbaeb8b77449f9fca0143ed96a1ddb5dc033e34d391cdd22ebe56a3181'
RAW_HELPER='3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'
ANCHORS=[
 {'P.mat':'164f3a3323b5105f7933cfed6b702ba58a0ac575b386de1d613198acb29f2fbf',
  'simout.mat':'502c04adf18fd91dc61236e282df2265c1235e4e9c38c00db38ff4927ddd64c7',
  'observed.mat':'21029016befc2b2c018ab32a7f673170bdb8b506d19df7f5af83822aaf14a5e5'},
 {'P.mat':'10ed3f815ff9d248c93c5950a4c11e6c2a080da5e2b24b82e851574b4fda2424',
  'simout.mat':'665aa9b471a77b5ef6f211b70806e51e34d23e29b09cb8facb96ad105ecb0f0a',
  'observed.mat':'740a2cd8f3cb88924f29972e198b0f55bf9314290696b372c2203ac943bc90d5'}]
GROUPS=[3,12,13,16,37,38,46,47]
LABELS=['A1e4_negative_reused','A1e4_zero_reused','A1e5_negative','A1e5_zero','Ainf_negative','Ainf_zero']
GAINS=[1e4,1e4,1e5,1e5,math.inf,math.inf]


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',required=True,type=Path);ap.add_argument('--project',required=True,type=Path)
 a=ap.parse_args();result=a.result.resolve();project=a.project.resolve()
 six_path=project/'analysis/behavior/local_static_20261030/verify_static_six.py';raw_path=project/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
 if sha(six_path)!=SIX_HELPER or sha(raw_path)!=RAW_HELPER:raise ValueError('Pinned independent log reader changed')
 sys.path[:0]=[str(six_path.parent),str(raw_path.parent)]
 import verify_static_six as six
 import verify_as_run as u
 import numpy as np
 import h5py
 need=u.need;R=json.loads((result/'receipt.json').read_text())
 need(R['status']=='four_actual_gain_points_two_reused_baseline_endpoints' and R['stage']=='complete','Job incomplete or cleanup failed')
 need(R.get('model_source_workspace_parameters_unchanged') and R['cleanup']['status']=='complete','Model/workspace or cleanup gate failed')
 need(R['dnl']=='not_measured' and R['inl']=='not_measured','Unexpected static linearity claim')
 need(sha(result/'restore_comparison.json')==PROOF==R['restore_comparison_sha256'] and R['baseline_model_sha256']==BASELINE,
      'Cross-model comparison identity mismatch')
 for name,expected,key in [('SarAdc_as_run.slx',MODEL,'model_sha256'),('applied_config_as_run.json',STATE,'state_sha256'),
                            ('source_pins.json',PINS,'source_pins_sha256'),('sar20_zero_a0_four_ae2d.m',CANDIDATE,'candidate_sha256')]:
  need(sha(result/name)==expected==R[key],name+' identity mismatch')
 need(sha(result/'source.zip')==R['source_zip_sha256'],'Source ZIP hash mismatch')
 rows=json.loads((result/'source_pins.json').read_text())['files'];pins={r['path'].replace('\\','/'):r['sha256'] for r in rows}
 need(len(pins)==len(rows)==105,'Unexpected source inventory')
 with zipfile.ZipFile(result/'source.zip') as z:
  names=z.namelist();need(len(names)==len(set(names)) and set(names)==set(pins),'Source ZIP inventory mismatch')
  for n,h in pins.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Source ZIP mismatch: '+n)
 need(sha(result/'anchors/prior_receipt.json')==PRIOR,'Prior receipt hash mismatch')
 need(len(R['anchors'])==2 and len(R['points'])==4 and len(R['cases'])==6,'Wrong case count')
 anchorP=result/'anchors/point_01/P.mat'
 with h5py.File(anchorP,'r') as f:negative=float(u.val(f,'P/input/offset_v'))
 need(negative<0,'Negative anchor not negative')
 inputs=[negative,0,negative,0,negative,0];allowed={'P/backend/ra/A0','P/ni/ra_finite_gain','P/front/input/offset_v','P/input/offset_v','P/xFE0'}
 event_time=None;cases=[]
 for i,(label,gain,x) in enumerate(zip(LABELS,GAINS,inputs)):
  if i<2:
   folder=result/'anchors'/f'point_{i+1:02d}';meta=R['anchors'][i]
   need(meta['rerun'] is False and meta['gain_label']=='A1e4_reused','Baseline was not reused')
   for name,h in ANCHORS[i].items():need(sha(folder/name)==h,'Prior anchor mismatch '+name)
  else:
   folder=result/f'point_{i-1:02d}';meta=R['points'][i-2]
   need(meta['index']==i-1 and meta['status']=='valid' and meta['global_rng_unchanged'] and meta['gain_label']==label,'New gain case status mismatch')
   for name,key in [('P.mat','P_sha256'),('simout.mat','simout_sha256'),('observed.mat','observed_sha256')]:
    need(sha(folder/name)==meta[key],f'{label} {name} mismatch')
  pfile=folder/'P.mat';need(set(u.pdiff(anchorP,pfile))<=allowed,f'{label} unexpected P difference')
  with h5py.File(pfile,'r') as f:
   actual_a0=float(u.val(f,'P/backend/ra/A0'));ugb=float(u.val(f,'P/backend/ra/UGB_hz'));cf=float(u.val(f,'P/backend/ra/Cf_f'));period=float(u.val(f,'P/Ts_s'))
   need(actual_a0==gain and ugb==1.2e9 and int(u.val(f,'P/ni/ra_finite_gain'))==int(math.isfinite(gain)),f'{label} A0/UGB/finite flag mismatch')
  logs=u.read_logs(folder/'simout.mat');ev=logs['event_log']['data'];t=logs['event_log']['time']
  if event_time is None:event_time=t
  else:need(u.same(event_time,t),f'{label} actual event times differ')
  o=six.verify_logs(logs,pfile,x,u,np,h5py);stored=meta['observation']
  need(o['held_v']==stored['held_input_v'] and o['code20']==stored['code20'] and o['ready_time_s']==stored['ready_time_s'] and
       np.array_equal(np.asarray(o['raw6']),np.asarray(stored['raw6'])) and meta['requested_v']==x,f'{label} actual RAW/held/code mismatch')
  nodes=[];idx={}
  for k,g in enumerate(GROUPS):
   ix=np.flatnonzero((ev[:,0]==4)&(ev[:,1]==g));need(len(ix)==1,f'{label} event group {g} absent/duplicate');idx[g]=int(ix[0]);p=idx[g]
   front=logs['front_log']['data'][p];back=logs['back_log']['data'][p];control=logs['control_log']['data'][p]
   actual={'group':g,'relative_time_s':float(t[p]-4*period),'held_v':float(front[0]),'vres_v':float(front[1]),'qres_c':float(front[2]),
           'vx_v':float(back[0]),'vy_v':float(back[1]),'ra_target_v':float(back[3]),'trial':float(control[0]),
           'D1':float(control[4]),'D2':float(control[5]),'DT':float(control[6])}
   saved=stored['actual_nodes'][k]
   need(all(saved[key]==value for key,value in actual.items()),f'{label} event group {g} differs from receipt')
   nodes.append(actual)
  i31=idx[12];i43=idx[13];Q=float(logs['front_log']['data'][i31,2]);x0=float(logs['back_log']['data'][i31,0]);b31=logs['back_log']['data'][i31];ng=float(b31[4]);tau=float(b31[5]);F=1 if math.isinf(gain) else gain/(gain+ng)
  ra_prediction=F*(Q/cf)+(x0-F*(Q/cf))*math.exp(-(t[i43]-t[i31])/tau);actual_vx=float(logs['back_log']['data'][i43,0])
  need(math.isfinite(tau) and tau>0 and abs(ra_prediction-actual_vx)<1e-14,f'{label} first RA interval does not match single-pole formula')
  cases.append({'label':label,'A0':'Inf' if math.isinf(gain) else gain,'UGB_hz':ugb,'requested_v':x,'held_v':o['held_v'],
                'raw6':o['raw6'],'code20':o['code20'],'ready_time_s':o['ready_time_s'],'actual_nodes':nodes,
                'first_RA_predicted_vx_v':ra_prediction,'first_RA_actual_vx_v':actual_vx,
                'first_RA_actual_minus_predicted_v':actual_vx-ra_prediction})
 deltas={'A1e4':cases[1]['code20']-cases[0]['code20'],'A1e5':cases[3]['code20']-cases[2]['code20'],
         'Ainf':cases[5]['code20']-cases[4]['code20']}
 need(R['code_delta']==deltas,'Actual code-delta summary differs from saved results')
 print(json.dumps({'status':'six_actual_cases_independently_read','cases':cases,'code_delta':deltas,
  'actual_event_times_bit_identical_all_cases':True,'model_sha256':MODEL,
  'scope':'ae2d baseline, a190 new samples; saved workspace and graph statically equal, not proven numerical equivalence. No missing-code/full-range DNL/INL or unique-cause conclusion; Inf A0 retains finite UGB.'},
  ensure_ascii=False,indent=2))


if __name__=='__main__':main()
