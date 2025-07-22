#!/bin/bash
# Flaskアプリを起動するスクリプト

# 仮想環境をアクティベート
source venv/bin/activate

# Flaskアプリを起動
echo "🚀 AutoBlogManager を起動しています..."
echo "📌 http://localhost:5000 でアクセスできます"
echo "停止するには Ctrl+C を押してください"
echo ""

python app.py