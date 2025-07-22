"""
軽量画像キャッシュ管理システム
メモリ効率を考慮した画像キャッシュ
"""
import os
import json
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import logging
from PIL import Image

logger = logging.getLogger(__name__)


class ImageCache:
    """軽量画像キャッシュ管理"""
    
    def __init__(self, cache_dir: str = "data/image_cache", max_size_gb: float = 1.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = int(max_size_gb * 1024 * 1024 * 1024)  # GB→Byte変換
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()
        
    def _load_index(self) -> Dict:
        """キャッシュインデックスを読み込む"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"entries": {}}
        return {"entries": {}}
    
    def _save_index(self):
        """キャッシュインデックスを保存"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def get_cache_key(self, prompt: str, service: str) -> str:
        """プロンプトとサービスからキャッシュキーを生成"""
        content = f"{prompt}_{service}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached_image(self, prompt_hash: str) -> Optional[str]:
        """
        キャッシュから画像を取得
        
        Args:
            prompt_hash: プロンプトのハッシュ値
            
        Returns:
            キャッシュされた画像のパス、なければNone
        """
        if prompt_hash in self.index["entries"]:
            entry = self.index["entries"][prompt_hash]
            image_path = Path(entry["path"])
            
            if image_path.exists():
                # アクセス時刻を更新
                entry["last_access"] = datetime.now().isoformat()
                self._save_index()
                logger.info(f"キャッシュヒット: {prompt_hash}")
                return str(image_path)
            else:
                # ファイルが存在しない場合はインデックスから削除
                del self.index["entries"][prompt_hash]
                self._save_index()
        
        return None
    
    def save_to_cache(self, prompt_hash: str, image_path: str, service: str) -> str:
        """
        画像をキャッシュに保存
        
        Args:
            prompt_hash: プロンプトのハッシュ値
            image_path: 元画像のパス
            service: 使用したサービス名
            
        Returns:
            キャッシュ内の画像パス
        """
        # キャッシュファイル名を生成
        cache_filename = f"{prompt_hash}_{service}.jpg"
        cache_path = self.cache_dir / cache_filename
        
        # 画像を圧縮して保存
        self.compress_image(image_path, str(cache_path))
        
        # インデックスに追加
        self.index["entries"][prompt_hash] = {
            "path": str(cache_path),
            "service": service,
            "created": datetime.now().isoformat(),
            "last_access": datetime.now().isoformat(),
            "size": cache_path.stat().st_size
        }
        
        self._save_index()
        
        # 容量チェックと古いファイルの削除
        self.optimize_storage()
        
        return str(cache_path)
    
    def compress_image(self, image_path: str, output_path: str, quality: int = 85):
        """
        画像を圧縮
        
        Args:
            image_path: 元画像のパス
            output_path: 出力パス
            quality: JPEG品質（1-100）
        """
        try:
            with Image.open(image_path) as img:
                # RGBAをRGBに変換（JPEGはアルファチャンネルをサポートしない）
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                # 最大サイズを制限（幅1920px）
                if img.width > 1920:
                    ratio = 1920 / img.width
                    new_size = (1920, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # JPEG形式で保存
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                logger.info(f"画像圧縮完了: {output_path}")
                
        except Exception as e:
            logger.error(f"画像圧縮エラー: {str(e)}")
            # 圧縮失敗時は元画像をコピー
            shutil.copy2(image_path, output_path)
    
    def optimize_storage(self):
        """ストレージ最適化"""
        # 現在のキャッシュサイズを計算
        total_size = sum(entry["size"] for entry in self.index["entries"].values())
        
        if total_size > self.max_size:
            logger.info(f"キャッシュサイズ超過: {total_size / 1024 / 1024:.1f}MB")
            
            # アクセス時刻でソート（古い順）
            sorted_entries = sorted(
                self.index["entries"].items(),
                key=lambda x: x[1].get("last_access", x[1]["created"])
            )
            
            # 古いファイルから削除
            for prompt_hash, entry in sorted_entries:
                if total_size <= self.max_size * 0.8:  # 80%まで削減
                    break
                
                try:
                    Path(entry["path"]).unlink()
                    total_size -= entry["size"]
                    del self.index["entries"][prompt_hash]
                    logger.info(f"古いキャッシュを削除: {entry['path']}")
                except:
                    pass
            
            self._save_index()
        
        # 30日以上古いファイルも削除
        self.cleanup_old_cache()
    
    def cleanup_old_cache(self, days: int = 30):
        """定期的なキャッシュクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=days)
        entries_to_delete = []
        
        for prompt_hash, entry in self.index["entries"].items():
            last_access = datetime.fromisoformat(entry.get("last_access", entry["created"]))
            if last_access < cutoff_date:
                entries_to_delete.append(prompt_hash)
        
        for prompt_hash in entries_to_delete:
            entry = self.index["entries"][prompt_hash]
            try:
                Path(entry["path"]).unlink()
                del self.index["entries"][prompt_hash]
                logger.info(f"期限切れキャッシュを削除: {entry['path']}")
            except:
                pass
        
        if entries_to_delete:
            self._save_index()
    
    def get_cache_stats(self) -> Dict:
        """キャッシュ統計を取得"""
        total_size = sum(entry["size"] for entry in self.index["entries"].values())
        
        return {
            "total_entries": len(self.index["entries"]),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "max_size_mb": round(self.max_size / 1024 / 1024, 2),
            "usage_percentage": round((total_size / self.max_size) * 100, 2) if self.max_size > 0 else 0,
            "oldest_entry": min(
                (entry.get("last_access", entry["created"]) for entry in self.index["entries"].values()),
                default=None
            )
        }