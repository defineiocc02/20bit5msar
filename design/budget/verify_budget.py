#!/usr/bin/env python3
"""Verify the SAR20-5 Rev0.3 design-constraint chain.

Read-only. Recomputes every derived number in error_budget_rev03.json from
docs/spec.yml, cross-checks the behavioral model parameters in
config/normal_parameters.m and the authoritative run's parameters.json,
and prints the remaining unverified design gates.

Exit 0 = all recomputable checks agree.
Exit 1 = a numeric or file-consistency mismatch (the budget has drifted).

Design gates marked NEEDS_CLOSED_LOOP / NOT_IMPLEMENTED are PRINTED, not
treated as failures: they are the honest output of this design guide.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUDGET_FILE = HERE / "error_budget_rev03.json"
SPEC_FILE = ROOT / "docs" / "spec.yml"
CONFIG_FILE = ROOT / "config" / "normal_parameters.m"
CSV_FILE = HERE / "parameter_binding.csv"
RUN_FILE = (
    ROOT / "analysis" / "behavior" / "public_normal_20261105" / "release_actual"
    / "behavior_12d08121-d679-40cd-9ee2-bc334ff42955" / "parameters.json"
)

KB = 1.380649e-23
T_K = 298.15

results: list[tuple[str, bool, str]] = []


def check(name: str, got, want, rel: float = 2e-4, unit: str = "") -> None:
    numeric = (
        isinstance(got, (int, float))
        and isinstance(want, (int, float))
        and not isinstance(got, bool)
        and not isinstance(want, bool)
    )
    if numeric:
        ok = math.isclose(got, want, rel_tol=rel, abs_tol=1e-12)
    else:
        ok = got == want
    detail = f"got={got} want={want} {unit}".strip()
    results.append((name, bool(ok), detail))


def load_json(path: Path):
    if not path.is_file():
        print(f"FATAL: missing input file {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    B = load_json(BUDGET_FILE)
    S = load_json(SPEC_FILE)
    P = load_json(RUN_FILE)
    cfg = CONFIG_FILE.read_text(encoding="utf-8")

    baseline = B["baseline"]
    D = B["derived"]
    K = B["constants"]
    tgt = S["target"]
    frac_spec = S["noise_budget"]["fractions"]
    alloc = {a["id"]: a for a in B["allocation"]}
    mods = {m["id"]: m for m in B["modules"]}

    # ---- 1. spec.yml must still be the baseline this budget was written for
    check("spec.fsr_diff_v == budget baseline", tgt["fsr_diff_v"], baseline["fsr_diff_v"])
    check("spec.snr_db_min", tgt["snr_db_min"], baseline["snr_db_min"])
    check("spec.sinad_db_min", tgt["sinad_db_min"], baseline["sinad_db_min"])
    check("spec.thd_dbc_max", tgt["thd_dbc_max"], baseline["thd_dbc_max"])
    check("spec.sample_rate_hz", tgt["sample_rate_hz"], baseline["fs_hz"])
    check("spec.test_input_hz", tgt["test_input_hz"], baseline["fin_hz"])
    check("spec.amplitude_dbfs", tgt["test_amplitude_dbfs"], baseline["amplitude_dbfs"])
    check("spec.reference_v", tgt["reference_v"], baseline["reference_v"])
    check("spec.temperature_K", tgt["test_temperature_c"] + 273.15, baseline["temperature_k"])

    # ---- 2. analytic chain: SPEC -> input-referred rms limits
    fsr = baseline["fsr_diff_v"]
    amp_dbfs = baseline["amplitude_dbfs"]
    vrms = (fsr / 2) * 10 ** (amp_dbfs / 20) / math.sqrt(2)
    noise = vrms / 10 ** (baseline["snr_db_min"] / 20)
    total = vrms / 10 ** (baseline["sinad_db_min"] / 20)
    dist = math.sqrt(total ** 2 - noise ** 2)
    thd = vrms * 10 ** (baseline["thd_dbc_max"] / 20)
    sinad_at_thd = 20 * math.log10(vrms / math.sqrt(noise ** 2 + thd ** 2))
    lsb = fsr / 2 ** baseline["output_bits"]
    qrms = lsb / math.sqrt(12)

    check("derived.vrms_minus1dbfs_v", vrms, D["vrms_minus1dbfs_v"], unit="V")
    check("derived.noise_rms_snr100_uv", noise * 1e6, D["noise_rms_snr100_uv"], unit="uV")
    check("derived.total_rms_sinad98_uv", total * 1e6, D["total_rms_sinad98_uv"], unit="uV")
    check("derived.distortion_from_sinad_uv", dist * 1e6, D["distortion_from_sinad_uv"], unit="uV")
    check("derived.distortion_from_sinad_dbc", 20 * math.log10(vrms / dist), D["distortion_from_sinad_dbc"], unit="dBc")
    check("derived.harmonic_rms_thd105dbc_uv", thd * 1e6, D["harmonic_rms_thd105dbc_uv"], unit="uV")
    check("derived.sinad_if_thd_at_limit_db", sinad_at_thd, D["sinad_if_thd_at_limit_db"], unit="dB")
    check("derived.thd_margin_db", sinad_at_thd - baseline["sinad_db_min"], D["thd_margin_db"], unit="dB")
    check("derived.thd_is_controlling", thd < dist, D["thd_controlling"])
    check("derived.lsb20_uv", lsb * 1e6, D["lsb20_uv"], unit="uV")
    check("derived.quantization_rms_uv", qrms * 1e6, D["quantization_rms_uv"], unit="uV")
    check("derived.quantization_power_fraction", (qrms / noise) ** 2, D["quantization_power_fraction"])
    check("derived.inl_4ppm_uv", baseline["inl_ppm_fsr_max"] * 1e-6 * fsr * 1e6, D["inl_4ppm_uv"], unit="uV")
    check("derived.delta1_uv", baseline["stage1_delta_v"] * 1e6, D["delta1_uv"], unit="uV")
    check("derived.stage2_step_uv", 1.024 / 2 ** 11 / baseline["ra_gain"] * 1e6,
          D["stage2_step_input_referred_uv"], unit="uV")

    vrms10 = (10 / 2) * 10 ** (amp_dbfs / 20) / math.sqrt(2)
    noise10 = vrms10 / 10 ** (baseline["snr_db_min"] / 20)
    check("derived.vrms_10v_workpoint_v", vrms10, D["vrms_10v_workpoint_v"], unit="V")
    check("derived.noise_rms_10v_snr100_uv", noise10 * 1e6, D["noise_rms_10v_snr100_uv"], unit="uV")
    check("derived.power_scale_10v_vs_rev03", (noise10 / noise) ** 2, D["power_scale_10v_vs_rev03"])

    # ---- 3. allocation closure
    fsum = sum(a["power_fraction"] for a in B["allocation"])
    check("allocation.power_fraction_sum", fsum, B["closure"]["power_fraction_sum"])
    rss2 = 0.0
    for key, val in frac_spec.items():
        check(f"allocation.{key}.fraction_matches_spec", val, alloc[key]["power_fraction"])
        lim = noise * math.sqrt(val) * 1e6
        check(f"allocation.{key}.rms_limit_uv", lim, alloc[key]["rms_limit_uv"], unit="uV")
        rss2 += lim ** 2
    check("allocation.sum_of_rms_limits_squared", rss2, (noise * 1e6) ** 2, unit="uV^2")

    # ---- 4. per-module analytic design limits
    cmin = 2 * KB * T_K / (noise * math.sqrt(alloc["sampling"]["power_fraction"])) ** 2
    check("M_SAMPLE_KTC.c_signal_min_pf", cmin * 1e12, mods["M_SAMPLE_KTC"]["design_limit"]["c_signal_min_pf"], unit="pF")

    vstep = K["vstep_worst_v"]
    t_acq = K["sample_window_ns"] * 1e-9
    need = math.log(vstep / thd)
    tau_max = t_acq / need
    C_f = P["front"]["C_f"]
    c_signal = sum(sum(row) for row in C_f[:8])
    c_top = c_signal + sum(P["front"]["Cp_f"][:8])
    ron_max = tau_max / c_top
    check("M_SAMPLE_RC.tau_max_ns", tau_max * 1e9, mods["M_SAMPLE_RC"]["design_limit"]["tau_max_ns"], unit="ns")
    check("M_SAMPLE_RC.ron_max_ohm", ron_max, mods["M_SAMPLE_RC"]["design_limit"]["ron_max_ohm"], unit="ohm")

    j = mods["M_JITTER"]["design_limit"]
    for fin, snr, key in [
        (baseline["fin_hz"], baseline["snr_db_min"], "sigma_t_100k_snr100_ps_all_budget"),
        (baseline["fin_ext_hz"], baseline["snr_ext_db_min"], "sigma_t_1m_snr96_ps_all_budget"),
    ]:
        st = 1 / (2 * math.pi * fin * 10 ** (snr / 20))
        check(f"M_JITTER.{key}", st * 1e12, j[key], unit="ps")
    check("M_JITTER.sigma_t_100k_ps_at_1pct_subbudget",
          1 / (2 * math.pi * baseline["fin_hz"] * 10 ** (baseline["snr_db_min"] / 20)) * 0.1 * 1e12,
          j["sigma_t_100k_ps_at_1pct_subbudget"], unit="ps")
    check("M_JITTER.sigma_t_1m_ps_at_1pct_subbudget",
          1 / (2 * math.pi * baseline["fin_ext_hz"] * 10 ** (baseline["snr_ext_db_min"] / 20)) * 0.1 * 1e12,
          j["sigma_t_1m_ps_at_1pct_subbudget"], unit="ps")

    G = baseline["ra_gain"]
    check("M_RA_NOISE.ra_output_max_uv_rms",
          alloc["ra_after_tracking"]["rms_limit_uv"] * G,
          mods["M_RA_NOISE"]["design_limit"]["ra_output_max_uv_rms"], unit="uV")
    check("M_COMPARATOR.stage2_input_max_uv_rms",
          alloc["comparator_after_tracking"]["rms_limit_uv"] * G,
          mods["M_COMPARATOR"]["design_limit"]["stage2_input_max_uv_rms"], unit="uV")

    t_dac = K["dac_window_ns"] * 1e-9
    tau_dac_max = t_dac / math.log(2 ** K["stage2_half_lsb_target_bits"])
    check("M_DAC_SETTLING.tau_max_ns_simple_exp", tau_dac_max * 1e9,
          mods["M_DAC_SETTLING"]["design_limit"]["tau_max_ns_simple_exp"], unit="ns")

    cf = P["backend"]["ra"]["Cf_f"]
    ng = 1 + c_top / cf
    ugb = P["backend"]["ra"]["UGB_hz"]
    tau_ra = ng / (2 * math.pi * ugb)
    check("M_RA_DYNAMICS.noise_gain", ng, mods["M_RA_DYNAMICS"]["design_limit"]["noise_gain"])
    check("M_RA_DYNAMICS.tau_ra_ns", tau_ra * 1e9, mods["M_RA_DYNAMICS"]["design_limit"]["tau_ra_ns"], unit="ns")
    check("M_STATIC_LINEARITY.inl_lsb20",
          baseline["inl_ppm_fsr_max"] * 1e-6 * fsr / lsb,
          mods["M_STATIC_LINEARITY"]["design_limit"]["inl_lsb20"])

    # ---- 5. model parameter binding (config + authoritative run)
    scalars = dict(re.findall(r"([A-Za-z_]\w*)\s*=\s*([0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)", cfg))
    for key, expected in [
        ("Ron_eq", 20), ("temperature_K", 298.15), ("dacTau_s", 0.5e-9),
        ("raA0", 1e4), ("raUGB_hz", 1.2e9), ("frontCpHalf_f", 100e-15),
        ("Ceff_f", 100e-15),
    ]:
        check(f"config.{key}", float(scalars[key]), expected)

    sigma_ktc = math.sqrt(2 * KB * T_K / c_signal)
    svx = P["backend"]["ra_noise"]["sigma_vx_rms"]
    scmp = P["control"]["comparator"]["sar2_noise_rms_v"]
    check("model.C_signal_pf", c_signal * 1e12, mods["M_SAMPLE_KTC"]["current_model"]["c_signal_pf"], unit="pF")
    check("model.C_top_pf", c_top * 1e12, mods["M_SAMPLE_KTC"]["current_model"]["c_top_pf"], unit="pF")
    check("model.sigma_ktc_uv", sigma_ktc * 1e6, mods["M_SAMPLE_KTC"]["current_model"]["sigma_uv_rms"], unit="uV")
    check("model.sampling_power_fraction", (sigma_ktc / noise) ** 2,
          mods["M_SAMPLE_KTC"]["current_model"]["power_fraction_used"])
    check("model.tau_sample_ns", P["front"]["tau_sample_s"][0] * 1e9,
          mods["M_SAMPLE_RC"]["current_model"]["tau_ns"], unit="ns")
    check("model.tau_sample_equals_RonC", P["front"]["tau_sample_s"][0], 20 * c_top)
    check("model.ra_input_referred_uv", svx / G * 1e6,
          mods["M_RA_NOISE"]["current_model"]["input_referred_uv_rms"], unit="uV")
    check("model.ra_after_7db_uv", svx / G / K["tracking_gain_paper_7db"] * 1e6,
          mods["M_RA_NOISE"]["current_model"]["after_tracking_7db_uv"], unit="uV")
    check("model.cmp_input_referred_uv", scmp / G * 1e6,
          mods["M_COMPARATOR"]["current_model"]["input_referred_uv_rms"], unit="uV")
    check("model.cmp_after_7db_uv", scmp / G / K["tracking_gain_paper_7db"] * 1e6,
          mods["M_COMPARATOR"]["current_model"]["after_tracking_7db_uv"], unit="uV")
    check("model.quantization_rms_uv", qrms * 1e6,
          mods["M_QUANTIZATION"]["current_model"]["quantization_rms_uv"], unit="uV")
    check("model.calibration_off", P["digital"]["calibration_mode"], "off")
    check("model.transport_off", P["transport"]["enabled"], False)
    check("model.workpoint_is_10V_not_rev03", P["fsr_diff_v"], 10, unit="V (expected mismatch marker)")

    # ---- 6. binding table shape
    with CSV_FILE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    widths = {len(r) for r in rows}
    check("parameter_binding.csv.column_count", widths, {9})
    results.append(("parameter_binding.csv.rows", len(rows) - 1 >= 25, f"data_rows={len(rows)-1}"))

    # ---- report
    print("=== SAR20-5 Rev0.3 design budget verification ===")
    print(f"baseline: {baseline['id']}  FSR={fsr} V  Fin={baseline['fin_hz']/1e3:.0f} kHz  "
          f"SNR>={baseline['snr_db_min']} dB  SINAD>={baseline['sinad_db_min']} dB")
    nfail = 0
    for name, ok, detail in results:
        if not ok:
            nfail += 1
            print(f"  [FAIL] {name}: {detail}")
    npass = len(results) - nfail
    print(f"checks: {npass} PASS / {nfail} FAIL / {len(results)} total")

    print("\n-- numeric limits that a designer can act on --")
    print(f"  noise ceiling @SNR100dB         : {noise*1e6:.4f} uV rms input-referred")
    print(f"  harmonic ceiling @THD-105dBc    : {thd*1e6:.4f} uV rms (controls over SINAD's {dist*1e6:.4f} uV)")
    print(f"  C_signal minimum (50% kT/C)     : {cmin*1e12:.4f} pF")
    print(f"  Ron maximum (12.5 ns window)    : {ron_max:.2f} ohm")
    print(f"  jitter max @100kHz / 1MHz       : {1/(2*math.pi*baseline['fin_hz']*1e5)*1e12:.3f} ps / "
          f"{1/(2*math.pi*baseline['fin_ext_hz']*10**(baseline['snr_ext_db_min']/20))*1e12:.3f} ps")
    print(f"  current C_signal                : {c_signal*1e12:.4f} pF -> sigma_ktc {sigma_ktc*1e6:.4f} uV "
          f"({(sigma_ktc/noise)**2*100:.2f}% of noise power)")

    print("\n-- unverified design gates (NOT failures; no compliance claim allowed) --")
    for m in B["modules"]:
        if m["verdict"] not in ("PASS_ANALYTIC", "CONDITIONAL_PASS_ANALYTIC"):
            print(f"  [{m['verdict']:<34s}] {m['id']:<20s} {m['gate'][:110]}")
    print(f"\nclosure verdict: {B['closure']['verdict']}")
    for r in B["closure"]["blocking_reasons"]:
        print(f"  - {r}")

    if nfail:
        print("\nRESULT: FAIL - budget numbers have drifted from spec.yml or the model. Re-derive before reuse.")
        return 1
    print("\nRESULT: PASS - analytic chain is self-consistent. Unverified gates above still require measurement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
