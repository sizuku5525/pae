#!/bin/bash

# 完全自動運営システム起動スクリプト

echo "🤖 完全自動記事生成システムを起動します"
echo "=================================="

# ログディレクトリ作成
mkdir -p logs
mkdir -p data

# 仮想環境をアクティベート
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# バックグラウンドで実行（nohup使用）
echo "バックグラウンドで起動中..."
nohup python3 -c "
import sys
sys.path.append('.')
from fully_autonomous import FullyAutonomousSystem
system = FullyAutonomousSystem()
system.start_scheduler()
" > logs/autonomous_output.log 2>&1 &

# プロセスIDを保存
echo $! > autonomous.pid

echo "✅ 起動完了"
echo "プロセスID: $(cat autonomous.pid)"
echo ""
echo "ログ確認: tail -f logs/autonomous.log"
echo "停止方法: ./stop_autonomous.sh"
echo ""
echo "統計確認: cat data/automation_stats.json"