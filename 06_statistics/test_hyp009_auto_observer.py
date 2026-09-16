"""Regression and boundary cases for frozen HYP-009 v0.1 semantics."""
import contextlib
import csv
import io
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from hyp009_auto_observer import (BASE, Candle, InputError, Observer, dec, formal_row,
                                  load_candles, main, opportunity_row, prepare_rows,
                                  report, session_allowed, stamp, write_records)
from summarize_hyp009 import read_csv, summarize

D = Decimal


def candle(time, o, h, l, c, *, spread=D('0.3'), event=False, tag='non-event', cost=D('0.1'), closed=True):
    return Candle(time, D(str(o)), D(str(h)), D(str(l)), D(str(c)), spread, event, tag, cost, closed)


def make_long(*, width=D('20'), intervals=2, pullback_pct=D('30'), pullback_pips=None, base=None, exit_mode='TP'):
    base = base or datetime.fromisoformat('2026-09-16T09:00:00+09:00')
    width = D(str(width))
    endpoint = D('150') + width * D('0.01')
    pips = D(str(pullback_pips)) if pullback_pips is not None else width * D(str(pullback_pct)) / 100
    p = endpoint - pips * D('0.01')
    data = [candle(base, '150.04', '150.06', '150.02', '150.04'),
            candle(base + timedelta(minutes=5), '150.03', '150.05', '150.00', '150.02')]
    end_index = 1 + intervals
    for index in range(2, end_index):
        high = D('150.05') + (endpoint - D('150.05')) * D(index - 1) / D(intervals)
        low = D('150.01') + D(index - 2) * D('0.001')
        data.append(candle(base + timedelta(minutes=5 * index), high - D('0.02'), high, low, high - D('0.01')))
    data.append(candle(base + timedelta(minutes=5 * end_index), endpoint - D('0.03'), endpoint, endpoint - D('0.04'), endpoint - D('0.01')))
    data.append(candle(base + timedelta(minutes=5 * (end_index + 1)), endpoint - D('0.03'), endpoint - D('0.01'), p, endpoint - D('0.03')))
    entry = endpoint + D('0.01')
    data.append(candle(base + timedelta(minutes=5 * (end_index + 2)), endpoint - D('0.03'), endpoint + D('0.02'), endpoint - D('0.04'), entry))
    risk = pips + D('2')
    stop = entry - risk * D('0.01')
    target = entry + risk * D('0.015')
    if exit_mode == 'TP':
        data.append(candle(base + timedelta(minutes=5 * (end_index + 3)), entry + D('0.01'), target + D('0.01'), entry - D('0.01'), target))
    elif exit_mode == 'BOTH':
        data.append(candle(base + timedelta(minutes=5 * (end_index + 3)), entry, target + D('0.01'), stop - D('0.01'), entry))
    return data


def mirror(data):
    return [replace(c, open=D('300') - c.open, high=D('300') - c.low, low=D('300') - c.high, close=D('300') - c.close) for c in data]


def run(data, *, forward=True):
    observer = Observer(forward_observed_at=data[0].time.isoformat() if forward else None, source='artificial fixture', price_series='mid')
    for item in data:
        observer.feed(item)
    observer.finish()
    return observer


def target_case(observer, direction='LONG'):
    matches = [c for c in observer.cases if c.direction == direction and c.start.price == (D('150') if direction == 'LONG' else D('150'))]
    return matches[-1] if matches else observer.cases[-1]


