"""
足球预测系统文件处理工具模块

提供文件操作相关的工具函数。
"""

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


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

    @staticmethod
    def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """复制文件"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            shutil.copy2(src_path, dst_path)
            return True
        except (FileNotFoundError, PermissionError, OSError):
            return False

    @staticmethod
    def move_file(src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """移动文件"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return True
        except (FileNotFoundError, PermissionError, OSError):
            return False

    @staticmethod
    def delete_file(file_path: Union[str, Path]) -> bool:
        """删除文件"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except (FileNotFoundError, PermissionError, OSError):
            return False

    @staticmethod
    def file_exists(file_path: Union[str, Path]) -> bool:
        """检查文件是否存在"""
        return Path(file_path).exists()

    @staticmethod
    def is_file(file_path: Union[str, Path]) -> bool:
        """检查路径是否为文件"""
        return Path(file_path).is_file()

    @staticmethod
    def is_directory(dir_path: Union[str, Path]) -> bool:
        """检查路径是否为目录"""
        return Path(dir_path).is_dir()

    @staticmethod
    def list_files(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
        """列出目录中的文件"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            return list(dir_path.glob(pattern))
        except (FileNotFoundError, OSError):
            return []

    @staticmethod
    def list_files_recursive(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
        """递归列出目录中的所有文件"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            return list(dir_path.rglob(pattern))
        except (FileNotFoundError, OSError):
            return []

    @staticmethod
    def get_file_extension(file_path: Union[str, Path]) -> str:
        """获取文件扩展名"""
        return Path(file_path).suffix

    @staticmethod
    def get_file_name(file_path: Union[str, Path]) -> str:
        """获取文件名（不含扩展名）"""
        return Path(file_path).stem

    @staticmethod
    def get_file_full_name(file_path: Union[str, Path]) -> str:
        """获取文件全名（含扩展名）"""
        return Path(file_path).name

    @staticmethod
    def create_backup(file_path: Union[str, Path], backup_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """创建文件备份"""
        try:
            src_path = Path(file_path)
            if not src_path.exists():
                return None

            if backup_dir is None:
                backup_path = src_path.with_suffix(f".backup{int(time.time())}")
            else:
                backup_dir_path = Path(backup_dir)
                backup_dir_path.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir_path / f"{src_path.name}.backup{int(time.time())}"

            shutil.copy2(src_path, backup_path)
            return backup_path
        except (FileNotFoundError, PermissionError, OSError):
            return None

    @staticmethod
    def read_text_file(file_path: Union[str, Path], encoding: str = "utf-8") -> Optional[str]:
        """读取文本文件"""
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (FileNotFoundError, UnicodeDecodeError, OSError):
            return None

    @staticmethod
    def write_text_file(content: str, file_path: Union[str, Path], encoding: str = "utf-8",
                        ensure_dir: bool = True) -> bool:
        """写入文本文件"""
        try:
            file_path_obj = Path(file_path)
            if ensure_dir:
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path_obj, "w", encoding=encoding) as f:
                f.write(content)
            return True
        except (PermissionError, OSError):
            return False

    @staticmethod
    def append_to_file(content: str, file_path: Union[str, Path], encoding: str = "utf-8") -> bool:
        """追加内容到文件"""
        try:
            with open(file_path, "a", encoding=encoding) as f:
                f.write(content)
            return True
        except (PermissionError, OSError):
            return False

    @staticmethod
    def get_directory_size(directory: Union[str, Path]) -> int:
        """获取目录总大小（字节）"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return 0

            total_size = 0
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except (FileNotFoundError, OSError):
            return 0

    @staticmethod
    def count_files(directory: Union[str, Path]) -> int:
        """统计目录中的文件数量"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return 0

            return len([f for f in dir_path.rglob("*") if f.is_file()])
        except (FileNotFoundError, OSError):
            return 0

    @staticmethod
    def safe_remove_directory(directory: Union[str, Path]) -> bool:
        """安全删除目录（仅删除空目录）"""
        try:
            dir_path = Path(directory)
            if dir_path.exists() and dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                return True
            return False
        except (FileNotFoundError, OSError):
            return False

    @staticmethod
    def remove_directory_force(directory: Union[str, Path]) -> bool:
        """强制删除目录及其内容"""
        try:
            dir_path = Path(directory)
            if dir_path.exists():
                shutil.rmtree(dir_path)
                return True
            return False
        except (FileNotFoundError, PermissionError, OSError):
            return False
