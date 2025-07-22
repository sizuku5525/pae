"""
アフィリエイト案件管理モジュール
各種アフィリエイトプログラムと案件を管理
"""
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AffiliateProgram:
    """アフィリエイトプログラムクラス"""
    
    def __init__(self, program_id: str, name: str, description: str = "",
                 commission_rate: str = "", cookie_duration: str = "",
                 payment_terms: str = "", notes: str = ""):
        self.program_id = program_id
        self.name = name
        self.description = description
        self.commission_rate = commission_rate
        self.cookie_duration = cookie_duration
        self.payment_terms = payment_terms
        self.notes = notes
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "commission_rate": self.commission_rate,
            "cookie_duration": self.cookie_duration,
            "payment_terms": self.payment_terms,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AffiliateProgram':
        program = cls(
            program_id=data["program_id"],
            name=data["name"],
            description=data.get("description", ""),
            commission_rate=data.get("commission_rate", ""),
            cookie_duration=data.get("cookie_duration", ""),
            payment_terms=data.get("payment_terms", ""),
            notes=data.get("notes", "")
        )
        program.created_at = data.get("created_at", program.created_at)
        program.updated_at = data.get("updated_at", program.updated_at)
        return program


class AffiliateProduct:
    """アフィリエイト案件（商品）クラス"""
    
    def __init__(self, product_id: str, program_id: str, name: str,
                 description: str = "", target_audience: str = "",
                 selling_points: str = "", price_range: str = "",
                 commission_details: str = "", link_url: str = "",
                 promotion_guidelines: str = "", avoid_expressions: str = "",
                 success_examples: str = "", notes: str = ""):
        self.product_id = product_id
        self.program_id = program_id
        self.name = name
        self.description = description  # 商品の詳細説明
        self.target_audience = target_audience  # ターゲット層の詳細
        self.selling_points = selling_points  # セールスポイント
        self.price_range = price_range  # 価格帯
        self.commission_details = commission_details  # 報酬詳細
        self.link_url = link_url  # アフィリエイトリンク
        self.promotion_guidelines = promotion_guidelines  # プロモーション指針
        self.avoid_expressions = avoid_expressions  # 避けるべき表現
        self.success_examples = success_examples  # 成功事例
        self.notes = notes  # その他メモ
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "product_id": self.product_id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "target_audience": self.target_audience,
            "selling_points": self.selling_points,
            "price_range": self.price_range,
            "commission_details": self.commission_details,
            "link_url": self.link_url,
            "promotion_guidelines": self.promotion_guidelines,
            "avoid_expressions": self.avoid_expressions,
            "success_examples": self.success_examples,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AffiliateProduct':
        product = cls(
            product_id=data["product_id"],
            program_id=data["program_id"],
            name=data["name"],
            description=data.get("description", ""),
            target_audience=data.get("target_audience", ""),
            selling_points=data.get("selling_points", ""),
            price_range=data.get("price_range", ""),
            commission_details=data.get("commission_details", ""),
            link_url=data.get("link_url", ""),
            promotion_guidelines=data.get("promotion_guidelines", ""),
            avoid_expressions=data.get("avoid_expressions", ""),
            success_examples=data.get("success_examples", ""),
            notes=data.get("notes", "")
        )
        product.created_at = data.get("created_at", product.created_at)
        product.updated_at = data.get("updated_at", product.updated_at)
        return product


