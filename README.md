# Instagram API Bot

Instagramから投稿・ストーリーをダウンロードし、Google Business Profileに自動アップロードするBot

## 📁 プロジェクト構造

```
instagramapi/
├── src/                    # メインコード
│   ├── __init__.py
│   ├── main.py            # メインエントリーポイント
│   ├── instagram_bot.py   # Instagram Bot
│   ├── downloader.py      # ダウンロード機能
│   ├── uploader.py        # アップロード機能
│   ├── upload_manager.py  # アップロード管理
│   ├── database.py        # データベース管理
│   ├── google_business_api.py  # Google Business Profile API
│   └── utils.py           # ユーティリティ関数
│
├── scripts/               # ユーティリティスクリプト
│   ├── __init__.py
│   ├── get_gbp_ids.py    # Google Business Profile ID取得
│   ├── db_viewer.py       # データベースビューアー
│   ├── log_viewer.py     # ログビューアー
│   └── upload_log_viewer.py  # アップロードログビューアー
│
├── config/               # 設定ファイル
│   ├── config.json       # メイン設定ファイル
│   ├── credentials_template.json  # 認証情報テンプレート
│   └── CONFIG_EXAMPLE.json  # 設定例
│
├── data/                 # データファイル
│   ├── session.json      # Instagramセッション
│   ├── upload_history.db # アップロード履歴データベース
│   └── upload_mock_logs.json  # モックアップロードログ
│
├── docs/                 # ドキュメント
│   ├── README.md         # メインドキュメント
│   ├── SETUP_GUIDE.md    # セットアップガイド
│   ├── ACCOUNT_LOCATION_ID_GUIDE.md  # ID取得ガイド
│   └── ...               # その他のドキュメント
│
├── examples/             # サンプルコード
│   ├── __init__.py
│   ├── example.py        # 基本的な使用例
│   ├── extensions_example.py  # 拡張機能の例
│   └── extensions.py     # 拡張機能
│
├── downloads/            # ダウンロードファイル（自動生成）
├── logs/                 # ログファイル（自動生成）
├── main.py               # プロジェクトルートからのエントリーポイント
├── requirements.txt       # 依存パッケージ
└── README.md             # このファイル
```

## 🚀 クイックスタート

### VMでお試しする場合（Docker不使用）

**Windows VMで直接Pythonで実行する場合の手順:**

#### 初回セットアップ（1回だけ）

```powershell
# 1. 仮想環境をセットアップ
.\scripts\setup_venv.bat

# 2. 設定ファイルを編集
# config/config.json を編集して認証情報を設定
```

#### 実行コマンド

```powershell
# テスト実行（1回だけ）
.\venv\Scripts\Activate.ps1
python -m src.scheduler --once

# 定期実行（常駐・1時間ごと）
.\scripts\run_scheduler_continuous.bat
```

**詳細:**
- クイックコマンド: `docs/QUICK_COMMANDS.md`
- セットアップガイド: `docs/VM_SETUP_GUIDE.md`

### 方法1: Dockerを使用（推奨・簡単）

```bash
# 1. 設定ファイルを準備（config/config.json）
# 2. Dockerイメージをビルド
docker-compose build

# 3. 実行（1回だけ）
docker-compose run --rm instagram-bot python -m src.scheduler --once

# または、定期実行（常駐）
docker-compose up -d
```

**詳細ドキュメント:**
- `docs/DOCKER_SETUP_GUIDE.md` - Dockerセットアップガイド
- `docker/README.md` - Docker関連ファイルの説明

### 方法2: 直接実行

#### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの準備

`config/config.json` を編集して、Instagramの認証情報とターゲット企業を設定します。

```json
{
  "instagram": {
    "username": "あなたのInstagramユーザー名",
    "password": "あなたのInstagramパスワード",
    "session_file": "data/session.json"
  },
  "targets": {
    "companies": [
      {
        "instagram_id": "ターゲットのInstagramID",
        "google_business_locations": [
          {
            "account_id": "Google Business ProfileのアカウントID",
            "location_id": "Google Business ProfileのロケーションID"
          }
        ]
      }
    ]
  }
}
```

### 3. Google Business Profile APIの設定

詳細は `docs/SETUP_GUIDE.md` を参照してください。

1. Google Cloud Consoleでプロジェクトを作成
2. Google Business Profile APIを有効化
3. OAuth 2.0認証情報を作成
4. `config/credentials.json` と `config/token.json` を配置

### 4. 実行

```bash
python main.py
```

## 📚 ドキュメント

- **セットアップ・実行ガイド**: `docs/GUIDE.md` - セットアップから実行まで全ての情報をまとめた統合ガイド

## 🛠️ ユーティリティスクリプト

### Google Business Profile ID取得

```bash
python scripts/get_gbp_ids.py
```

### データベースビューアー

```bash
python scripts/db_viewer.py
```

### ログビューアー

```bash
python scripts/log_viewer.py
```

## 📝 設定ファイルの場所

- **メイン設定**: `config/config.json`
- **認証情報**: `config/credentials.json` (Google Cloud Consoleからダウンロード)
- **トークン**: `config/token.json` (初回実行時に自動生成)

## 📦 データファイルの場所

- **セッション**: `data/session.json`
- **データベース**: `data/upload_history.db`
- **モックログ**: `data/upload_mock_logs.json`
- **ログファイル**: `logs/instagram_bot.log`

## 🔧 開発

### コードの構造

- `src/`: メインアプリケーションコード
- `scripts/`: ユーティリティスクリプト
- `examples/`: サンプルコード

### インポートパス

プロジェクトルートから実行する場合、`src/`内のモジュールは以下のようにインポートできます：

```python
from src.main import InstagramDownloadBot
from src.database import UploadDatabase
```

## 📄 ライセンス

このプロジェクトは個人利用を目的としています。

