#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
# from dotenv import load_dotenv  # .envファイルは使用しない
from modules.site_manager import SiteManager, Site
from modules.affiliate_manager import AffiliateManager, AffiliateProgram, AffiliateProduct
from modules.generator import ArticleGenerator
from modules.wordpress_publisher import WordPressPublisher
from modules.unsplash_fetcher import UnsplashFetcher
from modules.category_selector import CategorySelector
from modules.article_variation import ArticleVariationGenerator

# ログ設定
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIキーをconfig/api_keys.jsonから読み込む
# .envファイルは使用しない
try:
    with open('config/api_keys.json', 'r') as f:
        api_config = json.load(f)
        # 環境変数に設定（他のモジュールで使用するため）
        if api_config.get('claude', {}).get('api_key'):
            os.environ['CLAUDE_API_KEY'] = api_config['claude']['api_key']
        if api_config.get('venice', {}).get('api_key'):
            os.environ['VENICE_API_KEY'] = api_config['venice']['api_key']
        if api_config.get('unsplash', {}).get('access_key'):
            os.environ['UNSPLASH_ACCESS_KEY'] = api_config['unsplash']['access_key']
            
        # デバッグ用
        claude_key = api_config.get('claude', {}).get('api_key')
        if claude_key:
            logger.info(f"Claude APIキー読み込み成功: {claude_key[:10]}...")
        else:
            logger.warning("Claude APIキーが設定されていません")
