# HYP-009 検証管理・見送り観測の運用

作成：2026-09-15。売買条件の変更ではない。[v0.1本文](../03_hypotheses/HYP-009-5m-impulse-pullback-continuation.md)と[採点規約](HYP-009-v0.1-protocol.md)を優先し、両文書は凍結する。

## 正本と日々の記録

- 正式サンプル数の唯一の正本は `HYP-009-v0.1-tests.csv`。37列を維持する。全条件・決済・コスト確認済みの `valid=TRUE` のみ有効完了。実注文しなかった適格シグナルも仮想出口を追跡する。
- 見送り・判定不能の正本は [HYP-009-rejected-opportunities.csv](HYP-009-rejected-opportunities.csv)。正式30件・勝率・期待値・PF・平均Rには絶対に混ぜない。
- 既存仕様では正式CSVにFALSE/PENDINGも保存する。この仕様を廃止しない。そこに記録済みの見送りを詳細化するときは `parent_case_id` で結び、件数は親IDで重複排除する。新しいトリガー前の観察は見送りCSVだけでよい。
- 月次trade-logは説明と証拠への索引。ミスは [mistakes.md](../05_reviews/mistakes.md)。派生は既存の専用観察記録。いずれも正式件数の加算元にしない。
- READMEや台帳に最新件数を手入力しない。凍結文書の「0件」は初回固定時の記録として保持する。現況はリポジトリ直下で `python 06_statistics/summarize_hyp009.py` を実行する。スクリプトはCSVを読み取り、ファイルを書き換えない。

## 既存条件の照合結果

USDJPY・5分足・確定足のみ、Entry時刻JST 08:00以上〜翌01:00未満。左右1本の厳密なスイングで同値不可、右1本確定後に利用する。

LONGはL0→H1→押し→トリガー、SHORTはH0→L1→戻り→トリガー。インパルス10〜35pips・2〜8**間隔**。押し戻り1〜5本・20〜70%。トリガーは終点後2〜6本目。LONGは陽線かつ終値>前足高値、SHORTは陰線かつ終値<前足安値、実体率は両方40%以上。押し戻り区間はトリガー足を除くが、トリガー足ヒゲの70%超は無効を優先する。

SLはLONGのP−1pip／SHORTのP＋1pip、距離4〜20pips。通常TPは固定1.5R、次足から12本、最終足でもTP/SL優先、同一足両到達で順序不明ならSL先行。ギャップ・コスト・MFE/MAEは既存採点規約に従う。

同一インパルスの最初の候補1回のみ。spread>0.5pip除外、対象イベントの発表−10分〜＋15分（両端含む）除外。イベント対象は既存本文の7種類。実注文0.25%・日次停止条件も維持し、日次停止のみで適格仮想サンプルを除外しない。

大きく動いた方向を追わず、規定サイズ・時間と押し戻りを待つ。強い動きを見送ること自体は失敗ではない。防御的な設計が適切か、過剰かは未検証。

## 判定ミスを防ぐ

1. 表示時刻が始値時刻か終値時刻かを確認し、正式CSVは終値時刻（+09:00）に統一する。21:10開始の足なら21:15まで形成中。21:10というラベルだけで確定を決めない。
2. 形成中足はWATCH。確定後のOHLC・直前足高安・実体率を使う。右側確認足の未確定もスイング未確認として待つ。
3. 遅れて成立に気づいても現在価格へEntryを変更しない。仮想Entryは元のトリガー終値。実約定・遅延・未注文はnotesへ別記。過去画像の読み直しをフォワードへ昇格させない。
4. 閾値付近の価格を画像の見た目から推定しない。対象足をクリック／タップしたOHLC表示を取得する。アクセス不能ならその表示画像を依頼し、価格の手入力を原則要求しない。

## 見送りCSVの列

UTF-8・カンマ区切り。複数理由はセミコロン区切り。不明はUNKNOWN、定義不能・適用外はNA（既存CSVのN/Aと同義）。空欄や欠損を0にしない。

