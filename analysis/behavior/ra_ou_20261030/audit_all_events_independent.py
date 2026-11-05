#!/usr/bin/env python3
"""Read-only replay of the saved RA-OU N8 runs; emit JSON to stdout.

No MATLAB execution, model modification, or writes to a run directory.
Requires the project analysis environment, its pinned MCOS reader, the saved
v3 manifest snapshot next to this file, and the original run artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if not __debug__:
    raise RuntimeError('Do not use Python -O: it disables the replay assertions.')
import h5py
import numpy as np

MODEL = 'a190eae2be57e24f0fb923bad7bbf4144873f28ddc97b8196fdd80a512adbe9f'
MANIFEST = '9ed7eeae767fa399c300a18c8127f5a7bef57ec776301ad54239e0a935cd399c'
READER = '3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'
OLD_SIM = '555a4d494fecb2f6672bedc5c347ea48d4577c6a42dc6ec0a71ad12728373358'
PINS = {
    'off': ('dc064aa8fa204ac36d3f06ad128bbfd90da672c40c052de21530e7db378c353d', '5887b6a6cabb20dbd27308c94ac2bad431787cddbc340db1d02aaa3151377e3a'),
    'off_tap': ('1e4d09ac5610f8cd1ed53a9b06ee824cce4f3f3d04e1e1fd811876821a18cce1', '30161acfee2af3e4597a40e97f21ea545d07e93bd5d6c4db7030844af5d31a9e'),
    'zero_tap': ('946844dbbc86842846a7d7fbb5e6700e7c28b565c82f6c651caac4d842a4eeb5', 'ac749ba196e7ecefec28cb3126c4ee75af1983297298da3f070e0ae70c197b49'),
    'on': ('d7e9a3757ae30330e7f09039747614145fb0701449695566629aca221bca1894', 'cd8b3faf295e508bb19d1d18f900a61fa0a7d7ce981f74a47b317629310d2a00'),
    'on_repeat': ('f33fc52751b1833e1351a70b0360df9ac09b1273e7908245294bebdd5ed9fad6', '24ca22790f24a805f78a3ea00b0a2c70b707a04170895e5bd06eacdd7c368695'),
}
# Absolute numerical comparison tolerances for independent double-precision
# replay, not voltage-error specifications or statistical confidence limits.
RA_TOL_V = 1e-13
CT_TOL_V = 1e-12


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def roots(path: Path):
    """Read original MATLAB yout sigstream bytes; do not synthesize times."""
    with h5py.File(path, 'r') as f:
        seq = [f[ref] for ref in f['#subsystem#/MCOS'][()].ravel()]
        datasets = [g for g in seq if isinstance(g, h5py.Group)
                    and {'Elements', 'FileName', 'Version'} <= set(g)]
        assert len(datasets) == 1, 'ambiguous yout dataset'
        output = {}
        for ref in datasets[0]['Elements'][()].ravel():
            element = f[ref]
            path_data = f[element['BlockPath'][()].ravel()[0]][()].ravel()
            name = ''.join(chr(int(c)) for c in path_data).split('/')[-1]
            value = element['Values']
            width = int(value['SignalAttributes/Dimension'][()].item())
            def stream(index, item_width):
                group = f['#sigstream#'][str(index)]
                count = int(group['#length#'][()].item())
                assert int(group['#sampleSize#'][()].item()) == 8 * item_width
                data = group['#data#'][()].tobytes()
                assert len(data) >= count * item_width * 8
                return np.frombuffer(data, dtype='<f8', count=count * item_width).copy().reshape(count, item_width)
            data = stream(int(value['DataR2'][()].item()), width)
            times = stream(int(value['TimeR2'][()].item()), 1)[:, 0]
            assert len(times) == len(data) and np.all(np.diff(times) >= 0)
            assert name not in output
            output[name] = {'time': times, 'data': data}
        assert set(output) == {'Code20', 'CodeValid', 'CodeMeta'}
        return output


def normal(seed: int, epoch: int, sample_id: int, t0: float, t1: float):
    # These keys are reconstructed from actual logged times and saved stage
    # semantics; they are not recorded directly at the running function port.
    payload = b'SAR20-RA-OU-v1\0' + struct.pack('>QQQdd', seed, epoch, sample_id, t0, t1)
    digest = hashlib.sha256(payload).digest()
    a, b = struct.unpack('>QQ', digest[:16])
    u1 = ((a >> 12) + 0.5) * 2**-52
    u2 = ((b >> 12) + 0.5) * 2**-52
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return z, digest.hex()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--result', type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    result = (args.result or project / 'runs/work_20261030T154306Z/result').resolve()
    old = project / 'runs/behavior_81cd3a51-9ec4-4556-94e9-92f9ed6ef720/simout.mat'
    helper = project / 'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
    manifest_file = Path(__file__).resolve().with_name('candidate_manifest_v3_snapshot.json')
    assert sha(helper) == READER and sha(manifest_file) == MANIFEST and sha(old) == OLD_SIM
    sys.path.insert(0, str(helper.parent))
    import verify_as_run as u

    manifest = json.loads(manifest_file.read_text())
    assert len(manifest['files']) == 109
    for row in manifest['files']:
        file = result / 'sandbox' / row['path'].replace('\\', '/')
        assert file.is_file() and sha(file) == row['sha256'], row['path']
    model_file = result / 'sandbox/current/models/SarOUProbe.slx'
    assert sha(model_file) == MODEL
    logs, root = {}, {}
    for name, (p_hash, sim_hash) in PINS.items():
        case = result / name
        assert sha(case / 'P.mat') == p_hash and sha(case / 'simout.mat') == sim_hash, name
        logs[name] = u.read_logs(case / 'simout.mat')
        root[name] = roots(case / 'simout.mat')
        assert len(logs[name]) == 32
    assert u.pdiff(result / 'on/P.mat', result / 'on_repeat/P.mat') == []
    assert set(u.pdiff(result / 'on/P.mat', result / 'zero_tap/P.mat')) == {
        'P/backend/ra_noise/sigma_vx_rms', 'P/ni/ra_noise'}

    def same_logs(left, right):
        assert set(left) == set(right)
        for name in left:
            a, b = left[name], right[name]
            assert a['class'] == b['class'] and a['storage_shape'] == b['storage_shape'], name
            assert u.same(a['time'], b['time']) and u.same(a['data'], b['data']), name

    def same_roots(left, right):
        for name in ('Code20', 'CodeValid', 'CodeMeta'):
            assert u.same(left[name]['time'], right[name]['time'])
            assert u.same(left[name]['data'], right[name]['data'])

    same_logs(logs['off'], u.read_logs(old))
    same_roots(root['off'], roots(old))
    same_logs(logs['off_tap'], logs['zero_tap'])
    same_roots(root['off_tap'], root['zero_tap'])
    same_logs(logs['on'], logs['on_repeat'])
    same_roots(root['on'], root['on_repeat'])

    with h5py.File(result / 'on/P.mat', 'r') as f:
        times, groups, budget = u.read_calendar(f)
        epoch = int(u.val(f, 'P/epoch'))
        period = float(u.val(f, 'P/Ts_s'))
        a0 = float(u.val(f, 'P/backend/ra/A0'))
        tau_reset = float(u.val(f, 'P/backend/ra/tau_reset_s'))
        sigma = float(u.val(f, 'P/backend/ra_noise/sigma_vx_rms'))
        seed = int(u.val(f, 'P/backend/ra_noise/seed_u64'))
        plan = np.asarray(u.val(f, 'P/front/plan'))
        reference_v = float(u.val(f, 'P/backend/ct/reference_v'))
        qb = np.asarray(u.val(f, 'P/backend/ct/initial_main_qb_c')).ravel()
        net = {k: np.asarray(u.val(f, 'P/backend/ct/net_nominal/' + k), dtype=float)
               for k in ('cinc_f', 'bridge_f', 'main_f', 'sub_f', 'track_f',
                         'parasitic_main_f', 'parasitic_sub_f', 'dummy_f')}
        dig = {k: u.val(f, 'P/digital/' + k) for k in
               ('vref_v', 'fsr_diff_v', 'ra_gain', 'd2_offset_ra_v', 'd2_weights_ra_v', 'tracking_step_ra_v')}
        for key in ('bank/enabled', 'training/enabled', 'cal_cfg/enabled', 'frozen/enabled',
                    'front/ktc_enabled', 'front/jitter/enabled', 'front/dem_enabled',
                    'front/dither_enabled', 'backend/ni/az', 'ni/comparator_noise',
                    'ni/reference_recovery', 'backend/ni/cap_mismatch'):
            assert int(u.val(f, 'P/' + key)) == 0, key
        assert int(u.val(f, 'P/backend/ni/ra_noise')) == 1
        assert int(u.val(f, 'P/backend/ni/cinc_kick')) == 1
        assert int(u.val(f, 'P/backend/ct/replica_enabled')) == 1
        assert int(u.val(f, 'P/debug/adi_enabled')) == 1
        assert int(u.val(f, 'P/debug/dac_enabled')) == 1
        assert int(u.val(f, 'P/N')) == 8 and int(u.val(f, 'P/first_id')) == 4
    assert sigma == 0.001 and seed == 20261030 and epoch == 1
    assert plan.shape[1] == 8 and budget == {'d2_decide': 12, 'ta_compare': 8, 'ta_feedback': 7}
    on = logs['on']
    for name in ('event_log', 'control_log', 'back_log', 'adi_wire_log', 'raw_log',
                 'ready_log', 'record_log', 'record_ready_log', 'code_log', 'dac_ra_pre_log', 'az_route_log'):
        assert u.same(on['event_log']['time'], on[name]['time']), name
    event = on['event_log']['data']; t = on['event_log']['time']
    control = on['control_log']['data']; tap = on['adi_wire_log']['data']
    back = on['back_log']['data']; pre = on['dac_ra_pre_log']['data']
    route = on['az_route_log']['data']; raw = on['raw_log']['data']
    record = on['record_log']['data']; ready = on['ready_log']['data'][:, 0]
    code = on['code_log']['data'][:, 0]
    assert event.shape == (576, 2)
    assert np.array_equal(event[:, 0], np.repeat(np.arange(12), 48))
    assert np.array_equal(event[:, 1], np.tile(np.arange(1, 49), 12))
    expected_time = np.array([row[0] * period + times[int(row[1]) - 1] for row in event])
    assert u.same(t, expected_time)
    assert u.same(on['ready_log']['data'], on['record_ready_log']['data'])
    assert np.all(np.isin(ready, [0, 1]))
    ready_rows = np.flatnonzero(ready == 1)
    assert len(ready_rows) == 12 and np.array_equal(raw[ready_rows, 3], np.arange(12))
    assert np.all(raw[ready_rows, 4] == epoch) and np.all(raw[ready_rows, 5] == 1)
    assert u.same(raw[ready_rows], record[ready_rows])
    assert np.array_equal(raw[ready_rows, :3], control[ready_rows, 4:7])
    for index in ready_rows:
        assert code[index] == int(code[index]) == u.decode(raw[index], dig)

    r = root['on']; meta = on['bank_meta_log']
    assert u.same(u.at(r['Code20'], t, 'root Code20'), on['code_log']['data'])
    assert np.all(r['CodeValid']['data'] == 0)
    assert u.same(u.at(r['CodeMeta'], meta['time'], 'root CodeMeta'), meta['data'])
    assert np.all(np.isnan(meta['data'][:, [0, 2, 3, 4]]))
    assert u.same(meta['data'][:, 1], meta['time']) and np.all(meta['data'][:, 5:9] == 0)
    assert np.all(u.at(r['CodeValid'], t[ready_rows], 'root valid at ready') == 0)

    events = []
    total_d2 = total_ta = total_d2_feedback = total_ta_feedback = 0
    for sid in range(12):
        signs = np.zeros(19); counts = np.zeros(3); d2word = taword = 0
        d2n = tan = d2fb = tafb = 0
        for group in range(1, 49):
            i = sid * 48 + group - 1
            tokens = groups[group - 1]
            assert np.array_equal(tap[i, :8], np.sort(plan[sid, :]))
            assert np.array_equal(tap[i, 56:58], [sid, epoch])
            if 'cnv' in tokens:
                signs[:] = 0; counts[:] = 0
            if 'd2_feedback' in tokens:
                bit = (int(control[i - 1, 5]) >> (11 - d2fb)) & 1
                signs[d2fb] = 2 * bit - 1; d2fb += 1; total_d2_feedback += 1
            if 'ta_feedback' in tokens:
                bit = (int(control[i - 1, 6]) >> (7 - tafb)) & 1
                signs[12 + tafb] = 2 * bit - 1; tafb += 1; total_ta_feedback += 1; counts[2] += 1
            d2_decision = ta_decision = None
            if 'd2_decide' in tokens:
                bit = 11 - d2n; d2_decision = int(back[i, 1] >= 0)
                d2word = (d2word & ~(1 << bit)) | (d2_decision << bit)
                d2n += 1; total_d2 += 1; counts[0] += 1
            if 'ta_compare' in tokens:
                bit = 7 - tan; ta_decision = int(back[i, 1] >= 0)
                taword = (taword & ~(1 << bit)) | (ta_decision << bit)
                tan += 1; total_ta += 1; counts[1] += 1
            assert int(control[i, 5]) == d2word and int(control[i, 6]) == taword, (sid, group)
            assert np.array_equal(tap[i, 32:51], signs), (sid, group, 'feedback')
            assert np.array_equal(tap[i, 51:54], counts), (sid, group, 'counts')

            ds = tap[i, 32:44]; ts = tap[i, 44:51]
            active = bool(route[i, 3]); vx = back[i, 0] - back[i, 7]
            side_output = []
            for side in range(2):
                cs = net['cinc_f'].ravel()[side]; cb = net['bridge_f'].ravel()[side]
                cm = net['main_f'][side, :]; cl = net['sub_f'][side, :]; ct = net['track_f'][side, :]
                aa = cs + np.sum(cm) + cb + net['parasitic_main_f'].ravel()[side]
                bb = np.sum(cl) + np.sum(ct) + net['dummy_f'].ravel()[side] + cb + net['parasitic_sub_f'].ravel()[side]
                assert aa * bb - cb * cb > 0
                polarity = 1 - 2 * side
                dsign = ds if active else np.zeros(12)
                tsign = ts if active else np.zeros(7)
                qa = cs * polarity * vx / 2 - polarity * reference_v / 2 * np.dot(cm, dsign[:10]) - cb * qb[side] / bb
                qbs = -polarity * reference_v / 2 * (np.dot(cl, dsign[10:]) + np.dot(ct, tsign)) + qb[side]
                side_output.append((bb * qa + cb * qbs) / (aa * bb - cb * cb))
            vy_calculated = side_output[0] - side_output[1] if active else 0.0
            ct_error = float(vy_calculated - back[i, 1])
            assert abs(ct_error) < CT_TOL_V, (sid, group, ct_error)
            events.append({'id': sid, 'group': group, 'time_s': float(t[i]), 'tokens': tokens,
                           'vy_actual_v': float(back[i, 1]), 'vy_ct_replay_v': float(vy_calculated),
                           'ct_error_v': ct_error, 'd2_word': d2word, 'dt_word': taword,
                           'd2_decision': d2_decision, 'ta_decision': ta_decision,
                           'feedback_signs19': signs.astype(int).tolist(),
                           'tap_counts_d2_ta_feedback': counts.astype(int).tolist(),
                           'sample_ids8': tap[i, :8].astype(int).tolist()})
        assert (d2n, tan, d2fb, tafb) == (12, 8, 12, 7)

    intervals = []
    for i in range(1, len(t)):
        dt = float(t[i] - t[i - 1]); old_vx = float(back[i - 1, 0])
        tau = float(back[i - 1, 5]); target = float(back[i - 1, 3]); ng = float(back[i - 1, 4])
        active = bool(control[i - 1, 1]); old_id = int(control[i - 1, 8]); old_epoch = int(control[i - 1, 9])
        z = digest = None; innovation = 0.0
        if active:
            gain = a0 / (a0 + ng)
            deterministic = gain * target + (old_vx - gain * target) * math.exp(-dt / tau)
            z, digest = normal(seed, old_epoch, old_id, float(t[i - 1]), float(t[i]))
            innovation = sigma * math.sqrt(-math.expm1(-2 * dt / tau)) * z
            prediction = deterministic + innovation
        else:
            prediction = old_vx * math.exp(-dt / tau_reset) if tau_reset else 0.0
        observed = float(pre[i, 0]); error = prediction - observed
        assert abs(error) < RA_TOL_V, (i, active, error)
        intervals.append({'from_id': int(event[i - 1, 0]), 'from_group': int(event[i - 1, 1]),
                          'to_id': int(event[i, 0]), 'to_group': int(event[i, 1]),
                          't0_s': float(t[i - 1]), 't1_s': float(t[i]), 'dt_s': dt,
                          'old_command_id': old_id, 'old_epoch': old_epoch, 'active': active,
                          'previous_observed_vx_v': old_vx, 'reconstructed_key_sha256': digest,
                          'reconstructed_z': z, 'innovation_v': innovation,
                          'pre_vx_replay_v': prediction, 'pre_vx_actual_v': observed, 'error_v': error})

    zero = logs['zero_tap']; zpre = zero['dac_ra_pre_log']['data']; zback = zero['back_log']['data']
    i0 = int(np.flatnonzero((event[:, 0] == 0) & (event[:, 1] == 12))[0])
    i1 = int(np.flatnonzero((event[:, 0] == 0) & (event[:, 1] == 13))[0])
    assert i1 == i0 + 1 and u.same(pre[i0], zpre[i0]) and u.same(back[i0], zback[i0])
    first_z, first_digest = normal(seed, epoch, 0, float(t[i0]), float(t[i1]))
    first_tau = float(pre[i1, 5])
    expected_dx = sigma * math.sqrt(-math.expm1(-2 * (float(t[i1] - t[i0]) / first_tau))) * first_z
    actual_dx = float(pre[i1, 0] - zpre[i1, 0])
    alpha = []
    for side in range(2):
        cs = net['cinc_f'].ravel()[side]; cb = net['bridge_f'].ravel()[side]
        aa = cs + np.sum(net['main_f'][side]) + cb + net['parasitic_main_f'].ravel()[side]
        bb = np.sum(net['sub_f'][side]) + np.sum(net['track_f'][side]) + net['dummy_f'].ravel()[side] + cb + net['parasitic_sub_f'].ravel()[side]
        alpha.append(float(cs * bb / (aa * bb - cb * cb)))
    actual_dy = float(back[i1, 1] - zback[i1, 1])
    expected_dy = float(np.mean(alpha) * actual_dx)
    assert abs(actual_dx - expected_dx) < RA_TOL_V and abs(actual_dy - expected_dy) < CT_TOL_V
    zero_ix = np.flatnonzero(zero['ready_log']['data'][:, 0] == 1)
    assert len(zero_ix) == 12
    zero_codes = zero['code_log']['data'][zero_ix, 0]
    selected_delta = (code[ready_rows][4:] - zero_codes[4:]).astype(int).tolist()
    assert u.same(pre[:, 0], back[:, 0])

    cleanup_file = result / 'cleanup.mat'
    with h5py.File(cleanup_file, 'r') as f:
        cleanup = {'status': u.val(f, 'cleanup/status'),
                   'path_restored': bool(u.val(f, 'cleanup/path_restored')),
                   'cwd_restored': bool(u.val(f, 'cleanup/cwd_restored')),
                   'rng_restored': bool(u.val(f, 'cleanup/rng_restored')),
                   'main_snapshot_equal': bool(u.val(f, 'cleanup/main_snapshot_equal')),
                   'cache_original_bytes_restored': bool(u.val(f, 'cleanup/cache_original_bytes_restored'))}
    assert cleanup['status'] == 'cleanup_complete'
    assert cleanup['path_restored'] and cleanup['cwd_restored'] and cleanup['rng_restored'] and cleanup['main_snapshot_equal']

    report = {
        'schema': 'sar20-ra-ou-independent-all-events/v1',
        'status': 'independent_saved_artifact_replay_passed',
        'input_files_sha256': {name: {'P.mat': p, 'simout.mat': s} for name, (p, s) in PINS.items()},
        'old_simout_sha256': OLD_SIM, 'model_sha256': MODEL,
        'candidate_manifest_sha256': MANIFEST, 'reader_sha256': READER,
        'sigma_vx_rms_v': sigma, 'sigma_scope': '1mV differential output RMS is a test assumption, not a measured circuit noise value.',
        'event_count': len(events), 'cycle_count': 12, 'ready_count': len(ready_rows),
        'selected_ids': raw[ready_rows, 3][4:].astype(int).tolist(),
        'observed_d2_decisions': total_d2, 'observed_ta_decisions': total_ta,
        'observed_d2_feedback_updates': total_d2_feedback, 'observed_ta_feedback_updates': total_ta_feedback,
        'tap_counts_each_ready': [12, 8, 7], 'calendar_time_bits_equal': True,
        'raw_record_ready_and_public_decode_match': True,
        'replay': {'ra_tolerance_v': RA_TOL_V, 'ct_tolerance_v': CT_TOL_V,
                   'ra_interval_count': len(intervals), 'ra_active_intervals': sum(v['active'] for v in intervals),
                   'ra_reset_off_intervals': sum(not v['active'] for v in intervals),
                   'ra_max_abs_error_v': max(abs(v['error_v']) for v in intervals),
                   'ct_event_count': len(events), 'ct_max_abs_error_v': max(abs(v['ct_error_v']) for v in events),
                   'key_scope': 'Reconstructed from actual logged times and saved stage semantics, not directly instrumented at the DUT random function.',
                   'ct_scope': 'Uses actual tap signs, observed VX/reset baseline, saved nominal CT matrix and initial floating charge; not direct internal charge measurement.'},
        'first_ou': {'t0_s': float(t[i0]), 't1_s': float(t[i1]), 'key_sha256': first_digest,
                     'z': first_z, 'tau_s': first_tau, 'expected_delta_vx_v': expected_dx,
                     'actual_delta_vx_v': actual_dx, 'delta_vx_residual_v': actual_dx - expected_dx,
                     'alpha_per_half': alpha, 'expected_delta_vy_v': expected_dy,
                     'actual_delta_vy_v': actual_dy, 'delta_vy_residual_v': actual_dy - expected_dy},
        'comparisons': {'old_ea39_vs_candidate_a190_off_32_logs_and_three_roots_bit_equal': True,
                        'off_tap_vs_sigma0_32_logs_and_three_roots_bit_equal': True,
                        'on_vs_same_seed_repeat_32_logs_and_three_roots_bit_equal': True,
                        'on_P_vs_repeat_P_field_differences': [],
                        'on_P_vs_sigma0_field_differences': ['P/backend/ra_noise/sigma_vx_rms', 'P/ni/ra_noise'],
                        'bank_off_root_code_log_match': True, 'bank_off_root_valid_is_zero': True,
                        'bank_off_root_meta_log_match': True, 'selected_code_delta_on_minus_zero': selected_delta},
        'net_kick_observation': {'cinc_kick_enabled': True, 'replica_enabled': True, 'ct_mismatch_enabled': False,
                                 'pre_vx_equals_back_vx_at_all_576_recorded_events_bitwise': True,
                                 'scope': 'No nonzero net pre-to-back VX change observed; this does not independently measure every internal kick.'},
        'cleanup_receipt': cleanup,
        'limits': ['Only this isolated N8, fixed chip, input and seed.', 'No full-distribution or noise-PSD validation.',
                   'No physical 7dB paper claim, model promotion, PDK or silicon signoff.',
                   'ea39 historical OFF and a190 candidate are not byte-identical SLX.',
                   'On-disk source hashes do not prove freshness of same-path cached MATLAB function bytes.'],
        'events': events, 'intervals': intervals,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
