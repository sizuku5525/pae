#!/usr/bin/env python3
"""
記事の自動投稿スクリプト
生成された下書き記事を自動的にWordPressに投稿
"""
import logging
import json
import sys
from modules.site_manager import SiteManager
from modules.wordpress_publisher import WordPressPublisher
from modules.category_selector import CategorySelector
from modules.unsplash_fetcher import UnsplashFetcher
from modules.auto_publisher import AutoPublisher

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    print("記事自動投稿スクリプト")
    print("-" * 50)
    
    # マネージャーを初期化
    site_manager = SiteManager()
    category_selector = CategorySelector()
    unsplash_fetcher = UnsplashFetcher()
    
    # AutoPublisherを初期化
    auto_publisher = AutoPublisher(
        site_manager=site_manager,
        wordpress_publisher=WordPressPublisher,
        category_selector=category_selector,
        unsplash_fetcher=unsplash_fetcher
    )
    
    # オプションを表示
    print("\n実行モードを選択してください:")
    print("1. 今すぐ下書き記事をすべて投稿")
    print("2. 定期的な自動投稿を開始（6時間ごと）")
    print("3. 定期的な自動投稿を開始（カスタム間隔）")
    print("0. 終了")
    
    choice = input("\n選択 (0-3): ").strip()
    
    if choice == "1":
        # 即座に投稿
        print("\n下書き記事を投稿中...")
        auto_publisher.publish_pending_articles()
        print("完了しました。")
        
    elif choice == "2":
        # 6時間ごとの自動投稿
        print("\n6時間ごとの自動投稿を開始します。")
        print("停止するには Ctrl+C を押してください。")
        try:
            auto_publisher.schedule_publishing(interval_hours=6)
            # 最初の実行
            auto_publisher.publish_pending_articles()
            # 待機
            while True:
                pass
        except KeyboardInterrupt:
            print("\n\n自動投稿を停止中...")
            auto_publisher.stop_scheduling()
            print("停止しました。")
            
    elif choice == "3":
        # カスタム間隔
        interval = input("投稿間隔を時間単位で入力してください (例: 12): ").strip()
        try:
            interval_hours = int(interval)
            if interval_hours < 1:
                print("エラー: 1時間以上を指定してください。")
                return
                
            print(f"\n{interval_hours}時間ごとの自動投稿を開始します。")
            print("停止するには Ctrl+C を押してください。")
            
            auto_publisher.schedule_publishing(interval_hours=interval_hours)
            # 最初の実行
            auto_publisher.publish_pending_articles()
            # 待機
            while True:
                pass
        except ValueError:
            print("エラー: 有効な数値を入力してください。")
        except KeyboardInterrupt:
            print("\n\n自動投稿を停止中...")
            auto_publisher.stop_scheduling()
            print("停止しました。")
    
    elif choice == "0":
        print("終了します。")
    
    else:
        print("無効な選択です。")


def show_pending_articles():
    """下書き記事の一覧を表示"""
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        
        pending_count = 0
        print("\n下書き記事一覧:")
        print("-" * 80)
        
        for article in articles_data.get('articles', []):
            if article.get('status') == '下書き':
                pending_count += 1
                print(f"- {article.get('title', 'Untitled')}")
                print(f"  サイト: {article.get('site_name', 'Unknown')}")
                print(f"  作成日: {article.get('created_at', 'Unknown')}")
                print()
        
        print(f"合計: {pending_count}件の下書き記事")
        return pending_count > 0
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        return False


if __name__ == "__main__":
    # 下書き記事を確認
    if show_pending_articles():
        print("-" * 80)
        main()
    else:
        print("\n投稿する下書き記事がありません。")
        print("先に記事を生成してください。")