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
| HYP-008 | v0.1 | 2026-09-11T15:18:37+09:00（Asia/Tokyo） | [固定済み・50件基準](HYP-008-failed-high-breakdown-retest.md) |
| HYP-009 | v0.1 | 2026-09-14T13:31:09+09:00（Asia/Tokyo） | [探索30件・正式採用不可](HYP-009-5m-impulse-pullback-continuation.md) |

Version History: 2026-09-11 全8件をv0.1として初期登録。HYP-001〜007のChange Reasonは初期構築のためであり、条件・採用基準は未固定のまま。HYP-008のみ2026-09-11T15:18:37+09:00に初回固定。Change Reason: ユーザー指定の客観条件で検証を開始するため。

Status: HYP-001〜007はHYPOTHESIS、HYP-008とHYP-009はTESTING。各仮説の検証回数は0。勝敗・勝率・平均利益・平均損失・平均RR・期待値・最大連敗はUNKNOWN。再現性・環境依存性は未検証。正式採用0件。

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
| HYP-009 | 5分足インパルス・プルバック継続 | [個別仮説](HYP-009-5m-impulse-pullback-continuation.md) |

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
| HYP-008 | 客観条件・採点規約を固定済み。USDJPY 15分足、過去30＋フォワード20件を専用CSVで検証 |

HYP-001〜007の対象時間足・検証期間・必要件数・採用閾値はUNKNOWN。これらを固定するまでTESTINGへ移行しない。HYP-008は固定済みであり、条件変更時はv0.2を別作成してv0.1の結果を保持する。

## 類似・矛盾

- HYP-003とHYP-008は共通の戻り確認を持つ。一般原則と具体的売りパターンの関係として整理し、検証後に統合を検討する。
- HYP-002 / 004 / 006は見送り条件と重複するが、同じIDを参照し、別仮説として水増ししない。
- HYP-005の材料解釈がHYP-001の条件優先と衝突しないよう、ニュース解釈だけではエントリーしない。
- 未解消の正式ルール間矛盾: 該当なし（正式ルール0件）。

履歴: 2026-09-11 — 8件をHYPOTHESISとして初期登録。昇格なし。

履歴: 2026-09-14 — HYP-009 v0.1をTESTINGとして追加。固定日時2026-09-14T13:31:09+09:00、Change Reason: 5分足の探索用母集団を別検証するため。フォワード30件、実注文リスク0.25%。HYP-008の条件・状態・結果は変更せず完全別集計。HYP-009の30件だけでは正式採用しない。
