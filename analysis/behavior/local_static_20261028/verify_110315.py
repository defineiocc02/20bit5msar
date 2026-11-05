#!/usr/bin/env python3
"""Independent, read-only reconstruction of saved 110315 local DC points."""
import hashlib,json,zipfile
from pathlib import Path
import h5py
import numpy as np
import sys
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import at,decode,need,pdiff,read_calendar,read_logs,same,sha,val

job=root/'runs/az_probe_20261028T110315Z';run=job/'static_result'
receipt=json.loads((run/'receipt.json').read_text());outer=json.loads((job/'receipt.json').read_text())
need(receipt['stage']=='complete' and receipt['status']=='three_actual_transition_intervals_conditional_local_DNL_bounds',
     'Static result is not complete')
need(sha(run/'receipt.json')==outer['result_receipt_sha256'],'Outer receipt/result SHA mismatch')
need(sha(run/'SarAdc_factory.slx')==receipt['model_sha256']==outer['current_model_sha256'],
     'Factory model snapshot SHA mismatch')
need(sha(run/'source_manifest.json')==receipt['source_manifest_sha256'] and
     sha(run/'source.zip')==receipt['source_zip_sha256'],'Archived source identity mismatch')
manifest=json.loads((run/'source_manifest.json').read_text());rows=manifest.get('files',manifest)
pins={r['path'].replace('\\','/'):r['sha256'] for r in rows}
with zipfile.ZipFile(run/'source.zip','r') as z:
    need(set(z.namelist())==set(pins),'Archived source ZIP inventory differs from manifest')
    for name,digest in pins.items():need(hashlib.sha256(z.read(name)).hexdigest()==digest,'Source SHA mismatch '+name)

def signal_struct(path):
    with h5py.File(path,'r') as h:
        need('signals' in h and '#subsystem#/MCOS' in h,'Unsupported saved timeseries struct')
        seq=[h[r] for r in h['#subsystem#/MCOS'][()].ravel()];s=h['signals']
        names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)]
        found=[]
        for i,d in enumerate(seq):
            if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
            ns,t=seq[i-11],seq[i-9]
            if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and
                   isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
            count=int(ns[()].item())
            if count>0 and t.shape==(1,count) and (count==1 or d.shape[-1]==count):
                cls=d.attrs.get('MATLAB_class',b'');cls=cls.decode() if isinstance(cls,bytes) else str(cls)
                found.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,count)).T,'class':cls})
        need(len(names)==len(found)==9 and len(names)==len(set(names)),'Unsupported nine-series serialization')
        return dict(zip(names,found))

keep=['back_log','code_log','control_log','event_log','front_log','raw_log','ready_log','record_log','record_ready_log']
full=read_logs(run/'preflight_full_simout.mat');short=read_logs(run/'preflight_capped_simout.mat')
need(sha(run/'preflight_full_simout.mat')==receipt['observer_gate']['full_simout_sha256'] and
     sha(run/'preflight_capped_simout.mat')==receipt['observer_gate']['capped_simout_sha256'],
     'Full/capped preflight file SHA mismatch')
need(set(keep)==set(receipt['observer_gate']['log_names']) and all(k in full and k in short and
     full[k]['class']==short[k]['class'] and same(full[k]['time'],short[k]['time']) and
     same(full[k]['data'],short[k]['data']) for k in keep),'Full/capped nine-log raw bit mismatch')

