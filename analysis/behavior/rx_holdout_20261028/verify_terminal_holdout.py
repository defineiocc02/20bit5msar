#!/usr/bin/env python3
"""Post-terminal public RX/Ref/frozen-h holdout audit. No simulation or writes.

This script MUST NOT be run before the holdout job's terminal receipt. It checks
that receipt before opening any holdout run/P/log data. Only explicitly allowed
public HDF5 datasets are read; no frontend/back-end analog logger, held voltage,
actual C, full P, or prior holdout result is opened or hashed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import h5py
import numpy as np

REPORT={'schema':'sar20-rx-holdout-independent-terminal-audit/v1',
        'status':'not_started','analog_held_or_actual_C_read':False,
        'refit':False,'gain_offset_fit':False,'coefficient_update':False,
        'new_tolerance':False}

def need(ok,msg):
    if not ok: raise ValueError(msg)

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def same(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()

def val(f,path):
    n=f[path];a=np.asarray(n[()]);cls=n.attrs.get('MATLAB_class',b'')
    if cls==b'char':return ''.join(chr(int(x)) for x in a.ravel() if int(x))
    return a.ravel()[0].item() if a.size==1 else a.T

def fingerprint(f,node,memo):
    """Only call on the explicitly whitelisted public cfg/cache subtrees."""
    key=h5py.h5o.get_info(node.id).addr
    if key in memo:return memo[key]
    cls=str(node.attrs.get('MATLAB_class',b''))
    if isinstance(node,h5py.Group):
        v=('group',cls,tuple((k,fingerprint(f,node[k],memo)) for k in sorted(node)))
    else:
        a=np.asarray(node[()])
        if h5py.check_dtype(ref=node.dtype) is not None:
            v=('refs',cls,a.shape,tuple(fingerprint(f,f[r],memo) if r else None for r in a.ravel()))
        else:v=('data',cls,a.shape,a.dtype.str,hashlib.sha256(a.tobytes()).hexdigest())
    memo[key]=hashlib.sha256(repr(v).encode()).hexdigest();return memo[key]

def under(root,rel):
    rel=str(rel).replace('\\','/')
    need(not re.match(r'^[A-Za-z]:',rel) and not rel.startswith('/'),'Expected project-relative artifact path')
    out=(root/rel).resolve();need(out!=root and root in out.parents,'Artifact escaped project root');return out

def selected_logs(path,requested):
    """Read only specified timeseries payloads, never analog payloads.

    Uses the previously observed v7.3 MCOS organization. Inventory discovery
    examines object names, dtype and shapes only, not unspecified Data arrays.
    On an unfamiliar serialization it aborts before reading any logger data.
    """
    with h5py.File(path,'r') as h:
        need('#subsystem#/MCOS' in h,'Unsupported SimulationOutput serialization')
        seq=[h[r] for r in h['#subsystem#/MCOS'][()].ravel()]
        groups=[x for x in seq if isinstance(x,h5py.Group) and {'record_log','event_log'}<=set(x)]
        need(len(groups)==1,'Ambiguous SimulationOutput group')
        s=groups[0]
        ordered=sorted((int(s[n][()].ravel()[4]),n) for n in s if n not in ('tout','yout'))
        names=[n for _,n in ordered]
        need(len(names)==len(set(names)) and requested<=set(names),'Missing/duplicate public logger')
        candidates=[]
        for i,d in enumerate(seq):
            if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
            ns,t=seq[i-11],seq[i-9]
            if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1)
                   and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')
                   and len(t.shape)==2 and t.shape[0]==1):continue
            count=t.shape[1]
            if count>0 and (count==1 or d.shape[-1]==count):candidates.append((ns,t,d,count))
        need(len(candidates)==len(names),
             f'Unsupported logger serialization: {len(names)} names/{len(candidates)} structural candidates; no payload read')
        logs={}
        for name,(ns,t,d,count) in zip(names,candidates):
            if name not in requested:continue
            need(ns[()].item()==count and d.attrs.get('MATLAB_class',b'')==b'double' and
                 d.dtype==np.dtype('float64'),f'Unsupported selected logger metadata: {name}')
            tm=t[()].T[:,0];data=d[()].reshape((-1,count)).T
            need(np.all(np.isfinite(tm)) and np.all(np.diff(tm)>=0),f'{name}: nonmonotonic Time')
            logs[name]={'time':tm,'data':data}
        return logs

def at(log,times,name):
    times=np.asarray(times,dtype=np.float64).ravel();t=log['time'];ix=np.searchsorted(t,times)
    need(np.all(ix<len(t)) and np.all(t[ix]==times),name+': missing exact actual timestamp')
    need(all(np.count_nonzero(t==v)==1 for v in times),name+': ambiguous actual timestamp')
    return log['data'][ix]

def public_plan(rows,seed):
    plan=np.zeros((rows,8),dtype=np.uint8);plan[0]=np.arange(1,9)
    for row in range(1,rows):
        prev=set(int(x) for x in plan[row-1]);a=[x for x in range(1,19) if x not in prev]
        for k in range(len(a),1,-1):
            seed=(16807*((seed%2147483646)+1))%2147483647;q=seed%k
            a[k-1],a[q]=a[q],a[k-1]
        plan[row]=a[:8]
    return plan

def public_dither(id_,cfg):
    if not cfg['dither_enabled']:return 0.
    m=2147483647;word=(cfg['dither_seed']%(m-1)+1)*pow(16807,id_+1,m)%m
    return (math.floor(4*word/m)-1.5)*cfg['dither_input_amplitude_v']

def public_basis(raw,plan,cfg,h):
    n=len(raw);p=np.zeros((n,684),dtype=np.float64);b=np.zeros((n,684),dtype=np.float64)
    basis=np.zeros((n,14),dtype=np.float64)
    for row,r in enumerate(raw):
        d1,d2,dt,id_,epoch,valid=map(int,r);need(valid==1,'Invalid row cannot enter frozen evaluation')
        coarse,fine=divmod(d1,32);bank,count=divmod(coarse,32);levels=np.zeros(31)
        if bank==0:levels[:31-count]=-1
        else:levels[:count]=1
        finebits=np.array([2*((fine>>i)&1)-1 for i in range(4,-1,-1)])
        vd=public_dither(id_,cfg)*(1024/15)
        for physical_id in plan[id_]:
            j=int(physical_id)-1
            shift=(17*id_+7*epoch+11*j+cfg['dem_seed'])%31 if cfg['dem_enabled'] else 0
            physical=np.zeros(31);physical[(np.arange(31)+shift)%31]=levels
            cols=j*38;p[row,cols:cols+33]=1
            b[row,cols:cols+38]=cfg['vref_v']*np.r_[2*bank-1,physical,finebits,-1]
            b[row,cols+33:cols+37]+=vd
        pol=[1,-1,-1,1][id_%4] if cfg['az_mode'] in ('chop','hold_chop') else 1
        d2bits=[(d2>>i)&1 for i in range(11,-1,-1)]
        signs=np.array([2*((dt>>i)&1)-1 for i in range(7,-1,-1)])
        basis[row]=pol*np.r_[1,d2bits,np.sum(np.arange(8,0,-1)*signs)/8]
    u=basis@cfg['backend_weights_ra_v'];bh=b@h;den=p@h
    need(np.all(np.isfinite(den)&(den>0)) and np.all(np.isfinite(u)) and np.all(np.isfinite(bh)),
         'Invalid public frozen denominator/numerator')
    voltage=(u+bh)/den
    unsat=voltage*(2**20/(2*cfg['vref_v']))+2**19
    rounded=np.where(unsat>=0,np.floor(unsat+.5),np.ceil(unsat-.5))
    code=np.clip(rounded,0,2**20-1).astype(np.float64)
    return u,bh,den,voltage,code

def fft(codes,fs,fin,fsr):
    n=len(codes);need(n==1024 and fin*n/fs==29,'Fixed registered coherent bin 29 mismatch')
    v=((codes+.5)/2**20-.5)*fsr
    spectrum=np.fft.fft(v-v.mean())/n;power=np.abs(spectrum[:n//2+1])**2;power[1:-1]*=2
    other=power.copy();other[[0,29]]=0
    h=np.mod(np.arange(2,11)*29,n);h=np.setdiff1d(np.unique(np.minimum(h,n-h)),[0,29])
    sig=power[29];nd=other.sum();hd=power[h].sum();noise=nd-hd
    need(sig>0 and nd>0 and noise>0 and hd>0 and other.max()>0,'Degenerate actual-code spectrum')
    out={'snr_db':float(10*np.log10(sig/noise)),'sndr_db':float(10*np.log10(sig/nd)),
         'sfdr_db':float(10*np.log10(sig/other.max())),'thd_db':float(10*np.log10(hd/sig))}
    out['enob']=(out['sndr_db']-1.76)/6.02
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',type=Path,required=True)
    ap.add_argument('--run',type=Path,required=True)
    for name in ['protocol-sha256','coefficient-file-sha256','coefficient-sha256','public-cfg-sha256']:
        ap.add_argument('--'+name,required=True,help='hash fixed by pre-holdout registration/freeze')
    a=ap.parse_args();root=a.root.resolve();job=a.job.resolve();run=a.run.resolve()
    need(root in job.parents and root in run.parents,'Job/run must be inside selected project')
    receipt_path=job/'receipt.json';before=sha(receipt_path);R=json.loads(receipt_path.read_text())
    # Crucial ordering: no holdout run, training artifact, protocol, P or logs
    # are opened before this completed terminal-gate check.
    terminal={'rx_registered_holdout_passed_not_accepted','rx_registered_holdout_failed_not_accepted'}
    if R.get('status')=='failed':
        REPORT.update(status='terminal_job_failed_no_holdout_data_opened',receipt_sha256=before,
                      receipt_status=R.get('status'),receipt_stage=R.get('stage'))
        print(json.dumps(REPORT,ensure_ascii=False,indent=2));return 2
    if not(R.get('action')=='evaluate' and R.get('stage')=='evaluate_complete' and R.get('status') in terminal):
        REPORT.update(status='not_terminal_no_holdout_data_opened',receipt_sha256=before,
                      receipt_status=R.get('status'),receipt_stage=R.get('stage'))
        print(json.dumps(REPORT,ensure_ascii=False,indent=2));return 2
    need(R.get('factory_restored') is True and R.get('accepted') is False and
         R.get('activation')=='none' and R.get('holdout_data_opened_after_freeze') is True,
         'Terminal receipt lacks restore/freeze/acceptance boundary')
    given=[a.protocol_sha256,a.coefficient_file_sha256,a.coefficient_sha256,a.public_cfg_sha256]
    need(all(re.fullmatch('[0-9a-f]{64}',x) for x in given),'Expected pins must be lowercase SHA-256')
    need(R.get('protocol_sha256')==a.protocol_sha256 and R.get('coefficient_sha256')==a.coefficient_sha256 and
         R.get('coefficient_file_sha256')==a.coefficient_file_sha256,'Terminal receipt disagrees with pre-holdout pins')
    basename=re.split(r'[/\\]',str(R['actual_holdout_run']))[-1]
    need(run.name==basename and run.parent==(root/'runs').resolve(),'Supplied run is not the receipt actual run')
    train=under(root,R['training_job']);freeze=under(root,R['freeze_job'])
    tr=json.loads((train/'receipt.json').read_text());fr=json.loads((freeze/'receipt.json').read_text())
    need(tr['status']=='rx_train_candidate_ready_factory_restored' and
         fr['status']=='rx_candidate_frozen_not_accepted' and
         under(root,fr['training_job'])==train and
         tr['protocol_sha256']==fr['protocol_sha256']==a.protocol_sha256 and
         fr['coefficient_file_sha256']==a.coefficient_file_sha256 and
         fr['coefficient_sha256']==a.coefficient_sha256 and fr['public_cfg_sha256']==a.public_cfg_sha256 and
         fr['training_job_receipt_sha256']==sha(train/'receipt.json'),
         'Completed training/freeze receipt pins do not bind this candidate')
    protocol_path=train/'rx_protocol.json';need(sha(protocol_path)==a.protocol_sha256,'Registered protocol SHA changed')
    protocol=json.loads(protocol_path.read_text());th=protocol['thresholds'];trial=protocol['holdout'];src=trial['source']
    need(protocol['schema']=='sar20-rx-independent-holdout/v1' and trial['records']==1024 and
         trial['first_id']==4 and trial['epoch']==3 and protocol['sample_period_s']==2e-7 and
         src['offset_v']==0 and src['amplitude_v']==3.650563842595822 and
         src['frequency_hz']==29*5e6/1024 and src['phase_rad']==2.137 and
         th['holdout_rms_limit_v']==7.8125e-6 and th['holdout_max_abs_limit_v']==31.25e-6 and
         protocol['numerical_oracle_voltage_tolerance_v']==1e-12,'Registered protocol or original gates differ')
    need(R.get('public_oracle_integer_bit_exact') is True and
         R.get('public_oracle_max_voltage_delta_v',math.inf)<=protocol['numerical_oracle_voltage_tolerance_v'],
         'Terminal native public oracle did not meet the predeclared gate')
    marker=train/'holdout_consumed.json';reservation=json.loads(marker.read_text())
    need(sha(marker)==R['holdout_reservation_sha256'] and reservation['status']=='reserved_before_simulation' and
         reservation['protocol_sha256']==a.protocol_sha256 and
         reservation['coefficient_sha256']==a.coefficient_sha256 and under(root,reservation['evaluation_job'])==job,
         'Pre-simulation single-holdout reservation identity mismatch')
    lock=under(root,fr['freeze_workflow'])/'frozen_coefficients.mat'
    need(sha(lock)==a.coefficient_file_sha256,'Frozen public coefficient artifact changed')
    summary=json.loads((run/'summary.json').read_text())
    need(summary.get('status')=='complete' and summary.get('simulation_completed') and summary.get('records')==1024 and
         summary.get('capture_boundary')=='serial_rx' and
         summary.get('decode_mode')=='immutable_candidate_for_holdout' and not summary.get('calibration_accepted'),
         'Actual run summary is not a complete frozen RX holdout')
    selected=run/'selected.mat';need(sha(selected)==summary['selected_sha256'],'Selected public record file SHA mismatch')
    cache_fields={'schema','public_cfg','h','h_by_slice','plan','coefficient_sha256','public_cfg_sha256','lifecycle','acceptance'}
    cfg_fields={'schema','vref_v','fs_hz','plan_rows','pool_seed','pool_schedule','dem_enabled','dem_seed',
                'dem_schedule','dither_enabled','dither_seed','dither_input_amplitude_v','dither_schedule',
                'az_mode','backend_weights_ra_v','nominal_ra_gain','tracking_mode'}
    with h5py.File(lock,'r') as c,h5py.File(run/'parameters.mat','r') as p:
        need(set(c['C'])==cache_fields and set(p['P/frozen/cache'])==cache_fields and
             set(c['C/public_cfg'])==cfg_fields,'Frozen public cache schema is not the exact whitelist')
        need(fingerprint(c,c['C'],{})==fingerprint(p,p['P/frozen/cache'],{}) and
             fingerprint(c,c['C/public_cfg'],{})==fingerprint(p,p['P/cal_cfg/public_cfg'],{}),
             'Saved holdout public cache/config differs from immutable locked artifact')
        need(val(c,'C/lifecycle')=='frozen_for_holdout' and val(c,'C/acceptance')=='NOT_ACCEPTED' and
             val(c,'C/coefficient_sha256')==a.coefficient_sha256 and
             val(c,'C/public_cfg_sha256')==a.public_cfg_sha256,'Cache declared hashes/lifecycle differ')
        h=np.asarray(val(c,'C/h'),dtype=np.float64).ravel()
        need(h.shape==(684,) and np.all(np.isfinite(h)&(h>0)) and
             hashlib.sha256(h.astype('<f8').tobytes()).hexdigest()==a.coefficient_sha256,
             'Frozen h bytes/hash/shape differ')
        hs=np.asarray(val(c,'C/h_by_slice'));need(same(hs,h.reshape(18,38)),'h_by_slice differs from canonical h')
        cfg={k:val(c,'C/public_cfg/'+k) for k in cfg_fields}
        for key in ['pool_seed','dem_seed','dither_seed','plan_rows']:cfg[key]=int(cfg[key])
        for key in ['dem_enabled','dither_enabled']:cfg[key]=bool(cfg[key])
        cfg['backend_weights_ra_v']=np.asarray(cfg['backend_weights_ra_v']).ravel()
        need(cfg['schema']=='sar20-behavior-public-cal/v1' and cfg['pool_schedule']=='causal_18_8_8_2_pm_v1' and
             cfg['dem_schedule']=='pool_cyclic_shift31_v1' and cfg['dither_schedule']=='input_counter_tail1024_over15_v1' and
             cfg['tracking_mode']=='finite_sinc2' and cfg['fs_hz']==5e6 and cfg['nominal_ra_gain']==32 and
             cfg['dem_enabled']==bool(protocol['DEM']) and cfg['dither_enabled']==bool(protocol['dither']) and
             cfg['az_mode']=='off' and cfg['vref_v']==4.096 and len(cfg['backend_weights_ra_v'])==14,
             'Unexpected declared public feature configuration')
        plan=np.asarray(val(c,'C/plan'));public_plan_actual=np.asarray(val(p,'P/front/plan'))
        need(plan.shape==(cfg['plan_rows'],8) and np.array_equal(plan,public_plan(cfg['plan_rows'],cfg['pool_seed'])) and
             np.array_equal(public_plan_actual,plan),'Frozen/public generated plan mismatch')
        need(int(val(p,'P/N'))==1024 and int(val(p,'P/first_id'))==4 and int(val(p,'P/epoch'))==3 and
             bool(val(p,'P/transport/enabled')) and not bool(val(p,'P/training/enabled')) and
             not bool(val(p,'P/cal_cfg/enabled')) and bool(val(p,'P/frozen/enabled')) and
             bool(val(p,'P/training/reference/enabled')) and val(p,'P/training/reference/source')=='declared_external_reference' and
             a.protocol_sha256 in val(p,'P/training/reference/provenance'),
             'Saved holdout public mode/reference does not match protocol')
        for key in ['offset_v','amplitude_v','frequency_hz','phase_rad']:
            need(val(p,'P/training/reference/'+key)==src[key], 'Public reference declaration changed: '+key)
            need(val(p,'P/input/'+key)==src[key], 'Configured declared input changed: '+key)
        need(int(val(p,'P/training/reference/first_id'))==4 and int(val(p,'P/training/reference/epoch'))==3 and
             int(val(p,'P/training/reference/records'))==1024 and
             val(p,'P/training/reference/sample_period_s')==protocol['sample_period_s'],
             'Public reference ID/epoch/window/period changed')
    requested={'event_log','record_log','record_ready_log','paired_ref_log','train_ref_log',
               'frozen_log','code_log','nominal_code_log'}
    logs=selected_logs(run/'simout.mat',requested)
    for name,width in [('event_log',2),('record_log',6),('record_ready_log',1),('paired_ref_log',4),
                       ('train_ref_log',4),('frozen_log',12),('code_log',1),('nominal_code_log',1)]:
        need(logs[name]['data'].shape[1]==width,'Unexpected public logger width: '+name)
    rr=logs['record_ready_log'];flags=rr['data'][:,0];need(np.all(np.isin(flags,[0,1])),'RX ready not binary')
    ready=rr['time'][flags==1];need(len(np.unique(ready))==len(ready),'Duplicate actual RX ready time')
    observed=at(logs['record_log'],ready,'record_log');obs_code=at(logs['code_log'],ready,'code_log')[:,0]
    take=(observed[:,3]>=4)&(observed[:,3]<1028);raw=observed[take];times=ready[take];codes=obs_code[take]
    REPORT['outside_or_unclassified_ready']=[
        {'time_s':float(t),'raw6':[float(x) if math.isfinite(x) else str(x) for x in row]}
        for t,row,inside in zip(ready,observed,take) if not inside]
    REPORT['record_counts']={'all_ready':len(observed),'selected':len(raw),
         'valid_1':int(np.count_nonzero(raw[:,5]==1)),'valid_0':int(np.count_nonzero(raw[:,5]==0)),
         'other':int(np.count_nonzero(~np.isin(raw[:,5],[0,1])))}
    if len(raw)!=1024 or not np.all(np.isfinite(raw)) or not np.array_equal(raw[:,3],np.arange(4,1028)) or \
       not np.all(raw[:,4]==3) or not np.all(raw[:,5]==1):
        REPORT['selected_raw_including_invalid']=[[float(x) if math.isfinite(x) else str(x) for x in row] for row in raw]
        raise ValueError('Actual RX IDs/order/epoch/valid differ; invalid rows preserved; no FFT or filtering')
    need(np.all(raw==np.floor(raw)) and np.all((0<=raw[:,:3]) & (raw[:,:3]<=np.array([2047,4095,255]))) and
         np.all(np.isfinite(codes)) and np.all(codes==np.floor(codes)) and np.all((0<=codes)&(codes<2**20)),
         'Public RAW/code range invalid')
    with h5py.File(selected,'r') as s:
        need(same(s['selected/raw'][()].T,raw) and same(s['selected/code20'][()].ravel(),codes) and
             same(s['selected/time_s'][()].ravel(),times),'selected.mat != actual RX RAW/code/ready time')
        need(val(s,'metadata/fs_hz')==cfg['fs_hz'] and val(s,'metadata/fsr_diff_v')==2*cfg['vref_v'] and
             all(val(s,'metadata/stimulus/'+k)==src[k] for k in ['offset_v','amplitude_v','frequency_hz','phase_rad']),
             'Saved FFT input metadata differs from registered public source/configuration')
    need(np.array_equal(np.asarray(summary['raw_words']),raw) and np.array_equal(np.asarray(summary['code20']),codes) and
         np.array_equal(np.asarray(summary['sample_ids']),raw[:,3]),'Summary != actual RX selected data')
    refs=at(logs['paired_ref_log'],times,'paired_ref_log')
    diag=at(logs['frozen_log'],times,'frozen_log')
    nominal=at(logs['nominal_code_log'],times,'nominal_code_log')[:,0]
    need(np.array_equal(refs[:,1:3],raw[:,3:5]) and np.all(refs[:,3]==1) and
         np.all(np.isfinite(refs[:,0])) and np.all(diag[:,9:11]==1) and np.all(np.isfinite(diag[:,[0,6,7,8]])),
         'Actual paired reference or frozen diagnostics invalid')
    need(np.all(np.isfinite(nominal)) and np.all(nominal==np.floor(nominal)) and
         np.all((0<=nominal)&(nominal<2**20)),'Actual nominal code invalid')
    event=logs['event_log'];ev=event['data'];et=event['time'];cnv=np.empty(1024)
    rxevent=at(event,times,'RX event')
    need(np.array_equal(rxevent[:,0],raw[:,3]+2) and np.all(rxevent[:,1]==49),
         'Actual RX ready does not correspond to N-2 parent group49')
    for k,id_ in enumerate(raw[:,3]):
        ix=np.flatnonzero((ev[:,0]==id_)&(ev[:,1]==1));need(len(ix)==1,'Missing/duplicate actual CNV')
        cnv[k]=et[ix[0]]
    need(same(cnv,raw[:,3]*protocol['sample_period_s']),'Actual CNV differs from registered sample time')
    cnvref=at(logs['train_ref_log'],cnv,'declared external CNV reference')
    need(same(cnvref,refs),'CNV external reference and paired RX reference differ')
    # A separately evaluated sine is only a diagnostic; no new tolerance is used.
    declared=np.array([src['offset_v']+src['amplitude_v']*math.sin(
                      2*math.pi*src['frequency_hz']*t+src['phase_rad']) for t in cnv])
    u,bh,den,voltage,pred_code=public_basis(raw,plan,cfg,h)
    oracle_delta=float(np.max(np.abs(voltage-diag[:,8])))
    integer_mismatch=int(np.count_nonzero(pred_code!=codes))
    need(oracle_delta<=protocol['numerical_oracle_voltage_tolerance_v'] and integer_mismatch==0,
         'Public frozen voltage exceeds original 1e-12 V gate or integer code differs')
    actual_voltage=diag[:,8];lsb=2*cfg['vref_v']/2**20;evv=actual_voltage-refs[:,0]
    ecode=(codes-2**19)*lsb-refs[:,0]
    metrics={'voltage_rms_v':float(np.sqrt(np.mean(evv**2))),'voltage_max_abs_v':float(np.max(np.abs(evv))),
             'integer_center_rms_v':float(np.sqrt(np.mean(ecode**2))),
             'integer_center_max_abs_v':float(np.max(np.abs(ecode)))}
    passed=metrics['voltage_rms_v']<=th['holdout_rms_limit_v'] and \
        metrics['integer_center_rms_v']<=th['holdout_rms_limit_v'] and \
        metrics['voltage_max_abs_v']<=th['holdout_max_abs_limit_v'] and \
        metrics['integer_center_max_abs_v']<=th['holdout_max_abs_limit_v']
    need(bool(R['registered_holdout_passed'])==bool(passed),'Independent fixed gate disagrees with terminal receipt')
    fs=cfg['fs_hz'];fin=src['frequency_hz'];fsr=2*cfg['vref_v']
    frozen_fft=fft(codes,fs,fin,fsr);nominal_fft=fft(nominal,fs,fin,fsr)
    need(sha(receipt_path)==before,'Terminal receipt changed during readback')
    REPORT.update(status='terminal_public_holdout_independently_audited',
        receipt_status=R['status'],receipt_sha256=before,
        pre_holdout_pins={'protocol_sha256':a.protocol_sha256,'coefficient_file_sha256':a.coefficient_file_sha256,
                          'coefficient_sha256':a.coefficient_sha256,'public_cfg_sha256':a.public_cfg_sha256},
        selected_mat_sha256=sha(selected),
        whole_parameters_and_simout_sha='not read or hashed: files contain excluded analog state/data',
        protocol_and_immutable_cache={'protocol_holdout':trial,'holdout_rms_limit_v':th['holdout_rms_limit_v'],
             'holdout_max_abs_limit_v':th['holdout_max_abs_limit_v'],
             'predeclared_voltage_oracle_tolerance_v':protocol['numerical_oracle_voltage_tolerance_v'],
             'h_684_bytes_hash_verified':True,'public_cfg_semantic_identity_verified':True,
             'public_cfg_hash_boundary':'Compared declared MATLAB cfg hash and full public cfg identity; '
                  'MATLAB orderfields/jsonencode hash not independently reserialized in Python.',
             'public_plan_all_rows_reconstructed_and_matched':True,'holdout_reservation_sha256':sha(marker)},
        actual_RX_raw_and_selected_bits_equal=True,actual_public_reference_exact_CNVRX_join=True,
        reference_formula_python_max_abs_delta_v=float(np.max(np.abs(declared-refs[:,0]))),
        reference_scope='Declared ideal external reference with zero stated uncertainty; not measured hardware reference.',
        actual_frozen_diag_and_public_reconstruction={'voltage_max_abs_delta_v':oracle_delta,
             'original_oracle_voltage_tolerance_v':protocol['numerical_oracle_voltage_tolerance_v'],
             'integer_code_mismatches':integer_mismatch,'max_abs_u_delta_v':float(np.max(np.abs(u-diag[:,0]))),
             'max_abs_Bh_delta_v':float(np.max(np.abs(bh-diag[:,6]))),
             'max_abs_den_delta':float(np.max(np.abs(den-diag[:,7]))),
             'note':'Only public RAW, immutable h and public plan/config feed the independent basis; no analog held/C truth.'},
        fixed_registered_gates={'passed':bool(passed),'actual_metrics':metrics,
             'numpy_minus_terminal_receipt':{k:metrics[k]-float(R[k]) for k in metrics}},
        actual_code_fft={'N':1024,'fs_hz':fs,'fin_hz':fin,'bin':29,'frozen':frozen_fft,'nominal':nominal_fft,
             'frozen_numpy_minus_summary':{k:frozen_fft[k]-float(summary[k]) for k in frozen_fft if k in summary},
             'scope':'Actual valid codes; rectangular coherent FFT, H2-H10, no ENOB amplitude correction. '
                     'FFT uses code+0.5 center; registered accuracy gates use code-2^19 with no +0.5.'},
        acceptance='NOT_ACCEPTED; registered holdout gate only, no automatic bank activation',
        limits='Same chip/profile, registered ideal external reference, 1024 actual public RX records; '
               'no PDK, silicon, extra nonideal or generalized performance claim.',
        verifier_sha256=sha(Path(__file__).resolve()))
    print(json.dumps(REPORT,ensure_ascii=False,indent=2,allow_nan=False));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,OSError,IndexError,TypeError) as exc:
        REPORT.update(status='verification_failed',error=str(exc))
        print(json.dumps(REPORT,ensure_ascii=False,indent=2,allow_nan=False));sys.exit(1)
