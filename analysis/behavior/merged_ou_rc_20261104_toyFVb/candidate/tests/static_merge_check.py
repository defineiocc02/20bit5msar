#!/usr/bin/env python3
"""Three-way source identity and guard audit. Never executes MATLAB/Simulink."""
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile
import xml.etree.ElementTree as ET

candidate=Path(__file__).resolve().parents[1]
root=candidate.parent
analysis=root.parent
base_zip=analysis/'single_bank_1039_20261104/single_bank_1039_candidate_20261104_v2.zip'
ou_zip=analysis/'ou_az_dac_single_20261104_ABLrSI/ou_az_dac_single_candidate_20261104.zip'
rc_zip=analysis/'single_rc_ktc_20261104_croe8wyq/single_rc_ktc_candidate_20261104_v3.zip'
cmp_zip=analysis/'comparator_20261104/candidate_package.zip'
base=root/'baseline/single_bank'
ou=analysis/'ou_az_dac_single_20261104_ABLrSI/candidate'
rc=analysis/'single_rc_ktc_20261104_croe8wyq/single_bank'


def digest(b):
    return hashlib.sha256(b).hexdigest()


def safe_bytes(p):
    assert p.is_file() and p.stat().st_size<300_000_000,p
    return p.read_bytes()


for p,expected in ((base_zip,'09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7'),
                   (ou_zip,'34e70704d9a6a4ed9d2eb794e67ee5ee738dfe99db2c8f4cc3f8ab4e9bde8631'),
                   (rc_zip,'ede479868189a4e5a712e172173db7759208a62e1bfe9d6b31e644e86756feff'),
                   (cmp_zip,'368bc52069485dc1d14297349bddb1f669f251a62859fd8dfed2f0822de3a89b')):
    assert digest(safe_bytes(p))==expected,p


def mfiles(z,prefix):
    result={}
    for n in z.namelist():
        rel=n[len(prefix):] if n.startswith(prefix) else ''
        if rel.endswith('.m') and not rel.startswith('tests/'):
            assert z.getinfo(n).file_size<300_000_000
            result[rel]=z.read(n)
    return result


with ZipFile(base_zip) as zb,ZipFile(ou_zip) as zo,ZipFile(rc_zip) as zr:
    B=mfiles(zb,'single_bank/');O=mfiles(zo,'candidate/');R=mfiles(zr,'single_bank/')
    assert set(B)==set(O)==set(R) and len(B)==109
    # The directory baselines are independently pinned to all archive bytes.
    for rel in B:
        assert safe_bytes(base/rel)==B[rel] and safe_bytes(ou/rel)==O[rel] and safe_bytes(rc/rel)==R[rel],rel

ou_changed={p for p in B if O[p]!=B[p]}
rc_changed={p for p in B if R[p]!=B[p]}
overlap=ou_changed&rc_changed
assert overlap=={'config/adc_parameters.m','current/src/model/behavior_ra_noise_guard.m'}
step='current/src/frontend/behavior_frontend_step.m'
cmp_stage={'current/src/control/behavior_control_stage.m',
           'current/src/control/behavior_control_stage_sfun.m'}
cmp_guard='current/src/model/behavior_ra_noise_guard.m'
cmp_note='current/src/model/behavior_applied_note.m'
joint_binding={'current/src/model/behavior_dac_coupling_configuration.m',
               'current/src/physics/behavior_ra_noise_validate_backend.m',
               'current/src/physics/behavior_backend_step.m'}
with ZipFile(cmp_zip) as z:
    for rel in cmp_stage|{'current/src/control/behavior_comparator_sample.m',
                          'current/src/control/behavior_comparator_keyed_normal.m'}:
        assert safe_bytes(candidate/rel)==z.read('candidate/'+rel),rel
control_sfun='current/src/control/behavior_control_stage_sfun.m'
assert safe_bytes(candidate/control_sfun).decode().split('    function outputs(b)',1)[1]== \
    B[control_sfun].decode().split('    function outputs(b)',1)[1]
for rel in B:
    merged=safe_bytes(candidate/rel)
    if rel in cmp_stage or rel==cmp_guard or rel==cmp_note or rel in joint_binding:
        continue # These are checked against the frozen CMP and binding contracts below.
    if rel in overlap:
        result=subprocess.run(['git','merge-file','-p',str(ou/rel),str(base/rel),str(rc/rel)],capture_output=True)
        assert result.returncode==0 and merged==result.stdout,rel
    elif rel==step:
        old='''            v0=s.B_c(j,1)/C(1);v=rc_sine(v0,s.time_s,t,tau,s.input);
            s.B_c(j,1)=C(1)*v;
            s.B_c(j,2:3)=relax(s.B_c(j,2:3),s.B_target_c(j,2:3),dt,p.tau_precharge_s(j));'''
        new='''            % In the new single-bank kTC hold mode, Inf tau means retain the
            % signal charge bit-for-bit, including guard=0. Dividing by C and
            % multiplying back can change its last bit. Keep the historical
            % arithmetic for kTC OFF and for every finite/zero tau.
            if ~(is_single(p)&&p.ktc_enabled&&isinf(tau))
                v0=s.B_c(j,1)/C(1);v=rc_sine(v0,s.time_s,t,tau,s.input);
                s.B_c(j,1)=C(1)*v;
            end
            s.B_c(j,2:3)=relax(s.B_c(j,2:3),s.B_target_c(j,2:3),dt,p.tau_precharge_s(j));'''
        text=R[rel].decode()
        assert text.count(old)==1 and merged==text.replace(old,new).encode(),rel
    elif rel in ou_changed:
        assert merged==O[rel],rel
    elif rel in rc_changed:
        assert merged==R[rel],rel
    else:
        assert merged==B[rel],rel

