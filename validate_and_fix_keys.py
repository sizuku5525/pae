#!/usr/bin/env python3
"""
APIキーの形式を検証し、必要に応じて修正する
"""
import json
import re

def validate_api_key_format(key, service):
    """APIキーの形式を検証"""
    if service == 'gemini':
        # Gemini: AIzaSy で始まる
        return key.startswith('AIzaSy')
    elif service == 'openai':
        # OpenAI: sk- で始まる
        return key.startswith('sk-')
    elif service == 'unsplash':
        # Unsplash: 特定の形式はないが、長い文字列
        return len(key) > 20
    return False

def check_and_fix_api_keys():
    """APIキーをチェックして修正"""
    config_file = 'config/image_apis.json'
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    image_gen = config.get('image_generation', {})
    
    # 現在のキーを取得
    gemini_key = image_gen.get('gemini_image', {}).get('api_key', '')
    openai_key = image_gen.get('gpt_image', {}).get('api_key', '')
    
    print("=== 現在のAPIキー検証 ===")
    print(f"Gemini key: {gemini_key[:20]}...")
    print(f"  形式チェック: {'✓ 正しい' if validate_api_key_format(gemini_key, 'gemini') else '✗ 間違い'}")
    
    print(f"\nOpenAI key: {openai_key[:20]}...")
    print(f"  形式チェック: {'✓ 正しい' if validate_api_key_format(openai_key, 'openai') else '✗ 間違い'}")
    
    # もしキーが入れ替わっていたら修正
    needs_swap = False
    if gemini_key.startswith('sk-') and openai_key.startswith('AIzaSy'):
        print("\n⚠️  警告: APIキーが入れ替わっています！")
        needs_swap = True
        
        # キーを交換
        image_gen['gemini_image']['api_key'] = openai_key
        image_gen['gpt_image']['api_key'] = gemini_key
        
        print("✓ キーを正しい位置に修正しました")
        
    elif not validate_api_key_format(gemini_key, 'gemini') and gemini_key:
        print(f"\n⚠️  警告: Geminiキーの形式が正しくありません: {gemini_key[:20]}...")
    
    elif not validate_api_key_format(openai_key, 'openai') and openai_key:
        print(f"\n⚠️  警告: OpenAIキーの形式が正しくありません: {openai_key[:20]}...")
    
    if needs_swap:
        # 保存
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("\n=== 修正後 ===")
        print(f"Gemini key: {image_gen['gemini_image']['api_key'][:20]}...")
        print(f"OpenAI key: {image_gen['gpt_image']['api_key'][:20]}...")

if __name__ == "__main__":
    check_and_fix_api_keys()