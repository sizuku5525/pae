"""
自動投稿モジュール
生成された記事を自動的にWordPressに投稿
"""
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import schedule
import threading

logger = logging.getLogger(__name__)


class AutoPublisher:
    """記事の自動投稿を管理"""
    
    def __init__(self, site_manager, wordpress_publisher, category_selector, unsplash_fetcher):
        self.site_manager = site_manager
        self.wordpress_publisher = wordpress_publisher
        self.category_selector = category_selector
        self.unsplash_fetcher = unsplash_fetcher
        self.is_running = False
        self.thread = None
        
    def publish_article(self, article: Dict, site) -> bool:
        """
        記事を自動投稿
        
        Args:
            article: 記事データ
            site: サイト情報
            
        Returns:
            成功時True
        """
        try:
            # WordPressPublisherを初期化
            publisher = self.wordpress_publisher(
                site.url,
                site.wordpress_username,
                site.wordpress_app_password
            )
            
            # 接続テスト
            if not publisher.test_connection():
                logger.error(f"WordPress接続失敗: {site.name}")
                return False
            
            # カテゴリを自動選択
            wp_categories = publisher.get_categories()
            category_ids = []
            
            if wp_categories:
                selected_category_id = self.category_selector.select_category(
                    title=article.get('title', ''),
                    content=article.get('content', ''),
                    tags=article.get('tags', []),
                    available_categories=wp_categories
                )
                
                if selected_category_id:
                    category_ids.append(selected_category_id)
                    for cat in wp_categories:
                        if cat['id'] == selected_category_id:
                            logger.info(f"カテゴリ選択: {cat['name']}")
                            break
            
            # アイキャッチ画像を取得
            featured_media_id = None
            if self.unsplash_fetcher.is_configured():
                photo = self.unsplash_fetcher.get_photo_for_article(
                    title=article.get('title', ''),
                    keywords=article.get('tags', []),
                    content=article.get('content', '')[:500]
                )
                
                if photo:
                    featured_media_id = publisher.upload_media(
                        image_url=photo['url'],
                        alt_text=photo.get('alt_description', article.get('title', ''))
                    )
                    self.unsplash_fetcher.download_photo(photo['id'])
            
            # 記事を投稿
            result = publisher.publish_post(
                title=article.get('title', 'Untitled'),
                content=article.get('content', ''),
                excerpt=article.get('excerpt', ''),
                categories=category_ids,
                tags=article.get('tags', []),
                featured_media_id=featured_media_id,
                status='publish'
            )
            
            if result:
                logger.info(f"投稿成功: {result['link']}")
                return True
            else:
                logger.error("投稿失敗")
                return False
                
        except Exception as e:
            logger.error(f"自動投稿エラー: {str(e)}")
            return False
    
    def publish_pending_articles(self):
        """
        下書き状態の記事を自動投稿
        """
        try:
            import json
            
            # 記事データを読み込む
            with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
            
            updated = False
            
            for i, article in enumerate(articles_data.get('articles', [])):
                # 下書き状態の記事のみ処理
                if article.get('status') == '下書き':
                    site = self.site_manager.get_site_by_id(article.get('site_id'))
                    
                    if site and site.wordpress_username and site.wordpress_app_password:
                        logger.info(f"自動投稿開始: {article.get('title', 'Untitled')}")
                        
                        if self.publish_article(article, site):
                            # ステータスを更新
                            articles_data['articles'][i]['status'] = '公開済み'
                            articles_data['articles'][i]['published_at'] = datetime.now().isoformat()
                            updated = True
                            
                            # 投稿間隔を空ける（スパム防止）
                            time.sleep(60)  # 1分待機
            
            # 更新があれば保存
            if updated:
                with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
                    json.dump(articles_data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f"自動投稿処理エラー: {str(e)}")
    
    def schedule_publishing(self, interval_hours: int = 6):
        """
        定期的な自動投稿をスケジュール
        
        Args:
            interval_hours: 投稿間隔（時間）
        """
        schedule.every(interval_hours).hours.do(self.publish_pending_articles)
        
        def run_schedule():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにチェック
        
        self.is_running = True
        self.thread = threading.Thread(target=run_schedule)
        self.thread.start()
        
        logger.info(f"自動投稿スケジュール開始: {interval_hours}時間ごと")
    
    def stop_scheduling(self):
        """スケジュールを停止"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        logger.info("自動投稿スケジュール停止")