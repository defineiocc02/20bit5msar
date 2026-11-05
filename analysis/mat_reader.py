"""SAR20 MAT reader v1 (2026-10-26).
Read actual MATLAB v7.3 parameters and logger payloads; never simulate an ADC.
Reader routines are copied unchanged from archived verified readers. The Time
stream descriptor is only for same-index equality; physical event time must be
bound to native solver tout. See mat_reader_origin.json for source SHA.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import h5py
import numpy as np
from scipy import sparse

def _matlab_class(node: h5py.Dataset) -> str:
    value = node.attrs.get("MATLAB_class", b"")
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("ascii", errors="replace")
    return str(value)


def _scalar_double(node: h5py.Dataset) -> float | None:
    if _matlab_class(node) != "double" or node.dtype.kind != "f" or node.size != 1:
        return None
    return float(np.asarray(node[()]).reshape(-1)[0])


def _locate_simulation_output(sequence: list[Any]) -> h5py.Group:
    candidates = [
        obj for obj in sequence
        if isinstance(obj, h5py.Group) and {"tout", "yout"}.issubset(obj.keys())
    ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one serialized SimulationOutput; found {len(candidates)}")
    return candidates[0]


def read_solver_tout(raw: h5py.File) -> np.ndarray:
    refs = np.asarray(raw["#subsystem#/MCOS"][()]).reshape(-1)
    simout = _locate_simulation_output([raw[ref] for ref in refs])
    values = np.asarray(simout["tout"][()], dtype=np.float64).reshape(-1)
    if values.size == 0:
        raise ValueError(f"{raw.filename}: native solver tout is empty")
    return values


def read_logger_plan(raw_source: Path | h5py.File) -> dict[str, dict[str, Any]]:
    """Index logger metadata; return dataset paths so caller controls file lifetime."""
    if isinstance(raw_source, h5py.File):
        return _read_logger_plan_from_file(raw_source)
    with h5py.File(raw_source, "r", rdcc_nbytes=1 << 20, rdcc_nslots=521) as raw:
        return _read_logger_plan_from_file(raw)


def _read_logger_plan_from_file(raw: h5py.File) -> dict[str, dict[str, Any]]:
    if "#subsystem#/MCOS" not in raw:
        raise ValueError(f"{raw.filename}: no #subsystem#/MCOS table")
    refs = np.asarray(raw["#subsystem#/MCOS"][()]).reshape(-1)
    sequence = [raw[ref] for ref in refs]
    simout = _locate_simulation_output(sequence)
    names = set(simout.keys()) - {"tout", "yout"}
    if not names:
        raise ValueError(f"{raw.filename}: SimulationOutput has no logger variables")
    ordered = []
    for name in names:
        ref_row = np.asarray(simout[name][()]).reshape(-1)
        if ref_row.size <= 4:
            raise ValueError(f"{raw.filename}: logger {name} has no MCOS order index")
        ordered.append((int(ref_row[4]), name))
    ordered.sort()
    order_indices = [index for index, _ in ordered]
    expected_indices = list(range(2, 2 + 5 * len(names), 5))
    if order_indices != expected_indices:
        raise ValueError(
            f"{raw.filename}: unsupported MCOS logger order {order_indices}; "
            f"expected {expected_indices}"
        )

    series: list[dict[str, Any]] = []
    start = 0
    for i, obj in enumerate(sequence):
        if not isinstance(obj, h5py.Dataset) or _matlab_class(obj) != "double":
            continue
        if obj.dtype.kind != "f" or obj.dtype.itemsize != 8 or len(obj.shape) != 2:
            continue
        if obj.shape[0] < 1 or obj.shape[1] < 1:
            continue
        scalar_values = [
            value for q in sequence[start:i]
            if isinstance(q, h5py.Dataset)
            for value in [_scalar_double(q)]
            if value is not None
        ]
        dts = [x for x in scalar_values if 0.0 < x < 1e-6]
        t0s = [x for x in scalar_values if x < 0.0]
        lengths = [x for x in scalar_values if x == float(obj.shape[1])]
        if len(dts) == 1 and len(t0s) == 1 and len(lengths) == 1:
            series.append({
                "dataset_path": obj.name,
                "rows": int(obj.shape[1]),
                "width": int(obj.shape[0]),
                "t0": float(t0s[0]),
                "dt": float(dts[0]),
            })
            start = i + 1

    if len(series) != len(ordered):
        raise ValueError(
            f"{raw.filename}: indexed {len(series)} logger data arrays for "
            f"{len(ordered)} SimulationOutput variables"
        )
    return {name: meta for (_, name), meta in zip(ordered, series)}


def _time_bits(meta: dict[str, Any], first: int, last: int) -> np.ndarray:
    # This is the stored MATLAB timeseries descriptor convention used by RAW.parse.
    # It is for same-index serialization comparison only, never row matching/tick inference.
    row = np.arange(first, last, dtype=np.float64)
    time_s = meta["t0"] + meta["dt"] * row
    return np.asarray(time_s, dtype=np.float64).reshape(-1).view(np.uint64)


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def mat_value(file, node, active=frozenset()):
    """Preserve inherited Inf metadata; validate finite values at physical boundaries.

    Unlike the static GroupDac reader, p_source/p_f0 may contain declared infinite
    leak/clip metadata. No Inf/NaN is admitted into a physical voltage or stamp.
    """
    require(node.name not in active, 'Cyclic MATLAB parameter reference: ' + node.name)
    active = active | {node.name}
    if isinstance(node, h5py.Group):
        if 'MATLAB_sparse' in node.attrs:
            rows = int(node.attrs['MATLAB_sparse'])
            return sparse.csc_matrix((node['data'][()].reshape(-1), node['ir'][()].reshape(-1),
                                      node['jc'][()].reshape(-1)), shape=(rows, len(node['jc'])-1)).toarray()
        return {k: mat_value(file, node[k], active) for k in node if not k.startswith('#')}
    cls = node.attrs.get('MATLAB_class', b'')
    cls = cls.decode() if isinstance(cls, bytes) else str(cls)
    if node.attrs.get('MATLAB_empty', 0):
        return np.empty((0,))
    raw = np.asarray(node[()])
    if h5py.check_dtype(ref=node.dtype) is not None:
        values = [None if not r else mat_value(file, file[r], active) for r in raw.reshape(-1)]
        return values[0] if len(values) == 1 else values
    if cls == 'char':
        return ''.join(chr(int(x)) for x in raw.reshape(-1) if int(x))
    a = raw.transpose(tuple(reversed(range(raw.ndim)))) if raw.ndim > 1 else raw
    return a.reshape(-1)[0].item() if a.size == 1 else a


def variable(raw, name):
    require(name in raw, 'Missing actual saved ' + name)
    return mat_value(raw, raw[name])

