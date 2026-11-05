#!/usr/bin/env python3
"""Read-only event-by-event comparison of actual zero and negative DC endpoints."""
import hashlib,json,math,sys,zipfile
from pathlib import Path
import h5py
import numpy as np
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import at,decode,fingerprint,need,read_calendar,read_logs,same,sha,val
job=root/'runs/az_probe_20261028T112407Z';run=job/'zero_result'
prior=root/'runs/az_probe_20261028T110315Z/static_result'
R=json.loads((run/'receipt.json').read_text());outer=json.loads((job/'receipt.json').read_text())
need(R['stage']=='complete' and R['status']=='actual_multicode_jump_window_no_DNL' and
     sha(run/'receipt.json')==outer['result_receipt_sha256'],'Result receipt not complete or SHA differs')
need(sha(run/'SarAdc_factory.slx')==R['model_sha256']==outer['current_model_sha256_before'] and
     sha(prior/'SarAdc_factory.slx')==R['model_sha256'],'Recorded factory model differs')
need(sha(run/'source_manifest.json')==R['source_manifest_sha256'] and
     sha(run/'source.zip')==R['source_zip_sha256'],'New source archive SHA differs')
new_manifest=json.loads((run/'source_manifest.json').read_text())['files']
old_manifest=json.loads((prior/'source_manifest.json').read_text())['files']
canon=lambda rows:{r['path'].replace('\\','/'):r['sha256'] for r in rows}
need(canon(new_manifest)==canon(old_manifest),'Zero and negative as-run source manifest differs')
with zipfile.ZipFile(run/'source.zip') as z:
    pins=canon(new_manifest);need(set(z.namelist())==set(pins),'Source archive inventory differs')
    for name,h in pins.items():need(hashlib.sha256(z.read(name)).hexdigest()==h,'Source SHA mismatch '+name)
P0=run/'Pzero_reconstructed.mat';folder=run/'point_001';P1=folder/'P.mat';pt=R['points'][0]
need(sha(P0)==R['reused_anchors']['zero']['Pzero_reconstructed_sha256'] and
     sha(P1)==pt['P_mat_sha256'] and sha(folder/'signals.mat')==pt['signals_sha256'] and
     sha(folder/'observed.mat')==pt['observed_sha256'],'Saved P/signals/observed SHA differs')
need(sha(prior/'preflight_capped_simout.mat')==R['reused_anchors']['zero']['capped_simout_sha256'],
     'Prior actual 0V preflight SHA differs')

def pdiff_named(a,b):
    with h5py.File(a,'r') as f,h5py.File(b,'r') as g:
        fm={};gm={};out=[]
        def walk(x,y,path):
            if fingerprint(f,x,fm)==fingerprint(g,y,gm):return
            if isinstance(x,h5py.Group) and isinstance(y,h5py.Group):
                for k in sorted(set(x)|set(y)):
                    if k not in x or k not in y:out.append(path+'/'+k)
                    else:walk(x[k],y[k],path+'/'+k)
            else:out.append(path)
        walk(f['Pzero'],g['P'],'P');return out

diff=pdiff_named(P0,P1);need(set(diff)=={'P/input/offset_v','P/front/input/offset_v','P/xFE0'},
                             'Unexpected reconstructed zero vs negative saved P differences')
with h5py.File(P0,'r') as f,h5py.File(P1,'r') as g:
    for file,prefix,offset in [(f,'Pzero',0.),(g,'P',-7.8125e-6/256)]:
        need(val(file,prefix+'/input/offset_v')==offset and val(file,prefix+'/input/amplitude_v')==0 and
             val(file,prefix+'/front/input/offset_v')==offset and val(file,prefix+'/N')==1 and
             val(file,prefix+'/first_id')==4 and val(file,prefix+'/epoch')==1 and
             val(file,prefix+'/n_cycles')==5 and val(file,prefix+'/Ts_s')==2e-7 and
             not val(file,prefix+'/transport/enabled') and not val(file,prefix+'/training/enabled') and
             not val(file,prefix+'/frozen/enabled'),'P sample window/mode differs')
    times,groups,_=read_calendar(g)
    dig={k:val(g,'P/digital/'+k) for k in ['vref_v','fsr_diff_v','ra_gain','d2_offset_ra_v',
         'd2_weights_ra_v','tracking_step_ra_v']}
    need(not val(g,'P/digital/dither_enabled') and val(g,'P/digital/az_mode')=='off',
         'Nominal public decoder scope differs')

