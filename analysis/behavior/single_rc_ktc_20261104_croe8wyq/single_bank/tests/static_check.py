#!/usr/bin/env python3
"""Identity/boundary check only. Does not execute MATLAB or Simulink."""
from pathlib import Path
from zipfile import ZipFile
import hashlib,json,re
pkg=Path(__file__).resolve().parents[1]
base=pkg.parent/'FROZEN_BASE_v2.zip'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert base.is_file() and base.stat().st_size<300_000_000
assert sha(base.read_bytes())=='09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7'
expected={
 'config/adc_parameters.m',
 'current/src/frontend/behavior_frontend_init.m',
 'current/src/frontend/behavior_frontend_step.m',
 'current/src/frontend/behavior_jitter_prepare_front.m',
 'current/src/model/behavior_applied_note.m',
 'current/src/model/behavior_prepare_configuration.m',
 'current/src/model/behavior_ra_noise_guard.m',
 'tests/static_check.py',
}
with ZipFile(base) as z:
    originals={n[len('single_bank/'):]:z.read(n) for n in z.namelist()
               if n.startswith('single_bank/') and not n.endswith('/')}
    missing={'MANIFEST.json','STATIC_CHECK.json'}
    for n in missing:
        assert not (pkg/n).exists()
        assert (pkg/'baseline_v2'/('ORIGINAL_V2_'+n)).read_bytes()==originals[n]
    changed={n for n in originals if n not in missing and (pkg/n).read_bytes()!=originals[n]}
    assert changed==expected,(sorted(changed-expected),sorted(expected-changed))
    for n in ('current/src/frontend/behavior_frontend_pack.m',
              'current/src/frontend/behavior_frontend_unpack.m',
              'current/src/frontend/behavior_frontend_stage.m',
              'current/src/frontend/behavior_frontend_sfun.m',
              'current/models/SarAdc.slx'):
        assert (pkg/n).read_bytes()==originals[n]
    init=(pkg/'current/src/frontend/behavior_frontend_init.m').read_text()
    step=(pkg/'current/src/frontend/behavior_frontend_step.m').read_text()
    bind=(pkg/'current/src/frontend/behavior_jitter_prepare_front.m').read_text()
    guard=(pkg/'current/src/model/behavior_ra_noise_guard.m').read_text()
    original=originals['current/src/frontend/behavior_frontend_step.m'].decode()
    marker='function dv=sample_ktc_diff(ids,id,epoch,p)'
    assert step.split(marker,1)[1]==original.split(marker,1)[1]
    assert 'sqrt(-expm1(-2*duration(finiteMask)./tau(finiteMask)))' in step
    assert 'cmd.t_s-s.acquire_open_s(ids)' in step
    assert "'singleBank:ktcUnequalTau'" in init and "'singleBank:ktcUnequalTau'" in step
    assert "'singleBank:ktcInterruptedAcquisition'" in step
    assert all("'behaviorFE:jitterFiniteSamplingUnsupported'" in s for s in (init,step,bind))
    assert "'sar20RA:coverageKTC'" in guard and 'ktcTauOK' in guard
    assert 'if ~all(isinf(tau))' in step
    uncommented='\n'.join(line.split('%',1)[0] for line in step.splitlines())
    assert not re.search(r'\b(randn?|RandStream|persistent)\b',uncommented)
    sfun=(pkg/'current/src/frontend/behavior_frontend_sfun.m').read_text()
    assert 'inputWidths=[353 6 4];outputWidths=[353 7];' in sfun
    for name in ('behavior_frontend_init','behavior_frontend_step'):
        original_text=originals['current/src/frontend/'+name+'.m'].decode()
        renamed=(pkg/'tests/baseline_v2'/(name+'_v2.m')).read_text()
        assert renamed.replace(name+'_v2',name,1)==original_text
print(json.dumps({'status':'PASS_static_only','changed_source':sorted(changed),
 'unchanged_353_ABI':True,'unchanged_random_helper_and_keys':True,
 'single_equal_tau_and_finite_jitter_guards_present':True,
 'model_sha256':sha((pkg/'current/models/SarAdc.slx').read_bytes()),
 'model_warning':'historical d4 model, not the separately audited 485 graph',
 'matlab_execution':'NOT_RUN','simulink_execution':'NOT_RUN',
 'actual_circuit_validation':'NOT_RUN'},indent=2))
