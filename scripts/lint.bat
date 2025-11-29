@echo off
REM コード品質チェックスクリプト（Windows用）

echo === コード品質チェック開始 ===

REM RuffでLintチェック
echo 1. RuffでLintチェック...
ruff check src/ scripts/
if errorlevel 1 (
    echo Ruffチェックでエラーが見つかりました
    exit /b 1
)

REM Blackでフォーマットチェック
echo 2. Blackでフォーマットチェック...
black --check src/ scripts/
if errorlevel 1 (
    echo Blackチェックでフォーマットエラーが見つかりました
    echo フォーマットを修正するには: black src/ scripts/
    exit /b 1
)

REM MyPyで型チェック
echo 3. MyPyで型チェック...
mypy src/ || echo MyPyチェックで警告がありました（続行します）

echo === コード品質チェック完了 ===

