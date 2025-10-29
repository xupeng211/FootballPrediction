#!/usr/bin/env python3
"""
🔍 最终系统验证脚本

基于最佳实践的完整系统验证，确保种子用户测试前的系统质量
"""

import asyncio
import json
import time
import statistics
from datetime import datetime, timedelta
import httpx


class FinalSystemValidator:
    """最终系统验证器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.validation_results = []
        self.performance_metrics = []

    def log_validation(
        self,
        test_name: str,
        status: str,
        details: str = "",
        score: float = None,
        priority: str = "normal",
        recommendation: str = None,
    ):
        """记录验证结果"""
        result = {
            "test_name": test_name,
            "status": status,  # pass, fail, warning
            "details": details,
            "score": score,
            "priority": priority,  # critical, high, normal, low
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat(),
        }
        self.validation_results.append(result)

        # 状态图标
        icons = {"pass": "✅", "fail": "❌", "warning": "⚠️"}
        priority_icons = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}

        print(f"{icons.get(status, '❓')} {priority_icons.get(priority, '🔵')} {test_name}")
        if details:
            print(f"   📝 {details}")
        if score is not None:
            print(f"   📊 评分: {score:.1f}/100")
        if recommendation:
            print(f"   💡 建议: {recommendation}")

    async def validate_system_stability(self):
        """验证系统稳定性"""
        print("\n🏗️ 第一阶段：系统稳定性验证")
        print("=" * 50)

        stability_tests = [
            ("服务可用性", self.check_service_availability, "critical"),
            ("基础健康检查", self.check_basic_health, "critical"),
            ("数据库连接", self.check_database_connectivity, "critical"),
            ("API响应一致性", self.check_api_consistency, "high"),
            ("错误处理机制", self.check_error_handling, "high"),
            ("并发处理能力", self.check_concurrency, "normal"),
        ]

        for test_name, test_func, priority in stability_tests:
            try:
                score, status, details, recommendation = await test_func()
                self.log_validation(test_name, status, details, score, priority, recommendation)
            except Exception as e:
                self.log_validation(
                    test_name, "fail", f"验证失败: {str(e)}", 0, priority, "检查系统状态"
                )

    async def check_service_availability(self):
        """检查服务可用性"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.api_base_url}/")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "运行中":
                    return 100, "pass", "服务正常运行", "系统状态良好"
                else:
                    return 80, "warning", "服务运行但状态异常", "检查服务配置"
            else:
                return 0, "fail", f"HTTP {response.status_code}", "立即检查服务状态"
        except Exception:
            return 0, "fail", "服务不可访问", "启动服务并检查网络"

    async def check_basic_health(self):
        """检查基础健康状态"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.api_base_url}/api/health/")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    checks = data.get("checks", {})
                    db_status = checks.get("database", {}).get("status", "unknown")
                    latency = checks.get("database", {}).get("latency_ms", 0)

                    if db_status == "healthy" and latency < 100:
                        return 100, "pass", f"系统健康，数据库延迟: {latency}ms", "系统完全健康"
                    else:
                        return (
                            80,
                            "warning",
                            f"数据库状态: {db_status}, 延迟: {latency}ms",
                            "优化数据库性能",
                        )
                else:
                    return 60, "warning", "系统不健康", "检查系统组件"
            else:
                return 0, "fail", f"健康检查失败: HTTP {response.status_code}", "修复健康检查端点"
        except Exception:
            return 0, "fail", "健康检查不可用", "检查健康检查配置"

    async def check_database_connectivity(self):
        """检查数据库连接"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base_url}/api/health/")

            if response.status_code == 200:
                data = response.json()
                checks = data.get("checks", {})
                db_check = checks.get("database", {})

                if db_check.get("status") == "healthy":
                    latency = db_check.get("latency_ms", 0)
                    if latency < 50:
                        score = 100
                        status = "pass"
                    elif latency < 100:
                        score = 85
                        status = "warning"
                    else:
                        score = 70
                        status = "warning"

                    details = f"数据库连接正常，延迟: {latency}ms"
                    recommendation = "数据库性能优秀" if score == 100 else "优化数据库查询"
                    return score, status, details, recommendation
                else:
                    return 0, "fail", "数据库连接失败", "检查数据库配置和连接"
            else:
                return 0, "fail", "无法获取数据库状态", "检查健康检查端点"
        except Exception:
            return 0, "fail", "数据库连接测试失败", "检查数据库服务"

    async def check_api_consistency(self):
        """检查API响应一致性"""
        endpoints = ["/api/health/", "/api/v1/data/teams", "/api/v1/predictions/health", "/docs"]

        consistency_scores = []

        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")

                if response.status_code == 200:
                    # 检查响应格式一致性
                    try:
                        data = response.json()
                        if isinstance(data, dict) or isinstance(data, list):
                            consistency_scores.append(100)
                        else:
                            consistency_scores.append(80)
