import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class Site:
    def __init__(self, site_id: str, name: str, url: str, genre: str = "",
                 target_audience: str = "", monetization_policy: str = "",
                 wordpress_username: str = "", wordpress_app_password: str = "",
                 site_purpose: str = "", content_guidelines: str = "",
                 keywords_focus: str = "", avoid_topics: str = "",
                 genre_details: str = "", target_details: str = "",
                 ai_model: str = "gpt-4-1106-preview", affiliate_programs: List[str] = None,
                 custom_prompt: str = "", cta_link: str = "", cta_description: str = "",
                 cta_links: List[Dict] = None, categories: List[Dict] = None,
                 content_tone: str = "", content_rules: str = "",
                 image_service: str = "auto", image_style: str = "photorealistic", 
                 image_tone: str = "", image_instructions: str = "",
                 image_size: str = "1792x1024", image_quality: str = "8K, ultra detailed, high resolution",
                 image_avoid_terms: str = "low quality, blurry, distorted"):
        self.site_id = site_id
        self.name = name
        self.url = url
        self.genre = genre
        self.target_audience = target_audience
        self.monetization_policy = monetization_policy
        self.wordpress_username = wordpress_username
        self.wordpress_app_password = wordpress_app_password
        self.site_purpose = site_purpose  # サイトの目的・ミッション
        self.content_guidelines = content_guidelines  # コンテンツ作成ガイドライン
        self.keywords_focus = keywords_focus  # 重点キーワード
        self.avoid_topics = avoid_topics  # 避けるべきトピック
        self.genre_details = genre_details  # ジャンルの詳細説明
        self.target_details = target_details  # ターゲット読者の詳細説明
        self.ai_model = ai_model  # 使用するAIモデル (claude/venice)
        self.affiliate_programs = affiliate_programs or []  # 関連アフィリエイトプログラム
        self.custom_prompt = custom_prompt  # サイト別カスタムプロンプト
        self.cta_link = cta_link  # CTAリンク（旧形式との互換性）
        self.cta_description = cta_description  # CTAの説明（旧形式との互換性）
        self.cta_links = cta_links or []  # 複数のCTAリンク
        self.categories = categories or []  # WordPressカテゴリリスト
        self.content_tone = content_tone  # トーン・文体の指定
        self.content_rules = content_rules  # 記事作成ルール・決め事
        self.image_service = image_service  # 画像生成サービス
        self.image_style = image_style  # 画像スタイル
        self.image_tone = image_tone  # 画像のトーン・雰囲気
        self.image_instructions = image_instructions  # 画像生成の追加指示
        self.image_size = image_size  # 画像サイズ
        self.image_quality = image_quality  # 画質設定
        self.image_avoid_terms = image_avoid_terms  # 回避用語
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        
        # 旧形式のCTAリンクを新形式に変換
        if cta_link and not cta_links:
            self.cta_links = [{
                'url': cta_link,
                'description': cta_description,
                'keywords': '',
                'target_article_type': 'all'
            }]
    
    def to_dict(self) -> Dict:
        return {
            "site_id": self.site_id,
            "name": self.name,
            "url": self.url,
            "genre": self.genre,
            "target_audience": self.target_audience,
            "monetization_policy": self.monetization_policy,
            "wordpress_username": self.wordpress_username,
            "wordpress_app_password": self.wordpress_app_password,
            "site_purpose": self.site_purpose,
            "content_guidelines": self.content_guidelines,
            "keywords_focus": self.keywords_focus,
            "avoid_topics": self.avoid_topics,
            "genre_details": self.genre_details,
            "target_details": self.target_details,
            "ai_model": self.ai_model,
            "affiliate_programs": self.affiliate_programs,
            "custom_prompt": self.custom_prompt,
            "cta_link": self.cta_link,
            "cta_description": self.cta_description,
            "cta_links": self.cta_links,
            "categories": self.categories,
            "content_tone": self.content_tone,
            "content_rules": self.content_rules,
            "image_service": self.image_service,
            "image_style": self.image_style,
            "image_tone": self.image_tone,
            "image_instructions": self.image_instructions,
            "image_size": self.image_size,
            "image_quality": self.image_quality,
            "image_avoid_terms": self.image_avoid_terms,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Site':
        site = cls(
            site_id=data["site_id"],
            name=data["name"],
            url=data["url"],
            genre=data.get("genre", ""),
            target_audience=data.get("target_audience", ""),
            monetization_policy=data.get("monetization_policy", ""),
            wordpress_username=data.get("wordpress_username", ""),
            wordpress_app_password=data.get("wordpress_app_password", ""),
            site_purpose=data.get("site_purpose", ""),
            content_guidelines=data.get("content_guidelines", ""),
            keywords_focus=data.get("keywords_focus", ""),
            avoid_topics=data.get("avoid_topics", ""),
            genre_details=data.get("genre_details", ""),
            target_details=data.get("target_details", ""),
            ai_model=data.get("ai_model", "gpt-4-1106-preview"),
            affiliate_programs=data.get("affiliate_programs", []),
            custom_prompt=data.get("custom_prompt", ""),
            cta_link=data.get("cta_link", ""),
            cta_description=data.get("cta_description", ""),
            cta_links=data.get("cta_links", []),
            categories=data.get("categories", []),
            content_tone=data.get("content_tone", ""),
            content_rules=data.get("content_rules", ""),
            image_service=data.get("image_service", "auto"),
            image_style=data.get("image_style", "photorealistic"),
            image_tone=data.get("image_tone", ""),
            image_instructions=data.get("image_instructions", ""),
            image_size=data.get("image_size", "1792x1024"),
            image_quality=data.get("image_quality", "8K, ultra detailed, high resolution"),
            image_avoid_terms=data.get("image_avoid_terms", "low quality, blurry, distorted")
        )
        site.created_at = data.get("created_at", site.created_at)
        site.updated_at = data.get("updated_at", site.updated_at)
        return site


class SiteManager:
    def __init__(self, config_path: str = "config/sites.json"):
        self.config_path = config_path
        self.sites: List[Site] = []
        self.load_sites()
    
    def load_sites(self):
        """設定ファイルからサイト情報を読み込む"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sites = [Site.from_dict(site_data) for site_data in data.get("sites", [])]
            except Exception as e:
                print(f"サイト設定の読み込みエラー: {e}")
                self.sites = []
        else:
            self.sites = []
    
    def save_sites(self):
        """サイト情報を設定ファイルに保存"""
        try:
            data = {
                "sites": [site.to_dict() for site in self.sites]
            }
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"サイト設定の保存エラー: {e}")
            return False
    
    def add_site(self, site: Site) -> bool:
        """新しいサイトを追加"""
        if self.get_site_by_id(site.site_id):
            return False
        
        self.sites.append(site)
        return self.save_sites()
    
    def update_site(self, site_id: str, updated_site: Site) -> bool:
        """既存のサイトを更新"""
        for i, site in enumerate(self.sites):
            if site.site_id == site_id:
                updated_site.created_at = site.created_at
                updated_site.updated_at = datetime.now().isoformat()
                self.sites[i] = updated_site
                return self.save_sites()
        return False
    
    def delete_site(self, site_id: str) -> bool:
        """サイトを削除"""
        original_count = len(self.sites)
        self.sites = [site for site in self.sites if site.site_id != site_id]
        
        if len(self.sites) < original_count:
            return self.save_sites()
        return False
    
    def get_site_by_id(self, site_id: str) -> Optional[Site]:
        """IDでサイトを取得"""
        for site in self.sites:
            if site.site_id == site_id:
                return site
        return None
    
    def get_all_sites(self) -> List[Site]:
        """すべてのサイトを取得"""
        return self.sites
    
    def generate_site_id(self) -> str:
        """新しいサイトIDを生成"""
        import uuid
        return str(uuid.uuid4())[:8]
