"""
足球预测系统文件处理工具模块

提供文件操作相关的工具函数。
"""

from typing import Any

import hashlib
import json
import os
from pathlib import Path
from typing import Union, Dict, Any, Optional
import time


class FileUtils:
    """文件处理工具类"""

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """确保目录存在"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
        """读取JSON文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise FileNotFoundError(f"无法读取JSON文件 {file_path}: {e}")

    @staticmethod
    def write_json(
        data: Dict[str, Any], file_path: Union[str, Path], ensure_dir: bool = True
    ) -> None:
        """写入JSON文件"""
        file_path = Path(file_path)
        if ensure_dir:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def get_file_hash(file_path: Union[str, Path]) -> str:
        """获取文件MD5哈希值"""
        hash_md5 = hashlib.md5(usedforsecurity=False)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """获取文件大小（字节）"""
        try:
            if not os.path.exists(file_path):
                return 0
            return os.path.getsize(file_path)
        except (FileNotFoundError, OSError):
            return 0

    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """确保目录存在（别名方法）"""
        return FileUtils.ensure_dir(path)

    @staticmethod
    def read_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """读取JSON文件（别名方法）"""
        try:
            return FileUtils.read_json(file_path)
        except FileNotFoundError:
            return None

    @staticmethod
    def write_json_file(
        data: Dict[str, Any], file_path: Union[str, Path], ensure_dir: bool = True
    ) -> bool:
        """写入JSON文件（别名方法）"""
        try:
            FileUtils.write_json(data, file_path, ensure_dir)
            return True
        except (ValueError, KeyError, RuntimeError):
            return False

    @staticmethod
    def cleanup_old_files(directory: Union[str, Path], days: int = 30) -> int:
        """清理旧文件"""

        directory = Path(directory)
        if not directory.exists():
            return 0

        cutoff_time = time.time() - (days * 24 * 60 * 60)
        removed_count = 0

        try:
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1
        except (ValueError, KeyError, RuntimeError):
            pass

        return removed_count
