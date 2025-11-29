# アカウントがスキップされる原因と対処法

## 🔍 問題の状況

8アカウント設定されているのに、7アカウントしか認識されていない、または特定のアカウントがスキップされています。

## 📋 スキップされる原因

### 1. **`enabled`フラグが`false`に設定されている**

設定ファイル（`config/config.json`）で`enabled: false`になっているアカウントは自動的にスキップされます。

**確認方法**:
```json
{
  "instagram_accounts": [
    {
      "username": "g_l_2026_1",
      "password": "adminadmin7.26",
      "session_file": "data/session_account1.json",
      "enabled": false  // ← これがあるとスキップされる
    }
  ]
}
```

**対処法**: `enabled`フラグを削除するか、`"enabled": true`に設定してください。

### 2. **アカウントの初期化に失敗している**

ログインに失敗したアカウントは失敗リストに追加され、その後の処理でスキップされます。

**ログでの確認**:
```
ERROR - アカウント7の初期化に失敗しました
```

**対処法**:
- パスワードが正しいか確認
- セッションファイルを削除して再ログイン
- 2FA認証が必要な場合は対応
- アカウントがブロックされていないか確認

### 3. **コードが7アカウントしか対応していない**

現在のコードは「7アカウント対応」となっていますが、実際には8アカウントが設定されています。

**確認方法**: ログに「使用アカウント数: 7アカウント」と表示される場合、8番目のアカウントが認識されていない可能性があります。

---

## 🔧 対処方法

### 方法1: `enabled`フラグを確認・修正

`config/config.json`を開いて、すべてのアカウントに`enabled: true`が設定されているか、または`enabled`フラグが存在しないことを確認してください。

```json
{
  "instagram_accounts": [
    {
      "username": "g_l_2026_1",
      "password": "adminadmin7.26",
      "session_file": "data/session_account1.json"
      // enabledフラグがない = 有効（デフォルト）
    },
    {
      "username": "g_l_2026_2",
      "password": "Eadminadmin7.26",
      "session_file": "data/session_account2.json",
      "enabled": true  // 明示的に有効にする
    }
  ]
}
```

### 方法2: アカウントの初期化エラーを確認

ログファイルで、どのアカウントの初期化が失敗しているか確認：

```powershell
# 初期化失敗のログを確認
Select-String -Path "logs\scheduler.log" -Pattern "アカウント.*初期化に失敗"
```

失敗しているアカウントの原因を調査：
- パスワードが正しいか
- セッションファイルが破損していないか
- Instagramアカウントがブロックされていないか

### 方法3: セッションファイルを削除して再ログイン

失敗しているアカウントのセッションファイルを削除：

```powershell
# アカウント7のセッションファイルを削除（例）
Remove-Item "data\session_account7.json" -ErrorAction SilentlyContinue
```

次回実行時に再ログインが試行されます。

### 方法4: スキップされているアカウントを確認

実行時のログで、どのアカウントが使用されているか確認：

```powershell
# 使用されているアカウントを確認
Select-String -Path "logs\scheduler.log" -Pattern "使用アカウント数|アカウント.*でログイン"
```

---

## 💡 確認コマンド

### 1. 使用アカウント数を確認

```powershell
# 最新の実行ログから使用アカウント数を確認
Select-String -Path "logs\scheduler.log" -Pattern "使用アカウント数" | Select-Object -Last 1
```

### 2. 初期化失敗のアカウントを確認

```powershell
# 初期化失敗したアカウントを確認
Select-String -Path "logs\scheduler.log" -Pattern "アカウント.*初期化に失敗" | Select-Object -Last 10
```

### 3. 設定ファイルのアカウント数を確認

```powershell
# config.jsonのアカウント数を確認
python -c "import json; config = json.load(open('config/config.json')); print(f'設定されているアカウント数: {len(config.get(\"instagram_accounts\", []))}')"
```

---

## 🐛 よくある問題

### Q: 8アカウント設定したのに7アカウントしか使われない

A: 以下を確認してください：
1. `enabled`フラグが`false`になっているアカウントがないか
2. アカウントの初期化が失敗していないか
3. 設定ファイルのJSON形式が正しいか（カンマの位置など）

### Q: 特定のアカウントだけスキップされる

A: 以下を確認してください：
1. そのアカウントの`enabled`フラグが`false`になっていないか
2. そのアカウントの初期化が失敗していないか
3. そのアカウントのパスワードが正しいか
4. セッションファイルが破損していないか

### Q: すべてのアカウントがスキップされる

A: 以下を確認してください：
1. 設定ファイルの形式が正しいか
2. すべてのアカウントの`enabled`が`false`になっていないか
3. ログファイルでエラーメッセージを確認

