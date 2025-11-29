# Instagram Bot プロジェクト解析レポート

## 📋 プロジェクト概要

このプロジェクトは、**Instagramから投稿・ストーリーをダウンロードし、Google Business Profileに自動アップロードするBot**です。

### 主な機能
1. **Instagramコンテンツのダウンロード**
   - 投稿（画像・動画・アルバム）
   - ストーリー（画像・動画）
   - 複数企業の一括処理

2. **Google Business Profileへの自動アップロード**
   - ダウンロードしたコンテンツを自動的にGoogle Business Profileに投稿
   - 重複アップロードの防止（データベースで管理）
   - モックモード対応（テスト実行用）

3. **複数アカウント対応**
   - 最大7つのInstagramアカウントでローテーション処理
   - レート制限対策（アカウント切り替え）
   - 失敗時の自動再割り当て

4. **定期実行機能**
   - スケジューラーによる1時間ごとの自動実行
   - ロックファイルによる重複実行防止
   - Windows/Linux対応

---

## 🏗️ プロジェクト構造

```
instagramapi/
├── src/                          # メインコード
│   ├── main.py                   # メインエントリーポイント
│   ├── instagram_bot.py          # Instagram Botコアクラス
│   ├── downloader.py             # ダウンロード機能
│   ├── uploader.py               # アップロード機能
│   ├── upload_manager.py         # アップロード管理
│   ├── database.py               # データベース管理
│   ├── google_business_api.py    # Google Business Profile API
│   ├── scheduler.py              # スケジューラー
│   └── utils.py                  # ユーティリティ関数
│
├── scripts/                      # ユーティリティスクリプト
│   ├── get_gbp_ids.py           # Google Business Profile ID取得
│   ├── db_viewer.py             # データベースビューアー
│   ├── log_viewer.py            # ログビューアー
│   ├── upload_log_viewer.py     # アップロードログビューアー
│   ├── upload_status_report.py  # アップロード状況レポート
│   └── setup_credentials.py     # 認証情報セットアップ
│
├── config/                       # 設定ファイル
│   ├── config.json              # メイン設定ファイル
│   ├── CONFIG_EXAMPLE.json      # 設定例
│   └── credentials_template.json # 認証情報テンプレート
│
├── data/                         # データファイル（自動生成）
│   ├── session.json             # Instagramセッション
│   ├── upload_history.db        # アップロード履歴データベース
│   └── scheduler.lock           # スケジューラーロックファイル
│
├── downloads/                    # ダウンロードファイル（自動生成）
├── logs/                         # ログファイル（自動生成）
├── docs/                         # ドキュメント
│   └── GUIDE.md                 # セットアップ・実行ガイド
│
├── requirements.txt              # 依存パッケージ
├── pyproject.toml               # プロジェクト設定（Ruff/Black/MyPy）
└── README.md                     # プロジェクトREADME
```

---

## 🔧 技術スタック

### 主要ライブラリ
- **instagrapi**: Instagram APIクライアント
- **google-api-python-client**: Google Business Profile API
- **google-auth-oauthlib**: Google OAuth認証
- **sqlite3**: データベース（組み込み）
- **requests**: HTTPリクエスト
- **psutil**: プロセス管理（ロックファイル用）

### 開発ツール
- **Ruff**: Linter + Formatter
- **Black**: コードフォーマッター
- **MyPy**: 型チェッカー

### 環境
- **Python**: 3.10+
- **OS**: Windows / Linux / macOS
- **データベース**: SQLite3

---

## 📦 主要モジュールの詳細

### 1. `src/main.py` - メインエントリーポイント

**`InstagramDownloadBot`クラス**: 全体の処理を統括

- **初期化処理**
  - 設定ファイル（`config.json`）の読み込み
  - Instagramアカウントの設定（複数アカウント対応）
  - ターゲット企業リストの読み込み
  - Bot、Downloader、UploadManagerの初期化

- **主要メソッド**
  - `initialize()`: Botの初期化（ログイン）
  - `download_for_company()`: 特定企業のコンテンツをダウンロード
  - `download_all_companies()`: 全企業のコンテンツをダウンロード（7アカウントローテーション）
  - `load_companies_from_file()`: ファイルから企業リストを読み込み

**複数アカウントローテーション処理**:
- 最大7アカウントで分散処理
- 1アカウントあたり5社ずつ処理
- レート制限エラー時の自動再割り当て
- 失敗したアカウントの企業を他のアカウントに再分配

---

### 2. `src/instagram_bot.py` - Instagram Botコア

**`InstagramBot`クラス**: Instagram APIとの通信

