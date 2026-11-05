#!/usr/bin/env python3
"""Read-only replay of actual first OU interval; stdout only, never launches MATLAB.

Run after native v3 scratch output is mirrored:
  PROJECT/dependencies/analysis_env/bin/python audit_first_ou_event.py --project PROJECT --result RESULT
Requires actual RESULT/zero_tap and RESULT/on P.mat + simout.mat, not mock data.
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import h5py
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--result',type=Path,required=True)
    args=ap.parse_args();project=args.project.resolve();run=args.result.resolve()
    sys.dont_write_bytecode=True
    helper=project/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
    sys.path.insert(0,str(helper.parent))
    from verify_as_run import need,read_logs,val,pdiff,same,sha
    zdir=run/'zero_tap';odir=run/'on'
    zp=zdir/'P.mat';op=odir/'P.mat';zs=zdir/'simout.mat';os=odir/'simout.mat'
    for f in (zp,op,zs,os):need(f.is_file(),'Missing actual saved artifact '+str(f))
    diff=set(pdiff(zp,op))
    need(diff=={'P/backend/ra_noise/sigma_vx_rms','P/ni/ra_noise'},'Unexpected P differences '+repr(sorted(diff)))
    with h5py.File(op,'r') as f,h5py.File(zp,'r') as g:
        sigma=float(val(f,'P/backend/ra_noise/sigma_vx_rms'))
        seed=int(val(f,'P/backend/ra_noise/seed_u64'))
        epoch=int(val(f,'P/epoch'))
        need(sigma>0 and float(val(g,'P/backend/ra_noise/sigma_vx_rms'))==0,'Wrong sigma modes')
        need(seed==int(val(g,'P/backend/ra_noise/seed_u64')) and epoch==int(val(g,'P/epoch')),'Seed/epoch mismatch')
        need(int(val(f,'P/ni/comparator_noise'))==0 and int(val(f,'P/ni/reference_recovery'))==0 and
             float(val(f,'P/control/sar1/coarse_noise_rms_v'))==0,'Unqualified noise profile')
        for path in ['bank/enabled','training/enabled','cal_cfg/enabled','frozen/enabled']:
            need(int(val(f,'P/'+path))==0,'Unqualified mode '+path)
        net={k:np.asarray(val(f,'P/backend/ct/net_nominal/'+k),dtype=float) for k in
             ['cinc_f','bridge_f','main_f','sub_f','track_f','parasitic_main_f','parasitic_sub_f','dummy_f']}
        need(int(val(f,'P/backend/ni/cap_mismatch'))==0,'Only nominal CT matrix is supported')
    a=read_logs(zs);b=read_logs(os)
    for n in ('event_log','control_log','front_log','back_log','dac_ra_pre_log'):
        need(n in a and n in b and same(a[n]['time'],b[n]['time']),'Missing/different actual axis '+n)
    event=a['event_log']['data'];need(same(event,b['event_log']['data']),'Event IDs/groups differ')
    ids0=np.flatnonzero((event[:,0]==0)&(event[:,1]==12));ids1=np.flatnonzero((event[:,0]==0)&(event[:,1]==13))
    need(len(ids0)==len(ids1)==1 and ids1[0]==ids0[0]+1,'First active interval missing or ambiguous')
    i0=int(ids0[0]);i1=int(ids1[0])
    for n in ('control_log','front_log'):
        need(same(a[n]['data'][:i1+1],b[n]['data'][:i1+1]),'Pre-decision signal mismatch '+n)
    for n in ('dac_ra_pre_log','back_log'):
        need(same(a[n]['data'][i0],b[n]['data'][i0]),'RAstart prior state observable differs '+n)
    times=a['event_log']['time'];t0=float(times[i0]);t1=float(times[i1]);need(0<=t0<t1,'Bad event time')
    pre0=a['dac_ra_pre_log']['data'];pre1=b['dac_ra_pre_log']['data']
    tau=float(pre1[i1,5]);need(tau>0 and math.isfinite(tau) and pre0[i1,5]==tau,'RA tau mismatch')
    bits=lambda x:struct.unpack('>Q',struct.pack('>d',x))[0]
    payload=b'SAR20-RA-OU-v1\x00'+struct.pack('>QQQQQ',seed,epoch,0,bits(t0),bits(t1))
    digest=hashlib.sha256(payload).digest();w1=int.from_bytes(digest[:8],'big')>>12;w2=int.from_bytes(digest[8:16],'big')>>12
    u1=(w1+0.5)/float(1<<52);u2=(w2+0.5)/float(1<<52)
    normal=math.sqrt(-2*math.log(u1))*math.cos(2*math.pi*u2)
    expected=sigma*math.sqrt(-math.expm1(-2*((t1-t0)/tau)))*normal
    vx_on=float(pre1[i1,0]);vx_zero=float(pre0[i1,0]);observed=vx_on-vx_zero
    alpha=[]
    for side in range(2):
        cs=net['cinc_f'].ravel()[side];cb=net['bridge_f'].ravel()[side]
        A=cs+np.sum(net['main_f'][side,:])+cb+net['parasitic_main_f'].ravel()[side]
        B=np.sum(net['sub_f'][side,:])+np.sum(net['track_f'][side,:])+net['dummy_f'].ravel()[side]+cb
        need(A*B-cb*cb>0,'CT matrix singular');alpha.append(float(cs*B/(A*B-cb*cb)))
    k=(alpha[0]+alpha[1])/2
    vy_on=float(b['back_log']['data'][i1,1]);vy_zero=float(a['back_log']['data'][i1,1]);dy=vy_on-vy_zero
    def ulp(x):return float(np.spacing(abs(float(x))))
    tol_x=64*(ulp(vx_on)+ulp(vx_zero)+ulp(expected))
    tol_y=64*(ulp(vy_on)+ulp(vy_zero)+ulp(k*observed))
    need(abs(observed-expected)<=tol_x,'OU first-interval increment differs beyond floating tolerance')
    need(abs(dy-k*observed)<=tol_y,'CT VY coupling differs from independent 2x2 matrix')
    print(json.dumps({'status':'actual_first_ou_event_independently_checked',
       'files':{'zero_P':sha(zp),'on_P':sha(op),'zero_simout':sha(zs),'on_simout':sha(os),'project_reader':sha(helper)},
       'scope':'Only first ID0 interval; key from actual event timestamps plus static stage semantics, not an instrumented key pin.',
       'time_s':[t0,t1],'time_bits_hex':[format(bits(t0),'016x'),format(bits(t1),'016x')],
       'epoch':epoch,'id':0,'seed_u64':seed,'sigma_vx_rms':sigma,'tau_s':tau,
       'key_sha256':digest.hex(),'z':normal,'expected_dx_v':expected,'actual_dx_v':observed,
       'dx_residual_v':observed-expected,'dx_tolerance_v':tol_x,'alpha_per_half':alpha,
       'expected_dy_from_actual_dx_v':k*observed,'actual_dy_v':dy,
       'dy_residual_v':dy-k*observed,'dy_tolerance_v':tol_y,
       'limits':'No noise PSD, distribution, model promotion, PDK or silicon claim.'},indent=2))


if __name__=='__main__':main()
