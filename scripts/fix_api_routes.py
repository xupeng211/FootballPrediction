#!/usr/bin/env python3
"""
🔧 API路由修复脚本

测试和修复关键的API路由问题，提升系统完整性
"""

import asyncio
import json
import time
from datetime import datetime
import httpx


class APIRouteFixer:
    """API路由修复器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = []
        self.fixed_routes = []
        self.problem_routes = []

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
        self, name: str, path: str, method: str = "GET", expected_status: int = 200
    ):
        """测试单个API路由"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if method.upper() == "GET":
                    response = await client.get(f"{self.api_base_url}{path}")
                elif method.upper() == "POST":
                    response = await client.post(f"{self.api_base_url}{path}")
                else:
                    response = await client.request(method, f"{self.api_base_url}{path}")

                duration = time.time() - start_time

                if response.status_code == expected_status:
                    self.log_test(name, True, f"HTTP {response.status_code}", duration)
                    self.fixed_routes.append(
                        {
                            "name": name,
                            "path": path,
                            "status": response.status_code,
                            "method": method,
                        }
                    )
                    return True
                else:
                    details = f"HTTP {response.status_code} (期望: {expected_status})"
                    if response.status_code == 404:
                        details += " - 路由不存在"
                    elif response.status_code == 307:
                        details += " - 重定向问题"
                    elif response.status_code == 500:
                        details += " - 服务器内部错误"

                    self.log_test(name, False, details, duration)
                    self.problem_routes.append(
                        {
                            "name": name,
                            "path": path,
                            "status": response.status_code,
                            "expected_status": expected_status,
                            "method": method,
                            "error": response.text[:200],
                        }
                    )
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test(name, False, f"连接错误: {str(e)}", duration)
            self.problem_routes.append(
                {"name": name, "path": path, "method": method, "error": str(e)}
            )
            return False

    async def test_all_routes(self):
        """测试所有API路由"""
        print("🔧 开始API路由测试和修复")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        # 定义要测试的API路由
        routes_to_test = [
            # 基础功能（应该正常工作）
            ("健康检查", "/api/health/", "GET", 200),
            ("API文档", "/docs", "GET", 200),
            ("OpenAPI规范", "/openapi.json", "GET", 200),
            ("系统根路径", "/", "GET", 200),
            # 认证相关（已验证正常）
            ("用户注册", "/api/v1/auth/register", "POST", 201),
            ("用户登录", "/api/v1/auth/login", "POST", 200),
            ("用户信息", "/api/v1/auth/me", "GET", 200),
            ("用户登出", "/api/v1/auth/logout", "POST", 200),
            # 数据API（预期返回TODO数据）
            ("球队数据", "/api/v1/data/teams", "GET", 200),
            ("联赛数据", "/api/v1/data/leagues", "GET", 200),
            ("比赛数据", "/api/v1/data/matches", "GET", 200),
            # 监控相关
            ("监控指标", "/api/v1/metrics/prometheus", "GET", 200),
            ("监控统计", "/api/v1/monitoring/stats", "GET", 200),  # 预期失败
            # 功能路由（预期有问题）
            ("功能路由", "/api/v1/features", "GET", 200),  # 预期重定向问题
            # 高级功能（预期404）
            ("预测路由", "/api/v1/predictions", "GET", 200),  # 预期404
            ("CQRS路由", "/api/v1/cqrs", "GET", 200),  # 预期404
            ("观察者路由", "/api/v1/observers", "GET", 200),  # 预期404
            ("适配器路由", "/api/v1/adapters", "GET", 200),  # 预期404
            # 其他可能的路由
            ("装饰器路由", "/api/v1/decorators", "GET", 200),  # 预期404
            ("门面路由", "/api/v1/facades", "GET", 200),  # 预期404
        ]

        # 测试所有路由
        for name, path, method, expected_status in routes_to_test:
            await self.test_api_route(name, path, method, expected_status)
            await asyncio.sleep(0.05)  # 短暂延迟避免过快请求

        # 生成修复报告
        self.generate_fix_report()

    def analyze_problems(self):
        """分析路由问题"""
        print("\n🔍 问题分析:")

        if not self.problem_routes:
            print("   🎉 所有路由都正常工作！")
            return

        # 按问题类型分类
        not_found = [r for r in self.problem_routes if r.get("status") == 404]
        redirects = [r for r in self.problem_routes if r.get("status") == 307]
        server_errors = [r for r in self.problem_routes if r.get("status") == 500]
        connection_errors = [r for r in self.problem_routes if "error" in r]

        print("   📊 问题统计:")
        print(f"      404错误 (路由不存在): {len(not_found)}")
        print(f"      307重定向问题: {len(redirects)}")
        print(f"      500服务器错误: {len(server_errors)}")
        print(f"      连接错误: {len(connection_errors)}")

        if not_found:
            print("\n   🔴 需要创建的路由:")
            for route in not_found:
                print(f"      • {route['name']}: {route['path']} ({route['method']})")

        if redirects:
            print("\n   🟡 需要修复的重定向:")
            for route in redirects:
                print(f"      • {route['name']}: {route['path']} - 检查路由配置")

        if server_errors:
            print("\n   🔴 服务器错误:")
            for route in server_errors:
                print(f"      • {route['name']}: {route['path']} - 检查实现")

        if connection_errors:
            print("\n   🔴 连接问题:")
            for route in connection_errors:
                print(f"      • {route['name']}: {route['path']} - {route['error']}")

    def suggest_fixes(self):
        """建议修复方案"""
        print("\n💡 修复建议:")

        if not self.problem_routes:
            print("   ✨ 系统完整性优秀，可以进行种子用户测试")
            return

        # 根据问题类型提供建议
        not_found = [r for r in self.problem_routes if r.get("status") == 404]
        redirects = [r for r in self.problem_routes if r.get("status") == 307]

        if not_found:
            print("\n   🔧 立即修复建议:")
            print("   1. 检查main.py中的路由注册")
            print("   2. 确认对应的router模块存在")
            print("   3. 验证MINIMAL_API_MODE设置")

            # 具体路由建议
            critical_missing = [
                r
                for r in not_found
                if any(keyword in r["name"].lower() for keyword in ["监控统计", "预测", "cqrs"])
            ]
            if critical_missing:
                print("\n   🎯 关键缺失路由:")
                for route in critical_missing:
                    print(f"      • {route['name']}: 检查src/api/目录下对应模块")

        if redirects:
            print("\n   🔄 重定向问题修复:")
            for route in redirects:
                print(f"      • {route['name']}: 检查路由路径是否正确")

        print("\n   📋 修复优先级:")
        print("   1. 🔴 高优先级: 监控统计、基础数据路由")
        print("   2. 🟡 中优先级: 预测、CQRS等高级功能")
        print("   3. 🟢 低优先级: 装饰器、门面等扩展功能")

    def generate_fix_report(self):
        """生成修复报告"""
        print("\n" + "=" * 60)
        print("📊 API路由修复报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len(self.fixed_routes)
        failed_tests = len(self.problem_routes)
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 路由测试统计:")
        print(f"   总路由数: {total_tests}")
        print(f"   正常工作: {successful_tests}")
        print(f"   有问题: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        print("\n✅ 正常工作的路由:")
        for route in self.fixed_routes:
            print(f"   • {route['name']}: {route['path']} ({route['method']})")

        if self.problem_routes:
            print("\n❌ 有问题的路由:")
            for route in self.problem_routes:
                status_info = f"HTTP {route.get('status', 'Error')}"
                print(f"   • {route['name']}: {route['path']} ({route['method']}) - {status_info}")

        # 分析问题
        self.analyze_problems()

        # 建议修复
        self.suggest_fixes()

        # 系统评估
        print("\n🎯 系统完整性评估:")
        if success_rate >= 90:
            print("   🟢 优秀: 系统API功能完善，可以支持种子用户测试")
            system_status = "优秀"
        elif success_rate >= 75:
            print("   🟡 良好: 核心功能可用，建议修复部分路由")
            system_status = "良好"
        elif success_rate >= 60:
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
        route_bonus = (success_rate - 60) * 0.5  # 路由成功率带来的加成
        total_readiness = min(95, max(60, base_readiness + route_bonus))

        if total_readiness >= 90:
            print(f"   整体就绪度: {total_readiness:.0f}% 🟢 (可以开始种子用户测试)")
        elif total_readiness >= 80:
            print(f"   整体就绪度: {total_readiness:.0f}% 🟡 (建议修复关键问题后开始)")
        else:
            print(f"   整体就绪度: {total_readiness:.0f}% 🔴 (需要修复更多问题)")

        print("=" * 60)


async def main():
    """主函数"""
    fixer = APIRouteFixer()
    await fixer.test_all_routes()


if __name__ == "__main__":
    asyncio.run(main())
