#!/usr/bin/env python3
"""
配置备份脚本
Configuration Backup Script

自动备份和恢复配置文件
"""

import os
import sys
import json
import shutil
import tarfile
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import subprocess

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_crypto import ConfigCrypto


@dataclass
class BackupConfig:
    """备份配置"""
    name: str
    source_files: List[Path]
    destination_dir: Path
    retention_days: int = 30
    encrypt: bool = True
    compress: bool = True


class ConfigBackup:
    """配置备份管理器"""

    def __init__(self, backup_root: Optional[Path] = None):
        """
        初始化备份管理器

        Args:
            backup_root: 备份根目录
        """
        self.backup_root = backup_root or project_root / "backups"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.crypto = ConfigCrypto()
        self.backup_index_file = self.backup_root / "backup_index.json"
        self.backup_index = self._load_backup_index()

        # 预定义的备份配置
        self.backup_configs = {
            "env": BackupConfig(
                name = os.getenv("BACKUP_CONFIG_NAME_58"),
                source_files=[
                    project_root / ".env.production",
                    project_root / ".env.local",
                    project_root / ".env"
                ],
                destination_dir=self.backup_root / "env",
                retention_days=30,
                encrypt=True
            ),
            "config": BackupConfig(
                name = os.getenv("BACKUP_CONFIG_NAME_68"),
                source_files=[
                    project_root / "config" / "production.yaml",
                    project_root / "config" / "staging.yaml",
                    project_root / "docker-compose.yml",
                ],
                destination_dir=self.backup_root / "config",
                retention_days=30,
                encrypt=True
            ),
            "secrets": BackupConfig(
                name = os.getenv("BACKUP_CONFIG_NAME_79"),
                source_files=[
                    project_root / ".config_key",
                    project_root / ".config_key.salt",
                ],
                destination_dir=self.backup_root / "secrets",
                retention_days=90,
                encrypt=True
            ),
            "certificates": BackupConfig(
                name = os.getenv("BACKUP_CONFIG_NAME_88"),
                source_files=[
                    project_root / "certs",
                ],
                destination_dir=self.backup_root / "certs",
                retention_days=365,
                encrypt=True
            )
        }

    def _load_backup_index(self) -> Dict[str, Any]:
        """加载备份索引"""
        if self.backup_index_file.exists():
            try:
                with open(self.backup_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载备份索引失败: {e}")

        return {
            "last_backup": None,
            "backups": [],
            "configurations": {}
        }

    def _save_backup_index(self):
        """保存备份索引"""
        try:
            with open(self.backup_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.backup_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存备份索引失败: {e}")

    def backup_configuration(self, config_name: str,
                           password: Optional[str] = None) -> bool:
        """
        备份特定配置

        Args:
            config_name: 配置名称
            password: 加密密码

        Returns:
            是否成功
        """
        if config_name not in self.backup_configs:
            print(f"❌ 未知的配置: {config_name}")
            return False

        config = self.backup_configs[config_name]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            print(f"🔄 开始备份配置: {config_name}")

            # 创建备份目录
            backup_dir = config.destination_dir / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 备份文件列表
            backed_up_files = []

            for source_file in config.source_files:
                if source_file.exists():
                    if source_file.is_file():
                        # 备份单个文件
                        if config.encrypt:
                            # 加密备份
                            encrypted_file = backup_dir / f"{source_file.name}.enc"
                            if source_file.suffix == '.env':
                                success = self.crypto.encrypt_env_file(
                                    source_file, encrypted_file, password
                                )
                            else:
                                # 读取文件内容
                                if source_file.suffix in ['.yml', '.yaml']:
                                    import yaml
                                    with open(source_file, 'r', encoding='utf-8') as f:
                                        content = yaml.safe_load(f)
                                else:
                                    with open(source_file, 'r', encoding='utf-8') as f:
                                        content = json.load(f)

                                success = self.crypto.encrypt_config(
                                    content, encrypted_file, password
                                )

                            if success:
                                backed_up_files.append(str(encrypted_file))
                        else:
                            # 直接复制
                            dest_file = backup_dir / source_file.name
                            shutil.copy2(source_file, dest_file)
                            backed_up_files.append(str(dest_file))

                    elif source_file.is_dir():
                        # 备份目录
                        if config.compress:
                            # 压缩备份
                            archive_file = backup_dir / f"{source_file.name}.tar.gz"
                            with tarfile.open(archive_file, 'w:gz') as tar:
                                tar.add(source_file, arcname=source_file.name)
                            backed_up_files.append(str(archive_file))

                            if config.encrypt:
                                # 加密压缩文件
                                encrypted_file = backup_dir / f"{source_file.name}.tar.gz.enc"
                                self.crypto.encrypt_config(
                                    {"archive": str(archive_file.name)},
                                    encrypted_file,
                                    password
                                )
                                # 删除未加密的压缩文件
                                archive_file.unlink()
                                backed_up_files = [str(encrypted_file)]
                        else:
                            # 直接复制目录
                            dest_dir = backup_dir / source_file.name
                            shutil.copytree(source_file, dest_dir)
                            backed_up_files.append(str(dest_dir))

            # 创建备份清单
            manifest = {
                "config_name": config_name,
                "timestamp": timestamp,
                "files": backed_up_files,
                "encrypted": config.encrypt,
                "compressed": config.compress
            }

            with open(backup_dir / "manifest.json", 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)

            # 更新备份索引
            self.backup_index["last_backup"] = timestamp
            self.backup_index["backups"].append({
                "config_name": config_name,
                "timestamp": timestamp,
                "files": backed_up_files,
                "size": self._get_backup_size(backup_dir)
            })
            self._save_backup_index()

            print(f"✅ 配置 {config_name} 备份成功")
            print(f"📍 位置: {backup_dir}")
            return True

        except Exception as e:
            print(f"❌ 备份失败: {e}")
            # 清理失败的备份
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            return False

    def restore_configuration(self, config_name: str,
                            timestamp: Optional[str] = None,
                            password: Optional[str] = None,
                            force: bool = False) -> bool:
        """
        恢复配置

        Args:
            config_name: 配置名称
            timestamp: 备份时间戳，None表示使用最新备份
            password: 解密密码
            force: 是否强制覆盖现有文件

        Returns:
            是否成功
        """
        if config_name not in self.backup_configs:
            print(f"❌ 未知的配置: {config_name}")
            return False

        config = self.backup_configs[config_name]

        # 查找备份
        if timestamp:
            backup_dir = config.destination_dir / timestamp
        else:
            # 查找最新的备份
            backup_dirs = list(config.destination_dir.glob("*"))
            if not backup_dirs:
                print(f"❌ 没有找到 {config_name} 的备份")
                return False
            backup_dir = max(backup_dirs, key=lambda x: x.name)

        if not backup_dir.exists():
            print(f"❌ 备份不存在: {backup_dir}")
            return False

        # 读取备份清单
        manifest_file = backup_dir / "manifest.json"
        if not manifest_file.exists():
            print(f"❌ 备份清单不存在")
            return False

        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        try:
            print(f"🔄 开始恢复配置: {config_name}")
            print(f"📅 备份时间: {manifest['timestamp']}")

            # 检查现有文件
            if not force:
                for source_file in config.source_files:
                    if source_file.exists():
                        print(f"⚠️ 文件已存在: {source_file}")
                        if input("是否覆盖? (y/N): ").lower() != 'y':
                            print("❌ 恢复已取消")
                            return False

            # 恢复文件
            for file_info in manifest["files"]:
                backup_file = backup_dir / Path(file_info).name

                if backup_file.suffix == '.enc':
                    # 解密恢复
                    if backup_file.name.endswith('.env.enc'):
                        # 恢复.env文件
                        source_file = project_root / ".env.production"
                        self.crypto.decrypt_to_env_file(backup_file, source_file, password)
                    else:
                        # 恢复其他文件
                        decrypted_content = self.crypto.decrypt_config(backup_file, password)
                        if decrypted_content:
                            # 确定源文件路径
                            if 'archive' in decrypted_content:
                                # 处理压缩文件
                                archive_file = backup_dir / decrypted_content['archive']
                                if archive_file.exists():
                                    with tarfile.open(archive_file, 'r:gz') as tar:
                                        tar.extractall(project_root)
                            else:
                                # 普通配置文件
                                source_file = self._find_source_file(config, backup_file.name)
                                if source_file:
                                    if source_file.suffix in ['.yml', '.yaml']:
                                        import yaml
                                        with open(source_file, 'w', encoding='utf-8') as f:
                                            yaml.dump(decrypted_content, f, default_flow_style=False)
                                    else:
                                        with open(source_file, 'w', encoding='utf-8') as f:
                                            json.dump(decrypted_content, f, indent=2, ensure_ascii=False)
                else:
                    # 直接复制
                    source_file = self._find_source_file(config, backup_file.name)
                    if source_file:
                        if backup_file.suffix == '.tar.gz':
                            # 解压
                            with tarfile.open(backup_file, 'r:gz') as tar:
                                tar.extractall(project_root)
                        else:
                            # 复制文件
                            shutil.copy2(backup_file, source_file)

            print(f"✅ 配置 {config_name} 恢复成功")
            return True

        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            return False

    def _find_source_file(self, config: BackupConfig, backup_name: str) -> Optional[Path]:
        """查找源文件路径"""
        # 移除加密后缀
        if backup_name.endswith('.enc'):
            backup_name = backup_name[:-4]

        for source_file in config.source_files:
            if source_file.name == backup_name:
                return source_file

        return None

    def _get_backup_size(self, backup_dir: Path) -> int:
        """获取备份大小（字节）"""
        total_size = 0
        for file_path in backup_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def cleanup_old_backups(self, days: Optional[int] = None):
        """清理过期备份"""
        cutoff_date = datetime.now() - timedelta(days=days or 30)

        for config_name, config in self.backup_configs.items():
            if not config.destination_dir.exists():
                continue

            deleted_count = 0
            for backup_dir in config.destination_dir.iterdir():
                if backup_dir.is_dir():
                    # 尝试从目录名解析时间戳
                    try:
                        timestamp = datetime.strptime(backup_dir.name, "%Y%m%d_%H%M%S")
                        if timestamp < cutoff_date:
                            print(f"🗑️ 删除过期备份: {backup_dir}")
                            shutil.rmtree(backup_dir)
                            deleted_count += 1
                    except ValueError:
                        continue

            if deleted_count > 0:
                print(f"✅ {config_name}: 删除了 {deleted_count} 个过期备份")

    def list_backups(self, config_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """列出所有备份"""
        backups = {}

        configs_to_check = [config_name] if config_name else list(self.backup_configs.keys())

        for name in configs_to_check:
            if name not in self.backup_configs:
                continue

            config = self.backup_configs[name]
            config_backups = []

            if config.destination_dir.exists():
                for backup_dir in sorted(config.destination_dir.iterdir(),
                                        key=lambda x: x.name,
                                        reverse=True):
                    if backup_dir.is_dir():
                        manifest_file = backup_dir / "manifest.json"
                        if manifest_file.exists():
                            with open(manifest_file, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                            config_backups.append({
                                "timestamp": manifest["timestamp"],
                                "files": len(manifest["files"]),
                                "size": self._get_backup_size(backup_dir),
                                "encrypted": manifest.get("encrypted", False),
                                "path": backup_dir
                            })

            backups[name] = config_backups

        return backups

    def backup_all(self, password: Optional[str] = None) -> bool:
        """备份所有配置"""
        success = True
        for config_name in self.backup_configs.keys():
            if not self.backup_configuration(config_name, password):
                success = False

        return success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description = os.getenv("BACKUP_CONFIG_DESCRIPTION_437"))
    parser.add_argument('command', choices=[
        'backup', 'restore', 'list', 'cleanup', 'backup-all'
    ], help = os.getenv("BACKUP_CONFIG_HELP_444"))

    parser.add_argument('--config', '-c', help="配置名称")
    parser.add_argument('--timestamp', '-t', help="备份时间戳")
    parser.add_argument('--password', '-p', action = os.getenv("BACKUP_CONFIG_ACTION_449"), help="使用密码")
    parser.add_argument('--force', '-f', action = os.getenv("BACKUP_CONFIG_ACTION_449"), help="强制覆盖")
    parser.add_argument('--days', '-d', type=int, default=30, help="保留天数")

    args = parser.parse_args()

    # 初始化备份管理器
    backup_manager = ConfigBackup()

    # 获取密码
    password = None
    if args.password:
        import getpass
        password = getpass.getpass("请输入密码: ")

    # 执行命令
    if args.command == 'backup':
        if not args.config:
            print("❌ 需要指定配置名称")
            sys.exit(1)
        backup_manager.backup_configuration(args.config, password)

    elif args.command == 'restore':
        if not args.config:
            print("❌ 需要指定配置名称")
            sys.exit(1)
        backup_manager.restore_configuration(
            args.config, args.timestamp, password, args.force
        )

    elif args.command == 'list':
        backups = backup_manager.list_backups(args.config)
        for config_name, config_backups in backups.items():
            print(f"\n📁 {config_name}:")
            if config_backups:
                for backup in config_backups[:10]:  # 只显示最近10个
                    size_mb = backup["size"] / (1024 * 1024)
                    print(f"  📅 {backup['timestamp']} - "
                          f"{backup['files']} 文件, "
                          f"{size_mb:.2f} MB "
                          f"{'🔒' if backup['encrypted'] else ''}")
            else:
                print("  (无备份)")

    elif args.command == 'cleanup':
        backup_manager.cleanup_old_backups(args.days)

    elif args.command == 'backup-all':
        backup_manager.backup_all(password)


if __name__ == "__main__":
    main()