#!/usr/bin/env python3
"""SAR20 same-condition capture gate v1 (2026-10-26).

Compare the current-source 250 ps anchor to the archived 250 ps capture.
This gate requires exact stored data/time/tout/selected bits. It must not be
used as an equality criterion between different integration steps.
Run with <project>/dependencies/analysis_env/bin/python and this script path.
"""
from pathlib import Path
import hashlib
import json
import sys

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import mat_reader as mat


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def exact(a, b):
    if isinstance(a, dict) or isinstance(b, dict):
        return (isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys()
                and all(exact(a[k], b[k]) for k in a))
    if isinstance(a, list) or isinstance(b, list):
        return (isinstance(a, list) and isinstance(b, list) and len(a) == len(b)
                and all(exact(x, y) for x, y in zip(a, b)))
    if isinstance(a, str) or isinstance(b, str):
        return type(a) == type(b) and a == b
    x, y = np.asarray(a), np.asarray(b)
    return x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes()


def compare():
    base = ROOT / "analysis/p0_data"
    ref, new = base / "be250", base / "anchor"
    inputs = {}
    for label, folder in (("reference", ref), ("anchor", new)):
        result = json.loads((folder / "result.json").read_text())
        assert sha(folder / "raw.mat") == result["raw_sha256"]
        assert result["assumptions"]["max_step_s"] == 250e-12
        inputs[label] = dict(raw_sha256=sha(folder / "raw.mat"),
                             result_sha256=sha(folder / "result.json"),
                             selected_sha256=sha(folder / "selected.mat"),
                             model_sha256=result["model_sha256"],
                             elapsed_s=result["elapsed_s"])
    rows = []
    with h5py.File(ref / "raw.mat") as a, h5py.File(new / "raw.mat") as b:
        pa, pb = mat.read_logger_plan(a), mat.read_logger_plan(b)
        assert pa.keys() == pb.keys(), "Logger inventory differs"
        tout_equal = exact(mat.read_solver_tout(a), mat.read_solver_tout(b))
        for name in sorted(pa):
            ma, mb = pa[name], pb[name]
            same_shape = (ma["rows"], ma["width"]) == (mb["rows"], mb["width"])
            time_equal = same_shape and exact(mat._time_bits(ma, 0, ma["rows"]),
                                              mat._time_bits(mb, 0, mb["rows"]))
            data_equal = same_shape and exact(a[ma["dataset_path"]][()],
                                              b[mb["dataset_path"]][()])
            rows.append(dict(logger=name, shape_equal=same_shape,
                             data_bits_equal=data_equal, time_bits_equal=time_equal))
    with h5py.File(ref / "selected.mat") as a, h5py.File(new / "selected.mat") as b:
        selected_equal = exact(mat.variable(a, "selected"), mat.variable(b, "selected"))
    passed = tout_equal and selected_equal and all(
        r["shape_equal"] and r["data_bits_equal"] and r["time_bits_equal"] for r in rows)
    result = dict(status="bitwise_anchor_pass" if passed else "bitwise_anchor_fail",
                  scope="Current M8 source at same UGB/input/seed/250ps; compact observable capture",
                  inputs=inputs, native_tout_bits_equal=tout_equal,
                  entire_selected_tree_bits_equal=selected_equal, loggers=rows,
                  full_analog_state_or_charge_coverage=False,
                  tolerance_used=None)
    path = Path(__file__).resolve().parent / "anchor_comparison.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "loggers"}, indent=2), flush=True)
    assert passed, "Current source does not reproduce the archived same-condition capture"


if __name__ == "__main__":
    compare()
