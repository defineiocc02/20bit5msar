#!/usr/bin/env python3
"""Read-only high/low coherent N256 actual-code, source and permutation audit."""
import hashlib,json,math
from pathlib import Path
import h5py
import numpy as np
from verify_as_run import at,need,pdiff,read_logs,same,sha,val
from verify_n256_three import audit

root=Path(__file__).resolve().parents[3];runs=root/'runs';job=runs/'az_probe_20261028T103904Z'
receipt=json.loads((job/'receipt.json').read_text())
need(receipt['status']=='actual_pair_complete_pending_independent_review' and receipt['stage']=='finished',
     'Pair job receipt not complete')
cases=[('high_off',runs/'behavior_a821241e-39dd-4709-b141-dd47975bc0c7',0.,False),
       ('high_1ns',runs/'behavior_1ad89a39-949a-4ea0-bf59-78f15257032a',1e-9,True),
       ('low_off',runs/'behavior_59a2b584-fa64-48ef-8608-80ce71bbf10b',0.,False),
       ('low_1ns',runs/'behavior_47c22b65-fdff-402b-b315-ea0599df6891',1e-9,True)]
checked={};held={};allrx={}
for label,folder,tau,en in cases:
    result,pins,codes,raw,edges,solver=audit(label,folder,tau,en)
    L=read_logs(folder/'simout.mat');event=L['event_log'];ev=event['data'];et=event['time']
    ids=np.arange(4,260);ix=np.flatnonzero((ev[:,1]==1)&(ev[:,0]>=4)&(ev[:,0]<260))
    need(len(ix)==256 and np.array_equal(ev[ix,0],ids),'Actual CNV IDs missing or out of order')
    held[label]=at(L['front_log'],et[ix],'actual FrontLog CNV')[:,0]
    ready=L['record_ready_log'];flag=ready['data'][:,0];need(np.all(np.isin(flag,[0,1])),'Invalid ready flag')
    rt=ready['time'][flag==1];r=at(L['record_log'],rt,'record');c=at(L['code_log'],rt,'code')[:,0]
    need(r.shape==(260,6) and np.array_equal(r[:,3],np.arange(260)) and np.all(r[:,4]==1) and
         np.all(r[:,5]==1) and np.all(np.isfinite(r)),'Full observed RX sequence/valid/tags differs')
    e=at(event,rt,'RX event');need(np.array_equal(e[:,0],r[:,3]+2) and np.all(e[:,1]==49),
                                     'Actual RX ready is not N-2 parent group49')
    aq=L['ready_log'];aqt=aq['time'][aq['data'][:,0]==1];ar=at(L['raw_log'],aqt,'ADC RAW')
    for row in r:
        hit=np.flatnonzero((ar[:,3]==row[3])&(ar[:,4]==row[4]))
        need(len(hit)==1 and same(ar[hit[0]],row),'Full RX/ADC RAW6 mismatch')
    with h5py.File(folder/'parameters.mat','r') as f:
        plan=np.asarray(val(f,'P/front/plan'));tau_sample=np.asarray(val(f,'P/front/tau_sample_s')).ravel()
        aperture=bool(val(f,'P/front/jitter/enabled'));need(np.all(tau_sample==0) and not aperture,
             'Expected ideal sample settling / no aperture jitter')
    checked[label]={'result':result,'pins':pins,'codes':codes,'raw':raw,'edges':edges,
                    'solver':solver,'plan':plan}
    allrx[label]={'count':len(r),'valid_1':int(np.count_nonzero(r[:,5]==1)),
                  'valid_0':int(np.count_nonzero(r[:,5]==0)),'ids':[0,259],'epoch':1,
                  'all_ADC_to_RX_RAW6_same':True,'RX_group49_ID_plus_2':True}

for c,label in zip(receipt['cases'],['high_off','high_1ns']):
    folder=next(x[1] for x in cases if x[0]==label)
    for key,filename in {'SarAdc_slx':'SarAdc.slx','parameters_mat':'parameters.mat',
                         'source_zip':'source.zip','source_manifest_json':'source_manifest.json',
                         'simout_mat':'simout.mat','selected_mat':'selected.mat',
                         'spectrum_mat':'spectrum.mat','summary_json':'summary.json'}.items():
        need(sha(folder/filename)==c['as_run'][key],'Job as-run SHA mismatch: '+label+'/'+filename)
    need(c['observed_ready_count']==260 and c['observed_valid1']==260 and c['observed_valid0']==0 and
         c['observed_valid_unknown']==0 and c['selected_count']==256,'Job ready/valid count mismatch')
    need(checked[label]['result']['settings']['fin_hz']==996093.75 and
         checked[label]['result']['fundamental_bin']==51,'High-frequency actual input/bin mismatch')
    need(checked[label]['result']['sha256']['simout.mat']==c['simout_sha256'],'Job simout SHA mismatch')

base=checked['high_off'];need(all(x['pins']==base['pins'] for x in checked.values()),
                                '87 as-run source files differ')