- **ログイン機能**
  - セッションファイルによる認証情報の保存・再利用
  - 2FA認証対応
  - チャレンジ認証対応
  - 自動再ログイン

- **主要メソッド**
  - `login()`: Instagramにログイン
  - `get_user_id()`: ユーザー名からユーザーIDを取得
  - `get_user_info()`: ユーザー情報を取得
  - `check_connection()`: 接続状態を確認
  - `wait_between_requests()`: リクエスト間の待機時間

**エラーハンドリング**:
- レート制限（429エラー）の検出とリトライ
- ログイン失敗時の自動再試行
- セッション無効時の自動再ログイン

---

### 3. `src/downloader.py` - ダウンロード機能

**`InstagramDownloader`クラス**: コンテンツのダウンロード

- **ダウンロード対象**
  - 投稿（画像・動画・アルバム）
  - ストーリー（画像・動画）

- **ファイル管理**
  - 企業ごとのフォルダ分け（`downloads/{instagram_id}/`）
  - 日付ごとのフォルダ分け（`downloads/{instagram_id}/{YYYY-MM-DD}/`）
  - 投稿とストーリーの分類（`posts/`、`stories/`）

- **主要メソッド**
  - `download_all()`: 投稿・ストーリーを一括ダウンロード
  - `download_posts()`: 投稿をダウンロード
  - `download_stories()`: ストーリーをダウンロード
  - `_download_media()`: 個別メディアのダウンロード

**ダウンロード制限**:
- 投稿数制限（デフォルト: 6件）
- ストーリー数制限（デフォルト: 10件）
- 設定ファイル（`config.json`）で調整可能

---

### 4. `src/upload_manager.py` - アップロード管理

**`UploadManager`クラス**: アップロード処理の統合管理

- **アップロード機能**
  - ダウンロードした投稿・ストーリーをGoogle Business Profileにアップロード
  - 重複アップロードの防止（データベースでチェック）
  - 複数ロケーションへの同時アップロード対応

- **フィルタリング**
  - アップロード開始日時によるフィルタリング（`start_date`設定）
  - 既にアップロード済みのコンテンツをスキップ

- **主要メソッド**
  - `process_downloaded_posts()`: ダウンロードした投稿を処理
  - `process_downloaded_stories()`: ダウンロードしたストーリーを処理
  - `set_location_mapping()`: ロケーションマッピングを動的に設定

**モックモード**:
- 実際のアップロードを行わずにテスト実行
- ログファイルにアップロード結果を記録
- `config.json`の`upload.mock_mode`で制御

---

### 5. `src/database.py` - データベース管理

**`UploadDatabase`クラス**: SQLiteデータベースによる履歴管理

- **テーブル構成**
  1. **`instagram_location_mapping`**: Instagram IDとGoogle Business Profileロケーションのマッピング
  2. **`uploaded_posts`**: 投稿アップロード履歴
  3. **`uploaded_stories`**: ストーリーアップロード履歴
  4. **`execution_logs`**: 実行ログ（ダウンロード・アップロード結果）

- **主要機能**
  - 重複アップロードの防止（`UNIQUE`制約）
  - 実行ログの記録
  - ロケーションマッピングの管理
  - アップロード状況のクエリ

- **主要メソッド**
  - `is_post_uploaded()`: 投稿がアップロード済みかチェック
  - `is_story_uploaded()`: ストーリーがアップロード済みかチェック
  - `log_upload()`: アップロード履歴を記録
  - `log_execution()`: 実行ログを記録
  - `get_locations()`: ロケーション情報を取得

---

### 6. `src/scheduler.py` - スケジューラー

**`Scheduler`クラス**: 定期実行の管理

- **実行モード**
  - **1回実行**: `--once`フラグで1回だけ実行
  - **定期実行**: 指定間隔（デフォルト: 1時間）で繰り返し実行

- **ロックファイル機能**
  - 前の処理が完了していない場合はスキップ
  - Windows/Linux対応（`fcntl`/ファイルロック）
  - PIDチェックによるプロセス存在確認

- **主要メソッド**
  - `run_once()`: 1回だけ実行（ロックチェック付き）
  - `start()`: バックグラウンドで定期実行を開始
  - `stop()`: スケジューラーを停止

**実行間隔**:
- デフォルト: 1時間
- `--interval`オプションで変更可能（例: `--interval 0.5`で30分）

---

### 7. `src/google_business_api.py` - Google Business Profile API

**`GoogleBusinessProfileAPI`クラス**: Google Business Profile APIクライアント

- **認証**
  - OAuth 2.0認証（`credentials.json`、`token.json`）
  - サービスアカウント認証対応
  - 自動トークンリフレッシュ

