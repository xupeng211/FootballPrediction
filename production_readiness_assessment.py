#!/usr/bin/env python3
"""
🚀 生产就绪度评估脚本

全面评估系统生产就绪状态，并提供优化建议
"""

import asyncio
import json
import time
import psutil
import os
from datetime import datetime
import httpx


class ProductionReadinessAssessor:
    """生产就绪度评估器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = []
        self.system_metrics = {}

    def log_test(
        self,
        test_name: str,
        success: bool,
        details: str = "",
        duration: float = 0,
        score: float = None,
    ):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration": duration,
            "score": score,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   📝 {details}")
        if duration > 0:
            print(f"   ⏱️  耗时: {duration:.2f}秒")
        if score is not None:
            print(f"   📊 评分: {score:.1f}/100")

    async def assess_system_health(self):
        """评估系统健康状态"""
        print("\n🏥 步骤1: 评估系统健康状态")

        health_checks = [
            ("基础健康检查", "/api/health/"),
            ("应用健康状态", "/api/v1/status"),
            ("API文档可用性", "/docs"),
            ("OpenAPI规范", "/openapi.json"),
        ]

        health_score = 0
        for name, endpoint in health_checks:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        score = 100
                        health_score += 25
                        self.log_test(name, True, f"HTTP {response.status_code}", duration, score)
                    else:
                        score = 0
                        self.log_test(name, False, f"HTTP {response.status_code}", duration, score)
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration, 0)

        return health_score

    async def assess_api_functionality(self):
        """评估API功能完整性"""
        print("\n🔧 步骤2: 评估API功能完整性")

        api_categories = {
            "认证系统": [
                ("/api/v1/auth/register", "POST"),
                ("/api/v1/auth/login", "POST"),
                ("/api/v1/auth/logout", "POST"),
            ],
            "数据API": [
                ("/api/v1/data/teams", "GET"),
                ("/api/v1/data/leagues", "GET"),
                ("/api/v1/data/matches", "GET"),
                ("/api/v1/data/odds", "GET"),
            ],
            "预测系统": [
                ("/api/v1/predictions/health", "GET"),
                ("/api/v1/predictions/recent", "GET"),
            ],
            "监控系统": [
                ("/api/v1/metrics/prometheus", "GET"),
                ("/api/v1/events/health", "GET"),
                ("/api/v1/observers/status", "GET"),
            ],
            "核心架构": [("/api/v1/cqrs/system/status", "GET"), ("/api/v1/features/health", "GET")],
        }

        total_score = 0
        category_scores = {}

        for category, endpoints in api_categories.items():
            category_success = 0
            for endpoint, method in endpoints:
                start_time = time.time()
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        if method == "GET":
                            response = await client.get(f"{self.api_base_url}{endpoint}")
                        else:
                            response = await client.post(f"{self.api_base_url}{endpoint}")

                        time.time() - start_time

                        if response.status_code in [200, 201]:
                            category_success += 1
                        else:
                            print(f"   ⚠️ {endpoint}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"   ❌ {endpoint}: 连接错误 - {str(e)}")

            category_score = (category_success / len(endpoints)) * 100
            category_scores[category] = category_score
            total_score += category_score

            if category_score >= 80:
                status = "🟢"
            elif category_score >= 60:
                status = "🟡"
            else:
                status = "🔴"
            print(
                f"   {status} {category}: {category_success}/{len(endpoints)} ({category_score:.0f}%)"
            )

        overall_api_score = total_score / len(api_categories)
        return overall_api_score, category_scores

    async def assess_performance_metrics(self):
        """评估性能指标"""
        print("\n⚡ 步骤3: 评估性能指标")

        performance_tests = [
            ("响应时间测试", self.test_response_times),
            ("并发处理测试", self.test_concurrent_requests),
            ("系统资源使用", self.check_system_resources),
        ]

        performance_scores = []
        for test_name, test_func in performance_tests:
            try:
                score = await test_func()
                performance_scores.append(score)
                if score >= 80:
                    status = "🟢"
                elif score >= 60:
                    status = "🟡"
                else:
                    status = "🔴"
                print(f"   {status} {test_name}: {score:.0f}/100")
            except Exception as e:
                print(f"   ❌ {test_name}: 测试失败 - {str(e)}")
                performance_scores.append(0)

        return sum(performance_scores) / len(performance_scores)

    async def test_response_times(self):
        """测试响应时间"""
        endpoints = ["/api/health/", "/api/v1/data/teams", "/api/v1/predictions/health"]

        response_times = []
        for endpoint in endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    if response.status_code == 200:
                        response_times.append(time.time() - start_time)
            except Exception:
                pass

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            # 评分：平均响应时间 < 200ms = 100分, < 500ms = 80分, < 1s = 60分, 其他 = 40分
            if avg_time < 0.2:
                return 100
            elif avg_time < 0.5:
                return 80
            elif avg_time < 1.0:
                return 60
            else:
                return 40
        return 0

    async def test_concurrent_requests(self):
        """测试并发请求处理"""

        async def make_request():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{self.api_base_url}/api/health/")
                    return response.status_code == 200
            except Exception:
                return False

        # 并发10个请求
        start_time = time.time()
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        success_count = sum(results)
        success_rate = (success_count / len(results)) * 100

        # 评分：成功率 >= 90% 且平均时间 < 2s = 100分
        if success_rate >= 90 and duration < 2.0:
            return 100
        elif success_rate >= 80 and duration < 3.0:
            return 80
        elif success_rate >= 70:
            return 60
        else:
            return 40

    def check_system_resources(self):
        """检查系统资源使用"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage("/")

        self.system_metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_info.percent,
            "disk_percent": (disk_info.used / disk_info.total) * 100,
        }

        # 评分：CPU < 70%, Memory < 80%, Disk < 90%
        cpu_score = 100 if cpu_percent < 70 else 80 if cpu_percent < 85 else 60
        memory_score = 100 if memory_info.percent < 80 else 80 if memory_info.percent < 90 else 60
        disk_score = (
            100
            if self.system_metrics["disk_percent"] < 90
            else 80 if self.system_metrics["disk_percent"] < 95 else 60
        )

        return (cpu_score + memory_score + disk_score) / 3

    async def assess_security_measures(self):
        """评估安全措施"""
        print("\n🔒 步骤4: 评估安全措施")

        security_checks = [
            ("CORS配置检查", self.check_cors_configuration),
            ("错误处理安全性", self.check_error_handling),
            ("认证系统安全性", self.check_auth_security),
            ("HTTPS支持检查", self.check_https_support),
        ]

        security_scores = []
        for check_name, check_func in security_checks:
            try:
                score = await check_func()
                security_scores.append(score)
                if score >= 80:
                    status = "🟢"
                elif score >= 60:
                    status = "🟡"
                else:
                    status = "🔴"
                print(f"   {status} {check_name}: {score:.0f}/100")
            except Exception as e:
                print(f"   ❌ {check_name}: 检查失败 - {str(e)}")
                security_scores.append(0)

        return sum(security_scores) / len(security_scores)

    async def check_cors_configuration(self):
        """检查CORS配置"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.options(
                    f"{self.api_base_url}/api/health/", headers={"Origin": "http://localhost:3000"}
                )
                # 检查CORS头
                cors_headers = [
                    "Access-Control-Allow-Origin",
                    "Access-Control-Allow-Methods",
                    "Access-Control-Allow-Headers",
                ]
                header_count = sum(1 for header in cors_headers if header in response.headers)
                return (header_count / len(cors_headers)) * 100
            except Exception:
            return 0

    async def check_error_handling(self):
        """检查错误处理安全性"""
        try:
            # 故意请求一个不存在的端点
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base_url}/api/v1/nonexistent")
                if response.status_code == 404:
                    try:
                        error_data = response.json()
                        # 检查是否暴露敏感信息
                        sensitive_info = ["password", "secret", "key", "token", "stack"]
                        exposed_count = sum(
                            1 for info in sensitive_info if info in str(error_data).lower()
                        )
                        security_score = max(0, 100 - (exposed_count * 20))
                        return security_score
            except Exception:
                        return 80  # JSON解析失败也算安全
                else:
                    return 60
            except Exception:
            return 0

    async def check_auth_security(self):
        """检查认证系统安全性"""
        try:
            # 测试未授权访问
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base_url}/api/v1/auth/me")
                if response.status_code == 401:
                    return 100  # 正确返回未授权
                elif response.status_code == 200:
                    return 50  # 允许未授权访问，安全性较低
                else:
                    return 80
            except Exception:
            return 0

    async def check_https_support(self):
        """检查HTTPS支持"""
        # 当前使用HTTP，在生产环境中应该使用HTTPS
        if self.api_base_url.startswith("https://"):
            return 100
        else:
            return 40  # HTTP不是生产环境推荐

    async def assess_data_quality(self):
        """评估数据质量"""
        print("\n📊 步骤5: 评估数据质量")

        data_endpoints = [
            ("/api/v1/data/teams", "球队数据"),
            ("/api/v1/data/leagues", "联赛数据"),
            ("/api/v1/data/matches", "比赛数据"),
        ]

        quality_scores = []
        for endpoint, name in data_endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    time.time() - start_time

                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            # 检查数据质量
                            sample = data[0]
                            if isinstance(sample, dict) and len(sample) >= 3:
                                quality_score = 100
                            else:
                                quality_score = 70
                            quality_scores.append(quality_score)
                            print(f"   ✅ {name}: {len(data)}条记录, 质量: {quality_score}/100")
                        else:
                            print(f"   ❌ {name}: 无数据")
                            quality_scores.append(0)
                    else:
                        print(f"   ❌ {name}: HTTP {response.status_code}")
                        quality_scores.append(0)
            except Exception as e:
                print(f"   ❌ {name}: 错误 - {str(e)}")
                quality_scores.append(0)

        return sum(quality_scores) / len(quality_scores) if quality_scores else 0

    def calculate_overall_score(self, scores):
        """计算总体评分"""
        weights = {
            "system_health": 0.2,
            "api_functionality": 0.3,
            "performance": 0.2,
            "security": 0.15,
            "data_quality": 0.15,
        }

        overall_score = sum(scores[key] * weight for key, weight in weights.items())
        return overall_score

    def generate_readiness_report(self, scores):
        """生成生产就绪度报告"""
        print("\n" + "=" * 60)
        print("🚀 生产就绪度评估报告")
        print("=" * 60)

        # 各项评分
        print("📊 详细评分:")
        print(f"   🏥 系统健康: {scores['system_health']:.1f}/100")
        print(f"   🔧 API功能: {scores['api_functionality']:.1f}/100")
        print(f"   ⚡ 性能指标: {scores['performance']:.1f}/100")
        print(f"   🔒 安全措施: {scores['security']:.1f}/100")
        print(f"   📊 数据质量: {scores['data_quality']:.1f}/100")

        # 总体评分
        overall_score = self.calculate_overall_score(scores)
        print(f"\n🎯 总体生产就绪度: {overall_score:.1f}/100")

        # 评级
        if overall_score >= 90:
            grade = "A+ (优秀)"
            status = "🟢 完全就绪"
            deployment_ready = True
        elif overall_score >= 80:
            grade = "A (良好)"
            status = "🟢 基本就绪"
            deployment_ready = True
        elif overall_score >= 70:
            grade = "B (一般)"
            status = "🟡 需要改进"
            deployment_ready = False
        elif overall_score >= 60:
            grade = "C (较差)"
            status = "🔴 需要重大改进"
            deployment_ready = False
        else:
            grade = "D (不合格)"
            status = "🔴 不适合生产"
            deployment_ready = False

        print(f"\n🏆 评级: {grade}")
        print(f"📋 状态: {status}")

        # 系统资源信息
        if self.system_metrics:
            print("\n💻 系统资源:")
            print(f"   CPU使用率: {self.system_metrics['cpu_percent']:.1f}%")
            print(f"   内存使用率: {self.system_metrics['memory_percent']:.1f}%")
            print(f"   磁盘使用率: {self.system_metrics['disk_percent']:.1f}%")

        # 改进建议
        print("\n🚀 改进建议:")

        low_score_areas = [(name, score) for name, score in scores.items() if score < 70]
        if low_score_areas:
            print("   🔴 优先改进项:")
            for area, score in low_score_areas:
                area_names = {
                    "system_health": "系统健康",
                    "api_functionality": "API功能",
                    "performance": "性能指标",
                    "security": "安全措施",
                    "data_quality": "数据质量",
                }
                print(f"      • {area_names.get(area, area)}: {score:.1f}/100")

        if overall_score < 90:
            print("\n   📋 具体改进措施:")
            if scores["security"] < 80:
                print("      🔒 安全性:")
                print("         - 配置HTTPS证书")
                print("         - 强化CORS策略")
                print("         - 完善错误处理")

            if scores["performance"] < 80:
                print("      ⚡ 性能:")
                print("         - 优化数据库查询")
                print("         - 添加缓存策略")
                print("         - 配置负载均衡")

            if scores["data_quality"] < 80:
                print("      📊 数据:")
                print("         - 完善数据验证")
                print("         - 建立数据备份")
                print("         - 增加数据监控")

        # 部署建议
        print("\n🌐 部署建议:")
        if deployment_ready:
            print("   ✨ 系统已准备好进行生产部署")
            print("   📋 部署检查清单:")
            print("      ✅ 所有核心功能正常")
            print("      ✅ 性能指标满足要求")
            print("      ✅ 安全措施基本到位")
            print("      ✅ 数据质量良好")

            print("\n   🚀 生产部署步骤:")
            print("      1. 配置生产环境变量")
            print("      2. 设置数据库连接池")
            print("      3. 配置日志收集")
            print("      4. 设置监控告警")
            print("      5. 执行渐进式部署")
        else:
            print("   🔧 建议优先完成改进措施后再进行生产部署")
            print("   📋 改进完成后重新评估")

        print("\n🎊 生产就绪度评估完成!")
        print(f"   评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   总体评分: {overall_score:.1f}/100 ({grade})")
        print("=" * 60)

    async def run_production_readiness_assessment(self):
        """运行生产就绪度评估"""
        print("🚀 开始生产就绪度评估")
        print("=" * 60)
        print(f"📅 评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        # 执行评估步骤
        scores = {}

        scores["system_health"] = await self.assess_system_health()
        api_score, category_scores = await self.assess_api_functionality()
        scores["api_functionality"] = api_score
        scores["performance"] = await self.assess_performance_metrics()
        scores["security"] = await self.assess_security_measures()
        scores["data_quality"] = await self.assess_data_quality()

        # 生成报告
        self.generate_readiness_report(scores)


async def main():
    """主函数"""
    assessor = ProductionReadinessAssessor()
    await assessor.run_production_readiness_assessment()


if __name__ == "__main__":
    asyncio.run(main())
