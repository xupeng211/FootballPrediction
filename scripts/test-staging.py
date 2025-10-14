#!/usr/bin/env python3
"""
Staging环境完整测试脚本
执行功能、性能、安全和稳定性测试
"""

import asyncio
import subprocess
import time
import json
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class StagingTestRunner:
    """Staging环境测试执行器"""

    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.api_base = f"{self.base_url}/api/v1"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        }
        self.session = requests.Session()

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_test(self, test_name: str, test_func, critical: bool = True):
        """运行单个测试"""
        self.test_results["summary"]["total"] += 1
        self.log(f"运行测试: {test_name}")

        try:
            result = test_func()
            if result:
                self.test_results["tests"][test_name] = {
                    "status": "PASSED",
                    "critical": critical,
                    "message": "测试通过",
                }
                self.test_results["summary"]["passed"] += 1
                self.log(f"✅ {test_name} - 通过", "SUCCESS")
            else:
                self.test_results["tests"][test_name] = {
                    "status": "FAILED",
                    "critical": critical,
                    "message": "测试失败",
                }
                self.test_results["summary"]["failed"] += 1
                self.log(f"❌ {test_name} - 失败", "ERROR")
                if critical:
                    self.log("关键测试失败，终止测试流程", "ERROR")
                    sys.exit(1)
        except Exception as e:
            self.test_results["tests"][test_name] = {
                "status": "ERROR",
                "critical": critical,
                "message": str(e),
            }
            self.test_results["summary"]["failed"] += 1
            self.log(f"❌ {test_name} - 错误: {str(e)}", "ERROR")
            if critical:
                self.log("关键测试出错，终止测试流程", "ERROR")
                sys.exit(1)

    def check_staging_environment(self) -> bool:
        """检查Staging环境是否运行"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                self.log("Staging环境运行正常")
                return True
            else:
                self.log(f"Staging环境健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"无法连接到Staging环境: {str(e)}")
            return False

    def test_api_endpoints(self) -> bool:
        """测试所有API端点"""
        endpoints = [
            # 认证端点
            {
                "path": "/auth/login",
                "method": "POST",
                "data": {"username": "test", "password": "test"},
            },
            {
                "path": "/auth/register",
                "method": "POST",
                "data": {
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "test123",
                },
            },
            # 核心业务端点
            {"path": "/predictions", "method": "GET"},
            {"path": "/matches", "method": "GET"},
            {"path": "/teams", "method": "GET"},
            {"path": "/leagues", "method": "GET"},
            {"path": "/odds", "method": "GET"},
            # 健康和监控端点
            {"path": "/health", "method": "GET"},
            {"path": "/metrics", "method": "GET"},
            {"path": "/status", "method": "GET"},
        ]

        success_count = 0
        for endpoint in endpoints:
            url = f"{self.api_base}{endpoint['path']}"
            try:
                if endpoint["method"] == "GET":
                    response = self.session.get(url, timeout=10)
                elif endpoint["method"] == "POST":
                    response = self.session.post(
                        url, json=endpoint.get("data", {}), timeout=10
                    )

                if response.status_code in [200, 201, 401, 422]:
                    success_count += 1
                    self.log(
                        f"  ✓ {endpoint['method']} {endpoint['path']} - {response.status_code}"
                    )
                else:
                    self.log(
                        f"  ✗ {endpoint['method']} {endpoint['path']} - {response.status_code}"
                    )
            except Exception as e:
                self.log(
                    f"  ✗ {endpoint['method']} {endpoint['path']} - 错误: {str(e)}"
                )

        return success_count >= len(endpoints) * 0.8  # 80%成功率

    def test_database_connection(self) -> bool:
        """测试数据库连接"""
        try:
            response = self.session.get(f"{self.api_base}/health/database", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log("数据库连接正常")
                    return True
            return False
        except:
            return False

    def test_redis_connection(self) -> bool:
        """测试Redis连接"""
        try:
            response = self.session.get(f"{self.api_base}/health/redis", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log("Redis连接正常")
                    return True
            return False
        except:
            return False

    def test_authentication_flow(self) -> bool:
        """测试认证流程"""
        try:
            # 1. 注册用户
            register_data = {
                "username": f"testuser_{int(time.time())}",
                "email": f"test_{int(time.time())}@example.com",
                "password": "TestPassword123!",
            }

            response = self.session.post(
                f"{self.api_base}/auth/register", json=register_data
            )
            if response.status_code not in [200, 201]:
                return False

            # 2. 登录
            login_data = {
                "username": register_data["username"],
                "password": register_data["password"],
            }

            response = self.session.post(f"{self.api_base}/auth/login", json=login_data)
            if response.status_code != 200:
                return False

            token_data = response.json()
            token = token_data.get("access_token")
            if not token:
                return False

            # 3. 使用token访问受保护的端点
            headers = {"Authorization": f"Bearer {token}"}
            response = self.session.get(f"{self.api_base}/users/me", headers=headers)

            return response.status_code == 200

        except Exception as e:
            self.log(f"认证流程测试错误: {str(e)}")
            return False

    def test_prediction_service(self) -> bool:
        """测试预测服务"""
        try:
            # 获取预测
            response = self.session.get(f"{self.api_base}/predictions")
            if response.status_code != 200:
                return False

            # 创建预测请求
            predict_data = {
                "match_id": "test_match_123",
                "home_team": "Team A",
                "away_team": "Team B",
            }

            response = self.session.post(
                f"{self.api_base}/predictions", json=predict_data
            )
            return response.status_code in [200, 201, 400]  # 400可能是数据已存在

        except:
            return False

    def test_performance_benchmarks(self) -> bool:
        """测试性能基准"""
        try:
            # 简单的性能测试
            start_time = time.time()

            # 并发请求测试
            import concurrent.futures

            def make_request():
                try:
                    response = self.session.get(f"{self.api_base}/matches", timeout=5)
                    return response.status_code == 200
                except:
                    return False

            # 10个并发请求
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]

            end_time = time.time()
            total_time = end_time - start_time

            success_rate = sum(results) / len(results)
            avg_response_time = total_time / 10

            self.log(
                f"性能测试 - 成功率: {success_rate:.2%}, 平均响应时间: {avg_response_time:.3f}s"
            )

            # 成功率 > 90% 且平均响应时间 < 1秒
            return success_rate > 0.9 and avg_response_time < 1.0

        except:
            return False

    def test_monitoring_integration(self) -> bool:
        """测试监控集成"""
        try:
            # 检查Prometheus
            prometheus_response = requests.get(
                "http://localhost:9091/api/v1/query?query=up", timeout=5
            )
            prometheus_ok = prometheus_response.status_code == 200

            # 检查Grafana
            grafana_response = requests.get(
                "http://localhost:3001/api/health", timeout=5
            )
            grafana_ok = grafana_response.status_code == 200

            # 检查Loki
            loki_response = requests.get("http://localhost:3101/ready", timeout=5)
            loki_ok = loki_response.status_code == 200

            self.log(
                f"监控状态 - Prometheus: {'✓' if prometheus_ok else '✗'}, Grafana: {'✓' if grafana_ok else '✗'}, Loki: {'✓' if loki_ok else '✗'}"
            )

            return prometheus_ok and grafana_ok

        except:
            return False

    def test_security_headers(self) -> bool:
        """测试安全头"""
        try:
            response = self.session.get(f"{self.base_url}", timeout=10)
            headers = response.headers

            required_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection",
            ]

            missing_headers = []
            for header in required_headers:
                if header not in headers:
                    missing_headers.append(header)

            if missing_headers:
                self.log(f"缺少安全头: {', '.join(missing_headers)}")
                return False

            return True

        except:
            return False

    def run_stability_test(self) -> bool:
        """运行稳定性测试（简化版）"""
        try:
            # 5分钟的持续请求
            duration = 300  # 5分钟
            interval = 5  # 每5秒一次请求
            start_time = time.time()
            success_count = 0
            total_requests = 0

            self.log("开始5分钟稳定性测试...")

            while time.time() - start_time < duration:
                try:
                    response = self.session.get(f"{self.api_base}/health", timeout=5)
                    total_requests += 1
                    if response.status_code == 200:
                        success_count += 1
                    time.sleep(interval)
                except:
                    total_requests += 1

            success_rate = success_count / total_requests if total_requests > 0 else 0
            self.log(
                f"稳定性测试完成 - 成功率: {success_rate:.2%} ({success_count}/{total_requests})"
            )

            return success_rate > 0.95  # 95%成功率

        except:
            return False

    def generate_report(self):
        """生成测试报告"""
        report_path = f"reports/staging-test-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("reports").mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(self.test_results, f, indent=2)

        self.log(f"测试报告已保存: {report_path}")

        # 打印摘要
        self.log("\n" + "=" * 60)
        self.log("STAGING环境测试摘要")
        self.log("=" * 60)
        self.log(f"总测试数: {self.test_results['summary']['total']}")
        self.log(f"通过: {self.test_results['summary']['passed']}")
        self.log(f"失败: {self.test_results['summary']['failed']}")
        self.log(f"跳过: {self.test_results['summary']['skipped']}")

        if self.test_results["summary"]["failed"] == 0:
            self.log("\n✅ 所有测试通过！Staging环境准备就绪。", "SUCCESS")
        else:
            self.log(
                f"\n❌ 有 {self.test_results['summary']['failed']} 个测试失败", "ERROR"
            )

        self.log("=" * 60)

    def run_all_tests(self):
        """运行所有测试"""
        self.log("开始Staging环境完整测试...")

        # 基础环境检查
        self.run_test("环境健康检查", self.check_staging_environment, critical=True)

        # 功能测试
        self.run_test("API端点测试", self.test_api_endpoints, critical=True)
        self.run_test("数据库连接测试", self.test_database_connection, critical=True)
        self.run_test("Redis连接测试", self.test_redis_connection, critical=True)
        self.run_test("认证流程测试", self.test_authentication_flow, critical=True)
        self.run_test("预测服务测试", self.test_prediction_service, critical=True)

        # 性能测试
        self.run_test("性能基准测试", self.test_performance_benchmarks, critical=True)

        # 监控测试
        self.run_test("监控集成测试", self.test_monitoring_integration, critical=False)

        # 安全测试
        self.run_test("安全头检查", self.test_security_headers, critical=False)

        # 稳定性测试
        self.run_test("稳定性测试", self.run_stability_test, critical=True)

        # 生成报告
        self.generate_report()


def main():
    """主函数"""
    runner = StagingTestRunner()

    try:
        runner.run_all_tests()

        # 如果所有测试通过，返回0
        if runner.test_results["summary"]["failed"] == 0:
            print("\n✅ Staging环境测试全部通过！")
            sys.exit(0)
        else:
            print("\n❌ 部分测试失败，请检查报告")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试执行出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
