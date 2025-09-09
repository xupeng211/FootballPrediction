"""
足球预测系统文件处理工具模块

提供文件操作相关的工具函数。
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Union


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
        return os.path.getsize(file_path)
