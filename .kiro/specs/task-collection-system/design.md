# タスク収集システム 設計書

## 概要

タスク収集システムは、既存の `task_managemer_` をベースとした、Claudeを活用したスケジュール管理自動化システムです。Gmail・Slack・GitHub・Google Calendar・Notionとの統合により、各サービスからの情報収集とTODO管理を自動化します。requirements.txt を使用したPython依存関係管理、MCPサーバーとの統合、Google API認証の自動化を通じて、開発者が効率的にタスク管理環境を構築・運用できるよう設計されています。

## アーキテクチャ

### システム全体構成

```mermaid
graph TB
    subgraph "タスク収集システム"
        SM[SetupModule]
        AM[AuthenticationModule]
        VM[ValidationModule]
        TRM[TokenRefreshModule]
        LM[LaunchModule]
    end
    
    subgraph "外部サービス"
        Gmail[Gmail API]
        Slack[Slack API]
        GitHub[GitHub API]
        Calendar[Google Calendar API]
        Notion[Notion API]
        ClaudeDesktop[Claude Desktop]
    end
    
    subgraph "MCPサーバー群"
        GmailMCP[gmail_server.py]
        SlackMCP[slack_server.py]
        GitHubMCP[github_server.py]
        CalendarMCP[calendar_server.py]
        NotionMCP[notion_server.py]
    end
    
    subgraph "ファイルシステム"
        ENV[.env File]
        SETTINGS[config/settings.json]
        CACHE[cache/slack/]
        LOGS[logs/]
        BAT[start_claude_desktop.bat]
    end
    
    SM --> ENV
    AM --> ENV
    AM --> SETTINGS
    VM --> GmailMCP
    VM --> SlackMCP
    VM --> GitHubMCP
    VM --> CalendarMCP
    VM --> NotionMCP
    TRM --> Gmail
    TRM --> Calendar
    TRM --> ENV
    LM --> ENV
    LM --> SETTINGS
    LM --> CACHE
    LM --> ClaudeDesktop
    BAT --> LM
    
    GmailMCP --> Gmail
    SlackMCP --> Slack
    GitHubMCP --> GitHub
    CalendarMCP --> Calendar
    NotionMCP --> Notion
```

### モジュール構成

```
task_managemer_/
├── .env                         # 環境変数（実際の認証情報）
├── .gitignore                   # Git除外設定
├── gmail_refresh_token.py       # Googleトークン取得用スクリプト
├── README.md                    # メインマニュアル
├── requirements.txt             # Python依存関係
├── start_claude_desktop.bat     # Claude Desktop起動バッチ
├── cache/                       # キャッシュディレクトリ
│   └── slack/                   # Slackメタデータキャッシュ
├── config/                      # 設定ファイル
│   ├── .env.template            # 環境変数テンプレート
│   ├── mcp.json                 # MCPサーバー設定
│   └── settings.json            # アプリケーション設定
├── docs/                        # ドキュメント
│   ├── API_SETUP.md             # API設定手順
│   ├── TROUBLESHOOTING.md       # トラブルシューティング
│   ├── notion_prompts.md        # Notionプロンプト
│   └── workflow_prompts.md      # ワークフロープロンプト
├── logs/                        # ログファイル
├── scripts/                     # 運用スクリプト
│   ├── setup.py                 # プロジェクト初期化
│   ├── start_claude_desktop.py  # Claude Desktop起動
│   ├── refresh_google_tokens.py # Googleトークン更新
│   └── ...                      # その他運用スクリプト
├── servers/                     # MCPサーバー群
│   ├── __init__.py
│   ├── base.py                  # ベースクラス
│   ├── gmail_server.py          # Gmail MCPサーバー
│   ├── slack_server.py          # Slack MCPサーバー
│   ├── github_server.py         # GitHub MCPサーバー
│   ├── calendar_server.py       # Google Calendar MCPサーバー
│   └── notion_server.py         # Notion MCPサーバー
└── tests/                       # テスト・検証スクリプト
    ├── validate_config.py       # 設定検証
    ├── test_individual_apis.py  # 個別API接続テスト
    └── test_servers.py          # MCPサーバーテスト
```

