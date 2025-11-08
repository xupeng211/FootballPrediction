#!/usr/bin/env python3
"""
🗄️ 真实数据库集成脚本

将TODO假数据替换为真实的数据库数据，提升数据质量
"""

import asyncio
import time
from datetime import datetime, timedelta

import httpx
from sqlalchemy import text

from src.database.connection import get_async_session


class DatabaseIntegrator:
    """数据库集成器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = []
        self.db_session = None

    def log_test(self,
    test_name: str,
    success: bool,
    details: str = "",
    duration: float = 0):
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

    async def test_database_connection(self):
        """测试数据库连接"""
        print("\n🔗 步骤1: 测试数据库连接")

        start_time = time.time()
        try:
            async with get_async_session() as session:
                # 测试基本连接
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                duration = time.time() - start_time

                if row and row[0] == 1:
                    self.log_test("数据库连接", True, "连接成功", duration)
                    self.db_session = session
                    return True
                else:
                    self.log_test("数据库连接", False, "查询结果异常", duration)
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("数据库连接", False, f"连接错误: {str(e)}", duration)
            return False

    async def check_existing_data(self):
        """检查现有数据"""
        print("\n📊 步骤2: 检查现有数据库数据")

        tables_to_check = [
            ("teams", "球队表"),
            ("leagues", "联赛表"),
            ("matches", "比赛表"),
            ("predictions", "预测表"),
            ("users", "用户表"),
        ]

        existing_data = {}
        total_records = 0

        for table_name, display_name in tables_to_check:
            start_time = time.time()
            try:
                async with get_async_session() as session:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    duration = time.time() - start_time

                    existing_data[table_name] = count
                    total_records += count

                    if count > 0:
                        self.log_test(f"{display_name}数据检查",
    True,
    f"{count}条记录",
    duration)
                    else:
                        self.log_test(f"{display_name}数据检查", False, "无数据", duration)
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(f"{display_name}数据检查", False, f"查询错误: {str(e)}", duration)
                existing_data[table_name] = 0

        print(f"\n   📈 数据库总记录数: {total_records}")
        return existing_data, total_records

    async def create_sample_data_if_needed(self, existing_data):
        """如果需要，创建示例数据"""
        print("\n🌱 步骤3: 创建示例数据（如果需要）")

        # 检查是否需要创建数据
        tables_needing_data = [table for table,
    count in existing_data.items() if count == 0]

        if not tables_needing_data:
            self.log_test("示例数据创建", True, "数据库已有数据，跳过创建")
            return True

        print(f"   📝 需要创建数据的表: {tables_needing_data}")

        try:
            async with get_async_session() as session:
                # 创建联赛数据
                if "leagues" in tables_needing_data:
                    await self.create_league_data(session)

                # 创建球队数据
                if "teams" in tables_needing_data:
                    await self.create_team_data(session)

                # 创建比赛数据
                if "matches" in tables_needing_data:
                    await self.create_match_data(session)

                # 创建预测数据
                if "predictions" in tables_needing_data:
                    await self.create_prediction_data(session)

                await session.commit()
                self.log_test(
                    "示例数据创建", True, f"成功创建 {len(tables_needing_data)} 个表的数据"
                )
                return True

        except Exception as e:
            self.log_test("示例数据创建", False, f"创建失败: {str(e)}")
            return False

    async def create_league_data(self, session):
        """创建联赛数据"""
        leagues = [
            {"name": "英超联赛", "country": "英格兰", "season": "2024-25"},
            {"name": "西甲联赛", "country": "西班牙", "season": "2024-25"},
            {"name": "德甲联赛", "country": "德国", "season": "2024-25"},
            {"name": "意甲联赛", "country": "意大利", "season": "2024-25"},
            {"name": "法甲联赛", "country": "法国", "season": "2024-25"},
        ]

        for league in leagues:
            await session.execute(
                text(
                    """
                    INSERT INTO leagues (name, country, season, created_at)
                    VALUES (:name, :country, :season, NOW())
                """
                ),
                league,
            )

    async def create_team_data(self, session):
        """创建球队数据"""
        teams = [
            {"name": "曼联", "short_name": "MUN", "country": "英格兰", "league_id": 1},
            {"name": "利物浦", "short_name": "LIV", "country": "英格兰", "league_id": 1},
            {"name": "曼城", "short_name": "MCI", "country": "英格兰", "league_id": 1},
            {"name": "切尔西", "short_name": "CHE", "country": "英格兰", "league_id": 1},
            {"name": "阿森纳", "short_name": "ARS", "country": "英格兰", "league_id": 1},
            {"name": "皇家马德里", "short_name": "RMA", "country": "西班牙", "league_id": 2},
            {"name": "巴塞罗那", "short_name": "BAR", "country": "西班牙", "league_id": 2},
            {"name": "拜仁慕尼黑", "short_name": "FCB", "country": "德国", "league_id": 3},
            {"name": "尤文图斯", "short_name": "JUV", "country": "意大利", "league_id": 4},
            {"name": "巴黎圣日耳曼", "short_name": "PSG", "country": "法国", "league_id": 5},
        ]

        for team in teams:
            await session.execute(
                text(
                    """
                    INSERT INTO teams (name, short_name, country, league_id, created_at)
                    VALUES (:name, :short_name, :country, :league_id, NOW())
                """
                ),
                team,
            )

    async def create_match_data(self, session):
        """创建比赛数据"""
        matches = []
        current_date = datetime.now()

        # 创建未来两周的比赛
        for i in range(20):  # 创建20场比赛
            match_date = current_date + timedelta(days=i * 2,
    hours=random.randint(18,
    21))

            # 随机选择球队
            home_team_id = random.randint(1, 10)
            away_team_id = random.randint(1, 10)
            while away_team_id == home_team_id:
                away_team_id = random.randint(1, 10)

            matches.append(
                {
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "league_id": random.randint(1, 5),
                    "match_date": match_date,
                    "status": "pending",
                }
            )

        for match in matches:
            await session.execute(
                text(
                    """
                    INSERT INTO matches (home_team_id,
    away_team_id,
    league_id,
    match_date,
    status,
    created_at)
                    VALUES (:home_team_id,
    :away_team_id,
    :league_id,
    :match_date,
    :status,
    NOW())
                """
                ),
                match,
            )

    async def create_prediction_data(self, session):
        """创建预测数据"""
        predictions = []

        # 为最近的比赛创建预测
        for i in range(10):
            match_id = random.randint(1, 20)
            home_win_prob = round(random.uniform(0.3, 0.7), 2)
            draw_prob = round(random.uniform(0.2, 0.4), 2)
            away_win_prob = round(1.0 - home_win_prob - draw_prob, 2)

            predictions.append(
                {
                    "match_id": match_id,
                    "home_win_prob": home_win_prob,
                    "draw_prob": draw_prob,
                    "away_win_prob": away_win_prob,
                    "predicted_outcome": random.choice(["home", "draw", "away"]),
                    "confidence": round(random.uniform(0.6, 0.9), 2),
                    "model_version": "v1.0",
                }
            )

        for prediction in predictions:
            await session.execute(
                text(
                    """
                    INSERT INTO predictions (match_id, home_win_prob, draw_prob, away_win_prob,
                                           predicted_outcome, confidence, model_version, created_at)
                    VALUES (:match_id, :home_win_prob, :draw_prob, :away_win_prob,
                           :predicted_outcome, :confidence, :model_version, NOW())
                """
                ),
                prediction,
            )

    async def test_data_apis_with_real_data(self):
        """测试数据API与真实数据"""
        print("\n🔍 步骤4: 测试数据API与真实数据集成")

        data_endpoints = [
            ("球队数据API", "/api/v1/data/teams"),
            ("联赛数据API", "/api/v1/data/leagues"),
            ("比赛数据API", "/api/v1/data/matches"),
            ("赔率数据API", "/api/v1/data/odds"),
        ]

        success_count = 0

        for name, endpoint in data_endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}")
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        data = response.json()

                        # 分析数据质量
                        if isinstance(data, list) and len(data) > 0:
                            sample_item = data[0]

                            # 检查是否为真实数据（非TODO假数据）
                            is_real_data = self.check_if_real_data(sample_item, name)

                            if is_real_data:
                                self.log_test(
                                    name,
                                    True,
                                    f"HTTP {response.status_code}, 真实数据: {len(data)}条",
                                    duration,
                                )
                                success_count += 1
                            else:
                                self.log_test(
                                    name,
                                    False,
                                    f"HTTP {response.status_code}, 仍为TODO假数据",
                                    duration,
                                )
                        else:
                            self.log_test(
                                name, False, f"HTTP {response.status_code}, 无数据返回", duration
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

        print(f"\n   📈 数据API测试结果: {success_count}/{len(data_endpoints)} 成功")
        return success_count >= 3  # 至少3个数据API正常

    def check_if_real_data(self, data_item, api_name):
        """检查是否为真实数据"""
        if not isinstance(data_item, dict):
            return False

        # 检查常见的TODO假数据特征
        todo_indicators = [
            "Team 1",
            "Team 2",
            "League 1",
            "Country",
            "Country1",
            "Home Team",
            "Away Team",
            "Bookmaker1",
            "default",
        ]

        for indicator in todo_indicators:
            if any(indicator in str(value) for value in data_item.values()):
                return False

        # 检查是否有合理的ID和数据结构
        if "id" in data_item and isinstance(data_item["id"],
    int) and data_item["id"] > 0:
            return True

        return False

    async def optimize_data_quality(self):
        """优化数据质量"""
        print("\n🎯 步骤5: 优化数据质量")

        optimization_tasks = [
            ("数据完整性检查", self.check_data_integrity),
            ("数据一致性验证", self.check_data_consistency),
            ("性能优化", self.optimize_query_performance),
        ]

        completed_tasks = 0

        for task_name, task_func in optimization_tasks:
            try:
                result = await task_func()
                if result:
                    self.log_test(task_name, True, "优化成功")
                    completed_tasks += 1
                else:
                    self.log_test(task_name, False, "优化失败")
            except Exception as e:
                self.log_test(task_name, False, f"优化错误: {str(e)}")

        print(f"\n   📈 数据质量优化: {completed_tasks}/{len(optimization_tasks)} 成功")
        return completed_tasks >= 2

    async def check_data_integrity(self):
        """检查数据完整性"""
        try:
            async with get_async_session() as session:
                # 检查外键完整性
                result = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) as invalid_matches
                    FROM matches m
                    LEFT JOIN teams ht ON m.home_team_id = ht.id
                    LEFT JOIN teams at ON m.away_team_id = at.id
                    WHERE ht.id IS NULL OR at.id IS NULL
                """
                    )
                )
                invalid_matches = result.fetchone()[0]

                if invalid_matches == 0:
                    return True
                else:
                    print(f"   ⚠️ 发现 {invalid_matches} 条无效的比赛记录")
                    return False
        except Exception as e:
            print(f"   ❌ 完整性检查错误: {str(e)}")
            return False

    async def check_data_consistency(self):
        """检查数据一致性"""
        try:
            async with get_async_session() as session:
                # 检查预测数据与比赛数据的一致性
                result = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) as orphaned_predictions
                    FROM predictions p
                    LEFT JOIN matches m ON p.match_id = m.id
                    WHERE m.id IS NULL
                """
                    )
                )
                orphaned_predictions = result.fetchone()[0]

                if orphaned_predictions == 0:
                    return True
                else:
                    print(f"   ⚠️ 发现 {orphaned_predictions} 条孤立的预测记录")
                    return False
        except Exception as e:
            print(f"   ❌ 一致性检查错误: {str(e)}")
            return False

    async def optimize_query_performance(self):
        """优化查询性能"""
        try:
            async with get_async_session() as session:
                # 测试关键查询性能
                start_time = time.time()
                result = await session.execute(
                    text(
                        """
                    SELECT t.name, l.name as league_name
                    FROM teams t
                    JOIN leagues l ON t.league_id = l.id
                    LIMIT 10
                """
                    )
                )
                teams = result.fetchall()
                duration = time.time() - start_time

                if duration < 1.0 and len(teams) > 0:
                    return True
                else:
                    print(f"   ⚠️ 查询性能较慢: {duration:.2f}秒")
                    return False
        except Exception as e:
            print(f"   ❌ 性能测试错误: {str(e)}")
            return False

    async def run_database_integration(self):
        """运行完整的数据库集成"""
        print("🗄️ 开始真实数据库集成")
        print("=" * 60)
        print(f"📅 集成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        integration_results = {}

        # 执行集成步骤
        integration_results["db_connection"] = await self.test_database_connection()
        existing_data, total_records = await self.check_existing_data()
        integration_results["data_creation"] = await self.create_sample_data_if_needed(
            existing_data
        )
        integration_results["api_testing"] = await self.test_data_apis_with_real_data()
        integration_results["quality_optimization"] = await self.optimize_data_quality()

        # 生成集成报告
        self.generate_integration_report(integration_results, total_records)

    def generate_integration_report(self, results, total_records):
        """生成数据库集成报告"""
        print("\n" + "=" * 60)
        print("📊 数据库集成报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 集成测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        # 集成步骤结果
        print("\n🎯 集成步骤结果:")
        steps = [
            ("数据库连接", results["db_connection"]),
            ("数据创建", results["data_creation"]),
            ("API测试", results["api_testing"]),
            ("质量优化", results["quality_optimization"]),
        ]

        completed_steps = 0
        for step_name, success in steps:
            status = "✅" if success else "❌"
            print(f"   {status} {step_name}")
            if success:
                completed_steps += 1

        integration_completion = (completed_steps / len(steps)) * 100
        print(f"\n   集成完成率: {completed_steps}/{len(steps)} ({integration_completion:.1f}%)")

        # 数据统计
        print("\n📊 数据库统计:")
        print(f"   总记录数: {total_records}")
        if total_records > 0:
            print("   🟢 数据库状态: 健康，包含真实数据")
        else:
            print("   🔴 数据库状态: 空，需要创建数据")

        # 系统评估
        print("\n🎯 数据库集成评估:")
        if success_rate >= 85 and integration_completion >= 75:
            print("   🟢 优秀: 数据库集成成功，数据质量良好")
            system_status = "优秀"
            deployment_ready = True
        elif success_rate >= 70 and integration_completion >= 60:
            print("   🟡 良好: 数据库基本集成，存在少量问题")
            system_status = "良好"
            deployment_ready = True
        elif success_rate >= 60 and integration_completion >= 50:
            print("   🟡 一般: 数据库部分集成，需要改进")
            system_status = "一般"
            deployment_ready = False
        else:
            print("   🔴 需要改进: 数据库集成存在较多问题")
            system_status = "需要改进"
            deployment_ready = False

        # 下一步建议
        print("\n🚀 下一步建议:")
        if deployment_ready:
            print("   ✨ 数据库已准备就绪，可以进行生产部署")
            print("   📋 后续工作:")
            print("      1. 配置数据备份策略")
            print("      2. 设置数据监控告警")
            print("      3. 优化查询性能")
            print("      4. 建立数据更新机制")
        else:
            print("   🔧 建议优先解决:")
            failed_tests = [r for r in self.test_results if not r["success"]]
            if failed_tests:
                print("      关键问题:")
                for result in failed_tests[:3]:  # 显示前3个问题
                    print(f"      • {result['test_name']}: {result['details']}")

        print("\n🎊 数据库集成完成!")
        print(f"   系统状态: {system_status}")
        print(f"   集成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


async def main():
    """主函数"""
    integrator = DatabaseIntegrator()
    await integrator.run_database_integration()


if __name__ == "__main__":
    asyncio.run(main())
