#!/usr/bin/env python3
"""Read-only identity and source-contract checks; never runs MATLAB/model."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
candidate=root.parent/'merged_ou_rc_20261104_toyFVb/candidate'


def sha(p):
    assert p.is_file() and p.stat().st_size<300_000_000,p
    return hashlib.sha256(p.read_bytes()).hexdigest()


manifest='73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c'
assert sha(candidate/'MANIFEST.json')==manifest
assert sha(root/'SOURCE_PINS.json')=='4926aa0182de94450d6ae9c3c178d97dfa46c21418d47fdc9dbe9806f313f120'
assert sha(root/'layout.json')=='fab1aa95520b2e9af897cfe93e539083c8b3afbb8524bae5eedb574559393b31'
pins=json.loads((root/'SOURCE_PINS.json').read_text());assert pins['candidate_manifest_sha256']==manifest
for item in pins['items']:assert sha(candidate/item['path'])==item['sha256'],item['name']
layout=json.loads((root/'layout.json').read_text())
actual={s['name']:(s['first'],s['last']) for s in layout['sources']}
assert layout['width']==2015 and all(actual[k]==v for k,v in {
    'event2':(1,2),'FE_old':(3,355),'FE_final_next':(1415,1767),
    'RA_old':(1768,1815),'RA_advance_next':(1816,1863),
    'RA_final_next':(1960,2007),'RA_advance_obs':(2008,2015)}.items())
observer=(root/'ra_dense_observer.m').read_text()
assert 'pNoNewOu.ra_noise.sigma_vx_rms=0' in observer
assert 'pNoNewOu.ni.ra_noise=false' not in observer
assert "behavior_backend_stage('advance',bk0,t1,zeros(26,1),p,fe0)" in observer
assert "behavior_backend_stage('advance',bk0,q(k),zeros(26,1),pNoNewOu,fe0)" in observer
assert "bits(replayedState,endState)&&bits(replayedObs,endObs)" in observer
assert "bits(fe0,checkvec(record.fe_old_at_stop353,353))" in observer
assert "bits(bk0,checkvec(record.ra_old_at_stop48,48))" in observer
ou=(candidate/'current/src/physics/sar20_ra_ou_increment.m').read_text()
assert ou.index('if sigma_vx_rms == 0 ||')<ou.index('[z,digest_hex] = sar20_ra_keyed_normal')
assert 'return;' in ou[ou.index('if sigma_vx_rms == 0 ||'):ou.index('[z,digest_hex] = sar20_ra_keyed_normal')]
wrapper=(root/'ra_dense_from_tap.m').read_text()
for text in ('x(i,1415:1767)','x(i,1960:2007)','x(j,3:355)',
             'x(j,1768:1815)','x(j,1816:1863)','x(j,2008:2015)'):
    assert text in wrapper,text
print(json.dumps({'status':'static_contract_checks_passed',
    'candidate_manifest_sha256':manifest,'source_files_pinned':len(pins['items']),
    'layout_sha256':sha(root/'layout.json'),'sigma_zero_before_keyed_normal':True,
    'endpoint_state_and_observation_bit_gates_present':True,
    'actual_2015_tap_available_in_this_check':False,
    'matlab_or_simulink_executed':False},indent=2))
