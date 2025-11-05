---
name: today-tasks
description: Collect daily updates via MCP, summarise todos, and report errors.
help: >
  Run once after refreshing tokens. Executes Gmail, Slack, GitHub, Calendar,
  Notion checks plus daily summary and error analysis.
model: claude-3.5-sonnet
---
# 依頼内容
以下のフローを順番に実行し、結果を 1 レポートにまとめてください。
Notionへの出力およびレポートは日本語でおこなってください。

手順:
1. Gmail MCP で過去24時間に to:me で届いた未返信メールのうち、対応が必要なものを抽出します。メルマガや広告系メールは除外してください。
   出力: 件名 / 差出人 / 受信日時 / 要対応内容（1 行）/ 優先度 / メッセージ URL。
2. Slack MCP で過去 24 時間のメンションと DM を取得。
   出力: チャンネル名 / 発言者 / メッセージ要約 / スレッド URL / 必要なアクション。
3. GitHub MCP で自分に割り当てられた Open Issue を確認。
   出力: Issue タイトル / リポジトリ / ラベル / 最新更新 / 必要なアクション / URL。
4. Google Calendar MCP で本日と翌日の予定を取得。
   出力: イベント名 / 開始・終了（JST）/ 所要時間 / 会議 URL または場所 / 準備事項。
5. Notion MCP でタスクをデータベースに登録してください。カテゴリには情報源種別（Email / Slack / GitHub / Calendar）を、優先度には緊急度評価（High / Medium / Low）を設定し、登録ルールはnotion登録情報を参照してください。
6. 1〜5 の情報を基に日報を作成。
   - ✅ 完了したこと
   - ⏳ 進行中のタスク（課題・ブロッカー）
   - 📅 明日の予定（確定スケジュール）
   - 🔔 フォローが必要な事項
7. 途中でエラーが発生した MCP があれば、次の形式でまとめる:
   - 原因
   - 対処
   - 追加確認事項
   - 再試行が必要な手順

注意事項:
- 途中でエラーが出た場合でも残りのステップを可能な限り続行し、最後にエラー情報を記録してください。
- Notion への登録は重複しないように確認してから実施すること。
- Notion に登録する前に、カテゴリと優先度の値がそれぞれ正しい候補から選ばれているか必ず確認してください。報告は不要です。（カテゴリ=情報源、優先度=緊急度）。

# noiton登録情報
## 単一TODOアイテム作成

```
各MCPサーバーから取得した情報をNotion MCPサーバーを使用して、以下の情報でTODOアイテムを作成してください：

タスク名: {TASK_TITLE}
カテゴリ: {CATEGORY}
優先度: {PRIORITY}
期限: {DUE_DATE}
完了予定日: {EXPECTED_COMPLETION_DATE}
ソースURL: {SOURCE_URL}
説明: {DESCRIPTION}
ステータス: 未対応

```

※ カテゴリと優先度を取り違えないようにしてください。カテゴリには情報源種別（Email / Slack / GitHub / Calendar など）を、優先度には High / Medium / Low のいずれかを設定します。

### カテゴリと優先度の整合チェック

Notion に送信する前に、以下の条件を満たしていることを確認してください。

- カテゴリは情報源種別のみ: `Email` / `Slack` / `GitHub` / `Calendar`（必要に応じて `Other` など事前に合意した値）。
- 優先度は緊急度のみ: `High` / `Medium` / `Low`。
- `カテゴリ` に `High` や `Medium` が入っていないこと。
- `優先度` に `Email` や `Slack` が入っていないこと。

チェック段階で不一致を見つけた場合は、該当タスクの値を修正してから Notion MCP を呼び出します。


## カテゴリ別データ分類プロンプト

### 2.1 Gmail データの場合

```
以下のGmailデータをNotion TODOアイテムに変換してください：

Gmail情報:
- 件名: {EMAIL_SUBJECT}
- 送信者: {SENDER}
- 受信日時: {RECEIVED_DATE}
- メールURL: {EMAIL_URL}

変換ルール:
- タスク名: メール件名をそのまま使用
- カテゴリ: "Email"
- 優先度: 送信者のドメインが会社ドメインなら "High"、その他は "Medium"
- 期限: 受信日+2日
- 完了予定日: 受信日+1日
- ソースURL: メールURL
- 説明: "送信者: {SENDER}, 受信日時: {RECEIVED_DATE}"
- ステータス: "未対応"

Notion MCPサーバーを使用してTODOアイテムを作成してください。
```