| 列 | 内容 |
| --- | --- |
| opportunity_id / parent_case_id | OPP-HYP009-YYYYMMDD-NNN。既存正式CSVの対応ID、なければNA |
| classification | REJECTED_OPPORTUNITY / INSUFFICIENT_DATA。WATCH中は終結理由にしない |
| evidence_status | CONFIRMED / PROVISIONAL。概算・未照合の見送りは後者 |
| direction / rejection_reason | LONG・SHORT・UNKNOWN / 下表の理由（複数可） |
| observed_at / assessed_at / source | 観測開始・実際の判定時刻（+09:00）・保存画像/OHLC/提供記述への参照 |
| impulse_start_time / impulse_end_time | 足終値時刻。ラベルの意味未確認ならUNKNOWN、原文はnotesに保持 |
| impulse_start_price / impulse_end_price / impulse_pips / impulse_bars | 始終点円価格・幅pips・間隔数。概算はPROVISIONALで明記 |
| reference_time / reference_price / reference_basis | 観測基準の確定足終値時刻・終値円価格・TRIGGER_CLOSEまたはREJECTION_CLOSE |
| hypothetical_stop / hypothetical_stop_distance / r_status | 仮想SL円価格・距離pips・DEFINED / UNDEFINED / UNKNOWN |
| observation_end / observation_bars / outcome_status | 基準足の次から12本の終了時刻・取得済み本数0〜12・COMPLETE / PARTIAL / UNKNOWN |
| mfe_pips / mae_pips / mfe_r / mae_r | 非負の最大順行幅／逆行幅。下記の固定期間観測値 |
| reached_1r / reached_1_5r | TRUE / FALSE / UNKNOWN / NA。期間未完了で未到達ならUNKNOWN |
| first_1r / first_1_5r | ADVERSE_FIRST / FAVORABLE_FIRST / SAME_BAR / NEITHER / UNKNOWN / NA |
| notes | データ不足、構造識別、元ラベル、実売買との区別、訂正の旧値・新値・日時・根拠 |

同一始点・終点・方向を1観察とし、複数理由や画像追加で行を増やさない。親なしの場合もnotesに構造識別を固定する。判定不能が後に解消したら同じIDで訂正履歴を残す。正式適格性が確認できた場合のみ正本に記録し、対応する観察は集計対象から外すことをレビューで明記する（勝敗を見て移さない）。

## 見送り理由

| 理由 | 境界・終結時点 |
| --- | --- |
| IMPULSE_TOO_LARGE / IMPULSE_TOO_SMALL | >35 / <10pips |
| IMPULSE_TOO_LONG / IMPULSE_TOO_SHORT | >8 / <2間隔 |
| PULLBACK_TOO_SHALLOW | <20%。途中はWATCH、最終6本目まで成立せず終了した時に記録 |
| PULLBACK_TOO_DEEP | 一度でも>70%でINVALID |
| NO_TRIGGER | 終点後6本目まで規定トリガーなし |
| STOP_TOO_WIDE / STOP_TOO_TIGHT | >20 / <4pips |
| SPREAD | >0.5pip。不明はAMBIGUOUS_DATA |
| EVENT_WINDOW | 既存の指定イベント禁止区間。不明はAMBIGUOUS_DATA |
| OUT_OF_SESSION | Entryが01:00以上08:00未満 |
| AMBIGUOUS_DATA | 必要OHLC・確定状態・候補順位・spread・イベント等が不足 |
| INVALID_STOP_SIDE | SLの方向不正 |
| IMPULSE_ALREADY_USED | 同じインパルスの再利用。新しい機会として件数を増やさず元記録／ミスログに追記 |

理由別は複数ラベル集計なので合計が全件数を超える。主理由へ恣意的に一本化しない。未知理由は集計エラーとして修正する。

## 見送り後の測定（観測仕様 v1）

測定方法を結果を見て変更しない。トリガーが既存の時点・価格構造で識別できる場合はTRIGGER_CLOSE、識別できない場合は除外を初めて確認できた確定足のREJECTION_CLOSEを固定する。基準時刻と価格の根拠がない場合はUNKNOWNのまま。形成中の終点高値を基準終値の代用にしない。

基準足を除き次の連続12本（60分）を観察。途中の+1R・+1.5R・−1Rで観測を打ち切らない。欠損補間禁止。方向符号sはLONG=1、SHORT=−1。LONGのMFE=max(0,最高値−基準価格)/0.01、MAE=max(0,基準価格−最安値)/0.01。SHORTは高安と差の向きを反転する。

