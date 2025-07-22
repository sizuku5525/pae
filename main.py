#!/usr/bin/env python3
import tkinter as tk
from tkinter import font
import sys
import os

# モジュールパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    """メインエントリーポイント"""
    root = tk.Tk()
    
    # デフォルトフォント設定
    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(family="Noto Sans CJK JP", size=11)
    root.option_add("*Font", default_font)
    
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()