### 2.2 Slack データの場合

```
以下のSlackメンションデータをNotion TODOアイテムに変換してください：

Slack情報:
- メッセージ内容: {MESSAGE_CONTENT}
- 送信者: {SENDER}
- チャンネル名: {CHANNEL_NAME}
- 投稿日時: {POSTED_DATE}
- メッセージURL: {MESSAGE_URL}

変換ルール:
- タスク名: メッセージ内容の最初の50文字 + "への返信"
- カテゴリ: "Slack"
- 優先度: チャンネル名に "urgent" や "重要" が含まれる場合 "High"、その他は "Medium"
- 期限: 投稿日+1日
- 完了予定日: 投稿日+8時間
- ソースURL: メッセージURL
- 説明: "送信者: {SENDER}, チャンネル: {CHANNEL_NAME}, 投稿日時: {POSTED_DATE}"
- ステータス: "未対応"

Notion MCPサーバーを使用してTODOアイテムを作成してください。
```

### 2.3 GitHub データの場合

```
以下のGitHubイシューデータをNotion TODOアイテムに変換してください：

GitHub情報:
- イシュータイトル: {ISSUE_TITLE}
- リポジトリ名: {REPOSITORY_NAME}
- ラベル: {LABELS}
- 作成日: {CREATED_DATE}
- イシューURL: {ISSUE_URL}

変換ルール:
- タスク名: イシュータイトルをそのまま使用
- カテゴリ: "GitHub"
- 優先度: ラベルに "bug" や "critical" が含まれる場合 "High"、"enhancement" なら "Low"、その他は "Medium"
- 期限: 作成日+7日（マイルストーンがある場合はその日付）
- 完了予定日: 作成日+5日
- ソースURL: イシューURL
- 説明: "リポジトリ: {REPOSITORY_NAME}, ラベル: {LABELS}, 作成日: {CREATED_DATE}"
- ステータス: "未対応"

Notion MCPサーバーを使用してTODOアイテムを作成してください。
```

### Google Calendar データの場合

```
以下のGoogle CalendarイベントデータをNotion TODOアイテムに変換してください：

Calendar情報:
- イベントタイトル: {EVENT_TITLE}
- 開始時刻: {START_TIME}
- 終了時刻: {END_TIME}
- 場所: {LOCATION}
- イベントURL: {EVENT_URL}

変換ルール:
- タスク名: イベントタイトル + "の準備"
- カテゴリ: "Calendar"
- 優先度: "Medium"（固定）
- 期限: イベント開始時刻
- 完了予定日: イベント開始時刻
- ソースURL: イベントURL
- 説明: "場所: {LOCATION}, 時間: {START_TIME} - {END_TIME}"
- ステータス: "未対応"

Notion MCPサーバーを使用してTODOアイテムを作成してください。
```

## 重複チェックと更新処理プロンプト例

### 重複チェック実行

```
Notion MCPサーバーを使用して、以下の条件で重複TODOアイテムをチェックしてください：

データベースID: {DATABASE_ID}
チェック対象:
- タスク名: "{TASK_TITLE}"
- カテゴリ: "{CATEGORY}"
- ソースURL: "{SOURCE_URL}"

検索条件:
1. タスク名が完全一致するアイテム
2. ソースURLが完全一致するアイテム
3. カテゴリが同じで、タスク名が80%以上類似するアイテム

重複が見つかった場合は、既存アイテムのページIDとタイトルを教えてください。
重複がない場合は、新規作成可能と報告してください。
```

### 既存アイテム更新

```
Notion MCPサーバーを使用して、既存のTODOアイテムを更新してください：

ページID: {PAGE_ID}
更新内容:
- 優先度: {NEW_PRIORITY}
- 期限: {NEW_DUE_DATE}
- 完了予定日: {NEW_EXPECTED_DATE}
- 説明: {UPDATED_DESCRIPTION}
- ステータス: {NEW_STATUS}

更新理由: 重複データの統合により最新情報に更新

更新完了後、更新されたプロパティの一覧を教えてください。
```

### 3.3 重複アイテム統合

