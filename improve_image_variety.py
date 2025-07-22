#!/usr/bin/env python3
"""
画像の多様性を改善する設定変更スクリプト
"""
import json
import random

def update_unsplash_settings():
    """Unsplash設定を更新して画像の多様性を増やす"""
    
    # 検索キーワードのバリエーション
    keyword_variations = {
        "副業": ["side business", "freelance", "work from home", "remote work", "entrepreneur"],
        "ビジネス": ["business", "office", "laptop", "workspace", "professional"],
        "AI": ["artificial intelligence", "technology", "computer", "innovation", "digital"],
        "初心者": ["beginner", "learning", "education", "start", "growth"],
        "お金": ["money", "finance", "investment", "savings", "income"],
        "成功": ["success", "achievement", "goal", "winner", "celebration"],
        "失敗": ["challenge", "problem solving", "thinking", "strategy", "planning"]
    }
    
    # 画像スタイルのバリエーション
    styles = ["modern", "minimal", "creative", "professional", "casual"]
    colors = ["blue", "green", "orange", "purple", "neutral"]
    
    print("画像の多様性を改善する方法：")
    print("\n1. 検索キーワードをランダム化")
    print("   例：'副業' → 'side business', 'freelance', 'work from home'など")
    
    print("\n2. 検索時にスタイルや色を追加")
    print("   例：'副業' → 'side business modern blue'")
    
    print("\n3. 取得枚数を増やして選択肢を拡大")
    print("   per_page: 10 → 30")
    
    print("\n4. ページ番号をランダム化")
    print("   page: random.randint(1, 5)")
    
    # サンプルコード
    print("\n=== 改善案のサンプルコード ===")
    print("""
# unsplash_fetcher.py の search_photo メソッドを修正：

def search_photo(self, query: str, per_page: int = 30, orientation: str = "landscape") -> Optional[Dict]:
    # キーワードにバリエーションを追加
    style = random.choice(['modern', 'minimal', 'creative', 'professional'])
    enhanced_query = f"{query} {style}"
    
    # ページ番号をランダム化
    page = random.randint(1, 5)
    
    params = {
        "query": enhanced_query,
        "per_page": per_page,
        "page": page,
        "orientation": orientation,
        "order_by": "relevant"
    }
    
    # 複数の画像から重み付けで選択
    if data['results']:
        # 最初の数枚は使用頻度を下げる
        weights = [0.1, 0.1, 0.2] + [1.0] * (len(data['results']) - 3)
        photo = random.choices(data['results'], weights=weights[:len(data['results'])])[0]
""")

if __name__ == "__main__":
    update_unsplash_settings()