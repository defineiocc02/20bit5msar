#!/usr/bin/env python3
"""Read-only actual ID5 comparison; event ID/group and timestamps are authoritative."""
import json
import math
from pathlib import Path
import h5py
import numpy as np
from verify_as_run import archive_provenance, at, graph, need, pdiff, read_calendar, read_logs, same, sha, val

root=Path(__file__).resolve().parents[3]
dirs=[root/'runs/behavior_c5a4d0b8-7e34-4a92-b698-5bf72067ab09',
      root/'runs/behavior_8165ddcc-971e-49a6-938b-ad2fb6dd9603']
receipt_path=root/'runs/az_probe_20261028T093124Z/receipt.json'
receipt=json.loads(receipt_path.read_text())
assert receipt['status']=='actual_ID5_comparison_complete'
summaries=[json.loads((d/'summary.json').read_text()) for d in dirs]
for d,s,prefix in zip(dirs,summaries,['zero','finite']):
    archive_provenance(d,s,False)
    need(s['status']=='complete' and s['simulation_completed'] and s['records']==8, 'Incomplete as-run N8')
    need(sha(d/'simout.mat')==receipt[prefix+'_simout_sha256'] and
         sha(d/'SarAdc.slx')==receipt[prefix+'_model_sha256'], '093124 source identity mismatch')
source_files=[]
for d in dirs:
    source_files.append({x['path'].replace('\\','/'):x['sha256'] for x in
                         json.loads((d/'source_manifest.json').read_text())['files']})
need(source_files[0]==source_files[1], 'As-run source files differ')
b0,e0,c0=graph(dirs[0]/'SarAdc.slx'); b1,e1,c1=graph(dirs[1]/'SarAdc.slx')
need(e0==e1 and c0==c1 and b0.keys()==b1.keys(), 'As-run graph edges/solver/inventory differ')
block_changes=[]
for sid in sorted(b0):
    need(b0[sid][:2]==b1[sid][:2], 'As-run block name/type differs')
    for key in sorted(set(b0[sid][2])|set(b1[sid][2])):
        if b0[sid][2].get(key)!=b1[sid][2].get(key):block_changes.append([sid,key])
need(block_changes==[['105','AttributesFormatString']], 'Unexpected as-run block parameter changes')
diff=pdiff(dirs[0]/'parameters.mat',dirs[1]/'parameters.mat')
need(set(diff)=={'P/backend/dac_coupling/tau_dac_s','P/front/tau_dac_s','P/ni/dac_settling'},
     'Unexpected saved P difference: '+repr(diff))
for d,tau in zip(dirs,[0.,1e-9]):
    with h5py.File(d/'parameters.mat') as p:
        need(np.all(np.asarray(val(p,'P/front/tau_dac_s')).ravel()==tau) and
             bool(val(p,'P/backend/dac_coupling/enabled')) and bool(val(p,'P/debug/dac_enabled')),
             'Unexpected tau/coupling/probe')
        if tau==0:
            Ts=float(val(p,'P/Ts_s')); reset_tau=float(val(p,'P/backend/ra/tau_reset_s'))
            _,calendar,_=read_calendar(p)
L=[read_logs(d/'simout.mat') for d in dirs]
E=L[0]['event_log'];need(same(E['time'],L[1]['event_log']['time']) and
                          same(E['data'],L[1]['event_log']['data']), 'Different event streams')
e,t=E['data'],E['time']; mask=(e[:,0]==5)&(e[:,1]>=1)&(e[:,1]<=48)
indices=np.flatnonzero(mask);tt=t[indices]
need(len(indices)==48 and np.array_equal(e[indices,1],np.arange(1,49)) and
     same(at(L[0]['adc_executed_log'],tt,'ADC enable')[:,0],np.ones(48,dtype=np.uint8)),
     'Not the exact 48 actual ID5 ADC events')
names=['front_log','dac_ra_pre_log','back_log','control_log','event_log'];changes={};series={}
for name in names:
    x=at(L[0][name],tt,name);y=at(L[1][name],tt,name);series[name]=(x,y)
    changed=np.array([not np.array_equal(a,b,equal_nan=True) for a,b in zip(x,y)])
    ix=np.flatnonzero(changed)
    fields=[]
    for k in range(x.shape[1]):
        ci=np.flatnonzero(~((x[:,k]==y[:,k]) | (np.isnan(x[:,k])&np.isnan(y[:,k]))))
        fields.append({'field_1based':k+1,'changed_rows_numeric':len(ci),
                       'first_group':int(ci[0]+1) if len(ci) else None,
                       'first_relative_ns':float((tt[ci[0]]-5*Ts)*1e9) if len(ci) else None,
                       'first_delta_1ns_minus_zero':float(y[ci[0],k]-x[ci[0],k]) if len(ci) else None})
    changes[name]={'rows':len(x),'changed_rows_numeric':int(changed.sum()),
                   'first_group':int(ix[0]+1) if len(ix) else None,
                   'first_relative_ns':float((tt[ix[0]]-5*Ts)*1e9) if len(ix) else None,'fields':fields}
    old=receipt['changes'][name]
    need(old['observed_rows']==len(x) and old['changed_rows']==int(changed.sum()),name+' receipt mismatch')