class GoldenCases(unittest.TestCase):
    def test_golden_long(self):
        o = run(load_candles(BASE / 'fixtures/hyp009-golden-long.csv'))
        c = o.cases[0]
        self.assertEqual((c.status, c.direction, c.intervals, c.impulse_pips, c.pullback_pct), ('VALID_SAMPLE', 'LONG', 2, D('20'), D('30')))
        self.assertEqual((c.entry, c.stop, c.target, c.exit_reason, c.result_r), (D('150.21'), D('150.13'), D('150.33'), 'TP', D('1.4875')))

    def test_golden_long_is_independent_of_absolute_price(self):
        original = load_candles(BASE / 'fixtures/hyp009-golden-long.csv')
        shift = D('0.37')
        shifted = [replace(c, open=c.open + shift, high=c.high + shift,
                           low=c.low + shift, close=c.close + shift) for c in original]
        a, b = run(original).cases[0], run(shifted).cases[0]
        self.assertEqual((a.status, a.impulse_pips, a.intervals, a.pullback_pct,
                          a.stop_pips, a.exit_reason, a.gross_result_r, a.result_r),
                         (b.status, b.impulse_pips, b.intervals, b.pullback_pct,
                          b.stop_pips, b.exit_reason, b.gross_result_r, b.result_r))
        self.assertEqual((b.entry, b.stop, b.target),
                         (a.entry + shift, a.stop + shift, a.target + shift))

    def test_golden_too_long(self):
        o = run(load_candles(BASE / 'fixtures/hyp009-golden-too-long.csv'))
        self.assertEqual((o.cases[0].intervals, o.cases[0].reasons), (9, ['IMPULSE_TOO_LONG']))

    def test_golden_no_trigger(self):
        o = run(load_candles(BASE / 'fixtures/hyp009-golden-no-trigger.csv'))
        self.assertEqual(o.cases[0].reasons, ['NO_TRIGGER'])


