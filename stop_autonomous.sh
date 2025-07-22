#!/bin/bash

# 完全自動運営システム停止スクリプト

echo "🛑 完全自動記事生成システムを停止します"

if [ -f autonomous.pid ]; then
    PID=$(cat autonomous.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "✅ プロセス $PID を停止しました"
        rm autonomous.pid
    else
        echo "⚠️ プロセスは既に停止しています"
        rm autonomous.pid
    fi
else
    echo "❌ PIDファイルが見つかりません"
fi