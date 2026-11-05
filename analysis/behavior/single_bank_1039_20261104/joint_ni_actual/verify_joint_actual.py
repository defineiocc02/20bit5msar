#!/usr/bin/env python3
"""Independent readback of actual joint-NI N8/N256 MAT. No MATLAB/model execution."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
import h5py,numpy as np

ROOT=Path('/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020')
PRJ=ROOT/'analysis/behavior/single_bank_1039_20261104';RUN=PRJ/'joint_ni_actual'
sys.path.insert(0,str(ROOT/'analysis/behavior/finite_dac_review_20261028'));import verify_as_run as u

def need(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<=300_000_000,f'bad input or >300 MB {p}')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def ct_kick(P,sign):
    """Separate 2x2 charge solve using saved main and replica capacitors."""
    def network(name,s):
        base='P/backend/ct/'+name+'/'
        get=lambda k:np.asarray(u.val(P,base+k),dtype=float)
        cs=get('cinc_f').ravel();cb=get('bridge_f').ravel()
        main=get('main_f');sub=get('sub_f');tr=get('track_f')
        d=get('dummy_f').ravel();pm=get('parasitic_main_f').ravel();ps=get('parasitic_sub_f').ravel()
        capA=cs+main.sum(axis=1)+cb+pm;capB=sub.sum(axis=1)+tr.sum(axis=1)+d+cb+ps
        det=capA*capB-cb**2;need(np.all(det>0),'CT singular')
        ref=float(u.val(P,'P/backend/ct/reference_v'));q1=-np.array([1.,-1.])*ref/2*main[:,0]*s
        return cs*capB*q1/det,cs*(1-cs*capB/det)
    matched=not bool(u.val(P,'P/backend/ni/cap_mismatch'))
    qm,lm=network('net_nominal' if matched else 'net_actual',sign)
    qr,lr=network('net_nominal' if matched else 'net_replica',-sign)
    load=np.asarray(u.val(P,'P/backend/ct/output_parasitic_half_f')).ravel()+lm+lr
    return float(((qm+qr)/load)[0]-((qm+qr)/load)[1])

def main():
    manifest=json.loads((RUN/'transfer_manifest.json').read_text());need(len(manifest)==70,'expected 70 transfer entries')
    for e in manifest:
        f=RUN/e['path'];need(f.stat().st_size==e['bytes'] and sha(f)==e['sha256'],f'transfer hash {f}')
    P=[RUN/'ni_n8_match/P_used.mat',RUN/'ni_n8_joint/P_used.mat',RUN/'ni_n256/P_used.mat']
    S=[RUN/'ni_n8_match/simout.mat',RUN/'ni_n8_joint/simout.mat',RUN/'ni_n256/simout.mat']
    profile=RUN/'ni_profile/P_pair.mat'
    with h5py.File(profile,'r') as f:
        for kind,path in [('matched',P[0]),('joint',P[1])]:
            with h5py.File(path,'r') as g:need(u.fingerprint(f,f[kind],{})==u.fingerprint(g,g['P'],{}),f'{kind} differs profile')
        c=np.asarray(u.val(f,'joint/front/C_f'));offset=np.asarray(u.val(f,'assumption/branch_relative_offsets')).ravel()
        weights=np.asarray(u.val(f,'assumption/branch_weights')).ravel();cu=float(u.val(f,'joint/front/unit_cap_f'))
        need(c.shape==(18,38) and len(offset)==len(weights)==37 and
             np.all(c[:8,:37]==c[0,:37]) and np.all(c[:8,37]==0) and
             np.max(np.abs(c[0,:37]-cu*weights*(1+offset)))<1e-27,'actual array mismatch profile')
    pairdiff=u.pdiff(P[0],P[1]);need(pairdiff==['P/backend/ct/net_actual/cinc_f','P/backend/ct/net_replica/cinc_f',
         'P/backend/ni/cap_mismatch'],'matched-vs-joint changes')
    extend=u.pdiff(P[1],P[2]);allowed=sorted(['P/N','P/backend/dac_coupling/public_plan','P/cal_cfg/N_train',
      'P/cal_cfg/public_cfg/plan_rows','P/debug/dac_enabled','P/debug/dac_max_points','P/front/plan',
      'P/front/plan_rows','P/n_cycles','P/schedule/n_cycles','P/schedule/stop_time_s','P/stop_time_s',
      'P/training/reference/records']);need(extend==allowed,'N256 changed physical P')
    with h5py.File(P[1]) as f:
        g=lambda k:u.val(f,'P/'+k)
        need(g('front/ktc_enabled')==1 and g('front/mismatch_enabled')==1 and
          np.all(np.asarray(g('front/tau_dac_s'))==1e-9) and g('backend/az/mode')=='ordinary' and
          np.all(np.asarray(g('backend/az/write_tau_s'))==8e-9) and
          np.all(np.asarray(g('backend/az/leak_tau_s'))==1e-6) and g('backend/ct/replica_enabled')==1,
          'enabled P values differ')
        need(all(not bool(g(k)) for k in ('backend/ni/ra_noise','backend/ni/az_noise','backend/ni/reference_noise',
          'ni/comparator_noise','ni/reference_recovery','front/jitter/enabled','cal_cfg/enabled')) and
          g('digital/calibration_mode')=='off','unsupported NI enabled')
        cn=np.asarray(g('backend/ct/net_nominal/cinc_f'));cm=np.asarray(g('backend/ct/net_actual/cinc_f'))
        cr=np.asarray(g('backend/ct/net_replica/cinc_f'))
        need(np.allclose(cm,cn*1.001,rtol=1e-15,atol=0) and np.allclose(cr,cn*.999,rtol=1e-15,atol=0),
             'actual CINC scale')
        offsets,groups,budget=u.read_calendar(f);ts=float(g('Ts_s'));fs=float(g('fs_hz'));fsr=float(g('fsr_diff_v'))
        fin=float(g('input/frequency_hz'));amp=float(g('input/amplitude_v'));phase=float(g('input/phase_rad'))
    feed=next(i+1 for i,a in enumerate(groups) if 'd2_feedback' in a)
    logs=[u.read_logs(f) for f in S];raws=[];codes=[];rt=[];kicks=[];preds=[];signs=[];prestate=[]
    for j,L in enumerate(logs):
        ncyc=12 if j<2 else 260;e=L['event_log']['data'];t=L['event_log']['time']
        need(np.array_equal(e,np.column_stack((np.repeat(np.arange(ncyc),48),np.tile(np.arange(1,49),ncyc))))
          and u.same(t,np.repeat(np.arange(ncyc)*ts,48)+np.tile(offsets,ncyc)),f'events/time {j}')
        for n in ('raw_log','ready_log','record_log','record_ready_log','code_log','control_log','az_route_log','back_log','front_log'):
            need(u.same(t,L[n]['time']),f'axis {j} {n}')
        ready=L['ready_log']['data'][:,0];idx=np.flatnonzero(ready==1);rr=L['raw_log']['data'][idx]
        need(len(idx)==ncyc and np.array_equal(rr[:,3],np.arange(ncyc)) and np.all(rr[:,4:]==1) and
          u.same(rr,L['record_log']['data'][idx]) and u.same(ready,L['record_ready_log']['data'][:,0]) and
          u.same(rr[:,:3],L['control_log']['data'][idx,4:7]),f'actual raw/id/control {j}')
        raw=rr[4:];code=L['code_log']['data'][idx,0][4:];tm=t[idx][4:]
        with h5py.File(RUN/(['ni_n8_match','ni_n8_joint','ni_n256'][j])/'selected.mat') as f:
            for k,x in [('raw',raw),('code20',code),('time_s',tm)]:
                need(u.same(np.asarray(u.val(f,'selected/'+k)).reshape(x.shape),x),f'selected {j}/{k}')
        raws.append(raw);codes.append(code);rt.append(tm)
        if j<2:
            rows=np.flatnonzero(e[:,1]==feed);need(len(rows)==12 and u.same(t,L['dac_ra_pre_log']['time']),'feedback log')
            pre=L['dac_ra_pre_log']['data'][rows];back=L['back_log']['data'][rows]
            route=L['az_route_log']['data'][rows];ctl=L['control_log']['data'];need(np.all(route[:,3]==1) and np.all(route[:,4]==0),'RA route')
            sg=np.array([2*((int(ctl[q-1,5])>>11)&1)-1 for q in rows]);observed=back[:,0]-pre[:,0]
            with h5py.File(P[j]) as f:pred=np.array([ct_kick(f,int(s)) for s in sg])
            need(np.max(np.abs(pred-observed))<1e-12,'first D2 observed vs independent kick')
            kicks.append(observed);preds.append(pred);signs.append(sg)
            prestate.append(np.column_stack((pre[:,0],pre[:,2:8],route[:,2])))
    need(u.same(raws[1][:8],raws[2][:8]) and u.same(codes[1][:8],codes[2][:8]) and u.same(rt[1][:8],rt[2][:8]),
         'N256 actual prefix not equal N8 joint')
    need(np.array_equal(signs[0],signs[1]),'first D2 sign changed')
    tol=np.array([1e-12,1e-12,1e-12,1e-12,1e-18,1e-12,1e-12,1e-24])
    prestatediff=np.max(np.abs(prestate[0]-prestate[1]),axis=0)
    need(np.all(prestatediff<=tol),'paired first feedback prestates differ')
    need(np.max(np.abs(kicks[0]))<1e-12 and np.min(np.abs(kicks[1]))>1e-12,'unexpected paired kick')
    code=codes[2];need(len(code)==256 and np.all((code>=0)&(code<2**20)),'N256 code range')
    with h5py.File(RUN/'ni_n256/spectrum.mat') as f:
        power=np.asarray(u.val(f,'metrics/power_v2')).ravel();freq=np.asarray(u.val(f,'metrics/frequency_hz')).ravel()
        saved={k:float(u.val(f,'metrics/'+k)) for k in ('snr_db','sndr_db','sfdr_db','thd_db','enob')}
    v=((code+.5)/2**20-.5)*fsr;Y=np.fft.rfft(v-v.mean())/256;ind=np.abs(Y)**2;ind[1:-1]*=2
    rel=float(np.max(np.abs(ind[1:]-power[1:])/power[1:]));need(rel<1e-7 and len(power)==129 and
      np.array_equal(freq,np.arange(129)*fs/256),'FFT bins/powers')
    signal=ind[5];other=ind.copy();other[[0,5]]=0;nd=other.sum();harm=np.arange(2,11)*5
    hp=ind[harm].sum();noise=nd-hp
    calc={'snr_db':float(10*np.log10(signal/noise)),'sndr_db':float(10*np.log10(signal/nd)),
      'sfdr_db':float(10*np.log10(signal/max(other))),'thd_db':float(10*np.log10(hp/signal))}
    calc['enob']=(calc['sndr_db']-1.76)/6.02
    need(all(abs(calc[k]-saved[k])<1e-8 for k in saved),'FFT metrics')
    ideal=amp*np.sin(2*np.pi*fin*raws[2][:,3]*ts+phase)
    out=(code-2**19)*fsr/2**20;err=out-ideal;A=np.column_stack((np.ones(256),ideal));fit=np.linalg.lstsq(A,out,rcond=None)[0]
    ref={'mean_v':float(np.mean(err)),'raw_rms_v':float(np.sqrt(np.mean(err**2))),
      'fit_offset_v':float(fit[0]),'fit_gain':float(fit[1]),'fit_residual_rms_v':float(np.sqrt(np.mean((out-A@fit)**2)))}
    with h5py.File(RUN/'ni_n256/stimulus_reference.mat') as f:
        for a,b in [('mean_v','mean_output_minus_stimulus_v'),('raw_rms_v','raw_error_rms_v'),
          ('fit_offset_v','fitted_offset_v'),('fit_gain','fitted_gain'),('fit_residual_rms_v','post_fit_residual_rms_v')]:
            need(abs(ref[a]-float(u.val(f,'reference/'+b)))<1e-12,f'reference check {a}')
    report={'schema':'joint-ni-independent-actual-v1','transfer_items_sha_verified':70,
      'inputs_sha256':{str(x.relative_to(RUN)):sha(x) for x in P+S+[profile,RUN/'ni_n256/selected.mat',RUN/'ni_n256/spectrum.mat',RUN/'ni_n256/stimulus_reference.mat']},
      'profile_identity_and_actual_array_checked':True,'matched_to_joint_diff_paths':pairdiff,'jointN8_to_N256_diff_paths':extend,
      'event_rows':[576,576,12480],'actual_raw_counts':[12,12,260],'actual_selected_counts':[8,8,256],
      'joint_N256_prefix_raw_code_time_equals_N8':True,'first_feedback_group':feed,'feedback_times_s':logs[1]['event_log']['time'][np.flatnonzero(logs[1]['event_log']['data'][:,1]==feed)].tolist(),
      'feedback_signs':signs[1].tolist(),'matched_kick_v':kicks[0].tolist(),'joint_kick_v':kicks[1].tolist(),
      'joint_kick_independent_2x2_v':preds[1].tolist(),'pair_prestate_max_abs_difference':prestatediff.tolist(),
      'saved_metrics':saved,'independent_metrics':calc,'max_nonDC_fft_relative_power_error':rel,
      'stimulus_reference_recomputed':ref,'rail_endpoint_code_count':int(np.count_nonzero((code==0)|(code==2**20-1))),
      'configuration_scope':'kTC on, one deterministic shared capacitor mismatch sample, DAC tau 1 ns, AZ 8 ns/1 us, CINC 1.001/0.999; calibration off; RA OU/comparator/reference noise and jitter off',
      'limits':'First D2 kick compares actual same-event pre/post stage wires; signs derived from previous control bit; replica remains enabled. Stimulus reference is declared model input, not an independently measured external reference. No PDK, silicon, mismatch population, full noise or DNL/INL claim.'}
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