except Exception as e:
    logger.error(f"API設定ファイルの読み込みエラー: {str(e)}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
CORS(app)

# マネージャーのインスタンス
site_manager = SiteManager()
affiliate_manager = AffiliateManager()

# 実際の統計データを取得する関数
def get_real_stats():
    # 記事データを読み込む
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            articles = articles_data.get('articles', [])
    except:
        articles = []
    
    # 自動化統計を読み込む
    try:
        with open('data/automation_stats.json', 'r', encoding='utf-8') as f:
            auto_stats = json.load(f)
    except:
        auto_stats = {'total_generated': 0, 'total_published': 0}
    
    # 今日の投稿数を計算
    today = datetime.now().strftime('%Y-%m-%d')
    today_posts = len([a for a in articles if a.get('created_at', '').startswith(today)])
    
    # 今月の投稿数を計算
    this_month = datetime.now().strftime('%Y-%m')
    monthly_articles = len([a for a in articles if a.get('created_at', '').startswith(this_month)])
    
    return {
        'total_sites': len(site_manager.get_all_sites()),
        'active_sites': len([s for s in site_manager.get_all_sites()]),
        'total_articles': len(articles),
        'monthly_articles': monthly_articles,
        'today_posts': today_posts,
        'scheduled_posts': 0,  # 実装予定
        'api_usage': auto_stats.get('total_generated', 0),
        'api_remaining': 'Claude API使用中'
    }

def get_recent_activities():
    activities = []
    
    # 記事データから最近の活動を取得
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            articles = sorted(articles_data.get('articles', []), 
                            key=lambda x: x.get('created_at', ''), 
                            reverse=True)[:5]  # 最新5件
            
        for article in articles:
            created_at = datetime.fromisoformat(article.get('created_at', ''))
            time_diff = datetime.now() - created_at
            
            # 時間差を計算
            if time_diff.days > 0:
                time_ago = f'{time_diff.days}日前'
            elif time_diff.seconds > 3600:
                time_ago = f'{time_diff.seconds // 3600}時間前'
            else:
                time_ago = f'{time_diff.seconds // 60}分前'
            
            # アクティビティタイプを決定
            if article.get('status') == '公開済み':
                title = '記事を投稿しました'
                type_class = 'bg-success'
                icon = 'bi-check-circle'
            else:
                title = '記事を生成しました'
                type_class = 'bg-info'
                icon = 'bi-file-text'
            
            activities.append({
                'title': title,
                'description': f"{article.get('site_name', '')}に「{article.get('title', '')[:20]}...」",
                'time_ago': time_ago,
                'type_class': type_class,
                'icon': icon
            })
    except Exception as e:
        logger.error(f'最近の活動取得エラー: {str(e)}')
    
    # デフォルトの活動を追加（記事がない場合）
    if not activities:
        activities = [
            {
                'title': 'システム起動',
                'description': '自動投稿システムが開始されました',
                'time_ago': '今',
                'type_class': 'bg-primary',
                'icon': 'bi-play-circle'
            }
        ]
    
    return activities[:3]  # 最新3件を返す

def get_site_status():
    sites = site_manager.get_all_sites()
    site_status = []
    
    # 記事データを読み込む
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            articles = articles_data.get('articles', [])
    except:
        articles = []
    
    for site in sites[:3]:
        # サイトごとの記事を取得
        site_articles = [a for a in articles if a.get('site_id') == site.site_id]
        
        # 最後の投稿時間を計算
        if site_articles:
            latest_article = max(site_articles, key=lambda x: x.get('created_at', ''))
            created_at = datetime.fromisoformat(latest_article.get('created_at', ''))
            time_diff = datetime.now() - created_at
            
            if time_diff.days > 0:
                last_post = f'{time_diff.days}日前'
            elif time_diff.seconds > 3600:
                last_post = f'{time_diff.seconds // 3600}時間前'
            else:
                last_post = f'{time_diff.seconds // 60}分前'
                
            # 今日の投稿数で進捗を計算
            today = datetime.now().strftime('%Y-%m-%d')
            today_posts = len([a for a in site_articles if a.get('created_at', '').startswith(today)])
            progress = min(today_posts * 20, 100)  # 1記事20%として計算
        else:
            last_post = '未投稿'
            progress = 0
        
        site_status.append({
            'name': site.name,
            'status': '稼働中' if progress > 0 else '待機中',
            'status_class': 'success' if progress > 0 else 'secondary',
            'progress': progress,
            'progress_class': 'success' if progress >= 60 else 'warning' if progress >= 20 else 'danger',
            'last_post': last_post
        })
    
    return site_status

def get_performance_data():
    """過去7日間のパフォーマンスデータを取得"""
    # 記事データを読み込む
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            articles = articles_data.get('articles', [])
    except:
        articles = []
    
    # 過去7日間の日付リストを作成
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    
    # 日本語の曜日
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    labels = []
    generated_counts = []
    published_counts = []
    
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        # 曜日を取得
        weekday = weekdays[date.weekday()]
        labels.append(f"{date.month}/{date.day}({weekday})")
        
        # その日の記事を数える
        day_articles = [a for a in articles if a.get('created_at', '').startswith(date_str)]
        generated_counts.append(len(day_articles))
        
        # 公開済みの記事を数える
        published = len([a for a in day_articles if a.get('status') == '公開済み'])
        published_counts.append(published)
    
    return {
        'labels': labels,
        'generated': generated_counts,
        'published': published_counts
    }

@app.route('/')
def index():
    """メインダッシュボード"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """ダッシュボード画面"""
    return render_template('dashboard.html',
                         stats=get_real_stats(),
                         recent_activities=get_recent_activities(),
                         site_status=get_site_status(),
                         performance_data=get_performance_data())

@app.route('/api/sites', methods=['GET'])
def get_sites():
    """サイト一覧をJSON形式で取得"""
    sites = site_manager.get_all_sites()
    return jsonify([site.to_dict() for site in sites])

@app.route('/api/sites', methods=['POST'])
def add_site():
    """新しいサイトを追加"""
    data = request.json
    new_site = Site(
        site_id=site_manager.generate_site_id(),
        name=data.get('name', ''),
        url=data.get('url', ''),
        genre=data.get('genre', ''),
        target_audience=data.get('target_audience', ''),
        monetization_policy=data.get('monetization_policy', ''),
        wordpress_username=data.get('wordpress_username', ''),
        wordpress_app_password=data.get('wordpress_app_password', ''),
        site_purpose=data.get('site_purpose', ''),
        content_guidelines=data.get('content_guidelines', ''),
        keywords_focus=data.get('keywords_focus', ''),
        avoid_topics=data.get('avoid_topics', ''),
        genre_details=data.get('genre_details', ''),
        target_details=data.get('target_details', ''),
        ai_model=data.get('ai_model', 'claude'),
        custom_prompt=data.get('custom_prompt', ''),
        cta_link=data.get('cta_link', ''),
        cta_description=data.get('cta_description', ''),
        cta_links=data.get('cta_links', []),
        categories=data.get('categories', []),
        content_tone=data.get('content_tone', ''),
        content_rules=data.get('content_rules', ''),
        image_service=data.get('image_service', 'auto'),
        image_style=data.get('image_style', 'photorealistic'),
        image_tone=data.get('image_tone', ''),
        image_instructions=data.get('image_instructions', ''),
        image_size=data.get('image_size', '1792x1024'),
        image_quality=data.get('image_quality', '8K, ultra detailed, high resolution'),
        image_avoid_terms=data.get('image_avoid_terms', 'low quality, blurry, distorted')
    )
    
    if site_manager.add_site(new_site):
        return jsonify({'success': True, 'site': new_site.to_dict()})
    else:
        return jsonify({'success': False, 'error': 'Failed to add site'}), 400

@app.route('/api/sites/<site_id>', methods=['PUT'])
def update_site(site_id):
    """サイトを更新"""
    data = request.json
    updated_site = Site(
        site_id=site_id,
        name=data.get('name', ''),
        url=data.get('url', ''),
        genre=data.get('genre', ''),
        target_audience=data.get('target_audience', ''),
        monetization_policy=data.get('monetization_policy', ''),
        wordpress_username=data.get('wordpress_username', ''),
        wordpress_app_password=data.get('wordpress_app_password', ''),
        site_purpose=data.get('site_purpose', ''),
        content_guidelines=data.get('content_guidelines', ''),
        keywords_focus=data.get('keywords_focus', ''),
        avoid_topics=data.get('avoid_topics', ''),
        genre_details=data.get('genre_details', ''),
        target_details=data.get('target_details', ''),
        ai_model=data.get('ai_model', 'claude'),
        custom_prompt=data.get('custom_prompt', ''),
        cta_link=data.get('cta_link', ''),
        cta_description=data.get('cta_description', ''),
        cta_links=data.get('cta_links', []),
        categories=data.get('categories', []),
        content_tone=data.get('content_tone', ''),
        content_rules=data.get('content_rules', ''),
        image_service=data.get('image_service', 'auto'),
        image_style=data.get('image_style', 'photorealistic'),
        image_tone=data.get('image_tone', ''),
        image_instructions=data.get('image_instructions', ''),
        image_size=data.get('image_size', '1792x1024'),
        image_quality=data.get('image_quality', '8K, ultra detailed, high resolution'),
        image_avoid_terms=data.get('image_avoid_terms', 'low quality, blurry, distorted')
    )
    
    if site_manager.update_site(site_id, updated_site):
        return jsonify({'success': True, 'site': updated_site.to_dict()})
    else:
        return jsonify({'success': False, 'error': 'Failed to update site'}), 400

@app.route('/api/sites/<site_id>', methods=['DELETE'])
def delete_site(site_id):
    """サイトを削除"""
    if site_manager.delete_site(site_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete site'}), 400

@app.route('/api/generate', methods=['POST'])
def generate_articles():
    """記事生成"""
    logger.info("記事生成API呼び出し開始")
    data = request.json
    logger.info(f"リクエストデータ: {data}")
    
    site_id = data.get('site_id')
    count = int(data.get('count', 1))  # 整数に変換
    auto_publish = data.get('auto_publish', False)  # 自動投稿フラグ
    article_length = int(data.get('length', 5000))  # 文字数設定
    user_keywords = data.get('keywords', '')  # ユーザー指定のキーワード
    
    try:
        # バリデーション
        if not site_id:
            return jsonify({'success': False, 'error': 'サイトIDが指定されていません'}), 400
            
        # countが有効な数値か確認
        if count < 1 or count > 10:
            return jsonify({'success': False, 'error': '記事数は1〜10の範囲で指定してください'}), 400
        
        # サイト情報を取得
        site = site_manager.get_site_by_id(site_id)
        if not site:
            return jsonify({'success': False, 'error': 'サイトが見つかりません'}), 404
        
        # 記事生成器を初期化（サイトのAIモデル設定に応じて選択）
        if site.ai_model == 'venice':
            from modules.venice_generator import VeniceArticleGenerator
            generator = VeniceArticleGenerator()
        else:
            generator = ArticleGenerator()
        variation_generator = ArticleVariationGenerator()
        
        # 生成された記事を保存するファイル
        articles_file = 'data/generated_articles.json'
        
        # 既存の記事を読み込む
        try:
            with open(articles_file, 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
        except:
            articles_data = {'articles': []}
        
        generated_count = 0
        generated_article_ids = []
        
        # 指定された数の記事を生成
        for i in range(count):
            try:
                # アフィリエイト商品をランダムに選択（ある場合）
                all_products = affiliate_manager.get_all_products()
                affiliate_products = all_products[:2] if all_products else None
                
                # バリエーションを生成
                # ユーザー指定のキーワードがある場合はそれを優先
                if user_keywords:
                    base_keywords = [k.strip() for k in user_keywords.split(',') if k.strip()]
                else:
                    base_keywords = site.keywords_focus.split(',') if site.keywords_focus else []
                unique_keywords = variation_generator.get_unique_keywords(base_keywords, i)
                # ユーザーが指定した文字数を使用（バリエーションを加える）
                varied_article_length = variation_generator.get_article_length_variation(article_length, i)
                
                # site_infoにバリエーションプロンプトを追加
                site_info_with_variation = site.to_dict()
                site_info_with_variation['variation_prompt'] = variation_generator.generate_variation_prompt(
                    base_topic=site.genre_details or site.genre,
                    index=i,
                    total_count=count
                )
                
                # 記事を生成（エラー時はより短い長さで再試行）
                try:
                    article = generator.generate_article(
                        site_info=site_info_with_variation,
                        keywords=unique_keywords,
                        length=varied_article_length,
                        tone='friendly',
                        affiliate_products=[p.to_dict() for p in affiliate_products] if affiliate_products else None
                    )
                except Exception as first_error:
                    print(f"{varied_article_length}文字での生成に失敗。より短い文字数で再試行: {str(first_error)}")
                    # より短い長さで再試行
                    # ユーザー指定のキーワードを使用
                    retry_keywords = base_keywords if user_keywords else (site.keywords_focus.split(',') if site.keywords_focus else [])
                    article = generator.generate_article(
                        site_info=site.to_dict(),
                        keywords=retry_keywords,
                        length=min(3000, article_length // 2),  # 半分または3000文字の小さい方
                        tone='friendly',
                        affiliate_products=[p.to_dict() for p in affiliate_products] if affiliate_products else None
                    )
                
                # 記事にIDとサイト情報を追加
                article['id'] = f"article_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
                article['site_id'] = site_id
                article['site_name'] = site.name
                article['status'] = '下書き'
                article['created_at'] = datetime.now().isoformat()
                
                # 記事を保存
                articles_data['articles'].insert(0, article)
                generated_count += 1
                generated_article_ids.append(article['id'])
                
                # 自動投稿が有効な場合
                if auto_publish and site.wordpress_username and site.wordpress_app_password:
                    logger.info(f"自動投稿を開始: {article['title']}")
                    
                    try:
                        # WordPressに投稿
                        publisher = WordPressPublisher(
                            site.url,
                            site.wordpress_username,
                            site.wordpress_app_password
                        )
                        
                        if publisher.test_connection():
                            # カテゴリ選択
                            wp_categories = publisher.get_categories()
                            category_ids = []
                            
                            if wp_categories:
                                selector = CategorySelector()
                                selected_category_id = selector.select_category(
                                    title=article['title'],
                                    content=article['content'],
                                    tags=article['tags'],
                                    available_categories=wp_categories
                                )
                                
                                if selected_category_id:
                                    category_ids.append(selected_category_id)
                                    for cat in wp_categories:
                                        if cat['id'] == selected_category_id:
                                            logger.info(f"カテゴリ選択: {cat['name']}")
                                            break
                            
                            # アイキャッチ画像（サイト設定に基づく）
                            featured_media_id = None
                            
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
                                
                                # Unsplashを使用（フォールバックまたは指定された場合）
                                if site.image_service == 'unsplash' or (not featured_media_id and site.image_service != 'none'):
                                    unsplash = UnsplashFetcher()
                                    if unsplash.is_configured():
                                        photo = unsplash.get_photo_for_article(
                                            title=article['title'],
                                            keywords=article['tags'],
                                            content=article['content'][:500]
                                        )
                                        
                                        if photo:
                                            featured_media_id = publisher.upload_media(
                                                image_url=photo['url'],
                                                alt_text=photo.get('alt_description', article['title'])
                                            )
                                            unsplash.download_photo(photo['id'])
                            
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
                                # ステータスを更新
                                article['status'] = '公開済み'
                                article['wordpress_url'] = result['link']
                                article['wordpress_id'] = result['id']
                                article['published_at'] = datetime.now().isoformat()
                                logger.info(f"自動投稿成功: {result['link']}")
                            else:
                                logger.error("自動投稿失敗")
                        else:
                            logger.error("WordPress接続失敗")
                            
                    except Exception as publish_error:
                        logger.error(f"自動投稿エラー: {str(publish_error)}")
                        # 投稿エラーでも記事生成は成功とする
                
            except Exception as e:
                import traceback
                logger.error(f"記事生成エラー: {str(e)}")
                print(f"記事生成エラー: {str(e)}")
                traceback.print_exc()
                continue
        
        # ファイルに保存
        logger.info(f"記事を保存中... 生成数: {generated_count}")
        with open(articles_file, 'w', encoding='utf-8') as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"記事生成完了: {generated_count}件")
        
        # ファイルが正しく保存されたか確認
        with open(articles_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            logger.info(f"保存された記事数: {len(saved_data.get('articles', []))}")
        
        # 記事が1件も生成されていない場合はエラー
        if generated_count == 0:
            return jsonify({
                'success': False,
                'error': '記事の生成に失敗しました。APIキーとモデル設定を確認してください。',
                'generated_count': 0
            }), 500
        
        # レスポンスを即座に返す（長時間の処理でタイムアウトを防ぐ）
        response_data = {
            'success': True,
            'message': f'{generated_count}件の記事を生成しました',
            'generated_count': generated_count,
            'article_ids': generated_article_ids
        }
        
        logger.info(f"記事生成レスポンス: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"記事生成エラー: {str(e)}\n{error_trace}")
        
        # 部分的に成功している場合も考慮
        return jsonify({
            'success': False, 
            'error': str(e),
            'generated_count': generated_count if 'generated_count' in locals() else 0,
            'partial_success': generated_count > 0 if 'generated_count' in locals() else False
        }), 500

@app.route('/api/articles/recent', methods=['GET'])
def get_recent_articles():
    """最近の記事を取得"""
    try:
        limit = int(request.args.get('limit', 10))
        
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        
        articles = articles_data.get('articles', [])[:limit]
        
        # 記事データを整形
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                'id': article.get('id'),
                'title': article.get('title'),
                'site_name': article.get('site_name'),
                'status': article.get('status', '下書き'),
                'created_at': article.get('created_at'),
                'wordpress_url': article.get('wordpress_url')
            })
        
        return jsonify({'articles': formatted_articles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/publish/<article_id>', methods=['POST'])
def publish_article_to_wordpress(article_id):
    """記事をWordPressに投稿"""
    try:
        # 記事データを取得
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        
        article = None
        article_index = None
        for i, a in enumerate(articles_data.get('articles', [])):
            if a['id'] == article_id:
                article = a
                article_index = i
                break
        
        if not article:
            return jsonify({'success': False, 'error': '記事が見つかりません'}), 404
        
        # サイト情報を取得
        site = site_manager.get_site_by_id(article.get('site_id'))
        if not site:
            return jsonify({'success': False, 'error': 'サイト情報が見つかりません'}), 404
        
        # WordPress認証情報を確認
        if not site.wordpress_username or not site.wordpress_app_password:
            return jsonify({
                'success': False, 
                'error': 'WordPress認証情報が設定されていません。サイト設定を確認してください。'
            }), 400
        
        # WordPressPublisherを初期化
        publisher = WordPressPublisher(
            site.url,
            site.wordpress_username,
            site.wordpress_app_password
        )
        
        # 接続テスト
        if not publisher.test_connection():
            return jsonify({
                'success': False,
                'error': 'WordPressに接続できません。認証情報を確認してください。'
            }), 400
        
        # カテゴリを自動選択
        category_ids = []
        
        # WordPressから利用可能なカテゴリを取得
        wp_categories = publisher.get_categories()
        
        if wp_categories:
            # CategorySelectorを使用して最適なカテゴリを選択
            selector = CategorySelector()
            selected_category_id = selector.select_category(
                title=article.get('title', ''),
                content=article.get('content', ''),
                tags=article.get('tags', []),
                available_categories=wp_categories
            )
            
            if selected_category_id:
                category_ids.append(selected_category_id)
                
                # 選択されたカテゴリ名をログに記録
                for cat in wp_categories:
                    if cat['id'] == selected_category_id:
                        logger.info(f"選択されたカテゴリ: {cat['name']} (ID: {selected_category_id})")
                        break
        
        # カテゴリが選択されなかった場合のフォールバック
        if not category_ids:
            # デフォルトで「ブログ・アフィリエイト副業」カテゴリを使用
            for cat in wp_categories:
                if 'ブログ' in cat.get('name', ''):
                    category_ids.append(cat['id'])
                    logger.info(f"デフォルトカテゴリを使用: {cat['name']}")
                    break
        
        # Unsplashから画像を取得
        featured_media_id = None
        unsplash = UnsplashFetcher()
        
        if unsplash.is_configured():
            # 記事に適した画像を検索
            photo = unsplash.get_photo_for_article(
                title=article.get('title', ''),
                keywords=article.get('tags', []),
                content=article.get('content', '')[:500]  # 最初の500文字
            )
            
            if photo:
                # WordPressにアップロード
                featured_media_id = publisher.upload_media(
                    image_url=photo['url'],
                    alt_text=photo.get('alt_description', article.get('title', ''))
                )
                
                # Unsplashダウンロード通知
                unsplash.download_photo(photo['id'])
                
                logger.info(f"アイキャッチ画像設定: {photo['attribution']}")
        
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
            # 記事のステータスを更新
            articles_data['articles'][article_index]['status'] = '公開済み'
            articles_data['articles'][article_index]['wordpress_url'] = result['link']
            articles_data['articles'][article_index]['wordpress_id'] = result['id']
            articles_data['articles'][article_index]['published_at'] = datetime.now().isoformat()
            
            # ファイルに保存
            with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
                json.dump(articles_data, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True,
                'url': result['link'],
                'wordpress_id': result['id']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'WordPress投稿に失敗しました'
            }), 500
            
    except Exception as e:
        logger.error(f"WordPress投稿エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/sites')
def sites():
    """サイト管理画面"""
    sites_list = site_manager.get_all_sites()
    # ダミーデータを追加
    for site in sites_list:
        site.article_count = 123
        site.last_update = '2024年1月1日'
        site.health = 85
    return render_template('sites.html', sites=sites_list)

@app.route('/generate')
def generate():
    """記事生成画面"""
    sites_list = site_manager.get_all_sites()
    
    # 生成された記事を読み込む
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            generated_articles = []
            
            for article in articles_data.get('articles', [])[:50]:  # 最新50件
                # 表示用にフォーマット
                created_at = datetime.fromisoformat(article['created_at'])
                status_map = {
                    '下書き': 'secondary',
                    '公開済み': 'success',
                    'エラー': 'danger'
                }
                
                generated_articles.append({
                    'id': article['id'],
                    'created_at': created_at.strftime('%Y/%m/%d %H:%M'),
                    'site_name': article.get('site_name', 'Unknown'),
                    'title': article.get('title', 'Untitled'),
                    'status': article.get('status', '下書き'),
                    'status_class': status_map.get(article.get('status', '下書き'), 'secondary'),
                    'content': article.get('content', ''),
                    'tags': article.get('tags', [])
                })
    except:
        generated_articles = []
    
    return render_template('generate.html', 
                         sites=sites_list,
                         generated_articles=generated_articles)

@app.route('/settings')
def settings():
    """設定画面"""
    return render_template('settings.html')

@app.route('/reports')
def reports():
    """レポート画面"""
    # 実際のデータを集計
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            articles = articles_data.get('articles', [])
    except:
        articles = []
    
    # 統計データを集計
    total_articles = len(articles)
    published_articles = len([a for a in articles if a.get('status') == '公開済み'])
    draft_articles = len([a for a in articles if a.get('status') == '下書き'])
    success_rate = (published_articles / total_articles * 100) if total_articles > 0 else 0
    
    # 平均文字数
    total_chars = sum(len(a.get('content', '')) for a in articles)
    avg_chars = total_chars // total_articles if total_articles > 0 else 0
    
    # 月別集計（直近1年）
    monthly_data = {}
    one_year_ago = datetime.now() - timedelta(days=365)
    
    for article in articles:
        created_date = datetime.fromisoformat(article.get('created_at', ''))
        # 1年以内の記事のみ集計
        if created_date >= one_year_ago:
            month_key = created_date.strftime('%Y/%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = 0
            monthly_data[month_key] += 1
    
    # サイト別集計
    site_data = {}
    for article in articles:
        site_name = article.get('site_name', 'Unknown')
        if site_name not in site_data:
            site_data[site_name] = 0
        site_data[site_name] += 1
    
    # 時間帯別集計
    hourly_data = [0] * 6  # 0-4, 4-8, 8-12, 12-16, 16-20, 20-24
    for article in articles:
        created_date = datetime.fromisoformat(article.get('created_at', ''))
        hour = created_date.hour
        hourly_data[hour // 4] += 1
    
    # API使用量（推定）
    api_tokens = total_articles * 3000  # 1記事あたり約3000トークン
    api_cost = api_tokens * 0.003  # $0.003 per 1K tokens
    api_cost_jpy = api_cost * 140  # 1ドル140円換算
    
    return render_template('reports.html',
                         total_articles=total_articles,
                         published_articles=published_articles,
                         draft_articles=draft_articles,
                         success_rate=success_rate,
                         avg_chars=avg_chars,
                         api_cost_jpy=int(api_cost_jpy),
                         monthly_data=monthly_data,
                         site_data=site_data,
                         hourly_data=hourly_data)

@app.route('/automation')
def automation():
    """自動化設定画面"""
    return render_template('automation.html')

@app.route('/image-settings')
def image_settings():
    """画像生成設定画面 - 設定画面にリダイレクト"""
    return redirect(url_for('settings') + '#api')

@app.route('/emergency-check')
def emergency_check():
    """緊急確認画面"""
    return send_file('emergency_check.html')

@app.route('/debug-status')
def debug_status():
    """ステータス表示デバッグ画面"""
    return send_file('debug_status_display.html')

@app.route('/image-settings-simple')
def image_settings_simple():
    """画像生成設定画面（シンプル版）"""
    return render_template('image_settings_simple.html')

@app.route('/image-api-keys')
def image_api_keys():
    """画像生成APIキー設定 - 設定画面にリダイレクト"""
    return redirect(url_for('settings') + '#api')

@app.route('/affiliates')
def affiliates():
    """アフィリエイト管理画面"""
    return render_template('affiliates.html')

# アフィリエイトAPI
@app.route('/api/affiliate/programs', methods=['GET'])
def get_affiliate_programs():
    """アフィリエイトプログラム一覧を取得"""
    programs = affiliate_manager.get_all_programs()
    result = []
    for program in programs:
        program_dict = program.to_dict()
        # 関連する商品数を追加
        program_dict['product_count'] = len(affiliate_manager.get_products_by_program(program.program_id))
        result.append(program_dict)
    return jsonify(result)

@app.route('/api/affiliate/programs', methods=['POST'])
def add_affiliate_program():
    """アフィリエイトプログラムを追加"""
    data = request.json
    program = AffiliateProgram(
        program_id=affiliate_manager.generate_id(),
        name=data.get('name', ''),
        description=data.get('description', ''),
        commission_rate=data.get('commission_rate', ''),
        cookie_duration=data.get('cookie_duration', ''),
        payment_terms=data.get('payment_terms', ''),
        notes=data.get('notes', '')
    )
    
    if affiliate_manager.add_program(program):
        return jsonify({'success': True, 'program': program.to_dict()})
    else:
        return jsonify({'success': False, 'error': 'Failed to add program'}), 400

@app.route('/api/affiliate/programs/<program_id>', methods=['DELETE'])
def delete_affiliate_program(program_id):
    """アフィリエイトプログラムを削除"""
    if affiliate_manager.delete_program(program_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete program'}), 400

@app.route('/api/affiliate/products', methods=['GET'])
def get_affiliate_products():
    """アフィリエイト商品一覧を取得"""
    products = affiliate_manager.get_all_products()
    result = []
    for product in products:
        product_dict = product.to_dict()
        # プログラム名を追加
        program = affiliate_manager.get_program_by_id(product.program_id)
        product_dict['program_name'] = program.name if program else 'Unknown'
        result.append(product_dict)
    return jsonify(result)

@app.route('/api/affiliate/products', methods=['POST'])
def add_affiliate_product():
    """アフィリエイト商品を追加"""
    data = request.json
    product = AffiliateProduct(
        product_id=affiliate_manager.generate_id(),
        program_id=data.get('program_id', ''),
        name=data.get('name', ''),
        description=data.get('description', ''),
        target_audience=data.get('target_audience', ''),
        selling_points=data.get('selling_points', ''),
        price_range=data.get('price_range', ''),
        commission_details=data.get('commission_details', ''),
        link_url=data.get('link_url', ''),
        promotion_guidelines=data.get('promotion_guidelines', ''),
        avoid_expressions=data.get('avoid_expressions', ''),
        success_examples=data.get('success_examples', ''),
        notes=data.get('notes', '')
    )
    
    if affiliate_manager.add_product(product):
        return jsonify({'success': True, 'product': product.to_dict()})
    else:
        return jsonify({'success': False, 'error': 'Failed to add product'}), 400

@app.route('/api/affiliate/products/<product_id>', methods=['DELETE'])
def delete_affiliate_product(product_id):
    """アフィリエイト商品を削除"""
    if affiliate_manager.delete_product(product_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete product'}), 400

@app.route('/api/wordpress/categories', methods=['POST'])
def get_wordpress_categories():
    """WordPressカテゴリを取得"""
    try:
        data = request.json
        site_url = data.get('site_url')
        username = data.get('username')
        app_password = data.get('app_password')
        
        if not all([site_url, username, app_password]):
            return jsonify({'error': '必要な情報が不足しています'}), 400
        
        # WordPressPublisherを使用
        publisher = WordPressPublisher(site_url, username, app_password)
        
        # 接続テスト
        if not publisher.test_connection():
            return jsonify({'error': 'WordPress接続に失敗しました'}), 400
        
        # カテゴリを取得
        categories = publisher.get_categories()
        
        return jsonify(categories)
        
    except Exception as e:
        logger.error(f"カテゴリ取得エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API設定の読み込み・保存
@app.route('/api/settings/api', methods=['GET'])
def get_api_settings():
    """API設定を取得"""
    try:
        with open('config/api_keys.json', 'r') as f:
            data = json.load(f)
        # 実際の値をそのまま返す（セキュリティリスクはユーザーが了承済み）
        return jsonify(data)
    except:
        return jsonify({})

@app.route('/api/settings/api', methods=['POST'])
def save_api_settings():
    """API設定を保存"""
    data = request.json
    
    # 既存の設定を読み込む
    try:
        with open('config/api_keys.json', 'r') as f:
            existing = json.load(f)
    except:
        existing = {}
    
    # 新しい設定をマージ（空でない値のみ更新）
    for service in data:
        if service not in existing:
            existing[service] = {}
        for key, value in data[service].items():
            if value:  # 空でない値のみ更新
                existing[service][key] = value
    
    # 保存
    with open('config/api_keys.json', 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    # 環境変数も更新（他のモジュールで使用するため）
    if data.get('claude', {}).get('api_key'):
        os.environ['CLAUDE_API_KEY'] = data['claude']['api_key']
    if data.get('venice', {}).get('api_key'):
        os.environ['VENICE_API_KEY'] = data['venice']['api_key']
    if data.get('unsplash', {}).get('access_key'):
        os.environ['UNSPLASH_ACCESS_KEY'] = data['unsplash']['access_key']
    
    # .envファイルは使用しないため、更新処理を削除
    
    return jsonify({'success': True})

# 自動化関連のAPIエンドポイント
@app.route('/api/automation/settings', methods=['GET'])
def get_automation_settings():
    """自動化設定を取得"""
    try:
        with open('config/automation_settings.json', 'r') as f:
            settings = json.load(f)
        
        # 記事文字数の設定がない場合はデフォルト値を設定
        if 'article_length' not in settings:
            settings['article_length'] = 7000
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/automation/settings', methods=['POST'])
def save_automation_settings():
    """自動化設定を保存"""
    try:
        data = request.json
        
        # 既存の設定を読み込む
        with open('config/automation_settings.json', 'r') as f:
            settings = json.load(f)
        
        # 記事文字数の更新
        if 'article_length' in data:
            settings['article_length'] = data['article_length']
        
        # 設定を更新 - 深いマージを行う
        if 'global' in data:
            # 各項目を個別に更新
            if 'max_articles_per_day' in data['global']:
                settings['global']['max_articles_per_day'] = data['global']['max_articles_per_day']
            if 'min_interval_minutes' in data['global']:
                settings['global']['min_interval_minutes'] = data['global']['min_interval_minutes']
            if 'auto_publish' in data['global']:
                settings['global']['auto_publish'] = data['global']['auto_publish']
            
            # operation_hours
            if 'operation_hours' in data['global']:
                settings['global']['operation_hours'].update(data['global']['operation_hours'])
            
            # smart_scheduling
            if 'smart_scheduling' in data['global']:
                settings['global']['smart_scheduling'].update(data['global']['smart_scheduling'])
            
            # safety
            if 'safety' in data['global']:
                settings['global']['safety'].update(data['global']['safety'])
        
        # fully_autonomous.pyのlength値も更新
        if 'article_length' in data:
            # fully_autonomous.pyのlength値を更新
            import re
            with open('fully_autonomous.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            pattern = r'(length=)\d+(,)'
            replacement = f'\\g<1>{data["article_length"]}\\g<2>'
            new_content = re.sub(pattern, replacement, content)
            
            with open('fully_autonomous.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        # 設定ファイルを保存
        with open('config/automation_settings.json', 'w') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        # 保存後、読み込み直して確認（デバッグ用）
        logger.info(f"設定を保存しました: max_articles_per_day = {settings['global']['max_articles_per_day']}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"設定保存エラー: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/automation/status', methods=['GET'])
def get_automation_status():
    """自動化の状態を取得"""
    try:
        # PIDファイルの存在確認
        pid_file = 'autonomous.pid'
        running = False
        
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # プロセスの存在確認
            try:
                os.kill(pid, 0)
                running = True
            except OSError:
                running = False
        
        # 統計情報を読み込む
        stats = {}
        if os.path.exists('data/automation_stats.json'):
            with open('data/automation_stats.json', 'r') as f:
                stats = json.load(f)
        
        # 今日の記事数を計算
        today_count = 0
        if os.path.exists('data/generated_articles.json'):
            with open('data/generated_articles.json', 'r') as f:
                articles = json.load(f).get('articles', [])
            
            today = datetime.now().date()
            today_count = sum(1 for a in articles 
                            if datetime.fromisoformat(a.get('created_at', '')).date() == today)
        
        # 設定から最大記事数を取得
        max_articles = 10
        min_interval = 120
        if os.path.exists('config/automation_settings.json'):
            with open('config/automation_settings.json', 'r') as f:
                settings = json.load(f)
                max_articles = settings.get('global', {}).get('max_articles_per_day', 10)
                min_interval = settings.get('global', {}).get('min_interval_minutes', 120)
        
        # 次回実行時刻を計算
        next_run = None
        if running:
            try:
                # 最後の実行時刻がある場合はそれを使用
                if stats.get('last_run'):
                    last_run = datetime.fromisoformat(stats['last_run'])
                    next_run_time = last_run + timedelta(minutes=min_interval)
                else:
                    # 初回起動時は、現在時刻から次回実行時刻を計算
                    # fully_autonomous.pyはすぐに実行を開始するため、現在時刻+インターバル
                    next_run_time = datetime.now() + timedelta(minutes=min_interval)
                # 営業時間内かチェック
                operation_hours = settings.get('global', {}).get('operation_hours', {'start': 6, 'end': 23})
                start_hour = operation_hours['start']
                end_hour = operation_hours['end']
                
                # 終了時刻が開始時刻より小さい場合（例：22:00-2:00）は翌日をまたぐ
                if end_hour < start_hour:
                    # 現在時刻が営業時間内かチェック
                    if next_run_time.hour >= start_hour or next_run_time.hour < end_hour:
                        # 営業時間内なのでそのまま
                        pass
                    else:
                        # 営業時間外なので次の開始時刻に設定
                        if next_run_time.hour >= end_hour and next_run_time.hour < start_hour:
                            next_run_time = next_run_time.replace(hour=start_hour, minute=0, second=0)
                else:
                    # 通常の営業時間（例：1:00-23:00）
                    # 営業時間内かチェック：start_hour <= hour < end_hour
                    if next_run_time.hour < start_hour or next_run_time.hour >= end_hour:
                        # 営業時間外なので次の開始時刻に設定
                        if next_run_time.hour >= end_hour:
                            # 同日の終了時刻を過ぎている場合は翌日の開始時刻
                            next_day = next_run_time.date() + timedelta(days=1)
                            next_run_time = datetime.combine(next_day, datetime.min.time()).replace(hour=start_hour)
                        else:
                            # 開始時刻前の場合は同日の開始時刻
                            next_run_time = next_run_time.replace(hour=start_hour, minute=0, second=0)
                
                next_run = next_run_time.strftime('%H:%M')
            except Exception as e:
                logger.error(f"次回実行時刻計算エラー: {str(e)}")
                pass
        
        return jsonify({
            'success': True,
            'running': running,
            'today_count': today_count,
            'max_articles': max_articles,
            'stats': stats,
            'next_run': next_run
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/automation/start', methods=['POST'])
def start_automation():
    """自動化を開始"""
    try:
        import subprocess
        result = subprocess.run(['./start_autonomous.sh'], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': '自動化を開始しました'})
        else:
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/performance', methods=['GET'])
def get_dashboard_performance():
    """ダッシュボード用パフォーマンスデータを取得"""
    try:
        performance_data = get_performance_data()
        return jsonify({
            'success': True,
            'data': performance_data
        })
    except Exception as e:
        logger.error(f'パフォーマンスデータ取得エラー: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# import os

# @app.route('/api/automation/start', methods=['POST'])
# def start_automation():
#     """自動化を開始"""
#     try:
#         import subprocess
#         if os.name == 'nt':  # Windows
#             result = subprocess.run(['start_autonomous.bat'], capture_output=True, text=True)
#         else:  # Linux/Mac
#             result = subprocess.run(['./start_autonomous.sh'], capture_output=True, text=True)
        
#         if result.returncode == 0:
#             return jsonify({'success': True, 'message': '自動化を開始しました', 'output': result.stdout})
#         else:
#             return jsonify({'success': False, 'error': result.stderr}), 500
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/api/automation/stop', methods=['POST'])
def stop_automation():
    """自動化を停止"""
    try:
        import subprocess
        result = subprocess.run(['./stop_autonomous.sh'], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': '自動化を停止しました'})
        else:
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# 画像生成関連のAPIエンドポイント
@app.route('/api/image-generation/settings', methods=['GET'])
def get_image_generation_settings():
    """画像生成設定を取得"""
    try:
        # image_apis.jsonを読み込む
        with open('config/image_apis.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # ディープコピーを作成して元のデータを保護
        import copy
        settings = copy.deepcopy(config.get('image_generation', {}))
        
        # APIキーをマスク表示用に処理
        if 'gemini_image' in settings and settings['gemini_image'].get('api_key'):
            key = settings['gemini_image']['api_key']
            settings['gemini_image']['api_key_masked'] = key[:10] + '...' if len(key) > 10 else key
            del settings['gemini_image']['api_key']  # セキュリティのため実際のキーは削除
        
        if 'gpt_image' in settings and settings['gpt_image'].get('api_key'):
            key = settings['gpt_image']['api_key']
            settings['gpt_image']['api_key_masked'] = key[:10] + '...' if len(key) > 10 else key
            del settings['gpt_image']['api_key']  # セキュリティのため実際のキーは削除
        
        if 'unsplash' in settings and settings['unsplash'].get('access_key'):
            key = settings['unsplash']['access_key']
            settings['unsplash']['access_key_masked'] = key[:10] + '...' if len(key) > 10 else key
            del settings['unsplash']['access_key']  # セキュリティのため実際のキーは削除
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-generation/settings/raw', methods=['GET'])
def get_image_generation_settings_raw():
    """画像生成設定を取得（実際の値を返す）"""
    try:
        # image_apis.jsonを読み込む
        with open('config/image_apis.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 実際の値をそのまま返す（セキュリティリスクはユーザーが了承済み）
        settings = config.get('image_generation', {})
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-generation/api-keys', methods=['POST'])
def save_image_generation_api_keys():
    """画像生成APIキーを保存"""
    try:
        data = request.json
        logger.info(f"受信したAPIキーデータ: gemini={data.get('gemini_api_key', '')[:20] if data.get('gemini_api_key') else 'なし'}, gpt={data.get('gpt_api_key', '')[:20] if data.get('gpt_api_key') else 'なし'}")
        
        # 既存の設定を読み込む
        with open('config/image_apis.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # APIキーを更新（空文字列の場合は削除）
        if 'gemini_api_key' in data:
            if data['gemini_api_key']:
                if 'gemini_image' not in config['image_generation']:
                    config['image_generation']['gemini_image'] = {}
                config['image_generation']['gemini_image']['api_key'] = data['gemini_api_key']
                logger.info(f"Gemini APIキーを更新: {data['gemini_api_key'][:20]}...")
            else:
                # 空文字列の場合は削除
                if 'gemini_image' in config['image_generation'] and 'api_key' in config['image_generation']['gemini_image']:
                    del config['image_generation']['gemini_image']['api_key']
                    logger.info("Gemini APIキーを削除")
        
        # gpt_api_keyパラメータを処理（settings.htmlから送信される）
        if 'gpt_api_key' in data:
            if data['gpt_api_key']:
                if 'gpt_image' not in config['image_generation']:
                    config['image_generation']['gpt_image'] = {}
                config['image_generation']['gpt_image']['api_key'] = data['gpt_api_key']
                logger.info(f"OpenAI APIキーを更新: {data['gpt_api_key'][:20]}...")
            else:
                # 空文字列の場合は削除
                if 'gpt_image' in config['image_generation'] and 'api_key' in config['image_generation']['gpt_image']:
                    del config['image_generation']['gpt_image']['api_key']
                    logger.info("OpenAI APIキーを削除")
        
        if 'unsplash_access_key' in data:
            if data['unsplash_access_key']:
                if 'unsplash' not in config['image_generation']:
                    config['image_generation']['unsplash'] = {}
                config['image_generation']['unsplash']['access_key'] = data['unsplash_access_key']
                logger.info(f"Unsplash アクセスキーを更新: {data['unsplash_access_key'][:20]}...")
            else:
                # 空文字列の場合は削除
                if 'unsplash' in config['image_generation'] and 'access_key' in config['image_generation']['unsplash']:
                    del config['image_generation']['unsplash']['access_key']
                    logger.info("Unsplash アクセスキーを削除")
        
        # 保存
        with open('config/image_apis.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # .envファイルも更新
        if data.get('gemini_api_key'):
            os.environ['GOOGLE_GENAI_API_KEY'] = data['gemini_api_key']
        if data.get('openai_api_key'):
            os.environ['OPENAI_API_KEY_IMAGES'] = data['openai_api_key']
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-generation/settings', methods=['POST'])
def save_image_generation_settings():
    """画像生成設定を保存"""
    try:
        data = request.json
        
        # 既存の設定を読み込む
        with open('config/image_apis.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 設定を更新（既存の設定を保持しながら更新）
        if 'image_generation' not in config:
            config['image_generation'] = {}
        
        # 個別に更新（既存の値を保持）
        if 'enabled' in data:
            config['image_generation']['enabled'] = data['enabled']
        if 'auto_selection_mode' in data:
            config['image_generation']['auto_selection_mode'] = data['auto_selection_mode']
        if 'primary_service' in data:
            config['image_generation']['primary_service'] = data['primary_service']
        if 'monthly_budget' in data:
            config['image_generation']['monthly_budget'] = data['monthly_budget']
        
        # 自動選択ルールを更新
        if 'auto_selection_rules' in data:
            config['image_generation']['auto_selection_rules'] = data['auto_selection_rules']
        
        # 保存
        with open('config/image_apis.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-generation/prompt-settings', methods=['POST'])
def save_prompt_settings():
    """プロンプト設定を保存"""
    try:
        data = request.json
        
        # 既存の設定を読み込む
        with open('config/image_apis.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # プロンプト設定を更新（既存の設定を保持しながら更新）
        if 'prompt_settings' in data:
            if 'image_generation' not in config:
                config['image_generation'] = {}
            if 'prompt_settings' not in config['image_generation']:
                config['image_generation']['prompt_settings'] = {}
            
            # 既存の設定をマージ
            for key, value in data['prompt_settings'].items():
                config['image_generation']['prompt_settings'][key] = value
        
        # 保存
        with open('config/image_apis.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-generation/statistics', methods=['GET'])
def get_image_generation_statistics():
    """画像生成統計を取得"""
    try:
        # ユーザー選択履歴を読み込む
        stats = {
            'monthly_count': 0,
            'budget_usage': 0,
            'service_usage': {
                'gemini_image': 0,
                'gpt_image': 0,
                'unsplash': 0
            }
        }
        
        # user_image_preferences.jsonから統計を計算
        if os.path.exists('data/user_image_preferences.json'):
            with open('data/user_image_preferences.json', 'r', encoding='utf-8') as f:
                prefs = json.load(f)
            
            # 今月の生成数を計算
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            monthly_selections = [s for s in prefs.get('selections', []) 
                                if s['timestamp'].startswith(current_month)]
            stats['monthly_count'] = len(monthly_selections)
            
            # サービス別使用率を計算
            total = len(prefs.get('selections', []))
            if total > 0:
                for service in ['gemini_image', 'gpt_image', 'unsplash']:
                    count = sum(1 for s in prefs['selections'] if s['service'] == service)
                    stats['service_usage'][service] = round((count / total) * 100, 1)
        
        return jsonify({'success': True, **stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/articles/<article_id>', methods=['GET'])
def get_article(article_id):
    """記事詳細を取得"""
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            
        for article in articles_data.get('articles', []):
            if article['id'] == article_id:
                return jsonify(article)
        
        return jsonify({'error': '記事が見つかりません'}), 404
    except:
        return jsonify({'error': 'エラーが発生しました'}), 500

@app.route('/api/articles', methods=['GET'])
def get_all_articles():
    """全記事を取得"""
    try:
        with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        return jsonify(articles_data.get('articles', []))
    except:
        return jsonify([]), 200

@app.route('/api/wordpress/test-connection', methods=['GET'])
def test_wordpress_connection():
    """WordPress接続テスト"""
    try:
        site_id = request.args.get('site_id')
        
        # site_idが指定されていない場合は最初のサイトを使用
        if not site_id:
            sites = site_manager.get_all_sites()
            if sites:
                site = sites[0]
            else:
                return jsonify({'success': False, 'error': 'サイトが登録されていません'}), 404
        else:
            site = site_manager.get_site(site_id)
            if not site:
                return jsonify({'success': False, 'error': 'サイトが見つかりません'}), 404
            
        # WordPress設定を確認
        if not site.wordpress_username or not site.wordpress_app_password:
            return jsonify({
                'success': False,
                'connected': False,
                'error': 'WordPress認証情報が設定されていません'
            })
            
        # 詳細なテストを実行
        import requests
        from requests.auth import HTTPBasicAuth
        
        result = {
            'success': True,
            'api_available': False,
            'auth_success': False,
            'error_details': None
        }
        
        # REST APIの可用性を確認
        try:
            response = requests.get(f"{site.url.rstrip('/')}/wp-json", timeout=10)
            result['api_available'] = response.status_code == 200
        except Exception as e:
            result['error_details'] = f"REST API接続エラー: {str(e)}"
            
        # 認証テスト
        if result['api_available']:
            try:
                auth = HTTPBasicAuth(site.wordpress_username, site.wordpress_app_password)
                response = requests.get(
                    f"{site.url.rstrip('/')}/wp-json/wp/v2/users/me",
                    auth=auth,
                    timeout=10
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    result['auth_success'] = True
                    result['user_name'] = user_data.get('name', 'Unknown')
                    result['capabilities'] = list(user_data.get('capabilities', {}).keys())
                else:
                    result['error_details'] = f"認証エラー ({response.status_code}): "
                    try:
                        error_data = response.json()
                        result['error_details'] += error_data.get('message', '不明なエラー')
                    except:
                        result['error_details'] += response.text[:200]
                        
            except Exception as e:
                result['error_details'] = f"認証テストエラー: {str(e)}"
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wordpress/update-password', methods=['POST'])
def update_wordpress_password():
    """WordPressパスワードを更新"""
    try:
        data = request.json
        password = data.get('password')
        site_id = data.get('site_id')
        
        if not password:
            return jsonify({'success': False, 'error': 'パスワードが指定されていません'}), 400
        
        # site_idが指定されていない場合は最初のサイトを使用
        if not site_id:
            sites = site_manager.get_all_sites()
            if sites:
                site = sites[0]
                site_id = site.site_id
            else:
                return jsonify({'success': False, 'error': 'サイトが登録されていません'}), 404
        else:
            site = site_manager.get_site(site_id)
            if not site:
                return jsonify({'success': False, 'error': 'サイトが見つかりません'}), 404
        
        # パスワードを更新
        site.wordpress_app_password = password
        site_manager.update_site(site_id, site)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wordpress-settings')
def wordpress_settings():
    """WordPress設定画面"""
    sites = site_manager.get_all_sites()
    if sites:
        site = sites[0]
        return render_template('wordpress_settings.html',
                             site_url=site.url,
                             username=site.wordpress_username,
                             password_masked=f"{site.wordpress_app_password[:4]}...{site.wordpress_app_password[-4:]}" if site.wordpress_app_password else "未設定")
    else:
        return render_template('wordpress_settings.html',
                             site_url="未設定",
                             username="未設定",
                             password_masked="未設定")

@app.route('/api/system/reset', methods=['POST'])
def reset_system():
    """システムを初期化"""
    try:
        import shutil
        
        # 1. 記事データを初期化
        with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
            json.dump({'articles': []}, f, ensure_ascii=False, indent=2)
        
        # 2. 自動化統計を初期化
        with open('data/automation_stats.json', 'w', encoding='utf-8') as f:
            json.dump({
                'total_generated': 0,
                'total_published': 0,
                'errors': 0,
                'last_run': None
            }, f, ensure_ascii=False, indent=2)
        
        # 3. ユーザー設定を初期化
        if os.path.exists('data/user_image_preferences.json'):
            with open('data/user_image_preferences.json', 'w', encoding='utf-8') as f:
                json.dump({'selections': []}, f, ensure_ascii=False, indent=2)
        
        # 4. サイト設定を初期化
        with open('config/sites.json', 'w', encoding='utf-8') as f:
            json.dump({'sites': []}, f, ensure_ascii=False, indent=2)
        
        # 5. アフィリエイト設定を初期化
        if os.path.exists('data/affiliate_programs.json'):
            with open('data/affiliate_programs.json', 'w', encoding='utf-8') as f:
                json.dump({'programs': []}, f, ensure_ascii=False, indent=2)
        
        if os.path.exists('data/affiliate_products.json'):
            with open('data/affiliate_products.json', 'w', encoding='utf-8') as f:
                json.dump({'products': []}, f, ensure_ascii=False, indent=2)
        
        if os.path.exists('config/affiliates.json'):
            with open('config/affiliates.json', 'w', encoding='utf-8') as f:
                json.dump({'affiliates': []}, f, ensure_ascii=False, indent=2)
        
        # 6. APIキー設定を初期化
        with open('config/api_keys.json', 'w', encoding='utf-8') as f:
            json.dump({
                'claude': {
                    'api_key': '',
                    'model': 'claude-sonnet-4-20250514'
                },
                'venice': {
                    'api_key': ''
                },
                'unsplash': {
                    'access_key': ''
                }
            }, f, ensure_ascii=False, indent=2)
        
        # 7. 画像生成API設定を初期化
        with open('config/image_apis.json', 'w', encoding='utf-8') as f:
            json.dump({
                'image_generation': {
                    'enabled': True,
                    'auto_selection_mode': 'rotate',
                    'primary_service': 'gemini_image',
                    'monthly_budget': 1000,
                    'auto_selection_rules': {
                        'use_gemini_first': True,
                        'fallback_to_gpt': True,
                        'fallback_to_unsplash': True
                    },
                    'gemini_image': {
                        'enabled': True,
                        'model': 'gemini-2.0-flash-exp',
                        'safety_settings': 'medium'
                    },
                    'gpt_image': {
                        'enabled': True,
                        'model': 'dall-e-3',
                        'quality': 'standard',
                        'size': '1792x1024'
                    },
                    'unsplash': {
                        'enabled': True
                    },
                    'prompt_settings': {
                        'style': 'photorealistic',
                        'quality': '8K, ultra detailed, high resolution',
                        'avoid_terms': 'low quality, blurry, distorted',
                        'tone': '',
                        'additional_instructions': ''
                    }
                }
            }, f, ensure_ascii=False, indent=2)
        
        # 8. 自動化設定は保持（デフォルト設定のため）
        
        # 9. ログファイルをクリア
        log_files = ['logs/autonomous.log', 'logs/autonomous_output.log']
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write('')  # 空ファイルにする
        
        # 10. 生成された画像を削除
        image_dirs = ['static/generated_images/gpt', 'static/generated_images/gemini']
        for image_dir in image_dirs:
            if os.path.exists(image_dir):
                for file in os.listdir(image_dir):
                    file_path = os.path.join(image_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        
        # 11. PIDファイルを削除（自動化が実行中の場合）
        if os.path.exists('autonomous.pid'):
            os.remove('autonomous.pid')
        
        logger.info("システムが初期化されました")
        
        return jsonify({'success': True, 'message': 'システムが正常に初期化されました'})
        
    except Exception as e:
        logger.error(f"システム初期化エラー: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 開発サーバーのタイムアウトを延長
    import werkzeug.serving
    werkzeug.serving.WSGIRequestHandler.timeout = 300  # 5分
    
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
