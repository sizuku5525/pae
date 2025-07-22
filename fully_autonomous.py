#!/usr/bin/env python3
"""
完全自動化記事生成システム
人間は初期設定のみ、あとはAIが全自動で運営
"""
import json
import logging
import time
import schedule
import os
from datetime import datetime, timedelta
from modules.site_manager import SiteManager
from modules.generator import ArticleGenerator
from modules.wordpress_publisher import WordPressPublisher
from modules.category_selector import CategorySelector
from modules.unsplash_fetcher import UnsplashFetcher
from modules.content_strategist import ContentStrategist
from modules.autonomous_publisher import AutonomousPublisher
import anthropic
import threading

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/autonomous.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FullyAutonomousSystem:
    """完全自動運営システム"""
    
    def __init__(self):
        # 設定読み込み
        self.load_config()
        
        # マネージャー初期化
        self.site_manager = SiteManager()
        self.generator = ArticleGenerator()
        self.category_selector = CategorySelector()
        self.unsplash_fetcher = UnsplashFetcher()
        
        # Claude API初期化
        self.init_claude()
        
        # 統計情報を読み込み（既存のデータがあれば使用）
        try:
            with open('data/automation_stats.json', 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
        except:
            self.stats = {
                'total_generated': 0,
                'total_published': 0,
                'errors': 0,
                'last_run': None
            }
        
    def load_config(self):
        """自動化設定を読み込み"""
        try:
            with open('config/automation_settings.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            # デフォルト設定
            self.config = {
                'enabled': True,
                'sites': {},  # site_id: settings
                'global': {
                    'max_articles_per_day': 5,
                    'min_interval_minutes': 120,
                    'operation_hours': {
                        'start': 6,  # 6:00
                        'end': 23    # 23:00
                    },
                    'auto_publish': True,
                    'require_approval': False
                }
            }
            self.save_config()
    
    def save_config(self):
        """設定を保存"""
        with open('config/automation_settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def init_claude(self):
        """Claude API初期化"""
        try:
            with open('config/api_keys.json', 'r') as f:
                api_keys = json.load(f)
            
            claude_api_key = api_keys.get('claude', {}).get('api_key')
            if not claude_api_key:
                raise Exception("Claude APIキーが設定されていません")
                
            self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
            self.content_strategist = ContentStrategist(self.claude_client)
            
        except Exception as e:
            logger.error(f"Claude API初期化エラー: {str(e)}")
            raise
    
    def run_cycle_for_site(self, site):
        """1サイトの自動サイクルを実行"""
        logger.info(f"🤖 自動サイクル開始: {site.name}")
        
        try:
            # サイト固有の設定を取得
            site_config = self.config['sites'].get(site.site_id, {})
            max_articles = site_config.get('max_articles_per_day', 
                                         self.config['global']['max_articles_per_day'])
            
            # 今日の記事数を確認
            today_count = self.get_today_article_count(site.site_id)
            if today_count >= max_articles:
                logger.info(f"本日の上限到達: {today_count}/{max_articles}")
                return
            
            # 1. 過去記事分析
            past_analysis = self.content_strategist.analyze_published_articles(site.site_id)
            logger.info(f"過去記事分析完了: {past_analysis['total_articles']}件")
            
            # WordPress分析
            wordpress_analysis = None
            if site.wordpress_username and site.wordpress_app_password:
                try:
                    publisher = WordPressPublisher(
                        site.url,
                        site.wordpress_username,
                        site.wordpress_app_password
                    )
                    if publisher.test_connection():
                        wordpress_analysis = self.content_strategist.analyze_wordpress_content(publisher)
                except:
                    pass
            
            # 2. AIが自動でテーマ決定
            suggestions = self.content_strategist.generate_content_strategy(
                site.to_dict(),
                past_analysis,
                wordpress_analysis
            )
            
            if not suggestions:
                logger.error("テーマ生成失敗")
                self.stats['errors'] += 1
                return
            
            # 自動選択ロジック
            selected_topic = self.auto_select_topic(suggestions, past_analysis)
            logger.info(f"選択テーマ: {selected_topic['title']}")
            
            # 3. 記事生成
            site_info = site.to_dict()
            site_info['strategic_intent'] = selected_topic.get('reason', '')
            site_info['target_segment'] = selected_topic.get('target', '')
            
            article = self.generator.generate_article(
                site_info=site_info,
                keywords=selected_topic.get('keywords', []),
                length=self.config.get('article_length', 3000),
                tone='friendly'
            )
            
            if not article:
                logger.error("記事生成失敗")
                self.stats['errors'] += 1
                return
            
            # メタデータ追加
            article['id'] = f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            article['site_id'] = site.site_id
            article['site_name'] = site.name
            article['status'] = '下書き'
            article['created_at'] = datetime.now().isoformat()
            article['metadata'] = {
                **article.get('metadata', {}),
                'fully_autonomous': True,
                'strategy': selected_topic,
                'cycle_number': self.stats['total_generated'] + 1
            }
            
            # 記事保存
            self.save_article(article)
            self.stats['total_generated'] += 1
            logger.info(f"記事生成完了: {article['title']}")
            
            # 4. 自動投稿
            if self.config['global']['auto_publish'] and not self.config['global']['require_approval']:
                if site.wordpress_username and site.wordpress_app_password:
                    time.sleep(5)  # 少し待機
                    
                    result = self.publish_article(article, site)
                    if result['success']:
                        self.stats['total_published'] += 1
                        logger.info(f"自動投稿成功: {result['url']}")
                    else:
                        logger.error(f"投稿失敗: {result.get('error')}")
            
            # 統計更新
            self.stats['last_run'] = datetime.now().isoformat()
            self.save_stats()
            
        except Exception as e:
            logger.error(f"サイクルエラー: {str(e)}")
            self.stats['errors'] += 1
    
    def auto_select_topic(self, suggestions, past_analysis):
        """AIの提案から自動で最適なものを選択"""
        # 選択ロジック
        # 1. 過去記事との重複チェック
        # 2. キーワードの多様性
        # 3. 期待効果の高さ
        
        past_titles = past_analysis.get('titles', [])
        
        for suggestion in suggestions:
            # タイトルの類似度チェック
            is_duplicate = any(
                self.calculate_similarity(suggestion['title'], past_title) > 0.7
                for past_title in past_titles
            )
            
            if not is_duplicate:
                return suggestion
        
        # 重複がなければ最初の提案を選択
        return suggestions[0]
    
    def calculate_similarity(self, text1, text2):
        """簡易的な類似度計算"""
        # 実際にはもっと高度な類似度計算を実装
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def publish_article(self, article, site):
        """記事を投稿"""
        try:
            publisher = WordPressPublisher(
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
            
            # サイト設定に基づいて画像処理を決定
            logger.info(f"画像サービス設定: {site.image_service}")
            if site.image_service != 'none':
                # 新しい画像生成システムを使用
                if site.image_service in ['auto', 'gemini_image', 'gpt_image']:
                    try:
                        logger.info("画像生成システムを初期化中...")
                        from services.image_generation import ImageGenerationManager
                        image_manager = ImageGenerationManager()
                        
                        # サイト設定に基づいてプロンプトを調整
                        if image_manager.config.get('image_generation', {}).get('enabled', False):
                            logger.info("画像生成が有効です")
                            # ユーザー選択サービスまたは自動選択
                            user_preference = None if site.image_service == 'auto' else site.image_service
                            logger.info(f"画像生成サービス: {user_preference or 'auto'}")
                            
                            # プロンプト生成時にサイト設定を反映
                            image_manager.prompt_generator.default_style = site.image_style
                            image_manager.prompt_generator.quality = site.image_quality
                            image_manager.prompt_generator.additional_instructions = site.image_instructions
                            image_manager.prompt_generator.tone = site.image_tone
                            image_manager.prompt_generator.avoid_terms = site.image_avoid_terms.split(',')
                            
                            image_path = image_manager.generate_article_image(
                                article_title=article['title'],
                                keywords=article['tags'],
                                genre=site.genre,
                                user_preference=user_preference
                            )
                            
                            if image_path and os.path.exists(image_path):
                                logger.info(f"画像生成成功: {image_path}")
                                # 生成された画像をアップロード
                                featured_media_id = publisher.upload_media_from_file(
                                    file_path=image_path,
                                    alt_text=article['title']
                                )
                                logger.info(f"生成画像をアップロード: {image_path}, ID: {featured_media_id}")
                            else:
                                logger.warning("画像生成に失敗しました")
                        else:
                            logger.warning("画像生成が無効になっています")
                    except Exception as e:
                        logger.error(f"画像生成エラー: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # Unsplashを使用
                if site.image_service == 'unsplash' or (not featured_media_id and site.image_service != 'none'):
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
                # ステータス更新
                article['status'] = '公開済み'
                article['wordpress_url'] = result['link']
                article['wordpress_id'] = result['id']
                article['published_at'] = datetime.now().isoformat()
                self.update_article(article)
                
                # 統計情報を更新
                self.update_automation_stats('published')
                
                return {
                    'success': True,
                    'url': result['link'],
                    'wordpress_id': result['id']
                }
                
        except Exception as e:
            logger.error(f"投稿エラー: {str(e)}")
            # エラー統計を更新
            self.update_automation_stats('error')
            
        return {'success': False, 'error': str(e)}
    
    def get_today_article_count(self, site_id):
        """今日の記事数を取得"""
        try:
            with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            today = datetime.now().date()
            count = 0
            
            for article in data.get('articles', []):
                if article.get('site_id') == site_id:
                    created_date = datetime.fromisoformat(article['created_at']).date()
                    if created_date == today:
                        count += 1
            
            return count
            
        except:
            return 0
    
    def save_article(self, article):
        """記事を保存"""
        try:
            with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {'articles': []}
        
        data['articles'].insert(0, article)
        
        with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 統計情報を更新
        self.update_automation_stats('generated')
    
    def update_article(self, article):
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
        except:
            pass
    
    def update_automation_stats(self, stat_type):
        """自動化統計を更新"""
        try:
            # 既存の統計を読み込み
            try:
                with open('data/automation_stats.json', 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            except:
                stats = {
                    'total_generated': 0,
                    'total_published': 0,
                    'errors': 0,
                    'last_run': None
                }
            
            # 統計を更新
            if stat_type == 'generated':
                stats['total_generated'] += 1
            elif stat_type == 'published':
                stats['total_published'] += 1
            elif stat_type == 'error':
                stats['errors'] += 1
            
            stats['last_run'] = datetime.now().isoformat()
            
            # 保存
            with open('data/automation_stats.json', 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
                
        except Exception as e:
            logger.error(f"統計更新エラー: {str(e)}")
    
    def save_stats(self):
        """統計を保存"""
        with open('data/automation_stats.json', 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
    
    def run_all_sites(self):
        """全サイトの自動実行"""
        if not self.is_operation_hours():
            logger.info("営業時間外です")
            return
        
        sites = self.site_manager.get_all_sites()
        
        for site in sites:
            # サイトごとの自動化設定確認
            site_config = self.config['sites'].get(site.site_id, {})
            if site_config.get('enabled', True):
                self.run_cycle_for_site(site)
                
                # インターバル
                interval = self.config['global']['min_interval_minutes']
                time.sleep(interval * 60)
    
    def is_operation_hours(self):
        """営業時間内かチェック"""
        now = datetime.now()
        start_hour = self.config['global']['operation_hours']['start']
        end_hour = self.config['global']['operation_hours']['end']
        
        return start_hour <= now.hour < end_hour
    
    def start_scheduler(self):
        """スケジューラーを開始"""
        # 定期実行設定
        schedule.every(self.config['global']['min_interval_minutes']).minutes.do(self.run_all_sites)
        
        logger.info("🤖 完全自動運営システム起動")
        logger.info(f"設定: {self.config['global']}")
        
        # 初回実行
        self.run_all_sites()
        
        # スケジューラー実行
        while self.config['enabled']:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにチェック


def main():
    """メイン処理"""
    print("🤖 完全自動記事生成システム")
    print("="*80)
    print("\n【動作モード】")
    print("1. 完全自動モード（推奨）")
    print("2. 今すぐ1サイクル実行")
    print("3. 設定変更")
    print("0. 終了")
    
    choice = input("\n選択: ").strip()
    
    system = FullyAutonomousSystem()
    
    if choice == "1":
        print("\n完全自動モードで起動します。")
        print("停止するには Ctrl+C を押してください。")
        print("-" * 50)
        
        try:
            system.start_scheduler()
        except KeyboardInterrupt:
            print("\n\n自動運営を停止しました。")
            
    elif choice == "2":
        print("\n1サイクル実行します。")
        system.run_all_sites()
        print("\n完了しました。")
        
    elif choice == "3":
        print("\n設定ファイル: config/automation_settings.json")
        print("設定を変更後、再起動してください。")
        
    else:
        print("終了します。")


if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    main()