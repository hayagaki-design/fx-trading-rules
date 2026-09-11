# 仮説台帳 v0.1

Created / Last Reviewed: 2026-09-11

## バージョン・固定状況

| ID | Version | Test Criteria Fixed At | Promotion Criteria |
| --- | --- | --- | --- |
| HYP-001 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-002 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-003 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-004 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-005 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-006 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-007 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |
| HYP-008 | v0.1 | UNKNOWN（未固定） | UNKNOWN（未固定） |

Version History（全8件）: 2026-09-11 v0.1 初期登録。Change Reason: 初期構築のため。検証条件の変更はなし。全件、検証開始前に条件・採用基準の固定が必要。

全件Status: HYPOTHESIS。各仮説の検証回数は0。勝敗・勝率・平均利益・平均損失・平均RR・期待値・最大連敗はUNKNOWN。再現性・環境依存性は未検証。

| ID | 名称 | 定義 |
| --- | --- | --- |
| HYP-001 | 予想より条件 | [思想](../01_principles/trading-philosophy.md) |
| HYP-002 | レンジ中央では入らない | [エントリー](../01_principles/entry-principles.md) |
| HYP-003 | ブレイク直後を追いかけない | [エントリー](../01_principles/entry-principles.md) |
| HYP-004 | 指標初動を捨てる | [見送り](../01_principles/no-trade-rules.md) |
| HYP-005 | 材料と値動きの不一致を見る | [思想](../01_principles/trading-philosophy.md) |
| HYP-006 | エントリー前に撤退条件を決める | [撤退](../01_principles/exit-principles.md) |
| HYP-007 | 損切りを広げない | [リスク管理](../01_principles/risk-management.md) |
| HYP-008 | 重要高値ブレイク失敗 → 支持帯割れ → 戻り売り | [個別仮説](HYP-008-failed-high-breakdown-retest.md) |

## 検証課題

| ID | 検証前に決めること・反証観点 |
| --- | --- |
| HYP-001 | 分岐条件・判定時刻。事後的に条件を読み替えていないか |
| HYP-002 | レンジ幅・中央の定義。見送りがコスト控除後の成績改善につながるか |
| HYP-003 | ブレイク・戻りの定義。待機による約定悪化・機会損失を含めて比較 |
| HYP-004 | 発表時刻・待機区間・再開条件。初動後も荒い環境を識別できるか |
| HYP-005 | 材料の強弱・反応時間の事前定義。弱い反応が継続的に意味を持つか |
| HYP-006 | 各決済条件・比率。撤退の一貫性と実現損益Rを確認 |
| HYP-007 | 当初リスクと変更履歴。利益になった違反も含めて評価 |
| HYP-008 | 高値試行・支持帯・戻り失敗・再下落を客観化。全条件を満たさない事例を区別 |

全件、対象時間足・検証期間・必要件数・採用閾値はUNKNOWN。これらを固定するまでTESTINGへ移行しない。

## 類似・矛盾

- HYP-003とHYP-008は共通の戻り確認を持つ。一般原則と具体的売りパターンの関係として整理し、検証後に統合を検討する。
- HYP-002 / 004 / 006は見送り条件と重複するが、同じIDを参照し、別仮説として水増ししない。
- HYP-005の材料解釈がHYP-001の条件優先と衝突しないよう、ニュース解釈だけではエントリーしない。
- 未解消の正式ルール間矛盾: 該当なし（正式ルール0件）。

履歴: 2026-09-11 — 8件をHYPOTHESISとして初期登録。昇格なし。
