#!/usr/bin/env python3
"""
增强的测试套件
集成了API测试技能的全面测试解决方案
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

# 导入测试组件
try:
    import sys

    sys.path.append("src")
    sys.path.append(".claude/skills/api-testing")
    from main import app
    from enhanced_main import app as enhanced_app

    API_TESTING_ENABLED = True
except ImportError as e:
    logging.warning(f"API测试组件导入失败: {e}")
    API_TESTING_ENABLED = False

logger = logging.getLogger(__name__)


class EnhancedTestSuite:
    """
    增强的测试套件
    提供功能测试、性能测试和安全测试
    """

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = {
            "functional_tests": [],
            "performance_tests": [],
            "security_tests": [],
            "coverage_tests": [],
        }

    async def run_functional_tests(self):
        """运行功能测试"""
        logger.info("🧪 开始功能测试...")

        test_cases = [
            {
                "name": "Health Check",
                "method": "GET",
                "path": "/health",
                "expected_status": 200,
                "validator": lambda r: "status" in r.json() and r.json()["status"] == "healthy",
            },
            {
                "name": "Root Endpoint",
                "method": "GET",
                "path": "/",
                "expected_status": 200,
                "validator": lambda r: "service" in r.json(),
            },
            {
                "name": "Metrics Endpoint",
                "method": "GET",
                "path": "/metrics",
                "expected_status": 200,
                "validator": lambda r: r.headers.get("content-type", "").startswith("text/plain"),
            },
            {
                "name": "Database Health",
                "method": "GET",
                "path": "/api/database/health",
                "expected_status": 200,
                "validator": lambda r: "status" in r.json(),
            },
        ]

        results = []
        async with AsyncClient(app=enhanced_app, base_url=self.base_url) as client:
            for test_case in test_cases:
                start_time = time.time()
                try:
                    response = await client.request(test_case["method"], test_case["path"])
                    end_time = time.time()

                    test_result = {
                        "name": test_case["name"],
                        "status_code": response.status_code,
                        "expected_status": test_case["expected_status"],
                        "response_time_ms": (end_time - start_time) * 1000,
                        "passed": response.status_code == test_case["expected_status"],
                        "content_length": len(response.content),
                    }

                    # 自定义验证
                    try:
                        if "validator" in test_case:
                            test_result["validation_passed"] = test_case["validator"](response)
                    except Exception as e:
                        test_result["validation_passed"] = False
                        test_result["validation_error"] = str(e)

                    results.append(test_result)

                    if test_result["passed"]:
                        logger.info(f"✅ {test_case['name']}: {test_result['response_time_ms']:.2f}ms")
                    else:
                        logger.error(
                            f"❌ {test_case['name']}: {response.status_code} != {test_case['expected_status']}"
                        )

                except Exception as e:
                    results.append(
                        {
                            "name": test_case["name"],
                            "passed": False,
                            "error": str(e),
                            "response_time_ms": 0,
                        }
                    )
                    logger.error(f"❌ {test_case['name']}: {str(e)}")

        self.test_results["functional_tests"] = results
        return results

    async def run_performance_tests(self):
        """运行性能测试"""
        logger.info("⚡ 开始性能测试...")

        # 基础性能测试
        performance_tests = [
            {
                "name": "Health Check Performance",
                "method": "GET",
                "path": "/health",
                "target_time_ms": 50,
                "concurrent_users": 1,
                "duration_seconds": 10,
            },
            {
                "name": "Root Endpoint Performance",
                "method": "GET",
                "path": "/",
                "target_time_ms": 30,
                "concurrent_users": 1,
                "duration_seconds": 10,
            },
        ]

        results = []

        for test_case in performance_tests:
            result = await self._run_concurrent_test(test_case)
            results.append(result)

        self.test_results["performance_tests"] = results
        return results

    async def _run_concurrent_test(self, test_case: Dict) -> Dict:
        """运行并发测试"""
        logger.info(f"🚀 运行 {test_case['name']}")

        async def single_request():
            start_time = time.time()
            try:
                async with AsyncClient(app=enhanced_app, base_url=self.base_url) as client:
                    response = await client.request(test_case["method"], test_case["path"])
                    end_time = time.time()
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response_time_ms": (end_time - start_time) * 1000,
                    }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": (end_time - start_time) * 1000,
                }

        # 并发执行
        start_time = time.time()
        tasks = [single_request() for _ in range(test_case["concurrent_users"])]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # 分析结果
        successful_requests = [r for r in results if r["success"]]
        response_times = [r["response_time_ms"] for r in successful_requests]

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response_time = max_response_time = min_response_time = p95_response_time = 0

        performance_result = {
            "name": test_case["name"],
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(results) - len(successful_requests),
            "success_rate": len(successful_requests) / len(results) if results else 0,
            "avg_response_time_ms": avg_response_time,
            "max_response_time_ms": max_response_time,
            "min_response_time_ms": min_response_time,
            "p95_response_time_ms": p95_response_time,
            "target_time_ms": test_case["target_time_ms"],
            "meets_target": avg_response_time <= test_case["target_time_ms"],
            "total_duration_seconds": end_time - start_time,
            "requests_per_second": len(results) / (end_time - start_time),
        }

        if performance_result["meets_target"]:
            logger.info(f"✅ {test_case['name']}: {avg_response_time:.2f}ms <= {test_case['target_time_ms']}ms")
        else:
            logger.warning(f"⚠️ {test_case['name']}: {avg_response_time:.2f}ms > {test_case['target_time_ms']}ms")

        return performance_result

    async def run_security_tests(self):
        """运行安全测试"""
        logger.info("🔒 开始安全测试...")

        security_tests = [
            {
                "name": "SQL Injection Test",
                "method": "GET",
                "path": "/health",
                "params": {"test": "'; DROP TABLE users; --"},
                "expected_behavior": "should_not_execute_sql",
            },
            {
                "name": "XSS Test",
                "method": "GET",
                "path": "/",
                "params": {"test": '<script>alert("xss")</script>'},
                "expected_behavior": "should_not_execute_script",
            },
        ]

        results = []
        async with AsyncClient(app=enhanced_app, base_url=self.base_url) as client:
            for test_case in security_tests:
                try:
                    response = await client.request(
                        test_case["method"],
                        test_case["path"],
                        params=test_case.get("params"),
                    )

                    # 检查响应是否包含恶意内容
                    response_text = response.text.lower()
                    contains_malicious = any(
                        indicator in response_text for indicator in ["sql", "script", "alert", "drop", "select"]
                    )

                    result = {
                        "name": test_case["name"],
                        "status_code": response.status_code,
                        "contains_malicious_content": contains_malicious,
                        "passed": not contains_malicious and response.status_code < 500,
                    }

                    if result["passed"]:
                        logger.info(f"✅ {test_case['name']}: 安全测试通过")
                    else:
                        logger.warning(f"⚠️ {test_case['name']}: 可能存在安全问题")

                    results.append(result)

                except Exception as e:
                    results.append({"name": test_case["name"], "passed": False, "error": str(e)})
                    logger.error(f"❌ {test_case['name']}: {str(e)}")

        self.test_results["security_tests"] = results
        return results

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """运行覆盖率分析"""
        logger.info("📊 开始覆盖率分析...")

        try:
            import subprocess
            import sys

            # 运行pytest覆盖率测试
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term-missing",
                "tests/",
                "-v",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # 读取覆盖率报告
                try:
                    with open("coverage.json", "r") as f:
                        coverage_data = json.load(f)

                    coverage_result = {
                        "overall_coverage": coverage_data["totals"]["percent_covered"],
                        "files": coverage_data["files"],
                        "meets_target": coverage_data["totals"]["percent_covered"] >= 80.0,
                        "lines_covered": coverage_data["totals"]["covered_lines"],
                        "lines_missing": coverage_data["totals"]["missing_lines"],
                        "total_lines": coverage_data["totals"]["num_statements"],
                    }

                    logger.info(f"✅ 覆盖率分析完成: {coverage_result['overall_coverage']:.2f}%")
                    return coverage_result

                except Exception as e:
                    logger.error(f"读取覆盖率报告失败: {e}")
                    return {"error": str(e), "meets_target": False}

            else:
                logger.error(f"覆盖率测试失败: {result.stderr}")
                return {"error": result.stderr, "meets_target": False}

        except subprocess.TimeoutExpired:
            logger.error("覆盖率测试超时")
            return {"error": "Test timeout", "meets_target": False}

        except Exception as e:
            logger.error(f"覆盖率分析失败: {e}")
            return {"error": str(e), "meets_target": False}

    async def run_full_test_suite(self) -> Dict[str, Any]:
        """运行完整测试套件"""
        logger.info("🚀 开始完整测试套件...")

        start_time = time.time()

        # 运行所有测试
        functional_results = await self.run_functional_tests()
        performance_results = await self.run_performance_tests()
        security_results = await self.run_security_tests()
        coverage_results = self.run_coverage_analysis()

        end_time = time.time()

        # 计算总体统计
        total_tests = len(functional_results) + len(performance_results) + len(security_results)

        passed_tests = (
            sum(1 for r in functional_results if r.get("passed", False))
            + sum(1 for r in performance_results if r.get("meets_target", False))
            + sum(1 for r in security_results if r.get("passed", False))
        )

        overall_summary = {
            "total_execution_time_seconds": end_time - start_time,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "coverage_meets_target": coverage_results.get("meets_target", False),
            "overall_coverage": coverage_results.get("overall_coverage", 0),
            "test_results": self.test_results,
        }

        logger.info(f"✅ 测试套件完成: {passed_tests}/{total_tests} 通过 ({overall_summary['success_rate']:.1%})")
        logger.info(f"📊 覆盖率: {overall_summary['overall_coverage']:.1f}%")

        return overall_summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        report = []
        report.append("# 增强测试套件报告")
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 总体统计
        report.append("## 总体统计")
        report.append(f"- 总执行时间: {results['total_execution_time_seconds']:.2f}s")
        report.append(f"- 总测试数: {results['total_tests']}")
        report.append(f"- 通过测试数: {results['passed_tests']}")
        report.append(f"- 失败测试数: {results['failed_tests']}")
        report.append(f"- 成功率: {results['success_rate']:.1%}")
        report.append(f"- 代码覆盖率: {results['overall_coverage']:.1f}%")
        report.append(f"- 覆盖率达标: {'✅' if results['coverage_meets_target'] else '❌'}")
        report.append("")

        # 功能测试结果
        if results["test_results"]["functional_tests"]:
            report.append("## 功能测试结果")
            for test in results["test_results"]["functional_tests"]:
                status = "✅" if test.get("passed", False) else "❌"
                report.append(f"- {status} {test['name']}: {test.get('response_time_ms', 0):.2f}ms")
            report.append("")

        # 性能测试结果
        if results["test_results"]["performance_tests"]:
            report.append("## 性能测试结果")
            for test in results["test_results"]["performance_tests"]:
                status = "✅" if test.get("meets_target", False) else "⚠️"
                report.append(
                    f"- {status} {test['name']}: {test.get('avg_response_time_ms', 0):.2f}ms (目标: {test.get('target_time_ms', 0)}ms)"
                )
                report.append(f"  - 成功率: {test.get('success_rate', 0):.1%}")
                report.append(f"  - RPS: {test.get('requests_per_second', 0):.1f}")
            report.append("")

        # 安全测试结果
        if results["test_results"]["security_tests"]:
            report.append("## 安全测试结果")
            for test in results["test_results"]["security_tests"]:
                status = "✅" if test.get("passed", False) else "❌"
                report.append(f"- {status} {test['name']}")
            report.append("")

        return "\n".join(report)


# 便捷函数
async def run_enhanced_tests():
    """运行增强测试套件"""
    test_suite = EnhancedTestSuite()
    results = await test_suite.run_full_test_suite()

    # 生成报告
    report = test_suite.generate_test_report(results)

    # 保存报告
    with open("enhanced_test_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("📄 测试报告已保存到 enhanced_test_report.md")

    return results


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(run_enhanced_tests())