## コンポーネントと インターフェース

### 1. SetupModule (scripts/setup.py)

**責任**: プロジェクトの初期化処理

**主要機能**:
- requirements.txt を使用したPython依存関係のインストール
- config/.env.template から .env ファイルの生成
- 必要なディレクトリ構造の作成
- 初期設定の確認

**主要関数**:
```python
def ensure_directories(root: Path) -> List[Path]
def copy_env_template(root: Path, overwrite: bool) -> Path | None
def ensure_requirements(root: Path, install: bool) -> None
def main() -> None  # CLI エントリーポイント
```

### 2. AuthenticationModule (tests/)

**責任**: 認証情報の検証とテスト

**主要機能**:
- 環境変数と設定ファイルの整合性確認
- 各サービス（Gmail, Slack, GitHub, Google Calendar, Notion）への接続テスト
- 認証状態の詳細レポート

**主要ファイル**:
- `tests/validate_config.py`: 設定検証
- `tests/test_individual_apis.py`: 個別API接続テスト

### 3. ValidationModule (tests/test_servers.py)

**責任**: MCPサーバーとの通信テスト

**主要機能**:
- 各MCPサーバーの起動確認
- 基本的な機能テストの実行
- テスト結果のサマリー表示

**テスト対象MCPサーバー**:
- gmail_server.py
- slack_server.py  
- github_server.py
- calendar_server.py
- notion_server.py

### 4. TokenRefreshModule (scripts/refresh_google_tokens.py)

**責任**: Googleリフレッシュトークンの管理

**主要機能**:
- Gmail・Google Calendar のアクセストークン自動更新
- .env ファイルへの永続化またはプロセス環境変数への設定
- エラーハンドリングとログ記録

**主要関数**:
```python
def refresh_token(prefix: str) -> str
def update_env_file(env_path: Path, updates: dict[str, str]) -> None
def refresh_tokens(*, persist: bool = True, update_process_env: bool = True) -> dict[str, str]
```

### 5. LaunchModule (scripts/start_claude_desktop.py + start_claude_desktop.bat)

**責任**: Claude Desktop の適切な環境での起動

**主要機能**:
- 環境変数の読み込みと設定
- Slackチャンネルメタデータのキャッシュ
- PYTHONPATH の自動設定
- Claude Desktop の起動

**主要関数**:
```python
def ensure_env_loaded() -> None
def ensure_runtime_environment() -> None
def cache_slack_metadata() -> None
def maybe_refresh_tokens(settings: dict, args: argparse.Namespace, persist_tokens: bool) -> dict[str, str]
def launch_claude(claude_path: Path, wait: bool) -> None
```

## データモデル

### 環境変数構造 (.env)

```bash
# Gmail API Configuration
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token
GMAIL_ACCESS_TOKEN=your_gmail_access_token

# Slack API Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_USER_TOKEN=xoxp-your-slack-user-token
SLACK_WORKSPACE_ID=your_slack_workspace_id
SLACK_SELF_USER_ID=your_slack_user_id

# GitHub API Configuration
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_USERNAME=your_github_username

# Google Calendar API Configuration
GOOGLE_CALENDAR_CLIENT_ID=your_calendar_client_id
GOOGLE_CALENDAR_CLIENT_SECRET=your_calendar_client_secret
GOOGLE_CALENDAR_REFRESH_TOKEN=your_calendar_refresh_token
GOOGLE_CALENDAR_ACCESS_TOKEN=your_calendar_access_token

# Notion API Configuration
NOTION_TOKEN=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# Application Configuration
APP_LOG_LEVEL=INFO
APP_TIMEZONE=Asia/Tokyo
APP_DATE_FORMAT=%Y-%m-%d
APP_TIME_FORMAT=%H:%M:%S

# Security Configuration
ENCRYPTION_KEY=your_32_character_encryption_key_here
SESSION_SECRET=your_session_secret_key_here

# Rate Limiting Configuration
API_RATE_LIMIT_PER_MINUTE=60
API_TIMEOUT_SECONDS=30
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5
```

