#!/usr/bin/env python3
"""
🔧 修正的API路由测试脚本

基于OpenAPI规范进行准确的API路由测试
"""

import asyncio
import json
import time
from datetime import datetime
import httpx


class CorrectedRouteTester:
    """修正的API路由测试器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: str = "", duration: float = 0):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   📝 {details}")
        if duration > 0:
            print(f"   ⏱️  耗时: {duration:.2f}秒")

    async def test_api_route(
        self,
        name: str,
        path: str,
        method: str = "GET",
        expected_status: int = 200,
        data: dict = None,
    ):
        """测试单个API路由"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if method.upper() == "GET":
                    response = await client.get(f"{self.api_base_url}{path}")
                elif method.upper() == "POST":
                    if data:
                        response = await client.post(f"{self.api_base_url}{path}", json=data)
                    else:
                        response = await client.post(f"{self.api_base_url}{path}")
                elif method.upper() == "PUT":
                    response = await client.put(f"{self.api_base_url}{path}")
                else:
                    response = await client.request(method, f"{self.api_base_url}{path}")

                duration = time.time() - start_time

                if response.status_code == expected_status:
                    self.log_test(name, True, f"HTTP {response.status_code}", duration)
                    return True
                else:
                    details = f"HTTP {response.status_code} (期望: {expected_status})"
                    if response.status_code == 404:
                        details += " - 路由不存在"
                    elif response.status_code == 422:
                        details += " - 请求参数错误"
                    elif response.status_code == 401:
                        details += " - 需要认证"

                    # 尝试解析错误信息
                    try:
                        error_info = response.json()
                        if isinstance(error_info, dict) and "detail" in error_info:
                            details += f" - {error_info['detail']}"
