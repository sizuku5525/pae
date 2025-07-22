#!/usr/bin/env python3
"""
AI自律記事生成システム - 人間の承認付き
AIが提案 → 人間が選択 → AIが実行
"""
import json
import logging
from datetime import datetime
from modules.site_manager import SiteManager
from modules.generator import ArticleGenerator
from modules.wordpress_publisher import WordPressPublisher
from modules.category_selector import CategorySelector
from modules.unsplash_fetcher import UnsplashFetcher
from modules.content_strategist import ContentStrategist
from modules.autonomous_publisher import AutonomousPublisher
import anthropic

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def display_suggestions(suggestions):
    """AI提案を表示"""
    print("\n" + "="*80)
    print("🤖 AIからの記事提案")
    print("="*80)
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n【提案 {i}】")
        print(f"📝 タイトル: {suggestion.get('title', 'N/A')}")
        print(f"🔑 キーワード: {', '.join(suggestion.get('keywords', []))}")
        print(f"🎯 ターゲット: {suggestion.get('target', 'N/A')}")
        print(f"💡 理由: {suggestion.get('reason', 'N/A')}")
        print(f"📈 期待効果: {suggestion.get('expected_impact', 'N/A')}")
        print("-" * 40)


def get_user_approval(suggestions):
    """人間の承認を取得"""
    while True:
        print("\n選択してください:")
        print("1-5: 提案を選択して記事を生成")
        print("R: 再提案を依頼")
        print("M: 手動でテーマを入力")
        print("Q: 終了")
        
        choice = input("\n選択: ").strip().upper()
        
        if choice == 'Q':
            return None, None
        elif choice == 'R':
            return 'regenerate', None
        elif choice == 'M':
            return 'manual', None
        elif choice.isdigit() and 1 <= int(choice) <= len(suggestions):
            selected = suggestions[int(choice) - 1]
            print(f"\n✅ 「{selected['title']}」を選択しました")
            
            # 自動投稿の確認
            auto_publish = input("生成後に自動投稿しますか？ (Y/n): ").strip().lower()
            auto_publish = auto_publish != 'n'
            
            return 'approved', {
                'suggestion': selected,
                'auto_publish': auto_publish
            }
        else:
            print("❌ 無効な選択です")


def manual_input():
    """手動でテーマを入力"""
    print("\n手動テーマ入力")
    print("-" * 40)
    
    title = input("記事タイトル: ").strip()
    if not title:
        return None
    
    keywords = input("キーワード（カンマ区切り）: ").strip()
    keywords = [k.strip() for k in keywords.split(',')] if keywords else []
    
    auto_publish = input("生成後に自動投稿しますか？ (Y/n): ").strip().lower()
    auto_publish = auto_publish != 'n'
    
    return {
        'suggestion': {
            'title': title,
            'keywords': keywords,
            'reason': '手動入力',
            'target': '一般読者',
            'expected_impact': '手動指定のため不明'
        },
        'auto_publish': auto_publish
    }


