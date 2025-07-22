"""
カテゴリ自動選択モジュール
記事の内容に基づいて最適なカテゴリを選択
"""
import re
from typing import List, Dict, Optional


class CategorySelector:
    """記事内容に基づいてカテゴリを自動選択"""
    
    def __init__(self):
        # カテゴリごとのキーワードマッピング
        self.category_keywords = {
            'ブログ・アフィリエイト副業': [
                'ブログ', 'アフィリエイト', 'SEO', '記事', '執筆', 'WordPress',
                'コンテンツ', 'ライティング', 'アドセンス', 'ASP', '収益化'
            ],
            'ネット副業・在宅ワーク': [
                '在宅', 'リモート', 'オンライン', 'ネット副業', '在宅ワーク',
                'テレワーク', 'クラウドソーシング', '副業', 'ネットビジネス'
            ],
            'スキル販売・フリーランス': [
                'スキル', 'フリーランス', 'ココナラ', 'クラウドワークス', 'ランサーズ',
                'スキルシェア', '個人事業', '独立', 'フリーランサー'
            ],
            '動画編集・コンテンツ制作': [
                '動画', 'YouTube', '編集', 'コンテンツ', '制作', 'クリエイター',
                '映像', 'Premier', 'After Effects', '動画編集'
            ],
            '投資・資産運用': [
                '投資', '資産運用', '株', 'FX', '仮想通貨', '不動産',
                'NISA', 'iDeCo', '積立', '配当'
            ],
            '物販せどり副業': [
                'せどり', '転売', '物販', 'メルカリ', 'ヤフオク', 'Amazon',
                '仕入れ', '販売', 'ネットショップ', 'EC'
            ],
            '副業の税金・確定申告': [
                '税金', '確定申告', '税務', '節税', '経費', '控除',
                '税理士', '申告', '納税', '所得税'
            ]
        }
    
    def select_category(self, 
                       title: str, 
                       content: str, 
                       tags: List[str],
                       available_categories: List[Dict]) -> Optional[int]:
        """
        記事内容に基づいて最適なカテゴリを選択
        
        Args:
            title: 記事タイトル
            content: 記事本文
            tags: タグリスト
            available_categories: 利用可能なカテゴリリスト
            
        Returns:
            選択されたカテゴリID
        """
        # テキストを結合して小文字化
        full_text = f"{title} {content} {' '.join(tags)}".lower()
        
        # 各カテゴリのスコアを計算
        category_scores = {}
        
        for category in available_categories:
            category_name = category.get('name', '')
            category_id = category.get('id')
            
            if not category_name or not category_id:
                continue
            
            # このカテゴリのキーワードを取得
            keywords = self._get_keywords_for_category(category_name)
            
            # スコア計算
            score = 0
            for keyword in keywords:
                # タイトルでの出現は重み付けを高くする
                title_count = title.lower().count(keyword.lower())
                content_count = full_text.count(keyword.lower())
                
                score += title_count * 3  # タイトルは3倍の重み
                score += content_count
            
            # タグとの完全一致も考慮
            for tag in tags:
                if tag.lower() in [k.lower() for k in keywords]:
                    score += 5
            
            category_scores[category_id] = score
        
        # 最もスコアの高いカテゴリを選択
        if category_scores:
            selected_category_id = max(category_scores.items(), key=lambda x: x[1])[0]
            
            # スコアが0の場合はデフォルトカテゴリを使用
            if category_scores[selected_category_id] == 0:
                # "ブログ・アフィリエイト副業"をデフォルトとする
                for cat in available_categories:
                    if 'ブログ' in cat.get('name', ''):
                        return cat['id']
                # それもなければ最初のカテゴリ
                return available_categories[0]['id'] if available_categories else None
            
            return selected_category_id
        
        # カテゴリが見つからない場合
        return available_categories[0]['id'] if available_categories else None
    
    def _get_keywords_for_category(self, category_name: str) -> List[str]:
        """カテゴリ名から関連キーワードを取得"""
        # 完全一致を優先
        for key, keywords in self.category_keywords.items():
            if key in category_name or category_name in key:
                return keywords
        
        # 部分一致
        for key, keywords in self.category_keywords.items():
            key_parts = key.split('・')
            for part in key_parts:
                if part in category_name:
                    return keywords
        
        # デフォルト
        return []
    
    def analyze_content_theme(self, content: str) -> Dict[str, float]:
        """
        記事内容のテーマを分析
        
        Returns:
            各カテゴリの関連度スコア
        """
        theme_scores = {}
        content_lower = content.lower()
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                score += content_lower.count(keyword.lower())
            
            # 正規化（キーワード数で割る）
            if keywords:
                theme_scores[category] = score / len(keywords)
            else:
                theme_scores[category] = 0
        
        return theme_scores