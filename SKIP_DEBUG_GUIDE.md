# スキップ原因の確認方法と対処法

## 🔍 スキップされる主な原因

Instagram Botがエラーなしでスキップする場合、以下のいずれかの理由が考えられます：

### 1. **アップロード開始日時によるフィルタリング**（最も一般的）

**設定**: `config/config.json`の`upload.start_date`

現在の設定：
```json
"upload": {
  "start_date": "2025-11-23 00:00:00"
}
```

この日時より**以前**の投稿・ストーリーは自動的にスキップされます。

**ログでの確認**:
```
開始日時 (2025-11-23 00:00:00) 以前の投稿をスキップ: 3件
```

**対処法**:
- すべての投稿をアップロードしたい場合: `start_date`を削除または過去の日時に設定
- 特定の日時以降のみアップロードしたい場合: `start_date`を調整

### 2. **重複チェック（既にアップロード済み）**

データベースに既に記録されている投稿・ストーリーはスキップされます。

**ログでの確認**:
```
投稿は既にアップロード済みです: 2025-10-27 20:00:00 (dahlia_seikotsu, MSUZQCLK516049)
```

**対処法**:
- データベースのアップロード履歴を確認
- 必要に応じて、データベースから該当レコードを削除

### 3. **日時が取得できない**

メタデータファイルから日時が取得できない投稿・ストーリーはスキップされます。

**ログでの確認**:
```
投稿の日時が取得できませんでした: 3752855208574826192
ストーリーの日時が取得できませんでした: 3773949721405771320
```

**対処法**:
- メタデータファイル（`*_metadata.txt`）を確認
- メタデータファイルが存在するか確認

### 4. **スケジューラーのロック**

前の処理が完了していない場合、スケジューラーは実行をスキップします。

**ログでの確認**:
```
前の処理が完了していないため、スキップします
```

**対処法**:
- `data/scheduler.lock`ファイルを削除
- 前のプロセスが実行中でないか確認

---

## 🔧 スキップ原因を確認する方法

### 方法1: ログファイルを確認

```powershell
# スケジューラーログを確認
Get-Content logs\scheduler.log -Tail 100 | Select-String "スキップ"
```

### 方法2: アップロード状況レポートを確認

```powershell
python scripts\upload_status_report.py
```

### 方法3: データベースを確認

```powershell
python scripts\db_viewer.py
```

### 方法4: ログビューアーを使用

```powershell
python scripts\log_viewer.py
```

---

## 📝 対処方法

### 1. アップロード開始日時を変更する

`config/config.json`を編集：

```json
{
  "upload": {
    "start_date": null  // すべての投稿をアップロードする場合
    // または
    "start_date": "2025-01-01 00:00:00"  // 特定の日時以降のみ
  }
}
```

### 2. データベースのアップロード履歴を確認・削除

```powershell
# データベースビューアーで確認
python scripts\db_viewer.py

# SQLiteで直接確認
sqlite3 data\upload_history.db "SELECT * FROM uploaded_posts WHERE instagram_id = '対象のInstagram ID';"

# 特定のレコードを削除（注意：実行前にバックアップを取ってください）
sqlite3 data\upload_history.db "DELETE FROM uploaded_posts WHERE instagram_id = '対象のInstagram ID' AND location_id = '対象のLocation ID';"
```

### 3. スケジューラーのロックを解除

```powershell
# ロックファイルを削除（前のプロセスが終了していることを確認してから）
Remove-Item data\scheduler.lock -ErrorAction SilentlyContinue
```

---

## 💡 よくある質問

### Q: ダウンロードは成功したのにアップロードされない

A: 以下を確認してください：
1. `auto_upload`が`true`になっているか
2. `start_date`が設定されていないか
3. ロケーション情報が正しく設定されているか
4. データベースに既に記録されていないか

### Q: 特定の企業だけスキップされる

A: 以下を確認してください：
1. その企業のロケーション情報が正しく設定されているか
2. その企業の投稿日時が`start_date`より前でないか
3. その企業の投稿が既にアップロード済みでないか

### Q: すべてスキップされる

A: 以下を確認してください：
1. `start_date`が現在の日時より未来に設定されていないか
2. すべての投稿が既にアップロード済みでないか
3. メタデータファイルが正しく生成されているか

---

## 🔍 デバッグコマンド

スキップ原因を詳細に確認する場合：

```powershell
# 1. 最新のログを確認
Get-Content logs\scheduler.log -Tail 50

# 2. アップロード状況レポート
python scripts\upload_status_report.py

# 3. データベースのアップロード履歴
python scripts\db_viewer.py

# 4. 実行ログ
python scripts\log_viewer.py
```

