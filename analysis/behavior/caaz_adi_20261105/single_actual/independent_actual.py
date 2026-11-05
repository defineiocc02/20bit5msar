#!/usr/bin/env python3
"""Independent read-only audit of saved single-bank CICC/CAAZ N8. No MATLAB."""
from pathlib import Path
import csv, hashlib, importlib.util, json, math
import h5py
import numpy as np

ROOT=Path('/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020')
RUN=ROOT/'analysis/behavior/caaz_adi_20261105/single_actual'
OLD=ROOT/'analysis/behavior/normal_workpoint_20261104/windows_main_actual/normal_merged_n8'
GRAPH=ROOT/'analysis/behavior/caaz_adi_20261105/graph_build/demod_graph.slx'
SCRATCH=Path('/Users/zhaoyi/Obsidan/项目库临时文件夹/sar20_pku_integration_20261105.oa3b3aj4')
READER=ROOT/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
OUT=RUN/'independent_actual.json'
MAX=300_000_000

def need(x,msg):
    if not x:raise ValueError(msg)
def safe(p):
    p=Path(p);need(p.is_file() and not p.is_symlink() and p.stat().st_size<=MAX,f'unsafe/oversized {p}');return p
def sha(p):
    p=safe(p);h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def jread(p):return json.loads(safe(p).read_text(encoding='utf-8-sig'))
def csvread(p):
    with safe(p).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def same(a,b):
    a=np.asarray(a);b=np.asarray(b);return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()
def scalar(h,path):
    a=np.asarray(h[path][()]);need(a.size==1,f'non-scalar {path}');return a.ravel()[0].item()
def text(h,path):return ''.join(chr(int(q)) for q in np.asarray(h[path][()]).ravel())
def assert_csv_float(a,b,label):
    # writetable serializes limited decimal digits: compare to its stated precision,
    # never treat this as a model tolerance or a floating-point bit equality.
    need(math.isclose(float(a),float(b),rel_tol=3e-14,abs_tol=1e-18),f'CSV mismatch {label}')
def round_away(x):
    frac,whole=math.modf(x);return int(whole)+(1 if frac>=.5 else -1 if frac<=-.5 else 0)
def digital(h):
    g=h['P/digital'];q=lambda k:np.asarray(g[k][()]).ravel()
    v={'vref':float(q('vref_v')[0]),'fsr':float(q('fsr_diff_v')[0]),'gain':float(q('ra_gain')[0]),
       'bias':float(q('d1_bias_v')[0]),'weights':[float(x) for x in q('d2_weights_ra_v')],
       'offset':float(q('d2_offset_ra_v')[0]),'tracking':float(q('tracking_step_ra_v')[0]),
       'mode':text(h,'P/digital/az_mode')}
    need((v['vref'],v['fsr'],v['gain'],v['bias'])==(5.,10.,32.,0.) and len(v['weights'])==12,'unexpected DecodeP')
    need(not scalar(h,'P/digital/dither_enabled') and text(h,'P/digital/calibration_mode')=='off','dither/calibration active')
    return v
