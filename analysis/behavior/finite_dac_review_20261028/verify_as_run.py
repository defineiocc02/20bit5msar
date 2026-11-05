#!/usr/bin/env python3
"""Read-only verification of archived SAR20 as-run output; never run a model.

See README.md for the exact supported N8/N256 transport-on scope. No files are
written: JSON goes to stdout and the caller chooses whether to save it elsewhere.
Requires numpy, h5py and scipy. Existing logs, times, states and invalid words
are never replaced with reconstructed samples or filtered to make a run pass.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import h5py
import numpy as np
from scipy.linalg import expm


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def same(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def val(f, path):
    n = f[path]
    a = np.asarray(n[()])
    cls = n.attrs.get('MATLAB_class', b'')
    if cls == b'char':
        return ''.join(map(chr, a.ravel()))
    return a.ravel()[0].item() if a.size == 1 else a.T


def fingerprint(f, n, memo):
    addr = h5py.h5o.get_info(n.id).addr
    if addr in memo:
        return memo[addr]
    cls = str(n.attrs.get('MATLAB_class', b''))
    if isinstance(n, h5py.Group):
        value = ('g', cls, tuple((k, fingerprint(f, n[k], memo)) for k in sorted(n)))
    else:
        a = np.asarray(n[()])
        if h5py.check_dtype(ref=n.dtype) is not None:
            value = ('r', cls, a.shape,
                     tuple(fingerprint(f, f[r], memo) if r else None for r in a.ravel()))
        else:
            value = ('d', cls, a.shape, a.dtype.str, hashlib.sha256(a.tobytes()).hexdigest())
    memo[addr] = hashlib.sha256(repr(value).encode()).hexdigest()
    return memo[addr]


def pdiff(a, b):
    with h5py.File(a, 'r') as f, h5py.File(b, 'r') as g:
        fm, gm, result = {}, {}, []
        def walk(x, y, path):
            if fingerprint(f, x, fm) == fingerprint(g, y, gm):
                return
            if isinstance(x, h5py.Group) and isinstance(y, h5py.Group):
                for k in sorted(set(x) | set(y)):
                    if k not in x or k not in y:
                        result.append(path + '/' + k)
                    else:
                        walk(x[k], y[k], path + '/' + k)
            else:
                result.append(path)
        walk(f['P'], g['P'], 'P')
        return result


def read_logs(path):
    # Read actual serialized Time/Data arrays, not a reconstructed uniform axis.
    with h5py.File(path, 'r') as h:
        seq = [h[r] for r in h['#subsystem#/MCOS'][()].ravel()]
        candidates = [x for x in seq if isinstance(x, h5py.Group)
                      and {'raw_log', 'event_log'} <= set(x)]
        need(len(candidates) == 1, 'Unsupported or ambiguous SimulationOutput layout')
        s = candidates[0]
        names = [n for _, n in sorted((int(s[n][()].ravel()[4]), n)
                 for n in s if n not in ('tout', 'yout'))]
        arr = []
        for i, d in enumerate(seq):
            if i < 11 or not isinstance(d, h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape) < 2:
                continue
            ns, t = seq[i-11], seq[i-9]
            if not (isinstance(ns, h5py.Dataset) and ns.dtype == np.dtype('float64')
                    and ns.shape == (1, 1) and isinstance(t, h5py.Dataset)
                    and t.dtype == np.dtype('float64')):
                continue
            count = int(ns[()].item())
            if count > 0 and t.shape == (1, count) and (count == 1 or d.shape[-1] == count):
                cls = d.attrs.get('MATLAB_class', b'')
                cls = cls.decode() if isinstance(cls, bytes) else str(cls)
                time = t[()].T[:, 0]
                need(np.all(np.isfinite(time)) and np.all(np.diff(time) >= 0),
                     'Nonfinite or nonmonotonic native Time')
                arr.append({'time': time, 'data': d[()].reshape((-1, count)).T,
                            'class': cls, 'storage_shape': d.shape})
        need(len(names) == len(arr) and len(names) == len(set(names)),
             f'Unsupported MCOS logger layout: {len(names)} names, {len(arr)} arrays')
        return dict(zip(names, arr))


def at(log, times, label):
    times = np.asarray(times, dtype=float).reshape(-1)
    t = log['time']
    ix = np.searchsorted(t, times)
    need(np.all(ix < len(t)), f'{label} lacks actual timestamp')
    need(np.all(t[ix] == times), f'{label} lacks exact actual timestamp')
    need(all(np.count_nonzero(t == v) == 1 for v in times), f'{label} has ambiguous timestamps')
    return log['data'][ix]


def graph(path):
    blocks, edges, config = {}, set(), []
    with zipfile.ZipFile(path, 'r') as z:
        for name in z.namelist():
            if name.startswith('simulink/configSet') and name.endswith('.xml'):
                config.extend((p.get('Name'), p.text) for p in ET.fromstring(z.read(name)).iter('P'))
            if not (name.startswith('simulink/systems/') and name.endswith('.xml')):
                continue
            root = ET.fromstring(z.read(name))
            for b in root.findall('Block'):
                sid = b.get('SID')
                need(sid not in blocks, 'Duplicate SLX SID ' + str(sid))
                blocks[sid] = (b.get('Name'), b.get('BlockType'),
                               {p.get('Name'): p.text for p in b.findall('P')})
            for line in root.findall('Line'):
                src = line.find("P[@Name='Src']")
                if src is not None:
                    edges.update((src.text, d.text) for d in line.iter('P') if d.get('Name') == 'Dst')
    return blocks, edges, config


def archive_provenance(run, summary, scratch):
    model = run / ('SarDac.slx' if scratch else 'SarAdc.slx')
    need(model.is_file(), 'Missing as-run SLX: ' + str(model))
    files = {p: sha(run / p) for p in ['parameters.mat', 'simout.mat', 'summary.json', model.name]}
    need(files[model.name] == summary.get('model_sha256'), 'As-run SLX != saved summary model SHA')
    if scratch:
        return files, 'Scratch archive: no production source.zip/manifest claim.'
    for p in ['source.zip', 'source_manifest.json']:
        need((run / p).is_file(), 'Missing as-run provenance ' + p)
        files[p] = sha(run / p)
    need(files['parameters.mat'] == summary.get('config_sha256'), 'P hash != summary')
    need(files['source.zip'] == summary.get('source_zip_sha256'), 'Source ZIP hash != summary')
    manifest = json.loads((run / 'source_manifest.json').read_text())['files']
    if 'source_files' in summary:
        m = {(r['path'].replace('\\', '/'), r['sha256']) for r in manifest}
        s = {(r['path'].replace('\\', '/'), r['sha256']) for r in summary['source_files']}
        need(m == s, 'Saved source manifest and summary source pins differ')
    with zipfile.ZipFile(run / 'source.zip', 'r') as z:
        names = z.namelist()
        need(len(names) == len(set(names)), 'Source ZIP has duplicate names')
        for row in manifest:
            name = row['path'].replace('\\', '/')
            need(name in names, 'Source manifest file missing in ZIP: ' + name)
            need(hashlib.sha256(z.read(name)).hexdigest() == row['sha256'],
                 'Source ZIP hash mismatch: ' + name)
        need(set(names) == {r['path'].replace('\\', '/') for r in manifest},
             'Source ZIP differs from manifest inventory')
    return files, ('Saved source ZIP and manifest match; no independent MATLAB per-function '
                   'which/call trace is implied.')


def read_calendar(f):
    gr = f['P/adc_groups']
    times = [float(f[r][()][0, 0]) for r in gr['time_s'][()].ravel()]
    groups = []
    for ref in gr['events'][()].ravel():
        typ = f[ref]['type']
        if isinstance(typ, h5py.Dataset) and h5py.check_dtype(ref=typ.dtype) is not None:
            groups.append([''.join(map(chr, f[r][()].ravel())) for r in typ[()].ravel()])
        else:
            groups.append([''.join(map(chr, typ[()].ravel()))])
    need(len(groups) == len(times) == 48, 'Expected saved 48 actual ADC groups')
    budget = {t: sum(k.count(t) for k in groups)
              for t in ['d2_decide', 'ta_compare', 'ta_feedback']}
    need(list(budget.values()) == [12, 8, 7], 'Saved ADC calendar token budget changed')
    return times, groups, budget


def decode(row, dig):
    d1, d2, dt = (int(x) for x in row[:3])
    need(0 <= d1 < 2048 and 0 <= d2 < 4096 and 0 <= dt < 256, 'RAW word out of range')
    c, fine = divmod(d1, 32)
    v1 = (32*c + 2*fine - 1039)*dig['vref_v']/1024 - 17*dig['vref_v']/1024
    b2 = np.array([(d2 >> i) & 1 for i in range(11, -1, -1)])
    bt = np.array([(dt >> i) & 1 for i in range(7, -1, -1)])
    v2 = (dig['d2_offset_ra_v'] + np.sum(np.asarray(dig['d2_weights_ra_v']).ravel()*b2))/dig['ra_gain']
    vt = dig['tracking_step_ra_v']*np.sum(np.arange(8, 0, -1)*(2*bt-1))/8/dig['ra_gain']
    # Match the archived decoder's parenthesized binary64 operation order.
    unsat = ((v1+v2)+vt)*(2**20/dig['fsr_diff_v']) + 2**19
    rounded = math.floor(unsat+.5) if unsat >= 0 else math.ceil(unsat-.5)
    return int(np.clip(rounded, 0, 2**20-1))


def clean(x):
    x = float(x)
    return x if math.isfinite(x) else ('NaN' if math.isnan(x) else ('Inf' if x > 0 else '-Inf'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--baseline', type=Path, required=True,
                    help='actual same-N pre-promotion or scratch-off baseline')
    ap.add_argument('--expect', choices=['off', 'zero', 'finite', 'hold', 'legacy'], required=True)
    ap.add_argument('--scratch', action='store_true', help='historical scratch only; never a promotion verdict')
    ap.add_argument('--source-pins', type=Path,
                    help='reviewed expected source pin JSON; required for production candidate')
    args = ap.parse_args()
    run, base = args.run.resolve(), args.baseline.resolve()
    summary = json.loads((run / 'summary.json').read_text())
    files, source_boundary = archive_provenance(run, summary, args.scratch)
    base_scratch = (base / 'SarDac.slx').is_file()
    base_summary = json.loads((base / 'summary.json').read_text())
    base_files, base_boundary = archive_provenance(base, base_summary, base_scratch)
    base_status = base_summary.get('status') == 'complete' or (base_scratch and
                   base_summary.get('status') == 'actual_N8_old_all_logs_bit_exact')
    need(base_status and base_summary.get('simulation_completed', False), 'Baseline is not a completed capture')
    result = {'schema': 'sar20-finite-dac-as-run-readonly/v1', 'run': str(run),
              'baseline': str(base), 'expect': args.expect, 'scratch': args.scratch,
              'sha256': files, 'baseline_sha256': base_files,
              'verifier_sha256': sha(Path(__file__).resolve()),
              'source_execution_boundary': source_boundary, 'baseline_source_boundary': base_boundary,
              'analytic_tolerance_used': [], 'analytic_pass_declared': False,
              'scope': 'Actual saved behavioral run only; no simulation, ADC physics, silicon or signoff claim.'}
    model = run / ('SarDac.slx' if args.scratch else 'SarAdc.slx')
    blocks, edges, config = graph(model)
    base_model = base / ('SarDac.slx' if base_scratch else 'SarAdc.slx')
    base_blocks, base_edges, base_config = graph(base_model)
    need(blocks.get('237', (None,))[0] == 'FE_old' and blocks.get('321', (None,))[0] == 'RaAdvance',
         'SLX expected FE_old/RaAdvance SID identity changed; inspect manually')
    binding = blocks['321'][2].get('Parameters', '')
    old_fe_edge = ('237#out:1', '321#in:4') in edges
    checked_binding = ''.join(binding.split()) == "'advance',behavior_dac_backend_parameters(P)"
    probes = [sid for sid, v in blocks.items() if v[2].get('VariableName') == 'dac_ra_pre_log']
    need(len(probes) <= 1, 'Duplicate DAC RA pre-CINC observer')
    probe_edge = len(probes) == 1 and blocks[probes[0]][1] == 'ToWorkspace' and \
                 ('321#out:2', probes[0]+'#in:1') in edges
    result['as_run_graph'] = {'old_FE_to_advance_input4': old_fe_edge,
                              'RaAdvance_dialog': binding, 'checked_binding': checked_binding,
                              'actual_RaAdvance_pre_CINC_probe_edge': bool(probe_edge),
                              'added_native_edges_vs_baseline': sorted([list(x) for x in edges-base_edges]),
                              'removed_native_edges_vs_baseline': sorted([list(x) for x in base_edges-edges]),
                              'unit_delay_trigger_inventory_unchanged': sorted((s,v[0],v[1]) for s,v in blocks.items()
                                  if v[1] in ('UnitDelay','TriggerPort')) == sorted((s,v[0],v[1])
                                  for s,v in base_blocks.items() if v[1] in ('UnitDelay','TriggerPort')),
                              'solver_config_P_inventory_equal': config == base_config}
    need(not (base_edges-edges), 'An original as-run baseline native graph edge was removed')
    need(result['as_run_graph']['unit_delay_trigger_inventory_unchanged'], 'UnitDelay/Trigger inventory changed')
    need(result['as_run_graph']['solver_config_P_inventory_equal'], 'SLX solver/config parameters differ')
    if args.expect != 'legacy':
        need(old_fe_edge, 'As-run SLX lacks FE_old to RaAdvance input 4')
        if probes:
            need(probe_edge, 'As-run DAC probe does not come directly from RaAdvance output 2')
        allowed_new_edges = {('237#out:1','321#in:4')}
        if probes: allowed_new_edges.add(('321#out:2', probes[0]+'#in:1'))
        need(edges-base_edges <= allowed_new_edges, 'Unexpected new native graph edges versus baseline')
        if not args.scratch:
            need(checked_binding, 'As-run SLX lacks checked DAC binding expression')
            need(args.source_pins is not None, 'Candidate production verification requires reviewed --source-pins')
            pins_path = args.source_pins.resolve()
            pins = json.loads(pins_path.read_text())['files']
            wanted = {'current/src/model/behavior_applied_note.m',
                      'current/src/model/behavior_dac_backend_parameters.m',
                      'current/src/model/behavior_dac_coupling_configuration.m',
                      'current/src/model/behavior_prepare_configuration.m',
                      'current/src/model/behavior_training_configuration.m',
                      'current/src/physics/behavior_backend_sfun.m',
                      'current/src/physics/behavior_backend_stage.m',
                      'current/src/physics/behavior_backend_step.m',
                      'current/src/physics/behavior_dac_forcing_from_frontend.m',
                      'config/make_training_case.m'}
            need(set(pins) == wanted, 'Source pin inventory must contain the 10 reviewed runtime files')
            with zipfile.ZipFile(run / 'source.zip', 'r') as z:
                for name, expected in pins.items():
                    need(name in z.namelist() and hashlib.sha256(z.read(name)).hexdigest() == expected,
                         'As-run source differs from reviewed candidate pin: ' + name)
            result['reviewed_source_pin_sha256'] = sha(pins_path)
            result['reviewed_source_files_match'] = len(pins)

    logs, old = read_logs(run / 'simout.mat'), read_logs(base / 'simout.mat')
    required = {'event_log': 2, 'adc_executed_log': 1, 'raw_log': 6, 'ready_log': 1,
                'record_log': 6, 'record_ready_log': 1, 'code_log': 1,
                'front_log': 7, 'back_log': 8, 'control_log': 13,
                'frame_ready_log': 1, 'sample_ready_log': 1, 'transport_frame_log': 12}
    for name, width in required.items():
        need(name in logs and logs[name]['data'].shape[1] == width, 'Missing/malformed actual ' + name)
    d = pdiff(base / 'parameters.mat', run / 'parameters.mat')
    allowed = {'P/front/tau_dac_s', 'P/backend/dac_coupling', 'P/backend/dac_coupling/enabled',
               'P/backend/dac_coupling/tau_dac_s', 'P/backend/dac_coupling/frontend_schema',
               'P/backend/dac_coupling/public_plan', 'P/ni/dac_settling',
               'P/debug/dac_enabled', 'P/debug/dac_max_points'}
    result['saved_P_differences_vs_baseline'] = d
    need(set(d) <= allowed, 'Unexpected saved P differences: ' + repr(sorted(set(d)-allowed)))
    with h5py.File(run / 'parameters.mat', 'r') as f:
        N, first, epoch = (int(val(f, 'P/'+k)) for k in ['N', 'first_id', 'epoch'])
        Ts = float(val(f, 'P/Ts_s'))
        need(N in (8, 256), 'Only N8 or N256 is in scope')
        need(bool(val(f, 'P/transport/enabled')), 'This verifier requires actual transport ON')
        need(not val(f, 'P/backend/ni/az') and val(f, 'P/backend/az/mode') == 'off', 'AZ must be off')
        need(not val(f, 'P/training/enabled') and not val(f, 'P/frozen/enabled'),
             'Training/frozen must be off')
        need(val(f, 'P/digital/calibration_mode') == 'off' and not val(f, 'P/digital/dither_enabled'),
             'Decoder must be nominal and dither off')
        tau = np.asarray(val(f, 'P/front/tau_dac_s')).ravel()
        need(len(tau) == 18 and np.all(~np.isnan(tau)) and np.all(tau >= 0), 'Invalid saved DAC tau')
        en = bool(val(f, 'P/backend/dac_coupling/enabled')) if 'P/backend/dac_coupling/enabled' in f else False
        if args.expect != 'legacy':
            for a, b in [('P/front/tau_dac_s', 'P/backend/dac_coupling/tau_dac_s'),
                         ('P/front/schema', 'P/backend/dac_coupling/frontend_schema'),
                         ('P/front/plan', 'P/backend/dac_coupling/public_plan')]:
                need(a in f and b in f and fingerprint(f, f[a], {}) == fingerprint(f, f[b], {}),
                     'Prepared DAC binding differs from actual saved ' + a)
        ni = bool(val(f, 'P/ni/dac_settling'))
        need(ni == bool(en and np.any(np.isfinite(tau) & (tau > 0))), 'NI coverage flag mismatch')
        if args.expect == 'off': need(not en and np.all(tau == 0), 'Expected disabled / all-zero tau')
        if args.expect == 'zero': need(en and np.all(tau == 0), 'Expected enabled / all-zero tau')
        if args.expect == 'finite': need(en and np.all(np.isfinite(tau)) and np.any(tau > 0),
                                         'Expected enabled positive finite tau without Inf-held slices')
        if args.expect == 'hold': need(en and np.all(np.isinf(tau)) and not ni, 'Expected all-Inf nonsettling hold')
        times, groups, budget = read_calendar(f)
        parent_times = [float(f[ref][()][0,0]) for ref in f['P/groups/time_s'][()].ravel()]
        need(len(parent_times) == 49, 'Expected saved 49 parent groups')
        latch = [i+1 for i, g in enumerate(groups) if 'raw_latch' in g]
        need(len(latch) == 1, 'Saved ADC calendar must contain one raw_latch group')
        ra = {k: val(f, 'P/backend/ra/'+k) for k in ['Cf_f', 'A0', 'UGB_hz', 'vos_input_v', 'slew_v_per_s']}
        dig = {k: val(f, 'P/digital/'+k) for k in ['vref_v', 'fsr_diff_v', 'ra_gain',
                'd2_offset_ra_v', 'd2_weights_ra_v', 'tracking_step_ra_v']}
        probe = bool(val(f, 'P/debug/dac_enabled')) if 'P/debug/dac_enabled' in f else False
        fs = float(val(f, 'P/fs_hz')); fin = float(val(f, 'P/input/frequency_hz'))
        result['configuration'] = {'N': N, 'first_id': first, 'epoch': epoch, 'transport': 'on',
                                   'dac_coupling': en, 'tau_s': [clean(x) for x in tau],
                                   'finite_dac_NI': ni, 'probe_enabled': probe,
                                   'saved_calendar_token_budget': budget}
    with h5py.File(base / 'parameters.mat', 'r') as f:
        need(int(val(f, 'P/N')) == N and int(val(f, 'P/first_id')) == first and
             int(val(f, 'P/epoch')) == epoch, 'Baseline capture window differs')
    for name in ('event_log', 'adc_executed_log'):
        need(name in old and same(logs[name]['time'], old[name]['time']) and
             same(logs[name]['data'], old[name]['data']), 'Actual event time/data differs from baseline: '+name)
    if args.expect in ('off', 'zero'):
        mismatch = [k for k, v in old.items() if k not in logs or v['class'] != logs[k]['class']
                    or not same(v['time'], logs[k]['time']) or not same(v['data'], logs[k]['data'])]
        result['baseline_original_logs'] = {'count': len(old), 'mismatched': mismatch}
        need(not mismatch, 'Old-log Time/Data/class/shape/bit gate failed: ' + repr(mismatch))

    e = logs['event_log']['data']; te = logs['event_log']['time']
    executed = logs['adc_executed_log']['data'][:, 0]
    need(same(te, logs['adc_executed_log']['time']) and np.all(np.isin(executed, [0, 1])),
         'Actual executed/event time or binary flag invalid')
    need(np.array_equal(executed.astype(bool), (e[:, 1] >= 1) & (e[:, 1] <= 48)),
         'Actual executed events do not correspond to 48 ADC groups')
    rr = logs['record_ready_log']; ready = rr['data'][:, 0]
    need(np.all(np.isin(ready, [0, 1])), 'Actual RX ready is not binary')
    ready_times = rr['time'][ready == 1]
    need(len(np.unique(ready_times)) == len(ready_times), 'Duplicate actual RX ready time')
    records = at(logs['record_log'], ready_times, 'record_log')
    codes = at(logs['code_log'], ready_times, 'code_log')[:, 0]
    in_window = (records[:, 3] >= first) & (records[:, 3] < first+N)
    r, c, rt = records[in_window], codes[in_window], ready_times[in_window]
    # Preserve invalid and nonfinite raw/code; validity is assessed only after capture.
    result['actual_records'] = [{'time_s': float(t), 'raw6': [clean(x) for x in w], 'code20': clean(v)}
                                for t, w, v in zip(rt, r, c)]
    result['unclassified_or_outside_ready_records'] = [
        {'time_s': float(t), 'raw6': [clean(x) for x in w], 'code20': clean(v)}
        for t, w, v, keep in zip(ready_times, records, codes, in_window) if not keep]
    result['validity'] = {'ready_rows_in_window': len(r), 'valid_1': int(np.count_nonzero(r[:, 5] == 1)),
                          'valid_0': int(np.count_nonzero(r[:, 5] == 0)),
                          'valid_other_or_nonfinite': int(np.count_nonzero(~np.isin(r[:, 5], [0, 1]))),
                          'timeout': 'not separately observed',
                          'overrange': 'not independently observed; controller invalid latch is not hardware overrange'}
    failures = []
    valid_status = summary.get('status') == 'complete' or (args.scratch and summary.get('status') == 'actual_N8_old_all_logs_bit_exact')
    if not valid_status or not summary.get('simulation_completed', False):
        failures.append('Saved summary does not establish complete simulation')
    if len(r) != N or not np.array_equal(r[:, 3], np.arange(first, first+N)) or not np.all(r[:, 4] == epoch):
        failures.append('Selected RX ready IDs/order/epoch differ from saved P')
    if not np.all(r[:, 5] == 1):
        failures.append('Selected capture contains invalid or unknown valid values')
    if len(failures):
        result['checks_passed'] = False; result['promotion_accepted'] = False; result['failures'] = failures
        result['downstream_checks'] = 'not attempted due to selected-record failure; invalid rows retained above'
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)); return 1

    if not args.scratch:
        selected = run / 'selected.mat'
        need(selected.is_file() and sha(selected) == summary.get('selected_sha256'),
             'Completed run selected.mat missing or inconsistent with summary hash')
        with h5py.File(selected, 'r') as f:
            need(same(np.asarray(f['selected/raw'][()]).T, r) and
                 same(np.asarray(f['selected/code20'][()]).ravel(), c) and
                 same(np.asarray(f['selected/time_s'][()]).ravel(), rt),
                 'selected.mat differs from actual ready RAW/code/time')
        result['sha256']['selected.mat'] = sha(selected)
        result['selected_snapshot_matches_actual_ready_RAW_code_time'] = True

    need(np.all(np.isfinite(r)) and np.all(np.isfinite(c)) and np.all(c == np.floor(c)) and
         np.all((0 <= c) & (c < 2**20)), 'Valid records contain malformed RAW/code')
    ar = logs['ready_log']; adc_ready = ar['data'][:, 0]
    need(np.all(np.isin(adc_ready, [0, 1])), 'ADC ready is not binary')
    atime = ar['time'][adc_ready == 1]; aw = at(logs['raw_log'], atime, 'raw_log')
    need(len(np.unique(atime)) == len(atime), 'Duplicate ADC ready time')
    need(all(np.all(w[:3] == np.floor(w[:3])) for w in r), 'Valid RAW words are not integers')
    for row, code, recv_time in zip(r, c, rt):
        ident = int(row[3]); take = np.flatnonzero((e[:, 0] == ident) & (executed == 1))
        need(len(take) == 48 and np.array_equal(e[take, 1], np.arange(1, 49)),
             f'Actual 48 groups missing/duplicated for ID {ident}')
        need(same(te[take], np.array([ident*Ts+t for t in times])), 'Actual event time != saved calendar')
        ai = np.flatnonzero((aw[:, 3] == ident) & (aw[:, 4] == epoch))
        need(len(ai) == 1 and same(aw[ai[0]], row), 'ADC-to-RX RAW6 mismatch')
        ae = at(logs['event_log'], [atime[ai[0]]], 'ADC-ready event')[0]
        need(ae[0] == ident and ae[1] == latch[0], 'ADC ready is not the actual raw_latch event')
        ri = np.flatnonzero(te == recv_time)
        need(len(ri) == 1 and e[ri[0], 0] == ident+2 and e[ri[0], 1] == 49 and executed[ri[0]] == 0,
             'RX ready is not actual later N-2 group49')
        need(same(np.float64(recv_time), np.float64((ident+2)*Ts+parent_times[48])),
             'Actual RX time != saved parent slot expression')
        need(atime[ai[0]] < recv_time, 'RX ready does not follow ADC ready')
        frame = at(logs['transport_frame_log'], [recv_time], 'transport frame')[0]
        frame_ready = at(logs['frame_ready_log'], [recv_time], 'frame ready')[0,0]
        sample_ready = at(logs['sample_ready_log'], [recv_time], 'sample ready')[0,0]
        need(frame_ready == sample_ready == 1 and same(frame[[2,3,4,5,6,8]], row),
             'Actual valid RX frame/sample/RAW6 disagree')
        need(decode(row, dig) == int(code), 'Independent nominal code from actual RAW mismatch')
    result['actual_event_and_io'] = {
        '48_groups_per_selected_id': True, 'actual_calendar_bits_match_saved_P': True,
        'baseline_event_Time_Data_bits_match': True, 'ADC_and_RX_RAW6_same_id_epoch': True,
        'ADC_ready_actual_raw_latch': True, 'RX_ready_actual_group49_id_plus_2': True,
        'RX_actual_time_matches_saved_parent_slot': True, 'actual_valid_RX_frame_same_RAW6': True,
        'nominal_RAW_decode_exact': True,
        'comparator_counts': 'saved 12/8/7 token budget; individual comparator counter history not independently logged',
        'reset_state': 'BackLog is pre-final-reset; committed reset state not asserted'}

    interval = {'status': 'not recorded: no complete actual RaAdvance pre-CINC probe'}
    if probe:
        need(N == 8 and 'dac_ra_pre_log' in logs and probe_edge,
             'Enabled full probe requires N8 logger and actual RaAdvance source edge')
        need(np.all(tau == tau[0]) and (tau[0] >= 0), 'Interval posterior only supports uniform tau')
        need(math.isinf(float(ra['slew_v_per_s'])), 'Interval posterior only supports linear RA')
        p = logs['dac_ra_pre_log']
        need(same(p['time'], te[executed == 1]), 'Probe is not actual 48 ADC event times')
        start = [i for i, k in enumerate(groups) if 'ra_start' in k]
        stop = [i for i, k in enumerate(groups) if 'd2_prepare' in k]
        need(len(start) == 1 and stop and start[0] < stop[0], 'Invalid RAstart/D2 interval')
        g0, g1 = start[0]+1, stop[0]+1
        for kinds in groups[g0:g1]:
            need(not set(kinds) & {'coarse_latch','fine_prepare','fine_feedback','fine_decide','release'},
                 'D1 command/release inside interval')
        rows = []
        for row in r:
            ident = int(row[3]); ids = np.flatnonzero(e[:, 0] == ident)
            a = ids[e[ids, 1] == g0]; b = ids[e[ids, 1] == g1]
            need(len(a) == len(b) == 1, 'Missing/duplicate interval endpoints')
            t0, t1 = te[a[0]], te[b[0]]; h = t1-t0
            f0 = at(logs['front_log'], [t0], 'FrontLog t0')[0]
            f1 = at(logs['front_log'], [t1], 'FrontLog t1')[0]
            b0 = at(logs['back_log'], [t0], 'BackLog t0')[0]
            p1 = at(p, [t1], 'RaAdvance pre t1')[0]
            ctr = at(logs['control_log'], [t0,t1], 'Control interval')
            need(np.all(np.isfinite(np.r_[f0, f1, b0, p1, ctr.ravel()])) and h > 0,
                 'Nonfinite actual interval observation')
            need(ctr[0,1] == ctr[1,1] == 1 and ctr[0,11] == ctr[1,11] == ctr[1,12] == 0,
                 'Actual RA active / no-new-D1 / release phase gate failed')
            need(same(f0[4], f1[4]), 'Actual Ctop changed in interval')
            q0, q1, cf = f0[2], f1[2], float(ra['Cf_f'])
            ng = 1+f0[4]/cf; gain = 1 if math.isinf(ra['A0']) else ra['A0']/(ra['A0']+ng)
            R = ng/(2*math.pi*ra['UGB_hz']); D = float(tau[0])
            need(math.isfinite(R) and R > 0 and same(p1[3], q1/cf) and same(p1[4], ng) and same(p1[5], R),
                 'Actual pre-CINC endpoint target/NG/tau bit gate failed')
            if D == 0 or math.isinf(D):
                need(same(q0,q1), 'Zero/Inf should preserve interval endpoint Q bits'); delta = 0.; qinf = q0; y = 0.
            else:
                delta = (q1-q0)/(-math.expm1(-h/D)); qinf = q0+delta; y = h/D
            x = h/R
            M = np.array([[-x, -gain*(delta/cf)*x, gain*(qinf/cf+ng*ra['vos_input_v'])*x],
                          [0, -y, 0], [0, 0, 0]])
            prediction = (expm(M) @ np.array([b0[0], 1., 1.]))[0]
            rows.append({'id': ident, 't0_s': float(t0), 't1_s': float(t1),
                         'Q0_C': float(q0), 'Q1_C': float(q1), 'inferred_Qinf_C': float(qinf),
                         'actual_pre_VX_V': float(p1[0]), 'independent_expm_VX_V': float(prediction),
                         'raw_delta_V': float(p1[0]-prediction)})
        interval = {'status': 'actual endpoint deltas reported; no numerical pass/tolerance declared',
                    'group_start': g0, 'group_end': g1, 'rows': rows,
                    'max_abs_delta_V': max(abs(x['raw_delta_V']) for x in rows),
                    'boundary': 'Qinf inferred from actual FE endpoints; coupling posterior, not an independent FE physics oracle'}
    result['interval'] = interval
    if N == 256 and args.expect != 'hold':
        # Existing native coherence threshold, no automatic input or tolerance changes.
        ratio = fin*N/fs; fundamental = int(math.floor(ratio+.5))
        need(math.isfinite(fs) and fs > 0 and math.isfinite(fin) and
             0 < fundamental < N/2 and abs(ratio-fundamental) < 1e-9,
             'Saved input does not meet the native coherent FFT condition')
        volts = ((c+.5)/2**20-.5)*dig['fsr_diff_v']
        transform = np.fft.fft(volts-volts.mean())/N
        power = np.abs(transform[:N//2+1])**2; power[1:-1] *= 2
        other = power.copy(); other[[0, fundamental]] = 0
        harmonic = np.mod(np.arange(2,11)*fundamental, N)
        harmonic = np.setdiff1d(np.unique(np.minimum(harmonic, N-harmonic)), [0, fundamental])
        signal = power[fundamental]; nd = other.sum(); hd = power[harmonic].sum(); noise = nd-hd
        need(signal > 0 and nd > 0 and noise > 0 and hd > 0 and other.max() > 0,
             'Actual FFT power is degenerate; no metric invented')
        metrics = {'snr_db': float(10*np.log10(signal/noise)), 'sndr_db': float(10*np.log10(signal/nd)),
                   'sfdr_db': float(10*np.log10(signal/other.max())), 'thd_db': float(10*np.log10(hd/signal))}
        metrics['enob'] = (metrics['sndr_db']-1.76)/6.02
        result['actual_code_fft'] = {'fs_hz': fs, 'fin_hz': fin, 'fundamental_bin': fundamental,
            'harmonic_bins_H2_to_H10': harmonic.tolist(), 'metrics': metrics,
            'numpy_minus_saved_summary': {k: metrics[k]-summary[k] for k in metrics if k in summary},
            'boundary': 'Valid actual codes only; one coherent rectangular tone, H2-H10; '
                        'differences are reported without an added numerical acceptance tolerance.'}
    else:
        result['actual_code_fft'] = {'status': 'not run for N8 or Inf hold negative case'}
    result['checks_passed'] = True
    result['promotion_accepted'] = False
    result['checks_boundary'] = ('IO/timing and applicable bit gates only; analytic interval has no tolerance '
                                 'or pass verdict; this script does not grant promotion acceptance.')
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)); return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, IndexError, TypeError) as exc:
        print(json.dumps({'checks_passed': False, 'promotion_accepted': False, 'error': str(exc),
                          'boundary': 'Check failed or unsupported archive; no numerical verdict.'},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