既存のトリガーとその前の押し戻りPが識別でき、方向に正しいP±1pipのSLを計算できる場合だけRを定義する。距離が4〜20外でも観測上の分母は元の距離を保持し、適格トレードとはしない。単なる大きなインパルスやNO_TRIGGERでP・Entryが定義不能ならr_status=UNDEFINED、SL・距離・R・R到達・先後はNA。任意の4pipsや20pipsを代入しない。定義可能性自体が不明ならUNKNOWN。

MFE_R=MFE_pips/距離pips、MAE_R=MAE_pips/距離pips（初期分母固定、コスト前）。+1R/+1.5Rと−1Rに触れた最初の足番号を保存根拠から比較しfirst列を記録。同一5分足はSAME_BARとし、防御評価では保守的なSL先行参考件数にも表示するが、確定したADVERSE_FIRSTと区別する。どちらも未到達のNEITHERは12本完了時のみ。片側のみ到達ならその側が先行。

これらは固定60分の値動きであり純損益・勝率ではない。正式CSVのMFE/MAEは決済時までの保守的下限値なので直接同一指標として比較しない。理由別・基準種別別・CONFIRMED/PROVISIONAL別に、全件数、完了件数、R定義件数、指標ごとの有効分母と欠損を表示する。結果の良い場面だけ選ばず観測開始時点から連続記録し、事後観察は別とする。

## 30件レビューと変更候補

勝ち／負けはコスト控除後result_rの符号。TIME_STOPは出口理由であり勝ち負けと重なる。Openは適格性確認済みの仮想保有未決済。決済済みでもコスト不明はOpenではなく不足保留。

既存notesに `test_mode=forward;eligibility=CONFIRMED;position_status=OPEN|CLOSED;exit_reason=TP|SL|GAP_SL|TIME_STOP` を機械可読で追加し、観測開始・受領・判定・コスト根拠は従来どおり残す。これは37列の拡張ではなく記入方法。既存行で不足する項目は推測せず補完待ちにする。TRUEでも必要情報が欠ける行は集計監査エラーとし、黙って除外しない。

最初の30有効完了IDを時系列順に表示し、それ以前のPENDINGがあれば母集団確定を保留する。30件まではv0.1を維持する。変更案は下の表へOBSERVATION／v0.2 candidateとして別記し、適用しない。30件後も主要フィルター変更・追加は最大2個、旧結果保持、新規データと別採用基準が必要。

| 登録日 | 種別 | 根拠opportunity_id | 観察・変更候補 | 判定 |
| --- | --- | --- | --- | --- |
| 2026-09-15 | OBSERVATION | OPP-HYP009-20260915-001 | 大きく長い上昇を見送るケースの蓄積 | データ収集中。閾値変更案は未登録 |

## 今回の監査・不足

既存追跡27ファイルを確認。正式CSVはヘッダーのみ。月次の2件はHYP-008関連OBSERVEDで、通常009・派生の実績にはならない。

- 依頼の「2〜8本」は既存では両端を含む本数ではなく間隔数。「押し1〜5本」の次のトリガーは2〜6本目。既存定義を採用。
- 通常の固定1.5Rと派生ロックは出口が異なるため専用記録を維持。
- 既存CSVのFALSE/PENDING保存と専用見送りログは親IDで整合させる。
- 仮説管理READMEに「HYP-008のみTESTING」という古い現況記述があるため、案内部分のみ訂正。凍結本文・protocol内の初回0件は履歴として保持。
- 今回事例の154.700→155.086は約38.6pips、20:35→21:20は約9間隔。指定された組は正式インパルスに採用せず、IMPULSE_TOO_LARGEとIMPULSE_TOO_LONGの暫定見送り。左右スイング・足時刻の意味・画像・正確なOHLC・観測開始/判定時刻・後続12本・P/トリガー・spread・イベント・コストは未確認。他の短い適格インパルスの不存在までは断定しない。
- 見送り後の基準終値・SLが不明なのでRはNA、MFE/MAE_pipsはUNKNOWN。上昇38.6pipsを見送り後のMFEに転用しない。
