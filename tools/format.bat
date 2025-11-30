@echo off
REM コード自動整形スクリプト（Windows用）

echo === コード自動整形開始 ===

REM Ruffで自動修正
echo 1. Ruffで自動修正...
ruff check --fix src/ scripts/

REM Blackでフォーマット
echo 2. Blackでフォーマット...
black src/ scripts/

echo === コード自動整形完了 ===

