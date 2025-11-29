@echo off
REM 仮想環境セットアップ用バッチファイル

cd /d "%~dp0\.."

echo ========================================
echo 仮想環境のセットアップを開始します
echo ========================================
echo.

REM Pythonのバージョンを確認
python --version
if errorlevel 1 (
    echo エラー: Pythonがインストールされていません
    echo Python 3.10以上をインストールしてください
    pause
    exit /b 1
)

echo.
echo 1. 仮想環境を作成中...
python -m venv venv
if errorlevel 1 (
    echo エラー: 仮想環境の作成に失敗しました
    pause
    exit /b 1
)

echo.
echo 2. 仮想環境を有効化中...
call venv\Scripts\activate.bat

echo.
echo 3. pipをアップグレード中...
python -m pip install --upgrade pip

echo.
echo 4. 依存パッケージをインストール中...
pip install -r requirements.txt
if errorlevel 1 (
    echo エラー: 依存パッケージのインストールに失敗しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo セットアップが完了しました！
echo ========================================
echo.
echo 次のステップ:
echo 1. 仮想環境を有効化: venv\Scripts\activate.bat
echo 2. 設定ファイルを編集: config\config.json
echo 3. テスト実行: python -m src.scheduler --once
echo.
pause

