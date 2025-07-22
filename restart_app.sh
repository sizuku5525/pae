#!/bin/bash
# Flaskアプリを再起動

echo "🔄 Flaskアプリを再起動します..."

# 既存のプロセスを終了
pkill -f "python app.py" 2>/dev/null || true

# 少し待つ
sleep 1

# 仮想環境をアクティベートして起動
source venv/bin/activate
python app.py