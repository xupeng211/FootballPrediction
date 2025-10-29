#!/usr/bin/env python3
"""
端到端验证脚本

完整验证足球预测平台的数据流：
采集数据 → 清洗 → 特征生成 → 模型预测 → API返回 → 结果存储
"""

import asyncio
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import track
from rich.table import Table

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 项目模块导入 (必须在sys.path修改后)
from src.cache.redis_manager import RedisManager  # noqa: E402
from src.database.connection import DatabaseManager  # noqa: E402
from src.monitoring.metrics_exporter import get_metrics_exporter  # noqa: E402


class EndToEndVerification:
    """端到端验证器"""

    def __init__(self):
        """初始化验证器"""
        self.console = Console()
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()
        self.metrics_exporter = get_metrics_exporter()
        self.base_url = "http://localhost:8000"

        # 验证结果
        self.verification_results = {
            "database_connection": False,
            "cache_connection": False,
            "api_health": False,
            "metrics_collection": False,
            "data_pipeline": False,
            "prediction_pipeline": False,
            "monitoring_stack": False,
        }

    async def verify_infrastructure(self) -> bool:
        """验证基础设施组件"""
        self.console.print("\n🔍 [bold blue]验证基础设施组件[/bold blue]")

        # 1. 数据库连接
        try:
            await self.db_manager.initialize()
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    self.verification_results["database_connection"] = True
                    self.console.print("✅ 数据库连接正常")
        except Exception as e:
            self.console.print(f"❌ 数据库连接失败: {e}")

        # 2. Redis连接
        try:
            await self.redis_manager.ping()
            test_key = "test_verification"
            await self.redis_manager.aset(test_key, "test_value", expire=10)
            value = await self.redis_manager.aget(test_key)
            if value == "test_value":
                self.verification_results["cache_connection"] = True
                self.console.print("✅ Redis缓存连接正常")
                await self.redis_manager.adelete(test_key)
        except Exception as e:
            self.console.print(f"❌ Redis连接失败: {e}")

        # 3. API健康检查
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get("status") == "healthy":
                        self.verification_results["api_health"] = True
                        self.console.print("✅ API服务健康")
        except Exception as e:
            self.console.print(f"❌ API健康检查失败: {e}")

        return all(
            [
                self.verification_results["database_connection"],
                self.verification_results["cache_connection"],
                self.verification_results["api_health"],
            ]
        )

    async def verify_monitoring_stack(self) -> bool:
        """验证监控技术栈"""
        self.console.print("\n📊 [bold blue]验证监控技术栈[/bold blue]")

        monitoring_services = [
            ("Prometheus", "http://localhost:9090/-/ready"),
            ("Grafana", "http://localhost:3000/api/health"),
            ("指标导出", f"{self.base_url}/metrics"),
        ]

        success_count = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for service_name, endpoint in monitoring_services:
                try:
                    response = await client.get(endpoint)
                    if response.status_code == 200:
                        self.console.print(f"✅ {service_name} 服务正常")
                        success_count += 1
                    else:
                        self.console.print(f"⚠️ {service_name} 响应异常: {response.status_code}")
                except Exception as e:
                    self.console.print(f"❌ {service_name} 连接失败: {e}")

        # 验证指标收集
        try:
            await self.metrics_exporter.collect_all_metrics()
            content_type, metrics_data = self.metrics_exporter.get_metrics()
            if "football_" in metrics_data:
                self.console.print("✅ 指标收集正常")
                self.verification_results["metrics_collection"] = True
                success_count += 1
        except Exception as e:
            self.console.print(f"❌ 指标收集失败: {e}")

        self.verification_results["monitoring_stack"] = success_count >= 2
        return self.verification_results["monitoring_stack"]

    async def verify_data_pipeline(self) -> bool:
        """验证数据处理流水线"""
        self.console.print("\n🔄 [bold blue]验证数据处理流水线[/bold blue]")

        try:
            # 1. 验证数据表存在
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import text

                tables_to_check = [
                    "teams",
                    "leagues",
                    "matches",
                    "odds",
                    "predictions",
                    "data_collection_logs",
                ]

                for table in tables_to_check:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        self.console.print(f"📊 {table} 表: {count} 条记录")
                    except Exception as e:
                        self.console.print(f"⚠️ {table} 表查询失败: {e}")

                # 2. 检查最近的数据采集日志
                recent_logs_query = text(
                    """
                    SELECT collection_type, status, created_at
                    FROM data_collection_logs
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 5
                """
                )

                result = await session.execute(recent_logs_query)
                logs = result.fetchall()

                if logs:
                    self.console.print("📈 最近数据采集记录:")
                    for log in logs:
                        status_emoji = "✅" if log[1] == "success" else "❌"
                        self.console.print(f"  {status_emoji} {log[0]}: {log[1]} ({log[2]})")
                    self.verification_results["data_pipeline"] = True
                else:
                    self.console.print("⚠️ 未找到最近24小时的数据采集记录")

        except Exception as e:
            self.console.print(f"❌ 数据管道验证失败: {e}")

        return self.verification_results["data_pipeline"]

    async def verify_prediction_pipeline(self) -> bool:
        """验证预测流水线"""
        self.console.print("\n🔮 [bold blue]验证预测流水线[/bold blue]")

        try:
            # 1. 获取可用的比赛数据
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import text

                # 查找即将进行的比赛
                upcoming_matches_query = text(
                    """
                    SELECT m.id, m.home_team_id, m.away_team_id,
                           ht.name as home_team, at.name as away_team, m.match_time
                    FROM matches m
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    WHERE m.match_time > NOW()
                    AND m.status = 'scheduled'
                    ORDER BY m.match_time ASC
                    LIMIT 5
                """
                )

                result = await session.execute(upcoming_matches_query)
                matches = result.fetchall()

                if not matches:
                    self.console.print("⚠️ 未找到即将进行的比赛，创建测试数据...")
                    return await self._test_prediction_with_mock_data()

                # 2. 测试预测API
                test_match = matches[0]
                match_id, home_team_id, away_team_id = (
                    test_match[0],
                    test_match[1],
                    test_match[2],
                )

                self.console.print(f"🏟️ 测试比赛: {test_match[3]} vs {test_match[4]}")

                async with httpx.AsyncClient(timeout=30.0) as client:
                    prediction_request = {
                        "match_id": match_id,
                        "home_team_id": home_team_id,
                        "away_team_id": away_team_id,
                    }

                    response = await client.post(
                        f"{self.base_url}/api/v1/predictions/predict",
                        json=prediction_request,
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code == 200:
                        prediction_result = response.json()

                        # 验证预测结果结构
                        required_fields = [
                            "prediction_id",
                            "match_id",
                            "probabilities",
                            "predicted_result",
                            "confidence",
                            "created_at",
                        ]

                        if all(field in prediction_result for field in required_fields):
                            self.console.print("✅ 预测API响应结构正确")

                            # 显示预测结果
                            probs = prediction_result["probabilities"]
                            self.console.print(
                                f"📊 预测结果: {prediction_result['predicted_result']}"
                            )
                            self.console.print(f"🎯 置信度: {prediction_result['confidence']:.2%}")
                            self.console.print(
                                f"📈 概率分布: 主胜 {probs.get('home_win', 0):.3f} | 平局 {probs.get('draw', 0):.3f} | 客胜 {probs.get('away_win', 0):.3f}"
                            )

                            self.verification_results["prediction_pipeline"] = True
                        else:
                            self.console.print(f"❌ 预测结果缺少必要字段: {required_fields}")
                    else:
                        self.console.print(f"❌ 预测API调用失败: {response.status_code}")
                        self.console.print(f"响应内容: {response.text}")

        except Exception as e:
            self.console.print(f"❌ 预测流水线验证失败: {e}")

        return self.verification_results["prediction_pipeline"]

    async def _test_prediction_with_mock_data(self) -> bool:
        """使用模拟数据测试预测"""
        try:
            # 创建临时测试数据
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import text

                # 插入测试球队（如果不存在）
                await session.execute(
                    text(
                        """
                    INSERT INTO teams (id, name, country, league_id, founded)
                    VALUES (99999, '测试主队', 'Test', 1, 2000),
                           (99998, '测试客队', 'Test', 1, 2000)
                    ON CONFLICT (id) DO NOTHING
                """
                    )
                )

                # 插入测试比赛
                await session.execute(
                    text(
                        """
                    INSERT INTO matches (id, home_team_id, away_team_id, league_id, season, match_time, status)
                    VALUES (999999, 99999, 99998, 1, '2024-25', NOW() + INTERVAL '1 day', 'scheduled')
                    ON CONFLICT (id) DO NOTHING
                """
                    )
                )

                await session.commit()

            # 测试预测API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/predictions/predict",
                    json={
                        "match_id": 999999,
                        "home_team_id": 99999,
                        "away_team_id": 99998,
                    },
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    prediction_result = response.json()
                    self.console.print("✅ 模拟数据预测测试成功")
                    self.console.print(
                        f"📊 预测结果: {prediction_result.get('predicted_result', 'N/A')}"
                    )
                    return True

            return False

        except Exception as e:
            self.console.print(f"❌ 模拟数据测试失败: {e}")
            return False

    async def verify_database_writes(self) -> bool:
        """验证数据库写入功能"""
        self.console.print("\n💾 [bold blue]验证数据库写入[/bold blue]")

        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import text

                # 检查最近的预测记录
                recent_predictions_query = text(
                    """
                    SELECT p.id, p.match_id, p.prediction_result, p.confidence, p.created_at,
                           m.status as match_status
                    FROM predictions p
                    JOIN matches m ON p.match_id = m.id
                    WHERE p.created_at >= NOW() - INTERVAL '1 hour'
                    ORDER BY p.created_at DESC
                    LIMIT 5
                """
                )

                result = await session.execute(recent_predictions_query)
                predictions = result.fetchall()

                if predictions:
                    self.console.print("📝 最近预测记录:")
                    for pred in predictions:
                        self.console.print(
                            f"  🔮 预测ID {pred[0]}: {pred[2]} "
                            f"(置信度: {pred[3]:.2%}, 时间: {pred[4]})"
                        )
                    return True
                else:
                    self.console.print("⚠️ 未找到最近1小时的预测记录")
                    return False

        except Exception as e:
            self.console.print(f"❌ 数据库写入验证失败: {e}")
            return False

    def generate_verification_report(self) -> None:
        """生成验证报告"""
        self.console.print("\n📋 [bold yellow]端到端验证报告[/bold yellow]")

        # 创建结果表格
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("验证项目", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("描述")

        verification_items = [
            (
                "数据库连接",
                self.verification_results["database_connection"],
                "PostgreSQL连接和基本查询",
            ),
            (
                "缓存连接",
                self.verification_results["cache_connection"],
                "Redis缓存读写操作",
            ),
            ("API健康", self.verification_results["api_health"], "REST API服务状态"),
            (
                "指标收集",
                self.verification_results["metrics_collection"],
                "Prometheus指标导出",
            ),
            (
                "数据流水线",
                self.verification_results["data_pipeline"],
                "数据采集和存储流程",
            ),
            (
                "预测流水线",
                self.verification_results["prediction_pipeline"],
                "模型预测和API调用",
            ),
            (
                "监控技术栈",
                self.verification_results["monitoring_stack"],
                "Grafana和Prometheus服务",
            ),
        ]

        passed_count = 0

        for item_name, status, description in verification_items:
            status_emoji = "✅ 通过" if status else "❌ 失败"
            table.add_row(item_name, status_emoji, description)
            if status:
                passed_count += 1

        self.console.print(table)

        # 总体状态
        total_items = len(verification_items)
        success_rate = (passed_count / total_items) * 100

        if success_rate >= 80:
            status_color = "green"
            status_text = "🎉 系统状态良好"
        elif success_rate >= 60:
            status_color = "yellow"
            status_text = "⚠️ 系统部分功能异常"
        else:
            status_color = "red"
            status_text = "❌ 系统存在严重问题"

        self.console.print(
            f"\n[{status_color}]总体验证结果: {passed_count}/{total_items} ({success_rate:.1f}%)[/{status_color}]"
        )
        self.console.print(f"[{status_color}]{status_text}[/{status_color}]")

        return passed_count, total_items

    async def run_verification(self) -> bool:
        """运行完整验证流程"""
        self.console.print("🚀 [bold green]开始足球预测平台端到端验证[/bold green]")

        # 按顺序执行验证步骤
        verification_steps = [
            ("基础设施验证", self.verify_infrastructure),
            ("监控技术栈验证", self.verify_monitoring_stack),
            ("数据流水线验证", self.verify_data_pipeline),
            ("预测流水线验证", self.verify_prediction_pipeline),
            ("数据库写入验证", self.verify_database_writes),
        ]

        for step_name, verification_func in track(
            verification_steps, description="执行验证步骤..."
        ):
            self.console.print(f"\n🔍 正在执行: {step_name}")
            try:
                await verification_func()
            except Exception as e:
                self.console.print(f"❌ {step_name}执行失败: {e}")

        # 生成最终报告
        passed, total = self.generate_verification_report()

        return passed >= (total * 0.8)  # 80%通过率为成功


async def main():
    """主函数"""
    verifier = EndToEndVerification()

    try:
        success = await verifier.run_verification()

        if success:
            verifier.console.print("\n🎯 [bold green]端到端验证成功完成！[/bold green]")
            verifier.console.print("系统已准备好投入生产使用。")
            sys.exit(0)
        else:
            verifier.console.print("\n⚠️ [bold red]端到端验证发现问题[/bold red]")
            verifier.console.print("请检查失败项目并修复后重新验证。")
            sys.exit(1)

    except KeyboardInterrupt:
        verifier.console.print("\n⏹️ 验证被用户中断")
        sys.exit(1)
    except Exception as e:
        verifier.console.print(f"\n💥 验证过程发生异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