def reconstruct(row,d,chop):
    d1,d2,dt,id,epoch,valid=map(int,row);need(valid==1,'invalid actual row')
    b2=[(d2>>k)&1 for k in range(11,-1,-1)];bt=[(dt>>k)&1 for k in range(7,-1,-1)]
    v1=(2*d1-32*(d1//32)-1039)*(d['vref']/1024)+d['bias']
    v2=(sum(weight*bit for weight,bit in zip(d['weights'],b2))+d['offset'])/d['gain']
    stat=2*sum((8-k)*bit for k,bit in enumerate(bt))-36
    vt=stat*(d['tracking']/(8*d['gain']));pre=(v1+v2)+vt
    pol=1-2*(id%2) if chop else 1;v=pre if pol==1 else -pre
    u=v*(2**20/d['fsr'])+2**19;code=max(0,min(2**20-1,round_away(u)))
    return {'D1_v':v1,'D2_v':v2,'DT_v':vt,'CT_v':v2+vt,'pre_demod_v':pre,'input_pol':pol,'demod_v':v,
            'unrounded_code20':u,'independent_code20':code,'signed_code20':code-2**19}

def main():
    need(not OUT.exists(),'refuse to overwrite independent evidence')
    for p in [READER,GRAPH,OLD/'P_used.mat',OLD/'simout.mat',SCRATCH/'INTEGRATION_MANIFEST.json',SCRATCH/'audit_delta/CASE_MANIFEST.json',SCRATCH/'audit_delta/graph_receipt.json']:
        safe(p)
    spec=importlib.util.spec_from_file_location('verify_as_run',READER);u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
    integ=jread(SCRATCH/'INTEGRATION_MANIFEST.json');case=jread(SCRATCH/'audit_delta/CASE_MANIFEST.json');graph=jread(SCRATCH/'audit_delta/graph_receipt.json')
    need(sha(SCRATCH/'INTEGRATION_MANIFEST.json')==case['integration_manifest_sha256']==graph['input_manifest_sha256'],'integration identity mismatch')
    need(sha(SCRATCH/'audit_delta/graph_receipt.json')==case['graph_receipt_sha256'] and sha(GRAPH)==case['model_sha256']==graph['model_sha256'],'graph identity mismatch')
    need(sha(OLD/'P_used.mat')==case['reference_P_sha256'] and sha(OLD/'simout.mat')==case['reference_simout_sha256'],'old baseline identity mismatch')
    for e in case['source_files']:
        p=SCRATCH/'candidate'/e['path'];need(sha(p)==e['sha256'],f'candidate source changed: {e["path"]}')
    oldlogs=u.read_logs(OLD/'simout.mat');all_results={};newlogs={};savedP={}
    for name in ('cicc','caaz'):
        d=RUN/name;r=jread(d/'complete.json')
        need(r['status']=='N8_RAW_SIGNED_AZ_PASS' and r['profile']==name and r['manifest_sha256']==sha(SCRATCH/'audit_delta/CASE_MANIFEST.json') and r['model_sha256']==case['model_sha256'],'receipt identity')
        files={}
        for fn,key in [('P_used.mat','P_used_sha256'),('simout.mat','simout_sha256'),('checks.mat','checks_sha256')]:
            actual=sha(d/fn);need(actual==r[key],f'{name} {fn} hash mismatch');files[fn]=actual
        for fn in ['raw_signed_code.csv','input_actual_held.csv','az_actual_state.csv','complete.json']:
            files[fn]=sha(d/fn)
        L=u.read_logs(d/'simout.mat');newlogs[name]=L
        for x in ['event_log','front_log','record_log','record_ready_log','code_log','az_commit_log','pku_ra_old48','pku_ra_next48']:
            need(x in L and same(L[x]['time'],L['event_log']['time']),f'{name} axis {x}')
        event=L['event_log']['data'];old=L['pku_ra_old48']['data'];nxt=L['pku_ra_next48']['data'];az=L['az_commit_log']['data']
        need(event.shape==(576,2) and old.shape==nxt.shape==(576,48) and az.shape==(576,8),f'{name} shapes')
        need(np.array_equal(event,np.column_stack([np.repeat(np.arange(12),48),np.tile(np.arange(1,49),12)])),f'{name} event order')
        need(same(old[1:],nxt[:-1]),f'{name} RA delay mismatch')
        need(same(az[:,0],nxt[:,2]-nxt[:,3]) and same(az[:,1:],nxt[:,[37,38,39,40,41,42,47]]),f'{name} az next mapping')
        with h5py.File(d/'P_used.mat','r') as p:
            need(scalar(p,'P/N')==8 and scalar(p,'P/Ts_s')==200e-9 and scalar(p,'P/first_id')==4 and scalar(p,'P/epoch')==1,'N8 P invalid')
            need(bool(scalar(p,'P/front/single_bank')) and not bool(scalar(p,'P/backend/ni/az_noise')),'bank/az noise')
            need(bool(scalar(p,'P/backend/ni/ra_noise')) and bool(scalar(p,'P/front/ktc_enabled')),'normal OU/kTC disabled')
            need(not bool(scalar(p,'P/debug/adi_enabled')),'wire tap changed P')
            dg=digital(p);mode=text(p,'P/backend/az/mode');
            need(mode==dg['mode']==('ordinary' if name=='cicc' else 'pku_input_hold_chop_v1'),'mode join')
            if name=='caaz':need(text(p,'P/front/input_chop_mode')==mode,'front mode join')
            elif 'input_chop_mode' in p['P/front']:raise ValueError('legacy P gained input chop field')
            x0=np.asarray(p['P/xBK0'][()]).ravel();need(same(old[0,:],x0),'initial state mismatch')
            times,groups,budget=u.read_calendar(p)
            ra=[i+1 for i,g in enumerate(groups) if 'ra_start' in g];cn=[i+1 for i,g in enumerate(groups) if 'cnv' in g]
            need(len(ra)==len(cn)==1,'ambiguous RA start/CNV')
            first=int(scalar(p,'P/first_id'));N=int(scalar(p,'P/N'));epoch=int(scalar(p,'P/epoch'))
            savedP[name]={'mode':mode,'digital':dg,'N':N,'first_id':first,'epoch':epoch,'az_noise_enabled':False,
                          'ra_ou_enabled':True,'ktc_enabled':True,'single_bank':True,'adc_groups':len(groups),'calendar_counts':budget}
        ready=L['record_ready_log'];rt=ready['time'][ready['data'][:,0]==1];raw=u.at(L['record_log'],rt,'record');code=u.at(L['code_log'],rt,'code')[:,0]
        selection=(raw[:,3]>=first)&(raw[:,3]<first+N);raw=raw[selection];code=code[selection];rt=rt[selection]
        need(raw.shape==(8,6) and np.array_equal(raw[:,3],np.arange(4,12)) and np.all(raw[:,4]==epoch) and np.all(raw[:,5]==1),f'{name} RAW6')
        rows=csvread(d/'raw_signed_code.csv');need(len(rows)==8,f'{name} RAW CSV length')
        computed=[]
        for i,(row,w,c,t) in enumerate(zip(rows,raw,code,rt)):
            expected=[int(row[k]) for k in ['raw_D1','raw_D2','raw_DT','sample_id','epoch','valid']]
            need(expected==list(map(int,w)),f'{name} CSV/actual RAW mismatch row {i}')
            decoded=reconstruct(w,dg,name=='caaz');need(decoded['independent_code20']==int(c)==int(row['actual_code20'])==int(row['independent_code20']),f'{name} actual code mismatch row {i}')
            need(decoded['input_pol']==int(row['input_pol']) and decoded['signed_code20']==int(row['signed_code20']),f'{name} sign mismatch row {i}')
            assert_csv_float(row['nominal_voltage_v'],decoded['demod_v'],f'{name} nominal voltage {i}')
            computed.append(decoded)
        cnrows=event[:,1]==cn[0];cnids=event[cnrows,0];front=L['front_log']['data'][cnrows,0];cnT=L['event_log']['time'][cnrows];inputcsv=csvread(d/'input_actual_held.csv');need(len(inputcsv)==12,'input CSV length')
        for i,row in enumerate(inputcsv):
            need(int(row['sample_id'])==int(cnids[i]) and int(row['input_pol'])==(1-2*(i%2) if name=='caaz' else 1),'input CSV ID/POL')
            assert_csv_float(row['cnv_time_s'],cnT[i],'CNV time');assert_csv_float(row['actual_FE_held_v'],front[i],'FE held')
        route=event[:,1]==ra[0];rs=nxt[route];ids=event[route,0];azcsv=csvread(d/'az_actual_state.csv');need(len(azcsv)==12,'AZ CSV length')
        expectedCount=np.floor(ids/2)+1 if name=='caaz' else ids+1
        expectedLast=ids-(ids%2) if name=='caaz' else ids
        need(np.all(rs[:,37]==1) and np.array_equal(rs[:,38],np.floor(ids/2)) and np.all(rs[:,39]==epoch) and np.all(rs[:,41]==0) and np.array_equal(rs[:,42],expectedCount) and np.array_equal(rs[:,43],expectedLast),'AZ state/pair/write count')
        for i,row in enumerate(azcsv):
            need(int(row['sample_id'])==int(ids[i]) and int(row['write_count'])==int(rs[i,42]) and int(row['pair_id'])==int(rs[i,38]) and int(row['last_write_id'])==int(rs[i,43]),'AZ CSV tags')
            assert_csv_float(row['az_half_p_v'],rs[i,2],'AZ half P');assert_csv_float(row['az_half_n_v'],rs[i,3],'AZ half N')
        index5=int(np.flatnonzero(raw[:,3]==5)[0]);r5=raw[index5].astype(int)
        all_results[name]={'pid':r['pid'],'elapsed_sim_s':r['sim_s'],'files_sha256':files,'actual_log_count':len(L),
          'records':8,'record_ids':[int(x) for x in raw[:,3]],'record_time_s':[float(x) for x in rt],
          'input_polarity':[int(x['input_pol']) for x in computed],'ra_next_old_bit_pairs':575,'AZ_write_count_at_ra_start':[int(x) for x in rs[:,42]],
          'sample5':{'raw_D1':int(r5[0]),'raw_D2':int(r5[1]),'raw_DT':int(r5[2]),'sample_id':5,'epoch':int(r5[4]),'valid':int(r5[5]),'ready_time_s':float(rt[index5]),'actual_code20':int(code[index5]),**computed[index5],
                     'actual_FE_held_v':float(front[5]),'actual_az_half_p_v':float(rs[5,2]),'actual_az_half_n_v':float(rs[5,3]),'AZ_pair_id':int(rs[5,38]),'AZ_write_count':int(rs[5,42]),'last_AZ_write_id':int(rs[5,43]),'AZ_age_s':float(rs[5,40])}}
    a=newlogs['cicc'];need(set(a)-{'pku_ra_old48','pku_ra_next48'}==set(oldlogs),'CICC log inventory differs from old')
    for name in oldlogs:need(same(a[name]['time'],oldlogs[name]['time']) and same(a[name]['data'],oldlogs[name]['data']),f'CICC old log bits differ: {name}')
    need(u.pdiff(RUN/'cicc/P_used.mat',OLD/'P_used.mat')==[],'CICC full P differs')
    differences=u.pdiff(RUN/'caaz/P_used.mat',RUN/'cicc/P_used.mat');expected=['P/backend/az/mode','P/cal_cfg/public_cfg/az_mode','P/digital/az_mode','P/front/input_chop_mode'];need(differences==expected,f'Unexpected CAAZ P changes: {differences}')
    need(same(newlogs['cicc']['event_log']['time'],newlogs['caaz']['event_log']['time']),'case event times differ')
    result={'status':'INDEPENDENT_N8_AUDIT_PASS','audit_script_sha256':sha(Path(__file__)),'MCOS_reader_sha256':sha(READER),
       'case_manifest_sha256':sha(SCRATCH/'audit_delta/CASE_MANIFEST.json'),'graph_receipt_sha256':sha(SCRATCH/'audit_delta/graph_receipt.json'),'model_sha256':sha(GRAPH),
       'baseline_P_sha256':sha(OLD/'P_used.mat'),'baseline_simout_sha256':sha(OLD/'simout.mat'),
       'cicc_P_vs_actual_N8':'recursive exact dtype/shape/numeric bits, no differing fields','caaz_P_changed_fields':differences,
       'cicc_original_named_logs_exact_count':len(oldlogs),'three_root_ports':'MATLAB native baseline comparison reports PASS; this independent HDF reader does not parse yout',
       'cases':all_results,'limits':['single physical bank; ADI not run','AZ random write noise OFF in both runs; no 4.3 dB or CAAZ noise-benefit claim','CSV floating values checked at export precision; code20 independently reproduced for these rows, not float-operation bit equivalence','FE held minus nominal signal includes RC, history, and sampling noise; it is not standalone kTC'],
       'scope':'actual saved behavior N8 data, not silicon/PEX or production qualification'}
    with OUT.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print('PASS',OUT,'SHA256',sha(OUT),'logs',len(oldlogs),'caaz_sample5',result['cases']['caaz']['sample5'])
if __name__=='__main__':main()
