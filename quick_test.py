#!/usr/bin/env python3
"""
最小限の記事生成テスト
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.generator import ArticleGenerator

# 最小限のテスト
try:
    print("Claude 4 Sonnetで記事生成テスト中...")
    
    generator = ArticleGenerator()
    
    site_info = {
        'name': 'テストブログ',
        'genre': 'テクノロジー',
        'site_purpose': 'AI技術の解説'
    }
    
    article = generator.generate_article(
        site_info=site_info,
        keywords=['Claude 4', 'AI', '最新技術'],
        length=1000  # 短めでテスト
    )
    
    print(f"\n✅ 生成成功！")
    print(f"タイトル: {article['title']}")
    print(f"文字数: {len(article['content'])}文字")
    print(f"\n最初の200文字:")
    print(article['content'][:200] + "...")
    
except Exception as e:
    print(f"\n❌ エラー: {str(e)}")