except Exception:
                        consistency_scores.append(60)
                else:
                    consistency_scores.append(0)
except Exception:
                consistency_scores.append(0)

        avg_consistency = statistics.mean(consistency_scores)

        if avg_consistency >= 90:
            return 100, "pass", "API响应一致性优秀", "保持当前API设计"
        elif avg_consistency >= 70:
            return 80, "warning", f"API一致性: {avg_consistency:.1f}%", "标准化API响应格式"
        else:
            return 50, "fail", f"API一致性较差: {avg_consistency:.1f}%", "重构API响应格式"

    async def check_error_handling(self):
        """检查错误处理机制"""
        error_tests = [
            ("/api/v1/nonexistent", 404),
            ("/api/v1/auth/me", 401),  # 未授权访问
        ]

        handling_scores = []

        for endpoint, expected_status in error_tests:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")

                if response.status_code == expected_status:
                    # 检查错误响应格式
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict) and "detail" in error_data:
                            # 检查是否暴露敏感信息
                            sensitive_info = ["password", "secret", "stack", "trace"]
                            has_sensitive = any(
                                info in str(error_data).lower() for info in sensitive_info
                            )

                            if has_sensitive:
                                handling_scores.append(60)  # 暴露敏感信息
                            else:
                                handling_scores.append(100)  # 良好的错误处理
                        else:
                            handling_scores.append(80)
except Exception:
                        handling_scores.append(70)
                else:
                    handling_scores.append(50)
except Exception:
                handling_scores.append(0)

        avg_handling = statistics.mean(handling_scores)

        if avg_handling >= 90:
            return 100, "pass", "错误处理机制完善", "保持当前错误处理"
        elif avg_handling >= 70:
            return 80, "warning", f"错误处理: {avg_handling:.1f}%", "优化错误响应格式"
        else:
            return 50, "fail", f"错误处理需要改进: {avg_handling:.1f}%", "重构错误处理机制"

    async def check_concurrency(self):
        """检查并发处理能力"""

        async def make_request():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}/api/health/")
                    return response.status_code == 200
except Exception:
                return False

        # 并发测试
        concurrent_levels = [5, 10, 20]
        concurrency_scores = []

        for level in concurrent_levels:
            start_time = time.time()
            tasks = [make_request() for _ in range(level)]
            results = await asyncio.gather(*tasks)
            duration = time.time() - start_time

            success_rate = sum(results) / len(results)

            if success_rate >= 0.95 and duration < 2.0:
                concurrency_scores.append(100)
            elif success_rate >= 0.90 and duration < 3.0:
                concurrency_scores.append(85)
            elif success_rate >= 0.80:
                concurrency_scores.append(70)
            else:
                concurrency_scores.append(50)

        avg_concurrency = statistics.mean(concurrency_scores)

        if avg_concurrency >= 90:
            return 100, "pass", "并发处理能力优秀", "系统支持高并发访问"
        elif avg_concurrency >= 75:
            return 80, "warning", f"并发处理: {avg_concurrency:.1f}%", "优化并发处理性能"
        else:
            return 60, "warning", f"并发处理需要改进: {avg_concurrency:.1f}%", "增强系统并发能力"

    async def validate_functionality_completeness(self):
        """验证功能完整性"""
        print("\n🔧 第二阶段：功能完整性验证")
        print("=" * 50)

        functionality_tests = [
            ("核心数据API", self.check_core_data_apis, "critical"),
            ("用户认证系统", self.check_auth_system, "critical"),
            ("预测功能", self.check_prediction_features, "high"),
            ("监控系统", self.check_monitoring_system, "high"),
            ("API文档完整性", self.check_api_documentation, "normal"),
        ]

        for test_name, test_func, priority in functionality_tests:
            try:
                score, status, details, recommendation = await test_func()
                self.log_validation(test_name, status, details, score, priority, recommendation)
            except Exception as e:
                self.log_validation(
                    test_name, "fail", f"验证失败: {str(e)}", 0, priority, "检查功能实现"
                )

    async def check_core_data_apis(self):
        """检查核心数据API"""
        data_apis = [
            ("/api/v1/data/teams", "球队数据"),
            ("/api/v1/data/leagues", "联赛数据"),
            ("/api/v1/data/matches", "比赛数据"),
            ("/api/v1/data/odds", "赔率数据"),
        ]

        api_scores = []
        working_apis = []

        for endpoint, name in data_apis:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        # 检查数据质量
                        sample = data[0]
                        if isinstance(sample, dict) and len(sample) >= 3:
                            api_scores.append(100)
                            working_apis.append(name)
                        else:
                            api_scores.append(80)
                            working_apis.append(name)
                    else:
                        api_scores.append(60)
                else:
                    api_scores.append(0)
