# Instagram Bot 起動コマンド解析

## 📋 起動方法の概要

Instagram Botを起動する方法は、大きく分けて2つあります：

1. **スケジューラーを使用（推奨）**: 定期実行や1回実行を管理
2. **メインスクリプトを直接実行**: 1回だけ実行

---

## 🚀 起動コマンド一覧

### 方法1: スケジューラーを使用（推奨）

#### 1. テスト実行（1回だけ実行）

```powershell
# 仮想環境を使用する場合
.\venv\Scripts\Activate.ps1
python -m src.scheduler --once

# 仮想環境を使用しない場合（グローバルのPythonを使用）
python -m src.scheduler --once
```

**説明**:
- `--once`: 1回だけ実行して終了
- 前の処理が完了していない場合はスキップ（ロックファイルチェック）

#### 2. 定期実行（デフォルト: 1時間ごと）

```powershell
# 仮想環境を使用する場合
.\venv\Scripts\Activate.ps1
python -m src.scheduler

# 仮想環境を使用しない場合
python -m src.scheduler
```

**説明**:
- デフォルトで1時間ごとに実行
- `Ctrl+C`で停止可能
- バックグラウンドで実行される

#### 3. 定期実行（カスタム間隔）

```powershell
# 30分ごと
python -m src.scheduler --interval 0.5

# 2時間ごと
python -m src.scheduler --interval 2.0

# 0.1時間ごと（6分ごと）
python -m src.scheduler --interval 0.1
```

**説明**:
- `--interval`: 実行間隔を時間単位で指定
- 小数も使用可能（0.5 = 30分、2.0 = 2時間）

#### 4. ロックファイルを指定

```powershell
python -m src.scheduler --once --lock-file data/custom_lock.lock
```

**説明**:
- `--lock-file`: ロックファイルのパスを指定（デフォルト: `data/scheduler.lock`）
- 複数のスケジューラーを同時に実行する場合などに使用

---

### 方法2: メインスクリプトを直接実行

#### 1回だけ実行

```powershell
# 仮想環境を使用する場合
.\venv\Scripts\Activate.ps1
python -m src.main

# 仮想環境を使用しない場合
python -m src.main
```

**説明**:
- 1回だけ実行して終了
- スケジューラーを使用しないため、ロックファイルチェックなし
- 実行結果をコンソールに表示

---

## 🔧 スケジューラーのオプション

### 利用可能なオプション

| オプション | 説明 | デフォルト値 |
|-----------|------|------------|
| `--once` | 1回だけ実行して終了（定期実行しない） | なし |
| `--interval` | 実行間隔（時間）。例: `0.5`（30分）、`1.0`（1時間） | `1.0` |
| `--lock-file` | ロックファイルのパス | `data/scheduler.lock` |

### 使用例

```powershell
# 1回だけ実行
python -m src.scheduler --once

# 30分ごとに定期実行
python -m src.scheduler --interval 0.5

# 1回だけ実行（カスタムロックファイル）
python -m src.scheduler --once --lock-file data/custom.lock

# 2時間ごとに定期実行
python -m src.scheduler --interval 2.0
```

---

## 📝 実行前の準備

### 1. 仮想環境のセットアップ（初回のみ）

```powershell
# 仮想環境を作成・セットアップ
.\scripts\setup_venv.bat

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1
```

### 2. 設定ファイルの確認

`config/config.json`が正しく設定されているか確認：

- Instagramアカウント情報
- ターゲット企業リスト
- Google Business Profile設定
- アップロード設定

---

## 🔍 実行時の動作

### スケジューラー（`src.scheduler`）の動作

1. **ロックファイルチェック**
   - 前の処理が完了していない場合はスキップ
   - `data/scheduler.lock`ファイルで確認

2. **Botの初期化**
   - 設定ファイル（`config/config.json`）を読み込み
   - 複数アカウントが設定されている場合は、各アカウントをローテーション

3. **ダウンロード処理**
   - すべての企業のコンテンツをダウンロード
   - 投稿・ストーリーを取得

4. **アップロード処理**（`auto_upload: true`の場合）
   - ダウンロードしたコンテンツをGoogle Business Profileにアップロード
   - 重複チェック・日時フィルタリングを実行

5. **ログ記録**
   - `logs/scheduler.log`に実行ログを記録
   - データベースに実行履歴を記録

---

## 📊 実行結果の確認

### ログファイル

```powershell
# スケジューラーログを確認
Get-Content logs\scheduler.log -Tail 50

# リアルタイムで監視
Get-Content logs\scheduler.log -Wait -Tail 20
```

### 実行ログレポート

```powershell
# 実行ログを確認
python scripts\log_viewer.py

# アップロード状況レポート
python scripts\upload_status_report.py
```

### データベース確認

```powershell
# データベースビューアー
python scripts\db_viewer.py logs
```

---

## ⚠️ 注意事項

### 1. ロックファイル

- 前の処理が完了していない場合、新しい実行はスキップされます
- ロックファイルを手動で削除する場合は、前のプロセスが終了していることを確認してください

```powershell
# ロックファイルを削除（前のプロセスが終了していることを確認）
Remove-Item data\scheduler.lock -ErrorAction SilentlyContinue
```

### 2. 実行間隔

- 実行間隔は実際の処理時間に依存します
- 処理が長時間かかる場合、次の実行は前の処理が完了してから開始されます

### 3. エラー時の動作

- エラーが発生しても、スケジューラーは停止しません
- エラーはログファイルに記録されます
- 定期的にログを確認することを推奨します

---

## 💡 よくある使用方法

### テスト実行（1回だけ）

```powershell
.\venv\Scripts\Activate.ps1
python -m src.scheduler --once
```

### 定期実行（1時間ごと・バックグラウンド）

```powershell
.\venv\Scripts\Activate.ps1
python -m src.scheduler
```

### 定期実行（30分ごと）

```powershell
.\venv\Scripts\Activate.ps1
python -m src.scheduler --interval 0.5
```

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

## 🐛 トラブルシューティング

### エラー: "ModuleNotFoundError"

```powershell
# 仮想環境が有効化されているか確認
# または、依存パッケージをインストール
pip install -r requirements.txt
```

### エラー: "前の処理が完了していないため、スキップします"

```powershell
# 前のプロセスが終了していることを確認
# ロックファイルを削除（必要に応じて）
Remove-Item data\scheduler.lock -ErrorAction SilentlyContinue
```

### エラー: "Botの初期化に失敗しました"

- 設定ファイル（`config/config.json`）を確認
- Instagramアカウントの認証情報を確認
- セッションファイルを削除して再ログイン

---

## 📚 関連ドキュメント

- **README.md**: プロジェクトの概要とクイックスタート
- **docs/GUIDE.md**: セットアップ・実行ガイド
- **PROJECT_ANALYSIS.md**: プロジェクトの詳細解析

