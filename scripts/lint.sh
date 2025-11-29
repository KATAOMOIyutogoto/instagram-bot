#!/bin/bash
# コード品質チェックスクリプト（Linux/Mac用）

set -e

echo "=== コード品質チェック開始 ==="

# RuffでLintチェック
echo "1. RuffでLintチェック..."
ruff check src/ scripts/

# Blackでフォーマットチェック
echo "2. Blackでフォーマットチェック..."
black --check src/ scripts/

# MyPyで型チェック
echo "3. MyPyで型チェック..."
mypy src/ || true  # エラーがあっても続行

echo "=== コード品質チェック完了 ==="

