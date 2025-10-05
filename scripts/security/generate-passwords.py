#!/usr/bin/env python3
"""
强密码生成脚本
用于为FootballPrediction项目生成安全的随机密码
"""

import argparse
import json
import secrets
import string
from typing import Any, Dict


class SecurePasswordGenerator:
    """安全密码生成器"""

    def __init__(self):
        # 定义不同强度的字符集
        self.lowercase = string.ascii_lowercase
        self.uppercase = string.ascii_uppercase
        self.digits = string.digits
        self.special_safe = "!@#$%^&*()_+-="  # 安全的特殊字符
        self.special_extended = "!@#$%^&*()_+-=[]{}|;:,.<>?"  # 扩展特殊字符

    def generate_password(
        self,
        length: int = 32,
        use_extended_special: bool = False,
        min_lowercase: int = 2,
        min_uppercase: int = 2,
        min_digits: int = 2,
        min_special: int = 2,
    ) -> str:
        """
        生成符合安全要求的随机密码

        Args:
            length: 密码长度
            use_extended_special: 是否使用扩展特殊字符
            min_lowercase: 最少小写字母数
            min_uppercase: 最少大写字母数
            min_digits: 最少数字数
            min_special: 最少特殊字符数

        Returns:
            生成的密码字符串
        """
        if length < (min_lowercase + min_uppercase + min_digits + min_special):
            raise ValueError(f"密码长度 {length} 不足以满足最低字符要求")

        special_chars = (
            self.special_extended if use_extended_special else self.special_safe
        )
        all_chars = self.lowercase + self.uppercase + self.digits + special_chars

        # 确保密码包含每种类型的最小字符数
        password_chars = []
        password_chars.extend(
            secrets.choice(self.lowercase) for _ in range(min_lowercase)
        )
        password_chars.extend(
            secrets.choice(self.uppercase) for _ in range(min_uppercase)
        )
        password_chars.extend(secrets.choice(self.digits) for _ in range(min_digits))
        password_chars.extend(secrets.choice(special_chars) for _ in range(min_special))

        # 用随机字符填充剩余长度
        remaining_length = length - len(password_chars)
        password_chars.extend(
            secrets.choice(all_chars) for _ in range(remaining_length)
        )

        # 随机打乱字符顺序
        for i in range(len(password_chars)):
            j = secrets.randbelow(len(password_chars))
            password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

        return "".join(password_chars)

    def generate_jwt_secret(self, length: int = 64) -> str:
        """生成JWT密钥"""
        return self.generate_password(length, use_extended_special=True)

    def generate_db_password(self, length: int = 32) -> str:
        """生成数据库密码"""
        return self.generate_password(length, use_extended_special=False)

    def generate_service_password(self, length: int = 32) -> str:
        """生成服务密码"""
        return self.generate_password(length, use_extended_special=False)


def generate_all_passwords() -> Dict[str, Any]:
    """生成项目所需的所有密码"""
    generator = SecurePasswordGenerator()

    passwords = {
        # 数据库密码
        "DB_PASSWORD": generator.generate_db_password(32),
        "POSTGRES_PASSWORD": generator.generate_db_password(32),
        "DB_READER_PASSWORD": generator.generate_db_password(32),
        "DB_WRITER_PASSWORD": generator.generate_db_password(32),
        "DB_ADMIN_PASSWORD": generator.generate_db_password(32),
        # Redis密码
        "REDIS_PASSWORD": generator.generate_service_password(32),
        # MinIO密码
        "MINIO_ROOT_PASSWORD": generator.generate_service_password(32),
        "MINIO_SECRET_KEY": generator.generate_service_password(32),
        # 监控系统密码
        "GRAFANA_ADMIN_PASSWORD": generator.generate_service_password(32),
        "MARQUEZ_DB_PASSWORD": generator.generate_service_password(32),
        "MLFLOW_DB_PASSWORD": generator.generate_service_password(32),
        # 应用安全密钥
        "JWT_SECRET_KEY": generator.generate_jwt_secret(64),
        # 用户账号
        "MINIO_ROOT_USER": "football_minio_admin",
        "MARQUEZ_DB_USER": "marquez_user",
        "MLFLOW_DB_USER": "mlflow_user",
    }

    return passwords


