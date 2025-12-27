"""
V8.1 防弹级路径管理系统
解决所有导入混乱问题，实现零手动干预的自动化部署
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PathManager:
    """
    防弹级路径管理器

    核心功能：
    1. 自动探测和设置PYTHONPATH
    2. 统一所有模块的绝对导入路径
    3. 确保在任何环境下都能正确运行
    4. 提供路径验证和修复功能
    """

    _instance: Optional["PathManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "PathManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_paths()
            PathManager._initialized = True

    def _setup_paths(self) -> None:
        """设置所有必要的路径"""
        # 获取项目根目录
        self.project_root = self._find_project_root()

        # 设置核心路径
        self.src_path = self.project_root / "src"
        self.project_path = self.project_root

        # 自动配置PYTHONPATH
        self._configure_pythonpath()

        # 验证路径完整性
        self._validate_paths()

        logger.info(f"路径管理器初始化完成: {self.project_root}")

    def _find_project_root(self) -> Path:
        """智能探测项目根目录"""
        current = Path(__file__).resolve().parent

        # 向上查找项目根目录标志文件
        root_markers = ["pyproject.toml", "requirements.txt", "Dockerfile", "docker-compose.yml"]

        while current.parent != current:
            if any((current / marker).exists() for marker in root_markers):
                return current
            current = current.parent

        # 如果找不到，使用当前脚本所在目录的上级目录
        return Path(__file__).resolve().parent.parent

    def _configure_pythonpath(self) -> None:
        """配置PYTHONPATH环境变量"""
        paths_to_add = [str(self.project_root), str(self.src_path)]

        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
                logger.debug(f"添加到PYTHONPATH: {path}")

    def _validate_paths(self) -> None:
        """验证关键路径存在性"""
        critical_paths = {
            "project_root": self.project_root,
            "src_path": self.src_path,
            "config": self.src_path / "core",
            "ml": self.src_path / "ml",
            "api": self.src_path / "api",
            "database": self.src_path / "database",
        }

        missing_paths = []
        for name, path in critical_paths.items():
            if not path.exists():
                missing_paths.append(f"{name}: {path}")
                logger.warning(f"关键路径缺失: {name} -> {path}")

        if missing_paths:
            logger.warning(f"发现 {len(missing_paths)} 个缺失路径，系统可能功能受限")
        else:
            logger.info("所有关键路径验证通过")

    def get_absolute_import(self, module_path: str) -> str:
        """
        将相对导入转换为绝对导入

        Args:
            module_path: 模块路径 (如 'core.config' 或 '../api/client')

        Returns:
            str: 绝对导入路径
        """
        if module_path.startswith(".."):
            # 处理相对导入
            parts = module_path.split(".")
            current_level = 0

            for part in parts:
                if part == "":
                    current_level += 1
                else:
                    break

            # 计算绝对路径
            if current_level > 0:
                # 相对导入，转换为基于src的绝对导入
                remaining_parts = [p for p in parts if p]
                absolute_path = ".".join(remaining_parts)
                return absolute_path
        elif "." not in module_path:
            # 简单模块名，假设在src下
            return f"{module_path}"
        else:
            # 已经是绝对路径格式
            return module_path

    def ensure_importable(self, module_name: str) -> bool:
        """
        确保模块可以导入

        Args:
            module_name: 模块名称

        Returns:
            bool: 是否可以导入
        """
        try:
            __import__(module_name)
            return True
        except ImportError as e:
            logger.error(f"模块导入失败: {module_name} - {e}")
            return False

    def get_path_info(self) -> dict[str, Any]:
        """获取路径信息用于调试"""
        return {
            "project_root": str(self.project_root),
            "src_path": str(self.src_path),
            "python_path": sys.path[:5],  # 只显示前5个
            "working_directory": os.getcwd(),
            "initialized": self._initialized,
        }


# 全局单例实例
path_manager = PathManager()


def ensure_system_ready() -> bool:
    """
    确保系统准备就绪

    Returns:
        bool: 系统是否准备就绪
    """
    try:
        # 验证路径管理器
        pm = PathManager()

        # 测试关键模块导入
        critical_modules = [
            "src.core.config",
            "src.utils.database",
            "src.models.model_handler",  # 修正模块路径
        ]

        importable_modules = []
        failed_modules = []

        for module in critical_modules:
            if pm.ensure_importable(module):
                importable_modules.append(module)
            else:
                failed_modules.append(module)

        if failed_modules:
            logger.error(f"关键模块导入失败: {failed_modules}")
            return False

        logger.info(f"系统准备就绪，{len(importable_modules)}个关键模块可用")
        return True

    except Exception as e:
        logger.error(f"系统准备检查失败: {e}")
        return False


def auto_fix_imports(file_path: str) -> bool:
    """
    自动修复文件中的导入问题

    Args:
        file_path: 要修复的文件路径

    Returns:
        bool: 是否修复成功
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []
        changes_made = False

        for line in lines:
            if line.strip().startswith("from ") and ".." in line:
                # 修复相对导入
                parts = line.split()
                if len(parts) >= 2:
                    old_import = parts[1]
                    new_import = path_manager.get_absolute_import(old_import)

                    if old_import != new_import:
                        fixed_line = line.replace(old_import, new_import)
                        fixed_lines.append(fixed_line)
                        changes_made = True
                        logger.debug(f"修复导入: {old_import} -> {new_import}")
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        if changes_made:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(fixed_lines))
            logger.info(f"自动修复导入完成: {file_path}")

        return changes_made

    except Exception as e:
        logger.error(f"自动修复导入失败: {file_path} - {e}")
        return False


# 自动执行系统准备
if __name__ == "__main__":
    import json

    success = ensure_system_ready()
    print(f"系统准备状态: {'✅ 就绪' if success else '❌ 失败'}")
    print(json.dumps(path_manager.get_path_info(), indent=2, ensure_ascii=False))
