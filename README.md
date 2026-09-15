# FX Trading Rules — v0.1

このリポジトリは、自分専用のFXトレードシステムを育てるための検証リポジトリである。

目的は勝ったトレードを集めることではなく、日々の事例から仮説を抽出し、複数回検証して再現性・期待値・リスクリワードを確認した少数のパターンへ絞ること。ChatGPTと相談しながら運用する。

## ルールの状態

```text
OBSERVED（単発事例・気づき）
  ↓
HYPOTHESIS（仮説）
  ↓
TESTING（検証中）
  ↓
APPROVED（正式採用）

HYPOTHESIS / TESTING → REJECTED（検証で却下）
APPROVED → RETIRED（環境変化などにより使用停止）
```

REJECTED / RETIREDを再検討する際は履歴を残し、HYPOTHESISへ戻して再検証する。1回うまくいっただけでAPPROVEDにしない。勝ったから採用、負けたから却下という判断は禁止。

**v0.1の正式採用ルールは0件。** 初期思想は原則候補であり、有効性は未検証。仮説は実売買の許可を意味しない。損切りを含み損を理由に後から広げないことは、検証中も守る運用上の制約とする。

## 構成

| フォルダ | 用途 |
| --- | --- |
| [01_principles](01_principles/trading-philosophy.md) | 原則候補・リスク管理方針 |
| [02_setups](02_setups/README.md) | 正式採用セットアップ・見送りルール |
| [03_hypotheses](03_hypotheses/active-hypotheses.md) | 仮説と検証計画 |
| [04_trade-logs](04_trade-logs/2026/2026-09.md) | 約定記録・観測・見送り事例 |
| [05_reviews](05_reviews/mistakes.md) | 成否の構造、遵守、改善のレビュー |
| [06_statistics](06_statistics/README.md) | 集計定義・成績 |
| [07_templates](07_templates/rule-template.md) | 記録テンプレート |

## 日々の運用

会話のチャート判定がずれた場合は[チャート判定の運用正本](01_principles/chart-assessment-canonical.md)へ戻る。5分足は通常HYP-009、15分足はHYP-008。通常009の1.5R固定利確と、明示宣言による[1.5Rロック派生](03_hypotheses/HYP-009-lock-1.5R-v0.1.md)を分離する。派生はHYPOTHESISであり、固定条件による検証・採用は未実施。

HYP-009の正式サンプルは[既存37列CSV](06_statistics/HYP-009-v0.1-tests.csv)、見送りとデータ不足の観測は[別CSV](06_statistics/HYP-009-rejected-opportunities.csv)を正本とする。[検証管理・記入方法](06_statistics/HYP-009-observation-operations.md)を参照。現況の勝敗・有効完了・見送りは `python 06_statistics/summarize_hyp009.py` で両CSVから再計算する。見送りを正式30件や通常・派生成績に加算しない。

1. 事前に上・下・レンジの条件分岐、撤退条件、利確候補を記録する。
2. 結果にかかわらず、対象条件に合う事例・見送り・ルール違反を残す。事後解釈は事前シナリオと分離する。
3. 気づきをOBSERVEDとして保存し、価格そのものより値動きの構造へ抽象化する。
4. 既存仮説との類似・矛盾を調べる。類似は統合を検討し、矛盾は記録して解消するまで正式追加しない。
5. HYPOTHESISに反証条件と事前検証計画を設定してTESTINGへ進める。
6. 複数回検証し、検証回数・勝率・平均利益・平均損失・平均RR・最大連敗・期待値・条件の再現性・相場環境依存性をレビューする。
7. 事前に設定した採用基準を確認し、本人の判断と根拠・日付を記録してAPPROVEDへ昇格する。データ不足なら検証を続ける。

採用基準は検証前に決める。最低件数、コスト控除後の期待値、許容連敗・損失、再現性の判定方法、対象環境、未使用期間での確認条件が未設定のまま採用しない。好結果に合わせて基準を後から緩めない。条件変更時は版を分けて再検証する。

## IDと履歴

検証開始前に各仮説の条件と採用基準を固定し、Test Criteria Fixed Atに固定日時（タイムゾーン付き）を記録する。必要項目が1つでも未確定ならTESTINGへ進めない。HYP-001〜007は未固定。HYP-008と通常HYP-009はTESTING（条件は[台帳](03_hypotheses/active-hypotheses.md)参照）。1.5Rロック派生はHYPOTHESIS。正式採用0件。HYP-009の完了件数は上記CSVと集計スクリプトを参照する。

条件・採用基準を変更する場合は、既存版を上書きせず、例えばHYP-008 v0.1からv0.2へ分ける。旧版の条件・採用基準・検証結果を削除せず保持し、新版にVersion、Test Criteria Fixed At、Promotion Criteria、Version History、Change Reasonを記録する。変更日・変更理由・変更差分を必ず残し、旧版と新版の結果は別集計する。具体的な保存方法は[仮説管理](03_hypotheses/README.md)に従う。

- 仮説はHYP-001から連番。採用時にRULE-001から別の連番を払い出し、元のHYP IDと相互リンクする。
- OBSERVEDはOBS-YYYYMMDD-NNNで識別する。既存IDの再利用・削除による詰め直しはしない。
- 見送り条件も同じライフサイクルで管理し、採用時にはRULE IDを付ける。
- 状態変更・条件変更・統合・矛盾・却下・停止理由を各文書とCHANGELOGに記録する。旧証拠を消さない。
- 数値がない項目はUNKNOWNまたは未検証。UNKNOWNは0として集計しない。

ChatGPTは整理・反証・比較を補助する。提供されていない約定・相場データ・成績は推測で埋めない。
