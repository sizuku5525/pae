"""
画像生成統合管理システム
Google Gemini 2.0とGPT Image 1による自動画像生成
"""
import json
import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageGenerationManager:
    """画像生成統合管理クラス"""
    
    def __init__(self, config_path: str = "config/image_apis.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.preference_manager = UserPreferenceManager()
        self.selection_engine = AutoSelectionEngine(self.config)
        self.prompt_generator = PromptGenerator()
        
        # 各APIクライアントの初期化
        self._init_api_clients()
        
    def _load_config(self) -> Dict:
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定を返す"""
        return {
            "image_generation": {
                "enabled": True,
                "auto_selection_mode": True,
                "primary_service": "gemini_image",
                "secondary_service": "gpt_image",
                "fallback_service": "unsplash"
            }
        }
    
    def _init_api_clients(self):
        """APIクライアントを初期化"""
        self.gemini_client = None
        self.gpt_client = None
        self.unsplash_client = None
        
        # Gemini API初期化
        if self.config.get('image_generation', {}).get('gemini_image', {}).get('api_key'):
            try:
                self.gemini_client = GeminiImageAPI(
                    self.config['image_generation']['gemini_image']['api_key']
                )
            except Exception as e:
                logger.error(f"Gemini API初期化エラー: {str(e)}")
        
        # GPT Image API初期化
        if self.config.get('image_generation', {}).get('gpt_image', {}).get('api_key'):
            try:
                self.gpt_client = GPTImageAPI(
                    self.config['image_generation']['gpt_image']['api_key']
                )
            except Exception as e:
                logger.error(f"GPT Image API初期化エラー: {str(e)}")
    
    def generate_article_image(self, 
                             article_title: str, 
                             keywords: List[str], 
                             genre: str,
                             user_preference: Optional[str] = None) -> Optional[str]:
        """
        記事用画像を自動生成
        
        Args:
            article_title: 記事タイトル
            keywords: キーワードリスト
            genre: ジャンル
            user_preference: ユーザー指定のサービス
            
        Returns:
            画像パスまたはURL、失敗時はNone
        """
        if not self.config.get('image_generation', {}).get('enabled', True):
            logger.info("画像生成機能が無効です")
            return None
        
        # プロンプト生成
        prompt = self.prompt_generator.create_image_prompt(
            article_title, keywords, genre
        )
        
        # サービス選択
        if user_preference:
            selected_service = user_preference
        else:
            context = {
                'genre': genre,
                'keywords': keywords,
                'time': datetime.now(),
                'budget_status': self._get_budget_status()
            }
            selected_service = self.selection_engine.select_optimal_service(context)
        
        logger.info(f"選択されたサービス: {selected_service}")
        
        # 画像生成実行
        image_path = None
        success = False
        
        try:
            if selected_service == 'gemini_image' and self.gemini_client:
                image_path = self.gemini_client.generate(prompt)
                success = True
            elif selected_service == 'gpt_image' and self.gpt_client:
                image_path = self.gpt_client.generate(prompt)
                success = True
        except Exception as e:
            logger.error(f"{selected_service}での画像生成エラー: {str(e)}")
        
        # フォールバック処理
        if not success:
            logger.info("フォールバックサービスを試行中...")
            # ここでUnsplashなどのフォールバックを実行
            
        # 選択履歴を記録
        self.preference_manager.record_selection(
            genre, selected_service, datetime.now(), success
        )
        
        return image_path
    
    def _get_budget_status(self) -> Dict:
        """予算状況を取得"""
        # TODO: 実際の使用量とコストを計算
        return {
            'monthly_budget': self.config.get('image_generation', {}).get('monthly_budget', 50),
            'used': 10,  # 仮の値
            'remaining': 40
        }


class UserPreferenceManager:
    """ユーザー選択パターン管理クラス"""
    
    def __init__(self):
        self.preference_file = "data/user_image_preferences.json"
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> Dict:
        """選択履歴を読み込む"""
        os.makedirs(os.path.dirname(self.preference_file), exist_ok=True)
        if os.path.exists(self.preference_file):
            try:
                with open(self.preference_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {'selections': []}
        return {'selections': []}
    
    def record_selection(self, 
                        article_genre: str, 
                        selected_service: str, 
                        timestamp: datetime, 
                        success: bool):
        """ユーザーの選択を記録"""
        selection = {
            'genre': article_genre,
            'service': selected_service,
            'timestamp': timestamp.isoformat(),
            'success': success,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday()
        }
        
        self.preferences['selections'].append(selection)
        
        # 最新1000件のみ保持
        if len(self.preferences['selections']) > 1000:
            self.preferences['selections'] = self.preferences['selections'][-1000:]
        
        self._save_preferences()
    
    def _save_preferences(self):
        """選択履歴を保存"""
        with open(self.preference_file, 'w', encoding='utf-8') as f:
            json.dump(self.preferences, f, indent=2, ensure_ascii=False)
    
    def get_recommended_service(self, 
                               article_genre: str, 
                               current_time: datetime, 
                               budget_status: Dict) -> Optional[str]:
        """過去のパターンから推奨サービスを返す"""
        # ジャンル別の成功率を計算
        genre_stats = self._calculate_genre_stats(article_genre)
        
        # 時間帯別の成功率を計算
        hour_stats = self._calculate_hour_stats(current_time.hour)
        
        # 最も成功率の高いサービスを推奨
        recommendations = {}
        for service in ['gemini_image', 'gpt_image']:
            score = (genre_stats.get(service, 0.5) * 0.6 + 
                    hour_stats.get(service, 0.5) * 0.4)
            recommendations[service] = score
        
        # 予算が少ない場合はコスト優先
        if budget_status['remaining'] < budget_status['monthly_budget'] * 0.2:
            recommendations['gemini_image'] *= 1.2  # Geminiを優先
        
        return max(recommendations, key=recommendations.get)
    
    def _calculate_genre_stats(self, genre: str) -> Dict[str, float]:
        """ジャンル別の成功率を計算"""
        stats = {}
        genre_selections = [s for s in self.preferences['selections'] 
                          if s['genre'] == genre]
        
        for service in ['gemini_image', 'gpt_image']:
            service_selections = [s for s in genre_selections 
                                if s['service'] == service]
            if service_selections:
                success_rate = sum(1 for s in service_selections if s['success']) / len(service_selections)
                stats[service] = success_rate
            else:
                stats[service] = 0.5  # デフォルト値
        
        return stats
    
    def _calculate_hour_stats(self, hour: int) -> Dict[str, float]:
        """時間帯別の成功率を計算"""
        stats = {}
        # 前後2時間の範囲で計算
        hour_range = [(hour - 2 + i) % 24 for i in range(5)]
        hour_selections = [s for s in self.preferences['selections'] 
                         if s['hour'] in hour_range]
        
        for service in ['gemini_image', 'gpt_image']:
            service_selections = [s for s in hour_selections 
                                if s['service'] == service]
            if service_selections:
                success_rate = sum(1 for s in service_selections if s['success']) / len(service_selections)
                stats[service] = success_rate
            else:
                stats[service] = 0.5
        
        return stats
    
    def analyze_usage_pattern(self) -> Dict:
        """使用パターンを分析して最適化提案"""
        analysis = {
            'total_generations': len(self.preferences['selections']),
            'service_usage': {},
            'genre_preferences': {},
            'time_patterns': {},
            'recommendations': []
        }
        
        # サービス別使用率
        for service in ['gemini_image', 'gpt_image']:
            service_count = sum(1 for s in self.preferences['selections'] 
                              if s['service'] == service)
            analysis['service_usage'][service] = {
                'count': service_count,
                'percentage': service_count / len(self.preferences['selections']) if self.preferences['selections'] else 0
            }
        
        # ジャンル別推奨
        genres = set(s['genre'] for s in self.preferences['selections'])
        for genre in genres:
            genre_stats = self._calculate_genre_stats(genre)
            best_service = max(genre_stats, key=genre_stats.get)
            analysis['genre_preferences'][genre] = {
                'recommended_service': best_service,
                'success_rate': genre_stats[best_service]
            }
        
        return analysis


class AutoSelectionEngine:
    """自動選択エンジン"""
    
    def __init__(self, config: Dict):
        self.config = config.get('image_generation', {})
        self.rules = self.config.get('auto_selection_rules', {})
        self.user_prefs = self.config.get('user_preferences', {})
    
    def select_optimal_service(self, context: Dict) -> str:
        """
        最適なサービスを自動選択
        
        Args:
            context: 選択に必要なコンテキスト情報
            
        Returns:
            選択されたサービス名
        """
        scores = {}
        
        # 各サービスのスコアを計算
        for service in ['gemini_image', 'gpt_image']:
            scores[service] = self._calculate_service_score(service, context)
        
        # 最高スコアのサービスを選択
        selected = max(scores, key=scores.get)
        logger.info(f"サービススコア: {scores}")
        
        return selected
    
    def _calculate_service_score(self, service: str, context: Dict) -> float:
        """サービスのスコアを計算"""
        base_score = 50.0
        
        # ジャンル適合度
        genre = context.get('genre', '')
        if genre in self.rules.get(f'{genre}_articles', '').split(','):
            if self.rules.get(f'{genre}_articles') == service:
                base_score += 20
        
        # 予算考慮
        budget_status = context.get('budget_status', {})
        if budget_status.get('remaining', 50) < self.rules.get('budget_low_threshold', 10):
            if service == self.rules.get('budget_switch_service', 'gemini_image'):
                base_score += 15
        
        # 時間帯考慮
        current_hour = context.get('time', datetime.now()).hour
        if 9 <= current_hour <= 17 and service == 'gemini_image':
            base_score += 10  # 業務時間はGemini優先
        
        # サービス重み付け
        service_weight = self.config.get(service, {}).get('weight', 1.0)
        base_score *= service_weight
        
        return base_score


class PromptGenerator:
    """プロンプト自動生成クラス"""
    
    def __init__(self):
        self.style_templates = {
            'blog': "Professional blog header image about {topic}, clean modern design, no text, high quality photography",
            'business': "Business concept image for {topic}, corporate style, professional atmosphere, no text",
            'tech': "Technology themed image about {topic}, futuristic design, digital art style, no text",
            'lifestyle': "Lifestyle photography for {topic}, warm colors, natural lighting, no text"
        }
        # デフォルト設定（サイト設定で上書き可能）
        self.default_style = 'photorealistic'
        self.quality = '8K, ultra detailed, high resolution'
        self.additional_instructions = ''
        self.tone = ''
        self.avoid_terms = ['low quality', 'blurry', 'distorted']
    
    def create_image_prompt(self, 
                          title: str, 
                          keywords: List[str], 
                          genre: str) -> str:
        """
        記事内容を分析してプロンプト生成
        
        Args:
            title: 記事タイトル
            keywords: キーワードリスト
            genre: ジャンル
            
        Returns:
            生成されたプロンプト
        """
        # 基本トピックを抽出
        topic = self._extract_topic(title, keywords)
        
        # ジャンルに応じたテンプレート選択
        template = self.style_templates.get(genre, self.style_templates['blog'])
        
        # プロンプト生成
        prompt = template.format(topic=topic)
        
        # キーワードを追加
        if keywords:
            keyword_str = ", ".join(keywords[:3])  # 最大3つのキーワード
            prompt += f", featuring {keyword_str}"
        
        # スタイル設定を追加
        if self.default_style:
            prompt += f", {self.default_style}"
        
        # トーン設定を追加
        if self.tone:
            prompt += f", {self.tone}"
        
        # 品質設定を追加
        if self.quality:
            prompt += f", {self.quality}"
        
        # 追加指示を追加
        if self.additional_instructions:
            prompt += f", {self.additional_instructions}"
        
        # 回避用語を追加
        if self.avoid_terms:
            avoid_str = ", ".join(self.avoid_terms)
            prompt += f", avoid: {avoid_str}"
        
        logger.info(f"生成されたプロンプト: {prompt}")
        return prompt
    
    def _extract_topic(self, title: str, keywords: List[str]) -> str:
        """タイトルとキーワードからトピックを抽出"""
        # 簡易的な実装（実際はより高度な処理が必要）
        if keywords:
            return keywords[0]
        
        # タイトルから重要な単語を抽出
        # 日本語の場合は形態素解析が必要
        words = title.split()[:3]
        return " ".join(words)


class GeminiImageAPI:
    """Google Gemini 2.0 画像生成 API クライアント"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_base = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash-preview-image-generation"
        
        # 画像保存ディレクトリ
        self.image_dir = "static/generated_images/gemini"
        os.makedirs(self.image_dir, exist_ok=True)
    
    def generate(self, prompt: str) -> Optional[str]:
        """
        画像を生成
        
        Args:
            prompt: 画像生成プロンプト
            
        Returns:
            保存された画像のパス、失敗時はNone
        """
        try:
            url = f"{self.api_base}/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                    "response_modalities": ["TEXT", "IMAGE"]  # Correct parameter
                }
            }
            
            logger.info(f"Gemini APIで画像生成中: {prompt}")
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract image from response
                if 'candidates' in result and result['candidates']:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'inlineData' in part:
                                image_data = part['inlineData']['data']
                                mime_type = part['inlineData']['mimeType']
                                
                                # Save image
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                extension = mime_type.split('/')[-1] if '/' in mime_type else 'png'
                                filename = f"gemini_{timestamp}.{extension}"
                                image_path = os.path.join(self.image_dir, filename)
                                
                                # Decode and save
                                import base64
                                with open(image_path, 'wb') as f:
                                    f.write(base64.b64decode(image_data))
                                
                                logger.info(f"画像保存完了: {image_path}")
                                return image_path
                
                logger.error("Gemini API: 画像データが見つかりませんでした")
                return None
            else:
                logger.error(f"Gemini API エラー: HTTP {response.status_code} - {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"Gemini API エラー: {str(e)}")
            return None


class GPTImageAPI:
    """OpenAI GPT Image 1 API クライアント"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_base = "https://api.openai.com/v1"
        
        # 画像保存ディレクトリ
        self.image_dir = "static/generated_images/gpt"
        os.makedirs(self.image_dir, exist_ok=True)
    
    def generate(self, prompt: str) -> Optional[str]:
        """
        画像を生成
        
        Args:
            prompt: 画像生成プロンプト
            
        Returns:
            保存された画像のパス、失敗時はNone
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "dall-e-3",  # DALL-E 3 model
                "prompt": prompt,
                "size": "1792x1024",
                "quality": "standard",
                "n": 1
            }
            
            logger.info(f"GPT Image APIで画像生成中: {prompt}")
            
            response = requests.post(
                f"{self.api_base}/images/generations",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                image_url = result['data'][0]['url']
                
                # 画像をダウンロード
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = os.path.join(self.image_dir, f"gpt_{timestamp}.png")
                    
                    with open(image_path, 'wb') as f:
                        f.write(image_response.content)
                    
                    logger.info(f"画像保存完了: {image_path}")
                    return image_path
            
            logger.error(f"GPT Image API エラー: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"GPT Image API エラー: {str(e)}")
            return None