def signal_struct(path):
    with h5py.File(path,'r') as h:
        seq=[h[x] for x in h['#subsystem#/MCOS'][()].ravel()];s=h['signals']
        names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];out=[]
        for i,d in enumerate(seq):
            if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
            ns,t=seq[i-11],seq[i-9]
            if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and
                   isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
            count=int(ns[()].item())
            if count>0 and t.shape==(1,count) and (count==1 or d.shape[-1]==count):
                cls=d.attrs.get('MATLAB_class',b'');cls=cls.decode() if isinstance(cls,bytes) else str(cls)
                out.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,count)).T,'class':cls})
        need(len(names)==len(out)==9,'Unsupported nine-series serialization');return dict(zip(names,out))

keep=['back_log','code_log','control_log','event_log','front_log','raw_log','ready_log','record_log','record_ready_log']
A=read_logs(prior/'preflight_capped_simout.mat');full=read_logs(prior/'preflight_full_simout.mat')
B=signal_struct(folder/'signals.mat');need(set(B)==set(keep),'Negative point logger inventory differs')
need(all(k in A and k in full and A[k]['class']==full[k]['class'] and
     same(A[k]['time'],full[k]['time']) and same(A[k]['data'],full[k]['data']) for k in keep),
     'Zero full vs capped nine-log gate differs')
need(all(same(A[k]['time'],B[k]['time']) for k in keep),'Point event axes differ')
event=A['event_log']['data'];t=A['event_log']['time'];need(same(event,B['event_log']['data']) and
     event.shape==(240,2) and np.array_equal(event[:,0],np.repeat(np.arange(5),48)) and
     np.array_equal(event[:,1],np.tile(np.arange(1,49),5)) and
     same(t,np.array([i*2e-7+x for i in range(5) for x in times])),
     'Actual five warmup/target event calendars differ')

def actual_record(L,expected_code,expected_raw,offset):
    ready=L['ready_log']['data'][:,0];rready=L['record_ready_log']['data'][:,0]
    need(np.all(np.isin(ready,[0,1])) and same(ready,rready),'ADC/record ready differs')
    idx=np.flatnonzero(ready==1);need(len(idx)==5 and np.all(event[idx,1]==47) and
         np.array_equal(event[idx,0],np.arange(5)),'Expected five raw_latch events')
    raw=L['raw_log']['data'][idx];record=L['record_log']['data'][idx];code=L['code_log']['data'][idx,0]
    need(same(raw,record) and np.array_equal(raw[:,3],np.arange(5)) and
         np.all(raw[:,4]==1) and np.all(raw[:,5]==1) and np.all(code==expected_code) and
         np.array_equal(raw[-1],expected_raw) and decode(raw[-1],dig)==expected_code,
         'Actual RAW/ready/valid/code/public decode mismatch')
    held=float(L['front_log']['data'][idx[-1],0]);need(held==offset,'Actual held endpoint differs from declared DC')
    return {'raw6':raw[-1].tolist(),'code20':int(code[-1]),'all_ready_raw6':raw.tolist(),
            'all_ready_code20':code.tolist(),'actual_ready_s':float(t[idx[-1]]),'held_input_v':held}

zero=actual_record(A,524289,[1040,2374,42,4,1,1],0.)
negative=actual_record(B,524285,[1039,3417,42,4,1,1],-7.8125e-6/256)
need(zero['raw6']==R['reused_anchors']['zero']['raw6'] and zero['code20']==R['reused_anchors']['zero']['code20'] and
     negative['raw6']==pt['raw6'] and negative['code20']==pt['code20'],'Receipt actual RAW/code mismatch')
with h5py.File(folder/'observed.mat','r') as f:
    need(np.array_equal(np.asarray(val(f,'obs/raw6')).ravel(),negative['raw6']) and
         val(f,'obs/code20')==negative['code20'] and val(f,'obs/held_input_v')==negative['held_input_v'] and
         val(f,'obs/ready_time_s')==negative['actual_ready_s'],'Negative observed MAT differs')

