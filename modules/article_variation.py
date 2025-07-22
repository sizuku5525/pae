"""
記事のバリエーション生成モジュール
複数記事を生成する際の重複を防ぐ
"""
import random
from typing import List, Dict, Optional


class ArticleVariationGenerator:
    """記事のバリエーションを生成"""
    
    def __init__(self):
        # 記事の切り口リスト
        self.perspectives = [
            "初心者向け完全ガイド",
            "実践者が語る成功事例",
            "失敗から学ぶ注意点",
            "プロが教える上級テクニック",
            "コストパフォーマンス重視",
            "時間効率を最大化する方法",
            "よくある質問と回答集",
            "比較検証レポート",
            "最新トレンド解説",
            "実体験レビュー"
        ]
        
        # 記事構成のバリエーション
        self.structures = [
            "問題提起型（悩み→解決策）",
            "ストーリー型（体験談中心）",
            "データ分析型（数字で証明）",
            "ステップバイステップ型",
            "Q&A型（質問に答える）",
            "比較型（複数の選択肢）",
            "チェックリスト型",
            "事例紹介型",
            "理論解説型",
            "実践ガイド型"
        ]
        
        # フォーカスポイント
        self.focus_points = [
            "費用対効果",
            "時間短縮",
            "リスク回避",
            "収益最大化",
            "初期投資最小化",
            "スキル向上",
            "自動化・効率化",
            "安定性重視",
            "即効性重視",
            "長期的成長"
        ]
        
        # ターゲット層の細分化
        self.target_segments = [
            "完全初心者",
            "少し経験がある人",
            "中級者",
            "上級者",
            "忙しい会社員",
            "主婦・主夫",
            "学生",
            "シニア層",
            "フリーランス志望",
            "副業経験者"
        ]
    
    def generate_variation_prompt(self, base_topic: str, index: int, total_count: int) -> str:
        """
        記事のバリエーションプロンプトを生成
        
        Args:
            base_topic: 基本トピック
            index: 現在の記事番号（0から）
            total_count: 生成する記事の総数
            
        Returns:
            バリエーションプロンプト
        """
        # ランダムに要素を選択（ただし、indexをシードとして使用して一貫性を保つ）
        random.seed(index)
        
        perspective = random.choice(self.perspectives)
        structure = random.choice(self.structures)
        focus = random.choice(self.focus_points)
        target = random.choice(self.target_segments)
        
        # 記事番号に応じて異なる角度を設定
        if total_count > 1:
            angle_variations = [
                "基礎編",
                "実践編",
                "応用編",
                "トラブルシューティング編",
                "最新情報編"
            ]
            angle = angle_variations[index % len(angle_variations)]
        else:
            angle = ""
        
        variation_prompt = f"""
【この記事の独自性】
- 切り口: {perspective}
- 構成: {structure}
- フォーカス: {focus}
- メインターゲット: {target}
{f'- シリーズ: {angle}' if angle else ''}

【差別化のポイント】
- 他の記事とは異なる視点から{base_topic}を解説してください
- {target}の悩みに特化した内容にしてください
- {focus}を重視した実践的なアドバイスを含めてください
- {structure}の形式で記事を構成してください

【重要】
- 同じトピックでも、この記事独自の価値を提供してください
- 具体的な事例や数字は、この切り口に合わせて選んでください
- タイトルも上記の特徴を反映させてください
"""
        
        return variation_prompt
    
    def get_unique_keywords(self, base_keywords: List[str], index: int) -> List[str]:
        """
        記事ごとに異なるキーワードセットを生成
        
        Args:
            base_keywords: 基本キーワードリスト
            index: 記事番号
            
        Returns:
            ユニークなキーワードリスト
        """
        # 追加キーワードのプール
        additional_keywords = {
            0: ["入門", "基本", "始め方", "初心者"],
            1: ["コツ", "ポイント", "効率化", "時短"],
            2: ["失敗例", "注意点", "リスク", "対策"],
            3: ["成功事例", "実例", "体験談", "レビュー"],
            4: ["最新", "トレンド", "2024年版", "新常識"]
        }
        
        # 基本キーワードに追加キーワードを組み合わせる
        unique_keywords = base_keywords.copy()
        extra_keywords = additional_keywords.get(index % 5, [])
        
        # ランダムに2つ追加
        random.seed(index)
        selected_extras = random.sample(extra_keywords, min(2, len(extra_keywords)))
        unique_keywords.extend(selected_extras)
        
        return unique_keywords
    
    def get_article_length_variation(self, base_length: int, index: int) -> int:
        """
        記事ごとに少し異なる文字数を設定
        
        Args:
            base_length: 基本文字数
            index: 記事番号
            
        Returns:
            調整された文字数
        """
        # ±20%の範囲で変動
        variations = [0.8, 0.9, 1.0, 1.1, 1.2]
        multiplier = variations[index % len(variations)]
        
        return int(base_length * multiplier)