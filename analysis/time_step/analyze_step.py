#!/usr/bin/env python3
"""SAR20 step sensitivity, version 1.1 (2026-10-26).

Usage: <project>/dependencies/analysis_env/bin/python analysis/time_step/analyze_step.py
Reads two actual Simulink captures. It does not generate ADC samples or change
MATLAB, configuration, source, random state, or tolerances. Time and payloads
are paired by native row index, never by interpolation or nearest-time search.
Voltage/code differences are observations, not an invented convergence limit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import mat_reader as mat


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bits(value: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(value).view(np.uint64)


def serial(value):
    """JSON preserves finite binary64 values; nonfinite diagnostics stay explicit."""
    value = float(value)
    return value if np.isfinite(value) else str(value)


def read_arm(label: str) -> dict:
    folder = ROOT / "analysis/p0_data" / label
    origins = json.loads((folder.parent / "PATHS.json").read_text())
    origin = origins[label] if label in origins else json.loads((folder / "ORIGIN.json").read_text())
    for name, meta in origin["files"].items():
        assert sha(folder / name) == meta["sha256"], f"SHA mismatch: {label}/{name}"
    result = json.loads((folder / "result.json").read_text())
    with h5py.File(folder / "raw.mat", "r") as raw:
        plan = mat.read_logger_plan(raw)
        tout = mat.read_solver_tout(raw)
        signals = {name: np.asarray(raw[m["dataset_path"]][()]).T.copy()
                   for name, m in plan.items()}
        index = {group: {k: int(v) - 1 for k, v in
                        mat.variable(raw, f"p/idx/{group}").items()}
                 for group in ("ra", "ct", "control", "comparator")}
        model = mat.variable(raw, "modelHash")
        step = mat.variable(raw, "PoolAnalogCfg/max_step_s")
        fsr = mat.variable(raw, "p/fsr_diff_v")
        owner_dt = float(mat.variable(raw, "p/dt_s"))
        global_dt = float(mat.variable(raw, "cfg/dt_s"))
    assert result["model_sha256"] == model
    assert result["raw_sha256"] == sha(folder / "raw.mat")
    # The captures log at the global tick or exactly every fifth global tick.
    # Bind these rows to saved native tout rather than synthesizing event times.
    assert step == result["assumptions"]["max_step_s"]
    expected_step = {"be250": 250e-12, "be125": 125e-12, "be62p5": 62.5e-12}[label]
    assert float(step) == expected_step
    assert owner_dt == 5 * global_dt
    times, time_residuals = {}, {}
    for name, m in plan.items():
        if m["rows"] == len(tout):
            native = tout
            assert m["dt"] == global_dt
        elif m["rows"] == len(tout[::5]):
            native = tout[::5]
            assert m["dt"] == owner_dt
        else:
            raise ValueError(f"Unsupported native time mapping: {name}, {m}")
        assert native[0] == m["t0"]
        times[name] = native
        descriptor = mat._time_bits(m, 0, m["rows"]).view(np.float64)
        time_residuals[name] = float(np.max(np.abs(descriptor - native)))
    return dict(label=label, folder=folder, origin=origin, result=result,
                plan=plan, tout=tout, signals=signals, times=times,
                index=index, step=float(step), fsr=float(fsr),
                descriptor_to_native_max_abs_s=time_residuals)


def compare(a: dict, b: dict) -> dict:
    assert a["plan"].keys() == b["plan"].keys(), "Logger inventory changed"
    assert np.array_equal(bits(a["tout"]), bits(b["tout"])), "Native tout changed"
    assert a["index"] == b["index"], "Port index definitions changed"
    rows = []
    for name in sorted(a["plan"]):
        ma, mb = a["plan"][name], b["plan"][name]
        for field in ("rows", "width", "t0", "dt"):
            assert ma[field] == mb[field], f"Logger descriptor changed: {name}/{field}"
        assert np.array_equal(mat._time_bits(ma, 0, ma["rows"]),
                              mat._time_bits(mb, 0, mb["rows"]))
        x, y = a["signals"][name], b["signals"][name]
        different = bits(x) != bits(y)
        locations = np.argwhere(different)
        row = dict(logger=name, rows=ma["rows"], width=ma["width"],
                   difference_scope="entire_capture_including_warmup",
                   time_descriptor_bits_equal=True,
                   mapped_native_grid_bits_equal=bool(np.array_equal(
                       bits(a["times"][name]), bits(b["times"][name]))),
                   descriptor_to_native_max_abs_s={
                       arm["label"]: arm["descriptor_to_native_max_abs_s"][name]
                       for arm in (a, b)},
                   bitwise_equal=not bool(locations.size),
                   differing_elements=int(different.sum()))
        if locations.size:
            i, j = map(int, locations[0])
            row["first_difference"] = dict(row_0based=i, column_1based=j + 1,
                                          native_time_s=float(a["times"][name][i]),
                                          values={a["label"]: serial(x[i, j]),
                                                  b["label"]: serial(y[i, j])})
        rows.append(row)
    probes = {}
    for logger, group, field in [("pool_analog_ra", "ra", "vx"),
                                 ("pool_analog_ct", "ct", "vy")]:
        col = a["index"][group][field]
        delta = b["signals"][logger][:, col] - a["signals"][logger][:, col]
        probes[field] = dict(logger=logger, column_1based=col + 1, unit="Vdiff",
                            scope="entire_capture_including_warmup",
                            semantics="Outputs endpoint probe; Update commits afterward",
                            max_abs_difference_v=float(np.max(np.abs(delta))))
    ra = a["result"], b["result"]
    assert ra[0]["sample_ids"] == ra[1]["sample_ids"]
    codes = []
    for sid, x, y in zip(ra[0]["sample_ids"], ra[0]["code20"], ra[1]["code20"]):
        codes.append(dict(sample_id=sid, values={a["label"]: x, b["label"]: y},
                          delta_code=y-x, delta_direction=b["label"] + " - " + a["label"],
                          nominal_input_delta_v=(y-x)*a["fsr"]/(1 << 20)))
    return dict(status="actual_step_sensitivity_observed_no_convergence_verdict",
                analysis_source_sha256=sha(Path(__file__)),
                scope="N8 compact captures; no FFT, full-state, PRNG, or KCL acceptance",
                max_step_s=[a["step"], b["step"]],
                raw_sha256=[a["result"]["raw_sha256"], b["result"]["raw_sha256"]],
                model_sha256=[r["model_sha256"] for r in ra],
                elapsed_s=[r["elapsed_s"] for r in ra],
                native_tout_bits_equal=True, all_logger_time_descriptors_equal=True,
                time_mapping="Rows follow saved global/owner cadence and start/count. "
                             "Native grids and descriptors are compared exactly between the two arms. "
                             "Descriptor-to-native floating differences are reported, "
                             "not accepted against an invented time tolerance.",
                source_config_identity="See independent engineering_check; not inferred from filenames",
                bitwise_equal_loggers=[r["logger"] for r in rows if r["bitwise_equal"]],
                logger_comparisons=rows, physical_probe_differences=probes, codes=codes,
                code_voltage_scope="nominal Q20 code scaling, not a measured analog node difference",
                convergence_limit=None,
                missing_evidence=["no frozen time-discretization error budget",
                                  "compact omits full analog retained state and sample-kTC RNG/charge words",
                                  "comparator old/predicted state logs exist; RNG sequence not accepted here"])


def plot(a: dict, b: dict, target: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ctl = a["signals"]["adc_control"]
    ci = a["index"]["control"]
    sid_key = "sample_id"
    assert sid_key in ci, "Require saved control sample ID, never infer column"
    control_mask = ctl[:, ci[sid_key]] == 4
    assert np.count_nonzero(control_mask), "No actual sample ID4 rows"
    assert np.array_equal(np.unique(ctl[control_mask, ci["epoch"]]), [1.0])
    mask = control_mask.copy()
    for group, logger in [("ra", "pool_analog_ra"), ("ct", "pool_analog_ct")]:
        for arm in (a, b):
            mask &= arm["signals"][logger][:, arm["index"][group]["sample_id"]] == 4
    t = a["times"]["adc_control"][mask]
    start = a["times"]["adc_control"][control_mask][0]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    for ax, logger, group, field, title in [
        (axes[0], "pool_analog_ra", "ra", "vx", "RA output VX"),
        (axes[1], "pool_analog_ct", "ct", "vy", "CT comparator node VY")]:
        col = a["index"][group][field]
        for arm in (a, b):
            v = arm["signals"][logger][mask, col]
            ax.plot((t-start)*1e9, v, label=f'{arm["step"]*1e12:g} ps')
        ax.set_ylabel("Vdiff [V]")
        ax.set_title(title, loc="left")
        ax.grid(alpha=.2)
        ax.legend(loc="best")
    for logger, group, field in [("pool_analog_ra", "ra", "vx"),
                                 ("pool_analog_ct", "ct", "vy")]:
        col = a["index"][group][field]
        delta = b["signals"][logger][mask, col] - a["signals"][logger][mask, col]
        axes[2].plot((t-start)*1e9, delta*1e6, label=field.upper())
    axes[2].set_ylabel(f'{b["step"]*1e12:g} - {a["step"]*1e12:g} ps (uV)')
    axes[2].set_xlabel("Native time from first control sample ID4 row (ns)")
    axes[2].grid(alpha=.2)
    axes[2].legend(loc="best")
    fig.suptitle("Actual PoolCt N8 | ID4, epoch1 | UGB 1.2 GHz | calibration off\n"
                 "Outputs endpoint probes; Update commits afterward. First old-tag row excluded.")
    fig.savefig(target, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    labels = sys.argv[1:] or ["be250", "be125"]
    assert len(labels) == 2
    arms = [read_arm(label) for label in labels]
    report = compare(*arms)
    suffix = "" if labels == ["be250", "be125"] else "_" + "_".join(labels)
    (here / ("step_comparison" + suffix + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    plot(*arms, here / ("sample4_step" + suffix + ".png"))
    print(json.dumps({"status": report["status"], "loggers": len(report["logger_comparisons"]),
                      "equal_loggers": len(report["bitwise_equal_loggers"]),
                      "codes": report["codes"]}, indent=2), flush=True)
