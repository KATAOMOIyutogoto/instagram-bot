# ローカルテストガイド

## 1. 環境設定

### 1.1 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 1.2 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、以下の変数を設定してください：

```env
# データベース設定
DB_NAME=MEO.db
TABLE_NAME=MEO

# Chromeプロファイル設定
CHROME_PROFILE_PATH=C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data
PROFILE_NAME_1=Profile 1
PROFILE_NAME_2=Profile 2
PROFILE_NAME_3=Profile 3
PROFILE_NAME_4=Profile 4

# Instagram Cookie（オプション、現在は使用されていません）
INSTAGRAM_COOKIE_1=
INSTAGRAM_COOKIE_2=
INSTAGRAM_COOKIE_3=
INSTAGRAM_COOKIE_4=

# GBP投稿用プロファイル
PROFILE_NAME_GBP=Profile GBP

# テスト用Instagramユーザー名
TEST_USERNAME=your_test_username

# テスト用GBP Business ID
TEST_BUSINESS_ID=your_business_id

# テスト用GBP Business ID（複数ある場合）
TEST_USERNAME_num2=your_business_id_2

# 投稿の最大経過日数（0で無制限）
MAX_AGE_DAYS=3

# テスト用の開始日（YYYYMMDD形式）
TEST_USERNAME_start=20240101

# API Keys（オプション、現在は使用されていません）
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## 2. データベースの準備

### 2.1 データベースの作成

```bash
python DB_create.py
```

これで `MEO.db` が作成されます。

## 3. 個別スクリプトのテスト

### 3.1 投稿取得のテスト（post.py）

```bash
# 基本実行
python post.py <USERNAME> <PROCESS_ID>

# 例
python post.py test_user 20250115_120000
```

**引数:**
- `USERNAME`: Instagramのユーザー名
- `PROCESS_ID`: プロセスID（例: `20250115_120000`）

**動作:**
1. Instagramのプロフィールページにアクセス
2. 最新の投稿を取得（ピン留めを考慮）
3. メディア（画像/動画）をダウンロード
4. 説明文を取得
5. 重複チェック（DBに保存）

**確認ポイント:**
- `media/<USERNAME>/` にメディアファイルが保存される
- `media/<USERNAME>/description/<PROCESS_ID>` に説明文が保存される
- `log/<日付>/post_<USERNAME>_<日付>.log` にログが記録される

### 3.2 ストーリー取得のテスト（story.py）

```bash
# 基本実行
python story.py <USERNAME> <PROCESS_ID>

# 例
python story.py test_user 20250115_120000
```

**引数:**
- `USERNAME`: Instagramのユーザー名
- `PROCESS_ID`: プロセスID

**動作:**
1. Instagramのプロフィールページにアクセス
2. プロフィール写真をクリックしてストーリーを開く
3. ストーリーのメディア（動画/画像）を取得
4. 重複チェック（DBに保存）

**確認ポイント:**
- `media/<USERNAME>/` にメディアファイルが保存される
- `media/<USERNAME>/description/<PROCESS_ID>.txt` に説明文が保存される（空の場合あり）

### 3.3 GBP投稿のテスト（postGBP.py）

```bash
# 基本実行
python postGBP.py <MODE> <USERNAME> <BUSINESS_ID> <PROCESS_ID>

# 例
python postGBP.py post test_user your_business_id 20250115_120000
```

**引数:**
- `MODE`: `post` または `story`
- `USERNAME`: Instagramのユーザー名
- `BUSINESS_ID`: Google Business ProfileのBusiness ID
- `PROCESS_ID`: プロセスID

**前提条件:**
- `media/<USERNAME>/` にメディアファイルが存在すること
- `media/<USERNAME>/description/<PROCESS_ID>` に説明文が存在すること（オプション）

**動作:**
1. Google Business Profileの投稿画面を開く
2. メディアファイルをアップロード
3. 説明文を入力
4. CALLボタンを設定（オプション）
5. 投稿を送信

**確認ポイント:**
- GBPに投稿が作成される
- `log/<日付>/post_<USERNAME>_<日付>.log` または `log/<日付>/story_<USERNAME>_<日付>.log` にログが記録される

## 4. 統合テスト（GLINK_runbat_v2.py）

### 4.1 テスト用コマンドリストの作成

`GLINK_LIST_test.txt` を作成：

```
GLINK_v2 test_user
```

### 4.2 実行

```bash
python GLINK_runbat_v2.py
```

**注意:** このスクリプトは `GLINK_LIST.txt` を読み込みます。テスト時は `GLINK_LIST_test.txt` に変更するか、テスト用のユーザー名を追加してください。

## 5. データベースの確認

### 5.1 データベース内容の表示

```bash
python DB_print.py
```

### 5.2 特定ユーザーのレコード削除

```bash
# DB_delete_1record.py を編集してユーザー名とcache_keyを指定
python DB_delete_1record.py
```

## 6. トラブルシューティング

### 6.1 Chromeドライバーのエラー

- Chromeを完全に終了してから実行
- ChromeDriverManagerが自動的にドライバーをダウンロードします

### 6.2 メディアファイルが見つからない

- `media/<USERNAME>/` ディレクトリが存在するか確認
- ファイルの拡張子が正しいか確認（`.jpg`, `.mp4` など）

### 6.3 ログの確認

- `log/<日付>/` ディレクトリ内のログファイルを確認
- エラーが発生した場合は `err/<日付>/` に移動されます

### 6.4 アカウントロック

- 終了コード `3` が返された場合、60分待機します
- ログに「アカウントの自動化が検出された可能性があります」と表示されます

## 7. テストの流れ（推奨）

1. **データベースの準備**
   ```bash
   python DB_create.py
   ```

2. **投稿取得のテスト**
   ```bash
   python post.py test_user 20250115_120000
   ```

3. **取得したメディアの確認**
   - `media/test_user/` を確認

4. **GBP投稿のテスト**
   ```bash
   python postGBP.py post test_user your_business_id 20250115_120000
   ```

5. **ログの確認**
   - `log/<日付>/` 内のログファイルを確認

6. **データベースの確認**
   ```bash
   python DB_print.py
   ```

## 8. 注意事項

- テスト時は実際のInstagramアカウントを使用するため、レート制限に注意してください
- 複数のプロファイルを使用する場合は、それぞれログイン済みである必要があります
- GBP投稿にはGoogleアカウントへのログインが必要です
- メディアファイルは自動的にバックアップされます（`media/media_bk/`）