### 設定ファイル構造 (config/settings.json)

```json
{
  "desktop": {
    "claude_path": "C:/Users/<username>/AppData/Local/Claude/Claude.exe",
    "auto_refresh_google_tokens": true,
    "persist_google_tokens": true
  }
}
```

### Slackキャッシュ構造 (cache/slack/{workspace_id}_channels.json)

```json
{
  "workspace_id": "YOUR_WORKSPACE_ID",
  "fetched_at": "2024-01-01T12:00:00Z",
  "channel_count": 25,
  "channels": [
    {
      "id": "C1234567890",
      "name": "general",
      "is_private": false,
      "created": 1609459200,
      "num_members": 10
    }
  ]
}
```

### MCPサーバー設定構造 (config/mcp.json)

```json
{
  "gmail_server": {
    "command": "python",
    "args": ["-m", "servers.gmail_server"]
  },
  "slack_server": {
    "command": "python", 
    "args": ["-m", "servers.slack_server"]
  },
  "github_server": {
    "command": "python",
    "args": ["-m", "servers.github_server"]
  },
  "calendar_server": {
    "command": "python",
    "args": ["-m", "servers.calendar_server"]
  },
  "notion_server": {
    "command": "python",
    "args": ["-m", "servers.notion_server"]
  }
}
```

## エラーハンドリング

### エラー分類

1. **設定エラー**: 環境変数の不備、config/settings.json の問題
2. **認証エラー**: API トークンの無効化、各サービスへの認証失敗
3. **通信エラー**: MCPサーバーとの接続問題、外部API通信エラー
4. **システムエラー**: ファイルI/O、Python依存関係の問題
5. **Claude Desktop エラー**: 起動パスの問題、プロセス起動失敗

### エラーハンドリング戦略

既存実装では以下のアプローチを採用：

```python
# scripts/setup.py での例
try:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)])
except subprocess.CalledProcessError as exc:
    print(f'ERROR: 依存関係のインストールに失敗しました: {exc}')
    print('       コマンドを手動で再実行してください。')

# scripts/start_claude_desktop.py での例  
try:
    from refresh_google_tokens import refresh_tokens
except ImportError as exc:
    raise RuntimeError("refresh_google_tokens.py is missing or has import errors") from exc

# Slack API エラーハンドリング
from slack_sdk.errors import SlackApiError
try:
    response = client.conversations_list(...)
except SlackApiError as exc:
    raise RuntimeError(f"Failed to fetch Slack channel list: {exc.response['error']}") from exc
```

### ログ戦略

- **レベル**: 環境変数 `APP_LOG_LEVEL` で制御（デフォルト: INFO）
- **出力先**: logs/ ディレクトリ + コンソール
- **フォーマット**: 各モジュールで独自のフォーマット
- **タイムゾーン**: `APP_TIMEZONE` で制御（デフォルト: Asia/Tokyo）

## テスト戦略

### テスト分類

1. **設定検証テスト**: 環境変数と設定ファイルの整合性確認
2. **個別API接続テスト**: 各サービスへの認証・接続確認
3. **MCPサーバーテスト**: 各MCPサーバーの起動・機能確認
4. **統合テスト**: 全体ワークフローのテスト

### テスト実装方針

既存実装では以下のテスト構成を採用：

```python
# tests/validate_config.py
def validate_env_file() -> bool:
    """環境変数ファイルの検証"""
    
def validate_settings_json() -> bool:
    """設定ファイルの検証"""

# tests/test_individual_apis.py  
def test_gmail_connection() -> bool:
    """Gmail API接続テスト"""
    
def test_slack_connection() -> bool:
    """Slack API接続テスト"""
    
def test_github_connection() -> bool:
    """GitHub API接続テスト"""

# tests/test_servers.py
class TestMCPServers(unittest.TestCase):
    def test_gmail_server_startup(self):
        """Gmail MCPサーバー起動テスト"""
        
    def test_slack_server_functionality(self):
        """Slack MCPサーバー機能テスト"""
```

