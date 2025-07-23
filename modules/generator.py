"""
記事生成エンジン
GPT APIを使用してサイトの特性に合わせた記事を自動生成
"""
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
import openai
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleGeneratorGPT:
    """記事生成クラス（GPT版）"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: OpenAI  APIキー
        """
        # APIキーの取得優先順位: 引数 > 環境変数 > config/api_keys.json
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            
        if not self.api_key:
            try:
                with open('config/api_keys.json', 'r') as f:
                    api_config = json.load(f)
                    self.api_key = api_config.get('openai', {}).get('api_key', '')
            except:
                pass
                
        if not self.api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        
        openai.api_key = self.api_key
        
        # API設定から現在のモデルを読み込む
        self.model = "gpt-4-1106-preview"

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
            site_info: サイト情報（ジャンル、ターゲット、過去記事など）
            article_type: 記事タイプ（auto, howto, list, review, news, column）
            keywords: キーワードリスト
            length: 目標文字数
            tone: 文体（professional, casual, friendly）
        
        Returns:
            生成された記事情報
        """
        try:
            # 記事タイプを自動選択
            if article_type == 'auto':
                article_type = self._select_article_type(site_info)
            
            # プロンプトを構築
            prompt = self._build_prompt(site_info, article_type, keywords, length, tone, affiliate_products)
            logger.info(f"記事生成開始: {site_info.get('name', 'Unknown')} - モデル: {self.model}")            

            # GPT向けにenhanced_promptを組み立てる
            enhanced_prompt = f""" ... """
あなたはこのサイトの専門ライターかつコンテンツストラテジストです。
記事の目的と読者を深く理解し、SEOや最新のトレンド、過去の記事との重複回避も考慮しながら、
読者が実際に行動しやすいよう具体例・データ・洞察を含む、高品質で詳細な記事を執筆してください。

記事の長さはおおむね{length}文字を目安にします。
各セクションは十分な情報量があり、専門的でありながら読みやすい日本語で書いてください。

以下が執筆条件です：
{prompt}

{site_info.get('variation_prompt', '')}

【重要な指示】
1. 必ず{length}文字程度の充実した内容にしてください
2. 各セクションを詳細に展開し、具体例や実践的なアドバイスを含めてください
3. 読者が実際に行動できる具体的な情報を提供してください
4. 専門的な内容も分かりやすく解説してください
5. 可能なら最新のトレンドや統計データに触れてください
"""

        # OpenAI GPTで生成
            response = openai.ChatCompletion.create(
                model=self.model,
                temperature=0.7,
                max_tokens=30000,
                messages=[
                    {
                    "role": "user",
                    "content": enhanced_prompt
                    }
                ]
            )
            
            # レスポンスを解析
            choices = response.get("choices")
            if not choices or not choices[0].get("message", {}).get("content"):
                raise ValueError("APIレスポンスが不正です")
            content = choices[0]["message"]["content"]
            article = self._parse_response(content)
            
            # メタデータを追加
            article['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'site_id': site_info.get('site_id'),
                'keywords': keywords,
                'article_type': article_type,
                'length': len(article.get('content', '')),
                'model': self.model
            }
            
            logger.info(f"記事生成完了: {article.get('title', 'Untitled')}")
            return article
            
        except Exception as e:
            logger.error(f"記事生成エラー: {str(e)}")
            raise
    
        def _build_prompt(self, site_info, article_type, keywords, length, tone, affiliate_products):
        """プロンプトを構築"""
        
        # 基本情報
        site_name = site_info.get('name', 'ブログ')
        genre = site_info.get('genre', '一般')
        genre_details = site_info.get('genre_details', '')
        target_audience = site_info.get('target_audience', '一般読者')
        target_details = site_info.get('target_details', '')
        site_purpose = site_info.get('site_purpose', '')
        content_guidelines = site_info.get('content_guidelines', '')
        custom_prompt = site_info.get('custom_prompt', '')
        cta_link = site_info.get('cta_link', '')
        cta_description = site_info.get('cta_description', '')
        cta_links = site_info.get('cta_links', [])
        
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
  避けるべき表現: {product.get('avoid_expressions')}
"""
        
        # CTA情報
        cta_section = ""
        if cta_links:
            cta_section = """
【CTA（Call to Action）情報】
以下のCTAリンクから、記事の内容に最も適したものを選んで使用してください：

"""
            for i, cta in enumerate(cta_links, 1):
                cta_section += f"""CTA{i}:
- URL: {cta.get('url', '')}
- 説明: {cta.get('description', '')}
- 対象キーワード: {cta.get('keywords', '')}
- 適した記事タイプ: {cta.get('target_article_type', 'all')}

"""
            cta_section += """
【CTA使用の指示】
- 記事の内容とキーワードに最も関連性の高いCTAを選択
- 選んだCTAを記事内で2-3回、自然に配置
- 読者の行動を促す魅力的な文章でCTAへ誘導
"""
        elif cta_link:
            # 旧形式のCTAリンクとの互換性
            cta_section = f"""
