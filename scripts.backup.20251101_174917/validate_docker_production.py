#!/usr/bin/env python3
"""
Docker生产环境配置验证脚本
Production Docker Configuration Validation Script

验证Docker生产环境的完整性和最佳实践
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DockerProductionValidator:
    """Docker生产环境验证器"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0

    def validate_file_structure(self) -> bool:
        """验证Docker生产环境文件结构"""
        logger.info("🔍 验证Docker生产环境文件结构...")

        required_files = [
            "docker/docker-compose.production.yml",
            "docker/Dockerfile.production",
            "scripts/deploy_production.sh",
            "docker/gunicorn.conf.py",
            "docker/supervisord.conf"
        ]

        all_exist = True
        for file_path in required_files:
            self.total_checks += 1
            if os.path.exists(file_path):
                logger.info(f"  ✅ {file_path} 存在")
                self.success_count += 1
            else:
                logger.error(f"  ❌ {file_path} 不存在")
                self.errors.append(f"缺少必要文件: {file_path}")
                all_exist = False

        return all_exist

    def validate_docker_compose_config(self) -> bool:
        """验证docker-compose.production.yml配置"""
        logger.info("🔍 验证Docker Compose配置...")

        compose_file = "docker/docker-compose.production.yml"
        if not os.path.exists(compose_file):
            self.errors.append("docker-compose.production.yml文件不存在")
            return False

        try:
            # 读取并解析YAML文件
            import yaml
            with open(compose_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 验证基本结构
            if not config.get('version'):
                self.warnings.append("缺少Docker Compose版本声明")

            services = config.get('services', {})
            self.total_checks += 1
            if not services:
                self.errors.append("Docker Compose配置中没有服务定义")
                return False

            # 验证必要服务
            required_services = ['app', 'db', 'nginx']
            service_validation = True

            for service in required_services:
                self.total_checks += 1
                if service in services:
                    logger.info(f"  ✅ 服务 '{service}' 已定义")
                    self.success_count += 1

                    # 验证服务配置
                    service_config = services[service]
                    if service == 'app':
                        if not service_config.get('healthcheck'):
                            self.warnings.append(f"服务 '{service}' 缺少健康检查")
                    elif service == 'db':
                        if not service_config.get('volumes'):
                            self.warnings.append(f"服务 '{service}' 缺少数据持久化")
                    elif service == 'nginx':
                        if not service_config.get('ports'):
                            self.warnings.append(f"服务 '{nginx}' 缺少端口映射")
                else:
                    logger.warning(f"  ⚠️  服务 '{service}' 未定义")
                    self.warnings.append(f"建议的服务 '{service}' 未定义")

            # 验证网络配置
            networks = config.get('networks', {})
            self.total_checks += 1
            if networks:
                logger.info("  ✅ 网络配置已定义")
                self.success_count += 1
            else:
                self.warnings.append("建议定义自定义网络")

            # 验证卷配置
            volumes = config.get('volumes', {})
            self.total_checks += 1
            if volumes:
                logger.info("  ✅ 数据卷已定义")
                self.success_count += 1
            else:
                self.warnings.append("建议定义持久化数据卷")

            return True

        except Exception as e:
            self.errors.append(f"Docker Compose配置解析失败: {e}")
            return False

    def validate_dockerfile_production(self) -> bool:
        """验证生产环境Dockerfile"""
        logger.info("🔍 验证生产环境Dockerfile...")

        dockerfile = "docker/Dockerfile.production"
        if not os.path.exists(dockerfile):
            self.errors.append("Dockerfile.production不存在")
            return False

        try:
            with open(dockerfile, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查关键指令
            required_instructions = [
                "FROM", "WORKDIR", "USER", "EXPOSE", "HEALTHCHECK", "CMD"
            ]

            validation_passed = True
            for instruction in required_instructions:
                self.total_checks += 1
                if instruction in content:
                    logger.info(f"  ✅ 包含 {instruction} 指令")
                    self.success_count += 1
                else:
                    logger.warning(f"  ⚠️  缺少 {instruction} 指令")
                    self.warnings.append(f"建议包含 {instruction} 指令")

            # 检查安全特性
            security_checks = [
                ("非root用户", "USER appuser"),
                ("健康检查", "HEALTHCHECK"),
                ("多阶段构建", "FROM base as builder"),
                ("Python环境变量", "PYTHONUNBUFFERED=1")
            ]

            for check_name, pattern in security_checks:
                self.total_checks += 1
                if pattern in content:
                    logger.info(f"  ✅ {check_name} 配置正确")
                    self.success_count += 1
                else:
                    self.warnings.append(f"建议配置{check_name}")

            return True

        except Exception as e:
            self.errors.append(f"Dockerfile验证失败: {e}")
            return False

    def validate_deployment_script(self) -> bool:
        """验证部署脚本"""
        logger.info("🔍 验证部署脚本...")

        script_path = "scripts/deploy_production.sh"
        if not os.path.exists(script_path):
            self.errors.append("部署脚本deploy_production.sh不存在")
            return False

        try:
            # 检查脚本可执行性
            if not os.access(script_path, os.X_OK):
                logger.info("  🔧 设置脚本可执行权限")
                os.chmod(script_path, 0o755)

            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查关键功能
            required_functions = [
                "backup_data",
                "health_check",
                "deploy",
                "rollback",
                "show_status"
            ]

            for function in required_functions:
                self.total_checks += 1
                if f"function {function}" in content or f"{function}(" in content:
                    logger.info(f"  ✅ 包含 {function} 功能")
                    self.success_count += 1
                else:
                    self.warnings.append(f"建议包含 {function} 功能")

            # 检查安全特性
            security_checks = [
                ("set -e", "错误处理"),
                ("check_command", "命令检查"),
                ("check_port", "端口检查"),
                ("备份功能", "backup_data")
            ]

            for pattern, description in security_checks:
                self.total_checks += 1
                if pattern in content:
                    logger.info(f"  ✅ {description} 已实现")
                    self.success_count += 1
                else:
                    self.warnings.append(f"建议实现{description}")

            return True

        except Exception as e:
            self.errors.append(f"部署脚本验证失败: {e}")
            return False

    def validate_environment_template(self) -> bool:
        """验证环境配置模板"""
        logger.info("🔍 验证环境配置模板...")

        env_template = "environments/.env.production.example"
        if not os.path.exists(env_template):
            logger.warning("  ⚠️  环境配置模板不存在（可能被.gitignore忽略）")
            return True

        try:
            with open(env_template, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查关键配置项
            required_configs = [
                "DB_HOST",
                "DB_PASSWORD",
                "REDIS_PASSWORD",
                "JWT_SECRET_KEY",
                "DOMAIN",
                "GRAFANA_ADMIN_PASSWORD"
            ]

            for config in required_configs:
                self.total_checks += 1
                if config in content:
                    logger.info(f"  ✅ 包含 {config} 配置")
                    self.success_count += 1
                else:
                    self.warnings.append(f"建议包含 {config} 配置")

            # 检查安全性
            security_patterns = [
                "your-secure",
                "change-this",
                "super-secret"
            ]

            for pattern in security_patterns:
                self.total_checks += 1
                if pattern in content:
                    logger.info(f"  ✅ 包含安全占位符提示")
                    self.success_count += 1
                else:
                    self.warnings.append(f"建议添加安全配置提示")

            return True

        except Exception as e:
            self.errors.append(f"环境配置模板验证失败: {e}")
            return False

    def check_docker_availability(self) -> bool:
        """检查Docker环境"""
        logger.info("🔍 检查Docker环境...")

        try:
            # 检查Docker命令
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"  ✅ Docker: {result.stdout.strip()}")
                self.success_count += 1
            else:
                self.warnings.append("Docker未安装或不可用")
                return False

            # 检查docker-compose命令
            self.total_checks += 1
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"  ✅ Docker Compose: {result.stdout.strip()}")
                self.success_count += 1
            else:
                self.warnings.append("Docker Compose未安装或不可用")

            return True

        except Exception as e:
            self.warnings.append(f"Docker环境检查失败: {e}")
            return False

    def validate_compose_syntax(self) -> bool:
        """验证docker-compose语法"""
        logger.info("🔍 验证docker-compose语法...")

        compose_file = "docker/docker-compose.production.yml"
        if not os.path.exists(compose_file):
            return False

        try:
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "config", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )

            self.total_checks += 1
            if result.returncode == 0:
                logger.info("  ✅ Docker Compose语法正确")
                self.success_count += 1
                return True
            else:
                self.errors.append(f"Docker Compose语法错误: {result.stderr}")
                return False

        except Exception as e:
            self.warnings.append(f"Docker Compose语法验证失败: {e}")
            return False

    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        success_rate = (self.success_count / self.total_checks * 100) if self.total_checks > 0 else 0

        report = {
            "total_checks": self.total_checks,
            "success_count": self.success_count,
            "success_rate": round(success_rate, 2),
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "PASS" if len(self.errors) == 0 and success_rate >= 80 else "FAIL",
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if len(self.errors) > 0:
            recommendations.append("立即修复所有错误项")

        if len(self.warnings) > 0:
            recommendations.append("考虑实施警告项以提升安全性")

        if self.success_count < self.total_checks:
            recommendations.append("完善缺失的配置项")

        recommendations.extend([
            "定期测试Docker生产环境部署",
            "实施监控和日志收集",
            "配置自动备份策略",
            "实施安全扫描和漏洞检测"
        ])

        return recommendations

    def run_validation(self) -> Dict[str, Any]:
        """运行完整验证"""
        logger.info("🚀 开始Docker生产环境配置验证...")
        print("=" * 60)

        # 运行所有验证
        validation_results = []

        validation_results.append(self.validate_file_structure())
        validation_results.append(self.validate_docker_compose_config())
        validation_results.append(self.validate_dockerfile_production())
        validation_results.append(self.validate_deployment_script())
        validation_results.append(self.validate_environment_template())
        validation_results.append(self.check_docker_availability())
        validation_results.append(self.validate_compose_syntax())

        # 生成报告
        report = self.generate_report()

        # 打印结果
        print("\n" + "=" * 60)
        print("📊 Docker生产环境配置验证报告")
        print("=" * 60)
        print(f"✅ 通过检查: {report['success_count']}/{report['total_checks']}")
        print(f"📈 成功率: {report['success_rate']}%")
        print(f"🏆 状态: {report['status']}")

        if self.errors:
            print(f"\n❌ 错误 ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n⚠️  警告 ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if report['recommendations']:
            print(f"\n💡 改进建议:")
            for rec in report['recommendations']:
                print(f"  - {rec}")

        print("=" * 60)

        return report


def main():
    """主函数"""
    validator = DockerProductionValidator()

    try:
        report = validator.run_validation()

        # 保存报告到文件
        report_file = "docker_production_validation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 验证报告已保存到: {report_file}")

        # 根据结果设置退出码
        if report['status'] == 'PASS':
            logger.info("🎉 Docker生产环境配置验证通过！")
            sys.exit(0)
        else:
            logger.error("❌ Docker生产环境配置验证失败，请检查错误项")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️  验证被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 验证过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()