#!/usr/bin/env python3
"""Read actual 095606 artifacts and independently re-evaluate saved interval inputs."""
from decimal import Decimal,localcontext
from pathlib import Path
import hashlib,json,math,struct,zipfile
import h5py
import numpy as np
from verify_as_run import archive_provenance,at,graph,need,pdiff,read_calendar,read_logs,same,sha,val

root=Path(__file__).resolve().parents[3];run=root/'runs/az_probe_20261028T095606Z'
receipt=json.loads((run/'receipt.json').read_text())
need(receipt['status']=='isolated_joint_az_dac_N8_actual_parity_and_expm_recorded' and
     receipt['phase']=='complete','Receipt incomplete')
cases=[('far_mixed','behavior_6dc7cc07-849a-4717-b358-730170f8b547'),
       ('minus_ulp','behavior_e5717b4d-6f9d-4b9e-98fe-8d90f80a2e76'),
       ('plus_ulp','behavior_350b3dc4-6dc8-4c55-a3b8-5a2c91dcbef5')]

def compare_logs(original,probed):
    a,b=read_logs(original),read_logs(probed)
    need(set(b)==set(a)|{'joint_interval_log'},'Unexpected old/new logger inventory')
    failed=[k for k in a if a[k]['class']!=b[k]['class'] or
            not same(a[k]['time'],b[k]['time']) or not same(a[k]['data'],b[k]['data'])]
    need(not failed,'Old logger Time/Data/class/shape/raw bits differ: '+repr(failed))
    return a,b

def compare_all_logs(a,b):
    aa,bb=read_logs(a),read_logs(b)
    need(set(aa)==set(bb),'Original/plain logger inventory differs')
    need(all(aa[k]['class']==bb[k]['class'] and same(aa[k]['time'],bb[k]['time']) and
             same(aa[k]['data'],bb[k]['data']) for k in aa),'Original/plain logger bit mismatch')
    return len(aa)

def source_identity(folder):
    with zipfile.ZipFile(folder/'source.zip','r') as z:
        manifest=json.loads((folder/'source_manifest.json').read_text())['files']
        expected={x['path'].replace('\\','/'):x['sha256'] for x in manifest}
        need(set(z.namelist())==set(expected),'Source archive inventory mismatch')
        for name,h in expected.items():need(hashlib.sha256(z.read(name)).hexdigest()==h,'Source file SHA mismatch: '+name)
        for name,h in {**receipt['production_pins'],**receipt['helper_sha256']}.items():
            paths=[p for p in z.namelist() if Path(p).name==name+'.m']
            need(len(paths)==1 and hashlib.sha256(z.read(paths[0])).hexdigest()==h,
                 'Actual as-run source does not match recorded runtime pin: '+name)
    return len(expected)

def decimal_predict(row,cf,ng,gain,vos,leaks):
    D=Decimal.from_float
    with localcontext() as ctx:
        ctx.prec=90;h=D(float(row[5]-row[4]));r=D(float(row[13]));er=(-h/r).exp()
        cf,ng,gain,vos=map(D,map(float,[cf,ng,gain,vos]))
        vx=D(float(row[9]))*er+gain*(D(float(row[6]))/cf+ng*vos)*(1-er)
        for tau,delta in zip(row[28:36],row[36:44]):
            if tau==0 or math.isinf(tau):continue
            t=D(float(tau));H=(h/r)*er if t==r else t/(t-r)*((-h/t).exp()-er)
            vx+=gain*D(float(delta))/cf*(1-er-H)
        for j,tau in enumerate(leaks):
            if tau==0:continue
            if math.isinf(tau):H=1-er
            else:
                z=D(float(tau));H=(h/r)*er if z==r else z/(z-r)*((-h/z).exp()-er)
            vx+=(-1 if j==0 else 1)*gain*ng*D(float(row[14+j]))*H
        return float(vx)

def saved_tokens(f):
    result=[]
    for ref in f['P/adc_groups/events'][()].ravel():
        event=f[ref];kind=event['type'];index=event['index']
        if h5py.check_dtype(ref=kind.dtype) is not None:
            kinds=[''.join(map(chr,f[r][()].ravel())) for r in kind[()].ravel()]
            indices=[int(f[r][()].item()) for r in index[()].ravel()]
        else:
            kinds=[''.join(map(chr,kind[()].ravel()))];indices=[int(index[()].item())]
        need(len(kinds)==len(indices),'Malformed saved calendar token index')
        result.append(list(zip(kinds,indices)))
    return result

