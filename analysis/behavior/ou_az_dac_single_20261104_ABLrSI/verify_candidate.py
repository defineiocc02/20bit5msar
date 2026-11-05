#!/usr/bin/env python3
"""Read-only isolation and static boundary verification; no MATLAB execution."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
base = root / 'baseline' / 'single_bank'
cand = root / 'candidate'


def sha(p):
    assert p.is_file() and p.stat().st_size < 300_000_000, p
    return hashlib.sha256(p.read_bytes()).hexdigest()


assert sha(root/'BASELINE_v2.zip') == '09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7'
baseline_hashes = json.loads((root/'BASELINE_SHA256.json').read_text())
assert {str(p.relative_to(base)): sha(p) for p in base.rglob('*') if p.is_file()} == baseline_hashes
candidate_hashes = {str(p.relative_to(cand)): sha(p) for p in cand.rglob('*') if p.is_file()}
changed = {p for p in baseline_hashes if p in candidate_hashes and baseline_hashes[p] != candidate_hashes[p]}
added = set(candidate_hashes)-set(baseline_hashes)
removed = set(baseline_hashes)-set(candidate_hashes)
expected_changed = {
    'README_SINGLE.md','MANIFEST.json','STATIC_CHECK.json','config/adc_parameters.m',
    'current/models/SarAdc.slx','current/src/model/behavior_dac_coupling_configuration.m',
    'current/src/model/behavior_ra_noise_guard.m','current/src/physics/behavior_backend_stage.m',
    'current/src/physics/behavior_backend_step.m','current/src/physics/behavior_ra_noise_validate_backend.m',
    'tests/static_check.py',
}
expected_added = {'OU_AZ_DAC_README.md','tests/joint_math_oracle.py','tests/test_joint_ou_az_dac.m'}
assert changed == expected_changed, (sorted(changed-expected_changed),sorted(expected_changed-changed))
assert added == expected_added and not removed, (sorted(added),sorted(removed))
assert candidate_hashes['current/models/SarAdc.slx']=='48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'
for p in ('current/src/physics/behavior_backend_sfun.m',
          'current/src/physics/behavior_backend_pack.m',
          'current/src/physics/behavior_backend_unpack.m',
          'current/src/physics/sar20_ra_keyed_normal.m',
          'current/src/physics/sar20_ra_ou_increment.m',
          'current/src/physics/behavior_dac_forcing_from_frontend.m',
          'current/src/model/behavior_single_guard.m'):
    assert baseline_hashes[p] == candidate_hashes[p], p

rel = Path('current/src/physics/behavior_backend_stage.m')
old = (base/rel).read_text()
new = (cand/rel).read_text()
old_fragment = '''                % ON is rejected by the backend finite-DAC guard.
                [s,y]=behavior_backend_step(s,s.command,dt,p,forcing);
'''
new_fragment = '''                if noiseInterval
                    % Hash the original binary64 endpoint, never t0+dt.
                    [s,y]=behavior_backend_step(s,s.command,dt,p,forcing,double(eventTime));
                else
                    % Preserve the legacy OFF/zero-duration call and arithmetic.
                    [s,y]=behavior_backend_step(s,s.command,dt,p,forcing);
                end
'''
assert old.count(old_fragment)==1 and old.replace(old_fragment,new_fragment)==new
rel = Path('current/src/physics/behavior_backend_step.m')
old = (base/rel).read_text()
new = (cand/rel).read_text()
start = '    if dt==0\n        nextVx=startVx;'
end = '    % OU innovation belongs to the same physical VX'
assert old.split(start,1)[1].split(end,1)[0] == new.split(start,1)[1].split(end,1)[0]
assert old.split('function [s,tau,target]=advance_az',1)[1].split('function validate_inputs',1)[0] == \
    new.split('function [s,tau,target]=advance_az',1)[1].split('function validate_inputs',1)[0]
manifest = json.loads((cand/'MANIFEST.json').read_text())
assert manifest['files']=={p:v for p,v in candidate_hashes.items() if p!='MANIFEST.json'}
print(json.dumps({'status':'static_isolation_checks_passed','baseline_files':len(baseline_hashes),
    'changed_from_v2':sorted(changed),'added_to_v2':sorted(added),'removed':[],
    'baseline_zip_sha256':sha(root/'BASELINE_v2.zip'),
    'graph_sha256':candidate_hashes['current/models/SarAdc.slx'],
    'unchanged_backend_state_sfun_and_noise_generator':True,
    'deterministic_ra_arithmetic_source_unchanged':True,
    'matlab_or_simulink_run':False},indent=2))
