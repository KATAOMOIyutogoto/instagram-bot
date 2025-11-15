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

echo === ストーリー処理 ===
echo ストーリー取得スクリプトを実行中...
py MEO.py "%1"
if errorlevel 1 (
    echo ストーリー取得スクリプトがFalseでした
) else (
    echo GBP投稿スクリプトを実行中...
    py GBP.py "%1"
    if errorlevel 1 (
        echo GBP投稿スクリプトがFalseでした
    )
)


REM プロセスIDを取得
set "PID=%RANDOM%_%TIME:~6,5%"
set "PID=%PID:.=%"

echo === 投稿処理 ===
py post.py "%1" "%PID%"
if errorlevel 1 (
    echo 投稿取得スクリプトがFalseでした

) else (
    echo GBP投稿スクリプトを実行中...
    py post_GBP.py "%1" "%PID%"
    if errorlevel 1 (
        echo GBP投稿スクリプトがFalseでした
    )
)

echo すべての処理が完了しました
exit /b 0