def item(group):
    i=group-1; af,bf=series['front_log']; ap,bp=series['dac_ra_pre_log']; ac,bc=series['control_log']
    return {'group':group,'event_kinds':calendar[i], 'time_s':float(tt[i]),
            'relative_ns':float((tt[i]-5*Ts)*1e9),'front_zero':af[i].tolist(),
            'front_1ns':bf[i].tolist(),'pre_zero':ap[i].tolist(),'pre_1ns':bp[i].tolist(),
            'pre_delta_1ns_minus_zero':(bp[i]-ap[i]).tolist(),
            'control_zero':ac[i].tolist(),'control_1ns':bc[i].tolist()}

records=[]
for log in L:
    ready=log['record_ready_log'];rt=ready['time'][ready['data'][:,0]==1]
    rr=at(log['record_log'],rt,'record');cc=at(log['code_log'],rt,'code')[:,0]
    ix=np.flatnonzero((rr[:,3]==5)&(rr[:,4]==1));need(len(ix)==1,'Missing/duplicate ID5 received record')
    j=ix[0];need(rr[j,5]==1,'ID5 invalid')
    adc=at(log['raw_log'],[tt[46]],'ADC raw_latch')[0]
    need(at(log['ready_log'],[tt[46]],'ADC ready')[0,0]==1 and same(adc,rr[j]),
         'ADC vs RX RAW mismatch')
    records.append({'raw6':rr[j].tolist(),'code20':int(cc[j]),'actual_ADC_ready_s':float(tt[46]),
                    'actual_RX_ready_s':float(rt[j])})
need(records[0]==records[1], 'ID5 records differ')
need(records[0]['raw6']==receipt['zero_raw']==receipt['finite_raw'] and
     records[0]['code20']==receipt['zero_code20']==receipt['finite_code20'],'093124 record mismatch')

previous=np.flatnonzero((e[:,0]==4)&(e[:,1]==48));need(len(previous)==1,'ID4 release missing')
prev_t=float(t[previous[0]]); old=[];now=[];pred=[]
for log in L:
    old.append(float(at(log['dac_ra_pre_log'],[prev_t],'ID4 RaPre')[0,0]))
    now.append(float(at(log['dac_ra_pre_log'],[tt[0]],'ID5 RaPre')[0,0]))
    pred.append(old[-1]*math.exp(-(float(tt[0])-prev_t)/reset_tau))
need(same(np.asarray(pred),np.asarray(now)), 'Release→CNV reset-decay model does not match')
vtop_delta=np.abs(series['dac_ra_pre_log'][1][:,2]-series['dac_ra_pre_log'][0][:,2]);k=int(np.argmax(vtop_delta))
report={'schema':'sar20-ID5-093124-independent-readback/v1','verifier_sha256':sha(Path(__file__).resolve()),
        'receipt_sha256':sha(receipt_path),'runs':[{'path':str(d),'simout_sha256':sha(d/'simout.mat'),
        'model_sha256':sha(d/'SarAdc.slx'),'parameters_sha256':sha(d/'parameters.mat')} for d in dirs],
        'saved_P_differences':diff,'same_source_manifest_file_sha_count':len(source_files[0]),
        'same_native_edges_and_solver':True,'only_block_dialog_diff':block_changes,
        'block_dialog_note':'SID105 AttributesFormatString is display text for the different tau.',
        'time_selection':'event_log ID5/group1..48 joined exactly to native logger Time; '
        'no +/- time window','obs8_fields':['VX_V','VY_V','Vtop_V','target_V','NG','tau_RA_s','AZ_input_diff_V','CT_reset_baseline_V'],
        'row_comparison':'equal_nan numerical equality, like reported isequaln; not a raw-bit equality claim',
        'changes':changes,'selected_events':[item(g) for g in [1,2,3,5,12,13,47,48]],
        'ID5_record':records[0],
        'Vtop_max':{'group':k+1,'relative_ns':float((tt[k]-5*Ts)*1e9),
                    'abs_delta_V':float(vtop_delta[k]),'control_RA_on':float(series['control_log'][0][k,1]),
                    'boundary':'Vtop=(VX-target)/NG is an observation calculated even when RA is off; '
                               'not an independently measured VX or a standalone RA settling error.'},
        'cross_sample_reset_decay':{'ID4_release_time_s':prev_t,'ID4_release_pre_final_commit_VX_V':old,
                                    'ID5_CNV_VX_V':now,'saved_reset_tau_s':reset_tau,
                                    'elapsed_s':float(tt[0])-prev_t,'model_prediction_VX_V':pred,
                                    'prediction_bits_equal_observed':True,
                                    'boundary':'Source reset equation and two actual pre observations support the '
                                               'inference; full post-reset committed state is not independently logged.'},
        'scope':'Read actual event endpoints; no simulation or state interpolation; N8 one sample, '
                'not continuous peaks, silicon, or full N256 performance evidence.'}
print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
