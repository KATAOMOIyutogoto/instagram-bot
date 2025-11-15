@echo off
chcp 65001
setlocal enabledelayedexpansion

REM 正常 exit /b 0
REM 異常 exit /b 1

REM 引数チェック
if "%~1"=="" (
    echo 引数が指定されていません。
    echo 使用方法: %0 username
    exit /b 1
)

REM 1つ目のPythonスクリプトを実行
echo 1つ目のスクリプトを実行中...
py MEO.py "%1"
if errorlevel 1 (
    echo 1つ目のスクリプトがFalseでした
    exit /b 0
)

REM 1つ目が成功した場合、2つ目を実行
echo 2つ目のスクリプトを実行中...
py GBP.py "%1"
if errorlevel 1 (
    echo 2つ目のスクリプトがFlaseでした
    exit /b 0
)

echo すべての処理が完了しました
exit /b 0