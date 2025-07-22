"""
AIコンテンツストラテジスト
過去記事を分析して次の記事テーマを自動決定
"""
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import re
from collections import Counter

logger = logging.getLogger(__name__)


class ContentStrategist:
    """AIが過去記事を分析して戦略的に次の記事を決定"""
    
    def __init__(self, claude_client):
        self.claude_client = claude_client
        self.model = "claude-sonnet-4-20250514"
        
    def analyze_published_articles(self, site_id: str) -> Dict:
        """
        公開済み記事を分析
        
        Returns:
            分析結果の辞書
        """
        try:
            with open('data/generated_articles.json', 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
        except:
            return {
                'total_articles': 0,
                'topics_covered': [],
                'keyword_frequency': {},
                'performance_insights': {}
            }
        
        # サイトの記事をフィルタリング
        site_articles = [
            a for a in articles_data.get('articles', [])
            if a.get('site_id') == site_id and a.get('status') == '公開済み'
        ]
        
        # トピック分析
        topics = []
        all_keywords = []
        titles = []
        
        for article in site_articles:
            titles.append(article.get('title', ''))
            topics.append(article.get('title', ''))
            all_keywords.extend(article.get('tags', []))
        
        # キーワード頻度分析
        keyword_freq = Counter(all_keywords)
        
        # カテゴリ分析
        categories_used = []
        for article in site_articles:
            # メタデータからカテゴリ情報を取得（実装予定）
            pass
        
        return {
            'total_articles': len(site_articles),
            'topics_covered': topics,
            'titles': titles,
            'keyword_frequency': dict(keyword_freq),
            'recent_articles': site_articles[:10],  # 最新10記事
            'oldest_article_date': site_articles[-1]['created_at'] if site_articles else None,
            'newest_article_date': site_articles[0]['created_at'] if site_articles else None
        }
    
    def analyze_wordpress_content(self, publisher, limit: int = 50) -> Dict:
        """
        WordPress上の既存記事を分析
        
        Args:
            publisher: WordPressPublisher instance
            limit: 取得する記事数
            
        Returns:
            分析結果
        """
        try:
            # WordPress APIで記事一覧を取得
            import requests
            response = requests.get(
                f"{publisher.api_base}/posts",
                headers=publisher.headers,
                params={'per_page': limit, 'status': 'publish'}
            )
            
            if response.status_code != 200:
                return {'error': 'Failed to fetch WordPress posts'}
            
            posts = response.json()
            
            # 記事データを分析
            titles = []
            categories = []
            tags = []
            contents = []
            
            for post in posts:
                titles.append(post.get('title', {}).get('rendered', ''))
                
                # カテゴリとタグのIDから名前を取得する必要がある
                categories.extend(post.get('categories', []))
                tags.extend(post.get('tags', []))
                
                # コンテンツの最初の部分を取得
                content = post.get('content', {}).get('rendered', '')
                # HTMLタグを除去
                content = re.sub('<.*?>', '', content)
                contents.append(content[:500])  # 最初の500文字
            
            return {
                'total_posts': len(posts),
                'titles': titles,
                'category_ids': categories,
                'tag_ids': tags,
                'content_samples': contents
            }
            
        except Exception as e:
            logger.error(f"WordPress分析エラー: {str(e)}")
            return {'error': str(e)}
    
    def generate_content_strategy(self, site_info: Dict, past_analysis: Dict, 
                                wordpress_analysis: Optional[Dict] = None) -> List[Dict]:
        """
        AIが次に書くべき記事テーマを提案
        
        Args:
            site_info: サイト情報
            past_analysis: 過去記事の分析結果
            wordpress_analysis: WordPress既存記事の分析
            
        Returns:
            提案される記事テーマのリスト
        """
        # プロンプトを構築
        prompt = f"""
あなたは{site_info.get('name')}のコンテンツストラテジストです。
過去の記事を分析し、次に書くべき記事テーマを戦略的に提案してください。

【サイト情報】
- サイト名: {site_info.get('name')}
- ジャンル: {site_info.get('genre_details', site_info.get('genre'))}
- ターゲット: {site_info.get('target_details', site_info.get('target_audience'))}
- キーワード: {site_info.get('keywords_focus')}

【過去記事分析】
- 総記事数: {past_analysis.get('total_articles', 0)}
- 最近の記事タイトル:
{chr(10).join(['  - ' + t for t in past_analysis.get('titles', [])[:10]])}

- よく使われるキーワード:
{chr(10).join([f'  - {k}: {v}回' for k, v in sorted(past_analysis.get('keyword_frequency', {}).items(), key=lambda x: x[1], reverse=True)[:10]])}

{f'''【WordPress既存記事】
- 既存記事数: {wordpress_analysis.get('total_posts', 0)}
- 既存記事タイトル（一部）:
{chr(10).join(['  - ' + t for t in wordpress_analysis.get('titles', [])[:5]])}
''' if wordpress_analysis and not wordpress_analysis.get('error') else ''}

【分析してほしいこと】
1. カバーされていないトピック（ギャップ分析）
2. 読者が次に知りたいであろう内容
3. SEO的に狙うべきキーワード
4. トレンドや季節性を考慮した提案

【提案フォーマット】
以下の形式で5つの記事テーマを提案してください：

<suggestions>
<article>
<title>記事タイトル案</title>
<keywords>キーワード1, キーワード2, キーワード3</keywords>
<reason>この記事を書く理由（戦略的意図）</reason>
<target>想定読者層</target>
<expected_impact>期待される効果</expected_impact>
</article>
（5つ繰り返し）
</suggestions>

【重要な制約】
- 既存記事と重複しないテーマ
- 時期や季節を示すワードは使わない
- サイトの方向性に合致した内容
- 読者に価値を提供できる内容
"""
        
        try:
            # Claude APIで分析
            response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text
            
            # 提案を解析
            suggestions = self._parse_suggestions(content)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"コンテンツ戦略生成エラー: {str(e)}")
            return []
    
    def _parse_suggestions(self, content: str) -> List[Dict]:
        """提案されたコンテンツを解析"""
        suggestions = []
        
        # <article>タグで記事を抽出
        article_matches = re.findall(r'<article>(.*?)</article>', content, re.DOTALL)
        
        for article_content in article_matches:
            suggestion = {}
            
            # 各要素を抽出
            title_match = re.search(r'<title>(.*?)</title>', article_content)
            if title_match:
                suggestion['title'] = title_match.group(1).strip()
            
            keywords_match = re.search(r'<keywords>(.*?)</keywords>', article_content)
            if keywords_match:
                keywords_str = keywords_match.group(1).strip()
                suggestion['keywords'] = [k.strip() for k in keywords_str.split(',')]
            
            reason_match = re.search(r'<reason>(.*?)</reason>', article_content)
            if reason_match:
                suggestion['reason'] = reason_match.group(1).strip()
            
            target_match = re.search(r'<target>(.*?)</target>', article_content)
            if target_match:
                suggestion['target'] = target_match.group(1).strip()
            
            impact_match = re.search(r'<expected_impact>(.*?)</expected_impact>', article_content)
            if impact_match:
                suggestion['expected_impact'] = impact_match.group(1).strip()
            
            if suggestion.get('title'):
                suggestions.append(suggestion)
        
        return suggestions
    
    def select_next_topic(self, suggestions: List[Dict], selection_criteria: Dict = None) -> Dict:
        """
        提案から次のトピックを選択
        
        Args:
            suggestions: 提案リスト
            selection_criteria: 選択基準（優先順位など）
            
        Returns:
            選択されたトピック
        """
        if not suggestions:
            return {}
        
        # デフォルトは最初の提案を選択
        # 将来的にはより高度な選択ロジックを実装
        selected = suggestions[0]
        
        # 選択理由を追加
        selected['selection_reason'] = "最も戦略的価値が高いと判断"
        
        return selected
    
    def create_content_calendar(self, suggestions: List[Dict], 
                              posting_frequency: str = "daily") -> List[Dict]:
        """
        コンテンツカレンダーを作成
        
        Args:
            suggestions: 記事提案リスト
            posting_frequency: 投稿頻度（daily, twice_daily, weekly）
            
        Returns:
            スケジュール付きコンテンツリスト
        """
        calendar = []
        
        # 投稿間隔を決定
        intervals = {
            'daily': 1,
            'twice_daily': 0.5,
            'weekly': 7
        }
        
        interval_days = intervals.get(posting_frequency, 1)
        
        # 現在時刻から開始
        current_date = datetime.now()
        
        for i, suggestion in enumerate(suggestions):
            scheduled_date = current_date + timedelta(days=interval_days * i)
            
            calendar_entry = {
                **suggestion,
                'scheduled_date': scheduled_date.isoformat(),
                'scheduled_time': '10:00' if scheduled_date.hour < 12 else '15:00',
                'status': 'scheduled'
            }
            
            calendar.append(calendar_entry)
        
        return calendar