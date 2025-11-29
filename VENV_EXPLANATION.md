# 仮想環境（venv）の説明

## 📋 この2つのコマンドの役割

### 1. `.\scripts\setup_venv.bat` - 仮想環境のセットアップ

**何をするコマンド？**
- Pythonの仮想環境を作成し、必要なパッケージをインストールするスクリプト

**具体的な処理内容：**

```batch
1. Pythonのバージョンを確認
2. 仮想環境を作成（`python -m venv venv`）
3. 仮想環境を有効化
4. pipをアップグレード
5. 依存パッケージをインストール（`pip install -r requirements.txt`）
```

**なぜ必要？**
- プロジェクト専用のPython環境を作成
- システムのPythonとプロジェクトのPython環境を分離
- パッケージの競合を防ぐ
- 他のプロジェクトに影響を与えない

**実行タイミング：**
- **初回セットアップ時のみ**（1回だけ）

**実行結果：**
- `venv/` フォルダが作成される
- 必要なPythonパッケージがインストールされる

---

### 2. `.\venv\Scripts\Activate.ps1` - 仮想環境の有効化

**何をするコマンド？**
- 作成した仮想環境を有効化（アクティベート）するスクリプト

**具体的な処理内容：**
- 仮想環境内のPythonを使用するように切り替える
- 仮想環境内のパッケージを使用できるようにする
- コマンドプロンプトに `(venv)` という表示が追加される

**なぜ必要？**
- 仮想環境内のPythonとパッケージを使用するため
- システムのPythonではなく、プロジェクト専用のPythonを使うため

**実行タイミング：**
- **毎回Botを実行する前**に実行する必要がある

**実行結果：**
- コマンドプロンプトの先頭に `(venv)` が表示される
- 仮想環境内のPythonとパッケージが使用可能になる

---

## 🔄 全体の流れ

### 初回セットアップ（1回だけ）

```powershell
# ステップ1: 仮想環境を作成・セットアップ
.\scripts\setup_venv.bat

# このスクリプトが実行すること：
# 1. venvフォルダを作成
# 2. 必要なパッケージをインストール
```

### 実行時（毎回）

```powershell
# ステップ1: 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# ステップ2: Botを実行
python -m src.scheduler --once
```

---

## 💡 仮想環境（venv）とは？

### なぜ仮想環境を使うのか？

**問題点：**
- システムに直接パッケージをインストールすると、他のプロジェクトと競合する可能性がある
- パッケージのバージョンが異なる場合、動作しない可能性がある
- システムのPython環境が汚れる

**解決策：**
- プロジェクトごとに独立したPython環境を作成
- その環境内でのみパッケージを管理
- 他のプロジェクトに影響を与えない

### 仮想環境の仕組み

```
プロジェクトフォルダ/
├── venv/                    ← 仮想環境（このプロジェクト専用）
│   ├── Scripts/
│   │   ├── Activate.ps1     ← 有効化スクリプト
│   │   └── python.exe       ← 仮想環境内のPython
│   └── Lib/
│       └── site-packages/   ← インストールされたパッケージ
├── src/                     ← プロジェクトのコード
├── config/                  ← 設定ファイル
└── requirements.txt         ← 必要なパッケージのリスト
```

---

## 🔍 実際の動作確認

### 仮想環境が有効化されているか確認

```powershell
# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# コマンドプロンプトに (venv) が表示される
(venv) PS C:\Users\team4\...\instagram-bot-feature-updated-config>

# Pythonのパスを確認（仮想環境内のPythonを指している）
(venv) PS> python --version
Python 3.10.x

# パッケージのインストール場所を確認
(venv) PS> pip list
```

### 仮想環境を無効化する場合

```powershell
# 無効化
deactivate

# (venv) が消える
PS C:\Users\team4\...>
```

---

## ⚠️ よくある質問

### Q: 毎回`Activate.ps1`を実行する必要がある？

**A: はい、必要です。**
- 新しいコマンドプロンプトを開いた場合
- 仮想環境が無効化された場合
- 再度Botを実行する場合

仮想環境を有効化する必要があります。

### Q: `setup_venv.bat`を毎回実行する必要がある？

**A: いいえ、初回のみです。**
- 既に`venv/`フォルダが存在する場合は再実行不要
- パッケージを追加・更新したい場合のみ再実行

### Q: 仮想環境を使わずに実行できる？

**A: できますが、推奨されません。**
- システムのPythonに直接パッケージをインストールすることも可能
- ただし、パッケージの競合や環境の汚染が発生する可能性がある

### Q: `Activate.ps1`が実行できない？

**A: PowerShellの実行ポリシーが原因の可能性があります。**

```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# 実行ポリシーを変更（必要に応じて）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# または、cmd形式のアクティベートを使用
.\venv\Scripts\activate.bat
```

---

## 📝 まとめ

| コマンド | 実行タイミング | 役割 |
|---------|--------------|------|
| `.\scripts\setup_venv.bat` | 初回のみ | 仮想環境を作成・セットアップ |
| `.\venv\Scripts\Activate.ps1` | 実行時毎回 | 仮想環境を有効化 |

### 推奨される使用方法

```powershell
# 初回セットアップ（1回だけ）
.\scripts\setup_venv.bat

# 実行時（毎回）
.\venv\Scripts\Activate.ps1
python -m src.scheduler --once
```

