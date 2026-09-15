"""Read-only HYP-009 counters. Run from any directory with Python 3.10+."""
import csv
import json
import math
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
MISSING = {'', 'UNKNOWN', 'NA', 'N/A'}
REASONS = set('IMPULSE_TOO_LARGE IMPULSE_TOO_SMALL IMPULSE_TOO_LONG IMPULSE_TOO_SHORT PULLBACK_TOO_SHALLOW PULLBACK_TOO_DEEP NO_TRIGGER STOP_TOO_WIDE STOP_TOO_TIGHT SPREAD EVENT_WINDOW OUT_OF_SESSION AMBIGUOUS_DATA INVALID_STOP_SIDE IMPULSE_ALREADY_USED'.split())


def number(value):
    if value in MISSING:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Non-finite number')
    return result


def read_csv(path, key):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    seen = set()
    for row in rows:
        if None in row or None in row.values():
            raise ValueError(f'{path.name}: CSV column mismatch')
        if row[key] in seen or row[key] in MISSING:
            raise ValueError(f'{path.name}: duplicate/missing {key}')
        seen.add(row[key])
    return rows


def metadata(row):
    return dict(part.strip().split('=', 1) for part in row['notes'].split(';') if '=' in part)


def summarize(tests, opportunities):
    completed, opened, errors = [], [], []
    insufficient, rejected = set(), set()
    by_id = {r['case_id']: r for r in tests}
    structures = set()
    for row in tests:
        cid, valid, meta = row['case_id'], row['valid'], metadata(row)
        if valid not in {'TRUE', 'FALSE', 'PENDING'}:
            errors.append(f'{cid}: invalid valid value')
        if valid == 'FALSE':
            rejected.add(cid)
        if valid == 'PENDING':
            if meta.get('eligibility') == 'CONFIRMED' and meta.get('position_status') == 'OPEN' and number(row['entry']) is not None and row['exit'] in MISSING:
                opened.append(cid)
            else:
                insufficient.add(cid)
        if valid != 'TRUE':
            continue
        required = ['entry', 'stop', 'stop_pips', 'target', 'exit', 'result_r', 'spread_pips']
        if any(number(row[k]) is None for k in required) or row['exit_time'] in MISSING or meta.get('test_mode') != 'forward' or meta.get('eligibility') != 'CONFIRMED' or meta.get('position_status') != 'CLOSED' or meta.get('exit_reason') not in {'TP', 'SL', 'GAP_SL', 'TIME_STOP'}:
            errors.append(f'{cid}: TRUE row missing completion/evidence metadata')
            insufficient.add(cid)
            continue
        structure = tuple(row[k] for k in ['direction', 'impulse_start_time', 'impulse_end_time'])
        if structure in structures:
            errors.append(f'{cid}: duplicate impulse')
            continue
        structures.add(structure)
        completed.append(row)
    groups, parents = {}, set()
    for row in opportunities:
        oid, parent = row['opportunity_id'], row['parent_case_id']
        key = parent if parent not in MISSING else oid
        if parent not in MISSING:
            if parent not in by_id or parent in parents:
                errors.append(f'{oid}: missing/duplicate parent')
            elif by_id[parent]['valid'] == 'TRUE':
                errors.append(f'{oid}: valid sample also in opportunity log')
            parents.add(parent)
        reasons = set(row['rejection_reason'].split(';'))
        if not reasons <= REASONS:
            errors.append(f'{oid}: unknown rejection reason')
        if row['classification'] not in {'REJECTED_OPPORTUNITY', 'INSUFFICIENT_DATA'} or row['evidence_status'] not in {'CONFIRMED', 'PROVISIONAL'}:
            errors.append(f'{oid}: invalid classification/evidence')
        if row['outcome_status'] not in {'COMPLETE', 'PARTIAL', 'UNKNOWN'} or row['r_status'] not in {'DEFINED', 'UNDEFINED', 'UNKNOWN'}:
            errors.append(f'{oid}: invalid outcome/R status')
        bars = number(row['observation_bars'])
        if bars is None or not bars.is_integer() or not 0 <= bars <= 12 or (row['outcome_status'] == 'COMPLETE' and bars != 12):
            errors.append(f'{oid}: invalid observation bars')
        if row['classification'] == 'REJECTED_OPPORTUNITY':
            rejected.add(key)
        if row['classification'] == 'INSUFFICIENT_DATA' or row['evidence_status'] == 'PROVISIONAL' or 'AMBIGUOUS_DATA' in reasons or row['outcome_status'] != 'COMPLETE':
            insufficient.add(key)
        if row['r_status'] == 'UNDEFINED' and any(row[k] not in {'NA', 'N/A'} for k in ['hypothetical_stop', 'hypothetical_stop_distance', 'mfe_r', 'mae_r', 'reached_1r', 'reached_1_5r', 'first_1r', 'first_1_5r']):
            errors.append(f'{oid}: undefined R must be NA')
        if row['r_status'] == 'DEFINED' and (number(row['hypothetical_stop_distance']) is None or number(row['hypothetical_stop_distance']) <= 0):
            errors.append(f'{oid}: invalid R denominator')
        if row['r_status'] == 'DEFINED' and number(row['hypothetical_stop_distance']) is not None and number(row['hypothetical_stop_distance']) > 0:
            distance = number(row['hypothetical_stop_distance'])
            for pips, r_col in [('mfe_pips', 'mfe_r'), ('mae_pips', 'mae_r')]:
                a, b = number(row[pips]), number(row[r_col])
                if a is not None and b is not None and (a < 0 or b < 0 or abs(a / distance - b) > 0.01):
                    errors.append(f'{oid}: inconsistent {r_col}')
            for threshold, level in [('1r', 1.0), ('1_5r', 1.5)]:
                flag, mfe = row['reached_' + threshold], number(row['mfe_r'])
                if row['outcome_status'] == 'COMPLETE' and mfe is not None and flag in {'TRUE', 'FALSE'} and (flag == 'TRUE') != (mfe + 1e-9 >= level):
                    errors.append(f'{oid}: inconsistent reached_{threshold}')
        if row['classification'] != 'REJECTED_OPPORTUNITY':
            continue
        for reason in sorted(reasons):
            group = (reason, row['evidence_status'], row['reference_basis'])
            groups.setdefault(group, []).append(row)
    completed.sort(key=lambda r: (r['datetime_jst'], r['case_id']))
    values = [number(r['result_r']) for r in completed]
    gains, losses = sum(v for v in values if v > 0), -sum(v for v in values if v < 0)
    n = len(values)
    output = {
        'HYP-009 v0.1': {
            'Valid completed samples': n,
            'Wins': sum(v > 0 for v in values), 'Losses': sum(v < 0 for v in values),
            'Breakeven': values.count(0),
            'Time stops (overlap wins/losses)': sum(metadata(r)['exit_reason'] == 'TIME_STOP' for r in completed),
            'Open': len(opened), 'Rejected opportunities': len(rejected),
            'Insufficient-data observations (overlap rejected)': len(insufficient),
            'Win rate': sum(v > 0 for v in values) / n if n else 'UNKNOWN',
            'Expectancy / Average R': sum(values) / n if n else 'UNKNOWN',
            'Profit Factor': gains / losses if losses else ('INF' if gains else 'UNKNOWN'),
            'First 30 completed IDs': [r['case_id'] for r in completed[:30]],
            '30-sample cohort': 'REVIEW_PENDING' if n >= 30 and not any(r['valid'] == 'PENDING' and r['datetime_jst'] <= completed[29]['datetime_jst'] for r in tests) else 'NOT_FINAL',
        },
        'Reason groups (multi-label; do not sum)': [],
        'Legacy FALSE rows without opportunity detail': sorted(rejected - {r['parent_case_id'] if r['parent_case_id'] not in MISSING else r['opportunity_id'] for r in opportunities}),
        'Audit errors': errors,
    }
    for (reason, evidence, basis), rows in sorted(groups.items()):
        item = dict(reason=reason, evidence=evidence, reference_basis=basis, total=len(rows), complete=sum(r['outcome_status'] == 'COMPLETE' for r in rows), r_defined=sum(r['r_status'] == 'DEFINED' for r in rows))
        for metric in ['mfe_pips', 'mae_pips', 'mfe_r', 'mae_r']:
            values_for_metric = [number(r[metric]) for r in rows]
            known = [v for v in values_for_metric if v is not None]
            item[metric] = {'mean': sum(known) / len(known) if known else 'UNKNOWN', 'denominator': len(known), 'missing_or_ineligible': len(rows) - len(known)}
        for threshold in ['1r', '1_5r']:
            eligible = [r for r in rows if r['r_status'] == 'DEFINED' and r['outcome_status'] == 'COMPLETE']
            flags = [r['reached_' + threshold] for r in eligible if r['reached_' + threshold] in {'TRUE', 'FALSE'}]
            order = Counter(r['first_' + threshold] for r in eligible if r['first_' + threshold] in {'ADVERSE_FIRST', 'FAVORABLE_FIRST', 'SAME_BAR', 'NEITHER'})
            item[threshold] = {'reached': flags.count('TRUE'), 'denominator': len(flags), 'missing_or_ineligible': len(rows) - len(flags), 'first_passage': dict(order), 'order_denominator': sum(order.values()), 'conservative_adverse_including_same_bar': order['ADVERSE_FIRST'] + order['SAME_BAR']}
        output['Reason groups (multi-label; do not sum)'].append(item)
    return output


if __name__ == '__main__':
    report = summarize(read_csv(ROOT / 'HYP-009-v0.1-tests.csv', 'case_id'), read_csv(ROOT / 'HYP-009-rejected-opportunities.csv', 'opportunity_id'))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report['Audit errors'] else 0)
