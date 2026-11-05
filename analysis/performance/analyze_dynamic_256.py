#!/usr/bin/env python3
"""Independent actual-code FFT; run with dependencies/analysis_env/bin/python.

Inputs: a closed raw.mat/selected.mat/result.json capture, its artifact identity
manifest, and native dynamic receipt. No generated samples or ADC simulation.
Uses NumPy only for FFT, matching current cicc_spectrum.m's rectangular-window,
H2..H10 convention. It does not estimate INL/DNL or physical signoff.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import mat_reader as mat


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scalar(file, path):
    value = np.asarray(mat.variable(file, path))
    require(value.size == 1 and np.isfinite(value).all(), f"Invalid scalar: {path}")
    return float(value.reshape(-1)[0])


def same(a, b, label):
    require(np.array_equal(np.asarray(a), np.asarray(b)), f"Mismatch: {label}")


def sample_nodes(raw, sample_id, epoch):
    """Small actual-node view on native owner rows; no interpolation or ideal values."""
    plan = mat.read_logger_plan(raw)
    names = ["pool_analog_held", "pool_analog_ra", "pool_analog_ct", "adc_control",
             "pool_analog_tracking_state"]
    missing = [name for name in names if name not in plan]
    if missing:
        return dict(status="missing_node_logs", missing=missing), None
    index = mat.variable(raw, "PoolAnalogCfg/idx")
    for group in ("held", "ra", "ct", "control"):
        require(index[group] == mat.variable(raw, "p/idx/"+group), f"Saved {group} indices differ")
    fields = mat.variable(raw, "captureProfile/tracking_state_fields")
    require(fields == ["meta.sample_id", "meta.epoch", "meta.ct_tracking_sign(1:7)"],
            "Unreviewed tracking-state field mapping")
    saved_tracking_indices = np.asarray(mat.variable(raw, "captureProfile/tracking_state_indices_1based")).reshape(-1)
    require(saved_tracking_indices.size == plan[names[-1]]["width"], "Tracking observer width mismatch")
    control_meta = plan["adc_control"]
    for name in names:
        for key in ("rows", "t0", "dt"):
            same(plan[name][key], control_meta[key], name+" native row metadata/"+key)
    owner_dt = scalar(raw, "p/dt_s")
    global_dt = scalar(raw, "cfg/dt_s")
    stride = int(round(owner_dt/global_dt))
    require(stride > 0 and stride*global_dt == owner_dt and control_meta["dt"] == owner_dt,
            "Unreviewed owner/global cadence")
    native = mat.read_solver_tout(raw)[::stride]
    require(native.size == control_meta["rows"] and native[0] == control_meta["t0"],
            "Logger rows cannot be bound to native solver tout")
    control = np.asarray(raw[control_meta["dataset_path"]][()]).T
    ci = index["control"]
    col = lambda values, group, key: values[:, int(index[group][key])-1]
    selected = (col(control,"control","sample_id") == sample_id) & (col(control,"control","epoch") == epoch)
    rows = np.flatnonzero(selected)
    require(rows.size > 0, f"No actual control rows for sample ID {sample_id}, epoch {epoch}")
    start, stop = max(0, int(rows[0])-1), min(native.size, int(rows[-1])+3)
    time = native[start:stop]
    arrays = {name: np.asarray(raw[plan[name]["dataset_path"]][:,start:stop]).T for name in names}
    control = arrays["adc_control"]
    current = (col(control,"control","sample_id") == sample_id) & (col(control,"control","epoch") == epoch)
    events = []
    counts = {}
    repeated_tags = {}
    for label, pulse, tag in (("D2", "sar2_decide", "sar2_bit"), ("TA", "track_decide", "track_index")):
        asserted = current & (col(control,"control",pulse) != 0)
        tags = col(control,"control",tag)
        starts = asserted & ~np.r_[False, asserted[:-1]]
        starts[1:] |= asserted[1:] & asserted[:-1] & (tags[1:] != tags[:-1])
        event_tags = []
        for row in np.flatnonzero(starts):
            value = float(tags[row])
            require(np.isfinite(value) and value == np.floor(value), f"Invalid {tag}")
            events.append(dict(kind=label, tag=int(value), time_s=float(time[row])))
            event_tags.append(int(value))
        counts[label] = len(event_tags)
        repeated_tags[label] = sorted(tag for tag in set(event_tags) if event_tags.count(tag) > 1)
    tracking = arrays["pool_analog_tracking_state"]
    # Column meaning is checked against saved profile fields above, not inferred from analog targets.
    current_tracking = (tracking[:,0] == sample_id) & (tracking[:,1] == epoch)
    changed = current_tracking[1:] & current_tracking[:-1] & np.any(tracking[1:,2:] != tracking[:-1,2:], axis=1)
    normal_updates = 0
    full_clears = 0
    anomalies = []
    for row in np.flatnonzero(changed)+1:
        previous_signs, next_signs = tracking[row-1,2:], tracking[row,2:]
        changed_slots = np.flatnonzero(previous_signs != next_signs)
        old_count, new_count = int(np.count_nonzero(previous_signs)), int(np.count_nonzero(next_signs))
        additions = changed_slots[(previous_signs[changed_slots] == 0) &
                                  np.isin(next_signs[changed_slots], [-1,1])]
        flips = changed_slots[(previous_signs[changed_slots] != 0) &
                              (next_signs[changed_slots] != 0)]
        clears = changed_slots[(previous_signs[changed_slots] != 0) &
                               (next_signs[changed_slots] == 0)]
        if not np.isin(previous_signs, [-1,0,1]).all() or not np.isin(next_signs, [-1,0,1]).all():
            kind = "committed_tracking_sign_anomaly"
        elif changed_slots.size == 1 and additions.size == 1 and new_count == old_count+1:
            kind = "committed_tracking_sign_update";normal_updates += 1
        elif new_count == 0 and old_count > 0 and clears.size == changed_slots.size:
            kind = "committed_tracking_sign_clear";full_clears += 1
        else:
            kind = "committed_tracking_sign_anomaly"
        event = dict(kind=kind, time_s=float(time[row]), old_nonzero_count=old_count,
                     new_nonzero_count=new_count, changed_slots_1based=(changed_slots+1).tolist(),
                     added_slots_1based=(additions+1).tolist(), flipped_slots_1based=(flips+1).tolist(),
                     cleared_slots_1based=(clears+1).tolist(),
                     old_signs=previous_signs.tolist(), new_signs=next_signs.tolist())
        events.append(event)
        if kind == "committed_tracking_sign_anomaly":anomalies.append(event)
    expected = {"D2": int(scalar(raw,"p/bits/d2_raw")), "TA": int(scalar(raw,"p/bits/tracking_count")),
                "tracking_updates": int(scalar(raw,"p/bits/tracking_updates"))}
    counts["tracking_updates"] = normal_updates
    columns = {"held_committed_cache_v": col(arrays[names[0]],"held","v_held"),
               "held_cache_sample_id": col(arrays[names[0]],"held","sample_id"),
               "held_cache_valid": col(arrays[names[0]],"held","valid"),
               "ra_predicted_vx_v": col(arrays[names[1]],"ra","vx"),
               "ct_predicted_vy_v": col(arrays[names[2]],"ct","vy"),
               "control_sample_id": col(control,"control","sample_id"),
               "control_epoch": col(control,"control","epoch")}
    for key in ("cnv", "ra_enable", "sar2_decide", "sar2_bit", "track_decide", "track_index"):
        columns["control_"+key] = col(control,"control",key)
    for k in range(tracking.shape[1]-2):
        columns[f"committed_tracking_sign_{k+1}"] = tracking[:,k+2]
    for name, value in columns.items():
        require(np.isfinite(value).all(), f"Nonfinite actual node/control values: {name}")
    summary = dict(status="actual_nodes_read", sample_id=sample_id, epoch=epoch,
                   time_source="Saved native solver tout at identical owner row indices; no interpolation",
                   first_native_row_0based=start, rows=len(time), events=events,
                   observed_counts=counts, expected_counts_from_saved_p_bits=expected,
                   observed_sign_clear_events=full_clears,
                   tracking_sign_anomalies=anomalies, repeated_decision_tags=repeated_tags,
                   decision_marker_method="Asserted segment start or asserted tag change within sample/epoch; noncontinuous repeats retained",
                   observed_counts_match_saved_counts=counts == expected and not anomalies and not any(repeated_tags.values()),
                   saved_indices={g:index[g] for g in ("held","ra","ct","control")},
                   saved_tracking_state_indices_1based=saved_tracking_indices.tolist(),
                   semantics="Held is committed meta.held cache observed by Outputs, not same-edge post-Update; "
                             "RA VX and CT VY are predicted endpoint probes. Sign changes observe committed "
                             "tracking state at a later Outputs row, not an analog settling assertion.")
    return summary, (time, columns, events)


def write_sample_nodes(output, sample_id, payload, plt):
    if payload is None:
        return
    time, columns, events = payload
    with (output/f"sample_{sample_id}_nodes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream);writer.writerow(["native_time_s"]+list(columns))
        writer.writerows([format(time[k],".17g")]+[format(v[k],".17g") for v in columns.values()]
                         for k in range(len(time)))
    fig, axes = plt.subplots(3,1,figsize=(10,7),sharex=True)
    t = (time-time[0])*1e9
    axes[0].step(t,columns["held_committed_cache_v"],where="post",label="Committed held cache (Outputs observation)")
    axes[1].plot(t,columns["ra_predicted_vx_v"],label="Predicted endpoint RA VX")
    axes[1].plot(t,columns["ct_predicted_vy_v"],label="Predicted endpoint CT VY")
    for key in ("sar2_decide","track_decide","ra_enable"):
        axes[2].step(t,columns["control_"+key],where="post",label=key)
    for event in events:
        x=(event["time_s"]-time[0])*1e9
        color={"D2":"tab:blue","TA":"tab:orange","committed_tracking_sign_update":"tab:green",
               "committed_tracking_sign_clear":"gray","committed_tracking_sign_anomaly":"red"}[event["kind"]]
        for ax in axes:ax.axvline(x,color=color,alpha=.22,lw=.8)
        if event["kind"] in ("D2","TA"):
            axes[2].annotate(f'{event["kind"]} {event["tag"]}',(x,1),xytext=(0,3),textcoords="offset points",rotation=90,fontsize=6)
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8,loc="best")
    axes[0].set_ylabel("Held (V)");axes[1].set_ylabel("Probe (V)");axes[2].set_ylabel("Control")
    axes[2].set_xlabel(f"Time from first plotted native row (ns); origin {time[0]:.17g} s")
    fig.suptitle(f"Actual sample ID {sample_id}: blue D2, orange TA, green sign update, gray sign clear")
    fig.tight_layout();fig.savefig(output/f"sample_{sample_id}_nodes.png",dpi=160);plt.close(fig)


def analyze(args):
    folder = args.capture_dir.resolve()
    result_path = folder / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    codes_json = np.asarray(result["code20"], dtype=np.float64).reshape(-1)
    count = codes_json.size
    # Refuse short captures before any analysis, manifest conversion or plot.
    require(count >= 256, f"Actual capture N={count}; N>=256 is required. No FFT performed.")
    require(count & (count - 1) == 0, "Actual record length must be a power of two")
    require(result["stage"] == "complete" and result["simulation_run"] is True,
            "Capture is not a completed actual simulation")
    require(result["records"] == count, "Result record count differs from actual codes")
    require(np.isfinite(codes_json).all() and np.all(codes_json == np.floor(codes_json))
            and np.all((codes_json >= 0) & (codes_json < 2**20)),
            "Codes must be finite integers in [0,2^20)")

    identity = json.loads(args.identity.read_text(encoding="utf-8"))
    entries = {}
    for item in identity["artifacts"]:
        name = item["file"].replace("\\", "/").rsplit("/", 1)[-1]
        require(name not in entries, f"Duplicate manifest basename: {name}")
        entries[name] = item
    hashes = {}
    for name in ("raw.mat", "selected.mat", "result.json"):
        require(name in entries, f"Manifest lacks {name}")
        local = folder / name
        require(local.stat().st_size == entries[name]["bytes"], f"Size mismatch: {name}")
        hashes[name] = sha(local)
        require(hashes[name] == entries[name]["sha256"], f"SHA mismatch: {name}")
    require(hashes["raw.mat"] == result["raw_sha256"], "Result raw SHA differs from manifest")

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(receipt["stage"] == "complete" and
            receipt["status"] == "actual_n256_capture_complete_pending_independent_analysis",
            "Require completed native dynamic receipt")
    require(receipt["run"]["run_report"] == result, "Receipt/result payloads differ")
    require(receipt["global_rng_unchanged"] is True and
            receipt["first_eight_codes_match_closed_short"] is True,
            "Native RNG/prefix gate did not pass")

    with h5py.File(folder / "raw.mat", "r") as raw, h5py.File(folder / "selected.mat", "r") as selected:
        metadata_paths = ["p/fs_hz", "p/sample_period_s", "p/fsr_diff_v", "p/seed", "p/capture/record_length",
                          "p/capture/first_sample_id", "p/stimulus/frequency_hz",
                          "p/stimulus/amplitude_v", "p/stimulus/phase_rad", "p/stimulus/offset_v"]
        metadata = {}
        for path in metadata_paths:
            metadata[path] = scalar(selected, path)
            same(metadata[path], scalar(raw, path), path + " raw/selected")
        for key in ("tones_hz", "tones_amplitude_v", "tones_phase_rad"):
            require(np.asarray(mat.variable(selected, "p/stimulus/" + key)).size == 0,
                    "Single-tone FFT requires no extra stimulus tones")
            same(mat.variable(selected, "p/stimulus/" + key),
                 mat.variable(raw, "p/stimulus/" + key), key)
        fs, fsr, fin = (metadata[k] for k in
                       ("p/fs_hz", "p/fsr_diff_v", "p/stimulus/frequency_hz"))
        amplitude = metadata["p/stimulus/amplitude_v"]
        require(fs > 0 and fsr > 0 and amplitude > 0, "Invalid fs/FSR/amplitude")
        require(metadata["p/capture/record_length"] == count, "Saved p capture count differs")
        seed = metadata["p/seed"]
        require(seed == np.floor(seed) and seed >= 0, "Saved master seed is invalid")
        codes = np.asarray(mat.variable(selected, "selected/code20"), dtype=np.float64).reshape(-1)
        ids = np.asarray(mat.variable(selected, "selected/sample_ids")).reshape(-1)
        record = np.asarray(mat.variable(selected, "selected/record"))
        times = np.asarray(mat.variable(selected, "selected/nominal_sample_time_s")).reshape(-1)
        indices = mat.variable(selected, "p/idx/record")
        model_hash = mat.variable(raw, "modelHash")
        chosen_id = int(metadata["p/capture/first_sample_id"])+4 if args.sample_id is None else args.sample_id
        require(chosen_id in ids, "Node-view sample ID must be in the selected actual record")
        epoch_col = int(indices["epoch"])-1
        node_summary, node_payload = sample_nodes(raw, chosen_id, int(record[0,epoch_col]))
    same(codes, codes_json, "selected code20/result code20")
    same(ids, result["sample_ids"], "selected IDs/result IDs")
    first = metadata["p/capture/first_sample_id"]
    require(first == np.floor(first) and first >= 0, "Invalid saved first ID")
    same(ids, first + np.arange(count), "actual contiguous IDs")
    require(record.shape == (count, 11), "Actual selected Record11 shape differs")
    col = lambda name: record[:, int(indices[name]) - 1]
    same(col("sample_id"), ids, "Record11/sample IDs")
    epochs = col("epoch")
    require(np.isfinite(epochs).all() and np.all(epochs == np.floor(epochs)) and
            np.all((epochs >= 0) & (epochs <= 2**32 - 1)) and np.unique(epochs).size == 1,
            "Actual record must have one valid public epoch")
    require(np.all(col("valid") == 1) and np.all(col("ovr") == 0) and
            np.all(col("saturation") == 0), "Invalid/overrange/saturated Record11")
    require(times.size == count and np.isfinite(times).all() and np.all(np.diff(times) > 0),
            "Invalid nominal sample time array")
    # These are saved nominal calendar times, not a reconstruction of analog apertures.
    period = metadata["p/sample_period_s"]
    require(period > 0 and fs*period == 1, "Saved sample period and Fs are inconsistent")
    same(times, ids*period, "saved nominal calendar/producer ids*saved sample_period_s")
    require(model_hash == result["model_sha256"], "Raw/result model SHA differs")

    cycles = fin * count / fs
    fundamental = int(np.rint(cycles))
    require(0 < fundamental < count // 2 and abs(cycles - fundamental) < 1e-9,
            f"Actual stimulus is not coherent: cycles={cycles!r}")
    voltage = ((codes + 0.5) / 2**20 - 0.5) * fsr
    dc = float(np.mean(voltage))
    transform = np.fft.rfft(voltage - dc) / count
    power = np.abs(transform)**2
    power[1:-1] *= 2
    signal = float(power[fundamental])
    other = power.copy()
    other[[0, fundamental]] = 0
    nd = float(np.sum(other))
    harmonic_bins = np.mod(np.arange(2, 11) * fundamental, count)
    harmonic_bins = np.minimum(harmonic_bins, count - harmonic_bins)
    harmonic_bins = np.setdiff1d(np.unique(harmonic_bins), [0, fundamental])
    hp = float(np.sum(power[harmonic_bins]))
    noise = nd - hp
    spur = float(np.max(other))
    require(min(signal, nd, hp, noise, spur) > 0, "Degenerate powers; finite metric reporting is unsupported")
    metrics = dict(sndr_db=float(10*np.log10(signal/nd)), sfdr_db=float(10*np.log10(signal/spur)),
                   thd_db=float(10*np.log10(hp/signal)), snr_db=float(10*np.log10(signal/noise)))
    metrics["enob"] = (metrics["sndr_db"] - 1.76) / 6.02
    native = result["spectrum"]
    same(native["record_length"], count, "native spectrum N")
    same(native["sample_rate_hz"], fs, "native spectrum Fs")
    same(native["input_frequency_hz"], fin, "native spectrum Fin")
    same(native["fundamental_bin"], fundamental, "native spectrum bin")
    comparisons = {}
    for key, value in metrics.items():
        reference = float(native[key])
        require(np.isfinite(reference), f"Nonfinite native metric: {key}")
        comparisons[key] = dict(numpy=value, native=reference, delta=value-reference)
    # Deliberately report FFT-library numerical deltas, without invented model acceptance tolerances.
    native_power = np.asarray(native["power_v2"], dtype=float).reshape(-1)
    require(native_power.shape == power.shape and np.isfinite(native_power).all(), "Native spectrum shape/finite mismatch")
    frequency = np.arange(count//2 + 1)*fs/count
    same(np.asarray(native["frequency_hz"]).reshape(-1), frequency, "native frequency axis")
    input_level = float(20*np.log10(amplitude/(fsr/2)))
    report = dict(schema="sar20-independent-actual-dynamic/v1", status="actual_codes_independently_characterized",
                  scope="Actual code20 coherent rectangular FFT; no INL/DNL, calibration, full-state or physical signoff",
                  capture_dir=str(folder), native_receipt=str(args.receipt.resolve()),
                  input_hashes=hashes, identity_sha256=sha(args.identity), receipt_sha256=sha(args.receipt),
                  analysis_sha256=sha(Path(__file__)), mat_reader_sha256=sha(ROOT/"analysis/mat_reader.py"),
                  native_spectrum_source_sha256=sha(ROOT/"current/model/cicc/matlab/cicc_spectrum.m"),
                  native_model_sha256=model_hash, numpy_version=np.__version__, python=sys.executable,
                  sample_node_view=node_summary,
                  metadata=metadata, metadata_source="raw.mat and selected.mat saved p; equality required",
                  record_length=count, fundamental_bin=fundamental, cycles=cycles,
                  harmonic_bins=harmonic_bins.tolist(), epoch=int(epochs[0]),
                  first_sample_id=int(ids[0]), last_sample_id=int(ids[-1]),
                  commanded_input_level_dbfs=input_level,
                  stimulus_amplitude_scope="Saved p.stimulus command; not a measured held-node amplitude",
                  code_min=int(codes.min()), code_max=int(codes.max()),
                  rail_code_count=int(np.count_nonzero((codes == 0)|(codes == 2**20-1))),
                  nominal_time_source="selected.nominal_sample_time_s; not analog aperture measurement",
                  metrics=metrics, native_metric_comparisons=comparisons,
                  native_power_max_abs_delta_v2=float(np.max(np.abs(power-native_power))),
                  metric_comparison_tolerance=None, dc_voltage_v=dc,
                  signal_power_v2=signal, noise_distortion_power_v2=nd,
                  harmonic_H2_H10_power_v2=hp, noise_excluding_H2_H10_power_v2=noise,
                  conventions=dict(code_scale="Unsigned Q20 bin-center voltage: ((code+0.5)/2^20-0.5)*saved FSR",
                                   window="rectangular, coherent actual input", bandwidth="DC excluded through Nyquist",
                                   snr="Excludes only H2..H10; higher harmonics remain in noise",
                                   enob="(actual-level SNDR-1.76)/6.02; no full-scale amplitude correction",
                                   thd="H2..H10 power / fundamental power, dB",
                                   sfdr="Fundamental / largest non-DC non-fundamental single-bin power, dBc"),
                  unsupported_metrics=["INL", "DNL", "FOM", "full 20-bit static linearity"])
    # Verify all small/large inputs remained the same files through read-only analysis.
    for name, digest in hashes.items():
        require(sha(folder/name) == digest, f"Input changed during analysis: {name}")
    require(not args.output_dir.exists(), "Output directory already exists; refusing overwrite")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    args.output_dir.mkdir(parents=True)
    with (args.output_dir/"codes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sample_id", "epoch", "nominal_time_s", "code20"])
        writer.writerows((int(i), int(e), format(t, ".17g"), int(c)) for i,e,t,c in zip(ids,epochs,times,codes))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(frequency/1e3, 10*np.log10(np.maximum(power/signal, np.finfo(float).tiny)), lw=1)
    ax.set(xlabel="Frequency (kHz)", ylabel="Power per bin (dBc)",
           title=f"Actual code20: N={count}, Fin={fin:g} Hz", xlim=(0, fs/2e3))
    ax.grid(alpha=.25);fig.tight_layout()
    fig.savefig(args.output_dir/"spectrum.png", dpi=160);plt.close(fig)
    write_sample_nodes(args.output_dir, chosen_id, node_payload, plt)
    (args.output_dir/"analysis.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(dict(status=report["status"], output_dir=str(args.output_dir), metrics=metrics)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-id", type=int, help="Actual sample for node view; default first selected ID+4")
    args = parser.parse_args()
    try:
        analyze(args)
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps(dict(status="analysis_rejected", error=str(error))), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
