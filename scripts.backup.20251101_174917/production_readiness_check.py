#!/usr/bin/env python3
"""
生产环境就绪状态深度检查工具

对足球预测系统进行全面的生产环境就绪评估，
包括功能完整性、安全性、性能、监控等关键维度。
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests.exceptions import ConnectionError, Timeout

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ProductionReadinessChecker:
    """生产环境就绪状态检查器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            "api_endpoints": {},
            "database": {},
            "security": {},
            "performance": {},
            "monitoring": {},
            "configuration": {},
            "overall": {},
        }
        self.passed_checks = 0
        self.total_checks = 0

    def add_result(
        self, category: str, check_name: str, passed: bool, details: str = "", metrics: Dict = None
    ):
        """添加检查结果"""
        if category not in self.results:
            self.results[category] = {}

        self.results[category][check_name] = {
            "passed": passed,
            "details": details,
            "metrics": metrics or {},
            "timestamp": time.time(),
        }

        self.total_checks += 1
        if passed:
            self.passed_checks += 1

        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{category}.{check_name}: {status} - {details}")

    async def check_api_endpoints(self) -> bool:
        """检查API端点完整性"""
        logger.info("🔍 检查API端点完整性...")

        endpoints = [
            ("/", "根路径"),
            ("/api/health", "健康检查"),
            ("/api/v1/predictions", "预测API"),
            ("/api/v1/matches", "比赛数据API"),
            ("/api/v1/teams", "球队API"),
            ("/docs", "API文档"),
            ("/openapi.json", "OpenAPI规范"),
        ]

        all_passed = True

        for endpoint, description in endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                response = requests.get(url, timeout=10)

                passed = response.status_code < 500
                details = f"状态码: {response.status_code}"

                if response.status_code == 200:
                    details += " - 响应正常"
                elif response.status_code == 404:
                    details += " - 端点不存在"
                elif response.status_code >= 500:
                    details += " - 服务器错误"
                    all_passed = False

                self.add_result(
                    "api_endpoints",
                    description,
                    passed,
                    details,
                    {
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds(),
                    },
                )

            except (ConnectionError, Timeout) as e:
                self.add_result("api_endpoints", description, False, f"连接失败: {str(e)}")
                all_passed = False
            except Exception as e:
                self.add_result("api_endpoints", description, False, f"未知错误: {str(e)}")
                all_passed = False

        return all_passed

    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        logger.info("🔍 检查数据库连接...")

        try:
            # 测试数据库迁移状态
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    "from alembic import command; "
                    "from alembic.config import Config; "
                    "cfg = Config('alembic.ini'); "
                    "current = command.current(cfg); "
                    "print(f'Current revision: {current}')",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.add_result("database", "迁移状态", True, f"当前版本: {result.stdout.strip()}")
                return True
            else:
                self.add_result("database", "迁移状态", False, f"错误: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.add_result("database", "迁移状态", False, "检查超时")
            return False
        except Exception as e:
            self.add_result("database", "迁移状态", False, f"检查失败: {str(e)}")
            return False

    def check_security_configuration(self) -> bool:
        """检查安全配置"""
        logger.info("🔍 检查安全配置...")

        security_checks = []

        # 检查环境变量
        env_vars = [
            ("SECRET_KEY", "JWT密钥"),
            ("ALGORITHM", "JWT算法"),
            ("DATABASE_URL", "数据库连接"),
            ("REDIS_URL", "Redis连接"),
        ]

        for var_name, description in env_vars:
            value = os.getenv(var_name)
            passed = value is not None and len(value) > 0
            details = "已配置" if passed else "未配置"

            self.add_result("security", description, passed, details, {"configured": passed})

            security_checks.append(passed)

        # 检查安全漏洞
        try:
            result = subprocess.run(
                ["pip-audit", "--requirement", "requirements/requirements.lock", "--format=json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                try:
                    audit_data = json.loads(result.stdout)
                    vuln_count = len(audit_data.get("vulnerabilities", []))
                    passed = vuln_count == 0
                    details = f"发现 {vuln_count} 个漏洞"

                    self.add_result(
                        "security", "安全漏洞", passed, details, {"vulnerability_count": vuln_count}
                    )
                    security_checks.append(passed)

                except json.JSONDecodeError:
                    self.add_result("security", "安全漏洞", False, "无法解析扫描结果")
                    security_checks.append(False)
            else:
                self.add_result("security", "安全漏洞", False, f"扫描失败: {result.stderr}")
                security_checks.append(False)

        except subprocess.TimeoutExpired:
            self.add_result("security", "安全漏洞", False, "扫描超时")
            security_checks.append(False)
        except Exception as e:
            self.add_result("security", "安全漏洞", False, f"扫描错误: {str(e)}")
            security_checks.append(False)

        return all(security_checks)

    def check_code_quality(self) -> bool:
        """检查代码质量"""
        logger.info("🔍 检查代码质量...")

        quality_checks = []

        # MyPy检查
        try:
            result = subprocess.run(
                ["make", "type-check"], capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                self.add_result("configuration", "MyPy类型检查", True, "类型检查通过")
                quality_checks.append(True)
            else:
                # 统计错误数量
                error_lines = [line for line in result.stdout.split("\n") if "error:" in line]
                error_count = len(error_lines)
                self.add_result(
                    "configuration",
                    "MyPy类型检查",
                    False,
                    f"发现 {error_count} 个类型错误",
                    {"error_count": error_count},
                )
                quality_checks.append(False)

        except subprocess.TimeoutExpired:
            self.add_result("configuration", "MyPy类型检查", False, "检查超时")
            quality_checks.append(False)
        except Exception as e:
            self.add_result("configuration", "MyPy类型检查", False, f"检查失败: {str(e)}")
            quality_checks.append(False)

        # Ruff检查
        try:
            result = subprocess.run(["make", "lint"], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                self.add_result("configuration", "Ruff代码检查", True, "代码检查通过")
                quality_checks.append(True)
            else:
                # 统计警告数量
                warning_lines = [line for line in result.stdout.split("\n") if line.strip()]
                warning_count = len(warning_lines)
                self.add_result(
                    "configuration",
                    "Ruff代码检查",
                    False,
                    f"发现 {warning_count} 个代码问题",
                    {"warning_count": warning_count},
                )
                quality_checks.append(False)

        except subprocess.TimeoutExpired:
            self.add_result("configuration", "Ruff代码检查", False, "检查超时")
            quality_checks.append(False)
        except Exception as e:
            self.add_result("configuration", "Ruff代码检查", False, f"检查失败: {str(e)}")
            quality_checks.append(False)

        return all(quality_checks)

    def check_test_coverage(self) -> bool:
        """检查测试覆盖率"""
        logger.info("🔍 检查测试覆盖率...")

        try:
            result = subprocess.run(
                ["make", "coverage-fast"], capture_output=True, text=True, timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                # 尝试从输出中提取覆盖率
                output = result.stdout
                if "coverage:" in output.lower() or "%" in output:
                    self.add_result("configuration", "测试覆盖率", True, "覆盖率测试完成")
                    return True
                else:
                    self.add_result("configuration", "测试覆盖率", True, "覆盖率测试通过")
                    return True
            else:
                self.add_result("configuration", "测试覆盖率", False, "覆盖率测试失败")
                return False

        except subprocess.TimeoutExpired:
            self.add_result("configuration", "测试覆盖率", False, "测试超时")
            return False
        except Exception as e:
            self.add_result("configuration", "测试覆盖率", False, f"测试错误: {str(e)}")
            return False

    def check_monitoring_setup(self) -> bool:
        """检查监控设置"""
        logger.info("🔍 检查监控设置...")

        monitoring_checks = []

        # 检查监控文件存在性
        monitoring_files = [
            ("src/monitoring/metrics_collector.py", "指标收集器"),
            ("src/monitoring/system_monitor.py", "系统监控器"),
            ("config/monitoring/alert_rules.yml", "告警规则配置"),
        ]

        for file_path, description in monitoring_files:
            exists = Path(file_path).exists()
            self.add_result(
                "monitoring", description, exists, "文件存在" if exists else "文件不存在"
            )
            monitoring_checks.append(exists)

        return all(monitoring_checks)

    def check_performance_baseline(self) -> bool:
        """检查性能基线"""
        logger.info("🔍 检查性能基线...")

        try:
            result = subprocess.run(
                ["make", "benchmark"], capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                # 解析基准测试结果
                output = result.stdout
                if "Average DB operation time" in output:
                    self.add_result("performance", "基准测试", True, "基准测试完成")
                    return True
                else:
                    self.add_result("performance", "基准测试", False, "基准测试结果异常")
                    return False
            else:
                self.add_result("performance", "基准测试", False, "基准测试失败")
                return False

        except subprocess.TimeoutExpired:
            self.add_result("performance", "基准测试", False, "测试超时")
            return False
        except Exception as e:
            self.add_result("performance", "基准测试", False, f"测试错误: {str(e)}")
            return False

    def calculate_overall_score(self) -> float:
        """计算总体就绪分数"""
        if self.total_checks == 0:
            return 0.0

        score = (self.passed_checks / self.total_checks) * 10
        return round(score, 1)

    def generate_report(self) -> Dict:
        """生成检查报告"""
        overall_score = self.calculate_overall_score()

        # 确定就绪级别
        if overall_score >= 9.0:
            readiness_level = "🟢 生产就绪"
            readiness_color = "green"
        elif overall_score >= 7.0:
            readiness_level = "🟡 基本就绪"
            readiness_color = "yellow"
        elif overall_score >= 5.0:
            readiness_level = "🟠 需要改进"
            readiness_color = "orange"
        else:
            readiness_level = "🔴 未就绪"
            readiness_color = "red"

        self.results["overall"] = {
            "score": overall_score,
            "level": readiness_level,
            "color": readiness_color,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "pass_rate": (
                round((self.passed_checks / self.total_checks) * 100, 1)
                if self.total_checks > 0
                else 0
            ),
        }

        return self.results

    async def run_all_checks(self) -> Dict:
        """运行所有检查"""
        logger.info("🚀 开始生产环境就绪状态检查...")

        start_time = time.time()

        # 运行各项检查
        await self.check_api_endpoints()
        self.check_database_connection()
        self.check_security_configuration()
        self.check_code_quality()
        self.check_test_coverage()
        self.check_monitoring_setup()
        self.check_performance_baseline()

        end_time = time.time()
        duration = end_time - start_time

        # 生成报告
        report = self.generate_report()
        report["execution_time"] = duration

        return report


def main():
    """主函数"""
    print("🔍 足球预测系统生产环境就绪状态检查")
    print("=" * 60)

    checker = ProductionReadinessChecker()

    try:
        report = asyncio.run(checker.run_all_checks())

        print("\n" + "=" * 60)
        print("📊 检查报告")
        print("=" * 60)

        overall = report["overall"]
        print(f"🎯 总体评分: {overall['score']}/10")
        print(f"📈 就绪级别: {overall['level']}")
        print(f"✅ 通过检查: {overall['passed_checks']}/{overall['total_checks']}")
        print(f"📊 通过率: {overall['pass_rate']}%")
        print(f"⏱️  执行时间: {report['execution_time']:.2f}秒")

        print("\n📋 详细结果:")
        for category, checks in report.items():
            if category == "overall" or category == "execution_time":
                continue

            print(f"\n🔍 {category.upper()}:")
            for check_name, result in checks.items():
                status = "✅" if result["passed"] else "❌"
                print(f"  {status} {check_name}: {result['details']}")

        # 根据评分确定退出码
        if overall["score"] >= 8.0:
            print("\n🎉 系统已准备就绪，可以部署到生产环境！")
            return 0
        elif overall["score"] >= 6.0:
            print("\n⚠️  系统基本就绪，但建议先解决一些问题")
            return 1
        else:
            print("\n❌ 系统未就绪，需要解决关键问题后才能部署")
            return 2

    except KeyboardInterrupt:
        print("\n⏹️  检查被用户中断")
        return 130
    except Exception as e:
        logger.error(f"检查过程中发生错误: {e}")
        return 3


if __name__ == "__main__":
    exit(main())