```
Notion MCPサーバーを使用して、重複するTODOアイテムを統合してください：

保持するアイテム（メイン）:
- ページID: {MAIN_PAGE_ID}
- タスク名: {MAIN_TASK_TITLE}

削除するアイテム（重複）:
- ページID: {DUPLICATE_PAGE_ID}
- タスク名: {DUPLICATE_TASK_TITLE}

統合処理:
1. メインアイテムの説明欄に重複アイテムの情報を追記
2. より厳しい期限がある場合は期限を更新
3. より高い優先度がある場合は優先度を更新
4. 重複アイテムを削除

統合完了後、最終的なメインアイテムの内容を教えてください。
```

## 優先度と期限自動設定プロンプト例

### 優先度自動判定

```
以下の情報を基に、TODOアイテムの優先度を自動判定してください：

判定対象:
- カテゴリ: {CATEGORY}
- タスク名: {TASK_TITLE}
- 送信者/作成者: {CREATOR}
- キーワード: {KEYWORDS}
- 作成日時: {CREATED_DATE}

判定ルール:
【High優先度】
- Email: 会社ドメインからのメール、件名に「緊急」「至急」「ASAP」
- Slack: チャンネル名に「urgent」「重要」、メンションが複数回
- GitHub: ラベルに「bug」「critical」「security」
- Calendar: 1時間以内に開始予定のイベント

【Medium優先度】
- Email: 外部からのビジネスメール
- Slack: 通常のメンション
- GitHub: 通常のイシュー、「enhancement」以外
- Calendar: 通常のイベント

【Low優先度】
- Email: ニュースレター、自動通知
- GitHub: 「enhancement」「documentation」ラベル
- その他: 上記に該当しないもの

判定結果と理由を教えてください。
```

### 期限自動設定

```
以下の情報を基に、TODOアイテムの期限を自動設定してください：

設定対象:
- カテゴリ: {CATEGORY}
- 優先度: {PRIORITY}
- 作成日時: {CREATED_DATE}
- 関連イベント日時: {RELATED_EVENT_DATE}

設定ルール:
【Email】
- High優先度: 作成日+1日
- Medium優先度: 作成日+2日
- Low優先度: 作成日+7日

【Slack】
- High優先度: 作成日+4時間
- Medium優先度: 作成日+1日
- Low優先度: 作成日+3日

【GitHub】
- High優先度: 作成日+2日
- Medium優先度: 作成日+7日
- Low優先度: 作成日+14日

【Calendar】
- 全優先度: イベント開始時刻

計算された期限日時を教えてください。
```

## 完了予定日・完了日の自動設定プロンプト例

### 完了予定日自動設定

```
以下の情報を基に、TODOアイテムの完了予定日を自動設定してください：

設定対象:
- カテゴリ: {CATEGORY}
- 優先度: {PRIORITY}
- 期限: {DUE_DATE}
- 作成日時: {CREATED_DATE}

設定ルール:
【基本ルール】
- 完了予定日 = 期限 - バッファ時間

【バッファ時間】
- High優先度: 期限の25%前（最低2時間）
- Medium優先度: 期限の50%前（最低4時間）
- Low優先度: 期限の75%前（最低1日）

【カテゴリ別調整】
- Email: バッファ時間 × 0.8
- Slack: バッファ時間 × 0.6
- GitHub: バッファ時間 × 1.2
- Calendar: バッファ時間なし（期限と同じ）

計算された完了予定日時を教えてください。
```

### 完了日自動設定

```
Notion MCPサーバーを使用して、TODOアイテムの完了処理を実行してください：

対象アイテム:
- ページID: {PAGE_ID}
- タスク名: {TASK_TITLE}

完了処理:
1. 完了チェックボックスをONに設定
2. 完了日を現在日時に設定
3. ステータスを「完了」に変更
4. 説明欄に完了日時を追記

更新内容:
- 完了: ✓
- 完了日: {CURRENT_DATETIME}
- ステータス: 完了
- 説明: 既存の説明 + "\n完了日時: {CURRENT_DATETIME}"

処理完了後、更新されたアイテムの情報を教えてください。
```

### 一括完了処理

```
Notion MCPサーバーを使用して、複数のTODOアイテムを一括完了処理してください：

対象アイテム:
{COMPLETED_ITEMS_LIST}

各アイテムに対して以下の処理を実行:
1. 完了チェックボックスをONに設定
2. 完了日を現在日時に設定
3. ステータスを「完了」に変更

処理完了後、各アイテムの処理結果（成功/失敗）を報告してください。
```
