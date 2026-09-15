# Changelog

## HYP-009 1.5R lock variant and canonical chart assessment — 2026-09-15

- 1.5R到達後の対象保有への明示宣言による継続案を、HYP-009-lock-1.5R v0.1 / HYPOTHESISとして追加。採用基準未固定、検証0件、正式採用なし。
- 宣言・保有・ストップ変更有効化・実際の決済の観察様式を追加。既TP約定の付け替え禁止。初期Rと元Entry後12本期限を継承。
- 通常009の仮想出口との対比較、通常／派生および実注文／デモ／仮想の別集計を明記。日次実注文制限は共有し二重計上しない。
- 5分足009・15分足008、確定足のみ、短い判定と保有後表示のチャート運用正本を追加。注文不可・未確認時はENTRYと案内しない。
- README・台帳・統計案内を同期。HYP-008と通常HYP-009の固定文書・CSV・protocolは変更なし。
- 別環境のコミット582883d40834a62300d8e156b752f90bbeefc81dと指定パッチはこの環境に存在せず、ユーザーの要件から再作成。既存履歴は保持。

## HYP-009 v0.1 and risk sizing rules — 2026-09-14

- 全体資金管理として判定時口座残高の1取引最大0.5%を固定。SL幅から逆算し、発注単位へ切り下げる。絶対最大ロットはUNKNOWN。
- HYP-009 v0.1をTESTINGで追加。固定日時2026-09-14T13:31:09+09:00。USDJPY 5分足の高頻度探索戦略（頻度自体は未検証）。
- HYP-009のみ実注文リスク0.25%。日次最大4回 / 累計−1.0%以下 / 3連敗で実注文停止。停止後も仮想シグナルを記録。
- インパルス10〜35pips・2〜8間隔、押し・戻し20〜70%・1〜5本、トリガー実体比率40%以上。トリガー対象はユーザー確認により終点後2〜6本目に統一。
- SL幅4〜20pips、TP1.5R、12本タイムストップ。スプレッド上限0.5pip、重要イベント禁止区間を設定。
- 初回フォワード30件。30件だけでは正式採用しない。変更は別版、主要フィルター最大2個、旧結果を保持。
- 専用CSV（データ0件）・protocol追加。仮説台帳・統計案内を同期。GMO注文数量表記は操作メモとして記録。
- HYP-008の固定条件・専用文書・CSV・protocol・結果は変更なし。HYP-009とは完全別集計。HYP-001〜007はHYPOTHESISのまま、正式採用0件。

## HYP-008 v0.1 criteria freeze — 2026-09-11

- Test Criteria Fixed At: 2026-09-11T15:18:37+09:00（Asia/Tokyo）。
- HYP-008のみHYPOTHESIS → TESTING。USDJPY 15分足、帯・試行・支持割れ・戻り・固定SL/1.5R TP・16本タイムストップ・時間・イベント・除外・コストを初回固定。
- 過去30件＋フォワード20件の昇格・却下候補基準を固定。条件を満たしても本人レビューまで正式採用しない。
- 条件の境界・足内順序・構造重複・抽出期間と順序・イベントと環境タグ・利益集中計算を採点規約として明記。
- 専用CSV（実データ0件）と記入・集計仕様を追加。README類の現在状態を同期。
- Change Reason: ユーザーの指定に基づき、未検証案を初回固定して検証可能にするため。固定前の文書は初期コミットd0078b2d8b9be062f1fec42b0ed34bf26317d98dに保持。
- HYP-001〜007の条件・状態、既存OBSERVED、正式採用0件は変更なし。固定後の変更はv0.2を別作成し、旧条件・結果を保持して成績を混ぜない。

## v0.1 — 2026-09-11

- repository initial structure
- trading philosophy created
- hypothesis management introduced
- trade log introduced
- rule lifecycle introduced
- first USDJPY observations added
- hypothesis version fields and pre-test criteria freezing policy added
- previous versions and test results must be preserved with change dates and reasons

初期思想7件とセットアップ候補1件をHYPOTHESISとして登録。2026-09-10・2026-09-11のUSDJPY事例をOBSERVEDとして保存。正式採用ルール0件、完了した検証0件。成績の推測は行っていない。
