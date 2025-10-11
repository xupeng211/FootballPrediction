"""
from typing import Dict, List
数据质量监控器

实现数据质量检查与异常检测功能。
监控数据新鲜度、完整性、一致性和异常值。

监控指标：
- 数据新鲜度：检查最后更新时间
- 数据完整性：检查缺失值和必需字段
- 数据一致性：检查数据格式和范围
- 异常检测：识别可疑的赔率和比分

基于 DATA_DESIGN.md 第5.1节设计。
"""

from typing import Any, Dict, List
import logging
from datetime import datetime


class DataQualityMonitor:
    """
    数据质量监控器

    负责监控足球数据的质量，检测异常和问题，
    生成质量报告和告警。
    """

    def __init__(self):
        """初始化数据质量监控器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 质量检查阈值配置
        self.thresholds = {
            "data_freshness_hours": 24,  # 数据新鲜度阈值（小时）
            "missing_data_rate": 0.1,  # 缺失数据率阈值（10%）
            "odds_min_value": 1.01,  # 最小赔率值
            "odds_max_value": 100.0,  # 最大赔率值
            "score_max_value": 20,  # 最大比分值
            "suspicious_odds_change": 0.5,  # 可疑赔率变化阈值（50%）
        }

    async def check_data_freshness(self) -> Dict[str, Any]:
        """
        检查数据新鲜度

        Returns:
            Dict: 新鲜度检查结果
        """
        try:
            freshness_report: Dict[str, Any] = {
                "check_time": datetime.now().isoformat(),
                "status": "healthy",
                "issues": [],
                "warnings": [],
                "details": {},
            }

            async with self.db_manager.get_async_session() as session:
                # 检查赛程数据新鲜度
                fixtures_age = await self._check_fixtures_age(session)
                freshness_report["details"]["fixtures"] = fixtures_age

                if (
                    fixtures_age["hours_since_update"]
                    > self.thresholds["data_freshness_hours"]
                ):
                    freshness_report["issues"].append(
                        f"赛程数据过期：{fixtures_age['hours_since_update']}小时未更新"
                    )
                    freshness_report["status"] = "warning"

                # 检查赔率数据新鲜度
                odds_age = await self._check_odds_age(session)
                freshness_report["details"]["odds"] = odds_age

                if odds_age["hours_since_update"] > 1:  # 赔率数据应该更频繁更新
                    freshness_report["warnings"].append(
                        f"赔率数据可能过期：{odds_age['hours_since_update']}小时未更新"
                    )

                # 检查缺失的比赛
                missing_matches = await self._find_missing_matches(session)
                freshness_report["details"]["missing_matches"] = missing_matches

                if missing_matches["count"] > 0:
                    freshness_report["warnings"].append(
                        f"发现{missing_matches['count']}场可能缺失的比赛"
                    )

            return freshness_report

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"数据新鲜度检查失败: {str(e)}")
            return {
                "check_time": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        异常检测

        Returns:
            List[Dict]: 检测到的异常列表
        """
        anomalies: List[Any] = []

        try:
            async with self.db_manager.get_async_session() as session:
                # 检查赔率异常
                suspicious_odds = await self._find_suspicious_odds(session)
                anomalies.extend(suspicious_odds)

                # 检查比分异常
                unusual_scores = await self._find_unusual_scores(session)
                anomalies.extend(unusual_scores)

                # 检查数据一致性异常
                consistency_issues = await self._check_data_consistency(session)
                anomalies.extend(consistency_issues)

            self.logger.info(f"异常检测完成，发现{len(anomalies)}个异常")
            return anomalies

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"异常检测失败: {str(e)}")
            return [
                {
                    "type": "detection_error",
                    "message": f"异常检测过程出错: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            ]

    async def _check_fixtures_age(self, session) -> Dict[str, Any]:
        """检查赛程数据年龄"""
        try:
            # 查询最近的采集日志
            latest_log = await session.execute(
                """
                SELECT MAX(created_at) as last_update
                FROM data_collection_logs
                WHERE collection_type = 'fixtures' AND status = 'success'
                """
            )
            result = latest_log.fetchone()

            if result and result.last_update:
                hours_since = (
                    datetime.now() - result.last_update
                ).total_seconds() / 3600
                return {
                    "last_update": result.last_update.isoformat(),
                    "hours_since_update": round(hours_since, 2),
                    "status": (
                        "ok"
                        if hours_since < self.thresholds["data_freshness_hours"]
                        else "stale"
                    ),
                }
            else:
                return {
                    "last_update": None,
                    "hours_since_update": float("inf"),
                    "status": "no_data",
                }

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"检查赛程数据年龄失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _check_odds_age(self, session) -> Dict[str, Any]:
        """检查赔率数据年龄"""
        try:
            # 查询最近的赔率更新
            latest_odds = await session.execute(
                """
                SELECT MAX(collected_at) as last_update
                FROM odds
                WHERE collected_at > NOW() - INTERVAL '24 hours'
                """
            )
            result = latest_odds.fetchone()

            if result and result.last_update:
                hours_since = (
                    datetime.now() - result.last_update
                ).total_seconds() / 3600
                return {
                    "last_update": result.last_update.isoformat(),
                    "hours_since_update": round(hours_since, 2),
                    "status": "ok" if hours_since < 1 else "stale",
                }
            else:
                return {
                    "last_update": None,
                    "hours_since_update": float("inf"),
                    "status": "no_data",
                }

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"检查赔率数据年龄失败: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _find_missing_matches(self, session) -> Dict[str, Any]:
        """查找缺失的比赛"""
        try:
            # TODO: 实现缺失比赛检测逻辑
            # 1. 根据联赛赛程规律检测缺失的比赛
            # 2. 对比不同数据源的比赛数量

            return {"count": 0, "matches": [], "check_time": datetime.now().isoformat()}

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"查找缺失比赛失败: {str(e)}")
            return {"count": 0, "error": str(e)}

    async def _find_suspicious_odds(self, session) -> List[Dict[str, Any]]:
        """查找可疑赔率"""
        suspicious_odds: List[Any] = []

        try:
            # 查找异常的赔率值
            abnormal_odds = await session.execute(
                text(  # type: ignore
                    """
                SELECT id, match_id, bookmaker, home_odds, draw_odds, away_odds, collected_at
                FROM odds
                WHERE (home_odds < :odds_min_value
                       OR home_odds > :odds_max_value)
                   OR (draw_odds < :odds_min_value
                       OR draw_odds > :odds_max_value)
                   OR (away_odds < :odds_min_value
                       OR away_odds > :odds_max_value)
                AND collected_at > NOW() - INTERVAL '7 days'
                """
                ),
                {
                    "odds_min_value": self.thresholds["odds_min_value"],
                    "odds_max_value": self.thresholds["odds_max_value"],
                },
            )

            for row in abnormal_odds.fetchall():
                suspicious_odds.append(
                    {
                        "type": "abnormal_odds_value",
                        "odds_id": row.id,
                        "match_id": row.match_id,
                        "bookmaker": row.bookmaker,
                        "odds": {
                            "home": float(row.home_odds) if row.home_odds else None,
                            "draw": float(row.draw_odds) if row.draw_odds else None,
                            "away": float(row.away_odds) if row.away_odds else None,
                        },
                        "collected_at": row.collected_at.isoformat(),
                        "severity": "high",
                    }
                )

            # 查找赔率急剧变化
            # TODO: 实现赔率变化检测逻辑

            return suspicious_odds

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"查找可疑赔率失败: {str(e)}")
            return []

    async def _find_unusual_scores(self, session) -> List[Dict[str, Any]]:
        """查找异常比分"""
        unusual_scores: List[Any] = []

        try:
            # 查找异常高的比分
            high_scores = await session.execute(
                text(  # type: ignore
                    """
                SELECT id, home_team_id, away_team_id, home_score, away_score, match_time
                FROM matches
                WHERE (home_score > :score_max_value
                       OR away_score > :score_max_value)
                AND match_status = 'finished'
                AND match_time > NOW() - INTERVAL '30 days'
                """
                ),
                {"score_max_value": self.thresholds["score_max_value"]},
            )

            for row in high_scores.fetchall():
                unusual_scores.append(
                    {
                        "type": "unusual_high_score",
                        "match_id": row.id,
                        "home_team_id": row.home_team_id,
                        "away_team_id": row.away_team_id,
                        "score": f"{row.home_score}-{row.away_score}",
                        "match_time": row.match_time.isoformat(),
                        "severity": "medium",
                    }
                )

            return unusual_scores

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"查找异常比分失败: {str(e)}")
            return []

    async def _check_data_consistency(self, session) -> List[Dict[str, Any]]:
        """检查数据一致性"""
        consistency_issues: List[Any] = []

        try:
            # 检查比赛时间一致性
            time_issues = await session.execute(
                """
                SELECT id, match_time, created_at
                FROM matches
                WHERE match_time < created_at - INTERVAL '1 day'
                AND match_time > NOW() - INTERVAL '7 days'
                """
            )

            for row in time_issues.fetchall():
                consistency_issues.append(
                    {
                        "type": "inconsistent_match_time",
                        "match_id": row.id,
                        "match_time": row.match_time.isoformat(),
                        "created_at": row.created_at.isoformat(),
                        "message": "比赛时间早于创建时间",
                        "severity": "low",
                    }
                )

            return consistency_issues

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"检查数据一致性失败: {str(e)}")
            return []

    async def generate_quality_report(self) -> Dict[str, Any]:
        """
        生成完整的数据质量报告

        Returns:
            Dict: 质量报告
        """
        try:
            self.logger.info("开始生成数据质量报告")

            # 执行各项检查
            freshness_check = await self.check_data_freshness()
            anomalies = await self.detect_anomalies()

            # 计算总体质量评分
            quality_score = self._calculate_quality_score(freshness_check, anomalies)

            report: Dict[str, Any] = {
                "report_time": datetime.now().isoformat(),
                "overall_status": self._determine_overall_status(
                    freshness_check, anomalies
                ),
                "quality_score": quality_score,
                "freshness_check": freshness_check,
                "anomalies": {
                    "count": len(anomalies),
                    "high_severity": len(
                        [a for a in anomalies if a.get("severity") == "high"]
                    ),
                    "medium_severity": len(
                        [a for a in anomalies if a.get("severity") == "medium"]
                    ),
                    "low_severity": len(
                        [a for a in anomalies if a.get("severity") == "low"]
                    ),
                    "details": anomalies,
                },
                "recommendations": self._generate_recommendations(
                    freshness_check, anomalies
                ),
            }

            self.logger.info(
                f"数据质量报告生成完成，总体状态: {report['overall_status']}"
            )
            return report

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"生成数据质量报告失败: {str(e)}")
            return {
                "report_time": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e),
            }

    def _calculate_quality_score(self, freshness_check: Dict, anomalies: List) -> float:
        """计算质量评分（0-100）"""
        score = 100.0

        # 根据新鲜度扣分
        if freshness_check.get("status") == "warning":
            score -= 20
        elif freshness_check.get("status") == "error":
            score -= 40

        # 根据异常数量扣分
        high_severity_count = len([a for a in anomalies if a.get("severity") == "high"])
        medium_severity_count = len(
            [a for a in anomalies if a.get("severity") == "medium"]
        )
        low_severity_count = len([a for a in anomalies if a.get("severity") == "low"])

        score -= high_severity_count * 15
        score -= medium_severity_count * 8
        score -= low_severity_count * 3

        return max(0.0, score)

    def _determine_overall_status(self, freshness_check: Dict, anomalies: List) -> str:
        """确定总体状态"""
        high_severity_count = len([a for a in anomalies if a.get("severity") == "high"])

        if freshness_check.get("status") == "error" or high_severity_count > 5:
            return "critical"
        elif freshness_check.get("status") == "warning" or high_severity_count > 0:
            return "warning"
        else:
            return "healthy"

    def _generate_recommendations(
        self, freshness_check: Dict, anomalies: List
    ) -> List[str]:
        """生成改进建议"""
        recommendations: List[Any] = []

        if freshness_check.get("status") in ["warning", "error"]:
            recommendations.append("检查数据采集调度器是否正常运行")
            recommendations.append("验证外部API连接状态")

        high_severity_count = len([a for a in anomalies if a.get("severity") == "high"])
        if high_severity_count > 0:
            recommendations.append("立即处理高严重性异常数据")
            recommendations.append("检查数据源的可靠性")

        if len(anomalies) > 10:
            recommendations.append("考虑调整异常检测阈值")
            recommendations.append("增强数据验证规则")

        return recommendations
