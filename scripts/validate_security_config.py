#!/usr/bin/env python3
"""
安全配置验证脚本
Validate security configuration for production deployment
"""

import os
import re
import secrets
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

class SecurityValidator:
    """安全配置验证器"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success = []

    def log_error(self, message: str):
        """记录错误"""
        self.errors.append(f"❌ {message}")

    def log_warning(self, message: str):
        """记录警告"""
        self.warnings.append(f"⚠️  {message}")

    def log_success(self, message: str):
        """记录成功"""
        self.success.append(f"✅ {message}")

    def validate_jwt_keys(self) -> bool:
        """验证JWT密钥配置"""
        print("🔑 验证JWT密钥配置...")

        # 检查环境变量
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        jwt_refresh_secret = os.getenv("JWT_REFRESH_SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        if not jwt_secret:
            self.log_error("JWT_SECRET_KEY 未设置")
            return False

        if not jwt_refresh_secret:
            self.log_error("JWT_REFRESH_SECRET_KEY 未设置")
            return False

        if not algorithm:
            self.log_error("ALGORITHM 未设置")
            return False

        # 检查密钥强度
        weak_keys = [
            "your-secret-key-here",
            "your-jwt-secret-key-change-this",
            "your-secret-key-here-please-change-this"
        ]

        if jwt_secret in weak_keys:
            self.log_error("JWT_SECRET_KEY 使用默认值，存在安全风险")
            return False

        if jwt_refresh_secret in weak_keys:
            self.log_error("JWT_REFRESH_SECRET_KEY 使用默认值，存在安全风险")
            return False

        # 检查密钥长度
        if len(jwt_secret) < 32:
            self.log_warning(f"JWT_SECRET_KEY 长度不足 ({len(jwt_secret)} < 32)")

        if len(jwt_refresh_secret) < 32:
            self.log_warning(f"JWT_REFRESH_SECRET_KEY 长度不足 ({len(jwt_refresh_secret)} < 32)")

        # 检查算法
        if algorithm not in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]:
            self.log_error(f"不支持的JWT算法: {algorithm}")
            return False

        self.log_success(f"JWT密钥配置正确 (算法: {algorithm})")
        return True

    def validate_cors_configuration(self) -> bool:
        """验证CORS配置"""
        print("\n🌐 验证CORS配置...")

        cors_origins = os.getenv("CORS_ORIGINS", "")
        if not cors_origins:
            self.log_error("CORS_ORIGINS 未设置")
            return False

        origins = [origin.strip() for origin in cors_origins.split(",")]

        # 检查是否有不安全的配置
        if "*" in origins:
            self.log_error("CORS_ORIGINS 包含通配符 '*'，存在安全风险")
            return False

        # 检查开发环境配置
        dev_origins = ["http://localhost:3000", "http://localhost:8080"]
        has_prod_origin = any(origin not in dev_origins for origin in origins)

        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and not has_prod_origin:
            self.log_warning("生产环境未配置生产域名CORS")

        # 检查CORS设置
        cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
        cors_allow_methods = os.getenv("CORS_ALLOW_METHODS", "")
        cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", "")

        if cors_allow_credentials:
            self.log_success("CORS_ALLOW_CREDENTIALS 已启用")
        else:
            self.log_warning("CORS_ALLOW_CREDENTIALS 未启用")

        if cors_allow_methods:
            self.log_success(f"CORS_ALLOW_METHODS 已配置: {cors_allow_methods}")
        else:
            self.log_warning("CORS_ALLOW_METHODS 未配置")

        self.log_success(f"CORS_ORIGINS 已配置 ({len(origins)} 个源)")
        return True

    def validate_security_headers(self) -> bool:
        """验证安全头配置"""
        print("\n🛡️ 验证安全头配置...")

        secure_headers_enabled = os.getenv("SECURE_HEADERS_ENABLED", "false").lower() == "true"

        if not secure_headers_enabled:
            self.log_warning("SECURE_HEADERS_ENABLED 未启用")
            return False

        # 检查安全头配置
        security_headers = {
            "X_FRAME_OPTIONS": os.getenv("X_FRAME_OPTIONS", "DENY"),
            "X_CONTENT_TYPE_OPTIONS": os.getenv("X_CONTENT_TYPE_OPTIONS", "nosniff"),
            "X_XSS_PROTECTION": os.getenv("X_XSS_PROTECTION", "1; mode=block"),
            "STRICT_TRANSPORT_SECURITY": os.getenv("STRICT_TRANSPORT_SECURITY", "max-age=31536000; includeSubDomains")
        }

        for header, value in security_headers.items():
            if value:
                self.log_success(f"{header}: {value}")
            else:
                self.log_warning(f"{header}: 未配置")

        return True

    def validate_https_configuration(self) -> bool:
        """验证HTTPS配置"""
        print("\n🔒 验证HTTPS配置...")

        environment = os.getenv("ENVIRONMENT", "development")
        force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"

        if environment == "production":
            if not force_https:
                self.log_error("生产环境未启用HTTPS强制重定向")
                return False

            # 检查SSL证书路径
            ssl_cert = os.getenv("SSL_CERT_PATH")
            ssl_key = os.getenv("SSL_KEY_PATH")

            if not ssl_cert:
                self.log_warning("SSL_CERT_PATH 未配置")

            if not ssl_key:
                self.log_warning("SSL_KEY_PATH 未配置")

            if ssl_cert and ssl_key:
                self.log_success("SSL证书路径已配置")

            self.log_success("HTTPS强制重定向已启用")
        else:
            self.log_warning("开发环境，HTTPS强制重定向未启用")

        return True

    def validate_rate_limiting(self) -> bool:
        """验证速率限制配置"""
        print("\n⚡ 验证速率限制配置...")

        rate_limit_per_minute = os.getenv("RATE_LIMIT_PER_MINUTE", "60")
        rate_limit_burst = os.getenv("RATE_LIMIT_BURST", "10")

        try:
            limit_per_min = int(rate_limit_per_minute)
            burst = int(rate_limit_burst)

            if limit_per_min <= 0:
                self.log_error("RATE_LIMIT_PER_MINUTE 必须大于0")
                return False

            if burst <= 0:
                self.log_error("RATE_LIMIT_BURST 必须大于0")
                return False

            self.log_success(f"速率限制: {limit_per_min}/分钟 (突发: {burst})")

            # 建议值检查
            if limit_per_min > 1000:
                self.log_warning("速率限制过高，可能无法有效防护")
            elif limit_per_min < 10:
                self.log_warning("速率限制过低，可能影响正常用户")

            return True

        except ValueError:
            self.log_error("速率限制配置格式错误")
            return False

    def validate_database_security(self) -> bool:
        """验证数据库安全配置"""
        print("\n🗄️ 验证数据库安全配置...")

        db_password = os.getenv("DB_PASSWORD")
        redis_password = os.getenv("REDIS_PASSWORD")

        # 检查数据库密码
        if not db_password:
            self.log_error("DB_PASSWORD 未设置")
            return False

        if len(db_password) < 16:
            self.log_error("数据库密码过短")
            return False

        if db_password in ["password", "123456", "admin", "your_db_password"]:
            self.log_error("数据库密码使用常见弱密码")
            return False

        # 检查Redis密码
        if redis_password and len(redis_password) < 16:
            self.log_warning("Redis密码过短")

        self.log_success("数据库密码配置安全")
        return True

    def validate_password_policy(self) -> bool:
        """验证密码策略"""
        print("\n🔐 验证密码策略...")

        min_length = os.getenv("PASSWORD_MIN_LENGTH", "12")
        require_uppercase = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
        require_lowercase = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
        require_numbers = os.getenv("PASSWORD_REQUIRE_NUMBERS", "true").lower() == "true"
        require_symbols = os.getenv("PASSWORD_REQUIRE_SYMBOLS", "true").lower() == "true"

        try:
            length = int(min_length)

            if length < 8:
                self.log_warning("密码最小长度过短")
            elif length < 12:
                self.log_warning("建议密码最小长度至少12位")
            else:
                self.log_success(f"密码最小长度: {length} 位")

            policy_items = [
                ("大写字母", require_uppercase),
                ("小写字母", require_lowercase),
                ("数字", require_numbers),
                ("特殊字符", require_symbols)
            ]

            for name, required in policy_items:
                if required:
                    self.log_success(f"密码策略: 要求{name}")
                else:
                    self.log_warning(f"密码策略: 不要求{name}")

            return True

        except ValueError:
            self.log_error("密码策略配置格式错误")
            return False

    def validate_audit_logging(self) -> bool:
        """验证审计日志配置"""
        print("\n📝 验证审计日志配置...")

        audit_enabled = os.getenv("AUDIT_LOG_ENABLED", "false").lower() == "true"
        audit_level = os.getenv("AUDIT_LOG_LEVEL", "INFO")
        audit_file = os.getenv("AUDIT_LOG_FILE")

        if not audit_enabled:
            self.log_warning("审计日志未启用")
            return False

        self.log_success(f"审计日志已启用 (级别: {audit_level})")

        if audit_file:
            self.log_success(f"审计日志文件: {audit_file}")
        else:
            self.log_warning("审计日志文件未指定")

        return True

    def check_file_permissions(self) -> bool:
        """检查文件权限"""
        print("\n📁 检查文件权限...")

        files_to_check = [
            ".env.production",
            "config/security_config.json"
        ]

        for file_path in files_to_check:
            if Path(file_path).exists():
                file_mode = oct(Path(file_path).stat().st_mode)[-3:]
                if file_mode == "600":
                    self.log_success(f"{file_path}: 权限正确 ({file_mode})")
                else:
                    self.log_warning(f"{file_path}: 权限不安全 ({file_mode}，建议设置为600)")
            else:
                self.log_warning(f"{file_path}: 文件不存在")

        return True

    def validate_production_readiness(self) -> bool:
        """验证生产就绪性"""
        print("\n🚀 验证生产就绪性...")

        environment = os.getenv("ENVIRONMENT", "development")
        debug = os.getenv("DEBUG", "True").lower() == "true"
        log_level = os.getenv("LOG_LEVEL", "INFO")

        if environment == "production":
            if debug:
                self.log_error("生产环境不能启用DEBUG模式")
                return False

            if log_level.lower() in ["debug", "info"]:
                self.log_warning("生产环境建议使用WARNING或ERROR日志级别")

            self.log_success(f"生产环境配置: ENVIRONMENT={environment}, DEBUG={debug}")

        else:
            self.log_warning(f"当前环境: {environment} (生产部署前需要更改)")

        return True

    def run_validation(self) -> bool:
        """运行完整验证"""
        print("="*80)
        print("🔐 开始安全配置验证")
        print("="*80)

        validations = [
            self.validate_jwt_keys,
            self.validate_cors_configuration,
            self.validate_security_headers,
            self.validate_https_configuration,
            self.validate_rate_limiting,
            self.validate_database_security,
            self.validate_password_policy,
            self.validate_audit_logging,
            self.check_file_permissions,
            self.validate_production_readiness
        ]

        all_passed = True
        for validation in validations:
            try:
                result = validation()
                all_passed = all_passed and result
            except Exception as e:
                self.log_error(f"验证过程中出错: {str(e)}")
                all_passed = False

        return all_passed

    def print_summary(self):
        """打印验证摘要"""
        print("\n" + "="*80)
        print("📊 安全配置验证报告")
        print("="*80)
        print(f"📅 验证时间: {datetime.utcnow().isoformat()}")

        if self.success:
            print(f"\n✅ 通过 ({len(self.success)} 项):")
            for item in self.success:
                print(f"   {item}")

        if self.warnings:
            print(f"\n⚠️  警告 ({len(self.warnings)} 项):")
            for item in self.warnings:
                print(f"   {item}")

        if self.errors:
            print(f"\n❌ 错误 ({len(self.errors)} 项):")
            for item in self.errors:
                print(f"   {item}")

        print(f"\n🎯 总体状态: {'通过' if not self.errors else '需要修复'}")

        if self.errors:
            print("\n🔧 建议修复步骤:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error.replace('❌ ', '')}")

def load_env_file(env_file: str):
    """加载指定的环境文件"""
    if Path(env_file).exists():
        print(f"📁 加载环境文件: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 移除引号
                    value = value.strip('"\'')
                    os.environ[key] = value
        print(f"✅ 环境文件加载完成")
    else:
        print(f"❌ 环境文件不存在: {env_file}")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="验证安全配置")
    parser.add_argument("--env-file", default=".env.production",
                       help="要验证的环境文件路径 (默认: .env.production)")
    args = parser.parse_args()

    # 加载指定的环境文件
    load_env_file(args.env_file)

    validator = SecurityValidator()

    # 运行验证
    all_passed = validator.run_validation()

    # 打印摘要
    validator.print_summary()

    # 设置退出码
    exit_code = 0 if all_passed else 1
    exit(exit_code)

if __name__ == "__main__":
    main()