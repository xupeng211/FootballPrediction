#!/usr/bin/env python3
"""
🔍 开发环境检查器

自动执行任务启动前的细节规则检查，确保开发环境处于最佳状态。
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


class EnvironmentChecker:
    """开发环境检查器"""

    def __init__(self, project_root: str = "."):
        """
        初始化环境检查器

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root).resolve()
        self.check_results: Dict[str, Any] = {}
        # 设置日志器
        try:
            self.logger = Logger.setup_logger("env_checker", "INFO")
        except (NameError, AttributeError):
            # 如果Logger不可用，使用标准logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger("env_checker")

    def run_all_checks(self) -> Dict[str, Any]:
        """
        运行所有环境检查

        Returns:
            检查结果字典
        """
        self.logger.info("🔍 开始开发环境检查...")

        # 定义检查项目
        checks = [
            ("virtual_env", "虚拟环境检查", self._check_virtual_environment),
            ("dependencies", "依赖完整性检查", self._check_dependencies),
            ("git_branch", "Git分支检查", self._check_git_branch),
            ("git_sync", "Git同步状态检查", self._check_git_sync),
            ("dev_tools", "开发工具检查", self._check_development_tools),
            ("project_structure", "项目结构检查", self._check_project_structure),
        ]

        all_passed = True

        for check_id, check_name, check_func in checks:
            self.logger.info(f"  📋 {check_name}...")

            try:
                success, message, details = check_func()

                self.check_results[check_id] = {
                    "name": check_name,
                    "success": success,
                    "message": message,
                    "details": details,
                }

                if success:
                    self.logger.info(f"    ✅ {message}")
                else:
                    self.logger.warning(f"    ❌ {message}")
                    all_passed = False

                    # 提供修复建议
                    if "suggestion" in details:
                        self.logger.info(f"    💡 建议: {details['suggestion']}")

            except Exception as e:
                self.logger.error(f"    💥 检查异常: {e}")
                self.check_results[check_id] = {
                    "name": check_name,
                    "success": False,
                    "message": f"检查异常: {e}",
                    "details": {"exception": str(e)},
                }
                all_passed = False

        # 总结
        if all_passed:
            self.logger.info("\n🎉 开发环境检查全部通过！")
        else:
            self.logger.warning("\n⚠️ 开发环境存在问题，请根据建议修复")

        return self.check_results

    def _check_virtual_environment(self) -> Tuple[bool, str, Dict]:
        """检查虚拟环境状态"""
        try:
            # 检查是否在虚拟环境中
            in_venv = hasattr(sys, "real_prefix") or (
                hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
            )

            if in_venv:
                venv_path_str = sys.prefix
                return (
                    True,
                    f"虚拟环境已激活: {venv_path_str}",
                    {
                        "active": True,
                        "path": venv_path_str,
                        "python_version": sys.version,
                    },
                )
            else:
                # 检查项目中是否有虚拟环境目录
                venv_dirs = ["venv", "env", ".venv", ".env"]
                found_venv = None

                for venv_dir in venv_dirs:
                    venv_path = self.project_root / venv_dir
                    if venv_path.exists():
                        found_venv = venv_path
                        break

                if found_venv:
                    return (
                        False,
                        "虚拟环境未激活",
                        {
                            "active": False,
                            "available": str(found_venv),
                            "suggestion": f"运行: source {found_venv}/bin/activate (Linux/Mac) 或 {found_venv}\\Scripts\\activate (Windows)",
                        },
                    )
                else:
                    return (
                        False,
                        "未找到虚拟环境",
                        {
                            "active": False,
                            "available": None,
                            "suggestion": "运行: python -m venv venv && source venv/bin/activate",
                        },
                    )

        except Exception as e:
            return False, f"虚拟环境检查失败: {e}", {"exception": str(e)}

    def _check_dependencies(self) -> Tuple[bool, str, Dict]:
        """检查依赖完整性"""
        try:
            requirements_file = self.project_root / "requirements.txt"

            if not requirements_file.exists():
                return True, "未找到requirements.txt，跳过依赖检查", {"skipped": True}

            # 读取requirements.txt
            requirements = []
            with open(requirements_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # 提取包名（忽略版本号和extras）
                        package = (
                            line.split("==")[0]
                            .split(">=")[0]
                            .split("<=")[0]
                            .split("~=")[0]
                            .split("[")[0]  # 处理 extras 如 uvicorn[standard]
                        )
                        requirements.append(package)

            # 检查已安装的包
            result = subprocess.run(
                ["pip", "list", "--format=freeze"], capture_output=True, text=True
            )

            if result.returncode != 0:
                return (
                    False,
                    "无法获取已安装包列表",
                    {"error": result.stderr, "suggestion": "检查pip是否正常工作"},
                )

            installed_packages = set()
            for line in result.stdout.split("\n"):
                if "==" in line:
                    package = line.split("==")[0].lower()  # 转换为小写
                    installed_packages.add(package)

            # 检查缺失的包
            missing_packages = []
            for package in requirements:
                if package.lower() not in installed_packages:  # 小写比较
                    missing_packages.append(package)

            if not missing_packages:
                return (
                    True,
                    f"所有依赖已安装 ({len(requirements)}个包)",
                    {
                        "total_required": len(requirements),
                        "missing_count": 0,
                        "missing_packages": [],
                    },
                )
            else:
                return (
                    False,
                    f"缺少 {len(missing_packages)} 个依赖包: {', '.join(missing_packages)}",
                    {
                        "total_required": len(requirements),
                        "missing_count": len(missing_packages),
                        "missing_packages": missing_packages,
                        "suggestion": "运行: pip install -r requirements.txt",
                    },
                )

        except Exception as e:
            return False, f"依赖检查失败: {e}", {"exception": str(e)}

    def _check_git_branch(self) -> Tuple[bool, str, Dict]:
        """检查Git分支状态"""
        try:
            # 获取当前分支
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return (
                    False,
                    "无法获取Git分支信息",
                    {"error": result.stderr, "suggestion": "确保当前目录是Git仓库"},
                )

            current_branch = result.stdout.strip()
            main_branches = ["main", "master"]

            # 在CI环境中允许主分支
            if (
                os.getenv("ENVIRONMENT") == "ci"
                or os.getenv("CI") == "true"
                or os.getenv("GITHUB_ACTIONS") == "true"
            ):
                return (
                    True,
                    f"CI环境：当前分支 '{current_branch}'",
                    {"current_branch": current_branch, "is_ci": True},
                )

            if current_branch in main_branches:
                return (
                    False,
                    f"当前在主分支 '{current_branch}'",
                    {
                        "current_branch": current_branch,
                        "is_main_branch": True,
                        "suggestion": "创建feature分支: git checkout -b feature/your-feature-name",
                    },
                )
            else:
                return (
                    True,
                    f"当前在功能分支 '{current_branch}'",
                    {"current_branch": current_branch, "is_main_branch": False},
                )

        except Exception as e:
            return False, f"Git分支检查失败: {e}", {"exception": str(e)}

    def _check_git_sync(self) -> Tuple[bool, str, Dict]:
        """检查Git同步状态"""
        try:
            # 检查工作区状态
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, "无法检查Git状态", {"error": result.stderr}

            # 检查是否有未提交的更改
            uncommitted_changes = (
                result.stdout.strip().split("\n") if result.stdout.strip() else []
            )

            # 检查远程同步状态
            subprocess.run(
                ["git", "fetch", "--dry-run"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            behind_commits = 0
            ahead_commits = 0

            # 获取落后/领先信息
            status_result = subprocess.run(
                ["git", "status", "-sb"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            status_output = status_result.stdout
            if "behind" in status_output:
                # 提取落后的提交数
                import re

                match = re.search(r"behind (\d+)", status_output)
                if match:
                    behind_commits = int(match.group(1))

            if "ahead" in status_output:
                # 提取领先的提交数
                import re

                match = re.search(r"ahead (\d+)", status_output)
                if match:
                    ahead_commits = int(match.group(1))

            sync_status = {
                "uncommitted_changes": len(uncommitted_changes),
                "behind_commits": behind_commits,
                "ahead_commits": ahead_commits,
                "changes": uncommitted_changes[:5],  # 只显示前5个
            }

            if behind_commits > 0:
                return (
                    False,
                    f"代码落后远程 {behind_commits} 个提交",
                    {**sync_status, "suggestion": "运行: git pull origin main"},
                )
            elif len(uncommitted_changes) > 0:
                return (
                    True,
                    f"工作区有 {len(uncommitted_changes)} 个未提交更改",
                    sync_status,
                )
            else:
                return True, "Git工作区干净，与远程同步", sync_status

        except Exception as e:
            return False, f"Git同步检查失败: {e}", {"exception": str(e)}

    def _check_development_tools(self) -> Tuple[bool, str, Dict]:
        """检查开发工具完整性"""
        try:
            tools = {
                "black": "python -m black --version",
                "flake8": "python -m flake8 --version",
                "pytest": "python -m pytest --version",
                "mypy": "python -m mypy --version",
                "coverage": "python -m coverage --version",
                "radon": "python -m radon --version",
            }

            available_tools = {}
            missing_tools = []

            for tool_name, command in tools.items():
                try:
                    result = subprocess.run(
                        command.split(), capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        version = result.stdout.strip().split("\n")[0]
                        available_tools[tool_name] = version
                    else:
                        missing_tools.append(tool_name)

                except Exception:
                    missing_tools.append(tool_name)

            if not missing_tools:
                return (
                    True,
                    f"所有开发工具已安装 ({len(available_tools)}个)",
                    {"available_tools": available_tools, "missing_tools": []},
                )
            else:
                return (
                    False,
                    f"缺少 {len(missing_tools)} 个开发工具",
                    {
                        "available_tools": available_tools,
                        "missing_tools": missing_tools,
                        "suggestion": f"安装缺失工具: pip install {' '.join(missing_tools)}",
                    },
                )

        except Exception as e:
            return False, f"开发工具检查失败: {e}", {"exception": str(e)}

    def _check_project_structure(self) -> Tuple[bool, str, Dict]:
        """检查项目结构完整性"""
        try:
            required_dirs = ["tests", "scripts", "logs"]
            required_files = ["requirements.txt", "rules.md", "README.md"]

            missing_dirs = []
            missing_files = []

            for dir_name in required_dirs:
                if not (self.project_root / dir_name).exists():
                    missing_dirs.append(dir_name)

            for file_name in required_files:
                if not (self.project_root / file_name).exists():
                    missing_files.append(file_name)

            total_missing = len(missing_dirs) + len(missing_files)

            if total_missing == 0:
                return (
                    True,
                    "项目结构完整",
                    {
                        "required_dirs": required_dirs,
                        "required_files": required_files,
                        "missing_dirs": [],
                        "missing_files": [],
                    },
                )
            else:
                return (
                    False,
                    f"项目结构不完整，缺少 {total_missing} 项",
                    {
                        "required_dirs": required_dirs,
                        "required_files": required_files,
                        "missing_dirs": missing_dirs,
                        "missing_files": missing_files,
                        "suggestion": "运行 python scripts/setup_project.py 初始化项目结构",
                    },
                )

        except Exception as e:
            return False, f"项目结构检查失败: {e}", {"exception": str(e)}

    def print_summary(self) -> None:
        """打印检查摘要"""
        print("\n📊 环境检查摘要:")

        for check_id, result in self.check_results.items():
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}: {result['message']}")

    def get_action_items(self) -> List[str]:
        """获取需要执行的操作项"""
        actions = []

        for check_id, result in self.check_results.items():
            if not result["success"] and "suggestion" in result["details"]:
                actions.append(result["details"]["suggestion"])

        return actions


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="开发环境检查器")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--summary", action="store_true", help="显示检查摘要")
    parser.add_argument("--fix-suggestions", action="store_true", help="显示修复建议")

    args = parser.parse_args()

    checker = EnvironmentChecker(args.project_root)
    results = checker.run_all_checks()

    if args.summary:
        checker.print_summary()

    if args.fix_suggestions:
        actions = checker.get_action_items()
        if actions:
            print("\n🔧 修复建议:")
            for i, action in enumerate(actions, 1):
                print(f"   {i}. {action}")
        else:
            print("\n🎉 无需修复操作")

    # 返回适当的退出代码
    all_passed = all(result["success"] for result in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
