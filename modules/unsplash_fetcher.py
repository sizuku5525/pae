"""
Unsplash API画像取得モジュール
記事内容に基づいて関連画像を自動取得
"""
import requests
import os
from typing import Optional, Dict, List
import logging
import random
from .image_history_manager import ImageHistoryManager

logger = logging.getLogger(__name__)


class UnsplashFetcher:
    """Unsplash画像取得クラス"""
    
    def __init__(self, access_key: Optional[str] = None):
        """
        初期化
        
        Args:
            access_key: Unsplash Access Key
        """
        self.access_key = access_key or os.getenv('UNSPLASH_ACCESS_KEY')
        
        if not self.access_key:
            try:
                import json
                with open('config/api_keys.json', 'r') as f:
                    api_config = json.load(f)
                    self.access_key = api_config.get('unsplash', {}).get('access_key', '')
            except:
                pass
        
        self.base_url = "https://api.unsplash.com"
        self.headers = {
            "Authorization": f"Client-ID {self.access_key}"
        } if self.access_key else {}
    
    def is_configured(self) -> bool:
        """
        API設定が完了しているか確認
        
        Returns:
            設定済みの場合True
        """
        return bool(self.access_key)
    
    def search_photo(self, 
                    query: str, 
                    per_page: int = 10,
                    orientation: str = "landscape") -> Optional[Dict]:
        """
        キーワードで画像を検索
        
        Args:
            query: 検索キーワード
            per_page: 取得件数
            orientation: 画像の向き (landscape, portrait, squarish)
            
        Returns:
            画像情報の辞書、失敗時None
        """
        if not self.is_configured():
            logger.warning("Unsplash APIキーが設定されていません")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/search/photos",
                headers=self.headers,
                params={
                    "query": query,
                    "per_page": per_page,
                    "orientation": orientation,
                    "order_by": "relevant"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    # ランダムに1つ選択
                    photo = random.choice(data['results'])
                    return self._format_photo_data(photo)
            else:
                logger.error(f"Unsplash検索エラー: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Unsplash APIエラー: {str(e)}")
        
        return None
    
    def get_photo_for_article(self, 
                             title: str,
                             keywords: List[str] = None,
                             content: str = "") -> Optional[Dict]:
        """
        記事に適した画像を取得
        
        Args:
            title: 記事タイトル
            keywords: キーワードリスト
            content: 記事内容（キーワード抽出用）
            
        Returns:
            画像情報の辞書
        """
        # 検索キーワードを決定
        search_terms = []
        
        # キーワードから
        if keywords:
            search_terms.extend(keywords[:3])  # 最大3個
        
        # タイトルから重要な単語を抽出
        title_words = self._extract_keywords_from_text(title)
        search_terms.extend(title_words[:2])
        
        # 日本語の副業関連キーワードマッピング
        keyword_mapping = {
            '副業': 'side business laptop',
            'ブログ': 'blogging writing',
            'AI': 'artificial intelligence technology',
            '稼ぐ': 'earning money',
            '初心者': 'beginner learning',
            'アフィリエイト': 'affiliate marketing',
            '在宅': 'work from home',
            'ネット': 'internet online'
        }
        
        # 英語キーワードに変換
        english_terms = []
        for term in search_terms:
            if term in keyword_mapping:
                english_terms.append(keyword_mapping[term])
            else:
                # デフォルトで business/work 関連の画像を検索
                english_terms.append('business')
        
        # 検索実行
        for term in english_terms:
            result = self.search_photo(term)
            if result:
                logger.info(f"画像取得成功: {term}")
                return result
        
        # フォールバック：一般的なビジネス画像
        return self.search_photo("business technology")
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """
        テキストから重要なキーワードを抽出
        
        Args:
            text: テキスト
            
        Returns:
            キーワードリスト
        """
        # 重要な単語リスト
        important_words = [
            '副業', 'ブログ', 'AI', '稼ぐ', '初心者', 
            'アフィリエイト', '在宅', 'ネット', '収入',
            'ビジネス', 'マーケティング', 'SEO'
        ]
        
        keywords = []
        for word in important_words:
            if word in text:
                keywords.append(word)
        
        return keywords
    
    def _format_photo_data(self, photo: Dict) -> Dict:
        """
        写真データを整形
        
        Args:
            photo: Unsplash APIのレスポンス
            
        Returns:
            整形済み画像データ
        """
        return {
            'id': photo['id'],
            'url': photo['urls']['regular'],
            'thumb_url': photo['urls']['thumb'],
            'download_url': photo['urls']['full'],
            'width': photo['width'],
            'height': photo['height'],
            'description': photo.get('description', ''),
            'alt_description': photo.get('alt_description', ''),
            'photographer': photo['user']['name'],
            'photographer_url': photo['user']['links']['html'],
            'unsplash_url': photo['links']['html'],
            'attribution': f'Photo by {photo["user"]["name"]} on Unsplash'
        }
    
    def download_photo(self, photo_id: str) -> bool:
        """
        写真のダウンロード通知（Unsplash API要件）
        
        Args:
            photo_id: 写真ID
            
        Returns:
            成功時True
        """
        if not self.is_configured():
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/photos/{photo_id}/download",
                headers=self.headers
            )
            return response.status_code == 200
        except:
            return False