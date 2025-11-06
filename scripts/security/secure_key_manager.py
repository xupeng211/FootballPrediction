#!/usr/bin/env python3
"""
🔒 安全密钥管理器
用于生成、轮换和管理系统中的敏感密钥和密码
"""

import os
import sys
import secrets
import string
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecureKeyManager:
    """安全密钥管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = project_root

        self.backup_dir = self.project_root / "backups" / "security"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def generate_secure_key(self, length: int = 64) -> str:
        """生成安全密钥"""
        return secrets.token_urlsafe(length)

    def generate_strong_password(self, length: int = 32) -> str:
        """生成强密码"""
        chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
        return ''.join(secrets.choice(chars) for _ in range(length))

    def generate_api_key(self, prefix: str = "fp", length: int = 32) -> str:
        """生成API密钥"""
        random_part = secrets.token_urlsafe(length)
        return f"{prefix}_{random_part}"

    def generate_all_keys(self) -> Dict[str, str]:
        """生成所有需要的密钥"""
        keys = {
            'JWT_SECRET_KEY': self.generate_secure_key(64),
            'SECRET_KEY': self.generate_secure_key(64),
            'API_KEY': self.generate_api_key("fp", 32),
            'API_SECRET_KEY': self.generate_api_key("fp_secret", 32),
            'DB_PASSWORD': self.generate_strong_password(32),
            'REDIS_PASSWORD': self.generate_strong_password(32),
            'GRAFANA_PASSWORD': self.generate_strong_password(32),
            'JWT_REFRESH_SECRET_KEY': self.generate_secure_key(64),
            'ENCRYPTION_KEY': self.generate_secure_key(32),
        }

        # 记录生成时间
        keys['generated_at'] = datetime.now().isoformat()
        keys['next_rotation'] = (datetime.now() + timedelta(days=30)).isoformat()

        return keys

    def backup_current_config(self, env_file: str) -> Path:
        """备份当前配置文件"""
        env_path = self.project_root / env_file
        if env_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{env_file}.backup.{timestamp}"

            # 复制文件
            with open(env_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            logger.info(f"配置文件已备份: {backup_path}")
            return backup_path
        else:
            logger.warning(f"配置文件不存在: {env_path}")
            return Path()

    def rotate_keys(self, env_file: str = ".env") -> bool:
        """轮换密钥"""
        try:
            # 备份当前配置
            backup_path = self.backup_current_config(env_file)

            # 生成新密钥
            new_keys = self.generate_all_keys()

            # 读取当前配置
            env_path = self.project_root / env_file
            if not env_path.exists():
                logger.error(f"配置文件不存在: {env_path}")
                return False

            # 更新配置文件
            self._update_env_file(env_path, new_keys)

            # 保存密钥轮换记录
            self._save_rotation_record(env_file, new_keys, backup_path)

            logger.info(f"密钥轮换完成: {env_file}")
            return True

        except Exception as e:
            logger.error(f"密钥轮换失败: {e}")
            return False

    def _update_env_file(self, env_path: Path, new_keys: Dict[str, str]):
        """更新环境变量文件"""
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 更新密钥
        for key, value in new_keys.items():
            if key in ['generated_at', 'next_rotation']:
                continue

            # 查找并替换现有密钥
            import re
            pattern = rf'^{key}=.*$'
            replacement = f'{key}={value}'

            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                # 如果找不到，添加到文件末尾
                content += f'\n{key}={value}\n'

        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _save_rotation_record(self, env_file: str, new_keys: Dict[str, str], backup_path: Path):
        """保存密钥轮换记录"""
        record = {
            'env_file': env_file,
            'backup_file': str(backup_path),
            'rotated_keys': {k: v for k, v in new_keys.items() if k not in ['generated_at', 'next_rotation']},
            'rotation_time': new_keys['generated_at'],
            'next_rotation': new_keys['next_rotation'],
            'status': 'completed'
        }

        # 保存到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_path = self.backup_dir / f"key_rotation_{env_file}_{timestamp}.json"

        with open(record_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        logger.info(f"密钥轮换记录已保存: {record_path}")

    def check_key_age(self, env_file: str) -> Dict[str, Any]:
        """检查密钥年龄"""
        # 查找最近的轮换记录
        record_files = list(self.backup_dir.glob(f"key_rotation_{env_file}_*.json"))

        if not record_files:
            return {'status': 'no_records', 'message': '未找到密钥轮换记录'}

        # 获取最新的记录
        latest_record = max(record_files, key=lambda x: x.stat().st_mtime)

        with open(latest_record, 'r', encoding='utf-8') as f:
            record = json.load(f)

        rotation_time = datetime.fromisoformat(record['rotation_time'])
        next_rotation = datetime.fromisoformat(record['next_rotation'])
        current_time = datetime.now()

        days_since_rotation = (current_time - rotation_time).days
        days_until_next_rotation = (next_rotation - current_time).days

        return {
            'status': 'found',
            'last_rotation': rotation_time.isoformat(),
            'days_since_rotation': days_since_rotation,
            'next_rotation': next_rotation.isoformat(),
            'days_until_next_rotation': days_until_next_rotation,
            'needs_rotation': days_until_next_rotation <= 0,
            'record_file': str(latest_record)
        }

    def validate_security(self) -> Dict[str, Any]:
        """验证安全配置"""
        issues = []

        # 检查 .gitignore
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()

            required_entries = ['.env', '.env.production', '.env.local']
            for entry in required_entries:
                if entry not in gitignore_content:
                    issues.append(f"缺少 .gitignore 条目: {entry}")
        else:
            issues.append("缺少 .gitignore 文件")

        # 检查环境文件权限
        for env_file in ['.env', '.env.production']:
            env_path = self.project_root / env_file
            if env_path.exists():
                # 检查文件权限 (应该在600或更严格)
                stat_info = env_path.stat()
                mode = oct(stat_info.st_mode)[-3:]
                if mode != '600':
                    issues.append(f"文件权限过于宽松: {env_file} ({mode})")

        # 检查密钥强度
        env_files_to_check = ['.env', '.env.production']
        for env_file in env_files_to_check:
            env_path = self.project_root / env_file
            if env_path.exists():
                weak_keys = self._check_key_strength(env_path)
                if weak_keys:
                    issues.extend([f"{env_file}: {key}" for key in weak_keys])

        return {
            'status': 'passed' if not issues else 'issues_found',
            'issues': issues,
            'total_issues': len(issues)
        }

    def _check_key_strength(self, env_path: Path) -> list:
        """检查密钥强度"""
        weak_keys = []

        with open(env_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)

                    # 检查明显的弱密钥
                    weak_patterns = [
                        'password', 'secret', 'key', 'test', 'demo', 'example',
                        'localhost', '123456', 'admin', 'user', 'default',
                        'CHANGE_ME', 'REPLACE_ME', 'TODO', 'FIXME'
                    ]

                    for pattern in weak_patterns:
                        if pattern.lower() in value.lower():
                            weak_keys.append(f"{key} (line {line_num}): 包含弱模式 '{pattern}'")
                            break

                    # 检查长度
                    if key in ['JWT_SECRET_KEY', 'SECRET_KEY', 'API_SECRET_KEY'] and len(value) < 32:
                        weak_keys.append(f"{key} (line {line_num}): 密钥长度过短 ({len(value)} < 32)")

        return weak_keys

    def fix_file_permissions(self):
        """修复文件权限"""
        env_files = ['.env', '.env.production']

        for env_file in env_files:
            env_path = self.project_root / env_file
            if env_path.exists():
                # 设置为仅所有者可读写 (600)
                os.chmod(env_path, 0o600)
                logger.info(f"文件权限已修复: {env_file} (600)")

    def update_gitignore(self):
        """更新 .gitignore 文件"""
        gitignore_path = self.project_root / ".gitignore"

        required_entries = [
            "# Environment variables",
            ".env",
            ".env.local",
            ".env.development",
            ".env.production",
            ".env.test",
            "",
            "# Security backups",
            "backups/security/",
            "",
            "# Logs",
            "logs/",
            "*.log",
            "",
            "# Cache",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
            ""
        ]

        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                existing_content = f.read()
        else:
            existing_content = ""

        # 添加缺失的条目
        for entry in required_entries:
            if entry and entry not in existing_content:
                existing_content += f"\n{entry}"

        with open(gitignore_path, 'w') as f:
            f.write(existing_content)

        logger.info(" .gitignore 文件已更新")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='安全密钥管理器')
    parser.add_argument('--action', choices=['generate', 'rotate', 'check', 'validate', 'fix-permissions', 'update-gitignore'],
                       required=True, help='执行的操作')
    parser.add_argument('--env-file', default='.env', help='环境变量文件名')
    parser.add_argument('--project-root', help='项目根目录路径')

    args = parser.parse_args()

    # 初始化管理器
    project_root = Path(args.project_root) if args.project_root else None
    manager = SecureKeyManager(project_root)

    if args.action == 'generate':
        print("🔑 生成新密钥:")
        keys = manager.generate_all_keys()
        for key, value in keys.items():
            if key not in ['generated_at', 'next_rotation']:
                print(f"{key}={value}")

    elif args.action == 'rotate':
        print(f"🔄 轮换密钥: {args.env_file}")
        success = manager.rotate_keys(args.env_file)
        if success:
            print("✅ 密钥轮换成功")
        else:
            print("❌ 密钥轮换失败")
            sys.exit(1)

    elif args.action == 'check':
        print(f"🔍 检查密钥年龄: {args.env_file}")
        result = manager.check_key_age(args.env_file)
        if result['status'] == 'found':
            print(f"上次轮换: {result['last_rotation']}")
            print(f"距离下次轮换: {result['days_until_next_rotation']} 天")
            if result['needs_rotation']:
                print("⚠️ 需要轮换密钥")
            else:
                print("✅ 密钥仍然有效")
        else:
            print(f"❌ {result['message']}")

    elif args.action == 'validate':
        print("🔒 验证安全配置:")
        result = manager.validate_security()
        if result['status'] == 'passed':
            print("✅ 安全配置通过验证")
        else:
            print(f"❌ 发现 {result['total_issues']} 个安全问题:")
            for issue in result['issues']:
                print(f"  - {issue}")

    elif args.action == 'fix-permissions':
        print("🔧 修复文件权限:")
        manager.fix_file_permissions()
        print("✅ 文件权限修复完成")

    elif args.action == 'update-gitignore':
        print("📝 更新 .gitignore:")
        manager.update_gitignore()
        print("✅ .gitignore 更新完成")

if __name__ == "__main__":
    main()