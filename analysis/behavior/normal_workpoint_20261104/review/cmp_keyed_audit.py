#!/usr/bin/env python3
"""Independent normal N8 SAR2/TA decision audit; never run a model.

Reads explicitly SHA-pinned P, actual Simulink SimulationOutput and the
as-run graph/source snapshot. It never reads training/holdout records or
reconstructs an RA state. The only random calculation is an independent
Python SHA-256/Box-Muller reproduction of the declared comparator event key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zipfile
import xml.etree.ElementTree as ET

import h5py
import numpy as np

MAX_BYTES=300_000_000
SOURCE_PINS={
    'control/behavior_control_stage.m':'a80afa99e69112b325932bedecb4f554cabbcf32df26865c096bfbf0609d9429',
    'control/behavior_control_stage_sfun.m':'82ce9f15147e1c85661a71ae38d71f5ec0738b79c80652402df704ba49ddcc63',
    'control/behavior_sar_step.m':'61e74af8e5b7f07eff48fd53084c50d3ae6e420b133fd82297f14d328ac74a68',
    'control/behavior_comparator_sample.m':'d4807bb6674660cc60f83f35879ecce792659ba21302623184291fbb114ccbda',
    'control/behavior_comparator_keyed_normal.m':'564c41d9b814f312871a008eb53c2f62231ef617135302141ae4df591be70082',
    'analysis/behavior_adi_tap_sfun.m':'b2445f9d049d70985c382f47fdbdbca3cbb4cee276b8e473c2b87e88398b3164',
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def hash_file(path):
    path=Path(path)
    need(path.is_file() and path.stat().st_size<MAX_BYTES, f'missing or oversized: {path}')
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def verify_pin(path, expected, label):
    need(len(expected)==64 and all(c in '0123456789abcdef' for c in expected.lower()),
         f'{label} requires explicit SHA-256')
    actual=hash_file(path)
    need(actual==expected.lower(),f'{label} hash mismatch: {actual}')
    return actual


def no_holdout(path):
    p=Path(path)
    need(not any('holdout' in part.lower() for q in (p,p.resolve()) for part in q.parts),
         f'holdout path is out of scope: {path}')


def scalar(h, path):
    need(path in h and isinstance(h[path],h5py.Dataset),f'missing numeric field: {path}')
    a=np.asarray(h[path][()])
    need(a.size==1,f'non-scalar field: {path}')
    return a.ravel()[0].item()


def binary(h,path):
    v=scalar(h,path)
    need(v in (0,1),f'non-binary field: {path}')
    return bool(v)


def char_dataset(ds):
    a=np.asarray(ds[()]).ravel()
    return ''.join(chr(int(x)) for x in a)


def event_field(h, group, key):
    ds=group[key];values=np.asarray(ds[()]).ravel()
    if h5py.check_dtype(ref=ds.dtype) is not None:
        out=[]
        for ref in values:
            need(bool(ref),f'null event ref: {key}')
            x=h[ref]
            if key=='type':
                out.append(char_dataset(x))
            else:
                a=np.asarray(x[()]).ravel()
                need(a.size==1,f'non-scalar event field: {key}')
                out.append(float(a[0]))
        return out
    if key=='type':
        return [char_dataset(ds)]
    return [float(x) for x in values]


def load_parameters(path):
    with h5py.File(path,'r') as h:
        need('P' in h and isinstance(h['P'],h5py.Group),'P must be a MATLAB v7.3 struct')
        p='P/'
        need(scalar(h,p+'N')==8 and scalar(h,p+'Ts_s')==200e-9,'expected 5MS/s N8')
        need(binary(h,p+'front/single_bank') and not binary(h,p+'transport/enabled'),
             'expected single-bank direct RAW')
        need(not binary(h,p+'front/dem_enabled') and not binary(h,p+'front/dither_enabled'),
             'physical ADI DEM/dither must be OFF')
        for name in ['training','cal_cfg','frozen','bank']:
            need(not binary(h,p+name+'/enabled'),f'{name} must be OFF; no holdout/calibration')
        need(binary(h,p+'debug/adi_enabled'),'actual 58-word read-only observer is required')
        c=p+'control/comparator/'
        need(binary(h,c+'enabled'),'comparator profile is disabled')
        sigma=float(scalar(h,c+'sar2_noise_rms_v'))
        offset=float(scalar(h,c+'sar2_offset_v'))
        seed=int(scalar(h,c+'seed_u64'))
        tie=binary(h,c+'tie_decision')
        need(math.isfinite(sigma) and sigma>0 and math.isfinite(offset),'SAR2/TA sigma/offset invalid')
        need(0<=seed<2**64,'seed not uint64')
        epoch=int(scalar(h,p+'epoch'));first=int(scalar(h,p+'first_id'))
        cycles=int(scalar(h,p+'n_cycles'));period=float(scalar(h,p+'Ts_s'))
        need(0<=epoch<2**32 and first>=0 and cycles>=first+8,'invalid epoch/record window')
        need(binary(h,p+'ni/comparator_noise') and
             binary(h,p+'ni/comparator_noise_scope/sar2_and_tracking') and
             not binary(h,p+'ni/comparator_noise_scope/flash_preconvert'),
             'CMP coverage summary inconsistent')
        groups=h[p+'groups'];refs=np.asarray(groups['events'][()]).ravel()
        times=np.asarray(groups['time_s'][()]).ravel()
        need(len(refs)==len(times)==48,'expected 48 ADC groups')
        result=[]
        for ref,tref in zip(refs,times):
            ev=h[ref];names=event_field(h,ev,'type')
            indices=event_field(h,ev,'index');bits=event_field(h,ev,'bit')
            need(len(names)==len(indices)==len(bits),'event struct field length mismatch')
            events=[]
            for name,index,bit in zip(names,indices,bits):
                need(index==math.floor(index) and bit==math.floor(bit),'noninteger event index/bit')
                events.append({'type':name,'index':int(index),'bit':int(bit)})
            time=float(np.asarray(h[tref][()]).ravel()[0])
            result.append({'time_s':time,'events':events})
    counts={kind:sum(e['type']==kind for g in result for e in g['events'])
            for kind in ['d2_decide','d2_feedback','ta_compare','ta_feedback','raw_latch']}
    need(counts=={'d2_decide':12,'d2_feedback':12,'ta_compare':8,
                  'ta_feedback':7,'raw_latch':1},f'not M8 event calendar: {counts}')
    need(all(result[i]['time_s']<result[i+1]['time_s'] for i in range(47)),
         'calendar group times not strictly increasing')
    for name,count,width in [('d2_decide',12,12),('d2_feedback',12,12),
                             ('ta_compare',8,8),('ta_feedback',7,8)]:
        ev=[e for g in result for e in g['events'] if e['type']==name]
        need([e['index'] for e in ev]==list(range(count)) and
             all(e['bit']==width-1-e['index'] for e in ev),
             f'{name} indices or bit order differ from the declared M8 calendar')
    return {'sigma_vy_v':sigma,'offset_vy_v':offset,'seed_u64':seed,'tie_decision':int(tie),
            'epoch':epoch,'first_id':first,'N':8,'cycles':cycles,'period_s':period,
            'groups':result,'scheduled_counts':counts}


def read_logs(path):
    """Decode the checked archived R2024a MCOS timeseries layout; fail closed."""
    with h5py.File(path,'r') as h:
        need('#subsystem#/MCOS' in h,'unsupported SimulationOutput MCOS layout')
        seq=[h[r] for r in np.asarray(h['#subsystem#/MCOS'][()]).ravel()]
        candidates=[x for x in seq if isinstance(x,h5py.Group) and {'raw_log','event_log'}<=set(x)]
        need(len(candidates)==1,'ambiguous SimulationOutput')
        s=candidates[0]
        name_inventory=[n for n in s if n not in ('tout','yout')]
        need(not any('holdout' in n.lower() for n in name_inventory),
             'SimulationOutput contains a holdout-named log')
        try:
            names=[n for _,n in sorted((int(np.asarray(s[n][()]).ravel()[4]),n)
                                       for n in name_inventory)]
        except (IndexError,ValueError,TypeError) as err:
            raise ValueError('unsupported SimulationOutput logger index') from err
        descriptors=[]
        for i,d in enumerate(seq):
            if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:
                continue
            ns,t=seq[i-11],seq[i-9]
            if not (isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1)
                    and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):
                continue
            count=int(np.asarray(ns[()]).item())
            if count>0 and t.shape==(1,count) and (count==1 or d.shape[-1]==count):
                descriptors.append((t,d,count))
        need(len(names)==len(descriptors) and len(names)==len(set(names)),
             f'unsupported logger layout: {len(names)} names/{len(descriptors)} arrays')
        required={'event_log','back_log','control_log','raw_log','ready_log','adi_wire_log'}
        need(required<=set(names),'missing required normal N8 log')
        result={}
        for name,(t,d,count) in zip(names,descriptors):
            if name not in required:continue
            a=np.asarray(d[()]);time=np.asarray(t[()]).T[:,0]
            need(np.all(np.isfinite(time)) and np.all(np.diff(time)>=0),'invalid actual logger times')
            result[name]={'time':time,'data':a.reshape((-1,count)).T,
                          'class':str(d.attrs.get('MATLAB_class',b''))}
        return result


def graph_info(path):
    required={
        'simulink/systems/system_105.xml':[
            ('112#out:4','134#in:1'),('112#out:5','135#in:1'),
            ('112#out:1','131#in:1'),('112#out:2','132#in:1'),('109#out:1','136#in:1')],
        'simulink/systems/system_112.xml':[
            ('261#out:5','120#in:1'),('261#out:5','279#in:2'),
            ('279#out:1','285#in:4'),('285#out:3','312#in:8'),('261#out:2','312#in:5')],
        'simulink/systems/system_279.xml':[
            ('283#out:1','343#in:1'),('343#out:1','339#in:3'),('339#out:1','284#in:1')],
        'simulink/systems/system_285.xml':[
            ('291#out:1','346#in:4'),('346#out:2','345#in:1'),('345#out:1','295#in:1')],
        'simulink/systems/system_312.xml':[
            ('368#out:1','369#in:3'),('319#out:1','369#in:4'),('369#out:1','370#in:1')],
    }
    block_require={
        'simulink/systems/system_105.xml':{'131':('ToWorkspace','raw_log'),'132':('ToWorkspace','ready_log'),'134':('ToWorkspace','back_log'),
                                           '135':('ToWorkspace','control_log'),'136':('ToWorkspace','event_log')},
        'simulink/systems/system_279.xml':{'343':('Selector','2')},
        'simulink/systems/system_285.xml':{'346':('M-S-Function','behavior_control_stage_sfun')},
        'simulink/systems/system_312.xml':{'369':('M-S-Function','behavior_adi_tap_sfun'),
                                           '370':('ToWorkspace','adi_wire_log')},
    }
    graph_hashes={}
    with zipfile.ZipFile(path) as z:
        for name,edges in required.items():
            info=z.getinfo(name);need(info.file_size<MAX_BYTES,'oversized SLX XML member')
            data=z.read(info);graph_hashes[name]=hashlib.sha256(data).hexdigest()
            x=ET.fromstring(data);blocks={b.get('SID'):b for b in x.findall('Block')}
            actual=set()
            for line in x.findall('Line'):
                src=line.find("P[@Name='Src']")
                if src is not None:
                    actual.update((src.text,d.text) for d in line.iter('P') if d.get('Name')=='Dst')
            need(set(edges)<=actual,f'graph route mismatch in {name}')
            for sid,(typ,want) in block_require.get(name,{}).items():
                need(sid in blocks and blocks[sid].get('BlockType')==typ,f'graph block mismatch: {sid}')
                vals={p.get('Name'):p.text for p in blocks[sid].findall('P')}
                key={'ToWorkspace':'VariableName','Selector':'Indices','M-S-Function':'FunctionName'}[typ]
                need(vals.get(key)==want,f'graph block parameter mismatch: {sid}')
                if sid=='346':
                    need(vals.get('Parameters', '').replace(' ','')=="'decide',P",'wrong decision stage binding')
    return graph_hashes


def cmp_draw(seed,epoch,sample,event_code,event_index):
    words=(seed,epoch,sample,event_code,event_index)
    need(all(isinstance(v,int) and 0<=v<2**64 for v in words),'key word out of range')
    payload=b'SAR20-COMPARATOR-v1\x00'+struct.pack('>5Q',*words)
    digest=hashlib.sha256(payload).digest()
    a,b=struct.unpack('>QQ',digest[:16])
    # Exact binary64 operations and ordering as specified by the frozen code;
    # log/cos last bits may differ from the MATLAB host libm.
    u1=(float(a>>12)+0.5)/4503599627370496.0
    u2=(float(b>>12)+0.5)/4503599627370496.0
    need(0<u1<1 and 0<u2<1,'key yielded non-open uniform')
    z=math.sqrt(-2.0*math.log(u1))*math.cos(2.0*math.pi*u2)
    need(math.isfinite(z),'non-finite comparator variate')
    return z,digest.hex()


def real_int(v,lo,hi,label):
    x=float(v)
    need(math.isfinite(x) and x==math.floor(x) and lo<=x<=hi,f'invalid {label}: {v}')
    return int(x)


def bitword(v,bit,width,label):
    return (real_int(v,0,(1<<width)-1,label)>>bit)&1


def describe(values,sigma):
    x=np.asarray(values,dtype=float)
    need(x.size>0 and np.all(np.isfinite(x)),'invalid statistics input')
    a=np.abs(x)
    return {'count':int(x.size),'min_v':float(np.min(x)),'max_v':float(np.max(x)),
            'mean_v':float(np.mean(x)),'std_v_population':float(np.std(x)),
            'median_v':float(np.median(x)),'abs_min_v':float(np.min(a)),
            'abs_p05_v':float(np.percentile(a,5)),'abs_median_v':float(np.median(a)),
            'abs_p95_v':float(np.percentile(a,95)),
            'within_1_sigma_count':int(np.count_nonzero(a<=sigma)),
            'within_2_sigma_count':int(np.count_nonzero(a<=2*sigma)),
            'within_3_sigma_count':int(np.count_nonzero(a<=3*sigma))}


def check_context(logs,p):
    widths={'event_log':2,'back_log':8,'control_log':13,'raw_log':6,
            'ready_log':1,'adi_wire_log':58}
    for name,width in widths.items():
        need(name in logs and logs[name]['data'].shape[1]==width,f'missing/wrong log width: {name}')
    t=logs['event_log']['time'];E=logs['event_log']['data']
    need(E.shape==(p['cycles']*48,2),'actual event inventory size mismatch')
    need(np.array_equal(E[:,0],np.repeat(np.arange(p['cycles']),48)) and
         np.array_equal(E[:,1],np.tile(np.arange(1,49),p['cycles'])),'actual event order mismatch')
    expected=np.array([cycle*p['period_s']+g['time_s']
                       for cycle in range(p['cycles']) for g in p['groups']],dtype=np.float64)
    need(t.dtype==expected.dtype and t.tobytes()==expected.tobytes(),'actual event time words differ')
    for name in widths:
        need(logs[name]['time'].dtype==t.dtype and logs[name]['time'].tobytes()==t.tobytes(),
             f'{name} time axis differs')
    raw=logs['raw_log']['data'];ctrl=logs['control_log']['data']
    need(np.array_equal(raw[:,:3],ctrl[:,4:7]),'actual RAW and control words differ')
    need(np.array_equal(raw[:,3],E[:,0]) and np.all(raw[:,4]==p['epoch']) and
         np.array_equal(raw[:,3],ctrl[:,8]) and np.array_equal(raw[:,4],ctrl[:,9]),
         'actual sample/epoch tags differ')
    need(np.all(np.isin(raw[:,5],[0,1])),'RAW validity not binary')
    need(np.all(np.isfinite(logs['adi_wire_log']['data'][:,32:54])),
         'nonfinite feedback sign/count tap')
    return t,E,raw,ctrl,logs['back_log']['data'],logs['adi_wire_log']['data']


def audit(logs,p):
    t,E,raw,ctrl,back,tap=check_context(logs,p)
    rows=[];feedback_mismatch=[];counter_mismatch=[];word_mismatch=[];ready_mismatch=[]
    selected_start=p['first_id'];selected_end=selected_start+p['N']
    for sample in range(p['cycles']):
        first=sample*48;actual_signs=np.zeros(19,dtype=int);counts=[0,0,0]
        prior_d2={};prior_ta={};expected_d2=expected_dt=0
        actual_d2=actual_dt=0
        for gi,group in enumerate(p['groups']):
            pos=first+gi
            for token in group['events']:
                typ=token['type'];ix=token['index'];bit=token['bit']
                if typ=='cnv':
                    actual_signs[:]=0;counts=[0,0,0]
                elif typ in ('d2_feedback','ta_feedback'):
                    prior=prior_d2 if typ=='d2_feedback' else prior_ta
                    need(ix in prior,f'feedback without actual prior decision: {sample}/{typ}/{ix}')
                    actual_signs[ix if typ=='d2_feedback' else 12+ix]=2*prior[ix]-1
                    if typ=='ta_feedback':counts[2]+=1
                elif typ in ('d2_decide','ta_compare'):
                    d2=typ=='d2_decide';width=12 if d2 else 8;key_code=2 if d2 else 3
                    need(0<=ix<width and bit==width-1-ix,f'invalid {typ} index/bit')
                    vy=float(back[pos,1]);need(math.isfinite(vy),f'nonfinite VY at {sample}/{gi+1}')
                    observed=bitword(raw[pos,1 if d2 else 2],bit,width,typ)
                    control=bitword(ctrl[pos,5 if d2 else 6],bit,width,typ+' control')
                    need(observed==control,'RAW and control bit mismatch')
                    actual_id=real_int(E[pos,0],0,2**32-1,'actual event sample_id')
                    actual_epoch=real_int(raw[pos,4],0,2**32-1,'actual RAW epoch')
                    z,key=cmp_draw(p['seed_u64'],actual_epoch,actual_id,key_code,ix)
                    noise=p['sigma_vy_v']*z
                    effective=(vy+p['offset_vy_v'])+noise
                    need(math.isfinite(effective),'nonfinite effective comparator input')
                    predicted=1 if effective>0 else 0 if effective<0 else p['tie_decision']
                    no_offset_sign=1 if vy>0 else 0 if vy<0 else None
                    v_offset=vy+p['offset_vy_v']
                    offset_sign=1 if v_offset>0 else 0 if v_offset<0 else None
                    # Screening only: 128 ULP is not a formal bound on a
                    # different MATLAB libm. Never suppress a mismatch on it.
                    scale=max(abs(vy),abs(p['offset_vy_v']),abs(noise),abs(effective))
                    screen=128*(math.ulp(scale)+abs(p['sigma_vy_v'])*math.ulp(z))
                    row={'sample_id':actual_id,'epoch':actual_epoch,'group':gi+1,
                         'event_type':typ,'event_index':ix,'bit_index':bit,
                         'selected':selected_start<=sample<selected_end,'time_s':float(t[pos]),
                         'actual_vy_v':vy,'key_sha256':key,'z_python':z,'noise_v':noise,
                         'effective_vy_v':effective,'effective_is_physical_node':False,
                         'actual_bit':observed,'independent_bit':predicted,
                         'matches':observed==predicted,
                         'vy_sign_reference':no_offset_sign,
                         'offset_only_sign_reference':offset_sign,
                         'flip_vs_vy_sign':None if no_offset_sign is None else observed!=no_offset_sign,
                         'flip_vs_offset_only':None if offset_sign is None else observed!=offset_sign,
                         'near_zero_libm_screen_v':screen,'near_zero_libm_screen':abs(effective)<=screen}
                    rows.append(row)
                    if d2:
                        prior_d2[ix]=observed;actual_d2|=observed<<bit;expected_d2|=predicted<<bit;counts[0]+=1
                    else:
                        prior_ta[ix]=observed;actual_dt|=observed<<bit;expected_dt|=predicted<<bit;counts[1]+=1
                elif typ=='raw_latch':
                    observed_d2=real_int(raw[pos,1],0,4095,'latched D2')
                    observed_dt=real_int(raw[pos,2],0,255,'latched DT')
                    if observed_d2!=actual_d2 or observed_dt!=actual_dt:
                        word_mismatch.append({'sample_id':sample,'observed':[observed_d2,observed_dt],
                                              'from_observed_bits':[actual_d2,actual_dt]})
                    if observed_d2!=expected_d2 or observed_dt!=expected_dt:
                        word_mismatch.append({'sample_id':sample,'observed':[observed_d2,observed_dt],
                                              'from_independent_bits':[expected_d2,expected_dt]})
                    ready=real_int(logs['ready_log']['data'][pos,0],0,1,'raw ready')
                    if ready!=1:ready_mismatch.append(sample)
            got_counts=tap[pos,51:54]
            if not np.array_equal(got_counts,np.asarray(counts)):
                counter_mismatch.append({'sample_id':sample,'group':gi+1,
                                         'observed':got_counts.tolist(),'expected':counts[:]})
            got_signs=tap[pos,32:51]
            if not np.array_equal(got_signs,actual_signs):
                feedback_mismatch.append({'sample_id':sample,'group':gi+1,
                                          'observed':got_signs.tolist(),'expected':actual_signs.tolist()})
    need(len(rows)==p['cycles']*20,'decision inventory mismatch')
    summaries={}
    for name,part in [('all',rows),('selected',[r for r in rows if r['selected']]),
                      ('d2',[r for r in rows if r['event_type']=='d2_decide']),
                      ('ta',[r for r in rows if r['event_type']=='ta_compare']),
                      ('selected_d2',[r for r in rows if r['selected'] and r['event_type']=='d2_decide']),
                      ('selected_ta',[r for r in rows if r['selected'] and r['event_type']=='ta_compare'])]:
        summaries[name]={'decisions':len(part),'mismatched_bits':sum(not r['matches'] for r in part),
            'flips_vs_vy_sign':sum(r['flip_vs_vy_sign'] is True for r in part),
            'vy_sign_unavailable_at_exact_zero':sum(r['flip_vs_vy_sign'] is None for r in part),
            'flips_vs_offset_only':sum(r['flip_vs_offset_only'] is True for r in part),
            'offset_only_sign_unavailable_at_exact_zero':sum(r['flip_vs_offset_only'] is None for r in part),
            'near_zero_libm_screen_count':sum(r['near_zero_libm_screen'] for r in part),
            'actual_vy':describe([r['actual_vy_v'] for r in part],p['sigma_vy_v']),
            'effective_vy':describe([r['effective_vy_v'] for r in part],p['sigma_vy_v'])}
    return {'summaries':summaries,'rows':rows,'word_mismatch':word_mismatch,
            'counter_mismatch':counter_mismatch,'feedback_mismatch':feedback_mismatch,
            'ready_mismatch':ready_mismatch}


def self_test():
    z,h=cmp_draw(20261104,1,0,2,0)
    need(h=='61e7ca79dbc6fe7c97d3939daa4dc949a4b96ed50b3edf2a54d4147c814fd646','SHA vector')
    need(abs(z-(-1.1560934225053394))<1e-14,'Box-Muller vector')
    need(cmp_draw(20261104,1,0,2,0)==(z,h),'determinism')
    need(cmp_draw(20261104,1,0,3,0)[1]!=h,'event domain')

    # A synthetic 8-frame logger fixture, generated independently of cmp_draw.
    # Every comparator is well away from threshold except the one known SHA
    # vector above: VY=+1 mV and sigma=1 mV must flip that bit to zero.
    def token(kind,index=-1,bit=-1):
        return {'type':kind,'index':index,'bit':bit}
    sequence=[[token('cnv')]]
    for i in range(12):
        sequence.extend([[token('d2_decide',i,11-i)], [token('d2_feedback',i,11-i)]])
    for i in range(8):
        group=[] if i==0 else [token('ta_feedback',i-1,8-i)]
        sequence.append(group+[token('ta_compare',i,7-i)])
    sequence.append([token('raw_latch')])
    sequence.extend([[token('idle')]]*(48-len(sequence)))
    groups=[{'time_s':i*1e-9,'events':events} for i,events in enumerate(sequence)]
    p={'cycles':8,'first_id':0,'N':8,'epoch':1,'period_s':200e-9,
       'groups':groups,'seed_u64':20261104,'sigma_vy_v':0.001,
       'offset_vy_v':0.0,'tie_decision':0}
    n=8*48
    times=np.array([sample*p['period_s']+g['time_s'] for sample in range(8) for g in groups])
    def blank(width):return np.zeros((n,width),dtype=float)
    event=blank(2);raw=blank(6);control=blank(13);back=blank(8);tap=blank(58);ready=blank(1)
    for sample in range(8):
        d2=dt=0;signs=np.zeros(19,dtype=int);counts=[0,0,0];previous={}
        for gi,group in enumerate(groups):
            pos=sample*48+gi;event[pos]=[sample,gi+1]
            for ev in group['events']:
                kind=ev['type'];ix=ev['index'];bit=ev['bit']
                if kind in ('d2_decide','ta_compare'):
                    vy=0.1 if ix%2==0 else -0.1
                    if sample==0 and kind=='d2_decide' and ix==0:vy=0.001
                    decision=int(vy>0)
                    if sample==0 and kind=='d2_decide' and ix==0:decision=0
                    back[pos,1]=vy;previous[(kind,ix)]=decision
                    if kind=='d2_decide':d2|=decision<<bit;counts[0]+=1
                    else:dt|=decision<<bit;counts[1]+=1
                elif kind in ('d2_feedback','ta_feedback'):
                    original='d2_decide' if kind=='d2_feedback' else 'ta_compare'
                    signs[ix if kind=='d2_feedback' else 12+ix]=2*previous[(original,ix)]-1
                    if kind=='ta_feedback':counts[2]+=1
                elif kind=='raw_latch':ready[pos,0]=1
            raw[pos]=[0,d2,dt,sample,1,1]
            control[pos,4:7]=raw[pos,:3];control[pos,8:10]=[sample,1]
            tap[pos,32:51]=signs;tap[pos,51:54]=counts
    logs={name:{'time':times.copy(),'data':values} for name,values in
          [('event_log',event),('raw_log',raw),('control_log',control),
           ('back_log',back),('adi_wire_log',tap),('ready_log',ready)]}
    result=audit(logs,p)
    need(result['summaries']['all']['mismatched_bits']==0 and
         result['summaries']['all']['flips_vs_vy_sign']==1 and
         result['summaries']['selected_d2']['decisions']==96 and
         result['summaries']['selected_ta']['decisions']==64 and
         not result['feedback_mismatch'] and not result['counter_mismatch'] and
         not result['word_mismatch'] and not result['ready_mismatch'],
         'synthetic joined decision/feedback fixture')
    # A corruption is injected into the actual RAW and its mirrored control
    # signal together, so the decision oracle, not the mirror check, catches it.
    raw[1,1]=control[1,5]=2048
    damaged=audit(logs,p)
    need(damaged['summaries']['all']['mismatched_bits']==1 and
         bool(damaged['feedback_mismatch']) and bool(damaged['word_mismatch']),
         'synthetic wrong decision must be detected')
    raw[1,1]=control[1,5]=0
    tap[2,51]+=1
    need(bool(audit(logs,p)['counter_mismatch']),'synthetic wrong count must be detected')
    print(json.dumps({'status':'python_self_test_pass','key_sha256':h,'z':z,
                      'synthetic':{'frames':8,'decisions':160,'actual_flips_vs_vy':1,
                                   'wrong_bit_and_wrong_count_detected':True},
                      'scope':'synthetic key/logs only; no MATLAB or model data'},indent=2))


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--self-test',action='store_true')
    a.add_argument('--p',type=Path);a.add_argument('--p-sha')
    a.add_argument('--simout',type=Path);a.add_argument('--simout-sha')
    a.add_argument('--model',type=Path);a.add_argument('--model-sha')
    a.add_argument('--src-root',type=Path,help='actual frozen candidate/current/src')
    args=a.parse_args()
    if args.self_test:self_test();return
    need(all((args.p,args.p_sha,args.simout,args.simout_sha,args.model,args.model_sha,args.src_root)),
         'P, simout, model, their hashes and frozen src-root are required')
    for pth in [args.p,args.simout,args.model,args.src_root]:no_holdout(pth)
    pins={'P':verify_pin(args.p,args.p_sha,'P'),
          'simout':verify_pin(args.simout,args.simout_sha,'simout'),
          'model':verify_pin(args.model,args.model_sha,'model')}
    sources={name:verify_pin(args.src_root/name,expected,name) for name,expected in SOURCE_PINS.items()}
    graph=graph_info(args.model)
    p=load_parameters(args.p);logs=read_logs(args.simout);result=audit(logs,p)
    ok=(result['summaries']['all']['mismatched_bits']==0 and not result['word_mismatch'] and
        not result['counter_mismatch'] and not result['feedback_mismatch'] and not result['ready_mismatch'])
    report={'schema':'sar20-normal-n8-cmp-independent/v1',
            'status':'matched_with_libm_limits' if ok else 'mismatch_requires_investigation',
            'pins_sha256':pins,'source_sha256':sources,'graph_xml_sha256':graph,
            'parameters':{k:v for k,v in p.items() if k!='groups'},**result,
            'limits':['actual event-log group and saved P map determine event index; no direct comparator diagnostic was logged',
                      'Python and MATLAB log/cos can differ in final bits; near-zero screen is heuristic, not a proof',
                      'flips compare against sign(VY); exact-zero native comparator decision is unobserved',
                      'effective VY is reconstructed comparator input, not an observed analog node',
                      'feedback signs and counters are observed command/next-state wires, not committed analog state',
                      'no RA noise/physical state reconstruction, holdout, model run or silicon claim',
                      'on-disk source and graph hashes do not prove the executed MATLAB cache; use worker binding receipt']}
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    if not ok:sys.exit(2)


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status':'audit_input_or_integrity_error','error':str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
