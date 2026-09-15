"""HYP-009 v0.1 virtual observation engine; no broker or order integration."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

PIP = Decimal('0.01')
JST = timezone(timedelta(hours=9))
FIXED_AT = datetime.fromisoformat('2026-09-14T13:31:09+09:00')
BASE = Path(__file__).resolve().parent
FORMAL_PATH = BASE / 'HYP-009-v0.1-tests.csv'
OPPORTUNITY_PATH = BASE / 'HYP-009-rejected-opportunities.csv'
FORMAL_SCHEMA = tuple('case_id,datetime_jst,direction,session,event_tag,impulse_start_time,impulse_end_time,impulse_start_price,impulse_end_price,impulse_pips,impulse_bars,pullback_bars,pullback_extreme,pullback_pct,trigger_open,trigger_high,trigger_low,trigger_close,trigger_body_ratio,entry,stop,stop_pips,target,exit_time,exit,result_r,mfe_r,mae_r,spread_pips,account_balance,risk_pct,demo_ordered,demo_quantity,valid,invalid_reason,screenshot,notes'.split(','))
OPPORTUNITY_SCHEMA = tuple('opportunity_id,parent_case_id,classification,evidence_status,direction,rejection_reason,observed_at,assessed_at,source,impulse_start_time,impulse_end_time,impulse_start_price,impulse_end_price,impulse_pips,impulse_bars,reference_time,reference_price,reference_basis,hypothetical_stop,hypothetical_stop_distance,r_status,observation_end,observation_bars,outcome_status,mfe_pips,mae_pips,mfe_r,mae_r,reached_1r,reached_1_5r,first_1r,first_1_5r,notes'.split(','))


class InputError(ValueError):
    pass


def dec(value, label):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise InputError(f'{label}: missing or invalid number') from None
    if not result.is_finite():
        raise InputError(f'{label}: NaN/infinity is not allowed')
    return result


def aware_jst(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        raise InputError(f'timestamp: invalid ISO 8601 value {value!r}') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError('timestamp must include a timezone offset')
    return parsed.astimezone(JST)


def stamp(value):
    parsed = aware_jst(value)
    if parsed.second or parsed.microsecond or parsed.minute % 5:
        raise InputError('timestamp must be an exact 5-minute candle close')
    return parsed


def iso(value):
    return value.isoformat(timespec='seconds') if value else 'UNKNOWN'


def fmt(value):
    if value is None:
        return 'UNKNOWN'
    if isinstance(value, Decimal):
        return format(value.normalize(), 'f')
    return str(value)


def optional_dec(value, label):
    return None if value is None or str(value).strip() in {'', 'UNKNOWN'} else dec(value, label)


def optional_bool(value, label):
    if value is None or str(value).strip() in {'', 'UNKNOWN'}:
        return None
    normalized = str(value).strip().upper()
    if normalized in {'TRUE', '1'}:
        return True
    if normalized in {'FALSE', '0'}:
        return False
    raise InputError(f'{label}: use TRUE or FALSE')


@dataclass(frozen=True)
class Candle:
    time: datetime  # close time, never opening time
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    spread: Decimal | None = None
    event_blocked: bool | None = None
    event_tag: str = 'UNKNOWN'
    roundtrip_cost: Decimal | None = None
    closed: bool = True

    @classmethod
    def from_row(cls, row):
        for key in ('timestamp', 'open', 'high', 'low', 'close'):
            if key not in row or row[key] is None or not str(row[key]).strip():
                raise InputError(f'{key}: required input missing')
        prices = {k: dec(row[k], k) for k in ('open', 'high', 'low', 'close')}
        if any(value <= 0 for value in prices.values()):
            raise InputError('USDJPY OHLC prices must be positive')
        if prices['high'] < prices['low'] or prices['high'] < max(prices['open'], prices['close']) or prices['low'] > min(prices['open'], prices['close']):
            raise InputError(f"{row['timestamp']}: inconsistent OHLC")
        spread = optional_dec(row.get('spread_pips', row.get('spread')), 'spread_pips')
        cost = optional_dec(row.get('roundtrip_cost_pips'), 'roundtrip_cost_pips')
        if spread is not None and spread < 0 or cost is not None and cost < 0:
            raise InputError('spread/cost cannot be negative')
        event_tag = str(row.get('event_tag') or 'UNKNOWN').strip().lower()
        if event_tag not in {'event', 'non-event', 'unknown'}:
            raise InputError('event_tag: use event, non-event, or UNKNOWN')
        if 'symbol' in row and row['symbol'] not in {'', 'USDJPY'} or 'timeframe' in row and row['timeframe'] not in {'', '5m', 'M5'}:
            raise InputError('input must be USDJPY 5-minute candles')
        closed = optional_bool(row.get('closed', 'TRUE'), 'closed')
        if closed is None:
            raise InputError('closed: unknown confirmation state')
        return cls(stamp(row['timestamp']), **prices, spread=spread, event_blocked=optional_bool(row.get('event_blocked'), 'event_blocked'), event_tag=event_tag if event_tag != 'unknown' else 'UNKNOWN', roundtrip_cost=cost, closed=closed)


def load_candles(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {'timestamp', 'open', 'high', 'low', 'close'} <= set(reader.fieldnames):
            raise InputError('CSV requires timestamp,open,high,low,close headers')
        rows = list(reader)
    if not rows:
        raise InputError('CSV has no candles')
    if any(None in row or None in row.values() for row in rows):
        raise InputError('CSV row has a column mismatch')
    candles = [Candle.from_row(row) for row in rows]
    candles.sort(key=lambda c: c.time)
    for previous, current in zip(candles, candles[1:]):
        delta = current.time - previous.time
        if delta == timedelta(0):
            raise InputError(f'duplicate timestamp/candle: {iso(current.time)}')
        if delta < timedelta(minutes=5):
            raise InputError(f'non-5-minute spacing: {iso(current.time)}')
    if any(not candle.closed for candle in candles[:-1]):
        raise InputError('only the newest candle may be forming')
    return candles


@dataclass(frozen=True)
class Swing:
    kind: str
    index: int
    time: datetime
    confirmed_at: datetime
    price: Decimal


@dataclass
class Case:
    key: str
    direction: str
    start: Swing
    end: Swing
    impulse_pips: Decimal
    intervals: int
    status: str = 'WATCH'
    reasons: list[str] = field(default_factory=list)
    trigger_index: int | None = None
    pullback_bars: int | None = None
    pullback_extreme: Decimal | None = None
    pullback_pct: Decimal | None = None
    body_ratio: Decimal | None = None
    entry: Decimal | None = None
    stop: Decimal | None = None
    target: Decimal | None = None
    stop_pips: Decimal | None = None
    exit_index: int | None = None
    exit_price: Decimal | None = None
    exit_reason: str | None = None
    gross_result_r: Decimal | None = None
    result_r: Decimal | None = None
    mfe_pips: Decimal | None = None
    mae_pips: Decimal | None = None
    reference_index: int | None = None
    reference_basis: str | None = None
    observation: list[int] = field(default_factory=list)
    observation_halted: bool = False
    formal_id: str | None = None
    opportunity_id: str | None = None


def direction_sign(direction):
    return Decimal(1) if direction == 'LONG' else Decimal(-1)


def session_allowed(time):
    minute = time.hour * 60 + time.minute
    return minute >= 8 * 60 or minute < 60


def session_label(time):
    return f'{time.hour:02d}:00-{time.hour:02d}:59'


class Observer:
    def __init__(self, *, forward_observed_at=None, source='UNKNOWN', price_series='UNKNOWN'):
        self.candles: list[Candle] = []
        self.swings: list[Swing] = []
        self.cases: list[Case] = []
        self.active: Case | None = None
        self.positions: list[Case] = []
        self.observations: list[Case] = []
        self.trace: list[dict] = []
        self.errors: list[str] = []
        self.endpoints_evaluated = 0
        self.impulse_candidates = 0
        self.confirmed_count = 0
        self.assessed_at = datetime.now(JST)
        self.forward_observed_at = aware_jst(forward_observed_at) if forward_observed_at else None
        self.source = source
        self.price_series = price_series

    def feed(self, candle: Candle):
        if not candle.closed:
            self.trace.append({'at': iso(candle.time), 'state': 'WATCH', 'reason': 'forming_bar'})
            return 'WATCH'
        if self.candles:
            delta = candle.time - self.candles[-1].time
            if delta <= timedelta(0):
                raise InputError('non-increasing/duplicate candle timestamp')
            if delta != timedelta(minutes=5):
                self.errors.append(f'gap: {iso(self.candles[-1].time)} -> {iso(candle.time)}; no interpolation')
                for rejected in self.observations:
                    if len(rejected.observation) < 12:
                        rejected.observation_halted = True
                        if 'missing_observation_bars' not in rejected.reasons:
                            rejected.reasons.append('missing_observation_bars')
                if self.active:
                    self._reject(self.active, ['AMBIGUOUS_DATA'], len(self.candles) - 1, classification='INSUFFICIENT_DATA')
                    self.active = None
                for position in self.positions:
                    position.reasons.append('missing_exit_bars')
                    position.status = 'INSUFFICIENT_DATA'
                self.positions.clear()
                self.swings.clear()
        self.candles.append(candle)
        now = len(self.candles) - 1
        for position in list(self.positions):
            self._advance_exit(position, now)
        for rejected in self.observations:
            if rejected.reference_index is not None and not rejected.observation_halted and now > rejected.reference_index and len(rejected.observation) < 12:
                if now - rejected.reference_index == len(rejected.observation) + 1:
                    rejected.observation.append(now)
        confirmed = self._confirm_swing(now)
        active_before = self.active
        if self.active:
            self._advance_setup(self.active, now)
        # A swing confirmed inside the just-finished pullback belongs to the
        # already selected structure. It cannot spawn a fresh scored case.
        just_finished = active_before is not None and self.active is None
        if not self.active and confirmed and not just_finished:
            self._select_endpoint(confirmed, now)
            if self.active:
                self._advance_setup(self.active, now)
        return 'WATCH' if self.active else 'NO SETUP'

    def _confirm_swing(self, now):
        if now < 2:
            return []
        left, center, right = self.candles[now - 2:now + 1]
        if center.time - left.time != timedelta(minutes=5) or right.time - center.time != timedelta(minutes=5):
            return []
        found = []
        if center.high > left.high and center.high > right.high:
            found.append(Swing('HIGH', now - 1, center.time, right.time, center.high))
        if center.low < left.low and center.low < right.low:
            found.append(Swing('LOW', now - 1, center.time, right.time, center.low))
        self.swings.extend(found)
        self.confirmed_count += len(found)
        self.trace.extend({'at': iso(right.time), 'state': 'CONFIRMED_SWING', 'swing_at': iso(s.time), 'kind': s.kind} for s in found)
        return found

    def _candidate(self, start, end):
        direction = 'LONG' if end.kind == 'HIGH' else 'SHORT'
        width = (end.price - start.price) / PIP if direction == 'LONG' else (start.price - end.price) / PIP
        intervals = int((end.time - start.time) / timedelta(minutes=5))
        key = f'USDJPY-M5|{direction}|{iso(start.time)}|{iso(end.time)}'
        return Case(key, direction, start, end, width, intervals)

    def _select_endpoint(self, endpoints, now):
        possible = []
        fallback = []
        for end in endpoints:
            latest_opposite = None
            eligible = []
            for start in reversed(self.swings):
                if start.index >= end.index or start.kind == end.kind:
                    continue
                if latest_opposite is None:
                    latest_opposite = start
                candidate = self._candidate(start, end)
                if candidate.intervals > 8:
                    break  # older opposite swings cannot become eligible
                if 10 <= candidate.impulse_pips <= 35 and 2 <= candidate.intervals <= 8:
                    eligible.append(candidate)
            if latest_opposite is None:
                continue
            self.endpoints_evaluated += 1
            self.impulse_candidates += len(eligible)
            if eligible:
                possible.append(max(eligible, key=lambda c: c.start.index))
            else:
                fallback.append(self._candidate(latest_opposite, end))
        if possible:
            latest_start = max(c.start.index for c in possible)
            top = [c for c in possible if c.start.index == latest_start]
            if len(top) > 1:
                for c in top:
                    self.cases.append(c)
                    self._reject(c, ['AMBIGUOUS_DATA'], now, classification='INSUFFICIENT_DATA')
                return
            choice = top[0]
            self.cases.append(choice)
            self.active = choice
            self.trace.append({'at': iso(self.candles[now].time), 'state': 'SELECTED', 'key': choice.key, 'start_confirmed_at': iso(choice.start.confirmed_at), 'end_confirmed_at': iso(choice.end.confirmed_at)})
            return
        if fallback:
            for candidate in fallback:
                reasons = []
                if candidate.impulse_pips > 35:
                    reasons.append('IMPULSE_TOO_LARGE')
                if candidate.impulse_pips < 10:
                    reasons.append('IMPULSE_TOO_SMALL')
                if candidate.intervals > 8:
                    reasons.append('IMPULSE_TOO_LONG')
                if candidate.intervals < 2:
                    reasons.append('IMPULSE_TOO_SHORT')
                if not reasons:
                    continue
                self.cases.append(candidate)
                self._reject(candidate, reasons, now)

    def _pullback(self, case, start, end):
        section = self.candles[start:end + 1]
        p = min(c.low for c in section) if case.direction == 'LONG' else max(c.high for c in section)
        pct = (case.end.price - p) / (case.end.price - case.start.price) * 100 if case.direction == 'LONG' else (p - case.end.price) / (case.start.price - case.end.price) * 100
        return p, pct

    def _advance_setup(self, case, now):
        k = now - case.end.index
        if k < 1:
            return
        if self.candles[now].time.hour == 1 and self.candles[now].time.minute == 0:
            self._reject(case, ['OUT_OF_SESSION'], now)
            self.active = None
            return
        if k == 1:
            _, pct = self._pullback(case, now, now)
            if pct > 70:
                self._reject(case, ['PULLBACK_TOO_DEEP'], now)
                self.active = None
            return
        if k > 6:
            self._reject(case, ['NO_TRIGGER'], now)
            self.active = None
            return
        p, pct = self._pullback(case, case.end.index + 1, now - 1)
        case.pullback_bars, case.pullback_extreme, case.pullback_pct = k - 1, p, pct
        _, with_current = self._pullback(case, case.end.index + 1, now)
        if pct > 70 or with_current > 70:
            self._reject(case, ['PULLBACK_TOO_DEEP'], now)
            self.active = None
            return
        candle, previous = self.candles[now], self.candles[now - 1]
        ratio = abs(candle.close - candle.open) / (candle.high - candle.low) if candle.high != candle.low else Decimal(0)
        case.body_ratio = ratio
        trigger = candle.close > candle.open and candle.close > previous.high if case.direction == 'LONG' else candle.close < candle.open and candle.close < previous.low
        if 20 <= pct <= 70 and trigger and ratio >= Decimal('0.40'):
            self._trigger(case, now)
            self.active = None
            return
        if k == 6:
            self._reject(case, ['PULLBACK_TOO_SHALLOW' if pct < 20 and with_current < 20 else 'NO_TRIGGER'], now)
            self.active = None

    def _trigger(self, case, now):
        candle = self.candles[now]
        case.trigger_index = now
        case.entry = candle.close
        case.stop = case.pullback_extreme - PIP if case.direction == 'LONG' else case.pullback_extreme + PIP
        signed_distance = (case.entry - case.stop) * direction_sign(case.direction)
        case.stop_pips = signed_distance / PIP
        case.target = case.entry + direction_sign(case.direction) * signed_distance * Decimal('1.5') if signed_distance > 0 else None
        reasons = []
        if signed_distance <= 0:
            reasons.append('INVALID_STOP_SIDE')
        elif case.stop_pips < 4:
            reasons.append('STOP_TOO_TIGHT')
        elif case.stop_pips > 20:
            reasons.append('STOP_TOO_WIDE')
        if candle.spread is not None and candle.spread > Decimal('0.5'):
            reasons.append('SPREAD')
        if candle.event_blocked:
            reasons.append('EVENT_WINDOW')
        if not session_allowed(candle.time):
            reasons.append('OUT_OF_SESSION')
        if reasons:
            self._reject(case, reasons, now)
        else:
            missing = []
            if candle.spread is None:
                missing.append('spread_unknown')
            if candle.event_blocked is None or candle.event_tag == 'UNKNOWN':
                missing.append('event_time_unknown')
            if candle.roundtrip_cost is None:
                missing.append('cost_unknown')
            if self.price_series == 'UNKNOWN':
                missing.append('price_series_unknown')
            if self.forward_observed_at is None or self.forward_observed_at > case.start.time or case.start.time < FIXED_AT:
                missing.append('forward_provenance_unknown')
            case.reasons = missing
            case.status = 'INSUFFICIENT_DATA' if missing else 'VALID_SETUP'
            if missing:
                self._reject(case, ['AMBIGUOUS_DATA'], now, classification='INSUFFICIENT_DATA')
        if signed_distance > 0:
            self.positions.append(case)
        self.trace.append({'at': iso(candle.time), 'state': case.status, 'key': case.key, 'trigger': iso(candle.time), 'entry': fmt(case.entry), 'stop': fmt(case.stop), 'target': fmt(case.target), 'reasons': case.reasons})

    def _reject(self, case, reasons, reference_index, classification='REJECTED_OPPORTUNITY'):
        case.status = classification
        case.reasons = sorted(set(case.reasons + reasons))
        case.reference_index = reference_index
        case.reference_basis = 'TRIGGER_CLOSE' if case.trigger_index is not None else 'REJECTION_CLOSE'
        if case not in self.observations:
            self.observations.append(case)
        self.trace.append({'at': iso(self.candles[reference_index].time), 'state': classification, 'key': case.key, 'reasons': case.reasons})

    def _advance_exit(self, case, now):
        bars = now - case.trigger_index
        if bars < 1 or case.exit_index is not None:
            return
        candle = self.candles[now]
        sign = direction_sign(case.direction)
        sl_gap = sign * (candle.open - case.stop) < 0
        tp_gap = sign * (candle.open - case.target) > 0
        sl_hit = candle.low <= case.stop if case.direction == 'LONG' else candle.high >= case.stop
        tp_hit = candle.high >= case.target if case.direction == 'LONG' else candle.low <= case.target
        if sl_gap:
            exit_price, reason = candle.open, 'GAP_SL'
        elif tp_gap:
            exit_price, reason = case.target, 'TP'
        elif sl_hit:
            exit_price, reason = case.stop, 'SL'
        elif tp_hit:
            exit_price, reason = case.target, 'TP'
        elif bars == 12:
            exit_price, reason = candle.close, 'TIME_STOP'
        else:
            exit_price, reason = None, None
        # Before exit, only completed candles contribute full OHLC; exit candle
        # contributes its open and actual virtual exit, never its later extremes.
        if exit_price is None:
            favorable = max(Decimal(0), sign * (candle.high - case.entry) if sign > 0 else sign * (candle.low - case.entry))
            adverse = max(Decimal(0), -sign * (candle.low - case.entry) if sign > 0 else -sign * (candle.high - case.entry))
        else:
            points = (candle.open, exit_price)
            favorable = max(Decimal(0), *(sign * (p - case.entry) for p in points))
            adverse = max(Decimal(0), *(-sign * (p - case.entry) for p in points))
        case.mfe_pips = max(case.mfe_pips or Decimal(0), favorable / PIP)
        case.mae_pips = max(case.mae_pips or Decimal(0), adverse / PIP)
        if exit_price is not None:
            case.exit_index, case.exit_price, case.exit_reason = now, exit_price, reason
            case.gross_result_r = sign * (exit_price - case.entry) / (case.stop_pips * PIP)
            cost = self.candles[case.trigger_index].roundtrip_cost
            case.result_r = case.gross_result_r - cost / case.stop_pips if cost is not None else None
            if case.status == 'VALID_SETUP':
                case.status = 'VALID_SAMPLE'
            elif case.status == 'INSUFFICIENT_DATA' and 'cost_unknown' in case.reasons:
                case.status = 'INSUFFICIENT_DATA'
            self.positions.remove(case)
            self.trace.append({'at': iso(candle.time), 'state': 'VIRTUAL_EXIT', 'key': case.key, 'reason': reason, 'exit': fmt(exit_price), 'gross_r': fmt(case.gross_result_r), 'result_r': fmt(case.result_r)})

    def finish(self):
        if self.active:
            self.active.status = 'WATCH'
            self.active.reasons = ['future_trigger_bars_missing']
        for case in self.positions:
            case.status = 'INSUFFICIENT_DATA'
            if 'future_exit_bars_missing' not in case.reasons:
                case.reasons.append('future_exit_bars_missing')
        return self


def csv_rows(path, id_field):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        header, rows = reader.fieldnames, list(reader)
    if not header or id_field not in header or any(None in r or None in r.values() for r in rows):
        raise InputError(f'{path}: invalid target CSV')
    ids = [row[id_field] for row in rows]
    if len(ids) != len(set(ids)):
        raise InputError(f'{path}: duplicate existing ID')
    return header, rows


def structure_from_notes(notes):
    match = re.search(r'(?:^|;)structure_key=([^;]+)', notes or '')
    return match.group(1) if match else None


def existing_structure(row):
    key = structure_from_notes(row.get('notes'))
    if key:
        return key
    start, end, direction = row.get('impulse_start_time'), row.get('impulse_end_time'), row.get('direction')
    if start not in {'UNKNOWN', 'NA', 'N/A', '', None} and end not in {'UNKNOWN', 'NA', 'N/A', '', None} and direction in {'LONG', 'SHORT'}:
        return f'USDJPY-M5|{direction}|{start}|{end}'
    return None


def base_notes(notes):
    without_history = (notes or '').split(';auto_revision=', 1)[0]
    return re.sub(r';assessed_at=[^;]*', '', without_history)


def assign_ids(observer, formal_rows, opportunity_rows):
    formal_by_key = {existing_structure(r): r for r in formal_rows if existing_structure(r)}
    opp_by_key = {existing_structure(r): r for r in opportunity_rows if existing_structure(r)}
    next_formal = max([int(m.group(1)) for r in formal_rows if (m := re.fullmatch(r'HYP009-v01-(\d+)', r['case_id']))] or [0])
    per_date = {}
    for row in opportunity_rows:
        match = re.fullmatch(r'OPP-HYP009-(\d{8})-(\d+)', row['opportunity_id'])
        if match:
            per_date[match.group(1)] = max(per_date.get(match.group(1), 0), int(match.group(2)))
    for case in observer.cases:
        if case.trigger_index is not None:
            old = formal_by_key.get(case.key)
            if old:
                case.formal_id = old['case_id']
            else:
                next_formal += 1
                case.formal_id = f'HYP009-v01-{next_formal:04d}'
                formal_by_key[case.key] = {'case_id': case.formal_id}
        if case not in observer.observations:
            continue
        old = opp_by_key.get(case.key)
        if old:
            case.opportunity_id = old['opportunity_id']
        else:
            reference = observer.candles[case.reference_index].time
            day = reference.strftime('%Y%m%d')
            per_date[day] = per_date.get(day, 0) + 1
            case.opportunity_id = f'OPP-HYP009-{day}-{per_date[day]:03d}'
            opp_by_key[case.key] = {'opportunity_id': case.opportunity_id}


def formal_row(observer, case, header):
    row = dict.fromkeys(header, 'UNKNOWN')
    candle = observer.candles[case.trigger_index]
    complete = case.exit_index is not None
    true_sample = case.status == 'VALID_SAMPLE' and complete and case.result_r is not None
    known_exclusion = case.status == 'REJECTED_OPPORTUNITY'
    row.update(case_id=case.formal_id, datetime_jst=iso(candle.time), direction=case.direction, session=session_label(candle.time), event_tag=candle.event_tag,
               impulse_start_time=iso(case.start.time), impulse_end_time=iso(case.end.time), impulse_start_price=fmt(case.start.price), impulse_end_price=fmt(case.end.price), impulse_pips=fmt(case.impulse_pips), impulse_bars=str(case.intervals),
               pullback_bars=str(case.pullback_bars), pullback_extreme=fmt(case.pullback_extreme), pullback_pct=fmt(case.pullback_pct), trigger_open=fmt(candle.open), trigger_high=fmt(candle.high), trigger_low=fmt(candle.low), trigger_close=fmt(candle.close), trigger_body_ratio=fmt(case.body_ratio),
               entry=fmt(case.entry), stop=fmt(case.stop), stop_pips=fmt(case.stop_pips), target=fmt(case.target), exit_time=iso(observer.candles[case.exit_index].time) if complete else 'UNKNOWN', exit=fmt(case.exit_price), result_r=fmt(case.result_r) if true_sample else 'UNKNOWN',
               mfe_r=fmt(case.mfe_pips / case.stop_pips) if case.mfe_pips is not None and case.stop_pips and case.stop_pips > 0 else 'UNKNOWN',
               mae_r=fmt(case.mae_pips / case.stop_pips) if case.mae_pips is not None and case.stop_pips and case.stop_pips > 0 else 'UNKNOWN',
               spread_pips=fmt(candle.spread), account_balance='UNKNOWN', risk_pct='0.25', demo_ordered='FALSE', demo_quantity='0', valid='TRUE' if true_sample else 'FALSE' if known_exclusion else 'PENDING',
               invalid_reason='N/A' if true_sample else ';'.join(case.reasons) or 'future_exit_bars_missing', screenshot='N/A')
    notes = [f'auto_observer=v0.1', f'structure_key={case.key}', f'start_confirmed_at={iso(case.start.confirmed_at)}', f'end_confirmed_at={iso(case.end.confirmed_at)}', f'observed_at={iso(observer.forward_observed_at)}', f'assessed_at={iso(observer.assessed_at)}', f'test_mode={"forward" if observer.forward_observed_at else "historical"}', f'eligibility={"CONFIRMED" if true_sample else "UNKNOWN"}', f'position_status={"CLOSED" if complete else "OPEN"}', f'exit_reason={case.exit_reason or "UNKNOWN"}', f'gross_result_r={fmt(case.gross_result_r)}', f'mfe_pips={fmt(case.mfe_pips)}', f'mae_pips={fmt(case.mae_pips)}', f'roundtrip_cost_pips={fmt(candle.roundtrip_cost)}', f'price_series={observer.price_series}', f'source={observer.source}', 'mfe_mae=completed_bars_and_exit_points_only']
    row['notes'] = ';'.join(notes)
    return row


def first_passage(observer, case, threshold):
    if not case.observation or not case.stop_pips or case.stop_pips <= 0:
        return 'UNKNOWN'
    reference = observer.candles[case.reference_index].close
    distance = case.stop_pips * PIP
    sign = direction_sign(case.direction)
    favorable, adverse = None, None
    for position, index in enumerate(case.observation, 1):
        candle = observer.candles[index]
        best = sign * ((candle.high if sign > 0 else candle.low) - reference)
        worst = -sign * ((candle.low if sign > 0 else candle.high) - reference)
        if favorable is None and best >= distance * threshold:
            favorable = position
        if adverse is None and worst >= distance:
            adverse = position
    if favorable is not None and adverse is not None:
        return 'SAME_BAR' if favorable == adverse else 'FAVORABLE_FIRST' if favorable < adverse else 'ADVERSE_FIRST'
    if favorable is not None:
        return 'FAVORABLE_FIRST'
    if adverse is not None:
        return 'ADVERSE_FIRST'
    return 'NEITHER' if len(case.observation) == 12 else 'UNKNOWN'


def opportunity_row(observer, case, header):
    row = dict.fromkeys(header, 'UNKNOWN')
    reference = observer.candles[case.reference_index]
    observed = [observer.candles[i] for i in case.observation]
    sign = direction_sign(case.direction)
    mfe = max([Decimal(0)] + [sign * ((c.high if sign > 0 else c.low) - reference.close) / PIP for c in observed]) if observed else None
    mae = max([Decimal(0)] + [-sign * ((c.low if sign > 0 else c.high) - reference.close) / PIP for c in observed]) if observed else None
    defined = case.trigger_index is not None and case.stop_pips is not None and case.stop_pips > 0
    complete = len(observed) == 12
    statuses = {}
    for label, threshold in [('1r', Decimal(1)), ('1_5r', Decimal('1.5'))]:
        if not defined:
            statuses[f'reached_{label}'] = 'NA'
            statuses[f'first_{label}'] = 'NA'
        else:
            statuses[f'reached_{label}'] = 'TRUE' if mfe is not None and mfe >= case.stop_pips * threshold else 'FALSE' if complete else 'UNKNOWN'
            statuses[f'first_{label}'] = first_passage(observer, case, threshold)
    row.update(opportunity_id=case.opportunity_id, parent_case_id=case.formal_id or 'NA', classification=case.status if case.status in {'REJECTED_OPPORTUNITY', 'INSUFFICIENT_DATA'} else 'INSUFFICIENT_DATA',
               evidence_status='CONFIRMED' if observer.forward_observed_at and observer.forward_observed_at <= case.start.time else 'PROVISIONAL', direction=case.direction,
               rejection_reason=';'.join(r for r in case.reasons if r in {'IMPULSE_TOO_LARGE', 'IMPULSE_TOO_SMALL', 'IMPULSE_TOO_LONG', 'IMPULSE_TOO_SHORT', 'PULLBACK_TOO_SHALLOW', 'PULLBACK_TOO_DEEP', 'NO_TRIGGER', 'STOP_TOO_WIDE', 'STOP_TOO_TIGHT', 'SPREAD', 'EVENT_WINDOW', 'OUT_OF_SESSION', 'AMBIGUOUS_DATA', 'INVALID_STOP_SIDE'}) or 'AMBIGUOUS_DATA',
               observed_at=iso(observer.forward_observed_at), assessed_at=iso(observer.assessed_at), source=observer.source,
               impulse_start_time=iso(case.start.time), impulse_end_time=iso(case.end.time), impulse_start_price=fmt(case.start.price), impulse_end_price=fmt(case.end.price), impulse_pips=fmt(case.impulse_pips), impulse_bars=str(case.intervals),
               reference_time=iso(reference.time), reference_price=fmt(reference.close), reference_basis=case.reference_basis,
               hypothetical_stop=fmt(case.stop) if defined else 'NA', hypothetical_stop_distance=fmt(case.stop_pips) if defined else 'NA', r_status='DEFINED' if defined else 'UNDEFINED',
               observation_end=iso(observed[-1].time) if complete else 'UNKNOWN', observation_bars=str(len(observed)), outcome_status='COMPLETE' if complete else 'PARTIAL' if observed else 'UNKNOWN',
               mfe_pips=fmt(mfe), mae_pips=fmt(mae), mfe_r=fmt(mfe / case.stop_pips) if defined and mfe is not None else 'UNKNOWN' if defined else 'NA', mae_r=fmt(mae / case.stop_pips) if defined and mae is not None else 'UNKNOWN' if defined else 'NA', **statuses)
    row['notes'] = ';'.join([f'auto_observer=v0.1', f'structure_key={case.key}', f'start_confirmed_at={iso(case.start.confirmed_at)}', f'end_confirmed_at={iso(case.end.confirmed_at)}', f'technical_reasons={"|".join(case.reasons)}', f'price_series={observer.price_series}', 'fixed_observation=12_contiguous_bars_after_reference'])
    return row


def prepare_rows(observer, formal_path=FORMAL_PATH, opportunity_path=OPPORTUNITY_PATH):
    formal_header, formal_existing = csv_rows(formal_path, 'case_id')
    opportunity_header, opportunity_existing = csv_rows(opportunity_path, 'opportunity_id')
    if tuple(formal_header) != FORMAL_SCHEMA or tuple(opportunity_header) != OPPORTUNITY_SCHEMA:
        raise InputError('target CSV headers differ from frozen schemas')
    assign_ids(observer, formal_existing, opportunity_existing)
    formal = [formal_row(observer, c, formal_header) for c in observer.cases if c.trigger_index is not None]
    opportunities = [opportunity_row(observer, c, opportunity_header) for c in observer.observations]
    return (formal_header, formal_existing, formal), (opportunity_header, opportunity_existing, opportunities)


def merge_owned(existing, produced, id_field):
    by_id = {r[id_field]: i for i, r in enumerate(existing)}
    by_key = {existing_structure(r): i for i, r in enumerate(existing) if existing_structure(r)}
    result = list(existing)
    for row in produced:
        key = existing_structure(row)
        index = by_key.get(key)
        if index is not None:
            old = result[index]
            if 'auto_observer=v0.1' not in old.get('notes', ''):
                raise InputError(f'Existing manual row overlaps structure {key}; reconcile manually before write')
            row[id_field] = old[id_field]
            if id_field == 'case_id':
                if old['valid'] in {'TRUE', 'FALSE'} and row['valid'] != old['valid']:
                    raise InputError(f'{key}: cannot downgrade or change a confirmed eligibility; review manually')
                if old['exit_time'] not in {'UNKNOWN', ''} and row['exit_time'] in {'UNKNOWN', ''}:
                    raise InputError(f'{key}: cannot erase a recorded virtual exit')
                if old['valid'] == 'TRUE' and row['valid'] == 'TRUE' and any(old[k] != row[k] for k in ['entry', 'stop', 'target', 'exit', 'result_r']):
                    raise InputError(f'{key}: completed result changed; review source correction manually')
                if any(old[k] not in {'UNKNOWN', 'N/A', ''} and old[k] != row[k] for k in ['entry', 'stop', 'target']):
                    raise InputError(f'{key}: fixed Entry/SL/TP changed; review manually')
                if old['exit'] not in {'UNKNOWN', 'N/A', ''} and row['exit'] not in {'UNKNOWN', 'N/A', ''} and old['exit'] != row['exit']:
                    raise InputError(f'{key}: recorded exit price changed; review manually')
            else:
                if old['classification'] == 'REJECTED_OPPORTUNITY' and row['classification'] != old['classification']:
                    raise InputError(f'{key}: cannot downgrade confirmed rejection')
                if old['outcome_status'] == 'COMPLETE' and row['outcome_status'] != 'COMPLETE':
                    raise InputError(f'{key}: cannot erase completed 12-bar observation')
                if old['outcome_status'] == 'COMPLETE' and row['outcome_status'] == 'COMPLETE' and any(old[k] != row[k] for k in ['mfe_pips', 'mae_pips', 'mfe_r', 'mae_r', 'reached_1r', 'reached_1_5r']):
                    raise InputError(f'{key}: completed observation changed; review manually')
            if any(old[k] != row[k] for k in ['direction', 'impulse_start_time', 'impulse_end_time', 'impulse_start_price', 'impulse_end_price']):
                raise InputError(f'{key}: structure prices or timestamps changed; review manually')
            semantic_old = dict(old)
            semantic_old['notes'] = base_notes(old.get('notes'))
            semantic_new = dict(row)
            semantic_new['notes'] = base_notes(row.get('notes'))
            if id_field == 'opportunity_id':
                semantic_new['assessed_at'] = old['assessed_at']
            if semantic_old == semantic_new:
                result[index] = old
                continue
            state_before = old['valid'] if id_field == 'case_id' else f"{old['classification']}:{old['outcome_status']}"
            state_after = row['valid'] if id_field == 'case_id' else f"{row['classification']}:{row['outcome_status']}"
            history = old['notes'].split(';auto_revision=', 1)[1] if ';auto_revision=' in old['notes'] else ''
            if state_before != state_after:
                previous_hash = re.search(r'sha256=([0-9a-f]{64})', old['notes'])
                revision = f'{iso(datetime.now(JST))}:{state_before}->{state_after}:previous_sha256={previous_hash.group(1) if previous_hash else "UNKNOWN"}'
                history = history + '|' + revision if history else revision
            if history:
                row['notes'] += f';auto_revision={history}'
            result[index] = row
        elif row[id_field] in by_id:
            raise InputError(f'ID collision: {row[id_field]}')
        else:
            by_key[key] = len(result)
            by_id[row[id_field]] = len(result)
            result.append(row)
    return result


def write_csv_atomic(path, header, rows):
    path = Path(path)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', dir=path.parent, prefix='.hyp009-', suffix='.csv', delete=False) as handle:
        temp = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def write_records(observer, formal_path=FORMAL_PATH, opportunity_path=OPPORTUNITY_PATH):
    formal_group, opportunity_group = prepare_rows(observer, formal_path, opportunity_path)
    fh, old_f, new_f = formal_group
    oh, old_o, new_o = opportunity_group
    merged_f = merge_owned(old_f, new_f, 'case_id')
    merged_o = merge_owned(old_o, new_o, 'opportunity_id')
    # A provisional narrative on the same date and close endpoint prices cannot
    # be silently treated as a different confirmed market event.
    for old in old_o:
        if old.get('evidence_status') != 'PROVISIONAL' or existing_structure(old):
            continue
        for new in new_o:
            if old.get('direction') == new['direction'] and old['opportunity_id'][11:19] == new['opportunity_id'][11:19]:
                try:
                    if abs(dec(old['impulse_start_price'], 'old start') - dec(new['impulse_start_price'], 'new start')) <= Decimal('0.005') and abs(dec(old['impulse_end_price'], 'old end') - dec(new['impulse_end_price'], 'new end')) <= Decimal('0.005'):
                        raise InputError('Potential duplicate of a provisional opportunity; reconcile its ID manually before write')
                except InputError as exc:
                    if 'Potential duplicate' in str(exc):
                        raise
    if merged_f != old_f:
        write_csv_atomic(formal_path, fh, merged_f)
    if merged_o != old_o:
        write_csv_atomic(opportunity_path, oh, merged_o)
    return {'formal_added_or_updated': len(new_f), 'opportunities_added_or_updated': len(new_o)}


def report(observer):
    cases = []
    for c in observer.cases:
        cases.append({
            'case_id': c.formal_id or c.opportunity_id or 'WATCH', 'state': c.status,
            'direction': c.direction, 'start': iso(c.start.time), 'start_price': fmt(c.start.price),
            'start_confirmed_at': iso(c.start.confirmed_at), 'end': iso(c.end.time),
            'end_price': fmt(c.end.price), 'end_confirmed_at': iso(c.end.confirmed_at),
            'impulse_pips': fmt(c.impulse_pips), 'intervals': c.intervals,
            'pullback_bars': c.pullback_bars, 'pullback_pct': fmt(c.pullback_pct),
            'trigger': iso(observer.candles[c.trigger_index].time) if c.trigger_index is not None else 'UNKNOWN',
            'body_ratio': fmt(c.body_ratio), 'entry': fmt(c.entry), 'stop': fmt(c.stop),
            'risk_pips': fmt(c.stop_pips), 'target': fmt(c.target), 'exit': fmt(c.exit_price),
            'exit_reason': c.exit_reason or 'UNKNOWN', 'gross_result_r': fmt(c.gross_result_r),
            'result_r': fmt(c.result_r) if c.status == 'VALID_SAMPLE' else 'UNKNOWN',
            'mfe_pips': fmt(c.mfe_pips), 'mae_pips': fmt(c.mae_pips),
            'mfe_r': fmt(c.mfe_pips / c.stop_pips) if c.mfe_pips is not None and c.stop_pips and c.stop_pips > 0 else 'UNKNOWN',
            'mae_r': fmt(c.mae_pips / c.stop_pips) if c.mae_pips is not None and c.stop_pips and c.stop_pips > 0 else 'UNKNOWN',
            'reasons': c.reasons,
        })
    return {
        'version': 'HYP-009 AUTO OBSERVER v0.1', 'candles_processed': len(observer.candles),
        'confirmed_swings': observer.confirmed_count, 'impulse_candidates': observer.impulse_candidates,
        'valid_setups': sum(c.status in {'VALID_SETUP', 'VALID_SAMPLE'} for c in observer.cases),
        'valid_completed_samples': sum(c.status == 'VALID_SAMPLE' for c in observer.cases),
        'rejected_opportunities': sum(c.status == 'REJECTED_OPPORTUNITY' for c in observer.observations),
        'insufficient': sum(c.status == 'INSUFFICIENT_DATA' for c in observer.cases),
        'open_observations': sum(c.status == 'WATCH' or c.trigger_index is not None and c.exit_index is None for c in observer.cases),
        'data_issues': observer.errors, 'cases': cases,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='HYP-009 v0.1 virtual observer; no orders')
    parser.add_argument('--input', required=True, type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--dry-run', action='store_true', help='default; never change target CSVs')
    action.add_argument('--write', action='store_true', help='explicitly upsert auto-owned rows')
    parser.add_argument('--forward-observed-at', help='timezone-aware first contemporaneous observation time; retrospective replay must omit this')
    parser.add_argument('--price-series', choices=['mid', 'bid', 'ask', 'UNKNOWN'], default='UNKNOWN')
    parser.add_argument('--formal-csv', type=Path, default=FORMAL_PATH)
    parser.add_argument('--opportunities-csv', type=Path, default=OPPORTUNITY_PATH)
    args = parser.parse_args(argv)
    try:
        source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
        observer = Observer(forward_observed_at=args.forward_observed_at, source=f'{args.input.resolve()} sha256={source_hash}', price_series=args.price_series)
        for candle in load_candles(args.input):
            observer.feed(candle)
        observer.finish()
        prepare_rows(observer, args.formal_csv, args.opportunities_csv)
        if args.write:
            write_records(observer, args.formal_csv, args.opportunities_csv)
        print(json.dumps(report(observer), ensure_ascii=False, indent=2))
        return 0
    except (InputError, OSError) as exc:
        parser.exit(2, f'INPUT/WRITE ERROR: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
