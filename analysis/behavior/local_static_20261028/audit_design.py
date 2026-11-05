#!/usr/bin/env python3
"""Read only saved 115303 endpoints and prior gain evidence; write local analysis JSON."""
import sys,json,hashlib,math,zipfile
from pathlib import Path
import numpy as np,h5py
P=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');sys.path.insert(0,str(P/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import val,read_calendar,pdiff,at,sha,same,need
R=P/'runs/az_probe_20261028T115303Z/resume_result';D=P/'runs/az_probe_20261028T113441Z/gain_result';base=P/'runs/az_probe_20261028T112407Z/zero_result/point_001';
rec=json.loads((R/'receipt.json').read_text());gain=json.loads((D/'receipt.json').read_text());audit=Path('/tmp/sar20_gain_margin_20261028/gain_margin_audit.json');ga=json.loads(audit.read_text())
need(rec['status']=='actual_refined_multicode_windows_no_missing_code_claim' and gain['status']=='four_actual_a0_points_complete_review_required','Receipts not complete')
need(sha(D/'receipt.json')==ga['receipt_sha256'] and sha(D/'SarAdc_factory.slx')==ga['model_sha256'] and sha(D/'source_manifest.json')==ga['source_manifest_sha256'],'Prior audit pins no longer match')
need(sha(R/'SarAdc_factory.slx')==ga['model_sha256'] and sha(R/'source_manifest.json')==ga['source_manifest_sha256'],'New model/source manifest differs')
need(sha(R/'source.zip')==rec['source_zip_sha256'],'New source ZIP hash differs')
pins={x['path'].replace('\\','/'):x['sha256'] for x in json.loads((R/'source_manifest.json').read_text())['files']}
with zipfile.ZipFile(R/'source.zip') as z:
 need(set(z.namelist())==set(pins),'Source ZIP inventory differs')
 for name,digest in pins.items():need(hashlib.sha256(z.read(name)).hexdigest()==digest,'Source ZIP entry differs: '+name)

def signal_struct(path):
 with h5py.File(path,'r') as h:
  seq=[h[r] for r in h['#subsystem#/MCOS'][()].ravel()];s=h['signals'];names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];found=[]
  for i,d in enumerate(seq):
   if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
   ns,t=seq[i-11],seq[i-9]
   if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
   n=int(ns[()].item())
   if n>0 and t.shape==(1,n) and (n==1 or d.shape[-1]==n):found.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,n)).T})
  need(len(names)==len(found)==9,'Unexpected nine-series layout');return dict(zip(names,found))

# Recover the actual saved midpoint from the original postprocessing failure;
# the original observed.mat did not populate held, so use front_log directly.
mid=rec['recovered_midpoint']; md=R/'original_113931'
for name,key in [('P.mat','P_sha256'),('signals.mat','signals_sha256'),('observed.mat','observed_sha256'),('failed_simout.mat','simout_sha256'),('receipt.json','original_receipt_sha256')]:
 need(sha(md/name)==mid[key],'Recovered original hash differs: '+name)
need(mid['original_error_identifier']=='MATLAB:cellfun:NotAScalarOutput','Unexpected original failure')
ML=signal_struct(md/'signals.mat');mt=ML['event_log']['time'];me=ML['event_log']['data'];mr=ML['raw_log']['data'];mready=ML['ready_log']['data'][:,0];midx=np.flatnonzero(mready==1)
need(len(midx)==5 and same(mr[midx],ML['record_log']['data'][midx]) and same(mready,ML['record_ready_log']['data'][:,0]) and np.array_equal(mr[midx,3],np.arange(5)) and np.all(mr[midx,5]==1),'Recovered original RAW/ready mismatch')
need(np.array_equal(mr[midx[-1]],np.array([1039,3417,42,4,1,1])) and ML['code_log']['data'][midx[-1],0]==524285 and ML['front_log']['data'][midx[-1],0]==-1.52587890625e-8,'Recovered midpoint differs')
need(set(pdiff(base/'P.mat',md/'P.mat'))=={'P/input/offset_v','P/front/input/offset_v','P/xFE0'},'Recovered P scope differs')

