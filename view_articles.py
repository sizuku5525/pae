#!/usr/bin/env python3
"""
生成済み記事を見やすく表示するスクリプト
"""
import json
import sys
from datetime import datetime

def load_articles():
    """記事データを読み込む"""
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("記事データファイルが見つかりません")
        return None
    except json.JSONDecodeError:
        print("記事データの読み込みエラー")
        return None

def display_articles(site_id=None, limit=10):
    """記事を表示"""
    data = load_articles()
    if not data:
        return
    
    articles = data.get('articles', [])
    
    # サイトIDでフィルタ
    if site_id:
        articles = [a for a in articles if a.get('site_id') == site_id]
    
    # 最新順にソート
    articles.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    print(f"\n=== 生成済み記事 (最新{limit}件) ===\n")
    
    for i, article in enumerate(articles[:limit], 1):
        print(f"{i}. {article.get('title', '不明なタイトル')}")
        print(f"   作成日時: {article.get('created_at', '不明')}")
        print(f"   ステータス: {article.get('status', '不明')}")
        print(f"   サイト: {article.get('site_name', '不明')}")
        print(f"   文字数: {article.get('metadata', {}).get('length', 0)}")
        
        if article.get('wordpress_url'):
            print(f"   URL: {article.get('wordpress_url')}")
        
        print(f"   タグ: {', '.join(article.get('tags', []))}")
        print()

def show_stats():
    """統計情報を表示"""
    data = load_articles()
    if not data:
        return
    
    articles = data.get('articles', [])
    
    # サイト別統計
    site_stats = {}
    for article in articles:
        site_name = article.get('site_name', '不明')
        if site_name not in site_stats:
            site_stats[site_name] = {'total': 0, 'published': 0}
        
        site_stats[site_name]['total'] += 1
        if article.get('status') == '公開済み':
            site_stats[site_name]['published'] += 1
    
    print("\n=== 記事統計 ===\n")
    print(f"総記事数: {len(articles)}")
    print(f"公開済み: {sum(1 for a in articles if a.get('status') == '公開済み')}")
    
    print("\n=== サイト別統計 ===")
    for site, stats in site_stats.items():
        print(f"{site}: 総数 {stats['total']} / 公開済み {stats['published']}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        show_stats()
    else:
        # 表示件数を指定可能
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        display_articles(limit=limit)
        
        print("\n使い方:")
        print("  python view_articles.py      # 最新10件を表示")
        print("  python view_articles.py 20   # 最新20件を表示")
        print("  python view_articles.py stats # 統計情報を表示")