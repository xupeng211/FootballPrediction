#!/usr/bin/env python3
"""
配置迁移脚本
Configuration Migration Script

管理配置版本和迁移
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class Migration:
    """迁移定义"""
    version: str
    description: str
    timestamp: datetime
    forward: callable  # 向前迁移函数
    backward: Optional[callable] = None  # 向后迁移函数
    dependencies: List[str] = None  # 依赖的版本


class ConfigMigration:
    """配置迁移管理器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化迁移管理器

        Args:
            config_dir: 配置目录
        """
        self.config_dir = config_dir or project_root
        self.migrations_dir = self.config_dir / "migrations"
        self.migrations_file = self.migrations_dir / "migrations.json"
        self.current_version_file = self.migrations_dir / "current_version.txt"
        self.backup_dir = self.migrations_dir / "backups"

        # 确保目录存在
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 注册的迁移
        self.migrations: Dict[str, Migration] = {}
        self._register_migrations()

    def _register_migrations(self):
        """注册所有迁移"""

        # v1.0.0 -> v1.1.0: 添加Redis配置
        def migrate_1_0_to_1_1(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            if 'REDIS_HOST' not in env_vars:
                changes['REDIS_HOST'] = 'localhost'
            if 'REDIS_PORT' not in env_vars:
                changes['REDIS_PORT'] = '6379'
            if 'REDIS_DB' not in env_vars:
                changes['REDIS_DB'] = '0'
            return changes

        self.add_migration(Migration(
            version="1.1.0",
            description="添加Redis配置",
            timestamp=datetime(2024, 1, 1),
            forward=migrate_1_0_to_1_1
        ))

        # v1.1.0 -> v1.2.0: 重命名API配置变量
        def migrate_1_1_to_1_2(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            # 重命名变量
            if 'HOST' in env_vars and 'API_HOST' not in env_vars:
                changes['API_HOST'] = env_vars['HOST']
                changes['_remove_HOST'] = True
            if 'PORT' in env_vars and 'API_PORT' not in env_vars:
                changes['API_PORT'] = env_vars['PORT']
                changes['_remove_PORT'] = True
            return changes

        def revert_1_2_to_1_1(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            if 'API_HOST' in env_vars and 'HOST' not in env_vars:
                changes['HOST'] = env_vars['API_HOST']
                changes['_remove_API_HOST'] = True
            if 'API_PORT' in env_vars and 'PORT' not in env_vars:
                changes['PORT'] = env_vars['API_PORT']
                changes['_remove_API_PORT'] = True
            return changes

        self.add_migration(Migration(
            version="1.2.0",
            description="重命名API配置变量",
            timestamp=datetime(2024, 2, 1),
            forward=migrate_1_1_to_1_2,
            backward=revert_1_2_to_1_1,
            dependencies=["1.1.0"]
        ))

        # v1.2.0 -> v1.3.0: 添加缓存配置
        def migrate_1_2_to_1_3(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            if 'CACHE_ENABLED' not in env_vars:
                changes['CACHE_ENABLED'] = 'true'
            if 'CACHE_DEFAULT_TTL' not in env_vars:
                changes['CACHE_DEFAULT_TTL'] = '300'
            if 'MEMORY_CACHE_SIZE' not in env_vars:
                changes['MEMORY_CACHE_SIZE'] = '1000'
            return changes

        self.add_migration(Migration(
            version="1.3.0",
            description="添加缓存配置",
            timestamp=datetime(2024, 3, 1),
            forward=migrate_1_2_to_1_3,
            dependencies=["1.2.0"]
        ))

        # v1.3.0 -> v1.4.0: 添加监控配置
        def migrate_1_3_to_1_4(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            if 'METRICS_ENABLED' not in env_vars:
                changes['METRICS_ENABLED'] = 'true'
            if 'METRICS_PORT' not in env_vars:
                changes['METRICS_PORT'] = '9090'
            return changes

        self.add_migration(Migration(
            version="1.4.0",
            description="添加监控配置",
            timestamp=datetime(2024, 4, 1),
            forward=migrate_1_3_to_1_4,
            dependencies=["1.3.0"]
        ))

        # v1.4.0 -> v1.5.0: 增强安全配置
        def migrate_1_4_to_1_5(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            # 检查密钥强度
            for key in ['JWT_SECRET_KEY', 'SECRET_KEY']:
                if key in env_vars:
                    value = env_vars[key]
                    if len(value) < 32:
                        print(f"⚠️ 警告: {key} 长度不足，建议更新")
            # 添加新的安全配置
            if 'ACCESS_TOKEN_EXPIRE_MINUTES' not in env_vars:
                changes['ACCESS_TOKEN_EXPIRE_MINUTES'] = '30'
            return changes

        self.add_migration(Migration(
            version="1.5.0",
            description="增强安全配置",
            timestamp=datetime(2024, 5, 1),
            forward=migrate_1_4_to_1_5,
            dependencies=["1.4.0"]
        ))

        # v1.5.0 -> v1.6.0: 添加性能配置
        def migrate_1_5_to_1_6(env_vars: Dict[str, str]) -> Dict[str, str]:
            changes = {}
            if 'PERF_SLOW_QUERY_THRESHOLD' not in env_vars:
                changes['PERF_SLOW_QUERY_THRESHOLD'] = '1.0'
            if 'PERF_ENABLE_COMPRESSION' not in env_vars:
                changes['PERF_ENABLE_COMPRESSION'] = 'true'
            return changes

        self.add_migration(Migration(
            version="1.6.0",
            description="添加性能配置",
            timestamp=datetime(2024, 6, 1),
            forward=migrate_1_5_to_1_6,
            dependencies=["1.5.0"]
        ))

    def add_migration(self, migration: Migration):
        """添加迁移"""
        self.migrations[migration.version] = migration

    def get_current_version(self) -> str:
        """获取当前版本"""
        if self.current_version_file.exists():
            with open(self.current_version_file, 'r') as f:
                return f.read().strip()
        return "1.0.0"  # 默认初始版本

    def set_current_version(self, version: str):
        """设置当前版本"""
        with open(self.current_version_file, 'w') as f:
            f.write(version)

    def get_migration_path(self, from_version: str, to_version: str) -> List[Migration]:
        """获取迁移路径"""
        if from_version == to_version:
            return []

        # 解析版本号
        from_parts = [int(x) for x in from_version.split('.')]
        to_parts = [int(x) for x in to_version.split('.')]

        # 确定方向
        is_upgrade = to_parts > from_parts

        # 获取所有迁移并排序
        sorted_migrations = sorted(
            self.migrations.values(),
            key=lambda m: [int(x) for x in m.version.split('.')]
        )

        # 选择需要的迁移
        path = []
        if is_upgrade:
            for migration in sorted_migrations:
                mig_parts = [int(x) for x in migration.version.split('.')]
                if from_parts < mig_parts <= to_parts:
                    # 检查依赖
                    if self._check_dependencies(migration, from_version):
                        path.append(migration)
        else:
            # 降序排列用于降级
            for migration in reversed(sorted_migrations):
                mig_parts = [int(x) for x in migration.version.split('.')]
                if to_parts <= mig_parts < from_parts:
                    if migration.backward:
                        path.append(migration)

        return path

    def _check_dependencies(self, migration: Migration, from_version: str) -> bool:
        """检查迁移依赖"""
        if not migration.dependencies:
            return True

        for dep in migration.dependencies:
            dep_parts = [int(x) for x in dep.split('.')]
            from_parts = [int(x) for x in from_version.split('.')]
            if dep_parts > from_parts:
                return False

        return True

    def backup_config(self, env_file: Path) -> Path:
        """备份配置文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{env_file.stem}_{timestamp}.backup"
        backup_path = self.backup_dir / backup_name

        if env_file.exists():
            shutil.copy2(env_file, backup_path)
            print(f"✅ 配置已备份到: {backup_path}")
        else:
            # 创建空备份文件
            backup_path.touch()
            print(f"⚠️ 创建空备份文件: {backup_path}")

        return backup_path

    def migrate_env_file(self, env_file: Path, to_version: str,
                        dry_run: bool = False) -> bool:
        """
        迁移环境文件

        Args:
            env_file: 环境文件路径
            to_version: 目标版本
            dry_run: 是否试运行

        Returns:
            是否成功
        """
        if not env_file.exists():
            print(f"❌ 配置文件不存在: {env_file}")
            return False

        # 读取当前配置
        env_vars = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

        # 获取当前版本
        current_version = self.get_current_version()
        print(f"当前版本: {current_version}")
        print(f"目标版本: {to_version}")

        # 获取迁移路径
        migration_path = self.get_migration_path(current_version, to_version)

        if not migration_path:
            print("✅ 配置已是最新版本")
            return True

        print(f"\n需要执行 {len(migration_path)} 个迁移:")
        for migration in migration_path:
            print(f"  - {migration.version}: {migration.description}")

        # 备份配置
        if not dry_run:
            backup_path = self.backup_config(env_file)

        # 执行迁移
        try:
            for migration in migration_path:
                print(f"\n执行迁移: {migration.version} - {migration.description}")

                if dry_run:
                    print("  [试运行] 将执行以下变更:")

                changes = migration.forward(env_vars)

                if changes:
                    for key, value in changes.items():
                        if key.startswith('_remove_'):
                            # 删除变量
                            old_key = key[7:]  # 移除 '_remove_' 前缀
                            if dry_run:
                                print(f"    - 删除: {old_key}")
                            else:
                                if old_key in env_vars:
                                    del env_vars[old_key]
                                    print(f"    ✅ 已删除: {old_key}")
                        else:
                            # 添加或更新变量
                            if dry_run:
                                print(f"    - 设置: {key} = {'*' * min(len(str(value)), 8)}")
                            else:
                                old_value = env_vars.get(key)
                                env_vars[key] = str(value)
                                if old_value is None:
                                    print(f"    ✅ 已添加: {key}")
                                else:
                                    print(f"    ✅ 已更新: {key}")

            # 写入新配置
            if not dry_run:
                with open(env_file, 'w', encoding='utf-8') as f:
                    # 保留注释
                    with open(env_file, 'r', encoding='utf-8') as original:
                        lines = original.readlines()

                    # 写入新内容
                    f.write("# 自动迁移的配置文件\n")
                    f.write(f"# 迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# 版本: {to_version}\n\n")

                    for key, value in sorted(env_vars.items()):
                        f.write(f"{key}={value}\n")

                # 更新版本
                self.set_current_version(to_version)
                print(f"\n✅ 迁移完成！新版本: {to_version}")
                print(f"📁 备份文件: {backup_path}")

            return True

        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            if not dry_run and backup_path.exists():
                # 恢复备份
                shutil.copy2(backup_path, env_file)
                print("🔄 已恢复备份")
            return False

    def rollback(self, env_file: Path, to_version: str) -> bool:
        """
        回滚到指定版本

        Args:
            env_file: 环境文件路径
            to_version: 目标版本

        Returns:
            是否成功
        """
        current_version = self.get_current_version()
        print(f"当前版本: {current_version}")
        print(f"回滚到版本: {to_version}")

        # 获取回滚路径
        migration_path = self.get_migration_path(current_version, to_version)

        if not migration_path:
            print("❌ 无法回滚到指定版本")
            return False

        # 备份当前配置
        backup_path = self.backup_config(env_file)

        # 执行回滚
        try:
            # 读取配置
            env_vars = {}
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

            # 反向执行迁移
            for migration in migration_path:
                if migration.backward:
                    print(f"回滚: {migration.version} - {migration.description}")
                    changes = migration.backward(env_vars)

                    for key, value in changes.items():
                        if key.startswith('_remove_'):
                            old_key = key[7:]
                            if old_key in env_vars:
                                del env_vars[old_key]
                        else:
                            env_vars[key] = str(value)

            # 写入配置
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("# 回滚的配置文件\n")
                f.write(f"# 回滚时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 版本: {to_version}\n\n")

                for key, value in sorted(env_vars.items()):
                    f.write(f"{key}={value}\n")

            # 更新版本
            self.set_current_version(to_version)
            print(f"✅ 回滚完成！当前版本: {to_version}")
            return True

        except Exception as e:
            print(f"❌ 回滚失败: {e}")
            # 恢复备份
            if backup_path.exists():
                shutil.copy2(backup_path, env_file)
                print("🔄 已恢复备份")
            return False

    def list_migrations(self) -> List[Dict[str, Any]]:
        """列出所有迁移"""
        migrations_list = []

        for version, migration in self.migrations.items():
            migrations_list.append({
                'version': version,
                'description': migration.description,
                'timestamp': migration.timestamp.isoformat(),
                'dependencies': migration.dependencies or [],
                'has_backward': migration.backward is not None
            })

        return sorted(migrations_list, key=lambda x: x['version'])

    def status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        current_version = self.get_current_version()
        latest_version = max(self.migrations.keys()) if self.migrations else current_version

        # 获取待执行的迁移
        pending_migrations = self.get_migration_path(current_version, latest_version)

        return {
            'current_version': current_version,
            'latest_version': latest_version,
            'pending_migrations': len(pending_migrations),
            'up_to_date': current_version == latest_version
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置迁移工具")
    parser.add_argument('command', choices=[
        'migrate', 'rollback', 'status', 'list', 'init'
    ], help="命令")

    parser.add_argument('--file', '-f', type=Path,
                       default=project_root / ".env.production",
                       help="环境文件路径")
    parser.add_argument('--to', '-t', help="目标版本")
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help="试运行")
    parser.add_argument('--init-version', default='1.0.0',
                       help="初始化版本")

    args = parser.parse_args()

    # 初始化迁移管理器
    migrator = ConfigMigration()

    if args.command == 'init':
        # 初始化迁移
        migrator.set_current_version(args.init_version)
        print(f"✅ 迁移已初始化，当前版本: {args.init_version}")

    elif args.command == 'migrate':
        if not args.to:
            # 迁移到最新版本
            latest_version = max(migrator.migrations.keys()) if migrator.migrations else "1.0.0"
            args.to = latest_version

        success = migrator.migrate_env_file(args.file, args.to, args.dry_run)
        sys.exit(0 if success else 1)

    elif args.command == 'rollback':
        if not args.to:
            print("❌ 回滚需要指定目标版本 (--to)")
            sys.exit(1)

        success = migrator.rollback(args.file, args.to)
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        status = migrator.status()
        print(f"\n配置迁移状态:")
        print(f"当前版本: {status['current_version']}")
        print(f"最新版本: {status['latest_version']}")
        print(f"待执行迁移: {status['pending_migrations']}")
        print(f"状态: {'✅ 最新' if status['up_to_date'] else '⚠️ 需要更新'}")

    elif args.command == 'list':
        migrations = migrator.list_migrations()
        print(f"\n可用的迁移:")
        for migration in migrations:
            print(f"  v{migration['version']} - {migration['description']}")
            if migration['dependencies']:
                print(f"    依赖: {', '.join(migration['dependencies'])}")
            if migration['has_backward']:
                print(f"    ✓ 可回滚")


if __name__ == "__main__":
    main()