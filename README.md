# Task Collection System

## 概要

Task Collection System は Gmail / Slack / GitHub / Google Calendar / Notion と連携し、日次のタスク情報を自動収集・整理する運用支援プラットフォームです。MCP サーバーを通じて Claude Desktop から各サービスにアクセスし、タスク収集・照会・更新を安全かつ一貫した手順で実行できます。

## セットアップ手順

1. **依存関係のインストールと初期化**
   ```bash
   python scripts/setup.py --install-deps
   ```
   - 必要なディレクトリ（config / docs / logs / scripts / servers / tests / cache/slack など）を自動作成します。
   - `config/.env.template` をプロジェクトルートの `.env` にコピーします。

2. **環境変数の設定**
   - `.env` を開き、Gmail / Slack / GitHub / Google Calendar / Notion の認証情報を記入します。
   - 取得手順や権限設定は `docs/API_SETUP.md` を参照してください。

3. **設定ファイルの確認**
   - `config/settings.json` の `desktop` セクションで Claude Desktop の実行パス、Google トークン自動更新、Slack キャッシュの永続化などを調整します。
   - チェック用に `python tests/validate_config.py --report` を実行すると、`.env`・`settings.json`・MCP 設定の整合性レポートを出力できます。

4. **Claude Desktop 起動**
   ```bash
   python scripts/start_claude_desktop.py
   ```
   - 起動前に必要であれば Google トークン更新と Slack チャンネルキャッシュ生成が走ります。
   - `--refresh-only` を付けると環境準備のみを行い、Claude Desktop は起動しません。

## 主要コマンド

- `python scripts/setup.py --install-deps` : プロジェクト初期化と Python 依存関係インストール
- `python tests/validate_config.py --quiet` : 主要設定・環境変数の検証を静かなログで実行
- `python tests/test_individual_apis.py --service slack` : 指定サービスの API 認証テスト（`gmail|slack|github|calendar|notion` を指定可能）
- `pytest` : MCP サーバーのユニットテストと統合テスト（資格情報が無い場合は該当ケースがスキップされます）
- `python scripts/start_claude_desktop.py --refresh-only` : Google トークン更新と Slack キャッシュ生成のみを実行

## 技術スタック

| ライブラリ / ツール | バージョン | 概要 |
|---------------------|------------|------|
| Python              | 3.12       | プロジェクト全体の実行環境 |
| python-dotenv       | >=1.0.0    | `.env` から環境変数を読み込むユーティリティ |
| requests            | >=2.31.0   | Gmail / Calendar など HTTP ベース API へのアクセス |
| google-auth         | >=2.23.0   | Google OAuth 認証・トークンリフレッシュ |
| slack-sdk           | >=3.21.0   | Slack Web API からメッセージやチャンネル情報を取得 |
| PyGithub            | >=1.59.0   | GitHub API から課題情報を取得 |
| notion-client       | >=2.0.0    | Notion データベースの参照・更新 |
| fastmcp             | >=0.2.1    | Claude Desktop と連携する MCP サーバー基盤 |
| pytest              | >=7.4.0    | 自動テストフレームワーク |

## 運用ノート

- Slack MCP サーバーはチャンネルメタデータを `cache/slack/` に保存します（`.gitignore` 済み）。実チャンネル名が含まれるため、リポジトリにはコミットしないでください。必要になればスクリプト実行時に自動再生成されます。
- Google トークンの永続化は `config/settings.json` の `desktop.persist_google_tokens` で制御できます。`false` にすると `.env` へ保存せず、起動プロセスのみで利用します。
- 詳細なトラブルシューティングは `docs/TROUBLESHOOTING.md`、Claude Desktop で使用するワークフロープロンプトは `docs/workflow_prompts.md` と `docs/notion_prompts.md` を参照してください。

## テストについて

認証情報が未設定の場合、`tests/test_servers_integration.py` の統合テストは自動的にスキップされます。API の実接続テストを行う際は `.env` を正しく設定し、Slack では `SLACK_TEST_CHANNEL_ID` を指定してください。ユニットテスト `tests/test_server_tools.py` ではモックを用いて MCP ツール登録と基本レスポンスを検証しています。