- **アップロード機能**
  - 画像・動画のアップロード
  - 直接アップロードモード（`use_direct_upload`）
  - Google Cloud Storageバケット経由のアップロード対応

- **主要メソッド**
  - `upload_media()`: メディアをアップロード
  - `create_post()`: 投稿を作成
  - `_authenticate()`: 認証処理

---

## ⚙️ 設定ファイル（`config/config.json`）

### 基本構造

```json
{
  "instagram": {
    "username": "Instagramユーザー名",
    "password": "Instagramパスワード",
    "session_file": "data/session.json"
  },
  "instagram_accounts": [
    {
      "username": "アカウント1",
      "password": "パスワード1",
      "session_file": "data/session1.json",
      "enabled": true
    },
    // ... 最大7アカウント
  ],
  "targets": {
    "companies": [
      {
        "instagram_id": "ターゲットInstagram ID",
        "user_id": "ユーザーID（自動取得）",
        "google_business_locations": [
          {
            "account_id": "GBPアカウントID",
            "location_id": "GBPロケーションID"
          }
        ]
      }
    ],
    "download_limit": {
      "posts": 6,
      "stories": 10
    }
  },
  "download": {
    "base_directory": "downloads",
    "organize_by_company": true,
    "organize_by_date": true,
    "download_posts": true,
    "download_stories": true
  },
  "settings": {
    "retry_attempts": 3,
    "retry_delay": 5,
    "delay_between_requests": 2
  },
  "upload": {
    "auto_upload": true,
    "mock_mode": false,
    "start_date": "2025-11-23 00:00:00",
    "google_business": {
      "credentials_path": "config/credentials.json",
      "token_path": "config/token.json",
      "gcs_bucket": "",
      "use_direct_upload": true
    }
  }
}
```

### 主要設定項目

| 設定項目 | 説明 | デフォルト値 |
|---------|------|------------|
| `instagram_accounts` | 複数Instagramアカウントの設定 | なし |
| `targets.companies` | 処理対象のInstagramアカウントリスト | 必須 |
| `targets.download_limit.posts` | ダウンロードする投稿数 | 6 |
| `targets.download_limit.stories` | ダウンロードするストーリー数 | 10 |
| `upload.auto_upload` | 自動アップロードを有効にするか | `true` |
| `upload.mock_mode` | モックモード（テスト実行） | `false` |
| `upload.start_date` | アップロード開始日時 | なし |
| `settings.delay_between_requests` | リクエスト間の待機時間（秒） | 2 |

---

## 🔄 処理フロー

### 1. 初期化フロー
```
1. 設定ファイル（config.json）を読み込み
2. Instagramアカウントを初期化（複数アカウント対応）
3. Botをログイン（セッションファイルから読み込み、必要に応じて再ログイン）
4. Downloaderを初期化
5. UploadManagerを初期化（データベース接続）
```

### 2. ダウンロードフロー
```
1. ターゲット企業リストを取得
2. 各企業に対して：
   a. ユーザーIDを取得（キャッシュされている場合は使用）
   b. 投稿をダウンロード（制限数まで）
   c. ストーリーをダウンロード（制限数まで）
   d. ファイルを保存（企業・日付ごとに分類）
3. ダウンロード結果を記録
```

### 3. アップロードフロー（`auto_upload: true`の場合）
```
1. ダウンロードしたコンテンツを取得
2. アップロード開始日時でフィルタリング
3. データベースで重複チェック
4. Google Business Profile APIでアップロード
5. アップロード結果をデータベースに記録
```

### 4. 複数アカウントローテーション処理
```
1. 7アカウントで企業リストを分散（ループ方式）
2. 各アカウントで5社ずつ処理
3. レート制限エラーが発生した場合：
   a. 失敗したアカウントをマーク
   b. 残りの企業を他のアカウントに再割り当て
   c. 再割り当て先のアカウントで処理を継続
4. 全企業の処理が完了するまで繰り返し
```

---

## 🛠️ ユーティリティスクリプト

### `scripts/get_gbp_ids.py`
Google Business ProfileのアカウントID・ロケーションIDを取得

### `scripts/db_viewer.py`
データベースの内容を表示（アップロード履歴、実行ログなど）

### `scripts/log_viewer.py`
実行ログを表示（最近の実行結果、エラーなど）

### `scripts/upload_log_viewer.py`
アップロードログを表示（モックモードのアップロード結果）

### `scripts/upload_status_report.py`
アップロード状況レポートを生成

### `scripts/setup_credentials.py`
Google API認証情報のセットアップ

