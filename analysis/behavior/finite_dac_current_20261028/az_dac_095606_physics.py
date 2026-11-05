"""Read-only engineering interpretation of 095606 saved N8 data.
All numerical points are actual saved behavioral logs; decomposition is
conditional first-order analysis, not a transistor/silicon or spectrum claim.
"""
from pathlib import Path
import sys,json,math,hashlib
sys.dont_write_bytecode=True
import numpy as np,h5py
root=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(root/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import read_logs,read_calendar,at,val,same,sha
run=root/'runs/az_probe_20261028T095606Z';receipt=json.loads((run/'receipt.json').read_text())
assert receipt['status']=='isolated_joint_az_dac_N8_actual_parity_and_expm_recorded'
ind_path=root/'analysis/behavior/finite_dac_review_20261028/joint_095606_independent.json';ind=json.loads(ind_path.read_text());indcase={c['case']:c for c in ind['cases']}

def H(h,r,t):
 if math.isinf(t):return -math.expm1(-h/r)
 if t==0:return 0.
 if t==r:return (h/r)*math.exp(-h/r)
 # Independent separated-pole expression. Physical D here is 0.1/1/5ns;
 # none equal the actual R.  No AZ near pole uses this expression.
 return t/(t-r)*(math.exp(-h/t)-math.exp(-h/r))

def quantity_stats(arr):
 a=np.asarray(arr,dtype=float);return {'min':float(a.min()),'max':float(a.max()),'max_abs':float(np.max(np.abs(a)))}

cases=[];probes={}
for name in ['far_mixed','minus_ulp','plus_ulp']:
 folder=run/(name+'_run');summary=json.loads((folder/'summary.json').read_text());L=read_logs(folder/'simout.mat')
 probe=L['joint_interval_log'];q=probe['data'][probe['data'][:,0]==1];assert q.shape==(8,44) and np.array_equal(q[:,1],np.arange(4,12));probes[name]=q.copy()
 with h5py.File(folder/'parameters.mat','r') as f:
  Ts=float(val(f,'P/Ts_s'));Cf=float(val(f,'P/backend/ra/Cf_f'));A=float(val(f,'P/backend/ra/A0'));UGB=float(val(f,'P/backend/ra/UGB_hz'));vos=float(val(f,'P/backend/ra/vos_input_v'))
  limit=float(val(f,'P/control/sar2/limit_v'));FSR=float(val(f,'P/digital/fsr_diff_v'));Cgroup=np.asarray(val(f,'P/front/group_C_f'))
  assert math.isinf(float(val(f,'P/backend/ra/slew_v_per_s'))) and bool(val(f,'P/backend/ni/az'))
  plan=np.asarray(val(f,'P/front/plan'));leak=np.asarray(val(f,'P/backend/az/leak_tau_s')).ravel()
  offset=float(val(f,'P/input/offset_v'));amplitude=float(val(f,'P/input/amplitude_v'));freq=float(val(f,'P/input/frequency_hz'));phase=float(val(f,'P/input/phase_rad'))
  times,groups,budget=read_calendar(f)
 assert Cgroup.shape==(18,3) and plan.shape[1]==8 and len(leak)==2 and math.isinf(leak[1]) and vos==1e-3
 # Read original analytic.mat, verify recorded values against actual probe data.
 with h5py.File(run/(name+'_analytic.mat'),'r') as f:
  a=f['analytic'];ps=a['per_sample']
  for key,col in [('id',1),('polarity',3),('q0_C',6),('q1_C',7),('signed_drift_C',8),
                  ('VXpre_V',10),('VX_expm_V',11),('VX_minus_expm_V',12),('R_s',13),
                  ('AZ1_start_V',14),('AZ2_start_V',15),('AZpair',16),('AZwrites',17),('AZleak1_s',18)]:
   got=np.array([f[ref][()].ravel()[0] for ref in ps[key][()].ravel()],dtype=np.float64)
   assert same(got,np.asarray(q[:,col],dtype=np.float64)),(name,key)
  for key,start in [('physical_ids',20),('dac_taus_s',28),('delta_q_C',36)]:
   got=np.array([f[ref][()].ravel() for ref in ps[key][()].ravel()])
   assert same(got,q[:,start:start+8]),(name,key)
  assert int(a['valid_one_count'][()].item())==8 and bool(a['record_gate_all_8_valid'][()].item())
  assert not bool(a['analytical_pass_declared'][()].item())
 ev=L['event_log']['data'];evtime=L['event_log']['time'];checks=[];each=[]
 for row in q:
  ID=int(row[1]);indrow=next(x for x in indcase[name]['each_sample'] if x['ID']==ID)
  assert np.array_equal(row[20:28],indrow['physical_ids']) and np.array_equal(row[28:36],indrow['tau_D_s'])
  assert np.array_equal(row[36:44],indrow['signed_delta_Q_C'])
  assert np.float64(row[10]).tobytes()==np.float64(indrow['actual_pre_VX_V']).tobytes()
  idx=np.flatnonzero((ev[:,0]==ID)&(ev[:,1]>=1)&(ev[:,1]<=48));assert len(idx)==48 and np.array_equal(ev[idx,1],np.arange(1,49));tt=evtime[idx]
  front=at(L['front_log'],tt,'front');back=at(L['back_log'],tt,'back');route=at(L['az_route_log'],tt,'route');pre=at(L['dac_ra_pre_log'],tt,'RaAdvance')
  dec_idx=[g for g,types in enumerate(groups) if ('d2_decide' in types or 'ta_compare' in types)];assert len(dec_idx)==20
  rel_idx=[g for g,types in enumerate(groups) if 'release' in types];assert len(rel_idx)==1;g=rel_idx[0]
  vy=back[dec_idx,1];imax=int(np.argmax(np.abs(vy)));obsVy=float(vy[imax]);obsTime=float(tt[dec_idx[imax]])
  # Raw logged route[5] is the actual Vtop passed to FE in FE coordinates.
  vret=float(route[g,5]);R=float(row[13]);ng=1+float(np.sum(Cgroup[row[20:28].astype(int)-1,:]))/Cf
  # NG for the current modeled sampling top has Cp=0 and is also observed in pre.
  ng=float(at(L['dac_ra_pre_log'],[row[5]],'RaAdvance NG')[0,4]);F=1 if math.isinf(A) else A/(A+ng)
  h=float(row[5]-row[4]);e=math.exp(-h/R);deltas=row[36:44];taus=row[28:36];buckets={}
  for n,tau in [('0',0.),('0.1ns',.1e-9),('1ns',1e-9),('5ns',5e-9)]:
   if n=='0.1ns':mask=(taus>0)&(taus<.2e-9)
   else:mask=taus==tau
   dq=deltas[mask];npts=int(mask.sum());
   if tau==0:
    assert np.all(dq==0);fraction=1.;hcoef=0.;jcoef=-math.expm1(-h/R);residual=0.;drift=0.;j_contrib=0.;lag=0.
   else:
    actualtau=float(taus[mask][0]) if npts else tau;fraction=-math.expm1(-h/actualtau);hcoef=H(h,R,actualtau);jcoef=1-e-hcoef
    residual=float(np.sum(dq))*math.exp(-h/actualtau);drift=float(np.sum(dq))*fraction
    j_contrib=F/Cf*float(np.sum(dq))*jcoef;lag=-F/Cf*float(np.sum(dq))*hcoef
   buckets[n]={'slice_count':npts,'delta_Q_sum_C':float(np.sum(dq)),'fraction_settled':fraction,
      'conditional_Q_drift_C':drift,'conditional_Q_unsettled_C':residual,'H':hcoef,'J':jcoef,
      'conditional_VX_Qramp_component_V':j_contrib,'conditional_VX_lag_vs_instant_V':lag}
  ids=row[20:28].astype(int)-1;csignal=float(np.sum(Cgroup[ids,0]));cgroup=float(np.sum(Cgroup[ids,:]))
  tCNV=float(tt[0]);declared=offset+amplitude*math.sin(2*math.pi*freq*tCNV+phase)
  each.append({'ID':ID,'pol':int(row[3]),'t0_s':float(row[4]),'t1_s':float(row[5]),
   'Q0_signed_C':float(row[6]),'Q1_signed_C':float(row[7]),'Q_drift_signed_C':float(row[8]),
   'VXstart_V':float(row[9]),'VXpre_V':float(row[10]),'independent_expm_delta_V':float(row[12]),
   'R_s':R,'NG':ng,'finite_gain':F,'AZ1_start_V':float(row[14]),'AZ2_start_V':float(row[15]),
   'input_referred_offset_remaining_at_RAstart_V':float(vos-(row[14]-row[15])),
   'AZ_pair':int(row[16]),'AZ_write_count':int(row[17]),'AZ_near_predicate':bool(row[19]),
   'physical_ids':row[20:28].astype(int).tolist(),'tau_DAC_s':taus.tolist(),'delta_Q_signed_C':deltas.tolist(),
   'bucket':buckets,'conditional_all_Q_unsettled_C':sum(x['conditional_Q_unsettled_C'] for x in buckets.values()),
   'Q_drift_minus_single_pole_formula_C':float(row[8])-sum(x['conditional_Q_drift_C'] for x in buckets.values()),
   'conditional_all_VX_lag_vs_instant_V':sum(x['conditional_VX_lag_vs_instant_V'] for x in buckets.values()),
   'conditional_VX_lag_div_nominal32_V':sum(x['conditional_VX_lag_vs_instant_V'] for x in buckets.values())/32,
   'actual_release_vtop_FE_V':vret,'inferred_group_return_charge_C':-cgroup*vret,
   'sampling_C_signal_F':csignal,'input20_LSB_V':FSR/2**20,
   'one_inputLSB_charge_C':csignal*(FSR/2**20),'declared_input_at_actual_CNV_V':declared,
   'actual_front_held_at_CNV_V':float(front[0,0]),'decision_max_abs_VY_V':abs(obsVy),
   'decision_max_VY_signed_V':obsVy,'decision_max_VY_time_s':obsTime,
   'decision_VY_remaining_to_model_abs_limit_V':limit-abs(obsVy),
   'discrete_event_abs_VX_max_V':float(np.max(np.abs(pre[:,0]))),
   'discrete_event_abs_VY_max_V':float(np.max(np.abs(back[:,1]))),
   'actual_feedback_counts': [12,8,7]})
 signal=[e['declared_input_at_actual_CNV_V'] for e in each];held=[e['actual_front_held_at_CNV_V'] for e in each]
 maxvy=max(each,key=lambda x:x['decision_max_abs_VY_V']);maxvx=max(each,key=lambda x:x['discrete_event_abs_VX_max_V']);
 finq=[e['conditional_all_Q_unsettled_C'] for e in each];lag=[e['conditional_all_VX_lag_vs_instant_V'] for e in each]
 case={'name':name,'P_sha256':sha(folder/'parameters.mat'),'simout_sha256':sha(folder/'simout.mat'),
  'analytic_sha256':sha(run/(name+'_analytic.mat')),'AZ_leak1_s':float(leak[0]),'AZ_leak2_s':'Inf',
  'analog_vy_limit_V':limit,'sample_count':len(each),'raw_codes':summary['code20'],'raw_records':summary['raw_words'],
  'declared_input_at_CNV_V':quantity_stats(signal),'actual_held_at_CNV_V':quantity_stats(held),
  'Q0_signed_C':quantity_stats([e['Q0_signed_C'] for e in each]),'Q1_signed_C':quantity_stats([e['Q1_signed_C'] for e in each]),
  'Q_drift_signed_C':quantity_stats([e['Q_drift_signed_C'] for e in each]),
  'hypothetical_fixed_target_Q_unsettled_C':quantity_stats(finq),
  'conditional_VX_lag_vs_instant_V':quantity_stats(lag),'release_vtop_FE_V':quantity_stats([e['actual_release_vtop_FE_V'] for e in each]),
  'inferred_group_return_charge_C':quantity_stats([e['inferred_group_return_charge_C'] for e in each]),
  'decision_peak_VY':{'id':maxvy['ID'],'value_V':maxvy['decision_max_VY_signed_V'],'abs_V':maxvy['decision_max_abs_VY_V'],
    'time_s':maxvy['decision_max_VY_time_s'],'margin_to_abs_limit_V':maxvy['decision_VY_remaining_to_model_abs_limit_V']},
  'discrete_event_peak_VX':{'id':maxvx['ID'],'abs_V':maxvx['discrete_event_abs_VX_max_V']},
  'last_group_time_s':float(q[0,5]-q[0,4]),'per_sample':each}
 cases.append(case)
# Direct comparison is descriptive; code differences do not isolate a single parameter response.
candidate_codes=cases[0]['raw_codes']
# Compare observed Q and per-slice driver components only, not inferred codes.
cols=[1,2,3,4,5,6,7,8,20,21,22,23,24,25,26,27,*range(28,44)]
Q_bits_equal_across_cases=all(same(probes['far_mixed'][:,cols],probes[n][:,cols]) for n in ['minus_ulp','plus_ulp'])
for c in cases:
 oldcase=indcase[c['name']]
 c['code_difference_vs_far_mixed']=[int(x)-int(y) for x,y in zip(c['raw_codes'],candidate_codes)]
 c['near_conditions_present']=bool(oldcase['near_condition_count'])
 mean=[]
 for group in range(0,8,2):
  even=c['per_sample'][group];odd=c['per_sample'][group+1];dt=odd['t0_s']-even['t0_s'];ratio=odd['AZ1_start_V']/even['AZ1_start_V']
  mean.append({'pair':int(even['ID']//2),'observed_AZ1_odd_over_even':ratio,'expected_single_exponential':math.exp(-dt/c['AZ_leak1_s']),
      'AZ1_even_V':even['AZ1_start_V'],'AZ1_odd_V':odd['AZ1_start_V'],'actual_interval_s':dt,
      'AZ2_infinite_unchanged_rawbits':np.float64(even['AZ2_start_V']).tobytes()==np.float64(odd['AZ2_start_V']).tobytes()})
 c['AZ_pair_hold']=mean
out={'scope':'Read-only engineering interpretation of actual 095606 logs; exact 8 sampled events and local 12.5ns interval, no new simulation/FFT or physical signoff',
 'receipt_sha256':sha(run/'receipt.json'),'independent_review_sha256':sha(ind_path),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'full_scale_diff_V':FSR,'declared_amplitude_V':amplitude,'declared_amplitude_relative_full_scale_dB':20*math.log10(amplitude/(FSR/2)),
 'RA_start_to_D2_first_nominal_s':12.5e-9,'Q_and_per_slice_inputs_bit_equal_across_three_cases':Q_bits_equal_across_cases,'cases':cases}
outfile=Path(__file__).with_name('az_dac_095606_physics.json');outfile.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='cases'},ensure_ascii=False,indent=2))
for c in cases:
 print('\n',c['name'])
 for k in ['AZ_leak1_s','declared_input_at_CNV_V','actual_held_at_CNV_V','Q0_signed_C','Q1_signed_C','Q_drift_signed_C','hypothetical_fixed_target_Q_unsettled_C','conditional_VX_lag_vs_instant_V','release_vtop_FE_V','inferred_group_return_charge_C','decision_peak_VY','discrete_event_peak_VX','code_difference_vs_far_mixed','AZ_pair_hold']:
  print(k,c.get(k))
