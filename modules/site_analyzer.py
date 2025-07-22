"""
サイト分析モジュール
既存サイトの記事を分析して方向性を把握
"""
import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class SiteAnalyzer:
    """サイト分析クラス"""
    
    def __init__(self):
        """初期化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def analyze_site(self, site_url: str, max_articles: int = 5) -> Dict:
        """
        サイトを分析して記事の傾向を把握
        
        Args:
            site_url: サイトURL
            max_articles: 分析する記事数
            
        Returns:
            分析結果の辞書
        """
        try:
            # WordPressのREST APIを試す
            wp_api = self._check_wordpress_api(site_url)
            if wp_api:
                return self._analyze_wordpress_site(site_url, max_articles)
            else:
                # 通常のスクレイピング
                return self._analyze_general_site(site_url, max_articles)
                
        except Exception as e:
            logger.error(f"サイト分析エラー: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'articles': [],
                'categories': [],
                'style': {}
            }
    
    def _check_wordpress_api(self, site_url: str) -> bool:
        """
        WordPress REST APIが利用可能か確認
        
        Args:
            site_url: サイトURL
            
        Returns:
            利用可能な場合True
        """
        try:
            api_url = urljoin(site_url, '/wp-json/wp/v2/posts')
            response = self.session.get(api_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _analyze_wordpress_site(self, site_url: str, max_articles: int) -> Dict:
        """
        WordPress REST APIを使用してサイトを分析
        
        Args:
            site_url: サイトURL
            max_articles: 分析する記事数
            
        Returns:
            分析結果
        """
        try:
            # 最新記事を取得
            posts_url = urljoin(site_url, f'/wp-json/wp/v2/posts?per_page={max_articles}')
            posts_response = self.session.get(posts_url)
            posts = posts_response.json()
            
            # カテゴリを取得
            categories_url = urljoin(site_url, '/wp-json/wp/v2/categories?per_page=100')
            categories_response = self.session.get(categories_url)
            categories = categories_response.json()
            
            # 記事を分析
            analyzed_articles = []
            total_length = 0
            
            for post in posts:
                # HTMLタグを除去
                content = BeautifulSoup(post['content']['rendered'], 'html.parser').get_text()
                title = post['title']['rendered']
                
                analyzed_articles.append({
                    'title': title,
                    'url': post['link'],
                    'content_length': len(content),
                    'excerpt': content[:200] + '...' if len(content) > 200 else content,
                    'categories': [cat['id'] for cat in post.get('categories', [])]
                })
                
                total_length += len(content)
            
            # カテゴリ情報を整理
            category_list = [
                {
                    'id': cat['id'],
                    'name': cat['name'],
                    'slug': cat['slug'],
                    'count': cat.get('count', 0)
                }
                for cat in categories
            ]
            
            # スタイル分析
            avg_length = total_length // len(analyzed_articles) if analyzed_articles else 0
            
            return {
                'success': True,
                'articles': analyzed_articles,
                'categories': category_list,
                'style': {
                    'average_article_length': avg_length,
                    'total_articles_analyzed': len(analyzed_articles),
                    'common_categories': self._get_common_categories(analyzed_articles, category_list)
                }
            }
            
        except Exception as e:
            logger.error(f"WordPress API分析エラー: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'articles': [],
                'categories': [],
                'style': {}
            }
    
    def _analyze_general_site(self, site_url: str, max_articles: int) -> Dict:
        """
        一般的なHTMLスクレイピングでサイトを分析
        
        Args:
            site_url: サイトURL
            max_articles: 分析する記事数
            
        Returns:
            分析結果
        """
        try:
            # トップページを取得
            response = self.session.get(site_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 記事リンクを探す（一般的なパターン）
            article_links = []
            
            # h2, h3タグのリンク
            for heading in soup.find_all(['h2', 'h3']):
                link = heading.find('a')
                if link and link.get('href'):
                    article_links.append(urljoin(site_url, link['href']))
            
            # articleタグ内のリンク
            for article in soup.find_all('article'):
                link = article.find('a')
                if link and link.get('href'):
                    article_links.append(urljoin(site_url, link['href']))
            
            # 重複を除去
            article_links = list(set(article_links))[:max_articles]
            
            # 各記事を分析
            analyzed_articles = []
            for link in article_links:
                try:
                    article_data = self._analyze_article(link)
                    if article_data:
                        analyzed_articles.append(article_data)
                except:
                    continue
            
            return {
                'success': True,
                'articles': analyzed_articles,
                'categories': [],  # スクレイピングではカテゴリ取得は困難
                'style': {
                    'total_articles_analyzed': len(analyzed_articles)
                }
            }
            
        except Exception as e:
            logger.error(f"一般サイト分析エラー: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'articles': [],
                'categories': [],
                'style': {}
            }
    
    def _analyze_article(self, url: str) -> Optional[Dict]:
        """
        個別記事を分析
        
        Args:
            url: 記事URL
            
        Returns:
            記事情報
        """
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトルを取得
            title = soup.find('h1')
            if not title:
                title = soup.find('title')
            title_text = title.get_text().strip() if title else 'Untitled'
            
            # 本文を取得（一般的なパターン）
            content = ""
            for selector in ['article', 'main', '.content', '#content', '.entry-content']:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text().strip()
                    break
            
            if not content:
                # 最大のテキストブロックを取得
                content = soup.get_text()
            
            return {
                'title': title_text,
                'url': url,
                'content_length': len(content),
                'excerpt': content[:200] + '...' if len(content) > 200 else content
            }
            
        except Exception as e:
            logger.error(f"記事分析エラー: {url} - {str(e)}")
            return None
    
    def _get_common_categories(self, articles: List[Dict], categories: List[Dict]) -> List[str]:
        """
        最も使用されているカテゴリを取得
        
        Args:
            articles: 記事リスト
            categories: カテゴリリスト
            
        Returns:
            一般的なカテゴリ名のリスト
        """
        category_count = {}
        category_map = {cat['id']: cat['name'] for cat in categories}
        
        for article in articles:
            for cat_id in article.get('categories', []):
                if cat_id in category_map:
                    name = category_map[cat_id]
                    category_count[name] = category_count.get(name, 0) + 1
        
        # 使用頻度順にソート
        sorted_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)
        return [cat[0] for cat in sorted_categories[:5]]