"""
WordPressスクレイピングモジュール
WordPress REST APIを使用して既存記事を取得・分析
"""
import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import logging
from collections import Counter

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WordPressScraper:
    """WordPress記事スクレイピングクラス"""
    
    def __init__(self, site_url: str, username: Optional[str] = None, 
                 app_password: Optional[str] = None):
        """
        初期化
        
        Args:
            site_url: WordPressサイトのURL
            username: WordPress管理者ユーザー名
            app_password: アプリケーションパスワード
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = None
        
        if username and app_password:
            self.auth = (username, app_password)
        
        # APIエンドポイント
        self.endpoints = {
            'posts': f"{self.api_base}/posts",
            'categories': f"{self.api_base}/categories",
            'tags': f"{self.api_base}/tags",
            'media': f"{self.api_base}/media",
            'users': f"{self.api_base}/users"
        }
    
    def get_recent_posts(self, count: int = 100, days: int = 90) -> List[Dict]:
        """
        最近の投稿を取得
        
        Args:
            count: 取得する記事数
            days: 何日前までの記事を取得するか
        
        Returns:
            記事リスト
        """
        try:
            # 日付フィルター
            after_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            params = {
                'per_page': min(count, 100),  # 最大100件/ページ
                'after': after_date,
                'orderby': 'date',
                'order': 'desc',
                '_embed': True  # カテゴリ、タグ、著者情報を含める
            }
            
            posts = []
            page = 1
            
            while len(posts) < count:
                params['page'] = page
                response = requests.get(self.endpoints['posts'], 
                                      params=params, 
                                      auth=self.auth)
                
                if response.status_code != 200:
                    logger.error(f"記事取得エラー: {response.status_code}")
                    break
                
                page_posts = response.json()
                if not page_posts:
                    break
                
                posts.extend(page_posts)
                page += 1
                
                # 最後のページかチェック
                if 'X-WP-TotalPages' in response.headers:
                    if page > int(response.headers['X-WP-TotalPages']):
                        break
            
            # 必要な情報を抽出
            processed_posts = []
            for post in posts[:count]:
                processed_posts.append(self._process_post(post))
            
            logger.info(f"{len(processed_posts)}件の記事を取得しました")
            return processed_posts
            
        except Exception as e:
            logger.error(f"記事取得エラー: {str(e)}")
            return []
    
    def analyze_site_content(self, post_count: int = 50) -> Dict:
        """
        サイトコンテンツを分析
        
        Args:
            post_count: 分析する記事数
        
        Returns:
            分析結果
        """
        posts = self.get_recent_posts(count=post_count)
        
        if not posts:
            return {
                'error': '記事を取得できませんでした',
                'total_posts': 0
            }
        
        # 分析データの初期化
        analysis = {
            'total_posts': len(posts),
            'categories': Counter(),
            'tags': Counter(),
            'title_patterns': [],
            'content_patterns': [],
            'avg_content_length': 0,
            'posting_frequency': {},
            'popular_topics': [],
            'writing_style': {},
            'seo_patterns': {}
        }
        
        # 各記事を分析
        total_length = 0
        all_titles = []
        all_content = []
        
        for post in posts:
            # カテゴリとタグの集計
            for cat in post.get('categories', []):
                analysis['categories'][cat] += 1
            
            for tag in post.get('tags', []):
                analysis['tags'][tag] += 1
            
            # タイトルと本文を収集
            title = post.get('title', '')
            content = post.get('content', '')
            
            all_titles.append(title)
            all_content.append(content)
            total_length += len(content)
        
        # 平均文字数
        analysis['avg_content_length'] = int(total_length / len(posts)) if posts else 0
        
        # タイトルパターンの分析
        analysis['title_patterns'] = self._analyze_title_patterns(all_titles)
        
        # コンテンツパターンの分析
        analysis['content_patterns'] = self._analyze_content_patterns(all_content)
        
        # 投稿頻度の分析
        analysis['posting_frequency'] = self._analyze_posting_frequency(posts)
        
        # 人気トピックの抽出
        analysis['popular_topics'] = self._extract_popular_topics(posts)
        
        # 文体の分析
        analysis['writing_style'] = self._analyze_writing_style(all_content)
        
        # SEOパターンの分析
        analysis['seo_patterns'] = self._analyze_seo_patterns(posts)
        
        return analysis
    
    def find_content_gaps(self, site_purpose: str, existing_posts: List[Dict]) -> List[Dict]:
        """
        コンテンツギャップを発見（次に書くべき記事のアイデア）
        
        Args:
            site_purpose: サイトの目的・方針
            existing_posts: 既存の記事リスト
        
        Returns:
            記事アイデアのリスト
        """
        ideas = []
        
        # 既存記事のトピックを抽出
        existing_topics = set()
        existing_keywords = Counter()
        
        for post in existing_posts:
            # タイトルからキーワードを抽出
            title_keywords = self._extract_keywords(post.get('title', ''))
            existing_keywords.update(title_keywords)
            
            # トピックを記録
            if post.get('categories'):
                existing_topics.update(post['categories'])
        
        # カテゴリの組み合わせで新しいアイデアを生成
        categories = list(existing_topics)
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                idea = {
                    'type': 'category_combination',
                    'title_suggestion': f"{cat1}と{cat2}の関係性について",
                    'reason': f"既存カテゴリの新しい組み合わせ",
                    'priority': 'medium'
                }
                ideas.append(idea)
        
        # 人気キーワードの深堀り
        popular_keywords = existing_keywords.most_common(10)
        for keyword, count in popular_keywords[:5]:
            idea = {
                'type': 'keyword_expansion',
                'title_suggestion': f"{keyword}の完全ガイド",
                'reason': f"人気キーワード（{count}回使用）の詳細解説",
                'priority': 'high'
            }
            ideas.append(idea)
        
        # 季節性コンテンツの提案
        current_month = datetime.now().month
        seasonal_topics = self._get_seasonal_topics(current_month, site_purpose)
        ideas.extend(seasonal_topics)
        
        # トレンドトピックの提案（サイトの目的に基づく）
        trend_topics = self._get_trend_topics(site_purpose, existing_topics)
        ideas.extend(trend_topics)
        
        return ideas[:10]  # 上位10個のアイデアを返す
    
    def _process_post(self, post: Dict) -> Dict:
        """投稿データを処理"""
        processed = {
            'id': post.get('id'),
            'title': self._clean_html(post.get('title', {}).get('rendered', '')),
            'content': self._clean_html(post.get('content', {}).get('rendered', '')),
            'excerpt': self._clean_html(post.get('excerpt', {}).get('rendered', '')),
            'date': post.get('date'),
            'slug': post.get('slug'),
            'link': post.get('link'),
            'categories': [],
            'tags': [],
            'featured_media': post.get('featured_media')
        }
        
        # カテゴリとタグの名前を取得
        if '_embedded' in post:
            if 'wp:term' in post['_embedded']:
                for term_list in post['_embedded']['wp:term']:
                    for term in term_list:
                        if term.get('taxonomy') == 'category':
                            processed['categories'].append(term.get('name'))
                        elif term.get('taxonomy') == 'post_tag':
                            processed['tags'].append(term.get('name'))
        
        return processed
    
    def _clean_html(self, html: str) -> str:
        """HTMLタグを除去"""
        # 基本的なHTMLタグの除去
        clean = re.sub(r'<[^>]+>', '', html)
        # エンティティのデコード
        clean = clean.replace('&nbsp;', ' ')
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        return clean.strip()
    
    def _analyze_title_patterns(self, titles: List[str]) -> List[str]:
        """タイトルパターンを分析"""
        patterns = []
        
        # 数字を含むタイトル
        number_titles = [t for t in titles if re.search(r'\d+', t)]
        if len(number_titles) > len(titles) * 0.3:
            patterns.append("数字を含むタイトルが好まれる（例：5つの方法、10選）")
        
        # 疑問形タイトル
        question_titles = [t for t in titles if t.endswith('？') or t.endswith('?')]
        if len(question_titles) > len(titles) * 0.2:
            patterns.append("疑問形タイトルが多い")
        
        # How to形式
        howto_titles = [t for t in titles if '方法' in t or '仕方' in t or 'やり方' in t]
        if len(howto_titles) > len(titles) * 0.3:
            patterns.append("ハウツー記事が多い")
        
        return patterns
    
    def _analyze_content_patterns(self, contents: List[str]) -> List[str]:
        """コンテンツパターンを分析"""
        patterns = []
        
        # 平均的な段落数をチェック
        avg_paragraphs = sum(content.count('\n\n') + 1 for content in contents) / len(contents)
        patterns.append(f"平均段落数: {int(avg_paragraphs)}")
        
        # リスト形式の使用
        list_count = sum(1 for content in contents if '・' in content or '1.' in content)
        if list_count > len(contents) * 0.4:
            patterns.append("リスト形式をよく使用")
        
        return patterns
    
    def _analyze_posting_frequency(self, posts: List[Dict]) -> Dict:
        """投稿頻度を分析"""
        if not posts:
            return {}
        
        # 日付でソート
        sorted_posts = sorted(posts, key=lambda x: x.get('date', ''))
        
        # 週ごとの投稿数を計算
        weekly_posts = Counter()
        for post in sorted_posts:
            date_str = post.get('date', '')
            if date_str:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                week = date.isocalendar()[1]
                weekly_posts[week] += 1
        
        avg_per_week = sum(weekly_posts.values()) / len(weekly_posts) if weekly_posts else 0
        
        return {
            'average_per_week': round(avg_per_week, 1),
            'total_weeks': len(weekly_posts),
            'most_active_week': weekly_posts.most_common(1)[0] if weekly_posts else None
        }
    
    def _extract_popular_topics(self, posts: List[Dict]) -> List[str]:
        """人気トピックを抽出"""
        # すべてのキーワードを収集
        all_keywords = Counter()
        
        for post in posts:
            keywords = self._extract_keywords(post.get('title', '') + ' ' + post.get('content', ''))
            all_keywords.update(keywords)
        
        # 上位10個のキーワード
        popular = all_keywords.most_common(20)
        
        # ストップワードを除外
        stopwords = {'の', 'は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'です', 'ます'}
        filtered = [(word, count) for word, count in popular if word not in stopwords and len(word) > 1]
        
        return [word for word, count in filtered[:10]]
    
    def _analyze_writing_style(self, contents: List[str]) -> Dict:
        """文体を分析"""
        style = {
            'formal': 0,
            'casual': 0,
            'sentence_endings': Counter()
        }
        
        for content in contents:
            # 敬語の使用
            if 'です。' in content or 'ます。' in content:
                style['formal'] += 1
            else:
                style['casual'] += 1
            
            # 文末表現を収集
            sentences = re.split(r'[。！？]', content)
            for sentence in sentences:
                if sentence:
                    ending = sentence[-10:]  # 文末10文字
                    style['sentence_endings'][ending] += 1
        
        return {
            'formality': 'formal' if style['formal'] > style['casual'] else 'casual',
            'common_endings': style['sentence_endings'].most_common(5)
        }
    
    def _analyze_seo_patterns(self, posts: List[Dict]) -> Dict:
        """SEOパターンを分析"""
        patterns = {
            'title_length': [],
            'excerpt_usage': 0,
            'keyword_density': []
        }
        
        for post in posts:
            # タイトル長
            title_length = len(post.get('title', ''))
            patterns['title_length'].append(title_length)
            
            # 抜粋の使用
            if post.get('excerpt'):
                patterns['excerpt_usage'] += 1
        
        avg_title_length = sum(patterns['title_length']) / len(patterns['title_length']) if patterns['title_length'] else 0
        
        return {
            'avg_title_length': int(avg_title_length),
            'excerpt_usage_rate': patterns['excerpt_usage'] / len(posts) if posts else 0,
            'optimal_title_range': '25-35文字' if 25 <= avg_title_length <= 35 else f"{int(avg_title_length)}文字前後"
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        # 簡易的な形態素解析（実際はMeCabなどを使用すべき）
        # ここでは単純に名詞っぽいものを抽出
        words = re.findall(r'[ァ-ヾ]+|[一-龥]+', text)
        
        # 2文字以上の単語のみ
        keywords = [word for word in words if len(word) >= 2]
        
        return keywords
    
    def _get_seasonal_topics(self, month: int, site_purpose: str) -> List[Dict]:
        """季節性のあるトピックを提案"""
        seasonal_map = {
            1: ["新年", "目標", "始める"],
            2: ["バレンタイン", "節分"],
            3: ["ひな祭り", "卒業", "春"],
            4: ["新生活", "花見", "新年度"],
            5: ["ゴールデンウィーク", "母の日"],
            6: ["梅雨", "父の日"],
            7: ["夏休み", "海", "花火"],
            8: ["お盆", "夏祭り"],
            9: ["秋", "運動会", "読書"],
            10: ["ハロウィン", "紅葉"],
            11: ["七五三", "感謝"],
            12: ["クリスマス", "年末", "大掃除"]
        }
        
        topics = []
        current_keywords = seasonal_map.get(month, [])
        
        for keyword in current_keywords:
            topics.append({
                'type': 'seasonal',
                'title_suggestion': f"{keyword}に関する特集記事",
                'reason': f"{month}月の季節トピック",
                'priority': 'high'
            })
        
        return topics
    
    def _get_trend_topics(self, site_purpose: str, existing_topics: set) -> List[Dict]:
        """トレンドトピックを提案"""
        # サイトの目的に基づいて関連トレンドを提案
        # 実際はGoogle TrendsやSNS APIを使用すべき
        
        trend_ideas = []
        
        # AIやテクノロジー系
        if any(word in site_purpose for word in ['テクノロジー', 'IT', 'プログラミング', '技術']):
            trend_ideas.extend([
                {
                    'type': 'trend',
                    'title_suggestion': 'AI活用の最新事例',
                    'reason': 'テクノロジートレンド',
                    'priority': 'high'
                },
                {
                    'type': 'trend',
                    'title_suggestion': 'ChatGPTの実践的な使い方',
                    'reason': '話題のAIツール',
                    'priority': 'high'
                }
            ])
        
        # ライフスタイル系
        if any(word in site_purpose for word in ['ライフスタイル', '生活', '健康', 'ウェルネス']):
            trend_ideas.extend([
                {
                    'type': 'trend',
                    'title_suggestion': 'リモートワーク時代の健康管理',
                    'reason': '現代のライフスタイルトレンド',
                    'priority': 'medium'
                },
                {
                    'type': 'trend',
                    'title_suggestion': 'サステナブルな生活習慣',
                    'reason': '環境意識の高まり',
                    'priority': 'medium'
                }
            ])
        
        return trend_ideas