N=31;native=receipt['points'];need(len(native)==N,'Expected exactly 31 saved point records')
lsb=float(receipt['nominal_lsb_v']);resolution=float(receipt['required_bracket_width_v'])
need(lsb==7.8125e-6 and resolution==lsb/256,'Nominal LSB or original resolution differs')
samples=[];Pfirst=run/'point_001/P.mat'
for index,pt in enumerate(native,1):
    folder=run/f'point_{index:03d}';need(pt['index']==index and pt['status']=='valid','Missing/invalid point')
    for filename,key in [('P.mat','P_mat_sha256'),('signals.mat','signals_sha256'),('observed.mat','observed_sha256')]:
        need(sha(folder/filename)==pt[key],f'Point {index} {filename} SHA mismatch')
    diffs=pdiff(Pfirst,folder/'P.mat');allowed={'P/input/offset_v','P/front/input/offset_v','P/xFE0'}
    need(set(diffs)<=allowed,f'Point {index} unexpected saved P differences {diffs}')
    with h5py.File(folder/'P.mat','r') as f:
        off=float(val(f,'P/input/offset_v'));Ts=float(val(f,'P/Ts_s'))
        need(off==pt['voltage_v'] and val(f,'P/front/input/offset_v')==off and
             val(f,'P/input/amplitude_v')==0 and val(f,'P/front/input/amplitude_v')==0 and
             val(f,'P/N')==1 and val(f,'P/first_id')==4 and val(f,'P/epoch')==1 and
             val(f,'P/n_cycles')==5 and val(f,'P/seed')==20261020 and Ts==2e-7 and
             val(f,'P/fsr_diff_v')==8.192 and not val(f,'P/transport/enabled') and
             not val(f,'P/training/enabled') and not val(f,'P/frozen/enabled') and
             not val(f,'P/front/ktc_enabled') and not val(f,'P/front/mismatch_enabled') and
             not val(f,'P/front/dem_enabled') and not val(f,'P/front/dither_enabled') and
             not val(f,'P/front/jitter/enabled') and val(f,'P/backend/az/mode')=='off' and
             np.all(np.asarray(val(f,'P/front/tau_dac_s'))==0) and not val(f,'P/backend/dac_coupling/enabled'),
             f'Point {index} saved configuration mismatch')
        times,groups,budget=read_calendar(f)
        dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v',
             'd2_weights_ra_v','tracking_step_ra_v']}
        need(not val(f,'P/digital/dither_enabled') and val(f,'P/digital/az_mode')=='off',
             'Independent nominal decoder scope mismatch')
    L=signal_struct(folder/'signals.mat');need(set(L)==set(keep),f'Point {index} logger inventory differs')
    t=L['event_log']['time'];e=L['event_log']['data'];need(e.shape==(240,2) and
        np.array_equal(e[:,0],np.repeat(np.arange(5),48)) and
        np.array_equal(e[:,1],np.tile(np.arange(1,49),5)),f'Point {index} event group order differs')
    expected=np.array([i*Ts+x for i in range(5) for x in times])
    need(same(t,expected),f'Point {index} actual times differ from saved calendar')
    for k in keep:need(same(t,L[k]['time']),f'Point {index} {k} event time alignment differs')
    ready=L['ready_log']['data'][:,0];recReady=L['record_ready_log']['data'][:,0]
    need(np.all(np.isin(ready,[0,1])) and same(ready,recReady),f'Point {index} ready flags differ')
    ri=np.flatnonzero(ready==1);need(len(ri)==5 and np.all(e[ri,1]==47) and
         np.array_equal(e[ri,0],np.arange(5)),'Five actual raw_latch pulses not present')
    raw=L['raw_log']['data'][ri];rr=L['record_log']['data'][ri]
    codes=L['code_log']['data'][ri,0];rt=t[ri]
    need(same(raw,rr) and np.array_equal(raw[:,3],np.arange(5)) and np.all(raw[:,4]==1) and
         np.all(raw[:,5]==1) and np.all(np.isfinite(codes)) and np.all(codes==np.floor(codes)),
         'Actual warmup/selected RAW validity or ready data differs')
    code=int(codes[-1]);need(decode(raw[-1],dig)==code,'Public RAW-derived nominal integer code mismatch')
    held=float(L['front_log']['data'][ri[-1],0]);need(abs(held-off)<=resolution/16,
         'Observed held input exceeds original axis gate')
    with h5py.File(folder/'observed.mat','r') as f:
        need(same(np.asarray(val(f,'obs/all_ready_raw6')),raw) and
             same(np.asarray(val(f,'obs/all_ready_code20')).ravel(),codes) and
             same(np.asarray(val(f,'obs/all_ready_time_s')).ravel(),rt) and
             same(np.asarray(val(f,'obs/raw6')).ravel(),raw[-1]) and
             val(f,'obs/code20')==code and val(f,'obs/public_decode_code20')==code and
             val(f,'obs/ready_time_s')==rt[-1] and val(f,'obs/held_input_v')==held and
             val(f,'obs/held_minus_requested_v')==held-off and val(f,'obs/event_groups_per_id')==48,
             f'Point {index} observed MAT vs actual signal mismatch')
    need(np.array_equal(np.asarray(pt['all_ready_raw6']),raw) and np.array_equal(np.asarray(pt['raw6']),raw[-1]) and
         np.array_equal(np.asarray(pt['all_ready_code20']),codes) and np.array_equal(np.asarray(pt['all_ready_time_s']),rt) and
         pt['code20']==code and pt['held_input_v']==held and pt['held_minus_requested_v']==held-off,
         f'Point {index} receipt vs actual signal mismatch')
    samples.append({'index':index,'voltage_v':off,'code20':code,'raw6':raw[-1].tolist(),
                    'selected_ready_s':float(rt[-1]),'held_input_v':held,
                    'held_minus_requested_v':held-off,'all_ready_raw6':raw.tolist(),
                    'P_sha256':pt['P_mat_sha256'],'signals_sha256':pt['signals_sha256'],
                    'observed_sha256':pt['observed_sha256'],'P_difference_vs_point1':diffs})

