#!/usr/bin/env python3
"""
配置验证脚本
Configuration Validation Script

验证生产环境配置的完整性和正确性
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError, field_validator
import subprocess

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """数据库配置验证"""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600

    @field_validator('url')
    def validate_db_url(cls, v):
        if not v:
            raise ValueError("数据库URL不能为空")
        if not v.startswith(('postgresql://', 'sqlite:///')):
            raise ValueError("数据库URL格式无效")
        return v


class RedisConfig(BaseModel):
    """Redis配置验证"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10

    @field_validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("端口号必须在1-65535之间")
        return v


class SecurityConfig(BaseModel):
    """安全配置验证"""
    jwt_secret_key: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @field_validator('jwt_secret_key', 'secret_key')
    def validate_secret_keys(cls, v):
        if not v or len(v) < 32:
            raise ValueError("密钥长度必须至少32个字符")
        return v


class APIConfig(BaseModel):
    """API配置验证"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"

    @field_validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['critical', 'error', 'warning', 'info', 'debug']
        if v.lower() not in valid_levels:
            raise ValueError(f"日志级别必须是: {', '.join(valid_levels)}")
        return v.lower()


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self.env_file = project_root / ".env.production"
        self.required_vars = {
            'DATABASE_URL': str,
            'JWT_SECRET_KEY': str,
            'SECRET_KEY': str,
            'ENVIRONMENT': str,
            'API_HOST': str,
            'API_PORT': int,
        }

        self.optional_vars = {
            'REDIS_URL': str,
            'REDIS_HOST': str,
            'REDIS_PORT': int,
            'REDIS_PASSWORD': str,
            'LOG_LEVEL': str,
            'CORS_ORIGINS': str,
            'SENTRY_DSN': str,
        }

    def validate(self) -> ValidationResult:
        """执行完整验证"""
        result = ValidationResult(
            success=True,
            errors=[],
            warnings=[],
            info=[]
        )

        # 1. 检查.env文件存在
        if not self.env_file.exists():
            result.errors.append(f"环境配置文件不存在: {self.env_file}")
            result.success = False
            return result

        result.info.append(f"找到环境配置文件: {self.env_file}")

        # 2. 加载环境变量
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
            result.info.append("成功加载环境变量")
        except Exception as e:
            result.errors.append(f"加载环境变量失败: {e}")
            result.success = False
            return result

        # 3. 验证必需的环境变量
        for var_name, var_type in self.required_vars.items():
            value = os.getenv(var_name)
            if not value:
                result.errors.append(f"缺少必需的环境变量: {var_name}")
                result.success = False
            else:
                try:
                    # 类型转换验证
                    if var_type == int:
                        int(value)
                    result.info.append(f"✓ {var_name}: {'*' * min(len(value), 8)}")
                except ValueError:
                    result.errors.append(f"环境变量类型错误: {var_name} 应为 {var_type.__name__}")
                    result.success = False

        # 4. 验证可选的环境变量
        for var_name, var_type in self.optional_vars.items():
            value = os.getenv(var_name)
            if value:
                try:
                    if var_type == int:
                        int(value)
                    result.info.append(f"✓ {var_name}: 已设置")
                except ValueError:
                    result.warnings.append(f"环境变量类型错误: {var_name} 应为 {var_type.__name__}")

        # 5. 验证数据库配置
        self._validate_database_config(result)

        # 6. 验证Redis配置
        self._validate_redis_config(result)

        # 7. 验证安全配置
        self._validate_security_config(result)

        # 8. 验证API配置
        self._validate_api_config(result)

        # 9. 检查文件权限
        self._validate_file_permissions(result)

        # 10. 检查依赖安装
        self._validate_dependencies(result)

        return result

    def _validate_database_config(self, result: ValidationResult):
        """验证数据库配置"""
        try:
            db_config = DatabaseConfig(
                url=os.getenv('DATABASE_URL', ''),
                pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
                max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20'))
            )
            result.info.append("✓ 数据库配置有效")

            # 尝试连接测试
            if os.getenv('ENVIRONMENT') != 'development':
                result.warnings.append("建议在生产环境执行数据库连接测试")
        except ValidationError as e:
            result.errors.append(f"数据库配置无效: {e}")
            result.success = False

    def _validate_redis_config(self, result: ValidationResult):
        """验证Redis配置"""
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                import redis
                # 解析Redis URL
                if redis_url.startswith('redis://'):
                    result.info.append("✓ Redis URL格式有效")
                else:
                    result.warnings.append("Redis URL格式可能不正确")
            except ImportError:
                result.warnings.append("Redis库未安装，跳过验证")
        else:
            # 如果没有Redis URL，检查单独的Redis配置
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = os.getenv('REDIS_PORT', '6379')
            try:
                redis_config = RedisConfig(
                    host=redis_host,
                    port=int(redis_port)
                )
                result.info.append("✓ Redis配置有效")
            except ValidationError as e:
                result.errors.append(f"Redis配置无效: {e}")
                result.success = False

    def _validate_security_config(self, result: ValidationResult):
        """验证安全配置"""
        try:
            security_config = SecurityConfig(
                jwt_secret_key=os.getenv('JWT_SECRET_KEY', ''),
                secret_key=os.getenv('SECRET_KEY', ''),
                access_token_expire_minutes=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
            )

            # 检查密钥强度
            jwt_key = security_config.jwt_secret_key
            secret_key = security_config.secret_key

            if jwt_key == secret_key:
                result.warnings.append("JWT密钥和应用密钥相同，建议使用不同的密钥")

            result.info.append("✓ 安全配置有效")
        except ValidationError as e:
            result.errors.append(f"安全配置无效: {e}")
            result.success = False

    def _validate_api_config(self, result: ValidationResult):
        """验证API配置"""
        try:
            api_config = APIConfig(
                host=os.getenv('API_HOST', '0.0.0.0'),
                port=int(os.getenv('API_PORT', '8000')),
                log_level=os.getenv('LOG_LEVEL', 'info')
            )
            result.info.append("✓ API配置有效")
        except ValidationError as e:
            result.errors.append(f"API配置无效: {e}")
            result.success = False

    def _validate_file_permissions(self, result: ValidationResult):
        """验证文件权限"""
        sensitive_files = [
            '.env.production',
            '.env.local',
        ]

        for file_name in sensitive_files:
            file_path = project_root / file_name
            if file_path.exists():
                stat = file_path.stat()
                mode = oct(stat.st_mode)[-3:]
                if mode != '600' and mode != '640':
                    result.warnings.append(f"敏感文件权限过于开放: {file_name} ({mode})，建议设置为 600 或 640")

    def _validate_dependencies(self, result: ValidationResult):
        """验证依赖安装"""
        requirements_file = project_root / "requirements.txt"
        if requirements_file.exists():
            try:
                # 检查pip-audit是否安装
                subprocess.run(['pip-audit', '--version'],
                             capture_output=True, check=True)
                result.info.append("✓ pip-audit已安装，可执行安全扫描")
            except (subprocess.CalledProcessError, FileNotFoundError):
                result.warnings.append("建议安装pip-audit进行依赖安全扫描: pip install pip-audit")

    def generate_config_report(self, result: ValidationResult) -> str:
        """生成配置报告"""
        report = []
        report.append("=" * 60)
        report.append("配置验证报告")
        report.append("=" * 60)
        report.append(f"状态: {'✅ 成功' if result.success else '❌ 失败'}")
        report.append(f"时间: {self._get_current_time()}")
        report.append("")

        if result.errors:
            report.append("❌ 错误:")
            for error in result.errors:
                report.append(f"  - {error}")
            report.append("")

        if result.warnings:
            report.append("⚠️ 警告:")
            for warning in result.warnings:
                report.append(f"  - {warning}")
            report.append("")

        if result.info:
            report.append("ℹ️ 信息:")
            for info in result.info:
                report.append(f"  - {info}")
            report.append("")

        if result.success:
            report.append("✅ 配置验证通过，系统可以启动！")
        else:
            report.append("❌ 配置验证失败，请修复错误后重试！")

        return "\n".join(report)

    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("VALIDATE_CONFIG_DESCRIPTION_345"))
    parser.add_argument('--output', '-o',
                       help = os.getenv("VALIDATE_CONFIG_HELP_346"))
    parser.add_argument('--quiet', '-q',
                       action = os.getenv("VALIDATE_CONFIG_ACTION_347"),
                       help = os.getenv("VALIDATE_CONFIG_HELP_349"))

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format = os.getenv("VALIDATE_CONFIG_FORMAT_352")
    )

    # 执行验证
    validator = ConfigValidator()
    result = validator.validate()

    # 生成报告
    report = validator.generate_config_report(result)

    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {args.output}")
    else:
        print(report)

    # 设置退出码
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()