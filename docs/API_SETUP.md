# API設定手順書
このドキュメントでは、スケジュール管理自動化システムで使用する各APIの設定手順を詳しく説明します。
## 目次
1. [Gmail API設定](#gmail-api設定)
2. [Slack API設定](#slack-api設定)
3. [GitHub API設定](#github-api設定)
4. [Google Calendar API設定](#google-calendar-api設定)
5. [Notion API設定](#notion-api設定)
## Gmail API設定
### 1. Google Cloud Consoleでプロジェクト作成
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成または既存プロジェクトを選択
3. 「APIとサービス」→「ライブラリ」から「Gmail API」を有効化
### 2. OAuth 2.0認証情報の作成
1. 「APIとサービス」→「認証情報」に移動
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. アプリケーションの種類：「デスクトップアプリケーション」
4. 名前を入力して作成
5. クライアントIDとクライアントシークレットをメモ
### 3. OAuth同意画面の設定
1. 「OAuth同意画面」タブに移動
2. ユーザータイプ：「外部」を選択（個人用の場合）
3. 必要な情報を入力：
   - アプリ名
   - ユーザーサポートメール
   - 開発者の連絡先情報
### 4. スコープの追加
以下のスコープを追加：
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.labels`
### 5. リフレッシュトークンの取得
```python
# 以下のスクリプトを実行してリフレッシュトークンを取得
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
def get_refresh_token():
    flow = InstalledAppFlow.from_client_config({
        "installed": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }, SCOPES)
    
    creds = flow.run_local_server(port=0)
    print(f"Refresh Token: {creds.refresh_token}")
if __name__ == '__main__':
    get_refresh_token()
```
### 6. 環境変数の設定
`.env`ファイルに以下を追加：
```env
GMAIL_CLIENT_ID=your_client_id_here
GMAIL_CLIENT_SECRET=your_client_secret_here  
GMAIL_REFRESH_TOKEN=your_refresh_token_here
```
## Slack API設定
### 1. Slack Appの作成
1. [Slack API](https://api.slack.com/apps)にアクセス
2. 「Create New App」→「From scratch」を選択
3. アプリ名とワークスペースを選択
### 2. Bot Tokenスコープの設定
「OAuth & Permissions」セクションで以下のスコープを追加：
**Bot Token Scopes:**
- `channels:history` - チャンネルメッセージの読み取り
- `channels:read` - チャンネル情報の読み取り
- `users:read` - ユーザー情報の読み取り
- `group:history` - グループメッセージの読み取り
- `group:read` - グループ情報の読み取り
- `im:history` - ダイレクトメッセージの読み取り
- `mpim:history` - グループダイレクトメッセージの読み取り
**User Token Scopes:**
- `search:read` - メッセージ検索
### 3. アプリのインストール
1. 「Install App」セクションでワークスペースにアプリをインストール
2. Bot User OAuth TokenとUser OAuth Tokenを取得
### 4. 環境変数の設定
`.env`ファイルに以下を追加：
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_USER_TOKEN=xoxp-your-user-token-here
SLACK_WORKSPACE_ID=your-slack-workspace-id
```

Slack の Bot トークンとワークスペース ID を .env に設定したら、start_claude_desktop.bat（または python scripts/start_claude_desktop.py）を実行して最新のチャンネル一覧をキャッシュしてください。
### 1. Personal Access Tokenの作成
1. GitHubにログイン
2. 「Settings」→「Developer settings」→「Personal access tokens」→「Tokens (classic)」
3. 「Generate new token」→「Generate new token (classic)」を選択
### 2. 必要なスコープの選択
以下のスコープを選択：
- `repo` - プライベートリポジトリへのアクセス（必要に応じて）
- `read:org` - 組織情報の読み取り
- `read:user` - ユーザー情報の読み取り
### 3. 環境変数の設定
`.env`ファイルに以下を追加：
```env
GITHUB_TOKEN=ghp_your_personal_access_token_here
```
## Google Calendar API設定
### 1. Google Cloud Consoleでの設定
Gmail APIと同じプロジェクトを使用可能：
1. 「APIとサービス」→「ライブラリ」から「Google Calendar API」を有効化
2. 既存のOAuth 2.0クライアントIDを使用可能
### 2. スコープの追加
以下のスコープを追加：
- `https://www.googleapis.com/auth/calendar.readonly`
### 3. リフレッシュトークンの取得
Gmail APIと同様の手順でリフレッシュトークンを取得：
```python
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
# 上記のGmail APIと同じスクリプトを使用、SCOPESを変更
```
### 4. 環境変数の設定
`.env`ファイルに以下を追加：
```env
GOOGLE_CALENDAR_CLIENT_ID=your_client_id_here
GOOGLE_CALENDAR_CLIENT_SECRET=your_client_secret_here
GOOGLE_CALENDAR_REFRESH_TOKEN=your_refresh_token_here
```
## Notion API設定
### 1. Notion Integrationの作成
1. [Notion Developers](https://www.notion.so/my-integrations)にアクセス
2. 「New integration」をクリック
3. 以下の情報を入力：
   - Name: スケジュール管理自動化
   - Associated workspace: 使用するワークスペースを選択
   - Capabilities: 「Read content」「Update content」「Insert content」を選択
### 2. Integration Tokenの取得
作成後に表示される「Internal Integration Token」をコピー
### 3. NotionデータベースのセットアップT
#### データベースの作成
1. Notionで新しいページを作成
2. 「/database」と入力してデータベースを作成
3. 以下のプロパティを設定：
| プロパティ名 | タイプ | 設定 |
|------------|--------|------|
| 完了 | Checkbox | - |
| タスク名 | Title | - |
| カテゴリ | Select | Email, Slack, GitHub, Calendar |
| 優先度 | Select | High, Medium, Low |
| 期限 | Date | - |
| 完了予定日 | Date | - |
| 完了日 | Date | - |
| ソースURL | URL | - |
| 説明 | Text | - |
| ステータス | Select | 未対応, 進行中, 完了 |
#### データベースの共有
1. データベースページの右上「Share」をクリック
2. 「Invite」セクションで作成したIntegrationを検索して追加
3. 権限を「Can edit」に設定
#### データベースIDの取得
データベースのURLから32文字のIDを取得：
```
https://www.notion.so/workspace/DATABASE_ID?v=...
```
### 4. 環境変数の設定
`.env`ファイルに以下を追加：
```env
NOTION_TOKEN=secret_your_integration_token_here
NOTION_DATABASE_ID=your_32_character_database_id_here
```
## 設定の確認
すべてのAPI設定が完了したら、以下のコマンドで設定を確認：
```bash
python scripts/validate_config.py
```
このスクリプトは各APIへの接続をテストし、設定の問題を特定します。
## セキュリティのベストプラクティス
1. **トークンの管理**
   - `.env`ファイルは絶対にバージョン管理に含めない
   - 定期的にトークンを更新する
   - 不要になったトークンは無効化する
2. **最小権限の原則**
   - 必要最小限のスコープのみを付与
   - 読み取り専用権限を優先
3. **アクセス制御**
   - Notion Integrationは必要なデータベースのみに制限
   - Slack Appは必要なワークスペースのみにインストール
## トラブルシューティング
API設定で問題が発生した場合は、[TROUBLESHOOTING.md](TROUBLESHOOTING.md)を参照してください。
