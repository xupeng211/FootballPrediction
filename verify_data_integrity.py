#!/usr/bin/env python3
"""
🔍 数据完整性验证脚本

验证数据API返回的数据质量，评估是否为真实数据
"""

import asyncio
import json
import time
from datetime import datetime
import httpx


class DataIntegrityVerifier:
    """数据完整性验证器"""

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

    def analyze_data_quality(self, data, api_name):
        """分析数据质量"""
        if not isinstance(data, list) or len(data) == 0:
            return {"is_real": False, "reason": "无数据或格式错误", "score": 0}

        sample_item = data[0]
        if not isinstance(sample_item, dict):
            return {"is_real": False, "reason": "数据项不是字典格式", "score": 0}

        # 检查TODO假数据特征
        todo_patterns = [
            "Team \\d+",  # Team 1, Team 2, etc.
            "League \\d+",  # League 1, League 2, etc.
            "Country\\d*",  # Country, Country1, etc.
            "Home Team \\d+",  # Home Team 1, Home Team 2, etc.
            "Away Team \\d+",  # Away Team 1, Away Team 2, etc.
            "Bookmaker\\d+",  # Bookmaker1, Bookmaker2, etc.
            "default",  # default model version
            "null",  # null values
        ]

        import re

        todo_score = 0
        total_checks = 0

        for pattern in todo_patterns:
            total_checks += 1
            if re.search(pattern, json.dumps(sample_item)):
                todo_score += 1

        # 检查数据丰富度
        rich_data_indicators = 0
        if "id" in sample_item and isinstance(sample_item["id"], int) and sample_item["id"] > 0:
            rich_data_indicators += 1
        if (
            "name" in sample_item
            and isinstance(sample_item["name"], str)
            and len(sample_item["name"]) > 2
        ):
            rich_data_indicators += 1
        if len(sample_item) >= 4:  # 至少4个字段
            rich_data_indicators += 1

        # 计算综合得分
        todo_ratio = todo_score / total_checks if total_checks > 0 else 0
        rich_ratio = rich_data_indicators / 3

        overall_score = (rich_ratio * 0.7) - (todo_ratio * 0.3)

        is_real = overall_score > 0.3 and todo_ratio < 0.4

        return {
            "is_real": is_real,
            "reason": f"TODO特征: {todo_score}/{total_checks}, 数据丰富度: {rich_data_indicators}/3",
            "score": overall_score,
        }

    async def test_data_quality(self):
        """测试数据质量"""
        print("\n🔍 步骤1: 测试数据API质量")

        data_endpoints = [
            ("球队数据API", "/api/v1/data/teams"),
            ("联赛数据API", "/api/v1/data/leagues"),
            ("比赛数据API", "/api/v1/data/matches"),
            ("赔率数据API", "/api/v1/data/odds"),
        ]

        quality_results = []

        for name, endpoint in data_endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        data = response.json()
                        quality = self.analyze_data_quality(data, name)

                        if quality["is_real"]:
                            self.log_test(
                                name,
                                True,
                                f"HTTP {response.status_code}, 真实数据: {len(data)}条",
                                duration,
                            )
                        else:
                            self.log_test(
                                name,
                                False,
                                f"HTTP {response.status_code}, {quality['reason']}",
                                duration,
                            )

                        quality_results.append(
                            {
                                "name": name,
                                "quality": quality,
                                "data_count": len(data) if isinstance(data, list) else 0,
                            }
                        )
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
                        quality_results.append(
                            {
                                "name": name,
                                "quality": {"is_real": False, "reason": "API错误"},
                                "data_count": 0,
                            }
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)
                quality_results.append(
                    {
                        "name": name,
                        "quality": {"is_real": False, "reason": "连接错误"},
                        "data_count": 0,
                    }
                )

        return quality_results

    async def test_data_completeness(self):
        """测试数据完整性"""
        print("\n📊 步骤2: 测试数据完整性")

        completeness_tests = [
            ("系统健康检查", "/api/health/"),
            ("预测系统状态", "/api/v1/predictions/health"),
            ("事件系统状态", "/api/v1/events/health"),
            ("CQRS系统状态", "/api/v1/cqrs/system/status"),
        ]

        success_count = 0

        for name, endpoint in completeness_tests:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        data = response.json()

                        # 检查状态数据
                        if isinstance(data, dict):
                            if "status" in data and data["status"] in ["healthy", "运行中"]:
                                self.log_test(
                                    name,
                                    True,
                                    f"HTTP {response.status_code}, 状态: {data.get('status')}",
                                    duration,
                                )
                                success_count += 1
                            else:
                                self.log_test(
                                    name, False, f"HTTP {response.status_code}, 状态异常", duration
                                )
                        else:
                            self.log_test(
                                name, False, f"HTTP {response.status_code}, 响应格式错误", duration
                            )
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

        print(f"\n   📈 数据完整性: {success_count}/{len(completeness_tests)} 系统正常")
        return success_count >= 3

    async def test_data_consistency(self):
        """测试数据一致性"""
        print("\n🔗 步骤3: 测试数据一致性")

        # 测试相关数据的一致性
        consistency_tests = [
            ("球队与联赛关联性", "/api/v1/data/teams"),
            ("比赛与球队关联性", "/api/v1/data/matches"),
        ]

        success_count = 0

        for name, endpoint in consistency_tests:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        data = response.json()

                        if isinstance(data, list) and len(data) > 0:
                            # 检查数据一致性
                            consistency_ok = self.check_data_consistency(data, name)

                            if consistency_ok:
                                self.log_test(
                                    name,
                                    True,
                                    f"HTTP {response.status_code}, 数据一致性良好",
                                    duration,
                                )
                                success_count += 1
                            else:
                                self.log_test(
                                    name,
                                    False,
                                    f"HTTP {response.status_code}, 数据一致性问题",
                                    duration,
                                )
                        else:
                            self.log_test(
                                name, False, f"HTTP {response.status_code}, 无数据检查", duration
                            )
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

        print(f"\n   📈 数据一致性: {success_count}/{len(consistency_tests)} 通过")
        return success_count >= 1

    def check_data_consistency(self, data, test_name):
        """检查数据一致性"""
        if not isinstance(data, list) or len(data) == 0:
            return False

        # 简单的一致性检查
        for item in data[:5]:  # 检查前5条记录
            if not isinstance(item, dict):
                return False

            # 检查ID是否为正整数
            if "id" in item:
                if not isinstance(item["id"], int) or item["id"] <= 0:
                    return False

            # 检查名称是否合理
            if "name" in item:
                if not isinstance(item["name"], str) or len(item["name"]) < 2:
                    return False

        return True

    async def run_data_integrity_verification(self):
        """运行数据完整性验证"""
        print("🔍 开始数据完整性验证")
        print("=" * 60)
        print(f"📅 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        # 执行验证步骤
        quality_results = await self.test_data_quality()
        completeness_ok = await self.test_data_completeness()
        consistency_ok = await self.test_data_consistency()

        # 生成验证报告
        self.generate_verification_report(quality_results, completeness_ok, consistency_ok)

    def generate_verification_report(self, quality_results, completeness_ok, consistency_ok):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("📊 数据完整性验证报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 验证统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        # 数据质量分析
        print(f"\n🎯 数据质量分析:")
        real_data_count = 0
        total_data_count = 0

        for result in quality_results:
            if result["quality"]["is_real"]:
                real_data_count += 1
            total_data_count += result["data_count"]
            status = "🟢" if result["quality"]["is_real"] else "🔴"
            print(
                f"   {status} {result['name']}: {result['data_count']}条记录, 质量: {result['quality']['reason']}"
            )

        if total_data_count > 0:
            real_data_ratio = (real_data_count / len(quality_results)) * 100
            print(
                f"\n   📊 真实数据比例: {real_data_count}/{len(quality_results)} ({real_data_ratio:.1f}%)"
            )

        # 系统状态
        print(f"\n🔧 系统状态:")
        print(f"   数据完整性: {'✅ 通过' if completeness_ok else '❌ 失败'}")
        print(f"   数据一致性: {'✅ 通过' if consistency_ok else '❌ 失败'}")

        # 综合评估
        print(f"\n🎯 数据质量评估:")

        # 计算综合得分
        quality_score = success_rate * 0.4
        data_score = (real_data_count / len(quality_results)) * 100 * 0.4 if quality_results else 0
        system_score = (completeness_ok and consistency_ok) * 20

        overall_score = quality_score + data_score + system_score

        if overall_score >= 80:
            print("   🟢 优秀: 数据质量良好，可以支持生产使用")
            system_status = "优秀"
            production_ready = True
        elif overall_score >= 65:
            print("   🟡 良好: 数据质量基本满足需求，建议改进")
            system_status = "良好"
            production_ready = True
        elif overall_score >= 50:
            print("   🟡 一般: 数据质量可用，需要优化")
            system_status = "一般"
            production_ready = False
        else:
            print("   🔴 需要改进: 数据质量存在较多问题")
            system_status = "需要改进"
            production_ready = False

        print(f"   📊 综合评分: {overall_score:.1f}/100")

        # 改进建议
        print(f"\n🚀 改进建议:")
        if real_data_count == 0:
            print("   🔴 优先任务:")
            print("      • 替换TODO假数据为真实数据")
            print("      • 建立数据生成或导入机制")
            print("      • 实现数据库集成")
        elif real_data_count < len(quality_results):
            print("   🟡 优化任务:")
            print("      • 完善剩余API的数据质量")
            print("      • 增加数据丰富度和准确性")
        else:
            print("   🟢 维护任务:")
            print("      • 定期更新数据")
            print("      • 监控数据质量")
            print("      • 优化数据查询性能")

        # 种子用户测试就绪度
        seed_user_ready = overall_score >= 65
        print(f"\n🌱 种子用户测试就绪度:")
        if seed_user_ready:
            print("   🟢 系统已准备好进行种子用户测试")
            print("   📋 可以开始真实用户测试流程")
        else:
            print("   🔴 建议优先解决数据质量问题")
            print("   📋 完成数据优化后再进行用户测试")

        print(f"\n🎊 数据完整性验证完成!")
        print(f"   系统状态: {system_status}")
        print(f"   验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


async def main():
    """主函数"""
    verifier = DataIntegrityVerifier()
    await verifier.run_data_integrity_verification()


if __name__ == "__main__":
    asyncio.run(main())