【CTA（Call to Action）情報】
- リンク: {cta_link}
- 説明: {cta_description}
- 記事内で自然にCTAへ誘導してください
- CTAリンクは記事の中盤と終盤に配置
"""
        
        # カスタムプロンプトが設定されている場合
        if custom_prompt:
            # 変数を置換
            prompt = custom_prompt
            prompt = prompt.replace('{site_name}', site_name)
            prompt = prompt.replace('{genre}', genre)
            prompt = prompt.replace('{genre_details}', genre_details)
            prompt = prompt.replace('{target_audience}', target_audience)
            prompt = prompt.replace('{target_details}', target_details)
            prompt = prompt.replace('{site_purpose}', site_purpose)
            prompt = prompt.replace('{content_guidelines}', content_guidelines)
            prompt = prompt.replace('{tone}', self._get_tone_description(tone))
            prompt = prompt.replace('{article_type}', template['name'])
            prompt = prompt.replace('{length}', str(length))
            prompt = prompt.replace('{keywords}', keyword_str)
            prompt = prompt.replace('{affiliate_section}', affiliate_section)
            prompt = prompt.replace('{template_structure}', template['structure'])
            prompt = prompt.replace('{cta_link}', cta_link)
            prompt = prompt.replace('{cta_description}', cta_description)
            prompt = prompt.replace('{cta_section}', cta_section)
            
            # 文字数指定を強調
            prompt += f"\n\n【重要】必ず{length}文字程度の記事を作成してください。"
            
        else:
            # デフォルトプロンプト
            prompt = f"""
あなたは{site_name}の専門ライターです。
以下の条件で{genre}に関する記事を作成してください。

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
- 目標文字数: {length}文字程度（必須）
- キーワード: {keyword_str}
{affiliate_section}
{cta_section}

【記事構成】
{template['structure']}

【タイトル作成の重要指示】
- 読者の心を掴む魅力的なタイトルを作成
- 数字や具体的な成果を含める（例：月5万円、3ステップ、初心者でも7日で）
- 感情に訴える言葉を使う（例：驚愕の、誰でもできる、失敗しない）
- キーワードを自然に含めつつ、クリックしたくなる表現にする
- 「〜の方法」「〜のコツ」「〜完全ガイド」などの定番フレーズも活用
- 【重要】時期や季節を示すワードは絶対に使用しない（今年、来年、今月、春夏秋冬、年末年始、〇月など）
- 時間に依存しない普遍的なタイトルにする

【注意事項】
- SEOを意識したタイトルと見出しを作成
- 読者に価値を提供する内容にする
- 自然な日本語で執筆する
- 信頼性のある情報を提供する

以下の形式で出力してください：

<title>記事タイトル</title>

<description>メタディスクリプション（120文字程度）</description>

<tags>タグ1, タグ2, タグ3</tags>

<content>
記事本文をここに記載
見出しは##、###を使用してマークダウン形式で
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
            # 抜粋を生成（最初の150文字）
            plain_text = re.sub(r'#.*?\n', '', article['content'])
            plain_text = re.sub(r'\*\*(.*?)\*\*', r'\1', plain_text)
            article['excerpt'] = plain_text[:150] + '...' if len(plain_text) > 150 else plain_text
        
        return article
    
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
    
    def _get_howto_template(self) -> Dict:
        """ハウツー記事のテンプレート"""
        return {
            'name': 'ハウツー記事',
            'structure': '''
1. 導入（問題提起）
2. 必要なもの・準備
3. ステップバイステップの手順
4. 注意点・コツ
5. まとめ・次のステップ
'''
        }
    
    def _get_list_template(self) -> Dict:
        """リスト記事のテンプレート"""
        return {
            'name': 'リスト記事',
            'structure': '''
1. 導入（なぜこのリストが重要か）
2. リスト項目（5-10個）
   - 各項目の説明
   - メリット・デメリット
   - おすすめ度
3. 比較表（必要に応じて）
4. まとめ・選び方のポイント
'''
        }
    
    def _get_review_template(self) -> Dict:
        """レビュー記事のテンプレート"""
        return {
            'name': 'レビュー記事',
            'structure': '''
1. 製品・サービス概要
2. 特徴・スペック
3. 実際に使用した感想
4. メリット・デメリット
5. 他製品との比較
6. おすすめする人・しない人
7. 総評・評価
'''
        }
    
    def _get_news_template(self) -> Dict:
        """ニュース記事のテンプレート"""
        return {
            'name': 'ニュース記事',
            'structure': '''
1. リード文（5W1H）
2. 詳細情報
3. 背景・経緯
4. 影響・今後の展望
5. 関係者のコメント（架空でOK）
6. まとめ
'''
        }
    
    def _get_column_template(self) -> Dict:
        """コラム記事のテンプレート"""
        return {
            'name': 'コラム記事',
            'structure': '''
1. 導入（話題の提示）
2. 本論（3-4つのポイント）
3. 具体例・体験談
4. 考察・意見
5. 結論・読者へのメッセージ
'''
        }
    
    def generate_title_variations(self, base_title: str, count: int = 5) -> List[str]:
        """タイトルのバリエーションを生成"""
        prompt = f"""
以下のタイトルのバリエーションを{count}個作成してください。
SEOを意識し、クリックされやすいタイトルにしてください。

元のタイトル: {base_title}

形式:
1. タイトル1
2. タイトル2
...
"""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                max_tokens=500,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # タイトルを抽出
            choices = response.get("choices")
            if not choices or not choices[0].get("message", {}).get("content"):
                raise ValueError("APIレスポンスが不正です")
            content = choices[0]["message"]["content"]
            titles = re.findall(r'\d+\.\s*(.+)', content)
            return titles[:count]
            
        except Exception as e:
            logger.error(f"タイトル生成エラー: {str(e)}")
            return [base_title]
