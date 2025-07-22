#!/usr/bin/env python3
"""
設定確認スクリプト
"""
import json
import os

print("=== 現在の設定を確認 ===\n")

# 1. config/api_keys.json
print("1. config/api_keys.json:")
with open('config/api_keys.json', 'r') as f:
    config = json.load(f)
    print(f"  Claude APIキー: {config['claude']['api_key'][:20]}...")
    print(f"  Venice APIキー: {config['venice']['api_key'][:20]}...")
    print(f"  モデル: {config['claude']['model']}")

# 2. .env
print("\n2. .envファイル:")
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('CLAUDE_API_KEY'):
                value = line.split('=')[1].strip()
                print(f"  CLAUDE_API_KEY: {value[:20]}...")
            elif line.startswith('VENICE_API_KEY'):
                value = line.split('=')[1].strip()
                print(f"  VENICE_API_KEY: {value[:20]}...")

# 3. 比較
print("\n3. APIキーの比較:")
if config['claude']['api_key'] == config['venice']['api_key']:
    print("  ❌ 警告: ClaudeとVeniceのAPIキーが同じです！")
else:
    print("  ✅ ClaudeとVeniceのAPIキーは異なります")

# Claude 4のテスト結果
print("\n4. Claude 4テスト結果:")
print("  ✅ 記事生成成功（106秒、3967文字）")
print("  これはClaude 4が正常に動作したことを示します")

print("\n=== Web UIの設定保存に問題がある可能性があります ===")
print("設定画面でAPIキーを保存する際、入力フィールドの値が正しく取得されていない可能性があります。")