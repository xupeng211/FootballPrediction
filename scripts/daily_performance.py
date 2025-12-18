#!/usr/bin/env python3
"""
Sprint 9 实时监控看板 - 每日性能统计脚本

实时监控和统计系统性能：
1. 每日预测场次统计
2. 平均EV (期望价值) 计算
3. Kelly安全系统拦截次数统计
4. 资金池余额跟踪
5. 预测准确率监控
6. 系统性能指标

使用方法:
  python daily_performance.py --daily
  python daily_performance.py --realtime
  python daily_performance.py --report --date 2024-12-18

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - Production Monitoring)
"""

import asyncio
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import sqlite3
import pandas as pd
import requests
from dataclasses import dataclass, asdict
from decimal import Decimal

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings
from database.db_pool import DatabasePool

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class DailyPerformanceMetrics:
    """每日性能指标"""

    date: str
    total_predictions: int
    successful_predictions: int
    failed_predictions: int
    average_confidence: float
    average_ev: float
    kelly_safety_blocks: int
    kelly_manual_reviews: int
    total_staked: float
    total_return: float
    net_profit_loss: float
    roi_percentage: float
    current_bankroll: float
    prediction_accuracy: float
    brier_score: float
    system_uptime: float
    api_response_time: float
    memory_usage_mb: float
    cpu_usage_percentage: float
    data_collection_success_rate: float
    model_inference_time_ms: float


