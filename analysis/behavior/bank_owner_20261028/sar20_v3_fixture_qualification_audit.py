#!/usr/bin/env python3
"""Offline compare frozen source, receipts, public profile; never read old holdout records."""
import hashlib,json,math,sys,zipfile
from pathlib import Path
import h5py,numpy as np
R=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');A=Path('/tmp/sar20_az/rx_long_calibration/pingpong_main_v1')
sys.path.insert(0,str(R/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import fingerprint,need,sha,val
paths={k:R/f'runs/az_probe_20261028T{k}Z' for k in ['120503','120548','120612']}
r0=json.loads((paths['120503']/'receipt.json').read_text());w0=json.loads((paths['120503']/'wrapper_receipt.json').read_text());cache=json.loads((paths['120548']/'bank_cache_inspect.json').read_text());r=json.loads((paths['120612']/'receipt.json').read_text());w=json.loads((paths['120612']/'wrapper_receipt.json').read_text())
need(r0['status']=='failed' and r0['stage']=='preflight' and r0['error_identifier']=='bankFixtureJob:cached' and 'sar20_bank_sha256' in r0['error'],'initial failure differs')
need(w0['status']=='failed_preserved' and w0['path_restored'] and not w0['candidate_cached_files'],'initial wrapper')
need(cache['status']=='bank_candidate_cache_inspected' and len(cache['names'])==6 and not cache['loaded'] and all(not x for x in cache['resolved'].values()) and cache['model_status']=='stopped' and cache['model_dirty']=='off','cache inspection')
need(r['status']=='native_synthetic_fixture_v3_only_pass' and r['stage']=='complete' and not r['production_code_valid'] and not r['real_project_holdout_used'] and not r['current_model_operated'] and r['global_rng_unchanged'],'inner native fixture')
need(w['status']=='frozen_v3_native_fixture_pass' and w['fixture_status']==r['status'] and w['path_restored'] and not w['candidate_cached_files'] and w['model_status']=='stopped' and w['model_dirty']=='off','wrapper fixture')
need(w['model_sha256_before']==w['model_sha256_after']==w0['model_sha256_before']==w0['model_sha256_after']=='63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6','model receipt pins')
fx=r['fixture'];need(fx['status']=='synthetic_fixture_v3_only_pass' and not any(fx[k] for k in ['production_code_valid','real_project_holdout_used','actual_model_bound','same_run_training_arm_supported','full_bank_integration']) and fx['nonuniform_h'] and fx['epochs_tested']==[1,2,3] and fx['dem_on_off_tested'],'fixture scope')
zp=paths['120612']/'candidate.zip'
with zipfile.ZipFile(zp) as z,zipfile.ZipFile(R/'runs/behavior_a27903ef-c1c6-4e5e-b487-d2c1d468efef/source.zip') as base:
 pref='rx_long_calibration/bank_owner_candidate_v3/'; manifest= json.loads(z.read(pref+'frozen_manifest.json'));manifest_sha=hashlib.sha256(z.read(pref+'frozen_manifest.json')).hexdigest()
 need(manifest_sha==w['frozen_manifest_sha256']==w0['frozen_manifest_sha256'],'frozen manifest hash')
 rc={x['name']+'.m':x['sha256'] for x in r['candidate']};files={}
 for name,entry in manifest['files'].items():
  path=('jobs/' if name=='rx_bank_owner_fixture_v3_job.m' else pref)+name;h=hashlib.sha256(z.read(path)).hexdigest()
  need(h==entry['sha256'],name+' archived source differs manifest')
  if name in rc:need(h==rc[name],name+' archived source differs native receipt')
  files[name]=h
 need(len(rc)==6 and set(rc)==set(files)-{'rx_bank_owner_fixture_v3_job.m'},'candidate source inventory')
 need(hashlib.sha256(z.read(pref+'static_receipt.json')).hexdigest()==manifest['static_receipt_sha256'],'static receipt hash')
 for dep in r['dependencies']:
  h=hashlib.sha256(base.read('current/src/calibration/'+dep['name']+'.m')).hexdigest();need(h==dep['sha256'],'archived public dependency differs receipt '+dep['name'])
 qbytes=(A/'qualification_rx1024_v3.json').read_bytes();q=json.loads(qbytes);qsha=hashlib.sha256(qbytes).hexdigest()
 need(qbytes==z.read('rx_long_calibration/pingpong_main_v1/qualification_rx1024_v3.json'),'qualification changed since mirrored ZIP')
 # Frozen archive proves only the observed artifact bytes, not producer identity or authority.
tr=json.loads((R/'runs/az_probe_20261028T100042Z/receipt.json').read_text());fr=json.loads((R/'runs/az_probe_20261028T102242Z/receipt.json').read_text());ev=json.loads((R/'runs/az_probe_20261028T102427Z/receipt.json').read_text());audit=json.loads((R/'analysis/behavior/rx_holdout_20261028/independent_attempt1.json').read_text());pro=json.loads((R/'runs/az_probe_20261028T100042Z/rx_protocol.json').read_text())
for key,p in [('training_receipt_sha256',R/'runs/az_probe_20261028T100042Z/receipt.json'),('freeze_receipt_sha256',R/'runs/az_probe_20261028T102242Z/receipt.json'),('evaluation_receipt_sha256',R/'runs/az_probe_20261028T102427Z/receipt.json'),('protocol_sha256',R/'runs/az_probe_20261028T100042Z/rx_protocol.json'),('independent_previous_audit_sha256',R/'analysis/behavior/rx_holdout_20261028/independent_attempt1.json'),('independent_verifier_sha256',R/'analysis/behavior/rx_holdout_20261028/verify_terminal_holdout.py')]:need(sha(p)==q[key],'qualification source pin '+key)
need(q['status']=='behavior_profile_qualified' and q['kind']=='registered_behavior_simulation' and not q['fixture'] and q['acceptance']=='NOT_ACCEPTED' and q['activation']=='none' and not q['automatic_bank_publish'],'qualification status')
need(tr['train_gate']['rows']==q['train_recheck']['rows']==2048 and tr['train_gate']['fit_calls']==q['train_recheck']['fit_calls_original']==1 and tr['train_gate']['rank']==q['train_recheck']['rank_original']==q['train_recheck']['rank_independent']==684,'training audit assertion')
need(q['fixed_holdout_gates']==audit['fixed_registered_gates'] and q['frozen_public_oracle_summary']==audit['actual_frozen_diag_and_public_reconstruction'] and all(ev[k]==v for k,v in q['fixed_holdout_gates']['actual_metrics'].items()),'qualification historical summary differs')
need(q['selected_public_records_sha256']==audit['selected_mat_sha256'] and q['public_holdout_result_sha256']==ev['public_holdout_result_sha256'],'holdout hashes metadata')
need(q['protocol_sha256']==tr['protocol_sha256']==fr['protocol_sha256']==ev['protocol_sha256'] and q['coefficient_sha256']==fr['coefficient_sha256']==ev['coefficient_sha256'] and q['public_cfg_sha256']==fr['public_cfg_sha256'] and q['coefficient_file_sha256']==fr['coefficient_file_sha256']==ev['coefficient_file_sha256'],'qualification provenance')
need(pro['train']['records']==2048 and pro['train']['first_id']==4 and pro['train']['epoch']==1 and pro['holdout']['records']==1024 and pro['holdout']['first_id']==4 and pro['holdout']['epoch']==3,'protocol windows')
train=R/'runs/behavior_a27903ef-c1c6-4e5e-b487-d2c1d468efef';hold=R/'runs/behavior_dc38bf72-b9b2-42e6-a9d5-6b76a32a671f';frozen=R/'runs/calibration_freeze_ae16b620-10cf-464a-9411-0e85e180ee8c/frozen_coefficients.mat'
need(sha(frozen)==q['coefficient_file_sha256'],'frozen public cache hash')

def json_value(x):
 if isinstance(x,str):return x
 a=np.asarray(x)
 def c(v):
  if isinstance(v,(np.bool_,bool)):return bool(v)
  if not np.isfinite(v):return 'Inf' if v>0 else '-Inf' if v<0 else 'NaN'
  return float(v)
 return c(a.item()) if a.ndim==0 else [c(v) for v in a.ravel(order='F')]
with h5py.File(train/'parameters.mat') as t,h5py.File(hold/'parameters.mat') as h,h5py.File(frozen) as c:
 for key,v in q['public_profile'].items():
  need(json_value(val(t,'P/'+key))==v,'TRAIN public profile mismatch '+key)
  need(json_value(val(h,'P/'+key))==v,'HOLDOUT public profile mismatch '+key)
 plan=np.asarray(val(c,'C/plan'),dtype='uint8');need(list(plan.shape)==q['plan_shape'] and np.array_equal(plan,val(t,'P/front/plan')) and np.array_equal(plan,val(h,'P/front/plan')) and hashlib.sha256(plan.tobytes(order='F')).hexdigest()==q['plan_sha256'],'actual public plan')
 for field in ['P/cal_cfg/public_cfg']:
  need(fingerprint(t,t[field],{})==fingerprint(h,h[field],{})==fingerprint(c,c['C/public_cfg'],{}),'cfg consistency')
 hh=np.asarray(val(c,'C/h'),dtype='<f8');need(hh.shape==(684,1) and hashlib.sha256(hh.tobytes(order='F')).hexdigest()==q['coefficient_sha256'],'frozen public h')
 need(val(c,'C/acceptance')=='NOT_ACCEPTED' and val(c,'C/lifecycle')=='frozen_for_holdout','cache lifecycle')
base={'fixture_result':fx,'fixture_receipt_sha256':sha(paths['120612']/'receipt.json'),'wrapper_receipt_sha256':sha(paths['120612']/'wrapper_receipt.json'),'original_failed_receipt_sha256':sha(paths['120503']/'receipt.json'),'cache_inspection_sha256':sha(paths['120548']/'bank_cache_inspect.json'),'frozen_manifest_sha256':manifest_sha,'checked_source_sha256':files,'asrun_candidate_zip_sha256':sha(zp),'qualification_sha256':qsha,'qualification_pinned_receipts_and_audit':True,'training_and_holdout_public_profile_equal':True,'public_profile_field_count':len(q['public_profile']),'public_plan_2056x8_equal':True,'public_plan_sha256':q['plan_sha256'],'historical_h_sha256':q['coefficient_sha256'],'qualification_historical_metrics_equal_receipt_and_prior_audit':True,'limits':['No MATLAB reexecution, no model/actual P workspace accessed, no archived holdout row files opened or hashed by this audit.','Candidate source hashes are cross-checked post hoc; wrapper pins only manifest SHA; public dependency same-path cache freshness is not proven.','Wrapper clears candidate function names even after preflight failure and reports only candidate-path cached files.','Historical same-chip preimage used whole-P equality including opaque physical fields; it is not exclusively-public evidence.','Inspected current qualification generator statically opens both old holdout binary files for SHA even though it does not decode their rows; artifact does not pin its producer SHA.','Qualification artifact is not owner training/qualification certificate and cannot itself authorize integrated BankOwner code_valid.']}
print(json.dumps(base,ensure_ascii=False,indent=2,allow_nan=False))
