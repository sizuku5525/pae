import tkinter as tk
from tkinter import ttk, messagebox, font
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.site_manager import Site, SiteManager


class SiteDialog:
    def __init__(self, parent, title, site_manager: SiteManager, site: Site = None):
        self.result = False
        self.site_manager = site_manager
        self.site = site
        
        # ダイアログウィンドウ
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # フォント設定
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Noto Sans CJK JP", size=11)
        self.dialog.option_add("*Font", self.default_font)
        
        # 変数
        self.name_var = tk.StringVar(value=site.name if site else "")
        self.url_var = tk.StringVar(value=site.url if site else "")
        self.genre_var = tk.StringVar(value=site.genre if site else "")
        self.target_var = tk.StringVar(value=site.target_audience if site else "")
        self.monetization_var = tk.StringVar(value=site.monetization_policy if site else "")
        self.username_var = tk.StringVar(value=site.wordpress_username if site else "")
        self.password_var = tk.StringVar(value=site.wordpress_app_password if site else "")
        
        self.setup_ui()
        
        # ウィンドウを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # モーダルダイアログとして待機
        self.dialog.wait_window()
    
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 基本情報
        ttk.Label(main_frame, text="基本情報", font=("Noto Sans CJK JP", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(main_frame, text="サイト名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="URL:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.url_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="ジャンル:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.genre_var, width=40).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="ターゲット読者:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.target_var, width=40).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="収益化方針:").grid(row=5, column=0, sticky=tk.W, pady=5)
        monetization_text = tk.Text(main_frame, width=40, height=3, font=("Noto Sans CJK JP", 11))
        monetization_text.grid(row=5, column=1, sticky=tk.W, pady=5)
        monetization_text.insert(1.0, self.monetization_var.get())
        self.monetization_text = monetization_text
        
        # WordPress API情報
        ttk.Label(main_frame, text="WordPress API設定", font=("Noto Sans CJK JP", 13, "bold")).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(20, 10))
        
        ttk.Label(main_frame, text="ユーザー名:").grid(row=7, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.username_var, width=40).grid(row=7, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="アプリパスワード:").grid(row=8, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.password_var, width=40, show="*").grid(row=8, column=1, sticky=tk.W, pady=5)
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="保存", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # グリッドの設定
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
    
    def save(self):
        # 入力検証
        if not self.name_var.get().strip():
            messagebox.showerror("エラー", "サイト名を入力してください。")
            return
        
        if not self.url_var.get().strip():
            messagebox.showerror("エラー", "URLを入力してください。")
            return
        
        # URLの形式を確認
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_var.set(url)
        
        # 収益化方針をテキストウィジェットから取得
        monetization = self.monetization_text.get(1.0, tk.END).strip()
        
        # サイトオブジェクトを作成または更新
        if self.site:
            # 既存サイトの更新
            updated_site = Site(
                site_id=self.site.site_id,
                name=self.name_var.get().strip(),
                url=url,
                genre=self.genre_var.get().strip(),
                target_audience=self.target_var.get().strip(),
                monetization_policy=monetization,
                wordpress_username=self.username_var.get().strip(),
                wordpress_app_password=self.password_var.get().strip()
            )
            if self.site_manager.update_site(self.site.site_id, updated_site):
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("エラー", "サイトの更新に失敗しました。")
        else:
            # 新規サイトの追加
            new_site = Site(
                site_id=self.site_manager.generate_site_id(),
                name=self.name_var.get().strip(),
                url=url,
                genre=self.genre_var.get().strip(),
                target_audience=self.target_var.get().strip(),
                monetization_policy=monetization,
                wordpress_username=self.username_var.get().strip(),
                wordpress_app_password=self.password_var.get().strip()
            )
            if self.site_manager.add_site(new_site):
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("エラー", "サイトの追加に失敗しました。")
    
    def cancel(self):
        self.dialog.destroy()