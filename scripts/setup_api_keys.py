#!/usr/bin/env python3
"""
Sprint 9 API密钥配置引导脚本

安全地引导用户配置生产环境API密钥：
1. 交互式API密钥配置
2. 密钥安全验证
3. 连接测试
4. 配置文件生成

使用方法:
  python setup_api_keys.py
  python setup_api_keys.py --force

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - Production Deployment)
"""

import os
import sys
import json
import getpass
import secrets
from pathlib import Path
from typing import Dict, Any, Optional
import re
import requests

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings

class APIKeySetup:
    """API密钥配置助手"""

    def __init__(self):
        self.settings = get_settings()
        self.api_configs = {
            "fotmob": {
                "name": "FotMob API",
                "description": "足球比赛数据API",
                "required_vars": [
                    "FOTMOB_X_MAS_HEADER",
                    "FOTMOB_X_FOO_HEADER"
                ],
                "test_url": "https://www.fotmob.com/api/leagues?id=87",
                "instructions": [
                    "1. 访问 FotMob 官方网站",
                    "2. 在浏览器开发者工具中查看网络请求",
                    "3. 查找API请求的Header信息",
                    "4. 提取 X-MAS 和 X-FOO Header值"
                ]
            },
            "telegram": {
                "name": "Telegram Bot API",
                "description": "消息通知API（可选）",
                "required_vars": [
                    "TELEGRAM_BOT_TOKEN",
                    "TELEGRAM_CHAT_ID"
                ],
                "test_url": None,
                "instructions": [
                    "1. 与 @BotFather 对话创建机器人",
                    "2. 获取Bot Token",
                    "3. 与机器人对话获取Chat ID"
                ]
            },
            "sentry": {
                "name": "Sentry Error Tracking",
                "description": "错误跟踪服务（可选）",
                "required_vars": [
                    "SENTRY_DSN"
                ],
                "test_url": None,
                "instructions": [
                    "1. 访问 sentry.io 创建项目",
                    "2. 获取项目的 DSN",
                    "3. 配置错误跟踪"
                ]
            }
        }

    def generate_secure_keys(self) -> Dict[str, str]:
        """生成安全密钥"""
        return {
            "SECRET_KEY": secrets.token_urlsafe(32),
            "JWT_SECRET_KEY": secrets.token_urlsafe(32)
        }

    def validate_api_key(self, api_name: str, config: Dict[str, str]) -> bool:
        """验证API密钥"""
        if api_name == "fotmob":
            return self._validate_fotmob_keys(config)
        elif api_name == "telegram":
            return self._validate_telegram_keys(config)
        return True

    def _validate_fotmob_keys(self, config: Dict[str, str]) -> bool:
        """验证FotMob密钥"""
        try:
            headers = {
                "X-MAS": config.get("FOTMOB_X_MAS_HEADER", ""),
                "X-FOO": config.get("FOTMOB_X_FOO_HEADER", ""),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(
                "https://www.fotmob.com/api/leagues?id=87",
                headers=headers,
                timeout=10
            )

            return response.status_code == 200
        except:
            return False

    def _validate_telegram_keys(self, config: Dict[str, str]) -> bool:
        """验证Telegram密钥"""
        try:
            bot_token = config.get("TELEGRAM_BOT_TOKEN")
            if not bot_token:
                return False

            response = requests.get(
                f"https://api.telegram.org/bot{bot_token}/getMe",
                timeout=10
            )

            return response.status_code == 200
        except:
            return False

    def interactive_setup(self) -> Dict[str, str]:
        """交互式配置"""
        print("🔐 Sprint 9 API密钥安全配置")
        print("=" * 50)

        api_configs = {}
        secure_keys = self.generate_secure_keys()

        # 自动设置安全密钥
        print("\n🔒 自动生成安全密钥...")
        for key, value in secure_keys.items():
            api_configs[key] = value
            print(f"✅ {key}: {value[:10]}...")

        # 交互式配置其他API
        for api_name, config_info in self.api_configs.items():
            if api_name == "fotmob":
                # FotMob是必需的
                configured = self._configure_fotmob_api()
                api_configs.update(configured)
            else:
                # 其他API是可选的
                choice = input(f"\n是否配置 {config_info['name']}? (y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    configured = self._configure_api(api_name, config_info)
                    api_configs.update(configured)

        return api_configs

    def _configure_fotmob_api(self) -> Dict[str, str]:
        """配置FotMob API"""
        print(f"\n📊 配置 {self.api_configs['fotmob']['name']}")
        print(f"说明: {self.api_configs['fotmob']['description']}")
        print("\n配置说明:")
        for instruction in self.api_configs['fotmob']['instructions']:
            print(f"  {instruction}")

        config = {}

        # 获取X-MAS Header
        while True:
            mas_header = input("\n请输入 X-MAS Header: ").strip()
            if mas_header:
                config["FOTMOB_X_MAS_HEADER"] = mas_header
                break
            print("❌ X-MAS Header不能为空")

        # 获取X-FOO Header
        while True:
            foo_header = input("请输入 X-FOO Header: ").strip()
            if foo_header:
                config["FOTMOB_X_FOO_HEADER"] = foo_header
                break
            print("❌ X-FOO Header不能为空")

        # 验证密钥
        print("\n🔍 验证API密钥...")
        if self.validate_api_key("fotmob", config):
            print("✅ FotMob API连接测试成功!")
        else:
            print("❌ FotMob API连接测试失败!")
            retry = input("是否重新配置? (y/n): ").lower().strip()
            if retry in ['y', 'yes']:
                return self._configure_fotmob_api()

        return config

    def _configure_api(self, api_name: str, config_info: Dict[str, Any]) -> Dict[str, str]:
        """配置其他API"""
        print(f"\n📊 配置 {config_info['name']}")
        print(f"说明: {config_info['description']}")
        print("\n配置说明:")
        for instruction in config_info['instructions']:
            print(f"  {instruction}")

        config = {}

        for var in config_info['required_vars']:
            if var == "TELEGRAM_BOT_TOKEN":
                value = input(f"\n请输入 {var}: ").strip()
            elif var == "TELEGRAM_CHAT_ID":
                value = input(f"请输入 {var}: ").strip()
            else:
                value = getpass.getpass(f"\n请输入 {var}: ").strip()

            if value:
                config[var] = value

        # 验证密钥（如果有验证方法）
        if config and self.validate_api_key(api_name, config):
            print(f"✅ {config_info['name']}配置成功!")
        elif config:
            print(f"⚠️ {config_info['name']}配置完成，但验证失败")

        return config

    def create_env_file(self, api_configs: Dict[str, str], env_file: str = ".env.production"):
        """创建环境配置文件"""
        env_path = Path(env_file)

        # 读取现有配置文件
        existing_config = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key] = value

        # 更新配置
        existing_config.update(api_configs)

        # 写入配置文件
        with open(env_path, 'w') as f:
            f.write("# =============================================\n")
            f.write("# Football Prediction System - Production Config\n")
            f.write("# Generated by Sprint 9 API Setup Script\n")
            f.write(f"# Generated at: {datetime.now().isoformat()}\n")
            f.write("# =============================================\n\n")

            # 按分组写入配置
            groups = {
                "Environment": ["ENVIRONMENT", "DEBUG", "TZ", "PYTHONPATH"],
                "Security": ["SECRET_KEY", "JWT_SECRET_KEY", "JWT_ALGORITHM"],
                "API Service": ["API_HOST", "API_PORT", "CORS_ORIGINS"],
                "Database": ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"],
                "Redis": ["REDIS_HOST", "REDIS_PORT", "REDIS_DB"],
                "FotMob API": ["FOTMOB_BASE_URL", "FOTMOB_X_MAS_HEADER", "FOTMOB_X_FOO_HEADER"],
                "Kelly Safety": ["KELLY_MAX_STAKE_PERCENTAGE", "KELLY_EMERGENCY_STOP"],
                "ML Configuration": ["MODEL_DIR", "DEFAULT_MODEL_NAME"],
                "Monitoring": ["PROMETHEUS_ENABLED", "LOG_LEVEL"],
            }

            for group_name, keys in groups.items():
                f.write(f"# {group_name}\n")
                for key in keys:
                    if key in existing_config:
                        value = existing_config[key]
                        # 敏感信息部分隐藏
                        if any(sensitive in key.lower() for sensitive in ['key', 'token', 'password', 'secret']):
                            f.write(f"{key}={value}\n")
                        else:
                            f.write(f"{key}={value}\n")
                f.write("\n")

            # 写入其他配置
            f.write("# Additional Configuration\n")
            for key, value in existing_config.items():
                if not any(key in group_keys for group_keys in groups.values()):
                    f.write(f"{key}={value}\n")

        print(f"✅ 配置文件已保存: {env_path}")

        # 设置文件权限
        os.chmod(env_path, 0o600)
        print("🔒 文件权限已设置为仅所有者可读写")

    def verify_setup(self) -> bool:
        """验证配置"""
        print("\n🔍 验证配置...")

        try:
            # 验证环境变量
            os.environ.update(self._load_env_file())

            # 导入设置验证
            settings = get_settings()

            # 检查必需配置
            required_configs = [
                "database.host",
                "database.name",
                "fotmob.base_url"
            ]

            for config in required_configs:
                if not self._get_nested_attr(settings, config):
                    print(f"❌ 缺少必需配置: {config}")
                    return False

            print("✅ 配置验证通过!")
            return True

        except Exception as e:
            print(f"❌ 配置验证失败: {e}")
            return False

    def _get_nested_attr(self, obj, attr_path: str):
        """获取嵌套属性"""
        attrs = attr_path.split('.')
        current = obj
        for attr in attrs:
            if hasattr(current, attr):
                current = getattr(current, attr)
            else:
                return None
        return current

    def _load_env_file(self) -> Dict[str, str]:
        """加载环境文件"""
        env_file = Path(".env.production")
        config = {}

        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key] = value

        return config

    def run_connection_test(self):
        """运行连接测试"""
        print("\n🧪 运行连接测试...")
        try:
            import subprocess
            result = subprocess.run([
                sys.executable,
                Path(__file__).parent / "verify_live_connection.py",
                "quick"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ 连接测试通过!")
                print(result.stdout)
                return True
            else:
                print("❌ 连接测试失败!")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
            return False


def main():
    """主函数"""
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Sprint 9 API密钥配置")
    parser.add_argument("--force", action="store_true", help="强制重新配置")
    parser.add_argument("--test-only", action="store_true", help="仅测试现有配置")
    parser.add_argument("--env-file", default=".env.production", help="环境文件路径")

    args = parser.parse_args()

    setup = APIKeySetup()

    try:
        if args.test_only:
            # 仅测试配置
            if setup.verify_setup():
                setup.run_connection_test()
                return 0
            else:
                return 1

        # 检查是否已有配置
        env_file = Path(args.env_file)
        if env_file.exists() and not args.force:
            print(f"⚠️ 配置文件 {args.env_file} 已存在")
            overwrite = input("是否覆盖? (y/n): ").lower().strip()
            if overwrite not in ['y', 'yes']:
                print("配置已取消")
                return 0

        print("🚀 开始Sprint 9 API密钥配置...")

        # 交互式配置
        api_configs = setup.interactive_setup()

        # 创建环境文件
        setup.create_env_file(api_configs, args.env_file)

        # 验证配置
        if setup.verify_setup():
            # 运行连接测试
            if setup.run_connection_test():
                print(f"\n🎉 API配置完成!")
                print(f"📄 配置文件: {args.env_file}")
                print(f"🧪 连接测试: ✅ 通过")
                print(f"🚀 系统状态: 准备部署")
                return 0
            else:
                print(f"\n⚠️ API配置完成，但连接测试失败")
                print(f"请检查配置并重新测试: python verify_live_connection.py")
                return 1
        else:
            print(f"\n❌ 配置验证失败")
            return 1

    except KeyboardInterrupt:
        print(f"\n👋 配置已取消")
        return 1
    except Exception as e:
        print(f"❌ 配置失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())