ordered=sorted(samples,key=lambda x:x['voltage_v']);need(all(a['code20']<=b['code20'] for a,b in zip(ordered,ordered[1:])),
                                                         'Measured samples contain a reverse code step')
targets=[524290,524291,524292];endpoints=[lsb*i for i in range(1,5)];want=[524289,524290,524291,524292]
need(all(samples[i]['voltage_v']==endpoints[i] and samples[i]['code20']==want[i] for i in range(4)),
     'Four original endpoints differ')
cursor=4;transitions=[]
for i,target in enumerate(targets):
    lo=endpoints[i];hi=endpoints[i+1];iterations=0
    while hi-lo>resolution:
        mid=lo+(hi-lo)/2;p=samples[cursor];cursor+=1;iterations+=1
        need(p['voltage_v']==mid and p['code20'] in (target-1,target),'Actual bisection sequence/code differs')
        if p['code20']<target:lo=mid
        else:hi=mid
    stored=receipt['transitions'][i]
    need(stored['transition_to_code']==target and stored['lo_v']==lo and stored['hi_v']==hi and
         stored['bracket_width_v']==hi-lo and stored['bisection_measurements']==iterations and
         stored['lo_actual_code']==target-1 and stored['hi_actual_code']==target,
         'Stored threshold bracket differs from raw replays')
    transitions.append({'to_code':target,'lo_v':lo,'hi_v':hi,'width_v':hi-lo,'iterations':iterations})
need(cursor==N,'Point sequence does not end after three threshold searches')
widths=[]
for i in range(2):
    a,b=transitions[i:i+2];lo=b['lo_v']-a['hi_v'];hi=b['hi_v']-a['lo_v'];saved=receipt['local_widths'][i]
    need(saved['code']==a['to_code'] and saved['width_lower_v']==lo and saved['width_upper_v']==hi and
         saved['dnl_lower_lsb']==lo/lsb-1 and saved['dnl_upper_lsb']==hi/lsb-1,
         'Reported width/DNL bounds differ from actual interval arithmetic')
    widths.append({'code':a['to_code'],'width_lower_v':lo,'width_upper_v':hi,
                   'dnl_lower_lsb':lo/lsb-1,'dnl_upper_lsb':hi/lsb-1})
report={'schema':'sar20-110315-independent-local-dc/v1','verifier_sha256':sha(Path(__file__).resolve()),
        'receipt_sha256':sha(run/'receipt.json'),'model_sha256':sha(run/'SarAdc_factory.slx'),
        'source_zip_sha256':sha(run/'source.zip'),'source_files_verified':len(pins),
        'preflight_nine_Time_Data_class_shape_bits_equal':True,'preflight_scope':'Only zero-input N1, full vs capped logging',
        'point_count':len(samples),'each_point':'Saved P, nine actual timeseries, observed MAT and receipt read back; no new simulation',
        'four_actual_warmups_then_ID4':True,'per_ID_event_groups':48,'all_warmup_and_selected_valid':True,
        'measured_point_codes_nondecreasing':True,'max_abs_held_minus_requested_v':max(abs(x['held_minus_requested_v']) for x in samples),
        'original_input_axis_tolerance_v':resolution/16,'points':samples,'transition_brackets':transitions,
        'nominal_lsb_v':lsb,'conditional_local_DNL_bounds':widths,
        'scope':'The two DNL intervals are conditional on monotonic and single adjacent transitions between unsampled inputs; '
                'bracket endpoint inclusion is not established. Four warmups do not prove general steady state. '
                'No global monotonicity, full-range DNL/INL, silicon or PDK claim.',
        'per_point_retention':'Nine saved native timeseries; full SimulationOutput and ErrorMessage are not retained per point; '
                              'native no-error assertion and override details are from receipt/job source.'}
print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
