#!/usr/bin/env python3
"""Check normal single-bank RAW6 against public nominal digital output.

Inputs are a public records CSV and a public DecodeP JSON. No SimulationOutput,
full P, analog truth, held value, training reference or holdout is read. CSV
rows are already joined/selected by the producer; this script does not claim
an independent join to raw_capture or validate the Simulink graph wiring.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys

MAX_FILE_BYTES = 300_000_000
NOMINAL_D2 = (0.36, 0.24, 0.16, 0.104, 0.064, 0.04,
              0.024, 0.012, 0.008, 0.004, 0.002, 0.001)
REQUIRED_DIGITAL = frozenset({'vref_v', 'fsr_diff_v', 'ra_gain', 'd1_bias_v',
    'd2_weights_ra_v', 'd2_offset_ra_v', 'tracking_step_ra_v', 'az_mode',
    'tracking_mode', 'calibration_mode', 'dither_enabled'})
OPTIONAL_DIGITAL = frozenset({'schema', 'dither_seed', 'dither_amplitude_v', 'coefficient_source'})
RECORD_FIELDS = frozenset({'D1', 'D2', 'DT', 'ID', 'epoch', 'valid', 'time_s', 'code20'})


@dataclass(frozen=True)
class Digital:
    vref: float
    fsr: float
    gain: float
    bias: float
    d2weights: tuple[float, ...]
    d2offset: float
    tracking: float


def _read_bytes(path: Path, max_size: int = MAX_FILE_BYTES) -> bytes:
    with path.open('rb') as stream:
        size = Path(path).stat().st_size
        if size <= 0 or size > max_size:
            raise ValueError(f'input missing, empty or oversized: {path.name}')
        data = stream.read(max_size + 1)
    if not data or len(data) > max_size:
        raise ValueError(f'input empty or oversized: {path.name}')
    return data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{field} must be a public real scalar')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f'{field} must be finite')
    return number


def parse_digital(data: bytes) -> tuple[Digital, dict[str, float]]:
    def reject_constant(value: str) -> None:
        raise ValueError(f'nonfinite JSON number: {value}')
    obj = json.loads(data.decode('utf-8-sig'), parse_constant=reject_constant)
    if not isinstance(obj, dict) or not REQUIRED_DIGITAL <= obj.keys() or obj.keys() - (REQUIRED_DIGITAL | OPTIONAL_DIGITAL):
        raise ValueError('digital JSON must contain only the declared public DecodeP fields')
    if 'schema' in obj and obj['schema'] != 'sar20-behavior-decode/v1':
        raise ValueError('unexpected public digital schema')
    if obj['az_mode'] != 'ordinary' or obj['tracking_mode'] != 'finite_sinc2' or obj['calibration_mode'] != 'off':
        raise ValueError('require ordinary AZ, finite_sinc2 and calibration OFF')
    if obj['dither_enabled'] is not False and not (type(obj['dither_enabled']) in (int, float) and obj['dither_enabled'] == 0):
        raise ValueError('require dither OFF')
    vref = _finite_number(obj['vref_v'], 'vref_v')
    fsr = _finite_number(obj['fsr_diff_v'], 'fsr_diff_v')
    gain = _finite_number(obj['ra_gain'], 'ra_gain')
    bias = _finite_number(obj['d1_bias_v'], 'd1_bias_v')
    offset = _finite_number(obj['d2_offset_ra_v'], 'd2_offset_ra_v')
    track = _finite_number(obj['tracking_step_ra_v'], 'tracking_step_ra_v')
    if (vref, fsr, gain, bias) != (5.0, 10.0, 32.0, 0.0):
        raise ValueError('require Vref1=5 V, FSRdiff=10 V, G=32 and zero 17Cu bias')
    raw_weights = obj['d2_weights_ra_v']
    if not isinstance(raw_weights, list) or len(raw_weights) != 12:
        raise ValueError('d2_weights_ra_v must be a public 12-element vector')
    weights = tuple(_finite_number(x, f'd2_weights_ra_v[{k}]') for k, x in enumerate(raw_weights))
    # Same absolute voltage tolerance as the independent nominal-CT constructor;
    # reconstruction below always uses the actual supplied floating-point values.
    tol = 1e-12
    delta = max(abs(a-b) for a, b in zip(weights, NOMINAL_D2))
    if delta > tol or abs(offset - (-0.5095)) > tol or abs(track - 0.00025) > tol:
        raise ValueError('public D2 offset/weights or DT step do not match nominal CT900')
    if 'dither_seed' in obj:
        seed = _finite_number(obj['dither_seed'], 'dither_seed')
        if seed != math.floor(seed) or not 0 <= seed <= 2**32-1:
            raise ValueError('invalid public dither seed')
    if 'dither_amplitude_v' in obj and _finite_number(obj['dither_amplitude_v'], 'dither_amplitude_v') < 0:
        raise ValueError('invalid public dither amplitude')
    if 'coefficient_source' in obj and not isinstance(obj['coefficient_source'], str):
        raise ValueError('invalid public coefficient-source label')
    return Digital(vref, fsr, gain, bias, weights, offset, track), {
        'max_abs_d2_weight_difference_from_nominal_v': delta,
        'abs_d2_offset_difference_from_nominal_v': abs(offset+0.5095),
        'abs_tracking_step_difference_from_nominal_v': abs(track-0.00025),
        'nominal_coefficient_abs_tolerance_v': tol,
    }


def _csv_number(value: str | None, field: str, row: int) -> float:
    if value is None or not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f'row {row}: missing or malformed {field}')
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f'row {row}: nonnumeric {field}') from exc
    if not math.isfinite(number):
        raise ValueError(f'row {row}: nonfinite {field}')
    return number


def _csv_integer(value: str | None, field: str, row: int, upper: int) -> int:
    number = _csv_number(value, field, row)
    if number != math.floor(number) or not 0 <= number <= upper:
        raise ValueError(f'row {row}: invalid integer {field}')
    return int(number)


def parse_records(data: bytes, count: int, first_id: int, epoch: int) -> list[dict[str, object]]:
    import io
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))
    names = reader.fieldnames or []
    if len(names) != len(set(names)) or frozenset(names) not in (RECORD_FIELDS, RECORD_FIELDS | {'raw_ready'}):
        raise ValueError('CSV requires D1,D2,DT,ID,epoch,valid,time_s,code20 and optional raw_ready only')
    result: list[dict[str, object]] = []
    for line, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f'row {line}: extra CSV fields')
        if len(result) >= count:
            raise ValueError('more rows than the declared capture count')
        r = {
            'D1': _csv_integer(row['D1'], 'D1', line, 2047),
            'D2': _csv_integer(row['D2'], 'D2', line, 4095),
            'DT': _csv_integer(row['DT'], 'DT', line, 255),
            'sample_id': _csv_integer(row['ID'], 'ID', line, 2**32-1),
            'epoch': _csv_integer(row['epoch'], 'epoch', line, 2**32-1),
            'valid': _csv_integer(row['valid'], 'valid', line, 1),
            'time_s': _csv_number(row['time_s'], 'time_s', line),
            'code20': _csv_integer(row['code20'], 'code20', line, 2**20-1),
        }
        if r['valid'] != 1:
            raise ValueError(f'row {line}: invalid RAW; no filtering is performed')
        if 'raw_ready' in names and _csv_integer(row['raw_ready'], 'raw_ready', line, 1) != 1:
            raise ValueError(f'row {line}: row was not marked actual raw-ready')
        if r['sample_id'] != first_id + len(result) or r['epoch'] != epoch:
            raise ValueError(f'row {line}: sample ID sequence or epoch differs')
        if r['time_s'] < 0 or (result and r['time_s'] <= result[-1]['time_s']):
            raise ValueError(f'row {line}: actual timestamps must increase strictly')
        result.append(r)
    if len(result) != count:
        raise ValueError(f'expected {count} selected ready records, got {len(result)}')
    return result


def _round_away_float(value: float) -> int:
    # Avoid floor(x+0.5): the addition itself can round a number just below a
    # half-code to the next integer in binary64.
    fractional, whole = math.modf(value)
    if fractional >= 0.5:
        return int(whole)+1
    if fractional <= -0.5:
        return int(whole)-1
    return int(whole)


def _round_away_exact(value: Fraction) -> int:
    quotient, remainder = divmod(abs(value.numerator), value.denominator)
    magnitude = quotient + int(2*remainder >= value.denominator)
    return magnitude if value >= 0 else -magnitude


def _clip(value: int) -> int:
    return max(0, min(2**20-1, value))


def reconstruct(raw6: tuple[int, int, int, int, int, int], cfg: Digital) -> dict[str, object]:
    """Compute from public RAW6 + public nominal parameters only."""
    d1, d2, dt, sample_id, epoch, valid = raw6
    if not (0 <= d1 <= 2047 and 0 <= d2 <= 4095 and 0 <= dt <= 255 and valid == 1):
        raise ValueError('invalid public RAW6')
    coarse, fine = divmod(d1, 32)
    d2bits = [(d2 >> k) & 1 for k in range(11, -1, -1)]
    dtbits = [(dt >> k) & 1 for k in range(7, -1, -1)]
    weighted_signs = 2*sum((8-k)*bit for k, bit in enumerate(dtbits))-36

    # 485 graph operation grouping: nominal weight dot then offset; D2 and DT
    # have separate input-domain gains. Python's dot accumulation may differ
    # from Simulink's matrix implementation at binary64 half-code boundaries.
    d1_v = ((2*d1-32*coarse-1039)*(cfg.vref/1024))+cfg.bias
    d2weighted = 0.0
    for bit, weight in zip(d2bits, cfg.d2weights):
        d2weighted += bit*weight
    d2_ra_v = d2weighted+cfg.d2offset
    dt_ra_v = cfg.tracking*(weighted_signs/8)
    d2_v = d2_ra_v*(1/cfg.gain)
    dt_v = weighted_signs*(cfg.tracking/(8*cfg.gain))
    voltage_v = ((d1_v+d2_v)+dt_v)+0.0  # ordinary POL=+1, dither OFF
    unrounded = voltage_v*(2**20/cfg.fsr)+2**19
    if not math.isfinite(voltage_v) or not math.isfinite(unrounded):
        raise ValueError('nominal digital reconstruction overflow')
    rounded = _round_away_float(unrounded)
    predicted = _clip(rounded)

    # Exact rational arithmetic over the supplied binary64 public coefficients
    # is a diagnostic, not a substitute for the strict graph-like code gate.
    F = Fraction.from_float
    exact_d1 = Fraction(32*coarse+2*fine-1039)*F(cfg.vref)/1024+F(cfg.bias)
    exact_d2_ra = F(cfg.d2offset)+sum((bit*F(weight) for bit, weight in zip(d2bits, cfg.d2weights)), Fraction(0))
    exact_dt_ra = F(cfg.tracking)*Fraction(weighted_signs, 8)
    exact_voltage = exact_d1+(exact_d2_ra+exact_dt_ra)/F(cfg.gain)
    exact_counts = exact_voltage*Fraction(2**20, 1)/F(cfg.fsr)+2**19
    exact_code = _clip(_round_away_exact(exact_counts))
    fraction = exact_counts - (exact_counts.numerator // exact_counts.denominator)
    half_distance = float(abs(fraction-Fraction(1, 2)))
    return {'sample_id': sample_id, 'epoch': epoch, 'valid': valid,
            'D1': d1, 'D2': d2, 'DT': dt, 'coarse': coarse, 'fine': fine,
            'polarity': 1, 'dt_weighted_sign_sum': weighted_signs,
            'd1_input_v': d1_v, 'd2_ra_v': d2_ra_v, 'dt_ra_v': dt_ra_v,
            'd2_input_v': d2_v, 'dt_input_v': dt_v,
            'nominal_residual_ra_v': d2_ra_v+dt_ra_v,
            'nominal_residual_input_v': d2_v+dt_v,
            'digital_voltage_v': voltage_v, 'unrounded_code': unrounded,
            'rounded_before_saturation': rounded, 'predicted_code20': predicted,
            'clipped': int(predicted != rounded), 'exact_rational_code20': exact_code,
            'exact_distance_to_half_code': half_distance}


def _range(rows: list[dict[str, object]], name: str) -> dict[str, float]:
    values = [float(row[name]) for row in rows]
    return {'min': min(values), 'max': max(values)}


def run(records: list[dict[str, object]], cfg: Digital) -> list[dict[str, object]]:
    output = []
    for item in records:
        raw6 = tuple(int(item[k]) for k in ('D1', 'D2', 'DT', 'sample_id', 'epoch', 'valid'))
        row = reconstruct(raw6, cfg)
        actual = int(item['code20'])
        row.update({'time_s': item['time_s'], 'actual_code20': actual,
                    'integer_difference_actual_minus_predicted': actual-int(row['predicted_code20']),
                    'strict_match': int(actual == row['predicted_code20']),
                    'exact_rational_match': int(actual == row['exact_rational_code20'])})
        output.append(row)
    return output


def _write_output(directory: Path, rows: list[dict[str, object]], summary: dict[str, object]) -> None:
    # The output directory must be a new direct child of this script's review
    # directory; prior review evidence is never overwritten.
    base = Path(__file__).resolve().parent
    directory = directory.expanduser()
    if not directory.is_absolute():
        directory = base/directory
    if directory.parent.resolve() != base or directory.name in ('', '.', '..'):
        raise ValueError('output must be a new direct child of the review directory')
    directory.mkdir(mode=0o700, exist_ok=False)
    with (directory/'per_record.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (directory/'summary.json').open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True, help='prejoined public records CSV')
    parser.add_argument('--digital', type=Path, required=True, help='public DecodeP-only JSON')
    parser.add_argument('--expected-count', type=int, choices=(8, 256), required=True)
    parser.add_argument('--expected-first-id', type=int, default=4)
    parser.add_argument('--expected-epoch', type=int, required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='new directory name under this review folder')
    args = parser.parse_args()
    if not 0 <= args.expected_first_id <= 2**32-args.expected_count or not 0 <= args.expected_epoch <= 2**32-1:
        raise ValueError('invalid expected ID window or epoch')
    record_bytes = _read_bytes(args.records)
    digital_bytes = _read_bytes(args.digital, max_size=100_000)
    cfg, delta = parse_digital(digital_bytes)
    records = parse_records(record_bytes, args.expected_count, args.expected_first_id, args.expected_epoch)
    rows = run(records, cfg)
    mismatch = [int(row['sample_id']) for row in rows if not row['strict_match']]
    exact_mismatch = [int(row['sample_id']) for row in rows if not row['exact_rational_match']]
    summary = {
        'status': 'PASS' if not mismatch else 'FAIL_CODE_MISMATCH',
        'scope': 'public selected RAW6 and nominal DecodeP only; no ADC simulation, analog truth or calibration',
        'independent_raw_code_time_join_proven': False,
        'ready_selection_scope': 'CSV is preselected/joined by exporter; original raw_capture requires separate review',
        'digital_parameter_scope': 'public injected DecodeP JSON; runtime block binding requires separate evidence',
        'arithmetic_scope': 'strict Python graph-like binary64 gate; exact rational column is diagnostic, not tolerance',
        'records_sha256': _sha(record_bytes), 'digital_sha256': _sha(digital_bytes),
        'checker_sha256': _sha(_read_bytes(Path(__file__).resolve(), max_size=1_000_000)),
        'record_count': len(rows), 'first_id': args.expected_first_id, 'last_id': int(rows[-1]['sample_id']),
        'epoch': args.expected_epoch, 'time_range_s': _range(rows, 'time_s'),
        'strict_mismatch_count': len(mismatch), 'strict_mismatch_ids': mismatch,
        'exact_rational_mismatch_count': len(exact_mismatch), 'exact_rational_mismatch_ids': exact_mismatch,
        'saturated_count': sum(int(row['clipped']) for row in rows),
        'd1_input_v_range': _range(rows, 'd1_input_v'),
        'd2_ra_v_range': _range(rows, 'd2_ra_v'), 'dt_ra_v_range': _range(rows, 'dt_ra_v'),
        'nominal_residual_ra_v_range': _range(rows, 'nominal_residual_ra_v'),
        'nominal_residual_input_v_range': _range(rows, 'nominal_residual_input_v'),
        'residual_scope': 'D2+DT nominal digital reconstruction; not an observed analog residual or reference error',
        'configuration_delta': delta,
    }
    _write_output(args.output_dir, rows, summary)
    print(json.dumps({'status': summary['status'], 'records': len(rows), 'mismatches': len(mismatch),
                      'output_dir': str(args.output_dir)}, ensure_ascii=False))
    return 0 if not mismatch else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f'INPUT_OR_IO_ERROR: {exc}', file=sys.stderr)
        raise SystemExit(2)
