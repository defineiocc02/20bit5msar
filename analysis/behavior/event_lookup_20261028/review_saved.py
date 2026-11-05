#!/usr/bin/env python3
"""Read-only, independent MATLAB v7.3 simout review; never run MATLAB or edit source.

Usage:
  python review_saved.py --validation-dir /path/to/121500Z/validation --output /tmp/new-result
  python review_saved.py --self-check
The output directory must not already exist. This reader relies on the actual
saved MCOS timeseries layout and rejects unknown, partial or ambiguous layouts.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,sys
import h5py
import numpy as np

ROOT=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
DEFAULT_VALIDATION=ROOT/'runs/az_probe_20261028T121500Z/validation'
REFERENCES={
 'n8':ROOT/'runs/behavior_8165ddcc-971e-49a6-938b-ad2fb6dd9603',
 'n256':ROOT/'runs/behavior_47c22b65-fdff-402b-b315-ea0599df6891'}
EXPECTED_SOURCE={'old':'59e1c180ec3f1d71633717640ec445604405f71f8f69b49f679219d31b93629f',
                 'new':'59be23a252bb60f5a4b6e4612a28d0211c721a437edae66b73b64e6a3aecb018'}
EXPECTED_PIN='5d87bfd61335dc4db5f7adfb640f54e13a873cafa98471ee3ccea92829204183'
EXPECTED_MAIN='63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6'

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def raw_bytes(a):
 a=np.asarray(a);return a.tobytes(order='C')
def same(a,b):
 a=np.asarray(a);b=np.asarray(b)
 return a.shape==b.shape and a.dtype==b.dtype and raw_bytes(a)==raw_bytes(b)
def ds_class(d):
 v=d.attrs.get('MATLAB_class',b'')
 return v.decode() if isinstance(v,(bytes,np.bytes_)) else str(v)

def read_logs(file):
 """Conservative MCOS timeseries inventory adapted from reviewed actual 114345 parser."""
 with h5py.File(file,'r') as h:
  require('#subsystem#/MCOS' in h,f'{file}: no MCOS table')
  seq=[h[x] for x in h['#subsystem#/MCOS'][()].ravel()]
  candidates=[o for o in seq if isinstance(o,h5py.Group) and 'record_log' in o and 'record_ready_log' in o]
  require(len(candidates)==1,f'{file}: ambiguous/missing SimulationOutput group ({len(candidates)})')
  sim=candidates[0]; order=[]
  for k in sim:
   if k in ('tout','yout'):continue
   obj=sim[k]
   require(isinstance(obj,h5py.Dataset) and obj.size>=5,f'{file}: unrecognized SimulationOutput field {k}')
   order.append((int(obj[()].ravel()[4]),k))
  order.sort()
  require([i for i,_ in order]==list(range(2,2+5*len(order),5)),f'{file}: unexpected MCOS slot order')
  series=[]
  for i,o in enumerate(seq):
   if not(isinstance(o,h5py.Dataset) and o.dtype.name=='float64' and o.shape==(1,1)):continue
   n=o[()].item()
   if n<1 or n!=int(n) or i+11>=len(seq):continue
   flag,t,data=seq[i+1],seq[i+2],seq[i+11]
   if not(isinstance(flag,h5py.Dataset) and ds_class(flag)=='logical' and flag.size==1 and flag[()].item()==0):continue
   if not(isinstance(t,h5py.Dataset) and t.dtype.name=='float64' and t.shape==(1,int(n))):continue
   if not(isinstance(data,h5py.Dataset) and len(data.shape)>=2 and (data.shape[-1]==int(n) or int(n)==1)
      and data.dtype.name in ('float64','uint8') and ds_class(data) in ('double','logical')):continue
   raw=data[()];oriented=raw.transpose(tuple(range(raw.ndim-1,-1,-1)))
   if int(n)==1 and raw.shape[-1]!=1:oriented=oriented[None,...]
   series.append({'time':t[()].ravel(),'data':oriented,'raw_data':raw,
                  'data_class':ds_class(data),'raw_data_path':data.name,
                  'time_bytes':t.size*8,'data_bytes':raw.nbytes})
  require(len(series)==len(order),f'{file}: timeseries count {len(series)} != mapped {len(order)}')
  return {name:s for (_,name),s in zip(order,series)}

def scalar(h,key):
 a=np.asarray(h['P/'+key][()]);require(a.size==1,'Non-scalar P/'+key);return a.reshape(-1)[0].item()
def char_dataset(d):
 return ''.join(chr(int(c)) for c in np.asarray(d[()]).ravel() if int(c)!=0)
def read_parameters(file):
 with h5py.File(file,'r') as h:
  require('P' in h,f'{file}: missing P')
  v={k:scalar(h,k) for k in ['N','first_id','epoch','seed','Ts_s','fs_hz','fsr_diff_v','n_cycles','stop_time_s']}
  v['input']={k:scalar(h,'input/'+k) for k in ['offset_v','amplitude_v','frequency_hz','phase_rad']}
  v['seed_fields']={k:scalar(h,'front/'+k) for k in ['pool_seed','dem_seed','dither_seed','ktc_seed']}
  v['jitter_seed']=scalar(h,'front/jitter/seed')
  v['mode_flags']={k:bool(scalar(h,k)) for k in ['front/ktc_enabled','front/mismatch_enabled','front/dem_enabled',
      'front/dither_enabled','front/jitter/enabled','backend/dac_coupling/enabled','backend/ni/cinc_kick',
      'transport/enabled','training/enabled','training/reference/enabled','cal_cfg/enabled','frozen/enabled']}
  v['az_mode']=char_dataset(h['P/backend/az/mode'])
  v['tau_dac_s']=np.asarray(h['P/front/tau_dac_s'][()]).ravel()
  v['plan']=np.asarray(h['P/front/plan'][()]) # MATLAB transpose stored as 8 x rows
  v['C_f']=np.asarray(h['P/front/C_f'][()]);v['Cp_f']=np.asarray(h['P/front/Cp_f'][()])
  v['ra']={k:scalar(h,'backend/ra/'+k) for k in ['A0','UGB_hz','Cf_f','tau_reset_s','vos_input_v','slew_v_per_s']}
  v['ct_output_parasitic_half_f']=np.asarray(h['P/backend/ct/output_parasitic_half_f'][()]).ravel()
  fields=h['P/groups/time_s'][()].ravel();v['group_times']=np.array([np.asarray(h[r][()]).item() for r in fields],dtype=np.float64)
  f=h['P/calendar/type'][()].ravel();v['calendar_types']=[char_dataset(h[r]) for r in f]
  return v

def at_times(log,times,label):
 t=log['time'];require(np.all(np.isfinite(t)) and np.all(np.diff(t)>=0),f'{label}: invalid/decreasing time')
 require(len(np.unique(t))==len(t),f'{label}: repeated logger timestamps')
 i=np.searchsorted(t,times);require(np.all(i<len(t)),f'{label}: missing timestamp')
 require(np.array_equal(t[i],times),f'{label}: missing exact timestamp')
 return log['data'][i]
def records(logs,p):
 for k in ('record_log','record_ready_log','code_log','raw_log','ready_log'):
  require(k in logs,'Missing '+k)
 ready=logs['record_ready_log'];rflag=ready['data'].reshape(-1)
 require(np.all(np.isin(rflag,[0,1])),'Nonbinary actual RX ready')
 rt=ready['time'][rflag==1];require(len(np.unique(rt))==len(rt),'Duplicate RX ready times')
 rr=at_times(logs['record_log'],rt,'record_log');rc=at_times(logs['code_log'],rt,'code_log').reshape(-1)
 require(rr.ndim==2 and rr.shape[1]==6,'RAW6 shape mismatch')
 w=(rr[:,3]>=p['first_id'])&(rr[:,3]<p['first_id']+p['N'])
 selected=rr[w];codes=rc[w];st=rt[w]
 expected=np.arange(int(p['first_id']),int(p['first_id']+p['N']))
 require(len(selected)==p['N'] and np.array_equal(selected[:,3],expected) and np.all(selected[:,4]==p['epoch']),
         'Selected IDs/epoch/length do not match')
 require(np.all(selected[:,5]==1) and np.all(rr[:,5]==1),'At least one observed ready record is invalid/unknown')
 require(np.all(np.isfinite(codes)) and np.all(codes==np.floor(codes)) and np.all((codes>=0)&(codes<2**20)),
         'Selected code invalid')
 ardy=logs['ready_log'];aflag=ardy['data'].reshape(-1)
 require(np.all(np.isin(aflag,[0,1])),'Nonbinary ADC ready')
 at=ardy['time'][aflag==1];adc=at_times(logs['raw_log'],at,'raw_log')
 require(adc.ndim==2 and adc.shape[1]==6,'ADC RAW6 shape mismatch')
 by_tag={}
 for row in adc:
  tag=(int(row[3]),int(row[4]));require(tag not in by_tag,'Duplicate ADC raw tag');by_tag[tag]=row
 for row in rr:
  require(np.isfinite(row[3]) and np.isfinite(row[4]),'Invalid RX tag')
  tag=(int(row[3]),int(row[4]));require(tag in by_tag and same(row,by_tag[tag]),f'RX != ADC RAW at {tag}')
 return {'all_rx_time':rt,'all_rx_raw6':rr,'all_rx_code20':rc,'selected_time':st,'selected_raw6':selected,
         'selected_code20':codes,'adc_ready_count':len(adc)}

def compare_logs(a,b,excluded=()):
 names_a=set(a)-set(excluded);names_b=set(b)-set(excluded)
 require(names_a==names_b,'Timeseries name inventories differ: '+repr(sorted(names_a^names_b)))
 rows=[]
 for name in sorted(names_a):
  x=a[name];y=b[name]
  row={'name':name,'class_equal':x['data_class']==y['data_class'],
       'data_dtype_equal':x['raw_data'].dtype==y['raw_data'].dtype,
       'data_shape_equal':x['raw_data'].shape==y['raw_data'].shape,
       'time_shape_equal':x['time'].shape==y['time'].shape,
       'time_raw_bits_equal':same(x['time'],y['time']),
       'data_raw_bits_equal':same(x['raw_data'],y['raw_data']),
       'points':len(x['time']),'data_shape_hdf5':list(x['raw_data'].shape),
       'numeric_and_time_bytes':x['data_bytes']+x['time_bytes']}
  rows.append(row)
 return rows

def all_equal(rows):
 keys=('class_equal','data_dtype_equal','data_shape_equal','time_shape_equal','time_raw_bits_equal','data_raw_bits_equal')
 return all(all(row[k] for k in keys) for row in rows)

def read_saved_records(file,key):
 with h5py.File(file,'r') as h:
  require(key in h and isinstance(h[key],h5py.Group),f'{file}: missing {key} struct')
  group=h[key];out={}
  for name in ('selected_raw','selected_code20','selected_time_s','all_ready_raw','all_ready_code20','all_ready_time_s'):
   require(name in group,f'{file}: missing {name}');a=np.asarray(group[name][()])
   if name.endswith('_raw'):a=a.T
   else:a=a.ravel()
   out[name]=a
  return out

def check_saved_records(saved,actual,label):
 pairs={'selected_raw':'selected_raw6','selected_code20':'selected_code20','selected_time_s':'selected_time',
        'all_ready_raw':'all_rx_raw6','all_ready_code20':'all_rx_code20','all_ready_time_s':'all_rx_time'}
 for left,right in pairs.items():require(same(saved[left],actual[right]),f'{label}: saved {left} differs from raw logger')

def check_events(logs,p):
 e=logs['event_log'];d=e['data'];times=e['time'];n=int(p['n_cycles']);g=len(p['group_times'])
 require(d.shape==(n*g,2),'Unexpected event inventory dimensions')
 expected_tags=np.column_stack((np.repeat(np.arange(n,dtype=np.float64),g),np.tile(np.arange(1,g+1,dtype=np.float64),n)))
 expected_times=np.repeat(np.arange(n,dtype=np.float64)*p['Ts_s'],g)+np.tile(p['group_times'],n)
 require(same(d,expected_tags) and same(times,expected_times),'Actual event times/tags differ from saved P.groups')
 types=Counter(p['calendar_types']);require(types['d2_decide']==12 and types['ta_compare']==8 and types['ta_feedback']==7,
                                      'Saved M8 12/8/7 calendar differs')
 return {'actual_parent_hits':len(times),'cycles':n,'groups_per_cycle':g,'expected_ADC_groups_per_cycle':48,
         'exact_saved_group_time_and_tags':True,'declared_calendar_counts':{'D2_decide':12,'TA_compare':8,'TA_feedback':7},
         'scope':'Event log proves actual hit times/tags; calendar token counts alone are not observed physical feedback.'}

def check_n8_adi(logs,p):
 require('adi_wire_log' in logs,'ADI observer missing')
 w=logs['adi_wire_log'];ev=at_times(logs['event_log'],w['time'],'event_log for ADI');trace=w['data']
 require(trace.ndim==2 and trace.shape[1]==58,'ADI58 shape mismatch')
 result={}
 for sid in range(int(p['first_id']),int(p['first_id']+p['N'])):
  idx=np.flatnonzero((ev[:,0]==sid)&(ev[:,1]>=1)&(ev[:,1]<=48))
  require(len(idx)==48 and np.array_equal(ev[idx,1],np.arange(1,49)),'ADI ADC event inventory mismatch')
  counts=trace[idx[-1],51:54];require(np.array_equal(counts,[12,8,7]),'Actual ADI physical counters not 12/8/7')
  result[str(sid)]=[int(x) for x in counts]
 return result

def check_parameters(p,N):
 require(p['N']==N and p['first_id']==4 and p['epoch']==1 and p['seed']==20261020 and
         p['Ts_s']==2e-7 and p['fs_hz']==5e6 and p['fsr_diff_v']==8.192,'P record timing/seed differs')
 require(p['input']=={'offset_v':0.0,'amplitude_v':3.650563842595822,
                      'frequency_hz':97656.25,'phase_rad':0.731},'P stimulus differs')
 require(p['seed_fields']['pool_seed']==20269121 and len(p['group_times'])==49,'P plan seed/49 groups differs')
 require(np.all(p['tau_dac_s']==1e-9) and p['mode_flags']['backend/dac_coupling/enabled'] and
         p['mode_flags']['backend/ni/cinc_kick'] and p['mode_flags']['transport/enabled'] and p['az_mode']=='off',
         'P DAC/RA/RX scope differs')
 for name in ('front/ktc_enabled','front/mismatch_enabled','front/dem_enabled','front/dither_enabled',
              'front/jitter/enabled','training/enabled','training/reference/enabled','cal_cfg/enabled','frozen/enabled'):
  require(not p['mode_flags'][name],'Unexpected enabled '+name)
 require(p['ra']['A0']==10000 and p['ra']['UGB_hz']==1.2e9 and np.isinf(p['ra']['slew_v_per_s']) and
         np.all(p['ct_output_parasitic_half_f']==0.5e-12),'P analog baseline differs')
 require(p['n_cycles']==N+6,'P warmup/RX flush cycle count differs')

def run_case(name,folder,item):
 N={'n8':8,'n256':256}[name];pfile=folder/'parameters.mat';model=folder/'SarLookup.slx'
 old=folder/'old_simout.mat';new=folder/'new_simout.mat'
 for f in (pfile,model,old,new,folder/'old_records.mat',folder/'new_records.mat'):
  require(f.is_file(),'Missing saved artifact '+str(f))
 hashes={'parameters_mat':digest(pfile),'scratch_slx':digest(model),'old_simout':digest(old),'new_simout':digest(new)}
 for actual,key in [('parameters_mat','input_P_sha256'),('scratch_slx','model_sha256'),('old_simout','old_simout_sha256'),('new_simout','new_simout_sha256')]:
  require(hashes[actual]==item[key],f'{name}: hash differs from native receipt for {key}')
 require(item['old_event_source_sha256']==EXPECTED_SOURCE['old'] and item['new_event_source_sha256']==EXPECTED_SOURCE['new'],
         f'{name}: old/new source hash differs from frozen candidate')
 p=read_parameters(pfile);check_parameters(p,N)
 x=read_logs(old);y=read_logs(new);ab=compare_logs(x,y)
 require(len(ab)==30 and all_equal(ab),f'{name}: old/new 30 log bit gate failed')
 reference=read_logs(REFERENCES[name]/'simout.mat')
 ref=compare_logs(reference,x,('adi_wire_log',) if name=='n8' else ())
 require(len(ref)==(29 if name=='n8' else 30) and all_equal(ref),f'{name}: saved reference bit gate failed')
 a=records(x,p);b=records(y,p)
 for key in a:
  if isinstance(a[key],np.ndarray):require(same(a[key],b[key]),f'{name}: A/B record mismatch {key}')
  else:require(a[key]==b[key],f'{name}: A/B record scalar mismatch {key}')
 check_saved_records(read_saved_records(folder/'old_records.mat','oldRecord'),a,name+' old')
 check_saved_records(read_saved_records(folder/'new_records.mat','newRecord'),b,name+' new')
 events=check_events(x,p)
 adi=check_n8_adi(x,p) if name=='n8' else None
 H=events['actual_parent_hits'];K=int(math.ceil(math.log2(H+1)))
 timing={key:float(item[key]) for key in ('old_update_s','new_update_s','old_sim_s','new_sim_s')}
 require(all(math.isfinite(v) and v>=0 for v in timing.values()),'Invalid saved native timing')
 timing.update({'old_sim_per_selected_sample_s':timing['old_sim_s']/N,'new_sim_per_selected_sample_s':timing['new_sim_s']/N,
                'old_sim_per_parent_hit_s':timing['old_sim_s']/H,'new_sim_per_parent_hit_s':timing['new_sim_s']/H,
                'single_ordered_sim_difference_s':timing['new_sim_s']-timing['old_sim_s'],
                'single_ordered_old_over_new':timing['old_sim_s']/timing['new_sim_s'] if timing['new_sim_s']>0 else None,
                'scope':'One unprofiled old-then-new pair; full sim wall includes model startup and logging. Per-sample/hit values are arithmetic averages, not event CPU measurements; no stable speed claim.'})
 result={'case':name,'record_count':N,'hashes_as_reported_and_independently_read':hashes,
         'old_new_log_count':len(ab),'old_new_all_30_bit_equal':all_equal(ab),'reference_log_count':len(ref),
         'reference_all_bit_equal':all_equal(ref),'actual_RX_ready_count':len(a['all_rx_raw6']),
         'actual_ADC_ready_count':a['adc_ready_count'],'valid_zero_count':int(np.count_nonzero(a['all_rx_raw6'][:,5]==0)),
         'valid_unknown_count':int(np.count_nonzero(~np.isin(a['all_rx_raw6'][:,5],[0,1]))),
         'selected_ID_first':int(a['selected_raw6'][0,3]),'selected_ID_last':int(a['selected_raw6'][-1,3]),
         'selected_epoch':int(p['epoch']),'RX_ADC_raw_equal_for_all_ready':True,'saved_records_match_actual_log':True,
         'events':events,'actual_N8_adi_counters':adi,'timing':timing,
         'complexity':{'H_actual_parent_hits':H,'old_vector_boolean_elements_if_one_outputs_per_hit':2*H*H,
                       'candidate_binary_upper_comparison_bound_if_one_outputs_per_hit':H*K,'binary_steps_per_call_bound':K,
                       'scope':'Analytical count under one Outputs call per observed hit; actual callback count, CPU and acceleration are unmeasured.'},
         'input':p['input'],'plan_shape_hdf5':list(p['plan'].shape),'plan_sha256_raw':hashlib.sha256(raw_bytes(p['plan'])).hexdigest(),
         'source_sha256':{'old':item['old_event_source_sha256'],'new':item['new_event_source_sha256']}}
 return result,ab,ref,p,a

def self_check():
 for name,ref in REFERENCES.items():
  p=read_parameters(ref/'parameters.mat');N={'n8':8,'n256':256}[name];check_parameters(p,N)
  logs=read_logs(ref/'simout.mat');require(len(logs)==30,'Fixture expected 30 TS logs')
  r=records(logs,p);events=check_events(logs,p)
  print(json.dumps({'fixture':name,'logs':len(logs),'selected':len(r['selected_code20']),
                    'actual_event_hits':events['actual_parent_hits'],'status':'reader_self_check_only_not_121500'},ensure_ascii=False))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--validation-dir',type=Path,default=DEFAULT_VALIDATION)
 ap.add_argument('--output',type=Path);ap.add_argument('--self-check',action='store_true')
 ap.add_argument('--n256-only',action='store_true',help='Review N256 if its N8 A/B files have not yet been mirrored.')
 args=ap.parse_args()
 if args.self_check:self_check();return
 require(args.output is not None,'--output must specify a fresh /tmp directory')
 dest=args.output.resolve();require(str(dest).startswith('/tmp/') or str(dest).startswith('/private/tmp/'),'Output must be inside /tmp')
 require(not dest.exists(),'Output directory already exists; refuse overwrite')
 folder=args.validation_dir.resolve();receipt=folder/'receipt.json'
 require(receipt.is_file(),'121500 validation receipt has not been mirrored yet: '+str(receipt))
 R=json.loads(receipt.read_text());require(R.get('status')=='scratch_M8_N8_N256_actual_pair_complete_pending_independent_review',
   'Native A/B not complete: '+str(R.get('status')))
 require(R.get('main_model_sha_expected')==EXPECTED_MAIN and R.get('external_pins_sha256')==EXPECTED_PIN,
         'Native source/model manifest identity differs')
 require(R.get('main_file_unchanged') is True and R.get('global_rng_unchanged') is True and
         R.get('environment_cleanup')=='complete','Native main/RNG/environment receipt not clean')
 pure=R.get('pure_and_abnormal_index_gate',{});abnormal=R.get('abnormal_index_gate',{})
 require(pure.get('status')=='native_pure_lookup_and_abnormal_index_gate_pass' and
         pure.get('saved_actual_event_log_equal') is True,'Native pure event gate not passed')
 require(abnormal.get('before_start_matching',0)>0 and abnormal.get('strict_future_matching',0)>0 and
         abnormal.get('duplicate_and_reverse_precondition_rejected') is True and
         abnormal.get('duplicate_and_reverse_offset_rejected') is True,'Native abnormal-index gate incomplete')
 items={v['name']:v for v in R['cases']};require(set(items)=={'n8','n256'},'Native case inventory differs')
 n256,logs256,ref256,p256,r256=run_case('n256',folder/'n256',items['n256'])
 if args.n256_only:
  p8=read_parameters(REFERENCES['n8']/'parameters.mat');check_parameters(p8,8)
  r8=records(read_logs(REFERENCES['n8']/'simout.mat'),p8)
  n8=logs8=ref8=None
 else:
  n8,logs8,ref8,p8,r8=run_case('n8',folder/'n8',items['n8'])
 require(same(p8['plan'],p256['plan'][:,:p8['plan'].shape[1]]) and same(p8['C_f'],p256['C_f']) and
         same(p8['Cp_f'],p256['Cp_f']) and p8['seed_fields']==p256['seed_fields'] and p8['input']==p256['input'],
         'N8/N256 saved plan prefix, analog matrix, seed, or stimulus differs')
 require(same(r8['selected_raw6'],r256['selected_raw6'][:8]) and
         same(r8['selected_code20'],r256['selected_code20'][:8]) and
         same(r8['selected_time'],r256['selected_time'][:8]),'N256 actual first 8 records differ from N8')
 status='independent_saved_N256_readback_pass_N8_AB_not_reviewed' if args.n256_only else 'independent_saved_A_B_readback_pass'
 result={'schema':'independent-event-lookup-121500-review/v1','status':status,
         'validation_dir':str(folder),'native_receipt_sha256':digest(receipt),'external_pins_sha256':EXPECTED_PIN,
         'source_sha256':EXPECTED_SOURCE,'case_results':([n256] if args.n256_only else [n8,n256]),
         'N8_comparison_source':('archived production N8, not the new A/B' if args.n256_only else 'new scratch N8 A/B'),
         'N8_N256_plan_C_seed_input_and_first_8_equal':True,
         'native_abnormal_index_gate':abnormal,'review_script_sha256':digest(Path(__file__)),
         'limits':['Independent readback of these actual saved files; same-path compiled-source provenance is from native binding receipt.',
                   'Only one ordered old-then-new pair each; timing ratio is descriptive, not stable acceleration.',
                   'All visible log equality does not prove unobserved full analog state or every possible input.',
                   'Pure event rule error gate is not a separate Simulink malformed-schedule compile test.',
                   'No M1 N256 A/B or PDK signoff is claimed.']}
 dest.mkdir(parents=True)
 (dest/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with (dest/'log_bit_comparison.csv').open('w',newline='') as f:
  fields=['case','comparison']+list(logs256[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  groups=([('n256','old_vs_new',logs256),('n256','archived_vs_old',ref256)] if args.n256_only else
          [('n8','old_vs_new',logs8),('n8','archived_vs_old',ref8),('n256','old_vs_new',logs256),('n256','archived_vs_old',ref256)])
  for case,comp,rows in groups:
   for row in rows:w.writerow({'case':case,'comparison':comp,**row})
 lines=['# 121500 事件查找性能：独立保存原件回读','','结果来自实际已保存的P/SLX/simout和单次有序old→new；并非稳定速度结论。','',
        '| 记录 | 原/新30路 | 与旧归档 | 原/新sim (s) | 原/新update (s) | 单次原/新比 |',
        '|---|---:|---:|---:|---:|---:|']
 for r in ([n256] if args.n256_only else [n8,n256]):
  t=r['timing'];ratio=t['single_ordered_old_over_new'];rat='不可算' if ratio is None else f'{ratio:.4f}'
  lines.append(f"| {r['case']} | {r['old_new_log_count']}/30位同 | {r['reference_log_count']}路位同 | {t['old_sim_s']:.6f} / {t['new_sim_s']:.6f} | {t['old_update_s']:.6f} / {t['new_update_s']:.6f} | {rat} |")
 lines += ['','模拟耗时除以输出码数或实际parent hit数是整次sim wall的算术均值，包含启动与日志，不是单事件CPU耗时。',
           '源索引复杂度仅是假设每个已观察parent hit调用一次Outputs的上界估算；真实回调次数及热点需要profiler。',
           ('本次只回读N256，未核新N8 A/B；N256未开启ADI，不能据event token推称N256全物理状态已观察。' if args.n256_only else
            'N8另核ADI真实12/8/7；N256未开启ADI，不能据event token推称N256全物理状态已观察。'),
           '原始hash和逐路比对见同目录 JSON/CSV；单次旧→新顺序未控制缓存与预热，不应推广为稳定加速。']
 (dest/'REVIEW.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'status':result['status'],'output':str(dest),'n8_30':None if n8 is None else n8['old_new_all_30_bit_equal'],
                   'n256_30':n256['old_new_all_30_bit_equal']},ensure_ascii=False))

if __name__=='__main__':
 try:main()
 except Exception as e:print('REVIEW_INCOMPLETE: '+str(e),file=sys.stderr);sys.exit(2)