class FrozenBoundaries(unittest.TestCase):
    def test_long_and_short_symmetry(self):
        long = run(make_long())
        short = run(mirror(make_long()))
        a, b = long.cases[0], short.cases[0]
        self.assertEqual((a.status, b.status, b.direction), ('VALID_SAMPLE', 'VALID_SAMPLE', 'SHORT'))
        self.assertEqual((a.stop_pips, a.result_r, a.pullback_pct), (b.stop_pips, b.result_r, b.pullback_pct))
        self.assertEqual(b.target, b.entry - D('1.5') * (b.stop - b.entry))

    def test_impulse_10_pips_inclusive(self):
        c = run(make_long(width='10', pullback_pct='30')).cases[0]
        self.assertEqual((c.impulse_pips, c.status), (D('10'), 'VALID_SAMPLE'))

    def test_impulse_35_pips_inclusive(self):
        c = run(make_long(width='35', pullback_pct='30')).cases[0]
        self.assertEqual((c.impulse_pips, c.status), (D('35'), 'VALID_SAMPLE'))

    def test_impulse_above_35_rejected(self):
        c = run(make_long(width='35.01')).cases[0]
        self.assertIn('IMPULSE_TOO_LARGE', c.reasons)
        self.assertIsNone(c.trigger_index)

    def test_interval_2_inclusive(self):
        c = run(make_long(intervals=2)).cases[0]
        self.assertEqual((c.intervals, c.status), (2, 'VALID_SAMPLE'))

    def test_interval_8_inclusive(self):
        c = run(make_long(intervals=8)).cases[0]
        self.assertEqual((c.intervals, c.status), (8, 'VALID_SAMPLE'))

    def test_interval_9_rejected(self):
        c = run(make_long(intervals=9)).cases[0]
        self.assertIn('IMPULSE_TOO_LONG', c.reasons)

    def test_pullback_20_percent_inclusive(self):
        c = run(make_long(width='10', pullback_pct='20')).cases[0]
        self.assertEqual((c.pullback_pct, c.status), (D('20'), 'VALID_SAMPLE'))

    def test_pullback_70_percent_inclusive(self):
        c = run(make_long(width='20', pullback_pct='70')).cases[0]
        self.assertEqual((c.pullback_pct, c.status), (D('70'), 'VALID_SAMPLE'))

    def test_pullback_above_70_invalid(self):
        c = run(make_long(width='20', pullback_pct='70.01')).cases[0]
        self.assertIn('PULLBACK_TOO_DEEP', c.reasons)
        self.assertIsNone(c.trigger_index)

    def test_trigger_body_40_percent_inclusive(self):
        data = make_long()
        c = data[-2]
        data[-2] = replace(c, high=c.close + D('0.01'), low=c.close - D('0.09'))
        result = run(data).cases[0]
        self.assertEqual(result.body_ratio, D('0.40'))
        self.assertEqual(result.status, 'VALID_SAMPLE')

    def test_sl_4_pips_inclusive(self):
        c = run(make_long(width='10', pullback_pct='20')).cases[0]
        self.assertEqual((c.stop_pips, c.status), (D('4'), 'VALID_SAMPLE'))

    def test_sl_20_pips_inclusive(self):
        c = run(make_long(width='35', pullback_pips='18')).cases[0]
        self.assertEqual((c.stop_pips, c.status), (D('20'), 'VALID_SAMPLE'))

    def test_session_0800_allowed(self):
        base = datetime.fromisoformat('2026-09-16T07:35:00+09:00')
        c = run(make_long(base=base)).cases[0]
        self.assertEqual((c.status, c.trigger_index is not None), ('VALID_SAMPLE', True))
        self.assertEqual(c.entry, D('150.21'))

    def test_session_0055_allowed(self):
        base = datetime.fromisoformat('2026-09-17T00:30:00+09:00')
        c = run(make_long(base=base)).cases[0]
        self.assertEqual((c.status, c.trigger_index is not None), ('VALID_SAMPLE', True))

    def test_session_0100_excluded(self):
        base = datetime.fromisoformat('2026-09-17T00:35:00+09:00')
        c = run(make_long(base=base)).cases[0]
        self.assertIn('OUT_OF_SESSION', c.reasons)
        self.assertIsNone(c.trigger_index)

    def test_midnight_continuity(self):
        base = datetime.fromisoformat('2026-09-16T23:45:00+09:00')
        c = run(make_long(base=base)).cases[0]
        self.assertEqual((c.status, c.trigger_index is not None), ('VALID_SAMPLE', True))

    def test_same_bar_tp_sl_uses_sl_and_no_exit_high_for_mfe(self):
        c = run(make_long(exit_mode='BOTH')).cases[0]
        self.assertEqual((c.exit_reason, c.exit_price, c.mfe_pips), ('SL', c.stop, D('0')))

    def test_12_bar_time_stop(self):
        data = make_long(exit_mode=None)
        entry = data[-1].close
        for n in range(1, 13):
            time = data[-1].time + timedelta(minutes=5)
            data.append(candle(time, entry, entry + D('0.02'), entry - D('0.01'), entry + (D('0.01') if n == 12 else D('0'))))
        c = run(data).cases[0]
        self.assertEqual((c.exit_reason, c.exit_index - c.trigger_index, c.exit_price), ('TIME_STOP', 12, entry + D('0.01')))

    def test_uses_first_trigger_only(self):
        data = make_long(exit_mode=None)
        first = run(data).cases[0]
        next_time = data[-1].time + timedelta(minutes=5)
        data.append(candle(next_time, first.entry, first.target + D('0.01'), first.entry, first.target))
        o = run(data)
        self.assertEqual(sum(c.key == first.key for c in o.cases), 1)

    def test_latest_start_wins_for_same_endpoint(self):
        base = datetime.fromisoformat('2026-09-16T09:00:00+09:00')
        values = [('150.04','150.06','150.02','150.04'), ('150.04','150.05','150.00','150.03'),
                  ('150.03','150.07','150.01','150.06'), ('150.06','150.08','150.04','150.07'),
                  ('150.07','150.07','150.07','150.07'), ('150.07','150.09','150.05','150.08'),
                  ('150.08','150.11','150.06','150.10'), ('150.10','150.20','150.10','150.18'),
                  ('150.18','150.19','150.12','150.16')]
        data = [candle(base + timedelta(minutes=5*i), *item) for i, item in enumerate(values)]
        o = run(data)
        selected = [c for c in o.cases if c.end.index == 7 and c.status == 'WATCH']
        self.assertEqual((len(selected), selected[0].start.index, selected[0].impulse_pips), (1, 5, D('15')))

    def test_pullback_stays_shallow_until_sixth_bar(self):
        data = make_long(exit_mode=None)
        endpoint = data[3].high
        p = endpoint - D('0.02')
        data[4] = candle(data[4].time, endpoint - D('0.015'), endpoint - D('0.01'), p, endpoint - D('0.015'))
        data[5] = candle(data[5].time, endpoint - D('0.015'), endpoint - D('0.01'), p, endpoint - D('0.015'))
        for _ in range(4):
            time = data[-1].time + timedelta(minutes=5)
            data.append(candle(time, endpoint - D('0.015'), endpoint - D('0.01'), p, endpoint - D('0.015')))
        c = run(data).cases[0]
        self.assertEqual((c.pullback_pct, c.reasons), (D('10'), ['PULLBACK_TOO_SHALLOW']))

    def test_end_swing_not_known_early(self):
        data = make_long()
        before = run(data[:4])
        confirmed = run(data[:5])
        self.assertFalse(any(s.kind == 'HIGH' and s.index == 3 for s in before.swings))
        self.assertTrue(any(s.kind == 'HIGH' and s.index == 3 and s.confirmed_at == data[4].time for s in confirmed.swings))
        self.assertIsNone(confirmed.cases[0].trigger_index)

    def test_forming_bar_cannot_trigger(self):
        data = make_long()
        o = Observer(forward_observed_at=data[0].time.isoformat())
        for c in data[:5]:
            o.feed(c)
        o.feed(replace(data[5], closed=False))
        self.assertIsNone(o.cases[0].trigger_index)
        self.assertEqual(len(o.candles), 5)
        o.feed(data[5])
        self.assertIsNotNone(o.cases[0].trigger_index)

    def test_future_after_exit_does_not_change_mfe_mae(self):
        data = make_long()
        first = run(data).cases[0]
        last = data[-1]
        data.append(candle(last.time + timedelta(minutes=5), last.close, last.close + D('1'), last.close - D('1'), last.close))
        later = run(data).cases[0]
        self.assertEqual((later.mfe_pips, later.mae_pips), (first.mfe_pips, first.mae_pips))


