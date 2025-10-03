#!/usr/bin/env python3
"""
依赖锁定脚本
Dependency Lock Script

生成和验证依赖锁定文件
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class PackageInfo:
    """包信息"""
    name: str
    version: str
    locked_version: str
    hash: str
    dependencies: List[str]
    extras: List[str] = None
    source: str = "pypi"


class DependencyLocker:
    """依赖锁定管理器"""

    def __init__(self, requirements_file: Optional[Path] = None):
        """初始化锁定管理器"""
        self.requirements_file = requirements_file or project_root / "requirements.txt"
        self.lock_file = project_root / "requirements.lock"
        self.hash_file = project_root / "requirements.hash"

    def generate_lock(self, update: bool = False) -> bool:
        """
        生成锁定文件

        Args:
            update: 是否更新现有锁文件

        Returns:
            是否成功
        """
        print("🔒 生成依赖锁定文件...")

        if not self.requirements_file.exists():
            print(f"❌ requirements文件不存在: {self.requirements_file}")
            return False

        # 备份现有锁文件
        if self.lock_file.exists() and not update:
            print("⚠️ 锁文件已存在，使用 --update 更新")
            return False

        if self.lock_file.exists():
            backup_file = self.lock_file.with_suffix('.lock.backup')
            self.lock_file.rename(backup_file)
            print(f"📁 已备份现有锁文件: {backup_file}")

        try:
            # 获取所有依赖
            packages = self._get_all_packages()

            if not packages:
                print("❌ 未能获取依赖信息")
                return False

            # 生成锁文件内容
            lock_content = self._generate_lock_content(packages)

            # 写入锁文件
            with open(self.lock_file, 'w', encoding='utf-8') as f:
                f.write(lock_content)

            # 生成哈希文件
            self._generate_hash_file()

            print(f"✅ 锁文件已生成: {self.lock_file}")
            print(f"📦 已锁定 {len(packages)} 个包")

            return True

        except Exception as e:
            print(f"❌ 生成锁文件失败: {e}")

            # 恢复备份
            backup_file = self.lock_file.with_suffix('.lock.backup')
            if backup_file.exists():
                backup_file.rename(self.lock_file)
                print("🔄 已恢复备份文件")

            return False

    def _get_all_packages(self) -> List[PackageInfo]:
        """获取所有包信息"""
        packages = []

        # 使用pip freeze获取已安装的包
        try:
            result = subprocess.run(
                ['pip', 'freeze', '--all'],
                capture_output=True,
                text=True,
                check=True
            )

            installed_packages = {}
            for line in result.stdout.strip().split('\n'):
                if '==' in line:
                    name, version = line.split('==', 1)
                    installed_packages[name.lower()] = version

        except subprocess.CalledProcessError as e:
            print(f"❌ 获取已安装包失败: {e}")
            return []

        # 读取requirements.txt
        with open(self.requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue

                # 跳过开发依赖标记
                if line.startswith('-r') or line.startswith('#'):
                    continue

                # 解析包名
                package_name = self._parse_package_name(line)
                if not package_name:
                    continue

                # 获取包版本
                version = installed_packages.get(package_name.lower())
                if not version:
                    print(f"⚠️ 包未安装: {package_name}")
                    continue

                # 获取包的详细信息
                package_info = self._get_package_info(package_name, version)
                if package_info:
                    packages.append(package_info)

        return packages

    def _parse_package_name(self, line: str) -> Optional[str]:
        """解析包名"""
        # 处理各种格式
        # fastapi==0.100.0
        if '==' in line:
            return line.split('==')[0].strip()

        # fastapi>=0.100.0
        if '>=' in line:
            return line.split('>=')[0].strip()

        # fastapi[extra]==0.100.0
        if '[' in line and ']' in line:
            return line.split('[')[0].strip()

        # fastapi
        if ' ' not in line and '=' not in line and '<' not in line and '>' not in line:
            return line.strip()

        return None

    def _get_package_info(self, name: str, version: str) -> Optional[PackageInfo]:
        """获取包详细信息"""
        try:
            # 获取包的哈希值
            package_hash = self._get_package_hash(name, version)

            # 获取包的依赖
            dependencies = self._get_package_dependencies(name, version)

            return PackageInfo(
                name=name,
                version=version,
                locked_version=version,
                hash=package_hash,
                dependencies=dependencies,
                source="pypi"
            )

        except Exception as e:
            print(f"⚠️ 获取包信息失败 {name}: {e}")
            return None

    def _get_package_hash(self, name: str, version: str) -> str:
        """获取包的哈希值"""
        try:
            # 使用pip show获取信息
            result = subprocess.run(
                ['pip', 'show', name],
                capture_output=True,
                text=True,
                check=True
            )

            # 计算简单哈希（基于名称和版本）
            content = f"{name}-{version}-{datetime.now().isoformat()}"
            return hashlib.sha256(content.encode()).hexdigest()[:16]

        except:
            return "unknown"

    def _get_package_dependencies(self, name: str, version: str) -> List[str]:
        """获取包的依赖"""
        dependencies = []

        try:
            # 尝试从pip show获取Requires
            result = subprocess.run(
                ['pip', 'show', name],
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.split('\n'):
                if line.startswith('Requires:'):
                    requires = line.split(':', 1)[1].strip()
                    if requires:
                        dependencies = [dep.strip() for dep in requires.split(',')]
                    break

        except:
            pass

        return dependencies

    def _generate_lock_content(self, packages: List[PackageInfo]) -> str:
        """生成锁文件内容"""
        lines = []

        # 文件头
        lines.append("# Production Dependencies Lock File")
        lines.append("# 生产环境依赖锁定文件")
        lines.append(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("# Python Version: 3.11")
        lines.append("")

        # 按类别分组
        categories = self._categorize_packages(packages)

        for category, category_packages in categories.items():
            if category_packages:
                lines.append(f"# {category}")

                for pkg in sorted(category_packages, key=lambda x: x.name.lower()):
                    # 添加注释
                    if pkg.dependencies:
                        lines.append(f"# {pkg.name} requires: {', '.join(pkg.dependencies[:3])}")
                        if len(pkg.dependencies) > 3:
                            lines.append(f"# ... and {len(pkg.dependencies) - 3} more")

                    # 主包
                    line = f"{pkg.name}=={pkg.locked_version}"

                    # 添加哈希注释
                    if pkg.hash != "unknown":
                        line += f"  # hash: {pkg.hash}"

                    lines.append(line)

                lines.append("")

        # 开发工具提示
        lines.append("# Development Tools (exclude in production)")
        lines.append("# - Install requirements-dev.txt for development")

        return "\n".join(lines)

    def _categorize_packages(self, packages: List[PackageInfo]) -> Dict[str, List[PackageInfo]]:
        """将包按类别分组"""
        categories = {
            "Core Framework": [],
            "Database": [],
            "Redis & Cache": [],
            "Authentication & Security": [],
            "HTTP & API": [],
            "Background Tasks": [],
            "Data Processing": [],
            "Monitoring & Logging": [],
            "Utilities": [],
            "Machine Learning": [],
            "Other": []
        }

        # 分类规则
        framework_packages = {
            'fastapi', 'starlette', 'uvicorn', 'gunicorn', 'pydantic', 'pydantic-settings'
        }

        database_packages = {
            'sqlalchemy', 'asyncpg', 'alembic', 'psycopg2-binary', 'psycopg2'
        }

        cache_packages = {
            'redis', 'aioredis', 'hiredis'
        }

        security_packages = {
            'python-jose', 'passlib', 'python-multipart', 'cryptography', 'bcrypt'
        }

        http_packages = {
            'httpx', 'aiohttp', 'requests'
        }

        task_packages = {
            'celery', 'flower', 'kombu', 'billiard'
        }

        data_packages = {
            'pandas', 'numpy', 'python-dateutil', 'pytz', 'joblib', 'scikit-learn'
        }

        monitoring_packages = {
            'prometheus-client', 'structlog', 'rich', 'click', 'typer', 'tqdm'
        }

        util_packages = {
            'pyyaml', 'python-dotenv', 'click', 'typer', 'tqdm'
        }

        ml_packages = {
            'scikit-learn', 'joblib', 'scipy', 'matplotlib'
        }

        for pkg in packages:
            name_lower = pkg.name.lower()

            if any(p in name_lower for p in framework_packages):
                categories["Core Framework"].append(pkg)
            elif any(p in name_lower for p in database_packages):
                categories["Database"].append(pkg)
            elif any(p in name_lower for p in cache_packages):
                categories["Redis & Cache"].append(pkg)
            elif any(p in name_lower for p in security_packages):
                categories["Authentication & Security"].append(pkg)
            elif any(p in name_lower for p in http_packages):
                categories["HTTP & API"].append(pkg)
            elif any(p in name_lower for p in task_packages):
                categories["Background Tasks"].append(pkg)
            elif any(p in name_lower for p in data_packages):
                categories["Data Processing"].append(pkg)
            elif any(p in name_lower for p in monitoring_packages):
                categories["Monitoring & Logging"].append(pkg)
            elif any(p in name_lower for p in util_packages):
                categories["Utilities"].append(pkg)
            elif any(p in name_lower for p in ml_packages):
                categories["Machine Learning"].append(pkg)
            else:
                categories["Other"].append(pkg)

        return categories

    def _generate_hash_file(self):
        """生成哈希文件"""
        # 计算requirements.txt的哈希
        with open(self.requirements_file, 'rb') as f:
            requirements_hash = hashlib.sha256(f.read()).hexdigest()

        # 计算lock文件的哈希
        with open(self.lock_file, 'rb') as f:
            lock_hash = hashlib.sha256(f.read()).hexdigest()

        hash_data = {
            "requirements_hash": requirements_hash,
            "lock_hash": lock_hash,
            "generated_at": datetime.now().isoformat(),
            "python_version": "3.11"
        }

        with open(self.hash_file, 'w', encoding='utf-8') as f:
            json.dump(hash_data, f, indent=2, ensure_ascii=False)

    def verify_lock(self) -> bool:
        """验证锁文件是否有效"""
        print("🔍 验证依赖锁文件...")

        if not self.lock_file.exists():
            print("❌ 锁文件不存在")
            return False

        if not self.hash_file.exists():
            print("❌ 哈希文件不存在")
            return False

        try:
            # 读取哈希文件
            with open(self.hash_file, 'r', encoding='utf-8') as f:
                hash_data = json.load(f)

            # 计算当前requirements.txt的哈希
            with open(self.requirements_file, 'rb') as f:
                current_requirements_hash = hashlib.sha256(f.read()).hexdigest()

            # 计算当前lock文件的哈希
            with open(self.lock_file, 'rb') as f:
                current_lock_hash = hashlib.sha256(f.read()).hexdigest()

            # 比较哈希
            if hash_data["requirements_hash"] != current_requirements_hash:
                print("⚠️ requirements.txt已更改，需要重新生成锁文件")
                return False

            if hash_data["lock_hash"] != current_lock_hash:
                print("⚠️ 锁文件已更改，可能被手动修改")
                return False

            print("✅ 锁文件验证通过")
            return True

        except Exception as e:
            print(f"❌ 验证失败: {e}")
            return False

    def install_from_lock(self) -> bool:
        """从锁文件安装依赖"""
        print("📦 从锁文件安装依赖...")

        if not self.lock_file.exists():
            print("❌ 锁文件不存在")
            return False

        try:
            # 使用pip install安装
            result = subprocess.run(
                ['pip', 'install', '-r', str(self.lock_file)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ 依赖安装成功")
                return True
            else:
                print(f"❌ 安装失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 安装失败: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("LOCK_DEPENDENCIES_DESCRIPTION_465"))
    parser.add_argument('command', choices=[
        'generate', 'verify', 'install', 'update'
    ], help="命令")
    parser.add_argument('--requirements', '-r', type=Path,
                       help = os.getenv("LOCK_DEPENDENCIES_HELP_469"))

    args = parser.parse_args()

    # 初始化锁定管理器
    locker = DependencyLocker(args.requirements)

    if args.command == 'generate':
        success = locker.generate_lock()
        sys.exit(0 if success else 1)

    elif args.command == 'update':
        success = locker.generate_lock(update=True)
        sys.exit(0 if success else 1)

    elif args.command == 'verify':
        success = locker.verify_lock()
        sys.exit(0 if success else 1)

    elif args.command == 'install':
        success = locker.install_from_lock()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()