except Exception:
                api_scores.append(0)

        avg_score = statistics.mean(api_scores)
        working_count = len(working_apis)

        if working_count == len(data_apis) and avg_score >= 90:
            return (
                100,
                "pass",
                f"所有核心数据API正常工作 ({working_count}/{len(data_apis)})",
                "数据API完全就绪",
            )
        elif working_count >= 3:
            return (
                85,
                "pass",
                f"核心数据API基本正常 ({working_count}/{len(data_apis)})",
                "修复剩余数据API",
            )
        else:
            return (
                40,
                "fail",
                f"核心数据API异常 ({working_count}/{len(data_apis)})",
                "优先修复数据API",
            )

    async def check_auth_system(self):
        """检查认证系统"""
        auth_tests = [
            (
                "用户注册",
                "/api/v1/auth/register",
                "POST",
                {"username": "test", "email": "test@example.com", "password": "test123"},
            ),
            ("用户登出", "/api/v1/auth/logout", "POST", {}),
        ]

        auth_scores = []

        for test_name, endpoint, method, data in auth_tests:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    if method == "POST":
                        response = await client.post(f"{self.api_base_url}{endpoint}", json=data)
                    else:
                        response = await client.get(f"{self.api_base_url}{endpoint}")

                    if response.status_code in [200, 201]:
                        auth_scores.append(100)
                    else:
                        auth_scores.append(50)
except Exception:
                auth_scores.append(0)

        avg_score = statistics.mean(auth_scores)

        if avg_score >= 90:
            return 100, "pass", "认证系统完全正常", "认证系统就绪"
        elif avg_score >= 70:
            return 80, "warning", f"认证系统基本正常: {avg_score:.1f}%", "优化认证功能"
        else:
            return 40, "fail", f"认证系统存在问题: {avg_score:.1f}%", "修复认证系统"

    async def check_prediction_features(self):
        """检查预测功能"""
        prediction_apis = [
            "/api/v1/predictions/health",
            "/api/v1/predictions/recent",
        ]

        prediction_scores = []

        for endpoint in prediction_apis:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")

                if response.status_code == 200:
                    prediction_scores.append(100)
                else:
                    prediction_scores.append(50)
except Exception:
                prediction_scores.append(0)

        avg_score = statistics.mean(prediction_scores)

        if avg_score >= 90:
            return 100, "pass", "预测功能完全正常", "预测系统就绪"
        elif avg_score >= 70:
            return 80, "warning", f"预测功能基本正常: {avg_score:.1f}%", "优化预测功能"
        else:
            return 40, "fail", f"预测功能存在问题: {avg_score:.1f}%", "修复预测系统"

    async def check_monitoring_system(self):
        """检查监控系统"""
        monitoring_apis = [
            "/api/v1/events/health",
            "/api/v1/observers/status",
            "/api/v1/cqrs/system/status",
            "/api/v1/metrics/prometheus",
        ]

        monitoring_scores = []

        for endpoint in monitoring_apis:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")

                if response.status_code == 200:
                    monitoring_scores.append(100)
                else:
                    monitoring_scores.append(50)
