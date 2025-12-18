#!/usr/bin/env python3
"""
Sprint 9 真实API连接验证脚本

验证生产环境API密钥配置和连接状态：
1. FotMob API连接测试
2. 数据库连接验证
3. Redis缓存连接测试
4. 外部数据源权限检查
5. 系统健康状态评估

使用方法:
  python verify_live_connection.py --all
  python verify_live_connection.py --api fotmob
  python verify_live_connection.py --quick

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - Production Deployment)
"""

import asyncio
import aiohttp
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import psycopg2
import redis
from dataclasses import dataclass, asdict

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings
from database.db_pool import DatabasePool

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionTestResult:
    """连接测试结果"""
    service: str
    success: bool
    response_time_ms: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class SystemHealthReport:
    """系统健康报告"""
    overall_status: str
    connection_tests: List[ConnectionTestResult]
    recommendations: List[str]
    deployment_ready: bool
    critical_issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "connection_tests": [asdict(test) for test in self.connection_tests],
            "recommendations": self.recommendations,
            "deployment_ready": self.deployment_ready,
            "critical_issues": self.critical_issues,
            "timestamp": datetime.now().isoformat()
        }


class LiveConnectionVerifier:
    """真实API连接验证器"""

    def __init__(self):
        self.settings = get_settings()
        self.test_results = []

        # 测试用比赛ID（确保存在）
        self.test_match_id = "404650"  # 常用的比赛ID，可根据需要更改

    async def verify_all_connections(self) -> SystemHealthReport:
        """验证所有连接"""
        logger.info("🔍 开始全面连接验证...")

        # 执行所有测试
        tests = [
            ("database", self._test_database_connection),
            ("redis", self._test_redis_connection),
            ("fotmob_api", self._test_fotmob_api),
            ("model_loading", self._test_model_loading),
            ("ml_inference", self._test_ml_inference),
        ]

        for service_name, test_func in tests:
            logger.info(f"📡 测试 {service_name} 连接...")
            try:
                result = await test_func()
                self.test_results.append(result)

                status = "✅" if result.success else "❌"
                logger.info(f"{status} {service_name}: {result.response_time_ms:.0f}ms")

            except Exception as e:
                error_result = ConnectionTestResult(
                    service=service_name,
                    success=False,
                    response_time_ms=0,
                    details={},
                    error_message=str(e)
                )
                self.test_results.append(error_result)
                logger.error(f"❌ {service_name}: {str(e)}")

        # 生成报告
        report = self._generate_health_report()

        # 保存报告
        await self._save_health_report(report)

        return report

    async def _test_database_connection(self) -> ConnectionTestResult:
        """测试数据库连接"""
        start_time = time.time()

        try:
            # 测试连接池
            db_pool = DatabasePool()
            await db_pool.initialize()

            # 执行简单查询
            async with db_pool.get_connection() as conn:
                result = await conn.fetchval("SELECT version()")

                # 测试写入权限
                test_table = "connection_test"
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {test_table} (
                        id SERIAL PRIMARY KEY,
                        test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await conn.execute(f"INSERT INTO {test_table} DEFAULT VALUES")
                await conn.execute(f"DELETE FROM {test_table} WHERE test_timestamp < NOW() - INTERVAL '1 hour'")

            response_time = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                service="database",
                success=True,
                response_time_ms=response_time,
                details={
                    "version": result,
                    "connection_pool_size": db_pool.pool.size,
                    "write_permissions": True
                }
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTestResult(
                service="database",
                success=False,
                response_time_ms=response_time,
                details={},
                error_message=str(e)
            )

    async def _test_redis_connection(self) -> ConnectionTestResult:
        """测试Redis连接"""
        start_time = time.time()

        try:
            # 连接Redis
            redis_client = redis.Redis(
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                db=self.settings.redis.db,
                password=self.settings.redis.password or None,
                socket_timeout=5
            )

            # 测试基本操作
            test_key = "connection_test"
            test_value = f"test_{datetime.now().isoformat()}"

            redis_client.set(test_key, test_value, ex=60)
            retrieved_value = redis_client.get(test_key)
            redis_client.delete(test_key)

            # 测试连接信息
            info = redis_client.info()

            response_time = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                service="redis",
                success=True,
                response_time_ms=response_time,
                details={
                    "version": info.get("redis_version"),
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "test_data_integrity": retrieved_value.decode() == test_value
                }
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTestResult(
                service="redis",
                success=False,
                response_time_ms=response_time,
                details={},
                error_message=str(e)
            )

    async def _test_fotmob_api(self) -> ConnectionTestResult:
        """测试FotMob API连接"""
        start_time = time.time()

        try:
            # 准备请求头
            headers = self.settings.fotmob.get_headers()

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # 测试基础API连接
                url = f"{self.settings.fotmob.base_url}/leagues?id=87"  # Premier League ID

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        # 验证数据结构
                        leagues = data.get("leagues", [])

                        # 测试具体比赛详情
                        match_url = f"{self.settings.fotmob.base_url}/matchDetails?matchId={self.test_match_id}"

                        async with session.get(match_url, headers=headers) as match_response:
                            match_data = await match_response.json() if match_response.status == 200 else {}

                    else:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")

            response_time = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                service="fotmob_api",
                success=True,
                response_time_ms=response_time,
                details={
                    "league_count": len(leagues),
                    "api_status": response.status,
                    "match_data_available": len(match_data) > 0,
                    "response_headers": dict(response.headers),
                    "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining", "N/A")
                }
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTestResult(
                service="fotmob_api",
                success=False,
                response_time_ms=response_time,
                details={},
                error_message=str(e)
            )

    async def _test_model_loading(self) -> ConnectionTestResult:
        """测试模型加载"""
        start_time = time.time()

        try:
            # 检查模型文件
            from ml.inference.model_loader import ModelLoader

            model_loader = ModelLoader()

            # 检查默认模型
            model_info = model_loader.get_model_info()

            response_time = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                service="model_loading",
                success=True,
                response_time_ms=response_time,
                details={
                    "model_loaded": model_info["loaded"],
                    "model_name": model_info["name"],
                    "model_version": model_info["version"],
                    "model_path": model_info.get("path"),
                    "file_size_bytes": model_info.get("file_size_bytes")
                }
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTestResult(
                service="model_loading",
                success=False,
                response_time_ms=response_time,
                details={},
                error_message=str(e)
            )

    async def _test_ml_inference(self) -> ConnectionTestResult:
        """测试ML推理能力"""
        start_time = time.time()

        try:
            from ml.inference.predictor import MatchPredictor
            from strategy.kelly_criterion import KellyCriterion, KellyStrategy

            # 创建预测器
            predictor = MatchPredictor()

            # 创建Kelly系统（使用0.1倍Fractional Kelly）
            kelly = KellyCriterion(
                initial_bankroll=10000,
                kelly_strategy=KellyStrategy.FRACTIONAL_KELLY,
                fraction_multiplier=0.1  # 0.1倍凯利
            )

            # 测试预测
            test_data = {
                "home_team": "Manchester United",
                "away_team": "Arsenal",
                "home_odds": 2.10,
                "draw_odds": 3.40,
                "away_odds": 3.75
            }

            prediction_result = predictor.predict_match(test_data)
            kelly_result = kelly.generate_bet_recommendation({
                "home": {"odds": test_data["home_odds"], "probability": prediction_result["probabilities"]["home_win"]},
                "draw": {"odds": test_data["draw_odds"], "probability": prediction_result["probabilities"]["draw"]},
                "away": {"odds": test_data["away_odds"], "probability": prediction_result["probabilities"]["away_win"]},
            })

            response_time = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                service="ml_inference",
                success=True,
                response_time_ms=response_time,
                details={
                    "prediction_success": True,
                    "predictions_count": len(prediction_result["probabilities"]),
                    "kelly_recommendations": len(kelly_result),
                    "safety_enabled": kelly.get_safety_status()["safety_enabled"],
                    "model_confidence": max(prediction_result["probabilities"].values())
                }
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionTestResult(
                service="ml_inference",
                success=False,
                response_time_ms=response_time,
                details={},
                error_message=str(e)
            )

    def _generate_health_report(self) -> SystemHealthReport:
        """生成健康报告"""
        successful_tests = [r for r in self.test_results if r.success]
        failed_tests = [r for r in self.test_results if not r.success]

        # 确定整体状态
        if len(failed_tests) == 0:
            overall_status = "HEALTHY"
            deployment_ready = True
        elif len(successful_tests) >= len(self.test_results) * 0.8:
            overall_status = "WARNING"
            deployment_ready = True
        else:
            overall_status = "CRITICAL"
            deployment_ready = False

        # 识别关键问题
        critical_issues = []
        recommendations = []

        for test in failed_tests:
            if test.service in ["database", "fotmob_api"]:
                critical_issues.append(f"{test.service}: {test.error_message}")
            else:
                recommendations.append(f"修复 {test.service} 连接问题: {test.error_message}")

        # 性能建议
        slow_tests = [r for r in self.test_results if r.response_time_ms > 2000]
        if slow_tests:
            recommendations.append("以下服务响应较慢，建议优化: " + ", ".join([r.service for r in slow_tests]))

        return SystemHealthReport(
            overall_status=overall_status,
            connection_tests=self.test_results,
            recommendations=recommendations,
            deployment_ready=deployment_ready,
            critical_issues=critical_issues
        )

    async def _save_health_report(self, report: SystemHealthReport):
        """保存健康报告"""
        report_file = Path("logs/live_connection_report.json")
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"📄 健康报告已保存: {report_file}")

    async def test_specific_service(self, service_name: str) -> ConnectionTestResult:
        """测试特定服务"""
        service_map = {
            "database": self._test_database_connection,
            "redis": self._test_redis_connection,
            "fotmob": self._test_fotmob_api,
            "fotmob_api": self._test_fotmob_api,
            "model": self._test_model_loading,
            "model_loading": self._test_model_loading,
            "inference": self._test_ml_inference,
            "ml_inference": self._test_ml_inference,
        }

        if service_name not in service_map:
            raise ValueError(f"未知服务: {service_name}")

        logger.info(f"📡 测试 {service_name} 连接...")
        result = await service_map[service_name]()

        status = "✅" if result.success else "❌"
        logger.info(f"{status} {service_name}: {result.response_time_ms:.0f}ms")

        if result.error_message:
            logger.error(f"错误详情: {result.error_message}")

        return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 9 真实API连接验证")

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 全面验证命令
    all_parser = subparsers.add_parser('all', help='全面验证所有连接')
    all_parser.add_argument('--output', '-o', help='输出报告文件路径')

    # 特定服务测试
    service_parser = subparsers.add_parser('api', help='测试特定服务')
    service_parser.add_argument('service', help='服务名称 (database, redis, fotmob, model, inference)')

    # 快速检查
    quick_parser = subparsers.add_parser('quick', help='快速连接检查')

    args = parser.parse_args()

    verifier = LiveConnectionVerifier()

    try:
        if args.command == 'all':
            # 全面验证
            report = await verifier.verify_all_connections()

            # 输出摘要
            print(f"\n🏈️  Sprint 9 - 真实API连接验证完成")
            print(f"=" * 60)
            print(f"📊 整体状态: {report.overall_status}")
            print(f"🚀 部署就绪: {'✅ 是' if report.deployment_ready else '❌ 否'}")
            print(f"📡 测试服务: {len(report.connection_tests)}")
            print(f"✅ 成功连接: {len([t for t in report.connection_tests if t.success])}")
            print(f"❌ 失败连接: {len([t for t in report.connection_tests if not t.success])}")

            # 显示详细结果
            print(f"\n📋 连接测试详情:")
            for test in report.connection_tests:
                status = "✅" if test.success else "❌"
                print(f"  {status} {test.service:15} {test.response_time_ms:6.0f}ms")
                if test.error_message:
                    print(f"    错误: {test.error_message}")

            # 显示建议
            if report.recommendations:
                print(f"\n💡 改进建议:")
                for rec in report.recommendations:
                    print(f"  • {rec}")

            # 显示关键问题
            if report.critical_issues:
                print(f"\n🚨 关键问题:")
                for issue in report.critical_issues:
                    print(f"  • {issue}")

            # 退出码
            return 0 if report.deployment_ready else 1

        elif args.command == 'api':
            # 测试特定服务
            result = await verifier.test_specific_service(args.service)
            print(f"\n📡 {args.service} 连接测试:")
            print(f"状态: {'✅ 成功' if result.success else '❌ 失败'}")
            print(f"响应时间: {result.response_time_ms:.0f}ms")

            if result.success and result.details:
                print(f"详细信息:")
                for key, value in result.details.items():
                    print(f"  {key}: {value}")

            if result.error_message:
                print(f"错误: {result.error_message}")

            return 0 if result.success else 1

        elif args.command == 'quick':
            # 快速检查（只检查关键服务）
            critical_services = ["database", "redis", "fotmob"]
            all_success = True

            print(f"\n⚡ 快速连接检查...")
            for service in critical_services:
                try:
                    result = await verifier.test_specific_service(service)
                    if not result.success:
                        all_success = False
                except Exception as e:
                    print(f"❌ {service}: {str(e)}")
                    all_success = False

            print(f"\n{'✅ 所有关键服务正常' if all_success else '❌ 部分服务异常'}")
            return 0 if all_success else 1

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print(f"\n👋 验证已取消")
        return 1
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))