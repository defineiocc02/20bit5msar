#!/usr/bin/env python3
"""Read-only audit of a real single-bank return-probe N8; no MATLAB execution.

All inputs must be <=300MB. Checks saved graph wires, wrapper identity, actual
1457-word probe/log data and original logged output equality. The returned
charge is the stage's actual intermediate q_return, not inferred from post.
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys,zipfile
from pathlib import Path
import h5py,numpy as np
sys.dont_write_bytecode=True
LIMIT=300_000_000
BASE_MODEL='48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'
PLAIN_SIM='d472f01a80a832cd483783e4ceca0640a692e0094d1a64f5400411e5201a934c'
FIXTURE_P='dfa91dda5a686563b9b0fe17c5e8d906d94e6ff9168251bc27a0830099947e4f'
WRAPPER='0c321288cdcb2008237b3e71657722c5598f89888e16d518ee71fd08c12405ef'
READER='3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'
ROOT_READER='a73344211cdba2ad14825e4fe1612f7f2e864fa4e77ffacdc1392c04374c96a5'


def need(ok,msg):
    if not ok:raise ValueError(msg)


def bounded(p):
    p=Path(p);need(p.is_file() and not p.is_symlink() and p.stat().st_size<=LIMIT,f'missing/symlink/>300MB {p}');return p


def sha(p):
    h=hashlib.sha256()
    with bounded(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def graph(u,p):
    with zipfile.ZipFile(bounded(p)) as z:need(all(x.file_size<=LIMIT for x in z.infolist()),'oversized SLX entry')
    return u.graph(p)


def tout(p):
    with h5py.File(bounded(p),'r') as f:
        seq=[f[x] for x in f['#subsystem#/MCOS'][()].ravel()]
        owners=[g for g in seq if isinstance(g,h5py.Group) and {'event_log','raw_log','tout','yout'}<=set(g)]
        need(len(owners)==1,'ambiguous simout');d=owners[0]['tout']
        return np.asarray(d[()]),str(d.attrs.get('MATLAB_class'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--probe-simout',required=True,type=Path);ap.add_argument('--probe-sha',required=True)
    ap.add_argument('--probe-model',required=True,type=Path);ap.add_argument('--model-sha',required=True)
    ap.add_argument('--wrapper',required=True,type=Path)
    args=ap.parse_args();r=args.project.resolve();new=args.probe_simout.resolve();model=args.probe_model.resolve();wrapper=args.wrapper.resolve()
    reader=r/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py';rr=r/'analysis/behavior/ra_ou_20261030/audit_all_events_independent.py'
    need(sha(reader)==READER and sha(rr)==ROOT_READER,'independent reader identity mismatch')
    sys.path[:0]=[str(reader.parent),str(rr.parent)];import verify_as_run as u;import audit_all_events_independent as root_reader
    plain=r/'analysis/behavior/single_bank_1039_20261104/n8_plain/plain/simout.mat'
    p=r/'analysis/behavior/single_bank_1039_20261104/function_v2/single_bank_P.mat'
    original=r/'analysis/behavior/single_bank_1039_20261104/graph_v2/SarAdc.slx'
    for given in (args.probe_sha,args.model_sha):need(re.fullmatch(r'[a-fA-F0-9]{64}',given) is not None,'invalid pinned SHA')
    need(sha(plain)==PLAIN_SIM and sha(p)==FIXTURE_P and sha(original)==BASE_MODEL,'baseline identity differs')
    need(sha(new)==args.probe_sha.lower() and sha(model)==args.model_sha.lower() and sha(wrapper)==WRAPPER,'probe artifact identity differs')
    # Verify actual saved model plus its new wires, not just an ops proposal.
    ob,oe,oc=graph(u,original);nb,ne,nc=graph(u,model);need(oc==nc,'solver/config changed')
    need(set(ob)<=set(nb) and oe<=ne,'original blocks or edges removed')
    added=set(nb)-set(ob);need(len(added)==3,'expected exactly 3 added instrument blocks')
    by_name={nb[i][0]:i for i in added};need(set(by_name)=={'ReturnChargeProbe','ReturnAuditMux','ReturnAuditLog'},'unexpected new blocks')
    changed=[i for i in ob if ob[i]!=nb[i]]
    layout={'115','116','148','297','311'}
    need(set(changed)==layout|{'347'},'unexpected changed original blocks: '+repr(changed))
    for i in layout:
        need(ob[i][:2]==nb[i][:2],'layout block identity differs: '+i)
        a=dict(ob[i][2]);b=dict(nb[i][2]);a.pop('Position',None);b.pop('Position',None)
        need(a==b,'non-layout parameter changed: '+i)

    need(ob['347'][0:2]==nb['347'][0:2] and ob['347'][2].get('FunctionName')=='behavior_frontend_sfun' and
         nb['347'][2].get('FunctionName')=='behavior_frontend_return_probe_sfun','ChargeReturn wrapper binding differs')
    oldprops=dict(ob['347'][2]);newprops=dict(nb['347'][2]);oldprops.pop('FunctionName');newprops.pop('FunctionName')
    need(oldprops==newprops,'other ChargeReturn block parameters changed')
    port,mux,log=(by_name[x] for x in ('ReturnChargeProbe','ReturnAuditMux','ReturnAuditLog'))
    expected={('347#out:3',port+'#in:1'),('261#out:3',mux+'#in:1'),('297#out:3',mux+'#in:2'),
        ('297#out:2',mux+'#in:3'),('148#out:1',mux+'#in:4'),('232#out:3',mux+'#in:5'),
        ('297#out:5',mux+'#in:6'),('116#out:1',mux+'#in:7'),('115#out:1',mux+'#in:8'),
        (mux+'#out:1',log+'#in:1')}
    need(ne-oe==expected,'instrumented graph contains missing/unexpected new wires')
    added_edge_count=len(expected)
    need(nb[log][2].get('VariableName')=='single_return_probe_log','wrong probe logger')
    L0=u.read_logs(plain);L=u.read_logs(new);probe='single_return_probe_log'
    need(len(L0)==32 and set(L)==set(L0)|{probe},'timeseries inventory differs')
    for n in L0:
        a,b=L0[n],L[n];need(a['class']==b['class'] and a['storage_shape']==b['storage_shape'] and
            u.same(a['time'],b['time']) and u.same(a['data'],b['data']),'original timeseries changed '+n)
    r0,r1=root_reader.roots(plain),root_reader.roots(new)
    for n in r0:need(u.same(r0[n]['time'],r1[n]['time']) and u.same(r0[n]['data'],r1[n]['data']),'root changed '+n)
    t0,c0=tout(plain);t1,c1=tout(new);need(c0==c1 and u.same(t0,t1),'native tout differs')
    with h5py.File(bounded(p),'r') as f:
        v=lambda k:u.val(f,'P/'+k)
        need(v('N')==8 and v('n_cycles')==12 and v('front/single_bank')==1 and v('front/single_guard_s')==0,'unexpected single profile')
        need(np.all(np.asarray(v('front/tau_sample_s'))==0) and np.all(np.asarray(v('front/tau_precharge_s'))==0) and v('transport/enabled')==0,'expected zero tau/transport off')
        C=np.asarray(v('front/group_C_f'));epoch=int(v('epoch'))
    used=r/'analysis/behavior/single_bank_1039_20261104/n8_return/n8_run/P_used.mat'
    need(sha(used)=='7eda5f4827116e7a8a2347a24ebb013eb788719ee796f4632b8a14da46f40a5f' and
         not u.pdiff(used,p),'As-run saved P differs from the pinned fixture.')
    ev=L['event_log']['data'];te=L['event_log']['time'];pr=L[probe];D=pr['data']
    expected=np.column_stack((np.repeat(np.arange(12),48),np.tile(np.arange(1,49),12)))
    need(D.shape==(576,1457) and u.same(pr['time'],te) and np.array_equal(ev,expected),'probe/event axis/inventory mismatch')
    pre=D[:,:353];post=D[:,353:706];ctx=D[:,706:712];sampleOld=D[:,712:1065];sampleNext=D[:,1065:1418];qret=D[:,1418:1451];tags=D[:,1451:1453];source=D[:,1453:1457]
    need(u.same(tags,ev),'probe event tags differ from actual event_log')
    releases=np.flatnonzero(ctx[:,3]==2);need(len(releases)==12,'need 12 actual release contexts')
    nonrelease=np.flatnonzero(ctx[:,3]!=2);need(np.all(qret[releases,0]==1) and np.all(qret[nonrelease,0]==0) and np.all(np.isnan(qret[nonrelease,1:])),'probe release marker/sentinels differ')
    route=L['az_route_log'];back=L['back_log'];need(u.same(route['time'],te) and u.same(back['time'],te),'route/back axes differ')
    changed_numeric=0;changed_bits=0;checked=[]
    for k,row in enumerate(releases):
        ident=int(ev[row,0]);ids=qret[row,1:9].astype(int);need(np.array_equal(ids,np.arange(1,9)) and ctx[row,1]==ident and ctx[row,2]==epoch,'release IDs/tags differ')
        need(u.same(np.asarray([ctx[row,0]]),np.asarray([te[row]])) and u.same(np.asarray([pre[row,0]]),np.asarray([ctx[row,0]])) and u.same(pre[row,2:6],source[row,:]),'release pre-state/time/source mismatch')
        # POL off for this exact P; check actual context/back/route before using Vtop.
        need(u.same(np.asarray([ctx[row,5]]),np.asarray([route['data'][row,5]])) and
             u.same(np.asarray([ctx[row,5]]),np.asarray([back['data'][row,2]])),'actual Vtop route mismatch')
        B=pre[row,24:78].reshape((18,3),order='F');actual=qret[row,9:33].reshape((8,3),order='F');expectedQ=B[ids-1,:]-C[ids-1,:]*ctx[row,5]
        need(u.same(actual,expectedQ) and np.all(actual[:,2]==0),'actual intermediate q_return differs from B-C*Vtop')
        after=post[row,24:78].reshape((18,3),order='F')[ids-1,:]
        changed_numeric+=int(np.count_nonzero(after!=actual));changed_bits+=int(np.count_nonzero(after.view(np.uint64)!=actual.view(np.uint64)))
        need(np.all(post[row,6:14]==1) and np.all(post[row,168:176]==ident+1) and
             np.all(post[row,240:248]==0) and np.all(post[row,335:343]==ctx[row,0]),'post-return next acquisition tags differ')
        if k<11:
            j=row+1;need(j<len(te) and np.array_equal(ev[j],[ident+1,1]) and u.same(post[row,:],sampleOld[j,:]),'committed UnitDelay state not visible as next Sample.old')
            need(np.all(sampleNext[j,6:14]==2) and np.all(sampleNext[j,204:212]==ident+1) and
                 np.all(sampleNext[j,222:230]==epoch) and np.all(sampleNext[j,240:248]==1),'next capture tags differ')
        checked.append({'id':ident,'release_time_s':float(te[row]),'vtop_v':float(ctx[row,5]),
            'q_return_signal_C':actual[:,0].tolist(),'q_return_tail_C':actual[:,1].tolist(),
            'q_return_bias_C':actual[:,2].tolist(),'post_value_differs':int(np.count_nonzero(after!=actual))})
    print(json.dumps({'status':'return_probe_saved_artifacts_checked','instrumented_model_sha256':sha(model),
        'plain_simout_sha256':sha(plain),'probe_simout_sha256':sha(new),'wrapper_sha256':sha(wrapper),
        'P_sha256':sha(p),'P_used_sha256':sha(used),'original_timeseries_equal':len(L0),'tout_bit_equal':True,'root_ports_bit_equal':sorted(r0),
        'graph_added_blocks':by_name,'graph_added_wires':added_edge_count,'position_only_sids':sorted(layout),'event_rows':len(te),'actual_release_rows':len(checked),
        'next_sample_old_matches_prior_post':11,'post_vs_return_numeric_difference_count':changed_numeric,
        'post_vs_return_bit_difference_count':changed_bits,'release_details':checked,
        'scope':'guard=0 and tau_sample=0: actual same-call intermediate q_return and next-owner continuity; post has immediate reacquisition and may differ. No retained-charge sensitivity, PVT, silicon or full paper-reproduction claim.'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
