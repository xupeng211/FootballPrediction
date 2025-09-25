#!/usr/bin/env python3
"""
Comprehensive MCP Health Check Script
Tests all MCP servers for connectivity and functionality
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import docker
import requests


class MCPHealthChecker:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "global_mcp": {},
            "project_mcp": {},
            "summary": {"healthy": 0, "unhealthy": 0, "total": 0},
        }
        self.reports = []

    def add_result(self, category, name, status, response, error=None):
        """Add a health check result"""
        result = {
            "name": name,
            "status": status,  # "✅ 正常" or "❌ 异常"
            "response": response,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        if category not in self.results:
            self.results[category] = {}

        self.results[category][name] = result

        if status == "✅ 正常":
            self.results["summary"]["healthy"] += 1
        else:
            self.results["summary"]["unhealthy"] += 1
        self.results["summary"]["total"] += 1

    def log(self, message):
        """Log a message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        self.reports.append(f"[{timestamp}] {message}")

    # Global MCP Infrastructure Checks
    def check_postgresql_mcp(self):
        """Check PostgreSQL MCP - Execute SELECT 1"""
        self.log("🔍 检查 PostgreSQL MCP...")

        try:
            # Direct database connection test
            import psycopg2

            conn = psycopg2.connect(
                host="localhost",
                port="5432",
                user="postgres",
                password="postgres",
                database="postgres",
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == 1:
                self.add_result(
                    "global_mcp",
                    "PostgreSQL MCP",
                    "✅ 正常",
                    f"SELECT 1 返回: {result[0]}",
                )
                self.log("✅ PostgreSQL MCP: 连接正常")
            else:
                self.add_result(
                    "global_mcp",
                    "PostgreSQL MCP",
                    "❌ 异常",
                    "查询结果异常",
                    f"Expected 1, got {result}",
                )
                self.log("❌ PostgreSQL MCP: 查询结果异常")

        except Exception as e:
            self.add_result("global_mcp", "PostgreSQL MCP", "❌ 异常", f"连接失败: {str(e)}")
            self.log(f"❌ PostgreSQL MCP: {str(e)}")

    def check_redis_mcp(self):
        """Check Redis MCP - Execute PING"""
        self.log("🔍 检查 Redis MCP...")

        try:
            import redis

            # Try without password first
            r = redis.Redis(host="localhost", port=6379, decode_responses=True)
            result = r.ping()

            if result:
                self.add_result("global_mcp", "Redis MCP", "✅ 正常", f"PING 返回: {result}")
                self.log("✅ Redis MCP: 连接正常")
            else:
                self.add_result("global_mcp", "Redis MCP", "❌ 异常", "PING 返回 False")
                self.log("❌ Redis MCP: PING 返回 False")

        except Exception as e:
            # Try with password
            try:
                r = redis.Redis(
                    host="localhost",
                    port=6379,
                    password="redispass",
                    decode_responses=True,
                )
                result = r.ping()

                if result:
                    self.add_result(
                        "global_mcp", "Redis MCP", "✅ 正常", f"PING 返回: {result}"
                    )
                    self.log("✅ Redis MCP: 连接正常")
                else:
                    self.add_result("global_mcp", "Redis MCP", "❌ 异常", "PING 返回 False")
                    self.log("❌ Redis MCP: PING 返回 False")

            except Exception as e2:
                self.add_result("global_mcp", "Redis MCP", "❌ 异常", f"连接失败: {str(e2)}")
                self.log(f"❌ Redis MCP: {str(e2)}")

    def check_kafka_mcp(self):
        """Check Kafka MCP - List available topics"""
        self.log("🔍 检查 Kafka MCP...")

        try:
            from kafka import KafkaAdminClient, KafkaConsumer
            from kafka.errors import KafkaError

            # List topics using admin client
            admin_client = KafkaAdminClient(
                bootstrap_servers="localhost:9092", client_id="mcp-health-check"
            )

            topics = admin_client.list_topics()
            admin_client.close()

            if isinstance(topics, list):
                self.add_result(
                    "global_mcp",
                    "Kafka MCP",
                    "✅ 正常",
                    f"可用 topics: {topics[:5]}{'...' if len(topics) > 5 else ''}",
                )
                self.log(f"✅ Kafka MCP: 发现 {len(topics)} 个topics")
            else:
                self.add_result(
                    "global_mcp",
                    "Kafka MCP",
                    "✅ 正常",
                    f"Kafka连接正常，返回类型: {type(topics)}",
                )
                self.log("✅ Kafka MCP: 连接正常")

        except Exception as e:
            self.add_result("global_mcp", "Kafka MCP", "❌ 异常", f"连接失败: {str(e)}")
            self.log(f"❌ Kafka MCP: {str(e)}")

    def check_docker_mcp(self):
        """Check Docker MCP - List running containers"""
        self.log("🔍 检查 Docker MCP...")

        try:
            # Use subprocess instead of docker-py to avoid WSL connection issues
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                container_names = [
                    name for name in result.stdout.strip().split("\n") if name
                ]
                self.add_result(
                    "global_mcp",
                    "Docker MCP",
                    "✅ 正常",
                    f"运行中的容器: {container_names}",
                )
                self.log(f"✅ Docker MCP: 发现 {len(container_names)} 个运行中的容器")
            else:
                self.add_result(
                    "global_mcp",
                    "Docker MCP",
                    "❌ 异常",
                    f"命令执行失败: {result.stderr}",
                )
                self.log(f"❌ Docker MCP: 命令执行失败")

        except Exception as e:
            self.add_result(
                "global_mcp", "Docker MCP", "❌ 异常", f"Docker命令执行失败: {str(e)}"
            )
            self.log(f"❌ Docker MCP: {str(e)}")

    def check_kubernetes_mcp(self):
        """Check Kubernetes MCP - List pods in default namespace"""
        self.log("🔍 检查 Kubernetes MCP...")

        try:
            from kubernetes import client, config

            config.load_kube_config()

            v1 = client.CoreV1Api()
            pods = v1.list_namespaced_pod(namespace="default")

            pod_names = [pod.metadata.name for pod in pods.items]
            self.add_result(
                "global_mcp",
                "Kubernetes MCP",
                "✅ 正常",
                f"默认命名空间 pods: {pod_names}",
            )
            self.log(f"✅ Kubernetes MCP: 发现 {len(pod_names)} 个pods")

        except Exception as e:
            self.add_result(
                "global_mcp",
                "Kubernetes MCP",
                "❌ 异常",
                f"Kubernetes连接失败: {str(e)}",
            )
            self.log(f"❌ Kubernetes MCP: {str(e)}")

    def check_prometheus_mcp(self):
        """Check Prometheus MCP - Query up metric"""
        self.log("🔍 检查 Prometheus MCP...")

        try:
            response = requests.get(
                "http://localhost:9090/api/v1/query?query=up", timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data["status"] == "success":
                    metrics = data["data"]["result"]
                    self.add_result(
                        "global_mcp",
                        "Prometheus MCP",
                        "✅ 正常",
                        f"up 指标返回 {len(metrics)} 个结果",
                    )
                    self.log(f"✅ Prometheus MCP: 成功查询 up 指标")
                else:
                    self.add_result(
                        "global_mcp",
                        "Prometheus MCP",
                        "❌ 异常",
                        f"API返回状态: {data['status']}",
                    )
                    self.log(f"❌ Prometheus MCP: API返回状态异常")
            else:
                self.add_result(
                    "global_mcp",
                    "Prometheus MCP",
                    "❌ 异常",
                    f"HTTP状态码: {response.status_code}",
                )
                self.log(f"❌ Prometheus MCP: HTTP {response.status_code}")

        except Exception as e:
            self.add_result("global_mcp", "Prometheus MCP", "❌ 异常", f"连接失败: {str(e)}")
            self.log(f"❌ Prometheus MCP: {str(e)}")

    def check_grafana_mcp(self):
        """Check Grafana MCP - List available dashboards"""
        self.log("🔍 检查 Grafana MCP...")

        try:
            # Try with Basic Authentication (admin:admin)
            auth_headers = {"Authorization": "Basic YWRtaW46YWRtaW4="}
            response = requests.get(
                "http://localhost:3000/api/search", headers=auth_headers, timeout=10
            )

            if response.status_code == 200:
                dashboards = response.json()
                dashboard_count = len(dashboards) if isinstance(dashboards, list) else 0
                self.add_result(
                    "global_mcp",
                    "Grafana MCP",
                    "✅ 正常",
                    f"发现 {dashboard_count} 个dashboards",
                )
                self.log(f"✅ Grafana MCP: 发现 {dashboard_count} 个dashboards")
            else:
                # Also check if Grafana is accessible at all
                health_response = requests.get(
                    "http://localhost:3000/api/health", timeout=5
                )
                if health_response.status_code == 200:
                    self.add_result(
                        "global_mcp",
                        "Grafana MCP",
                        "✅ 正常",
                        "Grafana服务正常运行，需要认证访问API",
                    )
                    self.log("✅ Grafana MCP: 服务正常运行，需要认证访问API")
                else:
                    self.add_result(
                        "global_mcp",
                        "Grafana MCP",
                        "❌ 异常",
                        f"HTTP状态码: {response.status_code}",
                    )
                    self.log(f"❌ Grafana MCP: HTTP {response.status_code}")

        except Exception as e:
            self.add_result("global_mcp", "Grafana MCP", "❌ 异常", f"连接失败: {str(e)}")
            self.log(f"❌ Grafana MCP: {str(e)}")

    # Project-specific MCP Checks
    def check_mlflow_mcp(self):
        """Check MLflow MCP - List recent experiments"""
        self.log("🔍 检查 MLflow MCP...")

        try:
            import mlflow

            mlflow.set_tracking_uri("sqlite:///mlflow.db")

            client = mlflow.MlflowClient()
            experiments = client.search_experiments()

            experiment_names = [exp.name for exp in experiments]
            self.add_result(
                "project_mcp",
                "MLflow MCP",
                "✅ 正常",
                f"发现 {len(experiments)} 个experiments: {experiment_names}",
            )
            self.log(f"✅ MLflow MCP: 发现 {len(experiments)} 个experiments")

        except Exception as e:
            self.add_result("project_mcp", "MLflow MCP", "❌ 异常", f"连接失败: {str(e)}")
            self.log(f"❌ MLflow MCP: {str(e)}")

    def check_feast_mcp(self):
        """Check Feast MCP - List feature views"""
        self.log("🔍 检查 Feast MCP...")

        try:
            import yaml
            from feast import FeatureStore

            # Check if feature_store.yaml exists
            if Path("feature_store.yaml").exists():
                store = FeatureStore(repo_path=".")

                # Get feature views
                feature_views = store.list_feature_views()
                feature_view_names = [fv.name for fv in feature_views]

                self.add_result(
                    "project_mcp",
                    "Feast MCP",
                    "✅ 正常",
                    f"发现 {len(feature_views)} 个feature views: {feature_view_names}",
                )
                self.log(f"✅ Feast MCP: 发现 {len(feature_views)} 个feature views")
            else:
                self.add_result(
                    "project_mcp",
                    "Feast MCP",
                    "❌ 异常",
                    "feature_store.yaml 文件不存在",
                )
                self.log("❌ Feast MCP: feature_store.yaml 文件不存在")

        except Exception as e:
            self.add_result("project_mcp", "Feast MCP", "❌ 异常", f"连接失败: {str(e)}")
            self.log(f"❌ Feast MCP: {str(e)}")

    def check_coverage_mcp(self):
        """Check Coverage MCP - Read coverage.xml and output overall coverage"""
        self.log("🔍 检查 Coverage MCP...")

        try:
            # Try to find coverage files
            coverage_files = ["coverage.xml", ".coverage", "htmlcov/index.html"]

            found_coverage = False
            for cov_file in coverage_files:
                if Path(cov_file).exists():
                    found_coverage = True

                    if cov_file == "coverage.xml":
                        # Parse XML coverage report
                        import xml.etree.ElementTree as ET

                        tree = ET.parse(cov_file)
                        root = tree.getroot()

                        # Get coverage percentage
                        coverage_elem = root.find(".//coverage")
                        if coverage_elem is not None:
                            coverage_percent = coverage_elem.get("line-rate", "0")
                            coverage_percent = float(coverage_percent) * 100

                            self.add_result(
                                "project_mcp",
                                "Coverage MCP",
                                "✅ 正常",
                                f"整体覆盖率: {coverage_percent:.1f}% (从 {cov_file})",
                            )
                            self.log(f"✅ Coverage MCP: 整体覆盖率 {coverage_percent:.1f}%")
                            break

                    elif cov_file == ".coverage":
                        # Use coverage package to read data
                        import coverage

                        cov = coverage.Coverage()
                        cov.load()

                        # Get coverage data
                        data = cov.get_data()
                        files = data.measured_files()

                        self.add_result(
                            "project_mcp",
                            "Coverage MCP",
                            "✅ 正常",
                            f"发现覆盖率数据文件，包含 {len(files)} 个文件",
                        )
                        self.log(f"✅ Coverage MCP: 发现 {len(files)} 个覆盖率文件")
                        break

            if not found_coverage:
                # Check if we can generate coverage
                self.add_result(
                    "project_mcp",
                    "Coverage MCP",
                    "⚠️ 警告",
                    "未找到覆盖率文件，可能需要运行测试生成",
                )
                self.log("⚠️ Coverage MCP: 未找到覆盖率文件")

        except Exception as e:
            self.add_result("project_mcp", "Coverage MCP", "❌ 异常", f"读取失败: {str(e)}")
            self.log(f"❌ Coverage MCP: {str(e)}")

    def check_pytest_mcp(self):
        """Check Pytest MCP - Execute --collect-only to verify test discovery"""
        self.log("🔍 检查 Pytest MCP...")

        try:
            # Run pytest with --collect-only
            result = subprocess.run(
                ["pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Count collected tests
                output_lines = result.stdout.strip().split("\n")
                test_count = 0

                for line in output_lines:
                    if "test session starts" in line.lower():
                        continue
                    if line.strip() and not line.startswith("==="):
                        test_count += 1

                self.add_result(
                    "project_mcp",
                    "Pytest MCP",
                    "✅ 正常",
                    f"成功发现测试，输出: {result.stdout[:200]}...",
                )
                self.log(f"✅ Pytest MCP: 测试发现功能正常")
            else:
                self.add_result(
                    "project_mcp",
                    "Pytest MCP",
                    "❌ 异常",
                    f"测试收集失败: {result.stderr}",
                )
                self.log(f"❌ Pytest MCP: 测试收集失败")

        except Exception as e:
            self.add_result("project_mcp", "Pytest MCP", "❌ 异常", f"执行失败: {str(e)}")
            self.log(f"❌ Pytest MCP: {str(e)}")

    def generate_report(self):
        """Generate comprehensive health check report"""
        self.log("📋 生成健康检查报告...")

        # Create docs directory if it doesn't exist
        Path("docs").mkdir(exist_ok=True)

        # Generate markdown report
        report_content = f"""# MCP 健康检查报告

**检查时间**: {self.results['timestamp']}
**检查范围**: 全局基础设施MCP + 项目专用MCP

## 检查摘要

- **正常服务**: {self.results['summary']['healthy']}
- **异常服务**: {self.results['summary']['unhealthy']}
- **总服务数**: {self.results['summary']['total']}
- **健康率**: {self.results['summary']['healthy']/self.results['summary']['total']*100:.1f}%

## 全局基础设施MCP检查结果

"""

        # Add global MCP results
        for name, result in self.results.get("global_mcp", {}).items():
            status_icon = "✅" if result["status"] == "✅ 正常" else "❌"
            report_content += f"### {name} {status_icon}\n\n"
            report_content += f"- **状态**: {result['status']}\n"
            report_content += f"- **响应**: {result['response']}\n"
            if result.get("error"):
                report_content += f"- **错误**: {result['error']}\n"
            report_content += f"- **检查时间**: {result['timestamp']}\n\n"

        # Add project MCP results
        report_content += "## 项目专用MCP检查结果\n\n"

        for name, result in self.results.get("project_mcp", {}).items():
            status_icon = "✅" if result["status"] == "✅ 正常" else "❌"
            report_content += f"### {name} {status_icon}\n\n"
            report_content += f"- **状态**: {result['status']}\n"
            report_content += f"- **响应**: {result['response']}\n"
            if result.get("error"):
                report_content += f"- **错误**: {result['error']}\n"
            report_content += f"- **检查时间**: {result['timestamp']}\n\n"

        # Add execution logs
        report_content += "## 执行日志\n\n"
        report_content += "```\n"
        for log in self.reports:
            report_content += f"{log}\n"
        report_content += "```\n"

        # Add recommendations
        report_content += "## 建议和后续步骤\n\n"

        unhealthy_count = self.results["summary"]["unhealthy"]
        if unhealthy_count > 0:
            report_content += f"### 🔧 需要修复的问题 ({unhealthy_count}个)\n\n"

            for category in ["global_mcp", "project_mcp"]:
                for name, result in self.results.get(category, {}).items():
                    if result["status"] != "✅ 正常":
                        report_content += (
                            f"- **{name}**: {result.get('error', 'Unknown error')}\n"
                        )

            report_content += "\n"

        report_content += "### 🎯 建议的后续步骤\n\n"
        report_content += "1. **修复异常服务**: 根据上述错误信息修复连接问题\n"
        report_content += "2. **配置环境变量**: 确保所有服务的连接参数正确\n"
        report_content += "3. **重启服务**: 对配置变更的服务进行重启\n"
        report_content += "4. **定期检查**: 建议设置定时任务进行健康检查\n"
        report_content += "5. **监控告警**: 对关键MCP服务设置监控告警\n"

        # Write report
        with open("docs/MCP_HEALTH_CHECK.md", "w", encoding="utf-8") as f:
            f.write(report_content)

        self.log(f"✅ 健康检查报告已生成: docs/MCP_HEALTH_CHECK.md")

    def run_full_check(self):
        """Run comprehensive MCP health check"""
        self.log("🚀 开始MCP健康检查...")
        self.log("=" * 50)

        # Global MCP Infrastructure Checks
        self.log("\n📋 全局基础设施MCP检查:")
        self.check_postgresql_mcp()
        self.check_redis_mcp()
        self.check_kafka_mcp()
        self.check_docker_mcp()
        self.check_kubernetes_mcp()
        self.check_prometheus_mcp()
        self.check_grafana_mcp()

        # Project-specific MCP Checks
        self.log("\n📋 项目专用MCP检查:")
        self.check_mlflow_mcp()
        self.check_feast_mcp()
        self.check_coverage_mcp()
        self.check_pytest_mcp()

        # Generate report
        self.generate_report()

        # Print summary
        self.log("\n" + "=" * 50)
        self.log("📊 检查摘要:")
        self.log(f"   总服务数: {self.results['summary']['total']}")
        self.log(f"   正常服务: {self.results['summary']['healthy']}")
        self.log(f"   异常服务: {self.results['summary']['unhealthy']}")
        self.log(
            f"   健康率: {self.results['summary']['healthy']/self.results['summary']['total']*100:.1f}%"
        )

        self.log("✅ MCP健康检查完成")


if __name__ == "__main__":
    checker = MCPHealthChecker()
    checker.run_full_check()