def main():
    """メイン処理"""
    print("🤖 AI自律記事生成システム")
    print("="*80)
    
    # マネージャー初期化
    site_manager = SiteManager()
    sites = site_manager.get_all_sites()
    
    if not sites:
        print("❌ サイトが登録されていません")
        return
    
    # サイト選択
    print("\n登録サイト:")
    for i, site in enumerate(sites, 1):
        print(f"{i}. {site.name} ({site.url})")
    
    site_index = input("\nサイトを選択 (番号): ").strip()
    try:
        site = sites[int(site_index) - 1]
    except:
        print("❌ 無効な選択です")
        return
    
    print(f"\n選択されたサイト: {site.name}")
    
    # Claude API初期化
    try:
        with open('config/api_keys.json', 'r') as f:
            api_keys = json.load(f)
        claude_api_key = api_keys.get('claude', {}).get('api_key')
        
        if not claude_api_key:
            print("❌ Claude APIキーが設定されていません")
            return
            
        claude_client = anthropic.Anthropic(api_key=claude_api_key)
    except Exception as e:
        print(f"❌ API初期化エラー: {str(e)}")
        return
    
    # コンテンツストラテジスト初期化
    strategist = ContentStrategist(claude_client)
    
    # 過去記事分析
    print("\n📊 過去記事を分析中...")
    past_analysis = strategist.analyze_published_articles(site.site_id)
    print(f"分析完了: {past_analysis['total_articles']}件の記事")
    
    # WordPress分析（オプション）
    wordpress_analysis = None
    if site.wordpress_username and site.wordpress_app_password:
        print("\n🔍 WordPress既存記事を分析中...")
        try:
            publisher = WordPressPublisher(
                site.url,
                site.wordpress_username,
                site.wordpress_app_password
            )
            if publisher.test_connection():
                wordpress_analysis = strategist.analyze_wordpress_content(publisher)
                print(f"分析完了: {wordpress_analysis.get('total_posts', 0)}件の既存記事")
        except:
            print("WordPress分析をスキップ")
    
    # AI提案生成
    print("\n🤔 AIが記事テーマを検討中...")
    suggestions = strategist.generate_content_strategy(
        site.to_dict(),
        past_analysis,
        wordpress_analysis
    )
    
    if not suggestions:
        print("❌ 提案の生成に失敗しました")
        return
    
    # 提案表示と承認取得
    while True:
        display_suggestions(suggestions)
        
        action, params = get_user_approval(suggestions)
        
        if action is None:
            print("\n終了します")
            return
        elif action == 'regenerate':
            print("\n🔄 再提案を生成中...")
            suggestions = strategist.generate_content_strategy(
                site.to_dict(),
                past_analysis,
                wordpress_analysis
            )
            continue
        elif action == 'manual':
            params = manual_input()
            if not params:
                continue
            action = 'approved'
        
        if action == 'approved' and params:
            # 記事生成
            print("\n✍️ 記事を生成中...")
            
            generator = ArticleGenerator()
            
            # site_infoに戦略情報を追加
            site_info = site.to_dict()
            site_info['strategic_intent'] = params['suggestion'].get('reason', '')
            site_info['target_segment'] = params['suggestion'].get('target', '')
            
            try:
                article = generator.generate_article(
                    site_info=site_info,
                    keywords=params['suggestion'].get('keywords', []),
                    length=7000,
                    tone='friendly'
                )
                
                print(f"\n✅ 記事生成完了: {article['title']}")
                print(f"文字数: {len(article['content'])}文字")
                
                # 記事保存
                article['id'] = f"ai_guided_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                article['site_id'] = site.site_id
                article['site_name'] = site.name
                article['status'] = '下書き'
                article['created_at'] = datetime.now().isoformat()
                article['metadata'] = {
                    **article.get('metadata', {}),
                    'ai_guided': True,
                    'strategy': params['suggestion']
                }
                
                # ファイルに保存
                try:
                    with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except:
                    data = {'articles': []}
                
                data['articles'].insert(0, article)
                
                with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 自動投稿
                if params['auto_publish'] and site.wordpress_username and site.wordpress_app_password:
                    print("\n📤 WordPressに投稿中...")
                    
                    # AutonomousPublisherを使用
                    auto_publisher = AutonomousPublisher(
                        site_manager=site_manager,
                        generator=generator,
                        publisher_class=WordPressPublisher,
                        category_selector=CategorySelector(),
                        unsplash_fetcher=UnsplashFetcher(),
                        content_strategist=strategist
                    )
                    
                    result = auto_publisher._publish_article(article, site)
                    
                    if result['success']:
                        print(f"✅ 投稿成功: {result['url']}")
                        # ステータス更新
                        article['status'] = '公開済み'
                        article['wordpress_url'] = result['url']
                        article['published_at'] = datetime.now().isoformat()
                        
                        # 更新を保存
                        for i, a in enumerate(data['articles']):
                            if a['id'] == article['id']:
                                data['articles'][i] = article
                                break
                        
                        with open('data/generated_articles.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    else:
                        print(f"❌ 投稿失敗: {result.get('error', 'Unknown')}")
                
                break
                
            except Exception as e:
                print(f"❌ エラー: {str(e)}")
                continue


if __name__ == "__main__":
    main()