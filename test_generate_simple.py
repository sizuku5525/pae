#!/usr/bin/env python3
"""
シンプルな記事生成テスト（デバッグ付き）
"""
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.generator import ArticleGenerator
from modules.site_manager import SiteManager

print("=== シンプル記事生成テスト ===\n")

# 1. サイト情報を取得
site_manager = SiteManager()
sites = site_manager.get_all_sites()

if not sites:
    print("❌ サイトが登録されていません")
    exit(1)

site = sites[0]
print(f"✅ 対象サイト: {site.name}")
print(f"   URL: {site.url}")
print(f"   ジャンル: {site.genre}")

# 2. 記事生成器を初期化
print("\n記事生成器を初期化中...")
try:
    generator = ArticleGenerator()
    print("✅ 記事生成器の初期化成功")
except Exception as e:
    print(f"❌ 初期化エラー: {str(e)}")
    exit(1)

# 3. 記事を生成
print("\n記事を生成中...")
start_time = time.time()

try:
    article = generator.generate_article(
        site_info=site.to_dict(),
        keywords=site.keywords_focus.split(',') if site.keywords_focus else [],
        length=3000,  # テスト用に短めに
        tone='friendly'
    )
    
    elapsed_time = time.time() - start_time
    print(f"✅ 記事生成成功（{elapsed_time:.1f}秒）")
    
    # 4. 結果を表示
    print("\n=== 生成された記事 ===")
    print(f"タイトル: {article['title']}")
    print(f"説明: {article['description'][:100]}...")
    print(f"タグ: {', '.join(article['tags'])}")
    print(f"文字数: {len(article['content'])}")
    print(f"記事タイプ: {article['metadata']['article_type']}")
    
    # 5. ファイルに保存（オプション）
    filename = f"test_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(article, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 記事を {filename} に保存しました")
    
except Exception as e:
    print(f"❌ 記事生成エラー: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)