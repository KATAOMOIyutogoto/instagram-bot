# ブラウザのセッション情報をBotで使用する方法

## 📋 概要

ブラウザでログインできる場合、そのセッション情報（クッキー）をBotで使用できる可能性があります。

---

## 🔍 現在のセッションファイルの構造

セッションファイル（`data/session_account2.json`）には以下の情報が含まれています：

```json
{
    "authorization_data": {
        "ds_user_id": "78760622757",
        "sessionid": "78760622757%3AGV0rKO3ivspy3R%3A22%3AAYhCwRFGgILARORjgoj6lVt1eL3tA2Gn5shiOZSV2Q"
    }
}
```

この`sessionid`がブラウザのセッション情報です。

---

## 🔧 ブラウザからセッション情報を取得する方法

### 方法1: Networkタブから取得（推奨）

#### Google Chrome / Microsoft Edge

1. **Instagramにログイン**
   - https://www.instagram.com/ にアクセス
   - ログイン状態を確認

2. **開発者ツールを開く**
   - `F12`キーを押す、または右クリック→「検証」

3. **Networkタブを開く**
   - 上部のタブから「Network」を選択

4. **ページをリロード**
   - `F5`キーを押す、またはページを再読み込み
   - リクエスト一覧が表示される

5. **任意のリクエストをクリック**
   - リストから任意のリクエスト（例: `feed/timeline/` や `api/v1/users/web_profile_info/` など）を選択

6. **Request Headersを確認**
   - 「Headers」タブを選択
   - 「Request Headers」セクションを展開

7. **Cookieヘッダーから`sessionid`を取得**
   - 「Cookie:」という行を見つける
   - Cookie文字列の中から `sessionid=...` の部分を探す
   - `sessionid=` の後の値をコピー（セミコロン`;`まで、または次のクッキー名まで）

**例:**
```
Cookie: sessionid=78760622757%3AGV0rKO3ivspy3R%3A22%3A...; ds_user_id=78760622757; ...
```
この場合、`78760622757%3AGV0rKO3ivspy3R%3A22%3A...` がsessionidです。

#### より簡単な方法：検索機能を使用

1. **Networkタブを開いた状態で**
2. **`Ctrl+F`（検索）を押す**
3. **`sessionid`と入力**
4. **検索結果から`sessionid=`の後の値をコピー**

---

### 方法2: Applicationタブから取得

#### Google Chrome / Microsoft Edge

1. **Instagramにログイン**
   - https://www.instagram.com/ にアクセス
   - ログイン状態を確認

2. **開発者ツールを開く**
   - `F12`キーを押す、または右クリック→「検証」

3. **Applicationタブを開く**
   - 左側のメニューから「Application」を選択

4. **Cookiesを確認**
   - 左側の「Cookies」→「https://www.instagram.com」を展開

5. **`sessionid`を取得**
   - `sessionid`という名前のクッキーを見つける
   - 「Value」欄の値をコピー

#### Firefox

1. **Instagramにログイン**
   - https://www.instagram.com/ にアクセス

2. **開発者ツールを開く**
   - `F12`キーを押す

3. **ストレージタブを開く**
   - 「ストレージ」タブを選択

4. **Cookiesを確認**
   - 「Cookies」→「https://www.instagram.com」を展開

5. **`sessionid`を取得**
   - `sessionid`という名前のクッキーを見つける
   - 値をコピー

---

## 🔄 セッションファイルを更新する方法

### 手動で更新

1. **ブラウザから`sessionid`を取得**（上記の方法）

2. **セッションファイルを開く**
   - `data/session_account1.json`（または対象のアカウントのファイル）

3. **`authorization_data`を更新**
   ```json
   {
       "authorization_data": {
           "ds_user_id": "ユーザーID",
           "sessionid": "ブラウザから取得したsessionid"
       }
   }
   ```

4. **ファイルを保存**

5. **Botを再実行**
   ```powershell
   python -m src.scheduler --once
   ```

---

## ⚠️ 注意事項

### IPアドレスがブラックリストに入っている場合

**エラーメッセージ：**
```
We can send you an email to help you get back into your account. 
If you are sure that the password is correct, then change your IP address, 
because it is added to the blacklist of the Instagram Server
```

このエラーは、**IPアドレスがInstagramによってブロックされている**ことを示しています。

**ブラウザのセッション情報を使っても解決しない可能性があります。**
- IPアドレスがブロックされている場合、ブラウザからもアクセスできない可能性がある
- ブラウザからアクセスできる場合は、別のIPアドレスからアクセスしている可能性がある

### 対処方法

1. **IPアドレスを変更する**
   - VPNを使用
   - プロキシサーバーを使用
   - ルーターを再起動してIPアドレスを変更（動的IPの場合）

2. **しばらく待つ**
   - 24〜48時間待つと、ブロックが解除される可能性がある

3. **ブラウザのセッション情報を確認**
   - ブラウザからログインできるか確認
   - 同じIPアドレスからアクセスしているか確認

---

## 💡 ブラウザセッション情報を使うスクリプト

ブラウザからセッション情報を取得して、セッションファイルを更新するスクリプトを作成できます。

```python
import json
from pathlib import Path

def update_session_from_browser(session_file: str, sessionid: str, ds_user_id: str):
    """
    ブラウザから取得したセッション情報でセッションファイルを更新
    
    Args:
        session_file: セッションファイルのパス
        sessionid: ブラウザから取得したsessionidクッキー
        ds_user_id: ユーザーID
    """
    session_path = Path(session_file)
    
    # 既存のセッションファイルを読み込む
    if session_path.exists():
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
    else:
        # 新規作成する場合は基本的な構造を作成
        session_data = {
            "uuids": {},
            "cookies": {},
            "device_settings": {},
        }
    
    # authorization_dataを更新
    if "authorization_data" not in session_data:
        session_data["authorization_data"] = {}
    
    session_data["authorization_data"]["sessionid"] = sessionid
    session_data["authorization_data"]["ds_user_id"] = ds_user_id
    
    # ファイルを保存
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=4, ensure_ascii=False)
    
    print(f"セッションファイルを更新しました: {session_file}")

# 使用例
# update_session_from_browser(
#     "data/session_account1.json",
#     "ブラウザから取得したsessionid",
#     "ユーザーID"
# )
```

---

## 🔍 セッション情報が有効か確認する方法

### 1. ブラウザでログイン状態を確認

- Instagramにログインしているか確認
- 他のページにアクセスしてもログイン状態が維持されているか確認

### 2. セッションファイルを読み込んで確認

```python
import json

with open('data/session_account2.json', 'r', encoding='utf-8') as f:
    session = json.load(f)
    
print("sessionid:", session.get('authorization_data', {}).get('sessionid'))
print("ds_user_id:", session.get('authorization_data', {}).get('ds_user_id'))
```

### 3. Botで試してみる

```powershell
python -m src.scheduler --once
```

---

## 📝 まとめ

### ブラウザのセッション情報を使う手順

1. **ブラウザでInstagramにログイン**
2. **開発者ツールから`sessionid`を取得**
3. **セッションファイルを更新**
4. **Botを再実行**

### IPアドレスがブロックされている場合

- **ブラウザのセッション情報を使っても解決しない可能性が高い**
- **IPアドレスを変更するか、しばらく待つ必要がある**
- **ブラウザからも同じIPアドレスでアクセスできるか確認**

---

## 🔗 関連ドキュメント

- **CHALLENGE_AUTH_GUIDE.md**: チャレンジ認証の対処方法
- **START_COMMANDS.md**: 起動コマンドの説明