except Exception:
                        pass

                    self.log_test(name, False, details, duration)
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test(name, False, f"连接错误: {str(e)}", duration)
            return False

    async def test_all_corrected_routes(self):
        """测试所有修正后的API路由"""
        print("🔧 开始修正的API路由测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        # 基于OpenAPI规范定义的正确路由
        routes_to_test = [
            # 基础功能
            ("健康检查", "/api/health/", "GET", 200),
            ("API文档", "/docs", "GET", 200),
            ("系统根路径", "/", "GET", 200),
            # 认证相关
            (
                "用户注册",
                "/api/v1/auth/register",
                "POST",
                201,
                {"username": "testuser", "email": "test@example.com", "password": "testpass123"},
            ),
            ("用户登出", "/api/v1/auth/logout", "POST", 200),
            # 数据API（应该返回TODO数据）
            ("球队数据", "/api/v1/data/teams", "GET", 200),
            ("联赛数据", "/api/v1/data/leagues", "GET", 200),
            ("比赛数据", "/api/v1/data/matches", "GET", 200),
            ("赔率数据", "/api/v1/data/odds", "GET", 200),
            # 监控相关
            ("监控指标", "/api/v1/metrics", "GET", 200),
            ("服务状态", "/api/v1/status", "GET", 200),
            ("Prometheus指标", "/api/v1/metrics/prometheus", "GET", 200),
            # 功能路由
            ("功能信息", "/api/v1/features/", "GET", 200),
            ("功能健康检查", "/api/v1/features/health", "GET", 200),
            # 预测相关
            ("预测健康检查", "/api/v1/predictions/health", "GET", 200),
            ("最近预测", "/api/v1/predictions/recent", "GET", 200),
            # 事件系统
            ("事件健康检查", "/api/v1/events/health", "GET", 200),
            ("事件统计", "/api/v1/events/stats", "GET", 200),
            ("事件类型", "/api/v1/events/types", "GET", 200),
            # 观察者系统
            ("观察者状态", "/api/v1/observers/status", "GET", 200),
            ("观察者指标", "/api/v1/observers/metrics", "GET", 200),
            # CQRS系统
            ("CQRS系统状态", "/api/v1/cqrs/system/status", "GET", 200),
            # 仓储模式
            ("仓储预测列表", "/api/v1/repositories/predictions", "GET", 200),
            ("仓储用户列表", "/api/v1/repositories/users", "GET", 200),
            ("仓储比赛列表", "/api/v1/repositories/matches", "GET", 200),
            # 装饰器模式
            ("装饰器统计", "/api/v1/decorators/stats", "GET", 200),
        ]

        # 测试所有路由
        for route_data in routes_to_test:
            if len(route_data) == 4:
                name, path, method, expected_status = route_data
                await self.test_api_route(name, path, method, expected_status)
            else:
                name, path, method, expected_status, data = route_data
                await self.test_api_route(name, path, method, expected_status, data)

            await asyncio.sleep(0.05)  # 短暂延迟避免过快请求

        # 生成测试报告
        self.generate_corrected_report()

    def generate_corrected_report(self):
        """生成修正后的测试报告"""
        print("\n" + "=" * 60)
        print("📊 修正的API路由测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 路由测试统计:")
        print(f"   总路由数: {total_tests}")
        print(f"   正常工作: {successful_tests}")
        print(f"   有问题: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        print("\n✅ 正常工作的路由:")
        for result in self.test_results:
            if result["success"]:
                print(f"   • {result['test_name']}")

        if failed_tests > 0:
            print("\n❌ 有问题的路由:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['details']}")

        # 按功能分类统计
        categories = {
            "基础功能": ["健康检查", "API文档", "系统根路径"],
            "认证系统": ["用户注册", "用户登出"],
            "数据API": ["球队数据", "联赛数据", "比赛数据", "赔率数据"],
            "监控系统": ["监控指标", "服务状态", "Prometheus指标"],
            "功能路由": ["功能信息", "功能健康检查"],
            "预测系统": ["预测健康检查", "最近预测"],
            "事件系统": ["事件健康检查", "事件统计", "事件类型"],
            "观察者系统": ["观察者状态", "观察者指标"],
            "CQRS系统": ["CQRS系统状态"],
            "仓储模式": ["仓储预测列表", "仓储用户列表", "仓储比赛列表"],
            "装饰器模式": ["装饰器统计"],
        }

        print("\n📊 功能模块成功率:")
        for category, features in categories.items():
            category_tests = [r for r in self.test_results if r["test_name"] in features]
            if category_tests:
                category_success = len([r for r in category_tests if r["success"]])
                category_total = len(category_tests)
                category_rate = (
                    (category_success / category_total * 100) if category_total > 0 else 0
                )
                status = "🟢" if category_rate == 100 else "🟡" if category_rate >= 50 else "🔴"
                print(
                    f"   {status} {category}: {category_success}/{category_total} ({category_rate:.0f}%)"
                )

        # 系统评估
        print("\n🎯 系统完整性评估:")
        if success_rate >= 90:
            print("   🟢 优秀: 系统API功能完善，可以支持种子用户测试")
            system_status = "优秀"
        elif success_rate >= 80:
            print("   🟡 良好: 核心功能可用，建议修复部分路由")
            system_status = "良好"
        elif success_rate >= 70:
            print("   🟡 一般: 基础功能可用，需要完善路由")
            system_status = "一般"
        else:
            print("   🔴 需要改进: 存在较多路由问题")
            system_status = "需要改进"

        # 更新种子用户测试就绪度
        print("\n🚀 种子用户测试就绪度:")
        print(f"   当前状态: {system_status}")

        # 基于成功率计算就绪度
        base_readiness = 85  # 认证系统完成后的基础就绪度
        route_bonus = (success_rate - 70) * 0.5  # 路由成功率带来的加成
        total_readiness = min(95, max(70, base_readiness + route_bonus))

        if total_readiness >= 90:
            print(f"   整体就绪度: {total_readiness:.0f}% 🟢 (可以开始种子用户测试)")
            recommendation = "立即开始种子用户测试"
        elif total_readiness >= 85:
            print(f"   整体就绪度: {total_readiness:.0f}% 🟡 (建议修复关键问题后开始)")
            recommendation = "修复关键问题后开始测试"
        else:
            print(f"   整体就绪度: {total_readiness:.0f}% 🔴 (需要修复更多问题)")
            recommendation = "继续修复系统问题"

        print(f"\n📋 建议: {recommendation}")

        # 核心功能检查
        core_functions = ["健康检查", "球队数据", "联赛数据", "比赛数据", "用户注册"]
        core_success = len(
            [r for r in self.test_results if r["success"] and r["test_name"] in core_functions]
        )
        core_total = len(core_functions)
        core_rate = (core_success / core_total * 100) if core_total > 0 else 0

        print("\n🎯 核心功能检查:")
        print(f"   核心功能成功率: {core_success}/{core_total} ({core_rate:.0f}%)")
        if core_rate == 100:
            print("   🟢 所有关键功能正常，可以支持种子用户测试")
        elif core_rate >= 80:
            print("   🟡 大部分关键功能正常，可以进行基础种子用户测试")
        else:
            print("   🔴 关键功能存在问题，需要优先修复")

        print("=" * 60)


async def main():
    """主函数"""
    tester = CorrectedRouteTester()
    await tester.test_all_corrected_routes()


if __name__ == "__main__":
    asyncio.run(main())