actual=[];new=[]
for item in rec['points']:
 p=R/f"point_{item['index']:03d}"
 for nm,k in [('P.mat','P_mat_sha256'),('signals.mat','signals_sha256'),('observed.mat','observed_sha256')]:need(sha(p/nm)==item[k],'New sample hash mismatch '+nm)
 need(item['status']=='valid' and not item['simulation_error'] and item['global_rng_unchanged'],'Invalid point')
 differences=pdiff(base/'P.mat',p/'P.mat');need(set(differences)=={'P/input/offset_v','P/front/input/offset_v','P/xFE0'},'Unexpected profile drift')
 L=signal_struct(p/'signals.mat');e=L['event_log']['data'];t=L['event_log']['time'];r=L['raw_log']['data'];rr=L['record_log']['data'];ready=L['ready_log']['data'][:,0];rready=L['record_ready_log']['data'][:,0]
 with h5py.File(p/'P.mat') as f:
  times,groups,_=read_calendar(f);x=float(val(f,'P/input/offset_v'));A=float(val(f,'P/backend/ra/A0'));UGB=float(val(f,'P/backend/ra/UGB_hz'));cf=float(val(f,'P/backend/ra/Cf_f'));gainNom=float(val(f,'P/digital/ra_gain'));fsr=float(val(f,'P/digital/fsr_diff_v'));lsb=fsr/2**20
  need(A==10000 and UGB==1.2e9 and gainNom==32 and np.all(np.asarray(val(f,'P/front/tau_dac_s')).ravel()==0),'Wrong profile')
 need(e.shape==(240,2) and np.array_equal(e[:,0],np.repeat(np.arange(5),48)) and np.array_equal(e[:,1],np.tile(np.arange(1,49),5)) and same(t,np.array([i*2e-7+g for i in range(5) for g in times])),'Event log mismatch')
 for k in L:need(same(t,L[k]['time']),'Logger axis mismatch '+k)
 need(same(ready,rready),'Ready mismatch');ix=np.flatnonzero(ready==1);need(len(ix)==5 and same(r[ix],rr[ix]) and np.array_equal(r[ix,3],np.arange(5)) and np.all(r[ix,4]==1) and np.all(r[ix,5]==1),'Actual raw/tag mismatch')
 raw=r[ix[-1]];code=int(L['code_log']['data'][ix[-1],0]);front=L['front_log']['data'];back=L['back_log']['data'];ctl=L['control_log']['data']
 need(np.array_equal(raw,np.array(item['raw6'])) and code==item['code20'] and front[ix[-1],0]==x,'Saved sample mismatch')
 rows={g:int(np.flatnonzero((e[:,0]==4)&(e[:,1]==g))[0]) for g in [3,12,13,37,38,45,46,47]};i=rows[12];q=float(front[i,2]);target=float(back[i,3]);ng=float(back[i,4]);tau=float(back[i,5]);F=A/(A+ng);need(abs(target-q/cf)<1e-14,'Qres/Cf mismatch')
 record={'index':item['index'],'input_V':x,'held_V':float(front[ix[-1],0]),'raw6':raw.tolist(),'code':code,'P_sha256':sha(p/'P.mat'),'signals_sha256':sha(p/'signals.mat'),'P_changed_vs_prior_actual_negative':differences,'first_fine_Vres_V':float(front[rows[3],1]),'Qres_RAstart_C':q,'target_RA_V':target,'NG':ng,'tau_RA_s':tau,'A0':A,'F':F,'VX75_V':float(back[rows[38],0]),'VY75_V':float(back[rows[38],1])};actual.append(record)
