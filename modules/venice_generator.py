"""
VeniceAI記事生成エンジン
VeniceAI APIを使用してサイトの特性に合わせた記事を自動生成
"""
import os
import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VeniceArticleGenerator:
    """VeniceAI記事生成クラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: VeniceAI APIキー
        """
        # APIキーの取得優先順位: 引数 > 環境変数 > config/api_keys.json
        self.api_key = api_key
        
        if not self.api_key:
            self.api_key = os.getenv('VENICE_API_KEY')
            
        if not self.api_key:
            try:
                with open('config/api_keys.json', 'r') as f:
                    api_config = json.load(f)
                    self.api_key = api_config.get('venice', {}).get('api_key', '')
            except:
                pass
                
        if not self.api_key:
            raise ValueError("VeniceAI APIキーが設定されていません")
        
        self.api_base = "https://api.venice.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 記事タイプ別のテンプレート（Claude版と同じ）
        self.templates = {
            'howto': self._get_howto_template(),
            'list': self._get_list_template(),
            'review': self._get_review_template(),
            'news': self._get_news_template(),
            'column': self._get_column_template()
        }
    
    def generate_article(self, 
                        site_info: Dict,
                        article_type: str = 'auto',
                        keywords: Optional[List[str]] = None,
                        length: int = 7000,
                        tone: str = 'professional',
                        affiliate_products: Optional[List[Dict]] = None) -> Dict:
        """
        記事を生成
        
        Args:
            site_info: サイト情報
            article_type: 記事タイプ
            keywords: キーワードリスト
            length: 目標文字数
            tone: 文体
            affiliate_products: 使用するアフィリエイト商品
        
        Returns:
            生成された記事情報
        """
        try:
            # 記事タイプを自動選択
            if article_type == 'auto':
                article_type = self._select_article_type(site_info)
            
            # プロンプトを構築
            prompt = self._build_prompt(
                site_info, article_type, keywords, length, tone, affiliate_products
            )
            
            # VeniceAI APIで生成
            logger.info(f"VeniceAIで記事生成開始: {site_info.get('name', 'Unknown')}")
            
            payload = {
                "model": "llama-3.3-70b",  # VeniceAIのモデル
                "messages": [
                    {
                        "role": "system",
                        "content": "あなたは優秀な日本語コンテンツライターです。SEOに強く、読者に価値を提供する記事を作成します。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 8000,
                "stream": False
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"VeniceAI APIエラー: {response.status_code} - {response.text}")
                raise Exception(f"API Error: {response.status_code}")
            
            # レスポンスを解析
            result = response.json()
            content = result['choices'][0]['message']['content']
            article = self._parse_response(content)
            
            # アフィリエイトリンクを挿入
            if affiliate_products:
                article['content'] = self._insert_affiliate_links(
                    article['content'], affiliate_products
                )
            
            # メタデータを追加
            article['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'site_id': site_info.get('site_id'),
                'article_type': article_type,
                'keywords': keywords,
                'length': len(article.get('content', '')),
                'model': 'venice-llama-3.3-70b',
                'affiliate_products': [p.get('product_id') for p in (affiliate_products or [])]
            }
            
            logger.info(f"記事生成完了: {article.get('title', 'Untitled')}")
            return article
            
        except Exception as e:
            logger.error(f"VeniceAI記事生成エラー: {str(e)}")
            raise
    
    def _build_prompt(self, site_info: Dict, article_type: str, 
                      keywords: Optional[List[str]], length: int, tone: str,
                      affiliate_products: Optional[List[Dict]] = None) -> str:
        """プロンプトを構築"""
        
        # 基本情報
        site_name = site_info.get('name', 'ブログ')
        genre = site_info.get('genre', '一般')
        genre_details = site_info.get('genre_details', '')
        target_audience = site_info.get('target_audience', '一般読者')
        target_details = site_info.get('target_details', '')
        site_purpose = site_info.get('site_purpose', '')
        content_guidelines = site_info.get('content_guidelines', '')
        
        # テンプレートを取得
        template = self.templates.get(article_type, self.templates['column'])
        
        # キーワードを整形
        keyword_str = '、'.join(keywords) if keywords else 'なし'
        
        # アフィリエイト商品情報
        affiliate_section = ""
        if affiliate_products:
            affiliate_section = "\n【紹介する商品・サービス】\n"
            for product in affiliate_products:
                affiliate_section += f"""
- {product.get('name')}
  説明: {product.get('description')}
  ターゲット: {product.get('target_audience')}
  セールスポイント: {product.get('selling_points')}
  プロモーション指針: {product.get('promotion_guidelines')}
"""
        
        prompt = f"""
あなたは{site_name}の専門ライターです。
以下の条件で{genre}に関する詳細な記事を作成してください。

【サイト情報】
- サイト名: {site_name}
- ジャンル: {genre}
- ジャンル詳細: {genre_details}
- ターゲット読者: {target_audience}
- ターゲット詳細: {target_details}
- サイトの目的: {site_purpose}
- コンテンツガイドライン: {content_guidelines}
- 文体: {self._get_tone_description(tone)}

【記事要件】
- 記事タイプ: {template['name']}
- 目標文字数: {length}文字（必須）
- キーワード: {keyword_str}
{affiliate_section}

【記事構成】
{template['structure']}

【重要な指示】
1. 必ず{length}文字程度の充実した内容にしてください
2. 各セクションを詳細に展開し、具体例や実践的なアドバイスを含めてください
3. 読者が実際に行動できる具体的な情報を提供してください
4. 専門的な内容も分かりやすく解説してください
5. 最新のトレンドや統計データがあれば含めてください
6. アフィリエイト商品は自然な文脈で紹介してください

以下の形式で出力してください：

<title>記事タイトル</title>

<description>メタディスクリプション（120文字程度）</description>

<tags>タグ1, タグ2, タグ3</tags>

<content>
記事本文をここに記載
見出しは##、###を使用してマークダウン形式で
アフィリエイトリンクは [商品名](AFFILIATE_LINK_商品ID) の形式で記載
</content>
"""
        return prompt
    
    def _parse_response(self, content: str) -> Dict:
        """レスポンスを解析して記事データを抽出"""
        
        article = {
            'title': '',
            'description': '',
            'tags': [],
            'content': '',
            'excerpt': ''
        }
        
        # タイトルを抽出
        title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
        if title_match:
            article['title'] = title_match.group(1).strip()
        
        # メタディスクリプションを抽出
        desc_match = re.search(r'<description>(.*?)</description>', content, re.DOTALL)
        if desc_match:
            article['description'] = desc_match.group(1).strip()
        
        # タグを抽出
        tags_match = re.search(r'<tags>(.*?)</tags>', content, re.DOTALL)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            article['tags'] = [tag.strip() for tag in tags_str.split(',')]
        
        # 本文を抽出
        content_match = re.search(r'<content>(.*?)</content>', content, re.DOTALL)
        if content_match:
            article['content'] = content_match.group(1).strip()
            # 抜粋を生成
            plain_text = re.sub(r'#.*?\n', '', article['content'])
            plain_text = re.sub(r'\*\*(.*?)\*\*', r'\1', plain_text)
            plain_text = re.sub(r'\[.*?\]\(.*?\)', '', plain_text)
            article['excerpt'] = plain_text[:150] + '...' if len(plain_text) > 150 else plain_text
        
        return article
    
    def _insert_affiliate_links(self, content: str, affiliate_products: List[Dict]) -> str:
        """アフィリエイトリンクを実際のURLに置換"""
        for product in affiliate_products:
            placeholder = f"AFFILIATE_LINK_{product.get('product_id', '')}"
            actual_link = product.get('link_url', '#')
            content = content.replace(placeholder, actual_link)
        
        return content
    
    def _select_article_type(self, site_info: Dict) -> str:
        """サイト情報から適切な記事タイプを選択"""
        genre = site_info.get('genre', '').lower()
        
        if 'ニュース' in genre or 'news' in genre:
            return 'news'
        elif 'レビュー' in genre or 'review' in genre:
            return 'review'
        elif 'ハウツー' in genre or 'how' in genre:
            return 'howto'
        elif any(word in genre for word in ['ランキング', 'まとめ', 'list']):
            return 'list'
        else:
            return 'column'
    
    def _get_tone_description(self, tone: str) -> str:
        """文体の説明を取得"""
        tone_map = {
            'professional': 'プロフェッショナルで信頼性のある文体',
            'casual': 'カジュアルで親しみやすい文体',
            'friendly': 'フレンドリーで対話的な文体',
            'academic': 'アカデミックで論理的な文体',
            'enthusiastic': '熱意があり情熱的な文体'
        }
        return tone_map.get(tone, tone_map['professional'])
    
    # テンプレートメソッド（Claude版と同じ）
    def _get_howto_template(self) -> Dict:
        return {
            'name': 'ハウツー記事',
            'structure': '''
1. 導入（問題提起）- 500文字
2. 必要なもの・準備 - 800文字
3. ステップバイステップの手順 - 3000文字
4. 注意点・コツ - 1500文字
5. よくある質問 - 800文字
6. まとめ・次のステップ - 400文字
'''
        }
    
    def _get_list_template(self) -> Dict:
        return {
            'name': 'リスト記事',
            'structure': '''
1. 導入（なぜこのリストが重要か）- 600文字
2. リスト項目（7-10個）- 各600-800文字
3. 比較表 - 500文字
4. まとめ・選び方のポイント - 600文字
'''
        }
    
    def _get_review_template(self) -> Dict:
        return {
            'name': 'レビュー記事',
            'structure': '''
1. 製品・サービス概要 - 800文字
2. 特徴・スペック詳細 - 1200文字
3. 実際に使用した感想（具体的に）- 2000文字
4. メリット・デメリット - 1500文字
5. 他製品との比較 - 1000文字
6. おすすめする人・しない人 - 300文字
7. 総評・評価 - 200文字
'''
        }
    
    def _get_news_template(self) -> Dict:
        return {
            'name': 'ニュース記事',
            'structure': '''
1. リード文（5W1H）- 400文字
2. 詳細情報 - 2000文字
3. 背景・経緯 - 1500文字
4. 影響・今後の展望 - 2000文字
5. 専門家の見解 - 800文字
6. まとめ - 300文字
'''
        }
    
    def _get_column_template(self) -> Dict:
        return {
            'name': 'コラム記事',
            'structure': '''
1. 導入（話題の提示）- 600文字
2. 本論（4つのポイント）- 各1300文字
3. 具体例・体験談 - 1000文字
4. 考察・意見 - 600文字
5. 結論・読者へのメッセージ - 400文字
'''
        }