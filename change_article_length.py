#!/usr/bin/env python3
"""
自動化の記事文字数を変更するスクリプト
"""
import sys
import re

def change_article_length(new_length):
    """文字数を変更"""
    try:
        # ファイルを読み込み
        with open('fully_autonomous.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # length=7000 の部分を置換
        pattern = r'(length=)\d+(,)'
        replacement = f'\\g<1>{new_length}\\g<2>'
        
        new_content = re.sub(pattern, replacement, content)
        
        # ファイルに書き戻し
        with open('fully_autonomous.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 文字数を {new_length} に変更しました")
        print("\n次のコマンドで自動化を再起動してください：")
        print("./stop_autonomous.sh && ./start_autonomous.sh")
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使い方: python change_article_length.py [文字数]")
        print("例: python change_article_length.py 5000")
        sys.exit(1)
    
    try:
        new_length = int(sys.argv[1])
        if new_length < 1000 or new_length > 20000:
            print("文字数は1000〜20000の範囲で指定してください")
            sys.exit(1)
        
        change_article_length(new_length)
    except ValueError:
        print("文字数は数値で指定してください")
        sys.exit(1)