def generate_env_file(passwords: Dict[str, str], output_file: str = "env.secure"):
    """生成环境变量文件"""
    template = f"""# ==================================================
# 足球预测系统安全环境配置
# 自动生成于 {secrets.token_hex(8)}
# ==================================================

# 应用环境设置
ENVIRONMENT=production

# ==================================================
# 数据库配置
# ==================================================
DB_HOST=db
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD={passwords['DB_PASSWORD']}

POSTGRES_DB=football_prediction_dev
POSTGRES_USER=football_user
POSTGRES_PASSWORD={passwords['POSTGRES_PASSWORD']}

DB_READER_USER=football_reader
DB_READER_PASSWORD={passwords['DB_READER_PASSWORD']}

DB_WRITER_USER=football_writer
DB_WRITER_PASSWORD={passwords['DB_WRITER_PASSWORD']}

DB_ADMIN_USER=football_admin
DB_ADMIN_PASSWORD={passwords['DB_ADMIN_PASSWORD']}

# ==================================================
# Redis 配置
# ==================================================
REDIS_PASSWORD={passwords['REDIS_PASSWORD']}
REDIS_URL=redis://:{passwords['REDIS_PASSWORD']}@redis:6379/0

# ==================================================
# MinIO 对象存储配置
# ==================================================
MINIO_ROOT_USER={passwords['MINIO_ROOT_USER']}
MINIO_ROOT_PASSWORD={passwords['MINIO_ROOT_PASSWORD']}
MINIO_SECRET_KEY={passwords['MINIO_SECRET_KEY']}

# ==================================================
# 监控系统配置
# ==================================================
GRAFANA_ADMIN_PASSWORD={passwords['GRAFANA_ADMIN_PASSWORD']}
MARQUEZ_DB_USER={passwords['MARQUEZ_DB_USER']}
MARQUEZ_DB_PASSWORD={passwords['MARQUEZ_DB_PASSWORD']}
MLFLOW_DB_USER={passwords['MLFLOW_DB_USER']}
MLFLOW_DB_PASSWORD={passwords['MLFLOW_DB_PASSWORD']}

# ==================================================
# 应用安全配置
# ==================================================
JWT_SECRET_KEY={passwords['JWT_SECRET_KEY']}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# ==================================================
# Celery 配置
# ==================================================
CELERY_BROKER_URL=redis://:{passwords['REDIS_PASSWORD']}@redis:6379/0
CELERY_RESULT_BACKEND=redis://:{passwords['REDIS_PASSWORD']}@redis:6379/0

# ==================================================
# 其他配置
# ==================================================
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# 警告：此文件包含敏感信息，请勿提交到版本控制系统！
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"✅ 安全环境配置文件已生成: {output_file}")
    print("⚠️  请确保文件权限设置为 600 (仅所有者可读写)")
    print(f"   命令: chmod 600 {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FootballPrediction项目强密码生成器")
    parser.add_argument(
        "--format",
        choices=["env", "json", "text"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument("--output", type=str, help="输出文件名")
    parser.add_argument("--length", type=int, default=32, help="密码长度 (默认: 32)")

    args = parser.parse_args()

    print("🔐 生成强随机密码...")
    passwords = generate_all_passwords()

    if args.format == "json":
        output = json.dumps(passwords, indent=2, ensure_ascii=False)
        print(output)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"✅ JSON格式密码已保存到: {args.output}")

    elif args.format == "env":
        output_file = args.output or "env.secure"
        generate_env_file(passwords, output_file)

    else:  # text format
        print("\n🔑 生成的强随机密码:")
        print("=" * 60)
        for key, value in passwords.items():
            print(f"{key}={value}")
        print("=" * 60)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                for key, value in passwords.items():
                    f.write(f"{key}={value}\n")
            print(f"✅ 密码已保存到: {args.output}")

    print("\n🛡️  安全提醒:")
    print("1. 请立即复制这些密码到安全的位置")
    print("2. 不要将密码提交到版本控制系统")
    print("3. 定期轮换密码（建议90天）")
    print("4. 使用密钥管理服务存储生产环境密码")


if __name__ == "__main__":
    main()