### テスト環境

- **テストフレームワーク**: unittest (標準ライブラリ)
- **依存関係**: requirements.txt で管理
- **実行方法**: `python -m unittest tests.test_servers`
- **個別実行**: `python tests/validate_config.py`

## セキュリティ考慮事項

### 認証情報の保護

1. **.envファイル**: .gitignoreに追加済み、実際の認証情報を含む
2. **トークン管理**: 
   - `persist_google_tokens=false` でプロセス環境変数のみに保持可能
   - アクセストークンの自動更新でセキュリティ向上
3. **ログ**: 認証情報は環境変数から読み込み、ログには出力しない

### アクセス制御

1. **ファイルアクセス**: プロジェクトルート配下のみアクセス
2. **API通信**: 各サービスの公式SDKを使用（HTTPS通信）
3. **エラーメッセージ**: 具体的なトークン値は表示せず、設定不備のみ通知

### 設定ファイルセキュリティ

```bash
# .gitignore に含まれる項目
.env
logs/
cache/
__pycache__/
*.pyc
```

### 環境変数セキュリティ

- **ENCRYPTION_KEY**: 32文字の暗号化キー
- **SESSION_SECRET**: セッション管理用秘密鍵
- **API_RATE_LIMIT_PER_MINUTE**: レート制限でAPI乱用防止

## パフォーマンス考慮事項

### 応答時間目標

- **初期化処理**: requirements.txt インストール時間に依存（通常1-3分）
- **認証テスト**: 各API 5秒以内、全体30秒以内
- **MCPサーバーテスト**: 各サーバー10秒以内、全体1分以内
- **トークン更新**: Google API 応答時間に依存（通常5-15秒）
- **Claude Desktop起動**: システム依存（通常10-30秒）

### リソース使用量

- **メモリ使用量**: 
  - 基本動作: 50MB以内
  - Claude Desktop起動時: 追加100-200MB
- **ディスク使用量**: 
  - ログファイル: logs/ ディレクトリ
  - キャッシュ: cache/slack/ ディレクトリ（数MB）
- **ネットワーク**: 
  - API認証時のみ通信
  - Slackチャンネル情報取得（起動時1回）

### 最適化戦略

1. **Slackメタデータキャッシュ**: 起動時に1回取得、ローカルキャッシュ活用
2. **トークン管理**: 必要時のみ更新、プロセス環境変数で高速化
3. **並列処理**: 各API テストの並列実行（将来的改善点）

## 運用・保守

### 監視項目

1. **Googleトークン有効期限**: 自動更新機能で管理
2. **MCPサーバー接続**: Claude Desktop の MCP Server 状態で確認
3. **ログファイルサイズ**: logs/ ディレクトリの容量監視
4. **API レート制限**: 各サービスの制限値監視
5. **Claude Desktop 起動状態**: プロセス監視

### 保守作業

1. **依存関係更新**: requirements.txt の定期更新
2. **認証情報更新**: 
   - Google API: リフレッシュトークンの再取得（年次）
   - 他サービス: トークンの有効期限確認
3. **設定見直し**: 
   - config/settings.json の最適化
   - .env の不要な項目削除
4. **キャッシュクリア**: cache/ ディレクトリの定期クリア

### トラブルシューティング

既存実装では以下のドキュメントを提供：

1. **docs/TROUBLESHOOTING.md**: 一般的なエラーと対処方法
2. **docs/API_SETUP.md**: 各サービスのAPI設定手順
3. **README.md**: 基本的な使用方法とセットアップ手順

### 運用コマンド

```bash
# 初期セットアップ
python scripts/setup.py --install-deps

# 設定検証
python tests/validate_config.py

# 個別API テスト
python tests/test_individual_apis.py

# MCPサーバーテスト
python -m unittest tests.test_servers

# Googleトークン手動更新
python scripts/refresh_google_tokens.py

# Claude Desktop 起動
start_claude_desktop.bat
# または
python scripts/start_claude_desktop.py
```