# Instagram Bot セットアップ・実行ガイド

Instagramから投稿・ストーリーをダウンロードし、Google Business Profileに自動アップロードするBotのセットアップと実行方法を説明します。

## 📋 目次

1. [初回セットアップ](#初回セットアップ)
2. [設定ファイルの準備](#設定ファイルの準備)
3. [実行方法](#実行方法)
4. [ユーティリティスクリプト](#ユーティリティスクリプト)
5. [トラブルシューティング](#トラブルシューティング)

---

## 初回セットアップ

### 1. 仮想環境のセットアップ

```powershell
# プロジェクトディレクトリに移動
cd C:\Users\team4\Desktop\開発\instagramapi

# 自動セットアップスクリプトを実行
.\scripts\setup_venv.bat
```

または手動で：

```powershell
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. Google Business Profile APIの設定

1. **Google Cloud Consoleでプロジェクトを作成**
   - https://console.cloud.google.com/ にアクセス
   - 新しいプロジェクトを作成

2. **Google Business Profile APIを有効化**
   - 「APIとサービス」→「ライブラリ」
   - 「Google Business Profile API」を検索して有効化

3. **OAuth 2.0認証情報を作成**
   - 「APIとサービス」→「認証情報」
   - 「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類: 「デスクトップアプリ」
   - 認証情報をダウンロードして `config/credentials.json` に保存

4. **初回認証**
   - プログラムを実行すると、ブラウザが開いて認証を求められます
   - 認証後、`config/token.json` が自動生成されます

---

## 設定ファイルの準備

### config/config.json の設定

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
        "user_id": "ユーザーID（自動取得される）",
        "google_business_locations": [
          {
            "account_id": "Google Business ProfileのアカウントID（空でも可）",
            "location_id": "Google Business ProfileのロケーションID"
          }
        ]
      }
    ],
    "download_limit": {
      "posts": 6,
      "stories": 10
    }
  },
  "upload": {
    "auto_upload": true,
    "mock_mode": true,
    "start_date": "2025-11-23 00:00:00"
  }
}
```

### 主要な設定項目

- **`instagram.username`**: Instagramのユーザー名
- **`instagram.password`**: Instagramのパスワード
- **`targets.companies`**: 処理対象のInstagramアカウントリスト
- **`targets.download_limit.posts`**: ダウンロードする投稿数（デフォルト: 6）
- **`targets.download_limit.stories`**: ダウンロードするストーリー数（デフォルト: 10）
- **`upload.auto_upload`**: 自動アップロードを有効にするか（`true`/`false`）
- **`upload.mock_mode`**: モックモード（`true`の場合は実際にはアップロードしない）
- **`upload.start_date`**: この日時以降の投稿/ストーリーのみをアップロード

---

## 実行方法

### テスト実行（1回だけ実行）

```powershell
# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 1回だけ実行
python -m src.scheduler --once
```

### 定期実行（30分ごと）

```powershell
# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 定期実行（30分ごと）
python -m src.scheduler --interval 0.5

# 定期実行（1時間ごと）
python -m src.scheduler --interval 1.0
```

**Ctrl+Cで停止できます。**

### Windows Task Schedulerに登録（バックグラウンド実行）

1. Windowsの「タスクスケジューラー」を開く
2. 「基本タスクの作成」を選択
3. 以下の設定を行う：
   - **名前**: `InstagramBotScheduler`
   - **トリガー**: 「繰り返し」→ 30分ごと（または1時間ごと）
   - **操作**: 「プログラムの開始」
   - **プログラム**: `python`
   - **引数の追加**: `-m src.scheduler --once`
   - **開始**: プロジェクトのルートディレクトリ

---

## ユーティリティスクリプト

### 1. 全InstagramアカウントのユーザーIDを取得

```powershell
python scripts\fetch_all_user_ids.py
```

`config.json`内の全アカウントのユーザーIDを取得して保存します。既に保存されている場合はスキップされます。

### 2. アップロード状況レポート

```powershell
# 最新20件を表示
python scripts\upload_status_report.py --limit 20

# 特定のInstagram IDでフィルタ
python scripts\upload_status_report.py --instagram-id dahlia_seikotsu
```

ダウンロードしたファイルのうち、何がアップロードされて何がスキップされたかを確認できます。

### 3. データベースビューアー

```powershell
# アップロード履歴を確認
python scripts\db_viewer.py posts

# 特定のInstagram IDの投稿を確認
python scripts\db_viewer.py posts dahlia_seikotsu

# 実行ログを確認
python scripts\db_viewer.py logs
```

### 4. Google Business Profile ID取得

```powershell
python scripts\get_gbp_ids.py
```

Google Business ProfileのアカウントIDとロケーションIDを取得します。

---

## トラブルシューティング

### ログインエラー

- セッションファイル（`data/session.json`）を削除して再ログイン
- Instagramの認証情報が正しいか確認

### レート制限エラー（429エラー）

- `config.json`の`settings.delay_between_requests`を増やす（例: 5秒）
- 処理するアカウント数を減らす

### 重複アップロード

- モックモードでもDBに記録されるため、次回実行時はスキップされます
- データベース（`data/upload_history.db`）でアップロード履歴を確認できます

### ログの確認

```powershell
# スケジューラーログ
Get-Content logs\scheduler.log -Tail 30 -Encoding UTF8

# Bot実行ログ
Get-Content logs\instagram_bot.log -Tail 30 -Encoding UTF8
```

---

## ファイル構成

### 設定ファイル

- `config/config.json` - メイン設定ファイル
- `config/credentials.json` - Google API認証情報（Google Cloud Consoleからダウンロード）
- `config/token.json` - OAuthトークン（初回実行時に自動生成）

### データファイル

- `data/session.json` - Instagramセッション（自動生成）
- `data/upload_history.db` - アップロード履歴データベース（重複チェック用）
- `data/upload_mock_logs.json` - モックアップロードログ

### ログファイル

- `logs/scheduler.log` - スケジューラーの実行ログ
- `logs/instagram_bot.log` - Botの実行ログ

### ダウンロードファイル

- `downloads/` - ダウンロードした投稿・ストーリー（自動生成）

---

## よくある質問

### Q: ユーザーIDは自動で取得されるの？

A: 初回実行時に自動で取得され、`config.json`に保存されます。既に保存されている場合はスキップされます。

### Q: モックモードと実際のアップロードモードの違いは？

A: 
- **モックモード**: 実際にはアップロードせず、ログに記録するだけ
- **実際のモード**: Google Business Profile APIに実際にアップロード

どちらも重複チェックは機能します。

### Q: 重複アップロードは防げる？

A: はい。DBで重複チェックを行い、既にアップロード済みの投稿・ストーリーは自動でスキップされます。

### Q: 実行間隔を変更したい

A: `--interval`オプションで変更できます。例: `--interval 0.5`（30分ごと）、`--interval 2.0`（2時間ごと）

---

## サポート

問題が発生した場合は、ログファイル（`logs/scheduler.log`、`logs/instagram_bot.log`）を確認してください。