need(all(np.array_equal(x['plan'],base['plan']) for x in checked.values()),'Public slice plan differs')
need(all(x['edges']==base['edges'] and x['solver']==base['solver'] for x in checked.values()),
     'As-run graph edges/solver differs')
high_diff=pdiff(cases[0][1]/'parameters.mat',cases[1][1]/'parameters.mat')
expected={'P/backend/dac_coupling/enabled','P/backend/dac_coupling/tau_dac_s',
          'P/front/tau_dac_s','P/ni/dac_settling'}
need(set(high_diff)==expected,'Unexpected within-high-frequency P differences: '+repr(high_diff))
permutation={};n=256;a=215;b=88;ainv=pow(a,-1,n);idx=(a*np.arange(n)+b)%n
need((a*5)%n==51 and math.gcd(a,n)==1 and ainv==231,'Incorrect coherent permutation')
for tail,lowpath,highpath in [('off',cases[2][1],cases[0][1]),('1ns',cases[3][1],cases[1][1])]:
    lo=checked['low_'+tail];hi=checked['high_'+tail]
    need(lo['result']['settings']['fin_hz']==97656.25 and lo['result']['fundamental_bin']==5,
         'Low-frequency actual input/bin mismatch')
    low=lo['codes'];high=hi['codes'];need(np.array_equal(high,low[idx]) and
         np.array_equal(hi['raw'][:,:3],lo['raw'][idx,:3]),'Actual code/RAW is not the asserted permutation')
    need(np.array_equal(np.sort(high),np.sort(low)),'Sorted code multiset mismatch')
    diffs=pdiff(lowpath/'parameters.mat',highpath/'parameters.mat')
    need(set(diffs)=={'P/input/frequency_hz','P/front/input/frequency_hz','P/xFE0'},
         'Unexpected high/low same-tau P differences: '+repr(diffs))
    fsr=8.192
    lv=((low+.5)/2**20-.5)*fsr;hv=((high+.5)/2**20-.5)*fsr
    LF=np.fft.fft(lv-lv.mean())/n;HF=np.fft.fft(hv-hv.mean())/n
    remap=(ainv*np.arange(n))%n
    power_delta=float(np.max(np.abs(np.abs(HF)**2-np.abs(LF[remap])**2)))
    high_harm=hi['result']['harmonic_bins_H2_to_H10']
    low_harm=lo['result']['harmonic_bins_H2_to_H10']
    mapped=[min((ainv*k)%n,n-(ainv*k)%n) for k in high_harm]
    need(sorted(mapped)==sorted(low_harm),'H2-H10 bins do not map under actual permutation')
    hvdiff=held['high_'+tail]-held['low_'+tail][idx]
    permutation[tail]={'actual_code_and_RAW3_match_affine_permutation':256,'unique_code_count':len(np.unique(low)),
        'direct_same_index_code_differences':int(np.count_nonzero(high!=low)),
        'low_code_binary64_le_sha256':hashlib.sha256(np.asarray(low,dtype='<f8').tobytes()).hexdigest(),
        'high_code_binary64_le_sha256':hashlib.sha256(np.asarray(high,dtype='<f8').tobytes()).hexdigest(),
        'sorted_code_binary64_le_sha256':hashlib.sha256(np.sort(low).astype('<f8').tobytes()).hexdigest(),
        'same_tau_high_vs_low_saved_P_differences':diffs,
        'actual_sampled_held_max_abs_permuted_difference_V':float(np.max(np.abs(hvdiff))),
        'actual_sampled_held_exact_equal_count':int(np.count_nonzero(hvdiff==0)),
        'two_sided_power_max_abs_remapped_difference_V2':power_delta,
        'low_H2_H10_bins':low_harm,'high_H2_H10_bins':high_harm,
        'high_bins_mapped_to_low':sorted(mapped)}

report={'schema':'sar20-highfreq-N256-pair-independent/v1','verifier_sha256':sha(Path(__file__).resolve()),
        'job_receipt_sha256':sha(job/'receipt.json'),'as_run_87_source_file_hashes_same':True,
        'native_edges_solver_and_public_plan_same':True,'high_pair_P_differences':high_diff,
        'cases':{k:v['result'] for k,v in checked.items()},'full_observed_RX':allrx,
        'affine_permutation':{'j_low':'(215*j_high+88) mod 256, j=0 corresponds to ID4',
            'DFT_power_index':'k_low=(231*k_high) mod 256',
            'reason':'51=215*5 mod256 and 215 has inverse 231; the phase grids are reindexed, '
                     'with an ID4 phase offset accounted for by +88.',
            'cases':permutation},
        'scope':'Actual four N256 behavioral runs. Sorted equality alone is insufficient to imply equal spectrum; '
                'the observed affine order and harmonic bin remapping explain this pair. Sampled held values are '
                'not bit-identical under the mapping; no continuous analog state or general frequency invariance is proven. '
                'Sampling RC/jitter and other stated NI are off; 996093.75 Hz is not exactly 1 MHz or PDK/silicon signoff.'}
print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
