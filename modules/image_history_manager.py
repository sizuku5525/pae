"""
画像使用履歴管理モジュール
重複画像の使用を防ぐ
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ImageHistoryManager:
    """画像使用履歴を管理"""
    
    def __init__(self, history_file: str = 'data/image_history.json'):
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """履歴を読み込む"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {'images': []}
        return {'images': []}
    
    def _save_history(self):
        """履歴を保存"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def add_used_image(self, image_id: str, image_url: str, 
                      site_id: str = None, article_id: str = None):
        """使用した画像を記録"""
        entry = {
            'image_id': image_id,
            'image_url': image_url,
            'used_at': datetime.now().isoformat(),
            'site_id': site_id,
            'article_id': article_id
        }
        
        self.history['images'].append(entry)
        self._save_history()
        
        # 古い履歴を削除（6ヶ月以上前）
        self._cleanup_old_history()
    
    def is_image_used_recently(self, image_id: str, days: int = 30) -> bool:
        """最近使用されたかチェック"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for entry in self.history['images']:
            if entry['image_id'] == image_id:
                used_date = datetime.fromisoformat(entry['used_at'])
                if used_date > cutoff_date:
                    return True
        
        return False
    
    def get_used_image_ids(self, days: int = 30, site_id: str = None) -> List[str]:
        """最近使用した画像IDのリストを取得"""
        cutoff_date = datetime.now() - timedelta(days=days)
        used_ids = []
        
        for entry in self.history['images']:
            used_date = datetime.fromisoformat(entry['used_at'])
            if used_date > cutoff_date:
                if site_id is None or entry.get('site_id') == site_id:
                    used_ids.append(entry['image_id'])
        
        return list(set(used_ids))  # 重複を除去
    
    def _cleanup_old_history(self, months: int = 6):
        """古い履歴を削除"""
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        self.history['images'] = [
            entry for entry in self.history['images']
            if datetime.fromisoformat(entry['used_at']) > cutoff_date
        ]
        
        self._save_history()
    
    def get_usage_stats(self) -> Dict:
        """使用統計を取得"""
        total = len(self.history['images'])
        last_30_days = len(self.get_used_image_ids(days=30))
        last_7_days = len(self.get_used_image_ids(days=7))
        
        return {
            'total_images_used': total,
            'last_30_days': last_30_days,
            'last_7_days': last_7_days,
            'unique_images': len(set(entry['image_id'] for entry in self.history['images']))
        }