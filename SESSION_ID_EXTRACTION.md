# セッションIDの抽出方法（Networkタブから）

## 📋 あなたが取得したCookieヘッダー

```
cookie: datr=HjAqaXNKotscEy8nPQB5QNXz; ig_did=8F0C60D5-CCD8-4230-8BFD-2BEF75F0FB80; mid=aSowHgALAAGxhUV5bDVEZNoIsSSa; ig_nrcb=1; ps_l=1; ps_n=1; wd=1474x945; csrftoken=vy522cWKDiw8NsPp35LnGUhul7j024uG; sessionid=78618252267%3A5AjTuOE5N4mVoN%3A25%3AAYjYe3PSLh11Xq0YS_s8haALFJ7YXKJ8ETb-mgHEbw; ds_user_id=78618252267; rur="EAG\05478618252267\0541795916791:01fe8b13c2aed4404405bcd4042b10d1e525041a072a320bec8e47ce5ce3843347c13b1d"
```

## ✅ 抽出すべき情報

### 1. sessionid
```
78618252267%3A5AjTuOE5N4mVoN%3A25%3AAYjYe3PSLh11Xq0YS_s8haALFJ7YXKJ8ETb-mgHEbw
```

**抽出方法：**
- Cookie文字列の中から `sessionid=` を探す
- `sessionid=` の後から、次のセミコロン `;` まで（または文字列の終わりまで）をコピー

### 2. ds_user_id
```
78618252267
```

**抽出方法：**
- Cookie文字列の中から `ds_user_id=` を探す
- `ds_user_id=` の後から、次のセミコロン `;` まで（または文字列の終わりまで）をコピー

## 🔧 セッションファイルへの反映

### 方法1: スクリプトを使用（推奨）

```powershell
python scripts/update_session_from_browser.py data/session_account1.json "78618252267%3A5AjTuOE5N4mVoN%3A25%3AAYjYe3PSLh11Xq0YS_s8haALFJ7YXKJ8ETb-mgHEbw" "78618252267"
```

### 方法2: 手動で編集

セッションファイル（例: `data/session_account1.json`）を開いて、以下を更新：

```json
{
    "authorization_data": {
        "ds_user_id": "78618252267",
        "sessionid": "78618252267%3A5AjTuOE5N4mVoN%3A25%3AAYjYe3PSLh11Xq0YS_s8haALFJ7YXKJ8ETb-mgHEbw"
    }
}
```

## 📝 注意事項

1. **sessionidの値は完全にコピーする**
   - `sessionid=` の後の値全体をコピー
   - セミコロン `;` は含めない

2. **ds_user_idも一緒に取得する**
   - sessionidから自動抽出も可能ですが、明示的に指定する方が確実

3. **URLエンコードされた値はそのまま使用**
   - `%3A` などのエンコードされた文字はそのまま使用
   - デコードしない

## ✅ 確認方法

セッションファイルを更新した後、以下で確認：

```powershell
# すべてのアカウントのログイン状態を確認
python scripts/check_all_accounts_login.py
```