---

## 🔒 セキュリティ・エラーハンドリング

### セキュリティ対策
- セッションファイルによる認証情報の保存
- 認証情報ファイル（`credentials.json`）は`.gitignore`で除外
- パスワードは設定ファイルに保存（環境変数化推奨）

### エラーハンドリング
- **レート制限**: 429エラーの検出とリトライ（指数バックオフ）
- **ログイン失敗**: 自動再ログイン、セッション再作成
- **ネットワークエラー**: リトライ機能（設定可能な回数）
- **データベースエラー**: トランザクション処理、エラーログ記録

### ロックファイル機能
- スケジューラーの重複実行を防止
- Windows/Linux対応
- PIDチェックによるプロセス存在確認

---

## 📊 データベーススキーマ

### `instagram_location_mapping`
Instagram IDとGoogle Business Profileロケーションのマッピング

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | INTEGER | 主キー |
| `instagram_id` | TEXT | Instagramユーザー名/ID |
| `account_id` | TEXT | GBPアカウントID |
| `location_id` | TEXT | GBPロケーションID |
| `created_at` | TIMESTAMP | 作成日時 |

### `uploaded_posts`
投稿アップロード履歴

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | INTEGER | 主キー |
| `post_id` | TEXT | 投稿ID |
| `instagram_id` | TEXT | Instagramユーザー名/ID |
| `location_id` | TEXT | GBPロケーションID |
| `taken_at` | TIMESTAMP | 撮影日時 |
| `file_path` | TEXT | ファイルパス |
| `upload_status` | TEXT | アップロードステータス |
| `upload_date` | TIMESTAMP | アップロード日時 |

### `uploaded_stories`
ストーリーアップロード履歴（`uploaded_posts`と同じ構造）

### `execution_logs`
実行ログ

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | INTEGER | 主キー |
| `execution_type` | TEXT | 実行タイプ（download/upload） |
| `status` | TEXT | ステータス（success/failed） |
| `message` | TEXT | メッセージ |
| `instagram_id` | TEXT | Instagramユーザー名/ID |
| `started_at` | TIMESTAMP | 開始日時 |
| `completed_at` | TIMESTAMP | 完了日時 |
| `execution_time_seconds` | REAL | 実行時間（秒） |

---

## 🚀 実行方法

### 1. テスト実行（1回だけ）
```powershell
python -m src.scheduler --once
```

### 2. 定期実行（1時間ごと）
```powershell
python -m src.scheduler
```

### 3. 定期実行（カスタム間隔）
```powershell
python -m src.scheduler --interval 0.5  # 30分ごと
```

### 4. メインスクリプト実行
```powershell
python -m src.main
```

---

## 📝 ログ

### ログファイル
- `logs/instagram_bot.log`: Bot実行ログ
- `logs/scheduler.log`: スケジューラーログ

### ログレベル
- **INFO**: 通常の処理状況
- **WARNING**: 警告（リトライなど）
- **ERROR**: エラー（処理失敗など）
- **DEBUG**: デバッグ情報

### ログフォーマット
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

---

## 🔍 トラブルシューティング

### よくある問題

1. **ログイン失敗**
   - セッションファイルを削除して再ログイン
   - 2FA認証が必要な場合は認証コードを入力

2. **レート制限エラー**
   - 複数アカウントで分散処理
   - `delay_between_requests`を増やす

3. **アップロード失敗**
   - Google API認証情報を確認
   - データベースのアップロード履歴を確認

4. **スケジューラーの重複実行**
   - ロックファイル（`data/scheduler.lock`）を削除
   - 前のプロセスが終了しているか確認

---

## 📚 参考ドキュメント

- **README.md**: プロジェクトの概要
- **PROJECT_STRUCTURE.md**: プロジェクト構造の詳細
- **docs/GUIDE.md**: セットアップ・実行ガイド
- **config/CONFIG_EXAMPLE.json**: 設定ファイルの例

---

## 🔄 今後の改善点（推奨）

1. **環境変数による認証情報管理**
   - パスワードを環境変数から読み込む
   - `.env`ファイルのサポート

2. **監視・アラート機能**
   - エラー発生時の通知（メール、Slackなど）
   - 実行状況のダッシュボード

3. **パフォーマンス改善**
   - 並列処理の最適化
   - キャッシュ機能の強化

4. **テストコードの追加**
   - 単体テスト
   - 統合テスト

5. **Docker化の完全対応**
   - Docker Composeでの実行環境
   - 本番環境用の設定

---

**解析日時**: 2025-01-27
**プロジェクトバージョン**: 最新（コミット履歴を確認してください）

