#!/bin/bash
# コード自動整形スクリプト（Linux/Mac用）

set -e

echo "=== コード自動整形開始 ==="

# Ruffで自動修正
echo "1. Ruffで自動修正..."
ruff check --fix src/ scripts/

# Blackでフォーマット
echo "2. Blackでフォーマット..."
black src/ scripts/

echo "=== コード自動整形完了 ==="