class AffiliateManager:
    """アフィリエイト管理クラス"""
    
    def __init__(self, config_path: str = "config/affiliates.json"):
        self.config_path = config_path
        self.programs: List[AffiliateProgram] = []
        self.products: List[AffiliateProduct] = []
        self.load_data()
    
    def load_data(self):
        """設定ファイルからデータを読み込む"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.programs = [
                        AffiliateProgram.from_dict(p) 
                        for p in data.get("programs", [])
                    ]
                    self.products = [
                        AffiliateProduct.from_dict(p) 
                        for p in data.get("products", [])
                    ]
            except Exception as e:
                logger.error(f"アフィリエイトデータ読み込みエラー: {e}")
                self.programs = []
                self.products = []
        else:
            self.programs = []
            self.products = []
    
    def save_data(self):
        """データを設定ファイルに保存"""
        try:
            data = {
                "programs": [p.to_dict() for p in self.programs],
                "products": [p.to_dict() for p in self.products]
            }
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"アフィリエイトデータ保存エラー: {e}")
            return False
    
    # プログラム管理メソッド
    def add_program(self, program: AffiliateProgram) -> bool:
        """アフィリエイトプログラムを追加"""
        if self.get_program_by_id(program.program_id):
            return False
        
        self.programs.append(program)
        return self.save_data()
    
    def update_program(self, program_id: str, updated_program: AffiliateProgram) -> bool:
        """アフィリエイトプログラムを更新"""
        for i, program in enumerate(self.programs):
            if program.program_id == program_id:
                updated_program.created_at = program.created_at
                updated_program.updated_at = datetime.now().isoformat()
                self.programs[i] = updated_program
                return self.save_data()
        return False
    
    def delete_program(self, program_id: str) -> bool:
        """アフィリエイトプログラムを削除"""
        original_count = len(self.programs)
        self.programs = [p for p in self.programs if p.program_id != program_id]
        
        # 関連する商品も削除
        self.products = [p for p in self.products if p.program_id != program_id]
        
        if len(self.programs) < original_count:
            return self.save_data()
        return False
    
    def get_program_by_id(self, program_id: str) -> Optional[AffiliateProgram]:
        """IDでプログラムを取得"""
        for program in self.programs:
            if program.program_id == program_id:
                return program
        return None
    
    def get_all_programs(self) -> List[AffiliateProgram]:
        """すべてのプログラムを取得"""
        return self.programs
    
    # 商品管理メソッド
    def add_product(self, product: AffiliateProduct) -> bool:
        """アフィリエイト商品を追加"""
        if self.get_product_by_id(product.product_id):
            return False
        
        self.products.append(product)
        return self.save_data()
    
    def update_product(self, product_id: str, updated_product: AffiliateProduct) -> bool:
        """アフィリエイト商品を更新"""
        for i, product in enumerate(self.products):
            if product.product_id == product_id:
                updated_product.created_at = product.created_at
                updated_product.updated_at = datetime.now().isoformat()
                self.products[i] = updated_product
                return self.save_data()
        return False
    
    def delete_product(self, product_id: str) -> bool:
        """アフィリエイト商品を削除"""
        original_count = len(self.products)
        self.products = [p for p in self.products if p.product_id != product_id]
        
        if len(self.products) < original_count:
            return self.save_data()
        return False
    
    def get_product_by_id(self, product_id: str) -> Optional[AffiliateProduct]:
        """IDで商品を取得"""
        for product in self.products:
            if product.product_id == product_id:
                return product
        return None
    
    def get_products_by_program(self, program_id: str) -> List[AffiliateProduct]:
        """プログラムIDで商品を取得"""
        return [p for p in self.products if p.program_id == program_id]
    
    def get_all_products(self) -> List[AffiliateProduct]:
        """すべての商品を取得"""
        return self.products
    
    def get_products_for_site(self, site_info: Dict) -> List[AffiliateProduct]:
        """サイトに適した商品を取得"""
        # サイトのジャンルやターゲットに基づいて商品をフィルタリング
        suitable_products = []
        
        site_genre = site_info.get('genre', '').lower()
        site_target = site_info.get('target_audience', '').lower()
        site_keywords = site_info.get('keywords_focus', '').lower()
        
        for product in self.products:
            # 商品のターゲット層がサイトのターゲットと一致するかチェック
            product_target = product.target_audience.lower()
            
            # 簡単なマッチングロジック（実際はもっと高度にすべき）
            if (site_target in product_target or 
                product_target in site_target or
                any(keyword in product.description.lower() for keyword in site_keywords.split(','))):
                suitable_products.append(product)
        
        return suitable_products
    
    def generate_id(self) -> str:
        """新しいIDを生成"""
        import uuid
        return str(uuid.uuid4())[:8]