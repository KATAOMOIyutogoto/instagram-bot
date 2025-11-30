# Instagram API Bot

Instagramから投稿・ストーリーをダウンロードし、Google Business Profileに自動アップロードするBot

## 📋 目次

- [プロジェクト概要](#プロジェクト概要)
- [プロジェクト構造](#プロジェクト構造)
- [クイックスタート](#クイックスタート)
- [詳細セットアップ](#詳細セットアップ)
- [設定ファイル](#設定ファイル)
- [実行方法](#実行方法)
- [ユーティリティスクリプト](#ユーティリティスクリプト)
- [トラブルシューティング](#トラブルシューティング)
- [開発](#開発)

---

## プロジェクト概要

### 主な機能

1. **Instagramコンテンツのダウンロード**
   - 投稿（画像・動画・アルバム）
   - ストーリー（画像・動画）
   - 複数企業の一括処理

2. **Google Business Profileへの自動アップロード**
   - ダウンロードしたコンテンツを自動的にGoogle Business Profileに投稿
   - 重複アップロードの防止（データベースで管理）
   - モックモード対応（テスト実行用）
   - 動画変換機能（GBP要件に合わせて自動変換）
   - Seleniumベースのアップロード対応

3. **複数アカウント対応**
   - 最大7つのInstagramアカウントでローテーション処理
   - レート制限対策（アカウント切り替え）
   - 失敗時の自動再割り当て
   - セッションID重複チェック（アカウント凍結防止）

4. **定期実行機能**
   - スケジューラーによる1時間ごとの自動実行
   - ロックファイルによる重複実行防止
   - Windows/Linux対応

---

## プロジェクト構造

```
instagramapi/
├── src/                    # メインコード
│   ├── main.py            # メインエントリーポイント
│   ├── instagram_bot.py   # Instagram Bot
│   ├── downloader.py      # ダウンロード機能
│   ├── uploader.py        # アップロード機能
│   ├── upload_manager.py  # アップロード管理
│   ├── database.py        # データベース管理
│   ├── selenium_gbp_uploader.py  # Seleniumアップローダー
│   ├── scheduler.py       # スケジューラー
│   └── utils.py           # ユーティリティ関数
│
├── scripts/               # ユーティリティスクリプト（運用時に使用）
│   ├── check_all_accounts_login.py  # 全アカウントログイン状態確認
│   ├── db_viewer.py       # データベースビューアー
│   ├── extract_all_sessions_from_browser.py  # 全アカウントセッション自動取得
│   ├── extract_session_from_browser.py  # 単一アカウントセッション自動取得
│   ├── fetch_all_user_ids.py  # ユーザーID取得
│   ├── log_viewer.py     # ログビューアー
│   ├── update_session_from_browser.py  # セッション更新（手動）
│   └── upload_log_viewer.py  # アップロードログビューアー
│
├── tools/                 # 開発ツール（開発時に使用）
│   ├── format.bat        # コードフォーマット（Windows）
│   ├── format.sh         # コードフォーマット（Linux/Mac）
│   ├── lint.bat          # コード品質チェック（Windows）
│   ├── lint.sh           # コード品質チェック（Linux/Mac）
│   └── setup_venv.bat    # 仮想環境セットアップ
│
├── config/               # 設定ファイル
│   ├── config.json       # メイン設定ファイル
│   ├── credentials_template.json  # 認証情報テンプレート
│   └── CONFIG_EXAMPLE.json  # 設定例
│
├── data/                 # データファイル（自動生成）
│   ├── session_account*.json  # Instagramセッション
│   ├── upload_history.db # アップロード履歴データベース
│   └── upload_mock_logs.json  # モックアップロードログ
│
├── downloads/            # ダウンロードファイル（自動生成）
├── logs/                 # ログファイル（自動生成）
│   ├── instagram_bot.log
│   └── scheduler.log
├── requirements.txt       # 依存パッケージ
└── README.md             # このファイル
```

---

## クイックスタート

### 初回セットアップ（1回だけ）

```powershell
# 1. 仮想環境をセットアップ
.\tools\setup_venv.bat

# 2. 設定ファイルを編集
# config/config.json を編集して認証情報を設定
```

### 実行コマンド

```powershell
# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# テスト実行（1回だけ）
python -m src.scheduler --once

# 定期実行（1時間ごと）
python -m src.scheduler

# 定期実行（カスタム間隔）
python -m src.scheduler --interval 0.5  # 30分ごと
```

---

## 詳細セットアップ

### 1. 仮想環境のセットアップ

#### 自動セットアップ（推奨）

```powershell
.\tools\setup_venv.bat
```

このスクリプトは以下を実行します：
- Pythonのバージョンを確認
- 仮想環境を作成（`python -m venv venv`）
- pipをアップグレード
- 依存パッケージをインストール（`pip install -r requirements.txt`）

#### 手動セットアップ

```powershell
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 依存パッケージをインストール
pip install -r requirements.txt
```

#### 仮想環境の有効化（毎回実行時に必要）

```powershell
.\venv\Scripts\Activate.ps1
```

コマンドプロンプトの先頭に `(venv)` が表示されれば有効化成功です。

#### 仮想環境が有効化できない場合

PowerShellの実行ポリシーが原因の可能性があります：

```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# 実行ポリシーを変更（必要に応じて）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# または、cmd形式のアクティベートを使用
.\venv\Scripts\activate.bat
```

### 2. Google Business Profile IDの取得

Seleniumアップロードを使用する場合、Google Business ProfileのロケーションIDが必要です。

**手動で取得する方法：**

1. Google Business Profile Manager (https://business.google.com/) にアクセス
2. 該当するビジネスを選択
3. ブラウザのURLから `location_id` を確認
   - 例: `https://business.google.com/locations/1234567890123456789`
   - → `location_id` は `1234567890123456789`

4. 取得した `location_id` を `config/config.json` の `google_business_locations` に設定してください

### 3. Chromeプロファイルの設定（Seleniumアップロード用）

SeleniumベースのGoogle Business Profileアップロードを使用する場合、デスクトップに専用のChromeプロファイルを作成して設定する必要があります。

#### ステップ1: デスクトップにChromeプロファイルフォルダを作成

デスクトップに`ChromeProfile`という名前のフォルダを作成します。

**PowerShellで作成する場合：**

```powershell
# デスクトップのパスを取得してフォルダを作成
$desktop = [Environment]::GetFolderPath("Desktop")
$profilePath = Join-Path $desktop "ChromeProfile"
New-Item -ItemType Directory -Path $profilePath -Force
New-Item -ItemType Directory -Path "$profilePath\Default" -Force
```

**手動で作成する場合：**

1. デスクトップを開く
2. 新しいフォルダを作成し、名前を`ChromeProfile`にする
3. `ChromeProfile`フォルダを開き、さらに`Default`という名前のフォルダを作成

作成されるフォルダ構造：
```
デスクトップ/
└── ChromeProfile/
    └── Default/
```

#### ステップ2: Chromeをデスクトップのプロファイルで起動

デスクトップのプロファイルを使用してChromeを起動します：

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\<ユーザー名>\Desktop\ChromeProfile" --profile-directory="Default"
```

**注意**: `<ユーザー名>`の部分は、実際のWindowsユーザー名に置き換えてください。

**例（ユーザー名が`team4`の場合）：**

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\team4\Desktop\ChromeProfile" --profile-directory="Default"
```

#### ステップ3: Google Business Profileにログイン

起動したChromeで以下を実行してください：

1. **Google Business Profile Managerにアクセス**
   - https://business.google.com/ を開く
   - Googleアカウントでログイン

2. **ログイン状態を保持**
   - Google Business Profileにログインした状態を保持してください
   - ブラウザを閉じる前に、ログイン状態が保持されていることを確認

3. **プロファイル名の確認（必要に応じて）**
   - Chromeのアドレスバーに `chrome://version/` と入力してEnter
   - 「プロファイルパス」を確認
   - 通常は`Default`ですが、異なる場合はその名前を使用してください

#### ステップ4: config.jsonで設定

`config/config.json`の`upload.selenium`セクションに設定を追加します：

```json
{
  "upload": {
    "auto_upload": true,
    "mock_mode": false,
    "selenium": {
      "enabled": true,
      "chrome_profile_path": "C:\\Users\\<ユーザー名>\\Desktop\\ChromeProfile",
      "profile_name_gbp": "Default"
    }
  }
}
```

**設定項目の説明：**

- **`enabled`**: `true`に設定するとSeleniumアップロードが有効になります
- **`chrome_profile_path`**: デスクトップに作成した`ChromeProfile`フォルダのフルパス
  - Windowsの場合、バックスラッシュ`\`は2つ重ねて`\\`と記述する必要があります
  - 例: `C:\\Users\\team4\\Desktop\\ChromeProfile`
- **`profile_name_gbp`**: Chromeプロファイル名（通常は`Default`）

**設定例（ユーザー名が`team4`の場合）：**

```json
{
  "upload": {
    "selenium": {
      "enabled": true,
      "chrome_profile_path": "C:\\Users\\team4\\Desktop\\ChromeProfile",
      "profile_name_gbp": "Default"
    }
  }
}
```

#### プロファイル名が`Default`以外の場合

`chrome://version/`で確認したプロファイル名が`Default`以外の場合（例: `Profile 1`、`Profile 2`など）、`profile_name_gbp`にその名前を設定してください：

```json
{
  "upload": {
    "selenium": {
      "enabled": true,
      "chrome_profile_path": "C:\\Users\\team4\\Desktop\\ChromeProfile",
      "profile_name_gbp": "Profile 1"
    }
  }
}
```

#### 動作確認

設定が完了したら、モックモードを無効にしてテスト実行してください：

```powershell
.\venv\Scripts\Activate.ps1
python -m src.scheduler --once
```

**注意事項：**

- ChromeプロファイルでGoogle Business Profileにログインした状態を保持しておく必要があります
- Bot実行中は、そのChromeプロファイルを使用する他のChromeウィンドウを閉じることを推奨します
- 初回起動時にChromeが既存プロセスを終了することがあります（正常な動作です）

---

## 設定ファイル

### config/config.json

メインの設定ファイルです。以下の設定が可能です：

```json
{
  "instagram_accounts": [
    {
      "username": "アカウント1",
      "password": "パスワード1",
      "session_file": "data/session_account1.json",
      "enabled": true
    }
  ],
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
    ],
    "download_limit": {
      "posts": 6,
      "stories": 10
    }
  },
    "upload": {
      "auto_upload": true,
      "mock_mode": true,
      "start_date": "2025-11-23 00:00:00",
      "video_conversion": {
        "enabled": true,
        "min_width": 400,
        "min_height": 300
      },
      "selenium": {
        "enabled": false,
        "chrome_profile_path": "",
        "profile_name_gbp": ""
      }
    }
}
```

### 主要な設定項目

- **`instagram_accounts`**: Instagramアカウントのリスト（最大7アカウント）
  - `username`: Instagramユーザー名
  - `password`: Instagramパスワード
  - `session_file`: セッションファイルのパス
  - `enabled`: 有効/無効（`true`/`false`）

- **`targets.companies`**: 処理対象のInstagramアカウントリスト
  - `instagram_id`: ターゲットのInstagram ID
  - `google_business_locations`: Google Business Profileのロケーション情報

- **`upload.auto_upload`**: 自動アップロードを有効にするか（`true`/`false`）
- **`upload.mock_mode`**: モックモード（`true`の場合は実際にはアップロードしない）
- **`upload.start_date`**: この日時以降の投稿/ストーリーのみをアップロード
- **`upload.video_conversion.enabled`**: 動画変換を有効にするか
- **`upload.selenium.enabled`**: Seleniumアップロードを使用するか（`true`/`false`）
- **`upload.selenium.chrome_profile_path`**: Chromeプロファイルフォルダのフルパス
  - 例: `C:\\Users\\team4\\Desktop\\ChromeProfile`
  - Windowsの場合、パスの区切り文字`\`は`\\`と記述する必要があります
- **`upload.selenium.profile_name_gbp`**: Chromeプロファイル名（通常は`Default`）
  - `chrome://version/`で確認できます

---

## 実行方法

### スケジューラーを使用（推奨）

#### 1. テスト実行（1回だけ実行）

```powershell
.\venv\Scripts\Activate.ps1
python -m src.scheduler --once
```

**説明**:
- `--once`: 1回だけ実行して終了
- 前の処理が完了していない場合はスキップ（ロックファイルチェック）

#### 2. 定期実行（デフォルト: 1時間ごと）

```powershell
.\venv\Scripts\Activate.ps1
python -m src.scheduler
```

**説明**:
- デフォルトで1時間ごとに実行
- `Ctrl+C`で停止可能

#### 3. 定期実行（カスタム間隔）

```powershell
# 30分ごと
python -m src.scheduler --interval 0.5

# 2時間ごと
python -m src.scheduler --interval 2.0

# 6分ごと
python -m src.scheduler --interval 0.1
```

#### 4. カスタムロックファイル

```powershell
python -m src.scheduler --once --lock-file data/custom_lock.lock
```

### スケジューラーのオプション

| オプション | 説明 | デフォルト値 |
|-----------|------|------------|
| `--once` | 1回だけ実行して終了 | なし |
| `--interval` | 実行間隔（時間）。例: `0.5`（30分）、`1.0`（1時間） | `1.0` |
| `--lock-file` | ロックファイルのパス | `data/scheduler.lock` |

### Windows Task Schedulerに登録

1. Windowsの「タスクスケジューラー」を開く
2. 「基本タスクの作成」を選択
3. 設定：
   - **名前**: `InstagramBotScheduler`
   - **トリガー**: 「繰り返し」→ 30分ごと（または1時間ごと）
   - **操作**: 「プログラムの開始」
   - **プログラム**: `python`（またはフルパス: `C:\Python\python.exe`）
   - **引数の追加**: `-m src.scheduler --once`
   - **開始**: プロジェクトのルートディレクトリ

---

## ユーティリティスクリプト

### 1. 全アカウントのログイン状態を確認

```powershell
python scripts/check_all_accounts_login.py
```

すべてのInstagramアカウントのログイン状態を確認します。セッションファイルの有効性をチェックし、ログイン可能かどうかを表示します。

### 2. データベースビューアー

```powershell
# アップロード履歴を確認
python scripts/db_viewer.py posts

# 特定のInstagram IDの投稿を確認
python scripts/db_viewer.py posts <instagram_id>

# 実行ログを確認
python scripts/db_viewer.py logs
```

### 3. ログビューアー

```powershell
python scripts/log_viewer.py
```

実行ログを表示します。

### 4. セッションファイルの作成（自動取得ツール）

#### 全アカウントを一括取得（推奨）

config.jsonに設定されている全アカウントのセッション情報を順番に取得します：

```powershell
python scripts/extract_all_sessions_from_browser.py
```

このツールは：
1. `config.json`から全てのアカウントを読み込みます
2. 各アカウントに対して順番にブラウザでログイン画面を表示します
3. 手動でログインしてください（チャレンジ認証も対応）
4. ログインが完了すると、自動的にセッション情報を取得して保存します
5. 1つのアカウントが完了すると、次のアカウントの処理が始まります

#### 単一アカウントを取得

1つのアカウントだけを取得する場合：

```powershell
python scripts/extract_session_from_browser.py data/session_account1.json
```

#### 手動でセッションIDを取得する場合

ブラウザから手動でセッションIDを取得する場合：

```powershell
python scripts/update_session_from_browser.py <セッションファイル> <sessionid> [ds_user_id]
```

ブラウザから取得したセッションIDでセッションファイルを更新します。

---

## トラブルシューティング

### チャレンジ認証エラー

**エラーメッセージ**:
```
WARNING - チャレンジ認証が必要です。手動で対応してください
```

**対処方法**:

1. **ブラウザでInstagramにログイン**
   - https://www.instagram.com/ にアクセス
   - アカウントでログイン
   - チャレンジ認証を完了（メールやSMSで認証コードが送られる場合がある）

2. **セッションファイルを削除**
   ```powershell
   Remove-Item "data\session_account1.json" -ErrorAction SilentlyContinue
   ```

3. **再度Botを実行**
   ```powershell
   python -m src.scheduler --once
   ```

### IPアドレスがブラックリストに入っている場合

**エラーメッセージ**:
```
We can send you an email to help you get back into your account. 
If you are sure that the password is correct, then change your IP address, 
because it is added to the blacklist of the Instagram Server
```

**対処方法**:

1. **IPアドレスを変更する**
   - VPNを使用
   - プロキシサーバーを使用
   - ルーターを再起動してIPアドレスを変更（動的IPの場合）

2. **しばらく待つ**
   - 24〜48時間待つと、ブロックが解除される可能性がある

### ブラウザのセッション情報を使用する

ブラウザでログインできる場合、そのセッション情報をBotで使用できます。

#### 自動取得ツール（推奨）

最も簡単な方法は、自動取得ツールを使用することです：

```powershell
python scripts/extract_session_from_browser.py data/session_account1.json
```

このツールは：
- Chromeブラウザを自動的に開きます
- Instagramのログインページを表示します
- 手動でログインしてください（チャレンジ認証も対応）
- ログインが完了すると、自動的にセッション情報を取得して保存します

#### 手動でセッションIDを取得する方法

**方法1: Networkタブから取得（推奨）**

1. Instagramにログイン
2. 開発者ツールを開く（`F12`）
3. Networkタブを開く
4. ページをリロード（`F5`）
5. 任意のリクエストをクリック
6. Request Headers → Cookie から `sessionid=` の値をコピー
   - 例: `sessionid=78618252267%3A5AjTuOE5N4mVoN%3A25%3A...`
   - `sessionid=` の後から、次のセミコロン `;` までをコピー

**方法2: Applicationタブから取得**

1. Instagramにログイン
2. 開発者ツールを開く（`F12`）
3. Applicationタブを開く
4. Cookies → https://www.instagram.com を展開
5. `sessionid` の値をコピー

#### セッションファイルを更新

```powershell
python scripts/update_session_from_browser.py data/session_account1.json "SESSIONID" "USER_ID"
```

または、手動でセッションファイルを編集：

```json
{
    "authorization_data": {
        "ds_user_id": "78618252267",
        "sessionid": "78618252267%3A5AjTuOE5N4mVoN%3A25%3A..."
    }
}
```

### セッションIDが重複している場合

セッションIDが重複しているアカウントは自動的に無効化されます（アカウント凍結を防ぐため）。

重複している場合は、異なるセッションIDでセッションファイルを更新してください。

### ログインエラー

- セッションファイルを削除して再ログイン
- Instagramの認証情報が正しいか確認

### レート制限エラー（429エラー）

- `config.json`の`settings.delay_between_requests`を増やす（例: 5秒）
- 処理するアカウント数を減らす

### ロックファイルエラー

前の処理が完了していない場合は、新しい実行がスキップされます。

```powershell
# ロックファイルを削除（前のプロセスが終了していることを確認）
Remove-Item data\scheduler.lock -ErrorAction SilentlyContinue
```

---

## 開発

### コードの構造

- `src/`: メインアプリケーションコード
- `scripts/`: ユーティリティスクリプト（運用時に使用）
- `tools/`: 開発ツール（開発時に使用）

### 開発ツール

#### コードフォーマット

```powershell
# Windows
.\tools\format.bat

# Linux/Mac
./tools/format.sh
```

#### コード品質チェック

```powershell
# Windows
.\tools\lint.bat

# Linux/Mac
./tools/lint.sh
```

### インポートパス

プロジェクトルートから実行する場合、`src/`内のモジュールは以下のようにインポートできます：

```python
from src.main import InstagramDownloadBot
from src.database import UploadDatabase
```

### 技術スタック

- **Python**: 3.10+
- **主要ライブラリ**:
  - `instagrapi`: Instagram APIクライアント
  - `selenium`: ブラウザ自動化（Seleniumアップロード用）
  - `opencv-python`: 動画処理（動画変換用）
  - `sqlite3`: データベース（組み込み）

---

## 📄 ライセンス

このプロジェクトは個人利用を目的としています。