class InputAndRecords(unittest.TestCase):
    def test_timezone_to_jst(self):
        self.assertEqual(stamp('2026-09-16T00:25:00+00:00').isoformat(), '2026-09-16T09:25:00+09:00')

    def test_duplicate_timestamp_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.csv'
            lines = (BASE / 'fixtures/hyp009-golden-long.csv').read_text(encoding='utf-8').splitlines()
            path.write_text('\n'.join(lines + [lines[1]]) + '\n', encoding='utf-8')
            with self.assertRaises(InputError):
                load_candles(path)

    def test_invalid_ohlc_and_nan_fail(self):
        base = {'timestamp': '2026-09-16T09:00:00+09:00', 'open': '150', 'high': '149', 'low': '148', 'close': '150'}
        with self.assertRaises(InputError):
            Candle.from_row(base)
        base['high'] = 'NaN'
        with self.assertRaises(InputError):
            Candle.from_row(base)

    def test_gap_marks_active_insufficient_without_fill(self):
        data = make_long()
        data[5] = replace(data[5], time=data[5].time + timedelta(minutes=5))
        data[6] = replace(data[6], time=data[6].time + timedelta(minutes=5))
        o = run(data)
        self.assertTrue(o.errors)
        self.assertIn('AMBIGUOUS_DATA', o.cases[0].reasons)
        self.assertEqual(o.cases[0].status, 'INSUFFICIENT_DATA')

    def test_spread_unknown_is_pending(self):
        data = make_long()
        data[5] = replace(data[5], spread=None)
        o = run(data)
        c = o.cases[0]
        f = prepare_rows(o)[0][2][0]
        self.assertIn('spread_unknown', c.reasons)
        self.assertEqual(f['valid'], 'PENDING')

    def test_event_unknown_is_pending(self):
        data = make_long()
        data[5] = replace(data[5], event_blocked=None, event_tag='UNKNOWN')
        o = run(data)
        f = prepare_rows(o)[0][2][0]
        self.assertIn('event_time_unknown', o.cases[0].reasons)
        self.assertEqual(f['valid'], 'PENDING')

    def test_missing_cost_keeps_net_r_unknown_and_formal_pending(self):
        data = make_long()
        data[5] = replace(data[5], roundtrip_cost=None)
        o = run(data)
        c = o.cases[0]
        row = prepare_rows(o)[0][2][0]
        self.assertEqual(c.gross_result_r, D('1.5'))
        self.assertIsNone(c.result_r)
        self.assertEqual((row['valid'], row['result_r']), ('PENDING', 'UNKNOWN'))
        self.assertIn('cost_unknown', row['invalid_reason'])

    def test_unknown_price_series_keeps_formal_pending(self):
        data = make_long()
        o = Observer(forward_observed_at=data[0].time.isoformat())
        for item in data:
            o.feed(item)
        o.finish()
        row = prepare_rows(o)[0][2][0]
        self.assertEqual((row['valid'], row['result_r']), ('PENDING', 'UNKNOWN'))
        self.assertIn('price_series_unknown', row['invalid_reason'])

    def test_spread_above_limit_is_rejected(self):
        data = make_long()
        data[5] = replace(data[5], spread=D('0.51'))
        o = run(data)
        self.assertEqual(o.cases[0].status, 'REJECTED_OPPORTUNITY')
        self.assertIn('SPREAD', o.cases[0].reasons)
        self.assertEqual(prepare_rows(o)[0][2][0]['valid'], 'FALSE')

    def test_event_blocked_is_rejected(self):
        data = make_long()
        data[5] = replace(data[5], event_blocked=True, event_tag='event')
        c = run(data).cases[0]
        self.assertIn('EVENT_WINDOW', c.reasons)
        self.assertEqual(c.status, 'REJECTED_OPPORTUNITY')

    def test_stop_just_below_four_is_rejected(self):
        data = make_long(width='10', pullback_pct='20')
        trigger = data[5]
        data[5] = replace(trigger, open=D('150.08'), high=D('150.11'), low=D('150.075'), close=D('150.109'))
        c = run(data).cases[0]
        self.assertEqual(c.stop_pips, D('3.9'))
        self.assertIn('STOP_TOO_TIGHT', c.reasons)

    def test_undefined_stop_keeps_r_na(self):
        o = run(load_candles(BASE / 'fixtures/hyp009-golden-too-long.csv'))
        _, _, opportunities = prepare_rows(o)[1]
        self.assertEqual((opportunities[0]['r_status'], opportunities[0]['mfe_r'], opportunities[0]['reached_1r']), ('UNDEFINED', 'NA', 'NA'))

    def test_rejected_trigger_has_defined_observation_r(self):
        data = make_long(width='35', pullback_pips='19')
        o = run(data)
        row = prepare_rows(o)[1][2][0]
        self.assertEqual((o.cases[0].reasons, row['r_status'], row['hypothetical_stop_distance']), (['STOP_TOO_WIDE'], 'DEFINED', '21'))

    def test_rejected_observation_adverse_first(self):
        data = make_long(width='35', pullback_pips='19', exit_mode=None)
        entry = data[-1].close
        time = data[-1].time
        data.append(candle(time + timedelta(minutes=5), entry, entry + D('0.02'), entry - D('0.22'), entry - D('0.10')))
        data.append(candle(time + timedelta(minutes=10), entry - D('0.10'), entry + D('0.32'), entry - D('0.11'), entry + D('0.30')))
        for n in range(3, 13):
            data.append(candle(time + timedelta(minutes=5*n), entry, entry + D('0.02'), entry - D('0.01'), entry))
        o = run(data)
        c = next(c for c in o.cases if 'STOP_TOO_WIDE' in c.reasons)
        row = opportunity_row(o, c, prepare_rows(o)[1][0])
        self.assertEqual((row['observation_bars'], row['outcome_status'], row['reached_1_5r'], row['first_1_5r']), ('12', 'COMPLETE', 'TRUE', 'ADVERSE_FIRST'))

    def test_gap_halts_rejected_observation_without_filling(self):
        data = make_long(width='35', pullback_pips='19', exit_mode=None)
        reference_time = data[-1].time
        data.append(candle(reference_time + timedelta(minutes=5), '150.36', '150.38', '150.35', '150.36'))
        for n in range(3, 16):
            data.append(candle(reference_time + timedelta(minutes=5*n), '150.36', '150.38', '150.35', '150.36'))
        o = run(data)
        c = next(c for c in o.cases if 'STOP_TOO_WIDE' in c.reasons)
        row = opportunity_row(o, c, prepare_rows(o)[1][0])
        self.assertEqual((row['observation_bars'], row['outcome_status']), ('1', 'PARTIAL'))
        self.assertIn('missing_observation_bars', c.reasons)

    def test_retrospective_data_is_not_formal_forward(self):
        o = run(make_long(), forward=False)
        f = prepare_rows(o)[0][2][0]
        self.assertEqual(f['valid'], 'PENDING')
        self.assertIn('forward_provenance_unknown', f['invalid_reason'])

    def test_dry_run_keeps_target_csv_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            f, p = self._targets(directory)
            before = f.read_bytes(), p.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                main(['--input', str(BASE / 'fixtures/hyp009-golden-long.csv'), '--dry-run', '--forward-observed-at', '2026-09-16T09:00:00+09:00', '--formal-csv', str(f), '--opportunities-csv', str(p)])
            self.assertEqual((f.read_bytes(), p.read_bytes()), before)

    def test_double_write_keeps_one_case_id(self):
        with tempfile.TemporaryDirectory() as directory:
            f, p = self._targets(directory)
            o = run(load_candles(BASE / 'fixtures/hyp009-golden-long.csv'))
            write_records(o, f, p)
            first_bytes = f.read_bytes(), p.read_bytes()
            write_records(o, f, p)
            self.assertEqual((f.read_bytes(), p.read_bytes()), first_bytes)
            with f.open(encoding='utf-8', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual((len(rows), rows[0]['case_id']), (1, 'HYP009-v01-0001'))

    def test_double_write_keeps_one_rejection_id(self):
        with tempfile.TemporaryDirectory() as directory:
            f, p = self._targets(directory)
            with p.open(encoding='utf-8', newline='') as handle:
                baseline = list(csv.DictReader(handle))
            o = run(load_candles(BASE / 'fixtures/hyp009-golden-no-trigger.csv'))
            write_records(o, f, p)
            first_bytes = f.read_bytes(), p.read_bytes()
            write_records(o, f, p)
            self.assertEqual((f.read_bytes(), p.read_bytes()), first_bytes)
            with p.open(encoding='utf-8', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), len(baseline) + 1)
            self.assertEqual(len({r['opportunity_id'] for r in rows}), len(rows))

    def test_open_auto_row_updates_to_complete_without_new_id(self):
        with tempfile.TemporaryDirectory() as directory:
            f, p = self._targets(directory)
            data = make_long()
            write_records(run(data[:6]), f, p)
            with f.open(encoding='utf-8', newline='') as handle:
                open_row = list(csv.DictReader(handle))[0]
            self.assertEqual(open_row['valid'], 'PENDING')
            write_records(run(data), f, p)
            with f.open(encoding='utf-8', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual((len(rows), rows[0]['case_id'], rows[0]['valid']), (1, open_row['case_id'], 'TRUE'))

    def test_completed_auto_row_cannot_be_downgraded_by_short_input(self):
        with tempfile.TemporaryDirectory() as directory:
            f, p = self._targets(directory)
            data = make_long()
            write_records(run(data), f, p)
            before = f.read_bytes(), p.read_bytes()
            with self.assertRaises(InputError):
                write_records(run(data[:6]), f, p)
            self.assertEqual((f.read_bytes(), p.read_bytes()), before)

    def test_written_rejection_does_not_enter_formal_statistics(self):
        with tempfile.TemporaryDirectory() as directory:
            f, p = self._targets(directory)
            baseline = summarize(read_csv(f, 'case_id'), read_csv(p, 'opportunity_id'))
            data = make_long()
            data[5] = replace(data[5], spread=D('0.51'))
            write_records(run(data), f, p)
            summary = summarize(read_csv(f, 'case_id'), read_csv(p, 'opportunity_id'))
            self.assertEqual(summary['HYP-009 v0.1']['Valid completed samples'], 0)
            self.assertEqual(summary['HYP-009 v0.1']['Rejected opportunities'], baseline['HYP-009 v0.1']['Rejected opportunities'] + 1)
            self.assertEqual(summary['Audit errors'], [])

    @staticmethod
    def _targets(directory):
        f, p = Path(directory) / 'formal.csv', Path(directory) / 'opportunities.csv'
        f.write_bytes((BASE / 'HYP-009-v0.1-tests.csv').read_bytes())
        p.write_bytes((BASE / 'HYP-009-rejected-opportunities.csv').read_bytes())
        return f, p


if __name__ == '__main__':
    unittest.main()