ix=np.flatnonzero((event[:,0]==4)&(event[:,1]>=1)&(event[:,1]<=48));tt=t[ix]
fields={'front_log':['held_V','vres_V','qres_C','Cs_F','Ctop_F','vtop_equiv_V','dither_V'],
        'back_log':['VX_V','VY_V','Vtop_V','target_V','NG','tau_s','AZdiff_V','CTreset_V'],
        'control_log':['trial','ra_on','active','ready','D1','D2','DT','valid','ID','epoch','CNV','release','dac_changed'],
        'raw_log':['D1','D2','DT','ID','epoch','valid'],'code_log':['intermediate_or_final_code']}
first={}
for name,names in fields.items():
    x=A[name]['data'][ix];y=B[name]['data'][ix];first[name]={}
    for k,name_field in enumerate(names):
        rows=np.flatnonzero(x[:,k]!=y[:,k])
        if len(rows):
            i=int(rows[0]);first[name][name_field]={'group':i+1,'relative_ns':float((tt[i]-8e-7)*1e9),
                'zero':float(x[i,k]),'negative':float(y[i,k]),'negative_minus_zero':float(y[i,k]-x[i,k]),
                'changed_rows':len(rows)}

def contribution(raw):
    d1,d2,dt=map(int,raw[:3]);coarse,fine=divmod(d1,32);ref=float(dig['vref_v'])
    d1v=(32*coarse+2*fine-1039)*ref/1024-17*ref/1024
    db=np.array([(d2>>i)&1 for i in range(11,-1,-1)])
    ds=np.array([2*((dt>>i)&1)-1 for i in range(7,-1,-1)])
    d2v=(dig['d2_offset_ra_v']+np.sum(np.asarray(dig['d2_weights_ra_v']).ravel()*db))/dig['ra_gain']
    dtv=dig['tracking_step_ra_v']*np.sum(np.arange(8,0,-1)*ds)/8/dig['ra_gain']
    total=(d1v+d2v)+dtv
    return {'D1_v':float(d1v),'D2_v':float(d2v),'DT_v':float(dtv),'total_v':float(total),
            'code20':decode(np.asarray(raw,dtype=np.float64),dig)}
components={'zero':contribution(zero['raw6']),'negative':contribution(negative['raw6'])}
need(components['zero']['code20']==zero['code20'] and components['negative']['code20']==negative['code20'],
     'Independent public nominal contribution code differs')
window=R['transition_window'];need(window['low_v']==-7.8125e-6/256 and window['high_v']==0 and
     window['low_actual_code']==524285 and window['high_actual_code']==524289 and
     window['actual_code_span']==4 and not R['local_widths'],'Stored endpoint window differs')
report={'schema':'sar20-zero-112407-independent/v1','verifier_sha256':sha(Path(__file__).resolve()),
        'result_receipt_sha256':sha(run/'receipt.json'),'old_zero_simout_sha256':sha(prior/'preflight_capped_simout.mat'),
        'negative_signals_sha256':sha(folder/'signals.mat'),'model_sha256':R['model_sha256'],
        'source_files_verified':len(pins),'reconstructed_zero_vs_negative_P_differences':diff,
        'zero_P_provenance':'Pzero_reconstructed.mat is reconstructed later from pinned factory source; '
             'the 110315 zero preflight did not separately save its actual P.',
        'zero_preflight_full_vs_capped_nine_logs_bit_equal':True,'five_48_event_ids_and_times_equal':True,
        'zero':zero,'negative':negative,'first_changed_fields':first,'event_kinds':groups,
        'final_nominal_contributions_from_public_RAW':components,
        'contribution_scope':'Independently reconstructed from final public RAW and saved P.digital; '
                             'individual D1/D2/DT logger histories were capped and not saved at these points.',
        'decision_scope':'First fine compare outcome inferred from D1 bit write; separate Compare1 output not logged.',
        'window':{'low_v':window['low_v'],'high_v':window['high_v'],'span_V':window['bracket_width_v'],
                  'endpoint_codes':[524285,524289],
                  'scope':'Only two actual endpoints; intermediate codes/thresholds and missing codes unmeasured.'},
        'no_new_DNL_or_INL':True,'simulation_scope':'Original zero actual preflight and one new negative simulation; '
             'individual full simout at the new point is not retained, only nine saved timeseries and native status.'}
print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
