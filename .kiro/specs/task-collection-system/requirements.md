# タスク収集システム 要件定義書

## はじめに

本システムは、既存の `task_managemer_` をベースとして、Claudeを活用したスケジュール管理自動化システムの構築・運用を支援することを目的としています。Gmail・Slack・GitHub・Google Calendar・Notionとの統合により、各サービスからの情報収集とTODO管理を自動化します。Poetry を使用したPython環境での開発を前提とし、MCPサーバーとの統合によってタスクの収集・管理・実行を自動化します。システムは初期化から運用まで一貫したワークフローを提供し、開発者が手順通りに実行することで効率的なタスク管理環境を構築できることを目指します。

## 用語集

- **TaskCollectionSystem**: 本システム全体を指すメインシステム（task_managemer_ベース）
- **SetupModule**: プロジェクト初期化を担当するモジュール（scripts/setup.py）
- **AuthenticationModule**: 認証・トークン管理を担当するモジュール（tests/validate_config.py, tests/test_individual_apis.py）
- **ValidationModule**: MCP接続確認とテスト実行を担当するモジュール（tests/test_servers.py）
- **TokenRefreshModule**: Googleトークン自動更新を担当するモジュール（scripts/refresh_google_tokens.py）
- **LaunchModule**: Claude Desktop起動を担当するモジュール（scripts/start_claude_desktop.py, start_claude_desktop.bat）
- **MCPServer**: Model Context Protocol サーバー（servers/配下の各サーバー）
- **GoogleRefreshToken**: Google API アクセス用のリフレッシュトークン
- **EnvironmentFile**: 環境変数を格納する.envファイル
- **Poetry**: Pythonパッケージ管理ツール
- **RequirementsFile**: Python依存関係を定義するrequirements.txt

## 要件

### 要件1

**ユーザーストーリー:** 開発者として、プロジェクトを簡単に初期化したいので、一つのコマンドで必要な環境設定が完了するようにしたい

#### 受け入れ基準

1. 初期化コマンドが実行された時、SetupModuleはRequirementsFileを使用してPython依存関係をインストールする
2. 初期化コマンドが実行された時、SetupModuleはconfig/.env.templateからリポジトリルートにEnvironmentFileを配置する
3. 必要なディレクトリが存在しない場合、SetupModuleはconfig/, docs/, logs/, scripts/ディレクトリを作成する
4. EnvironmentFileが既に存在する場合、SetupModuleは--forceオプション指定時のみ上書きする

### 要件2

**ユーザーストーリー:** 開発者として、認証情報が正しく設定されていることを確認したいので、手動で設定したトークンの疎通確認ができるようにしたい

#### 受け入れ基準

1. 設定検証コマンドが実行された時、AuthenticationModuleはEnvironmentFileとconfig/settings.jsonの整合性を確認する
2. 個別API テストコマンドが実行された時、AuthenticationModuleは各サービス（Gmail, Slack, GitHub, Google Calendar, Notion）への接続を確認する
3. 認証が成功した場合、AuthenticationModuleは各サービスの接続状況を表示する
4. 認証が失敗した場合、AuthenticationModuleは具体的なエラー内容とトラブルシューティング情報を表示する

### 要件3

**ユーザーストーリー:** 開発者として、MCPサーバーが正常に動作することを確認したいので、MCPサーバー経由でのテスト実行ができるようにしたい

#### 受け入れ基準

1. MCPサーバーテストが実行された時、ValidationModuleは各MCPServer（gmail_server, slack_server, github_server, calendar_server, notion_server）の起動を確認する
2. 各MCPServerが起動した時、ValidationModuleは基本的な機能テストを実行する
3. MCPServerとの通信が失敗した場合、ValidationModuleは詳細なエラー情報とログファイルの場所を提供する
4. 全てのテストが完了した時、ValidationModuleはテスト結果サマリーを表示する

### 要件4

**ユーザーストーリー:** 開発者として、GoogleRefreshTokenの更新を自動化したいので、Claude Desktop実行時にPythonコードでトークン更新が行われるようにしたい

#### 受け入れ基準

1. start_claude_desktop.batが実行された時、LaunchModuleはscripts/start_claude_desktop.pyを起動する
2. config/settings.jsonでauto_refresh_google_tokensがtrueの場合、TokenRefreshModuleはGmail・Google CalendarのAccessTokenを自動更新する
3. persist_google_tokensがtrueの場合、TokenRefreshModuleは新しいトークンをEnvironmentFileに保存する
4. persist_google_tokensがfalseの場合、TokenRefreshModuleはトークンをプロセス環境変数にのみ設定する

### 要件5

**ユーザーストーリー:** 開発者として、システムを簡単に使い始められるようにしたいので、手順通りに実行すればタスク管理ができる詳細なマニュアルが欲しい

#### 受け入れ基準

1. README.mdが参照された時、TaskCollectionSystemは初期化からClaude Desktop起動までの詳細な手順を提供する
2. docs/API_SETUP.mdが参照された時、TaskCollectionSystemは各サービスのAPI認証設定手順を提供する
3. docs/TROUBLESHOOTING.mdが参照された時、TaskCollectionSystemは一般的なエラーと対処方法を提供する
4. docs/workflow_prompts.mdが参照された時、TaskCollectionSystemはClaude Desktopで使用するプロンプトテンプレートを提供する

### 要件6

**ユーザーストーリー:** 開発者として、Claude Desktopを適切な環境で起動したいので、MCP環境変数とSlackメタデータが自動設定されるようにしたい

#### 受け入れ基準

1. Claude Desktop起動時、LaunchModuleはEnvironmentFileから認証情報を読み込む
2. SLACK_BOT_TOKENが設定されている場合、LaunchModuleはSlackチャンネル情報をcache/slackディレクトリにキャッシュする
3. PYTHONPATH環境変数が設定されていない場合、LaunchModuleはプロジェクトルートを追加する
4. config/settings.jsonのclaude_pathに基づいて、LaunchModuleはClaude Desktopを起動する