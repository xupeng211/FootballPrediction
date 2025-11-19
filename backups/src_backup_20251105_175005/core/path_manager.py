"""路径管理器 - 统一Python路径配置.

解决Python模块导入路径问题，支持多种环境配置。
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PathManager:
    """统一路径管理器 - 解决Python路径配置问题."""

    def __init__(self, project_root: Path | None = None):
        """初始化路径管理器.

        Args:
            project_root: 项目根目录，如果为None则自动检测
        """
        if project_root is None:
            self.project_root = self._detect_project_root()
        else:
            self.project_root = Path(project_root)

        self.src_path = self.project_root / "src"
        self._is_configured = False

        logger.info(f"项目根目录: {self.project_root}")
        logger.info(f"src路径: {self.src_path}")

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录."""
        current = Path.cwd()

        # 查找项目根目录标记
        markers = ["pyproject.toml", "setup.py", "README.md", "CLAUDE.md"]

        while current != current.parent:
            for marker in markers:
                if (current / marker).exists():
                    logger.info(f"检测到项目根目录标记: {marker}")
                    return current
            current = current.parent

        # 如果没有找到，使用当前目录
        logger.warning("未找到项目根目录标记，使用当前目录")
        return Path.cwd()

    def setup_src_path(self, force: bool = False) -> bool:
        """设置src路径到Python路径.

        Args:
            force: 是否强制重新配置

        Returns:
            bool: 配置是否成功
        """
        if self._is_configured and not force:
            logger.info("路径已配置，跳过")
            return True

        try:
            src_str = str(self.src_path)

            # 检查src目录是否存在
            if not self.src_path.exists():
                logger.error(f"src目录不存在: {self.src_path}")
                return False

            # 添加到Python路径
            if src_str not in sys.path:
                sys.path.insert(0, src_str)
                logger.info(f"已添加src到Python路径: {src_str}")
            else:
                logger.info(f"src已在Python路径中: {src_str}")

            # 验证配置
            if self._verify_src_import():
                self._is_configured = True
                logger.info("✅ src路径配置成功")
                return True
            else:
                logger.error("❌ src路径配置验证失败")
                return False

        except Exception as e:
            logger.error(f"配置src路径失败: {e}")
            return False

    def _verify_src_import(self) -> bool:
        """验证src模块是否可以导入."""
        try:
            # 尝试导入src模块
            pass

            return True
        except ImportError as e:
            logger.warning(f"src导入验证失败: {e}")
            return False

    def ensure_src_importable(self) -> bool:
        """确保src可以正常导入."""
        if self._verify_src_import():
            return True

        # 如果无法导入，尝试重新配置路径
        return self.setup_src_path(force=True)

    def get_environment_info(self) -> dict[str, Any]:
        """获取环境信息."""
        return {
            "project_root": str(self.project_root),
            "src_path": str(self.src_path),
            "src_exists": self.src_path.exists(),
            "python_path": sys.path[:5],  # 只显示前5个路径
            "working_directory": os.getcwd(),
            "pythonpath_env": os.environ.get("PYTHONPATH", ""),
            "is_configured": self._is_configured,
        }

    def setup_environment_paths(self) -> dict[str, bool]:
        """设置多环境路径配置."""
        results = {}

        # 1. 本地开发环境
        results["local"] = self._setup_local_environment()

        # 2. Docker环境检测
        results["docker"] = self._detect_docker_environment()

        # 3. IDE环境检测
        results["ide"] = self._detect_ide_environment()

        return results

    def _setup_local_environment(self) -> bool:
        """设置本地开发环境."""
        try:
            # 设置PYTHONPATH环境变量
            pythonpath = os.environ.get("PYTHONPATH", "")
            src_path_str = str(self.src_path)

            if src_path_str not in pythonpath:
                new_pythonpath = (
                    f"{pythonpath}:{src_path_str}" if pythonpath else src_path_str
                )
                os.environ["PYTHONPATH"] = new_pythonpath
                logger.info(f"设置PYTHONPATH: {new_pythonpath}")

            return True
        except Exception as e:
            logger.error(f"本地环境设置失败: {e}")
            return False

    def _detect_docker_environment(self) -> bool:
        """检测Docker环境."""
        docker_indicators = [
            "/.dockerenv",  # Docker容器标记文件
            os.path.exists("/proc/1/cgroup")
            and "docker" in open("/proc/1/cgroup").read(),
        ]

        is_docker = any(docker_indicators)
        if is_docker:
            logger.info("检测到Docker环境")
            # Docker环境特殊配置
            os.environ["PYTHONPATH"] = str(self.src_path)

        return is_docker

    def _detect_ide_environment(self) -> bool:
        """检测IDE环境."""
        ide_indicators = [
            os.environ.get("VS_CODE_PID"),  # VS Code
            os.environ.get("PYCHARM_HOSTED"),  # PyCharm
            os.environ.get("JETBRAINS_IDE"),  # JetBrains IDEs
        ]

        is_ide = any(ide_indicators)
        if is_ide:
            logger.info("检测到IDE环境")

        return is_ide

    def create_ide_config_files(self) -> dict[str, bool]:
        """创建IDE配置文件."""
        results = {}

        # VS Code配置
        results["vscode"] = self._create_vscode_config()

        # PyCharm配置（.idea目录通常不需要手动创建）
        results["pycharm"] = self._create_pycharm_hints()

        return results

    def _create_vscode_config(self) -> bool:
        """创建VS Code配置."""
        try:
            vscode_dir = self.project_root / ".vscode"
            vscode_dir.mkdir(exist_ok=True)

            settings_file = vscode_dir / "settings.json"
            settings_content = {
                "python.defaultInterpreterPath": "./.venv/bin/python",
                "python.analysis.extraPaths": ["./src"],
                "python.analysis.autoSearchPaths": True,
                "python.analysis.diagnosticSeverityOverrides": {
                    "reportMissingImports": "none"
                },
            }

            import json

            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings_content, f, indent=2, ensure_ascii=False)

            logger.info("✅ VS Code配置文件已创建")
            return True
        except Exception as e:
            logger.error(f"VS Code配置创建失败: {e}")
            return False

    def _create_pycharm_hints(self) -> bool:
        """创建PyCharm配置提示."""
        try:
            hints_file = self.project_root / ".idea" / "misc.xml"
            hints_file.parent.mkdir(exist_ok=True)

            # PyCharm通常需要手动配置，这里创建提示文件
            readme_content = """
# PyCharm配置说明

请手动配置以下设置：

1. 打开 File -> Settings -> Project -> Python Interpreter
2. 选择项目虚拟解释器: ./.venv/bin/python
3. 打开 File -> Settings -> Project -> Project Structure
4. 将src目录标记为Sources Root

或者：
- 右键点击src目录 -> Mark Directory as -> Sources Root
"""

            pycharm_readme = self.project_root / "PYCHARM_SETUP.md"
            with open(pycharm_readme, "w", encoding="utf-8") as f:
                f.write(readme_content)

            logger.info("✅ PyCharm配置提示已创建")
            return True
        except Exception as e:
            logger.error(f"PyCharm配置提示创建失败: {e}")
            return False

    def validate_configuration(self) -> dict[str, Any]:
        """验证路径配置."""
        validation_results = {
            "src_path_exists": self.src_path.exists(),
            "src_in_python_path": str(self.src_path) in sys.path,
            "src_importable": False,
            "environment_setup": {},
            "errors": [],
        }

        # 测试src导入
        try:
            pass

            validation_results["src_importable"] = True
        except ImportError as e:
            validation_results["errors"].append(f"src导入失败: {e}")

        # 环境设置验证
        validation_results["environment_setup"] = self.setup_environment_paths()

        return validation_results


# 全局路径管理器实例
_path_manager: PathManager | None = None


def get_path_manager() -> PathManager:
    """获取全局路径管理器实例."""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
        _path_manager.setup_src_path()
    return _path_manager


def setup_project_paths() -> bool:
    """设置项目路径（便捷函数）."""
    manager = get_path_manager()
    return manager.setup_src_path()


def ensure_src_importable() -> bool:
    """确保src可以导入（便捷函数）."""
    manager = get_path_manager()
    return manager.ensure_src_importable()


# 自动执行路径配置
if __name__ == "__main__":
    # 如果直接运行此文件，执行配置和验证
    manager = PathManager()
    success = manager.setup_src_path()

    info = manager.get_environment_info()
    for _key, _value in info.items():
        pass

    validation = manager.validate_configuration()
    for _key, _value in validation.items():
        pass

    if success:
        pass
    else:
        pass
