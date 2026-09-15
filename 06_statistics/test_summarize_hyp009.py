"""Checks population separation and missing-R handling without market data."""
import unittest
from summarize_hyp009 import summarize


class SummaryTests(unittest.TestCase):
    def test_valid_trade_and_rejected_parent_are_separate(self):
        base = dict.fromkeys('case_id valid notes direction impulse_start_time impulse_end_time datetime_jst entry stop stop_pips target exit result_r spread_pips exit_time'.split(), 'UNKNOWN')
        valid = dict(base, case_id='HYP009-v01-0001', valid='TRUE', direction='LONG', impulse_start_time='2026-09-16T10:00:00+09:00', impulse_end_time='2026-09-16T10:15:00+09:00', datetime_jst='2026-09-16T10:25:00+09:00', entry='150.000', stop='149.900', stop_pips='10', target='150.150', exit='150.150', result_r='1.4', spread_pips='0.3', exit_time='2026-09-16T10:35:00+09:00', notes='test_mode=forward;eligibility=CONFIRMED;position_status=CLOSED;exit_reason=TP')
        false = dict(base, case_id='HYP009-v01-0002', valid='FALSE', datetime_jst='2026-09-16T11:00:00+09:00')
        opportunity = dict.fromkeys('opportunity_id parent_case_id classification evidence_status direction rejection_reason outcome_status r_status hypothetical_stop hypothetical_stop_distance mfe_r mae_r reached_1r reached_1_5r first_1r first_1_5r observation_bars mfe_pips mae_pips reference_basis'.split(), 'UNKNOWN')
        opportunity.update(opportunity_id='OPP-HYP009-20260916-001', parent_case_id='HYP009-v01-0002', classification='REJECTED_OPPORTUNITY', evidence_status='CONFIRMED', direction='LONG', rejection_reason='STOP_TOO_WIDE', outcome_status='COMPLETE', observation_bars='12', r_status='DEFINED', hypothetical_stop='149.750', hypothetical_stop_distance='25', mfe_pips='40', mae_pips='25', mfe_r='1.6', mae_r='1', reached_1r='TRUE', reached_1_5r='TRUE', first_1r='ADVERSE_FIRST', first_1_5r='ADVERSE_FIRST', reference_basis='TRIGGER_CLOSE')
        report = summarize([valid, false], [opportunity])
        overview = report['HYP-009 v0.1']
        self.assertEqual((overview['Valid completed samples'], overview['Wins'], overview['Rejected opportunities']), (1, 1, 1))
        self.assertEqual(overview['Expectancy / Average R'], 1.4)
        self.assertEqual(report['Reason groups (multi-label; do not sum)'][0]['1_5r']['first_passage']['ADVERSE_FIRST'], 1)
        self.assertEqual(report['Audit errors'], [])

    def test_undefined_r_keeps_missing_denominator(self):
        opportunity = dict.fromkeys('opportunity_id parent_case_id classification evidence_status direction rejection_reason outcome_status r_status hypothetical_stop hypothetical_stop_distance mfe_r mae_r reached_1r reached_1_5r first_1r first_1_5r observation_bars mfe_pips mae_pips reference_basis'.split(), 'UNKNOWN')
        opportunity.update(opportunity_id='OPP-HYP009-20260916-002', parent_case_id='NA', classification='REJECTED_OPPORTUNITY', evidence_status='PROVISIONAL', rejection_reason='IMPULSE_TOO_LARGE', outcome_status='UNKNOWN', observation_bars='0', r_status='UNDEFINED', hypothetical_stop='NA', hypothetical_stop_distance='NA', mfe_r='NA', mae_r='NA', reached_1r='NA', reached_1_5r='NA', first_1r='NA', first_1_5r='NA')
        report = summarize([], [opportunity])
        self.assertEqual(report['HYP-009 v0.1']['Valid completed samples'], 0)
        self.assertEqual(report['Reason groups (multi-label; do not sum)'][0]['1r']['denominator'], 0)
        self.assertEqual(report['Audit errors'], [])


if __name__ == '__main__':
    unittest.main()
