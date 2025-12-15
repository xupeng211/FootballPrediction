#!/usr/bin/env python3
"""
🔍 项目上下文加载器

自动收集项目信息，为Cursor闭环系统提供完整的上下文数据。
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加项目路径以便导入核心模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 临时跳过有问题的导入，直接使用标准logging
import logging
logger = logging.getLogger(__name__)

try:
    from src.core import Logger  # noqa: E402
    logger_instance = Logger()
except ImportError:
    # 如果导入失败，使用标准logging
    logger_instance = logger


class ProjectContextLoader:
    """项目上下文加载器"""

    def __init__(self, project_root: str = "."):
        """
        初始化上下文加载器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.context: Dict[str, Any] = {}
        # 设置日志器
        # 设置日志器
        try:
            self.logger = Logger.setup_logger("context_loader", "INFO")
        except (NameError, AttributeError):
            # 如果Logger不可用，使用标准logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger("context_loader")

    def load_all_context(self) -> Dict[str, Any]:
        """
        加载所有项目上下文信息

        Returns:
            包含完整项目上下文的字典
        """
        self.logger.info("🔍 开始加载项目上下文...")

        self.context = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "directory_structure": self._get_directory_structure(),
            "git_info": self._get_git_info(),
            "existing_modules": self._get_existing_modules(),
            "existing_tests": self._get_existing_tests(),
            "dependencies": self._get_dependencies(),
            "recent_changes": self._get_recent_changes(),
            "project_stats": self._get_project_stats(),
        }

        self.logger.info("✅ 项目上下文加载完成")
        return self.context

    def _get_directory_structure(self) -> Dict[str, Any]:
        """获取目录结构"""
        self.logger.info("  📁 扫描目录结构...")

        structure = {
            "root_files": [],
            "directories": {},
            "total_files": 0,
            "total_directories": 0,
        }

        try:
            # 获取根目录文件
            for item in self.project_root.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    structure["root_files"].append(item.name)

            # 获取主要目录信息
            for directory in ["src", "tests", "docs", "scripts", "logs"]:
                dir_path = self.project_root / directory
                if dir_path.exists():
                    structure["directories"][directory] = self._scan_directory(dir_path)

            # 统计总数
            structure["total_files"] = sum(
                len(info.get("files", [])) for info in structure["directories"].values()
            )
            structure["total_directories"] = len(structure["directories"])

        except Exception as e:
            structure["error"] = f"扫描目录结构失败: {e}"

        return structure

    def _scan_directory(self, directory: Path) -> Dict[str, Any]:
        """扫描单个目录"""
        info = {"files": [], "subdirectories": [], "python_files": [], "test_files": []}

        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(directory)
                    info["files"].append(str(relative_path))

                    if item.suffix == ".py":
                        info["python_files"].append(str(relative_path))

                        if "test" in item.name.lower():
                            info["test_files"].append(str(relative_path))

                elif item.is_dir() and item != directory:
                    relative_path = item.relative_to(directory)
                    if str(relative_path).count(os.sep) == 0:  # 只记录直接子目录
                        info["subdirectories"].append(str(relative_path))

        except Exception as e:
            info["error"] = f"扫描目录失败: {e}"

        return info

    def _get_git_info(self) -> Dict[str, Any]:
        """获取Git信息 - 收集版本控制状态，为开发上下文提供代码变更追踪能力"""
        self.logger.info("  🌿 获取Git信息...")

        git_info = {
            "repository_exists": False,
            "current_branch": None,
            "recent_commits": [],
            "status": None,
            "remote_url": None,
        }

        try:
            # 检查是否是Git仓库 - 确定项目是否在版本控制下
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                git_info["repository_exists"] = True

                # 获取当前分支 - 了解开发分支情况，便于分支策略管理
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    git_info["current_branch"] = result.stdout.strip()

                # 获取最近提交 - 了解代码变更历史，便于理解项目演进
                result = subprocess.run(
                    ["git", "log", "--oneline", "-10"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    git_info["recent_commits"] = result.stdout.strip().split("\n")

                # 获取状态 - 检查工作区变更，确保开发环境清洁
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    git_info["status"] = result.stdout.strip()

                # 获取远程URL - 了解仓库来源，便于协作和部署
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    git_info["remote_url"] = result.stdout.strip()

        except Exception as e:
            # Git命令执行失败时记录错误，不影响其他上下文信息收集
            git_info["error"] = f"获取Git信息失败: {e}"

        return git_info

    def _get_existing_modules(self) -> Dict[str, Any]:
        """获取已存在的模块"""
        self.logger.info("  📦 分析现有模块...")

        modules = {"python_modules": [], "module_structure": {}, "import_analysis": {}}

        try:
            src_path = self.project_root / "src"
            if src_path.exists():
                for py_file in src_path.rglob("*.py"):
                    relative_path = py_file.relative_to(src_path)
                    modules["python_modules"].append(str(relative_path))

                    # 分析模块结构
                    module_name = (
                        str(relative_path).replace(os.sep, ".").replace(".py", "")
                    )
                    modules["module_structure"][module_name] = {
                        "file_path": str(relative_path),
                        "size": py_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            py_file.stat().st_mtime
                        ).isoformat(),
                    }

        except Exception as e:
            modules["error"] = f"分析模块失败: {e}"

        return modules

    def _get_existing_tests(self) -> Dict[str, Any]:
        """获取已存在的测试"""
        self.logger.info("  🧪 扫描测试文件...")

        tests = {"test_files": [], "test_structure": {}, "coverage_info": None}

        try:
            tests_path = self.project_root / "tests"
            if tests_path.exists():
                for test_file in tests_path.rglob("test_*.py"):
                    relative_path = test_file.relative_to(tests_path)
                    tests["test_files"].append(str(relative_path))

                    tests["test_structure"][str(relative_path)] = {
                        "size": test_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            test_file.stat().st_mtime
                        ).isoformat(),
                    }

        except Exception as e:
            tests["error"] = f"扫描测试失败: {e}"

        return tests

    def _get_dependencies(self) -> Dict[str, Any]:
        """获取依赖信息"""
        self.logger.info("  📋 分析项目依赖...")

        dependencies = {
            "requirements_txt": None,
            "setup_py": None,
            "pyproject_toml": None,
            "pipfile": None,
            "conda_env": None,
        }

        try:
            # 检查requirements.txt
            req_file = self.project_root / "requirements.txt"
            if req_file.exists():
                dependencies["requirements_txt"] = (
                    req_file.read_text().strip().split("\n")
                )

            # 检查setup.py
            setup_file = self.project_root / "setup.py"
            if setup_file.exists():
                dependencies["setup_py"] = "存在"

            # 检查pyproject.toml
            pyproject_file = self.project_root / "pyproject.toml"
            if pyproject_file.exists():
                dependencies["pyproject_toml"] = "存在"

            # 检查Pipfile
            pipfile = self.project_root / "Pipfile"
            if pipfile.exists():
                dependencies["pipfile"] = "存在"

        except Exception as e:
            dependencies["error"] = f"分析依赖失败: {e}"

        return dependencies

    def _get_recent_changes(self) -> Dict[str, Any]:
        """获取最近的变更"""
        self.logger.info("  📝 分析最近变更...")

        changes = {
            "modified_files": [],
            "added_files": [],
            "deleted_files": [],
            "last_commit_info": None,
        }

        try:
            # 获取工作区状态
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    status = line[:2]
                    filename = line[3:]

                    if "M" in status:
                        changes["modified_files"].append(filename)
                    elif "A" in status:
                        changes["added_files"].append(filename)
                    elif "D" in status:
                        changes["deleted_files"].append(filename)

            # 获取最后一次提交信息
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%H|%an|%ad|%s"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout:
                parts = result.stdout.split("|")
                if len(parts) >= 4:
                    changes["last_commit_info"] = {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    }

        except Exception as e:
            changes["error"] = f"分析变更失败: {e}"

        return changes

    def _get_project_stats(self) -> Dict[str, Any]:
        """获取项目统计信息"""
        self.logger.info("  📊 生成项目统计...")

        stats = {
            "total_python_files": 0,
            "total_test_files": 0,
            "total_lines_of_code": 0,
            "project_size_mb": 0,
            "last_activity": None,
        }

        try:
            python_files = list(self.project_root.rglob("*.py"))
            stats["total_python_files"] = len(python_files)

            test_files = [f for f in python_files if "test" in f.name.lower()]
            stats["total_test_files"] = len(test_files)

            # 计算代码行数
            total_lines = 0
            for py_file in python_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        total_lines += len(f.readlines())
                except Exception:
                    pass

            stats["total_lines_of_code"] = total_lines

            # 计算项目大小
            total_size = 0
            for file_path in self.project_root.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

            stats["project_size_mb"] = round(total_size / (1024 * 1024), 2)

            # 获取最后活动时间
            if python_files:
                latest_time = max(f.stat().st_mtime for f in python_files)
                stats["last_activity"] = datetime.fromtimestamp(latest_time).isoformat()

        except Exception as e:
            stats["error"] = f"生成统计失败: {e}"

        return stats

    def save_context(self, output_file: str = "logs/project_context.json") -> None:
        """
        保存上下文到文件

        Args:
            output_file: 输出文件路径
        """
        output_path = self.project_root / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 上下文已保存到: {output_path}")

    def print_summary(self) -> None:
        """打印上下文摘要"""
        self.logger.info("\n📋 项目上下文摘要:")
        self.logger.info(f"   📁 项目根目录: {self.context['project_root']}")

        if self.context["git_info"]["repository_exists"]:
            self.logger.info(
                f"   🌿 Git分支: {self.context['git_info']['current_branch']}"
            )
            self.logger.info(
                f"   📝 最近提交: {len(self.context['git_info']['recent_commits'])} 条"
            )

        self.logger.info(
            f"   📦 Python模块: {len(self.context['existing_modules']['python_modules'])} 个"
        )
        self.logger.info(
            f"   🧪 测试文件: {len(self.context['existing_tests']['test_files'])} 个"
        )
        self.logger.info(
            f"   📊 代码行数: {self.context['project_stats']['total_lines_of_code']}"
        )
        self.logger.info(
            f"   💾 项目大小: {self.context['project_stats']['project_size_mb']} MB"
        )


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="项目上下文加载器")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--output", default="logs/project_context.json", help="输出文件")
    parser.add_argument("--summary", action="store_true", help="显示摘要")

    args = parser.parse_args()

    loader = ProjectContextLoader(args.project_root)
    loader.load_all_context()
    loader.save_context(args.output)

    if args.summary:
        loader.print_summary()


if __name__ == "__main__":
    main()
