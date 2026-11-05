#!/usr/bin/env python3
"""SAR20-5 本地只读调试探针（不加载模型、不调用 MATLAB、不仿真 ADC）。

数据源：某个已保存的真实 run 目录（parameters.mat / selected.mat /
summary.json / parameters.json）。所有数字都来自该 run 的实际落盘文件；
本工具不插值、不重算模拟状态、不产生新 P、不修改任何工程文件。

它做两件 MATLAB 之外也能做的事：
  1. 把「生效参数」和「256 条码」摆到眼前，不再靠 CHECKPOINT.md 的文字回忆。
  2. 忠实复现 current/src/digital/behavior_decode.m 的名义数字解码链，
     用公开 RAW 独立复算 code20，与 MATLAB 实测码逐条比对。
     一致 -> 数字重构没问题，异常在模拟/日志侧；不一致 -> 解码合同或权重变了。

    python3 sar20_probe.py info    [run_dir]
    python3 sar20_probe.py decode  [run_dir] --id 5
    python3 sar20_probe.py decode  [run_dir] --all
    python3 sar20_probe.py diff    <run_a> <run_b>
    python3 sar20_probe.py html    [run_dir] [--out report.html]

省略 run_dir 时使用当前已发布的 N256 normal run。

证据边界：本工具只读「已保存的公开结果」，属于静态/离线核算，不是仿真、
不是综合、不是 PEX 或 signoff。事件级波形与 5 路日志对齐仍须走 MATLAB
SAR20('sample', id, runPath)；工程自带 analysis/mat_reader.py 的
read_logger_plan 对当前 32-logger 的 simout.mat 已失效（实测报
"indexed 0 logger data arrays for 32 SimulationOutput variables"），
本工具不猜测其 MCOS 布局，也不伪造事件时间线。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import h5py
import numpy as np

ANALYSIS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYSIS))
from mat_reader import variable, mat_value  # noqa: E402  (工程内已验证的 v7.3 读取器)

PROJECT = ANALYSIS.parent
DEFAULT_RUN = (
    PROJECT / "analysis/behavior/public_normal_20261105/release_actual"
    / "behavior_12d08121-d679-40cd-9ee2-bc334ff42955"
)


# --------------------------------------------------------------------------
# 读取
# --------------------------------------------------------------------------
def load_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir).resolve()
    needed = ["parameters.mat", "selected.mat", "summary.json"]
    missing = [n for n in needed if not (run_dir / n).is_file()]
    if missing:
        raise SystemExit(f"不是完整的已保存 run 目录，缺少 {missing}: {run_dir}")
    # 只展开调试真正需要的 P 子树。整份 P 里的 calendar/adc_groups/schedule
    # 含上万元素的 cell，用 mat_value 全量递归实测需 30 s；按需读取为 0.002 s。
    # 全量参数比对改用 parameters.json（键与 P 逐一对齐，见 summary.json 的
    # config_identity 说明），避免为了 diff 去展开大结构。
    light_keys = (
        "N", "Ts_s", "epoch", "first_id", "seed", "fs_hz", "fsr_diff_v",
        "n_cycles", "stop_time_s", "schema", "input", "ni", "digital", "debug",
    )
    with h5py.File(run_dir / "parameters.mat", "r") as f:
        P = {k: mat_value(f, f["P"][k]) for k in light_keys if k in f["P"]}
    with h5py.File(run_dir / "selected.mat", "r") as f:
        selected = variable(f, "selected")
        metadata = variable(f, "metadata")
    summary = json.loads((run_dir / "summary.json").read_text())
    pj = run_dir / "parameters.json"
    params_json = json.loads(pj.read_text()) if pj.is_file() else None
    receipt = None
    for cand in (run_dir.parent / "release_receipt.json",
                 run_dir / "release_receipt.json"):
        if cand.is_file():
            receipt = json.loads(cand.read_text())
            break
    raw = np.asarray(selected["raw"], dtype=np.float64)
    code = np.asarray(selected["code20"], dtype=np.float64).reshape(-1)
    time_s = np.asarray(selected["time_s"], dtype=np.float64).reshape(-1)
    fields = [str(x) for x in np.asarray(selected["raw_fields"]).reshape(-1)]
    if raw.ndim != 2 or raw.shape[1] != len(fields):
        raise SystemExit(f"selected.raw 形状异常: {raw.shape}, fields={fields}")
    return {
        "dir": run_dir, "P": P, "params_json": params_json,
        "selected": selected, "metadata": metadata,
        "summary": summary, "receipt": receipt,
        "raw": raw, "code": code, "time_s": time_s, "fields": fields,
    }


def scalar(v, default=None):
    if v is None:
        return default
    a = np.asarray(v).reshape(-1)
    if not a.size:
        return default
    first = a[0]
    return first.item() if hasattr(first, "item") and not isinstance(first, str) else first


def text(v) -> str:
    if isinstance(v, str):
        return v
    a = np.asarray(v).reshape(-1)
    return "".join(str(x) for x in a) if a.size else ""


def plain(v):
    """把 mat_reader 的返回值转成纯 Python，便于 JSON/diff。"""
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.generic,)):
        return v.item()
    return v


# --------------------------------------------------------------------------
# 名义解码：逐行对应 current/src/digital/behavior_decode.m (v1, 2026-10-27)
# --------------------------------------------------------------------------
def matlab_round(x: float) -> int:
    """MATLAB round = nearest, ties away from zero (Python round 是 banker's)。"""
    return int(math.floor(x + 0.5)) if x >= 0 else int(math.ceil(x - 0.5))


def public_pol(sample_id: int, mode: str) -> int:
    if mode in ("chop", "hold_chop"):
        return (1, -1, -1, 1)[sample_id % 4]
    return 1


def public_dither(sample_id: int, dig: dict) -> float:
    if not scalar(dig["dither_enabled"], 0):
        return 0.0
    modulus, a = 2147483647, 16807
    word = int(scalar(dig["dither_seed"])) % (modulus - 1) + 1
    exp = sample_id + 1
    while exp > 0:
        if exp & 1:
            word = word * a % modulus
        a = a * a % modulus
        exp >>= 1
    return (math.floor(4.0 * word / modulus) - 1.5) * scalar(dig["dither_amplitude_v"])


def decode_row(raw_row: np.ndarray, dig: dict) -> dict:
    d1, d2, dt, sid, epoch, valid = (int(round(x)) for x in raw_row[:6])
    vref = scalar(dig["vref_v"])
    fsr = scalar(dig["fsr_diff_v"])
    gain = scalar(dig["ra_gain"])
    c, f = divmod(d1, 32)
    d1_dac = (32 * c + 2 * f - 1039) * vref / 1024.0
    # 源码：字段缺失时用 legacy -17*vref/1024；字段存在则即使为 0 也必须采用。
    d1_bias = scalar(dig.get("d1_bias_v"), None)
    if d1_bias is None:
        d1_bias = -17 * vref / 1024.0
    d1_v = d1_dac + d1_bias

    d2_bits = [(d2 >> b) & 1 for b in range(11, -1, -1)]
    w = np.asarray(dig["d2_weights_ra_v"], dtype=np.float64).reshape(-1)
    d2_ra = scalar(dig["d2_offset_ra_v"]) + float(np.dot(w, np.asarray(d2_bits)))

    dt_bits = [(dt >> b) & 1 for b in range(7, -1, -1)]
    signs = np.asarray([2 * b - 1 for b in dt_bits], dtype=np.float64)
    dt_stat = float(np.dot(np.arange(8, 0, -1, dtype=np.float64), signs))
    dt_weighted = dt_stat / 8.0  # 源码注释：除以 8 是刻意，不是 36 归一化
    dt_ra = scalar(dig["tracking_step_ra_v"]) * dt_weighted

    pol = public_pol(sid, text(dig.get("az_mode", "off")))
    d2_v = pol * d2_ra / gain
    dt_v = pol * dt_ra / gain
    dith = public_dither(sid, dig)
    voltage = (d1_v + d2_v) + dt_v + dith
    unsat = voltage * (2 ** 20 / fsr) + 2 ** 19
    rounded = matlab_round(unsat)
    code = max(0, min(2 ** 20 - 1, rounded))
    return {
        "id": sid, "epoch": epoch, "valid": int(valid),
        "raw_d1": d1, "raw_d2": d2, "raw_dt": dt,
        "d1_c": c, "d1_f": f, "d1_dac_v": d1_dac, "d1_bias_v": d1_bias,
        "d1_v": d1_v, "d2_bits": d2_bits, "d2_ra_v": d2_ra, "d2_v": d2_v,
        "dt_bits": dt_bits, "dt_stat": dt_stat, "dt_weighted": dt_weighted,
        "dt_ra_v": dt_ra, "dt_v": dt_v, "pol": pol, "dither_v": dith,
        "voltage_v": voltage, "unsat_code": unsat, "rounded_code": rounded,
        "clip": rounded != code, "code20": code,
    }


DECODE_REQUIRED = (
    "vref_v", "fsr_diff_v", "ra_gain", "d2_weights_ra_v", "d2_offset_ra_v",
    "tracking_step_ra_v", "dither_enabled", "dither_seed", "dither_amplitude_v",
)


def decode_all(run: dict) -> list[dict]:
    dig = run["P"].get("digital") or {}
    missing = [k for k in DECODE_REQUIRED if dig.get(k) is None]
    if missing:
        raise ValueError(
            f"该 run 的 P.digital 不满足当前 nominal 解码合同，缺 {missing}；"
            "旧配置请用 MATLAB 侧对应解码，本探针不猜测权重。"
        )
    return [decode_row(row, dig) for row in run["raw"]]


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------
def cmd_info(run: dict) -> None:
    s, P, m = run["summary"], run["P"], run["metadata"]
    print(f"run 目录      : {run['dir']}")
    print(f"status        : {s.get('status')} / {s.get('simulation_completed')}")
    print(f"utc           : {s.get('utc')}")
    print(f"SLX SHA       : {s.get('model_sha256')}")
    print(f"config SHA    : {s.get('config_sha256')}")
    print(f"记录数        : {len(run['code'])}  (字段 {run['fields']})")
    print(f"Fs / FSR      : {scalar(P['fs_hz'])/1e6:g} MHz / {scalar(P['fsr_diff_v']):g} V")
    inp = P["input"]
    print(f"输入          : Fin={scalar(inp['frequency_hz'])/1e3:g} kHz, "
          f"A={scalar(inp['amplitude_v']):.9f} V, phase={scalar(inp['phase_rad'])} rad, "
          f"offset={scalar(inp['offset_v'])} V")
    print(f"N / first_id / epoch / seed : {scalar(P['N']):g} / "
          f"{scalar(P['first_id']):g} / {scalar(P['epoch']):g} / {scalar(P['seed']):g}")
    print(f"decode        : mode={text(P['digital']['calibration_mode'])}, "
          f"az={text(P['digital']['az_mode'])}, tracking={text(P['digital']['tracking_mode'])}")
    print("非理想开关 (P.ni):")
    for k, v in P["ni"].items():
        if isinstance(v, dict):
            print(f"  {k:26s} {plain(v)}")
        else:
            print(f"  {k:26s} {'ON ' if scalar(v, 0) else 'OFF'}  ({scalar(v, 0):g})")
    if run["receipt"] and run["receipt"].get("metrics"):
        met = run["receipt"]["metrics"]
        print("实测指标 (来自 release_receipt.json):")
        print("  " + ", ".join(f"{k}={v:.6f}" for k, v in met.items()))
    print()
    print("事件级日志: 工程 analysis/mat_reader.py 的 read_logger_plan 对当前 "
          "32-logger simout.mat 已失效；请用 MATLAB SAR20('sample',id,runPath)。")
    print("本页所有数值均为已保存公开结果的离线核算，不是仿真 / 综合 / signoff。")


def cmd_decode(run: dict, sample_id: int | None, all_rows: bool) -> None:
    rows = decode_all(run)
    by_id = {r["id"]: (i, r) for i, r in enumerate(rows)}
    if all_rows or sample_id is None:
        bad = [(i, r) for i, r in enumerate(rows) if r["code20"] != int(run["code"][i])]
        print(f"独立复算 code20 vs MATLAB 实测: {len(rows)-len(bad)}/{len(rows)} 逐条一致")
        if bad:
            for i, r in bad[:10]:
                print(f"  ID{r['id']:>4} 复算={r['code20']} 实测={int(run['code'][i])} "
                      f"Δ={r['code20']-int(run['code'][i])}")
            print("  -> 数字解码链与保存结果不符：先查 P.digital 权重/偏置/az_mode，")
            print("     再查 current/src/digital/behavior_decode.m 是否被改动。")
        else:
            print("  -> 名义数字重构自洽；若现象异常，问题不在解码，去查模拟侧日志/状态。")
        if sample_id is None:
            return
    if sample_id not in by_id:
        raise SystemExit(f"该 run 没有 sample ID={sample_id}；可用 ID "
                         f"{min(by_id)}..{max(by_id)}")
    i, r = by_id[sample_id]
    print(f"\n=== sample ID {sample_id} (第 {i+1} 条记录, epoch {r['epoch']}, valid={r['valid']}) ===")
    print(f"保存时间      : {run['time_s'][i]:.12g} s")
    print(f"RAW           : D1={r['raw_d1']}  D2={r['raw_d2']}  DT={r['raw_dt']}")
    print(f"D1 链         : c={r['d1_c']}, f={r['d1_f']} -> DAC {r['d1_dac_v']:.12f} V"
          f"  + bias {r['d1_bias_v']:.12f} V = {r['d1_v']:.12f} V")
    print(f"D2 链         : bits={''.join(map(str,r['d2_bits']))} -> "
          f"RA {r['d2_ra_v']:.12f} V / gain = {r['d2_v']*1e3:.9f} mV")
    print(f"DT 链         : bits={''.join(map(str,r['dt_bits']))} -> "
          f"stat={r['dt_stat']:g} /8 = {r['dt_weighted']:g} -> "
          f"RA {r['dt_ra_v']:.12f} V / gain = {r['dt_v']*1e6:.9f} µV")
    print(f"POL={r['pol']:+d}  dither={r['dither_v']:.12g} V")
    print(f"合成电压      : {r['voltage_v']:.12f} V")
    print(f"unsat/rounded : {r['unsat_code']:.6f} / {r['rounded_code']}  clip={r['clip']}")
    print(f"复算 code20   : {r['code20']}     MATLAB 实测: {int(run['code'][i])}    "
          f"{'一致' if r['code20']==int(run['code'][i]) else '不一致'}")
    print("注：以上是名义输入域数字分量，不是模拟残差探针。")


def _flatten(v, prefix="") -> dict:
    out = {}
    if isinstance(v, dict):
        for k, x in v.items():
            out.update(_flatten(x, f"{prefix}.{k}" if prefix else k))
    elif isinstance(v, (list, tuple, np.ndarray)):
        a = np.asarray(v)
        if a.size <= 64:
            out[prefix] = a.tolist()
        else:
            # 大数组必须比内容：只比 shape 会漏掉 calendar/schedule 这类改动。
            blob = (a.tobytes() if a.dtype != object else repr(a.tolist()).encode())
            digest = hashlib.sha256(blob).hexdigest()[:12]
            out[prefix] = f"<array shape={a.shape} sha={digest}>"
    else:
        out[prefix] = v
    return out


def cmd_diff(run_a: dict, run_b: dict) -> None:
    # 优先用 parameters.json（P 的全量可读投影，键逐一对齐）做逐字段 diff；
    # 缺失时才退回按需读取的轻量 P，并明确标注范围，不假装是全量比对。
    full = bool(run_a["params_json"] and run_b["params_json"])
    fa = _flatten(run_a["params_json"] if full else run_a["P"])
    fb = _flatten(run_b["params_json"] if full else run_b["P"])
    print("参数来源      : " + ("parameters.json（P 的全量可读投影）" if full
                             else "P 按需子树（非全量；至少一个 run 缺 parameters.json）"))
    keys = sorted(set(fa) | set(fb))
    changed = []
    for k in keys:
        va, vb = fa.get(k, "<缺失>"), fb.get(k, "<缺失>")
        if va != vb:
            changed.append((k, va, vb))
    print(f"参数差异 (P 逐字段): {len(changed)} 项")
    for k, va, vb in changed[:80]:
        print(f"  {k}\n      A: {str(va)[:150]}\n      B: {str(vb)[:150]}")
    if len(changed) > 80:
        print(f"  ... 另有 {len(changed)-80} 项")
    print(f"\nSLX SHA: A={run_a['summary'].get('model_sha256','?')[:16]}  "
          f"B={run_b['summary'].get('model_sha256','?')[:16]}")
    try:
        ma = {r["id"]: r for r in decode_all(run_a)}
        mb = {r["id"]: r for r in decode_all(run_b)}
    except ValueError as exc:
        print(f"\n跳过码比较：{exc}")
        print("参数差异仍有效；若要比较码，请选两个都满足当前解码合同的 run。")
        return
    ids = sorted(set(ma) & set(mb))
    n_code = sum(1 for i in ids if ma[i]["code20"] != mb[i]["code20"])
    n_raw = sum(1 for i in ids if (ma[i]["raw_d1"], ma[i]["raw_d2"], ma[i]["raw_dt"])
                != (mb[i]["raw_d1"], mb[i]["raw_d2"], mb[i]["raw_dt"]))
    print(f"共同 ID {len(ids)} 个: RAW 不同 {n_raw} 个, 复算 code20 不同 {n_code} 个")
    for i in ids[:8]:
        print(f"  ID{i:>4}: A={ma[i]['raw_d1']}/{ma[i]['raw_d2']}/{ma[i]['raw_dt']} "
              f"code={ma[i]['code20']:>7}   B={mb[i]['raw_d1']}/{mb[i]['raw_d2']}/{mb[i]['raw_dt']} "
              f"code={mb[i]['code20']:>7}   Δcode={mb[i]['code20']-ma[i]['code20']:+d}")
    print("\n提示：若 P 无差异但码不同 -> 查随机流/seed 或源码；若 P 有差异 -> 上表即定位到字段。")


def cmd_html(run: dict, out: Path) -> None:
    rows = decode_all(run)
    mism = sum(1 for i, r in enumerate(rows) if r["code20"] != int(run["code"][i]))
    ni = {k: (plain(v) if isinstance(v, dict) else scalar(v))
          for k, v in run["P"]["ni"].items()}
    data = {
        "run": str(run["dir"]),
        "summary": {k: run["summary"].get(k) for k in
                    ("utc", "model_sha256", "config_sha256", "status")},
        "config": {
            "N": scalar(run["P"]["N"]), "fs_hz": scalar(run["P"]["fs_hz"]),
            "fsr_diff_v": scalar(run["P"]["fsr_diff_v"]),
            "seed": scalar(run["P"]["seed"]),
            "first_id": scalar(run["P"]["first_id"]),
            "input": plain(run["P"]["input"]),
            "digital": plain(run["P"]["digital"]),
            "ni": ni,
        },
        "metrics": (run["receipt"] or {}).get("metrics"),
        "mismatch": mism,
        "records": [
            {**r, "measured_code": int(run["code"][i]),
             "time_s": float(run["time_s"][i]),
             "match": r["code20"] == int(run["code"][i])}
            for i, r in enumerate(rows)
        ],
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    tpl = HTML_TEMPLATE.replace("__PAYLOAD__", payload.replace("</", "<\\/"))
    out = Path(out).resolve()
    out.write_text(tpl, encoding="utf-8")
    print(f"已生成 {out}  ({out.stat().st_size:,} bytes)")
    print(f"内含 {len(rows)} 条真实记录；独立复算与实测不一致 {mism} 条。")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAR20-5 本地调试面板 · 只读</title>
<style>
:root{--bg:#f7f8fa;--card:#fff;--line:#e3e6eb;--ink:#1c2128;--dim:#6b7280;
--accent:#2563eb;--ok:#0f8a4a;--bad:#c62828;--soft:#eef2f7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:24px 0 10px}
.sub{color:var(--dim);font-size:13px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:14px}
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600}
.b-ok{background:#e6f6ec;color:var(--ok)}.b-bad{background:#fdeaea;color:var(--bad)}
.b-info{background:#e8effd;color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px 20px}
.kv{display:flex;justify-content:space-between;gap:10px;border-bottom:1px dashed var(--line);padding:4px 0}
.kv span:first-child{color:var(--dim)}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
table{border-collapse:collapse;width:100%;font-size:12.5px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{background:var(--soft);color:var(--dim);font-weight:600;position:sticky;top:0}
td:first-child,th:first-child{text-align:left}tbody tr{cursor:pointer}tbody tr:hover{background:#f0f5ff}
.sel{background:#e3edff!important}
.scroll{max-height:380px;overflow:auto;border:1px solid var(--line);border-radius:8px}
input,select{padding:7px 10px;border:1px solid var(--line);border-radius:7px;background:#fff;color:var(--ink);font-size:13px}
.chain{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
.step{background:var(--soft);border-radius:8px;padding:10px 12px}
.step b{display:block;color:var(--accent);font-size:12px;margin-bottom:3px}
.note{color:var(--dim);font-size:12.5px;border-left:3px solid var(--line);padding-left:12px;margin:10px 0}
.flex{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.ok{color:var(--ok)}.bad{color:var(--bad)}
</style></head><body><div class="wrap">
<h1>SAR20-5 本地调试面板 <span class="badge b-info">只读 · 离线</span></h1>
<div class="sub" id="sub"></div>
<div class="card"><h2 style="margin-top:0">运行身份与生效参数</h2><div class="grid" id="cfg"></div>
<div class="note" id="warn"></div></div>
<div class="card"><h2 style="margin-top:0">解码自检</h2><div id="check"></div>
<div class="note">独立复算是 <span class="mono">current/src/digital/behavior_decode.m</span> 的 Python 忠实移植，只覆盖<strong>名义数字重构</strong>。一致只说明解码链自洽，不证明模拟侧正确，也不构成仿真或 signoff。</div></div>
<div class="card"><h2 style="margin-top:0">记录表（点击一行查看该 sample 的解码链）</h2>
<div class="flex"><label>ID <input id="q" type="number" style="width:100px"></label>
<label>只看不一致 <input id="onlyBad" type="checkbox"></label><span id="count" class="mono"></span></div>
<div class="scroll"><table><thead><tr><th>ID</th><th>epoch</th><th>valid</th><th>D1</th><th>D2</th><th>DT</th>
<th>复算 code20</th><th>实测 code20</th><th>Δ</th><th>时间 (µs)</th></tr></thead><tbody id="tb"></tbody></table></div></div>
<div class="card"><h2 style="margin-top:0" id="chainTitle">解码链</h2><div class="chain" id="chain"></div>
<div class="note">D1/D2/DT 是名义输入域数字分量，<strong>不是模拟残差探针</strong>。事件级波形与 5 路日志对齐请用 MATLAB
<span class="mono">SAR20('sample', id, runPath)</span>；工程 <span class="mono">analysis/mat_reader.py</span> 的
<span class="mono">read_logger_plan</span> 对当前 32-logger 的 simout.mat 已失效，本页不猜测 MCOS 布局、不伪造事件时间线。</div></div>
</div><script>
const D=__PAYLOAD__;
const f=(x,n=6)=>typeof x==='number'?(Number.isInteger(x)?x.toString():x.toFixed(n)):String(x??'');
document.getElementById('sub').textContent='数据源：'+D.run+' · 全部数值来自该 run 已保存的实际文件';
const c=D.config, rows=D.records;
let h='';
const kv=(k,v)=>'<div class="kv"><span>'+k+'</span><span class="mono">'+v+'</span></div>';
h+=kv('status',D.summary.status||'-')+kv('UTC',D.summary.utc||'-');
h+=kv('SLX SHA',String(D.summary.model_sha256||'-').slice(0,20)+'…');
h+=kv('config SHA',String(D.summary.config_sha256||'-').slice(0,20)+'…');
h+=kv('N / Fs',f(c.N,0)+' / '+(c.fs_hz/1e6)+' MHz');
h+=kv('FSR (diff)',f(c.fsr_diff_v,3)+' V')+kv('Fin',(c.input.frequency_hz/1e3)+' kHz');
h+=kv('幅度',f(c.input.amplitude_v,9)+' V')+kv('phase',f(c.input.phase_rad,3)+' rad');
h+=kv('seed / first_id',f(c.seed,0)+' / '+f(c.first_id,0));
h+=kv('decode / AZ',c.digital.calibration_mode+' / '+c.digital.az_mode);
h+=kv('tracking',c.digital.tracking_mode)+kv('RA gain',f(c.digital.ra_gain,0));
document.getElementById('cfg').innerHTML=h;
const on=[],off=[];for(const[k,v]of Object.entries(c.ni)){(typeof v==='number'&&v)?on.push(k):off.push(k)}
document.getElementById('warn').innerHTML='非理想开关：<b>ON</b> '+on.join(', ')+
  '<br><b>OFF</b> '+off.join(', ')+'<br>这些都是<strong>本 run 的 P 实际值</strong>，不是 README 描述、不是论文标称。';
const m=D.metrics;
document.getElementById('check').innerHTML=
 (D.mismatch===0?'<span class="badge b-ok">256/256 一致</span>':'<span class="badge b-bad">'+D.mismatch+' 条不一致</span>')+
 ' &nbsp; 独立复算 code20 与 MATLAB 实测逐条比对'+
 (m?'<div class="mono" style="margin-top:8px">实测指标：SNDR '+m.sndr_db.toFixed(6)+' dB · SNR '+m.snr_db.toFixed(6)+' dB · ENOB '+m.enob.toFixed(6)+' bit</div>':'');
const tb=document.getElementById('tb');let cur=-1;
function render(){
 const q=document.getElementById('q').value, bad=document.getElementById('onlyBad').checked;
 const list=rows.filter(r=>(!q||r.id==Number(q))&&(!bad||!r.match));
 tb.innerHTML=list.map(r=>'<tr data-i="'+rows.indexOf(r)+'" class="'+(rows.indexOf(r)===cur?'sel':'')+'">'+
  '<td>'+r.id+'</td><td>'+r.epoch+'</td><td>'+r.valid+'</td><td>'+r.raw_d1+'</td><td>'+r.raw_d2+'</td><td>'+r.raw_dt+'</td>'+
  '<td>'+r.code20+'</td><td>'+r.measured_code+'</td><td class="'+(r.match?'ok':'bad')+'">'+(r.code20-r.measured_code)+'</td>'+
  '<td>'+(r.time_s*1e6).toFixed(4)+'</td></tr>').join('');
 document.getElementById('count').textContent=list.length+' / '+rows.length+' 条';
 tb.querySelectorAll('tr').forEach(tr=>tr.onclick=()=>{cur=Number(tr.dataset.i);render();chain(cur)});
}
function chain(i){const r=rows[i];if(!r)return;
 document.getElementById('chainTitle').textContent='解码链 · sample ID '+r.id;
 const s=(t,v)=>'<div class="step"><b>'+t+'</b><span class="mono">'+v+'</span></div>';
 document.getElementById('chain').innerHTML=
 s('RAW','D1='+r.raw_d1+' · D2='+r.raw_d2+' · DT='+r.raw_dt)+
 s('D1 拆分','c='+r.d1_c+' · f='+r.d1_f+' · DAC '+f(r.d1_dac_v,12)+' V')+
 s('D1 输入域',f(r.d1_v,12)+' V (bias '+f(r.d1_bias_v,12)+')')+
 s('D2 bits',r.d2_bits.join('')+' → RA '+f(r.d2_ra_v,12)+' V')+
 s('D2 输入域',(r.d2_v*1e3).toFixed(6)+' mV')+
 s('DT bits',r.dt_bits.join('')+' → stat '+r.dt_stat+' /8 = '+r.dt_weighted)+
 s('DT 输入域',(r.dt_v*1e6).toFixed(6)+' µV')+
 s('POL / dither',r.pol+' / '+f(r.dither_v,9)+' V')+
 s('合成电压',f(r.voltage_v,12)+' V')+
 s('量化','unsat '+f(r.unsat_code,4)+' → round '+r.rounded_code)+
 s('code20',r.code20+' &nbsp; 实测 '+r.measured_code+' &nbsp; '+(r.match?'<span class="ok">一致</span>':'<span class="bad">不一致</span>'))+
 s('保存时刻',(r.time_s*1e9).toFixed(2)+' ns');
}
document.getElementById('q').oninput=render;document.getElementById('onlyBad').onchange=render;
render();chain(1);
</script></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info", help="运行身份与生效参数")
    p.add_argument("run", nargs="?", default=str(DEFAULT_RUN))
    p = sub.add_parser("decode", help="独立复算名义解码并与实测码比对")
    p.add_argument("run", nargs="?", default=str(DEFAULT_RUN))
    p.add_argument("--id", type=int)
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("diff", help="两个 run 的参数与码差异")
    p.add_argument("run_a"); p.add_argument("run_b")
    p = sub.add_parser("html", help="生成离线静态调试页")
    p.add_argument("run", nargs="?", default=str(DEFAULT_RUN))
    p.add_argument("--out", default=str(Path(__file__).with_name("sar20_debug_report.html")))
    a = ap.parse_args()
    if a.cmd == "diff":
        cmd_diff(load_run(a.run_a), load_run(a.run_b))
    else:
        run = load_run(a.run)
        try:
            if a.cmd == "info":
                cmd_info(run)
            elif a.cmd == "decode":
                cmd_decode(run, a.id, a.all)
            elif a.cmd == "html":
                cmd_html(run, a.out)
        except ValueError as exc:
            raise SystemExit(f"解码失败：{exc}")


if __name__ == "__main__":
    main()
