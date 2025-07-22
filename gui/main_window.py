import tkinter as tk
from tkinter import ttk, messagebox, font
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.site_manager import SiteManager, Site
from gui.site_dialog import SiteDialog


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoBlogManager - WordPress自動化ツール")
        
        # ウィンドウサイズと位置設定
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # ウィンドウを画面中央に配置
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 1200) // 2
        y = (screen_height - 800) // 2
        self.root.geometry(f"1200x800+{x}+{y}")
        
        # フォント設定
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Noto Sans CJK JP", size=11)
        self.root.option_add("*Font", self.default_font)
        
        # スタイル設定
        style = ttk.Style()
        style.configure(".", font=("Noto Sans CJK JP", 11))
        style.configure("Heading.TLabel", font=("Noto Sans CJK JP", 13, "bold"))
        
        self.site_manager = SiteManager()
        
        self.setup_ui()
        self.refresh_site_list()
    
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ツールバー
        toolbar = ttk.Frame(main_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(toolbar, text="サイト追加", command=self.add_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="編集", command=self.edit_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="削除", command=self.delete_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="更新", command=self.refresh_site_list).pack(side=tk.LEFT, padx=5)
        
        # サイト一覧
        list_frame = ttk.LabelFrame(main_frame, text="サイト一覧", padding="10")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Treeview
        columns = ("name", "url", "genre", "target")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=20)
        
        self.tree.heading("#0", text="ID")
        self.tree.heading("name", text="サイト名")
        self.tree.heading("url", text="URL")
        self.tree.heading("genre", text="ジャンル")
        self.tree.heading("target", text="ターゲット")
        
        self.tree.column("#0", width=100)
        self.tree.column("name", width=200)
        self.tree.column("url", width=300)
        self.tree.column("genre", width=150)
        self.tree.column("target", width=150)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 実行パネル
        exec_frame = ttk.LabelFrame(main_frame, text="記事生成・投稿", padding="10")
        exec_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(exec_frame, text="記事数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.article_count_var = tk.StringVar(value="1")
        ttk.Spinbox(exec_frame, from_=1, to=10, textvariable=self.article_count_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Button(exec_frame, text="記事生成", command=self.generate_articles).grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(exec_frame, text="記事投稿", command=self.publish_articles).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 進行状況
        self.progress_var = tk.StringVar(value="待機中")
        ttk.Label(exec_frame, textvariable=self.progress_var).grid(row=3, column=0, columnspan=2, pady=10)
        
        self.progress_bar = ttk.Progressbar(exec_frame, mode='indeterminate')
        self.progress_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 設定の重み
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def refresh_site_list(self):
        # ツリービューをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # サイトを再読み込み
        self.site_manager.load_sites()
        
        # サイトを表示
        for site in self.site_manager.get_all_sites():
            self.tree.insert("", "end", text=site.site_id,
                           values=(site.name, site.url, site.genre, site.target_audience))
    
    def add_site(self):
        dialog = SiteDialog(self.root, "サイト追加", self.site_manager)
        if dialog.result:
            self.refresh_site_list()
            messagebox.showinfo("成功", "サイトを追加しました。")
    
    def edit_site(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集するサイトを選択してください。")
            return
        
        site_id = self.tree.item(selected[0])["text"]
        site = self.site_manager.get_site_by_id(site_id)
        
        if site:
            dialog = SiteDialog(self.root, "サイト編集", self.site_manager, site)
            if dialog.result:
                self.refresh_site_list()
                messagebox.showinfo("成功", "サイトを更新しました。")
    
    def delete_site(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "削除するサイトを選択してください。")
            return
        
        site_id = self.tree.item(selected[0])["text"]
        site = self.site_manager.get_site_by_id(site_id)
        
        if site and messagebox.askyesno("確認", f"サイト「{site.name}」を削除しますか？"):
            if self.site_manager.delete_site(site_id):
                self.refresh_site_list()
                messagebox.showinfo("成功", "サイトを削除しました。")
            else:
                messagebox.showerror("エラー", "サイトの削除に失敗しました。")
    
    def generate_articles(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "記事を生成するサイトを選択してください。")
            return
        
        self.progress_var.set("記事生成中...")
        self.progress_bar.start()
        
        # TODO: 記事生成機能の実装
        messagebox.showinfo("情報", "記事生成機能は後で実装されます。")
        
        self.progress_bar.stop()
        self.progress_var.set("待機中")
    
    def publish_articles(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "記事を投稿するサイトを選択してください。")
            return
        
        self.progress_var.set("記事投稿中...")
        self.progress_bar.start()
        
        # TODO: 記事投稿機能の実装
        messagebox.showinfo("情報", "記事投稿機能は後で実装されます。")
        
        self.progress_bar.stop()
        self.progress_var.set("待機中")