for rel in ('current/src/frontend/behavior_frontend_pack.m',
            'current/src/frontend/behavior_frontend_unpack.m',
            'current/src/frontend/behavior_frontend_stage.m',
            'current/src/frontend/behavior_frontend_sfun.m',
            'current/src/physics/behavior_backend_pack.m',
            'current/src/physics/behavior_backend_unpack.m',
            'current/src/physics/behavior_backend_sfun.m',
            'current/src/control/behavior_sar_pack.m',
            'current/src/control/behavior_sar_unpack.m',
            'current/src/physics/sar20_ra_keyed_normal.m',
            'current/src/physics/sar20_ra_ou_increment.m'):
    assert safe_bytes(candidate/rel)==B[rel],rel
marker='function dv=sample_ktc_diff(ids,id,epoch,p)'
assert safe_bytes(candidate/step).decode().split(marker,1)[1]==B[step].decode().split(marker,1)[1]
guard=safe_bytes(candidate/'current/src/model/behavior_ra_noise_guard.m').decode()
for text in ('fixed_single_bank_ctop_f','ktcTauOK','tCoverage=t(:)',
             "'sar20RA:unqualifiedCalibration'","'sar20RA:comparatorNoise'"):
    assert text in guard,text
assert 'behavior_comparator_configuration(P,mode)' in guard
assert 'logical(P.ni.comparator_noise)==logical(noise)' in \
    safe_bytes(candidate/'current/src/model/behavior_comparator_configuration.m').decode()
assert 'coarse_noise_rms_v' in guard and 'isfinite(cn)&&cn==0' in guard
assert "if isfield(P,'control')&&isstruct(P.control)&&isscalar(P.control)" in guard
cmp=safe_bytes(candidate/'current/src/model/behavior_comparator_configuration.m').decode()
for text in ('behavior_ra_noise_validate_backend(P.backend)', 'behavior_single_guard(P,true)',
             'fixed_single_bank_ctop_f','validate_joint_ra_binding(P)',
             'abs(P.Ts_s-200e-9)<1e-18',"'sar20Cmp:m8Only'", "'sar20Cmp:scope'",
             "'sar20Cmp:unqualifiedCalibration'",'~logical(P.transport.enabled)'):
    assert text in cmp,text
assert 'sar20Cmp:raNoiseCombination' not in cmp
assert 'hasComparator' in safe_bytes(candidate/'current/src/model/behavior_dac_coupling_configuration.m').decode()
assert "isfield(p.dac_coupling,'fixed_single_bank_ctop_f')" in \
    safe_bytes(candidate/'current/src/physics/behavior_backend_step.m').decode()
assert "isfield(p.dac_coupling,'fixed_single_bank_ctop_f')" in \
    safe_bytes(candidate/'current/src/physics/behavior_ra_noise_validate_backend.m').decode()
assert 'single_bank' in guard and 'nominal(:,38)=0' in guard
note=safe_bytes(candidate/cmp_note).decode()
assert 'OFF注入(采样保持, flag=1)' in note and 'SAR2/TA offset' in note
stage=safe_bytes(candidate/'current/src/physics/behavior_backend_stage.m').decode()
assert 'behavior_backend_step(s,s.command,dt,p,forcing,double(eventTime))' in stage
assert digest(safe_bytes(candidate/'current/models/SarAdc.slx'))=='48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'
# Static graph wiring only: due feedback/CT commit precedes RA comparator VY,
# which is carried through the compare mux into the decision stage. This is
# not a native simulation or a proof of analog settling.
def edges(xml):
    result=set()
    def visit(node,src=None):
        for p in node.findall('P'):
            if p.get('Name')=='Src':src=p.text
        for p in node.findall('P'):
            if p.get('Name')=='Dst':result.add((src,p.text))
        for branch in node.findall('Branch'):visit(branch,src)
    for line in ET.fromstring(xml).findall('Line'):visit(line)
    return result
required={
 'simulink/systems/system_244.xml':{('331#out:3','329#in:3'),('329#out:1','327#in:3'),('327#out:1','259#in:1')},
 'simulink/systems/system_112.xml':{('244#out:4','261#in:7'),('261#out:5','279#in:2'),('279#out:1','285#in:4')},
 'simulink/systems/system_261.xml':{('270#out:1','334#in:1'),('334#out:2','277#in:1')},
 'simulink/systems/system_279.xml':{('283#out:1','343#in:1'),('343#out:1','339#in:3'),('339#out:1','284#in:1')},
 'simulink/systems/system_285.xml':{('291#out:1','346#in:4')},
}
with ZipFile(candidate/'current/models/SarAdc.slx') as graph:
    for path,need in required.items():assert need<=edges(graph.read(path)),path
print(json.dumps({'status':'PASS_static_source_merge_only','m_files_compared':len(B),
    'ou_only':sorted(ou_changed-rc_changed),'rc_only':sorted(rc_changed-ou_changed),
    'merged_overlap':sorted(overlap),'guard0_inf_signal_hold_fix':True,
    'unchanged_state_pack_frontend_backend_sfunctions':True,
    'control_sfun_matches_archived_cmp_candidate':True,'noise_key_helpers_unchanged':True,
    'control_sfun_outputs_body_unchanged':True,
    'comparator_sources_match_archived_cmp_candidate':True,
    'graph_static_due_ct_vy_decide_wiring':True,
    'graph_sha256':digest(safe_bytes(candidate/'current/models/SarAdc.slx')),
    'matlab_or_simulink_run_for_merged_candidate':False},indent=2))
