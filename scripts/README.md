# Scripts Directory

このディレクトリは Task Collection System の運用スクリプトをまとめています。

## setup.py

プロジェクトの初期セットアップを行います。必要なディレクトリ作成、`.env` テンプレートのコピー、依存関係インストールを自動化します。

```bash
python scripts/setup.py --install-deps        # requirements.txt の依存関係をインストール
python scripts/setup.py --force               # 既存の .env をテンプレートで上書き
```

## refresh_google_tokens.py

Google OAuth のリフレッシュトークンを使ってアクセストークンを更新します。既定では `.env` に書き戻しますが、オプションでプロセス内更新のみにもできます。

```bash
python scripts/refresh_google_tokens.py               # トークンを更新し .env へ保存
python scripts/refresh_google_tokens.py --no-persist  # カレントプロセスのみ更新
```

## start_claude_desktop.py

環境変数の読み込み、Google トークンの自動更新、Slack チャンネルキャッシュ生成を行った後に Claude Desktop を起動します。

```bash
python scripts/start_claude_desktop.py                # すべての準備を実施して起動
python scripts/start_claude_desktop.py --refresh-only # 起動せずに各種準備のみ
```

> 認証設定チェックや個別 API テストのツールは `tests/validate_config.py`、`tests/test_individual_apis.py` に移動しました。