near=actual[-1];need(near['input_V']==-1.9073486328125e-9 and near['held_V']==near['input_V'] and near['code']==524285 and near['raw6'][:3]==[1039,3417,42],'Closest measured point differs')
window=rec['narrowest_multicode_window'];need(window['low']['voltage_v']==near['input_V'] and window['high']['voltage_v']==0 and window['code_delta']==4 and window['held_span_v']==1.9073486328125e-9,'Window mismatch')
priorcases={x['name']:x for x in ga['cases']};n=priorcases['A1e4_negative']['decode'];z=priorcases['A1e4_zero']['decode'];
F=near['F'];k=1/F
# Oracle-only calculation using known internal model F; neither fitting nor rerunning.
def oracle(v):
 a=v['d1_input_V'];r=v['d2_input_V']+v['dt_input_V'];o=a+k*r;u=o/lsb+2**19;return {'D1_V':a,'raw_CT_V':r,'output_V':o,'unrounded_code':u,'illustrative_code':math.floor(u+.5)}
U=abs(near['target_RA_V'])/gainNom
budget=[]
for frac in [1,.5,.25]:
 A=near['NG']*(U/(frac*lsb)-1);budget.append({'gain_allocation_LSB':frac,'A0_min':A,'A0_min_dB':20*math.log10(A)})
exampleA=100000.;eGain=U*near['NG']/(exampleA+near['NG']);
tau_req_ns=43.75
ugb_req=near['NG']/(2*math.pi*tau_req_ns*1e-9)*math.log(U/(0.1*lsb));settle=U*math.exp(-tau_req_ns*1e-9/near['tau_RA_s']);first_d2=U*math.exp(-13.75e-9/near['tau_RA_s'])
out={'schema':'sar20-zero-local-physical-design-review/v1','scope':'Only archived 115303 actual points plus independently read 113441/112407/110315; no new MATLAB run; no missing-code or full-range DNL/INL claim.','new_receipt_sha256':sha(R/'receipt.json'),'same_model_sha256':ga['model_sha256'],'source_manifest_sha256':ga['source_manifest_sha256'],'archived_sources_checked':len(pins),'recovered_midpoint_actual_input_V':float(ML['front_log']['data'][midx[-1],0]),'recovered_midpoint_original_failure':mid['original_error_identifier'],'gain_audit_sha256':sha(audit),'zero_prior_P_boundary':'110315 original zero preflight P not independently saved; reconstruction only.','new_samples':actual,'zero_actual_raw6':[1040,2374,42,4,1,1],'zero_actual_code':524289,'narrowest_interval_V':[near['input_V'],0],'span_V':-near['input_V'],'span_nominal_LSB':-near['input_V']/lsb,'observed_endpoint_code_difference':4,'fixed_target_idealization':{'target_abs_V':abs(near['target_RA_V']),'nominal_gain':gainNom,'target_input_V':U,'nominal_lsb_V':lsb,'NG':near['NG'],'tau_RA_s':near['tau_RA_s'],'closed_loop_gain_1e4':F,'gain_examples':budget,'A0_example':exampleA,'A0_example_dB':20*math.log10(exampleA),'gain_error_1e5_V':eGain,'gain_error_1e5_lsb':eGain/lsb,'gain_allocation_0p5_margin_lsb':0.5-eGain/lsb,'first_TA_delta_s':43.75e-9,'first_TA_infA0_settling_error_V':settle,'first_TA_infA0_settling_lsb':settle/lsb,'ugb_for_0p1_lsb_first_TA_Hz':ugb_req,'at_1p2GHz_fraction_above_min':1.2e9/ugb_req-1,'first_D2_infA0_settling_error_V':first_d2,'first_D2_infA0_settling_lsb':first_d2/lsb},'public_raw_correction_oracle_only':{'scale_1_over_F':k,'negative':oracle(n),'zero':oracle(z),'warning':'Uses actual internal model F as an oracle; is an offline arithmetic counterfactual, not a calibrated or simulated code or a public training method.'},'recommended_next':'Two new A0=1e5 points at -1.9073486328125 nV and zero, plus one A0=Inf negative at same new negative input; reuse actual A0=1e4 endpoints and Inf zero. Fix P/seed/ID4/UGB and retain RAW/time/FE/BK/TA traces.'}
Path(__file__).with_name('design_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
for k in ['new_samples','fixed_target_idealization','public_raw_correction_oracle_only']:print(k,json.dumps(out[k],ensure_ascii=False))
