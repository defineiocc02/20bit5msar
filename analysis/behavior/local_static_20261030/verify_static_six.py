#!/usr/bin/env python3
"""Offline verification of an actual six-point run; prints JSON, writes nothing."""
from __future__ import annotations
import argparse, hashlib, json, math, sys, zipfile
from pathlib import Path

MODEL='ae2d2b023362fd39b1cfaad39278b8c91fbad23d542f19df864547fb7e77e733'
STATE='63d4d082b511837b47afc559b1079f7b2a3bdc847bd0d861e4b65a8b6c378ee5'
PINS='edeabf9ec82d33a844cf36581ed0fd3d5d5f9da27e79e76ab15daea393278e32'
LSB=7.8125e-6
X=[-LSB/4096,0,7.8277587890625e-6,7.843017578125e-6,15.6707763671875e-6,15.68603515625e-6]


def verify_logs(logs, Ppath, offset, util, np, h5py):
    need,at,same,val,decode=util.need,util.at,util.same,util.val,util.decode
    keep=['back_log','code_log','control_log','event_log','front_log','raw_log','ready_log','record_log','record_ready_log']
    need(all(n in logs for n in keep),'Missing actual logger')
    with h5py.File(Ppath,'r') as f:
        need(float(val(f,'P/input/offset_v'))==offset and float(val(f,'P/input/amplitude_v'))==0,'Wrong point stimulus')
        need(int(val(f,'P/N'))==1 and int(val(f,'P/first_id'))==4 and int(val(f,'P/epoch'))==1,'Wrong N/ID/epoch')
        need(int(val(f,'P/n_cycles'))==5 and float(val(f,'P/digital/fsr_diff_v'))==8.192,'Wrong cycles or FSR')
        dig={k:val(f,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v','d2_weights_ra_v','tracking_step_ra_v']}
        _,_,budget=util.read_calendar(f)
    event=logs['event_log'];time=event['time'];ev=event['data']
    need(ev.shape==(240,2) and np.array_equal(ev[:,0],np.repeat(np.arange(5),48)) and
         np.array_equal(ev[:,1],np.tile(np.arange(1,49),5)),'Wrong actual event groups')
    for n in keep:
        need(same(time,logs[n]['time']),f'{n} Time differs from event Time')
    adc=logs['ready_log']['data'][:,0];rec=logs['record_ready_log']['data'][:,0]
    need(np.all(np.isin(adc,[0,1])) and same(adc,rec),'ADC/record ready differs')
    ix=np.flatnonzero(rec==1)
    need(len(ix)==5 and np.array_equal(ev[ix,0],np.arange(5)) and np.all(ev[ix,1]==47),'Wrong ready IDs/groups')
    times=time[ix]
    raw=at(logs['raw_log'],times,'raw_log');record=at(logs['record_log'],times,'record_log')
    codes=at(logs['code_log'],times,'code_log')[:,0]
    held=at(logs['front_log'],times,'front_log')[:,0]
    need(same(raw,record) and np.array_equal(raw[:,3],np.arange(5)) and
         np.all(raw[:,4]==1) and np.all(raw[:,5]==1),'Wrong actual RAW/epoch/valid')
    need(np.all(np.isfinite(held)) and np.all(np.abs(held-offset)<=LSB/2**24),'Actual held input outside axis tolerance')
    need(np.all(np.isfinite(codes)) and all(decode(row,dig)==int(c) and int(c)==c for row,c in zip(raw,codes)),
         'Actual code differs from independent public decode')
    return {'requested_v':offset,'held_v':float(held[-1]),'all_held_v':held.tolist(),
            'raw6':raw[-1].tolist(),'all_raw6':raw.tolist(),'code20':int(codes[-1]),
            'all_code20':[int(v) for v in codes],'ready_time_s':float(times[-1]),
            'calendar_budget':budget}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',required=True,type=Path)
    ap.add_argument('--project',required=True,type=Path)
    a=ap.parse_args(); result=a.result.resolve(); project=a.project.resolve()
    sys.path.insert(0,str(project/'analysis/behavior/finite_dac_review_20261028'))
    import verify_as_run as u
    import h5py
    import numpy as np
    need=u.need;sha=u.sha
    R=json.loads((result/'receipt.json').read_text())
    need(R['status'] in ('six_actual_points_conditional_local_dnl','six_actual_points_no_local_dnl'),'Run was partial or restoration failed')
    need(R.get('model_source_workspace_parameters_unchanged') and R['cleanup']['status']=='complete','Identity or cleanup gate not passed')
    need(sha(result/'SarAdc_as_run.slx')==MODEL==R['model_sha256'],'Model pin mismatch')
    need(sha(result/'applied_config_as_run.json')==STATE==R['state_sha256'],'State pin mismatch')
    need(sha(result/'source_pins.json')==PINS==R['source_pins_sha256'],'Source pin manifest mismatch')
    need(sha(result/'sar20_static_six_ae2d.m')==R['candidate_sha256'],'Candidate source mismatch')
    need(sha(result/'source.zip')==R['source_zip_sha256'],'Source ZIP hash mismatch')
    pin_rows=json.loads((result/'source_pins.json').read_text())['files']
    pins={r['path'].replace('\\','/'):r['sha256'] for r in pin_rows}
    need(len(pins)==len(pin_rows)==105,'Unexpected source pin inventory')
    with zipfile.ZipFile(result/'source.zip') as z:
        names=z.namelist();need(len(names)==len(set(names)) and set(names)==set(pins),'Source ZIP inventory mismatch')
        for n,h in pins.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Source ZIP hash mismatch: '+n)
    need(len(R['points'])==len(X),'Wrong number of recorded points')
    points=[]; pfiles=[]
    for i,(p,x) in enumerate(zip(R['points'],X),1):
        folder=result/f'point_{i:02d}';pfile=folder/'P.mat';pfiles.append(pfile)
        need(p['index']==i and p['status']=='valid' and p['requested_v']==x and p['global_rng_unchanged'],f'Point {i} receipt mismatch')
        for name,key in [('P.mat','P_sha256'),('simout.mat','simout_sha256'),('observed.mat','observed_sha256')]:
            need(sha(folder/name)==p[key],f'Point {i} {name} SHA mismatch')
        with h5py.File(pfile,'r') as f:
            for k in ['bank/enabled','transport/enabled','training/enabled','training/reference/enabled',
                      'cal_cfg/enabled','frozen/enabled','front/ktc_enabled','front/mismatch_enabled',
                      'front/dem_enabled','front/dither_enabled','front/jitter/enabled','backend/dac_coupling/enabled']:
                need(int(u.val(f,'P/'+k))==0,f'Point {i} {k} unexpectedly enabled')
            need(float(u.val(f,'P/backend/ra/A0'))==1e4 and float(u.val(f,'P/backend/ra/UGB_hz'))==1.2e9,
                 f'Point {i} RA profile mismatch')
        diff=set(u.pdiff(pfiles[0],pfile))
        need(diff <= {'P/input/offset_v','P/front/input/offset_v','P/xFE0'},f'Point {i} unexpected P differences: {diff}')
        q=verify_logs(u.read_logs(folder/'simout.mat'),pfile,x,u,np,h5py)
        o=p['observation']
        need(q['held_v']==o['held_input_v'] and q['code20']==o['code20'] and q['ready_time_s']==o['ready_time_s'],
             f'Point {i} selected result differs from receipt')
        need(np.array_equal(np.asarray(q['all_raw6']),np.asarray(o['all_ready_raw6'])) and
             np.array_equal(np.asarray(q['all_code20']),np.asarray(o['all_ready_code20'])),f'Point {i} RAW/code differs from receipt')
        points.append(q)
    held=[p['held_v'] for p in points];codes=[p['code20'] for p in points]
    need(all(a<b for a,b in zip(held,held[1:])),'Actual held inputs not ordered')
    local=None
    if codes[3]==codes[2]+1 and codes[4]==codes[3] and codes[5]==codes[4]+1:
        lo=(held[4]-held[3])/LSB-1;hi=(held[5]-held[2])/LSB-1
        local={'code':codes[3],'dnl_lower_lsb':lo,'dnl_upper_lsb':hi}
        saved=R['local_dnl']
        need(R['status']=='six_actual_points_conditional_local_dnl' and saved['code']==codes[3] and
             math.isclose(saved['dnl_lower_lsb'],lo,rel_tol=0,abs_tol=1e-12) and
             math.isclose(saved['dnl_upper_lsb'],hi,rel_tol=0,abs_tol=1e-12),'Conditional DNL receipt mismatch')
    else:
        need(R['status']=='six_actual_points_no_local_dnl' and not R['local_dnl'],'Inconsistent no-DNL outcome')
    Z=R['zero_window']
    need(Z['code_low']==codes[0] and Z['code_high']==codes[1] and Z['code_delta']==codes[1]-codes[0],
         'Zero-window receipt mismatch')
    print(json.dumps({'status':'actual_raw_independently_read','points':points,
        'observed_codes_nondecreasing':all(a<=b for a,b in zip(codes,codes[1:])),
        'zero_window':{'held_low_v':held[0],'held_high_v':held[1],'code_low':codes[0],
                       'code_high':codes[1],'code_delta':codes[1]-codes[0]},
        'conditional_local_dnl':local,'model_sha256':MODEL,'source_files_verified':len(pins),
        'scope':'Finite samples only; no global DNL/INL, missing-code, steady-state or unsampled monotonicity proof.'},
        ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