except Exception:
                monitoring_scores.append(0)

        avg_score = statistics.mean(monitoring_scores)

        if avg_score >= 85:
            return 100, "pass", "监控系统完全正常", "监控体系就绪"
        elif avg_score >= 65:
            return 80, "warning", f"监控系统基本正常: {avg_score:.1f}%", "优化监控功能"
        else:
            return 40, "fail", f"监控系统存在问题: {avg_score:.1f}%", "修复监控系统"

    async def check_api_documentation(self):
        """检查API文档完整性"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base_url}/openapi.json")

            if response.status_code == 200:
                openapi_data = response.json()

                # 检查OpenAPI规范完整性
                required_fields = ["openapi", "info", "paths"]
                missing_fields = [field for field in required_fields if field not in openapi_data]

                if not missing_fields:
                    paths = openapi_data.get("paths", {})
                    path_count = len(paths)

                    if path_count >= 20:
                        return 100, "pass", f"API文档完整，包含{path_count}个端点", "文档优秀"
                    elif path_count >= 10:
                        return (
                            85,
                            "pass",
                            f"API文档基本完整，包含{path_count}个端点",
                            "完善剩余文档",
                        )
                    else:
                        return 70, "warning", f"API文档较少，仅{path_count}个端点", "增加API文档"
                else:
                    return (
                        50,
                        "fail",
                        f"OpenAPI规范不完整，缺少: {missing_fields}",
                        "完善OpenAPI规范",
                    )
            else:
                return 0, "fail", f"API文档不可用: HTTP {response.status_code}", "修复API文档生成"
        except Exception:
            return 0, "fail", "API文档测试失败", "检查API文档配置"

    async def validate_performance_benchmarks(self):
        """验证性能基准"""
        print("\n⚡ 第三阶段：性能基准验证")
        print("=" * 50)

        performance_tests = [
            ("响应时间基准", self.check_response_time_benchmarks, "high"),
            ("吞吐量测试", self.check_throughput, "normal"),
            ("资源使用效率", self.check_resource_efficiency, "normal"),
        ]

        for test_name, test_func, priority in performance_tests:
            try:
                score, status, details, recommendation = await test_func()
                self.log_validation(test_name, status, details, score, priority, recommendation)
            except Exception as e:
                self.log_validation(
                    test_name, "fail", f"验证失败: {str(e)}", 0, priority, "检查系统性能"
                )

    async def check_response_time_benchmarks(self):
        """检查响应时间基准"""
        critical_endpoints = ["/api/health/", "/api/v1/data/teams", "/api/v1/predictions/health"]

        response_times = []

        for endpoint in critical_endpoints:
            times = []
            for _ in range(3):  # 每个端点测试3次
                start_time = time.time()
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(f"{self.api_base_url}{endpoint}")
                        if response.status_code == 200:
                            times.append(time.time() - start_time)
except Exception:
                    pass

            if times:
                avg_time = statistics.mean(times)
                response_times.append(avg_time)

        if response_times:
            overall_avg = statistics.mean(response_times)
            max_time = max(response_times)

            # 评分标准
            if overall_avg < 0.1 and max_time < 0.2:  # 平均<100ms, 最大<200ms
                return 100, "pass", f"响应时间优秀: 平均{overall_avg*1000:.0f}ms", "性能优秀"
            elif overall_avg < 0.2 and max_time < 0.5:  # 平均<200ms, 最大<500ms
                return 85, "pass", f"响应时间良好: 平均{overall_avg*1000:.0f}ms", "性能良好"
            elif overall_avg < 0.5 and max_time < 1.0:  # 平均<500ms, 最大<1s
                return 70, "warning", f"响应时间一般: 平均{overall_avg*1000:.0f}ms", "优化响应时间"
            else:
                return 50, "fail", f"响应时间较慢: 平均{overall_avg*1000:.0f}ms", "优化性能"
        else:
            return 0, "fail", "无法测量响应时间", "检查API可用性"

    async def check_throughput(self):
        """检查吞吐量"""

        async def single_request():
            try:
                async with httpx.AsyncClient(timeout=3) as client:
                    response = await client.get(f"{self.api_base_url}/api/health/")
                    return response.status_code == 200
except Exception:
                return False

        # 吞吐量测试：30秒内处理请求数
        test_duration = 10  # 10秒测试
        start_time = time.time()
        request_count = 0
        success_count = 0

        while time.time() - start_time < test_duration:
            tasks = [single_request() for _ in range(5)]  # 每批发送5个请求
            results = await asyncio.gather(*tasks)
            request_count += len(results)
            success_count += sum(results)
            await asyncio.sleep(0.1)  # 短暂延迟

        throughput = request_count / test_duration  # 请求/秒
        success_rate = (success_count / request_count) * 100

        if throughput >= 50 and success_rate >= 95:
            return (
                100,
                "pass",
                f"吞吐量优秀: {throughput:.1f} req/s, 成功率: {success_rate:.1f}%",
                "吞吐量优秀",
            )
        elif throughput >= 30 and success_rate >= 90:
            return (
                85,
                "pass",
                f"吞吐量良好: {throughput:.1f} req/s, 成功率: {success_rate:.1f}%",
                "吞吐量良好",
            )
        elif throughput >= 20 and success_rate >= 85:
            return (
                70,
                "warning",
                f"吞吐量一般: {throughput:.1f} req/s, 成功率: {success_rate:.1f}%",
                "优化吞吐量",
            )
        else:
            return (
                50,
                "fail",
                f"吞吐量较低: {throughput:.1f} req/s, 成功率: {success_rate:.1f}%",
                "优化系统性能",
            )

    async def check_resource_efficiency(self):
        """检查资源使用效率"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 资源使用评分
            if cpu_percent < 50 and memory_percent < 70:
                return (
                    100,
                    "pass",
                    f"资源使用高效: CPU {cpu_percent:.1f}%, 内存 {memory_percent:.1f}%",
                    "资源效率优秀",
                )
            elif cpu_percent < 70 and memory_percent < 80:
                return (
                    85,
                    "pass",
                    f"资源使用良好: CPU {cpu_percent:.1f}%, 内存 {memory_percent:.1f}%",
                    "资源效率良好",
                )
            elif cpu_percent < 85 and memory_percent < 90:
                return (
                    70,
                    "warning",
                    f"资源使用一般: CPU {cpu_percent:.1f}%, 内存 {memory_percent:.1f}%",
                    "优化资源使用",
                )
            else:
                return (
                    50,
                    "fail",
                    f"资源使用较高: CPU {cpu_percent:.1f}%, 内存 {memory_percent:.1f}%",
                    "优化系统资源",
                )
        except ImportError:
            return 80, "warning", "无法检查资源使用情况", "安装psutil进行资源监控"
        except Exception:
            return 50, "fail", "资源检查失败", "检查系统监控"

    def calculate_overall_score(self):
        """计算总体评分"""
        if not self.validation_results:
            return 0, "fail", "无验证结果"

        # 按优先级加权计算
        weights = {"critical": 0.4, "high": 0.3, "normal": 0.2, "low": 0.1}

        total_score = 0
        total_weight = 0

        for result in self.validation_results:
            if result["score"] is not None:
                weight = weights.get(result["priority"], 0.1)
                total_score += result["score"] * weight
                total_weight += weight

        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0

        # 确定整体状态
        critical_failures = [
            r
            for r in self.validation_results
            if r["priority"] == "critical" and r["status"] == "fail"
        ]

        if critical_failures:
            return final_score, "fail", f"存在{len(critical_failures)}个关键问题"
        elif final_score >= 90:
            return final_score, "pass", "系统验证优秀"
        elif final_score >= 80:
            return final_score, "pass", "系统验证良好"
        elif final_score >= 70:
            return final_score, "warning", "系统基本可用，建议优化"
        else:
            return final_score, "fail", "系统需要改进"

    def generate_validation_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("🔍 最终系统验证报告")
        print("=" * 60)

        # 按优先级统计
        priority_stats = {}
        status_stats = {"pass": 0, "fail": 0, "warning": 0}

        for result in self.validation_results:
            priority = result["priority"]
            status = result["status"]

            if priority not in priority_stats:
                priority_stats[priority] = {"count": 0, "avg_score": 0}

            priority_stats[priority]["count"] += 1
            if result["score"] is not None:
                priority_stats[priority]["avg_score"] += result["score"]

            status_stats[status] += 1

        # 计算平均分
        for priority in priority_stats:
            if priority_stats[priority]["count"] > 0:
                priority_stats[priority]["avg_score"] /= priority_stats[priority]["count"]

        print("📊 验证统计:")
        print(f"   总验证项: {len(self.validation_results)}")
        print(f"   ✅ 通过: {status_stats['pass']}")
        print(f"   ❌ 失败: {status_stats['fail']}")
        print(f"   ⚠️ 警告: {status_stats['warning']}")

        print("\n🎯 按优先级分析:")
        for priority, stats in priority_stats.items():
            priority_names = {"critical": "关键", "high": "高", "normal": "普通", "low": "低"}
            icons = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}
            print(
                f"   {icons.get(priority, '🔵')} {priority_names.get(priority, priority)}: {stats['count']}项, 平均分: {stats['avg_score']:.1f}"
            )

        # 计算总体评分
        overall_score, overall_status, overall_message = self.calculate_overall_score()

        print("\n🏆 总体验证结果:")
        print(f"   📊 总体评分: {overall_score:.1f}/100")

        status_icons = {"pass": "✅", "fail": "❌", "warning": "⚠️"}
        print(f"   {status_icons.get(overall_status, '❓')} 整体状态: {overall_message}")

        # 关键问题
        critical_issues = [
            r
            for r in self.validation_results
            if r["priority"] == "critical" and r["status"] in ["fail", "warning"]
        ]

        if critical_issues:
            print("\n🔴 关键问题需要立即处理:")
            for issue in critical_issues:
                print(f"   • {issue['test_name']}: {issue['details']}")
                if issue.get("recommendation"):
                    print(f"     💡 建议: {issue['recommendation']}")

        # 改进建议
        all_recommendations = [
            r.get("recommendation")
            for r in self.validation_results
            if r.get("recommendation") and r["status"] in ["fail", "warning"]
        ]

        if all_recommendations:
            print("\n💡 改进建议:")
            for i, rec in enumerate(all_recommendations[:5], 1):  # 显示前5个建议
                print(f"   {i}. {rec}")

        # 种子用户测试就绪度评估
        print("\n🌱 种子用户测试就绪度评估:")

        if overall_score >= 85 and status_stats["fail"] == 0:
            print("   🟢 完全就绪: 系统验证优秀，可以立即开始种子用户测试")
            readiness_score = 100
        elif (
            overall_score >= 75
            and len(
                [
                    r
                    for r in self.validation_results
                    if r["priority"] == "critical" and r["status"] == "fail"
                ]
            )
            == 0
        ):
            print("   🟡 基本就绪: 系统基本可用，建议修复关键问题后开始测试")
            readiness_score = 80
        else:
            print("   🔴 需要改进: 建议优先修复问题后再进行种子用户测试")
            readiness_score = 60

        print("\n🚀 推荐行动:")
        if readiness_score >= 90:
            print("   ✨ 立即开始种子用户测试！")
            print("   📋 准备测试计划和用户招募")
            print("   🎊 系统已完全就绪")
        elif readiness_score >= 75:
            print("   🔧 优先修复关键问题")
            print("   📋 并行准备种子用户测试计划")
            print("   🌱 问题修复后立即开始测试")
        else:
            print("   🔴 立即修复所有关键问题")
            print("   🔧 进行系统优化和改进")
            print("   📋 重新进行系统验证")

        print("\n🎊 最终系统验证完成!")
        print(f"   验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   总体评分: {overall_score:.1f}/100")
        print(f"   测试就绪度: {readiness_score}/100")
        print("=" * 60)

        return overall_score, readiness_score

    async def run_final_validation(self):
        """运行最终系统验证"""
        print("🔍 开始最终系统验证")
        print("=" * 60)
        print(f"📅 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 验证目标: {self.api_base_url}")
        print("=" * 60)

        # 执行验证阶段
        await self.validate_system_stability()
        await self.validate_functionality_completeness()
        await self.validate_performance_benchmarks()

        # 生成最终报告
        overall_score, readiness_score = self.generate_validation_report()

        return overall_score, readiness_score


async def main():
    """主函数"""
    validator = FinalSystemValidator()
    overall_score, readiness_score = await validator.run_final_validation()

    # 根据验证结果给出明确建议
    print("\n🎯 基于最佳实践的建议:")
    if readiness_score >= 90:
        print("   🚀 立即行动: 开始种子用户测试")
    elif readiness_score >= 75:
        print("   🔧 并行行动: 修复关键问题 + 准备种子用户测试")
    else:
        print("   🔴 优先行动: 修复系统问题")


if __name__ == "__main__":
    asyncio.run(main())
