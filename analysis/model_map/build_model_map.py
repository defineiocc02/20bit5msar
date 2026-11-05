#!/usr/bin/env python3
"""Build an offline, interactive map of the real SarAdc.slx structure.

No MATLAB, no Simulink, no simulation. Reads the SLX as a ZIP of XML files and
extracts subsystems, blocks, signal lines, block annotations and original
positions, then scans current/src/**/*.m to bind S-Functions to source files
and to build an approximate static call graph.

Outputs (in this directory):
  model_map.json        machine-readable structure
  sar20_model_map.html  single-file offline visualizer (from template.html)

Usage:
  python3 build_model_map.py
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SLX = ROOT / "current" / "models" / "SarAdc.slx"
SRC = ROOT / "current" / "src"
CALENDAR = SRC / "control" / "behavior_calendar.m"
TEMPLATE = HERE / "template.html"
OUT_JSON = HERE / "model_map.json"
OUT_HTML = HERE / "sar20_model_map.html"


def ptext(node, name: str, default: str = "") -> str:
    el = node.find(f"P[@Name='{name}']")
    return el.text if el is not None and el.text is not None else default


def parse_position(raw: str):
    nums = re.findall(r"-?\d+(?:\.\d+)?", raw or "")
    return [float(x) for x in nums[:4]] if len(nums) >= 4 else None


def parse_slx() -> dict:
    with zipfile.ZipFile(SLX) as z:
        names = sorted(n for n in z.namelist()
                       if re.fullmatch(r"simulink/systems/system_[^/]+\.xml", n))
        systems: dict[str, dict] = {}
        for n in names:
            stem = Path(n).stem
            r = ET.fromstring(z.read(n))
            blocks = []
            for b in r.findall("Block"):
                pc = b.find("PortCounts")
                sub = b.find("System")
                attrs = ptext(b, "AttributesFormatString")
                blocks.append({
                    "sid": b.get("SID") or "",
                    "name": b.get("Name") or "",
                    "type": b.get("BlockType") or "",
                    "pos": parse_position(ptext(b, "Position")),
                    "func": ptext(b, "FunctionName"),
                    "value": ptext(b, "Value"),
                    "attrs": attrs[:4000],
                    "sub": sub.get("Ref") if sub is not None else "",
                    "nin": int(pc.get("in", 0)) if pc is not None else 0,
                    "nout": int(pc.get("out", 0)) if pc is not None else 0,
                })
            lines = []
            for L in r.findall("Line"):
                src, dst = ptext(L, "Src"), ptext(L, "Dst")
                ms = re.match(r"(\d+)#(out|in):(\d+)", src)
                md = re.match(r"(\d+)#(out|in):(\d+)", dst)
                if not (ms and md):
                    continue
                lines.append({
                    "src": ms.group(1), "src_port": int(ms.group(3)),
                    "dst": md.group(1), "dst_port": int(md.group(3)),
                    "points": ptext(L, "Points"),
                })
            systems[stem] = {"file": stem, "name": stem, "path": stem,
                             "blocks": blocks, "lines": lines,
                             "parent": "", "children": []}

    # resolve subsystem references into a tree
    for sys_key, sys_data in systems.items():
        for b in sys_data["blocks"]:
            if b["sub"] and b["sub"] in systems:
                child = systems[b["sub"]]
                child["parent"] = sys_key
                child["name"] = b["name"]
                sys_data["children"].append(b["sub"])

    def build_path(key: str, seen=None) -> str:
        seen = seen or set()
        if key in seen:
            return key
        seen.add(key)
        s = systems[key]
        if not s["parent"]:
            return "SarAdc"
        return build_path(s["parent"], seen) + " / " + s["name"]

    for key in systems:
        systems[key]["path"] = build_path(key)
    systems["system_root"]["name"] = "SarAdc（顶层）"
    systems["system_root"]["path"] = "SarAdc"

    return systems


def scan_sources(systems: dict) -> dict:
    files = []
    for f in sorted(SRC.rglob("*.m")):
        rel = f.relative_to(SRC).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        defs = re.findall(
            r"^\s*function\s+(?:\[[^\]]*\]|[\w.]+)\s*=\s*(\w+)\s*\(", text, re.M)
        if not defs:
            m = re.match(r"^\s*function\s+(\w+)\s*\(", text, re.M)
            defs = [m.group(1)] if m else []
        files.append({
            "path": rel,
            "dir": rel.split("/")[0],
            "name": f.name,
            "lines": text.count("\n") + 1,
            "defs": defs,
            "calls": [],
            "called_by": [],
            "sfun_blocks": [],
        })

    funcs = {fn: i for i, f in enumerate(files) for fn in f["defs"]}
    by_stem = {Path(f["path"]).stem: i for i, f in enumerate(files)}
    for i, f in enumerate(files):
        text = (SRC / f["path"]).read_text(encoding="utf-8", errors="replace")
        body = re.sub(r"^\s*function[^\n]*\n", "", text, flags=re.M)
        body = re.sub(r"%[^\n]*", "", body)
        called = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", body)) & set(funcs)
        f["calls"] = sorted(called - set(f["defs"]))

    for i, f in enumerate(files):
        for fn in f["calls"]:
            j = funcs.get(fn)
            if j is not None and i != j:
                files[j]["called_by"].append(f["path"])

    sfun_to_file = {}
    for sys_data in systems.values():
        for b in sys_data["blocks"]:
            if not b["func"]:
                continue
            idx = by_stem.get(b["func"])
            entry = {"system": sys_data["file"], "path": sys_data["path"],
                     "block": b["name"], "function": b["func"]}
            if idx is not None:
                files[idx]["sfun_blocks"].append(entry)
                sfun_to_file[b["func"]] = files[idx]["path"]
            else:
                sfun_to_file[b["func"]] = ""
    for f in files:
        f["called_by"] = sorted(set(f["called_by"]))
    return {"files": files, "sfun_to_file": sfun_to_file}


def build_events() -> list:
    """Expand behavior_calendar.m add() rules by PARSING THE SOURCE.

    A deliberately tiny MATLAB-subset evaluator handles exactly the constructs
    this file uses: plain `add(...);` statements, `for k=a:b ... end` loops, and
    the one-line `if cond,add(...);end`. MATLAB is never executed. If the source
    calendar changes shape, the guard assertions below fail loudly instead of
    quietly shipping a stale timeline.
    """
    src = CALENDAR.read_text(encoding="utf-8", errors="replace")
    lines = []
    for raw in src.splitlines():
        line = raw.split("%", 1)[0].strip()   # strip MATLAB comments
        if line:
            lines.append(line)
    start = next(i for i, l in enumerate(lines) if l.startswith("events=repmat"))
    stop = next(i for i, l in enumerate(lines) if "sortrows" in l)
    body = lines[start + 1:stop]

    ev = []

    def add(ns, typ, index=-1, bit=-1, priority=0):
        ev.append({"ns": float(ns), "type": typ, "index": int(index),
                   "bit": int(bit), "priority": int(priority),
                   "tick": round(float(ns) / 0.25)})

    safe = {"__builtins__": {}, "add": add}

    def run(lo: int, hi: int, env: dict) -> None:
        i = lo
        while i < hi:
            line = body[i]
            m = re.match(r"for\s+(\w+)\s*=\s*(-?\d+)\s*:\s*(-?\d+)\s*$", line)
            if m:
                var, a, b = m.group(1), int(m.group(2)), int(m.group(3))
                j, depth = i + 1, 1
                while j < hi and depth:
                    if re.match(r"for\s+\w+\s*=", body[j]):
                        depth += 1
                    elif body[j] == "end":
                        depth -= 1
                    j += 1
                for v in range(a, b + 1):
                    run(i + 1, j - 1, {**env, var: v})
                i = j
                continue
            im = re.match(r"if\s+(.+?)\s*,\s*(add\(.*\))\s*;\s*end\s*$", line)
            if im:
                if eval(im.group(1), safe, dict(env)):
                    eval(im.group(2), safe, dict(env))
                i += 1
                continue
            if line.startswith("add("):
                eval(line.rstrip(";"), safe, dict(env))
            i += 1

    run(0, len(body), {})
    ev.sort(key=lambda e: (e["tick"], e["priority"]))
    assert len(ev) == 73, f"calendar drift: expected 73 events, got {len(ev)}"
    assert min(e["ns"] for e in ev) == 0.0 and max(e["ns"] for e in ev) == 90.0
    return ev


# Execution order of the six Adc compute stages. Source: docs/READ_GRAPH.md
# "依赖顺序与路径" table (lines 32-39). NOT the SLX child order, which is
# alphabetical storage order. Diagnostics is a 7th, observation-only child.
COMPUTE_STAGES = [
    ("SampleRaAdvance", "采样 + 旧 RA/AZ 推进（旧命令先于本次事件）"),
    ("DacCtFeedback", "到期反馈提交 → DAC1 实际残差 → CT 开关"),
    ("Sar1TrialRaCt", "六位预转换 / SAR1 trial → RA + AZ"),
    ("ResidueCtCompare", "Compare1 看 DAC1 残差、Compare2 看 CT 实际 VY"),
    ("SarDecisionTracking", "12 次 D2 / 8 次 TA 比较 / 7 次物理反馈"),
    ("ChargeReturnRaReset", "按实际 Vtop 返还电荷 + 信号 reset"),
]


def derive_stats(systems: dict, sources: dict, events: list) -> dict:
    """Counts used by the UI, all derived from parsed data (no hand-written numbers)."""
    ud = [(k, b) for k, s in systems.items()
          for b in s["blocks"] if b["type"] == "UnitDelay"]
    adc_key = next(k for k, s in systems.items() if s["name"] == "Adc")
    adc = systems[adc_key]
    sfun = [(k, b) for k, s in systems.items()
            for b in s["blocks"] if b["type"] == "M-S-Function"]
    types = [e["type"] for e in events]
    names = [systems[c]["name"] for c in adc["children"]]
    return {
        "unique_event_times": len({e["ns"] for e in events}),
        "unit_delay_total": len(ud),
        "unit_delay_adc": sum(1 for k, _ in ud if k == adc_key),
        "unit_delay_analog": [{"sid": b["sid"], "name": b["name"]}
                              for k, b in ud if k == adc_key],
        "unit_delay_other": [{"sid": b["sid"], "name": b["name"],
                              "path": systems[k]["path"]}
                             for k, b in ud if k != adc_key],
        "sfun_blocks": len(sfun),
        "sfun_distinct": len({b["func"] for _, b in sfun}),
        "adc_children": len(adc["children"]),
        "adc_child_names": names,
        "adc_tree_is_alphabetical": names == sorted(names),
        "root_blocks": len(systems["system_root"]["blocks"]),
        "ta_compares": types.count("ta_compare"),
        "ta_feedbacks": types.count("ta_feedback"),
        "d2_steps": types.count("d2_decide"),
    }


def main() -> None:
    systems = parse_slx()
    sources = scan_sources(systems)
    events = build_events()
    sha = hashlib.sha256(SLX.read_bytes()).hexdigest()

    n_blocks = sum(len(s["blocks"]) for s in systems.values())
    n_lines = sum(len(s["lines"]) for s in systems.values())
    derived = derive_stats(systems, sources, events)
    data = {
        "meta": {
            "slx": "current/models/SarAdc.slx",
            "slx_sha256": sha,
            "slx_bytes": SLX.stat().st_size,
            "systems": len(systems),
            "blocks": n_blocks,
            "lines": n_lines,
            "sfunctions": len(sources["sfun_to_file"]),
            "source_files": len(sources["files"]),
            "source_lines": sum(f["lines"] for f in sources["files"]),
            "events": len(events),
            "event_source": "current/src/control/behavior_calendar.m",
            "method": "SLX read as ZIP/XML; calendar expanded by parsing the .m source; "
                      "no MATLAB, no model load, no simulation",
            "derived": derived,
            "compute_stages": [{"name": n, "desc": d} for n, d in COMPUTE_STAGES],
            "compute_stages_source": "docs/READ_GRAPH.md lines 32-39 (依赖顺序与路径); "
                                     "Adc 第 7 个子 Diagnostics 仅观察",
            "transport_note_source": "docs/READ_GRAPH.md line 54 (138 ns / 538 ns 为文档记载，"
                                     "不在 0-90 ns 日历事件中)",
        },
        "systems": systems,
        "sources": sources,
        "events": events,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    if "/*__MODEL_DATA__*/" not in html:
        raise SystemExit("template.html is missing the /*__MODEL_DATA__*/ placeholder")
    OUT_HTML.write_text(html.replace("/*__MODEL_DATA__*/", payload), encoding="utf-8")

    print(f"SLX SHA256   : {sha}")
    print(f"systems      : {len(systems)}   blocks: {n_blocks}   lines: {n_lines}")
    print(f"S-Functions  : {derived['sfun_blocks']} blocks / "
          f"{derived['sfun_distinct']} distinct entry points, "
          f"resolved: {sum(1 for v in sources['sfun_to_file'].values() if v)}")
    print(f"source files : {len(sources['files'])}   events: {len(events)} "
          f"({derived['unique_event_times']} unique times)")
    print(f"UnitDelay    : {derived['unit_delay_total']} total, "
          f"{derived['unit_delay_adc']} inside Adc (analog state owners)")
    print(f"Adc children : {derived['adc_children']} "
          f"(6 compute stages + Diagnostics); tree alphabetical: "
          f"{derived['adc_tree_is_alphabetical']}")
    print(f"wrote        : {OUT_JSON.name} ({OUT_JSON.stat().st_size:,} B)")
    print(f"wrote        : {OUT_HTML.name} ({OUT_HTML.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
