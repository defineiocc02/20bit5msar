#!/usr/bin/env python3
"""Read-only graph/source comparison of the saved 024439 scratch binding gate."""
from pathlib import Path
import json
from verify_as_run import graph, need, sha

root = Path(__file__).resolve().parents[3]
run = root / 'runs/az_probe_20261027T024439Z'
previous = root / 'runs/az_probe_20261027T023003Z'
a, ea, ca = graph(run/'binding/before.slx')
b, eb, cb = graph(run/'binding/after.slx')
need(a.keys() == b.keys(), 'Block inventory changed')
need(all(a[k][:2] == b[k][:2] for k in a), 'Block name/type changed')
changes = []
for sid in sorted(a):
    ap, bp = a[sid][2], b[sid][2]
    for key in sorted(set(ap) | set(bp)):
        if ap.get(key) != bp.get(key):
            changes.append([sid, key, ap.get(key), bp.get(key)])
expected = [['321', 'Parameters', "'advance',P.backend",
             "'advance',behavior_dac_backend_parameters(P)"]]
need(changes == expected, 'Unexpected SLX block/dialog differences')
need(ea == eb and ca == cb, 'Graph edge or saved config changed')
need(('237#out:1','321#in:4') in eb, 'Old FE to RA input 4 edge missing')
helper = run/'candidate/runtime/src/model/behavior_dac_backend_parameters.m'
need(sha(helper) == sha(run/'binding/binding_source.m'), 'Saved helper differs from gate source')
paths = ['src/physics/behavior_backend_sfun.m', 'src/physics/behavior_backend_stage.m',
         'src/physics/behavior_backend_step.m', 'src/physics/behavior_dac_forcing_from_frontend.m',
         'src/model/behavior_dac_coupling_configuration.m']
pins = {}
for path in paths:
    a_path = previous/'candidate/runtime'/path
    b_path = run/'candidate/runtime'/path
    need(sha(a_path) == sha(b_path), 'Saved 023003/024439 candidate source differs: '+path)
    pins[path] = sha(b_path)
receipt = json.loads((run/'receipt.json').read_text())
need(receipt['valid_binding_compile'] and not receipt['ADC_simulation_run'] and
     not receipt['main_integrated'], 'Unexpected saved native gate scope')
report = {'schema':'sar20-independent-binding-archive/v1', 'run':str(run),
          'input_sha256':{name:sha(run/name) for name in ['binding/before.slx', 'binding/after.slx',
                          'binding/binding_source.m', 'receipt.json']},
          'block_count_before_after':[len(a),len(b)], 'native_edge_count_before_after':[len(ea),len(eb)],
          'saved_graph_edges_equal':True, 'saved_config_equal':True,
          'only_block_parameter_difference':changes, 'old_FE_to_RA_input4_in_after':True,
          'five_023003_and_024439_saved_candidate_source_hashes':pins,
          'helper_source_matches_binding_snapshot':True,
          'receipt_native_compile_and_rejection_identifiers':{
              'valid_binding_compile':receipt['valid_binding_compile'],
              **{key:receipt[key]['identifier'] for key in
                 ['stale_binding_pure','stale_binding_native','training_rejected',
                  'registered_bench_rejected','frozen_rejected']}},
          'ADC_simulation_run':False, 'main_integrated':False,
          'boundary':'Compile and rejection identifiers are copied from native receipt, '
                     'not re-executed; no per-function MATLAB call trace was independently saved.',
          'verifier_sha256':sha(Path(__file__).resolve())}
print(json.dumps(report,ensure_ascii=False,indent=2))