plain=run/'plain_run';far=run/'far_mixed_run';base=root/'runs'/cases[0][1]
for d in [plain,far]:archive_provenance(d,json.loads((d/'summary.json').read_text()),False)
need(not pdiff(base/'parameters.mat',plain/'parameters.mat') and
     not pdiff(plain/'parameters.mat',far/'parameters.mat'),'Original/plain/probed P differs')
count=compare_all_logs(base/'simout.mat',plain/'simout.mat');need(count==30,'Expected 30 original logs')
Ab,Eb,Cb=graph(plain/'SarAdc.slx');Ap,Ep,Cp=graph(far/'SarAdc.slx')
need(Cb==Cp and not(Eb-Ep) and set(Ap)-set(Ab)=={'453','454'},'Scratch graph original inventory/solver changed')
expected={('237#out:1','453#in:1'),('236#out:1','453#in:2'),('323#out:1','453#in:3'),
          ('322#out:2','453#in:4'),('321#out:2','453#in:5'),('453#out:1','454#in:1')}
need(Ep-Eb==expected and Ap['453'][2].get('FunctionName')=='joint_interval_probe_sfun' and
     Ap['454'][2].get('VariableName')=='joint_interval_log','Scratch observation edges/blocks differ')
graphchanges=[]
for sid in sorted(Ab):
    need(Ab[sid][:2]==Ap[sid][:2],'Existing block name/type changed')
    for key in sorted(set(Ab[sid][2])|set(Ap[sid][2])):
        if Ab[sid][2].get(key)!=Ap[sid][2].get(key):graphchanges.append([sid,key])