class RealTimeDashboard:
    """实时监控看板"""

    def __init__(self):
        self.settings = get_settings()
        self.db_pool = None

    async def initialize(self):
        """初始化数据库连接"""
        self.db_pool = DatabasePool()
        await self.db_pool.initialize()

    async def generate_daily_report(self, date: str = None) -> DailyPerformanceMetrics:
        """生成每日性能报告"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"📊 生成 {date} 的性能报告")

        # 获取基础指标
        metrics = await self._collect_basic_metrics(date)

        # 获取Kelly安全指标
        kelly_metrics = await self._collect_kelly_metrics(date)
        metrics.update(kelly_metrics)

        # 获取财务指标
        financial_metrics = await self._collect_financial_metrics(date)
        metrics.update(financial_metrics)

        # 获取预测质量指标
        quality_metrics = await self._collect_quality_metrics(date)
        metrics.update(quality_metrics)

        # 获取系统性能指标
        performance_metrics = await self._collect_system_metrics()
        metrics.update(performance_metrics)

        return DailyPerformanceMetrics(**metrics)

    async def _collect_basic_metrics(self, date: str) -> Dict[str, Any]:
        """收集基础指标"""
        try:
            async with self.db_pool.get_connection() as conn:
                # 查询当天的预测记录
                query = """
                SELECT
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN success = true THEN 1 END) as successful_predictions,
                    COUNT(CASE WHEN success = false THEN 1 END) as failed_predictions,
                    AVG(confidence) as average_confidence
                FROM matches_realtime
                WHERE DATE(created_at) = $1
                """

                result = await conn.fetchrow(query, date)

                return {
                    "date": date,
                    "total_predictions": result["total_predictions"] or 0,
                    "successful_predictions": result["successful_predictions"] or 0,
                    "failed_predictions": result["failed_predictions"] or 0,
                    "average_confidence": float(result["average_confidence"] or 0.0),
                }

        except Exception as e:
            logger.error(f"收集基础指标失败: {e}")
            return {
                "date": date,
                "total_predictions": 0,
                "successful_predictions": 0,
                "failed_predictions": 0,
                "average_confidence": 0.0,
            }

    async def _collect_kelly_metrics(self, date: str) -> Dict[str, Any]:
        """收集Kelly安全指标"""
        try:
            async with self.db_pool.get_connection() as conn:
                # 查询Kelly安全统计
                query = """
                SELECT
                    COUNT(CASE WHEN safety_block = true THEN 1 END) as kelly_safety_blocks,
                    COUNT(CASE WHEN manual_review = true THEN 1 END) as kelly_manual_reviews,
                    AVG(ev) as average_ev
                FROM matches_realtime
                WHERE DATE(created_at) = $1
                """

                result = await conn.fetchrow(query, date)

                return {
                    "kelly_safety_blocks": result["kelly_safety_blocks"] or 0,
                    "kelly_manual_reviews": result["kelly_manual_reviews"] or 0,
                    "average_ev": float(result["average_ev"] or 0.0),
                }

        except Exception as e:
            logger.error(f"收集Kelly指标失败: {e}")
            return {
                "kelly_safety_blocks": 0,
                "kelly_manual_reviews": 0,
                "average_ev": 0.0,
            }

    async def _collect_financial_metrics(self, date: str) -> Dict[str, Any]:
        """收集财务指标"""
        try:
            async with self.db_pool.get_connection() as conn:
                # 查询财务统计
                query = """
                SELECT
                    COALESCE(SUM(stake_amount), 0) as total_staked,
                    COALESCE(SUM(return_amount), 0) as total_return
                FROM matches_realtime
                WHERE DATE(created_at) = $1
                AND stake_amount > 0
                """

                result = await conn.fetchrow(query, date)

                total_staked = float(result["total_staked"])
                total_return = float(result["total_return"])
                net_profit_loss = total_return - total_staked
                roi_percentage = (
                    (net_profit_loss / total_staked * 100) if total_staked > 0 else 0.0
                )

                # 获取当前资金池
                bankroll_query = """
                SELECT current_bankroll FROM kelly_portfolio
                ORDER BY updated_at DESC
                LIMIT 1
                """

                bankroll_result = await conn.fetchrow(bankroll_query)
                current_bankroll = (
                    float(bankroll_result["current_bankroll"])
                    if bankroll_result
                    else 10000.0
                )

                return {
                    "total_staked": total_staked,
                    "total_return": total_return,
                    "net_profit_loss": net_profit_loss,
                    "roi_percentage": roi_percentage,
                    "current_bankroll": current_bankroll,
                }

        except Exception as e:
            logger.error(f"收集财务指标失败: {e}")
            return {
                "total_staked": 0.0,
                "total_return": 0.0,
                "net_profit_loss": 0.0,
                "roi_percentage": 0.0,
                "current_bankroll": 10000.0,
            }

    async def _collect_quality_metrics(self, date: str) -> Dict[str, Any]:
        """收集预测质量指标"""
        try:
            async with self.db_pool.get_connection() as conn:
                # 计算预测准确率
                accuracy_query = """
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN predicted_outcome = actual_outcome THEN 1 END) as correct_predictions
                FROM matches_realtime
                WHERE DATE(created_at) = $1
                AND actual_outcome IS NOT NULL
                """

                accuracy_result = await conn.fetchrow(accuracy_query, date)

                total_matches = accuracy_result["total_matches"]
                correct_predictions = accuracy_result["correct_predictions"]
                prediction_accuracy = (
                    (correct_predictions / total_matches * 100)
                    if total_matches > 0
                    else 0.0
                )

                # 计算Brier Score（如果可用）
                brier_score = await self._calculate_brier_score(date, conn)

                return {
                    "prediction_accuracy": prediction_accuracy,
                    "brier_score": brier_score,
                }

        except Exception as e:
            logger.error(f"收集质量指标失败: {e}")
            return {"prediction_accuracy": 0.0, "brier_score": 0.0}

    async def _calculate_brier_score(self, date: str, conn) -> float:
        """计算Brier Score"""
        try:
            # 简化的Brier Score计算
            query = """
            SELECT
                predicted_prob_home,
                predicted_prob_draw,
                predicted_prob_away,
                actual_outcome
            FROM matches_realtime
            WHERE DATE(created_at) = $1
            AND actual_outcome IS NOT NULL
            AND (predicted_prob_home IS NOT NULL
                 AND predicted_prob_draw IS NOT NULL
                 AND predicted_prob_away IS NOT NULL)
            """

            results = await conn.fetch(query, date)

            if not results:
                return 0.0

            brier_score_sum = 0.0
            for result in results:
                # 获取预测概率
                pred_home = result["predicted_prob_home"]
                pred_draw = result["predicted_prob_draw"]
                pred_away = result["predicted_prob_away"]

                # 创建实际结果向量
                actual_outcome = result["actual_outcome"]
                if actual_outcome == "HOME":
                    actual_vector = [1, 0, 0]
                elif actual_outcome == "DRAW":
                    actual_vector = [0, 1, 0]
                elif actual_outcome == "AWAY":
                    actual_vector = [0, 0, 1]
                else:
                    continue

                predicted_vector = [pred_home, pred_draw, pred_away]

                # 计算Brier Score: (predicted - actual)^2
                brier_score = sum(
                    (p - a) ** 2 for p, a in zip(predicted_vector, actual_vector)
                )
                brier_score_sum += brier_score

            return brier_score_sum / len(results) if results else 0.0

        except Exception as e:
            logger.error(f"计算Brier Score失败: {e}")
            return 0.0

    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统性能指标"""
        try:
            import psutil

            # 系统资源使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()

            # API响应时间（通过健康检查）
            api_response_time = await self._measure_api_response_time()

            # 模型推理时间（从日志或性能监控）
            model_inference_time = await self._get_model_inference_time()

            # 数据收集成功率
            data_collection_success_rate = (
                await self._get_data_collection_success_rate()
            )

            return {
                "system_uptime": time.time(),  # 简化的uptime
                "api_response_time": api_response_time,
                "memory_usage_mb": memory_info.used / (1024 * 1024),
                "cpu_usage_percentage": cpu_percent,
                "model_inference_time_ms": model_inference_time,
                "data_collection_success_rate": data_collection_success_rate,
            }

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {
                "system_uptime": 0.0,
                "api_response_time": 0.0,
                "memory_usage_mb": 0.0,
                "cpu_usage_percentage": 0.0,
                "model_inference_time_ms": 0.0,
                "data_collection_success_rate": 0.0,
            }

    async def _measure_api_response_time(self) -> float:
        """测量API响应时间"""
        try:
            import requests

            start_time = time.time()
            response = requests.get("http://localhost:8000/health", timeout=5)
            response_time = (time.time() - start_time) * 1000
            return response_time if response.status_code == 200 else 0.0
        except:
            return 0.0

    async def _get_model_inference_time(self) -> float:
        """获取模型推理时间"""
        try:
            async with self.db_pool.get_connection() as conn:
                query = """
                SELECT AVG(inference_time_ms) as avg_inference_time
                FROM model_performance_logs
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                """

                result = await conn.fetchrow(query)
                return float(result["avg_inference_time"] or 0.0)
        except:
            return 0.0

    async def _get_data_collection_success_rate(self) -> float:
        """获取数据收集成功率"""
        try:
            async with self.db_pool.get_connection() as conn:
                query = """
                SELECT
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN success = true THEN 1 END) as successful_attempts
                FROM data_collection_logs
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                """

                result = await conn.fetchrow(query)
                total = result["total_attempts"]
                successful = result["successful_attempts"]

                return (successful / total * 100) if total > 0 else 0.0
        except:
            return 0.0

    async def generate_realtime_dashboard(self) -> Dict[str, Any]:
        """生成实时监控看板数据"""
        logger.info("📈 生成实时监控看板")

        try:
            # 获取今日性能指标
            today_metrics = await self.generate_daily_report()

            # 获取7天趋势
            trend_data = await self._get_seven_day_trend()

            # 获取实时告警
            alerts = await self._get_active_alerts()

            # 获取系统状态
            system_status = await self._get_system_status()

            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "today_metrics": asdict(today_metrics),
                "seven_day_trend": trend_data,
                "active_alerts": alerts,
                "system_status": system_status,
            }

            # 保存看板数据
            await self._save_dashboard_data(dashboard_data)

            return dashboard_data

        except Exception as e:
            logger.error(f"生成实时看板失败: {e}")
            return {"error": str(e)}

    async def _get_seven_day_trend(self) -> List[Dict[str, Any]]:
        """获取7天趋势数据"""
        try:
            async with self.db_pool.get_connection() as conn:
                query = """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN success = true THEN 1 END) as successful_predictions,
                    AVG(confidence) as avg_confidence,
                    COALESCE(SUM(stake_amount), 0) as total_staked,
                    COALESCE(SUM(return_amount), 0) as total_return
                FROM matches_realtime
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """

                results = await conn.fetch(query)

                trend_data = []
                for result in results:
                    net_pl = float(result["total_return"]) - float(
                        result["total_staked"]
                    )
                    roi = (
                        (net_pl / float(result["total_staked"]) * 100)
                        if float(result["total_staked"]) > 0
                        else 0.0
                    )

                    trend_data.append(
                        {
                            "date": result["date"].strftime("%Y-%m-%d"),
                            "total_predictions": result["total_predictions"],
                            "successful_predictions": result["successful_predictions"],
                            "avg_confidence": float(result["avg_confidence"] or 0),
                            "total_staked": float(result["total_staked"]),
                            "total_return": float(result["total_return"]),
                            "net_profit_loss": net_pl,
                            "roi_percentage": roi,
                        }
                    )

                return trend_data

        except Exception as e:
            logger.error(f"获取7天趋势失败: {e}")
            return []

    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = []

        try:
            # 检查资金风险告警
            today_metrics = await self.generate_daily_report()
            if today_metrics.roi_percentage < -10:  # 当日亏损超过10%
                alerts.append(
                    {
                        "type": "financial",
                        "severity": "high",
                        "message": f"当日ROI过低: {today_metrics.roi_percentage:.1f}%",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 检查安全系统告警
            if today_metrics.kelly_safety_blocks > 5:  # 安全拦截过多
                alerts.append(
                    {
                        "type": "safety",
                        "severity": "medium",
                        "message": f"Kelly安全拦截次数过多: {today_metrics.kelly_safety_blocks}次",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 检查系统性能告警
            if today_metrics.api_response_time > 2000:  # API响应过慢
                alerts.append(
                    {
                        "type": "performance",
                        "severity": "medium",
                        "message": f"API响应时间过长: {today_metrics.api_response_time:.0f}ms",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 检查预测准确率告警
            if today_metrics.prediction_accuracy < 40:  # 准确率过低
                alerts.append(
                    {
                        "type": "quality",
                        "severity": "high",
                        "message": f"预测准确率过低: {today_metrics.prediction_accuracy:.1f}%",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            logger.error(f"获取告警失败: {e}")

        return alerts

    async def _get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            import requests

            # 检查各个服务状态
            services = {
                "api": "http://localhost:8000/health",
                "database": "http://localhost:8000/api/v1/health/database",
                "redis": "http://localhost:8000/api/v1/health/redis",
                "model": "http://localhost:8000/api/v1/health/model",
            }

            status = {}
            for service, url in services.items():
                try:
                    response = requests.get(url, timeout=5)
                    status[service] = {
                        "status": (
                            "healthy" if response.status_code == 200 else "unhealthy"
                        ),
                        "response_time": response.elapsed.total_seconds() * 1000,
                    }
                except:
                    status[service] = {"status": "down", "response_time": 0}

            # 计算整体状态
            healthy_count = sum(1 for s in status.values() if s["status"] == "healthy")
            total_count = len(status)

            overall_status = "healthy"
            if healthy_count < total_count:
                overall_status = "partial" if healthy_count > 0 else "down"

            return {
                "overall_status": overall_status,
                "services": status,
                "healthy_percentage": (
                    (healthy_count / total_count * 100) if total_count > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"overall_status": "error", "services": {}, "healthy_percentage": 0}

    async def _save_dashboard_data(self, dashboard_data: Dict[str, Any]):
        """保存看板数据"""
        try:
            dashboard_dir = Path("data/dashboard")
            dashboard_dir.mkdir(parents=True, exist_ok=True)

            # 保存最新数据
            latest_file = dashboard_dir / "latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)

            # 保存历史数据（按日期）
            date_file = dashboard_dir / f"{datetime.now().strftime('%Y%m%d')}.json"
            with open(date_file, "w", encoding="utf-8") as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info("📄 看板数据已保存")

        except Exception as e:
            logger.error(f"保存看板数据失败: {e}")

    async def check_observation_mode_conditions(self) -> Dict[str, Any]:
        """检查是否需要进入观察模式"""
        logger.info("🔍 检查观察模式条件")

        try:
            # 获取最近10场比赛的Brier Score
            async with self.db_pool.get_connection() as conn:
                query = """
                SELECT
                    predicted_prob_home,
                    predicted_prob_draw,
                    predicted_prob_away,
                    actual_outcome,
                    created_at
                FROM matches_realtime
                WHERE actual_outcome IS NOT NULL
                AND created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 10
                """

                results = await conn.fetch(query)

                if len(results) < 10:
                    return {
                        "should_enter_observation_mode": False,
                        "reason": "数据不足（少于10场比赛）",
                        "current_brier_score": 0.0,
                        "historical_brier_score": 0.0,
                        "deviation_percentage": 0.0,
                    }

                # 计算最近的Brier Score
                recent_brier = await self._calculate_brier_score_from_results(results)

                # 获取历史回测的Brier Score（这里简化处理）
                historical_brier = 0.25  # 假设历史回测Brier Score为0.25

                # 计算偏差
                deviation = abs(recent_brier - historical_brier)
                deviation_percentage = (
                    (deviation / historical_brier * 100) if historical_brier > 0 else 0
                )

                # 判断是否需要进入观察模式
                should_enter_observation = deviation_percentage > 15  # 偏差超过15%

                result = {
                    "should_enter_observation_mode": should_enter_observation,
                    "reason": (
                        f"Brier Score偏差{deviation_percentage:.1f}%超过15%阈值"
                        if should_enter_observation
                        else "Brier Score在正常范围内"
                    ),
                    "current_brier_score": recent_brier,
                    "historical_brier_score": historical_brier,
                    "deviation_percentage": deviation_percentage,
                    "recent_matches_count": len(results),
                }

                if should_enter_observation:
                    logger.warning(f"⚠️ 建议进入观察模式: {result['reason']}")
                    await self._trigger_observation_mode(result)
                else:
                    logger.info(f"✅ 无需进入观察模式: {result['reason']}")

                return result

        except Exception as e:
            logger.error(f"检查观察模式条件失败: {e}")
            return {
                "should_enter_observation_mode": False,
                "reason": f"检查失败: {str(e)}",
                "current_brier_score": 0.0,
                "historical_brier_score": 0.0,
                "deviation_percentage": 0.0,
            }

    async def _calculate_brier_score_from_results(self, results) -> float:
        """从结果计算Brier Score"""
        try:
            brier_score_sum = 0.0
            valid_results = 0

            for result in results:
                pred_home = result["predicted_prob_home"]
                pred_draw = result["predicted_prob_draw"]
                pred_away = result["predicted_prob_away"]

                if None in [pred_home, pred_draw, pred_away]:
                    continue

                actual_outcome = result["actual_outcome"]
                if actual_outcome == "HOME":
                    actual_vector = [1, 0, 0]
                elif actual_outcome == "DRAW":
                    actual_vector = [0, 1, 0]
                elif actual_outcome == "AWAY":
                    actual_vector = [0, 0, 1]
                else:
                    continue

                predicted_vector = [pred_home, pred_draw, pred_away]

                brier_score = sum(
                    (p - a) ** 2 for p, a in zip(predicted_vector, actual_vector)
                )
                brier_score_sum += brier_score
                valid_results += 1

            return brier_score_sum / valid_results if valid_results > 0 else 0.0

        except Exception as e:
            logger.error(f"计算Brier Score失败: {e}")
            return 0.0

    async def _trigger_observation_mode(self, reason: Dict[str, Any]):
        """触发观察模式"""
        logger.critical(f"🚨 触发观察模式: {reason['reason']}")

        try:
            # 记录观察模式触发事件
            async with self.db_pool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO observation_mode_events
                    (trigger_reason, brier_score, deviation_percentage, created_at)
                    VALUES ($1, $2, $3, NOW())
                """,
                    reason["reason"],
                    reason["current_brier_score"],
                    reason["deviation_percentage"],
                )

            # 这里可以添加更多的观察模式触发逻辑
            # 例如：修改系统配置、发送告警通知等

        except Exception as e:
            logger.error(f"触发观察模式失败: {e}")

    def print_dashboard_summary(self, metrics: DailyPerformanceMetrics):
        """打印看板摘要"""
        print("\n" + "=" * 60)
        print("📈 足球预测系统 - 实时监控看板")
        print("=" * 60)
        print(f"📅 日期: {metrics.date}")
        print(f"🎯 预测统计: {metrics.total_predictions} 场")
        print(f"✅ 成功预测: {metrics.successful_predictions} 场")
        print(f"❌ 失败预测: {metrics.failed_predictions} 场")
        print(f"📊 平均置信度: {metrics.average_confidence:.1%}")
        print(f"💰 平均EV: {metrics.average_ev:.3f}")
        print(f"🛡️ Kelly安全拦截: {metrics.kelly_safety_blocks} 次")
        print(f"👥 Kelly人工审查: {metrics.kelly_manual_reviews} 次")
        print(f"💵 总投注金额: ¥{metrics.total_staked:,.2f}")
        print(f"💸 总回报金额: ¥{metrics.total_return:,.2f}")
        print(f"📈 净盈亏: ¥{metrics.net_profit_loss:,.2f}")
        print(f"📊 ROI: {metrics.roi_percentage:.2f}%")
        print(f"💰 当前资金池: ¥{metrics.current_bankroll:,.2f}")
        print(f"🎯 预测准确率: {metrics.prediction_accuracy:.1%}")
        print(f"📏 Brier Score: {metrics.brier_score:.4f}")
        print(f"⚡ API响应时间: {metrics.api_response_time:.0f}ms")
        print(f"💾 内存使用: {metrics.memory_usage_mb:.1f}MB")
        print(f"🖥️ CPU使用率: {metrics.cpu_usage_percentage:.1f}%")
        print("=" * 60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 9 实时监控看板")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 每日报告命令
    daily_parser = subparsers.add_parser("daily", help="生成每日性能报告")
    daily_parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)")

    # 实时看板命令
    realtime_parser = subparsers.add_parser("realtime", help="生成实时监控看板")

    # 报告命令
    report_parser = subparsers.add_parser("report", help="生成性能报告")
    report_parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)")

    # 观察模式检查
    observation_parser = subparsers.add_parser(
        "check-observation", help="检查观察模式条件"
    )

    args = parser.parse_args()

    dashboard = RealTimeDashboard()
    await dashboard.initialize()

    try:
        if args.command == "daily":
            # 生成每日报告
            date = args.date or datetime.now().strftime("%Y-%m-%d")
            metrics = await dashboard.generate_daily_report(date)

            dashboard.print_dashboard_summary(metrics)

            # 保存报告
            report_data = asdict(metrics)
            report_file = Path(f"logs/daily_report_{date}.json")
            report_file.parent.mkdir(exist_ok=True)

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n📄 报告已保存: {report_file}")

        elif args.command == "realtime":
            # 生成实时看板
            dashboard_data = await dashboard.generate_realtime_dashboard()

            print("\n📈 实时监控看板")
            print("=" * 40)
            print(f"📊 时间: {dashboard_data['timestamp']}")

            # 今日指标
            today = dashboard_data["today_metrics"]
            print(f"🎯 今日预测: {today['total_predictions']} 场")
            print(f"💰 ROI: {today['roi_percentage']:.2f}%")
            print(f"🛡️ 安全拦截: {today['kelly_safety_blocks']} 次")

            # 系统状态
            status = dashboard_data["system_status"]
            print(f"🖥️ 系统状态: {status['overall_status']}")
            print(f"✅ 服务健康度: {status['healthy_percentage']:.1f}%")

            # 告警
            alerts = dashboard_data["active_alerts"]
            if alerts:
                print(f"⚠️ 活跃告警: {len(alerts)} 个")
                for alert in alerts[:3]:  # 只显示前3个
                    print(f"  • {alert['message']}")
            else:
                print("✅ 无活跃告警")

        elif args.command == "report":
            # 生成性能报告
            date = args.date or datetime.now().strftime("%Y-%m-%d")
            metrics = await dashboard.generate_daily_report(date)

            dashboard.print_dashboard_summary(metrics)

            # 生成详细报告
            report_data = {
                "metrics": asdict(metrics),
                "timestamp": datetime.now().isoformat(),
                "report_type": "daily_performance",
            }

            report_file = Path(f"logs/performance_report_{date}.json")
            report_file.parent.mkdir(exist_ok=True)

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n📄 性能报告已保存: {report_file}")

        elif args.command == "check-observation":
            # 检查观察模式条件
            result = await dashboard.check_observation_mode_conditions()

            print("\n🔍 观察模式检查结果")
            print("=" * 40)
            print(
                f"是否进入观察模式: {'是' if result['should_enter_observation_mode'] else '否'}"
            )
            print(f"原因: {result['reason']}")
            print(f"当前Brier Score: {result['current_brier_score']:.4f}")
            print(f"历史Brier Score: {result['historical_brier_score']:.4f}")
            print(f"偏差百分比: {result['deviation_percentage']:.1f}%")

        else:
            parser.print_help()
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n👋 监控已停止")
        return 1
    except Exception as e:
        logger.error(f"❌ 监控失败: {e}")
        return 1
    finally:
        if dashboard.db_pool:
            await dashboard.db_pool.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
