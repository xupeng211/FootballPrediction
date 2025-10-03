#!/usr/bin/env python3
"""
配置加密存储工具
Configuration Encryption Storage Utility

提供配置文件的加密存储和解密功能
"""

import os
import sys
import json
import base64
import getpass
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ConfigCrypto:
    """配置加密管理器"""

    def __init__(self, key_file: Optional[Path] = None):
        """
        初始化加密管理器

        Args:
            key_file: 密钥文件路径，如果为None则使用默认位置
        """
        self.key_file = key_file or project_root / ".config_key"
        self._key: Optional[bytes] = None

    def _generate_key_from_password(self, password: str, salt: bytes) -> bytes:
        """从密码生成密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _load_or_create_key(self, password: Optional[str] = None) -> bytes:
        """加载或创建密钥"""
        if self._key:
            return self._key

        if self.key_file.exists():
            # 加载现有密钥
            with open(self.key_file, 'rb') as f:
                self._key = f.read()
        else:
            # 创建新密钥
            if password:
                # 使用密码派生密钥
                salt = os.urandom(16)
                self._key = self._generate_key_from_password(password, salt)
                # 保存盐值
                salt_file = self.key_file.with_suffix('.salt')
                with open(salt_file, 'wb') as f:
                    f.write(salt)
            else:
                # 生成随机密钥
                self._key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(self._key)

            # 设置文件权限为只有所有者可读写
            os.chmod(self.key_file, 0o600)

        return self._key

    def encrypt_config(self, config: Dict[str, Any],
                      output_file: Path,
                      password: Optional[str] = None) -> bool:
        """
        加密配置文件

        Args:
            config: 配置字典
            output_file: 输出文件路径
            password: 可选的密码

        Returns:
            是否成功
        """
        try:
            key = self._load_or_create_key(password)
            fernet = Fernet(key)

            # 序列化配置
            config_json = json.dumps(config, indent=2, ensure_ascii=False)
            config_bytes = config_json.encode('utf-8')

            # 加密
            encrypted_data = fernet.encrypt(config_bytes)

            # 保存加密文件
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'wb') as f:
                f.write(encrypted_data)

            # 设置权限
            os.chmod(output_file, 0o600)

            print(f"✅ 配置已加密保存到: {output_file}")
            return True

        except Exception as e:
            print(f"❌ 加密失败: {e}")
            return False

    def decrypt_config(self, input_file: Path,
                      password: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        解密配置文件

        Args:
            input_file: 输入文件路径
            password: 可选的密码

        Returns:
            解密后的配置字典，失败返回None
        """
        try:
            key = self._load_or_create_key(password)
            fernet = Fernet(key)

            # 读取加密文件
            with open(input_file, 'rb') as f:
                encrypted_data = f.read()

            # 解密
            decrypted_data = fernet.decrypt(encrypted_data)
            config_json = decrypted_data.decode('utf-8')

            # 反序列化
            config = json.loads(config_json)

            print(f"✅ 配置已成功解密")
            return config

        except Exception as e:
            print(f"❌ 解密失败: {e}")
            return None

    def encrypt_env_file(self, env_file: Path,
                        output_file: Path,
                        password: Optional[str] = None) -> bool:
        """
        加密.env文件

        Args:
            env_file: .env文件路径
            output_file: 输出文件路径
            password: 可选的密码

        Returns:
            是否成功
        """
        try:
            # 解析.env文件
            config = {}
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

            return self.encrypt_config(config, output_file, password)

        except Exception as e:
            print(f"❌ 加密.env文件失败: {e}")
            return False

    def decrypt_to_env_file(self, input_file: Path,
                           output_file: Path,
                           password: Optional[str] = None) -> bool:
        """
        解密到.env文件

        Args:
            input_file: 加密文件路径
            output_file: 输出.env文件路径
            password: 可选的密码

        Returns:
            是否成功
        """
        try:
            config = self.decrypt_config(input_file, password)
            if config is None:
                return False

            # 写入.env文件
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 自动生成的环境配置文件\n")
                f.write("# 请勿手动编辑\n\n")
                for key, value in config.items():
                    # 敏感信息使用星号遮蔽显示
                    if 'SECRET' in key or 'PASSWORD' in key or 'KEY' in key:
                        display_value = f"'{value}'"
                    else:
                        display_value = value
                    f.write(f"{key}={display_value}\n")

            # 设置权限
            os.chmod(output_file, 0o600)

            print(f"✅ 环境配置已保存到: {output_file}")
            return True

        except Exception as e:
            print(f"❌ 解密到.env文件失败: {e}")
            return False

    def create_backup(self, source_file: Path,
                     backup_dir: Path,
                     password: Optional[str] = None) -> bool:
        """
        创建加密备份

        Args:
            source_file: 源文件路径
            backup_dir: 备份目录
            password: 可选的密码

        Returns:
            是否成功
        """
        try:
            import datetime

            # 创建备份目录
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 生成备份文件名（包含时间戳）
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{source_file.stem}_{timestamp}.enc"
            backup_file = backup_dir / backup_filename

            # 根据文件类型选择加密方法
            if source_file.suffix == '.env':
                return self.encrypt_env_file(source_file, backup_file, password)
            else:
                # 读取配置
                if source_file.suffix in ['.yml', '.yaml']:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                else:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                return self.encrypt_config(config, backup_file, password)

        except Exception as e:
            print(f"❌ 创建备份失败: {e}")
            return False

    def list_encrypted_files(self, directory: Path) -> list[Path]:
        """列出目录中的加密文件"""
        return list(directory.glob("*.enc"))

    def delete_key(self):
        """删除密钥文件"""
        if self.key_file.exists():
            os.remove(self.key_file)
            # 删除盐值文件
            salt_file = self.key_file.with_suffix('.salt')
            if salt_file.exists():
                os.remove(salt_file)
            print(f"✅ 密钥文件已删除")
        else:
            print(f"⚠️ 密钥文件不存在")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置加密存储工具")
    parser.add_argument('command', choices=[
        'encrypt', 'decrypt', 'encrypt-env', 'decrypt-env',
        'backup', 'list', 'delete-key'
    ], help="要执行的命令")

    parser.add_argument('--input', '-i', type=Path, help="输入文件路径")
    parser.add_argument('--output', '-o', type=Path, help="输出文件路径")
    parser.add_argument('--backup-dir', '-b', type=Path,
                       default=project_root / "backups",
                       help="备份目录")
    parser.add_argument('--password', '-p', action='store_true',
                       help="使用密码保护")
    parser.add_argument('--key-file', '-k', type=Path,
                       help="自定义密钥文件路径")

    args = parser.parse_args()

    # 初始化加密管理器
    crypto = ConfigCrypto(args.key_file)

    # 获取密码（如果需要）
    password = None
    if args.password:
        password = getpass.getpass("请输入密码: ")

    # 执行命令
    if args.command == 'encrypt':
        if not args.input or not args.output:
            print("❌ 需要指定输入和输出文件")
            sys.exit(1)
        crypto.encrypt_config(
            json.load(args.input.open()),
            args.output,
            password
        )

    elif args.command == 'decrypt':
        if not args.input:
            print("❌ 需要指定输入文件")
            sys.exit(1)
        config = crypto.decrypt_config(args.input, password)
        if config:
            if args.output:
                json.dump(config, args.output.open('w', encoding='utf-8'),
                         indent=2, ensure_ascii=False)
                print(f"✅ 解密内容已保存到: {args.output}")
            else:
                print(json.dumps(config, indent=2, ensure_ascii=False))

    elif args.command == 'encrypt-env':
        if not args.input or not args.output:
            print("❌ 需要指定输入和输出文件")
            sys.exit(1)
        crypto.encrypt_env_file(args.input, args.output, password)

    elif args.command == 'decrypt-env':
        if not args.input or not args.output:
            print("❌ 需要指定输入和输出文件")
            sys.exit(1)
        crypto.decrypt_to_env_file(args.input, args.output, password)

    elif args.command == 'backup':
        if not args.input:
            print("❌ 需要指定要备份的文件")
            sys.exit(1)
        crypto.create_backup(args.input, args.backup_dir, password)

    elif args.command == 'list':
        backup_dir = args.backup_dir or project_root / "backups"
        encrypted_files = crypto.list_encrypted_files(backup_dir)
        if encrypted_files:
            print(f"📁 {backup_dir} 中的加密文件:")
            for file in encrypted_files:
                print(f"  - {file.name}")
        else:
            print(f"📁 {backup_dir} 中没有加密文件")

    elif args.command == 'delete-key':
        crypto.delete_key()


if __name__ == "__main__":
    main()