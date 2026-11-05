#!/usr/bin/env python3
"""Read-only replay of saved RX codes with two float64 D2 sum orders.

Emits JSON to stdout. Does not execute MATLAB or change saved run files.
The comparison is exact for integer output codes; no tolerance is applied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if not __debug__:
    raise RuntimeError('Do not use Python -O: it disables replay assertions.')
import h5py
import numpy as np

P_SHA = '62138fae71796b749938ef5e91afc622d062e00d2e1e1a585b0333357c5b3131'
SIM_SHA = 'f68d90df2e8e47b1d0a228c3726c1803de7e427abe6df1ad31f74f63a0aa8798'
RUNNER_SHA = '75192d070445373664fd588a479ccd90d5066bd3178b33e480018f5f9753ce7f'
READER_SHA = '3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def round_away_and_clip(x):
    rounded = math.floor(x + 0.5) if x >= 0 else math.ceil(x - 0.5)
    return max(0, min(2**20 - 1, rounded))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[3])
    args = ap.parse_args()
    root = args.project.resolve()
    result = root / 'runs/work_20261030T161056Z/result'
    p_file = result / 'on256/P.mat'
    sim_file = result / 'on256/simout.mat'
    runner = result / 'sar20_ra_ou_transport_n256.m'
    helper = root / 'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
    assert sha(p_file) == P_SHA and sha(sim_file) == SIM_SHA
    assert sha(runner) == RUNNER_SHA and sha(helper) == READER_SHA
    sys.path.insert(0, str(helper.parent))
    import verify_as_run as u

    with h5py.File(p_file, 'r') as f:
        digital = {k: u.val(f, 'P/digital/' + k) for k in
                   ('vref_v', 'fsr_diff_v', 'ra_gain', 'd2_offset_ra_v',
                    'd2_weights_ra_v', 'tracking_step_ra_v')}
        assert int(u.val(f, 'P/transport/enabled')) == 1
        assert int(u.val(f, 'P/backend/ni/ra_noise')) == 1
        assert int(u.val(f, 'P/digital/dither_enabled')) == 0
        assert int(u.val(f, 'P/bank/enabled')) == 0
        assert int(u.val(f, 'P/frozen/enabled')) == 0
        assert u.val(f, 'P/digital/az_mode') == 'off'
    weights = np.asarray(digital['d2_weights_ra_v']).ravel()
    assert len(weights) == 12 and float(digital['ra_gain']) == 32.0

    logs = u.read_logs(sim_file)
    actual_ready = logs['record_ready_log']
    flags = actual_ready['data'][:, 0]
    assert np.all(np.isin(flags, [0, 1]))
    times = actual_ready['time'][flags == 1]
    raw = u.at(logs['record_log'], times, 'record_log')
    codes = u.at(logs['code_log'], times, 'code_log')[:, 0]
    terms = np.column_stack([u.at(logs[name], times, name)[:, 0]
                             for name in ('d1_log', 'd2_log', 'dt_log')])
    assert len(times) == 260 and np.array_equal(raw[:, 3], np.arange(260))
    assert np.all(raw[:, 4] == 1) and np.all(raw[:, 5] == 1)

    def calculate(record, dot):
        d1, d2, dt = (int(v) for v in record[:3])
        coarse, fine = divmod(d1, 32)
        bits2 = np.array([(d2 >> i) & 1 for i in range(11, -1, -1)])
        bits_ta = np.array([(dt >> i) & 1 for i in range(7, -1, -1)])
        d1_v = (32 * coarse + 2 * fine - 1039) * digital['vref_v'] / 1024 - 17 * digital['vref_v'] / 1024
        products = weights * bits2
        weighted = float(np.dot(weights, bits2)) if dot else float(np.sum(products))
        d2_v = (digital['d2_offset_ra_v'] + weighted) / digital['ra_gain']
        dt_v = digital['tracking_step_ra_v'] * np.sum(np.arange(8, 0, -1) * (2 * bits_ta - 1)) / 8 / digital['ra_gain']
        unsat = float(((d1_v + d2_v) + dt_v) * (2**20 / digital['fsr_diff_v']) + 2**19)
        return {'weighted_sum_ra_v': weighted, 'd1_v': float(d1_v),
                'd2_v': float(d2_v), 'dt_v': float(dt_v),
                'unsat_code': unsat, 'code20': round_away_and_clip(unsat)}

    rows = []
    mismatches = {'np_sum': [], 'np_dot': []}
    d2_equal = {'np_sum': 0, 'np_dot': 0}
    max_d2_difference = {'np_sum': 0.0, 'np_dot': 0.0}
    for index in range(len(times)):
        v1, v2, vt = map(float, terms[index])
        logged_unsat = ((v1 + v2) + vt) * (2**20 / digital['fsr_diff_v']) + 2**19
        actual = int(codes[index])
        assert codes[index] == actual == round_away_and_clip(logged_unsat), index
        calculations = {'np_sum': calculate(raw[index], False),
                        'np_dot': calculate(raw[index], True)}
        for name, value in calculations.items():
            if value['code20'] != actual:
                mismatches[name].append(index)
            if value['d2_v'] == v2:
                d2_equal[name] += 1
            max_d2_difference[name] = max(max_d2_difference[name], abs(value['d2_v'] - v2))
        rows.append({'id': index, 'rx_time_s': float(times[index]),
                     'raw6': raw[index].astype(int).tolist(), 'actual_code20': actual,
                     'actual_d1_d2_dt_v': [v1, v2, vt],
                     'actual_logged_terms_unsat_code': float(logged_unsat),
                     **calculations})
    target = rows[138]
    assert target['raw6'] == [201, 2764, 108, 138, 1, 1]
    assert target['actual_code20'] == 91643 and target['actual_logged_terms_unsat_code'] == 91642.5
    report = {
        'schema': 'sar20-ou-transport-id138-rounding/v1',
        'status': 'saved_RX_and_float_order_replayed',
        'P_sha256': P_SHA, 'simout_sha256': SIM_SHA,
        'as_run_runner_sha256': RUNNER_SHA, 'project_reader_sha256': READER_SHA,
        'python': sys.version, 'numpy': np.__version__, 'platform': platform.platform(),
        'records': len(rows), 'record_ready_boundary': 'actual RX record_ready',
        'exact_code_tolerance_counts': 0, 'actual_logged_terms_code_mismatches': [],
        'model_reconstruction_code_mismatch_ids': mismatches,
        'd2_component_equal_count': d2_equal,
        'd2_component_max_abs_difference_v': max_d2_difference,
        'id138': target,
        'id138_hex': {'logged_d2_v': float(terms[138, 1]).hex(),
                      'np_sum_d2_v': target['np_sum']['d2_v'].hex(),
                      'np_dot_d2_v': target['np_dot']['d2_v'].hex(),
                      'np_sum_unsat': target['np_sum']['unsat_code'].hex(),
                      'np_dot_unsat': target['np_dot']['unsat_code'].hex()},
        'qualification': ['Logged components and saved MATLAB output are actual run evidence.',
                          'Python sum and dot may use different reduction order across platforms.',
                          'Equal rounded codes do not prove bit-identical D2 components.',
                          'The internal intermediate of the native behavior_decode call was not separately logged.',
                          'No changes to DUT, tolerances, original run, or sampled code values.'],
        'rows': rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
