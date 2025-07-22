"""
完全自律型記事生成・投稿システム
AIが自分で判断して記事を生成・投稿
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AutonomousPublisher:
    """完全自律的に記事を生成・投稿するAIシステム"""
    
    def __init__(self, site_manager, generator, publisher_class, 
                 category_selector, unsplash_fetcher, content_strategist):
        self.site_manager = site_manager
        self.generator = generator
        self.publisher_class = publisher_class
        self.category_selector = category_selector
        self.unsplash_fetcher = unsplash_fetcher
        self.content_strategist = content_strategist
        
    def run_autonomous_cycle(self, site_id: str) -> Dict:
        """
        完全自律サイクルを実行
        1. 過去記事を分析
        2. 次のテーマを決定
        3. 記事を生成
        4. 自動投稿
        
        Returns:
            実行結果
        """
        logger.info(f"自律サイクル開始: サイトID {site_id}")
        
        # サイト情報を取得
        site = self.site_manager.get_site_by_id(site_id)
        if not site:
            return {'success': False, 'error': 'サイトが見つかりません'}
        
        try:
            # 1. 過去記事を分析
            logger.info("ステップ1: 過去記事分析")
            past_analysis = self.content_strategist.analyze_published_articles(site_id)
            
            # WordPress分析（オプション）
            wordpress_analysis = None
            if site.wordpress_username and site.wordpress_app_password:
                publisher = self.publisher_class(
                    site.url,
                    site.wordpress_username,
                    site.wordpress_app_password
                )
                if publisher.test_connection():
                    wordpress_analysis = self.content_strategist.analyze_wordpress_content(publisher)
            
            # 2. 次のテーマを決定
            logger.info("ステップ2: 次のテーマ決定")
            suggestions = self.content_strategist.generate_content_strategy(
                site.to_dict(),
                past_analysis,
                wordpress_analysis
            )
            
            if not suggestions:
                return {'success': False, 'error': 'テーマ提案の生成に失敗'}
            
            # 最適なテーマを選択
            selected_topic = self.content_strategist.select_next_topic(suggestions)
            logger.info(f"選択されたテーマ: {selected_topic.get('title')}")
            
            # 3. 記事を生成
            logger.info("ステップ3: 記事生成")
            
            # site_infoに戦略的情報を追加
            site_info = site.to_dict()
            site_info['strategic_intent'] = selected_topic.get('reason', '')
            site_info['target_segment'] = selected_topic.get('target', '')
            
            # 記事生成
            article = self.generator.generate_article(
                site_info=site_info,
                keywords=selected_topic.get('keywords', []),
                length=7000,
                tone='friendly'
            )
            
            if not article:
                return {'success': False, 'error': '記事生成に失敗'}
            
            # 記事にメタデータを追加
            article['id'] = f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            article['site_id'] = site_id
            article['site_name'] = site.name
            article['status'] = '下書き'
            article['created_at'] = datetime.now().isoformat()
            article['metadata'] = {
                **article.get('metadata', {}),
                'autonomous': True,
                'strategy': selected_topic,
                'past_articles_analyzed': past_analysis.get('total_articles', 0)
            }
            
            # 記事を保存
            self._save_article(article)
            
            # 4. 自動投稿
            if site.wordpress_username and site.wordpress_app_password:
                logger.info("ステップ4: 自動投稿")
                publish_result = self._publish_article(article, site)
                
                if publish_result['success']:
                    # ステータスを更新
                    article['status'] = '公開済み'
                    article['wordpress_url'] = publish_result['url']
                    article['wordpress_id'] = publish_result['wordpress_id']
                    article['published_at'] = datetime.now().isoformat()
                    self._update_article(article)
                    
                    return {
                        'success': True,
                        'article': article,
                        'strategy': selected_topic,
                        'wordpress_url': publish_result['url']
                    }
            
            return {
                'success': True,
                'article': article,
                'strategy': selected_topic,
                'status': 'draft'
            }
            
        except Exception as e:
            logger.error(f"自律サイクルエラー: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _publish_article(self, article: Dict, site) -> Dict:
        """記事をWordPressに投稿"""
        try:
            publisher = self.publisher_class(
                site.url,
                site.wordpress_username,
                site.wordpress_app_password
            )
            
            if not publisher.test_connection():
                return {'success': False, 'error': 'WordPress接続失敗'}
            
            # カテゴリ選択
            wp_categories = publisher.get_categories()
            category_ids = []
            
            if wp_categories:
                selected_category_id = self.category_selector.select_category(
                    title=article['title'],
                    content=article['content'],
                    tags=article['tags'],
                    available_categories=wp_categories
                )
                
                if selected_category_id:
                    category_ids.append(selected_category_id)
            
            # アイキャッチ画像
            featured_media_id = None
            if self.unsplash_fetcher.is_configured():
                photo = self.unsplash_fetcher.get_photo_for_article(
                    title=article['title'],
                    keywords=article['tags'],
                    content=article['content'][:500]
                )
                
                if photo:
                    featured_media_id = publisher.upload_media(
                        image_url=photo['url'],
                        alt_text=photo.get('alt_description', article['title'])
                    )
                    self.unsplash_fetcher.download_photo(photo['id'])
            
            # 投稿
            result = publisher.publish_post(
                title=article['title'],
                content=article['content'],
                excerpt=article.get('excerpt', ''),
                categories=category_ids,
                tags=article['tags'],
                featured_media_id=featured_media_id,
                status='publish'
            )
            
            if result:
                return {
                    'success': True,
                    'url': result['link'],
                    'wordpress_id': result['id']
                }
            
            return {'success': False, 'error': '投稿失敗'}
            
        except Exception as e:
            logger.error(f"投稿エラー: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _save_article(self, article: Dict):
        """記事を保存"""
        try:
            with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {'articles': []}
        
        data['articles'].insert(0, article)
        
        with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _update_article(self, article: Dict):
        """記事を更新"""
        try:
            with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for i, a in enumerate(data['articles']):
                if a['id'] == article['id']:
                    data['articles'][i] = article
                    break
            
            with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"記事更新エラー: {str(e)}")
    
    def analyze_performance(self, site_id: str) -> Dict:
        """
        パフォーマンスを分析してAIの戦略を改善
        
        Returns:
            パフォーマンス分析結果
        """
        # 将来的な実装：
        # - Google Analytics連携
        # - WordPress統計取得
        # - クリック率、滞在時間分析
        # - 人気記事の特徴抽出
        # - 改善提案
        
        return {
            'status': 'not_implemented',
            'message': 'パフォーマンス分析は今後実装予定'
        }