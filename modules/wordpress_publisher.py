"""
WordPress自動投稿モジュール
WordPress REST APIを使用して記事を自動投稿
"""
import requests
import base64
import json
from typing import Dict, Optional, List
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """WordPress投稿管理クラス"""
    
    def __init__(self, site_url: str, username: str, app_password: str):
        """
        初期化
        
        Args:
            site_url: WordPressサイトのURL
            username: WordPressユーザー名
            app_password: アプリケーションパスワード
        """
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        
        # 認証ヘッダーを作成
        credentials = f"{username}:{app_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        # APIエンドポイント
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
    
    def test_connection(self) -> bool:
        """
        WordPress接続をテスト
        
        Returns:
            接続成功時True
        """
        try:
            # カテゴリエンドポイントで接続テスト（認証不要）
            response = requests.get(
                f"{self.api_base}/categories",
                headers=self.headers,
                params={'per_page': 1},
                timeout=10
            )
            if response.status_code == 200:
                return True
                
            # 認証が必要なエンドポイントも試す
            response = requests.get(
                f"{self.api_base}/users/me",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"WordPress接続エラー: {str(e)}")
            return False
    
    def get_categories(self) -> List[Dict]:
        """
        カテゴリ一覧を取得
        
        Returns:
            カテゴリのリスト
        """
        try:
            response = requests.get(
                f"{self.api_base}/categories",
                headers=self.headers,
                params={'per_page': 100}
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"カテゴリ取得エラー: {str(e)}")
            return []
    
    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """
        カテゴリを取得または作成
        
        Args:
            category_name: カテゴリ名
            
        Returns:
            カテゴリID
        """
        # 既存のカテゴリを検索
        categories = self.get_categories()
        for cat in categories:
            if cat['name'] == category_name:
                return cat['id']
        
        # 新規作成
        try:
            response = requests.post(
                f"{self.api_base}/categories",
                headers=self.headers,
                json={'name': category_name}
            )
            if response.status_code in [200, 201]:
                return response.json()['id']
        except Exception as e:
            logger.error(f"カテゴリ作成エラー: {str(e)}")
        
        return None
    
    def upload_media(self, image_url: str, alt_text: str = "") -> Optional[int]:
        """
        画像をメディアライブラリにアップロード
        
        Args:
            image_url: 画像URL
            alt_text: 代替テキスト
            
        Returns:
            メディアID
        """
        try:
            # 画像をダウンロード
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                return None
            
            # ファイル名を生成
            filename = f"image_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            
            # WordPressにアップロード
            headers = self.headers.copy()
            headers['Content-Type'] = 'image/jpeg'
            headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            response = requests.post(
                f"{self.api_base}/media",
                headers=headers,
                data=image_response.content
            )
            
            if response.status_code in [200, 201]:
                media_id = response.json()['id']
                
                # 代替テキストを設定
                if alt_text:
                    requests.post(
                        f"{self.api_base}/media/{media_id}",
                        headers=self.headers,
                        json={'alt_text': alt_text}
                    )
                
                return media_id
                
        except Exception as e:
            logger.error(f"画像アップロードエラー: {str(e)}")
        
        return None
    
    def publish_post(self, 
                    title: str,
                    content: str,
                    excerpt: str = "",
                    categories: List[int] = None,
                    tags: List[str] = None,
                    featured_media_id: Optional[int] = None,
                    status: str = "publish") -> Optional[Dict]:
        """
        記事を投稿
        
        Args:
            title: 記事タイトル
            content: 記事本文（HTML）
            excerpt: 抜粋
            categories: カテゴリIDのリスト
            tags: タグのリスト
            featured_media_id: アイキャッチ画像ID
            status: 投稿ステータス（publish, draft, private）
            
        Returns:
            投稿結果の辞書、失敗時None
        """
        try:
            # マークダウンをHTMLに変換
            html_content = self._markdown_to_html(content)
            
            # 投稿データを構築
            post_data = {
                'title': title,
                'content': html_content,
                'excerpt': excerpt,
                'status': status,
                'comment_status': 'open',
                'ping_status': 'open'
            }
            
            # カテゴリを設定
            if categories:
                post_data['categories'] = categories
            
            # タグを設定
            if tags:
                tag_ids = []
                for tag_name in tags:
                    tag_id = self._get_or_create_tag(tag_name)
                    if tag_id:
                        tag_ids.append(tag_id)
                if tag_ids:
                    post_data['tags'] = tag_ids
            
            # アイキャッチ画像を設定
            if featured_media_id:
                post_data['featured_media'] = featured_media_id
            
            # 投稿
            response = requests.post(
                f"{self.api_base}/posts",
                headers=self.headers,
                json=post_data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"記事投稿成功: {result['link']}")
                return {
                    'id': result['id'],
                    'link': result['link'],
                    'title': result['title']['rendered'],
                    'status': result['status']
                }
            else:
                logger.error(f"投稿エラー: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"記事投稿エラー: {str(e)}")
        
        return None
    
    def _get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """
        タグを取得または作成
        
        Args:
            tag_name: タグ名
            
        Returns:
            タグID
        """
        try:
            # 既存のタグを検索
            response = requests.get(
                f"{self.api_base}/tags",
                headers=self.headers,
                params={'search': tag_name}
            )
            
            if response.status_code == 200:
                tags = response.json()
                for tag in tags:
                    if tag['name'] == tag_name:
                        return tag['id']
            
            # 新規作成
            response = requests.post(
                f"{self.api_base}/tags",
                headers=self.headers,
                json={'name': tag_name}
            )
            
            if response.status_code in [200, 201]:
                return response.json()['id']
                
        except Exception as e:
            logger.error(f"タグ作成エラー: {str(e)}")
        
        return None
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        マークダウンをHTMLに変換
        
        Args:
            markdown_text: マークダウンテキスト
            
        Returns:
            HTML
        """
        # 簡易的な変換（必要に応じてmarkdownライブラリを使用）
        html = markdown_text
        
        # 見出しを変換
        html = html.replace('### ', '<h3>')
        html = html.replace('## ', '<h2>')
        html = html.replace('# ', '<h1>')
        
        # 改行を追加
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('<h'):
                lines[i] = line + '</h' + line[2] + '>'
            elif line.strip():
                lines[i] = f'<p>{line}</p>'
        
        # リンクを変換
        import re
        html = '\n'.join(lines)
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
        
        # 太字を変換
        html = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', html)
        
        return html
    
    def upload_media_from_file(self, file_path: str, alt_text: str = "") -> Optional[int]:
        """
        ローカルファイルから画像をアップロード
        
        Args:
            file_path: アップロードするファイルのパス
            alt_text: 代替テキスト
            
        Returns:
            メディアID、失敗時はNone
        """
        try:
            # ファイルを読み込む
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # ファイル名を取得
            file_name = os.path.basename(file_path)
            
            # Content-Typeを判定
            content_type = 'image/jpeg'
            if file_name.lower().endswith('.png'):
                content_type = 'image/png'
            elif file_name.lower().endswith('.webp'):
                content_type = 'image/webp'
            
            # WordPressにアップロード
            headers = {
                **self.headers,
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{file_name}"'
            }
            
            response = requests.post(
                f"{self.api_base}/media",
                headers=headers,
                data=file_data
            )
            
            if response.status_code in [200, 201]:
                media = response.json()
                media_id = media['id']
                
                # altテキストを設定
                if alt_text:
                    update_data = {
                        'alt_text': alt_text,
                        'caption': alt_text
                    }
                    requests.post(
                        f"{self.api_base}/media/{media_id}",
                        headers=self.headers,
                        json=update_data
                    )
                
                logger.info(f"メディアアップロード成功: {media_id}")
                return media_id
            else:
                logger.error(f"メディアアップロードエラー: {response.status_code}")
                
        except Exception as e:
            logger.error(f"ファイルアップロードエラー: {str(e)}")
        
        return None