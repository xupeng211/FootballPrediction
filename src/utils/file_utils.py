from typing import Any

"""
足球预测系统文件处理工具模块

提供文件操作相关的工具函数.
"""
import hashlib
import json
import os
import time
from pathlib import Path


class FileUtils:
    """文件处理工具类"""

    @staticmethod
    def ensure_dir(path: str | Path) -> Path:
        """确保目录存在"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """确保目录存在(ensure_dir的别名)"""
        return FileUtils.ensure_dir(path)

    @staticmethod
    def read_text(path: str | Path, encoding: str = "utf-8") -> str:
        """读取文本文件"""
        path = Path(path)
        return path.read_text(encoding=encoding)

    @staticmethod
    def write_text(path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """写入文本文件"""
        path = Path(path)
        FileUtils.ensure_dir(path.parent)
        path.write_text(content, encoding=encoding)

    @staticmethod
    def read_json(path: str | Path, encoding: str = "utf-8") -> dict[str, Any]:
        """读取JSON文件"""
        content = FileUtils.read_text(path, encoding)
        return json.loads(content)

    @staticmethod
    def write_json(path: str | Path, data: dict[str, Any], encoding: str = "utf-8", indent: int = 2) -> None:
        """写入JSON文件"""
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        FileUtils.write_text(path, content, encoding)

    @staticmethod
    def get_file_hash(path: str | Path, algorithm: str = "md5") -> str:
        """获取文件哈希值"""
        path = Path(path)
        hash_func = hashlib.new(algorithm)

        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    @staticmethod
    def get_file_size(path: str | Path) -> int:
        """获取文件大小(字节)"""
        path = Path(path)
        return path.stat().st_size

    @staticmethod
    def get_file_mtime(path: str | Path) -> float:
        """获取文件修改时间"""
        path = Path(path)
        return path.stat().st_mtime

    @staticmethod
    def exists(path: str | Path) -> bool:
        """检查文件或目录是否存在"""
        return Path(path).exists()

    @staticmethod
    def is_file(path: str | Path) -> bool:
        """检查是否为文件"""
        return Path(path).is_file()

    @staticmethod
    def is_dir(path: str | Path) -> bool:
        """检查是否为目录"""
        return Path(path).is_dir()

    @staticmethod
    def delete(path: str | Path) -> bool:
        """删除文件或目录"""
        path = Path(path)
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
            return True
        except OSError:
            return False

    @staticmethod
    def list_files(directory: str | Path, pattern: str = "*") -> list[Path]:
        """列出目录中的文件"""
        directory = Path(directory)
        return list(directory.glob(pattern))

    @staticmethod
    def get_temp_dir() -> Path:
        """获取临时目录"""
        return Path("/tmp")
