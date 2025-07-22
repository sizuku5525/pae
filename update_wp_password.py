#!/usr/bin/env python3
"""
WordPressアプリケーションパスワードを更新するスクリプト
ユーザーに正しい形式を入力してもらう
"""
import json

print("WordPress アプリケーションパスワード更新")
print("-" * 50)
print("\nWordPressの管理画面で表示されるアプリケーションパスワードを")
print("正確に入力してください。")
print("\n例: xxxx xxxx xxxx xxxx xxxx xxxx")
print("（4文字ごとにスペースがある形式）")
print("\n現在保存されているパスワード: Sy-26120895sy")
print("-" * 50)

# ユーザーから入力を受け取る
new_password = input("\n新しいパスワードを入力してください: ").strip()

if not new_password:
    print("パスワードが入力されませんでした。終了します。")
    exit(1)

# 確認
print(f"\n入力されたパスワード: '{new_password}'")
confirm = input("このパスワードで更新しますか？ (y/n): ").lower()

if confirm != 'y':
    print("キャンセルしました。")
    exit(0)

# sites.jsonを更新
try:
    with open('config/sites.json', 'r', encoding='utf-8') as f:
        sites_data = json.load(f)
    
    # 最初のサイトのパスワードを更新
    if sites_data['sites']:
        sites_data['sites'][0]['wordpress_app_password'] = new_password
        
        with open('config/sites.json', 'w', encoding='utf-8') as f:
            json.dump(sites_data, f, ensure_ascii=False, indent=2)
        
        print("\n✅ パスワードを更新しました。")
        print("テストを実行して確認してください: python3 test_wp_publish.py")
    else:
        print("❌ サイトが見つかりません。")
        
except Exception as e:
    print(f"❌ エラー: {str(e)}")