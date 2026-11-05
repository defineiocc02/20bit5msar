#!/usr/bin/env python3
"""Read actual 15-point output and pinned endpoint simouts; print JSON only."""
from __future__ import annotations
import argparse, hashlib, json, sys, zipfile
from pathlib import Path
sys.dont_write_bytecode=True

ROOT_MODEL='ae2d2b023362fd39b1cfaad39278b8c91fbad23d542f19df864547fb7e77e733'
ROOT_STATE='63d4d082b511837b47afc559b1079f7b2a3bdc847bd0d861e4b65a8b6c378ee5'
SOURCE_PINS='edeabf9ec82d33a844cf36581ed0fd3d5d5f9da27e79e76ab15daea393278e32'
CANDIDATE='aa1e2c9960f3e10df6dde5831bdb58b100f2020bffd4f5e4bcadd15d862617f4'
PRIOR_RECEIPT='7994fa7b60ea653e17d4aa3c06a17ced8a6e83d3ad72e8b64c96c3eefae7986c'
SIX_HELPER='44ee80fbaeb8b77449f9fca0143ed96a1ddb5dc033e34d391cdd22ebe56a3181'
RAW_HELPER='3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'
ANCHORS=[
 {'P.mat':'1e5af6d4499cb171f57a55c6516a9a828f5ad781e9f307032727dae801be7dc6',
  'simout.mat':'70e8d1b858f1e1f4eff2abe9212eb741c5fa6744d691a7646073d870fe327faa',
  'observed.mat':'c6286948863078d0211b5fe29461b932f829b46a761331b6460be88e21c3cfd1'},
 {'P.mat':'10ed3f815ff9d248c93c5950a4c11e6c2a080da5e2b24b82e851574b4fda2424',
  'simout.mat':'665aa9b471a77b5ef6f211b70806e51e34d23e29b09cb8facb96ad105ecb0f0a',
  'observed.mat':'740a2cd8f3cb88924f29972e198b0f55bf9314290696b372c2203ac943bc90d5'}]