need(all(key=='Position' for _,key in graphchanges),'Existing non-position block parameter changed')
outputs=[]
for label,original_name in cases:
    folder=run/(label+'_run');original=root/'runs'/original_name
    summary=json.loads((folder/'summary.json').read_text());files,source_boundary=archive_provenance(folder,summary,False)
    need(summary['status']=='complete' and summary['simulation_completed'] and summary['records']==8 and
         summary['capture_boundary']=='direct_raw','Actual selected run scope invalid')
    need(sha(folder/'SarAdc.slx')==receipt['cases'][label]['probed_model_sha256'],'SLX hash != receipt')
    need(not pdiff(original/'parameters.mat',folder/'parameters.mat'),'Original/probed saved P differs')
    old,L=compare_logs(original/'simout.mat',folder/'simout.mat');need(len(old)==30,'Expected 30 old loggers')
    source_count=source_identity(folder);pr=L['joint_interval_log'];valid=pr['data'][:,0]==1
    q=pr['data'][valid];t=pr['time'][valid];need(q.shape==(8,44) and
         np.array_equal(q[:,1],np.arange(4,12)) and np.all(q[:,2]==1),'Probe IDs/epoch/valid mismatch')
    need(np.all(np.isin(pr['data'][:,0],[0,1])),'Probe valid nonbinary')
    with h5py.File(folder/'parameters.mat','r') as f:
        N=int(val(f,'P/N'));first=int(val(f,'P/first_id'));epoch=int(val(f,'P/epoch'))
        Ts=float(val(f,'P/Ts_s'));times,groups,budget=read_calendar(f);tokens=saved_tokens(f)
        cf=float(val(f,'P/backend/ra/Cf_f'));a0=float(val(f,'P/backend/ra/A0'))
        ugb=float(val(f,'P/backend/ra/UGB_hz'));vos=float(val(f,'P/backend/ra/vos_input_v'))
        leaks=np.asarray(val(f,'P/backend/az/leak_tau_s')).ravel();tau=np.asarray(val(f,'P/front/tau_dac_s')).ravel()
        plan=val(f,'P/front/plan');need(N==8 and first==4 and epoch==1 and
             val(f,'P/backend/az/mode')=='hold_chop' and val(f,'P/backend/ni/az') and
             val(f,'P/backend/dac_coupling/enabled') and not val(f,'P/transport/enabled') and
             math.isinf(val(f,'P/backend/ra/slew_v_per_s')),'Prepared P does not match test scope')
        need(math.isinf(leaks[1]),'Second AZ hold is not Inf')
    g0=[i+1 for i,x in enumerate(groups) if 'ra_start' in x];g1=[i+1 for i,x in enumerate(groups) if 'd2_prepare' in x]
    need(len(g0)==1 and g1 and g0[0]<g1[0] and budget=={'d2_decide':12,'ta_compare':8,'ta_feedback':7},
         'Saved calendar/event budget changed')
    t0=q[:,4];t1=q[:,5];need(same(t,t1) and same(t0,np.array([i*Ts+times[g0[0]-1] for i in range(4,12)])) and
         same(t1,np.array([i*Ts+times[g1[0]-1] for i in range(4,12)])),'Actual interval time differs')
    fe0=at(L['front_log'],t0,'front start');fe1=at(L['front_log'],t1,'front end')
    bk0=at(L['back_log'],t0,'back start');pre=at(L['dac_ra_pre_log'],t1,'RApre')
    need(same(fe0[:,2]*q[:,3],q[:,6]) and same(fe1[:,2]*q[:,3],q[:,7]) and
         same(bk0[:,0],q[:,9]) and same(pre[:,0],q[:,10]) and same(q[:,10]-q[:,11],q[:,12]),
         'Actual FE/Q/VX/pre/logged delta differ from probe')
    need(same(pre[:,3],q[:,7]/cf) and same(pre[:,5],q[:,13]) and
         same(pre[:,2],(pre[:,0]-pre[:,3])/pre[:,4]),'Actual target/R/Vtop differ')
    event=L['event_log'];e=event['data'];te=event['time']
    for j,row in enumerate(q):
        ident=int(row[1]);ix=np.flatnonzero((e[:,0]==ident)&(e[:,1]>=1)&(e[:,1]<=48));tt=te[ix]
        need(len(ix)==48 and np.array_equal(e[ix,1],np.arange(1,49)) and
             same(tt,np.array([ident*Ts+v for v in times])),'Actual 48-group calendar mismatch')
        W=at(L['adi_wire_log'],tt,'ADI');C=at(L['control_log'],tt,'control')
        Rte=at(L['az_route_log'],tt,'AZ route');Z=at(L['az_commit_log'],tt,'AZ commit')
        B=at(L['back_log'],tt,'back');counts=np.zeros(3);signs=np.zeros(7);last=None
        need(np.array_equal(W[:,:8],np.tile(np.sort(plan[ident]),(48,1))) and
             np.all(W[:,56]==ident) and np.all(W[:,57]==epoch),'Actual ADI owner/tags differ')
        for g,evs in enumerate(tokens):
            for kind,index in evs:
                if kind=='d2_decide':counts[0]+=1
                if kind=='ta_compare':counts[1]+=1
                if kind=='ta_feedback':counts[2]+=1
            need(np.array_equal(W[g,51:54],counts),'Actual D2/TA counters differ')
            for kind,index in evs:
                if kind=='ta_feedback':
                    need(g>0 and 0<=index<7,'Unexpected TA feedback index')
                    signs[index]=2*((int(C[g-1,6])>>(7-index))&1)-1
                elif kind=='ta_compare' and index==7:last=g
            need(np.array_equal(W[g,44:51],signs),'Actual TA feedback signs differ')
        need(np.array_equal(counts,[12,8,7]) and last is not None and
             np.all(W[last:47,52]==8) and np.all(W[last:47,53]==7) and
             np.array_equal(W[last:47,44:51],np.tile(W[last,44:51],(47-last,1))),
             'Actual final 8th comparison / 7 update boundary differs')
        pol=float(row[3]);expected_charge=Rte[:,1] if pol>0 else -Rte[:,1]
        need(np.all(Rte[:,0]==pol) and same(Rte[:,2],expected_charge) and
             not np.any((Rte[:,3]!=0)&(Rte[:,4]!=0)),'Actual AZ/RA route/POL mismatch')
        returned=B[-1,2] if pol>0 else -B[-1,2]
        need(same(np.float64(Rte[-1,5]),np.float64(returned)),'Actual release Vtop route mismatch')
        active=np.flatnonzero(Rte[:,3]!=0)
        need(row[16]==ident//2 and row[17]>=1 and Z[g1[0]-1,1]==1 and
             Z[g1[0]-1,2]==ident//2 and Z[g1[0]-1,3]==epoch and Z[g1[0]-1,5]==0 and
             len(active)>0 and np.all(Z[active,1]==1) and np.all(Z[active,5]==0) and
             np.all(Z[:,6]==row[17]) and (np.any(Rte[:,4]!=0)==(ident%2==0)),
             'Actual AZ pair/write/active flags differ')
    for j in range(0,8,2):
        need(q[j,16]==q[j+1,16] and q[j,17]==q[j+1,17] and
             same(np.float64(q[j,15]),np.float64(q[j+1,15])),
             'Actual AZ infinite-leak half/pair/write-count differs')
    azdelta=[];anal=[]
    for j,row in enumerate(q):
        ident=int(row[1]);ids=plan[ident].astype(int);ng=float(pre[j,4]);R=ng/(2*math.pi*ugb)
        need(np.array_equal(row[20:28],ids) and same(row[28:36],tau[ids-1]) and
             same(np.float64(row[13]),np.float64(R)),'Probe actual ID/tau/RA pole mismatch')
        word=struct.unpack('>Q',struct.pack('>d',float(row[13])))[0]
        leakword=struct.unpack('>Q',struct.pack('>d',float(row[18])))[0]
        if label=='far_mixed':need(row[19]==0,'Far pole incorrectly near')
        else:
            need(row[19]==1 and (leakword-word)==(-1 if label=='minus_ulp' else 1),'AZ pole not actual +/- one ULP')
        gain=1. if math.isinf(a0) else a0/(a0+ng)
        oracle=decimal_predict(row,cf,ng,gain,vos,leaks)
        anal.append({'ID':ident,'t0_s':float(row[4]),'t1_s':float(row[5]),
                     'actual_pre_VX_V':float(row[10]),'native_expm_VX_V':float(row[11]),
                     'actual_minus_native_expm_V':float(row[12]),'decimal90_VX_V':oracle,
                     'actual_minus_decimal90_V':float(row[10])-oracle,
                     'native_expm_minus_decimal90_V':float(row[11])-oracle,
                     'AZ1_start_V':float(row[14]),'AZ2_start_V':float(row[15]),
                     'tau_R_hex':float(row[13]).hex(),'tau_AZ1_hex':float(row[18]).hex(),
                     'near_condition':bool(row[19]),'physical_ids':row[20:28].tolist(),
                     'tau_D_s':row[28:36].tolist(),'signed_delta_Q_C':row[36:44].tolist()})
    # Independently check selected records against actual ready and saved MAT report.
    ready=L['record_ready_log'];rt=ready['time'][ready['data'][:,0]==1]
    raw=at(L['record_log'],rt,'record');code=at(L['code_log'],rt,'code')[:,0]
    sel=(raw[:,3]>=4)&(raw[:,3]<12);raw=raw[sel];code=code[sel];rt=rt[sel]
    need(raw.shape==(8,6) and np.array_equal(raw[:,3],np.arange(4,12)) and
         np.all(raw[:,4]==1) and np.all(raw[:,5]==1),'Actual record tags/valid differ')
    with h5py.File(folder/'selected.mat','r') as f:
        need(sha(folder/'selected.mat')==summary['selected_sha256'] and
             same(f['selected/raw'][()].T,raw) and same(f['selected/code20'][()].ravel(),code) and
             same(f['selected/time_s'][()].ravel(),rt),'Selected actual record mismatch')
    report_path=run/(label+'_analytic.mat')
    with h5py.File(report_path,'r') as f:
        need(int(val(f,'analytic/sample_count'))==8 and int(val(f,'analytic/valid_one_count'))==8 and
             bool(val(f,'analytic/record_gate_all_8_valid')) and not bool(val(f,'analytic/analytical_pass_declared')) and
             bool(f['analytic/analytical_tolerance'].attrs.get('MATLAB_empty',0)),
             'Analytic report valid/tolerance flags differ')
        need(same(f['analytic/record_rows'][()].T,raw) and same(f['analytic/record_code20'][()].ravel(),code) and
             same(f['analytic/record_time_s'][()].ravel(),rt),'Analytic report actual record mismatch')
        ps=f['analytic/per_sample'];mapping={'id':1,'polarity':3,'q0_C':6,'q1_C':7,'signed_drift_C':8,
             'VXpre_V':10,'VX_expm_V':11,'VX_minus_expm_V':12,'R_s':13,'AZ1_start_V':14,
             'AZ2_start_V':15,'AZpair':16,'AZwrites':17,'AZleak1_s':18,'near_branch':19}
        for key,col in mapping.items():
            got=np.array([f[ref][()].ravel()[0] for ref in ps[key][()].ravel()],dtype=np.float64)
            need(same(got,np.asarray(q[:,col],dtype=np.float64)),'Analytic per-sample mismatch '+key)
        for key,start in [('physical_ids',20),('dac_taus_s',28),('delta_q_C',36)]:
            got=np.array([f[ref][()].ravel() for ref in ps[key][()].ravel()])
            need(same(got,q[:,start:start+8]),'Analytic per-sample vector mismatch '+key)
        max_saved=float(val(f,'analytic/max_abs_VX_minus_expm_V'))
        need(same(np.float64(max_saved),np.float64(np.max(np.abs(q[:,12])))) and
             same(np.float64(max_saved),np.float64(receipt['cases'][label]['max_abs_VX_minus_expm_V'])),
             'Native report/receipt max residual mismatch')
        leak_saved=f['analytic/az_hold/finite_leak_raw_delta_V'][()].ravel()
        leak_deltas=np.array([q[k+1,14]-q[k,14]*math.exp(-(q[k+1,4]-q[k,4])/leaks[0])
                              for k in range(0,8,2)])
    outputs.append({'case':label,'source_run':original_name,'as_run_identity':files,
                    'analytic_sha256':sha(report_path),'simout_sha256':sha(folder/'simout.mat'),
                    'saved_source_files_verified':source_count,'source_execution_boundary':source_boundary,
                    'probed_vs_original_old_timeseries_rawbits_equal':len(old),
                    'saved_P_original_vs_probe_rawbits_equal':True,'probe_actual_intervals':len(q),
                    'near_condition_count':int(np.count_nonzero(q[:,19])),'actual_valid_records':len(raw),
                    'actual_ADI_12D2_8TA_7updates_and_all_7_feedback_signs':True,
                    'actual_AZ_POL_pair_and_infinite_leak_half_checked':True,
                    'native_max_abs_VX_minus_expm_V':max_saved,
                    'independent_decimal90_max_abs_actual_minus_VX_V':max(abs(x['actual_minus_decimal90_V']) for x in anal),
                    'independent_decimal90_max_abs_expm_minus_VX_V':max(abs(x['native_expm_minus_decimal90_V']) for x in anal),
                    'saved_leak_residual_V':leak_saved.tolist(),'python_leak_residual_V':leak_deltas.tolist(),
                    'each_sample':anal})
for label in ['minus_ulp','plus_ulp']:
    need(pdiff(far/'parameters.mat',run/(label+'_run')/'parameters.mat')==['P/backend/az/leak_tau_s'],
         'Near/far has extra P differences')
out={'schema':'sar20-joint-095606-independent-readback/v1','verifier_sha256':sha(Path(__file__).resolve()),
     'receipt_sha256':sha(run/'receipt.json'),'original_vs_plain_old_timeseries_rawbits_equal':count,
     'plain_vs_far_P_rawbits_equal':True,'original_native_edges':len(Eb),'probed_native_edges':len(Ep),
     'removed_original_edges':0,'added_observation_edges':[list(x) for x in sorted(expected)],
     'existing_block_changes':graphchanges,'solver_equal':True,'cases':outputs,
     'main_untouched':'reported true by isolated job receipt; this readback does not independently inspect the live host.',
     'boundary':'24 saved pre-CINC interval observations and inputs; FE353/BK48 full histories not retained. '
                'Decimal and native expm share the recorded physical-state scalars; no new tolerance or analytical pass. '
                'Near predicate plus nonzero AZ amplitude is source-condition evidence, not a branch instrumentation trace. '
                'No extrapolation to full state space, PVT, transistor or silicon.'}
print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
