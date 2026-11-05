#!/usr/bin/env python3
"""Read-only, independent three-run N256 RAW/FFT audit; JSON to stdout."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import h5py
import numpy as np
from verify_as_run import archive_provenance, at, fingerprint, graph, need, pdiff, read_calendar, read_logs, same, sha, val


def array_sha(a):
    """SHA-256 of row-major IEEE binary64, explicitly little-endian."""
    return hashlib.sha256(np.asarray(a, dtype='<f8', order='C').tobytes()).hexdigest()


def fft(codes, fs, fin, fsr):
    n = len(codes); ratio = fin*n/fs; bin_ = int(math.floor(ratio+.5))
    need(n == 256 and 0 < bin_ < n/2 and abs(ratio-bin_) < 1e-9, 'Existing coherent-tone gate failed')
    voltage = ((codes+.5)/2**20-.5)*fsr
    power = np.abs(np.fft.fft(voltage-voltage.mean())/n)[:n//2+1]**2
    power[1:-1] *= 2
    other = power.copy(); other[[0,bin_]] = 0
    harmonic = np.mod(np.arange(2,11)*bin_, n)
    harmonic = np.setdiff1d(np.unique(np.minimum(harmonic,n-harmonic)), [0,bin_])
    sig, nd, hd = power[bin_], other.sum(), power[harmonic].sum()
    need(sig > 0 and nd > 0 and nd-hd > 0 and hd > 0 and other.max() > 0, 'Degenerate spectrum')
    result = {'snr_db':float(10*np.log10(sig/(nd-hd))), 'sndr_db':float(10*np.log10(sig/nd)),
              'sfdr_db':float(10*np.log10(sig/other.max())), 'thd_db':float(10*np.log10(hd/sig))}
    result['enob'] = (result['sndr_db']-1.76)/6.02
    return result, bin_, harmonic, power


def audit(label, run, tau_expect, enabled_expect):
    run = run.resolve()
    summary = json.loads((run/'summary.json').read_text())
    need(summary.get('status') == 'complete' and summary.get('simulation_completed') and
         summary.get('spectrum_status') == 'actual_codes_characterized' and
         summary.get('capture_boundary') == 'serial_rx' and summary.get('decode_mode') == 'nominal',
         f'{label}: incomplete/non-nominal as-run summary')
    hashes, provenance = archive_provenance(run,summary,False)
    hashes.update({name:sha(run/name) for name in ['selected.mat','spectrum.mat']})
    need(hashes['selected.mat'] == summary['selected_sha256'], f'{label}: selected SHA mismatch')
    blocks, edges, cfg = graph(run/'SarAdc.slx')
    need(('237#out:1','321#in:4') in edges and
         ''.join(blocks['321'][2].get('Parameters','').split()) == "'advance',behavior_dac_backend_parameters(P)",
         f'{label}: as-run FE edge/checked binding missing')
    with h5py.File(run/'parameters.mat','r') as p, h5py.File(run/'selected.mat','r') as s, \
         h5py.File(run/'spectrum.mat','r') as sp:
        N, first, epoch = [int(val(p,'P/'+k)) for k in ['N','first_id','epoch']]
        fs, fsr, fin = [float(val(p,k)) for k in ['P/fs_hz','P/fsr_diff_v','P/input/frequency_hz']]
        tau = np.asarray(val(p,'P/front/tau_dac_s')).ravel(); en=bool(val(p,'P/backend/dac_coupling/enabled'))
        need(N==256 and first==4 and epoch==1 and len(tau)==18 and np.all(tau==tau_expect)
             and en==enabled_expect and bool(val(p,'P/ni/dac_settling'))==enabled_expect,
             f'{label}: N/window/tau/coupling/coverage mismatch')
        for a,b in [('P/front/tau_dac_s','P/backend/dac_coupling/tau_dac_s'),
                    ('P/front/schema','P/backend/dac_coupling/frontend_schema'),
                    ('P/front/plan','P/backend/dac_coupling/public_plan')]:
            need(fingerprint(p,p[a],{}) == fingerprint(p,p[b],{}), f'{label}: saved binding mismatch {a}')
        need(fingerprint(p,p['P/input'],{})==fingerprint(s,s['metadata/stimulus'],{})==
             fingerprint(sp,sp['metrics/stimulus'],{}), f'{label}: saved input metadata differs')
        need(same(np.float64(fs),np.float64(val(s,'metadata/fs_hz'))) and
             same(np.float64(fsr),np.float64(val(s,'metadata/fsr_diff_v'))) and
             same(np.float64(fs),np.float64(val(sp,'metrics/sample_rate_hz'))) and
             same(np.float64(fsr),np.float64(val(sp,'metrics/full_scale_diff_v'))) and
             same(np.float64(fin),np.float64(val(sp,'metrics/input_frequency_hz'))) and
             int(val(sp,'metrics/record_length'))==N, f'{label}: FFT metadata mismatch')
        raw = np.asarray(s['selected/raw'][()]).T
        codes = np.asarray(s['selected/code20'][()]).ravel()
        times = np.asarray(s['selected/time_s'][()]).ravel()
        need(raw.shape==(N,6) and codes.shape==(N,) and times.shape==(N,) and
             np.all(np.isfinite(raw)) and np.all(np.isfinite(codes)) and
             np.array_equal(raw[:,3],np.arange(first,first+N)) and np.all(raw[:,4]==epoch)
             and np.all(raw[:,5]==1) and np.all(codes==np.floor(codes)) and
             np.all((codes>=0)&(codes<2**20)), f'{label}: invalid/incomplete selected capture')
        need(summary['records']==N and np.array_equal(np.asarray(summary['raw_words']),raw) and
             np.array_equal(np.asarray(summary['code20']),codes) and
             np.array_equal(np.asarray(summary['sample_ids']),raw[:,3]), f'{label}: summary vs selected mismatch')
        settings = {'N':N,'first_id':first,'epoch':epoch,'fs_hz':fs,'fin_hz':fin,'fsr_diff_v':fsr,
                    'input_amplitude_v':float(val(p,'P/input/amplitude_v')),
                    'input_phase_rad':float(val(p,'P/input/phase_rad')),
                    'input_offset_v':float(val(p,'P/input/offset_v')), 'tau_uniform_s':float(tau[0]),
                    'dac_coupling_enabled':en,'finite_dac_ni':bool(val(p,'P/ni/dac_settling')),
                    'parasitic_ni':bool(val(p,'P/ni/parasitic')),
                    'az':bool(val(p,'P/backend/ni/az')), 'ktc':bool(val(p,'P/front/ktc_enabled')),
                    'mismatch':bool(val(p,'P/front/mismatch_enabled')),
                    'dem':bool(val(p,'P/front/dem_enabled')),
                    'dither':bool(val(p,'P/front/dither_enabled')),
                    'jitter':bool(val(p,'P/front/jitter/enabled')),
                    'training':bool(val(p,'P/training/enabled')), 'frozen':bool(val(p,'P/frozen/enabled')),
                    'calibration_mode':val(p,'P/digital/calibration_mode'),
                    'RA_A0':float(val(p,'P/backend/ra/A0')), 'RA_UGB_hz':float(val(p,'P/backend/ra/UGB_hz'))}
        adc_times, groups, budget = read_calendar(p)
        latch = [i+1 for i,g in enumerate(groups) if 'raw_latch' in g]
        parent_times = [float(p[ref][()][0,0]) for ref in p['P/groups/time_s'][()].ravel()]
        ts = float(val(p,'P/Ts_s'))
        need(len(latch)==1 and len(parent_times)==49,f'{label}: unsupported saved calendar')
        need(not any(settings[k] for k in ['az','ktc','mismatch','dem','dither','jitter','training','frozen'])
             and settings['calibration_mode']=='off', f'{label}: stated disabled NI/calibration scope changed')
        matlab = {k:float(val(sp,'metrics/'+k)) for k in ['snr_db','sndr_db','sfdr_db','thd_db','enob']}
        need(all(same(np.float64(matlab[k]),np.float64(summary[k])) for k in matlab),
             f'{label}: spectrum.mat metric differs bitwise from summary')
        old_power = np.asarray(sp['metrics/power_v2'][()]).ravel()
        old_frequency = np.asarray(sp['metrics/frequency_hz'][()]).ravel()
        old_bin = int(val(sp,'metrics/fundamental_bin'))
    logs = read_logs(run/'simout.mat')
    rready = logs['record_ready_log']; flags = rready['data'][:,0]
    need(np.all(np.isin(flags,[0,1])), f'{label}: invalid RX ready flags')
    alltimes = rready['time'][flags==1]
    allraw = at(logs['record_log'],alltimes,'record_log')
    allcode = at(logs['code_log'],alltimes,'code_log')[:,0]
    selected = (allraw[:,3]>=first)&(allraw[:,3]<first+N)
    need(same(allraw[selected],raw) and same(allcode[selected],codes) and same(alltimes[selected],times),
         f'{label}: selected does not equal actual RX ready RAW/code/time')
    ar = logs['ready_log']; arf=ar['data'][:,0]; need(np.all(np.isin(arf,[0,1])),f'{label}: invalid ADC ready')
    atimes=ar['time'][arf==1]; araw=at(logs['raw_log'],atimes,'ADC raw')
    receive_events=at(logs['event_log'],times,'RX event')
    receive_executed=at(logs['adc_executed_log'],times,'RX ADC-executed flag')[:,0]
    need(np.array_equal(receive_events[:,0],raw[:,3]+2) and np.all(receive_events[:,1]==49) and
         np.all(receive_executed==0) and
         same(times,np.array([(ident+2)*ts+parent_times[48] for ident in raw[:,3]])),
         f'{label}: actual RX timing/group49 is not saved N-2 slot')
    for row in raw:
        ix = np.flatnonzero((araw[:,3]==row[3])&(araw[:,4]==row[4]))
        need(len(ix)==1 and same(araw[ix[0]],row),f'{label}: ADC and RX actual RAW mismatch')
        e=at(logs['event_log'],[atimes[ix[0]]],'ADC-ready event')[0]
        executed=at(logs['adc_executed_log'],[atimes[ix[0]]],'ADC-executed flag')[0,0]
        need(e[0]==row[3] and e[1]==latch[0] and executed==1 and
             same(np.float64(atimes[ix[0]]),np.float64(row[3]*ts+adc_times[latch[0]-1])) and
             atimes[ix[0]]<times[int(row[3])-first], f'{label}: actual ADC raw_latch timing differs')
    ours, bin_, harmonics, power=fft(codes,fs,fin,fsr)
    need(bin_==old_bin and np.array_equal(old_frequency,np.arange(N//2+1)*fs/N),
         f'{label}: saved FFT frequency/bin mismatch')
    digest=hashlib.sha256(b'SAR20-FFT-input/v1\0'+np.asarray(codes,dtype='<f8').tobytes()+
                          struct.pack('<ddd',fs,fin,fsr)).hexdigest()
    manifest=json.loads((run/'source_manifest.json').read_text())['files']
    pins={x['path'].replace('\\','/'):x['sha256'] for x in manifest}
    result={'label':label,'run':str(run),'sha256':hashes,'source_execution_boundary':provenance,
            'input_hashes':{'selected_raw6_256x6_binary64_le_rowmajor':array_sha(raw),
                            'selected_code20_256_binary64_le':array_sha(codes),
                            'actual_RX_ready_time_256_binary64_le':array_sha(times),
                            'FFT_input_code_fs_fin_fsr_sha256':digest,
                            'definition':'SHA-256 of ASCII SAR20-FFT-input/v1 + NUL, then 256 code20 binary64 little-endian, then Fs/Fin/FSR as three binary64 little-endian values'},
            'settings':settings,'selected_and_actual_RX_RAW_code_time_bits_equal':True,
            'same_run_ADC_to_RX_RAW6_by_ID_epoch_bits_equal':True,
            'ADC_raw_latch_and_RX_group49_N_minus_2_actual_timing_checked':True,'valid_records':N,
            'summary_and_spectrum_mat_five_metrics_bit_equal':True,'fundamental_bin':bin_,
            'harmonic_bins_H2_to_H10':harmonics.tolist(), 'independent_fft':ours,
            'saved_matlab_fft':matlab,'numpy_minus_saved_matlab':{k:ours[k]-matlab[k] for k in ours},
            'max_abs_numpy_minus_saved_power_v2':float(np.max(np.abs(power-old_power))),
            'spectrum_identity_boundary':'spectrum.mat SHA is measured on readback; summary has no recorded spectrum.mat SHA. '
                   'FFT input binding is verified by the independently read actual code, metadata and recomputed spectrum, '
                   'not by an as-run input hash stored in spectrum.mat.',
            'fft_scope':'256 actual valid codes; coherent rectangular single-sided FFT, H2-H10, no ENOB amplitude correction; no INL/DNL/PVT or silicon claim.'}
    return result,pins,codes,raw,edges,cfg


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--off',type=Path,required=True);ap.add_argument('--tau01',type=Path,required=True)
    ap.add_argument('--tau1',type=Path,required=True);args=ap.parse_args()
    cases=[audit('off',args.off,0.,False),audit('0.1ns',args.tau01,1e-10,True),audit('1ns',args.tau1,1e-9,True)]
    base=args.off.resolve();allowed={'P/front/tau_dac_s','P/backend/dac_coupling/enabled',
                                   'P/backend/dac_coupling/tau_dac_s','P/ni/dac_settling'}
    diff={};code_delta={}
    for (result,pins,codes,raw,edges,cfg),path in zip(cases[1:],[args.tau01,args.tau1]):
        d=pdiff(base/'parameters.mat',path.resolve()/'parameters.mat')
        need(set(d)==allowed, result['label']+': unexpected P differences '+repr(d));diff[result['label']]=d
        delta=codes-cases[0][2];code_delta[result['label']]={'changed_count':int(np.count_nonzero(delta)),
                                  'max_abs_counts':float(np.max(np.abs(delta)))}
        need(pins==cases[0][1],result['label']+': saved source manifest differs from off')
        need(edges==cases[0][4] and cfg==cases[0][5],result['label']+': as-run edges/solver differ')
    report={'schema':'sar20-three-actual-n256-independent-raw-fft/v1',
            'verifier_sha256':sha(Path(__file__).resolve()),'cases':[c[0] for c in cases],
            'full_saved_P_differences_vs_off':diff,'same_source_manifest_file_hashes_all_three':True,
            'same_native_edges_and_solver_all_three':True,'changed_code_vs_off':code_delta,
            'scope':'Read-only posterior check of three saved public N256 runs; no ADC simulation, no new tolerance, '
                    'no altered current or inferred continuous/internal FE state.'}
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
