# Instagramチャレンジ認証の対処方法

## 🔒 チャレンジ認証とは？

Instagramのセキュリティ機能で、自動ログインや不審なアクセスを検出した場合に追加の認証を求めるものです。

**エラーメッセージ：**
```
WARNING - チャレンジ認証が必要です。手動で対応してください
```

---

## 🔧 対処方法

### 方法1: ブラウザで手動ログインしてチャレンジ認証を完了（推奨）

1. **ブラウザでInstagramにログイン**
   - https://www.instagram.com/ にアクセス
   - アカウント `g_l_2026_1` でログイン
   - パスワード: `adminadmin7.26`

2. **チャレンジ認証を完了**
   - セキュリティチェックが表示されたら対応
   - メールやSMSで認証コードが送られる場合がある
   - 認証コードを入力して完了

3. **セッションファイルを削除**
   ```powershell
   Remove-Item "data\session_account1.json" -ErrorAction SilentlyContinue
   ```

4. **再度Botを実行**
   ```powershell
   python -m src.scheduler --once
   ```

---

### 方法2: セッションファイルを削除して再ログイン

```powershell
# アカウント1のセッションファイルを削除
Remove-Item "data\session_account1.json" -ErrorAction SilentlyContinue

# 再度Botを実行
python -m src.scheduler --once
```

---

### 方法3: しばらく待ってから再試行

チャレンジ認証は一時的な場合もあります。1-2時間待ってから再度実行してみてください。

---

## 📋 各アカウントのセッションファイルの場所

| アカウント | セッションファイル |
|-----------|------------------|
| アカウント1 | `data/session_account1.json` |
| アカウント2 | `data/session_account2.json` |
| アカウント3 | `data/session_account3.json` |
| アカウント4 | `data/session_account4.json` |
| アカウント5 | `data/session_account5.json` |
| アカウント6 | `data/session_account6.json` |
| アカウント7 | `data/session_account7.json` |
| アカウント8 | `data/session_account8.json` |

---

## 🔍 現在のエラーの状況

ログを見ると、`g_l_2026_1`（アカウント1）でチャレンジ認証が必要になっています。

**対処手順：**

1. **ブラウザでInstagramにログイン**
   - https://www.instagram.com/ にアクセス
   - ユーザー名: `g_l_2026_1`
   - パスワード: `adminadmin7.26`
   - チャレンジ認証を完了

2. **セッションファイルを削除**
   ```powershell
   Remove-Item "data\session_account1.json" -ErrorAction SilentlyContinue
   ```

3. **再度Botを実行**
   ```powershell
   python -m src.scheduler --once
   ```

---

## ⚠️ 注意事項

### チャレンジ認証が頻繁に発生する場合

- **原因**:
  - 短時間に多数のリクエストを送信している
  - 複数のアカウントで同じIPアドレスからアクセスしている
  - 不審なアクセスパターンが検出されている

- **対処法**:
  - リクエスト間隔を長くする（`delay_between_requests`を増やす）
  - 実行間隔を長くする（`--interval`を増やす）
  - 使用するアカウント数を減らす

### すべてのアカウントでチャレンジ認証が発生する場合

- **原因**:
  - 同じIPアドレスから複数のアカウントにアクセスしている
  - Instagramのレート制限に引っかかっている

- **対処法**:
  - 一時的に実行を停止して待機（数時間〜1日）
  - VPNやプロキシを使用（推奨されない場合もあり）
  - アカウントごとに異なるIPアドレスを使用

---

## 🔄 自動リトライについて

現在のコードでは、チャレンジ認証が必要な場合、そのアカウントは失敗として扱われ、他のアカウントに処理が再割り当てされます。

しかし、チャレンジ認証を手動で解決すれば、次回の実行から正常に動作するようになります。

---

## 💡 予防策

### 1. リクエスト間隔を適切に設定

`config/config.json`で設定：

```json
{
  "settings": {
    "delay_between_requests": 3  // 2秒から3秒に増やす
  }
}
```

### 2. 実行間隔を長くする

```powershell
# 1時間ごとから2時間ごとに変更
python -m src.scheduler --interval 2.0
```

### 3. 定期的にブラウザでログイン

- 定期的にブラウザでInstagramにログインして、アカウントが正常であることを確認
- これにより、チャレンジ認証の発生を減らせる可能性がある

---

## 📝 まとめ

**今すぐやること：**

1. ブラウザでInstagramにログインしてチャレンジ認証を完了
2. セッションファイルを削除
   ```powershell
   Remove-Item "data\session_account1.json" -ErrorAction SilentlyContinue
   ```
3. 再度Botを実行
   ```powershell
   python -m src.scheduler --once
   ```

---

## 🔗 関連ドキュメント

- **START_COMMANDS.md**: 起動コマンドの説明
- **README.md**: プロジェクトの概要

