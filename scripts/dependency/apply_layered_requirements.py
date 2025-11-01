#!/usr/bin/env python3
"""
应用分层依赖管理方案
自动安装正确的依赖集并验证无冲突
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, Optional


class LayeredDependencyManager:
    """分层依赖管理器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.requirements_dir = project_root / "requirements"
        self.python_executable = sys.executable
        self.pip_options = ["--no-cache-dir", "--disable-pip-version-check"]

    def setup_environment(self, env_type: str = "production") -> bool:
        """设置指定类型的环境"""
        print(f"🔧 设置 {env_type} 环境...")

        # 选择对应的requirements文件
        req_file = self._get_requirements_file(env_type)
        if not req_file or not req_file.exists():
            print(f"❌ 找不到 {env_type} 环境的requirements文件")
            return False

        # 备份当前环境
        if not self._backup_current_env():
            print("❌ 无法备份当前环境")
            return False

        # 清理现有环境（可选）
        if env_type == "production":
            if not self._cleanup_dev_packages():
                print("⚠️ 清理开发包时出现问题，继续...")

        # 安装依赖
        if not self._install_requirements(req_file):
            print(f"❌ 安装 {env_type} 依赖失败")
            return False

        # 验证安装
        if not self._verify_installation(env_type):
            print(f"❌ {env_type} 环境验证失败")
            return False

        print(f"✅ {env_type} 环境设置成功")
        return True

    def _get_requirements_file(self, env_type: str) -> Optional[Path]:
        """获取对应的requirements文件"""
        mapping = {
            "minimum": "minimum.txt",
            "core": "core.txt",
            "api": "api.txt",
            "ml": "ml.txt",
            "production": "production.txt",
            "development": "development.txt",
        }

        if env_type not in mapping:
            return None

        return self.requirements_dir / mapping[env_type]

    def _backup_current_env(self) -> bool:
        """备份当前环境"""
        print("  - 备份当前环境...")

        # 创建备份目录
        backup_dir = self.project_root / ".env_backup" / "current"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 导出包列表
        try:
            result = subprocess.run(
                [self.python_executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                check=True,
            )

            with open(backup_dir / "requirements.txt", "w") as f:
                f.write(result.stdout)

            print(f"    ✓ 备份保存到: {backup_dir}")
            return True
        except subprocess.CalledProcessError:
            return False

    def _cleanup_dev_packages(self) -> bool:
        """清理开发工具包"""
        print("  - 清理开发工具包...")

        # 需要移除的开发工具
        dev_packages = [
            "semgrep",
            "rich-toolkit",
            "pipdeptree",
            "pyproject-api",
            "checkov",
            "fastmcp",
            "mypy",
            "black",
            "flake8",
            "pytest",
            "coverage",
            "tox",
            "pre-commit",
            "isort",
            "autoflake",
            "autopep8",
            "pyupgrade",
            "bandit",
            "safety",
            "pip-audit",
            "mypy",
            "pylint",
            "pycodestyle",
            "pydocstyle",
            "pyflakes",
        ]

        success = True
        for pkg in dev_packages:
            try:
                result = subprocess.run(
                    [self.python_executable, "-m", "pip", "uninstall", pkg, "-y"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"    ✓ 移除 {pkg}")
                pass  # 忽略不存在的包

        return success

    def _install_requirements(self, req_file: Path) -> bool:
        """安装requirements文件"""
        print(f"  - 安装 {req_file.name}...")

        try:
            # 升级pip
            subprocess.run(
                [self.python_executable, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                check=True,
            )

            # 安装依赖
            subprocess.run(
                [self.python_executable, "-m", "pip", "install", "-r", str(req_file)]
                + self.pip_options,
                capture_output=True,
                text=True,
                check=True,
            )

            print(f"    ✓ 成功安装 {req_file.name}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"    ❌ 安装失败: {e.stderr}")
            return False

    def _verify_installation(self, env_type: str) -> bool:
        """验证安装"""
        print(f"  - 验证 {env_type} 环境...")

        # 1. 检查pip check
        print("    检查依赖冲突...")
        result = subprocess.run(
            [self.python_executable, "-m", "pip", "check"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("    ❌ 发现依赖冲突:")
            for line in result.stderr.split("\n"):
                if line.strip():
                    print(f"      - {line}")
            return False

        print("    ✓ 无依赖冲突")

        # 2. 检查核心包
        if env_type in ["production", "core", "api"]:
            core_packages = ["fastapi", "sqlalchemy", "pydantic", "uvicorn"]
            print("    检查核心包...")

            for pkg in core_packages:
                try:
                    __import__(pkg)
                    print(f"    ✓ {pkg} 已安装")
                except ImportError:
                    print(f"    ❌ {pkg} 未安装")
                    return False

        # 3. 检查ML包（如果需要）
        if env_type in ["production", "ml"]:
            ml_packages = ["numpy", "pandas", "scikit-learn"]
            print("    检查ML包...")

            for pkg in ml_packages:
                try:
                    __import__(pkg)
                    print(f"    ✓ {pkg} 已安装")
                except ImportError:
                    print(f"    ❌ {pkg} 未安装")
                    return False

        # 4. 环境特定验证
        self._environment_specific_checks(env_type)

        return True

    def _environment_specific_checks(self, env_type: str):
        """环境特定检查"""

        if env_type == "production":
            print("    生产环境特定检查...")

            # 检查配置文件
            env_file = self.project_root / ".env.production"
            if env_file.exists():
                print("    ✓ .env.production 存在")
            else:
                print("    ⚠️ .env.production 不存在")

            # 检查Docker配置
            docker_files = [
                "Dockerfile",
                "docker-compose.yml",
                "config/docker/docker-compose.production.yml",
            ]

            for docker_file in docker_files:
                if (self.project_root / docker_file).exists():
                    print(f"    ✓ {docker_file} 存在")

        elif env_type == "minimum":
            print("    最小环境特定检查...")

            # 检查是否能启动FastAPI
            try:
                import importlib.util

                spec = importlib.util.find_spec("fastapi")
                if spec:
                    print("    ✓ FastAPI 可导入")
            except ImportError:
                print("    ❌ FastAPI 不可导入")

    def switch_environment(self, target_env: str) -> bool:
        """切换环境"""
        print(f"🔄 切换到 {target_env} 环境...")

        # 创建新的虚拟环境（可选）
        venv_path = self.project_root / f".venv-{target_env}"
        if not venv_path.exists():
            print(f"  - 创建虚拟环境 {venv_path}...")
            subprocess.run([self.python_executable, "-m", "venv", str(venv_path)], check=True)

        # 激活虚拟环境并安装依赖
        if sys.platform == "win32":
            pip_executable = venv_path / "Scripts" / "pip.exe"
        else:
            pip_executable = venv_path / "bin" / "pip"

        if pip_executable.exists():
            print(f"  - 在 {venv_path} 中安装依赖...")
            req_file = self._get_requirements_file(target_env)
            if req_file and req_file.exists():
                subprocess.run([str(pip_executable), "install", "-r", str(req_file)], check=True)
                print(f"✅ {target_env} 环境准备完成")
                print(f"  激活命令: source {venv_path}/bin/activate")
                return True

        return False

    def generate_report(self) -> Dict:
        """生成环境报告"""
        print("📊 生成环境报告...")

        report = {
            "timestamp": subprocess.run(
                ["date", "-Iseconds"], capture_output=True, text=True
            ).stdout.strip(),
            "python_version": sys.version,
            "pip_version": subprocess.run(
                [self.python_executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "environments": {},
        }

        # 检查各种环境
        env_types = ["minimum", "core", "api", "ml", "production"]

        for env_type in env_types:
            req_file = self._get_requirements_file(env_type)
            if req_file and req_file.exists():
                report["environments"][env_type] = {
                    "requirements_file": str(req_file),
                    "exists": True,
                    "package_count": self._count_packages(req_file),
                }
            else:
                report["environments"][env_type] = {
                    "requirements_file": None,
                    "exists": False,
                }

        # 保存报告
        report_file = self.project_root / "docs/_reports" / "DEPENDENCY_ENVIRONMENTS_REPORT.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ 报告保存到: {report_file}")
        return report

    def _count_packages(self, req_file: Path) -> int:
        """计算包数量"""
        count = 0
        with open(req_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-r"):
                    count += 1
        return count

    def fix_production_conflicts(self) -> bool:
        """修复生产环境冲突"""
        print("🔧 修复生产环境冲突...")

        # 生产环境需要移除的包
        conflict_packages = [
            "rich-toolkit",  # 版本冲突
            "semgrep",  # 开发工具
            "fastmcp",  # 开发工具
            "pipdeptree",  # 开发工具
            "checkov",  # 开发工具
            "mypy",  # 开发工具
            "black",  # 开发工具
            "flake8",  # 开发工具
            "pytest",  # 测试工具
            "coverage",  # 测试工具
        ]

        success = True
        for pkg in conflict_packages:
            result = subprocess.run(
                [self.python_executable, "-m", "pip", "uninstall", pkg, "-y"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  ✓ 移除冲突包: {pkg}")

        # 安装兼容版本
        compatible_packages = {
            "numpy": "1.26.4",
            "pandas": "2.2.3",
            "pydantic": "2.10.4",
            "rich": "13.9.4",
            "urllib3": "2.2.3",
        }

        for pkg, version in compatible_packages.items():
            result = subprocess.run(
                [self.python_executable, "-m", "pip", "install", f"{pkg}=={version}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  ✓ 安装兼容版本: {pkg}=={version}")

        return success


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="分层依赖管理工具")
    parser.add_argument(
        "--env",
        choices=["minimum", "core", "api", "ml", "production", "development"],
        default="production",
        help="环境类型",
    )
    parser.add_argument(
        "--action",
        choices=["setup", "switch", "report", "fix"],
        default="setup",
        help="操作类型",
    )

    args = parser.parse_args()

    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    manager = LayeredDependencyManager(project_root)

    if args.action == "setup":
        success = manager.setup_environment(args.env)
        if success:
            print(f"\n✅ {args.env} 环境设置完成！")
        else:
            print(f"\n❌ {args.env} 环境设置失败！")
            sys.exit(1)

    elif args.action == "switch":
        success = manager.switch_environment(args.env)
        if success:
            print(f"\n✅ 已切换到 {args.env} 环境！")
        else:
            print("\n❌ 切换失败！")
            sys.exit(1)

    elif args.action == "report":
        report = manager.generate_report()
        print("\n📊 环境报告:")
        for env, info in report["environments"].items():
            status = "✅" if info["exists"] else "❌"
            pkg_count = f" ({info['package_count']} 包)" if info["package_count"] else ""
            print(f"  {status} {env}: {info['requirements_file']}{pkg_count}")

    elif args.action == "fix":
        success = manager.fix_production_conflicts()
        if success:
            print("\n✅ 生产环境冲突已修复！")
        else:
            print("\n❌ 修复失败！")
            sys.exit(1)


if __name__ == "__main__":
    main()