LSB=7.8125e-6
LOW=-LSB/4096
STEP=-LOW/16


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',required=True,type=Path)
    ap.add_argument('--project',required=True,type=Path)
    args=ap.parse_args();result=args.result.resolve();project=args.project.resolve()
    six_path=project/'analysis/behavior/local_static_20261030/verify_static_six.py'
    raw_path=project/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
    if sha(six_path)!=SIX_HELPER or sha(raw_path)!=RAW_HELPER:
        raise ValueError('Pinned independent log reader source changed')
    sys.path[:0]=[str(six_path.parent),str(raw_path.parent)]
    import verify_static_six as six
    import verify_as_run as u
    import h5py
    import numpy as np
    need=u.need
    R=json.loads((result/'receipt.json').read_text())
    need(R['status']=='fifteen_actual_interior_and_two_reused_endpoints' and R['stage']=='complete',
         'Actual job incomplete or cleanup failed')
    need(R.get('model_source_workspace_parameters_unchanged') and R['cleanup']['status']=='complete',
         'Source/workspace or cleanup gate failed')
    need(R['dnl']=='not_measured' and R['inl']=='not_measured','Unexpected DNL/INL claim')
    for name,expected,key in [('SarAdc_as_run.slx',ROOT_MODEL,'model_sha256'),
                              ('applied_config_as_run.json',ROOT_STATE,'state_sha256'),
                              ('source_pins.json',SOURCE_PINS,'source_pins_sha256'),
                              ('sar20_zero15_ae2d.m',CANDIDATE,'candidate_sha256')]:
        need(sha(result/name)==expected==R[key],name+' identity mismatch')
    need(sha(result/'source.zip')==R['source_zip_sha256'],'Source ZIP hash mismatch')
    pin_rows=json.loads((result/'source_pins.json').read_text())['files']
    pins={r['path'].replace('\\','/'):r['sha256'] for r in pin_rows}
    need(len(pins)==len(pin_rows)==105,'Unexpected source inventory')
    with zipfile.ZipFile(result/'source.zip') as z:
        names=z.namelist();need(len(names)==len(set(names)) and set(names)==set(pins),'Source ZIP inventory mismatch')
        for n,h in pins.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Source ZIP mismatch: '+n)
    need(sha(result/'anchors/prior_receipt.json')==PRIOR_RECEIPT,'Prior receipt pin mismatch')
    need(len(R['anchors'])==2 and len(R['points'])==15 and len(R['samples'])==17 and len(R['adjacent'])==16,
         'Expected two anchors, 15 actual points and 17 samples')
    need(R['requested_step_v']==STEP,'Requested step differs')
    requested=[LOW]+[LOW+j*STEP for j in range(1,16)]+[0.0]
    need(np.array_equal(np.asarray(R['requested_interior_v']),np.asarray(requested[1:-1])),'Wrong requested interior grid')
    measurements=[];event_time=None;anchorP=result/'anchors/point_01/P.mat'
    allowed={'P/input/offset_v','P/front/input/offset_v','P/xFE0'}
    for j in range(17):
        if j in (0,16):
            n=0 if j==0 else 1;folder=result/'anchors'/f'point_{n+1:02d}';meta=R['anchors'][n]
            need(meta['rerun'] is False,'Reused anchor incorrectly marked rerun')
            for name,h in ANCHORS[n].items():need(sha(folder/name)==h,'Anchor identity mismatch: '+name)
            expected_origin='reused_actual_endpoint'
        else:
            folder=result/f'point_{j:02d}';meta=R['points'][j-1]
            need(meta['index']==j and meta['status']=='valid' and meta['global_rng_unchanged'],f'Point {j} failed')
            for name,key in [('P.mat','P_sha256'),('simout.mat','simout_sha256'),('observed.mat','observed_sha256')]:
                need(sha(folder/name)==meta[key],f'Point {j} {name} mismatch')
            expected_origin='new_actual_interior'
        pfile=folder/'P.mat';diff=set(u.pdiff(anchorP,pfile));need(diff<=allowed,f'Point {j} P drift: {diff}')
        logs=u.read_logs(folder/'simout.mat')
        if event_time is None:event_time=logs['event_log']['time']
        else:need(u.same(event_time,logs['event_log']['time']),f'Point {j} actual event time differs')
        point=six.verify_logs(logs,pfile,requested[j],u,np,h5py)
        obs=meta['observation'];sample=R['samples'][j]
        need(point['held_v']==obs['held_input_v']==sample['held_input_v'] and
             point['code20']==obs['code20']==sample['code20'] and
             point['ready_time_s']==obs['ready_time_s']==sample['ready_time_s'] and
             np.array_equal(np.asarray(point['raw6']),np.asarray(obs['raw6'])) and
             np.array_equal(np.asarray(point['raw6']),np.asarray(sample['raw6'])) and
             sample['requested_v']==requested[j] and sample['origin']==expected_origin,
             f'Point {j} actual observation/sample differs')
        measurements.append(point)
    held=[m['held_v'] for m in measurements];codes=[m['code20'] for m in measurements]
    need(all(a<b for a,b in zip(held,held[1:])),'Held input order differs')
    need(codes[0]==524285 and codes[-1]==524289,'Pinned actual anchor codes differ')
    changes=[]
    for j in range(16):
        d=R['adjacent'][j];delta=codes[j+1]-codes[j]
        need(d['left_index']==j+1 and d['right_index']==j+2 and
             d['left_held_v']==held[j] and d['right_held_v']==held[j+1] and
             d['left_code']==codes[j] and d['right_code']==codes[j+1] and d['delta_code']==delta,
             f'Adjacent sampled difference {j+1} mismatch')
        changes.append({'left_held_v':held[j],'right_held_v':held[j+1],
                        'left_code':codes[j],'right_code':codes[j+1],'delta_code':delta})
    print(json.dumps({'status':'actual_17_samples_independently_read','samples':measurements,
        'adjacent_sample_differences':changes,'observed_codes_nondecreasing':all(a<=b for a,b in zip(codes,codes[1:])),
        'actual_event_time_bit_identical_for_all_17':True,'model_sha256':ROOT_MODEL,
        'scope':'Sampled endpoints only; unsampled inputs remain unobserved. No missing-code or global DNL/INL conclusion.'},
        ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
