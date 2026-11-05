#!/usr/bin/env python3
"""Read existing finite-DAC captures; never simulate or write run artifacts."""

from pathlib import Path
import hashlib
import json
import math

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
NATIVE = RUNS / "az_probe_20261027T020421Z"
ZERO = RUNS / "az_probe_20261027T022517Z"
FINITE = RUNS / "az_probe_20261027T023003Z"
OLD = RUNS / "behavior_e385aab5-b7f4-48bc-8111-eb231b8e4d50"
CASES = (
    "dac_off_tau0",
    "dac_enabled_tau0",
    "dac_finite_0p1ns",
    "dac_finite_1ns",
    "dac_finite_5ns",
    "dac_Inf_nonsettling_negative",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_logs(path):
    # Reader for these saved MATLAB 7.3 SimulationOutput files. Fail closed if
    # the saved object inventory does not match the timeseries inventory.
    with h5py.File(path) as h:
        seq = [h[ref] for ref in h["#subsystem#/MCOS"][()].ravel()]
        owners = [x for x in seq if isinstance(x, h5py.Group)
                  and {"raw_log", "event_log"} <= set(x)]
        assert len(owners) == 1, (path, len(owners))
        owner = owners[0]
        names = [name for _, name in sorted(
            (int(owner[name][()].ravel()[4]), name)
            for name in owner if name not in ("tout", "yout"))]
        series = []
        for i, data in enumerate(seq):
            if (i < 11 or not isinstance(data, h5py.Dataset)
                    or data.dtype.kind not in "fiu" or len(data.shape) < 2):
                continue
            count, time = seq[i - 11], seq[i - 9]
            if not (isinstance(count, h5py.Dataset)
                    and count.dtype == np.dtype("float64")
                    and count.shape == (1, 1)
                    and isinstance(time, h5py.Dataset)
                    and time.dtype == np.dtype("float64")):
                continue
            n = int(count[()].item())
            if n > 0 and time.shape == (1, n) and (n == 1 or data.shape[-1] == n):
                cls = data.attrs.get("MATLAB_class", b"")
                if isinstance(cls, bytes):
                    cls = cls.decode()
                series.append({"time": time[()].ravel(),
                               "data": data[()].reshape((-1, n)).T,
                               "class": str(cls),
                               "storage_shape": data.shape})
        assert len(names) == len(series), (path, len(names), len(series))
        return dict(zip(names, series))


def same_array(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


def same_log(a, b):
    return (a["class"] == b["class"] and a["storage_shape"] == b["storage_shape"]
            and same_array(a["time"], b["time"]) and same_array(a["data"], b["data"]))


def saved_parameters(path):
    with h5py.File(path) as h:
        def val(name):
            a = h["P/" + name][()]
            return a.ravel()[0].item() if a.size == 1 else a.ravel()
        return {name: val(name) for name in (
            "N", "first_id", "epoch", "Ts_s", "stop_time_s", "seed",
            "input/offset_v", "input/amplitude_v", "input/frequency_hz",
            "input/phase_rad", "digital/vref_v", "digital/fsr_diff_v",
            "digital/ra_gain", "digital/d2_offset_ra_v",
            "digital/d2_weights_ra_v", "digital/tracking_step_ra_v")}


def independently_decode(raw, p):
    d1, d2, dt = map(int, raw[:3])
    coarse, fine = divmod(d1, 32)
    vref = p["digital/vref_v"]
    v1 = (32 * coarse + 2 * fine - 1039) * vref / 1024 - 17 * vref / 1024
    d2_bits = np.array([(d2 >> bit) & 1 for bit in range(11, -1, -1)])
    dt_bits = np.array([(dt >> bit) & 1 for bit in range(7, -1, -1)])
    gain = p["digital/ra_gain"]
    v2 = (p["digital/d2_offset_ra_v"]
          + np.sum(p["digital/d2_weights_ra_v"] * d2_bits)) / gain
    vt = (p["digital/tracking_step_ra_v"]
          * np.sum(np.arange(8, 0, -1) * (2 * dt_bits - 1)) / 8 / gain)
    scaled = ((v1 + v2) + vt) * 2**20 / p["digital/fsr_diff_v"] + 2**19
    return int(np.clip(math.floor(scaled + 0.5), 0, 2**20 - 1))


def verify_case(name, baseline):
    folder = (ZERO if name in CASES[:2] else FINITE) / name
    p = saved_parameters(folder / "parameters.mat")
    logs = read_logs(folder / "simout.mat")
    assert same_log(logs["event_log"], baseline["event_log"]), name
    event = logs["event_log"]
    ready = logs["record_ready_log"]
    record = logs["record_log"]
    code = logs["code_log"]
    assert same_array(ready["time"], record["time"])
    assert same_array(ready["time"], code["time"])
    all_ready = np.flatnonzero(ready["data"][:, 0] == 1)
    rows = record["data"][all_ready]
    first, count, epoch = int(p["first_id"]), int(p["N"]), int(p["epoch"])
    in_window = (rows[:, 3] >= first) & (rows[:, 3] < first + count)
    selected = all_ready[in_window]
    raw = record["data"][selected]
    codes = code["data"][selected, 0]
    assert np.array_equal(raw[:, 3], np.arange(first, first + count)), name
    assert np.all(raw[:, 4] == epoch), name
    # Keep both valid and invalid rows in the requested ID range.
    assert all(independently_decode(row, p) == int(c)
               for row, c in zip(raw, codes)), name
    for ix, row in zip(selected, raw):
        adc = logs["raw_log"]["data"]
        found = np.flatnonzero((logs["ready_log"]["data"][:, 0] == 1)
                               & (adc[:, 3] == row[3]) & (adc[:, 4] == row[4]))
        assert len(found) == 1 and same_array(adc[found[0]], row), (name, row[3])
        cnv = event["time"][(event["data"][:, 0] == row[3] + 2)
                            & (event["data"][:, 1] == 1)]
        assert len(cnv) == 1 and record["time"][ix] == cnv[0] + 138e-9
    return {"case": name, "target_rows": len(raw),
            "all_ready_rows_including_startup": len(all_ready),
            "valid": int(np.count_nonzero(raw[:, 5] == 1)),
            "invalid": int(np.count_nonzero(raw[:, 5] != 1)),
            "codes": [int(x) for x in codes],
            "all_event_time_and_data_bits_match_off": True,
            "adc_raw_to_rx_and_integer_decode_exact": True,
            "actual_slot_cnv_plus_138ns_exact": True}


def main():
    native = json.loads((NATIVE / "independent_native.json").read_text())
    for name, expected in native["files_sha256"].items():
        assert sha(NATIVE / name) == expected, name
    for name, expected in native["source_sha256"].items():
        assert sha(NATIVE / "candidate" / name) == expected, name
    finite = json.loads((FINITE / "independent_finite.json").read_text())
    for case in finite["cases"]:
        for name, expected in case["file_sha256"].items():
            assert sha(FINITE / case["name"] / name) == expected, (case["name"], name)
    for case in finite["scratch_off_allzero_actual_29logs_vs_old"]:
        assert sha(ZERO / case["case"] / "simout.mat") == case["simout_sha256"]

    old = read_logs(OLD / "simout.mat")
    off = read_logs(ZERO / CASES[0] / "simout.mat")
    on_zero = read_logs(ZERO / CASES[1] / "simout.mat")
    assert len(old) == 29 and len(off) == len(on_zero) == 30
    assert set(off) == set(on_zero) and set(off) - set(old) == {"dac_ra_pre_log"}
    assert all(same_log(off[name], old[name]) for name in old)
    assert all(same_log(on_zero[name], old[name]) for name in old)
    assert all(same_log(off[name], on_zero[name]) for name in off)
    rows = [verify_case(name, off) for name in CASES]
    print(json.dumps({"historical_hashes_match_independent_reports": True,
                      "off_and_on_zero_each_match_old_29_logs": True,
                      "off_and_on_zero_match_all_30_logs": True,
                      "cases": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
