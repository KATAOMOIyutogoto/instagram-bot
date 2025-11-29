# プロジェクト構造

```
instagramapi/
├── azure/                    # Azureデプロイ用ファイル
│   ├── azure-setup.sh        # Azure自動セットアップ（Linux/Mac）
│   ├── azure-setup.ps1       # Azure自動セットアップ（Windows）
│   ├── deploy-container-app.bicep          # Container Apps用テンプレート
│   ├── deploy-container-instance.bicep     # Container Instances用テンプレート
│   ├── logic-app-scheduled-trigger.json    # Logic Apps用トリガー設定
│   └── README.md             # Azureデプロイ用README
│
├── config/                   # 設定ファイル
│   ├── config.json          # メイン設定ファイル
│   ├── credentials_template.json  # 認証情報テンプレート
│   └── CONFIG_EXAMPLE.json  # 設定例
│
├── data/                     # データファイル（自動生成）
│   ├── session.json         # Instagramセッション
│   ├── upload_history.db     # アップロード履歴データベース
│   ├── upload_mock_logs.json # モックアップロードログ
│   └── scheduler.lock        # スケジューラーロックファイル
│
├── docs/                     # ドキュメント
│   ├── README.md            # メインドキュメント
│   ├── SETUP_GUIDE.md       # セットアップガイド
│   ├── DOCKER_SETUP_GUIDE.md      # Dockerセットアップガイド
│   ├── AZURE_DEPLOYMENT_GUIDE.md  # Azureデプロイガイド
│   ├── SCHEDULER_GUIDE.md   # スケジューラー実行ガイド
│   ├── ACCOUNT_LOCATION_ID_GUIDE.md  # ID取得ガイド
│   └── ...                  # その他のドキュメント
│
├── downloads/                # ダウンロードファイル（自動生成）
│   └── [instagram_id]/      # 企業ごとのフォルダ
│       └── [date]/          # 日付ごとのフォルダ
│           ├── posts/       # 投稿ファイル
│           └── stories/    # ストーリーファイル
│
├── examples/                 # サンプルコード
│   ├── __init__.py
│   ├── example.py           # 基本的な使用例
│   ├── extensions_example.py # 拡張機能の例
│   └── extensions.py        # 拡張機能
│
├── logs/                     # ログファイル（自動生成）
│   ├── instagram_bot.log    # Bot実行ログ
│   └── scheduler.log        # スケジューラーログ
│
├── scripts/                  # ユーティリティスクリプト
│   ├── __init__.py
│   ├── get_gbp_ids.py       # Google Business Profile ID取得
│   ├── db_viewer.py         # データベースビューアー
│   ├── log_viewer.py        # ログビューアー
│   ├── upload_log_viewer.py # アップロードログビューアー
│   ├── setup_credentials.py # 認証情報セットアップ
│   ├── update_config.py     # 設定ファイル更新
│   ├── create_task_scheduler.ps1  # Windows Task Scheduler登録
│   ├── run_scheduler.bat    # スケジューラー実行（1回）
│   ├── run_scheduler_continuous.bat  # スケジューラー実行（常駐）
│   ├── docker-run-once.sh   # Docker実行（Linux/Mac）
│   └── docker-run-once.bat  # Docker実行（Windows）
│
├── docker/                   # Docker関連の追加ファイル
│   ├── README.md            # Docker関連README
│   ├── docker-compose.prod.yml  # 本番環境用設定
│   └── docker-compose.dev.yml   # 開発環境用設定
│
├── src/                      # メインコード
│   ├── __init__.py
│   ├── main.py              # メインエントリーポイント
│   ├── instagram_bot.py     # Instagram Bot
│   ├── downloader.py         # ダウンロード機能
│   ├── uploader.py           # アップロード機能
│   ├── upload_manager.py     # アップロード管理
│   ├── database.py           # データベース管理
│   ├── google_business_api.py # Google Business Profile API
│   ├── scheduler.py          # スケジューラー
│   └── utils.py             # ユーティリティ関数
│
├── .github/                  # GitHub Actions
│   └── workflows/
│       └── scheduled-run.yml # 定期実行ワークフロー
│
├── docker/                   # Docker関連の追加ファイル
│   ├── README.md            # Docker関連README
│   ├── docker-compose.prod.yml  # 本番環境用設定
│   └── docker-compose.dev.yml   # 開発環境用設定
│
├── .dockerignore             # Docker除外ファイル
├── .gitignore                # Git除外ファイル
├── Dockerfile                # Dockerイメージ定義
├── docker-compose.yml        # Docker Compose設定（基本）
├── main.py                   # プロジェクトルートからのエントリーポイント
├── requirements.txt          # 依存パッケージ
├── README.md                 # プロジェクトREADME
└── PROJECT_STRUCTURE.md      # このファイル
```

## 主要ディレクトリの説明

### `azure/`
Azureクラウド環境へのデプロイ用ファイルが含まれています。
- 自動セットアップスクリプト
- Bicepテンプレート（インフラ定義）
- Logic Apps設定

### `config/`
設定ファイルを配置します。
- `config.json`: メイン設定（Instagram認証情報、ターゲット企業など）
- `credentials.json`: Google Business Profile API認証情報（手動で配置）
- `token.json`: OAuthトークン（自動生成）

### `data/`
実行時に生成されるデータファイルが保存されます。
- セッションファイル
- データベース
- ロックファイル

### `docs/`
プロジェクトのドキュメントが含まれています。
- セットアップガイド
- デプロイガイド
- API設定ガイド

### `scripts/`
ユーティリティスクリプトが含まれています。
- データベースビューアー
- ログビューアー
- スケジューラー実行スクリプト

### `src/`
メインのアプリケーションコードが含まれています。

## 自動生成されるディレクトリ

以下のディレクトリは実行時に自動生成されます：
- `data/` - データファイル
- `logs/` - ログファイル
- `downloads/` - ダウンロードファイル

これらのディレクトリは`.gitignore`で除外されています。
