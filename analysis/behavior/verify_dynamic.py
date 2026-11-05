"""v1: independently characterize saved Simulink codes; never simulate an ADC.

Usage: analysis_env/bin/python verify_dynamic.py <actual_run_directory>
Reads selected.mat/parameters.mat/summary.json and preserves their hashes.
FFT-library differences are reported, not hidden by a changed model tolerance.
"""
from pathlib import Path
import hashlib
import json
import sys

import h5py
import numpy as np

run = Path(sys.argv[1]).resolve()
summary = json.loads((run / "summary.json").read_text())
assert summary["status"] == "complete" and summary["simulation_completed"]
with h5py.File(run / "selected.mat") as f:
    codes = f["selected/code20"][()].reshape(-1)
    raw = f["selected/raw"][()].T
    times = f["selected/time_s"][()].reshape(-1)
    fs = float(f["metadata/fs_hz"][()].item())
    fsr = float(f["metadata/fsr_diff_v"][()].item())
    fin = float(f["metadata/stimulus/frequency_hz"][()].item())
with h5py.File(run / "parameters.mat") as f:
    first = int(f["P/first_id"][()].item())
    epoch = int(f["P/epoch"][()].item())
    n = int(f["P/N"][()].item())
assert n == 256 == len(codes) == summary["records"]
assert np.array_equal(codes, summary["code20"])
assert np.array_equal(raw, summary["raw_words"])
assert np.array_equal(raw[:, 3], np.arange(first, first + n))
assert np.all(raw[:, 4] == epoch) and np.all(raw[:, 5] == 1)
assert np.all(codes == np.floor(codes)) and np.all((codes >= 0) & (codes < 2**20))
fundamental = round(fin * n / fs)
assert abs(fin * n / fs - fundamental) < 1e-9
volts = ((codes + 0.5) / 2**20 - 0.5) * fsr
spectrum = np.fft.fft(volts - volts.mean()) / n
power = np.abs(spectrum[: n // 2 + 1]) ** 2
power[1:-1] *= 2
other = power.copy()
other[[0, fundamental]] = 0
harmonics = np.mod(np.arange(2, 11) * fundamental, n)
harmonics = np.setdiff1d(np.unique(np.minimum(harmonics, n - harmonics)), [0, fundamental])
signal, nd, distortion = power[fundamental], other.sum(), power[harmonics].sum()
metrics = {
    "snr_db": float(10 * np.log10(signal / (nd - distortion))),
    "sndr_db": float(10 * np.log10(signal / nd)),
    "sfdr_db": float(10 * np.log10(signal / other.max())),
    "thd_db": float(10 * np.log10(distortion / signal)),
}
metrics["enob"] = (metrics["sndr_db"] - 1.76) / 6.02
identity = {
    name: hashlib.sha256((run / name).read_bytes()).hexdigest()
    for name in ("selected.mat", "parameters.mat", "summary.json", "SarAdc.slx", "source.zip")
}
report = {
    "status": "actual_codes_independently_characterized",
    "records": n,
    "ids": [first, first + n - 1],
    "epoch": epoch,
    "fs_hz": fs,
    "fin_hz": fin,
    "metrics": metrics,
    "numpy_minus_matlab": {k: metrics[k] - summary[k] for k in metrics},
    "source_identity": identity,
    "scope": "Coherent FFT only, H2-H10 harmonic separation; no INL/DNL or complete-paper claim",
}
(run / "independent_spectrum.json").write_text(json.dumps(report, indent=2))
np.savetxt(run / "codes.csv", np.column_stack((raw, times, codes)), delimiter=",",
           header="D1,D2,DT,sample_id,epoch,valid,raw_ready_time_s,code20", comments="", fmt="%.17g")
print(json.dumps({k: report[k] for k in ("status", "metrics", "numpy_minus_matlab")}, indent=2))
