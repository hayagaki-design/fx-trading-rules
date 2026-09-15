# HYP-009 AUTO OBSERVER v0.1

[実装](hyp009_auto_observer.py)は、CSVまたは将来のMarket Data Adapterから渡された**確定済みUSDJPY・5分足**を時系列で観測し、[凍結済みHYP-009 v0.1](../03_hypotheses/HYP-009-5m-impulse-pullback-continuation.md)と[採点規約](HYP-009-v0.1-protocol.md)を実行する。売買条件の定義や変更、証券会社API接続、注文・発注・決済注文は行わない。

## 入力CSV

必須ヘッダーは `timestamp,open,high,low,close`。`timestamp` は**足の終値時刻**をISO 8601のタイムゾーン付きで保存する。例：`2026-09-16T09:25:00+09:00`。UTC等もJSTへ変換する。始値時刻のCSVをそのまま投入しない。入力を古い→新しい順へ並べ直し、重複時刻、OHLC矛盾、NaN/無限大、欠損、5分未満の間隔を拒否する。5分超の欠損は補間せず、進行中の候補・出口をINSUFFICIENTとして止める。

任意ヘッダー：

| 列 | 値と意味 |
| --- | --- |
| `spread_pips` または `spread` | Entry時の実測pips。未提供はspread_unknown。0.5超はNO TRADE |
| `event_blocked` | TRUE/FALSE。既存7種類のイベント発表−10分〜＋15分（両端含む）のEntry禁止を**入力側で**計算した値。未提供はevent_time_unknown |
| `event_tag` | event/non-event。上の禁止幅とは別に、インパルス始点〜Entryと発表−10分〜＋60分の重なりによる分類。未提供はUNKNOWN |
| `roundtrip_cost_pips` | 仮想Entry/Exitの価格系列に**含まれていない**往復実測コスト。未提供はcost_unknown。0は実測・価格系列の根拠がある場合のみ使用 |
| `closed` | TRUE/FALSE。列がなければCSV全行を確定済み足とみなす。FALSEは末尾の形成中足だけ許容し、WATCHだけ返す。UNKNOWNは拒否 |
| `symbol` / `timeframe` | 任意の整合検査列。USDJPY / 5m（またはM5）のみ許容 |

OHLCは価格系列（mid/bid/ask）を`--price-series`でも指定する。系列が不明なら純Rを確定しない。価格に含まれるスプレッドと別途コストを二重控除しないため、元データの価格系列・計測根拠を確認して入力する。[人工Golden CSV](fixtures/hyp009-golden-long.csv)は仕様テスト用で、市場実績やフォワード30件ではない。

## 実行

リポジトリ直下から実行する。指定がなければdry-runで、**既存の正式CSV・見送りCSVを書き換えない**。

```powershell
python -B 06_statistics/hyp009_auto_observer.py --input 06_statistics/fixtures/hyp009-golden-long.csv --dry-run --forward-observed-at 2026-09-16T09:00:00+09:00 --price-series mid
```

実行例の主な出力は `candles_processed=7`、`confirmed_swings=2`、`impulse_candidates=1`、`valid_completed_samples=1`、Entry `150.21`、SL `150.13`、固定TP `150.33`、仮想TP結果 `1.4875R`。**人工データのテスト結果**であり現実の正式サンプル数ではない。

実データを書き込む場合だけ`--write`を指定する。実行前にdry-runの判定とデータ出所を確認する。`--formal-csv`/`--opportunities-csv`はテスト・隔離したCSVへの明示的な出力先指定で、通常は既存正本を使う。入力ファイルの絶対パスとSHA-256を監査情報へ記録する。

```powershell
python -B 06_statistics/hyp009_auto_observer.py --input C:/path/to/usdjpy-m5.csv --write --price-series mid --forward-observed-at 2026-09-16T09:00:00+09:00
```

`--forward-observed-at`は固定後に実際に連続観測を開始した時刻が分かる場合だけ指定する。過去ファイルの後日読み直しには指定しない。ソフトウェアは入力者が後から時刻を偽っていないかを証明できないため、元データ・受領時刻の証拠を保管する。指定がない場合、シグナルとgross Rを計算できても`forward_provenance_unknown`として正式30件の有効完了にはしない。

## 状態と記録

エンジンは右側1本が**確定してから**スイングを登録する。各判定の`start/end`足時刻と`start/end_confirmed_at`、候補順位、インパルス幅・間隔、押し戻り・トリガー、Entry/SL/TP、仮想出口、R、見送り理由を出力・notesへ残す。形成中足ではTRIGGEREDを出さない。Entryは確定トリガー足の終値から動かさない。

価格シグナルが成立しても、spread・イベント・往復コスト・価格系列・フォワード観測開始の根拠が不明ならPENDING / INSUFFICIENT_DATA。勝敗を推測しない。正式37列CSVではTRUEの**有効完了**だけが成績対象で、FALSE/PENDING行も既存採点規約どおり保持する。トリガー前の見送りは別CSVのみ、トリガー後のNO TRADEは正式CSVのFALSE行と別CSVを`parent_case_id`で結ぶ。見送り・派生1.5Rロックは通常009の勝率・期待値・PFに加算しない。[現況集計](summarize_hyp009.py)で確認する。

正式`case_id`は既存仕様の`HYP009-v01-NNNN`連番。見送り`opportunity_id`は`OPP-HYP009-YYYYMMDD-NNN`。判定時に始点・終点・方向の`structure_key`を固定し、`--write`再実行では既存IDを使う。エンジンが作った行だけ更新し、手入力の同一構造行は上書きせず停止する。既存の概算観察と価格が近い同日の事例も、勝手に別IDへ確定させず手動照合を要求する。

適格候補は「最新終点→同一終点の最新始点」で選ぶ。適格候補がない場合の**見送り観測**は、確定した終点に対する最新の反対スイング始点だけを評価し、全足組み合わせを生成しない。既に選択中の形の押し足は新しい見送り候補にしない。これは観測ログの抽出方法であり、v0.1の正式採点条件を変更しない。

見送り後は、確定足のreference closeから次の連続12本を観測する。途中で欠損足があれば観測を停止してPARTIALと記録し、後の足を12本へ詰めない。Pと正しい仮想SLがない場合はMFE/MAEのpipsのみ記録し、R・1R/1.5R到達・先後はNA。足内の有利な順序を推測しない。正式トレードのMFE/MAEは決済前の完了足OHLCと決済足の始値・仮想決済価格のみで計算し、決済後の高安・未来足を含めない。

## 将来の入力アダプター

Market Data Adapterは、GMOや外部FXデータから取得した足を、価格系列・スプレッド・イベントカレンダー・コスト根拠・確定状態とともに`Candle`へ変換して`Observer.feed()`へ渡せる。形成中足は`closed=False`でWATCH、確定後だけ`closed=True`で逐次投入する。アダプターが日時の意味、欠損、イベント禁止幅、コストを検証する必要がある。Observer本体はブローカーに依存しない。注文機能は設計対象外。
