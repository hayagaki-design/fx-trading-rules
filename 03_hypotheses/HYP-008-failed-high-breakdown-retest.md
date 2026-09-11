# HYP-008 重要高値ブレイク失敗 → 支持帯割れ → 戻り売り

| 項目 | 内容 |
| --- | --- |
| Rule ID | HYP-008（RULE ID未発行） |
| Rule Name | 重要高値ブレイク失敗 → 支持帯割れ → 戻り売り |
| Status | HYPOTHESIS |
| Version | v0.1 |
| Test Criteria Fixed At | UNKNOWN（未固定・検証開始不可） |
| Promotion Criteria | UNKNOWN（未固定。検証開始前に定義する） |
| Version History | 2026-09-11: v0.1 初期登録。条件変更なし |
| Change Reason | 初期構築のため |
| Created | 2026-09-11 |
| Last Reviewed | 2026-09-11 |
| Market | USDJPY（他通貨への適用は未検証） |
| Timeframe | UNKNOWN |
| Market Environment | 重要高値・抵抗帯の突破失敗後。環境依存性は未検証 |
| Setup | 高値更新失敗後の支持帯下抜けと戻り失敗 |
| Entry Conditions | 市場が明確に意識する高値・抵抗帯がある／複数回試す／高値更新失敗／直近支持帯を下抜け／戻りが入る／元の支持帯を取り返せない |
| Entry Trigger | 戻り後の再下落。具体的な足・確定条件はUNKNOWN |
| Stop Loss | ブレイク失敗シナリオが否定される価格。事前に決定し、含み損を理由に広げない |
| Take Profit | 次の支持帯。第二利確・配分はUNKNOWN |
| Invalidation | 抵抗帯の突破定着、または戻りで元の支持帯を回復する等。確定条件は検証前に定義 |
| Do Not Trade When | 支持帯を割った瞬間の追いかけ売り／戻り失敗未確認／損切り未定／利確余地が事前の基準を満たさない |
| Evidence | OBS-20260910-001、OBS-20260911-001。いずれも一部構造の観測であり全条件充足の証拠ではない |
| Number of Tests | 0 |
| Wins | UNKNOWN |
| Losses | UNKNOWN |
| Win Rate | UNKNOWN |
| Average Win | UNKNOWN |
| Average Loss | UNKNOWN |
| Average RR | UNKNOWN |
| Expected Value | UNKNOWN |
| Max Losing Streak | UNKNOWN |
| Known Weaknesses | 戻りがなく下落する機会損失／だまし／指標後の急変／支持帯判定の主観性。程度は未検証 |
| Related Rules | HYP-003、HYP-004、HYP-005、HYP-006、HYP-007。正式ルールなし |
| Example Trades | [2026-09の観測記録](../04_trade-logs/2026/2026-09.md) |
| Notes | 個別価格を一般条件にしない。勝ったから採用・負けたから却下しない |

## 未確定事項と検証計画

重要帯の選定方法、複数回試行の回数と間隔、突破失敗・下抜け・戻り・取り返せないことの足確定条件、時間足、検証期間、必要件数、採用閾値はUNKNOWN。

これらを固定し、条件該当事例を損益に関係なく抽出する。指標有無・トレンド／レンジ・時間帯で分け、コスト控除後の損益Rと全評価指標を比較する。未使用期間でも確認する。再現性が低い、期待値が基準未満、環境を限定しないと成立しない等の反証を記録する。

## 履歴

- 2026-09-11: ユーザー提供の観測2件からHYPOTHESISとして登録。検証・正式採用は未実施。
